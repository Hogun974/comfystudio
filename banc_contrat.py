#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Le contrat OpenAPI des programmes, confronte au studio qui l'applique.

contrat.py decrit /api/v1/* et /mcp a des machines — un assistant IA, un outil
qui importe une API. Une description qui ment est pire qu'une description
absente : l'assistant appelle une route qui n'existe plus, attend un etat qui
n'arrive jamais, se branche sur un code de refus que le studio ne rend pas. Ce
banc confronte chaque moitie a l'autre, DANS LES DEUX SENS.

CE QU'IL GARDE, DANS L'ORDRE DES DEGATS :

  1. LES PORTES LIBRES. Seuls le lien signe et le contrat lui-meme se lisent
     sans cle ; toute autre operation herite de bearerAuth. Un « security: [] »
     pose par megarde sur POST /api/v1/rendus dirait a un client qu'il peut
     lancer des rendus sans cle — et un client genere ne poserait plus
     l'en-tete.
  2. LES ROUTES. Chaque route que S.app() enregistre sous /api/v1/ (et /mcp)
     est decrite, avec sa methode ; chaque chemin decrit existe dans le
     routeur. GET /api/v1/openapi.json est EXIGE : c'est par elle que le
     document est servi.
  3. LES REFUS. Chaque code que serveur.py peut rendre (releve dans son TEXTE :
     refus_programme, refus, _sans_cle, « "code": ») est dans le contrat, avec
     le meme statut HTTP ; chaque code du contrat est rendu quelque part, et a
     sa phrase dans traductions.py.
  4. LA FORME. Les champs de Rendu, Fichier, Cle, Moi, Moteur, Moteurs et du
     corps d'un rappel sont ceux que le studio produit — mesures sur ce qu'il
     rend, pas sur ce qu'on croit qu'il rend. Les champs de DemandeRendu et de
     ReponseQuestion sont ceux que les routes LISENT.
  5. LES BORNES. Les etats, ATTENDRE_MAX (la borne de chaque « attendre »),
     les durees, les tailles, les priorites, les outils MCP : recopies dans
     contrat.py, puisque serveur.py l'importe et non l'inverse, ils doivent
     etre egaux a ceux de serveur.py.
  6. LE DOCUMENT. Du JSON pur (aucun tuple, aucun objet), OpenAPI 3.1, chaque
     $ref resolu, chaque operationId unique, l'adresse du studio reprise, un
     document neuf a chaque appel.

    python banc_contrat.py

CE QU'IL NE VOIT PAS :

  - La conformite au schema officiel d'OpenAPI 3.1 : aucun validateur n'est
    dans la bibliotheque standard. Le banc verifie la structure qu'il connait
    (refs, operationId, securite), pas chaque mot-clef.
  - Les reponses REELLES d'une requete HTTP : les formes sont mesurees en
    appelant les fonctions qui les produisent, pas le routeur sur un socket.
  - Le 413 du serveur HTTP lui-meme (corps JSON au-dela de la borne) : il
    n'a ni corps JSON ni code, le contrat le dit en prose.
  - Les descriptions : qu'une phrase dise vrai ne se mesure pas.
"""
import inspect
import json
import os
import re
import shutil
import sys
import tempfile

for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DONNEES = tempfile.mkdtemp(prefix="banc_contrat_")
os.environ["STUDIO_DONNEES"] = DONNEES
ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import serveur as S  # noqa: E402
import contrat as C  # noqa: E402
import traductions  # noqa: E402

ok, rate = [], []


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


class Req(dict):
    """Le peu d'une requete aiohttp que les fonctions mesurees lisent."""

    def __init__(self, **champs):
        super().__init__(**champs)
        self.headers, self.cookies, self.query, self.match_info = {}, {}, {}, {}


def operations(doc):
    """{(chemin, methode)} des operations decrites."""
    return {(p, m) for p, item in doc["paths"].items() for m in item}


def tous_les_refs(noeud):
    if isinstance(noeud, dict):
        for k, v in noeud.items():
            if k == "$ref":
                yield v
            else:
                yield from tous_les_refs(v)
    elif isinstance(noeud, list):
        for v in noeud:
            yield from tous_les_refs(v)


def resoudre(doc, ref):
    if not ref.startswith("#/"):
        return None
    noeud = doc
    for morceau in ref[2:].split("/"):
        if not isinstance(noeud, dict) or morceau not in noeud:
            return None
        noeud = noeud[morceau]
    return noeud


def proprietes(doc, nom):
    return set(doc["components"]["schemas"][nom].get("properties", {}))


def schemas_attendre(noeud, chemin=""):
    """Chaque schema d'un champ ou d'un parametre « attendre »."""
    if isinstance(noeud, dict):
        if noeud.get("name") == "attendre" and "schema" in noeud:
            yield chemin, noeud["schema"]
        props = noeud.get("properties")
        if isinstance(props, dict) and "attendre" in props:
            yield chemin + ".attendre", props["attendre"]
        for k, v in noeud.items():
            yield from schemas_attendre(v, f"{chemin}/{k}")
    elif isinstance(noeud, list):
        for i, v in enumerate(noeud):
            yield from schemas_attendre(v, f"{chemin}[{i}]")


try:
    BASE = "http://studio.maison:8199"
    DOC = C.document(BASE)
    TEXTE = open(os.path.join(ICI, "serveur.py"), encoding="utf-8").read()

    # ══════════════════════════════════════════════════════════════════
    print("\n  ── les portes libres ──")
    schema_ = DOC["components"]["securitySchemes"].get("bearerAuth") or {}
    dit(schema_.get("type") == "http" and schema_.get("scheme") == "bearer",
        "le schema de securite est bearerAuth, http + bearer", str(schema_))
    dit(DOC.get("security") == [{"bearerAuth": []}],
        "toute operation exige la cle par defaut", str(DOC.get("security")))
    libres = sorted(f"{m.upper()} {p}" for p, item in DOC["paths"].items()
                    for m, op in item.items() if op.get("security") == [])
    attendus = ["GET /api/v1/lien/{jeton}", "GET /api/v1/openapi.json"]
    dit(libres == attendus,
        "seuls le lien signe et le contrat se lisent sans cle", ", ".join(libres))
    autres = [f"{m.upper()} {p}" for p, item in DOC["paths"].items()
              for m, op in item.items() if "security" in op and op["security"] != []]
    dit(not autres, "aucune operation ne remplace la securite par une autre",
        ", ".join(autres) or "aucune")

    # ══════════════════════════════════════════════════════════════════
    print("\n  ── les routes, dans les deux sens ──")
    ROUTEUR = set()
    for r in S.app().router.routes():
        chemin = r.resource.canonical if r.resource else ""
        if r.method == "HEAD":
            continue
        if chemin.startswith(S.PREFIXE_PROGRAMME) or chemin == S.CHEMIN_MCP:
            # « * » sur /mcp : la route repond 405 a tout sauf POST, et c'est
            # POST que le contrat decrit.
            ROUTEUR.add((chemin, "post" if r.method == "*" else r.method.lower()))
    DECRITES = operations(DOC)
    dit(len(ROUTEUR) >= 10, "le releve du routeur trouve les routes de programme",
        f"{len(ROUTEUR)} operations")
    oubliees = sorted(ROUTEUR - DECRITES)
    dit(not oubliees, "chaque route du routeur est decrite dans le contrat",
        ", ".join(f"{m.upper()} {p}" for p, m in oubliees) or "toutes")
    fantomes = sorted(DECRITES - ROUTEUR - {("/api/v1/openapi.json", "get")})
    dit(not fantomes, "chaque chemin du contrat existe dans le routeur",
        ", ".join(f"{m.upper()} {p}" for p, m in fantomes) or "tous")
    dit(("/api/v1/openapi.json", "get") in DECRITES,
        "le contrat se decrit lui-meme (GET /api/v1/openapi.json)")
    dit(("/api/v1/openapi.json", "get") in ROUTEUR,
        "GET /api/v1/openapi.json est branchee dans le routeur",
        "absente : a brancher dans app()" if ("/api/v1/openapi.json", "get")
        not in ROUTEUR else "presente")

    # ══════════════════════════════════════════════════════════════════
    print("\n  ── les refus et leurs codes ──")
    # LE BLOC DES PROGRAMMES, ET LUI SEUL. Les routes de gestion des cles
    # (/api/compte/acces), qui le suivent, rendent elles aussi des codes —
    # mais a une SESSION, dans la page : elles ne sont pas dans ce contrat.
    debut = TEXTE.find("# ══════════════════════ pilotage par programme")
    fin = TEXTE.find("# ── la gestion des cles, par leur proprietaire", debut)
    BLOC = TEXTE[debut:fin] if 0 <= debut < fin else ""
    dit(len(BLOC) > 20000, "temoin : le bloc « pilotage par programme » est trouve",
        f"{len(BLOC)} caracteres")
    # (code, statut) releves dans le TEXTE. Le statut suit la cle dans
    # refus_programme(cle, statut, ...) et refus(cle, statut, ...).
    RELEVES = set()
    for cle, statut in re.findall(
            r'(?:refus_programme|(?<![_\w])refus)\(\s*"erreur\.([a-z_]+)",\s*(\d{3})',
            BLOC):
        RELEVES.add((cle, int(statut)))
    # _sans_cle rend toujours 401 : sa cle par defaut, et celle qu'on lui passe.
    for cle in re.findall(r'_sans_cle\([^)]*"erreur\.([a-z_]+)"', BLOC):
        RELEVES.add((cle, 401))
    # Les refus ecrits a la main, « return 400, {"erreur": T("erreur.x"… ».
    # LE CODE EXPLICITE PRIME, quand le corps en porte un : le conseil du
    # garde-fou (« ecris fille ou garcon ») a sa PROPRE phrase, mais garde le
    # code « refus_mineurs » — un workflow n'a pas a en connaitre deux. Deduire
    # le code de la cle aurait invente un « refus_mineurs_genre » que le
    # serveur ne rend jamais (4 novembre 2026).
    for statut, cle, explicite in re.findall(
            r'return (\d{3}), \{"erreur": T\("erreur\.([a-z_]+)"'
            r'(?:[^}]*?"code": "([a-z_]+)")?', BLOC):
        RELEVES.add((explicite or cle, int(statut)))
    CODES_LUS = {c for c, _ in RELEVES}
    dit(len(CODES_LUS) >= 15, "le releve du texte trouve les codes de refus",
        f"{len(CODES_LUS)} codes")
    # TEMOIN DU RELEVE : chaque appel a refus_programme( porte sa cle en
    # premier argument, sur la meme ligne. Un appel ecrit autrement echapperait
    # au releve, et le banc serait vert de ce qu'il n'a pas lu. Le seul appel
    # sans cle litterale est celui de _sans_cle, qui relaie la sienne — lue
    # juste au-dessus, par sa signature et par ses appelants.
    litteraux = len(re.findall(r'(?<!def )refus_programme\(\s*"', BLOC))
    lus = len(re.findall(r'(?<!def )refus_programme\(\s*"erreur\.[a-z_]+",\s*\d{3}', BLOC))
    relais = re.findall(r'(?<!def )refus_programme\(\s*([^"\s][^,]*),', BLOC)
    dit(litteraux == lus and lus >= 15 and relais == ["cle"],
        "chaque appel a refus_programme est lu par le releve",
        f"{lus} lus sur {litteraux}, relais {relais}")
    ecrits = len(re.findall(r'return \d{3}, \{"erreur"', BLOC))
    lus_main = len(re.findall(r'return \d{3}, \{"erreur": T\("erreur\.[a-z_]+"', BLOC))
    dit(ecrits == lus_main and ecrits >= 1,
        "chaque refus ecrit a la main est lu par le releve",
        f"{lus_main} lus sur {ecrits}")
    absents = sorted(CODES_LUS - set(C.REFUS))
    dit(not absents, "chaque code que serveur.py rend est dans le contrat",
        ", ".join(absents) or "tous")
    texte_refus = json.dumps(DOC["components"]["schemas"]["Refus"], ensure_ascii=False)
    non_decrits = sorted(c for c in CODES_LUS if f"`{c}`" not in texte_refus)
    dit(not non_decrits, "et chacun apparait dans la description des refus",
        ", ".join(non_decrits) or "tous")
    enum_ = DOC["components"]["schemas"]["Refus"]["properties"]["code"].get("enum")
    dit(set(enum_ or ()) == set(C.REFUS) | set(C.REFUS_COMMUNS)
        and len(enum_ or ()) == len(set(enum_ or ())),
        "l'enum du code de Refus est la table des refus, plus celle des refus "
        "communs, sans doublon", f"{len(enum_ or ())} codes")
    mauvais = sorted(f"{c} : {s} dans serveur.py, {C.REFUS[c][0]} dans le contrat"
                     for c, s in RELEVES if c in C.REFUS and C.REFUS[c][0] != s)
    dit(not mauvais, "chaque code a le meme statut HTTP des deux cotes",
        " ; ".join(mauvais) or "tous")
    morts = sorted(set(C.REFUS) - CODES_LUS)
    dit(not morts, "chaque code du contrat est rendu par serveur.py",
        ", ".join(morts) or "tous")
    sans_phrase = sorted(c for c in C.REFUS if "erreur." + c not in traductions.TEXTES)
    dit(not sans_phrase, "chaque code a sa phrase dans traductions.py",
        ", ".join(sans_phrase) or "tous")

    # QUAND REESSAYER. Chaque 429 du studio porte Retry-After et
    # « reessayer_dans » (serveur.reessayer_dans) : le contrat doit le dire,
    # sinon un client genere ne le lit pas et reessaie a l'aveugle.
    freine = DOC["components"]["responses"]["Freine"]
    dit("Retry-After" in (freine.get("headers") or {})
        and "reessayer_dans" in DOC["components"]["schemas"]["Refus"]["properties"],
        "les 429 du contrat decrivent Retry-After, et Refus son « reessayer_dans »")
    codes_429 = sorted(c for c, (s, _q) in C.REFUS.items() if s == 429)
    dit(all(c in freine.get("description", "") for c in codes_429),
        "la reponse « Freine » nomme chaque code rendu en 429",
        ", ".join(codes_429))

    # ── LES REFUS COMMUNS AVEC LA PAGE ──
    # valider_demande et api_televerser vivent HORS du bloc des programmes :
    # la page les appelle aussi. Le contrat disait qu'ils n'avaient « pas
    # encore » de code alors qu'ils en portaient un (4 novembre 2026) ; on les
    # releve donc dans le source de ces deux fonctions, avec la meme rigueur.
    print("\n  ── les refus communs avec la page ──")
    SOURCE_VALIDER = inspect.getsource(S.valider_demande)
    SOURCE_TELEVERSER = inspect.getsource(S.api_televerser)
    COMMUNS = set()
    for cle, code, statut in re.findall(
            r'T\("erreur\.([a-z_]+)"[^}]*?"code": "([a-z_]+)"\},\s*status=(\d{3})',
            SOURCE_VALIDER):
        COMMUNS.add((code, int(statut)))
    ecrits_v = SOURCE_VALIDER.count('"code": "')
    dit(ecrits_v == len(COMMUNS) and ecrits_v >= 10,
        "temoin : chaque code de valider_demande est lu avec son statut",
        f"{len(COMMUNS)} lus sur {ecrits_v}")
    lus_t = re.findall(r'_refus_televersement\(\s*"erreur\.([a-z_]+)",\s*(\d{3})',
                       SOURCE_TELEVERSER)
    appels_t = len(re.findall(r'_refus_televersement\(', SOURCE_TELEVERSER))
    dit(appels_t == len(lus_t) and appels_t >= 5,
        "temoin : chaque refus du televersement passe par _refus_televersement, "
        "et chacun est lu avec son statut", f"{len(lus_t)} lus sur {appels_t}")
    COMMUNS |= {(c, int(s)) for c, s in lus_t}
    # Aucun refus du televersement ecrit a la main, sans code : c'est
    # precisement ce qui manquait.
    a_la_main = re.findall(r'json_response\(\s*\{"erreur"', SOURCE_TELEVERSER)
    dit(not a_la_main, "aucun refus du televersement n'est ecrit sans code",
        f"{len(a_la_main)} ecrits a la main")
    rep = S._refus_televersement("erreur.aucun_fichier", 400, "en")
    corps_t = json.loads(rep.text)
    dit(rep.status == 400 and corps_t.get("code") == "aucun_fichier"
        and corps_t.get("erreur") == traductions.T("erreur.aucun_fichier", "en"),
        "_refus_televersement rend la phrase dans la langue ET le code tire de la cle",
        str(corps_t))
    TOUS = dict(C.REFUS, **C.REFUS_COMMUNS)
    absents_c = sorted(c for c, _ in COMMUNS if c not in TOUS)
    dit(not absents_c, "chaque code commun rendu est dans le contrat",
        ", ".join(absents_c) or f"{len(COMMUNS)} codes")
    mauvais_c = sorted(f"{c} : {s} dans serveur.py, {TOUS[c][0]} dans le contrat"
                       for c, s in COMMUNS if c in TOUS and TOUS[c][0] != s)
    dit(not mauvais_c, "chaque code commun a le meme statut des deux cotes",
        " ; ".join(mauvais_c) or "tous")
    morts_c = sorted(set(C.REFUS_COMMUNS) - {c for c, _ in COMMUNS})
    dit(not morts_c, "chaque code commun du contrat est rendu par l'une des "
        "deux fonctions", ", ".join(morts_c) or "tous")
    doubles = sorted(set(C.REFUS) & set(C.REFUS_COMMUNS))
    dit(not doubles, "aucun code n'est dans les deux tables du contrat",
        ", ".join(doubles) or "aucun")
    non_decrits_c = sorted(c for c in C.REFUS_COMMUNS if f"`{c}`" not in texte_refus)
    dit(not non_decrits_c, "et chaque code commun apparait dans la description "
        "des refus", ", ".join(non_decrits_c) or "tous")
    dit("pas encore" not in texte_refus,
        "la description ne dit plus que ces refus n'ont « pas encore » de code",
        "")
    sans_phrase_c = sorted(c for c in C.REFUS_COMMUNS
                           if "erreur." + c not in traductions.TEXTES)
    dit(not sans_phrase_c, "chaque code commun a sa phrase dans traductions.py",
        ", ".join(sans_phrase_c) or "tous")

    # ══════════════════════════════════════════════════════════════════
    print("\n  ── la forme de ce que le studio rend ──")
    acces_ = S._acces.Acces(os.path.join(DONNEES, "_acces_banc.json"))
    cree = acces_.creer("banc", "banc du contrat", 0)
    fiche = cree["fiche"]
    tid = "ab" * 16
    conv = {"id": "c" * 32, "api": {"cle": fiche["id"]},
            "tours": [{"id": tid, "etat": "fini", "demande": "un renard",
                       "fichiers": [{"filename": "studio_1.png"},
                                    {"filename": "studio_1.mp4"}]}]}
    S.SECRET_LIENS = "secret du banc"
    corps = S.rendu_public(tid, conv, None, conv["tours"][0], BASE, "fr")
    dit(set(corps) == proprietes(DOC, "Rendu"),
        "Rendu : les champs du contrat sont ceux de rendu_public",
        f"en trop {sorted(proprietes(DOC, 'Rendu') - set(corps))}, "
        f"manquants {sorted(set(corps) - proprietes(DOC, 'Rendu'))}")
    dit(len(corps["fichiers"]) == 2 and corps["etat"] == "fini",
        "temoin : le rendu mesure a bien deux fichiers et il est fini",
        f"{len(corps['fichiers'])} fichiers, {corps['etat']}")
    f0 = corps["fichiers"][0] if corps["fichiers"] else {}
    dit(set(f0) == proprietes(DOC, "Fichier"),
        "Fichier : les champs du contrat sont ceux d'un fichier rendu",
        f"rendus {sorted(f0)}")
    dit(bool(f0.get("lien")) and bool(f0.get("url")),
        "temoin : le fichier mesure porte une url ET un lien signe")
    # Les adresses rendues tombent sur des chemins DECRITS.
    gabarits = [re.compile("^" + re.escape(BASE) + re.sub(r"\\\{[a-z]+\\\}", "[^/]+", re.escape(p)) + "$")
                for p in DOC["paths"]]
    adresses = [f.get(k) for f in corps["fichiers"] for k in ("url", "lien")]
    hors = [a for a in adresses if not any(g.match(a or "") for g in gabarits)]
    dit(not hors and len(adresses) == 4,
        "chaque url et chaque lien rendus designent un chemin du contrat",
        ", ".join(hors) or f"{len(adresses)} adresses")
    dit(set(fiche) == proprietes(DOC, "Cle"),
        "Cle : les champs du contrat sont ceux de la fiche publique",
        f"fiche {sorted(fiche)}")
    S.ACCES = acces_
    req = Req(par_cle=fiche, compte="banc", pid="b" * 32)
    moi = json.loads(S.asyncio.run(S.api_v1_moi(req)).text)
    dit(set(moi) == proprietes(DOC, "Moi"),
        "Moi : les champs du contrat sont ceux de GET /api/v1/moi", f"{sorted(moi)}")
    moteurs = S._moteurs_pour(dict(fiche, nuage=True), "fr")
    dit(len(moteurs) >= 5 and all(set(m) == proprietes(DOC, "Moteur") for m in moteurs),
        "Moteur : les champs du contrat sont ceux de chaque moteur liste",
        f"{len(moteurs)} moteurs, champs {sorted(moteurs[0]) if moteurs else '?'}")
    source_moteurs = inspect.getsource(S.api_v1_moteurs)
    champs_moteurs = set(re.findall(r'"([a-z_]+)":', source_moteurs))
    dit(champs_moteurs == proprietes(DOC, "Moteurs"),
        "Moteurs : les champs du contrat sont ceux de GET /api/v1/moteurs",
        f"{sorted(champs_moteurs)}")
    # TOUS LES CORPS SIGNES, et non le premier trouve : le vrai rappel et
    # l'essai (rappel.essai) n'ont pas les memes champs, et lire le premier
    # faisait dependre la verification de l'ORDRE des fonctions dans
    # serveur.py — l'essai, ecrit plus haut, a pris la place du vrai rappel
    # (4 novembre 2026). L'union doit etre exactement ce que le contrat decrit.
    corps_signes = re.findall(r"_rappels\.corps_de\(\{(.*?)\}\)", TEXTE, re.S)
    champs_rappel = set()
    for c_ in corps_signes:
        champs_rappel |= set(re.findall(r'"([a-z_]+)":', c_))
    dit(len(corps_signes) >= 2 and len(champs_rappel) >= 3
        and champs_rappel == proprietes(DOC, "EvenementRappel"),
        "EvenementRappel : les champs du contrat sont ceux du corps signe",
        f"{len(corps_signes)} corps, {sorted(champs_rappel)}")

    print("\n  ── les champs que les routes lisent ──")
    lus_demande = set()
    for fn in (S.lancer_pour_programme, S._nuage_du_programme, S.api_v1_rendre):
        lus_demande |= set(re.findall(r'\bd\.get\("([a-z_0-9]+)"', inspect.getsource(fn)))
    m_ = re.search(r"for nom_prog, nom_page in \((.*?)\):",
                   inspect.getsource(S.lancer_pour_programme), re.S)
    passes = set(re.findall(r'\("([a-z_]+)", "[a-z_]+"\)', m_.group(1))) if m_ else set()
    dit(len(passes) >= 4, "temoin : la table des noms passes a la page est lue",
        f"{sorted(passes)}")
    lus_demande |= passes
    dit(lus_demande == proprietes(DOC, "DemandeRendu"),
        "DemandeRendu : les champs du contrat sont ceux que POST /api/v1/rendus lit",
        f"en trop {sorted(proprietes(DOC, 'DemandeRendu') - lus_demande)}, "
        f"non decrits {sorted(lus_demande - proprietes(DOC, 'DemandeRendu'))}")
    lus_reponse = set(re.findall(r'\bd\.get\("([a-z_]+)"', inspect.getsource(S.api_v1_repondre)))
    dit(len(lus_reponse) >= 2 and lus_reponse == proprietes(DOC, "ReponseQuestion"),
        "ReponseQuestion : les champs du contrat sont ceux que la route lit",
        f"{sorted(lus_reponse)}")

    # ══════════════════════════════════════════════════════════════════
    print("\n  ── les bornes, recopiees de serveur.py ──")
    dit(C.ETATS == S.ETATS_PROGRAMME, "les etats du contrat sont ETATS_PROGRAMME",
        str(C.ETATS))
    enum_etat = DOC["components"]["schemas"]["Rendu"]["properties"]["etat"]["enum"]
    manque = [e for e in S.ETATS_PROGRAMME if e not in enum_etat]
    dit(not manque and len(enum_etat) == len(S.ETATS_PROGRAMME),
        "chaque etat de ETATS_PROGRAMME est dans l'enum du schema Rendu",
        ", ".join(manque) or f"{len(enum_etat)} etats")
    dit(set(C.ETATS_FINAUX) == set(S.ETATS_FINAUX), "les etats finaux sont les memes")
    dit(C.ATTENDRE_MAX == S.ATTENDRE_MAX, "ATTENDRE_MAX est celui de serveur.py",
        f"{C.ATTENDRE_MAX} contre {S.ATTENDRE_MAX}")
    dit(C.LISTE_MAX == S.LISTE_MAX, "LISTE_MAX est celui de serveur.py",
        f"{C.LISTE_MAX} contre {S.LISTE_MAX}")
    bornes = list(schemas_attendre(DOC))
    fausses = [c for c, s in bornes if s.get("maximum") != S.ATTENDRE_MAX
               or s.get("minimum") != 0]
    dit(len(bornes) >= 3 and not fausses,
        "chaque « attendre » du contrat est borne a ATTENDRE_MAX",
        ", ".join(fausses) or f"{len(bornes)} champs")
    dit(C.ATTENDRE_MCP == S.ATTENDRE_MCP, "ATTENDRE_MCP est celui de serveur.py")
    dit(C.LIEN_DUREE == S.LIEN_DUREE, "LIEN_DUREE est celui de serveur.py")
    dit((C.IDEMPOTENCE_DUREE, C.IDEMPOTENCE_LONGUEUR)
        == (S.IDEMPOTENCE_DUREE, S.IDEMPOTENCE_LONGUEUR),
        "l'idempotence a la meme duree et la meme longueur")
    entete_ = DOC["components"]["parameters"]["IdempotencyKey"]["schema"]
    dit(entete_.get("maxLength") == S.IDEMPOTENCE_LONGUEUR,
        "l'en-tete Idempotency-Key est borne a IDEMPOTENCE_LONGUEUR")
    dit(C.DEMANDE_MAX == S.DEMANDE_MAX and C.VARIANTES_MAX == S.VARIANTES_MAX
        and C.CORPS_MAX == S.CORPS_MAX,
        "DEMANDE_MAX, VARIANTES_MAX et CORPS_MAX sont ceux de serveur.py")
    dit(set(C.TAILLES) == set(S.TAILLES) and len(C.TAILLES) == len(S.TAILLES),
        "les tailles sont celles de serveur.py",
        f"{sorted(set(C.TAILLES) ^ set(S.TAILLES)) or 'egales'}")
    dit(tuple(C.PRIORITES) == tuple(p for p in S.PRIORITES if p),
        "les priorites sont celles de serveur.py")
    # Ce que la cle peut faire : les familles que le contrat annonce sont
    # celles qu'acces.py accepte, et la route qui peut les refuser dit son 403.
    ops_ = ((DOC["components"]["schemas"]["Cle"]["properties"].get("operations")
             or {}).get("items") or {}).get("enum")
    dit(ops_ == list(S._acces.OPERATIONS),
        "les familles d'« operations » sont celles d'acces.OPERATIONS, dans l'ordre",
        repr(ops_))
    types_ = ((DOC["components"]["schemas"]["DemandeRendu"]["properties"]
               .get("image_type") or {}).get("enum"))
    dit(types_ and sorted(types_) == sorted(S.TYPES_IMAGE),
        "« image_type » enumere exactement les types que serveur.py accepte",
        repr(types_))
    dit("403" in DOC["paths"]["/api/v1/rendus"]["post"]["responses"],
        "POST /api/v1/rendus annonce le 403 d'une operation que la cle ne permet pas")
    familles = set(S.FAMILLES) | {"objet3d", "autre"}
    dit(set(C.TYPES_FICHIER) == familles, "les types de fichier sont les familles de sortie",
        f"{sorted(familles)}")
    noms_outils = tuple(o["name"] for o in S.outils_mcp())
    dit(C.OUTILS_MCP == noms_outils, "les outils MCP sont ceux de outils_mcp()",
        ", ".join(noms_outils))
    desc_mcp = DOC["paths"]["/mcp"]["post"]["description"]
    absents_mcp = [n for n in noms_outils if n not in desc_mcp]
    dit(len(noms_outils) >= 5 and not absents_mcp,
        "chaque outil MCP est nomme dans la description de /mcp",
        ", ".join(absents_mcp) or "tous")

    # ══════════════════════════════════════════════════════════════════
    print("\n  ── le document ──")
    try:
        brut = json.dumps(DOC)
        pur = json.loads(brut) == DOC
    except (TypeError, ValueError) as e:
        brut, pur = "", False
        print(f"       {type(e).__name__}: {e}")
    dit(pur, "le document est du JSON pur (json.dumps, aller-retour egal)")
    dit(DOC.get("openapi", "").startswith("3.1"), "le document est un OpenAPI 3.1",
        DOC.get("openapi", "?"))
    refs = list(tous_les_refs(DOC))
    casses = sorted({r for r in refs if resoudre(DOC, r) is None})
    dit(len(refs) >= 20 and not casses, "chaque $ref se resout dans le document",
        ", ".join(casses) or f"{len(refs)} refs")
    ids = [op.get("operationId") for item in DOC["paths"].values() for op in item.values()]
    dit(all(ids) and len(set(ids)) == len(ids), "chaque operation a un operationId unique",
        f"{len(ids)} operations")
    dit(DOC.get("servers") == [{"url": BASE, "description": "ce studio"}],
        "l'adresse du studio est reprise dans servers", str(DOC.get("servers")))
    dit("servers" not in C.document(""), "sans adresse, le document n'en invente pas")
    DOC["paths"].clear()
    dit(bool(C.document(BASE)["paths"]), "un document neuf a chaque appel")
    evenements = (C.document()["webhooks"]["rendu"]["post"]["requestBody"]["content"]
                  ["application/json"]["schema"])
    dit(resoudre(C.document(), evenements.get("$ref", "")) is not None,
        "le rappel est decrit comme un webhook OpenAPI 3.1")
    # LA POLITIQUE D'ESSAIS DECRITE EST CELLE DE rappels.py : un integrateur
    # qui lit « 409 arrete les essais » croirait perdu le rappel que n8n
    # refuse parce que son execution n'a pas encore atteint le Wait.
    import rappels as _R
    # LA LISTE QUI SUIT « réessayé sur », et non tout le texte : la phrase
    # qui explique le 409 de n8n le nomme aussi, et masquait une liste fausse.
    _desc = C.document()["webhooks"]["rendu"]["post"]["description"]
    _liste = re.search(r"réessayé sur ((?:\d{3}, )+)5xx", _desc)
    _lus = [int(x) for x in re.findall(r"\d{3}", _liste.group(1))] if _liste else []
    dit(409 in _R._PASSAGERS and _lus == list(_R._PASSAGERS),
        "la description du rappel nomme chaque statut re-essaye, 409 compris",
        f"lus {_lus}, attendus {list(_R._PASSAGERS)}")
finally:
    shutil.rmtree(DONNEES, ignore_errors=True)

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
for x in rate:
    print("    NON :", x)
sys.exit(1 if rate else 0)
