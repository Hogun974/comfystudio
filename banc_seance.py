# -*- coding: utf-8 -*-
"""Entrer, sortir, changer de conversation — et ce qu'un inconnu apprend.

    python banc_seance.py

TROIS ROUTES QUE PERSONNE N'EMPRUNTAIT. Le releve du 5 septembre 2026 a compte
treize routes du studio qu'aucun banc ne visitait, ni par son chemin ni par sa
fonction. Celles-ci sont les trois que la PAGE appelle — pas la console
d'administration, la page de tout le monde :

    POST /api/compte/sortir              api_sortir
    POST /api/conversation/{cid}/activer api_activer
    GET  /api/fournisseurs               api_fournisseurs

Elles sont courtes. Ce qu'elles gardent ne l'est pas :

  - SORTIR DOIT VRAIMENT SORTIR. La suppression du biscuit porte « path="/" »,
    et ce n'est pas decoratif : un biscuit pose sur « / » ne s'efface QUE par
    une suppression qui nomme le meme chemin. Sans lui, le navigateur garde le
    sien, la page affiche « deconnecte » et la requete suivante repart
    connectee. C'est le pire des deux etats — on croit etre sorti.
  - ON N'ACTIVE PAS LA CONVERSATION DE QUELQU'UN D'AUTRE. C'est la seule chose
    qui separe deux espaces sur un studio ouvert au reseau local.
  - LA ROUTE DES FOURNISSEURS N'EST PAS PROTEGEE, ET C'EST VOULU : elle sert un
    bandeau a tout le monde. Sa docstring promet « aucune cle, aucun indice de
    cle » — c'est cette promesse-la qu'on mesure, parce qu'une route ouverte
    qui laisse filer un secret le laisse filer a n'importe qui.

CE QU'IL NE VOIT PAS :

  - Que la page appelle bien ces routes. banc_page.py releve le HTML ; ce
    banc-ci appelle les fonctions. Les deux moities sont tenues separement, et
    aucune ne remplace l'autre.
  - Le vrai cycle d'un navigateur. Ce que « sortir » efface est mesure sur la
    reponse HTTP, pas sur un navigateur qui la recoit.
"""
import asyncio
import json
import os
import sys
import tempfile
import time

os.environ["STUDIO_DONNEES"] = tempfile.mkdtemp(prefix="banc_seance_")
os.environ["STUDIO_AUTH"] = "libre"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serveur as S  # noqa: E402

ok, rate = [], []
MOI = "m" * 32
TOI = "t" * 32


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


class Req(dict):
    def __init__(self, pid=MOI, match=None, corps=None, requete=None):
        super().__init__(pid=pid, compte="")
        self.match_info = match or {}
        self.headers, self.cookies = {}, {}
        self.query = requete or {}
        self._corps = corps

    async def json(self):
        if self._corps is None:
            raise ValueError("pas de corps")
        return self._corps


def lire(rep):
    return rep.status, json.loads(rep.text)


lancer = asyncio.run

try:
    # ══════════════════════════════════════════════════════════════════
    #  1. sortir — et le chemin du biscuit, qui decide de tout
    # ══════════════════════════════════════════════════════════════════
    print("\n  ── sortir ──")
    rep = lancer(S.api_sortir(Req()))
    dit(rep.status == 200, "la sortie repond 200", f"HTTP {rep.status}")

    # ON LIT LE MORCEAU QUI PARTIRA EN « Set-Cookie », et non un drapeau
    # interne : c'est le navigateur qui obeit, et il n'obeit qu'a cet en-tete.
    # aiohttp ne le materialise dans headers qu'a l'envoi ; avant cela il vit
    # dans rep.cookies, et c'est OutputString() qui rend la ligne exacte.
    morceau = rep.cookies.get("studio_compte")
    biscuit = morceau.OutputString() if morceau else ""
    dit(bool(biscuit), "elle pose bien un « Set-Cookie » sur studio_compte",
        biscuit[:60] or "aucun")

    # LE CHEMIN, ET C'EST TOUT LE CAS. Le biscuit de connexion est pose avec
    # « path="/" » ; un navigateur n'efface QUE le biscuit dont le nom ET le
    # chemin correspondent. Une suppression sans chemin viserait celui du
    # dossier courant — « /api/compte » — qui n'existe pas. La page afficherait
    # « deconnecte » et la requete suivante repartirait connectee.
    dit("Path=/" in biscuit and "Path=/api" not in biscuit,
        "et elle l'efface sur « / », le chemin ou la connexion l'a pose : sans "
        "cela le navigateur garde le sien, et l'on se croit sorti",
        biscuit[:80])
    dit(biscuit.split(";")[0].strip() in ('studio_compte=""', "studio_compte="),
        "le biscuit repart vide", biscuit.split(";")[0])
    # ET PERIME, ce qui est l'autre moitie de l'effacement : un biscuit vide
    # mais sans date passee reste pose, vide, jusqu'a la fin de la session du
    # navigateur.
    dit("Max-Age=0" in biscuit or "01 Jan 1970" in biscuit,
        "et perime : vide mais sans date passee, il resterait pose",
        biscuit[len(biscuit.split(";")[0]):][:56])

    # CE QU'ELLE NE PEUT PAS FAIRE, ET QUE docs/comptes.md ECRIT. Le jeton de
    # session est signe et sans registre : il n'y a rien a revoquer cote
    # serveur. Sortir efface le biscuit, et le jeton reste valable jusqu'a sa
    # peremption. Ce cas est la pour que la promesse et le code ne divergent
    # pas — si un registre de sessions apparaissait un jour, il rougirait.
    # COMPTES est None tant que charger_comptes() n'a pas tourne, et ce banc
    # ne demarre pas de studio : on pose un registre a nous, dans le dossier
    # temporaire, comme banc_comptes.py le fait.
    import comptes as _c
    S.COMPTES = _c.Comptes(os.path.join(os.environ["STUDIO_DONNEES"],
                                        "_comptes.json"), "secret-de-banc")
    S.COMPTES.creer("quelqu-un", "un-mot-de-passe-assez-long")
    jeton = S.COMPTES.jeton("quelqu-un")
    dit(bool(jeton) and S.COMPTES.nom_du_jeton(jeton) == "quelqu-un",
        "le jeton de session vaut par sa SIGNATURE : il se relit apres la "
        "sortie, et « sortir » n'a donc rien a revoquer — c'est ce que "
        "docs/comptes.md ecrit", f"{len(jeton)} caracteres")

    # IL Y A QUAND MEME UN LEVIER, ET IL N'EST PAS LA OU L'ON CROIT. Le jeton
    # est signe, mais nom_du_jeton() relit le registre a la fin : un compte
    # SUPPRIME ferme ses sessions ouvertes, la ou un mot de passe change ne les
    # ferme pas. C'est la seule revocation qui existe, et elle merite d'etre
    # gardee — si la derniere ligne de nom_du_jeton() disparaissait au profit
    # du seul nom signe, un compte efface continuerait d'entrer.
    S.COMPTES.supprimer("quelqu-un")
    dit(S.COMPTES.nom_du_jeton(jeton) is None,
        "en revanche SUPPRIMER un compte ferme ses sessions : le jeton signe "
        "ne suffit pas, le compte doit exister encore",
        "le meme jeton ne rend plus rien")

    # ══════════════════════════════════════════════════════════════════
    #  2. activer une conversation — la sienne, et seulement la sienne
    # ══════════════════════════════════════════════════════════════════
    print("\n  ── changer de conversation ──")
    S.CONVERSATIONS.clear()
    S.COURANTE.clear()
    mienne = S._vide(proprietaire=MOI)
    tienne = S._vide(proprietaire=TOI)
    fermee = S._vide(proprietaire=MOI)
    fermee["ferme"] = time.time()
    for c in (mienne, tienne, fermee):
        S.CONVERSATIONS[c["id"]] = c

    st, d = lire(lancer(S.api_activer(Req(match={"cid": mienne["id"]}))))
    dit(st == 200 and d.get("courante") == mienne["id"]
        and S.COURANTE.get(MOI) == mienne["id"],
        "activer la mienne la rend courante, cote reponse ET cote studio",
        f"HTTP {st}")

    # LE CAS QUI SEPARE DEUX ESPACES. Sur un studio ouvert au reseau local,
    # c'est la seule chose qui empeche d'ouvrir le fil de quelqu'un d'autre en
    # collant son identifiant.
    st, d = lire(lancer(S.api_activer(Req(match={"cid": tienne["id"]}))))
    dit(st == 404 and S.COURANTE.get(MOI) == mienne["id"],
        "celle de quelqu'un d'autre rend 404, et ne deplace RIEN : la courante "
        "reste la mienne", f"HTTP {st}, courante={S.COURANTE.get(MOI)}")

    # « INCONNUE » ET NON « REFUSEE », et les deux mots comptent : repondre 403
    # dirait « elle existe, mais pas pour toi », ce qui publie l'existence des
    # conversations des autres a qui essaie des identifiants.
    st_inconnue, _ = lire(lancer(S.api_activer(Req(match={"cid": "pas-un-id"}))))
    dit(st_inconnue == 404 and st == 404,
        "et une conversation qui n'existe pas rend la MEME chose : distinguer "
        "les deux publierait l'existence des fils des autres",
        f"celle d'un autre {st}, une inexistante {st_inconnue}")

    st, d = lire(lancer(S.api_activer(Req(match={"cid": fermee["id"]}))))
    dit(st == 404,
        "une conversation fermee ne se rouvre pas par la : elle attend sa purge",
        f"HTTP {st}")

    # ══════════════════════════════════════════════════════════════════
    #  3. les fournisseurs — une route ouverte, donc une promesse a tenir
    # ══════════════════════════════════════════════════════════════════
    print("\n  ── ce qu'un inconnu apprend des fournisseurs ──")
    SECRET = "sk-une-cle-qui-ne-doit-jamais-sortir-0123456789"
    vraie_cle, S.cle_de = S.cle_de, lambda n: SECRET
    try:
        st, d = lire(lancer(S.api_fournisseurs(Req())))
        plat = json.dumps(d)
        dit(st == 200 and d, "la route repond sans jeton : elle sert un bandeau "
            "a tout le monde, et c'est voulu", f"HTTP {st}, {len(d)} modalite(s)")
        # LA PROMESSE DE SA DOCSTRING, MESUREE. Une route ouverte qui laisse
        # filer un secret le laisse filer a n'importe qui.
        dit(SECRET not in plat and "sk-" not in plat,
            "et elle ne porte NI la cle NI un morceau de cle", plat[:70])
        dit(all(set(v) <= {"libelle", "choix", "titre", "distant"}
                for v in d.values()),
            "quatre champs par modalite, et pas un de plus",
            ", ".join(sorted({k for v in d.values() for k in v})))
        # « distant » EST UN BOOLEEN, ET IL DIT DEJA QUELQUE CHOSE : que le
        # studio a une cle pour ce fournisseur-la. C'est le minimum pour que la
        # page puisse avertir « ceci part chez un tiers », et c'est la limite
        # exacte de ce qu'une route ouverte doit dire.
        dit(all(isinstance(v.get("distant"), bool) for v in d.values()),
            "« distant » est un booleen : la page doit pouvoir avertir que la "
            "demande part chez un tiers, sans rien apprendre de plus",
            str({k: v.get("distant") for k, v in d.items()})[:70])
    finally:
        S.cle_de = vraie_cle
finally:
    pass

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
for x in rate:
    print("    NON :", x)
sys.exit(1 if rate else 0)
