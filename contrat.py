# -*- coding: utf-8 -*-
"""Le contrat OpenAPI du pilotage par programme : /api/v1/* et /mcp.

POURQUOI CE MODULE EXISTE. Un assistant IA qu'on branche sur une API, un
outil qui importe une description d'API (Postman, Insomnia, un generateur de
client), un humain qui ecrit un workflow n8n : tous ont besoin de savoir quelles
routes existent, ce qu'elles prennent, ce qu'elles rendent et comment elles
refusent. docs/piloter-par-programme.md le dit a un humain ; ce document le dit
a une machine, dans le format qu'elles lisent toutes, OpenAPI 3.1. Il est servi
par le studio lui-meme (GET /api/v1/openapi.json), avec l'adresse du studio
telle que le client l'a jointe, pour qu'un client qui le lit sache ou appeler.

POURQUOI A LA MAIN. Les generateurs d'OpenAPI pour aiohttp lisent des
decorateurs ou des modeles pydantic que ce depot n'a pas, et tirent des
dependances qu'un NAS sans pip n'a pas non plus. Un dict Python ecrit a la main
se relit en entier ; banc_contrat.py le confronte au routeur et au texte de
serveur.py DANS LES DEUX SENS, ce qu'aucun generateur ne ferait pour les
phrases des refus.

POURQUOI IL N'IMPORTE PAS serveur.py. C'est serveur.py qui l'importe, pour
servir le document : l'inverse ferait un cycle. Les bornes qui vivent dans
serveur.py (ATTENDRE_MAX, les etats, les tailles) sont donc RECOPIEES ici, et
banc_contrat.py exige qu'elles soient egales a celles de serveur.py — une
recopie sans banc deriverait a la premiere borne changee. Ce qui vit dans
acces.py, rappels.py et mcp.py, modules sans dependance, est lu a la source.

CE QU'IL NE FAIT PAS.
  - Il ne valide rien : aucune requete ne passe par ce document. Les gardes
    sont dans serveur.py ; le document les DECRIT.
  - Il ne decrit pas les routes de la page (/api/generer, /api/compte/*) ni
    celles de l'administration : elles ne prennent pas de cle d'acces, et un
    programme n'a rien a y faire.
  - Il ne decrit pas le protocole MCP lui-meme, message par message : /mcp y
    figure comme une route JSON-RPC, et la liste des outils se lit par
    tools/list, qui fait foi.
"""
import acces as _acces
import mcp as _mcp
import rappels as _rappels

VERSION_OPENAPI = "3.1.0"

# ── Les bornes recopiees de serveur.py (banc_contrat.py les confronte) ──
ATTENDRE_MAX = 600
ATTENDRE_MCP = 45
ETATS = ("en_file", "en_cours", "attente_machine", "question",
         "fini", "erreur", "annule")
ETATS_FINAUX = ("question", "fini", "erreur", "annule")
LIEN_DUREE = 24 * 3600
IDEMPOTENCE_DUREE = 24 * 3600
IDEMPOTENCE_LONGUEUR = 200
DEMANDE_MAX = 3000
VARIANTES_MAX = 4
CORPS_MAX = 4 * 1024 ** 2
# Triees : dans serveur.py, TAILLES est un ensemble, sans ordre. Un document
# qui changerait d'ordre a chaque demarrage ferait croire a un client qui le
# met en cache que l'API a change.
TAILLES = ("1024x1024", "1080x1350", "1216x832", "1280x720", "1600x900",
           "1920x1080", "768x1344", "832x1216")
PRIORITES = ("brouillon", "rapide", "soigne")
TYPES_FICHIER = ("image", "video", "audio", "objet3d", "autre")
OUTILS_MCP = ("generer_rendu", "etat_rendu", "repondre_question",
              "annuler_rendu", "lister_moteurs")

# ── Les refus qui portent un code ───────────────────────────────────────
# Le code est la cle de traductions.py sans sa famille (refus_programme). Il
# est STABLE : un workflow branche sur lui continue de marcher le jour ou la
# phrase change. Chaque entree : le statut HTTP, et ce que le programme doit
# en faire — c'est ce qu'il lit, pas une paraphrase de la phrase.
REFUS = {
    "cle_requise": (401, "Aucune clé d'accès présentée sur une route qui en "
                         "exige une. Poser « Authorization: Bearer cs_… »."),
    "cle_refusee": (401, "Clé inconnue, révoquée, ou éteinte par un changement "
                         "de mot de passe ou de second facteur. Ne pas "
                         "réessayer : demander une clé neuve."),
    "cle_hors_perimetre": (403, "Une clé d'accès présentée hors de /api/v1 et "
                                "/mcp. Elle n'y vaut rien, jamais."),
    "trop_d_essais": (429, "Trop de clés refusées depuis cette adresse : "
                           "attendre le nombre de secondes annoncé."),
    "corps_illisible": (400, "Le corps n'est pas un objet JSON."),
    "attendre_bornes": (400, f"« attendre » hors de 0 à {ATTENDRE_MAX} secondes."),
    "idempotence_illisible": (400, f"En-tête Idempotency-Key de plus de "
                                   f"{IDEMPOTENCE_LONGUEUR} caractères."),
    "cle_file_pleine": (429, "La clé a déjà autant de rendus en cours que son "
                             "plafond « en_file » : attendre qu'un se termine."),
    "cle_file_variantes": (429, "Les variantes demandées feraient dépasser le "
                                "plafond « en_file » : en demander moins, ou "
                                "attendre."),
    "cle_plafond_jour": (429, "La clé a atteint son plafond « par_jour » : "
                              "rien ne passera avant minuit, heure du studio."),
    "champ_illisible": (400, "Un champ n'a pas la forme attendue ; la phrase "
                             "le nomme."),
    "rappel_refuse": (400, "L'adresse de rappel est refusée : hôte non déclaré "
                           "dans la clé, schéma autre que http(s), "
                           "identifiants dans l'URL, ou URL ambiguë."),
    "image_illisible": (400, "image_base64 n'est pas du base64."),
    "fichier_vide": (400, "L'image envoyée est vide."),
    "fichier_trop_lourd": (413, "L'image dépasse le plafond de sa famille."),
    "conversation_inconnue": (404, "Aucune conversation ouverte de CETTE clé ne "
                                   "porte cet identifiant."),
    "cle_sans_nuage": (400, "Moteur distant demandé, et la clé n'a pas droit au "
                            "nuage (ou la demande l'a retiré)."),
    "refus_mineurs": (422, "Contenu sexuel impliquant des mineurs : refusé "
                           "avant la file, rien n'est compté."),
    "rendu_inconnu": (404, "Aucun rendu de CETTE clé ne porte cet identifiant "
                           "(ou le fichier demandé n'existe pas)."),
    "rendu_termine": (409, "Annulation d'un rendu déjà terminé."),
    "pas_de_question": (409, "Réponse à un rendu qui n'est pas dans l'état "
                             "« question »."),
    "reponse_vide": (400, "La réponse à la question est vide."),
}

_REF = "#/components/"


def _ref(genre, nom):
    return {"$ref": f"{_REF}{genre}/{nom}"}


def _json(schema):
    return {"application/json": {"schema": schema}}


def _table_des_refus():
    lignes = ["| code | statut | ce que le programme en fait |",
              "|---|---|---|"]
    for code, (statut, quoi) in REFUS.items():
        lignes.append(f"| `{code}` | {statut} | {quoi} |")
    return "\n".join(lignes)


def _schemas():
    nul = ["string", "null"]
    rendu = {
        "type": "object",
        "description": (
            "Un rendu, tel qu'un programme le lit. La même forme partout : "
            "la réponse des routes /api/v1/rendus, le champ « rendu » d'un "
            "rappel, le contenu structuré des outils MCP. Pour un rendu à "
            "variantes, « id » est celui du premier tirage et « fichiers » "
            "rassemble ceux de tous les tirages."),
        "required": ["id", "etat", "fichiers"],
        "properties": {
            "id": {"type": "string", "pattern": "^[0-9a-f]{32}$"},
            "etat": {
                "type": "string", "enum": list(ETATS),
                "description": (
                    "en_file : attend son tour (« position »). en_cours : "
                    "calcule (« avance », de 0 à 1, quand la machine la "
                    "donne). attente_machine : la machine demandée est en "
                    "pause, la demande repartira seule à son retour. question "
                    "(final) : le studio demande une précision, lire "
                    "« questions » et répondre par .../reponse. fini (final) : "
                    "lire « fichiers ». erreur (final) : lire « erreur ». "
                    "annule (final).")},
            "demande": {"type": "string"},
            "conversation": {"type": nul,
                             "description": "À repasser dans « conversation » "
                                            "pour enchaîner (« la même en "
                                            "bleu »)."},
            "cree": {"type": nul,
                     "description": "Heure locale du studio, "
                                    "« AAAA-MM-JJTHH:MM:SS+HHMM » (décalage "
                                    "sans deux-points). Null quand le rendu "
                                    "n'est plus en mémoire."},
            "intention": {"type": nul},
            "moteur": {"type": nul},
            "machine": {"type": nul},
            "position": {"type": ["integer", "null"],
                         "description": "Rang dans la file, travaux en vol "
                                        "compris."},
            "avance": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
            "secondes": {"type": ["number", "null"]},
            "fichiers": {"type": "array", "items": _ref("schemas", "Fichier")},
            "questions": {"type": "array", "items": {"type": "string"}},
            "description": {"type": nul},
            "erreur": {
                "type": ["object", "null"],
                "properties": {
                    "code": {"type": "string",
                             "description": "« annule », ou le code de la "
                                            "panne (« inconnue » à défaut)."},
                    "message": {"type": "string"}}},
            "journal": {"type": "array", "items": {"type": nul},
                        "description": "Les cinq dernières lignes du fil du "
                                       "rendu, celles que la page montre."},
        },
    }
    fichier = {
        "type": "object",
        "required": ["rang", "nom", "type", "url"],
        "properties": {
            "rang": {"type": "integer", "minimum": 0,
                     "description": "Numéro du fichier dans le rendu, tous "
                                    "tirages confondus."},
            "variante": {"type": "integer", "minimum": 1},
            "nom": {"type": "string"},
            "type": {"type": "string", "enum": list(TYPES_FICHIER)},
            "url": {"type": "string",
                    "description": "Avec la clé d'accès en en-tête."},
            "lien": {"type": nul,
                     "description": f"Lien signé, SANS en-tête, valable "
                                    f"{LIEN_DUREE // 3600} h. Il meurt avec "
                                    f"sa clé."},
        },
    }
    refus = {
        "type": "object",
        "required": ["erreur"],
        "description": (
            "Un refus. « erreur » est une phrase, en français ou en anglais "
            "selon Accept-Language ; « code » est stable et c'est sur lui "
            "qu'un programme se branche.\n\n" + _table_des_refus() + "\n\n"
            "Les refus de la validation commune avec la page (demande vide ou "
            "trop longue, taille, moteur, priorité, variantes, machine ou "
            "image inconnues) et ceux de POST /api/v1/fichiers n'ont pas "
            "encore de « code » : seulement « erreur », en 400 (404 pour une "
            "image inconnue, 413 pour un fichier trop lourd). Un corps JSON "
            f"de plus de {CORPS_MAX // 1024 ** 2} Mio est refusé en 413 par "
            "le serveur HTTP, avec un corps texte."),
        "properties": {
            "erreur": {"type": "string"},
            "code": {"type": "string", "enum": list(REFUS)},
        },
    }
    demande = {
        "type": "object",
        "description": "Il faut « demande » ou une image (« image » ou "
                       "« image_base64 »), ou les deux.",
        "properties": {
            "demande": {"type": "string", "maxLength": DEMANDE_MAX,
                        "description": "En langage naturel, dans n'importe "
                                       "quelle langue : ne pas traduire."},
            "moteur": {"type": "string",
                       "description": "Une « cle » de GET /api/v1/moteurs. "
                                      "Imposer un moteur impose aussi "
                                      "l'opération (agrandir, détourer…)."},
            "taille": {"type": "string", "enum": list(TAILLES)},
            "priorite": {"type": "string", "enum": list(PRIORITES)},
            "variantes": {"type": "integer", "minimum": 1,
                          "maximum": VARIANTES_MAX},
            "machine": {"type": "string",
                        "description": "Identifiant d'une machine du parc."},
            "image": {"type": "string",
                      "description": "Le nom rendu par POST /api/v1/fichiers."},
            "image_base64": {"type": "string",
                             "description": "Une image en base64, ou une URL "
                                            "« data:image/png;base64,… ». "
                                            f"Bornée par le corps JSON "
                                            f"({CORPS_MAX // 1024 ** 2} Mio) : "
                                            "au-delà, passer par "
                                            "/api/v1/fichiers."},
            "image_type": {"type": "string", "default": "png",
                           "description": "Extension de l'image base64 : "
                                          "png, jpg, jpeg, webp…"},
            "conversation": {"type": "string",
                             "description": "Une conversation de CETTE clé, "
                                            "pour enchaîner sur son contexte."},
            "rappel": {"type": "string",
                       "description": "URL à prévenir à la fin, signée. Son "
                                      "hôte doit être déclaré dans la clé."},
            "attendre": _attendre("Secondes à attendre la fin avant de "
                                  "répondre (0 par défaut)."),
            "nuage": {"type": "boolean", "default": True,
                      "description": "false interdit le nuage pour cette "
                                     "demande. true ne l'ouvre pas à une clé "
                                     "qui n'y a pas droit."},
        },
    }
    reponse = {
        "type": "object", "required": ["reponse"],
        "properties": {
            "reponse": {"type": "string", "minLength": 1},
            "attendre": _attendre("Secondes à attendre la fin du NOUVEAU "
                                  "rendu."),
            "rappel": {"type": "string",
                       "description": "Par défaut, celui du rendu qui a posé "
                                      "la question."},
        },
    }
    moteur = {
        "type": "object",
        "properties": {
            "cle": {"type": "string"}, "titre": {"type": "string"},
            "pour": {"type": "string"}, "type": {"type": "string"},
            "distant": {"type": "boolean",
                        "description": "Moteur d'un fournisseur du nuage ; "
                                       "listé seulement pour une clé qui y "
                                       "a droit."},
            "present": {"type": "boolean",
                        "description": "false : ses modèles ne sont sur "
                                       "aucune machine."},
        },
    }
    cle = {
        "type": "object",
        "description": "La fiche publique d'une clé : ni son secret, ni le "
                       "secret de rappel.",
        "properties": {
            "id": {"type": "string", "pattern": "^[0-9a-f]{8}$"},
            "compte": {"type": "string"}, "nom": {"type": "string"},
            "apercu": {"type": "string"},
            "cree": {"type": "number"}, "vu": {"type": ["number", "null"]},
            "nuage": {"type": "boolean"},
            "hotes": {"type": "array", "items": {"type": "string"}},
            "en_file": {"type": "integer", "minimum": 1,
                        "maximum": _acces.EN_FILE_MAX},
            "par_jour": {"type": "integer", "minimum": 0,
                         "maximum": _acces.PAR_JOUR_MAX,
                         "description": "0 : sans plafond."},
            "generation": {"type": "integer"},
        },
    }
    evenement = {
        "type": "object",
        "description": "Le corps d'un rappel : JSON compact, clés triées, UTF-8.",
        "properties": {
            "evenement": {"type": "string", "enum": list(_rappels.EVENEMENTS)},
            "id": {"type": "string"},
            "rendu": _ref("schemas", "Rendu"),
            "envoye": {"type": "string"},
        },
    }
    return {
        "Rendu": rendu, "Fichier": fichier, "Refus": refus,
        "DemandeRendu": demande, "ReponseQuestion": reponse,
        "Moteur": moteur, "Cle": cle, "EvenementRappel": evenement,
        "Moteurs": {
            "type": "object",
            "properties": {
                "moteurs": {"type": "array", "items": _ref("schemas", "Moteur")},
                "tailles": {"type": "array", "items": {"type": "string"}},
                "priorites": {"type": "array", "items": {"type": "string"}},
                "variantes_max": {"type": "integer"},
            }},
        "Moi": {
            "type": "object",
            "properties": {
                "compte": {"type": "string"},
                "cle": _ref("schemas", "Cle"),
                "en_cours": {"type": "integer"},
                "aujourdhui": {"type": "integer"},
                "attendre_max": {"type": "integer"},
            }},
        "Televersement": {
            "type": "object",
            "properties": {
                "image": {"type": "string",
                          "description": "À passer dans « image »."},
                "octets": {"type": "integer"},
            }},
        "JsonRpc": {
            "type": "object",
            "description": "Un message JSON-RPC 2.0 (un seul : pas de lot).",
            "required": ["jsonrpc"],
            "properties": {
                "jsonrpc": {"type": "string", "enum": ["2.0"]},
                "id": {"type": ["string", "integer"]},
                "method": {"type": "string"},
                "params": {"type": "object"},
                "result": {"type": "object"},
                "error": {"type": "object"},
            }},
    }


def _attendre(description):
    return {"type": "integer", "minimum": 0, "maximum": ATTENDRE_MAX,
            "description": description}


def _parametres():
    return {
        "tid": {"name": "tid", "in": "path", "required": True,
                "description": "L'« id » rendu par POST /api/v1/rendus.",
                "schema": {"type": "string", "pattern": "^[0-9a-f]{32}$"}},
        "rang": {"name": "rang", "in": "path", "required": True,
                 "schema": {"type": "integer", "minimum": 0}},
        "jeton": {"name": "jeton", "in": "path", "required": True,
                  "schema": {"type": "string"}},
        "attendre": {"name": "attendre", "in": "query", "required": False,
                     "schema": _attendre("Secondes à attendre un état final "
                                         "avant de répondre.")},
        "IdempotencyKey": {
            "name": "Idempotency-Key", "in": "header", "required": False,
            "description": f"Même clé, même rendu, pendant "
                           f"{IDEMPOTENCE_DUREE // 3600} h : un programme qui "
                           f"réessaie ne lance pas un second rendu.",
            "schema": {"type": "string", "maxLength": IDEMPOTENCE_LONGUEUR}},
        "McpVersion": {
            "name": "MCP-Protocol-Version", "in": "header", "required": False,
            "description": "Absent : 2025-03-26 est supposée. Une version "
                           "inconnue est refusée en 400.",
            "schema": {"type": "string", "enum": list(_mcp.VERSIONS)}},
    }


def _reponses():
    refus = {"content": _json(_ref("schemas", "Refus"))}
    return {
        "Refus": dict(refus, description="Refusé : lire « code »."),
        "SansCle": {
            "description": "Clé absente ou refusée (cle_requise, cle_refusee).",
            "headers": {"WWW-Authenticate": {
                "schema": {"type": "string"},
                "description": "Bearer realm=\"comfystudio\""}},
            "content": _json(_ref("schemas", "Refus"))},
        "Freine": dict(refus, description="trop_d_essais, cle_file_pleine, "
                                          "cle_file_variantes, cle_plafond_jour."),
        "Inconnu": dict(refus, description="rendu_inconnu."),
        "UnRendu": {
            "description": "Le rendu.",
            "headers": {"Location": {"schema": {"type": "string"}}},
            "content": _json(_ref("schemas", "Rendu"))},
        "UnFichier": {
            "description": "Les octets du fichier, avec son type.",
            "content": {"application/octet-stream": {
                "schema": {"type": "string", "contentMediaType":
                           "application/octet-stream"}}}},
    }


def _communes(*statuts):
    """Les reponses que toute route a cle peut rendre, plus celles qu'on nomme."""
    # Pas de 403 « cle_hors_perimetre » : il ne se rend que HORS de ces
    # routes, a une cle presentee ailleurs.
    rep = {"401": _ref("responses", "SansCle"),
           "429": _ref("responses", "Freine")}
    for s in statuts:
        rep[str(s)] = _ref("responses", "Refus")
    return rep


def _chemins():
    p_tid, p_att = _ref("parameters", "tid"), _ref("parameters", "attendre")
    rendu_cree = {
        "description": "Accepté, pas encore fini (ou fini dans le délai : "
                       "200). Location désigne le rendu.",
        "headers": {"Location": {"schema": {"type": "string"}}},
        "content": _json(_ref("schemas", "Rendu"))}
    return {
        "/api/v1/rendus": {"post": {
            "operationId": "creerRendu",
            "summary": "Demander un rendu",
            "description": (
                "Valide la demande, la met en file et rend le rendu. Avec "
                f"« attendre » (au plus {ATTENDRE_MAX} s), la réponse attend "
                "un état final. Les plafonds de la clé passent d'abord, puis "
                "l'adresse de rappel, l'image, la conversation, la validation "
                "commune avec la page, le droit au nuage, et le garde-fou des "
                "mineurs — tout cela AVANT la file."),
            "parameters": [_ref("parameters", "IdempotencyKey")],
            "requestBody": {"required": True,
                            "content": _json(_ref("schemas", "DemandeRendu"))},
            "responses": dict(_communes(400, 404, 413, 422), **{
                "202": rendu_cree,
                "200": {"description": "Déjà dans un état final, ou rejoué par "
                                       "Idempotency-Key (en-tête "
                                       "Idempotent-Replayed: true).",
                        "headers": {
                            "Location": {"schema": {"type": "string"}},
                            "Idempotent-Replayed": {
                                "schema": {"type": "string", "enum": ["true"]}}},
                        "content": _json(_ref("schemas", "Rendu"))}})}},
        "/api/v1/rendus/{tid}": {
            "get": {
                "operationId": "lireRendu",
                "summary": "Lire un rendu",
                "parameters": [p_tid, p_att],
                "responses": dict(_communes(400),
                                  **{"200": _ref("responses", "UnRendu"),
                                     "404": _ref("responses", "Inconnu")})},
            "delete": {
                "operationId": "annulerRendu",
                "summary": "Annuler un rendu",
                "description": "Le retire de la file ou l'interrompt, "
                               "variantes comprises.",
                "parameters": [p_tid],
                "responses": dict(_communes(409),
                                  **{"200": _ref("responses", "UnRendu"),
                                     "404": _ref("responses", "Inconnu")})}},
        "/api/v1/rendus/{tid}/reponse": {"post": {
            "operationId": "repondreQuestion",
            "summary": "Répondre à la question d'un rendu",
            "description": "Lance un NOUVEAU rendu, dans la même conversation, "
                           "avec la précision ajoutée. Lire son « id ».",
            "parameters": [p_tid],
            "requestBody": {"required": True,
                            "content": _json(_ref("schemas", "ReponseQuestion"))},
            "responses": dict(_communes(400, 409, 413, 422),
                              **{"202": rendu_cree,
                                 "200": _ref("responses", "UnRendu"),
                                 "404": _ref("responses", "Inconnu")})}},
        "/api/v1/rendus/{tid}/fichiers/{rang}": {"get": {
            "operationId": "telechargerFichier",
            "summary": "Télécharger un fichier d'un rendu",
            "parameters": [p_tid, _ref("parameters", "rang")],
            "responses": dict(_communes(),
                              **{"200": _ref("responses", "UnFichier"),
                                 "404": _ref("responses", "Inconnu")})}},
        "/api/v1/fichiers": {"post": {
            "operationId": "televerserImage",
            "summary": "Envoyer une image à retoucher, agrandir, animer…",
            "description": "Multipart : le premier champ qui porte un nom de "
                           "fichier. Rend le nom à passer dans « image ».",
            "requestBody": {"required": True, "content": {
                "multipart/form-data": {"schema": {
                    "type": "object",
                    "properties": {"fichier": {
                        "type": "string", "contentMediaType":
                            "application/octet-stream"}}}}}},
            "responses": dict(_communes(400, 413), **{
                "200": {"description": "Déposé.",
                        "content": _json(_ref("schemas", "Televersement"))}})}},
        "/api/v1/moteurs": {"get": {
            "operationId": "listerMoteurs",
            "summary": "Les moteurs, tailles et priorités que cette clé peut "
                       "demander",
            "responses": dict(_communes(), **{
                "200": {"description": "La liste.",
                        "content": _json(_ref("schemas", "Moteurs"))}})}},
        "/api/v1/moi": {"get": {
            "operationId": "lireCle",
            "summary": "La clé présentée, son compte, ses compteurs",
            "responses": dict(_communes(), **{
                "200": {"description": "La fiche.",
                        "content": _json(_ref("schemas", "Moi"))}})}},
        "/api/v1/lien/{jeton}": {"get": {
            "operationId": "lireLienSigne",
            "summary": "Un fichier par lien signé, sans en-tête",
            "description": f"Le lien porte sa preuve : la clé, le rendu, le "
                           f"fichier, la date de fin ({LIEN_DUREE // 3600} h). "
                           f"Il meurt avec sa clé.",
            "security": [],
            "parameters": [_ref("parameters", "jeton")],
            "responses": {"200": _ref("responses", "UnFichier"),
                          "404": _ref("responses", "Inconnu")}}},
        "/api/v1/openapi.json": {"get": {
            "operationId": "lireContrat",
            "summary": "Ce document",
            "security": [],
            "responses": {"200": {
                "description": "OpenAPI 3.1, JSON.",
                "content": _json({"type": "object"})}}}},
        "/mcp": {"post": {
            "operationId": "mcp",
            "summary": "MCP (Model Context Protocol), transport Streamable HTTP",
            "description": (
                "Un message JSON-RPC par POST, une réponse JSON ; pas de flux "
                "SSE, pas de session. Révisions acceptées : "
                + ", ".join(_mcp.VERSIONS) + " (pas 2026-07-28). Outils : "
                "generer_rendu (lance un rendu et attend au plus « attendre » "
                f"secondes, {ATTENDRE_MCP} par défaut), etat_rendu (suit un "
                "rendu), repondre_question (répond à l'état « question »), "
                "annuler_rendu, lister_moteurs. tools/list fait foi."),
            "parameters": [_ref("parameters", "McpVersion")],
            "requestBody": {"required": True,
                            "content": _json(_ref("schemas", "JsonRpc"))},
            "responses": {
                "200": {"description": "La réponse JSON-RPC.",
                        "content": _json(_ref("schemas", "JsonRpc"))},
                "202": {"description": "Une notification : pas de corps."},
                "400": {"description": "Version MCP refusée (erreur JSON-RPC "
                                       "-32600) ou corps illisible (-32700).",
                        "content": _json(_ref("schemas", "JsonRpc"))},
                "401": _ref("responses", "SansCle")}}},
    }


def _rappel():
    entetes = [
        {"name": _rappels.ENTETE_SIGNATURE, "in": "header", "required": True,
         "description": "« t=<horodatage>,v1=<HMAC-SHA256 hex> », signé sur "
                        "« <t>.<corps brut> » avec le secret de rappel de la "
                        f"clé. Tolérance : {_rappels.TOLERANCE} s.",
         "schema": {"type": "string"}},
        {"name": _rappels.ENTETE_EVENEMENT, "in": "header", "required": True,
         "schema": {"type": "string", "enum": list(_rappels.EVENEMENTS)}},
        {"name": _rappels.ENTETE_LIVRAISON, "in": "header", "required": True,
         "description": "Le même d'un essai à l'autre : dédupliquer dessus.",
         "schema": {"type": "string"}},
    ]
    essais = ", ".join(str(d) for d in _rappels.DELAIS)
    return {"rendu": {"post": {
        "operationId": "rappelRendu",
        "summary": "Le studio prévient l'URL « rappel » qu'un rendu est fini",
        "description": (
            f"Un POST à la fin du rendu (fini, erreur, question, annule). "
            f"Attentes avant chaque essai : {essais} s ; réessayé sur 408, "
            f"425, 429, 5xx, délai ({_rappels.DELAI_REPONSE} s) ou "
            f"injoignable ; jamais de redirection suivie. Non persisté : un "
            f"studio qui s'arrête pendant les essais perd ce rappel."),
        "parameters": entetes,
        "requestBody": {"required": True,
                        "content": _json(_ref("schemas", "EvenementRappel"))},
        "responses": {"200": {"description": "Tout 2xx vaut livré."}}}}}


def document(base: str = "") -> dict:
    """Le document OpenAPI 3.1, neuf a chaque appel.

    « base » est l'adresse du studio telle que le client l'a jointe
    (base_publique dans serveur.py). Vide, le document ne nomme aucun serveur :
    la spec dit alors « / », c'est-a-dire l'origine d'ou on l'a lu — ce qui
    reste juste pour un client qui l'a recu du studio lui-meme.
    """
    doc = {
        "openapi": VERSION_OPENAPI,
        "info": {
            "title": "ComfyStudio — pilotage par programme",
            "version": "1",
            "description": (
                "Demander des rendus (images, vidéos, musique, objets 3D, "
                "retouches) à un studio ComfyStudio depuis un programme : n8n, "
                "un assistant IA, un script. Une clé d'accès par programme, "
                "créée par son propriétaire dans la page (mot de passe et "
                "second facteur). La clé ne vaut que sur /api/v1 et /mcp, "
                "jamais pour l'administration, et ne voit que les rendus "
                "qu'elle a demandés. Documentation : "
                "docs/piloter-par-programme.md."),
            "license": {"name": "AGPL-3.0-only",
                        "identifier": "AGPL-3.0-only"},
        },
        "security": [{"bearerAuth": []}],
        "paths": _chemins(),
        "webhooks": _rappel(),
        "components": {
            "securitySchemes": {"bearerAuth": {
                "type": "http", "scheme": "bearer",
                "bearerFormat": "cs_<8 hex>_<43 caractères>",
                "description": "Une clé d'accès, dans « Authorization: Bearer "
                               "cs_… ». Jamais dans l'adresse ni un cookie."}},
            "schemas": _schemas(),
            "parameters": _parametres(),
            "responses": _reponses(),
        },
    }
    if base:
        doc["servers"] = [{"url": base, "description": "ce studio"}]
    return doc
