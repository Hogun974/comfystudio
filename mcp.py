# -*- coding: utf-8 -*-
"""La couche protocole de MCP (Model Context Protocol), cote serveur.

POURQUOI CE MODULE EXISTE. Un assistant IA — Claude Desktop, Claude Code, le
noeud « MCP Client » d'un agent n8n, tout client MCP — ne sait pas remplir un
formulaire du studio : il sait appeler des OUTILS, decrits par un nom et un
schema JSON, et lire ce qu'ils rendent. MCP est le contrat de cet echange. Ce
fichier en ecrit la moitie serveur : un message JSON-RPC 2.0 entre, une reponse
sort. serveur.py s'occupe de tout ce qui est HTTP — la route /mcp, la cle
d'acces, les en-tetes, le code de statut — et ne fait qu'appeler traiter().

POURQUOI A LA MAIN ET NON LE SDK OFFICIEL. Le SDK Python de MCP tire pydantic,
starlette, anyio, httpx et une demi-douzaine d'autres paquets ; le studio doit
demarrer sur un NAS sans pip, avec aiohttp pour seule dependance. Et la partie
qui nous sert est petite : trois methodes (initialize, tools/list,
tools/call), un ping, deux notifications. Elle tient ici et se relit en
entier, ce qui n'est pas vrai d'un SDK dont on n'utiliserait qu'un vingtieme.

LES VERSIONS SUIVIES, ET CELLE QUI NE L'EST PAS. Spec relue le 4 novembre 2026
sur modelcontextprotocol.io. Ce module parle les revisions « a poignee de
main » 2025-03-26, 2025-06-18 et 2025-11-25 : le client ouvre par initialize,
le serveur repond sa version, ses capacites et son identite. La revision
COURANTE de la spec est pourtant 2026-07-28, et elle n'est PAS ici, par choix :
elle supprime initialize et ping, rend server/discover obligatoire, exige la
version et les capacites du client dans le _meta de CHAQUE requete, un champ
resultType dans chaque resultat et ttlMs/cacheScope sur tools/list. C'est un
autre protocole, pas une option du premier ; le declarer dans VERSIONS sans en
suivre les regles serait mentir a un client qui nous croirait. La spec prevoit
justement ce cas (« Backward Compatibility », transport Streamable HTTP) : un
client des deux epoques essaie d'abord une requete moderne, et s'il recoit un
400 dont le corps n'est PAS une erreur moderne reconnue, il retombe sur
initialize. version_acceptee() et refus_de_version() sont ecrits pour que ce
repli ait lieu — voir leurs docstrings.

CE QU'IL NE FAIT PAS :
  - aucun transport : ni HTTP, ni SSE, ni stdio. Une reponse est un dict, le
    serveur la serialise ;
  - aucune session (pas de MCP-Session-Id) : chaque message se traite seul, ce
    que la spec permet — l'en-tete de session est un « MAY » du serveur ;
  - aucun lot JSON-RPC : MCP les a retires en 2025-06-18 (changelog,
    « Remove support for JSON-RPC batching », PR #416) ;
  - ni ressources, ni prompts, ni sampling, ni elicitation, ni taches : le
    studio n'expose que des outils, et declarer une capacite qu'on ne sert pas
    ferait appeler des methodes qui rendraient -32601 ;
  - pas de pagination de tools/list : une poignee d'outils ;
  - pas d'annulation : notifications/cancelled est accepte et ignore. Un outil
    du studio confie un rendu a la file et rend la main ; ce qui tourne ensuite
    ne depend plus de la requete MCP qui l'a demande.
"""
import inspect
import json
import math
import re
import sys
import traceback

# La plus recente d'abord : c'est elle qu'initialize propose quand le client en
# demande une qu'on ne connait pas — la spec 2025-11-25 (lifecycle, « Version
# Negotiation ») dit que le serveur « MUST respond with another protocol
# version it supports. This SHOULD be the latest version supported by the
# server ». 2026-07-28 n'y est pas : voir l'en-tete du module.
#
# 2025-03-26 RESTE, et pas seulement par politesse envers les vieux clients :
# c'est la version que la spec dit d'assumer quand l'en-tete
# MCP-Protocol-Version manque (transports, « Protocol Version Header »). La
# retirer d'ici ferait accepter, par version_acceptee(None), une version que le
# module ne declare pas.
VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26")
VERSION_PAR_DEFAUT = "2025-03-26"

NOM_SERVEUR = "comfystudio"

# Les codes de JSON-RPC 2.0 (jsonrpc.org/specification, section 5.1), les seuls
# dont ce module a besoin. -32700 n'est jamais rendu par traiter(), qui recoit
# un message deja analyse : il est la pour serveur.py, qui decode le corps.
CODE_ANALYSE = -32700
CODE_REQUETE = -32600
CODE_METHODE = -32601
CODE_PARAMETRES = -32602

# Ce qu'une reponse reprend d'une chaine fournie par le client (nom de methode,
# nom d'outil, en-tete). Assez pour reconnaitre sa faute, pas assez pour qu'un
# client renvoie dix kilo-octets dans un message d'erreur.
ECHO_MAX = 80

# Les noms d'outils que la spec 2025-11-25 recommande (« Tool Names ») : 1 a 128
# caracteres, lettres ASCII, chiffres, « _ », « - » et « . ». Un nom hors de
# cette forme marche chez certains clients et pas chez d'autres — l'API de
# Claude, par exemple, refuse les noms d'outils a espace.
_NOM_OUTIL = re.compile(r"[A-Za-z0-9_.-]{1,128}")

_TYPES = ("string", "integer", "number", "boolean", "array")

# Les mots d'un schema que valider_arguments() ne fait que lire pour un humain.
_ANNOTATIONS = {"description", "title", "default", "examples"}

# Les mots que valider_arguments() FAIT RESPECTER, par type. outil() refuse
# tout autre mot : un « pattern » ou un « exclusiveMinimum » ecrit dans un
# schema et que personne n'applique est une garde qu'on croit avoir.
_MOTS_PROPRIETE = {
    None: {"type", "enum"},
    "string": {"minLength", "maxLength"},
    "integer": {"minimum", "maximum"},
    "number": {"minimum", "maximum"},
    "boolean": set(),
    "array": {"items", "minItems", "maxItems"},
}
_MOTS_OBJET = {"type", "properties", "required", "additionalProperties"}


class ErreurOutil(ValueError):
    """Un refus qu'un outil sait expliquer : « ce rendu n'existe pas ».

    Son message est MONTRE AU MODELE, tel quel, dans un resultat isError : il
    doit donc dire quoi corriger, et ne rien contenir qu'on ne montrerait pas a
    l'auteur de la requete. Toute autre exception levee par un outil est
    remplacee par un message generique.
    """


# ── Les blocs de contenu ─────────────────────────────────────────────────
# Formes de la spec 2025-11-25, « Tool Result ». resource_link n'existe que
# depuis 2025-06-18 : un client 2025-03-26 strict peut refuser un resultat qui
# en contient. Un outil qui rend un lien() fait donc bien d'ajouter un texte()
# qui porte la meme adresse.
def texte(t):
    return {"type": "text", "text": t}


def image(donnees_b64, type_mime):
    return {"type": "image", "data": donnees_b64, "mimeType": type_mime}


def lien(uri, nom, type_mime=None, description=None):
    bloc = {"type": "resource_link", "uri": uri, "name": nom}
    # Omis plutot que null : le schema de la spec les declare optionnels, pas
    # « nullables », et un client qui valide refuserait un null.
    if type_mime is not None:
        bloc["mimeType"] = type_mime
    if description is not None:
        bloc["description"] = description
    return bloc


# ── La definition d'un outil ─────────────────────────────────────────────
def _verifie_propriete(nom, schema):
    """Leve ValueError si ce schema de propriete sort de ce qu'on sait valider."""
    if not isinstance(schema, dict):
        raise ValueError(f"propriete {nom} : le schema doit etre un objet")
    genre = schema.get("type")
    if genre is not None and genre not in _TYPES:
        raise ValueError(f"propriete {nom} : type {genre!r} non pris en charge")
    if genre is None and "enum" not in schema:
        # Une propriete sans type ni enum accepte n'importe quoi, y compris un
        # objet de dix mega-octets : c'est presque toujours un oubli.
        raise ValueError(f"propriete {nom} : ni type ni enum")
    permis = _ANNOTATIONS | _MOTS_PROPRIETE[None] | _MOTS_PROPRIETE.get(genre, set())
    inconnus = sorted(set(schema) - permis)
    if inconnus:
        raise ValueError(f"propriete {nom} : mots non appliques {inconnus}")
    if "enum" in schema and (not isinstance(schema["enum"], list)
                             or not schema["enum"]):
        raise ValueError(f"propriete {nom} : enum doit etre une liste non vide")
    if "items" in schema:
        _verifie_propriete(f"{nom}[]", schema["items"])


def outil(nom, titre, description, schema, appel):
    """Un outil tel que traiter() le sert. Leve ValueError a la construction.

    LES REFUS SONT ICI, AU DEMARRAGE, ET PAS A L'APPEL. Un schema qui promet une
    garde que valider_arguments() n'applique pas, un nom que certains clients
    refusent, un appel synchrone qui bloquerait la boucle du studio : chacun
    serait invisible jusqu'au jour ou un modele s'y heurte. Ici, le studio ne
    demarre pas, et la faute porte son nom.
    """
    if not isinstance(nom, str) or not _NOM_OUTIL.fullmatch(nom):
        raise ValueError(f"nom d'outil hors de la forme de la spec : {nom!r}")
    if not isinstance(schema, dict) or schema.get("type") != "object":
        # La spec 2025-11-25 : inputSchema « MUST be a valid JSON Schema
        # object », et les arguments d'un tools/call sont toujours un objet.
        raise ValueError(f"{nom} : le schema doit etre de type object")
    inconnus = sorted(set(schema) - _MOTS_OBJET - _ANNOTATIONS)
    if inconnus:
        raise ValueError(f"{nom} : mots non appliques {inconnus}")
    proprietes = schema.get("properties", {})
    if not isinstance(proprietes, dict):
        raise ValueError(f"{nom} : properties doit etre un objet")
    for cle, sous in proprietes.items():
        _verifie_propriete(cle, sous)
    requis = schema.get("required", [])
    absents = [r for r in requis if r not in proprietes]
    if absents:
        # Un argument obligatoire que le schema ne decrit pas : le modele ne
        # peut pas deviner son type, et avec additionalProperties False il ne
        # peut meme pas l'envoyer. L'outil serait inappelable.
        raise ValueError(f"{nom} : obligatoires non decrits {absents}")
    if not isinstance(schema.get("additionalProperties", True), bool):
        raise ValueError(f"{nom} : additionalProperties doit etre un booleen")
    if not inspect.iscoroutinefunction(appel):
        raise ValueError(f"{nom} : l'appel doit etre une fonction async")
    return {"name": nom, "title": titre, "description": description,
            "inputSchema": schema, "appel": appel}


# ── La validation des arguments ──────────────────────────────────────────
def _nom_du_type(v):
    # bool avant int : en Python, True est un int.
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "booléen"
    if isinstance(v, int):
        return "entier"
    if isinstance(v, float):
        return "nombre"
    if isinstance(v, str):
        return "chaîne"
    if isinstance(v, list):
        return "liste"
    if isinstance(v, dict):
        return "objet"
    return type(v).__name__


def _bon_type(v, genre):
    """Le test de type, sans le piege de Python : isinstance(True, int) vaut
    True, et un booleen passerait pour un entier — « largeur: true » deviendrait
    une image d'un pixel de large."""
    if genre == "string":
        return isinstance(v, str)
    if genre == "integer":
        # PLUS STRICT QUE JSON SCHEMA, et c'est voulu : la 2020-12 tient 3.0
        # pour un entier, mais l'outil recevrait un float Python et
        # range(3.0) leverait. Un client JavaScript n'envoie jamais 3.0 (
        # JSON.stringify ecrit « 3 ») ; un client Python qui le ferait recoit
        # une faute qu'il peut corriger.
        return isinstance(v, int) and not isinstance(v, bool)
    if genre == "number":
        # NaN et l'infini : json.loads les accepte par defaut, et NaN echappe a
        # toute comparaison — « NaN < 1 » et « NaN > 1 » sont faux tous deux,
        # donc minimum et maximum le laisseraient passer.
        return (isinstance(v, (int, float)) and not isinstance(v, bool)
                and math.isfinite(v))
    if genre == "boolean":
        return isinstance(v, bool)
    if genre == "array":
        return isinstance(v, list)
    return False


def _egal(a, b):
    # « True in [0, 1] » vaut True en Python. Pour JSON Schema, un booleen
    # n'est egal qu'a un booleen ; 1 et 1.0, eux, sont le meme nombre.
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a is b
    if isinstance(a, (int, float)) != isinstance(b, (int, float)):
        return False
    return a == b


_NOM_TYPE_ATTENDU = {"string": "une chaîne", "integer": "un entier",
                     "number": "un nombre fini", "boolean": "un booléen",
                     "array": "une liste"}


def _fautes_valeur(chemin, v, schema):
    genre = schema.get("type")
    if genre is not None and not _bon_type(v, genre):
        return [f"« {chemin} » doit être {_NOM_TYPE_ATTENDU[genre]} "
                f"(reçu : {_nom_du_type(v)})"]
    fautes = []
    if "enum" in schema and not any(_egal(v, e) for e in schema["enum"]):
        permis = ", ".join(json.dumps(e, ensure_ascii=False)
                           for e in schema["enum"])
        fautes.append(f"« {chemin} » doit valoir l'une de ces valeurs : {permis}")
    if genre in ("integer", "number"):
        if "minimum" in schema and v < schema["minimum"]:
            fautes.append(f"« {chemin} » vaut {v}, le minimum est {schema['minimum']}")
        if "maximum" in schema and v > schema["maximum"]:
            fautes.append(f"« {chemin} » vaut {v}, le maximum est {schema['maximum']}")
    if genre == "string":
        # len() compte les points de code, comme JSON Schema le demande ; un
        # emoji fait un caractere, et non deux comme en JavaScript.
        if "minLength" in schema and len(v) < schema["minLength"]:
            fautes.append(f"« {chemin} » fait {len(v)} caractères, "
                          f"au moins {schema['minLength']} attendus")
        if "maxLength" in schema and len(v) > schema["maxLength"]:
            fautes.append(f"« {chemin} » fait {len(v)} caractères, "
                          f"au plus {schema['maxLength']} permis")
    if genre == "array":
        if "minItems" in schema and len(v) < schema["minItems"]:
            fautes.append(f"« {chemin} » a {len(v)} éléments, "
                          f"au moins {schema['minItems']} attendus")
        if "maxItems" in schema and len(v) > schema["maxItems"]:
            fautes.append(f"« {chemin} » a {len(v)} éléments, "
                          f"au plus {schema['maxItems']} permis")
        if "items" in schema:
            for i, x in enumerate(v):
                fautes += _fautes_valeur(f"{chemin}[{i}]", x, schema["items"])
    return fautes


def valider_arguments(schema, arguments):
    """Les fautes des arguments au regard du schema, en francais. Vide = valide.

    Un SOUS-ENSEMBLE de JSON Schema 2020-12, celui que outil() laisse ecrire :
    rien de ce qu'un schema d'outil du studio peut contenir n'est ignore ici.
    Les messages sont faits pour un modele de langage qui va se corriger : ils
    nomment l'argument, ce qui etait attendu et ce qui a ete recu — le TYPE recu,
    jamais la valeur, qui peut etre une invite de dix mille caracteres.
    """
    if not isinstance(arguments, dict):
        return [f"les arguments doivent être un objet (reçu : "
                f"{_nom_du_type(arguments)})"]
    proprietes = schema.get("properties", {})
    fautes = [f"« {r} » est obligatoire" for r in schema.get("required", [])
              if r not in arguments]
    if schema.get("additionalProperties", True) is False:
        connus = ", ".join(proprietes) or "aucun"
        fautes += [f"« {k} » n'est pas un argument de cet outil "
                   f"(arguments connus : {connus})"
                   for k in arguments if k not in proprietes]
    for cle, sous in proprietes.items():
        if cle in arguments:
            fautes += _fautes_valeur(cle, arguments[cle], sous)
    return fautes


# ── L'en-tete de version ─────────────────────────────────────────────────
def version_acceptee(entete):
    """L'en-tete HTTP MCP-Protocol-Version convient-il ? False -> 400.

    ABSENT, IL CONVIENT : la spec 2025-11-25 (transports, « Protocol Version
    Header ») dit qu'un serveur qui ne recoit pas l'en-tete « SHOULD assume
    protocol version 2025-03-26 ». C'est le cas de la requete initialize
    elle-meme, que le client envoie avant de connaitre la version, et de tout
    client 2025-03-26, ou l'en-tete n'existait pas encore.

    PRESENT ET INCONNU, IL NE CONVIENT PAS : « If the server receives a request
    with an invalid or unsupported MCP-Protocol-Version, it MUST respond with
    400 Bad Request ». C'est aussi ce 400 qui fait retomber un client 2026-07-28
    sur initialize — voir refus_de_version().
    """
    if entete is None:
        return True
    return isinstance(entete, str) and entete.strip() in VERSIONS


def _court(s):
    s = str(s)
    return s if len(s) <= ECHO_MAX else s[:ECHO_MAX] + "…"


def erreur(code, message, id_=None, donnees=None):
    """Une reponse d'erreur JSON-RPC. id_ None quand l'id n'a pas pu etre lu :
    JSON-RPC 2.0 (section 5) demande alors « id: null », et non l'absence."""
    corps = {"code": code, "message": message}
    if donnees is not None:
        corps["data"] = donnees
    return {"jsonrpc": "2.0", "id": id_, "error": corps}


def refus_de_version(entete):
    """Le corps du 400 que serveur.py rend quand version_acceptee() refuse.

    PAS -32022, ET C'EST LE POINT. -32022 est l'UnsupportedProtocolVersionError
    de la revision 2026-07-28. Un client des deux epoques qui essaie d'abord une
    requete moderne lit le corps du 400 : s'il y trouve une erreur moderne
    reconnue, il conclut que le serveur est moderne et RE-ESSAIE en moderne,
    sans jamais tenter initialize ; s'il n'en trouve pas, il retombe sur
    initialize (spec 2026-07-28, Streamable HTTP, « Backward Compatibility »).
    Rendre -32022 ici, par souci de bien faire, enfermerait ce client dehors.
    -32600 est une erreur JSON-RPC ordinaire, d'avant MCP, que tout client
    reconnait comme « pas moderne ».

    Le message nomme les versions acceptees, comme la spec le recommande a un
    serveur qui refuse : c'est souvent le seul diagnostic que le client
    montrera.
    """
    return erreur(CODE_REQUETE,
                  f"Bad Request : version du protocole MCP non prise en charge "
                  f"(« {_court(entete)} ») ; versions acceptées : "
                  f"{', '.join(VERSIONS)}")


# ── Le traitement d'un message ───────────────────────────────────────────
def _id_lisible(id_):
    # MCP 2025-11-25 (basic, « Requests ») : « Requests MUST include a string
    # or integer ID » et « Unlike base JSON-RPC, the ID MUST NOT be null ».
    # Un booleen n'est ni l'un ni l'autre, quoi qu'en dise isinstance.
    return isinstance(id_, str) or (isinstance(id_, int)
                                    and not isinstance(id_, bool))


def _signaler_par_defaut(nom, exc):
    # Le journal du studio est la sortie standard ; la trace y va, et nulle
    # part ailleurs.
    print(f"[mcp] l'outil {nom} a echoue : "
          + "".join(traceback.format_exception(
              type(exc), exc, exc.__traceback__)).rstrip(),
          file=sys.stderr, flush=True)


def _signale(signaler, nom, exc):
    # Un journal qui leve ne doit pas emporter la reponse : le client attend
    # toujours la sienne.
    try:
        (signaler or _signaler_par_defaut)(nom, exc)
    except Exception:
        pass


def _echec_generique(nom):
    return {"content": [texte(f"L'outil « {nom} » a échoué. Le détail est "
                              f"noté dans le journal du studio.")],
            "isError": True}


async def _appeler(params, outils, contexte, signaler):
    """(resultat, None) ou (None, erreur JSON-RPC sans id)."""
    nom = params.get("name")
    if not isinstance(nom, str):
        return None, (CODE_PARAMETRES, "Invalid params : « name » manque ou "
                                       "n'est pas une chaîne")
    trouve = next((o for o in outils if o["name"] == nom), None)
    if trouve is None:
        # Spec 2025-11-25, tools, « Error Handling » : un outil inconnu est une
        # erreur de PROTOCOLE, et l'exemple qu'elle donne est -32602.
        return None, (CODE_PARAMETRES, f"Unknown tool : {_court(nom)}")
    arguments = params.get("arguments", {})
    if not isinstance(arguments, dict):
        # Une requete qui ne satisfait pas le schema de CallToolRequest
        # (« arguments » y est un objet) est, elle aussi, une erreur de
        # protocole selon la meme section.
        return None, (CODE_PARAMETRES, "Invalid params : « arguments » doit "
                                       "être un objet")
    fautes = valider_arguments(trouve["inputSchema"], arguments)
    if fautes:
        # PAS -32602, ET LA SPEC LE DIT DEPUIS 2025-11-25 (changelog, SEP-1303 :
        # « input validation errors should be returned as Tool Execution Errors
        # rather than Protocol Errors to enable model self-correction »). Les
        # clients montrent un resultat isError au modele, qui se corrige ; une
        # erreur JSON-RPC, ils la montrent a l'humain ou l'avalent. La 2025-06-18
        # rangeait encore « Invalid arguments » parmi les erreurs de protocole :
        # on applique la regle recente a toutes les versions, puisqu'un client
        # plus ancien lit un resultat isError sans difficulte.
        return {"content": [texte(f"Arguments invalides pour « {nom} » :\n- "
                                  + "\n- ".join(fautes))],
                "isError": True}, None
    try:
        resultat = await trouve["appel"](arguments, contexte)
    except ErreurOutil as e:
        return {"content": [texte(str(e) or f"L'outil « {nom} » a refusé "
                                            f"la demande.")],
                "isError": True}, None
    except Exception as e:
        # TOUTE AUTRE EXCEPTION EST MUETTE POUR LE CLIENT. Son texte peut porter
        # un chemin du NAS, un nom de machine, l'adresse d'un noeud de calcul :
        # le modele n'en ferait rien, et la reponse sort du reseau local.
        #
        # « Exception » et non « BaseException » : asyncio.CancelledError en
        # descend directement depuis Python 3.8, et doit traverser — l'avaler
        # ferait repondre une requete que le serveur abandonne, et retiendrait
        # l'arret du studio. KeyboardInterrupt et SystemExit de meme.
        _signale(signaler, nom, e)
        return _echec_generique(nom), None
    if not isinstance(resultat, dict) or not isinstance(
            resultat.get("content", []), list):
        _signale(signaler, nom,
                 TypeError(f"resultat mal forme : {type(resultat).__name__}"))
        return _echec_generique(nom), None
    rendu = dict(resultat)
    # « content » est OBLIGATOIRE dans CallToolResult, meme quand l'outil ne
    # rend que structuredContent : un client qui valide refuse sinon tout le
    # resultat.
    rendu.setdefault("content", [])
    try:
        # LA REPONSE DOIT ETRE DU JSON PUR. Un outil qui glisse des octets, un
        # ensemble ou un NaN ferait lever json.dumps dans serveur.py, APRES
        # traiter() : le client recevrait un 500 sans corps JSON-RPC, et le
        # modele ne saurait rien. allow_nan=False parce que « NaN » sort de
        # json.dumps sans erreur mais n'est pas du JSON — JSON.parse le refuse.
        json.dumps(rendu, allow_nan=False)
    except (TypeError, ValueError) as e:
        _signale(signaler, nom, e)
        return _echec_generique(nom), None
    return rendu, None


async def traiter(message, outils, contexte, *, version_logiciel="",
                  instructions="", signaler=None):
    """La reponse JSON-RPC a un message, ou None quand il n'en faut aucune.

    None pour une notification (pas de cle « id ») et pour une REPONSE envoyee
    par le client : JSON-RPC interdit de repondre a l'une comme a l'autre, et la
    spec 2025-11-25 (transports) demande alors un 202 sans corps.

    « signaler(nom, exception) » recoit l'exception qu'un outil a levee et que
    le client ne verra pas ; par defaut, sa trace part sur la sortie d'erreur.
    """
    if not isinstance(message, dict):
        # Une liste serait un lot JSON-RPC : MCP n'en veut plus depuis
        # 2025-06-18. Une chaine ou un nombre n'est pas un message du tout.
        return erreur(CODE_REQUETE, "Invalid Request : le message doit être "
                                    "un objet JSON (les lots ne sont pas "
                                    "acceptés)")
    id_ = message.get("id")
    id_rendu = id_ if _id_lisible(id_) else None
    if message.get("jsonrpc") != "2.0":
        return erreur(CODE_REQUETE, "Invalid Request : « jsonrpc » doit valoir "
                                    "« 2.0 »", id_rendu)
    methode = message.get("method")
    if "method" not in message and ("result" in message or "error" in message):
        # Une reponse du client a une requete du serveur. Ce serveur n'en
        # envoie aucune, mais la spec permet au client d'en poster une, et y
        # repondre ouvrirait une partie de ping-pong entre deux pairs.
        return None
    if not isinstance(methode, str):
        return erreur(CODE_REQUETE, "Invalid Request : « method » manque ou "
                                    "n'est pas une chaîne", id_rendu)
    if "id" not in message:
        # notifications/initialized, notifications/cancelled, ou n'importe
        # quelle autre : rien a faire, et surtout rien a repondre — meme a une
        # methode inconnue. Un client qui recevrait une reponse a sa
        # notification la prendrait pour la reponse d'une autre requete.
        return None
    if not _id_lisible(id_):
        return erreur(CODE_REQUETE, "Invalid Request : « id » doit être une "
                                    "chaîne ou un entier")
    params = message.get("params", {})

    def resultat(r):
        return {"jsonrpc": "2.0", "id": id_, "result": r}

    if methode not in ("initialize", "ping", "tools/list", "tools/call"):
        return erreur(CODE_METHODE, f"Method not found : {_court(methode)}", id_)
    if not isinstance(params, dict):
        return erreur(CODE_PARAMETRES, "Invalid params : « params » doit être "
                                       "un objet", id_)

    if methode == "initialize":
        demandee = params.get("protocolVersion")
        # La regle de negociation : la meme si on la connait, sinon la plus
        # recente des notres, et c'est au client de decider s'il raccroche.
        version = demandee if demandee in VERSIONS else VERSIONS[0]
        r = {"protocolVersion": version,
             # listChanged False : la liste d'outils est fixee au demarrage, et
             # ce serveur sans flux SSE n'aurait de toute facon aucun moyen
             # d'envoyer notifications/tools/list_changed.
             "capabilities": {"tools": {"listChanged": False}},
             "serverInfo": {"name": NOM_SERVEUR, "title": "ComfyStudio",
                            "version": version_logiciel}}
        if instructions:
            r["instructions"] = instructions
        return resultat(r)
    if methode == "ping":
        # Spec, utilities/ping : le recepteur « MUST respond promptly with an
        # empty response ».
        return resultat({})
    if methode == "tools/list":
        # Les quatre cles publiques, et pas une de plus : « appel » est une
        # fonction, et json.dumps leverait sur elle. L'ordre est celui de la
        # liste, donc stable d'un appel a l'autre — ce qui laisse le client
        # (et le cache d'invite du modele) reutiliser ce qu'il a deja vu.
        return resultat({"tools": [
            {"name": o["name"], "title": o["title"],
             "description": o["description"], "inputSchema": o["inputSchema"]}
            for o in outils]})
    r, faute = await _appeler(params, outils, contexte, signaler)
    if faute is not None:
        return erreur(faute[0], faute[1], id_)
    return resultat(r)
