#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Le pilotage du studio par programme, eprouve DE BOUT EN BOUT dans serveur.py.

banc_acces.py, banc_rappels.py et banc_mcp.py gardent les trois modules purs :
la forme d'une cle, la signature d'un rappel, le protocole MCP. Aucun des trois
ne voit ce que serveur.py en fait — et c'est la que se jouent les promesses :
une cle qui ouvrirait l'administration, un programme qui lirait les images
faites a la main, un rendu « sans nuage » parti chez un fournisseur facture.
Ce banc-ci passe par les vraies routes, le vrai middleware « identite » et le
vrai « exiger_compte », avec des requetes fabriquees, sans reseau ni carte.

CE QU'IL GARDE, DANS L'ORDRE DES DEGATS :

  1. L'identite par cle : elle donne le bon compte, ne pose aucun cookie, ne
     vaut que sur /api/v1/ et /mcp (403 ailleurs, sans appeler la route), se
     freine apres trois cles fausses SANS freiner les mots de passe, et meurt
     avec le mot de passe ou le compte — sans ressusciter avec un compte
     recree sous le meme nom.
  2. Une cle ne vaut jamais administration, meme sur un compte admin et meme
     accompagnee du jeton X-Admin.
  3. exiger_compte laisse les routes de programme a leur propre garde, et
     une session de navigateur n'y suffit pas (401 « cle_requise »).
  4. La gestion des cles : session ET mot de passe (ET code si le second
     facteur est arme) pour en creer une, la cle montree une fois sans cache,
     revocation de SES cles seulement, console d'administration au jeton.
  5. Lancer un rendu : marque « api » sur la tache et la file, conversation
     neuve invisible de la page, toutes les gardes AVANT la file (vide,
     longueur, moteur, mineurs, nuage, rappel, file pleine, plafond du jour
     qui survit a un rechargement, idempotence, conversation d'une autre cle,
     image en base64, attente bornee).
  6. Lire un rendu : chaque etat public, les groupes de variantes, la lecture
     apres redemarrage, et le cloisonnement par cle.
  7. Les fichiers : par rang, par lien signe sans cle, et la mort du lien avec
     sa cle.
  8. Le nuage : nuage_permis, llm_distant_possible, la marque restauree par
     reprendre_file() et recopiee par lancer_variantes().
  9. Les rappels : livres une fois, signes du secret de la cle, jamais pour
     une cle revoquee ni pour un rendu pas fini.
 10. MCP : le transport, les six outils, les refus sans exception.
 11. La retention : seules les conversations de PROGRAMME vieilles de trente
     jours se ferment.
 12. Deux gardes relues dans le texte : garde_fou apres traduire() dans
     executer(), la marque recopiee dans lancer_variantes().

    Lancer : python banc_pilotage.py
    (sous Bash : cd /d/ComfyStudio && uv run --with aiohttp python banc_pilotage.py)

CE QU'IL NE VOIT PAS :

  - Le vrai routeur aiohttp et le vrai transport HTTP : les requetes sont
    fabriquees, le middleware est appele a la main. Un chemin mal declare dans
    app() ne se verrait pas ici.
  - Un vrai rendu : les taches « finies » sont posees a la main, executer()
    ne tourne pas. Que la garde du nuage d'executer() replie bien sur le local
    n'est vu que par la lecture du texte (section 12) et par nuage_permis().
  - Un vrai POST de rappel : rappels.livrer est remplace ; sa mecanique
    (re-essais, redirections) est l'affaire de banc_rappels.py.
  - origine_verifiee et en_tetes_surs : ils ne sont pas dans la chaine
    appelee ici.
  - Le temps long : le lien qui expire au bout d'un jour, la retention mesuree
    sur l'horloge, l'oubli des echecs.
"""
import ast
import asyncio
import base64
import json
import os
import shutil
import sys
import tempfile
import time
import uuid

ICI = os.path.dirname(os.path.abspath(__file__))
DOSSIER = tempfile.mkdtemp(prefix="banc_pilotage_")
os.environ["STUDIO_DONNEES"] = DOSSIER
os.environ["STUDIO_AUTH"] = "obligatoire"
# LE DOSSIER D'ENTREE DE COMFYUI, ET LE SIEN SEULEMENT. Sans ces deux lignes le
# studio vise le ComfyUI voisin du depot : l'image en base64 du cas 5 serait
# ecrite dans son vrai dossier input, et purger_entrees() y ferait le menage.
os.environ["COMFY_DIR"] = os.path.join(DOSSIER, "comfy")
os.environ["COMFY_ENTREE"] = os.path.join(DOSSIER, "entrees")
sys.path.insert(0, ICI)
import serveur as S  # noqa: E402
import acces  # noqa: E402
import comptes  # noqa: E402
import mfa  # noqa: E402
import rappels  # noqa: E402
from aiohttp import web  # noqa: E402
from multidict import CIMultiDict  # noqa: E402

ok, rate = [], []


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


MDP = "mot-de-passe-du-banc"
MDP_NEUF = "un-autre-mot-de-passe-du-banc"
JETON_ADMIN = "jeton-admin-du-banc-0123456789abcdef"
HOTE_N8N = "n8n.maison:5678"
RAPPEL_OK = "http://n8n.maison:5678/webhook/3f1c-banc"
REFUS_MINEUR = "a child in a sexual pose"     # un des REFUS de banc_adulte.py
ILLISIBLE = object()
OUTILS_MCP = {"generer_rendu", "etat_rendu", "repondre_question",
              "annuler_rendu", "lister_rendus", "lister_moteurs"}


class Transport:
    """Ce que _cle_freinage() et _identite_par_cle() lisent : l'adresse."""

    def get_extra_info(self, quoi, defaut=None):
        return ("127.0.0.1", 5000) if quoi == "peername" else defaut


class Req(dict):
    """Le minimum qu'attendent le middleware et les routes de programme.

    Les en-tetes sont un CIMultiDict, comme ceux d'aiohttp : « authorization »
    et « Authorization » sont le meme en-tete, et un dict ordinaire ferait
    rater a la route celui qu'un client ecrit en minuscules.
    match_info est un dict MUTABLE : api_v1_annuler y ecrit l'identifiant de
    chaque tirage avant d'appeler l'annulation de la page.
    """

    def __init__(self, chemin="/", methode="GET", cle=None, entetes=None,
                 cookies=None, corps=None, match=None, requete=None, **champs):
        super().__init__(**champs)
        self.path = chemin
        self.method = methode
        self.headers = CIMultiDict(entetes or {})
        if "Host" not in self.headers:
            self.headers["Host"] = "studio.maison:8199"
        if cle:
            self.headers["Authorization"] = f"Bearer {cle}"
        self.cookies = dict(cookies or {})
        self.match_info = dict(match or {})
        self.query = dict(requete or {})
        self.scheme = "http"
        self.transport = Transport()
        self._corps = corps

    async def json(self):
        if self._corps is None or self._corps is ILLISIBLE:
            raise ValueError("corps illisible")
        return self._corps


def lire(rep):
    try:
        corps = json.loads(rep.text) if rep.text else None
    except (TypeError, ValueError):
        corps = None
    return rep.status, corps


async def passer(req, route):
    """La requete par les deux middlewares qui decident de l'identite."""
    async def suite(r):
        return await S.exiger_compte(r, route)
    return await S.identite(req, suite)


async def appel(req, route, middleware=True):
    """(statut, corps, reponse). Jamais d'exception : une route qui leve rend
    un 500 fabrique, et le banc continue — sinon il s'arreterait avant la
    ligne qu'une mutation nomme, et passerait pour casse."""
    try:
        if middleware:
            rep = await passer(req, route)
        else:
            rep = await route(req)
    except web.HTTPException as e:
        return e.status, None, e
    except Exception as e:
        return 500, {"erreur": f"la route a leve {type(e).__name__}: {e}"}, None
    statut, corps = lire(rep)
    return statut, corps, rep


def code(corps):
    return (corps or {}).get("code") if isinstance(corps, dict) else None


class Temoin:
    """Une route factice qui note ce que le middleware lui a passe."""

    def __init__(self):
        self.vus = []

    async def __call__(self, req):
        self.vus.append({"compte": req.get("compte"), "pid": req.get("pid"),
                         "par_cle": req.get("par_cle")})
        return web.json_response({"ok": True})


def nouvelle_cle(compte, nom, **reglages):
    reglages.setdefault("hotes", [HOTE_N8N])
    return S.ACCES.creer(compte, nom, S.COMPTES.generation(compte), **reglages)


def fiche_de(cle):
    return S.ACCES.reconnaitre(cle, S._generation_du_compte)


def pid_de(nom):
    return comptes.identifiant(nom)


def cle_fausse(cle):
    """La meme forme, un dernier caractere change : seul le secret est faux."""
    return cle[:-1] + ("A" if cle[-1] != "A" else "B")


def vider_file():
    n = 0
    while S.FILE_ATTENTE is not None and not S.FILE_ATTENTE.empty():
        S.FILE_ATTENTE.get_nowait()
        n += 1
    return n


def remise_a_zero():
    for registre in (S.TACHES, S.CONVERSATIONS, S.EN_FILE, S.ARMEES,
                     S.IDEMPOTENCE, S._ECHECS, S.COURANTE, S.ENTREES,
                     S.EN_VOL, S.AVANCES):
        registre.clear()
    S.ATTENTE.clear()
    vider_file()


def conv_de_programme(fiche):
    conv = S._vide(titre="programme", proprietaire=pid_de(fiche["compte"]))
    conv["api"] = {"cle": fiche["id"], "nom": fiche["nom"], "lancements": []}
    S.CONVERSATIONS[conv["id"]] = conv
    return conv


def poser_rendu(fiche, etat="fini", conv=None, tache=True, fichiers=None,
                variantes=None, rappel=None, nuage=False):
    """Un rendu de programme ecrit a la main : la tache, et son tour.

    etat : « fini », « question », « erreur », ou « en cours ».
    """
    conv = conv or conv_de_programme(fiche)
    tid = uuid.uuid4().hex
    if fichiers is None:
        fichiers = ([{"filename": f"rendu_{tid[:8]}.png", "subfolder": "",
                      "type": "output", "noeud": "local"}]
                    if etat == "fini" else [])
    conv["tours"].append({
        "id": tid, "heure": "12:00", "demande": "un phare dans la brume",
        "modele": "klein4b", "type": "image", "etat": etat,
        "fichiers": fichiers, "variantes": variantes,
        "questions": ["De quelle couleur ?"] if etat == "question" else None,
        "avis": 0, "note": ""})
    if tache:
        S.TACHES[tid] = {
            "etapes": [{"t": "12:00", "msg": "rendu du banc"}], "etat": etat,
            "debut": time.time(), "demande": "un phare dans la brume",
            "conversation": conv["id"], "proprietaire": pid_de(fiche["compte"]),
            "api": {"cle": fiche["id"], "nuage": nuage, "rappel": rappel,
                    "base": "", "langue": "fr"},
            "plan": {"intention": "image", "modele": "klein4b"},
            "fichiers": list(fichiers)}
        if variantes:
            S.TACHES[tid]["variantes"] = dict(variantes)
        if etat == "question":
            S.TACHES[tid]["questions"] = ["De quelle couleur ?"]
    return tid, conv


# ══════════════════════════════════════════════════════════════════════
#  Le decor : des comptes, des cles, un jeton d'administration
# ══════════════════════════════════════════════════════════════════════
S.COMPTES = comptes.Comptes(os.path.join(DOSSIER, "_comptes.json"), "secret-de-banc")
S.ACCES = acces.Acces(os.path.join(DOSSIER, "_acces.json"))
S.ACCES.charger()
S.SECRET_LIENS = "secret-des-liens-du-banc"
S.ADMIN_JETON = JETON_ADMIN
for _nom, _admin in (("jordan", True), ("camille", False), ("sacha", False),
                     ("dominique", False), ("lou", False), ("maxime", False)):
    S.COMPTES.creer(_nom, MDP, admin=_admin)
PID_J = pid_de("jordan")

N8N = nouvelle_cle("jordan", "n8n", nuage=False)               # sans nuage
AGENT = nouvelle_cle("jordan", "agent", nuage=True)            # meme compte, nuage
# « maxime » n'est touche par aucune section : sa cle vit d'un bout a l'autre,
# et un 404 sur elle dit le cloisonnement, pas une cle eteinte en route.
AUTRUI = nouvelle_cle("maxime", "maxime n8n", nuage=True)      # un autre compte
K_N8N, K_AGENT, K_AUTRUI = N8N["cle"], AGENT["cle"], AUTRUI["cle"]
F_N8N, F_AGENT, F_AUTRUI = fiche_de(K_N8N), fiche_de(K_AGENT), fiche_de(K_AUTRUI)


# ══════════════════════════════════════════════════════════════════════
#  1. L'identite par cle
# ══════════════════════════════════════════════════════════════════════
async def s_identite():
    temoin = Temoin()
    st, _c, rep = await appel(Req("/api/v1/moi", cle=K_N8N), temoin)
    vu = temoin.vus[-1] if temoin.vus else {}
    dit(st == 200 and len(temoin.vus) == 1,
        "une vraie cle sur /api/v1/moi atteint la route", f"HTTP {st}")
    dit(vu.get("compte") == "jordan" and vu.get("pid") == PID_J,
        "la route voit le compte de la cle, et l'espace de ce compte",
        f"{vu.get('compte')} / {str(vu.get('pid'))[:8]}")
    dit(bool(vu.get("par_cle")) and vu["par_cle"].get("id") == F_N8N["id"],
        "la fiche de la cle est posee sur la requete (par_cle)")
    dit(rep is not None and len(rep.cookies) == 0,
        "une reponse a un programme ne pose AUCUN cookie",
        ", ".join(rep.cookies) if rep is not None else "pas de reponse")
    # Le temoin du « aucun cookie » : la meme route, sans cle, en pose un.
    _st, _c, rep_ = await appel(Req("/api/v1/moi"), Temoin())
    dit(rep_ is not None and "studio" in rep_.cookies,
        "temoin : sans cle, le middleware pose bien son cookie « studio »")

    for chemin in ("/api/generer", "/api/admin/noeuds", "/api/compte/acces",
                   "/api/fichier", "/mcp/"):
        t = Temoin()
        st, c, _r = await appel(Req(chemin, "POST", cle=K_N8N), t)
        dit(st == 403 and code(c) == "cle_hors_perimetre" and not t.vus,
            f"la cle sur {chemin} est refusee en 403 « cle_hors_perimetre », "
            f"route jamais appelee", f"HTTP {st} {code(c)} appels={len(t.vus)}")

    t = Temoin()
    st, c, rep = await appel(Req("/api/v1/moi", cle=cle_fausse(K_N8N)), t)
    dit(st == 401 and code(c) == "cle_refusee" and not t.vus,
        "une cle au secret faux rend 401 « cle_refusee », route jamais appelee",
        f"HTTP {st} {code(c)}")
    dit(rep is not None and "Bearer" in (rep.headers.get("WWW-Authenticate") or ""),
        "et son 401 porte WWW-Authenticate: Bearer (RFC 6750)")
    t = Temoin()
    await appel(Req("/api/v1/moi", cle=K_N8N,
                    cookies={"studio_compte": S.COMPTES.jeton("maxime")}), t)
    vu = t.vus[-1] if t.vus else {}
    dit(vu.get("compte") == "jordan" and vu.get("pid") == PID_J,
        "la cle PRIME sur le cookie de session d'un autre compte", str(vu.get("compte")))
    S.COMPTES.creer("Lea.M", MDP)
    t = Temoin()
    await appel(Req("/api/v1/moi", cle=nouvelle_cle("Lea.M", "script")["cle"]), t)
    vu = t.vus[-1] if t.vus else {}
    dit(vu.get("compte") == "Lea.M" and vu.get("pid") == pid_de("Lea.M"),
        "le compte d'une cle garde son nom EXACT (le dossier de sorties en depend)",
        str(vu.get("compte")))
    st, _c, _r = await appel(Req("/api/v1/moi", cle="cs_pas_la_forme"), Temoin())
    dit(st == 401, "une cle mal formee « cs_… » rend 401 elle aussi", f"HTTP {st}")
    S._ECHECS.clear()

    # Un jeton de proxy : ignore, la requete continue par son cookie.
    t = Temoin()
    st, _c, _r = await appel(Req("/api/compte", entetes={
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.proxy.signature"},
        cookies={"studio_compte": S.COMPTES.jeton("jordan")}), t)
    vu = t.vus[-1] if t.vus else {}
    dit(st == 200 and vu.get("compte") == "jordan" and not vu.get("par_cle"),
        "un « Bearer » de proxy sans « cs_ » est ignore : la session passe, "
        "sans par_cle", f"HTTP {st} compte={vu.get('compte')}")

    # Le freinage : trois secrets faux pour UNE cle, puis 429 au quatrieme —
    # mais la BONNE cle passe toujours. Le frein se lisait avant la
    # verification, et l'identifiant public d'une cle (imprime dans chaque lien
    # signe) suffisait a la tenir en 429 : revue de securite du 4 novembre 2026.
    S.ECHECS_CLES.clear()
    for _ in range(3):
        await appel(Req("/api/v1/moi", cle=cle_fausse(K_N8N)), Temoin())
    t = Temoin()
    st, c, _r = await appel(Req("/api/v1/moi", cle=cle_fausse(K_N8N)), t)
    t_bonne = Temoin()
    st_b, _c, _r = await appel(Req("/api/v1/moi", cle=K_N8N), t_bonne)
    dit(st == 429 and code(c) == "trop_d_essais" and not t.vus,
        "apres trois secrets faux pour une cle, le quatrieme rend 429",
        f"HTTP {st} {code(c)}")
    dit(st_b == 200 and bool(t_bonne.vus),
        "et la bonne cle passe quand meme : on verifie avant de freiner",
        f"HTTP {st_b}")

    compte_, refus_ = S._ouvrir_porte(Req("/api/compte/entrer", "POST"),
                                      "jordan", MDP, None, "fr")
    dit(refus_ is None and bool(compte_),
        "et ce compteur n'est PAS celui des connexions : jordan entre encore "
        "par mot de passe depuis la meme adresse",
        f"refus HTTP {refus_.status}" if refus_ is not None else "")
    # (La bonne cle a remis son compteur a zero : on rejoue la rafale pour
    # lire ou elle s'inscrit.)
    for _ in range(3):
        await appel(Req("/api/v1/moi", cle=cle_fausse(K_N8N)), Temoin())
    dit(bool(S.ECHECS_CLES) and not any(k[0] == "jordan" for k in S._ECHECS)
        and not any(len(k) == 3 for k in S._ECHECS),
        "temoin : la rafale est comptee, dans la table des cles et pas dans "
        "celle des connexions", repr(list(S.ECHECS_CLES)))
    S.ECHECS_CLES.clear()

    # DES CLES AU HASARD N'INSCRIVENT RIEN. Elles remplissaient la table
    # commune et chassaient les compteurs des mots de passe : un identifiant
    # qui ne designe aucune cle n'a rien a deviner. Le temoin : un secret faux
    # pour une cle qui EXISTE, lui, s'inscrit.
    for i in range(50):
        await appel(Req("/api/v1/moi",
                        cle=f"cs_{i:08x}_" + "A" * 43), Temoin())
    au_hasard = len(S.ECHECS_CLES)
    await appel(Req("/api/v1/moi", cle=cle_fausse(K_N8N)), Temoin())
    dit(au_hasard == 0 and len(S.ECHECS_CLES) == 1,
        "cinquante cles d'identifiant inconnu n'inscrivent rien ; un secret "
        "faux pour une vraie cle, si", f"{au_hasard} puis {len(S.ECHECS_CLES)}")
    S.ECHECS_CLES.clear()

    # UNE CLE MORTE NE FREINE PERSONNE. Un n8n qui interroge encore avec une
    # cle REVOQUEE ne doit pas couper les autres workflows du meme hote, dont
    # les cles sont bonnes. Elle est refusee en 401, toujours, et n'inscrit
    # rien : revoquee, elle n'a plus de secret a deviner.
    S.ECHECS_CLES.clear()
    morte = nouvelle_cle("jordan", "cle revoquee")
    S.ACCES.revoquer(morte["fiche"]["id"])
    for _ in range(6):
        await appel(Req("/api/v1/moi", cle=morte["cle"]), Temoin())
    t_vivante, t_morte = Temoin(), Temoin()
    st_v, _c, _r = await appel(Req("/api/v1/moi", cle=K_N8N), t_vivante)
    st_m, c_m, _r = await appel(Req("/api/v1/moi", cle=morte["cle"]), t_morte)
    dit(st_v == 200 and t_vivante.vus and st_m == 401 and code(c_m) == "cle_refusee"
        and not S.ECHECS_CLES,
        "une cle revoquee qui insiste est refusee sans rien inscrire, et ne "
        "freine pas les cles valides de la meme adresse",
        f"vivante HTTP {st_v}, morte HTTP {st_m}, table {len(S.ECHECS_CLES)}")
    S.ECHECS_CLES.clear()

    # Le mot de passe change : la cle meurt.
    k = nouvelle_cle("sacha", "script")["cle"]
    st1, _c, _r = await appel(Req("/api/v1/moi", cle=k), Temoin())
    S.COMPTES.changer_mdp("sacha", MDP_NEUF)
    st2, c2, _r = await appel(Req("/api/v1/moi", cle=k), Temoin())
    dit(st1 == 200 and st2 == 401,
        "changer le mot de passe du compte eteint sa cle (401)",
        f"avant HTTP {st1}, apres HTTP {st2} {code(c2)}")

    # Le compte supprime : la cle est revoquee, et ne ressuscite pas.
    res = nouvelle_cle("dominique", "script")
    st1, _c, _r = await appel(Req("/api/v1/moi", cle=res["cle"]), Temoin())
    st, c, _r = await appel(Req("/api/admin/comptes/dominique", "DELETE",
                                entetes={"X-Admin": JETON_ADMIN},
                                match={"nom": "dominique"}),
                            S.api_admin_compte_supprimer, middleware=False)
    dit(st1 == 200 and st == 200 and S.ACCES.fiche(res["fiche"]["id"]) is None,
        "supprimer le compte revoque sa cle dans le magasin",
        f"avant HTTP {st1}, suppression HTTP {st}")
    S.COMPTES.creer("dominique", MDP)
    st, _c, _r = await appel(Req("/api/v1/moi", cle=res["cle"]), Temoin())
    dit(st == 401 and S.COMPTES.generation("dominique") == res["fiche"]["generation"],
        "un compte recree sous le meme nom (meme generation) ne ressuscite "
        "pas l'ancienne cle", f"HTTP {st}")
    S._ECHECS.clear()


# ══════════════════════════════════════════════════════════════════════
#  2. La cle ne vaut jamais administration
# ══════════════════════════════════════════════════════════════════════
async def s_administration():
    r = Req("/api/v1/moi", entetes={"X-Admin": JETON_ADMIN}, compte="jordan",
            pid=PID_J, par_cle=F_N8N)
    dit(S.admin_ok(r) is False,
        "admin_ok() est faux pour une cle posee sur un compte admin, MEME "
        "avec un X-Admin valide")
    dit(S.est_admin(r) is False,
        "est_admin() est faux pour une cle posee sur un compte admin")
    sans = Req("/api/admin/acces", entetes={"X-Admin": JETON_ADMIN},
               compte="jordan", pid=PID_J)
    dit(S.admin_ok(sans) is True and S.est_admin(sans) is True,
        "temoin : la meme requete sans cle est administratrice")


# ══════════════════════════════════════════════════════════════════════
#  3. exiger_compte et la garde des routes de programme
# ══════════════════════════════════════════════════════════════════════
async def s_exiger():
    for chemin in ("/api/v1/rendus", "/api/v1/lien/x", "/mcp"):
        t = Temoin()
        rep = await S.exiger_compte(Req(chemin, "POST", compte=""), t)
        dit(rep.status == 200 and len(t.vus) == 1,
            f"exiger_compte laisse {chemin} a sa propre garde", f"HTTP {rep.status}")
    t = Temoin()
    rep = await S.exiger_compte(Req("/api/generer", "POST", compte=""), t)
    dit(rep.status == 401 and not t.vus,
        "temoin : exiger_compte ferme /api/generer sans compte", f"HTTP {rep.status}")

    st, c, rep = await appel(Req("/api/v1/moi", compte="jordan", pid=PID_J),
                             S.api_v1_moi, middleware=False)
    dit(st == 401 and code(c) == "cle_requise"
        and "Bearer" in ((rep.headers.get("WWW-Authenticate") or "") if rep is not None else ""),
        "une route v1 sans cle rend 401 « cle_requise » + WWW-Authenticate, "
        "meme avec un compte connecte", f"HTTP {st} {code(c)}")
    st, c, _r = await appel(Req("/api/v1/rendus", "POST", corps={"demande": "un chat"},
                                cookies={"studio_compte": S.COMPTES.jeton("jordan")}),
                            S.api_v1_rendre)
    dit(st == 401 and code(c) == "cle_requise" and not S.TACHES,
        "une vraie session de navigateur ne lance rien sur /api/v1/rendus",
        f"HTTP {st} {code(c)}")
    st, c, _r = await appel(Req("/api/v1/moi", par_cle=F_N8N, compte="jordan",
                                pid=PID_J), S.api_v1_moi, middleware=False)
    dit(st == 200 and (c or {}).get("compte") == "jordan",
        "temoin : la meme route avec une fiche de cle repond 200", f"HTTP {st}")


# ══════════════════════════════════════════════════════════════════════
#  4. La gestion des cles par leur proprietaire
# ══════════════════════════════════════════════════════════════════════
async def s_gestion():
    S._ECHECS.clear()
    for methode, route in (("GET", S.api_mes_acces), ("POST", S.api_creer_acces)):
        st, _c, _r = await appel(Req("/api/compte/acces", methode, corps={},
                                     compte=""), route, middleware=False)
        dit(st == 401, f"{methode} /api/compte/acces sans session rend 401",
            f"HTTP {st}")
    st, _c, _r = await appel(Req("/api/compte/acces", compte="jordan", pid=PID_J,
                                 par_cle=F_N8N), S.api_mes_acces, middleware=False)
    dit(st == 401, "une cle ne liste pas les cles, meme posee sur le compte",
        f"HTTP {st}")

    biscuit = {"studio_compte": S.COMPTES.jeton("sacha")}
    st, _c, _r = await appel(Req("/api/compte/acces", "POST", cookies=biscuit,
                                 corps={"mdp": "pas-le-bon-mdp", "nom": "n8n"}),
                             S.api_creer_acces)
    dit(st == 403 and S._ECHECS.get(("sacha", "127.0.0.1"), (0,))[0] == 1,
        "un mauvais mot de passe refuse la creation, et compte dans le "
        "freinage des connexions", f"HTTP {st} {S._ECHECS}")
    S._ECHECS.clear()
    avant = len(S.ACCES.liste("sacha"))
    st, c_cree, rep = await appel(Req("/api/compte/acces", "POST", cookies=biscuit,
                                      corps={"mdp": MDP_NEUF, "nom": "n8n du salon",
                                             "hotes": [HOTE_N8N]}),
                                  S.api_creer_acces)
    cle = (c_cree or {}).get("cle") or ""
    dit(st == 201 and cle.startswith("cs_") and len(S.ACCES.liste("sacha")) == avant + 1,
        "le bon mot de passe cree la cle, rendue en clair", f"HTTP {st}")
    dit(rep is not None and (rep.headers.get("Cache-Control") or "") == "no-store",
        "la reponse qui porte la cle est « Cache-Control: no-store »",
        (rep.headers.get("Cache-Control") if rep is not None else "") or "absent")
    st2, c2, _r = await appel(Req("/api/v1/moi", cle=cle), S.api_v1_moi)
    dit(st2 == 200 and (c2 or {}).get("compte") == "sacha",
        "et elle marche aussitot par le middleware", f"HTTP {st2}")

    st, c, _r = await appel(Req("/api/compte/acces", cookies=biscuit), S.api_mes_acces)
    cles = (c or {}).get("cles") or []
    actives = {x.get("id"): x.get("active") for x in cles}
    dit(st == 200 and actives.get(((c_cree or {}).get("fiche") or {}).get("id")) is True,
        "la liste du proprietaire montre sa cle neuve active", repr(actives))
    dit(False in actives.values(),
        "et celle que le mot de passe change en section 1 a eteinte, inactive",
        repr(actives))
    dit(cles and not any("empreinte" in x or "secret_rappel" in x for x in cles),
        "et ni l'empreinte ni le secret de rappel n'y sortent")
    S.COMPTES.changer_mdp("sacha", MDP)
    biscuit = {"studio_compte": S.COMPTES.jeton("sacha")}
    st, c, _r = await appel(Req("/api/compte/acces", cookies=biscuit), S.api_mes_acces)
    cles = (c or {}).get("cles") or []
    dit(st == 200 and cles and all(x.get("active") is False for x in cles),
        "apres un changement de mot de passe, la liste les montre eteintes",
        f"HTTP {st}, actives={[x.get('active') for x in cles]}")

    # Le second facteur arme : le code est exige.
    secret, _uri = S.COMPTES.mfa_preparer("camille")
    S.COMPTES.mfa_confirmer("camille", mfa.code(secret, quand=time.time() - mfa.PAS))
    bisc_c = {"studio_compte": S.COMPTES.jeton("camille")}
    st, c, _r = await appel(Req("/api/compte/acces", "POST", cookies=bisc_c,
                                corps={"mdp": MDP, "nom": "agent"}), S.api_creer_acces)
    dit(st == 403 and (c or {}).get("mfa") is True,
        "second facteur arme : sans code, la creation est refusee (403, mfa)",
        f"HTTP {st}")
    st, c, _r = await appel(Req("/api/compte/acces", "POST", cookies=bisc_c,
                                corps={"mdp": MDP, "nom": "agent",
                                       "code": mfa.code(secret)}), S.api_creer_acces)
    dit(st == 201 and str((c or {}).get("cle", "")).startswith("cs_"),
        "et avec le code, elle est acceptee", f"HTTP {st}")
    cle_camille = (c or {}).get("fiche", {}).get("id")

    # Revoquer : la sienne oui, celle d'un autre non.
    mienne = nouvelle_cle("sacha", "a revoquer")
    st, _c, _r = await appel(Req(f"/api/compte/acces/{mienne['fiche']['id']}",
                                 "DELETE", cookies=biscuit,
                                 match={"ident": mienne["fiche"]["id"]}),
                             S.api_revoquer_acces)
    dit(st == 200 and S.ACCES.fiche(mienne["fiche"]["id"]) is None,
        "DELETE de SA cle la revoque (200)", f"HTTP {st}")
    st, _c, _r = await appel(Req(f"/api/compte/acces/{cle_camille}", "DELETE",
                                 cookies=biscuit, match={"ident": cle_camille}),
                             S.api_revoquer_acces)
    dit(st == 404 and S.ACCES.fiche(cle_camille) is not None,
        "DELETE de la cle d'un AUTRE compte rend 404, et elle vit encore",
        f"HTTP {st}")

    # LA DATE DE FIN, de bout en bout : choisie a la creation, refusee en 401
    # « cle_expiree » une fois passee — son propre code, sans compter d'echec —,
    # et la cle n'est plus « vivante » pour ses liens et ses rappels.
    st, c, _r = await appel(Req("/api/compte/acces", "POST", cookies=biscuit,
                                corps={"mdp": MDP, "nom": "essai",
                                       "expire_jours": 30}), S.api_creer_acces)
    fin_ = ((c or {}).get("fiche") or {}).get("expire") or 0
    dit(st == 201 and abs(fin_ - (time.time() + 30 * 86400)) < 60,
        "une cle creee pour 30 jours porte sa date de fin", f"HTTP {st}")
    st, c, _r = await appel(Req("/api/compte/acces", "POST", cookies=biscuit,
                                corps={"mdp": MDP, "nom": "trop longue",
                                       "expire_jours": 400}), S.api_creer_acces)
    dit(st == 400 and code(c) == "acces_expire",
        "une duree de plus d'un an est refusee, avec son code", f"HTTP {st} {code(c)}")
    vieille_ = S.ACCES.creer("sacha", "expiree", S.COMPTES.generation("sacha"),
                             expire_jours=1, maintenant=time.time() - 2 * 86400)
    S.ECHECS_CLES.clear()
    for _ in range(5):
        await appel(Req("/api/v1/moi", cle=vieille_["cle"]), Temoin())
    t_exp = Temoin()
    st, c, _r = await appel(Req("/api/v1/moi", cle=vieille_["cle"]), t_exp)
    dit(st == 401 and code(c) == "cle_expiree" and not t_exp.vus,
        "une cle passee sa date de fin rend 401 « cle_expiree », meme apres "
        "cinq essais", f"HTTP {st} {code(c)}")
    dit(not S.ECHECS_CLES,
        "et ses essais ne comptent pas comme des secrets faux : le secret est "
        "juste, c'est la date qui est passee", repr(list(S.ECHECS_CLES)))
    st, c, _r = await appel(Req("/api/v1/moi", cle=cle_fausse(vieille_["cle"])), Temoin())
    dit(st == 401 and code(c) == "cle_refusee",
        "un secret FAUX pour une cle expiree rend « cle_refusee » : la date de "
        "fin ne se lit qu'avec la cle", f"HTTP {st} {code(c)}")
    S.ECHECS_CLES.clear()
    dit(not S.cle_vivante(S.ACCES.fiche(vieille_["fiche"]["id"]))
        and S.cle_vivante(S.ACCES.fiche(((nouvelle_cle("sacha", "un jour",
                                                       expire_jours=1))["fiche"])["id"])),
        "une cle expiree n'est plus vivante pour ses liens et ses rappels ; une "
        "cle d'un jour, neuve, l'est")
    st, c, _r = await appel(Req("/api/compte/acces", cookies=biscuit), S.api_mes_acces)
    par_id = {x.get("id"): x for x in (c or {}).get("cles") or []}
    v_ = par_id.get(vieille_["fiche"]["id"]) or {}
    dit(v_.get("expiree") is True and v_.get("active") is False,
        "la liste du proprietaire la montre expiree, et inactive", repr(v_.get("expiree")))
    dit(((c or {}).get("bornes") or {}).get("expirations") == list(S._acces.EXPIRATIONS),
        "et propose a la page les durees que le magasin connait")
    # MORTE PENDANT L'ATTENTE. Une attente dure jusqu'a dix minutes : la cle
    # peut arriver a sa date de fin, ou etre revoquee, entre la question et la
    # reponse. La route REST rend alors le bon code ; MCP, qui insere l'image
    # en base64, ne doit pas la donner non plus (relecture du 4 novembre 2026).
    pendant = nouvelle_cle("sacha", "pendant l'attente", expire_jours=1)
    f_pendant = pendant["fiche"]
    tid_p, _conv_p = poser_rendu(f_pendant, "fini")
    req_p = Req(f"/api/v1/rendus/{tid_p}", cle=pendant["cle"], match={"tid": tid_p})
    req_p["pid"], req_p["compte"] = pid_de("sacha"), "sacha"
    rep_ = await S._repondre_rendu(req_p, f_pendant, tid_p)
    dit(rep_.status == 200, "temoin : vivante, la cle lit son rendu fini", f"HTTP {rep_.status}")
    S.ACCES.fiches[f_pendant["id"]]["expire"] = time.time() - 1
    rep_ = await S._repondre_rendu(req_p, f_pendant, tid_p)
    dit(rep_.status == 401 and json.loads(rep_.text).get("code") == "cle_expiree",
        "une cle arrivee a sa date de fin PENDANT l'attente rend « cle_expiree », "
        "pas « cle_refusee »", f"HTTP {rep_.status} {rep_.text[:80]}")
    try:
        await S._resultat_mcp(req_p, f_pendant, tid_p)
        donne = "l'outil MCP a rendu le resultat"
    except S._mcp.ErreurOutil as e:
        donne = "" if str(e) == S.T("erreur.cle_expiree", "fr") else f"refus : {e}"
    dit(not donne, "et l'outil MCP refuse lui aussi de rendre l'image, avec la "
        "meme raison", donne)
    S.ACCES.fiches[f_pendant["id"]]["expire"] = None
    S.ACCES.revoquer(f_pendant["id"])
    rep_ = await S._repondre_rendu(req_p, f_pendant, tid_p)
    dit(rep_.status == 401 and json.loads(rep_.text).get("code") == "cle_refusee",
        "revoquee pendant l'attente, elle rend « cle_refusee »", f"HTTP {rep_.status}")
    for ident_ in [i for i, f in list(S.ACCES.fiches.items())
                   if f["compte"] == "sacha" and f["nom"] in ("essai", "expiree", "un jour")]:
        S.ACCES.revoquer(ident_)

    # L'administration.
    st, c, _r = await appel(Req("/api/admin/acces", entetes={"X-Admin": JETON_ADMIN}),
                            S.api_admin_acces)
    cles = (c or {}).get("cles") or []
    dit(st == 200 and len(cles) == len(S.ACCES.fiches) >= 5
        and not any("empreinte" in x or "secret_rappel" in x for x in cles),
        "GET /api/admin/acces liste toutes les cles, sans leurs secrets",
        f"HTTP {st}, {len(cles)} sur {len(S.ACCES.fiches)}")
    st, _c, _r = await appel(Req("/api/admin/acces"), S.api_admin_acces)
    dit(st == 403, "sans jeton, /api/admin/acces rend 403", f"HTTP {st}")
    st, _c, _r = await appel(Req("/api/admin/acces", entetes={"X-Admin": JETON_ADMIN},
                                 cle=K_N8N), S.api_admin_acces)
    dit(st == 403, "une cle avec le jeton X-Admin n'ouvre pas la console des cles",
        f"HTTP {st}")
    victime = nouvelle_cle("sacha", "victime de l'admin")["fiche"]["id"]
    st, _c, _r = await appel(Req(f"/api/admin/acces/{victime}", "DELETE",
                                 entetes={"X-Admin": JETON_ADMIN},
                                 match={"ident": victime}), S.api_admin_acces_revoquer)
    dit(st == 200 and S.ACCES.fiche(victime) is None,
        "DELETE /api/admin/acces/{ident} revoque n'importe quelle cle", f"HTTP {st}")


# ══════════════════════════════════════════════════════════════════════
#  5. Lancer un rendu
# ══════════════════════════════════════════════════════════════════════
async def lancer(cle, corps, entetes=None):
    return await appel(Req("/api/v1/rendus", "POST", cle=cle, corps=corps,
                           entetes=entetes), S.api_v1_rendre)


def rien_de_plus(avant):
    """Rien en file, aucune tache, aucune conversation de plus."""
    return (len(S.TACHES), S.FILE_ATTENTE.qsize(), len(S.CONVERSATIONS)) == avant


def etat_des_registres():
    return len(S.TACHES), S.FILE_ATTENTE.qsize(), len(S.CONVERSATIONS)


async def s_lancer():
    remise_a_zero()
    page = S._vide(proprietaire=PID_J)
    page["modifie"] = time.time() - 3600
    S.CONVERSATIONS[page["id"]] = page

    st, c, rep = await lancer(K_N8N, {"demande": "un phare dans la brume"})
    tid = (c or {}).get("id") or ""
    t = S.TACHES.get(tid) or {}
    marque = t.get("api") or {}
    dit(st == 202 and len(tid) == 32, "POST /api/v1/rendus rend 202 et un identifiant",
        f"HTTP {st}")
    dit(marque.get("cle") == F_N8N["id"] and marque.get("nuage") is False
        and "rappel" in marque,
        "la tache porte la marque « api » (cle, nuage, rappel)", repr(marque)[:90])
    dit((S.EN_FILE.get(tid) or {}).get("api") == marque and marque,
        "l'entree de la file porte la MEME marque (elle va sur le disque)")
    dit(S.FILE_ATTENTE.qsize() == 1, "un element est pousse dans la file",
        f"{S.FILE_ATTENTE.qsize()}")
    conv = S.CONVERSATIONS.get(t.get("conversation")) or {}
    dit(conv and conv.get("id") != page["id"]
        and (conv.get("api") or {}).get("cle") == F_N8N["id"],
        "une conversation NEUVE, marquee « api », est creee pour ce rendu")
    vider_file()

    st, c, _r = await appel(Req("/api/conversations", compte="jordan", pid=PID_J),
                            S.api_conversations, middleware=False)
    ids = [x.get("id") for x in (c or {}).get("conversations") or []]
    dit(page["id"] in ids and conv.get("id") not in ids,
        "la conversation du programme n'apparait pas dans la liste de la page",
        f"{len(ids)} listee(s)")
    S.COURANTE.clear()
    choisie = S.conv_de(None, PID_J)
    dit(choisie.get("id") == page["id"] and conv.get("modifie", 0) > page["modifie"],
        "conv_de() ne choisit pas la conversation de programme, meme plus recente",
        f"choisie {choisie.get('id')}")

    # Les refus de la validation commune : rien en file.
    for corps, quoi in (({"demande": "   "}, "une demande vide"),
                        ({"demande": "x" * (S.DEMANDE_MAX + 1)}, "une demande trop longue"),
                        ({"demande": "un chat", "moteur": "pas-un-moteur"}, "un moteur inconnu")):
        avant = etat_des_registres()
        st, c, _r = await lancer(K_N8N, corps)
        dit(st == 400 and rien_de_plus(avant),
            f"{quoi} rend 400 sans rien mettre en file", f"HTTP {st} {code(c)}")

    avant, jour = etat_des_registres(), S._lances_aujourdhui(F_N8N["id"])
    st, c, _r = await lancer(K_N8N, {"demande": REFUS_MINEUR})
    dit(st == 422 and code(c) == "refus_mineurs" and rien_de_plus(avant),
        "garde_fou AVANT la file : 422 « refus_mineurs », rien en file",
        f"HTTP {st} {code(c)}")
    dit(S._lances_aujourdhui(F_N8N["id"]) == jour,
        "et le refus ne compte pas dans le plafond du jour")
    await lancer(K_N8N, {"demande": "un phare"})
    vider_file()
    dit(S._lances_aujourdhui(F_N8N["id"]) == jour + 1,
        "temoin : un lancement accepte, lui, y compte")

    # Le nuage.
    garde = S.CLES.get("nanobanana")
    S.CLES["nanobanana"] = {"cle": "cle-de-banc"}
    try:
        avant = etat_des_registres()
        st, c, _r = await lancer(K_N8N, {"demande": "un chat", "moteur": "nanobanana"})
        dit(st == 400 and code(c) == "cle_sans_nuage" and rien_de_plus(avant),
            "un moteur distant sur une cle sans nuage rend 400 « cle_sans_nuage »",
            f"HTTP {st} {code(c)}")
        st, c, _r = await lancer(K_N8N, {"demande": "un chat", "moteur": "nanobanana",
                                         "nuage": True})
        dit(st == 400 and code(c) == "cle_sans_nuage",
            "« nuage: true » dans la demande n'ouvre pas le nuage de la cle",
            f"HTTP {st} {code(c)}")
        st, c, _r = await lancer(K_N8N, {"demande": "un chat", "nuage": True})
        dit(st == 202 and ((S.TACHES.get((c or {}).get("id")) or {}).get("api") or {}).get("nuage") is False,
            "et la marque d'une demande locale « nuage: true » reste sans nuage",
            f"HTTP {st}")
        st, c, _r = await lancer(K_AGENT, {"demande": "un chat", "moteur": "nanobanana"})
        dit(st == 202 and ((S.TACHES.get((c or {}).get("id")) or {}).get("api") or {}).get("nuage") is True,
            "temoin : la cle qui a droit au nuage lance le moteur distant", f"HTTP {st}")
        st, c, _r = await lancer(K_AGENT, {"demande": "un chat", "nuage": False})
        dit(st == 202 and ((S.TACHES.get((c or {}).get("id")) or {}).get("api") or {}).get("nuage") is False,
            "« nuage: false » RESTREINT une cle qui a le nuage", f"HTTP {st}")
    finally:
        if garde is None:
            S.CLES.pop("nanobanana", None)
        else:
            S.CLES["nanobanana"] = garde
    vider_file()

    # Le rappel.
    avant = etat_des_registres()
    st, c, _r = await lancer(K_N8N, {"demande": "un chat",
                                     "rappel": "http://routeur.maison/admin"})
    dit(st == 400 and code(c) == "rappel_refuse" and rien_de_plus(avant),
        "un rappel vers un hote non declare rend 400 « rappel_refuse »",
        f"HTTP {st} {code(c)}")
    st, c, _r = await lancer(K_N8N, {"demande": "un chat", "rappel": RAPPEL_OK})
    dit(st == 202 and ((S.TACHES.get((c or {}).get("id")) or {}).get("api") or {}).get("rappel") == RAPPEL_OK,
        "un rappel vers l'hote declare est accepte et garde sur la marque",
        f"HTTP {st}")
    vider_file()

    # La file pleine.
    remise_a_zero()
    k1 = nouvelle_cle("jordan", "une a la fois", en_file=1)["cle"]
    st1, _c, _r = await lancer(k1, {"demande": "un chat"})
    avant = etat_des_registres()
    st2, c2, _r = await lancer(k1, {"demande": "un chien"})
    dit(st1 == 202 and st2 == 429 and code(c2) == "cle_file_pleine" and rien_de_plus(avant),
        "« en_file » atteint : 429 « cle_file_pleine »", f"HTTP {st1} puis {st2} {code(c2)}")
    vider_file()

    # LES VARIANTES COMPTENT DANS LE PLAFOND. Une cle reglee sur deux rendus a
    # la fois lancait quatre taches d'un coup avec « variantes: 4 ». Le temoin :
    # deux variantes, qui tiennent, passent.
    remise_a_zero()
    k2 = nouvelle_cle("jordan", "deux a la fois", en_file=2)["cle"]
    avant = etat_des_registres()
    st4, c4, _r = await lancer(k2, {"demande": "un chat", "variantes": 4})
    rien_avant = rien_de_plus(avant)
    st2v, _c, _r = await lancer(k2, {"demande": "un chat", "variantes": 2})
    dit(st4 == 429 and code(c4) == "cle_file_variantes" and rien_avant and st2v == 202,
        "des variantes qui depasseraient « en_file » sont refusees avant la "
        "file, celles qui tiennent passent",
        f"4 variantes HTTP {st4} {code(c4)}, 2 variantes HTTP {st2v}")
    vider_file()

    # Le plafond du jour, et sa survie a un rechargement.
    remise_a_zero()
    res = nouvelle_cle("jordan", "deux par jour", par_jour=2)
    k2, ident2 = res["cle"], res["fiche"]["id"]
    st_a = [(await lancer(k2, {"demande": f"un chat {i}"}))[0] for i in range(2)]
    st3, c3, _r = await lancer(k2, {"demande": "un troisieme chat"})
    dit(st_a == [202, 202] and st3 == 429 and code(c3) == "cle_plafond_jour",
        "« par_jour » atteint : 429 « cle_plafond_jour »", f"{st_a} puis {st3} {code(c3)}")
    S.CONVERSATIONS.clear()
    S.TACHES.clear()
    S.charger_conversations()
    st4, c4, _r = await lancer(k2, {"demande": "un chat apres redemarrage"})
    dit(S._lances_aujourdhui(ident2) == 2 and st4 == 429 and code(c4) == "cle_plafond_jour",
        "et le plafond SURVIT a un rechargement : il se compte sur les conversations",
        f"relu {S._lances_aujourdhui(ident2)}, HTTP {st4} {code(c4)}")

    # L'idempotence.
    remise_a_zero()
    entetes = {"Idempotency-Key": "lot-du-matin-42"}
    st1, c1, _r = await lancer(K_N8N, {"demande": "un chat"}, entetes)
    st2, c2, rep2 = await lancer(K_N8N, {"demande": "un chat"}, entetes)
    miennes = [x for x, t in S.TACHES.items() if (t.get("api") or {}).get("cle") == F_N8N["id"]]
    dit(st1 == 202 and (c1 or {}).get("id") == (c2 or {}).get("id") and len(miennes) == 1,
        "une Idempotency-Key rejouee rend le meme rendu, et une seule tache",
        f"{len(miennes)} tache(s)")
    dit(rep2 is not None and rep2.headers.get("Idempotent-Replayed") == "true",
        "et la reponse rejouee le dit (Idempotent-Replayed)")
    st3, c3, _r = await lancer(K_AGENT, {"demande": "un chat"}, entetes)
    dit(st3 == 202 and (c3 or {}).get("id") != (c1 or {}).get("id"),
        "la meme Idempotency-Key sur une AUTRE cle est un autre rendu", f"HTTP {st3}")

    # LE REGISTRE SURVIT A UN REDEMARRAGE. Le guide conseille « Retry On Fail »
    # pour rattraper un studio qui redemarre : c'est au reessai d'APRES le
    # redemarrage que la cle doit encore designer le meme rendu. On simule
    # l'arret en vidant la memoire, et le demarrage en relisant le disque.
    try:
        with open(S.FICHIER_IDEMPOTENCE, encoding="utf-8") as f:
            sur_disque = json.load(f)
    except (OSError, ValueError):
        sur_disque = []
    dit([F_N8N["id"], "lot-du-matin-42", (c1 or {}).get("id")] in [l[:3] for l in sur_disque],
        "une Idempotency-Key est ecrite sur le disque des que son rendu part",
        f"{len(sur_disque)} ligne(s)")
    S.IDEMPOTENCE.clear()
    relues = S.charger_idempotence()
    st5, c5, rep5 = await lancer(K_N8N, {"demande": "un chat"}, entetes)
    miennes = [x for x, t in S.TACHES.items() if (t.get("api") or {}).get("cle") == F_N8N["id"]]
    dit(relues >= 2 and (c5 or {}).get("id") == (c1 or {}).get("id") and len(miennes) == 1
        and rep5 is not None and rep5.headers.get("Idempotent-Replayed") == "true",
        "apres un redemarrage, la meme Idempotency-Key rend ENCORE le meme rendu, "
        "sans en lancer un second", f"{relues} relue(s), {len(miennes)} tache(s)")
    # Une ligne perimee, une mal formee, un identifiant de rendu qui n'en est
    # pas un : ecartees a la lecture, sans faire tomber les autres.
    vieille = time.time() - S.IDEMPOTENCE_DUREE - 60
    with open(S.FICHIER_IDEMPOTENCE, "w", encoding="utf-8") as f:
        json.dump(sur_disque + [[F_N8N["id"], "hier", "a" * 32, vieille],
                                [F_N8N["id"], "bancal"],
                                [F_N8N["id"], "pas-un-tid", "../../x", time.time()],
                                [F_N8N["id"], "", "b" * 32, time.time()],
                                [F_N8N["id"], "drapeau", "c" * 32, True]], f)
    relues2 = S.charger_idempotence()
    cles_relues = {k for _c, k in S.IDEMPOTENCE}
    dit(relues2 == relues and not cles_relues & {"hier", "bancal", "pas-un-tid", "", "drapeau"},
        "a la lecture, les cles perimees, mal formees, vides ou au rendu illisible "
        "sont ecartees, et les bonnes restent", f"{relues2} relue(s)")
    with open(S.FICHIER_IDEMPOTENCE, "w", encoding="utf-8") as f:
        f.write("{ceci n'est pas du json")
    dit(S.charger_idempotence() == 0 and not S.IDEMPOTENCE,
        "un registre illisible repart vide au lieu d'empecher le demarrage")
    # LA BORNE : un programme qui pose une cle neuve a chaque appel ne fait
    # pas grossir le fichier sans fin ; les plus anciennes partent.
    S.IDEMPOTENCE.clear()
    base = time.time()
    for i in range(S.IDEMPOTENCE_MAX + 3):
        S.IDEMPOTENCE[(F_N8N["id"], f"k{i}")] = ("d" * 32, base + i)
    S._borner_idempotence()
    dit(len(S.IDEMPOTENCE) == S.IDEMPOTENCE_MAX
        and (F_N8N["id"], "k0") not in S.IDEMPOTENCE
        and (F_N8N["id"], f"k{S.IDEMPOTENCE_MAX + 2}") in S.IDEMPOTENCE,
        "le registre est borne, et ce sont les plus anciennes cles qui partent",
        f"{len(S.IDEMPOTENCE)} sur {S.IDEMPOTENCE_MAX}")
    S.IDEMPOTENCE.clear()
    # DEUX ENVOIS SIMULTANES, une seule cle d'idempotence : un seul rendu. Le
    # registre se lit avant le depot et s'ecrit apres, sans attente entre les
    # deux — la file n'a pas de plafond, son put() ne rend pas la main. Un
    # await glisse un jour dans ce chemin ouvrirait la course : ce cas la voit.
    remise_a_zero()
    jumeaux = {"Idempotency-Key": "deux-a-la-fois"}
    (sa, ca, _ra), (sb, cb, _rb) = await asyncio.gather(
        lancer(K_N8N, {"demande": "un chat"}, jumeaux),
        lancer(K_N8N, {"demande": "un chat"}, jumeaux))
    miennes = [x for x, t in S.TACHES.items() if (t.get("api") or {}).get("cle") == F_N8N["id"]]
    dit((ca or {}).get("id") == (cb or {}).get("id") and len(miennes) == 1,
        "deux envois simultanes de la meme Idempotency-Key font un seul rendu",
        f"{len(miennes)} tache(s), HTTP {sa}/{sb}")
    # UN REJEU DONT LE RENDU N'EXISTE PLUS lance un rendu neuf. Sinon chaque
    # essai rendait 404 pendant vingt-quatre heures : le workflow n'aurait
    # jamais eu son image.
    S.IDEMPOTENCE[(F_N8N["id"], "rendu-efface")] = ("e" * 32, time.time())
    sv, cv, repv = await lancer(K_N8N, {"demande": "un chat"}, {"Idempotency-Key": "rendu-efface"})
    dit(sv == 202 and (cv or {}).get("id") not in (None, "e" * 32)
        and (repv is None or repv.headers.get("Idempotent-Replayed") != "true")
        and S.IDEMPOTENCE.get((F_N8N["id"], "rendu-efface"), ("",))[0] == (cv or {}).get("id"),
        "une Idempotency-Key dont le rendu a disparu lance un rendu neuf, et "
        "designe desormais celui-la", f"HTTP {sv}")
    vider_file()
    S.IDEMPOTENCE.clear()
    # Et le demarrage le relit : une lecture que le lancement du studio
    # n'appelle pas serait verte ici et absente en service. Le bloc
    # « __main__ » ne s'importe pas : on le lit dans le texte.
    with open(S.__file__, encoding="utf-8") as f:
        principal_ = f.read().split('if __name__ == "__main__":', 1)[-1]
    dit("    charger_idempotence()" in principal_.split("web.run_app", 1)[0],
        "le studio relit son registre d'idempotence a son demarrage")
    vider_file()

    # La conversation : la sienne, pas celle d'une autre cle.
    autre = conv_de_programme(F_AGENT)
    sienne = conv_de_programme(F_N8N)
    avant = etat_des_registres()
    st, c, _r = await lancer(K_N8N, {"demande": "la meme en bleu", "conversation": autre["id"]})
    dit(st == 404 and code(c) == "conversation_inconnue" and rien_de_plus(avant),
        "la conversation d'une autre cle (meme compte) rend 404", f"HTTP {st} {code(c)}")
    n_conv = len(S.CONVERSATIONS)
    st, c, _r = await lancer(K_N8N, {"demande": "la meme en bleu", "conversation": sienne["id"]})
    dit(st == 202 and (S.TACHES.get((c or {}).get("id")) or {}).get("conversation") == sienne["id"]
        and len(S.CONVERSATIONS) == n_conv,
        "la sienne est reutilisee, sans conversation de plus", f"HTTP {st}")
    vider_file()

    # L'image en base64. La file de la cle repart a vide : sinon « en_file »
    # refuserait avant meme de lire l'image, et ces cas ne mesureraient rien.
    remise_a_zero()
    autre = conv_de_programme(F_AGENT)
    octets =b"\x89PNG\r\n\x1a\n" + b"image-du-banc" * 8
    st, c, _r = await lancer(K_N8N, {"demande": "agrandis-la",
                                     "image_base64": base64.b64encode(octets).decode()})
    t = S.TACHES.get((c or {}).get("id")) or {}
    nom = t.get("image") or ""
    dit(st == 202 and nom and S.ENTREES.get(nom) == PID_J
        and os.path.exists(os.path.join(S.DOSSIER_ENTREE, nom)),
        "image_base64 valide : posee dans ENTREES au nom du compte, portee par la tache",
        f"HTTP {st} {nom}")
    st, c, _r = await lancer(K_N8N, {"demande": "agrandis-la", "image_base64":
                                     "data:image/png;base64," + base64.b64encode(octets).decode()})
    dit(st == 202, "une URL de donnees « data:image/png;base64,… » est acceptee",
        f"HTTP {st}")
    avant = etat_des_registres()
    st, c, _r = await lancer(K_N8N, {"demande": "agrandis-la", "image_base64": "@@pas du base64@@"})
    dit(st == 400 and code(c) == "image_illisible" and rien_de_plus(avant),
        "un base64 invalide rend 400 « image_illisible »", f"HTTP {st} {code(c)}")
    vider_file()
    # « Tout est valide : maintenant seulement, on ecrit. » — lancer_pour_programme.
    # Un refus par etape : avant l'image (la conversation), pendant la
    # validation commune (le moteur), et apres elle (garde_fou). L'image est
    # deposee AVANT valider_demande, qui exige de la trouver au registre :
    # chaque refus posterieur doit donc la reprendre.
    image_b64 = base64.b64encode(octets).decode()
    for corps, attendu, quoi in (
            ({"demande": "agrandis-la", "conversation": autre["id"]},
             "conversation_inconnue", "une conversation etrangere"),
            ({"demande": "agrandis-la", "moteur": "pas-un-moteur"}, None,
             "un moteur inconnu"),
            ({"demande": REFUS_MINEUR}, "refus_mineurs", "garde_fou")):
        entrees_avant = set(S.ENTREES)
        disque_avant = set(os.listdir(S.DOSSIER_ENTREE))
        st, c, _r = await lancer(K_N8N, dict(corps, image_base64=image_b64))
        dit(st in (400, 404, 422) and (attendu is None or code(c) == attendu),
            f"temoin : la demande a image refusee par {quoi} rend {st}", f"{code(c)}")
        dit(set(S.ENTREES) == entrees_avant
            and set(os.listdir(S.DOSSIER_ENTREE)) == disque_avant,
            f"une demande REFUSEE ({quoi}) n'ecrit pas son image, ni sur le "
            f"disque ni dans ENTREES",
            f"{len(set(S.ENTREES) - entrees_avant)} image(s) restee(s)")

    # L'attente bornee.
    remise_a_zero()
    for valeur in (-1, S.ATTENDRE_MAX + 1, "dix", True):
        avant = etat_des_registres()
        st, c, _r = await lancer(K_N8N, {"demande": "un chat", "attendre": valeur})
        dit(st == 400 and code(c) == "attendre_bornes" and rien_de_plus(avant),
            f"« attendre » = {valeur!r} rend 400 « attendre_bornes »", f"HTTP {st} {code(c)}")
    st, _c, _r = await lancer(K_N8N, {"demande": "un chat", "attendre": 0})
    dit(st == 202, "temoin : « attendre » = 0 est accepte", f"HTTP {st}")
    vider_file()


# ══════════════════════════════════════════════════════════════════════
#  6. Lire un rendu
# ══════════════════════════════════════════════════════════════════════
async def lire_rendu(cle, tid):
    return await appel(Req(f"/api/v1/rendus/{tid}", cle=cle, match={"tid": tid}),
                       S.api_v1_rendu)


async def s_lire():
    remise_a_zero()
    tid, _conv = poser_rendu(F_N8N, "en cours")
    S.ATTENTE.append(tid)
    st, c, _r = await lire_rendu(K_N8N, tid)
    dit(st == 200 and (c or {}).get("etat") == "en_file" and isinstance((c or {}).get("position"), int),
        "en file : « en_file », avec sa position", f"{(c or {}).get('etat')} {(c or {}).get('position')}")
    tid, _conv = poser_rendu(F_N8N, "en cours")
    st, c, _r = await lire_rendu(K_N8N, tid)
    dit((c or {}).get("etat") == "en_cours", "sortie de la file : « en_cours »",
        str((c or {}).get("etat")))
    tid, _conv = poser_rendu(F_N8N, "en cours")
    S.ARMEES[tid] = {"quand": time.time()}
    st, c, _r = await lire_rendu(K_N8N, tid)
    dit((c or {}).get("etat") == "attente_machine",
        "armee pour une machine en pause : « attente_machine »", str((c or {}).get("etat")))
    tid, _conv = poser_rendu(F_N8N, "question")
    st, c, _r = await lire_rendu(K_N8N, tid)
    dit((c or {}).get("etat") == "question" and (c or {}).get("questions") == ["De quelle couleur ?"],
        "une question : « question », avec ses questions", repr((c or {}).get("questions")))
    tid_fini, _conv = poser_rendu(F_N8N, "fini")
    st, c, _r = await lire_rendu(K_N8N, tid_fini)
    f = ((c or {}).get("fichiers") or [{}])[0]
    dit((c or {}).get("etat") == "fini" and str(f.get("url", "")).startswith("http://studio.maison:8199/api/v1/rendus/")
        and "/api/v1/lien/" in str(f.get("lien") or ""),
        "fini : ses fichiers, avec une url ET un lien signe", str(f.get("url"))[:70])
    tid, _conv = poser_rendu(F_N8N, "erreur")
    S.TACHES[tid].update(S.marque_panne("panne.interrompue"))
    st, c, _r = await lire_rendu(K_N8N, tid)
    err = (c or {}).get("erreur") or {}
    dit((c or {}).get("etat") == "erreur" and err.get("code") == "interrompue" and err.get("message"),
        "erreur : un code tire de la marque de panne, et sa phrase", repr(err)[:80])
    tid, _conv = poser_rendu(F_N8N, "en cours")
    S.ATTENTE.append(tid)
    S.EN_FILE[tid] = {"tid": tid}
    st, c, _r = await appel(Req(f"/api/v1/rendus/{tid}", "DELETE", cle=K_N8N,
                                match={"tid": tid}), S.api_v1_annuler)
    dit(st == 200 and (c or {}).get("etat") == "annule"
        and ((c or {}).get("erreur") or {}).get("code") == "annule" and tid not in S.ATTENTE,
        "annule par DELETE : « annule », retire de la file", f"HTTP {st} {(c or {}).get('etat')}")

    st, c, _r = await appel(Req(f"/api/v1/rendus/{tid_fini}", "DELETE", cle=K_N8N,
                                match={"tid": tid_fini}), S.api_v1_annuler)
    dit(st == 409 and (S.TACHES.get(tid_fini) or {}).get("etat") == "fini",
        "annuler un rendu fini rend 409, et il reste fini", f"HTTP {st}")

    # L'annulation d'un groupe emporte chaque tirage.
    conv = conv_de_programme(F_N8N)
    a1, _c = poser_rendu(F_N8N, "en cours", conv=conv)
    S.TACHES[a1]["variantes"] = conv["tours"][-1]["variantes"] = {"groupe": a1, "rang": 1, "sur": 2}
    a2, _c = poser_rendu(F_N8N, "en cours", conv=conv, variantes={"groupe": a1, "rang": 2, "sur": 2})
    S.ATTENTE.extend([a1, a2])
    st, c, _r = await appel(Req(f"/api/v1/rendus/{a1}", "DELETE", cle=K_N8N,
                                match={"tid": a1}), S.api_v1_annuler)
    dit(st == 200 and all((S.TACHES.get(x) or {}).get("annulee") for x in (a1, a2))
        and not S.ATTENTE.count(a2),
        "annuler un groupe annule aussi ses variantes", f"HTTP {st} {(c or {}).get('etat')}")

    # La reponse a une question : un nouveau rendu, dans la meme conversation.
    tid_q, conv_q = poser_rendu(F_N8N, "question")
    st, c, _r = await appel(Req(f"/api/v1/rendus/{tid_q}/reponse", "POST", cle=K_N8N,
                                match={"tid": tid_q}, corps={"reponse": "en bleu"}),
                            S.api_v1_repondre)
    neuf = S.TACHES.get((c or {}).get("id")) or {}
    dit(st == 202 and neuf.get("conversation") == conv_q["id"]
        and "Précisions : en bleu" in (neuf.get("demande") or ""),
        "repondre a une question lance un rendu neuf, dans sa conversation, avec "
        "« Précisions : »", f"HTTP {st}")
    st, c, _r = await appel(Req(f"/api/v1/rendus/{tid_fini}/reponse", "POST", cle=K_N8N,
                                match={"tid": tid_fini}, corps={"reponse": "en bleu"}),
                            S.api_v1_repondre)
    dit(st == 409 and code(c) == "pas_de_question",
        "repondre a un rendu qui ne pose pas de question rend 409", f"HTTP {st} {code(c)}")
    vider_file()

    # « attendre » rend la main des que le rendu s'acheve, pas au bout du delai.
    tid_w, conv_w = poser_rendu(F_N8N, "en cours")

    async def finir_bientot():
        await asyncio.sleep(0.3)
        S.TACHES[tid_w]["etat"] = "fini"
        conv_w["tours"][-1].update(etat="fini", fichiers=[
            {"filename": "attendu.png", "subfolder": "", "noeud": "local"}])

    debut = time.monotonic()
    fin_ = asyncio.create_task(finir_bientot())
    st, c, _r = await appel(Req(f"/api/v1/rendus/{tid_w}", cle=K_N8N, match={"tid": tid_w},
                                requete={"attendre": "5"}), S.api_v1_rendu)
    await fin_
    duree = time.monotonic() - debut
    dit(st == 200 and (c or {}).get("etat") == "fini" and duree < 3,
        "?attendre=5 rend la main des que le rendu est fini", f"{(c or {}).get('etat')} en {duree:.1f} s")

    # Les groupes de variantes.
    conv = conv_de_programme(F_N8N)
    g1, _c = poser_rendu(F_N8N, "fini", conv=conv)
    S.TACHES[g1]["variantes"] = {"groupe": g1, "rang": 1, "sur": 2}
    conv["tours"][-1]["variantes"] = {"groupe": g1, "rang": 1, "sur": 2}
    g2, _c = poser_rendu(F_N8N, "en cours", conv=conv, variantes={"groupe": g1, "rang": 2, "sur": 2})
    st, c, _r = await lire_rendu(K_N8N, g1)
    dit((c or {}).get("etat") == "en_cours",
        "un groupe dont une variante calcule encore reste « en_cours »", str((c or {}).get("etat")))
    S.TACHES[g2]["etat"] = "erreur"
    conv["tours"][-1]["etat"] = "erreur"
    st, c, _r = await lire_rendu(K_N8N, g1)
    dit((c or {}).get("etat") == "fini" and len((c or {}).get("fichiers") or []) == 1,
        "un groupe dont un tirage a abouti est « fini », meme si l'autre a echoue",
        str((c or {}).get("etat")))
    conv = conv_de_programme(F_N8N)
    h1, _c = poser_rendu(F_N8N, "erreur", conv=conv, variantes={"groupe": "", "rang": 1, "sur": 2})
    S.TACHES[h1]["variantes"] = conv["tours"][-1]["variantes"] = {"groupe": h1, "rang": 1, "sur": 2}
    h2, _c = poser_rendu(F_N8N, "fini", conv=conv, variantes={"groupe": h1, "rang": 2, "sur": 2})
    st, c, _r = await lire_rendu(K_N8N, h1)
    fs = (c or {}).get("fichiers") or []
    dit((c or {}).get("etat") == "fini" and [x.get("variante") for x in fs] == [2],
        "le premier tirage echoue, le second aboutit : le groupe est « fini », "
        "avec le fichier de la variante 2", f"{(c or {}).get('etat')} {[x.get('variante') for x in fs]}")

    # Cent fichiers et plus : le lien signe ne sait pas porter le rang 100
    # (acces._LIEN, deux chiffres). Le commentaire de rendu_public promet
    # qu'un lien qui ne se fait pas ne rend pas le rendu illisible.
    beaucoup = [{"filename": f"image_{i:03d}.png", "subfolder": "", "noeud": "local"}
                for i in range(101)]
    tid_100, _conv = poser_rendu(F_N8N, "fini", fichiers=beaucoup)
    st, c, _r = await lire_rendu(K_N8N, tid_100)
    fs = (c or {}).get("fichiers") or []
    dit(st == 200 and len(fs) == 101 and fs[0].get("lien"),
        "un rendu de 101 fichiers se lit encore (le lien du rang 100 ne se signe "
        "pas, le rendu doit rester lisible)", f"HTTP {st} {(c or {}).get('erreur', '')}"[:110])

    # Apres un redemarrage simule.
    tid_vieux, _conv = poser_rendu(F_N8N, "en cours")
    S.TACHES.clear()
    st, c, _r = await lire_rendu(K_N8N, tid_fini)
    dit(st == 200 and (c or {}).get("etat") == "fini" and (c or {}).get("fichiers"),
        "apres TACHES.clear(), un rendu fini se lit encore depuis son tour", f"HTTP {st}")
    st, c, _r = await lire_rendu(K_N8N, tid_vieux)
    dit(st == 200 and (c or {}).get("etat") == "erreur",
        "un tour « en cours » sans tache se lit « erreur », pas « en_cours » pour toujours",
        f"HTTP {st} {(c or {}).get('etat')}")

    # Le cloisonnement.
    tid, _conv = poser_rendu(F_N8N, "fini")
    st0, _c, _r = await lire_rendu(K_N8N, tid)
    st1, _c, _r = await lire_rendu(K_AUTRUI, tid)
    st2, _c, _r = await lire_rendu(K_AGENT, tid)
    dit(st0 == 200 and st1 == 404, "la cle d'un autre compte rend 404", f"{st0} / {st1}")
    dit(st2 == 404, "une AUTRE cle du meme compte rend 404 elle aussi", f"HTTP {st2}")
    S.TACHES.clear()
    st3, _c, _r = await lire_rendu(K_AGENT, tid)
    dit(st3 == 404, "et toujours 404 quand le rendu se relit depuis son tour", f"HTTP {st3}")
    for faux in ("../../_comptes", tid.upper(), tid[:31], "z" * 32):
        st, _c, _r = await lire_rendu(K_N8N, faux)
        dit(st == 404, f"un identifiant qui n'est pas 32 hex ({faux[:12]}…) rend 404",
            f"HTTP {st}")


# ══════════════════════════════════════════════════════════════════════
#  7. Les fichiers
# ══════════════════════════════════════════════════════════════════════
async def s_fichiers():
    remise_a_zero()
    servis = []
    vrai_servir = S.servir_sortie

    async def faux_servir(req, ident, sous, nom, genre="output"):
        servis.append((ident, sous, nom))
        return web.json_response({"servi": nom})

    S.servir_sortie = faux_servir
    try:
        tid, conv = poser_rendu(F_N8N, "fini")
        nom = conv["tours"][-1]["fichiers"][0]["filename"]

        async def fichier(cle, rang, t=tid):
            return await appel(Req(f"/api/v1/rendus/{t}/fichiers/{rang}", cle=cle,
                                   match={"tid": t, "rang": str(rang)}), S.api_v1_fichier)

        st, _c, _r = await fichier(K_N8N, 0)
        dit(st == 200 and servis == [("local", "", nom)],
            "le fichier au rang 0 est servi par servir_sortie(noeud, sous-dossier, nom)",
            repr(servis))
        for rang in (1, -1, "abc"):
            servis.clear()
            st, _c, _r = await fichier(K_N8N, rang)
            dit(st == 404 and not servis, f"le rang {rang!r} rend 404, rien n'est servi",
                f"HTTP {st}")
        servis.clear()
        st, _c, _r = await fichier(K_AGENT, 0)
        dit(st == 404 and not servis, "une autre cle du compte ne lit pas ce fichier",
            f"HTTP {st}")

        st, c, _r = await lire_rendu(K_N8N, tid)
        lien = (((c or {}).get("fichiers") or [{}])[0].get("lien")) or ""
        jeton = lien.rsplit("/", 1)[-1]

        async def par_lien(j):
            return await appel(Req(f"/api/v1/lien/{j}", match={"jeton": j}), S.api_v1_lien)

        servis.clear()
        st, _c, rep = await par_lien(jeton)
        dit(st == 200 and servis == [("local", "", nom)],
            "le lien signe sert le fichier SANS cle", f"HTTP {st}")
        dit(rep is not None and "no-store" in (rep.headers.get("Cache-Control") or ""),
            "et sa reponse ne se garde dans aucun cache partage")
        servis.clear()
        altere = jeton[:-1] + ("0" if jeton[-1] != "0" else "1")
        st, _c, _r = await par_lien(altere)
        dit(st == 404 and not servis, "un lien altere rend 404", f"HTTP {st}")

        # Un fichier hors de mes_fichiers n'est jamais servi.
        tid2, conv2 = poser_rendu(F_N8N, "fini", fichiers=[])
        S.TACHES[tid2]["fichiers"] = [{"filename": "ailleurs.png", "subfolder": "",
                                       "noeud": "local"}]
        servis.clear()
        st, _c, _r = await fichier(K_N8N, 0, tid2)
        dit(st == 404 and not servis,
            "un fichier qui n'est dans aucun tour du compte n'est jamais servi", f"HTTP {st}")
        tid3, conv3 = poser_rendu(F_N8N, "fini")
        st, c, _r = await lire_rendu(K_N8N, tid3)
        jeton3 = ((((c or {}).get("fichiers") or [{}])[0].get("lien")) or "").rsplit("/", 1)[-1]
        conv3["ferme"] = time.time()
        servis.clear()
        st, _c, _r = await fichier(K_N8N, 0, tid3)
        st_l, _c, _r = await par_lien(jeton3)
        dit(st == 404 and st_l == 404 and not servis,
            "une conversation fermee ne sert plus ses fichiers, ni par cle ni par lien",
            f"HTTP {st} / {st_l}")

        # Le lien meurt avec sa cle.
        res = nouvelle_cle("jordan", "condamnee")
        f_c = fiche_de(res["cle"])
        tid4, _conv4 = poser_rendu(f_c, "fini")
        st, c, _r = await lire_rendu(res["cle"], tid4)
        jeton4 = ((((c or {}).get("fichiers") or [{}])[0].get("lien")) or "").rsplit("/", 1)[-1]
        st_a, _c, _r = await par_lien(jeton4)
        S.ACCES.revoquer(f_c["id"])
        servis.clear()
        st_b, _c, _r = await par_lien(jeton4)
        dit(st_a == 200 and st_b == 404 and not servis,
            "une cle revoquee : son lien rend 404", f"avant {st_a}, apres {st_b}")

        # Et quand la cle s'eteint par le mot de passe, sans etre revoquee ?
        res = nouvelle_cle("lou", "script de lou")
        f_l = fiche_de(res["cle"])
        tid5, _conv5 = poser_rendu(f_l, "fini")
        st, c, _r = await lire_rendu(res["cle"], tid5)
        jeton5 = ((((c or {}).get("fichiers") or [{}])[0].get("lien")) or "").rsplit("/", 1)[-1]
        st_a, _c, _r = await par_lien(jeton5)
        S.COMPTES.changer_mdp("lou", MDP_NEUF)
        st_k, _c, _r = await lire_rendu(res["cle"], tid5)
        servis.clear()
        st_b, _c, _r = await par_lien(jeton5)
        dit(st_a == 200 and st_k == 401,
            "temoin : la cle de lou est bien eteinte par le changement de mot de passe",
            f"lien avant {st_a}, cle apres {st_k}")
        dit(st_b == 404 and not servis,
            "une cle eteinte par le changement de mot de passe : ses liens meurent avec elle",
            f"le lien rend HTTP {st_b} apres le changement")
        S._ECHECS.clear()
    finally:
        S.servir_sortie = vrai_servir


# ══════════════════════════════════════════════════════════════════════
#  8. Le nuage
# ══════════════════════════════════════════════════════════════════════
async def s_nuage():
    remise_a_zero()
    t_prog, _c = poser_rendu(F_N8N, "en cours", nuage=False)
    t_nuage, _c = poser_rendu(F_AGENT, "en cours", nuage=True)
    t_page = uuid.uuid4().hex
    S.TACHES[t_page] = {"etapes": [], "etat": "en cours", "proprietaire": PID_J}
    dit(S.nuage_permis(t_prog) is False, "nuage_permis() est faux pour une tache de cle sans nuage")
    dit(S.nuage_permis(t_nuage) is True, "et vrai pour une tache de cle qui a le nuage")
    dit(S.nuage_permis(t_page) is True and S.nuage_permis(None) is True,
        "et vrai pour une demande de la page")

    choix = next(iter(S.fournisseurs.LLM))
    garde = (S.fournisseur_dispo, S.cle_de, S.nuage_actif)
    S.fournisseur_dispo = lambda modalite: choix
    S.cle_de = lambda fournisseur: "cle-de-banc"
    S.nuage_actif = lambda pid, modalite="llm": True
    try:
        texte = "un phare au coucher du soleil"
        dit(S.llm_distant_possible(texte, PID_J, t_page) == choix,
            "temoin : un fournisseur de texte configure sert une demande de la page",
            repr(S.llm_distant_possible(texte, PID_J, t_page)))
        dit(S.llm_distant_possible(texte, PID_J, t_prog) == "",
            "llm_distant_possible() rend \"\" pour une tache de cle sans nuage, "
            "meme avec un fournisseur configure",
            repr(S.llm_distant_possible(texte, PID_J, t_prog)))
        dit(S.llm_distant_possible(texte, None, t_prog) == "",
            "et sans pid non plus (le chemin de l'analyse)")
    finally:
        S.fournisseur_dispo, S.cle_de, S.nuage_actif = garde

    # La liste des moteurs suit le droit au nuage de la cle.
    garde_cle = S.CLES.get("nanobanana")
    S.CLES["nanobanana"] = {"cle": "cle-de-banc"}
    try:
        _st, c1, _r = await appel(Req("/api/v1/moteurs", cle=K_N8N), S.api_v1_moteurs)
        _st, c2, _r = await appel(Req("/api/v1/moteurs", cle=K_AGENT), S.api_v1_moteurs)
    finally:
        if garde_cle is None:
            S.CLES.pop("nanobanana", None)
        else:
            S.CLES["nanobanana"] = garde_cle
    d1 = [m.get("cle") for m in (c1 or {}).get("moteurs") or [] if m.get("distant")]
    d2 = [m.get("cle") for m in (c2 or {}).get("moteurs") or [] if m.get("distant")]
    dit(not d1 and "nanobanana" in d2 and (c1 or {}).get("moteurs"),
        "/api/v1/moteurs ne montre les moteurs distants qu'a une cle qui a le nuage",
        f"sans nuage {d1}, avec {d2}")

    # reprendre_file() restaure la marque.
    remise_a_zero()
    conv = conv_de_programme(F_N8N)
    tid = uuid.uuid4().hex
    conv["tours"].append({"id": tid, "demande": "un chat", "etat": "en cours", "fichiers": []})
    marque = {"cle": F_N8N["id"], "nuage": False, "rappel": RAPPEL_OK, "base": "", "langue": "fr"}
    with open(S.FICHIER_FILE, "w", encoding="utf-8") as f:
        json.dump([{"tid": tid, "texte": "un chat", "conversation": conv["id"],
                    "proprietaire": PID_J, "image": None, "modele": None,
                    "taille": None, "priorite": "", "noeud": None,
                    "modele_choisi": False, "variantes": 1, "api": marque}], f)
    await S.reprendre_file()
    dit((S.TACHES.get(tid) or {}).get("api") == marque and S.nuage_permis(tid) is False,
        "reprendre_file() restaure la marque « api » depuis _file.json : la "
        "tache reprise reste sans nuage", repr((S.TACHES.get(tid) or {}).get("api"))[:80])
    dit(S.FILE_ATTENTE.qsize() == 1, "temoin : la demande reprise est bien en file")
    vider_file()

    # lancer_variantes() recopie la marque sur chaque tirage, sans le rappel.
    remise_a_zero()
    conv = conv_de_programme(F_N8N)
    tid = uuid.uuid4().hex
    S.TACHES[tid] = {"etapes": [], "etat": "en cours", "conversation": conv["id"],
                     "proprietaire": PID_J, "api": dict(marque)}
    S.EN_FILE[tid] = {"tid": tid, "api": dict(marque)}
    conv["tours"].append({"id": tid, "demande": "un chat", "etat": "en cours", "fichiers": []})
    autres = await S.lancer_variantes(tid, "un chat", conv,
                                      {"intention": "image", "modele": "klein4b"}, 3)
    marques = [(S.TACHES.get(a) or {}).get("api") or {} for a in autres]
    dit(len(autres) == 2 and all(m.get("cle") == F_N8N["id"] and m.get("nuage") is False
                                 for m in marques),
        "lancer_variantes() recopie la marque sur chaque tirage", f"{len(autres)} tirage(s)")
    dit(marques and all(m.get("rappel") is None for m in marques)
        and all((S.EN_FILE.get(a) or {}).get("api") == m for a, m in zip(autres, marques)),
        "sans le rappel (un seul par rendu), et jusque dans la file")
    dit(S._en_cours_de_cle(F_N8N["id"]) == 3,
        "et chaque tirage compte dans les rendus en file de la cle",
        f"{S._en_cours_de_cle(F_N8N['id'])}")
    vider_file()


# ══════════════════════════════════════════════════════════════════════
#  9. Les rappels
# ══════════════════════════════════════════════════════════════════════
async def s_rappels():
    remise_a_zero()
    recus = []
    vrai_livrer = S._rappels.livrer

    async def faux_livrer(session, url, corps, secret, *, evenement, livraison, **_):
        recus.append({"url": url, "corps": corps, "secret": secret,
                      "evenement": evenement, "livraison": livraison})
        return {"livre": True, "essais": 1, "statut": 200, "raison": "livre"}

    res = nouvelle_cle("jordan", "rappel revoque")
    f_rev = fiche_de(res["cle"])
    t_fini, _c = poser_rendu(F_N8N, "fini", rappel=RAPPEL_OK)
    t_cours, _c = poser_rendu(F_N8N, "en cours", rappel=RAPPEL_OK)
    t_rev, _c = poser_rendu(f_rev, "fini", rappel=RAPPEL_OK)
    t_sans, _c = poser_rendu(F_N8N, "fini", rappel=None)
    S.ACCES.revoquer(f_rev["id"])
    # L'autre facon de tuer une cle : le mot de passe change, la fiche reste.
    S.COMPTES.creer("noa", MDP)
    res_e = nouvelle_cle("noa", "rappel eteint")
    t_eteint, _c = poser_rendu(fiche_de(res_e["cle"]), "fini", rappel=RAPPEL_OK)
    S.COMPTES.changer_mdp("noa", MDP_NEUF)
    S._rappels.livrer = faux_livrer
    try:
        veilleur = asyncio.create_task(S.veiller_rappels())
        await asyncio.sleep(2.5)
        veilleur.cancel()
        await asyncio.gather(veilleur, return_exceptions=True)
        await asyncio.sleep(0.1)
    finally:
        S._rappels.livrer = vrai_livrer
    pour_fini = [r for r in recus if t_fini.encode() in r["corps"]]
    dit(len(pour_fini) == 1, "une tache finie qui porte un rappel est livree UNE fois",
        f"{len(pour_fini)} livraison(s) en 2,5 s")
    r = pour_fini[0] if pour_fini else {}
    dit(r.get("evenement") == "rendu.fini" and r.get("url") == RAPPEL_OK,
        "evenement « rendu.fini », vers l'URL exacte declaree", f"{r.get('evenement')} {r.get('url')}")
    try:
        lu = json.loads(r.get("corps") or b"{}")
    except ValueError:
        lu = {}
    dit(lu.get("id") == t_fini and (lu.get("rendu") or {}).get("id") == t_fini
        and (lu.get("rendu") or {}).get("etat") == "fini"
        and (lu.get("rendu") or {}).get("fichiers"),
        "le corps se relit en JSON et porte le meme rendu, avec ses fichiers")
    entete = rappels.signature(r.get("secret") or "x", int(time.time()), r.get("corps") or b"")
    dit(rappels.signature_valide(N8N["secret_rappel"], entete, r.get("corps") or b"x"),
        "signe avec le secret_rappel que la cle a recu a sa creation")
    dit(not any(t_cours.encode() in x["corps"] for x in recus),
        "une tache pas finie n'est pas livree")
    dit(not any(t_rev.encode() in x["corps"] for x in recus)
        and ((S.TACHES[t_rev].get("api") or {}).get("livraison") or {}).get("livre") is False,
        "la cle revoquee entre-temps : pas de livraison, et la raison est notee",
        repr((S.TACHES[t_rev].get("api") or {}).get("livraison")))
    dit(not any(t_sans.encode() in x["corps"] for x in recus)
        and "livraison" not in (S.TACHES[t_sans].get("api") or {}),
        "une tache sans rappel : rien")
    dit(not any(t_eteint.encode() in x["corps"] for x in recus),
        "la cle eteinte par un changement de mot de passe ne signe plus de rappel",
        f"{sum(t_eteint.encode() in x['corps'] for x in recus)} livraison(s) en son nom")
    dit(len([x for x in recus if t_eteint.encode() not in x["corps"]]) == 1,
        "temoin : une seule livraison en tout, et pas zero", f"{len(recus)}")


# ══════════════════════════════════════════════════════════════════════
#  10. MCP
# ══════════════════════════════════════════════════════════════════════
async def mcp(cle, message, version="2025-06-18", methode="POST"):
    entetes = {"MCP-Protocol-Version": version} if version else {}
    return await appel(Req("/mcp", methode, cle=cle, corps=message, entetes=entetes),
                       S.api_mcp)


def rpc(methode, params=None, ident=1):
    m = {"jsonrpc": "2.0", "method": methode, "id": ident}
    if params is not None:
        m["params"] = params
    return m


async def s_mcp():
    remise_a_zero()
    st, _c, rep = await mcp(None, rpc("tools/list"))
    dit(st == 401 and rep is not None and rep.headers.get("WWW-Authenticate"),
        "/mcp sans cle rend 401, avec WWW-Authenticate", f"HTTP {st}")
    st, _c, _r = await appel(Req("/mcp", "POST", corps=rpc("tools/list"),
                                 cookies={"studio_compte": S.COMPTES.jeton("jordan")}),
                             S.api_mcp)
    dit(st == 401, "une session de navigateur n'ouvre pas /mcp", f"HTTP {st}")
    st, _c, rep = await mcp(K_N8N, None, methode="GET")
    dit(st == 405 and rep is not None and rep.headers.get("Allow") == "POST",
        "GET /mcp rend 405 avec Allow: POST", f"HTTP {st}")
    st, c, _r = await mcp(K_N8N, rpc("tools/list"), version="2026-07-28")
    err = (c or {}).get("error") or {}
    dit(st == 400 and err and err.get("code") != -32022,
        "une MCP-Protocol-Version inconnue rend 400, SANS le code -32022",
        f"HTTP {st} code {err.get('code')}")
    st, c, _r = await mcp(K_N8N, ILLISIBLE)
    dit(st == 400 and ((c or {}).get("error") or {}).get("code") == -32700,
        "un corps illisible rend 400 -32700", f"HTTP {st}")
    st, c, _r = await mcp(K_N8N, rpc("initialize", {"protocolVersion": "2025-06-18",
                                                    "capabilities": {},
                                                    "clientInfo": {"name": "banc"}}), version=None)
    res = (c or {}).get("result") or {}
    dit(st == 200 and res.get("protocolVersion") == "2025-06-18"
        and (res.get("serverInfo") or {}).get("name") == "comfystudio",
        "initialize : protocolVersion et serverInfo.name « comfystudio »", repr(res)[:80])
    st, c, rep = await mcp(K_N8N, {"jsonrpc": "2.0", "method": "notifications/initialized"})
    dit(st == 202 and c is None and rep is not None and not rep.text,
        "une notification rend 202 sans corps", f"HTTP {st}")
    st, c, _r = await mcp(K_N8N, rpc("tools/list"))
    noms = {o.get("name") for o in ((c or {}).get("result") or {}).get("tools") or []}
    dit(noms == OUTILS_MCP, "tools/list rend les six outils", repr(sorted(noms)))
    st, c, _r = await mcp(K_N8N, rpc("tools/call", {"name": "lister_moteurs", "arguments": {}}))
    contenu = ((c or {}).get("result") or {}).get("content") or [{}]
    dit(contenu[0].get("type") == "text" and "klein4b" in contenu[0].get("text", ""),
        "tools/call lister_moteurs rend un contenu texte", contenu[0].get("text", "")[:50])
    st, c, _r = await mcp(K_N8N, rpc("tools/call", {"name": "generer_rendu",
                                                    "arguments": {"demande": "un phare",
                                                                  "attendre": 0}}))
    sc = ((c or {}).get("result") or {}).get("structuredContent") or {}
    tid = sc.get("id") or ""
    dit(len(tid) == 32 and ((S.TACHES.get(tid) or {}).get("api") or {}).get("cle") == F_N8N["id"]
        and S.FILE_ATTENTE.qsize() == 1,
        "generer_rendu (attendre 0) rend un identifiant, et une tache marquee « api » en file",
        f"{tid[:8]} file={S.FILE_ATTENTE.qsize()}")
    vider_file()
    st, c, _r = await mcp(K_N8N, rpc("tools/call", {"name": "generer_rendu",
                                                    "arguments": {"demande": REFUS_MINEUR,
                                                                  "attendre": 0}}))
    res = (c or {}).get("result") or {}
    dit(st == 200 and res.get("isError") is True and S.FILE_ATTENTE.qsize() == 0,
        "generer_rendu refuse par garde_fou : isError, rien en file", f"HTTP {st}")

    vrai_octets = S._octets_de_sortie

    async def faux_octets(ident, sous, nom):
        return b"\x89PNG-octets-du-banc"

    S._octets_de_sortie = faux_octets
    try:
        tid_f, _conv = poser_rendu(F_N8N, "fini")
        st, c, _r = await mcp(K_N8N, rpc("tools/call", {"name": "etat_rendu",
                                                        "arguments": {"id": tid_f, "attendre": 0}}))
    finally:
        S._octets_de_sortie = vrai_octets
    res = (c or {}).get("result") or {}
    sc = res.get("structuredContent") or {}
    types = [x.get("type") for x in res.get("content") or []]
    dit(sc.get("etat") == "fini" and len(sc.get("fichiers") or []) == 1 and res.get("isError") is False,
        "etat_rendu sur un rendu fini : structuredContent avec ses fichiers", f"{sc.get('etat')}")
    dit("image" in types and "resource_link" in types,
        "et l'image inseree, plus son lien", repr(types))
    # La reponse blanche : /api/v1/rendus/{id}/reponse la refuse (reponse_vide),
    # l'outil MCP doit en faire autant — sinon il lance un rendu « Precisions : »
    # vide, du temps de carte pour une reponse que personne n'a donnee.
    tid_q, _conv = poser_rendu(F_N8N, "question")
    n_taches = len(S.TACHES)
    st, c, _r = await mcp(K_N8N, rpc("tools/call", {"name": "repondre_question",
                                                    "arguments": {"id": tid_q, "reponse": "   ",
                                                                  "attendre": 0}}))
    res = (c or {}).get("result") or {}
    dit(res.get("isError") is True and len(S.TACHES) == n_taches,
        "repondre_question avec une reponse blanche est refuse, comme par la route REST",
        f"isError={res.get('isError')}, {len(S.TACHES) - n_taches} rendu(s) lance(s)")
    vider_file()
    st, c, _r = await mcp(K_N8N, rpc("tools/call", {"name": "repondre_question",
                                                    "arguments": {"id": tid_q, "reponse": "en bleu",
                                                                  "attendre": 0}}))
    sc = ((c or {}).get("result") or {}).get("structuredContent") or {}
    dit("Précisions : en bleu" in ((S.TACHES.get(sc.get("id")) or {}).get("demande") or ""),
        "temoin : repondre_question avec une vraie reponse lance le rendu precise")
    vider_file()
    st, c, _r = await mcp(K_AUTRUI, rpc("tools/call", {"name": "etat_rendu",
                                                       "arguments": {"id": tid_f, "attendre": 0}}))
    res = (c or {}).get("result") or {}
    dit(st == 200 and res.get("isError") is True and "error" not in (c or {}),
        "etat_rendu sur le rendu d'une autre cle : isError, sans exception", f"HTTP {st}")


# ══════════════════════════════════════════════════════════════════════
#  11. La retention
# ══════════════════════════════════════════════════════════════════════
async def s_retention():
    remise_a_zero()
    jour = 24 * 3600
    vieille = conv_de_programme(F_N8N)
    vieille["modifie"] = time.time() - 31 * jour
    recente = conv_de_programme(F_N8N)
    recente["modifie"] = time.time() - 29 * jour
    page = S._vide(proprietaire=PID_J)
    page["modifie"] = time.time() - 400 * jour
    S.CONVERSATIONS[page["id"]] = page
    fermees = S.fermer_vieux_programmes()
    dit(bool(vieille.get("ferme")), "une conversation de programme de 31 jours est fermee")
    dit(not recente.get("ferme"), "une de 29 jours ne l'est pas")
    dit(not page.get("ferme"), "une conversation de la PAGE ne l'est jamais, meme de 400 jours")
    dit(fermees == 1, "temoin : exactement une fermeture", f"{fermees}")


# ══════════════════════════════════════════════════════════════════════
#  12. Les gardes, relues dans le texte
# ══════════════════════════════════════════════════════════════════════
def fonction(arbre, nom):
    return next((n for n in ast.walk(arbre)
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == nom), None)


def appels(noeud, nom):
    return sorted(n.lineno for n in ast.walk(noeud)
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == nom)


async def s_texte():
    with open(os.path.join(ICI, "serveur.py"), encoding="utf-8") as f:
        arbre = ast.parse(f.read())
    ex = fonction(arbre, "executer")
    # DANS LE MEME BLOC que « plan = await traduire(...) », et apres lui. « Une
    # garde_fou quelque part plus bas » ne suffit pas : executer() en appelle
    # deux autres sur les zones de retouche, cinq cents lignes plus loin, et
    # elles laisseraient ce cas vert garde retiree — mesure par la mutation.
    suivies = []
    for n in ast.walk(ex) if ex else []:
        for champ in ("body", "orelse", "finalbody"):
            instr = getattr(n, champ, None)
            if not isinstance(instr, list):
                continue
            for i, s in enumerate(instr):
                if (isinstance(s, ast.Assign) and isinstance(s.value, ast.Await)
                        and isinstance(s.value.value, ast.Call)
                        and isinstance(s.value.value.func, ast.Name)
                        and s.value.value.func.id == "traduire"):
                    suivies.append(any(
                        isinstance(x, ast.Expr) and isinstance(x.value, ast.Call)
                        and isinstance(x.value.func, ast.Name)
                        and x.value.func.id == "garde_fou" for x in instr[i + 1:]))
    dit(bool(suivies) and all(suivies),
        "executer() appelle garde_fou APRES traduire(), dans le meme bloc : le "
        "prompt traduit est garde lui aussi", f"{len(suivies)} traduction(s), {suivies}")
    # La garde du nuage dans executer() : un moteur distant demande par une cle
    # sans nuage doit y replier sur le local. Ce banc ne fait pas tourner
    # executer() ; il exige au moins que la garde y soit.
    dit(bool(appels(ex, "nuage_permis")) if ex else False,
        "executer() consulte nuage_permis() avant de partir chez un fournisseur",
        f"lignes {appels(ex, 'nuage_permis') if ex else []}")
    lv = fonction(arbre, "lancer_variantes")
    poses = set()
    for n in ast.walk(lv) if lv else []:
        if isinstance(n, ast.Assign):
            for cible in n.targets:
                if (isinstance(cible, ast.Subscript) and isinstance(cible.slice, ast.Constant)
                        and cible.slice.value == "api" and isinstance(cible.value, ast.Subscript)
                        and isinstance(cible.value.value, ast.Name)):
                    poses.add(cible.value.value.id)
    dit({"TACHES", "EN_FILE"} <= poses,
        "lancer_variantes() recopie la marque « api » sur la tache ET dans la file",
        repr(sorted(poses)))


# ══════════════════════════════════════════════════════════════════════
#  13. Ce que la revue de securite a trouve, le 4 novembre 2026
# ══════════════════════════════════════════════════════════════════════
# Une relecture adverse du code assemble, apres ce banc : onze constats, dont
# deux graves. Chacun a ici son cas et son temoin — un correctif que rien ne
# mesure revient a la premiere retouche.
PNG_FACTICE = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64).decode()


async def s_revue():
    # ── 1. Une reponse aiohttp FAUSSE ne laisse rien passer ──────────────
    # Avant aiohttp 3.12, une web.Response vaut False (MutableMapping vide) :
    # « if refus: » laissait passer un mot de passe faux. On REMET ce
    # comportement le temps du cas, et on exige que rien ne passe.
    remise_a_zero()
    a_soi = "__bool__" in S.web.Response.__dict__
    ancien = S.web.Response.__dict__.get("__bool__")
    S.web.Response.__bool__ = lambda self: False
    try:
        faux_vraiment = bool(S.web.json_response({})) is False
        biscuit = {"studio_compte": S.COMPTES.jeton("lou")}
        avant = len(S.ACCES.liste("lou"))
        st1, _c, _r = await appel(Req("/api/compte/acces", "POST", cookies=biscuit,
                                      corps={"mdp": "pas-le-bon", "nom": "intrus"}),
                                  S.api_creer_acces)
        apres = len(S.ACCES.liste("lou"))
        S._ECHECS.clear()
        st2, c2, _r = await lancer(K_N8N, {"demande": ""})
        st3, c3, _r = await appel(Req("/api/generer", "POST", compte="jordan",
                                      pid=PID_J, corps={"texte": ""}),
                                  S.api_generer, middleware=False)
    finally:
        if a_soi:
            S.web.Response.__bool__ = ancien
        else:
            del S.web.Response.__bool__
    dit(faux_vraiment and st1 == 403 and apres == avant,
        "avec une reponse aiohttp fausse (avant 3.12), un mot de passe faux ne "
        "cree AUCUNE cle", f"reponse fausse : {faux_vraiment}, HTTP {st1}, "
                           f"{apres - avant} cle(s) de plus")
    dit(st2 == 400 and code(c2) == "demande_vide" and st3 == 400,
        "et un refus de validation reste un refus, pour un programme comme "
        "pour la page", f"programme HTTP {st2} {code(c2)}, page HTTP {st3}")
    vider_file()

    # ── 2. Le type d'image vient d'une liste, jamais du client ───────────
    remise_a_zero()
    dehors = os.path.dirname(os.path.abspath(S.DOSSIER_ENTREE))
    cible = os.path.join(dehors, "cible_du_banc.png")
    with open(cible, "wb") as f:
        f.write(b"original")
    avant_ = set(os.listdir(S.DOSSIER_ENTREE)) if os.path.isdir(S.DOSSIER_ENTREE) else set()
    pieges = ["png\\..\\..\\cible_du_banc.png", "png/../../cible_du_banc.png",
              "../png", "gif", "PNG "]
    # (Un type VIDE n'est pas un piege : il vaut « png », le defaut documente.)
    statuts = []
    for type_ in pieges:
        st, c, _r = await lancer(K_N8N, {"demande": "x", "image_base64": PNG_FACTICE,
                                         "image_type": type_})
        statuts.append((st, code(c)))
    st_d, c_d, _r = await lancer(K_N8N, {
        "demande": "x",
        "image_base64": "data:image/png\\..\\..\\cible_du_banc.png;base64," + PNG_FACTICE})
    statuts.append((st_d, code(c_d)))
    # La cible peut avoir DISPARU : c'est exactement ce que faisait la faute
    # sous Windows (ecrite, puis effacee par le refus). La lire sans garde
    # ferait tomber la section au lieu de rougir sur cette ligne.
    intacte = os.path.exists(cible) and open(cible, "rb").read() == b"original"
    apres_ = set(os.listdir(S.DOSSIER_ENTREE)) if os.path.isdir(S.DOSSIER_ENTREE) else set()
    # « PNG  » (casse et espace) est un vrai type : il passe, et c'est le temoin
    # que le refus vient de la liste et non d'un refus de tout.
    refuses = [s for s, (st, cd) in zip(pieges + ["data:"], statuts)
               if s != "PNG " and not (st == 400 and cd == "champ_illisible")]
    st_ok = statuts[pieges.index("PNG ")][0]
    dit(not refuses and intacte and st_ok == 202
        and len(apres_ - avant_) == 1,
        "un type d'image qui n'est pas dans la liste est refuse — chemin, "
        "traversee, en-tete data: compris — et rien n'est ecrit hors du dossier",
        f"passes a tort : {refuses}, cible intacte : {intacte}, temoin HTTP {st_ok}")
    if os.path.exists(cible):
        os.remove(cible)
    vider_file()

    # ── 3. L'issue d'un rappel ne revient pas a la cle ───────────────────
    remise_a_zero()
    tid, conv = poser_rendu(F_N8N, rappel="http://n8n.maison:5678/hook")
    tour = next(x for x in conv["tours"] if x["id"] == tid)

    async def injoignable(*_a, **_k):
        return {"livre": False, "essais": 4, "statut": None, "raison": "injoignable"}
    vrai = S._rappels.livrer
    S._rappels.livrer = injoignable
    try:
        await S._livrer_rappel(tid, S.TACHES[tid]["api"], conv, S.TACHES[tid], tour)
    finally:
        S._rappels.livrer = vrai
    st, c, _r = await appel(Req(f"/api/v1/rendus/{tid}", cle=K_N8N, match={"tid": tid}),
                            S.api_v1_rendu)
    fil = " | ".join((c or {}).get("journal") or [])
    dit(st == 200 and "rappel" not in fil and "injoignable" not in fil
        and S.TACHES[tid]["api"]["livraison"].get("raison") == "injoignable",
        "l'issue d'un rappel ne revient pas dans le fil que la cle lit (sinon "
        "c'est une sonde de ports)", f"fil : {fil[:80]}")

    # ── 4. Les questions se purgent, et les conversations sont bornees ───
    remise_a_zero()
    for _ in range(5):
        poser_rendu(F_N8N, etat="question")
    S.purger_taches(garder=0)
    dit(not any(x.get("etat") == "question" for x in S.TACHES.values()),
        "les taches « question » se purgent comme les autres taches finies",
        f"{sum(1 for x in S.TACHES.values() if x.get('etat') == 'question')} restantes")
    ancien_plafond = S.CONVERSATIONS_PAR_CLE
    S.CONVERSATIONS_PAR_CLE = 3
    try:
        k = nouvelle_cle("lou", "bornee", en_file=10)
        for i in range(4):
            await lancer(k["cle"], {"demande": f"un chat numero {i}"})
        siennes = [x for x in S.CONVERSATIONS.values()
                   if (x.get("api") or {}).get("cle") == k["fiche"]["id"]]
        ouvertes = [x for x in siennes if not x.get("ferme")]
    finally:
        S.CONVERSATIONS_PAR_CLE = ancien_plafond
    dit(len(siennes) == 4 and len(ouvertes) == 3,
        "au-dela du plafond, la plus ancienne conversation de la cle est fermee",
        f"{len(siennes)} conversations, {len(ouvertes)} ouvertes")
    vider_file()

    # ── 5. Des attentes bornees, et qui meurent avec la cle ──────────────
    remise_a_zero()
    tid, _conv = poser_rendu(F_N8N, etat="en cours")
    S.ATTENTES[F_N8N["id"]] = S.ATTENTES_PAR_CLE
    t0 = time.monotonic()
    await S.attendre_rendu(tid, PID_J, F_N8N, 30)
    plein = time.monotonic() - t0
    S.ATTENTES.pop(F_N8N["id"], None)
    t0 = time.monotonic()
    await S.attendre_rendu(tid, PID_J, F_N8N, 1)
    temoin = time.monotonic() - t0
    dit(plein < 0.5 and temoin >= 0.9 and not S.ATTENTES,
        "au plafond d'attentes, une attente de plus rend la main aussitot — et "
        "sous le plafond, elle attend vraiment",
        f"au plafond {plein:.2f} s, temoin {temoin:.2f} s")
    k = nouvelle_cle("lou", "revoquee en route")
    f_ = fiche_de(k["cle"])
    tid, _conv = poser_rendu(f_, etat="en cours")
    attente = asyncio.create_task(S.attendre_rendu(tid, pid_de("lou"), f_, 30))
    await asyncio.sleep(0.3)
    S.ACCES.revoquer(f_["id"])
    t0 = time.monotonic()
    try:
        await asyncio.wait_for(attente, timeout=3)
        finie = True
    except asyncio.TimeoutError:
        finie = False
        attente.cancel()
    dit(finie and time.monotonic() - t0 < 2,
        "une cle revoquee pendant une attente de trente secondes la voit finir "
        "dans la seconde", f"finie : {finie}")

    # ── 6. Une machine retiree n'est pas un 500 ──────────────────────────
    remise_a_zero()
    tid, _conv = poser_rendu(F_N8N, fichiers=[{"filename": "partie.png", "subfolder": "",
                                               "type": "output", "noeud": "machine_partie"}])
    st, c, _r = await appel(Req(f"/api/v1/rendus/{tid}/fichiers/0", cle=K_N8N,
                                match={"tid": tid, "rang": "0"}), S.api_v1_fichier)
    dit(st == 404 and code(c) == "rendu_inconnu",
        "le fichier d'une machine retiree du parc rend 404, pas 500",
        f"HTTP {st} {code(c)}")

    # ── 7. Le rang d'un fichier ne change pas ────────────────────────────
    remise_a_zero()
    conv = conv_de_programme(F_N8N)
    t1, _ = poser_rendu(F_N8N, etat="en cours", conv=conv, fichiers=[])
    groupe = {"groupe": t1, "sur": 2}
    S.TACHES[t1]["variantes"] = dict(groupe, rang=1)
    next(x for x in conv["tours"] if x["id"] == t1)["variantes"] = dict(groupe, rang=1)
    t2, _ = poser_rendu(F_N8N, etat="fini", conv=conv, variantes=dict(groupe, rang=2))
    st, c, _r = await appel(Req(f"/api/v1/rendus/{t1}", cle=K_N8N, match={"tid": t1}),
                            S.api_v1_rendu)
    fs = (c or {}).get("fichiers") or []
    servis = []

    async def note(_req, ident, sous, nom, genre="output"):
        servis.append(nom)
        return S.web.json_response({"servi": nom})
    vraie, S.servir_sortie = S.servir_sortie, note
    try:
        await appel(Req(f"/api/v1/rendus/{t1}/fichiers/25", cle=K_N8N,
                        match={"tid": t1, "rang": "25"}), S.api_v1_fichier)
        st0, _c, _r = await appel(Req(f"/api/v1/rendus/{t1}/fichiers/0", cle=K_N8N,
                                      match={"tid": t1, "rang": "0"}), S.api_v1_fichier)
    finally:
        S.servir_sortie = vraie
    dit(len(fs) == 1 and fs[0]["rang"] == 25 and fs[0]["variante"] == 2
        and servis == [fs[0]["nom"]] and st0 == 404,
        "la variante 2 finie avant la 1 prend le rang 25, qu'elle gardera — le "
        "rang 0 reste a la variante 1, encore vide",
        f"rangs {[x['rang'] for x in fs]}, servi {servis}, rang 0 HTTP {st0}")

    # UN TIRAGE DE PLUS DE VINGT-CINQ FICHIERS NE DEBORDE PAS sur le suivant :
    # le vingt-sixieme de la variante 1 prendrait sinon le rang 25 — celui du
    # premier fichier de la variante 2 —, et deux fichiers auraient le meme
    # lien. Au-dela de vingt-cinq, un fichier est montre sans rang.
    remise_a_zero()
    conv = conv_de_programme(F_N8N)
    beaucoup = [{"filename": f"v1_{i:02d}.png", "subfolder": "", "type": "output",
                 "noeud": "local"} for i in range(30)]
    t1, _ = poser_rendu(F_N8N, etat="fini", conv=conv, fichiers=beaucoup)
    groupe = {"groupe": t1, "sur": 2}
    S.TACHES[t1]["variantes"] = dict(groupe, rang=1)
    next(x for x in conv["tours"] if x["id"] == t1)["variantes"] = dict(groupe, rang=1)
    poser_rendu(F_N8N, etat="fini", conv=conv, variantes=dict(groupe, rang=2))
    st, c, _r = await appel(Req(f"/api/v1/rendus/{t1}", cle=K_N8N, match={"tid": t1}),
                            S.api_v1_rendu)
    fs = (c or {}).get("fichiers") or []
    rangs = [x["rang"] for x in fs if x["rang"] is not None]
    v2 = [x for x in fs if x["variante"] == 2]
    dit(len(fs) == 31 and len(rangs) == len(set(rangs)) == 26
        and v2 and v2[0]["rang"] == 25,
        "un tirage de plus de vingt-cinq fichiers ne deborde pas sur le rang du "
        "suivant : aucun rang n'est donne deux fois",
        f"{len(fs)} fichiers, {len(rangs)} rangs, {len(set(rangs))} distincts")

    # ── Le refus du garde-fou : traduit, et qui sait aider ───────────────
    # « sexe » dit aussi le genre : seul avec un bebe, il fait refuser une fete
    # de devoilement. Le garde-fou ne le retire pas — « montre le sexe du bebe »
    # porte les memes mots —, mais il dit comment demander l'autre. Le temoin :
    # un refus ordinaire ne porte PAS ce conseil.
    remise_a_zero()
    st_g, c_g, _r = await lancer(K_N8N, {"demande": "une fete pour reveler le sexe du bebe"})
    st_o, c_o, _r = await lancer(K_N8N, {"demande": "a child in a sexual pose"})
    dit(st_g == 422 and code(c_g) == "refus_mineurs"
        and "fille ou garçon" in (c_g or {}).get("erreur", "")
        and st_o == 422 and "fille ou garçon" not in (c_o or {}).get("erreur", ""),
        "un refus du au seul mot « sexe » dit d'ecrire « fille ou garcon » — un "
        "refus ordinaire, non", f"genre HTTP {st_g}, ordinaire HTTP {st_o}")
    try:
        S.garde_fou("a child in a sexual pose")
        marque = None
    except RuntimeError as e:
        marque = getattr(e, "marque", None)
    dit((marque or {}).get("cle") == "panne.refus_mineurs"
        and "minors" in S.traductions.rendre(marque, "en"),
        "le refus du garde-fou porte sa marque : il se traduit, au lieu de "
        "partir en francais dans toutes les langues",
        str(marque))

    # ── 10. Le plafond du jour compte les variantes ──────────────────────
    remise_a_zero()
    k = nouvelle_cle("lou", "trois par jour", par_jour=3, en_file=10)["cle"]
    st4, c4, _r = await lancer(k, {"demande": "un chat", "variantes": 4})
    st3, _c, _r = await lancer(k, {"demande": "un chat", "variantes": 3})
    st1, c1, _r = await lancer(k, {"demande": "un chien"})
    dit(st4 == 429 and code(c4) == "cle_plafond_jour" and st3 == 202
        and st1 == 429 and code(c1) == "cle_plafond_jour",
        "le plafond du jour compte des rendus : quatre variantes ne passent pas "
        "sous trois, trois passent, et le suivant est refuse",
        f"4 HTTP {st4}, 3 HTTP {st3}, puis HTTP {st1}")
    vider_file()

    # ── 11. Un compte de programmes seulement a sa conversation de page ──
    remise_a_zero()
    k = nouvelle_cle("dominique", "seulement des programmes")
    poser_rendu(fiche_de(k["cle"]))
    st, c, _r = await appel(Req("/api/conversations", compte="dominique",
                                pid=pid_de("dominique")), S.api_conversations,
                            middleware=False)
    liste = (c or {}).get("conversations") or []
    dit(st == 200 and (c or {}).get("courante") and len(liste) == 1
        and not any(est["id"] == (c or {}).get("courante") and False for est in liste)
        and not S.CONVERSATIONS[(c or {}).get("courante")].get("api"),
        "un compte qui n'a servi qu'a des programmes recoit quand meme sa "
        "conversation de page", f"courante {(c or {}).get('courante')}, {len(liste)} listee(s)")


# ══════════════════════════════════════════════════════════════════════
#  14. Retrouver ses rendus, et essayer son rappel
# ══════════════════════════════════════════════════════════════════════
async def s_liste():
    # ── la liste : les rendus de CETTE cle, et d'elle seule ─────────────
    remise_a_zero()
    a, _ = poser_rendu(F_N8N)
    time.sleep(0.01)
    b, _ = poser_rendu(F_N8N, etat="en cours")
    time.sleep(0.01)
    conv_g = conv_de_programme(F_N8N)
    g1, _ = poser_rendu(F_N8N, conv=conv_g)
    groupe = {"groupe": g1, "sur": 2}
    S.TACHES[g1]["variantes"] = dict(groupe, rang=1)
    next(x for x in conv_g["tours"] if x["id"] == g1)["variantes"] = dict(groupe, rang=1)
    g2, _ = poser_rendu(F_N8N, conv=conv_g, variantes=dict(groupe, rang=2))
    autre, _ = poser_rendu(F_AGENT)          # meme compte, AUTRE cle
    etranger, _ = poser_rendu(F_AUTRUI)      # autre compte
    st, c, _r = await appel(Req("/api/v1/rendus", cle=K_N8N), S.api_v1_lister)
    ids = [x["id"] for x in (c or {}).get("rendus") or []]
    dit(st == 200 and set(ids) == {a, b, g1} and len(ids) == 3,
        "la liste rend les rendus de cette cle, et d'elle seule — ni ceux d'une "
        "autre cle du meme compte, ni ceux d'un autre compte",
        f"{len(ids)} rendus ; autre cle {autre in ids}, autre compte {etranger in ids}")
    dit(g2 not in ids and ids and ids[0] == g1,
        "les variantes viennent avec leur groupe, et le plus recent vient en tete",
        f"tete {ids[:1]}, variante 2 listee : {g2 in ids}")
    st2, c2, _r = await appel(Req("/api/v1/rendus", cle=K_N8N, requete={"limite": "2"}),
                              S.api_v1_lister)
    st0, c0, _r = await appel(Req("/api/v1/rendus", cle=K_N8N, requete={"limite": "0"}),
                              S.api_v1_lister)
    stx, cx, _r = await appel(Req("/api/v1/rendus", cle=K_N8N,
                                  requete={"limite": str(S.LISTE_MAX + 1)}),
                              S.api_v1_lister)
    dit(st2 == 200 and len((c2 or {}).get("rendus") or []) == 2
        and st0 == 400 and code(c0) == "champ_illisible"
        and stx == 400 and code(cx) == "champ_illisible",
        "« limite » borne la liste, et se refuse hors de 1 a LISTE_MAX",
        f"2 -> {len((c2 or {}).get('rendus') or [])}, 0 -> HTTP {st0}, "
        f"{S.LISTE_MAX + 1} -> HTTP {stx}")

    # ── l'essai de rappel : signe, vers un hote declare, borne ──────────
    remise_a_zero()
    S.DERNIER_ESSAI.clear()
    recus = []

    async def faux(session, url, corps, secret, **k):
        recus.append({"url": url, "corps": corps, "secret": secret, **k})
        return {"livre": True, "essais": 1, "statut": 200, "raison": "livre"}
    vrai = S._rappels.livrer
    S._rappels.livrer = faux
    try:
        hors, c_h, _r = await appel(Req("/api/v1/rappels/essai", "POST", cle=K_N8N,
                                        corps={"rappel": "http://ailleurs.maison/x"}),
                                    S.api_v1_essai_rappel)
        st, c, _r = await appel(Req("/api/v1/rappels/essai", "POST", cle=K_N8N,
                                    corps={"rappel": f"http://{HOTE_N8N}/webhook/essai"}),
                                S.api_v1_essai_rappel)
        st_2, c_2, _r = await appel(Req("/api/v1/rappels/essai", "POST", cle=K_N8N,
                                        corps={"rappel": f"http://{HOTE_N8N}/webhook/essai"}),
                                    S.api_v1_essai_rappel)
    finally:
        S._rappels.livrer = vrai
    r0 = recus[0] if recus else {}
    dit(hors == 400 and code(c_h) == "rappel_refuse" and len(recus) == 1,
        "un essai vers un hote non declare est refuse, et rien ne part",
        f"HTTP {hors} {code(c_h)}, {len(recus)} envoi(s)")
    dit(st == 200 and (c or {}).get("livre") is True
        and r0.get("evenement") == "rappel.essai"
        and r0.get("secret") == S.ACCES.secret_rappel(F_N8N["id"])
        and r0.get("delais") == (0,),
        "l'essai part vers l'hote declare, signe du secret de la cle, en un seul "
        "essai, et dit ce qu'il en est",
        f"HTTP {st}, evenement {r0.get('evenement')}, delais {r0.get('delais')}")
    dit(st_2 == 429 and code(c_2) == "trop_d_essais" and len(recus) == 1,
        "un second essai dans les dix secondes est freine",
        f"HTTP {st_2} {code(c_2)}")


# ══════════════════════════════════════════════════════════════════════
#  15. Les humains d'abord dans la file
# ══════════════════════════════════════════════════════════════════════
async def s_humains_dabord():
    """La file etait strictement dans l'ordre d'arrivee : un lot n8n mettait
    l'humain devant l'ecran derriere ses rendus. Une horloge FACTICE pour le
    vieillissement : attendre dix minutes ne mesurerait que la patience."""
    remise_a_zero()
    heure = [0.0]
    for tid, api in (("p1", True), ("p2", True), ("h1", False), ("h2", False),
                     ("sans_tache", None)):
        if api is not None:
            S.TACHES[tid] = {"api": {"cle": F_N8N["id"]}} if api else {}
            S.TACHES[tid]["debut"] = time.time()
    q = S.FileHumainsDabord(horloge=lambda: heure[0])
    for tid in ("p1", "p2", "h1", "h2", "sans_tache"):
        S.ATTENTE.append(tid)
        await q.put({"tid": tid})
    ordre = [(await q.get())["tid"] for _ in range(5)]
    dit(ordre == ["h1", "h2", "sans_tache", "p1", "p2"],
        "une demande humaine passe devant celles des programmes, et une demande "
        "sans tache connue compte pour humaine", repr(ordre))
    dit(S.ATTENTE[:3] == ["h1", "h2", "sans_tache"] and S.ATTENTE[3:] == ["p1", "p2"],
        "et la position affichee le dit : ATTENTE range l'humain devant",
        repr(S.ATTENTE))

    # Le vieillissement : un programme qui a attendu dix minutes reprend son
    # tour. Le temoin : a 599 s, l'humain passe encore devant.
    for limite, attendu in ((S.VIEILLISSEMENT_PROGRAMME - 1, "humain"),
                            (S.VIEILLISSEMENT_PROGRAMME, "programme")):
        q = S.FileHumainsDabord(horloge=lambda: heure[0])
        heure[0] = 0.0
        S.TACHES["prog"] = {"api": {"cle": F_N8N["id"]}}
        S.TACHES["humain"] = {}
        await q.put({"tid": "prog"})
        heure[0] = float(limite)
        await q.put({"tid": "humain"})
        premier = (await q.get())["tid"]
        dit(premier == ("prog" if attendu == "programme" else "humain"),
            f"un programme qui a attendu {limite} s : "
            f"{'il reprend son tour' if attendu == 'programme' else 'l humain passe encore devant'}",
            f"premier servi : {premier}")

    # Le contrat d'asyncio.Queue que les travailleurs supposent : task_done et
    # join tiennent, qsize et empty suivent.
    q = S.FileHumainsDabord()
    S.TACHES["a"], S.TACHES["b"] = {"api": {"cle": "x"}}, {}
    await q.put({"tid": "a"})
    await q.put({"tid": "b"})
    taille = q.qsize()
    await q.get(); q.task_done()
    await q.get(); q.task_done()
    try:
        await asyncio.wait_for(q.join(), timeout=1)
        rejoint = True
    except asyncio.TimeoutError:
        rejoint = False
    dit(taille == 2 and q.empty() and rejoint,
        "le contrat d'asyncio.Queue tient : qsize, empty, task_done et join",
        f"qsize {taille}, vide {q.empty()}, join {rejoint}")
    S.ATTENTE.clear()
    # LE STUDIO S'EN SERT : une file parfaite que demarrer_file() ne cree pas
    # serait du code mort, vert ici et absent en service.
    import inspect
    source_ = inspect.getsource(S.demarrer_file)
    dit("FILE_ATTENTE = FileHumainsDabord()" in source_
        and "asyncio.Queue()" not in source_,
        "le studio demarre bien sa file avec les humains d'abord")


# ══════════════════════════════════════════════════════════════════════
#  16. Un rappel en cours survit a un redemarrage
# ══════════════════════════════════════════════════════════════════════
def registre_sur_disque():
    try:
        with open(S.FICHIER_RAPPELS, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


async def s_rappels_persistants():
    """Une livraison dure jusqu'a deux minutes et demie. Un studio redemarre
    pendant ce temps la perdait, et le noeud Wait de n8n attendait pour rien."""
    remise_a_zero()
    S.RAPPELS_EN_COURS.clear()
    S.sauver_rappels()
    tid, conv = poser_rendu(F_N8N, rappel=f"http://{HOTE_N8N}/webhook/w1")
    jamais = asyncio.Event()
    recus = []

    async def bloque(*_a, **k):
        recus.append(k.get("livraison"))
        await jamais.wait()          # la livraison est en plein essai

    async def note(*_a, **k):
        recus.append(k.get("livraison"))
        return {"livre": True, "essais": 1, "statut": 200, "raison": "livre"}

    vrai = S._rappels.livrer
    S._rappels.livrer = bloque
    veilleur = asyncio.create_task(S.veiller_rappels())
    try:
        await asyncio.sleep(1.6)
        avant_arret = registre_sur_disque()
        # L'ARRET DU STUDIO : le veilleur et la livraison sont annules.
        veilleur.cancel()
        for tache_ in list(S.LIVRAISONS):
            tache_.cancel()
        await asyncio.gather(veilleur, *list(S.LIVRAISONS), return_exceptions=True)
        apres_arret = registre_sur_disque()
        id_livraison = (apres_arret.get(tid) or {}).get("livraison")
        dit(tid in avant_arret and tid in apres_arret and id_livraison
            and recus == [id_livraison],
            "une livraison en cours est sur le disque, et un arret du studio ne "
            "l'efface pas", f"inscrite {tid in avant_arret}, apres l'arret "
                            f"{tid in apres_arret}")

        # LE REDEMARRAGE : plus de tache en memoire, le registre relu.
        S.TACHES.clear()
        S.RAPPELS_EN_COURS.clear()
        recus.clear()
        S._rappels.livrer = note
        repris = S.reprendre_rappels()
        await asyncio.gather(*list(S.LIVRAISONS), return_exceptions=True)
        dit(repris == 1 and recus == [id_livraison] and tid not in registre_sur_disque(),
            "au demarrage, elle est reprise avec le MEME identifiant de livraison, "
            "puis quitte le registre", f"{repris} reprise(s), identifiant "
                                      f"{'identique' if recus == [id_livraison] else recus}")

        # Le temoin : une livraison qui aboutit ne laisse rien derriere elle.
        remise_a_zero()
        recus.clear()
        tid2, _ = poser_rendu(F_N8N, rappel=f"http://{HOTE_N8N}/webhook/w2")
        veilleur = asyncio.create_task(S.veiller_rappels())
        await asyncio.sleep(1.6)
        await asyncio.gather(*list(S.LIVRAISONS), return_exceptions=True)
        veilleur.cancel()
        await asyncio.gather(veilleur, return_exceptions=True)
        dit(len(recus) == 1 and tid2 not in registre_sur_disque() and not S.RAPPELS_EN_COURS,
            "une livraison qui aboutit quitte le registre", f"{len(recus)} envoi(s)")
        # Et le demarrage s'en sert : une reprise que demarrer_file() n'appelle
        # pas serait verte ici et absente en service.
        import inspect
        dit("reprendre_rappels()" in inspect.getsource(S.demarrer_file),
            "le studio reprend ses rappels a son demarrage")
    finally:
        S._rappels.livrer = vrai
        jamais.set()


async def principal():
    S.FILE_ATTENTE = asyncio.Queue()
    for titre, corps in (
            ("1. l'identite par cle", s_identite),
            ("2. la cle ne vaut jamais administration", s_administration),
            ("3. exiger_compte et la garde des routes de programme", s_exiger),
            ("4. la gestion des cles par leur proprietaire", s_gestion),
            ("5. lancer un rendu", s_lancer),
            ("6. lire un rendu", s_lire),
            ("7. les fichiers", s_fichiers),
            ("8. le nuage", s_nuage),
            ("9. les rappels", s_rappels),
            ("10. MCP", s_mcp),
            ("11. la retention", s_retention),
            ("12. les gardes, relues dans le texte", s_texte),
            ("13. ce que la revue de securite a trouve", s_revue),
            ("14. retrouver ses rendus, et essayer son rappel", s_liste),
            ("15. les humains d'abord dans la file", s_humains_dabord),
            ("16. un rappel en cours survit a un redemarrage", s_rappels_persistants)):
        print(f"\n  ── {titre} ──")
        try:
            await corps()
        except Exception as e:
            dit(False, f"la section « {titre} » s'est arretee en route",
                f"{type(e).__name__}: {e}")


try:
    asyncio.run(principal())
finally:
    shutil.rmtree(DOSSIER, ignore_errors=True)

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
for x in rate:
    print("    NON :", x)
sys.exit(1 if rate else 0)
