# -*- coding: utf-8 -*-
"""Entrer, sortir, changer de conversation — et ce qu'un inconnu apprend.

    python banc_seance.py

TROIS ROUTES QUE PERSONNE N'EMPRUNTAIT. Le releve du 5 septembre 2026 a compte
treize routes du studio qu'aucun banc ne visitait, ni par son chemin ni par sa
fonction. Celles-ci sont les trois que la PAGE appelle — pas la console
d'administration, la page de tout le monde :

    POST /api/compte/sortir              api_sortir
    POST /api/conversation/{cid}/activer api_activer

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
    # SUPPRIME ferme ses sessions ouvertes. C'etait la seule revocation
    # jusqu'au 6 septembre 2026 — la generation, ci-dessous, en est la
    # seconde — et elle merite d'etre gardee : si la derniere ligne de
    # nom_du_jeton() disparaissait au profit du seul nom signe, un compte
    # efface continuerait d'entrer.
    S.COMPTES.supprimer("quelqu-un")
    dit(S.COMPTES.nom_du_jeton(jeton) is None,
        "en revanche SUPPRIMER un compte ferme ses sessions : le jeton signe "
        "ne suffit pas, le compte doit exister encore",
        "le meme jeton ne rend plus rien")

    # ── LA GENERATION : CE QUI TOUCHE A L'IDENTITE FERME LES SESSIONS ──
    # Jusqu'au 6 septembre 2026, une session capturee restait bonne trente
    # jours QUOI QUE FASSE son proprietaire : changer le mot de passe qu'on
    # croyait vole ne fermait rien. Le jeton porte depuis un numero de
    # generation, sous la signature ; changer de mot de passe, armer ou
    # desarmer le second facteur l'incrementent, et tout jeton d'avant ne
    # designe plus personne. La simple deconnexion d'un appareil, elle, ne
    # touche a rien : sortir sur le telephone ne ferme pas l'ordinateur du
    # salon — c'est le cas « sortir » ci-dessus.
    import mfa as _mfa
    MDP1, MDP2 = "un-mot-de-passe-assez-long", "un-autre-mot-de-passe-long"
    S.COMPTES.creer("prudent", MDP1)
    vieux = S.COMPTES.jeton("prudent")
    S.COMPTES.changer_mdp("prudent", MDP2)
    neuf = S.COMPTES.jeton("prudent")
    dit(S.COMPTES.nom_du_jeton(vieux) is None
        and S.COMPTES.nom_du_jeton(neuf) == "prudent",
        "changer de mot de passe FERME les sessions ouvertes : le jeton "
        "d'avant ne designe plus personne, celui remis apres ouvre",
        f"avant={S.COMPTES.nom_du_jeton(vieux)!r}, "
        f"apres={S.COMPTES.nom_du_jeton(neuf)!r}")

    # LA GENERATION EST SIGNEE, ET C'EST TOUT L'INTERET. Le numero se lit dans
    # le jeton ; si on pouvait y ecrire le numero courant, un vieux jeton
    # capture se ranimerait d'une simple retouche.
    morceaux = neuf.split(".")
    retouche = ".".join(vieux.split(".")[:2] + [morceaux[2]] + vieux.split(".")[3:])
    dit(len(morceaux) == 4 and S.COMPTES.nom_du_jeton(retouche) is None,
        "et retoucher la generation dans un vieux jeton ne le ranime pas : "
        "elle est SOUS la signature, pas a cote",
        f"{len(morceaux)} morceaux, retouche={S.COMPTES.nom_du_jeton(retouche)!r}")

    avant_mfa = S.COMPTES.jeton("prudent")
    secret_totp, _ = S.COMPTES.mfa_preparer("prudent")
    S.COMPTES.mfa_confirmer("prudent", _mfa.code(secret_totp))
    dit(S.COMPTES.nom_du_jeton(avant_mfa) is None
        and S.COMPTES.nom_du_jeton(S.COMPTES.jeton("prudent")) == "prudent",
        "ARMER le second facteur ferme les sessions d'avant : celui qui "
        "tenait une session sans le code ne la garde pas",
        f"avant={S.COMPTES.nom_du_jeton(avant_mfa)!r}")

    avant_retrait = S.COMPTES.jeton("prudent")
    S.COMPTES.mfa_retirer("prudent")
    dit(S.COMPTES.nom_du_jeton(avant_retrait) is None
        and S.COMPTES.nom_du_jeton(S.COMPTES.jeton("prudent")) == "prudent",
        "le DESARMER aussi : une protection levee par un tiers ne laisse pas "
        "courir les sessions qu'elle gardait",
        f"avant={S.COMPTES.nom_du_jeton(avant_retrait)!r}")


    # L'ANCIEN FORMAT NE PASSE PLUS. Un jeton a trois morceaux, signe comme
    # avant le 6 septembre 2026, est exactement ce qu'un navigateur garde
    # encore apres la mise a jour — et ce qu'une capture d'alors contiendrait.
    # Le refuser deconnecte tout le monde une fois ; l'accepter « par
    # compatibilite » laisserait la generation contournable a jamais.
    fin = str(int(time.time() + 3600))
    import hashlib as _h
    import hmac as _hm
    ancien = f"prudent.{fin}." + _hm.new(S.COMPTES.secret, f"prudent.{fin}".encode(),
                                         _h.sha256).hexdigest()[:32]
    dit(ancien.count(".") == 2 and S.COMPTES.nom_du_jeton(ancien) is None,
        "un jeton de l'ancien format, a trois morceaux et signe sans "
        "generation, ne rend plus rien",
        f"{ancien[:24]}… -> {S.COMPTES.nom_du_jeton(ancien)!r}")

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

finally:
    pass

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
for x in rate:
    print("    NON :", x)
sys.exit(1 if rate else 0)
