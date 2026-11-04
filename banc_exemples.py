#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Les deux workflows n8n du depot, confrontes au contrat qu'ils appellent.

exemples/n8n-rendu-comfystudio.json et exemples/n8n-rappel-comfystudio.json
sont ce qu'un humain importe tel quel dans n8n. Un exemple faux est pire
qu'un exemple absent : il est COPIE. Une route renommee, un etat oublie, un
429 reessaye pour toujours, et c'est cent workflows qui heritent de la faute
sans que personne ne relise le JSON — n8n ne le montre que noeud par noeud.

Ce banc ne recopie rien du studio : les routes, les methodes, les champs des
corps, les parametres, l'enum des etats et des evenements, les etats finaux
viennent de contrat.py (document() et ses constantes), que banc_contrat.py
confronte lui-meme au routeur. Un contrat qui change fait donc rougir ici les
exemples qui ne suivent pas.

CE QU'IL GARDE, DANS L'ORDRE DES DEGATS :

  1. LA CLE. Aucune cle « cs_ » ni secret dans les fichiers ; chaque noeud HTTP
     passe par le credential « ComfyStudio », nomme et rien d'autre ; aucun
     Authorization pose a la main ; et la cle ne part QUE vers le studio — une
     URL lue dans un corps de rappel non verifie ferait partir l'en-tete vers
     qui l'a ecrite.
  2. LE DOUBLE RENDU. Chaque POST /api/v1/rendus porte Idempotency-Key, sur
     l'identifiant de l'execution : n8n reessaie, et chaque essai sans elle
     etait un rendu de plus.
  3. LES BOUCLES. Toute boucle (relecture, reessai) passe par un If borne sur
     $runIndex ; un 429 sans « reessayer_dans » n'est pas reessaye — le
     studio l'omet exactement quand attendre ne servirait a rien.
  4. LE CONTRAT. Chaque URL est une route decrite, avec sa methode ; chaque
     champ du corps, chaque parametre est decrit ; chaque champ LU dans une
     expression ($json.body.etat…) existe dans ce que cette route rend — y
     compris la difference entre une reponse complete (statusCode, body) et
     le corps seul, la faute la plus commune d'un workflow n8n.
  5. LES ETATS ET LES EVENEMENTS. Chaque etat compare est dans l'enum, chaque
     etat final a sa branche ; le Switch du rappel traite les evenements que
     le studio envoie, et rien qu'il n'envoie pas.
  6. LE TIMEOUT. Il depasse « attendre », sinon n8n coupe avant la reponse.
  7. LE GRAPHE. Types n8n connus, connexions vers des noeuds qui existent,
     tout noeud atteignable depuis le declencheur.

    python banc_exemples.py

CE QU'IL NE VOIT PAS :

  - n8n lui-meme : aucun n8n ne joue ces fichiers ici. Les types et versions
    sont ceux que n8n exporte (table TYPES), pas ceux qu'il accepterait.
  - La semantique fine des expressions : il releve les « $json.<chemin> » et
    « $('Noeud').first().json.<chemin> », pas le JavaScript autour.
  - La signature du rappel : l'exemple ne la verifie pas (la doc donne la
    recette du noeud Code), il se garde seulement d'en avoir besoin pour la
    cle.
"""
import json
import os
import re
import sys

for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
# contrat.py n'importe que acces, mcp et rappels, tous sans dependance : ce
# banc tourne sans aiohttp, comme le studio sur un NAS sans pip.
import contrat as C  # noqa: E402

ok, rate = [], []


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


EXEMPLES = (("rendu", "exemples/n8n-rendu-comfystudio.json"),
            ("rappel", "exemples/n8n-rappel-comfystudio.json"))
BASE = "http://STUDIO:8199"
CREDENTIAL = "ComfyStudio"

# Les types que ces exemples ont le droit d'employer, avec la version que n8n
# exporte. Un type mal orthographie s'importe en « noeud inconnu » sans un
# mot : on ne laisse passer que ce qu'on sait exister.
TYPES = {"n8n-nodes-base.httpRequest": 4.2, "n8n-nodes-base.if": 2,
         "n8n-nodes-base.switch": 3, "n8n-nodes-base.wait": 1.1,
         "n8n-nodes-base.stickyNote": 1, "n8n-nodes-base.manualTrigger": 1,
         "n8n-nodes-base.noOp": 1, "n8n-nodes-base.stopAndError": 1}
# Ce qui laisse passer son entree telle quelle : $json y est celui d'avant.
PASSANTS = {"n8n-nodes-base.if", "n8n-nodes-base.switch",
            "n8n-nodes-base.noOp", "n8n-nodes-base.stopAndError"}

DOC = C.document(BASE)


# ── le contrat ─────────────────────────────────────────────────────────
def resoudre(noeud):
    """Suit les $ref jusqu'au schema (ou la reponse) qu'ils designent."""
    vus = 0
    while isinstance(noeud, dict) and "$ref" in noeud and vus < 20:
        cible = DOC
        for morceau in noeud["$ref"][2:].split("/"):
            cible = (cible or {}).get(morceau) if isinstance(cible, dict) else None
        noeud, vus = cible, vus + 1
    return noeud


def parametres_de(op):
    return [resoudre(p) or {} for p in op.get("parameters", [])]


def schemas_rendus(op, deux_cents_seulement):
    """Les schemas JSON que l'operation peut rendre."""
    lus = []
    for statut, rep in sorted(op.get("responses", {}).items()):
        if deux_cents_seulement and not statut.startswith("2"):
            continue
        schema = ((resoudre(rep) or {}).get("content", {})
                  .get("application/json", {}).get("schema"))
        if schema is not None:
            lus.append(schema)
    return lus


ENUM_ETATS = set(DOC["components"]["schemas"]["Rendu"]["properties"]["etat"]["enum"])
ENUM_EVENEMENTS = set(DOC["components"]["schemas"]["EvenementRappel"]
                      ["properties"]["evenement"]["enum"])
OBJET_VIDE = {"type": "object", "properties": {}}
LIBRE = {}           # schema vide : tout chemin y est accepte (en-tetes…)


def chemin_accepte(schema, segments):
    """Vrai si « segments » se lit dans un objet de ce schema."""
    schema = resoudre(schema)
    if not segments:
        return True
    if not isinstance(schema, dict):
        return False
    if "anyOf" in schema:
        return any(chemin_accepte(s, segments) for s in schema["anyOf"])
    if schema == LIBRE:
        return True
    tete, reste = segments[0], segments[1:]
    types = schema.get("type")
    types = types if isinstance(types, list) else [types]
    if "array" in types:
        if tete == "length":
            return not reste
        if tete.startswith("["):
            return chemin_accepte(schema.get("items", LIBRE), reste)
        return False
    proprietes = schema.get("properties")
    if isinstance(proprietes, dict) and tete in proprietes:
        return chemin_accepte(proprietes[tete], reste)
    return False


# ── le workflow ────────────────────────────────────────────────────────
def chaines(valeur):
    if isinstance(valeur, str):
        yield valeur
    elif isinstance(valeur, dict):
        for v in valeur.values():
            yield from chaines(v)
    elif isinstance(valeur, list):
        for v in valeur:
            yield from chaines(v)


RE_JSON = re.compile(r"\$json((?:\.[A-Za-z_]\w*|\[\d+\])+)")
RE_AUTRE = re.compile(r"\$\(\s*'([^']+)'\s*\)\.(?:item|first\(\)|last\(\))\.json"
                      r"((?:\.[A-Za-z_]\w*|\[\d+\])+)")


def segments_de(chemin):
    return re.findall(r"[A-Za-z_]\w*|\[\d+\]", chemin)


class Flux:
    """Un workflow lu : noeuds par nom, sorties, entrees."""

    def __init__(self, doc):
        self.doc = doc
        self.noeuds = {n.get("name"): n for n in doc.get("nodes", [])}
        self.sorties = {}
        for source, branches in (doc.get("connections") or {}).items():
            self.sorties[source] = [[c.get("node") for c in (b or [])]
                                    for b in (branches or {}).get("main", [])]
        self.entrees = {}
        for source, branches in self.sorties.items():
            for b in branches:
                for cible in b:
                    self.entrees.setdefault(cible, []).append(source)
        self._entree = {}

    def utiles(self):
        return [n for n in self.noeuds.values()
                if n.get("type") != "n8n-nodes-base.stickyNote"]

    def sortie(self, nom, index):
        b = self.sorties.get(nom, [])
        return b[index] if index < len(b) else []

    def atteints(self, depart, index=None, sans=()):
        """Les noeuds atteints depuis « depart » (une de ses sorties, ou toutes)."""
        if index is None:
            pile = [c for b in self.sorties.get(depart, []) for c in b]
        else:
            pile = list(self.sortie(depart, index))
        vus = set()
        while pile:
            nom = pile.pop()
            if nom in vus or nom in sans:
                continue
            vus.add(nom)
            pile.extend(c for b in self.sorties.get(nom, []) for c in b)
        return vus

    # ce que $json est, a l'entree d'un noeud
    def sortie_de(self, nom):
        n = self.noeuds.get(nom) or {}
        type_, p = n.get("type"), n.get("parameters") or {}
        if type_ == "n8n-nodes-base.httpRequest":
            op = operation_de(n)[1]
            reponse = ((p.get("options") or {}).get("response") or {}).get("response") or {}
            if reponse.get("responseFormat") == "file" or op is None:
                return OBJET_VIDE
            if reponse.get("fullResponse"):
                return {"type": "object", "properties": {
                    "statusCode": {"type": "integer"},
                    "statusMessage": {"type": "string"}, "headers": LIBRE,
                    "body": {"anyOf": schemas_rendus(op, False)}}}
            return {"anyOf": schemas_rendus(op, True)}
        if type_ == "n8n-nodes-base.wait":
            if p.get("resume") == "webhook":
                # Reveille par le rappel : le corps du studio dans « body ».
                # Reveille par le delai : l'entree, telle quelle.
                return {"anyOf": [{"type": "object", "properties": {
                    "headers": LIBRE, "params": LIBRE, "query": LIBRE,
                    "body": {"$ref": "#/components/schemas/EvenementRappel"}}},
                    self.entree_de(nom)]}
            return self.entree_de(nom)
        if type_ in PASSANTS:
            return self.entree_de(nom)
        return OBJET_VIDE

    def entree_de(self, nom):
        if nom in self._entree:
            return self._entree[nom]
        # En cours de calcul : une boucle de passants ne rend rien de plus
        # que ce que ses autres entrees apportent.
        self._entree[nom] = {"anyOf": []}
        formes = [self.sortie_de(p) for p in self.entrees.get(nom, [])]
        self._entree[nom] = {"anyOf": formes}
        return self._entree[nom]

    def ancetres_http(self, nom):
        """Les noeuds HTTP dont la reponse arrive ici, a travers les passants."""
        vus, pile, trouves = set(), list(self.entrees.get(nom, [])), []
        while pile:
            p = pile.pop()
            if p in vus:
                continue
            vus.add(p)
            t = (self.noeuds.get(p) or {}).get("type")
            if t == "n8n-nodes-base.httpRequest":
                trouves.append(p)
            elif t in PASSANTS or t == "n8n-nodes-base.wait":
                pile.extend(self.entrees.get(p, []))
        return trouves


def operation_de(n):
    """(gabarit, operation, requete) de l'URL d'un noeud HTTP, ou (None, None, raison)."""
    p = n.get("parameters") or {}
    url = p.get("url") or ""
    url = url[1:] if url.startswith("=") else url
    if not url.startswith(BASE + "/"):
        return None, None, "hors de " + BASE
    chemin, _, requete = url[len(BASE):].partition("?")
    segs = chemin.split("/")
    methode = (p.get("method") or "GET").lower()
    for gabarit, item in DOC["paths"].items():
        gs = gabarit.split("/")
        if len(gs) != len(segs):
            continue
        bon = True
        for g, s in zip(gs, segs):
            expression = bool(re.fullmatch(r"\{\{.*\}\}", s))
            if g.startswith("{"):
                bon = bon and bool(s)
            else:
                bon = bon and not expression and s == g
        if bon:
            return gabarit, item.get(methode), requete
    return None, None, "aucun chemin du contrat"


def http_noeuds(flux):
    return [n for n in flux.utiles() if n.get("type") == "n8n-nodes-base.httpRequest"]


def reponse_options(n):
    return (((n.get("parameters") or {}).get("options") or {}).get("response") or {}) \
        .get("response") or {}


def corps_envoye(n):
    brut = (n.get("parameters") or {}).get("jsonBody")
    if brut is None:
        return None
    texte = brut[1:] if brut.startswith("=") else brut
    return json.loads(re.sub(r"\{\{.*?\}\}", "EXPR", texte))


def paires(n, cle):
    return [(x.get("name"), x.get("value"))
            for x in ((n.get("parameters") or {}).get(cle) or {}).get("parameters", [])]


def conditions_de(n):
    p = n.get("parameters") or {}
    if n.get("type") == "n8n-nodes-base.if":
        return [(0, c) for c in (p.get("conditions") or {}).get("conditions", [])]
    if n.get("type") == "n8n-nodes-base.switch":
        return [(i, c) for i, r in enumerate((p.get("rules") or {}).get("values", []))
                for c in (r.get("conditions") or {}).get("conditions", [])]
    return []


def regles(n):
    return ((n.get("parameters") or {}).get("rules") or {}).get("values", [])


def switchs_sur(flux, motif):
    return [n for n in flux.utiles() if n.get("type") == "n8n-nodes-base.switch"
            and any(re.search(motif, str(c.get("leftValue", "")))
                    for _, c in conditions_de(n))]


def valeurs_par_sortie(n, motif):
    """{index de sortie: [valeurs comparees]} d'un Switch, pour ce motif."""
    lus = {}
    for i, c in conditions_de(n):
        if re.search(motif, str(c.get("leftValue", ""))):
            lus.setdefault(i, []).append(c.get("rightValue"))
    return lus


def est_borne(n):
    return n.get("type") == "n8n-nodes-base.if" and any(
        "$runIndex" in str(c.get("leftValue", ""))
        and (c.get("operator") or {}).get("operation") in ("lt", "lte")
        and isinstance(c.get("rightValue"), int) and 0 < c["rightValue"] <= 20
        for _, c in conditions_de(n))


def cycle(flux):
    """Un cycle qui ne passe par la sortie « vrai » d'aucune borne, ou None."""
    def suivants(nom):
        n = flux.noeuds.get(nom) or {}
        for i, b in enumerate(flux.sorties.get(nom, [])):
            if i == 0 and est_borne(n):
                continue
            yield from b
    couleur = {}

    def visiter(nom, pile):
        couleur[nom] = 1
        for s in suivants(nom):
            if couleur.get(s) == 1:
                return pile + [nom, s]
            if not couleur.get(s):
                trouve = visiter(s, pile + [nom])
                if trouve:
                    return trouve
        couleur[nom] = 2
        return None
    for nom in flux.noeuds:
        if not couleur.get(nom):
            trouve = visiter(nom, [])
            if trouve:
                return trouve
    return None


FLUX = {}
TEXTES = {}
print("\n  ── les fichiers ──")
for cle, rel in EXEMPLES:
    chemin = os.path.join(ICI, *rel.split("/"))
    try:
        with open(chemin, encoding="utf-8") as f:
            TEXTES[cle] = f.read()
        doc = json.loads(TEXTES[cle])
        lisible = isinstance(doc.get("nodes"), list) and isinstance(doc.get("connections"), dict)
    except (OSError, ValueError, AttributeError) as e:
        doc, lisible = None, False
        print(f"       {type(e).__name__}: {e}")
    dit(lisible, f"[{cle}] {rel} se lit : du JSON avec nodes et connections")
    if lisible:
        FLUX[cle] = Flux(doc)

for cle, flux in FLUX.items():
    print(f"\n  ── [{cle}] le graphe ──")
    inconnus = sorted(f"{n.get('name')} : {n.get('type')} v{n.get('typeVersion')}"
                      for n in flux.doc["nodes"]
                      if TYPES.get(n.get("type")) != n.get("typeVersion"))
    dit(not inconnus, f"[{cle}] chaque noeud a un type n8n connu, a sa version",
        ", ".join(inconnus) or f"{len(flux.doc['nodes'])} noeuds")
    noms = [n.get("name") for n in flux.doc["nodes"]]
    ids = [n.get("id") for n in flux.doc["nodes"]]
    dit(len(set(noms)) == len(noms) and len(set(ids)) == len(ids) and all(ids),
        f"[{cle}] noms et identifiants de noeud uniques")
    # n8n relie les noeuds PAR LEUR NOM : un noeud renomme d'un cote seulement
    # laisse une fleche vers rien, que l'import avale sans un mot.
    orphelins = sorted({s for s in flux.sorties if s not in flux.noeuds}
                       | {c for b in flux.sorties.values() for x in b for c in x
                          if c not in flux.noeuds})
    dit(not orphelins, f"[{cle}] chaque connexion relie des noeuds qui existent",
        ", ".join(orphelins) or "toutes")
    declencheurs = [n["name"] for n in flux.utiles() if n.get("type", "").endswith("Trigger")]
    atteints = set(declencheurs)
    for d in declencheurs:
        atteints |= flux.atteints(d)
    perdus = sorted(n["name"] for n in flux.utiles() if n["name"] not in atteints)
    dit(len(declencheurs) == 1 and not perdus,
        f"[{cle}] tout noeud est atteignable depuis le declencheur",
        ", ".join(perdus) or f"declencheur {declencheurs}")
    boucle = cycle(flux)
    dit(boucle is None, f"[{cle}] chaque boucle passe par un If borne sur $runIndex",
        " -> ".join(boucle) if boucle else "aucune boucle libre")
    # Sans « = » en tete, n8n envoie « {{ $execution.id }} » en toutes lettres :
    # chaque execution aurait la MEME Idempotency-Key, et la seconde rendrait
    # le rendu de la premiere.
    nues = sorted({n["name"] for n in flux.utiles() for s in chaines(n.get("parameters"))
                   if "{{" in s and not s.startswith("=")})
    dit(not nues, f"[{cle}] chaque expression est dans un champ qui commence par « = »",
        ", ".join(nues) or "toutes")

for cle, flux in FLUX.items():
    print(f"\n  ── [{cle}] la cle d'acces ──")
    texte = TEXTES[cle]
    # La forme d'une cle (cs_ puis lettres) ou d'un secret de rappel (43
    # caracteres base64url) : un exemple qui en porte une, meme « pour
    # l'essai », la publie avec le depot.
    fuites = re.findall(r"cs_[0-9A-Za-z]", texte) + re.findall(r"[A-Za-z0-9_-]{40,}", texte)
    dit(not fuites, f"[{cle}] aucune cle d'acces ni secret dans le fichier",
        ", ".join(f[:16] + "…" for f in fuites) or "aucun")
    mauvais = []
    for n in http_noeuds(flux):
        p = n.get("parameters") or {}
        if (p.get("authentication"), p.get("genericAuthType")) != (
                "genericCredentialType", "httpHeaderAuth") \
                or n.get("credentials") != {"httpHeaderAuth": {"name": CREDENTIAL}}:
            mauvais.append(n["name"])
    dit(http_noeuds(flux) and not mauvais,
        f"[{cle}] chaque noeud HTTP passe par le credential « {CREDENTIAL} », nomme et rien d'autre",
        ", ".join(mauvais) or f"{len(http_noeuds(flux))} noeuds")
    a_la_main = [n["name"] for n in http_noeuds(flux)
                 if any((k or "").lower() == "authorization" for k, _ in paires(n, "headerParameters"))]
    dit(not a_la_main, f"[{cle}] aucun en-tete Authorization pose a la main",
        ", ".join(a_la_main) or "aucun")
    # L'HOTE EST ECRIT, JAMAIS LU. Le credential pose la cle sur toute
    # requete du noeud : une URL tiree d'un corps de rappel (que l'exemple ne
    # verifie pas) enverrait la cle a qui a forge ce corps.
    ailleurs = [n["name"] for n in http_noeuds(flux)
                if not (n.get("parameters") or {}).get("url", "").lstrip("=").startswith(BASE + "/api/v1/")]
    dit(not ailleurs, f"[{cle}] la cle ne part que vers {BASE}/api/v1/, ecrit en toutes lettres",
        ", ".join(ailleurs) or "tous")

for cle, flux in FLUX.items():
    print(f"\n  ── [{cle}] le contrat ──")
    hors, params_faux, champs_faux, bornes, courts = [], [], [], [], []
    for n in http_noeuds(flux):
        p = n.get("parameters") or {}
        gabarit, op, requete = operation_de(n)
        if op is None:
            hors.append(f"{(p.get('method') or 'GET')} {p.get('url')} ({requete if gabarit is None else 'methode absente du contrat'})")
            continue
        decrits = {(x.get("in"), x.get("name")) for x in parametres_de(op)}
        envoyes = [("query", k) for k, _ in paires(n, "queryParameters")]
        envoyes += [("query", k.split("=")[0]) for k in requete.split("&") if k]
        envoyes += [("header", k) for k, _ in paires(n, "headerParameters")]
        params_faux += [f"{n['name']} : {ou} {k}" for ou, k in envoyes if (ou, k) not in decrits]
        attendre = None
        for k, v in paires(n, "queryParameters"):
            if k == "attendre":
                attendre = int(v)
        try:
            corps = corps_envoye(n)
        except ValueError as e:
            champs_faux.append(f"{n['name']} : corps illisible ({e})")
            corps = None
        if corps is not None:
            schema = resoudre(op.get("requestBody", {}).get("content", {})
                              .get("application/json", {}).get("schema")) or {}
            props = schema.get("properties", {})
            for k, v in corps.items():
                attendu = (props.get(k) or {}).get("type")
                bon_type = {"string": isinstance(v, str), "boolean": isinstance(v, bool),
                            "integer": isinstance(v, int) and not isinstance(v, bool)
                            }.get(attendu, k in props)
                if k not in props or not bon_type:
                    champs_faux.append(f"{n['name']} : {k}={v!r}")
            if isinstance(corps.get("attendre"), int):
                attendre = corps["attendre"]
        if attendre is not None:
            if not 0 <= attendre <= C.ATTENDRE_MAX:
                bornes.append(f"{n['name']} : {attendre}")
            # DIX SECONDES DE MARGE : le studio rend la main a « attendre »
            # pile, puis compose la reponse ; un timeout egal coupe sur la
            # derniere seconde le rendu qu'on a attendu cinq minutes.
            delai = (p.get("options") or {}).get("timeout") or 300000
            if not (isinstance(delai, int) and delai >= attendre * 1000 + 10000):
                courts.append(f"{n['name']} : timeout {delai} ms pour attendre={attendre}")
    dit(http_noeuds(flux) and not hors,
        f"[{cle}] chaque URL appelee est une route du contrat, avec sa methode",
        ", ".join(hors) or f"{len(http_noeuds(flux))} appels")
    dit(not params_faux, f"[{cle}] chaque parametre de requete et d'en-tete est decrit par l'operation",
        ", ".join(params_faux) or "tous")
    dit(not champs_faux, f"[{cle}] chaque champ du corps envoye existe dans le schema de la requete",
        ", ".join(champs_faux) or "tous")
    dit(not bornes, f"[{cle}] chaque « attendre » est dans les bornes du contrat (0 a {C.ATTENDRE_MAX})",
        ", ".join(bornes) or "tous")
    dit(not courts, f"[{cle}] le timeout n8n depasse « attendre » d'au moins 10 s",
        ", ".join(courts) or "tous")

    # LES CHAMPS LUS. « $json.etat » derriere un noeud regle sur la reponse
    # complete ne vaut rien (il faut « $json.body.etat ») : n8n n'y voit
    # aucune faute, le Switch tombe dans le repli a chaque execution.
    lus_faux, lus = [], 0
    for n in flux.utiles():
        if n.get("type") == "n8n-nodes-base.stickyNote":
            continue
        entree = flux.entree_de(n["name"])
        for s in chaines(n.get("parameters")):
            for chemin in RE_JSON.findall(s):
                lus += 1
                if not chemin_accepte(entree, segments_de(chemin)):
                    lus_faux.append(f"{n['name']} : $json{chemin}")
            for autre, chemin in RE_AUTRE.findall(s):
                lus += 1
                if autre not in flux.noeuds or not chemin_accepte(
                        flux.sortie_de(autre), segments_de(chemin)):
                    lus_faux.append(f"{n['name']} : $('{autre}').json{chemin}")
    dit(lus >= 5 and not lus_faux,
        f"[{cle}] chaque champ lu dans une expression existe dans ce que le studio rend",
        ", ".join(lus_faux) or f"{lus} lectures")

    posts = [n for n in http_noeuds(flux) if operation_de(n)[:1] == ("/api/v1/rendus",)
             and (n.get("parameters") or {}).get("method") == "POST"]
    sans_cle = [n["name"] for n in posts
                if not any(k == "Idempotency-Key" and "$execution.id" in str(v)
                           for k, v in paires(n, "headerParameters"))]
    dit(len(posts) == 1 and not sans_cle,
        f"[{cle}] l'Idempotency-Key est posee sur le POST /api/v1/rendus, sur $execution.id",
        ", ".join(sans_cle) or f"{len(posts)} POST")

    print(f"\n  ── [{cle}] les etats ──")
    MOTIF_ETAT = r"\$json(?:\.body)?\.etat\b"
    inconnus = sorted({f"{n['name']} : {c.get('rightValue')!r}" for n in flux.utiles()
                       for _, c in conditions_de(n)
                       if re.search(MOTIF_ETAT, str(c.get("leftValue", "")))
                       and c.get("rightValue") not in ENUM_ETATS})
    dit(not inconnus, f"[{cle}] chaque etat compare existe dans l'enum du contrat",
        ", ".join(inconnus) or "tous")
    aiguillages = switchs_sur(flux, MOTIF_ETAT)
    manques = []
    for n in aiguillages:
        par_sortie = valeurs_par_sortie(n, MOTIF_ETAT)
        for e in C.ETATS_FINAUX:
            sorties_ = [i for i, vs in par_sortie.items() if e in vs]
            if not sorties_ or not all(flux.sortie(n["name"], i) for i in sorties_):
                manques.append(f"{n['name']} : {e}")
    dit(aiguillages and not manques,
        f"[{cle}] chaque etat final du contrat a sa branche dans l'aiguillage",
        ", ".join(manques) or f"{len(aiguillages)} aiguillage(s), {', '.join(C.ETATS_FINAUX)}")

    def telechargements(depuis_noeud, index):
        return [x for x in flux.atteints(depuis_noeud, index)
                if (flux.noeuds[x].get("type") == "n8n-nodes-base.httpRequest"
                    and operation_de(flux.noeuds[x])[0] == "/api/v1/rendus/{tid}/fichiers/{rang}"
                    and reponse_options(flux.noeuds[x]).get("responseFormat") == "file")]
    sans_fichier = []
    for n in aiguillages:
        for i, vs in valeurs_par_sortie(n, MOTIF_ETAT).items():
            if "fini" in vs and not telechargements(n["name"], i):
                sans_fichier.append(n["name"])
    dit(aiguillages and not sans_fichier,
        f"[{cle}] « fini » mene au telechargement d'un fichier, en binaire",
        ", ".join(sans_fichier) or "oui")

    def relectures(depuis_noeud, index):
        return [x for x in flux.atteints(depuis_noeud, index)
                if flux.noeuds[x].get("type") == "n8n-nodes-base.httpRequest"
                and operation_de(flux.noeuds[x])[0] == "/api/v1/rendus/{tid}"
                and (flux.noeuds[x].get("parameters") or {}).get("method", "GET") == "GET"]

    if cle == "rendu":
        # Le repli est l'index qui suit la derniere regle : en_file, en_cours,
        # attente_machine — et tout etat que le contrat ajouterait sans etre
        # final.
        sondes = []
        for n in aiguillages:
            for x in relectures(n["name"], len(regles(n))):
                att = dict(paires(flux.noeuds[x], "queryParameters")).get("attendre")
                if att and int(att) > 0 and n["name"] in flux.atteints(x):
                    sondes.append(x)
        dit(aiguillages and sondes,
            f"[{cle}] un etat non final relit GET /api/v1/rendus/{{tid}} avec attendre, puis revient a l'aiguillage",
            ", ".join(sondes) or "aucune relecture")

        print(f"\n  ── [{cle}] les refus et le 429 ──")
        post = posts[0] if posts else {"name": "?"}
        op_post = DOC["paths"]["/api/v1/rendus"]["post"]
        statuts = switchs_sur(flux, r"\$json\.statusCode\b")
        deux_cents = {int(s) for s in op_post["responses"] if s.startswith("2")}
        vers_aiguillage = [n["name"] for n in statuts
                           for i, vs in valeurs_par_sortie(n, r"\$json\.statusCode\b").items()
                           if set(vs) == deux_cents
                           and any(a["name"] in flux.atteints(n["name"], i) for a in aiguillages)]
        dit(vers_aiguillage,
            f"[{cle}] les statuts 2xx du contrat ({', '.join(map(str, sorted(deux_cents)))}) menent a l'aiguillage",
            ", ".join(vers_aiguillage) or "aucune regle")
        # SANS « Never Error », n8n leve sur le 429 avant que le Switch ne le
        # voie : la branche du 429 existe, et n'est jamais prise.
        lecteurs = [h for n in statuts for h in flux.ancetres_http(n["name"])]
        sourds = [h for h in lecteurs
                  if not (reponse_options(flux.noeuds[h]).get("neverError")
                          and reponse_options(flux.noeuds[h]).get("fullResponse"))]
        dit(statuts and lecteurs and not sourds,
            f"[{cle}] le statut est lu sur un POST regle Never Error et reponse complete",
            ", ".join(sourds) or ", ".join(lecteurs) or "aucun")
        sorties_429 = [(n["name"], i) for n in statuts
                       for i, vs in valeurs_par_sortie(n, r"\$json\.statusCode\b").items()
                       if 429 in vs]
        gardes = [c_ for s, i in sorties_429 for c_ in flux.sortie(s, i)]

        def garde_reessai(nom):
            n = flux.noeuds.get(nom) or {}
            return n.get("type") == "n8n-nodes-base.if" and any(
                "reessayer_dans" in str(c.get("leftValue", ""))
                and (c.get("operator") or {}).get("operation") == "exists"
                for _, c in conditions_de(n))
        dit("429" in op_post["responses"] and sorties_429 and gardes
            and all(garde_reessai(g) and post["name"] not in flux.atteints(g, 1)
                    for g in gardes),
            f"[{cle}] un 429 sans reessayer_dans n'est pas reessaye",
            f"sorties 429 {sorties_429}, gardes {gardes}")
        attentes = [g for g in gardes for w in flux.atteints(g, 0)
                    if flux.noeuds[w].get("type") == "n8n-nodes-base.wait"
                    and "reessayer_dans" in str((flux.noeuds[w].get("parameters") or {}).get("amount"))
                    and post["name"] in flux.atteints(w)]
        dit(gardes and len(set(attentes)) == len(gardes),
            f"[{cle}] un 429 avec reessayer_dans attend ce delai, puis redemande",
            ", ".join(attentes) or "aucune attente")
        replis = [n["name"] for n in statuts
                  if post["name"] in flux.atteints(n["name"], len(regles(n)))
                  or not flux.sortie(n["name"], len(regles(n)))]
        dit(statuts and not replis,
            f"[{cle}] tout autre refus s'arrete sans redemander : « code » dit pourquoi",
            ", ".join(replis) or "oui")

    if cle == "rappel":
        print(f"\n  ── [{cle}] le rappel ──")
        post = posts[0] if posts else {"name": "?", "parameters": {}}
        try:
            corps = corps_envoye(post) or {}
        except ValueError:
            corps = {}
        brut = str((post.get("parameters") or {}).get("jsonBody"))
        dit("rappel" in corps and re.search(r'"rappel"\s*:\s*"\{\{\s*\$execution\.resumeUrl\s*\}\}"', brut)
            and not corps.get("attendre"),
            f"[{cle}] le POST porte rappel = $execution.resumeUrl, et n'attend pas",
            str(corps))
        attentes = [n for n in flux.utiles() if n.get("type") == "n8n-nodes-base.wait"
                    and (n.get("parameters") or {}).get("resume") == "webhook"]
        pw = (attentes[0].get("parameters") or {}) if attentes else {}
        dit(len(attentes) == 1 and attentes[0]["name"] in flux.atteints(post["name"])
            and pw.get("httpMethod") == "POST",
            f"[{cle}] un Wait « On Webhook Call » en POST suit le POST",
            ", ".join(a["name"] for a in attentes) or "aucun")
        # UNE LIMITE, parce qu'un rappel peut se perdre (quatre essais, puis
        # rien) : sans elle, l'execution dort pour toujours.
        dit(pw.get("limitWaitTime") is True and pw.get("limitType") == "afterTimeInterval"
            and int(pw.get("resumeAmount") or 0) > 0,
            f"[{cle}] le Wait a une limite d'attente",
            f"limitWaitTime={pw.get('limitWaitTime')}, {pw.get('resumeAmount')} {pw.get('resumeUnit')}")
        MOTIF_EV = r"\$json\.body\.evenement\b"
        aiguilles_ev = switchs_sur(flux, MOTIF_EV)
        lus_ev = {v for n in aiguilles_ev for vs in valeurs_par_sortie(n, MOTIF_EV).values() for v in vs}
        # CE QUE LE STUDIO ENVOIE : « rendu.<etat> » pour chaque etat final,
        # lu dans serveur.py tel qu'il le construit, plus « rappel.essai ».
        try:
            source = open(os.path.join(ICI, "serveur.py"), encoding="utf-8").read()
        except OSError:
            source = ""
        construit = re.search(r'evenement\s*=\s*f"rendu\.\{[^}]*\[\s*[\'"]etat[\'"]\s*\]\s*\}"', source)
        envoyes = {"rendu." + e for e in C.ETATS_FINAUX}
        dit(construit is not None and envoyes <= ENUM_EVENEMENTS,
            "temoin : le studio nomme ses evenements « rendu.<etat final> », tous dans l'enum du contrat",
            ", ".join(sorted(envoyes - ENUM_EVENEMENTS)) or ("construit dans serveur.py"
                                                             if construit else "construction introuvable"))
        dit(aiguilles_ev and lus_ev and lus_ev <= ENUM_EVENEMENTS,
            f"[{cle}] les evenements du Switch sont ceux que le studio envoie",
            ", ".join(sorted(lus_ev - ENUM_EVENEMENTS)) or ", ".join(sorted(lus_ev)))
        sans_branche = []
        for e in sorted(envoyes):
            if not any(flux.sortie(n["name"], i) for n in aiguilles_ev
                       for i, vs in valeurs_par_sortie(n, MOTIF_EV).items() if e in vs):
                sans_branche.append(e)
        dit(aiguilles_ev and not sans_branche,
            f"[{cle}] chaque evenement de fin a sa branche",
            ", ".join(sans_branche) or "tous")
        reveils = [x for n in aiguilles_ev for x in relectures(n["name"], len(regles(n)))]
        dit(aiguilles_ev and reveils,
            f"[{cle}] reveille par le delai, il relit GET /api/v1/rendus/{{tid}}",
            ", ".join(reveils) or "aucune relecture")

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
for x in rate:
    print("    NON :", x)
sys.exit(1 if rate else 0)
