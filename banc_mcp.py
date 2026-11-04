#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""La couche MCP du studio, message par message, contre la spec.

CE QUE CE BANC GARDE, DANS L'ORDRE DES DEGATS :

  1. LE TEXTE D'UNE EXCEPTION NE SORT PAS. Un outil qui leve une ValueError
     portant un chemin du NAS ou un nom de machine : la reponse ne doit rien en
     contenir, nulle part dans le JSON serialise — elle sort du reseau local et
     finit dans le contexte d'un modele. La trace, elle, doit arriver au
     journal : un echec muet des deux cotes ne se diagnostique plus.
  2. UNE NOTIFICATION NE LANCE RIEN. Un tools/call sans « id » ne doit ni
     executer l'outil ni recevoir de reponse : sinon un client qui « notifie »
     lance un rendu dont personne n'attend le resultat, et une reponse a une
     notification serait prise pour celle d'une autre requete.
  3. UN ARGUMENT INVALIDE N'ATTEINT PAS L'OUTIL. Le booleen qui passe pour un
     entier (isinstance(True, int) vaut True en Python), le NaN qui echappe a
     minimum et maximum, l'argument inconnu, l'obligatoire absent.
  4. LE MODELE PEUT SE CORRIGER. Arguments invalides et refus d'un outil
     reviennent en resultat isError, pas en erreur JSON-RPC -32602 que les
     clients montrent a l'humain ou avalent — spec 2025-11-25, SEP-1303.
  5. LA NEGOCIATION. Une version connue est reprise, une inconnue recoit la
     plus recente des notres ; l'en-tete absent est accepte, l'inconnu refuse,
     et le corps du refus n'est PAS l'erreur moderne -32022 qui empecherait un
     client 2026-07-28 de retomber sur initialize.
  6. LA FORME. jsonrpc, l'id repris (y compris 0, qui est faux en Python),
     result OU error et jamais les deux, et du JSON pur a chaque etape d'un
     aller-retour complet initialize -> initialized -> tools/list -> tools/call.

Aucun reseau, aucun studio, aucun fichier : ce banc n'importe que mcp.py, qui
n'importe que la bibliotheque standard.

    python banc_mcp.py

CE QU'IL NE VOIT PAS :

  - le HTTP : le 202 d'une notification, le 400 d'une version refusee, la cle
    d'acces, l'en-tete Origin. C'est serveur.py ; ce banc ne prouve que les
    valeurs que serveur.py recevra (None, False, le corps du refus) ;
  - un VRAI client : rien ici n'a ete joue contre Claude Desktop, Claude Code
    ou le noeud MCP Client de n8n. Les formes sont celles des exemples de la
    spec 2025-11-25, recopiees a la main ;
  - la revision 2026-07-28, sans poignee de main, que le module ne parle pas ;
  - un client 2025-03-26 strict qui refuserait un bloc resource_link ou un
    champ title, apparus en 2025-06-18 : traiter() ne sait pas quelle version
    a ete negociee et rend la meme chose a tous ;
  - JSON Schema au-dela du sous-ensemble que outil() laisse ecrire.
"""
import asyncio
import io
import json
import math
import os
import sys

# LA CONSOLE WINDOWS ECRIT EN cp1252, et ce banc n'importe pas serveur.py, qui
# reconfigure la sortie pour le reste du depot. Sans ces lignes, il meurt sur
# son premier guillemet francais au lieu de rendre son verdict.
for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)

import mcp  # noqa: E402

ok, rate = [], []


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


# ── Les outils factices ──────────────────────────────────────────────────
# Chacun imite une conduite qu'un vrai outil du studio peut avoir. APPELS
# compte les executions : c'est le temoin de « l'outil n'a pas tourne ».
APPELS = []
SECRET = "/mnt/nas-privé/machine-gpu-7/clef"
JOURNAL = []


def signaler(nom, exc):
    JOURNAL.append((nom, f"{type(exc).__name__}: {exc}"))


async def appel_rendu(arguments, contexte):
    APPELS.append(("rendre", dict(arguments), contexte))
    return {"content": [mcp.texte(f"rendu lancé : {arguments['invite']}")],
            "structuredContent": {"identifiant": "r-42"}}


async def appel_refus(arguments, contexte):
    APPELS.append(("refuser", dict(arguments), contexte))
    raise mcp.ErreurOutil("Ce rendu n'existe pas : vérifie l'identifiant.")


async def appel_refus_vide(arguments, contexte):
    raise mcp.ErreurOutil("")


async def appel_panne(arguments, contexte):
    APPELS.append(("panne", dict(arguments), contexte))
    raise ValueError(f"impossible d'ouvrir {SECRET}")


async def appel_annule(arguments, contexte):
    raise asyncio.CancelledError()


async def appel_structure_seule(arguments, contexte):
    return {"structuredContent": {"etat": "fini"}}


async def appel_pas_un_dict(arguments, contexte):
    return ["pas", "un", "resultat"]


async def appel_contenu_pas_liste(arguments, contexte):
    return {"content": "texte nu"}


async def appel_octets(arguments, contexte):
    return {"content": [mcp.texte("ok")], "structuredContent": {"brut": b"\x00"}}


async def appel_nan(arguments, contexte):
    return {"content": [mcp.texte("ok")], "structuredContent": {"x": math.nan}}


async def appel_sans_parametre(arguments, contexte):
    APPELS.append(("etat", dict(arguments), contexte))
    return {"content": [mcp.texte(f"{len(arguments)} argument(s)")]}


SCHEMA_RENDU = {
    "type": "object",
    "properties": {
        "invite": {"type": "string", "minLength": 1, "maxLength": 50,
                   "description": "ce qu'il faut dessiner"},
        "largeur": {"type": "integer", "minimum": 64, "maximum": 2048},
        "modele": {"type": "string", "enum": ["flux", "klein"]},
        "net": {"type": "boolean"},
        "force": {"type": "number", "minimum": 0, "maximum": 1},
        "graines": {"type": "array", "items": {"type": "integer"},
                    "maxItems": 3},
    },
    "required": ["invite"],
    "additionalProperties": False,
}
VIDE = {"type": "object", "additionalProperties": False}

OUTILS = [
    mcp.outil("rendre", "Rendre une image", "Lance un rendu.", SCHEMA_RENDU,
              appel_rendu),
    mcp.outil("refuser", "Refus", "Refuse toujours.", VIDE, appel_refus),
    mcp.outil("refuser_vide", "Refus", "Refuse sans dire.", VIDE,
              appel_refus_vide),
    mcp.outil("panne", "Panne", "Leve une ValueError.", VIDE, appel_panne),
    mcp.outil("annule", "Annule", "Est annule.", VIDE, appel_annule),
    mcp.outil("structure", "Structure", "Sans content.", VIDE,
              appel_structure_seule),
    mcp.outil("pas_dict", "Pas dict", "Rend une liste.", VIDE,
              appel_pas_un_dict),
    mcp.outil("contenu_nu", "Contenu nu", "content n'est pas une liste.", VIDE,
              appel_contenu_pas_liste),
    mcp.outil("octets", "Octets", "Rend des octets.", VIDE, appel_octets),
    mcp.outil("nan", "NaN", "Rend NaN.", VIDE, appel_nan),
    mcp.outil("etat", "Etat", "Sans parametre.", {"type": "object"},
              appel_sans_parametre),
]
CONTEXTE = {"compte": "banc"}


def jouer(message, **options):
    options.setdefault("signaler", signaler)
    return asyncio.run(mcp.traiter(message, OUTILS, CONTEXTE, **options))


def requete(methode, params=None, id_=1):
    m = {"jsonrpc": "2.0", "id": id_, "method": methode}
    if params is not None:
        m["params"] = params
    return m


def appeler(nom, arguments=None, id_=1):
    p = {"name": nom}
    if arguments is not None:
        p["arguments"] = arguments
    return jouer(requete("tools/call", p, id_))


def forme(rep, id_, genre):
    """La reponse a exactement la forme JSON-RPC attendue : jsonrpc, l'id
    repris (avec son TYPE : 1 n'est pas « 1 »), et result XOR error."""
    if not isinstance(rep, dict):
        return False
    attendu = {"jsonrpc", "id", genre}
    return (set(rep) == attendu and rep["jsonrpc"] == "2.0"
            and rep["id"] == id_ and type(rep["id"]) is type(id_))


def code(rep):
    return (rep or {}).get("error", {}).get("code")


def texte_de(rep):
    return " ".join(b.get("text", "") for b in rep["result"]["content"])


def json_pur(rep):
    try:
        json.dumps(rep, allow_nan=False)
        return True
    except (TypeError, ValueError):
        return False


# ═════════════════════════════════════════════════════════════════════════
print("\n  ── le texte d'une exception ne sort pas ──")
JOURNAL.clear()
rep = appeler("panne", {}, 9)
serial = json.dumps(rep, ensure_ascii=False)
dit(forme(rep, 9, "result") and rep["result"].get("isError") is True,
    "une ValueError devient un resultat isError, pas une erreur JSON-RPC",
    serial[:120])
morceaux = ["nas-privé", "machine-gpu-7", "ValueError", "impossible d'ouvrir",
            "Traceback", "clef"]
fuites = [m for m in morceaux if m in serial
          or m in json.dumps(rep)]  # ensure_ascii echappe les accents : les deux
dit(not fuites, "le secret n'apparait NULLE PART dans la reponse serialisee",
    ", ".join(fuites) or f"{len(morceaux)} morceaux cherches")
dit(len(morceaux) >= 5 and all(m in SECRET or m in ("ValueError", "Traceback",
                                                    "impossible d'ouvrir")
                               for m in morceaux),
    "et la recherche porte bien sur des morceaux du secret (temoin)")
dit("panne" in texte_de(rep) and "journal" in texte_de(rep),
    "le message generique nomme l'outil et dit ou chercher", texte_de(rep))
dit(len(JOURNAL) == 1 and SECRET in JOURNAL[0][1] and JOURNAL[0][0] == "panne",
    "et la trace arrive au journal, elle : un echec muet des deux cotes ne se "
    "diagnostique plus", repr(JOURNAL)[:100])
# Le signaleur par defaut ecrit sur la sortie d'erreur ; on l'y attrape.
_vraie = sys.stderr
sys.stderr = io.StringIO()
try:
    rep_defaut = asyncio.run(mcp.traiter(requete("tools/call", {"name": "panne"}),
                                         OUTILS, CONTEXTE))
    capte = sys.stderr.getvalue()
finally:
    sys.stderr = _vraie
dit(SECRET in capte and "ValueError" in capte and "Traceback" in capte
    and SECRET not in json.dumps(rep_defaut, ensure_ascii=False),
    "sans signaleur, la trace part sur la sortie d'erreur et pas au client",
    capte.strip().splitlines()[0][:80] if capte.strip() else "rien capte")


def signaleur_casse(nom, exc):
    raise RuntimeError("le journal est plein")


rep = jouer(requete("tools/call", {"name": "panne"}, 3), signaler=signaleur_casse)
dit(forme(rep, 3, "result") and rep["result"].get("isError") is True,
    "un signaleur qui leve n'emporte pas la reponse")
for nom_outil, pourquoi in (("pas_dict", "un outil qui rend une liste"),
                            ("contenu_nu", "un content qui n'est pas une liste"),
                            ("octets", "des octets dans le resultat"),
                            ("nan", "un NaN dans le resultat")):
    rep = appeler(nom_outil, {}, 4)
    dit(forme(rep, 4, "result") and rep["result"].get("isError") is True
        and json_pur(rep),
        f"{pourquoi} : isError generique, et la reponse reste du JSON pur",
        json.dumps(rep, default=repr)[:90])
try:
    appeler("annule", {})
    passe = False
except asyncio.CancelledError:
    passe = True
dit(passe, "asyncio.CancelledError traverse : l'avaler ferait repondre une "
           "requete abandonnee et retiendrait l'arret du studio")

# ═════════════════════════════════════════════════════════════════════════
print("\n  ── une notification ne lance rien ──")
APPELS.clear()
notifications = [
    {"jsonrpc": "2.0", "method": "notifications/initialized"},
    {"jsonrpc": "2.0", "method": "notifications/cancelled",
     "params": {"requestId": 1, "reason": "trop long"}},
    {"jsonrpc": "2.0", "method": "methode/inconnue"},
    {"jsonrpc": "2.0", "method": "initialize",
     "params": {"protocolVersion": "2025-06-18"}},
    {"jsonrpc": "2.0", "method": "tools/call",
     "params": {"name": "rendre", "arguments": {"invite": "un chat"}}},
    {"jsonrpc": "2.0", "method": "ping", "params": "pas un objet"},
]
reponses = [jouer(n) for n in notifications]
dit(len(notifications) >= 6 and all(r is None for r in reponses),
    "aucune notification ne recoit de reponse, meme une methode inconnue",
    f"{sum(r is None for r in reponses)}/{len(notifications)} a None")
dit(APPELS == [], "un tools/call sans id n'execute PAS l'outil",
    repr(APPELS)[:80])
rep = appeler("rendre", {"invite": "un chat"}, 5)
dit(len(APPELS) == 1 and APPELS[0][0] == "rendre",
    "et le meme tools/call AVEC un id l'execute bien (temoin)",
    repr(APPELS)[:80])
dit(APPELS and APPELS[0][2] is CONTEXTE,
    "l'outil recoit le contexte du serveur tel quel")
reponse_client = {"jsonrpc": "2.0", "id": 7, "result": {}}
dit(jouer(reponse_client) is None
    and jouer({"jsonrpc": "2.0", "id": 8, "error": {"code": 1, "message": "x"}})
    is None,
    "une REPONSE postee par le client ne recoit pas de reponse (JSON-RPC)")

# ═════════════════════════════════════════════════════════════════════════
print("\n  ── un argument invalide n'atteint pas l'outil ──")
# Chaque cas nomme la FAUTE attendue, pas seulement l'argument : un booleen
# pour « largeur » est aussi sous le minimum (True vaut 1), et un banc qui ne
# chercherait que le nom serait vert sur la faute d'a cote.
invalides = [
    ("un booleen pour un entier", {"invite": "a", "largeur": True},
     "« largeur » doit être un entier (reçu : booléen)"),
    ("une chaine pour un entier", {"invite": "a", "largeur": "512"},
     "« largeur » doit être un entier (reçu : chaîne)"),
    ("un flottant pour un entier", {"invite": "a", "largeur": 512.0},
     "« largeur » doit être un entier (reçu : nombre)"),
    ("sous le minimum", {"invite": "a", "largeur": 63},
     "« largeur » vaut 63, le minimum est 64"),
    ("au-dessus du maximum", {"invite": "a", "largeur": 2049},
     "« largeur » vaut 2049, le maximum est 2048"),
    ("hors de l'enum", {"invite": "a", "modele": "sdxl"},
     "« modele » doit valoir l'une de ces valeurs"),
    ("l'obligatoire absent", {"largeur": 512}, "« invite » est obligatoire"),
    ("un argument inconnu", {"invite": "a", "pirate": 1},
     "« pirate » n'est pas un argument de cet outil"),
    ("un NaN pour un nombre", {"invite": "a", "force": math.nan},
     "« force » doit être un nombre fini (reçu : nombre)"),
    ("une invite vide", {"invite": ""}, "« invite » fait 0 caractères"),
    ("un element de liste faux", {"invite": "a", "graines": [1, "2"]},
     "« graines[1] » doit être un entier (reçu : chaîne)"),
]
APPELS.clear()
for pourquoi, arguments, faute in invalides:
    rep = appeler("rendre", arguments, 11)
    dit(forme(rep, 11, "result") and rep["result"].get("isError") is True
        and faute in texte_de(rep),
        f"{pourquoi} : resultat isError qui dit {faute.split(' (')[0]}",
        texte_de(rep).replace(chr(10), " ")[:110] if forme(rep, 11, "result")
        else json.dumps(rep)[:90])
dit(len(invalides) >= 10 and APPELS == [],
    "et l'outil n'a tourne pour AUCUN de ces cas",
    f"{len(invalides)} cas, {len(APPELS)} appel(s)")
rep = appeler("rendre", {"invite": "a", "largeur": 64, "modele": "klein",
                         "net": False, "force": 1, "graines": [1, 2, 3]}, 12)
dit(forme(rep, 12, "result") and not rep["result"].get("isError")
    and len(APPELS) == 1,
    "des arguments valides, bornes comprises, passent (temoin)",
    texte_de(rep) if forme(rep, 12, "result") else json.dumps(rep)[:90])

# ═════════════════════════════════════════════════════════════════════════
print("\n  ── le modele peut se corriger ──")
rep = appeler("refuser", {}, 13)
dit(forme(rep, 13, "result") and rep["result"] ==
    {"content": [{"type": "text",
                  "text": "Ce rendu n'existe pas : vérifie l'identifiant."}],
     "isError": True},
    "ErreurOutil devient un resultat isError portant son message, tel quel",
    json.dumps(rep, ensure_ascii=False)[:100])
rep = appeler("refuser_vide", {}, 14)
dit(forme(rep, 14, "result") and rep["result"]["isError"] is True
    and "refuser_vide" in texte_de(rep),
    "une ErreurOutil sans message dit tout de meme qui a refuse",
    texte_de(rep))
dit(issubclass(mcp.ErreurOutil, ValueError),
    "ErreurOutil est une ValueError, comme les refus nommes du depot")
rep = appeler("rendre", {"invite": "a", "largeur": True}, 15)
dit("error" not in rep and rep["result"]["content"][0]["type"] == "text",
    "des arguments invalides ne sont PAS une erreur JSON-RPC -32602 "
    "(spec 2025-11-25, SEP-1303)", json.dumps(rep)[:90])
# Ce qui reste une erreur de protocole : la requete elle-meme est mal formee.
protocole = [
    ("outil inconnu", {"name": "fantome"}),
    ("name absent", {}),
    ("name qui n'est pas une chaine", {"name": 3}),
    ("arguments en liste", {"name": "etat", "arguments": [1]}),
    ("arguments null", {"name": "etat", "arguments": None}),
]
for pourquoi, params in protocole:
    rep = jouer(requete("tools/call", params, "p"))
    dit(forme(rep, "p", "error") and code(rep) == -32602,
        f"{pourquoi} : erreur JSON-RPC -32602", json.dumps(rep)[:90])
rep = jouer(requete("tools/call", {"name": "x" * 500}, 16))
dit(code(rep) == -32602 and len(rep["error"]["message"]) < 120,
    "un nom d'outil de 500 caracteres n'est pas renvoye en entier",
    f"{len(rep['error']['message'])} caracteres")
APPELS.clear()
rep = appeler("etat", None, 17)
dit(forme(rep, 17, "result") and APPELS and APPELS[0][1] == {},
    "arguments absents : l'outil recoit {}", texte_de(rep))
rep = appeler("structure", {}, 18)
dit(forme(rep, 18, "result") and rep["result"] ==
    {"content": [], "structuredContent": {"etat": "fini"}},
    "un resultat sans content recoit content: [] et garde le reste tel quel",
    json.dumps(rep))
rep = appeler("rendre", {"invite": "un chat"}, 19)
dit(forme(rep, 19, "result") and rep["result"] ==
    {"content": [{"type": "text", "text": "rendu lancé : un chat"}],
     "structuredContent": {"identifiant": "r-42"}},
    "le resultat d'un outil est rendu tel quel, sans isError ajoute",
    json.dumps(rep, ensure_ascii=False))

# ═════════════════════════════════════════════════════════════════════════
print("\n  ── la negociation ──")
for demandee in mcp.VERSIONS:
    rep = jouer(requete("initialize", {"protocolVersion": demandee,
                                       "capabilities": {},
                                       "clientInfo": {"name": "banc",
                                                      "version": "1"}}))
    dit(forme(rep, 1, "result") and rep["result"]["protocolVersion"] == demandee,
        f"une version connue est reprise : {demandee}",
        rep.get("result", {}).get("protocolVersion", json.dumps(rep)[:60]))
for pourquoi, params in (("2026-07-28, sans poignee de main",
                          {"protocolVersion": "2026-07-28"}),
                         ("une date inconnue", {"protocolVersion": "1999-01-01"}),
                         ("protocolVersion absent", {}),
                         ("protocolVersion qui n'est pas une chaine",
                          {"protocolVersion": 20250618})):
    rep = jouer(requete("initialize", params))
    dit(forme(rep, 1, "result")
        and rep["result"]["protocolVersion"] == mcp.VERSIONS[0],
        f"{pourquoi} : la plus recente des notres, {mcp.VERSIONS[0]}",
        rep.get("result", {}).get("protocolVersion", json.dumps(rep)[:60]))
rep = jouer(requete("initialize"))
dit(forme(rep, 1, "result") and rep["result"]["protocolVersion"] == mcp.VERSIONS[0],
    "initialize sans params repond quand meme")
dit(list(mcp.VERSIONS) == sorted(mcp.VERSIONS, reverse=True)
    and len(set(mcp.VERSIONS)) == len(mcp.VERSIONS) >= 2,
    "VERSIONS commence par la plus recente : c'est elle que propose la "
    "negociation", ", ".join(mcp.VERSIONS))
dit(mcp.VERSION_PAR_DEFAUT in mcp.VERSIONS,
    "la version qu'on assume sans en-tete est l'une des notres",
    mcp.VERSION_PAR_DEFAUT)
dit(all(v <= "2025-11-25" for v in mcp.VERSIONS),
    "aucune version sans poignee de main (2026-07-28 et suivantes) n'est "
    "declaree : le module n'en suit pas les regles")
rep = jouer(requete("initialize", {"protocolVersion": "2025-11-25"}),
            version_logiciel="3.1", instructions="Demande un rendu.")
dit(rep["result"] == {
    "protocolVersion": "2025-11-25",
    "capabilities": {"tools": {"listChanged": False}},
    "serverInfo": {"name": "comfystudio", "title": "ComfyStudio",
                   "version": "3.1"},
    "instructions": "Demande un rendu."},
    "le resultat d'initialize a exactement la forme attendue",
    json.dumps(rep["result"])[:100])
rep = jouer(requete("initialize", {"protocolVersion": "2025-11-25"}))
dit("instructions" not in rep["result"]
    and rep["result"]["serverInfo"]["version"] == "",
    "instructions vides : la cle est omise")

print("\n  ── l'en-tete MCP-Protocol-Version ──")
dit(mcp.version_acceptee(None), "absent : accepte (la spec dit d'assumer "
                                "2025-03-26)")
dit(all(mcp.version_acceptee(v) for v in mcp.VERSIONS),
    "chacune des notres : acceptee", ", ".join(mcp.VERSIONS))
dit(mcp.version_acceptee(" 2025-06-18 "), "avec des espaces autour : acceptee")
refusees = ["2026-07-28", "1999-01-01", "", "2025-06-18; x", 20250618]
dit(len(refusees) >= 5 and not any(mcp.version_acceptee(v) for v in refusees),
    "inconnue, vide ou d'un autre type : refusee (le HTTP rendra 400)",
    ", ".join(repr(v) for v in refusees if mcp.version_acceptee(v)) or
    f"{len(refusees)} refusees")
corps = mcp.refus_de_version("2026-07-28")
dit(set(corps) == {"jsonrpc", "id", "error"} and corps["id"] is None
    and code(corps) == -32600,
    "le corps du refus est une erreur JSON-RPC ordinaire, sans id",
    json.dumps(corps, ensure_ascii=False)[:90])
dit(not -32099 <= code(corps) <= -32020,
    "et PAS une erreur moderne (-32020 a -32099, dont -32022) : un client "
    "2026-07-28 doit pouvoir retomber sur initialize", str(code(corps)))
dit(all(v in corps["error"]["message"] for v in mcp.VERSIONS)
    and "2026-07-28" in corps["error"]["message"],
    "le message nomme la version refusee et les versions acceptees",
    corps["error"]["message"][:100])
dit(len(mcp.refus_de_version("x" * 5000)["error"]["message"]) < 300,
    "un en-tete de 5000 caracteres n'est pas renvoye en entier")

# ═════════════════════════════════════════════════════════════════════════
print("\n  ── la forme des messages ──")
non_objets = [[requete("ping")], "ping", None, 42]
reps = [jouer(m) for m in non_objets]
dit(len(non_objets) >= 4 and all(forme(r, None, "error") and code(r) == -32600
                                 for r in reps),
    "un message qui n'est pas un objet (lot, chaine, null, nombre) : -32600, "
    "id null", json.dumps(reps[0], ensure_ascii=False)[:90])
cas_requete = [
    ("jsonrpc 1.0", {"jsonrpc": "1.0", "id": 7, "method": "ping"}, 7),
    ("jsonrpc absent", {"id": "a", "method": "ping"}, "a"),
    ("method absent", {"jsonrpc": "2.0", "id": "b"}, "b"),
    ("method qui n'est pas une chaine", {"jsonrpc": "2.0", "id": 2, "method": 42}, 2),
    ("id booleen et jsonrpc faux", {"jsonrpc": "1", "id": True, "method": "ping"},
     None),
    ("id null", {"jsonrpc": "2.0", "id": None, "method": "ping"}, None),
    ("id flottant", {"jsonrpc": "2.0", "id": 1.5, "method": "ping"}, None),
    ("id booleen", {"jsonrpc": "2.0", "id": False, "method": "ping"}, None),
    ("id liste", {"jsonrpc": "2.0", "id": [1], "method": "ping"}, None),
]
for pourquoi, m, id_ in cas_requete:
    r = jouer(m)
    dit(forme(r, id_, "error") and code(r) == -32600,
        f"{pourquoi} : -32600, id {json.dumps(id_)}", json.dumps(r)[:90])
for id_ in (0, "", "abc", -5, 2 ** 53):
    r = jouer(requete("ping", id_=id_))
    dit(forme(r, id_, "result") and r["result"] == {},
        f"ping, id {json.dumps(id_)} repris avec son type : result {{}}",
        json.dumps(r))
r = jouer(requete("server/discover", {}, 21))
dit(forme(r, 21, "error") and code(r) == -32601,
    "methode inconnue (meme server/discover, de la 2026-07-28) : -32601",
    json.dumps(r)[:90])
r = jouer(requete("ressources/" + "z" * 400, {}, 22))
dit(code(r) == -32601 and len(r["error"]["message"]) < 120,
    "un nom de methode de 400 caracteres n'est pas renvoye en entier")
r = jouer(requete("tools/list", ["pas", "un", "objet"], 23))
dit(forme(r, 23, "error") and code(r) == -32602,
    "params qui n'est pas un objet : -32602", json.dumps(r)[:90])
dit(all(isinstance(r["error"]["code"], int) and isinstance(
    r["error"]["message"], str) and r["error"]["message"]
    for r in reps + [jouer(m) for _, m, _ in cas_requete]),
    "chaque erreur porte un code entier et un message non vide")

print("\n  ── tools/list ──")
r = jouer(requete("tools/list", {"cursor": "ignore"}, 30))
outils_vus = r["result"]["tools"]
dit(forme(r, 30, "result") and set(r["result"]) == {"tools"},
    "tools/list : un seul champ, tools, et pas de nextCursor")
dit([o["name"] for o in outils_vus] == [o["name"] for o in OUTILS],
    "tous les outils, dans l'ordre de la liste (stable d'un appel a l'autre)",
    ", ".join(o["name"] for o in outils_vus[:4]) + "…")
dit(all(set(o) == {"name", "title", "description", "inputSchema"}
        for o in outils_vus) and len(outils_vus) >= 5,
    "chaque outil a exactement name, title, description, inputSchema — "
    "jamais la fonction d'appel", repr(sorted(outils_vus[0])))
dit(outils_vus[0]["inputSchema"] == SCHEMA_RENDU and json_pur(r),
    "le schema est servi tel quel, et la liste est du JSON pur")

# ═════════════════════════════════════════════════════════════════════════
print("\n  ── valider_arguments, cas par cas ──")
V = mcp.valider_arguments
S = SCHEMA_RENDU
dit(V(S, {"invite": "un chat"}) == [], "le minimum valide : aucune faute")
dit(len(V(S, [])) == 1 and len(V(S, None)) == 1 and len(V(S, "x")) == 1,
    "des arguments qui ne sont pas un objet : une faute", V(S, [])[0])
f = V(S, {})
dit(len(f) == 1 and "invite" in f[0] and "obligatoire" in f[0],
    "l'obligatoire absent est nomme", f[0] if f else "")
f = V(S, {"invite": "a", "x": 1, "y": 2})
dit(len(f) == 2 and "« x »" in f[0] and "invite" in f[0],
    "chaque argument inconnu est nomme, avec la liste des connus",
    f[0][:90] if f else "")
dit(V({"type": "object", "properties": {"a": {"type": "string"}}},
      {"a": "x", "b": 1}) == [],
    "sans additionalProperties: false, un argument en plus est permis")
dit(V(S, {"invite": 3}) != [], "une chaine attendue, un entier recu : faute")
dit(len(V(S, {"invite": ""})) == 1 and len(V(S, {"invite": "x" * 51})) == 1
    and V(S, {"invite": "x" * 50}) == [] and V(S, {"invite": "x"}) == [],
    "minLength et maxLength, bornes comprises")
dit(V(S, {"invite": "🐱" * 50}) == [],
    "un emoji compte pour un caractere, comme JSON Schema le demande")
long = V(S, {"invite": "secret-" * 2000})
dit(len(long) == 1 and len(long[0]) < 150 and "secret-" not in long[0],
    "la faute dit la longueur, pas la valeur : une invite de 14 000 "
    "caracteres n'est pas recopiee", long[0] if long else "")
for valeur, attendu, pourquoi in ((True, 1, "True pour un entier"),
                                  (False, 1, "False pour un entier"),
                                  (512.0, 1, "512.0 pour un entier"),
                                  ("512", 1, "« 512 » pour un entier"),
                                  (None, 1, "null pour un entier"),
                                  (512, 0, "512 pour un entier"),
                                  (64, 0, "le minimum lui-meme"),
                                  (2048, 0, "le maximum lui-meme"),
                                  (63, 1, "un sous le minimum"),
                                  (2049, 1, "un au-dessus du maximum")):
    f = V(S, {"invite": "a", "largeur": valeur})
    dit(len(f) == attendu, f"largeur : {pourquoi}", "; ".join(f) or "valide")
f = V(S, {"invite": "a", "largeur": True})
dit(f and "booléen" in f[0] and "entier" in f[0],
    "la faute du booleen dit ce qui etait attendu et ce qui a ete recu",
    f[0] if f else "")
try:
    f = V(S, {"invite": "a", "largeur": "abc"})
    dit(len(f) == 1, "un type faux arrete les autres controles : pas de "
                     "« 'abc' < 64 » qui leverait", f[0])
except TypeError as e:
    dit(False, "un type faux arrete les autres controles : pas de "
               "« 'abc' < 64 » qui leverait", repr(e))
for valeur, attendu, pourquoi in ((0, 0, "l'entier 0 pour un nombre"),
                                  (0.5, 0, "0.5"),
                                  (True, 1, "True pour un nombre"),
                                  (math.nan, 1, "NaN"),
                                  (math.inf, 1, "l'infini"),
                                  (1.01, 1, "au-dessus du maximum")):
    f = V(S, {"invite": "a", "force": valeur})
    dit(len(f) == attendu, f"force : {pourquoi}", "; ".join(f) or "valide")
dit(V(S, {"invite": "a", "net": True}) == []
    and len(V(S, {"invite": "a", "net": 1})) == 1
    and len(V(S, {"invite": "a", "net": "true"})) == 1,
    "un booleen est un booleen, et ni 1 ni « true »")
dit(V(S, {"invite": "a", "modele": "flux"}) == []
    and len(V(S, {"invite": "a", "modele": "Flux"})) == 1,
    "l'enum est sensible a la casse")
f = V(S, {"invite": "a", "modele": "sdxl"})
dit(f and '"flux"' in f[0] and '"klein"' in f[0],
    "la faute d'enum liste les valeurs permises", f[0] if f else "")
ENUM = {"type": "object", "properties": {"n": {"enum": [0, 1]}}}
dit(len(V(ENUM, {"n": True})) == 1 and len(V(ENUM, {"n": False})) == 1
    and V(ENUM, {"n": 1}) == [] and V(ENUM, {"n": 1.0}) == [],
    "enum [0, 1] : ni True ni False (piege « True in [0, 1] »), mais 1.0 oui")
dit(V(S, {"invite": "a", "graines": [1, 2, 3]}) == []
    and len(V(S, {"invite": "a", "graines": [1, 2, 3, 4]})) == 1
    and len(V(S, {"invite": "a", "graines": {"0": 1}})) == 1
    and len(V(S, {"invite": "a", "graines": [1, True, "3"]})) == 2,
    "une liste : son type, sa taille, et le type de chaque element")
dit(V(VIDE, {}) == [] and len(V(VIDE, {"a": 1})) == 1,
    "le schema sans parametre recommande par la spec n'accepte que {}")

print("\n  ── outil() refuse ce qu'il ne sait pas garder ──")


async def appel_neutre(arguments, contexte):
    return {"content": []}


def appel_synchrone(arguments, contexte):
    return {"content": []}


refus = [
    ("un nom a espace", lambda: mcp.outil("lancer rendu", "t", "d", VIDE,
                                          appel_neutre)),
    ("un nom vide", lambda: mcp.outil("", "t", "d", VIDE, appel_neutre)),
    ("un nom de 129 caracteres", lambda: mcp.outil("a" * 129, "t", "d", VIDE,
                                                   appel_neutre)),
    ("un schema qui n'est pas un objet", lambda: mcp.outil(
        "a", "t", "d", {"type": "array"}, appel_neutre)),
    ("un « pattern » qu'on n'applique pas", lambda: mcp.outil(
        "a", "t", "d", {"type": "object", "properties": {
            "x": {"type": "string", "pattern": "^a"}}}, appel_neutre)),
    ("un « exclusiveMinimum » qu'on n'applique pas", lambda: mcp.outil(
        "a", "t", "d", {"type": "object", "properties": {
            "x": {"type": "integer", "exclusiveMinimum": 0}}}, appel_neutre)),
    ("un minimum sur une chaine", lambda: mcp.outil(
        "a", "t", "d", {"type": "object", "properties": {
            "x": {"type": "string", "minimum": 0}}}, appel_neutre)),
    ("un type objet en propriete", lambda: mcp.outil(
        "a", "t", "d", {"type": "object", "properties": {
            "x": {"type": "object"}}}, appel_neutre)),
    ("une propriete sans type ni enum", lambda: mcp.outil(
        "a", "t", "d", {"type": "object", "properties": {"x": {}}},
        appel_neutre)),
    ("un obligatoire non decrit", lambda: mcp.outil(
        "a", "t", "d", {"type": "object", "required": ["x"]}, appel_neutre)),
    ("additionalProperties en schema", lambda: mcp.outil(
        "a", "t", "d", {"type": "object", "additionalProperties": {}},
        appel_neutre)),
    ("un appel synchrone", lambda: mcp.outil("a", "t", "d", VIDE,
                                             appel_synchrone)),
    ("un mot inconnu dans items", lambda: mcp.outil(
        "a", "t", "d", {"type": "object", "properties": {
            "x": {"type": "array", "items": {"type": "string",
                                             "format": "uri"}}}},
        appel_neutre)),
]
for pourquoi, fabrique in refus:
    try:
        fabrique()
        refuse = False
    except ValueError:
        refuse = True
    dit(refuse, f"outil() refuse {pourquoi}")
try:
    bon = mcp.outil("admin.rendu_v2-b", "t", "d", SCHEMA_RENDU, appel_neutre)
    dit(set(bon) == {"name", "title", "description", "inputSchema", "appel"},
        "et accepte un outil correct, nom a point, tiret et souligne (temoin)")
except ValueError as e:
    dit(False, "et accepte un outil correct, nom a point, tiret et souligne "
               "(temoin)", str(e))

print("\n  ── les blocs de contenu ──")
dit(mcp.texte("a") == {"type": "text", "text": "a"}, "texte()")
dit(mcp.image("QUJD", "image/png") ==
    {"type": "image", "data": "QUJD", "mimeType": "image/png"}, "image()")
dit(mcp.lien("https://s/f.png", "f.png") ==
    {"type": "resource_link", "uri": "https://s/f.png", "name": "f.png"},
    "lien() sans options : ni mimeType ni description, pas meme a null")
dit(mcp.lien("https://s/f.png", "f.png", "image/png", "le rendu") ==
    {"type": "resource_link", "uri": "https://s/f.png", "name": "f.png",
     "mimeType": "image/png", "description": "le rendu"}, "lien() complet")
dit(mcp.erreur(-32700, "Parse error") ==
    {"jsonrpc": "2.0", "id": None, "error": {"code": -32700,
                                             "message": "Parse error"}},
    "erreur() pour serveur.py : id null quand l'id n'a pas pu etre lu")

# ═════════════════════════════════════════════════════════════════════════
print("\n  ── un aller-retour complet, en JSON a chaque etape ──")


def passe_par_json(message, **options):
    """Le message tel que serveur.py le recevra (decode d'un corps JSON), et la
    reponse telle qu'il l'enverra. None si json.dumps leve."""
    entree = json.loads(json.dumps(message))
    rep = jouer(entree, **options)
    if rep is None:
        return None, "rien"
    try:
        return rep, json.dumps(rep, allow_nan=False)
    except (TypeError, ValueError) as e:
        return rep, None


etapes = []
rep, s = passe_par_json(requete("initialize", {
    "protocolVersion": "2025-11-25", "capabilities": {},
    "clientInfo": {"name": "n8n", "version": "1.90"}}, 1),
    version_logiciel="3.1")
etapes.append(("initialize", s is not None and forme(rep, 1, "result")
               and rep["result"]["protocolVersion"] == "2025-11-25"))
rep, s = passe_par_json({"jsonrpc": "2.0", "method": "notifications/initialized"})
etapes.append(("notifications/initialized", rep is None))
rep, s = passe_par_json(requete("tools/list", None, 2))
etapes.append(("tools/list", s is not None and forme(rep, 2, "result")
               and "rendre" in [o["name"] for o in rep["result"]["tools"]]))
rep, s = passe_par_json(requete("tools/call", {
    "name": "rendre", "arguments": {"invite": "un phare", "largeur": 1024}},
    "trois"))
etapes.append(("tools/call", s is not None and forme(rep, "trois", "result")
               and json.loads(s)["result"]["structuredContent"]
               == {"identifiant": "r-42"}))
rep, s = passe_par_json(requete("tools/call", {
    "name": "rendre", "arguments": {"invite": "un phare", "largeur": "grand"}},
    4))
etapes.append(("tools/call invalide", s is not None and forme(rep, 4, "result")
               and json.loads(s)["result"]["isError"] is True))
rep, s = passe_par_json(requete("tools/call", {"name": "panne"}, 5))
etapes.append(("tools/call en panne", s is not None
               and SECRET not in json.loads(s)["result"]["content"][0]["text"]))
manquees = [n for n, bon in etapes if not bon]
dit(len(etapes) == 6 and not manquees,
    "initialize -> initialized -> tools/list -> tools/call : chaque reponse "
    "a sa forme et se serialise", ", ".join(manquees) or
    " -> ".join(n for n, _ in etapes))

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
for x in rate:
    print("    NON :", x)
sys.exit(1 if rate else 0)
