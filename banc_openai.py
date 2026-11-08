#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""La porte compatible OpenAI (/openai/v1/), eprouvee par de VRAIES requetes HTTP.

Open WebUI, LibreChat, le noeud OpenAI de n8n et les SDK openai parlent a
« une API d'images OpenAI » des qu'on leur donne une base et une cle. Ce banc
leur ressemble : il poste ce qu'ils postent, et lit ce qu'ils lisent —
« error.message », « data[i].b64_json » ou « data[i].url » —, a travers le
VRAI routeur et la VRAIE chaine d'intergiciels de S.app(), sur un serveur
aiohttp de test lance sur 127.0.0.1, port au hasard.

CE QU'IL GARDE :

  1. Les refus AU FORMAT OPENAI, avec leur statut : 401 sans cle (et
     WWW-Authenticate), 401 d'une cle fausse traduit par format_openai, 403
     d'une cle sans la famille de la route, 429 sur les plafonds avec
     Retry-After (et X-Should-Retry: false quand reessayer ne sert a rien),
     400 sur un champ faux avec son « param », le 404 du routeur, le 500
     d'une exception sans rejeu.
  2. La reponse : {created, data: [{b64_json | url, revised_prompt}]}, le
     base64 qui redonne les octets, le lien signe ABSOLU et valide, le
     defaut de response_format selon le modele.
  3. La traduction des champs : n -> variantes (borne VARIANTES_MAX), size ->
     la taille de TAILLES la plus proche, model inconnu ignore, model du
     studio impose, quality -> priorite.
  4. Les gardes partagees : la marque de la tache restreinte a la famille de
     la route, le garde-fou avant la file, l'idempotence, l'attente bornee
     (504 quand le rendu tarde, sans rejeu), la question du studio rendue en
     400 lisible.
  5. Les edits en multipart, l'image sous « image » ou « image[] », son type
     lu dans l'en-tete quand le nom n'a pas d'extension.
  6. GET /openai/v1/models : les moteurs d'image de la cle, « comfystudio »
     en tete, rien qui ne fasse pas d'image.

CE QU'IL NE VOIT PAS :

  - Un vrai rendu : un faux travailleur lit la file et pose les taches finies
    a la main ; executer() ne tourne pas. Que operation_refusee() arrete une
    video apres l'analyse est l'affaire de banc_pilotage.py (section 17) —
    ici, seulement que la marque porte la bonne restriction.
  - Les octets d'un vrai ComfyUI : _octets_de_sortie est remplace. Le lien
    signe n'est pas suivi (il irait chercher le fichier sur 127.0.0.1:8188).
  - Un vrai client OpenAI : le SDK n'est pas une dependance du depot. Sa
    facon de lire l'erreur — body.get("error", body) — est imitee.

    Lancer : uv run --with aiohttp python banc_openai.py
"""
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
DOSSIER = tempfile.mkdtemp(prefix="banc_openai_")
os.environ["STUDIO_DONNEES"] = DOSSIER
os.environ["STUDIO_AUTH"] = "obligatoire"
# Le dossier d'entree de ComfyUI, et le sien seulement : l'image des edits y
# est deposee, et purger_entrees() y fait le menage.
os.environ["COMFY_DIR"] = os.path.join(DOSSIER, "comfy")
os.environ["COMFY_ENTREE"] = os.path.join(DOSSIER, "entrees")
sys.path.insert(0, ICI)
import serveur as S  # noqa: E402
import acces  # noqa: E402
import comptes  # noqa: E402
import aiohttp  # noqa: E402
from aiohttp.test_utils import TestServer  # noqa: E402

ok, rate = [], []


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


MDP = "mot-de-passe-du-banc"
REFUS_MINEUR = "a child in a sexual pose"     # un des REFUS de banc_adulte.py
OCTETS = b"\x89PNG-octets-du-banc-openai"
GEN = "/openai/v1/images/generations"
EDITS = "/openai/v1/images/edits"
MODELES = "/openai/v1/models"

# ══════════════════════════════════════════════════════════════════════
#  Le decor : un compte, des cles, un faux travailleur
# ══════════════════════════════════════════════════════════════════════
S.COMPTES = comptes.Comptes(os.path.join(DOSSIER, "_comptes.json"), "secret-de-banc")
S.ACCES = acces.Acces(os.path.join(DOSSIER, "_acces.json"))
S.ACCES.charger()
S.SECRET_LIENS = "secret-des-liens-du-banc-openai"
S.COMPTES.creer("jordan", MDP, admin=False)
# Les modeles du catalogue ne sont sur aucune machine du banc : sans ceci,
# aucun moteur n'est « present » et la liste des modeles serait vide.
S.manquants_partout = lambda cle: []


def nouvelle_cle(nom, **reglages):
    return S.ACCES.creer("jordan", nom, S.COMPTES.generation("jordan"), **reglages)["cle"]


TOUT = nouvelle_cle("open webui")                                  # toutes familles
IMAGE = nouvelle_cle("images seules", operations=["image"])
VIDEO = nouvelle_cle("videos seules", operations=["video"])
UNE = nouvelle_cle("une a la fois", en_file=1)
JOUR = nouvelle_cle("une par jour", par_jour=1)


def fiche_de(cle):
    return S.ACCES.reconnaitre(cle, S._generation_du_compte)


# Ce que le faux travailleur fait du prochain rendu : « fini », « question »,
# « video » (l'analyse a lu une video, la marque l'arrete), « lent » (jamais
# fini), « mp4 » (fini, mais sans image).
COMPORTEMENT = {"mode": "fini"}
VUS = []                     # chaque entree de file lue, telle quelle


def fichier(tid, ext=".png"):
    return {"filename": f"rendu_{tid[:8]}{ext}", "subfolder": "",
            "type": "output", "noeud": "local"}


def finir(tid, conv, fichiers, plan, groupe=None):
    t = S.TACHES[tid]
    t.update(etat="fini", plan=plan, fichiers=list(fichiers))
    if groupe:
        t["variantes"] = dict(groupe)
    for x in conv["tours"]:
        if x["id"] == tid:
            x.update(etat="fini", fichiers=list(fichiers), prompt=plan["prompt"],
                     type="image", modele=plan["modele"], variantes=groupe)
    if tid in S.ATTENTE:
        S.ATTENTE.remove(tid)


async def travailleur():
    """LE FAUX TRAVAILLEUR NE MEURT PAS. Une tache effacee par remise_a_zero()
    pendant son petit sommeil levait KeyError, le travailleur s'arretait, et
    chaque rendu suivant attendait ses 540 s : le banc pendait au lieu de
    rougir (releve en jouant la mutation des attentes, 5 novembre 2026)."""
    while True:
        item = await S.FILE_ATTENTE.get()
        VUS.append(item)
        mode = COMPORTEMENT["mode"]
        await asyncio.sleep(0.05)
        if item["tid"] not in S.TACHES:
            continue
        try:
            traiter(item, mode)
        except Exception as e:
            print(f"  (faux travailleur : {type(e).__name__}: {e})")


def traiter(item, mode):
    tid, conv = item["tid"], item["conv"]
    plan = {"intention": "image", "modele": item.get("modele") or "klein4b",
            "prompt": "prompt revu : " + (item.get("texte") or "")}
    t = S.TACHES[tid]
    if mode == "lent":
        return
    if mode == "question":
        t.update(etat="question", questions=["De quelle couleur ?"], plan=plan)
        for x in conv["tours"]:
            if x["id"] == tid:
                x.update(etat="question", questions=["De quelle couleur ?"])
        return
    if mode == "video":
        t["etat"] = "erreur"
        t[S.MARQUE_PANNE] = S.panne_de("panne.cle_operation_interdite",
                                       operation="video", permises="image")
        for x in conv["tours"]:
            if x["id"] == tid:
                x["etat"] = "erreur"
        return
    if mode == "plafond":
        t["etat"] = "erreur"
        t[S.MARQUE_PANNE] = S.panne_de("panne.cle_plafond_famille", famille="image",
                                       plafond=1)
        for x in conv["tours"]:
            if x["id"] == tid:
                x["etat"] = "erreur"
        return
    if mode == "mp4":
        finir(tid, conv, [fichier(tid, ".mp4")], plan)
        return
    combien = int(item.get("variantes") or 1)
    groupe = {"groupe": tid, "sur": combien} if combien > 1 else None
    for rang in range(2, combien + 1):
        autre = uuid.uuid4().hex
        S.TACHES[autre] = {"etapes": [], "etat": "en cours", "debut": time.time(),
                           "demande": item.get("texte"), "conversation": conv["id"],
                           "proprietaire": t["proprietaire"],
                           "api": dict(t.get("api") or {}),
                           "variantes": dict(groupe, rang=rang)}
        S.enregistrer_tour(conv, autre, item.get("texte"), {}, None, None, [], "en cours")
        finir(autre, conv, [fichier(autre)], plan, dict(groupe, rang=rang))
    finir(tid, conv, [fichier(tid)], plan, dict(groupe, rang=1) if groupe else None)


PLAFONDS = []


async def faux_octets(ident, sous, nom, plafond=S.IMAGE_MCP_MAX):
    PLAFONDS.append(plafond)
    return OCTETS + nom.encode("ascii")


S._octets_de_sortie = faux_octets


def remise_a_zero():
    for registre in (S.TACHES, S.CONVERSATIONS, S.EN_FILE, S.ARMEES,
                     S.IDEMPOTENCE, S.COURANTE, S.ENTREES, S.EN_VOL, S.AVANCES,
                     S.ECHECS_CLES, S.REESSAIS_OPENAI):
        registre.clear()
    S.ATTENTE.clear()
    VUS.clear()
    COMPORTEMENT["mode"] = "fini"


def finir_les_lents():
    """Les rendus « lents » restes en file comptent dans en_file : on les clot."""
    for t in S.TACHES.values():
        if t.get("etat") not in ("fini", "erreur", "question"):
            t["etat"] = "erreur"


def erreur(corps):
    """Ce que le SDK openai lit : body.get("error", body)."""
    if not isinstance(corps, dict):
        return {}
    e = corps.get("error", corps)
    return e if isinstance(e, dict) else {}


def forme_openai(corps):
    e = erreur(corps)
    return (isinstance(corps, dict) and set(corps) == {"error"}
            and set(e) == {"message", "type", "param", "code"}
            and isinstance(e.get("message"), str) and e["message"]
            and isinstance(e.get("type"), str))


class Client:
    def __init__(self, serveur):
        self.serveur = serveur
        # TRENTE SECONDES PAR REQUETE : un rendu du banc dure 50 ms. Un faux
        # travailleur mort ou une attente qui ne finit pas doit faire rougir
        # la section, pas pendre le banc jusqu'aux 540 s de la route.
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))

    async def appel(self, methode, chemin, cle=None, json_=None, data=None, entetes=None):
        h = dict(entetes or {})
        if cle:
            h["Authorization"] = f"Bearer {cle}"
        async with self.session.request(methode, self.serveur.make_url(chemin),
                                        json=json_, data=data, headers=h) as r:
            brut_ = await r.read()
            try:
                corps = json.loads(brut_) if brut_ else None
            except ValueError:
                corps = None
            return r.status, corps, r.headers

    async def fermer(self):
        await self.session.close()


# ══════════════════════════════════════════════════════════════════════
#  1. Les refus, au format OpenAI
# ══════════════════════════════════════════════════════════════════════
async def s_refus(c):
    remise_a_zero()
    st, corps, h = await c.appel("POST", GEN, json_={"prompt": "un phare"})
    dit(st == 401 and forme_openai(corps) and erreur(corps).get("code") == "cle_requise",
        "sans cle : 401 au format OpenAI, code « cle_requise »", f"HTTP {st} {corps}")
    dit(bool(h.get("WWW-Authenticate")), "et le 401 garde WWW-Authenticate")
    dit(h.get("X-Content-Type-Options") == "nosniff",
        "et les en-tetes surs de toute reponse (format_openai est apres en_tetes_surs)")
    fausse = TOUT[:-1] + ("A" if TOUT[-1] != "A" else "B")
    st, corps, _h = await c.appel("POST", GEN, cle=fausse, json_={"prompt": "un phare"})
    dit(st == 401 and forme_openai(corps) and erreur(corps).get("code") == "cle_refusee",
        "une cle fausse : le refus du middleware, traduit en 401 OpenAI", f"HTTP {st} {corps}")
    S.ECHECS_CLES.clear()
    st, corps, _h = await c.appel("POST", GEN, cle=VIDEO, json_={"prompt": "un phare"})
    dit(st == 403 and forme_openai(corps)
        and erreur(corps).get("code") == "cle_operation_interdite"
        and erreur(corps).get("type") == "permission_error" and not VUS,
        "une cle sans « image » est refusee en 403, rien en file", f"HTTP {st} {corps}")
    st, corps, _h = await c.appel("GET", MODELES)
    dit(st == 401 and forme_openai(corps), "GET /models sans cle : 401 OpenAI", f"HTTP {st}")
    st, corps, _h = await c.appel("POST", GEN, cle=TOUT, data=b"{pas du json",
                                  entetes={"Content-Type": "application/json"})
    dit(st == 400 and forme_openai(corps) and erreur(corps).get("code") == "corps_illisible",
        "un corps illisible : 400 OpenAI « corps_illisible »", f"HTTP {st} {corps}")
    st, corps, _h = await c.appel("POST", GEN, cle=TOUT, json_={"prompt": "  "})
    dit(st == 400 and erreur(corps).get("param") == "prompt" and not VUS,
        "un prompt vide : 400, param « prompt », rien en file", f"HTTP {st} {corps}")
    st, corps, _h = await c.appel("POST", GEN, cle=TOUT, json_={"prompt": "un phare",
                                                                 "stream": True})
    dit(st == 400 and erreur(corps).get("code") == "flux_refuse"
        and erreur(corps).get("param") == "stream" and not VUS,
        "stream: true est refuse en 400, rien en file", f"HTTP {st} {corps}")
    st, corps, _h = await c.appel("POST", GEN, cle=TOUT, json_={"prompt": "un phare",
                                                                 "response_format": "png"})
    dit(st == 400 and erreur(corps).get("param") == "response_format",
        "un response_format inconnu : 400, param « response_format »", f"HTTP {st} {corps}")
    st, corps, _h = await c.appel("POST", "/openai/v1/chat/completions", cle=TOUT,
                                  json_={"messages": []})
    dit(st == 404 and forme_openai(corps),
        "une route inconnue sous /openai/v1/ : 404 au format OpenAI", f"HTTP {st} {corps}")
    st, corps, _h = await c.appel("POST", GEN, cle=TOUT, json_={"prompt": REFUS_MINEUR})
    dit(st == 422 and forme_openai(corps) and erreur(corps).get("code") == "refus_mineurs"
        and erreur(corps).get("param") == "prompt" and not VUS,
        "le garde-fou refuse AVANT la file : 422 « refus_mineurs », param prompt",
        f"HTTP {st} {corps}")
    st, corps, _h = await c.appel("GET", "/api/v1/moi", cle=TOUT)
    dit(st == 200 and "error" not in (corps or {}),
        "temoin : hors de /openai/v1/, la meme cle parle toujours le format du studio",
        f"HTTP {st}")
    st, corps, _h = await c.appel("POST", "/api/v1/rendus", cle=TOUT, json_={})
    dit(st == 400 and "erreur" in (corps or {}) and "error" not in (corps or {}),
        "et un refus de /api/v1 n'est pas traduit", f"HTTP {st} {corps}")


# ══════════════════════════════════════════════════════════════════════
#  2. Les plafonds de la cle : 429 et quand reessayer
# ══════════════════════════════════════════════════════════════════════
async def s_plafonds(c):
    remise_a_zero()
    attente = S.ATTENDRE_OPENAI
    S.ATTENDRE_OPENAI = 1
    try:
        COMPORTEMENT["mode"] = "lent"
        st, corps, h = await c.appel("POST", GEN, cle=UNE, json_={"prompt": "un phare"})
        dit(st == 504 and erreur(corps).get("code") == "delai_depasse"
            and h.get("X-Should-Retry") == "false" and len(VUS) == 1,
            "un rendu qui tarde : 504 « delai_depasse », X-Should-Retry: false",
            f"HTTP {st} {corps}")
        dit(VUS and VUS[0]["tid"] in (erreur(corps).get("message") or ""),
            "et la phrase donne l'identifiant du rendu, qui continue")
        st, corps, h = await c.appel("POST", GEN, cle=UNE, json_={"prompt": "un autre"})
        dit(st == 429 and forme_openai(corps) and erreur(corps).get("code") == "cle_file_pleine"
            and erreur(corps).get("type") == "rate_limit_error",
            "file pleine (en_file=1) : 429 OpenAI « cle_file_pleine »", f"HTTP {st} {corps}")
        dit(h.get("Retry-After") == str(S.REESSAI_FILE) and "X-Should-Retry" not in h,
            "avec Retry-After, et le SDK peut reessayer (delai court)",
            f"Retry-After={h.get('Retry-After')} X-Should-Retry={h.get('X-Should-Retry')}")
    finally:
        S.ATTENDRE_OPENAI = attente
        finir_les_lents()
    remise_a_zero()
    st, corps, _h = await c.appel("POST", GEN, cle=JOUR, json_={"prompt": "un phare"})
    dit(st == 200, "temoin : le premier rendu du jour passe", f"HTTP {st}")
    st, corps, h = await c.appel("POST", GEN, cle=JOUR, json_={"prompt": "un phare"})
    attendu = S.secondes_avant_minuit()
    dit(st == 429 and erreur(corps).get("code") == "cle_plafond_jour"
        and h.get("Retry-After") and abs(int(h["Retry-After"]) - attendu) <= 5,
        "plafond du jour : 429 « cle_plafond_jour », Retry-After jusqu'a minuit",
        f"HTTP {st} Retry-After={h.get('Retry-After')}")
    dit(attendu <= S.REESSAI_SDK_MAX or h.get("X-Should-Retry") == "false",
        "et X-Should-Retry: false, le SDK ne rejouera pas des heures de plafond",
        f"X-Should-Retry={h.get('X-Should-Retry')}")
    remise_a_zero()
    st, corps, h = await c.appel("POST", GEN, cle=UNE, json_={"prompt": "un phare", "n": 2})
    dit(st == 429 and erreur(corps).get("code") == "cle_file_variantes"
        and "Retry-After" not in h and h.get("X-Should-Retry") == "false" and not VUS,
        "n=2 sur une cle d'un rendu a la fois : 429 sans delai, sans rejeu, rien en file",
        f"HTTP {st} {h.get('X-Should-Retry')}")
    # Les attentes par cle : au-dela, refuser AVANT de lancer.
    ident = fiche_de(TOUT)["id"]
    S.ATTENTES[ident] = S.ATTENTES_PAR_CLE
    try:
        st, corps, h = await c.appel("POST", GEN, cle=TOUT, json_={"prompt": "un phare"})
    finally:
        S.ATTENTES.pop(ident, None)
    dit(st == 429 and erreur(corps).get("code") == "attentes_pleines" and not VUS
        and h.get("Retry-After"),
        "trop d'attentes pour la cle : 429 avant de lancer, rien en file", f"HTTP {st}")


# ══════════════════════════════════════════════════════════════════════
#  3. La reponse : b64_json, url, et ce que les champs deviennent
# ══════════════════════════════════════════════════════════════════════
async def s_reponse(c):
    remise_a_zero()
    PLAFONDS.clear()
    st, corps, _h = await c.appel("POST", GEN, cle=TOUT, json_={
        "prompt": "un phare dans la brume", "model": "gpt-image-1", "size": "1536x1024",
        "quality": "high", "user": "abc", "style": "vivid", "background": "auto"})
    data = (corps or {}).get("data") or [{}]
    dit(st == 200 and isinstance((corps or {}).get("created"), int) and len(data) == 1,
        "un rendu fini : 200, « created » entier, une image", f"HTTP {st} {str(corps)[:120]}")
    b64 = data[0].get("b64_json") or ""
    try:
        lus = base64.b64decode(b64, validate=True)
    except ValueError:
        lus = b""
    dit(lus.startswith(OCTETS) and "url" not in data[0],
        "sans response_format, gpt-image-1 rend du base64 qui redonne les octets",
        f"{lus[:20]!r}")
    dit(data[0].get("revised_prompt") == "prompt revu : un phare dans la brume",
        "revised_prompt est le prompt que le studio a vraiment rendu",
        repr(data[0].get("revised_prompt")))
    dit(PLAFONDS == [S.IMAGE_OPENAI_MAX],
        "le base64 est lu sous le plafond de la route, pas celui de MCP", repr(PLAFONDS))
    item = VUS[-1] if VUS else {}
    dit(item.get("taille") == "1216x832",
        "size 1536x1024 devient la taille la plus proche, 1216x832", repr(item.get("taille")))
    dit(item.get("modele") is None and not item.get("modele_choisi"),
        "model « gpt-image-1 » est ignore : le studio choisit", repr(item.get("modele")))
    dit(item.get("priorite") == "soigne", "quality high devient la priorite « soigne »",
        repr(item.get("priorite")))
    marque = (S.TACHES.get(item.get("tid")) or {}).get("api") or {}
    dit(marque.get("operations") == ["image"] and marque.get("cle") == fiche_de(TOUT)["id"],
        "la marque de la tache est restreinte a « image », sous la cle qui l'a lancee",
        repr(marque.get("operations")))

    remise_a_zero()
    st, corps, _h = await c.appel("POST", GEN, cle=TOUT, json_={
        "prompt": "un phare", "response_format": "url", "size": "auto", "model": "klein4b"})
    data = (corps or {}).get("data") or [{}]
    url = data[0].get("url") or ""
    base = str(c.serveur.make_url("/api/v1/lien/"))
    jeton = url[len(base):] if url.startswith(base) else ""
    dit(st == 200 and url.startswith(base) and "b64_json" not in data[0],
        "response_format url : un lien signe ABSOLU du studio", url[:80])
    dit(bool(jeton) and S._acces.lien_valide(S.SECRET_LIENS, jeton) is not None,
        "et le lien se verifie avec le secret des liens")
    item = VUS[-1] if VUS else {}
    dit(item.get("modele") == "klein4b" and item.get("modele_choisi"),
        "model « klein4b », un moteur du studio, est impose", repr(item.get("modele")))
    dit(item.get("taille") is None, "size auto : le studio choisit la taille",
        repr(item.get("taille")))

    remise_a_zero()
    st, corps, _h = await c.appel("POST", GEN, cle=TOUT, json_={"prompt": "un phare",
                                                                 "model": "dall-e-3"})
    data = (corps or {}).get("data") or [{}]
    dit(st == 200 and data[0].get("url") and "b64_json" not in data[0],
        "dall-e-3 sans response_format : un lien, comme l'original", str(data[0])[:80])
    item = VUS[-1] if VUS else {}
    dit(item.get("modele") is None, "et dall-e-3 n'impose aucun moteur")

    remise_a_zero()
    st, corps, _h = await c.appel("POST", GEN, cle=TOUT, json_={"prompt": "un phare",
                                                                 "model": "wan5b"})
    item = VUS[-1] if VUS else {}
    dit(st == 200 and item.get("modele") is None,
        "un moteur du studio qui ne fait pas d'image (wan5b) est ignore aussi",
        f"HTTP {st} {item.get('modele')!r}")

    remise_a_zero()
    st, corps, _h = await c.appel("POST", GEN, cle=TOUT, json_={"prompt": "un phare", "n": 3})
    data = (corps or {}).get("data") or []
    item = VUS[-1] if VUS else {}
    dit(st == 200 and item.get("variantes") == 3 and len(data) == 3
        and all(d.get("b64_json") for d in data),
        "n=3 : trois variantes en file, trois images rendues", f"HTTP {st} {len(data)}")
    dit(len({d.get("b64_json") for d in data}) == 3, "et trois images distinctes")
    remise_a_zero()
    st, corps, _h = await c.appel("POST", GEN, cle=TOUT, json_={"prompt": "un phare",
                                                                 "n": S.VARIANTES_MAX + 1})
    dit(st == 400 and erreur(corps).get("code") == "variantes_bornes"
        and erreur(corps).get("param") == "n" and not VUS,
        f"n={S.VARIANTES_MAX + 1} : 400 « variantes_bornes », param n, rien en file",
        f"HTTP {st} {corps}")
    for faux in ("grand", "0x512", 1024):
        st, corps, _h = await c.appel("POST", GEN, cle=TOUT, json_={"prompt": "un phare",
                                                                     "size": faux})
        dit(st == 400 and erreur(corps).get("param") == "size" and not VUS,
            f"size {faux!r} : 400, param « size »", f"HTTP {st}")
    for taille, voulue in (("1024x1024", "1024x1024"), ("1024x1536", "832x1216"),
                           ("1024x1792", "768x1344"), ("1792x1024", "1920x1080"),
                           ("512x512", "1024x1024"), ("1080x1350", "1080x1350")):
        dit(S.taille_proche(taille) == voulue, f"taille_proche({taille}) = {voulue}",
            repr(S.taille_proche(taille)))


# ══════════════════════════════════════════════════════════════════════
#  4. Ce que le studio rend d'autre qu'une image
# ══════════════════════════════════════════════════════════════════════
async def s_issues(c):
    remise_a_zero()
    COMPORTEMENT["mode"] = "question"
    st, corps, h = await c.appel("POST", GEN, cle=TOUT, json_={"prompt": "un truc"})
    dit(st == 400 and erreur(corps).get("code") == "question"
        and "De quelle couleur ?" in (erreur(corps).get("message") or ""),
        "le studio pose une question : 400 « question », la question dans le message",
        f"HTTP {st} {corps}")
    marque = ((S.TACHES.get((VUS[-1] if VUS else {}).get("tid")) or {}).get("api") or {})
    dit(marque.get("sans_question") is True,
        "la tache lancee par la route porte « sans_question » : executer() ne "
        "questionnera pas un client qui ne sait pas repondre", repr(marque))
    remise_a_zero()
    COMPORTEMENT["mode"] = "video"
    st, corps, h = await c.appel("POST", GEN, cle=TOUT, json_={"prompt": "une video d'un chat"})
    dit(st == 400 and erreur(corps).get("code") == "cle_operation_interdite",
        "l'analyse lit une video : 400 « cle_operation_interdite », pas une panne",
        f"HTTP {st} {corps}")
    remise_a_zero()
    COMPORTEMENT["mode"] = "plafond"
    st, corps, h = await c.appel("POST", GEN, cle=TOUT, json_={"prompt": "un phare"})
    ra = int(h.get("Retry-After") or 0)
    dit(st == 429 and erreur(corps).get("code") == "cle_plafond_famille"
        and abs(ra - S.secondes_avant_minuit()) <= 2 and h.get("X-Should-Retry") == "false",
        "un plafond atteint apres l'analyse : 429 « cle_plafond_famille », Retry-After "
        "jusqu'a minuit, sans rejeu du SDK", f"HTTP {st} {erreur(corps).get('code')} {ra}")
    remise_a_zero()
    COMPORTEMENT["mode"] = "mp4"
    st, corps, h = await c.appel("POST", GEN, cle=TOUT, json_={"prompt": "un phare"})
    dit(st == 500 and erreur(corps).get("code") == "sans_image"
        and h.get("X-Should-Retry") == "false",
        "un rendu sans image : 500 « sans_image », X-Should-Retry: false", f"HTTP {st}")
    remise_a_zero()
    vraie = S._reponse_openai

    async def leve(*a, **k):
        raise RuntimeError("panne du banc")
    S._reponse_openai = leve
    try:
        st, corps, h = await c.appel("POST", GEN, cle=TOUT, json_={"prompt": "un phare"})
    finally:
        S._reponse_openai = vraie
    dit(st == 500 and forme_openai(corps) and erreur(corps).get("code") == "panne"
        and h.get("X-Should-Retry") == "false"
        and "panne du banc" not in (erreur(corps).get("message") or ""),
        "une exception : 500 OpenAI « panne », sans rejeu, sans la trace", f"HTTP {st} {corps}")
    remise_a_zero()
    entetes = {"Idempotency-Key": "open-webui-1"}
    st1, c1, _h = await c.appel("POST", GEN, cle=TOUT, json_={"prompt": "un phare"},
                                entetes=entetes)
    st2, c2, h2 = await c.appel("POST", GEN, cle=TOUT, json_={"prompt": "un phare"},
                                entetes=entetes)
    dit(st1 == st2 == 200 and len(VUS) == 1 and h2.get("Idempotent-Replayed") == "true"
        and (c1 or {}).get("data") == (c2 or {}).get("data"),
        "meme Idempotency-Key : un seul rendu, la meme reponse rejouee",
        f"{len(VUS)} rendu(s), {h2.get('Idempotent-Replayed')}")

    # LE REESSAI DU SDK, SANS Idempotency-Key : ce que fait openai-python
    # apres le 504 d'un proxy qui coupe a 90 s.
    remise_a_zero()
    st1, c1, _h = await c.appel("POST", GEN, cle=TOUT, json_={"prompt": "un phare"},
                                entetes={"x-stainless-retry-count": "0"})
    st2, c2, h2 = await c.appel("POST", GEN, cle=TOUT, json_={"prompt": "un phare"},
                                entetes={"x-stainless-retry-count": "1"})
    dit(st1 == st2 == 200 and len(VUS) == 1 and h2.get("Idempotent-Replayed") == "true"
        and (c1 or {}).get("data") == (c2 or {}).get("data"),
        "le reessai du SDK (x-stainless-retry-count: 1) rejoint le rendu deja "
        "lance : la carte n'en fait qu'un", f"{len(VUS)} rendu(s)")
    remise_a_zero()
    for _ in range(2):
        await c.appel("POST", GEN, cle=TOUT, json_={"prompt": "un phare"})
    dit(len(VUS) == 2,
        "mais deux demandes identiques qui ne se disent pas reessai restent "
        "deux rendus", f"{len(VUS)} rendu(s)")
    remise_a_zero()
    await c.appel("POST", GEN, cle=TOUT, json_={"prompt": "un phare"},
                  entetes={"x-stainless-retry-count": "0"})
    await c.appel("POST", GEN, cle=TOUT, json_={"prompt": "un phare la nuit"},
                  entetes={"x-stainless-retry-count": "1"})
    dit(len(VUS) == 2,
        "et le reessai d'une AUTRE demande lance son propre rendu",
        f"{len(VUS)} rendu(s)")
    remise_a_zero()
    COMPORTEMENT["mode"] = "video"
    await c.appel("POST", GEN, cle=TOUT, json_={"prompt": "un phare"},
                  entetes={"x-stainless-retry-count": "0"})
    COMPORTEMENT["mode"] = "fini"
    st, _c2, h2 = await c.appel("POST", GEN, cle=TOUT, json_={"prompt": "un phare"},
                                entetes={"x-stainless-retry-count": "1"})
    dit(len(VUS) == 2 and st == 200 and h2.get("Idempotent-Replayed") != "true",
        "le reessai d'un rendu ECHOUE en lance un nouveau, au lieu de rejouer l'erreur",
        f"{len(VUS)} rendu(s), HTTP {st}")


# ══════════════════════════════════════════════════════════════════════
#  5. Les edits, en multipart
# ══════════════════════════════════════════════════════════════════════
def formulaire(image=True, nom_champ="image", nom_fichier=None, type_="image/png", **champs):
    f = aiohttp.FormData()
    for k, v in champs.items():
        f.add_field(k, str(v))
    if image:
        f.add_field(nom_champ, b"\x89PNG\r\n\x1a\n-image-a-retoucher",
                    filename=nom_fichier or uuid.uuid4().hex, content_type=type_)
    else:
        # Un masque SEUL : le corps reste un multipart (sans aucun fichier,
        # aiohttp l'enverrait en urlencoded), et le masque doit etre ecarte,
        # pas pris pour l'image.
        f.add_field("mask", b"\x89PNG-masque", filename="masque.png",
                    content_type="image/png")
    return f


async def s_edits(c):
    remise_a_zero()
    st, corps, _h = await c.appel("POST", EDITS, cle=TOUT, data=formulaire(
        type_="image/jpeg", prompt="le ciel en rose", n=2, size="1536x1024"))
    data = (corps or {}).get("data") or [{}]
    item = VUS[-1] if VUS else {}
    marque = (S.TACHES.get(item.get("tid")) or {}).get("api") or {}
    dit(st == 200 and data[0].get("b64_json") and len(data) == 1,
        "un edit en multipart (fichier sans extension, type par l'en-tete) : 200, une image",
        f"HTTP {st} {str(corps)[:120]}")
    # En JPEG et non en PNG : « png » est aussi le repli d'un type introuvable,
    # et un en-tete ignore passerait inapercu sur une image PNG.
    dit(item.get("image") in S.ENTREES and item["image"].endswith(".jpg"),
        "l'image est deposee comme un envoi, en .jpg comme son en-tete le dit",
        repr(item.get("image")))
    dit(marque.get("operations") == ["retouche"],
        "la marque de la tache est restreinte a « retouche »", repr(marque.get("operations")))
    remise_a_zero()
    st_p, corps_p, _h = await c.appel("POST", EDITS, cle=TOUT, data=formulaire(
        prompt="le meme personnage sur une plage"))
    item_p = VUS[-1] if VUS else {}
    dit(st_p != 403 and not item_p.get("modele"),
        "« le meme personnage » sur la route des retouches n'est pas impose au "
        "moteur d'edition : pas de 403 d'entree, l'analyse decide (relecture "
        "du 8 novembre 2026)", f"HTTP {st_p} {erreur(corps_p).get('code')} "
                              f"{item_p.get('modele')!r}")
    remise_a_zero()
    st, corps, _h = await c.appel("POST", EDITS, cle=TOUT, data=formulaire(
        type_="image/jpeg", prompt="le ciel en rose", n=2, size="1536x1024"))
    item = VUS[-1] if VUS else {}
    dit(item.get("modele") == S.MOTEUR_RETOUCHE_OPENAI,
        "sans modele choisi, la route des retouches impose le moteur d'edition : "
        "« le ciel en rose » n'est plus laisse a l'analyse, qui y lisait une image",
        repr(item.get("modele")))
    dit(item.get("variantes") == 1 and item.get("taille") is None,
        "n et size ne valent rien pour une retouche : une seule, a la taille d'origine",
        f"variantes={item.get('variantes')} taille={item.get('taille')}")
    remise_a_zero()
    st, corps, _h = await c.appel("POST", EDITS, cle=TOUT, data=formulaire(
        nom_champ="image[]", nom_fichier="photo.webp", prompt="le ciel en rose",
        response_format="url", n=8))
    data = (corps or {}).get("data") or [{}]
    dit(st == 200 and data[0].get("url"), "« image[] » est lu aussi, et url rend un lien",
        f"HTTP {st}")
    dit(st == 200, "n=8 sur un edit n'est pas refuse : la retouche l'ignore", f"HTTP {st}")
    remise_a_zero()
    st, corps, _h = await c.appel("POST", EDITS, cle=TOUT, data=formulaire(
        image=False, prompt="le ciel en rose"))
    dit(st == 400 and erreur(corps).get("code") == "aucun_fichier"
        and erreur(corps).get("param") == "image" and not VUS,
        "un edit sans image : 400 « aucun_fichier », param image", f"HTTP {st} {corps}")
    st, corps, _h = await c.appel("POST", EDITS, cle=TOUT, json_={"prompt": "x"})
    dit(st == 400 and erreur(corps).get("code") == "formulaire_attendu",
        "un edit en JSON : 400 « formulaire_attendu »", f"HTTP {st} {corps}")
    st, corps, _h = await c.appel("POST", EDITS, cle=IMAGE, data=formulaire(prompt="x"))
    dit(st == 403 and erreur(corps).get("code") == "cle_operation_interdite" and not VUS,
        "une cle « image » seule ne retouche pas : 403", f"HTTP {st} {corps}")


# ══════════════════════════════════════════════════════════════════════
#  6. GET /openai/v1/models
# ══════════════════════════════════════════════════════════════════════
async def s_modeles(c):
    remise_a_zero()
    st, corps, _h = await c.appel("GET", MODELES, cle=TOUT)
    data = (corps or {}).get("data") or []
    ids = [m.get("id") for m in data]
    dit(st == 200 and (corps or {}).get("object") == "list"
        and all(m.get("object") == "model" and isinstance(m.get("created"), int)
                and m.get("owned_by") for m in data),
        "la liste a la forme d'OpenAI : object list, des « model »", f"HTTP {st}")
    dit(ids[:1] == [S.MODELE_STUDIO], "« comfystudio » (le choix du studio) en tete",
        repr(ids[:3]))
    dit("klein4b" in ids and "edition" in ids and "wan5b" not in ids and "audio" not in ids,
        "les moteurs d'image et de retouche, et rien d'autre", repr(ids))
    st, corps, _h = await c.appel("GET", MODELES, cle=IMAGE)
    ids = [m.get("id") for m in (corps or {}).get("data") or []]
    dit("klein4b" in ids and "edition" not in ids,
        "une cle « image » ne voit pas les moteurs de retouche", repr(ids))
    st, corps, _h = await c.appel("GET", MODELES, cle=VIDEO)
    ids = [m.get("id") for m in (corps or {}).get("data") or []]
    dit(ids == [S.MODELE_STUDIO], "une cle « video » ne voit aucun moteur d'image", repr(ids))

    # NI CE QU'AUCUNE CARTE DU PARC NE PORTE (ronde 10). Le PC derriere son
    # agent, eteint : 11 Go, 14,5 en debordant. klein9bhd (18) et flux1hd
    # (26) quittent la liste deroulante du client ; un « model » qui les nomme
    # est ignore comme un modele inconnu — le studio choisit, au lieu de
    # partir vers un refus.
    gardes_ = (dict(S.REGISTRE), dict(S.ETAT_NOEUDS))
    S.REGISTRE["pc_banc"] = {"id": "pc_banc", "titre": "PC (RTX 2080 Ti)",
                             "agent": True, "jeton": "x", "pause": None}
    S.ETAT_NOEUDS["pc_banc"] = {"repond": False, "vram": 11.0, "ram": 63.8}
    try:
        st, corps, _h = await c.appel("GET", MODELES, cle=TOUT)
        ids = [m.get("id") for m in (corps or {}).get("data") or []]
        lourd_, _f, _r = S._demande_openai({"prompt": "un phare", "model": "klein9bhd"},
                                           "image", fiche_de(TOUT), "fr")
        tient_, _f, _r = S._demande_openai({"prompt": "un phare", "model": "klein9b"},
                                           "image", fiche_de(TOUT), "fr")
    finally:
        S.REGISTRE.clear()
        S.REGISTRE.update(gardes_[0])
        S.ETAT_NOEUDS.clear()
        S.ETAT_NOEUDS.update(gardes_[1])
    dit(st == 200 and "klein9bhd" not in ids and "flux1hd" not in ids and "klein9b" in ids,
        "/models ne propose ni klein9bhd ni flux1hd, que le parc ne porte pas ; "
        "klein9b reste", repr(ids))
    dit(lourd_ is not None and "moteur" not in lourd_
        and (tient_ or {}).get("moteur") == "klein9b",
        "« model: klein9bhd » est ignore, le studio choisit ; « klein9b » est "
        "pris tel quel", f"{lourd_} / {tient_}"[:100])


async def principal():
    S.FILE_ATTENTE = asyncio.Queue()
    app = S.app()
    # Ni travailleurs, ni veilleur, ni ecoute de ComfyUI : le faux travailleur
    # du banc lit la file, et rien ne sort vers une machine.
    app.on_startup.remove(S.demarrer_file)
    serveur = TestServer(app, host="127.0.0.1")
    await serveur.start_server()
    ouvrier = asyncio.create_task(travailleur())
    c = Client(serveur)
    try:
        for titre, corps in (("1. les refus, au format OpenAI", s_refus),
                             ("2. les plafonds de la cle", s_plafonds),
                             ("3. la reponse et les champs", s_reponse),
                             ("4. ce que le studio rend d'autre", s_issues),
                             ("5. les edits, en multipart", s_edits),
                             ("6. la liste des modeles", s_modeles)):
            print(f"\n  ── {titre} ──")
            try:
                await corps(c)
            except Exception as e:
                dit(False, f"la section « {titre} » s'est arretee en route",
                    f"{type(e).__name__}: {e}")
    finally:
        ouvrier.cancel()
        await c.fermer()
        await serveur.close()


try:
    asyncio.run(principal())
finally:
    shutil.rmtree(DOSSIER, ignore_errors=True)

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
for x in rate:
    print("    NON :", x)
sys.exit(1 if rate else 0)
