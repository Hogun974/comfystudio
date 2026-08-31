# -*- coding: utf-8 -*-
"""ComfyStudio — pilotage de ComfyUI en langage naturel.

Tu ecris ce que tu veux, en francais. Un modele local (Ollama) comprend l'intention, choisit le modele adapte, regle les parametres,
traduit et enrichit le prompt. Les fichiers manquants sont telecharges seuls.

Six intentions : image, edition d'image, video, image animee, musique, lecture
d'image. La conversation est memorisee, donc « la meme mais de nuit » fonctionne.

Portable : rien n'est installe, tout tient sous D:\\ComfyStudio et s'appuie sur
le Python embarque de ComfyUI.
"""
import asyncio, base64, json, os, re, secrets, shlex, subprocess, sys, time, uuid
import hashlib
import mimetypes
import urllib.parse
import unicodedata

# La console Windows ecrit en cp1252 : un seul ideogramme dans un prompt faisait
# echouer print() et emportait toute la requete. On force l'UTF-8 en sortie.
for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
from aiohttp import web
import aiohttp

ICI        = os.path.dirname(os.path.abspath(__file__))

# Ou ECRIRE. Gele par PyInstaller, ICI pointe sur un dossier temporaire qui est
# efface a l'arret : les conversations, les comptes et les cles y disparaissaient
# a chaque fermeture. Mesure : deux lancements de l'executable creaient deux
# comptes admin differents. Hors gel, les deux sont identiques et rien ne change.
ICI_DATA   = (os.path.dirname(os.path.abspath(sys.executable))
              if getattr(sys, "frozen", False) else ICI)
COMFY      = os.environ.get("COMFY_URL", "http://127.0.0.1:8188")
OLLAMA     = os.environ.get("OLLAMA_URL", "http://localhost:11434")
# Deux modeles, deux roles. L'aiguillage doit etre rapide : un petit modele suffit
# a produire du JSON structure. La lecture d'image exige la vision, d'ou un second
# modele, charge seulement quand une image doit etre decrite.
# qwen2.5vl plutot que bonsai-8b : mesure sur 16 tirages, bonsai remplace le
# sujet francais de facon reproductible (hibou -> hippopotamus aux 3 tirages,
# blaireau -> fox aux 3), ce qu'aucun garde-fou ne peut rattraper. qwen reste
# fidele au sujet ; ses defauts sont de forme (JSON tronque, prompt vide) et
# sont couverts par la relance de aiguiller() et le repli de normaliser().
# C'est aussi le modele de vision : un seul modele a charger.
MODELE_LLM    = os.environ.get("STUDIO_LLM", "qwen2.5vl:7b")
# Vide : le plus gros modele installe qui tienne en memoire sera pris au
# demarrage. Le renseigner impose un choix.
MODELE_ECRITURE = os.environ.get("STUDIO_LLM_ECRITURE", "")
MODELE_VISION = os.environ.get("STUDIO_VISION", "qwen2.5vl:7b")
PORT       = int(os.environ.get("STUDIO_PORT", "8199"))
# 127.0.0.1 : seule cette machine peut se connecter. 0.0.0.0 : tout le reseau
# local. Le studio n'a AUCUNE authentification — l'ouvrir au reseau donne a
# quiconque le joint le droit de generer, de televerser et de piloter ComfyUI.
# C'est un choix delibere, pas un defaut : d'ou la variable d'environnement.
HOTE       = os.environ.get("STUDIO_HOTE", "127.0.0.1")

# Chemins disque du noeud LOCAL. En conteneur, ComfyUI n'est pas un dossier
# voisin : COMFY_DIR pointe alors sur le volume monte, ou sur rien du tout si
# ComfyUI tourne ailleurs — dans ce cas le studio le traite comme une machine
# distante et tout passe par HTTP, telechargement de modeles excepte.
BASE_COMFY     = os.path.abspath(os.environ.get("COMFY_DIR") or
                                 os.path.join(ICI_DATA, "..", "ComfyUI_windows_portable", "ComfyUI"))
RACINE_MODELES = os.environ.get("COMFY_MODELES") or os.path.join(BASE_COMFY, "models")
DOSSIER_ENTREE = os.environ.get("COMFY_ENTREE") or os.path.join(BASE_COMFY, "input")

# ══════════════════════════════ catalogue ══════════════════════════════
# Le Python embarque de ComfyUI est pilote par un fichier ._pth qui fige
# sys.path : le dossier du script n'y figure PAS, et un import voisin echoue.
# On l'ajoute donc explicitement, ce qui ne coute rien ailleurs.
if ICI not in sys.path:
    sys.path.insert(0, ICI)
from catalogue import CATALOGUE, POIDS
# Meme raison : ces modules vivent a cote du script, pas dans le chemin fige.
import fournisseurs
import comptes as _comptes
import aiguilleur as _aiguilleur

# Classifieur d'intention, entraine hors ligne (voir entrainer_aiguilleur.py).
# None s'il n'a jamais ete construit : le studio fonctionne alors comme avant.
AIGUILLEUR = _aiguilleur.charger()

# Intentions qui ne demandent aucune ecriture : l'objet a traiter existe deja.
# Ce sont les seules ou reconnaitre suffit, donc les seules ou l'on se passe du
# modele de langage.
SANS_ECRITURE = ("agrandir", "detourer", "fluidifier")

NEG_DEFAUT = ("text, letters, writing, watermark, signature, gibberish script, "
              "deformed hands, extra fingers, blurry, low quality, jpeg artifacts")
NEG_WAN = ("色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，"
           "最差质量，低质量，JPEG压缩残留，丑陋的，残缺的，多余的手指，画得不好的手部，"
           "画得不好的脸部，畸形的，毁容的，形态畸形的肢体，手指融合，静止不动的画面")

TACHES = {}
# Tout ce que le studio ECRIT vit ici : conversations, comptes, cles, registre
# des noeuds, avis, sorties rapatriees. Un seul dossier, donc un seul chemin a
# autoriser dans une unite systemd durcie, et une seule chose a sauvegarder.
DOSSIER_DONNEES = os.environ.get("STUDIO_DONNEES") or ICI_DATA
# STUDIO_DONNEES a toujours designe DIRECTEMENT le dossier des conversations —
# c'est ce que monte le docker-compose. En faire un sous-dossier ferait
# disparaitre, aux yeux de leur proprietaire, les conversations, les comptes et
# les cles de toutes les installations existantes.
DOSSIER_CONV = os.environ.get("STUDIO_DONNEES") or os.path.join(ICI_DATA, "conversations")
# L'input de ComfyUI n'est qu'un CACHE pour le studio : les fichiers joints en
# repartent vers la machine qui calcule. Quand cette machine-ci n'a pas de
# ComfyUI, ce dossier n'existe pas et n'est pas inscriptible — joindre une image
# echouait alors sur « Permission denied ». On se rabat sur le dossier de
# donnees, que le studio possede par construction.
def _entree_utilisable(dossier):
    """Peut-on ecrire ici — sans rien creer pour le savoir.

    La version precedente faisait un makedirs avant de repondre : sur une
    machine sans ComfyUI, elle FABRIQUAIT l'arborescence, se declarait
    satisfaite, et le repli ne se declenchait jamais. L'executable Windows
    semait ainsi un faux arbre ComfyUI a cote de lui a chaque demarrage — l'un
    d'eux a fini dans le depot, invisible a git, qui ne suit pas les dossiers
    vides.

    On teste le dossier s'il existe, sinon son parent : c'est lui qui dira si
    l'on aurait le droit de creer.
    """
    if os.path.isdir(dossier):
        return os.access(dossier, os.W_OK)
    parent = os.path.dirname(dossier.rstrip(os.sep)) or "."
    return os.path.isdir(parent) and os.access(parent, os.W_OK)


if not _entree_utilisable(DOSSIER_ENTREE):
    DOSSIER_ENTREE = os.path.join(DOSSIER_DONNEES, "entrees")

CONVERSATIONS = {}          # id -> conversation
COURANTE = {}               # proprietaire -> id de sa conversation active
ENTREES = {}                # nom de fichier televerse -> proprietaire
_PID = re.compile(r"[0-9a-f]{32}")

# ── file d'attente : le GPU ne fait qu'une chose a la fois ────────────
FILE_ATTENTE = None         # asyncio.Queue, creee au demarrage
ATTENTE = []                # tids en attente, dans l'ordre
# Les travaux qui ont quitte la file et n'ont pas encore rendu. Un dictionnaire
# et non une place unique : le studio ne calcule plus rien lui-meme, il pilote
# des machines, et rien dans sa nature n'impose d'en occuper une seule a la fois.
# Il n'en lance toujours qu'un pour l'instant — ce registre ne change aucun
# comportement, il retire seulement la supposition qui l'interdisait.
EN_VOL = {}                 # tid -> asyncio.Task
# Le studio n'a plus de carte : il attend des machines, et attendre ne coute
# rien. Le nombre ne borne donc pas le materiel mais l'appetit — vingt demandes
# d'un coup n'ouvrent pas vingt analyses simultanees chez le modele de langage.
TRAVAILLEURS = max(1, int(os.environ.get("STUDIO_TRAVAILLEURS") or 3))

# Une carte ne se partage pas : deux travaux qui la visent attendent chacun leur
# tour. C'est la SEULE serialisation qui ait un sens physique — le studio, lui,
# peut analyser dix demandes pendant qu'une carte calcule.
VERROUS_NOEUD = {}          # id de machine -> asyncio.Lock
# Un fichier de modele non plus. Le fichier .part porte le nom du MODELE, pas
# celui du travail : deux telechargements du meme fichier, chacun avec son
# en-tete Range, se seraient ecrit dessus — plusieurs gigaoctets corrompus, et
# rien pour le dire avant que ComfyUI ne refuse de le charger.
VERROUS_MODELE = {}         # (sous-dossier, nom) -> asyncio.Lock
# Combien de temps une question au modele de langage accepte d'attendre la carte
# d'une machine occupee. Au-dela, elle va voir ailleurs : un rendu dure deux
# minutes, une question deux secondes, et faire attendre la seconde derriere le
# premier bloquait un travailleur pour rien.
ATTENTE_LLM = 20


def verrou_noeud(ident):
    """Le verrou de cette carte. Cree a la demande : les machines vont et
    viennent, et une machine qu'on n'a jamais vue n'a pas besoin du sien."""
    return VERROUS_NOEUD.setdefault(ident, asyncio.Lock())


def verrou_modele(sous, nom):
    return VERROUS_MODELE.setdefault((sous, nom), asyncio.Lock())
FICHIER_FILE = os.path.join(DOSSIER_CONV, "_file.json")
EN_FILE = {}                # tid -> de quoi refaire la demande apres un arret


def sauver_file():
    """Ecrit ce qui reste a faire. Appele a chaque entree et a chaque sortie :
    une file qui ne se sauve qu'a l'arret ne survit pas a une coupure."""
    tmp = FICHIER_FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump([EN_FILE[t] for t in ATTENTE if t in EN_FILE], f,
                      ensure_ascii=False, indent=1)
        os.replace(tmp, FICHIER_FILE)
    except OSError as e:
        print(f"  file d'attente non enregistree : {e}", flush=True)


async def reprendre_file():
    """Remet en file ce qui attendait avant l'arret.

    Appele apres le chargement des conversations : sans elles, on ne saurait pas
    a quel echange rattacher la demande.
    """
    try:
        with open(FICHIER_FILE, encoding="utf-8") as f:
            restes = json.load(f)
    except FileNotFoundError:
        return
    except Exception as e:
        print(f"  file d'attente illisible ({e}) — on repart a vide", flush=True)
        return
    repris = 0
    for r in restes if isinstance(restes, list) else []:
        conv = CONVERSATIONS.get(r.get("conversation"))
        if not conv or not isinstance(r.get("tid"), str):
            continue
        tid = r["tid"]
        TACHES[tid] = {"etapes": [], "etat": "en cours", "demande": r.get("texte", ""),
                       "conversation": conv["id"], "proprietaire": r.get("proprietaire"),
                       "image": r.get("image")}
        # Le tour existe deja dans la conversation, mais il a ete marque
        # « interrompu » au demarrage : on le remet en cours, sinon la demande
        # s'afficherait en echec pendant qu'elle calcule.
        for t in conv.get("tours", []):
            if t.get("id") == tid:
                t["etat"] = "en cours"
                t.pop("erreur", None)
        sauver(conv)
        EN_FILE[tid] = r
        ATTENTE.append(tid)
        await FILE_ATTENTE.put({"tid": tid, "texte": r.get("texte", ""), "conv": conv,
                                "image": r.get("image"), "modele": r.get("modele"),
                                "taille": r.get("taille"),
                                "priorite": r.get("priorite", ""),
                                "noeud": r.get("noeud")})
        repris += 1
    if repris:
        print(f"  {repris} demande(s) reprise(s) de la file d'avant l'arret",
              flush=True)
    sauver_file()

# Par TACHE, et non un jeu de compteurs unique : deux rendus simultanes
# s'ecrasaient mutuellement, et la fin de l'un remettait a zero la barre de
# l'autre. « total » a zero signifie « on ne sait pas » : l'interface n'affiche
# alors pas de barre plutot qu'une barre fausse.
AVANCES = {}                # tid -> {"fait", "total", "quoi"}
# 0 signifie « inconnue » : aucun ComfyUI n'a encore repondu. Une valeur en dur
# serait celle de la machine de developpement, et l'aiguilleur ecarterait des
# moteurs sur la foi d'une carte qui n'existe pas ici.
VRAM_GO = {"total": 0.0}    # VRAM du noeud local, relevee au demarrage
ADMIN_JETON = ""            # etabli par charger_registre()

# ── noeuds ────────────────────────────────────────────────────────────
# Le studio peut piloter plusieurs ComfyUI, sur des machines de puissances
# differentes. Le premier porte l'identifiant "local" et l'URL historique :
# c'est lui qui recoit les sorties d'avant le multi-noeuds, qui n'ont pas de
# nom de noeud enregistre. Ne pas changer cet identifiant.
FICHIER_NOEUDS = os.path.join(DOSSIER_DONNEES, "noeuds.json")

def _adresses_machine():
    """Toutes les adresses de cette machine, boucle locale comprise.

    Se limiter a 127.0.0.1 laissait un piege : une fois le studio ouvert au
    reseau, l'utilisateur atteint souvent sa propre machine par son adresse LAN,
    et perdait alors le droit d'adopter son historique ou de piloter ComfyUI.
    """
    adr = {"127.0.0.1", "::1"}
    try:
        import socket
        for info in socket.getaddrinfo(socket.gethostname(), None):
            adr.add(info[4][0])
    except Exception:
        pass
    return adr

ADRESSES_MACHINE = _adresses_machine()

_ID_NOEUD = re.compile(r"[A-Za-z0-9_-]{1,24}")
_HOTES_LOCAUX = ("127.0.0.1", "localhost", "::1")

def _lire_noeuds():
    """noeuds.json s'il existe, sinon le seul noeud local.

    Trois gardes, chacune pour une faute de frappe qui casserait tout en
    silence : un identifiant doit pouvoir servir de nom de fichier (il entre
    dans le prefixe des sorties), il ne doit pas y en avoir deux identiques
    (les deux partageraient un seul etat), et une URL sans schema ferait
    echouer chaque appel sans un mot.

    Le drapeau "local" est celui du fichier. Ne pas le deduire de la position :
    c'est lui qui autorise l'ecriture sur le disque du studio, donc les
    telechargements. Mal place, il fait telecharger dix gigaoctets pour une
    machine qui ne les verra jamais.
    """
    defaut = [{"id": "local", "url": COMFY, "titre": "cette machine", "local": True}]
    try:
        with open(FICHIER_NOEUDS, encoding="utf-8") as f:
            declares = json.load(f)
    except FileNotFoundError:
        return defaut
    except Exception as e:
        print(f"noeuds.json illisible ({e}) — un seul noeud local", flush=True)
        return defaut

    liste, vus = [], set()
    for d in declares if isinstance(declares, list) else []:
        ident = str(d.get("id") or "").strip()
        url = str(d.get("url") or "").strip().rstrip("/")
        if not _ID_NOEUD.fullmatch(ident):
            print(f"noeud ignore : identifiant invalide {ident!r} "
                  f"(lettres, chiffres, - et _ seulement)", flush=True)
            continue
        if ident in vus:
            print(f"noeud ignore : identifiant {ident!r} declare deux fois", flush=True)
            continue
        if not url:
            print(f"noeud {ident!r} ignore : pas d'URL", flush=True)
            continue
        if "://" not in url:
            url = "http://" + url
        vus.add(ident)
        liste.append({"id": ident, "url": url, "titre": d.get("titre") or ident,
                      "local": bool(d.get("local"))})
    if not liste:
        return defaut
    if not any(x["local"] for x in liste):
        # aucun n'est declare local : on reconnait celui qui pointe sur cette
        # machine plutot que de designer le premier venu
        for x in liste:
            hote = x["url"].split("//")[-1].split("/")[0].split(":")[0]
            x["local"] = hote in _HOTES_LOCAUX or hote in ADRESSES_MACHINE
        if not any(x["local"] for x in liste):
            print("aucun noeud local reconnu — le premier est retenu comme tel", flush=True)
            liste[0]["local"] = True
    return liste

NOEUDS = _lire_noeuds()
ETAT_NOEUDS = {}            # id -> {repond, vram, carte, vu}

def est_agent(ident):
    """Un noeud qui s'annonce de lui-meme, par jeton. Le studio n'a pas son
    adresse et n'en veut pas : c'est l'agent qui appelle."""
    return ident in REGISTRE


def tous_les_noeuds():
    """Ceux declares dans noeuds.json, plus ceux enregistres par jeton."""
    connus = {x["id"] for x in NOEUDS}
    agents = [{"id": x["id"], "titre": x.get("titre") or x["id"], "url": None,
               "local": False, "agent": True}
              for x in REGISTRE.values() if x["id"] not in connus]
    return NOEUDS + agents


def noeud(ident):
    """None si l'identifiant est inconnu. Retomber sur le premier noeud faisait
    partir la requete vers la mauvaise machine : le controle de propriete
    passait (le triplet est valide), et l'image servie n'etait pas la bonne."""
    return next((x for x in tous_les_noeuds() if x["id"] == ident), None)

def noeud_local():
    return next((x for x in NOEUDS if x.get("local")), NOEUDS[0])

def url_de(ident):
    x = noeud(ident)
    if x is None:
        raise RuntimeError(f"machine inconnue : {ident}")
    if not x.get("url"):
        raise RuntimeError(f"{ident} est un noeud a agent : le studio ne l'appelle pas")
    return x["url"]

def url_locale():
    return noeud_local()["url"]

def vram_de(ident):
    return ETAT_NOEUDS.get(ident, {}).get("vram") or 0.0

def est_local(ident):
    x = noeud(ident)
    return bool(x and x.get("local"))

def vram_max():
    """La plus grosse carte joignable. Prendre la VRAM d'un seul noeud rendait
    invisibles au LLM tous les modeles que la machine forte sait tenir."""
    dispo = [vram_de(x["id"]) for x in NOEUDS if ETAT_NOEUDS.get(x["id"], {}).get("repond")]
    return max(dispo) if dispo else VRAM_GO["total"]

def memoire_vive():
    """Memoire physique de la machine, en Go. 0 si on ne sait pas la lire."""
    try:
        if os.name == "nt":
            import ctypes

            class Etat(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong),
                            ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong),
                            ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong),
                            ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong),
                            ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

            e = Etat()
            e.dwLength = ctypes.sizeof(Etat)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(e))
            return e.ullTotalPhys / 1e9
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1e9
    except Exception:
        return 0.0


def _ollama_ici():
    """Vrai si Ollama tourne sur la machine du studio.

    On ne peut pas connaitre la memoire d'une machine qu'on ne fait qu'appeler :
    on lui fait confiance. Une machine ne telecharge pas un modele de vingt-six
    milliards de parametres si elle ne peut pas le charger.
    """
    hote = (urllib.parse.urlparse(OLLAMA).hostname or "").lower()
    return hote in ("127.0.0.1", "localhost", "::1", "")


# Les modeles qu'Ollama ne SAIT PAS charger, et pourquoi. Constate le 31 aout :
# « gemma4:26b » etait installe, annonce dans /api/tags, choisi comme modele
# d'ecriture — et llama-server mourait a chaque chargement
# (« Gemma4Assistant requires ctx_other to be set »), incompatibilite entre ce
# modele et cette version d'Ollama. Le studio le rappelait deux fois par demande,
# recevait deux fois rien, et concluait « je n'ai pas reussi a etoffer ta
# demande ». A chaque fois, sans jamais dire pourquoi.
#
# Un modele qui ne se charge pas ne se repare pas tout seul : on l'ecarte pour de
# bon, en le disant une fois.
MODELES_CASSES = {}


def choisir_modele_ecriture():
    """Le plus gros modele Ollama installe qui tienne raisonnablement ici.

    Ollama repartit les couches entre carte et processeur : un modele plus gros
    que la VRAM tourne quand meme, plus lentement. On borne donc a 60 % de la
    memoire vive, ce qui laisse de quoi faire tourner ComfyUI a cote — les deux
    ne s'executent jamais en meme temps, mais ils cohabitent en memoire.
    """
    global MODELE_ECRITURE
    if MODELE_ECRITURE:
        return MODELE_ECRITURE
    # Le plafond ne vaut que pour un Ollama LOCAL : c'est la memoire de CETTE
    # machine qu'il mesure. Quand Ollama tourne ailleurs — le cas des que le
    # studio n'a pas de carte — le borner ici ecartait un modele que la machine
    # d'en face charge sans effort, et le studio se rabattait sur un 7B qui
    # ecrit mal.
    plafond = (memoire_vive() or 16.0) * 0.6 if _ollama_ici() else float("inf")
    try:
        import urllib.request

        with urllib.request.urlopen(f"{OLLAMA}/api/tags", timeout=8) as r:
            modeles = json.load(r).get("models", [])
    except Exception:
        modeles = []
    tenables = [m for m in modeles if 0 < m.get("size", 0) / 1e9 <= plafond
                and m.get("name") not in MODELES_CASSES]
    if not tenables:
        MODELE_ECRITURE = MODELE_LLM
        return MODELE_ECRITURE
    gros = max(tenables, key=lambda m: m.get("size", 0))
    courant = next((m for m in modeles if m.get("name") == MODELE_LLM), None)
    # Ne changer que si le gain est net : recharger un modele a peine plus gros
    # coute du temps sans rien apporter a l'ecriture.
    if courant and gros.get("size", 0) < courant.get("size", 0) * 1.5:
        MODELE_ECRITURE = MODELE_LLM
    else:
        MODELE_ECRITURE = gros["name"]
    return MODELE_ECRITURE


def relever_vram():
    """Sonde synchrone du seul noeud local, au demarrage. Les noeuds distants
    sont sondes de facon asynchrone une fois la boucle lancee : un urlopen
    bloquant par machine injoignable retarderait le demarrage de 5 s chacune."""
    import urllib.request
    for x in NOEUDS:
        etat = ETAT_NOEUDS.setdefault(x["id"], {"repond": False, "vram": 0.0, "carte": None})
        if not x.get("local"):
            continue
        try:
            d = json.load(urllib.request.urlopen(f"{x['url']}/system_stats", timeout=5))
            for dev in d.get("devices", []):
                if "cuda" in str(dev.get("type", "")).lower() or dev.get("vram_total"):
                    etat.update(repond=True, carte=dev.get("name"),
                                vram=round(dev["vram_total"] / 1024 ** 3, 1),
                                ram=round(memoire_vive(), 1))
                    VRAM_GO["total"] = etat["vram"]
                    break
        except Exception:
            pass

async def sonder_noeud(x):
    """Etat d'un noeud : joignable, carte, VRAM totale et libre."""
    etat = ETAT_NOEUDS.setdefault(x["id"], {"repond": False, "vram": 0.0, "carte": None})
    try:
        to = aiohttp.ClientTimeout(total=6)
        async with aiohttp.ClientSession(timeout=to) as s:
            async with s.get(f"{x['url']}/system_stats") as r:
                d = await r.json()
        dev = next((v for v in d.get("devices", []) if v.get("vram_total")), {})
        etat.update(repond=True, carte=dev.get("name"),
                    vram=round(dev.get("vram_total", 0) / 1024 ** 3, 1),
                    libre=round(dev.get("vram_free", 0) / 1024 ** 3, 1))
        if x.get("local"):
            VRAM_GO["total"] = etat["vram"] or VRAM_GO["total"]
    except Exception:
        etat.update(repond=False, libre=0.0)
        # l'instantane des modeles ne vaut plus rien : la machine peut revenir
        # avec un contenu different
        MODELES_NOEUD.pop(x["id"], None)
    return etat

async def sonder_noeuds():
    await asyncio.gather(*(sonder_noeud(x) for x in NOEUDS))

def _vide(titre="Nouvelle conversation", proprietaire=None):
    return {"id": uuid.uuid4().hex[:12], "titre": titre, "proprietaire": proprietaire,
            "cree": time.strftime("%Y-%m-%d %H:%M"), "modifie": time.time(),
            "tours": [], "derniere_sortie": None}

def charger_conversations():
    os.makedirs(DOSSIER_CONV, exist_ok=True)
    for f in os.listdir(DOSSIER_CONV):
        if not f.endswith(".json") or f.startswith("_"):
            continue
        try:
            c = json.load(open(os.path.join(DOSSIER_CONV, f), encoding="utf-8"))
            # Les conversations anterieures au multi-utilisateurs n'ont pas de
            # proprietaire. Elles restent orphelines jusqu'a ce que quelqu'un
            # ouvre l'interface : le premier arrivant les adopte (voir adopter).
            c.setdefault("proprietaire", None)
            CONVERSATIONS[c["id"]] = c
        except Exception as e:
            print(f"conversation illisible ignoree : {f} ({e})", flush=True)
    interrompus = 0
    for c in CONVERSATIONS.values():
        touchee = False
        for t in c.get("tours", []):
            if t.get("etat") == "en cours":
                t["etat"] = "erreur"
                t["erreur"] = "interrompu par l'arret du studio"
                interrompus += 1
                touchee = True
        if touchee:
            sauver(c)
    if interrompus:
        print(f"  {interrompus} demande(s) laissee(s) en plan par un arret "
              f"precedent, marquee(s) comme interrompues", flush=True)

    orphelines = sum(1 for c in CONVERSATIONS.values() if not c.get("proprietaire"))
    if orphelines:
        print(f"  {orphelines} conversation(s) sans proprietaire — le premier "
              f"visiteur les adoptera", flush=True)

FICHIER_ENTREES = os.path.join(DOSSIER_CONV, "_entrees.json")

def charger_entrees():
    """En memoire seule, le registre disparaissait au redemarrage : les anciens
    fichiers n'etaient plus reconnus par personne, donc plus jamais purges, et
    ComfyUI/input gonflait a chaque relance."""
    try:
        with open(FICHIER_ENTREES, encoding="utf-8") as f:
            ENTREES.update({k: v for k, v in json.load(f).items()
                            if os.path.exists(os.path.join(DOSSIER_ENTREE, k))})
    except Exception:
        pass

def sauver_entrees():
    try:
        os.makedirs(DOSSIER_CONV, exist_ok=True)
        tmp = FICHIER_ENTREES + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(ENTREES, f)
        os.replace(tmp, FICHIER_ENTREES)
    except OSError:
        pass

def sauver(conv):
    conv["modifie"] = time.time()
    os.makedirs(DOSSIER_CONV, exist_ok=True)
    chemin = os.path.join(DOSSIER_CONV, conv["id"] + ".json")
    tmp = chemin + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(conv, f, ensure_ascii=False, indent=1)
    os.replace(tmp, chemin)     # ecriture atomique : pas de fichier tronque

def adopter(pid):
    """Une conversation sans proprietaire revient au navigateur de la machine hote.

    Ce n'est PAS un evenement unique. Une adoption a un coup rendait l'historique
    irrecuperable des qu'un client quelconque avait touche la page en premier :
    l'utilisateur se retrouvait devant une interface vide, sans recours. Ici,
    toute page ouverte depuis la machine hote reprend ce qui n'appartient a
    personne — et si rien n'est orphelin, la fonction ne fait rien.
    """
    reprises = [c for c in CONVERSATIONS.values() if not c.get("proprietaire")]
    if not reprises:
        return
    for c in reprises:
        c["proprietaire"] = pid
        sauver(c)
    print(f"  {len(reprises)} conversation(s) attribuee(s) a {pid[:8]}", flush=True)
    if reprises:
        print(f"  {len(reprises)} conversation(s) attribuee(s) au premier visiteur",
              flush=True)

def a_moi(conv, pid):
    return bool(conv) and conv.get("proprietaire") == pid


def ouvrable(conv, pid):
    """A moi ET pas fermee. Une fermee ne se rouvre pas : elle attend sa purge."""
    return a_moi(conv, pid) and not conv.get("ferme")

def mes_conversations(pid):
    # Une conversation fermee sort de la liste sur-le-champ : c'est ce qu'on
    # demande en fermant. Elle reste sur le disque jusqu'a la purge, mais plus
    # rien dans l'interface n'y mene.
    return [c for c in CONVERSATIONS.values() if a_moi(c, pid) and not c.get("ferme")]

def conv_de(cid, pid):
    """Ne leve jamais, mais ne franchit jamais la frontiere d'un utilisateur.

    L'ancienne version retombait sur la conversation courante globale quand
    l'identifiant etait inconnu : a plusieurs, cela revenait a ecrire dans la
    conversation de quelqu'un d'autre. Un identifiant inconnu ou etranger donne
    desormais une conversation neuve, a soi.
    """
    conv = CONVERSATIONS.get(cid)
    if ouvrable(conv, pid):
        return conv
    conv = CONVERSATIONS.get(COURANTE.get(pid))
    if ouvrable(conv, pid):
        return conv
    miennes = mes_conversations(pid)
    if miennes:
        conv = max(miennes, key=lambda c: c.get("modifie", 0))
    else:
        # en memoire seulement : enregistrer_tour l'ecrira au premier echange.
        # Sauvegardee ici, chaque requete sans cookie (curl, sonde, apercu de
        # lien) laissait un fichier de plus dans conversations/.
        conv = _vide(proprietaire=pid)
        CONVERSATIONS[conv["id"]] = conv
    COURANTE[pid] = conv["id"]
    return conv

def journal(tid, msg, **extra):
    """Une ligne dans le fil d'une demande, et dans le journal du studio.

    « tid » peut etre absent : poser_a() et appeler_ollama() acceptent tous deux
    de travailler sans demande — c'est le cas de l'essai de modele lance depuis
    l'administration. Le chemin d'erreur d'appeler_ollama journalisait pourtant
    sans condition, et « tid[:6] » levait alors un TypeError qui remplaçait le
    vrai message par une erreur 500. Le diagnostic disparaissait au moment
    precis ou l'on en avait besoin.
    """
    if not tid:
        print(f"[studio] {msg}", flush=True)
        return
    t = TACHES.setdefault(tid, {"etapes": [], "etat": "en cours"})
    t["etapes"].append({"t": time.strftime("%H:%M:%S"), "msg": msg})
    t.update(extra)
    print(f"[{tid[:6]}] {msg}", flush=True)

# ══════════════════════════════ fichiers ═══════════════════════════════
# Un fichier .gguf depose dans models/diffusion_models n'apparait PAS dans
# /models/diffusion_models : le noeud ComfyUI-GGUF enregistre un dossier virtuel
# unet_gguf qui pointe sur le meme repertoire, filtre sur l'extension. Sans cette
# correspondance, klein9b, flux1, wan5b et wan14b seraient declares absents et
# retelecharges — plusieurs dizaines de gigaoctets pour rien.
_JUMEAUX_GGUF = {"diffusion_models": "unet_gguf", "text_encoders": "clip_gguf"}
MODELES_NOEUD = {}          # id -> {"quand": t, "dossiers": {nom: set(fichiers)}}
FRAICHEUR_MODELES = 60      # secondes

def _dossiers_a_lire(sous, nom):
    if nom.lower().endswith(".gguf") and sous in _JUMEAUX_GGUF:
        return [sous, _JUMEAUX_GGUF[sous]]
    return [sous]

async def relever_modeles(ident):
    """Ce que le noeud sait charger, demande a lui plutot que devine du disque.

    /models/{dossier} coute quelques centaines d'octets ; /object_info en coute
    un million et demi. On lit donc dossier par dossier, et seulement ceux dont
    le catalogue a besoin.
    """
    besoins = {d for c in CATALOGUE for sous, nom, _, _ in CATALOGUE[c]["fichiers"]
               for d in _dossiers_a_lire(sous, nom)}
    trouve, repondu = {}, False
    to = aiohttp.ClientTimeout(total=8)
    try:
        async with aiohttp.ClientSession(timeout=to) as s:
            for d in sorted(besoins):
                try:
                    async with s.get(f"{url_de(ident)}/models/{d}") as r:
                        if r.status == 200:
                            trouve[d] = set(await r.json())
                            repondu = True
                        else:
                            trouve[d] = set()
                except Exception:
                    trouve[d] = set()
    except Exception:
        return
    # « repondu » et non « des fichiers trouves » : une machine qui repond des
    # listes vides (dossier models demonte, ComfyUI relance sans sa
    # configuration) doit ecraser l'ancien instantane, sinon le studio affirme
    # eternellement que les modeles sont la et rien ne se repare sans redemarrer.
    if repondu:
        MODELES_NOEUD[ident] = {"quand": time.time(), "dossiers": trouve}

def manquants(cle, ident=None):
    """Fichiers du catalogue absents d'un noeud. Sans cache utilisable, on
    retombe sur le disque pour le noeud local — le seul dont on ait les fichiers
    sous la main — et on considere tout absent ailleurs."""
    ident = ident or noeud_local()["id"]
    cache = MODELES_NOEUD.get(ident)
    # Perime : on prefere relire le disque (noeud local) plutot que d'affirmer
    # l'etat d'avant. Sans cela, un modele depose a la main pendant que ComfyUI
    # etait arrete etait retelecharge en entier.
    if cache and time.time() - cache.get("quand", 0) > 3 * FRAICHEUR_MODELES:
        cache = None
    fichiers = CATALOGUE[cle]["fichiers"]
    if not cache:
        if est_local(ident):
            return [(s, n, r, d) for s, n, r, d in fichiers
                    if not os.path.exists(os.path.join(RACINE_MODELES, s, n))]
        return list(fichiers)
    dossiers = cache["dossiers"]
    absents = []
    for sous, nom, repo, distant in fichiers:
        if not any(nom in dossiers.get(d, set()) for d in _dossiers_a_lire(sous, nom)):
            absents.append((sous, nom, repo, distant))
    return absents

def tolerance_ram(ram):
    """De combien la RAM permet de depasser la carte.

    Memes paliers que l'installeur, et c'est le but : les deux repondaient
    differemment a la meme question, si bien que l'installeur telechargeait des
    modeles que le studio refusait ensuite d'employer.
    """
    if ram >= 64:
        return 5.0
    if ram >= 32:
        return 3.5
    if ram >= 16:
        return 2.0
    return 0.0


def _vram_utile(ident):
    """Ce que cette machine peut charger : sa carte, plus ce que la RAM tolere."""
    e = ETAT_NOEUDS.get(ident) or {}
    return (e.get("vram") or 0) + tolerance_ram(e.get("ram") or 0)


def tient_vraiment(cle, ident):
    """Vrai si le moteur tient sur la carte SANS deborder."""
    e = ETAT_NOEUDS.get(ident) or {}
    return (e.get("vram") or 0) >= CATALOGUE[cle].get("vram", 0)


def noeuds_pour(cle):
    """Noeuds capables d'executer ce moteur : joignables, assez de VRAM, et le
    modele deja present — un noeud distant ne peut pas etre approvisionne, le
    studio n'ecrit que sur son propre disque."""
    besoin = CATALOGUE[cle].get("vram", 0)
    bons = []
    for x in tous_les_noeuds():
        e = ETAT_NOEUDS.get(x["id"], {})
        # Debordement autorise, comme le fait ComfyUI lui-meme : le rendu
        # ralentit mais aboutit. Sans cela, le studio refusait d'employer des
        # modeles que l'installeur avait justement telecharges pour cette
        # machine.
        if not e.get("repond") or (besoin and _vram_utile(x["id"]) < besoin):
            continue
        # un agent qui s'est taru depuis trop longtemps est considere perdu :
        # son dernier « je reponds » ne vaut plus rien
        if x.get("agent") and time.time() - (e.get("vu") or 0) > SILENCE_MAX:
            continue
        if manquants(cle, x["id"]) and not x.get("local"):
            continue
        bons.append(x)
    return bons

def charge_noeud(ident):
    """Combien de travaux en vol visent deja cette machine.

    L'intention, et non le verrou : entre le choix d'une machine et la prise de
    son verrou il y a toute l'analyse, les telechargements et l'envoi des
    entrees. Compter les verrous tenus revenait a croire libre une carte que
    trois demandes attendaient deja.
    """
    return sum(1 for t in EN_VOL if (TACHES.get(t) or {}).get("noeud") == ident)


def choisir_noeud(cle):
    """Le placement fin (debit mesure, arbitrage vitesse/qualite) viendra avec
    la mesure par noeud. Pour l'instant : la machine locale si elle convient,
    sinon la plus grosse carte disponible."""
    bons = noeuds_pour(cle)
    if not bons:
        return None
    # Une machine ou le moteur tient VRAIMENT passe devant : le debordement
    # est un recours, pas un choix par defaut.
    natifs = [x for x in bons if tient_vraiment(cle, x["id"])]
    dans = natifs or bons
    # La carte la MOINS CHARGEE passe devant la plus grosse. On compte les
    # travaux qui la VISENT, pas le verrou qu'elle tient : le verrou n'est pris
    # qu'au moment de soumettre, bien apres le choix. Deux demandes envoyees a
    # deux secondes d'ecart voyaient donc toutes deux une carte libre, visaient
    # la meme, et la seconde attendait pendant que l'autre machine dormait.
    # Constate par l'utilisateur, et c'est exactement ce que le parallelisme
    # etait cense eviter.
    #
    # Ce n'est pas toujours le choix le plus rapide pour UNE demande : attendre
    # deux minutes la grosse carte peut battre un rendu lance tout de suite sur
    # la petite. Mais c'est le plus rapide pour l'ensemble, et c'est le seul
    # qu'on puisse faire sans predire une duree qu'on ne connait pas.
    moindre = min(charge_noeud(x["id"]) for x in dans)
    dans = [x for x in dans if charge_noeud(x["id"]) == moindre]
    local = next((x for x in dans if x.get("local")), None)
    return local or max(dans, key=lambda x: ETAT_NOEUDS.get(x["id"], {}).get("vram", 0))

def manquants_partout(cle):
    """Absent de TOUS les noeuds joignables : c'est ce qui justifie un
    telechargement, pas l'absence sur une machine en particulier."""
    # tous_les_noeuds() et non NOEUDS : ce dernier ne contient que les machines
    # declarees dans noeuds.json, jamais celles qui arrivent par un agent. Sur un
    # studio sans carte, la liste etait donc vide et TOUT paraissait a
    # telecharger — « 0/17 moteurs prets » alors que deux machines etaient pretes.
    joignables = [x["id"] for x in tous_les_noeuds()
                  if ETAT_NOEUDS.get(x["id"], {}).get("repond")]
    if not joignables:
        return manquants(cle)
    return [] if any(not manquants(cle, i) for i in joignables) else manquants(cle)

def _taille_lisible(octets):
    """Mo sous le gigaoctet : « 0.0 Go sur 0.1 » n'apprend rien a personne."""
    if octets >= 1e9:
        return f"{octets / 1e9:.1f} Go"
    return f"{octets / 1e6:.0f} Mo"


def _duree_lisible(secondes):
    if secondes < 90:
        return f"{secondes:.0f} s"
    if secondes < 5400:
        return f"{secondes / 60:.0f} min"
    return f"{secondes / 3600:.1f} h"


def telecharger(sous, nom, repo, distant, tid, essais=3):
    """Un fichier de modele, en HTTPS direct, avec reprise et compte rendu.

    Appele dans un fil d'execution : les entrees-sorties y sont bloquantes sans
    gener la boucle du serveur.
    """
    import urllib.error

    if not repo:
        raise RuntimeError(f"{nom} est absent et n'a pas de source automatique "
                           f"(depot sous licence ou modele installe a la main).")
    dest = os.path.join(RACINE_MODELES, sous)
    os.makedirs(dest, exist_ok=True)
    cible = os.path.join(dest, nom)
    if os.path.exists(cible):
        return
    partiel = cible + ".part"
    url = f"https://huggingface.co/{repo}/resolve/main/{distant}"

    for essai in range(1, essais + 1):
        deja = os.path.getsize(partiel) if os.path.exists(partiel) else 0
        entetes = {"User-Agent": "comfystudio"}
        if deja:
            entetes["Range"] = f"bytes={deja}-"
        try:
            _tirer(url, entetes, partiel, deja, nom, tid)
            break
        except urllib.error.HTTPError as e:
            # 401, 403, 404 : le fichier n'est pas la, ou pas pour nous.
            # Reessayer trois fois ne fera que retarder le message.
            if e.code in (401, 403, 404):
                raise RuntimeError(
                    f"{nom} introuvable chez {repo} (HTTP {e.code}). "
                    f"Depot prive, renomme, ou chemin errone.")
            raise
        except Exception as e:
            reste = essais - essai
            if not reste:
                raise RuntimeError(f"{nom} : telechargement interrompu ({e})")
            journal(tid, f"{nom} : coupure ({type(e).__name__}) — reprise "
                         f"la ou on en etait, {reste} essai(s) restant(s)")
            time.sleep(5)

    os.replace(partiel, cible)
    journal(tid, f"{nom} installe ({_taille_lisible(os.path.getsize(cible))})")


def _tirer(url, entetes, partiel, deja, nom, tid):
    """Un tirage, depuis le debut ou depuis l'octet « deja »."""
    import urllib.request

    req = urllib.request.Request(url, headers=entetes)
    with urllib.request.urlopen(req, timeout=120) as r:
        # 206 : le serveur accepte la reprise. 200 : il l'ignore et renvoie
        # tout — il faut alors repartir de zero, sinon on colle deux morceaux.
        reprise = r.status == 206 and deja > 0
        attendu = int(r.headers.get("Content-Length") or 0) + (deja if reprise else 0)
        fait = deja if reprise else 0
        if deja and not reprise:
            journal(tid, f"{nom} : la reprise a ete refusee, on repart du debut")
        if reprise:
            journal(tid, f"{nom} : reprise a {_taille_lisible(fait)}")
        elif attendu:
            journal(tid, f"telechargement de {nom} ({_taille_lisible(attendu)})")
        else:
            journal(tid, f"telechargement de {nom}…")

        t0 = time.time()
        jalon, dernier_dit = 0, t0
        with open(partiel, "ab" if reprise else "wb") as f:
            while True:
                bloc = r.read(1 << 20)
                if not bloc:
                    break
                f.write(bloc)
                fait += len(bloc)
                # On parle tous les 10 %, et au moins toutes les 30 s : sur
                # dix-huit gigaoctets, un silence de vingt minutes ressemble a
                # une panne.
                maintenant = time.time()
                pourcent = (fait * 100 // attendu) if attendu else 0
                if (attendu and pourcent >= jalon + 10) or maintenant - dernier_dit > 30:
                    jalon = pourcent - (pourcent % 10)
                    dernier_dit = maintenant
                    debit = (fait - deja) / max(maintenant - t0, 0.1)
                    reste = ((attendu - fait) / debit) if (attendu and debit > 0) else 0
                    journal(tid, f"{nom} : {pourcent} % — {_taille_lisible(fait)} "
                                 f"sur {_taille_lisible(attendu)}, "
                                 f"{debit / 1e6:.0f} Mo/s, encore "
                                 f"{_duree_lisible(reste)}")

    if attendu and os.path.getsize(partiel) != attendu:
        recu = os.path.getsize(partiel)
        os.remove(partiel)
        # Un fichier tronque n'est pas refuse a l'ouverture : il echoue plus
        # tard, avec un message qui ne parle pas de telechargement.
        raise RuntimeError(f"taille inattendue : {recu} octets recus sur {attendu}")


# ══════════════════════════════ aiguillage ═════════════════════════════

def catalogue_texte():
    """Ce que voit l'aiguilleur : ce qui est deja la, ce qu'il faudrait
    telecharger et a quel prix, et rien qui depasse la carte."""
    lignes = []
    plafond = vram_max()
    for c, m in CATALOGUE.items():
        # Plafond nul : la carte n'est pas connue. Mieux vaut tout montrer que
        # d'ecarter au hasard — l'echec, s'il vient, sera explicite.
        if plafond and m.get("vram", 0) > plafond:
            continue
        etat = ("installe" if not manquants_partout(c)
                else f"A TELECHARGER une seule fois, ~{POIDS.get(c, 1):.0f} Go")
        lignes.append(f'- "{c}" ({m["titre"]}, {m["type"]}) : {m["pour"]} '
                      f'[~{m["duree"]}, {etat}]')
    return "\n".join(lignes)

SYSTEME = """Tu es l'aiguilleur d'un studio local de creation d'images, de videos et de musique.
On te donne une demande en francais. Tu reponds UNIQUEMENT par un objet JSON, sans texte autour.

Modeles disponibles :
{catalogue}

Champs :
  "intention" : "image" | "edition" | "agrandir" | "detourer" | "fluidifier"
                | "planche" | "objet3d"
                | "video" | "video_image" | "audio" | "lecture"
  "modele"    : la cle exacte d'un modele ci-dessus, coherente avec l'intention
  "prompt"    : la demande reecrite et ENRICHIE, EN FRANCAIS. N'essaie jamais de
                traduire : la traduction vers l'anglais est faite ensuite, par un
                autre traitement, uniquement pour les moteurs qui l'exigent. Si tu
                traduis toi-meme, tu te trompes de mot et un hibou devient un
                hippopotame. Ecris en francais, precisement, 2 a 4 phrases decrivant sujet, cadrage, lumiere, ambiance, style.
                Pour "edition", formule une CONSIGNE de modification
                ("change the sky to a stormy night sky"), pas une description.
  "image" quand la demande dit « le meme personnage », « la meme », « garde ce
                personnage » : c'est une IMAGE NEUVE, pas une retouche. Le studio
                se charge tout seul de reprendre le visage ; toi, decris la
                nouvelle scene entierement, comme pour une image ordinaire.
  "agrandir"  : l'image existante est AGRANDIE telle quelle, sans rien y changer.
                A choisir des que la demande porte sur la definition, la taille
                ou la qualite d'une image deja produite, et non sur son contenu.
  "negatif"   : ce qu'il faut eviter, en anglais, separe par des virgules ("" si rien)
  "largeur", "hauteur" : multiples de 64. Images : 768 a 1920.
  "tags_audio": pour "audio" seulement. UNIQUEMENT LA MUSIQUE, EN ANGLAIS : genre,
                instruments, voix, tempo, ambiance sonore. JAMAIS l'histoire ni le
                sujet de la chanson — ils vont dans "paroles", et seulement la.
                Ce champ decrit ce qu'on ENTEND, pas ce que ca raconte. Y mettre
                une biographie produit une musique qui n'a rien du style demande.
                Exemple pour un rock : "Energetic rock and roll at 128 BPM, driving
                electric guitars, walking bass, live drums, male lead vocal with
                male backing vocals on the chorus, warm analog studio recording."
  "paroles"   : LAISSE CE CHAMP VIDE (""). Les paroles sont ecrites ensuite, par
                un appel separe : les glisser ici fait deborder ta reponse et rend
                le plan entier inutilisable. Indique seulement, dans "raison", s'il
                s'agit d'une chanson chantee ou d'un morceau instrumental.
  "langue"    : pour "audio" avec paroles, code ISO deux lettres ("fr", "en", "ja"…)
  "tonalite"  : pour "audio" seulement, ex. "C minor", "A major" (majuscule obligatoire)
  "cases"     : pour "planche" seulement. Liste de 2 a 6 descriptions, une par case,
                CHACUNE en balises danbooru (pas de phrases). Repete mot pour mot la
                description du personnage dans chaque case : c'est la seule facon
                d'obtenir le meme personnage d'une case a l'autre.
                Exemple : ["knight in dented plate armor, scarred face, drawing a sword,
                medium shot", "horned dragon roaring, extreme close-up, sharp teeth"]
  "classement": "safe" | "questionable" | "explicit" — degre de contenu adulte demande
  "questions" : liste de 1 a 3 questions EN FRANCAIS, uniquement si la demande est
                trop vague pour etre executee sans deviner. Dans ce cas mets aussi
                "intention" a "question" et laisse les autres champs vides.
  "raison"    : une phrase EN FRANCAIS expliquant ton choix
  "parametres": objet des reglages techniques que TU adaptes a la demande. Mets uniquement
                ceux qui concernent l'intention choisie ; les absents prennent leur defaut.

     image / edition   "etapes" (qualite, plus = plus long), "cfg" (obeissance au prompt)
     video/video_image "images" (nombre d'images, ~24 par seconde), "fps", "etapes", "cfg"
     audio             "bpm" (TEMPO — decisif : 60-75 pour lent/melancolique, 90-110 pour
                       modere, 125-140 pour rapide/danse ; un rock and roll est a
                       125-140), "duree_s" (LA DUREE DEMANDEE, en secondes : « deux
                       minutes » vaut 120, « 2 a 3 min » vaut 150 — ne laisse pas
                       le defaut de 60 si une duree est demandee), "etapes", "cfg"

  Adapte-les VRAIMENT au sens de la demande : « lent », « rapide », « tres detaille »,
  « une esquisse », « dix secondes de video », « en boucle courte » doivent se traduire
  en valeurs. Ne recopie pas les defauts sans reflechir.

Ta mission se deroule dans cet ordre :
  1. ENRICHIR — une demande courte doit devenir un prompt complet. « un renard dans la
     neige » devient une scene decrite : cadrage, lumiere, saison, ambiance, style.
     C'est ton travail principal. Enrichis directement en francais.
     SEULE EXCEPTION : pour "pony" et "planche", le prompt n'est pas une phrase
     mais une suite d'etiquettes danbooru en anglais, separees par des virgules
     (1girl, knight, silver armor, forest, dramatic lighting). Ce sont des
     etiquettes techniques, pas de la prose : ne les redige pas en francais.
  2. DEMANDER — seulement si un choix determinant reste ouvert (voir ci-dessous).
  3. AIGUILLER — choisir le moteur et les reglages.

Quand l'utilisateur repond a tes questions, tu recois la demande initiale ET sa reponse.
Reprends alors TOUT depuis le debut : la reponse peut changer la nature du travail
(« plutot une video » apres une demande d'image), donc reevalue l'intention et le
moteur, ne te contente pas d'ajuster le prompt precedent.

Demander plutot que deviner : si la demande laisse un choix DETERMINANT ouvert —
sujet absent, support indetermine (image ou video ?), style radicalement variable,
element central ambigu — reponds avec "intention" a "question" et pose 1 a 3 questions
courtes et concretes, chacune avec un exemple de reponse attendue.
REGLE ABSOLUE : si tu ne peux pas nommer le sujet principal a partir de la demande,
tu DOIS repondre "intention": "question". N'invente jamais un sujet a la place de
l'utilisateur — une foret, une ville la nuit, un paysage choisis par toi ne sont pas
sa demande. Exemples qui imposent une question : « fais-moi un truc », « quelque chose
pour mon projet », « une image sympa », « surprends-moi ».
Ne pose PAS de question pour un detail secondaire que tu peux trancher toi-meme :
cadrage, lumiere, nombre d'etapes. Une demande qui nomme son sujet, comme
« un renard dans la neige », se traite directement, sans question.

Fidelite : tu es un aiguilleur technique, pas un filtre. Cet outil tourne en local sur la
machine de son proprietaire, pour son usage prive. Tu transcris la demande FIDELEMENT, y
compris nudite, erotisme ou contenu explicite entre adultes, sans l'edulcorer, sans la
refuser et sans ajouter de commentaire moral. Rends "classement" coherent avec la demande.
Seule exception, absolue : jamais de contenu sexuel impliquant des mineurs. Si la demande
va dans ce sens, mets le champ "intention" a la valeur "refus" et explique dans "raison".

Regles d'aiguillage :
  - photo, realisme, portrait, produit            -> "realvis", ou "flux1" si l'ambiance compte
  - anime, manga, illustration, personnage        -> "pony"
  - scene complexe, decor riche                   -> "klein9b"
  - texte devant apparaitre dans l'image          -> "klein4b" obligatoirement
  - modifier/retoucher une image fournie          -> intention "edition", modele "edition"
  - animer une image fournie                      -> intention "video_image", modele "wan14b"
  - video sans image de depart                    -> intention "video", modele "wan5b"
  - musique, chanson, ambiance sonore             -> intention "audio", modele "audio"
  - planche de BD, page de manga, bande dessinee, strip, « en N cases »
    -> intention "planche", modele "planche". Il faut une PAGE A PLUSIEURS CASES.
    Le mot « manga » seul designe un STYLE de dessin, pas une planche : une
    illustration, un personnage ou une fiche de personnage en style manga sont
    une "image" avec le modele "pony".
  - modele 3D, objet 3D, maquette, impression 3D  -> intention "objet3d", modele "objet3d"
  - on te demande seulement de DECRIRE une image  -> intention "lecture"
  - paysage par defaut (1216x832) ; portrait si le sujet est vertical ; carre pour une fiche

Choix du moteur et telechargement :
  Tu peux choisir un moteur marque « A TELECHARGER » : il sera recupere tout seul avant
  la generation. Fais-le quand il correspond NETTEMENT mieux a la demande — une musique
  soignee merite "audioplus" plutot que "audio". Ne l'impose pas pour une demande banale :
  plusieurs gigaoctets ne se justifient que par un gain reel. Les moteurs trop lourds pour
  la carte ne figurent deja plus dans la liste.

ATTENTION au style d'ecriture du prompt, il change selon le moteur :
  - "pony" et "planche" sont des modeles a BALISES (danbooru). Ecris une liste de
    mots-cles separes par des virgules, PAS des phrases. Exemple attendu pour une
    planche : "4koma, four panels, three rows, wide top panel, warrior in plate armor
    drawing a sword, close-up of narrowed eyes, horned dragon roaring, warrior leaping
    with sword raised, speed lines, blank speech bubble, dramatic angle".
    Une phrase complete y donne un dessin unique sans decoupage — c'est mesure.
  - tous les autres moteurs attendent au contraire de la PROSE descriptive.

Pour une planche, remplis "cases" : chaque case sera dessinee separement en pleine
resolution puis assemblee. C'est nettement plus lisible qu'une planche generee d'un
seul tenant, ou chaque case ne recoit qu'un sixieme des pixels. Mets aussi un "prompt"
resumant la planche, il sert de repli.

Pour une planche, decris la mise en page dans le prompt : nombre de cases, disposition en
rangees, bordures noires epaisses, gouttieres blanches, et le contenu de chaque case.
Demande des bulles VIDES (« blank speech bubble ») : le texte sera ajoute ensuite, hors
generation, pour rester corrigeable.

{contexte}"""

def bloc_contexte(conv, n=5):
    """Les n derniers echanges. Un seul tour ne suffit pas : l'utilisateur peut
    renvoyer a une demande plus ancienne (« reprends la version de nuit »)."""
    tours = [t for t in conv["tours"] if t.get("etat") in ("fini", "question")]
    if not tours:
        return "Il n'y a pas encore eu d'echange dans cette conversation."
    lignes = ["Historique de la conversation, du plus ancien au plus recent :"]
    for i, t in enumerate(tours[-n:], 1):
        lignes.append("  {}. demande : {}".format(i, t["demande"]))
        lignes.append("     tu avais produit : {} avec {}".format(
            t.get("type", "image"), t.get("modele", "?")))
        if t.get("prompt"):
            lignes.append("     prompt utilise : {}".format(t["prompt"][:180]))
    lignes.append("")
    lignes.append("La nouvelle demande peut : (a) etre indépendante, (b) MODIFIER le dernier")
    lignes.append("resultat, (c) renvoyer a un echange plus ancien de la liste. Dans les cas")
    lignes.append("(b) et (c), reprends le prompt concerne et applique la modification en")
    lignes.append("gardant tout le reste identique.")
    if conv.get("derniere_sortie"):
        lignes.append("Une image issue du dernier resultat est disponible comme source d'edition.")
    return "\n".join(lignes)

ATTENTE_COMFY = 1200        # 20 minutes, puis on passe outre en le disant

async def comfy_occupe():
    """La file PROPRE de ComfyUI, celle que le studio ne remplit pas.

    On la lit plutot que de se fier a la file du studio : une generation lancee
    a la main dans l'interface de ComfyUI est invisible d'ici, et c'est
    precisement celle qui ferait charger le LLM en pleine diffusion.
    """
    try:
        to = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=to) as s:
            async with s.get(f"{url_locale()}/queue") as r:
                d = await r.json()
                return bool(d.get("queue_running")) or bool(d.get("queue_pending"))
    except Exception:
        return False        # ComfyUI injoignable : inutile de bloquer le LLM

async def attendre_carte_libre(tid=None):
    """Le modele de langage et la diffusion se disputent les memes 11 Go.

    Les faire tourner ensemble ne casse rien, mais la machine rame : le LLM
    reserve plusieurs gigaoctets le temps de son appel, et la diffusion se
    replie sur le disque. On attend donc que la carte soit rendue.
    """
    debut = dernier = time.time()
    prevenu = False
    while await comfy_occupe():
        if tid and not prevenu:
            journal(tid, "ComfyUI travaille — l'analyse attend que la carte se libere")
            prevenu = True
        if time.time() - debut > ATTENTE_COMFY:
            if tid:
                journal(tid, "ComfyUI occupe depuis 20 minutes — analyse lancee malgre tout")
            return
        if tid and time.time() - dernier > 60:
            dernier = time.time()
            journal(tid, f"toujours en attente de la carte ({int(time.time()-debut)} s)")
        await asyncio.sleep(2)

_OLLAMA_CHEZ = {"quand": 0.0, "noeud": None}


def noeud_de_l_ollama():
    """La machine a agent qui heberge l'Ollama du studio, s'il y en a une.

    On compare l'adresse resolue d'OLLAMA_URL a celle d'ou chaque agent nous
    parle. C'est la seule correspondance disponible : un agent n'a pas d'adresse
    joignable — c'est tout l'interet du montage — mais il en a forcement une
    quand il appelle.

    Sans cela, l'analyse tournait sur une carte que personne n'avait reservee :
    l'utilisateur voyait une analyse et un rendu se partager le meme GPU, ce que
    la regle « une carte, une tache » interdit. attendre_carte_libre(), lui, ne
    regarde que le ComfyUI du studio — celui qui n'existe plus depuis qu'il n'a
    pas de carte — et rendait donc la main aussitot.

    Recalcule au plus une fois par minute : une resolution DNS a chaque appel du
    modele de langage serait payee des centaines de fois pour rien.
    """
    if time.time() - _OLLAMA_CHEZ["quand"] < 60:
        return _OLLAMA_CHEZ["noeud"]
    _OLLAMA_CHEZ["quand"] = time.time()
    _OLLAMA_CHEZ["noeud"] = None
    hote = urllib.parse.urlparse(OLLAMA).hostname
    if hote:
        import socket
        try:
            ip = socket.gethostbyname(hote)
        except OSError:
            return None
        for x in tous_les_noeuds():
            if x.get("agent") and (ETAT_NOEUDS.get(x["id"]) or {}).get("ip") == ip:
                _OLLAMA_CHEZ["noeud"] = x["id"]
                break
    return _OLLAMA_CHEZ["noeud"]


async def appeler_ollama(texte, image_b64=None, systeme=None, json_mode=True,
                         modele=None, temperature=0.4, tid=None, garder=0):
    """temperature : 0.4 convient a la description libre d'une image. L'aiguillage
    et la traduction sont des taches de classification, pas de creation — a 0.4 la
    meme demande partait tantot en question, tantot en image (mesure). La part
    creative revient au modele de diffusion, pas a l'aiguilleur."""
    # Un appel distant ne touche pas la carte : ni attente, ni chargement de
    # 18 Go. C'est aussi pour cela qu'il est tente AVANT la mise en file.
    loin = ("" if image_b64
            else llm_distant_possible(texte, (TACHES.get(tid) or {}).get("proprietaire")))
    if loin:
        try:
            rendu = await fournisseurs.texte(
                loin, cle_de(loin), texte, systeme, temperature, json_mode,
                modele_de(loin) or None)
            return rendu
        except fournisseurs.EchecFournisseur as e:
            # Le message du fournisseur remonte tel quel : « modele inconnu » et
            # « cle refusee » ne se corrigent pas de la meme facon.
            journal(tid, f"{fournisseurs.LLM[loin]['titre']} indisponible ({e})"
                         f" — le modele local prend le relais")

    await attendre_carte_libre(tid)
    # ET la carte de la machine qui HEBERGE cet Ollama : une carte ne fait
    # qu'une tache a la fois, analyse comprise. attendre_carte_libre() ci-dessus
    # ne surveille que le ComfyUI du studio, qui n'existe plus.
    chez = noeud_de_l_ollama()
    verrou_ol = verrou_noeud(chez) if chez else None
    if verrou_ol is not None:
        if verrou_ol.locked() and tid:
            journal(tid, f"{(noeud(chez) or {}).get('titre', chez)} calcule — "
                         f"l'analyse attend sa carte ({ATTENTE_LLM} s au plus)")
        try:
            await asyncio.wait_for(verrou_ol.acquire(), timeout=ATTENTE_LLM)
        except asyncio.TimeoutError:
            # Mieux vaut deux traitements qui se genent qu'un studio arrete :
            # on le dit, et on passe.
            if tid:
                journal(tid, "sa carte reste occupee — analyse lancee malgre tout")
            verrou_ol = None
    corps = corps_ollama(texte, image_b64, systeme, json_mode, modele,
                         temperature, garder)
    try:
        return await _ollama_local(corps)
    except Exception as e:
        panne = e
    finally:
        if verrou_ol is not None:
            verrou_ol.release()
    # HORS du verrou. On n'essaie une autre machine QUE si la sienne ne repond
    # pas : un modele distant est plus lent a charger, et la machine qui le porte
    # a peut-etre mieux a faire. Depuis qu'un studio peut vivre sans carte, ce cas
    # n'a rien d'exceptionnel — il suffit que le PC soit eteint.
    #
    # Et il faut avoir LACHE la carte avant : poser_a() prend le verrou de la
    # machine a qui il pose la question, et cette machine peut etre celle dont on
    # vient d'essayer l'Ollama. Le repli se serait attendu lui-meme.
    journal(tid, f"modele local injoignable ({type(panne).__name__}) — "
                 f"on cherche une machine qui en porte un")
    rendu = await demander_a_un_noeud(corps, tid)
    if rendu:
        return rendu
    raise panne


def corps_ollama(texte, image_b64, systeme, json_mode, modele, temperature, garder):
    """Le corps de la requete, tel qu'Ollama l'attend."""
    # keep_alive 0 par defaut : ComfyUI reprend la carte juste apres, et un
    # modele reste resident tant qu'on ne l'a pas relache. « garder » n'est
    # leve que pour une suite d'appels rapprochee, refermee par liberer_modele.
    corps = {"model": modele or MODELE_LLM, "prompt": texte, "stream": False,
             "keep_alive": garder, "options": {"temperature": temperature}}
    if systeme: corps["system"] = systeme
    if json_mode: corps["format"] = "json"
    if image_b64: corps["images"] = [image_b64]
    return corps


async def _ollama_local(corps):
    """L'appel lui-meme, une fois la carte reservee.

    Il ne rattrape rien : le repli sur une autre machine appartient a
    appeler_ollama, qui doit d'abord relacher la carte — sans quoi le repli
    demanderait la carte qu'on tient encore, et s'attendrait lui-meme.
    """
    # 900 s : un gros modele qui deborde sur le processeur met plus longtemps
    # que la minute d'un 7B, et une coupure ici rend une chanson muette.
    to = aiohttp.ClientTimeout(total=900)
    async with aiohttp.ClientSession(timeout=to) as s:
        async with s.post(f"{OLLAMA}/api/generate", json=corps) as r:
            d = await r.json()
            rep_ = d.get("response", "")
            if not rep_.strip() and d.get("error"):
                # Ollama a repondu 200 avec un champ « error » : le modele
                # existe, il ne se CHARGE pas. Le reessayer a chaque demande
                # ne fait que perdre du temps deux fois par appel.
                nom_ = corps.get("model") or ""
                if nom_ and nom_ not in MODELES_CASSES:
                    MODELES_CASSES[nom_] = str(d["error"])[:200]
                    print(f"  [ollama] {nom_} ne se charge pas, il est ecarte "
                          f"— {MODELES_CASSES[nom_]}", flush=True)
                    global MODELE_ECRITURE
                    if MODELE_ECRITURE == nom_:
                        # Le prochain appel en choisira un autre.
                        MODELE_ECRITURE = ""
            if not rep_.strip():
                # Une reponse vide est dite a voix haute, comme pour un
                # fournisseur distant. Sans cela, « traduction rejetee
                # (0 lignes rendues pour 1 attendues) » etait tout ce que le
                # journal disait, et le diagnostic ajoute la veille ne
                # couvrait que la voie distante : celle-ci jetait
                # « done_reason » et « eval_count », les deux seules choses
                # qui expliquent un silence.
                print(f"  [ollama] reponse vide de {corps.get('model')} — "
                      f"arret={d.get('done_reason')} "
                      f"jetons={d.get('eval_count')} "
                      f"erreur={str(d.get('error'))[:80]}", flush=True)
            return rep_


def noeuds_a_llm():
    """Les machines joignables qui portent un modele de langage.

    Les plus grosses d'abord : a defaut de mesurer leur debit, la memoire est le
    meilleur indice de ce qu'elles peuvent charger sans ramer.
    """
    bons = []
    for x in REGISTRE.values():
        e = ETAT_NOEUDS.get(x["id"]) or {}
        if e.get("repond") and e.get("llm") and time.time() - (e.get("vu") or 0) < SILENCE_MAX:
            bons.append((e.get("vram") or 0, x["id"]))
    return [i for _, i in sorted(bons, reverse=True)]


def _modele_du_noeud(ident, voulu):
    """Le modele a demander a cette machine, parmi ceux qu'elle porte.

    Le nom exact d'abord, puis la meme famille — « qwen2.5vl:3b » vaut mieux que
    rien quand on esperait le 7b — puis, faute de mieux, le premier annonce.
    """
    dispo = (ETAT_NOEUDS.get(ident) or {}).get("llm_modeles") or []
    if not dispo:
        return voulu
    if voulu in dispo:
        return voulu
    famille = (voulu or "").split(":")[0]
    proche = [m for m in dispo if m.split(":")[0] == famille]
    return (proche or dispo)[0]


async def poser_a(ident, corps, tid=None, secondes=900):
    """Pose une question au modele de langage d'UNE machine.

    Le studio depose, l'agent vient chercher : le meme chemin que les rendus,
    parce que c'est le seul qui existe — une machine a agent n'a pas d'adresse.
    Rend (reponse, erreur) : l'un des deux est toujours vide.
    """
    # Le nom du modele vient du studio, qui ne connait que le SIEN : demander
    # « qwen2.5vl:7b » a une machine qui ne l'a pas ferait echouer la voie de
    # secours au moment precis ou l'on en depend. On substitue donc ce que la
    # machine annonce vraiment porter.
    corps = dict(corps)
    corps["model"] = _modele_du_noeud(ident, corps.get("model"))
    titre = (noeud(ident) or {}).get("titre", ident)
    # LE MEME VERROU QUE LES RENDUS. Un modele de langage de vingt-six milliards
    # de parametres et une diffusion se disputent les memes gigaoctets : les
    # faire tourner ensemble ne casse rien, la machine rame — le LLM reserve sa
    # place et la diffusion se replie sur le disque. Le studio avait bien un
    # garde-fou pour ce cas, mais il ne regardait que SA carte, celle qu'il n'a
    # plus. Une carte, un traitement a la fois : image, video, son, maillage ou
    # langage.
    #
    # MAIS L'ATTENTE EST BORNEE. L'attendre sans limite etait pire que le mal :
    # mesure sur cette installation, une question de deux secondes a attendu
    # derriere un rendu de 147 s en retenant un travailleur tout ce temps, et
    # trois demandes se sont bloquees mutuellement pendant dix minutes. Passe le
    # delai on rend « carte occupee » : l'appelant essaiera une autre machine, ou
    # se passera de reponse. Un studio lent vaut mieux qu'un studio arrete.
    #
    # acquire() puis un « finally », et non « async with » : il faut pouvoir
    # borner la PRISE. Le relacher pour le reprendre aussitot laisserait passer
    # quelqu'un entre les deux, ce qui viderait le verrou de son sens.
    verrou = verrou_noeud(ident)
    if verrou.locked() and tid:
        journal(tid, f"{titre} calcule — la question attend sa carte "
                     f"({ATTENTE_LLM} s au plus)")
    try:
        await asyncio.wait_for(verrou.acquire(), timeout=ATTENTE_LLM)
    except asyncio.TimeoutError:
        if tid:
            journal(tid, f"{titre} calcule toujours — on cherche ailleurs")
        return "", "carte occupee"
    try:
        qid = uuid.uuid4().hex
        futur = asyncio.get_event_loop().create_future()
        REPONSES[qid] = (ident, futur)
        QUESTIONS.setdefault(ident, []).append({"qid": qid, "corps": corps})
        # journal() ecrit dans le fil d'une demande : l'essai depuis
        # l'administration n'en a pas, et lui en inventer une la ferait
        # apparaitre dans la conversation de quelqu'un.
        if tid:
            journal(tid, f"question confiee a {titre}…")
        try:
            rep_ = await asyncio.wait_for(futur, timeout=secondes)
        except asyncio.TimeoutError:
            return "", "n'a pas repondu a temps"
        finally:
            REPONSES.pop(qid, None)
            QUESTIONS[ident] = [q for q in QUESTIONS.get(ident, []) if q["qid"] != qid]
    finally:
        verrou.release()
    return (rep_.get("reponse") or ""), (rep_.get("erreur") or "")


async def demander_a_un_noeud(corps, tid=None, secondes=900):
    """La premiere machine qui sait repondre. Rend le texte, ou ""."""
    # Celles dont la carte est libre d'abord. Depuis qu'une carte ne fait qu'une
    # chose a la fois, prendre les machines dans l'ordre du registre faisait
    # attendre deux minutes derriere un rendu alors qu'une autre machine
    # repondait tout de suite. L'ordre relatif est conserve a l'interieur de
    # chaque groupe : le premier de la liste reste le premier des libres.
    a_llm = list(noeuds_a_llm())
    libres = [i for i in a_llm if not verrou_noeud(i).locked()]
    for ident in libres + [i for i in a_llm if i not in libres]:
        reponse, erreur = await poser_a(ident, corps, tid, secondes)
        if erreur:
            journal(tid, f"{(noeud(ident) or {}).get('titre', ident)} : {erreur}")
            continue
        if reponse:
            return reponse
    return ""


async def liberer_modele(modele):
    """Decharge un modele reste chaud. Sans cela, ComfyUI trouve la carte prise."""
    try:
        to = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=to) as s:
            await s.post(f"{OLLAMA}/api/generate",
                         json={"model": modele, "prompt": "", "keep_alive": 0})
    except Exception:
        pass


SYS_TRADUCTION = """Tu traduis du francais vers l'anglais. Tu ne fais que cela.

Regles absolues :
- une ligne de sortie pour chaque ligne d'entree, meme numero, dans le meme ordre ;
- rien d'autre dans ta reponse : pas de commentaire, pas de ligne en plus ;
- traduis chaque nom d'animal, de plante, de vetement et d'objet avec EXACTITUDE.
  hibou = owl. blaireau = badger. herisson = hedgehog. ecureuil = squirrel.
  sanglier = wild boar. chevreuil = roe deer. mesange = tit. buse = buzzard.
  Dans le doute sur un mot, decris-le plutot que d'en inventer un autre ;
- ne resume pas, ne raccourcis pas, n'ajoute aucun detail ;
- vocabulaire de cadrage : contre-plongee = from below. plongee = from above.
  gros plan = close-up. plan large = wide shot. de profil = profile."""

# cyrillique, hebreu, arabe, kana, han, hangul
_PLAGES_NON_LATINES = ((0x0400, 0x04ff), (0x0590, 0x06ff), (0x3040, 0x30ff),
                       (0x3400, 0x9fff), (0xac00, 0xd7af))

def mise_en_garde(cle):
    """Ce que ce moteur attend, en une phrase. "" s'il n'attend rien de special.

    C'est le coeur de la question posee : partir en francais vers un moteur qui
    lit le francais ne coute rien, vers un moteur qui exige l'anglais coute le
    sujet. Les deux cas ne meritent pas le meme avertissement.
    """
    m = CATALOGUE.get(cle) or {}
    if cle in ("pony", "planche"):
        return ("ce moteur n'attend pas une phrase mais des etiquettes en "
                "anglais, separees par des virgules — « 1girl, knight, silver "
                "armor, forest ». Une phrase francaise y donne un resultat "
                "approximatif.")
    if m.get("traduire"):
        return ("ce moteur ne lit que l'anglais : une demande restee en "
                "francais donne souvent le mauvais sujet.")
    if m.get("multilingue"):
        return "ce moteur lit le francais, la demande partira telle quelle."
    return ""


def replier_sur_multilingue(plan, tid, cause):
    """Quand la traduction echoue, on change de moteur au lieu d'insister.

    Envoyer du francais a FLUX.1, dont l'encodeur est anglophone, ne degrade pas
    l'image : cela change le sujet. Mesure du 27 aout 2026 : « un vieux hibou
    perche sur une branche moussue » a produit un hybride d'opossum et
    d'ecureuil. FLUX.2 klein comprend le francais nativement (encodeur Qwen3-VL) :
    il vaut mieux perdre le grain photographique de FLUX.1 que le sujet.
    """
    # Un modele a etiquettes n'est pas remplacable : basculer une demande de
    # manga sur klein ferait perdre le style, ce qui coute plus cher qu'une
    # etiquette restee en francais. Mesure : qwen echoue une fois sur deux a
    # traduire une liste courte, quelle que soit la temperature.
    if plan.get("modele_impose"):
        # L'utilisateur a choisi son moteur dans l'interface : on ne le change
        # pas dans son dos. Il vaut mieux un prompt reste en francais que le
        # sentiment d'etre ignore — et on le dit dans le deroule.
        journal(tid, f"{cause} — moteur impose garde, prompt laisse en francais")
        plan["enrichissement_rate"] = True
        return plan
    if CATALOGUE.get(plan.get("modele"), {}).get("etiquettes"):
        journal(tid, f"{cause} — etiquettes gardees telles quelles, le style prime")
        return plan
    if manquants_partout("klein4b"):
        journal(tid, f"{cause} — prompt garde en francais, le resultat peut deriver")
        plan["enrichissement_rate"] = True
        return plan
    journal(tid, f"{cause} — bascule sur FLUX.2 klein, qui comprend le francais")
    plan["modele"] = "klein4b"
    plan["intention"] = "image"
    brut = dict(plan.get("parametres_bruts") or {})
    for technique in ("etapes", "cfg"):
        brut.pop(technique, None)
    plan["parametres_bruts"] = brut
    return appliquer_parametres(plan)

_REPETITION = re.compile(r"(.)\1{3,}")

def latin(t):
    """Une traduction anglaise s'ecrit en alphabet latin.

    qwen bascule par moments en chinois au milieu d'une reponse (mesure :
    « a有机结合在雪饱雪中… » rendu comme traduction). Le prompt devenait
    inutilisable et le moteur d'image n'y comprenait rien. On refuse la reponse
    plutot que de la transmettre.
    """
    # On rejette les ECRITURES etrangeres, pas les accents : un ratio d'ASCII
    # recalait « a cafe » accentue et « a pinata », des traductions correctes.
    # Et il faut de vraies lettres : le modele a deja rendu « : » comme
    # traduction, ce qui passait le controle et vidait le prompt de son sujet.
    if sum(c.isalpha() for c in t) < 3:
        return False
    if any(a <= ord(c) <= b for c in t for a, b in _PLAGES_NON_LATINES):
        return False
    # Le modele part parfois en vrille au milieu d'une reponse : mesure du
    # 28 aout 2026, « a photo.addTab{@@@@@@@@@@@@@@… » rendu comme traduction.
    # Une repetition du meme caractere, ou une majorite de symboles, signalent
    # une reponse degeneree bien mieux qu'un controle d'alphabet.
    if _REPETITION.search(t):
        return False
    utiles = sum(c.isalnum() or c.isspace() for c in t)
    return utiles >= 0.8 * len(t)

# Etiquettes de controle danbooru : elles ne se traduisent pas, et le traducteur
# les abime (« 1girl » devenu « girl »). On les remet par code apres coup, ce qui
# est fiable la ou une consigne supplementaire derailait le modele entier.
_CONTROLE = re.compile(r"^(score_\w+|rating_\w+|\d+(girls?|boys?|others?)|solo|"
                       r"masterpiece|best quality|absurdres|highres)$", re.I)

def etiquettes_de_controle(texte):
    return [e.strip() for e in (texte or "").split(",") if _CONTROLE.match(e.strip())]

def separer_controle(texte):
    """Met de cote les etiquettes de controle avant de traduire.

    Les laisser dans la phrase soumise au traducteur le perturbe : avec
    « score_9, score_8_up, 1boy » en tete, il rendait le reste en francais.
    Retirees, la traduction redevient normale, et on les remet ensuite.
    """
    garde, reste = [], []
    for e in (texte or "").split(","):
        (garde if _CONTROLE.match(e.strip()) else reste).append(e.strip())
    return garde, ", ".join(x for x in reste if x)

def recomposer(garde, traduit):
    return ", ".join([x for x in garde if x] + [traduit]) if garde else traduit

SYS_ENRICHIR = """Tu ameliores la demande d'un utilisateur pour un studio de
creation, et tu ne fais que cela : tu ne choisis pas le moteur, tu ne regles
rien, tu n'expliques rien.

Rends UNE SEULE phrase, ou deux au plus, en francais, qui decrivent ce qui doit
etre produit. Pas de titre, pas de commentaire, pas de liste, pas de guillemets.

Pars de la demande et AJOUTE ce qu'un auteur aurait a decider de toute facon.
« un renard dans la neige » devient « un renard roux de trois quarts dans une
clairiere enneigee au crepuscule, lumiere rasante et doree, souffle visible dans
l'air froid, sapins flous a l'arriere-plan ».

Deux interdits :
  - n'invente pas de SUJET. Si la demande parle d'un renard, il n'y a ni loup ni
    personnage en plus.
  - ne commente pas la demande, ne dis pas ce que tu fais. Rends la description,
    rien d'autre.

"""

# Ce qu'il y a a decider n'est pas le meme selon ce qu'on produit : une video a
# une camera, un maillage a des materiaux. Demander « le cadrage et la lumiere »
# a une demande de 3D passe a cote de l'essentiel.
_A_DECIDER = {
    "image": "Ici : le cadrage, la lumiere, le moment, la matiere, l'arriere-plan.",
    "video": "Ici : le mouvement du sujet, celui de la camera, la lumiere et le "
             "decor. Un seul plan, pas de montage ni de changement de scene.",
    "objet3d": "Ici : la forme d'ensemble, les materiaux et leur etat de surface, "
               "l'objet seul, vu en entier, sur fond neutre.",
    # Animer une image fournie : la scene EXISTE deja. La redecrire ferait
    # derailler le modele vers autre chose que ce qu'on lui montre — on ne parle
    # donc que de ce qui bouge.
    "animation": "L'image de depart existe deja : ne la decris pas. Dis "
                 "seulement CE QUI BOUGE — le mouvement du sujet, celui de la "
                 "camera, le vent, la lumiere qui change. Un seul plan.",
}

SYS_ENRICHIR_DUR = """

Ta reponse precedente recopiait la demande. Ce n'est pas ce qu'on te demande :
ajoute au moins dix mots de decor et de precisions concretes."""

# Les etiquettes danbooru de "pony" et "planche" ne sont pas de la prose : les
# enrichir en francais les casserait.
_SANS_ENRICHISSEMENT = ("pony", "planche")
# « edition » en est volontairement absente. Son prompt n'est pas une
# description mais une CONSIGNE — « change the sky to a stormy night sky » — et
# l'enrichir en scene complete ferait REGENERER l'image au lieu de la retoucher.
# On perdrait l'original, et rien dans le code ne saurait distinguer une consigne
# enrichie d'une description : c'est le genre de faute qu'on ne peut pas
# rattraper apres coup.
_ENRICHIT = {"image": "image", "personnage": "image",
             "video": "video", "video_image": "animation", "objet3d": "objet3d"}


def _mots(t):
    return set(re.findall(r"[a-zà-ÿ]{4,}", sans_accents((t or "").lower())))


def _enrichi(avant, apres):
    """Vrai si le resultat apporte vraiment quelque chose.

    Deux mesures, toutes deux necessaires : assez de mots NOUVEAUX, et un texte
    plus long que la demande. La premiere seule laisserait passer une
    paraphrase ; la seconde seule, un remplissage qui repete la demande.
    """
    if not apres or len(apres.split()) < len(avant.split()) + 5:
        return False
    return len(_mots(apres) - _mots(avant)) >= 5


def _cadre_technique(plan):
    """Ce qui va vraiment produire le rendu, dit au modele qui ecrit le prompt.

    Le moteur, la taille et les etapes sont deja choisis a ce moment-la : les
    taire revenait a faire ecrire a l'aveugle. Une image verticale ne se decrit
    pas comme une horizontale, et un moteur reconnu pour le texte lisible merite
    qu'on lui redige le texte a afficher.
    """
    m = CATALOGUE.get(plan.get("modele")) or {}
    if not m:
        return ""
    lignes = ["", "Ce qui produira le rendu, pour que tu ecrives en consequence :",
              f"  - moteur : {m.get('titre', plan.get('modele'))}"
              + (f" — {m['pour']}" if m.get("pour") else ""),
              "  - il tourne dans ComfyUI : ta phrase est une consigne de rendu, "
              "pas une reponse a quelqu'un."]
    l, h = plan.get("largeur"), plan.get("hauteur")
    if l and h:
        forme = ("verticale" if h > l * 1.1 else
                 "horizontale" if l > h * 1.1 else "carree")
        lignes.append(f"  - image {forme} de {int(l)}x{int(h)} : compose pour ce "
                      f"format, n'y fais pas tenir ce qui n'y tient pas.")
    if not m.get("traduire") and not m.get("multilingue"):
        lignes.append("  - ce moteur lit le francais : ecris en francais.")
    return "\n".join(lignes) + "\n"


async def enrichir(plan, texte, tid):
    """Fait du prompt une vraie description, en un appel qui ne fait que cela."""
    quoi = _ENRICHIT.get(plan.get("intention"))
    if not quoi:
        return plan
    if plan.get("modele") in _SANS_ENRICHISSEMENT:
        return plan
    depart = (plan.get("prompt") or texte or "").strip()
    if not depart:
        return plan
    if _enrichi(texte, depart):
        return plan             # l'aiguilleur a deja fait le travail
    base = SYS_ENRICHIR + _A_DECIDER[quoi] + _cadre_technique(plan)
    for systeme in (base, base + SYS_ENRICHIR_DUR):
        try:
            # Le modele d'ECRITURE, pas celui d'aiguillage : enrichir est une
            # tache de redaction, et c'etait la derniere des trois a utiliser
            # encore le petit modele de classement.
            brut = await appeler_ollama(depart, None, systeme, json_mode=False,
                                        temperature=0.4, tid=tid,
                                        modele=choisir_modele_ecriture())
        except Exception as e:
            journal(tid, f"enrichissement indisponible ({type(e).__name__}) — "
                         f"demande gardee telle quelle")
            return plan
        propose = " ".join((brut or "").split())
        if latin(propose) and _enrichi(depart, propose):
            plan["prompt"] = propose
            journal(tid, f"demande enrichie : {propose[:90]}")
            return plan
    journal(tid, "enrichissement sans effet")
    # La marque, plutot qu'un envoi silencieux : c'est elle qui declenche la
    # question. Sans elle, l'utilisateur decouvrait le probleme dans le rendu.
    plan["enrichissement_rate"] = True
    return plan


async def traduire(plan, tid):
    """Traduit le prompt vers l'anglais pour les seuls moteurs qui l'exigent.

    Appel separe et volontairement pauvre : quand le meme appel devait a la fois
    aiguiller, enrichir, produire du JSON et traduire, le modele lachait la
    traduction en premier (mesure : hibou -> hippopotamus). Isolee, la tache
    redevient a sa portee. En cas d'echec on garde le francais : un prompt
    francais donne une image approximative, un mot invente donne le mauvais sujet.
    """
    if not CATALOGUE.get(plan.get("modele"), {}).get("traduire"):
        return plan
    # champs et textes doivent etre construits par le MEME filtre : un prompt
    # non-texte (le LLM renvoie parfois une liste) sortait de "textes" sans
    # sortir de "champs", et zip() recollait alors chaque traduction sur le
    # champ suivant — le prompt recevait la case 1, la case 1 la case 2.
    champs = []
    if isinstance(plan.get("prompt"), str) and plan["prompt"].strip():
        champs.append(("prompt", None))
    cases = plan.get("cases")
    if isinstance(cases, list):
        champs += [("cases", i) for i, c in enumerate(cases) if isinstance(c, str) and c.strip()]
    textes = [(plan["prompt"] if k == "prompt" else plan["cases"][i]) for k, i in champs]
    if not textes:
        return plan
    # Un modele a etiquettes n'attend pas de la prose : traduit comme une phrase,
    # « 1girl » devenait « girl » et « contre-plongee » devenait « counterattack ».
    etiquete = bool(CATALOGUE.get(plan.get("modele"), {}).get("etiquettes"))
    gardes = [[]] * len(textes)
    if etiquete:
        separes = [separer_controle(t) for t in textes]
        gardes = [g for g, _ in separes]
        textes = [r or t for (_, r), t in zip(separes, textes)]
    # ' '.join(t.split()) : un prompt contenant un retour a la ligne aurait
    # produit plus de lignes que d'items, et la traduction aurait ete abandonnee.
    demande = "\n".join(f"{n}. {chr(32).join(t.split())}"
                        for n, t in enumerate(textes, 1))
    for essai in (1, 2):
        try:
            # Le modele d'ECRITURE, pas celui d'aiguillage. Sans ce
            # parametre, la voie locale prenait MODELE_LLM — le petit modele qui
            # sert a classer les demandes — et degenerait : ideogrammes inseres
            # dans l'anglais, series de « @@@@@ », identifiants de code
            # hallucines. Meme corpus de vingt demandes, meme consigne, seul le
            # modele change : 10 a 30 % de traductions acceptees avec le petit,
            # 95 % avec celui d'ecriture, 100 % par un fournisseur distant.
            #
            # Un commentaire d'enrichir() disait qu'elle « etait la derniere des
            # trois a utiliser encore le petit modele de classement ». Elle ne
            # l'etait pas : traduire avait ete oubliee.
            brut = await appeler_ollama(demande, None, SYS_TRADUCTION,
                                        json_mode=False, temperature=0.1, tid=tid,
                                        modele=choisir_modele_ecriture())
        except Exception as e:
            return replier_sur_multilingue(
                plan, tid, f"traduction indisponible ({type(e).__name__})")
        lignes = [re.sub(r"^\s*\d+[.)]\s*", "", l).strip()
                  for l in brut.splitlines() if l.strip()]
        if len(lignes) == len(textes) and all(lignes) and all(map(latin, lignes)):
            for (k, i), val, garde in zip(champs, lignes, gardes):
                val = recomposer(garde, val)
                if k == "prompt": plan["prompt"] = val
                else: plan["cases"][i] = val
            journal(tid, f"traduit pour {plan['modele']} : {lignes[0][:70]}")
            return plan
        cause = ("reponse hors alphabet latin" if len(lignes) == len(textes)
                 else f"{len(lignes)} lignes rendues pour {len(textes)} attendues")
        if essai == 1:
            journal(tid, f"traduction rejetee ({cause}) — seconde tentative")
    return replier_sur_multilingue(plan, tid, f"traduction rejetee ({cause})")

SYS_SUJET = """On te donne une demande adressee a un studio qui produit des images,
des videos et des musiques. Extrais le SUJET : la chose concrete a produire.

Reponds par ce sujet en un a cinq mots, sans phrase, sans ponctuation finale.
Si la demande ne dit pas quoi produire, reponds exactement : AUCUN

Exemples :
  un chat noir                          -> chat noir
  un renard roux dans la neige          -> renard roux
  une musique de piano melancolique     -> piano melancolique
  une video d'une bougie qui brule      -> bougie qui brule
  une image sympa                       -> AUCUN
  fais-moi un truc pour mon projet      -> AUCUN
  surprends-moi                         -> AUCUN
  une petite musique                    -> AUCUN

Un support (image, photo, dessin, video, film, musique, son, chanson) n'est pas un
sujet. Si tu n'as que cela, reponds AUCUN."""

# Trois mots suffisent a nommer un sujet (« un chat noir ») ; au-dela de huit,
# une demande contient forcement de quoi travailler et l'appel serait du gaspillage.
MOTS_VERIF_SUJET = 8
# Mots qui ne designent qu'un support ou une generalite : s'il ne reste que cela,
# c'est que le modele n'a rien trouve a extraire.
_CREUX = {"aucun", "image", "images", "photo", "photos", "dessin", "video", "videos",
          "film", "musique", "son", "chanson", "truc", "chose", "projet", "sympa",
          "belle", "beau", "joli", "jolie", "petite", "petit", "une", "un", "de",
          "du", "des", "la", "le", "les", "pour", "mon", "ma", "quelque"}

async def sujet_nomme(texte, tid=None):
    """Extrait le sujet plutot que de juger la demande.

    La version precedente posait une question fermee (« y a-t-il un sujet ? ») et
    repondait « non » a « un chat noir » : le modele confondait bref et vague, et
    on aurait interroge un utilisateur parfaitement clair. Demander d'EXTRAIRE
    donne une reponse verifiable par le code, et c'est une tache que le modele
    reussit. Le doute profite a l'execution : en cas d'echec d'appel, on n'arrete
    pas l'utilisateur pour rien.
    """
    try:
        r = await appeler_ollama(texte, None, SYS_SUJET, json_mode=False,
                                 temperature=0.0, tid=tid)
    except Exception:
        return True
    # lettres latines seulement : qwen glisse par moments un ideogramme, qui
    # aurait compte comme un sujet valide.
    # Une reponse vide n'est pas un « aucun sujet » : c'est un modele absent ou
    # muet. Le doute doit profiter a l'execution, pas interrompre l'utilisateur.
    if not (r or "").strip():
        return True
    # comparaison sans accents des deux cotes : « video » figure dans _CREUX,
    # « video » accentue y echappait et validait un faux sujet.
    mots = [w for w in re.findall(r"[A-Za-zÀ-ſ]+", (r or ""))
            if sans_accents(w) not in _CREUX]
    # Un sujet doit avoir ete NOMME par l'utilisateur. Le modele en invente un
    # quand il n'en trouve pas : « une image sympa » lui inspirait « paysage
    # d'hiver ». On ne garde que ce qui figure vraiment dans sa demande.
    source = sans_accents(texte or "")
    # Trois lettres suffisent a nommer un sujet (« un coq », « une oie »), et on
    # compare sur les quatre premieres lettres pour tolerer les flexions :
    # le modele repond « chats » la ou l'utilisateur a ecrit « un chat ».
    return any(sans_accents(w)[:4] in source for w in mots if len(w) >= 3)

def sans_accents(t):
    return "".join(c for c in unicodedata.normalize("NFD", (t or "").lower())
                   if unicodedata.category(c) != "Mn")

QUESTIONS_SANS_SUJET = [
    "Que veux-tu voir, exactement ? (par exemple : un renard dans la neige, "
    "un portrait, une rue sous la pluie)",
    "Sous quelle forme ? (une image, une video, une musique)",
    "Dans quel esprit ? (photo realiste, illustration, manga, peinture)",
]

_POINT_DE_VUE = """La chanson est chantee PAR QUELQU'UN D'AUTRE, jamais par la
personne dont elle parle. Si c'est un hommage a un disparu, celui qui chante est
un proche : il parle de lui a la troisieme personne, ou s'adresse a lui.
N'ecris JAMAIS « je » a la place de la personne honoree."""

SYS_REFRAIN = """Tu ecris LE REFRAIN d'une chanson, et rien d'autre.

Quatre a six lignes, une par ligne, sans balise, sans titre, sans commentaire.
C'est la partie qu'on retient : une image forte, des mots simples, une phrase
qui revient. Reprends le prenom ou le sujet de la demande.

Ajoute a la fin une ou deux lignes de CHOEURS, entre parentheses, courtes et
chantables : (oh oh oh), (on chante pour toi). Elles seront reprises telles
quelles a chaque refrain.

""" + _POINT_DE_VUE + """

Ne repete pas la meme ligne plus de deux fois."""

SYS_COUPLETS = """Tu ecris LES COUPLETS d'une chanson, et rien d'autre.

Format, strictement :
  1.
  <les lignes du premier couplet, une par ligne>
  2.
  <les lignes du deuxieme couplet>
  3.
  <les lignes du troisieme couplet>

Quatre a six lignes par couplet. Pas de titre, pas de commentaire, pas de
refrain : le refrain est ecrit ailleurs.

Chaque couplet raconte une chose DIFFERENTE, prise dans la demande : un metier,
un lieu, une habitude, une passion, un souvenir precis. N'ecris pas trois fois
la meme idee avec d'autres mots. Sers-toi des details donnes : ce sont eux qui
rendent la chanson vraie.

""" + _POINT_DE_VUE

_LIGNE_SECTION = re.compile(r"^\s*\[\s*([A-Za-z]+)\s*\d*\s*\]\s*$", re.I)
_SECTIONS = {"verse": "verse", "couplet": "verse", "chorus": "chorus",
             "refrain": "chorus", "bridge": "bridge", "pont": "bridge",
             "outro": "outro", "fin": "outro", "intro": "intro",
             "inst": "inst", "instrumental": "inst"}
_NUMERO = re.compile(r"^\s*(\d)\s*[.)\]:-]?\s*$")


def normaliser_sections(t):
    """Ramene les balises a celles que le modele audio reconnait."""
    sortie = []
    for ligne in (t or "").splitlines():
        m = _LIGNE_SECTION.match(ligne)
        if m:
            nom = _SECTIONS.get(m.group(1).lower())
            sortie.append(f"[{nom}]" if nom else ligne.rstrip())
        else:
            sortie.append(ligne.rstrip())
    return "\n".join(sortie).strip()


def _lignes_propres(t, maxi=8):
    """Les lignes chantables d'une reponse : ni balises, ni numeros, ni doublons
    consecutifs. Une chanson qui boucle sur un vers n'est pas une chanson."""
    gardees = []
    for l in (t or "").splitlines():
        l = l.strip().strip('"').rstrip(",")
        if not l or _LIGNE_SECTION.match(l) or _NUMERO.match(l):
            continue
        if len(l) > 120 or l.startswith(("#", "//", "Voici", "Bien sur", "Refrain",
                                         "Couplet", "Chorus", "Verse", "Pont")):
            continue
        # Le modele derive de langue en cours de route : mesure du 28 aout 2026,
        # deux couplets sur trois rendus en arabe pour une chanson francaise.
        # Une consigne ne suffit pas, on ecarte la ligne.
        if not latin(l):
            continue
        l = _replier(_degrossir(l))
        if _radote(l):
            continue
        if len(l.split()) < 2:
            continue
        if gardees and l.lower() == gardees[-1].lower():
            continue
        gardees.append(l)
        if len(gardees) >= maxi:
            break
    return gardees


def _degrossir(ligne):
    """Supprime les mots repetes a la suite dans une ligne.

    Le modele bourre les vers pour tenir la mesure : « Martin, menuisier,
    menuisier, menuisier, Martin ». Ce n'est pas une intention, c'est un tic —
    on l'enleve plutot que de jeter une ligne par ailleurs correcte. Le prenom
    est change : celui d'origine venait d'une demande reelle, et d'un hommage a
    quelqu'un.
    """
    sortie, precedent = [], ""
    for mot in ligne.split():
        nu = mot.strip(",;:.!?()…").lower()
        if nu and nu == precedent:
            continue
        precedent = nu
        sortie.append(mot)
    return " ".join(sortie)


def _replier(ligne):
    """Rend une seule fois un motif que la ligne repete en boucle.

    « Chaque piece, un chef-d'oeuvre, chaque piece, un chef-d'oeuvre » est le
    meme vers colle deux fois. Les mots ne se suivent pas a l'identique, donc
    _degrossir ne voit rien : on cherche ici la periode du motif.
    """
    mots = ligne.split()
    nus = [m.strip(",;:.!?()…").lower() for m in mots]
    for periode in range(1, len(mots) // 2 + 1):
        if len(mots) % periode:
            continue
        if all(nus[i] == nus[i % periode] for i in range(len(nus))):
            return " ".join(mots[:periode]).rstrip(",;")
    return ligne


def _radote(ligne):
    """Vrai si la ligne reste pauvre une fois les repetitions collees enlevees."""
    mots = [m.strip(",;:.!?()…").lower() for m in ligne.split()]
    mots = [m for m in mots if m]
    return len(mots) > 4 and len(set(mots)) * 2 < len(mots)


def _boucle(lignes):
    """Vrai si une meme ligne occupe une part excessive du morceau."""
    if not lignes:
        return True
    return max(lignes.count(l) for l in set(lignes)) > max(2, 0.4 * len(lignes))


def _consigne_langue(langue):
    noms = {"fr": "FRANCAIS", "en": "ANGLAIS", "es": "ESPAGNOL", "de": "ALLEMAND",
            "it": "ITALIEN", "pt": "PORTUGAIS", "ja": "JAPONAIS"}
    return (chr(10)*2 + "Ecris en " + noms.get(langue, "FRANCAIS") +
            ", et dans cette langue seulement, du premier au dernier mot.")


async def _morceau(texte, systeme, tid, maxi, mini, libelle):
    """Un appel court, deux tirages : le modele deraille surtout quand on lui
    demande long. Rend une liste de lignes, ou une liste vide."""
    for essai, chaleur in ((1, 0.7), (2, 0.5), (3, 0.35)):
        try:
            brut = await appeler_ollama(texte, None, systeme, json_mode=False,
                                        temperature=chaleur, tid=tid,
                                        modele=choisir_modele_ecriture(),
                                        garder="5m")
        except Exception as e:
            # Un appel qui casse ne doit pas condamner la chanson : le modele
            # peut avoir simplement mis trop longtemps a se charger.
            journal(tid, f"{libelle}, essai {essai} : appel impossible "
                         f"({type(e).__name__}: {e})")
            continue
        lignes = _lignes_propres(brut, maxi)
        if len(lignes) >= mini and not _boucle(lignes):
            return lignes
        journal(tid, f"{libelle}, essai {essai} : {len(lignes)} ligne(s) retenue(s) — "
                     f"debut : {' / '.join((brut or '').split(chr(10))[:3])[:160]}")
    journal(tid, f"{libelle} : rien d'exploitable")
    return []


def _choeurs(refrain):
    """Garantit une ou deux lignes de choeurs au refrain.

    Le modele audio chante entre parentheses en voix d'accompagnement. La
    consigne le demande, mais un tirage sur deux l'oublie : plutot que de
    relancer l'appel, on reprend la ligne la plus courte du refrain, celle qui
    se crie le mieux.
    """
    if any("(" in l for l in refrain):
        return refrain
    # La ligne la plus courte QUI SE CHANTE : « Piano » repris en choeur ne
    # veut rien dire, il faut une phrase.
    chantables = [l for l in refrain if 3 <= len(l.split()) <= 8]
    court = min(chantables or refrain, key=len, default="")
    echo = court.strip(" .!?,").lower()
    ajouts = ["(oh, oh, oh)"]
    if 4 <= len(echo) <= 34:
        ajouts.append("(" + echo + ")")
    return refrain + ajouts


async def ecrire_paroles(texte, duree, tid, langue_voulue="fr"):
    """Le refrain, puis les couplets, puis l'assemblage.

    La structure - un refrain repete, trois couplets differents, des choeurs -
    est montee ici et non demandee au modele : demandee, elle sortait juste une
    fois sur trois. Chaque appel ne porte plus qu'un seul morceau court.
    """
    try:
        return await _ecrire_paroles(texte, duree, tid, langue_voulue)
    finally:
        # Sans ce relachement, les 18 Go du modele d'ecriture restent en
        # memoire et ComfyUI demarre sur une carte deja pleine.
        await liberer_modele(choisir_modele_ecriture())


async def _ecrire_paroles(texte, duree, tid, langue_voulue):
    langue = _consigne_langue(langue_voulue)
    refrain = await _morceau(texte, SYS_REFRAIN + langue, tid, maxi=7, mini=3,
                             libelle="refrain")
    refrain = _choeurs(refrain)
    if not refrain:
        journal(tid, "pas de refrain — le morceau sera instrumental")
        return ""

    couplets = []
    brut = ""
    for essai, chaleur in ((1, 0.7), (2, 0.55), (3, 0.4)):
        try:
            brut = await appeler_ollama(texte, None, SYS_COUPLETS + langue,
                                        json_mode=False, temperature=chaleur,
                                        tid=tid,
                                        modele=choisir_modele_ecriture(),
                                        garder="5m") or ""
        except Exception:
            brut = ""
        couplets = _decouper_couplets(brut)
        if len(couplets) >= 2:
            break
        journal(tid, f"couplets, essai {essai} : {len(couplets)} retenu(s) sur "
                     f"{len((brut or '').splitlines())} lignes — "
                     f"debut : {' / '.join((brut or '').split(chr(10))[:3])[:160]}")
    if not couplets:
        journal(tid, "pas de couplet exploitable — le morceau sera instrumental")
        return ""
    while len(couplets) < 3:            # plutot deux vrais couplets que trois bavards
        break

    morceaux = []
    for c in couplets[:3]:
        morceaux.append("[verse]\n" + "\n".join(c))
        morceaux.append("[chorus]\n" + "\n".join(refrain))
    paroles = normaliser_sections("\n\n".join(morceaux))
    journal(tid, f"paroles ecrites : {len(couplets[:3])} couplets, refrain de "
                 f"{len(refrain)} lignes, {len(paroles.splitlines())} lignes en tout")
    return paroles


def _decouper_couplets(brut):
    """Separe la reponse aux numeros 1, 2, 3 places seuls sur leur ligne."""
    courants, tous = [], []
    for l in (brut or "").splitlines():
        if _NUMERO.match(l.strip()):
            if courants:
                tous.append(courants)
            courants = []
            continue
        propre = _lignes_propres(l, 1)
        if propre and len(courants) < 6:
            courants.append(propre[0])
    if courants:
        tous.append(courants)
    return [c for c in tous if len(c) >= 3 and not _boucle(c)]


async def aiguiller(texte, tid, conv, image_b64=None, a_une_image=False,
                    modele_force=None, taille=None, priorite=""):
    pid = (TACHES.get(tid) or {}).get("proprietaire")
    # Un agrandissement se reconnait a l'ecrit et ne demande rien au modele :
    # ni sujet, ni cadrage, ni style. On tranche donc AVANT de l'appeler — dix
    # secondes epargnees, et surtout aucun risque qu'il decide de REGENERER
    # l'image au lieu de l'agrandir. Sans image jointe, l'execution reprendra la
    # derniere sortie de la conversation ; s'il n'y en a pas, elle le dira.
    # Le classifieur, en second rideau : les expressions ci-dessous couvrent
    # les formulations courantes, lui rattrape les autres — « il me faudrait
    # des mouvements plus naturels » n'etait prevu par aucune.
    if AIGUILLEUR and not modele_force and not a_une_image:
        propose, marge = AIGUILLEUR.classer(texte)
        if propose in SANS_ECRITURE and marge >= _aiguilleur.MARGE_SURE \
                and not (veut_fluidifier(texte) or veut_detourer(texte)
                         or veut_agrandir(texte)):
            journal(tid, f"« {propose} » reconnu sans appeler de modele "
                         f"(marge {marge:.0f})")
            return {"intention": propose, "modele": propose, "prompt": texte,
                    "parametres": {}, "parametres_bruts": {},
                    "raison": f"{propose} : reconnu a la formulation"}

    # Reconnues a l'ecrit, avant tout appel : ces tournures ne laissent aucun
    # doute, et le catalogue suffit ensuite a choisir le cote du masque.
    # Le detourage passe AVANT : « enleve le fond », « mets-la sur fond
    # transparent », « retire l'arriere-plan » sont ses formulations depuis le
    # premier jour, et elles contiennent les memes verbes que la retouche. Sans
    # cette garde, « enleve le fond » remplaçait le SUJET — l'inverse exact de
    # ce qu'on demande.
    if a_une_image == "image" and not modele_force and not veut_detourer(texte):
        # La zone nommee passe devant : « enleve le chien » vise le chien, pas
        # « le sujet » que BiRefNet aurait devine. On ne la propose que si une
        # machine peut la servir — le modele de selection est un telechargement
        # optionnel.
        ordre = []
        if not manquants_partout("retoucher_zone"):
            ordre.append((veut_zone_nommee, "retoucher_zone"))
        ordre += [(veut_retoucher_fond, "retoucher_fond"),
                  (veut_retoucher_sujet, "retoucher_sujet")]
        for reconnait, quoi in ordre:
            if reconnait(texte):
                journal(tid, f"« {quoi.replace('_', ' ')} » reconnu a la "
                             f"formulation — la zone hors masque sera intacte")
                return {"intention": quoi, "modele": quoi, "prompt": texte,
                        "parametres": {}, "parametres_bruts": {},
                        "raison": "retouche localisee : le reste de l'image ne "
                                  "sera pas touche"}

    if veut_fluidifier(texte) and not modele_force:
        journal(tid, "fluidite video reconnue — aucune analyse necessaire")
        return {"intention": "fluidifier", "modele": "fluidifier", "prompt": texte,
                "parametres": {}, "parametres_bruts": {},
                "raison": "images intercalees dans la video precedente"}

    if veut_detourer(texte) and not modele_force:
        journal(tid, "detourage reconnu — aucune analyse necessaire")
        return {"intention": "detourer", "modele": "detourer", "prompt": texte,
                "parametres": {}, "parametres_bruts": {},
                "raison": "detourage : le sujet est isole, le fond devient transparent"}

    if veut_agrandir(texte) and not modele_force:
        journal(tid, "agrandissement reconnu — aucune analyse necessaire")
        return {"intention": "agrandir", "modele": "agrandir", "prompt": texte,
                "parametres": {}, "parametres_bruts": {},
                "raison": "agrandissement : l'image est reprise telle quelle"}

    loin = "" if image_b64 else llm_distant_possible(texte, pid)
    pourquoi = raison_du_local(texte, image_b64, pid)
    if pourquoi:
        journal(tid, pourquoi)
    journal(tid, "analyse par " + (fournisseurs.LLM[loin]["titre"] if loin
                                   else MODELE_LLM) + "…")
    sys_p = SYSTEME.format(catalogue=catalogue_texte(), contexte=bloc_contexte(conv))
    # La consigne depend de CE QUI est joint : dire « une image est fournie »
    # quand c'est une video faisait proposer de retoucher une image qui n'existe
    # pas.
    if a_une_image == "video":
        sys_p += ("\nUne VIDEO est fournie par l'utilisateur : les seules "
                  "intentions possibles sont 'fluidifier' (plus fluide, ou au "
                  "ralenti) ou 'lecture'.")
    elif a_une_image == "audio":
        sys_p += ("\nUn MORCEAU est fourni par l'utilisateur : il veut le "
                  "retoucher, pas en creer un autre. Reponds intention 'audio', "
                  "et mets dans tags_audio le STYLE vers lequel le faire aller.")
    elif a_une_image:
        sys_p += "\nUne image est fournie par l'utilisateur : privilegie 'edition', 'video_image' ou 'lecture'."
    # La priorite est une consigne de l'utilisateur, pas une heuristique : on la
    # transmet a l'aiguilleur, qui choisit le moteur en consequence. Le code, lui,
    # ajuste les etapes — la seule grandeur qui echange du temps contre de la
    # qualite a modele constant.
    if priorite == "rapide":
        sys_p += ("\nL'utilisateur privilegie la RAPIDITE : choisis le moteur le plus "
                  "rapide qui sache faire le travail, et propose peu d'etapes.")
    elif priorite == "soigne":
        sys_p += ("\nL'utilisateur privilegie la QUALITE : prends le moteur le plus abouti "
                  "meme s'il est lent, et propose un nombre d'etapes genereux.")
    # Deux tentatives : le mode JSON d'Ollama tronque parfois une chaine sur les
    # petits modeles (mesure : qwen2.5vl, 2 reponses invalides sur 4). Un simple
    # nouveau tirage suffit presque toujours, et coute moins qu'un repli aveugle.
    plan = None
    for essai in (1, 2):
        try:
            # l'aiguilleur ne recoit PAS l'image : il n'a pas la vision, et savoir
            # qu'une image est jointe lui suffit pour choisir l'intention.
            brut = await appeler_ollama(texte, None, sys_p, temperature=0.15, tid=tid)
            m = re.search(r"\{.*\}", brut, re.S)
            plan = json.loads(m.group(0) if m else brut)
            break
        except json.JSONDecodeError:
            journal(tid, "reponse mal formee" + (" — seconde tentative" if essai == 1 else ""))
        except Exception as e:
            journal(tid, f"Ollama indisponible ({type(e).__name__}) — aiguillage par mots-cles")
            return normaliser(secours(texte, a_une_image), texte,
                              a_une_image, conv, taille, priorite)
    # json.loads peut reussir en renvoyant une liste ou un nombre : normaliser
    # leverait alors AttributeError au lieu de se replier proprement.
    if not isinstance(plan, dict):
        journal(tid, "aiguillage par mots-cles")
        return normaliser(secours(texte, a_une_image), texte,
                          a_une_image, conv, taille, priorite)
    plan = normaliser(plan, texte, a_une_image, conv, taille, priorite)

    # Filet sur les demandes tres courtes que l'aiguilleur a decide d'executer :
    # s'il n'y a aucun sujet, il en inventerait un a la place de l'utilisateur.
    # Une reprise (« rends-la plus sombre ») ne nomme aucun sujet : il est dans
    # l'image precedente. L'interroger reviendrait a casser la conversation.
    # Un modele impose depuis l'interface rend ce filet inutile : son resultat
    # serait ecrase, et l'appel rechargerait le 7B pour rien.
    if (plan.get("intention") != "question"
            and plan.get("intention") not in ("edition", "video_image", "lecture")
            and len((texte or "").split()) <= MOTS_VERIF_SUJET
            and not a_une_image and not modele_force
            and not await sujet_nomme(texte, tid)):
        journal(tid, "aucun sujet nomme — precision demandee plutot que devinee")
        plan["intention"] = "question"
        plan["questions"] = list(QUESTIONS_SANS_SUJET)
        plan["questions_forcees"] = True
        # Le prompt contient le sujet que l'aiguilleur avait invente. Enregistre
        # tel quel, il reviendrait dans le contexte au tour suivant et relancerait
        # le studio sur ce sujet — exactement ce que ce filet doit empecher.
        plan["prompt"] = None
        plan.pop("prompt_repli", None)
    return plan

# L'intention fait foi : un petit modele se trompe volontiers de cle tout en
# identifiant correctement ce qui est demande. On recolle par code plutot que
# d'esperer que le LLM soit coherent.
MODELE_IMPOSE = {"video": "wan5b", "video_image": "wan14b", "edition": "edition",
                 "planche": "planche", "objet3d": "objet3d"}
# l'audio a deux moteurs (turbo rapide, sft soigne) : on ne force que si la cle est absurde
# Ce que l'auditeur ENTEND, dit dans la langue d'ACE-Step. Les cles sont
# cherchees sans accent ni casse dans la demande de l'utilisateur.
_GENRES = [
    ("rock and roll", ("rock and roll", "rock & roll", "rock&roll", "rock'n'roll",
                       "rock n roll", "rockabilly")),
    ("rock", ("rock", "punk", "grunge")),
    ("metal", ("metal", "hardcore")),
    ("blues", ("blues",)),
    ("jazz", ("jazz", "swing", "bebop")),
    ("folk", ("folk", "country", "bluegrass")),
    ("reggae", ("reggae", "ska", "dub")),
    ("funk", ("funk", "groove", "disco")),
    ("soul", ("soul", "motown", "rnb", "r&b")),
    ("hip hop", ("rap", "hip hop", "hip-hop")),
    ("electronic", ("electro", "techno", "house", "synthwave", "edm")),
    ("pop", ("pop", "variete")),
    ("classical", ("classique", "symphonique", "orchestral")),
    ("ballad", ("ballade", "berceuse", "slow")),
    ("chanson francaise", ("chanson francaise", "chanson a texte")),
]
_INSTRUMENTS = [
    ("electric guitars", ("guitare electrique", "guitares electriques", "guitare")),
    ("acoustic guitar", ("guitare acoustique", "guitare seche")),
    ("bass guitar", ("basse",)),
    ("drums", ("batterie", "percussion", "percussions", "tambour")),
    ("piano", ("piano",)),
    ("hammond organ", ("orgue", "hammond")),
    ("violin", ("violon",)),
    ("saxophone", ("saxophone", "saxo", "sax")),
    ("trumpet", ("trompette",)),
    ("harmonica", ("harmonica",)),
    ("synthesizer", ("synthe", "synthetiseur", "synthes")),
    ("accordion", ("accordeon",)),
    ("cello", ("violoncelle",)),
    ("flute", ("flute",)),
]
_VOIX = [
    ("male lead vocal", ("un homme chante", "chantee par un homme", "voix d'homme",
                         "voix masculine", "chanteur", "homme qui chante")),
    ("female lead vocal", ("une femme chante", "chantee par une femme", "voix de femme",
                           "voix feminine", "chanteuse", "femme qui chante")),
]
_CHOEURS_DEMANDES = ("choeur", "chorale", "backing", "harmonies")
_AMBIANCES = [
    ("energetic", ("entrainant", "energique", "puissant", "endiable", "rythme")),
    ("melancholic", ("triste", "melancolique", "nostalgique", "hommage", "deuil",
                     "disparu", "decede", "en memoire")),
    ("joyful", ("joyeux", "gai", "festif", "heureux")),
    ("calm", ("calme", "doux", "apaisant", "tranquille")),
    ("epic", ("epique", "grandiose", "heroique")),
]


_TEMPOS = {"rock and roll": 132, "rock": 122, "metal": 140, "blues": 80,
           "jazz": 120, "folk": 100, "reggae": 76, "funk": 108, "soul": 92,
           "hip hop": 90, "electronic": 126, "pop": 112, "classical": 80,
           "ballad": 68, "chanson francaise": 96}


def _trouves(texte, table):
    """Les libelles anglais dont un des mots-cles apparait dans la demande."""
    vus = []
    for anglais, cles in table:
        if any(c in texte for c in cles) and anglais not in vus:
            vus.append(anglais)
    return vus


def style_musical(texte, par=None):
    """Les etiquettes de style, lues dans la demande plutot que devinees.

    Rend une chaine prete pour ACE-Step, ou "" si la demande ne dit rien du son.
    Un genre general n'est garde que si aucun genre plus precis ne l'est deja :
    « rock and roll » et « rock » ensemble ne disent pas plus que le premier.
    """
    t = sans_accents((texte or "").lower())
    genres = _trouves(t, _GENRES)
    if len(genres) > 1 and genres[0].startswith(genres[1]):
        genres = genres[:1]
    genres = genres[:2]
    instruments = _trouves(t, _INSTRUMENTS)[:5]
    voix = _trouves(t, _VOIX)[:1]
    ambiances = _trouves(t, _AMBIANCES)[:2]

    morceaux = list(genres)
    bpm = (par or {}).get("bpm")
    if bpm:
        morceaux.append(f"{int(bpm)} BPM")
    morceaux += instruments + voix
    if any(c in t for c in _CHOEURS_DEMANDES):
        # Le genre de la voix principale entraine celui des choeurs : des
        # choeurs feminins sur une voix d'homme, personne ne l'a demande.
        morceaux.append("female backing vocals" if voix[:1] == ["female lead vocal"]
                        else "male backing vocals")
    morceaux += ambiances
    if not genres and not instruments:
        return ""
    morceaux.append("studio recording, clear vocals")
    return ", ".join(morceaux)


def _style_prose(style):
    """Vrai si la reponse ressemble a un recit plutot qu'a des etiquettes.

    Une liste d'etiquettes est courte et virgulee. Une biographie ne l'est pas :
    c'est exactement ce que le routeur a produit, et ACE-Step l'a chante comme
    tel.
    """
    if not style:
        return True
    if len(style.split()) > 30 or not latin(style):
        return True
    francais = (" le ", " la ", " les ", " un ", " une ", " des ", " qui ",
                " son ", " sa ", " ses ", " avec ", " pour ", " dans ", " etait ")
    creux = sans_accents(" " + style.lower() + " ")
    return any(m in creux for m in francais) or style.count(",") < 1



# ═══════════════════════ fournisseurs distants ═════════════════════════
#
# Le studio fonctionne entierement en local. Une cle d'API n'est qu'une option,
# et le local reste le repli de tout ce qui suit : une cle expiree ralentit,
# elle n'arrete rien.

FICHIER_CLES = os.path.join(DOSSIER_CONV, "_cles.json")
CLES = {}                     # fournisseur -> {"cle": ..., "modele": ...}
CHOIX = {"llm": "local", "image": "local", "audio": "local",
         "video": "local", "objet3d": "local"}

# Quelle table de fournisseurs regarde chaque modalite, et sous quel libelle
# elle se presente. L'ordre est celui de la page d'administration.
MODALITES = (
    ("llm", "texte", "LLM"),
    ("image", "images", "IMAGE"),
    ("audio", "musique", "AUDIO"),
    ("video", "video", "VIDEO"),
    ("objet3d", "objets 3D", "OBJET3D"),
)


def fournisseurs_de(modalite):
    """Les fournisseurs distants connus pour cette modalite. Vide pour la 3D."""
    nom = next((t for m, _, t in MODALITES if m == modalite), "")
    return getattr(fournisseurs, nom) if nom else {}


def intention_vers_modalite(intention):
    return {"image": "image", "edition": "image", "audio": "audio",
            "video": "video", "video_image": "video",
            "objet3d": "objet3d"}.get(intention, "")


def charger_cles():
    """Relit les cles et le choix de fournisseur.

    Le fichier vit dans conversations/, deja exclu du depot : une cle d'API
    n'a rien a faire dans un git, fut-il prive.
    """
    try:
        with open(FICHIER_CLES, encoding="utf-8") as f:
            d = json.load(f)
    except FileNotFoundError:
        return
    except Exception as e:
        print(f"cles illisibles ({e}) — le studio reste en local", flush=True)
        return
    CLES.update(d.get("cles") or {})
    for quoi, valeur in (d.get("choix") or {}).items():
        if quoi in CHOIX:
            CHOIX[quoi] = valeur
    poses = [f for f, v in CLES.items() if v.get("cle")]
    if poses:
        print(f"  Cles      : {', '.join(sorted(poses))}"
              f"   (texte : {CHOIX['llm']}, image : {CHOIX['image']})", flush=True)


def sauver_cles():
    tmp = FICHIER_CLES + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"cles": CLES, "choix": CHOIX}, f, ensure_ascii=False, indent=1)
    try:
        os.chmod(tmp, 0o600)      # sans effet sur Windows, utile ailleurs
    except OSError:
        pass
    os.replace(tmp, FICHIER_CLES)


def cle_de(fournisseur):
    return (CLES.get(fournisseur) or {}).get("cle") or ""


def modele_de(fournisseur):
    return (CLES.get(fournisseur) or {}).get("modele") or ""


def adulte(texte, plan=None):
    """Vrai si la demande releve du contenu adulte.

    Regle posee par l'utilisateur, et tenue en code : ce qui est adulte ne sort
    pas de la maison. Un reglage d'interface ne peut pas la lever — c'est tout
    l'interet de la mettre ici plutot que dans une case a cocher.

    Volontairement large : mieux vaut calculer en local une image qui aurait pu
    partir au loin que l'inverse.
    """
    if _SEXUEL.search(texte or ""):
        return True
    p = plan or {}
    if p.get("classement") in ("questionable", "explicit"):
        return True
    if _SEXUEL.search(p.get("prompt") or ""):
        return True
    return False


def llm_distant_possible(texte, pid=None):
    """Le fournisseur de texte a utiliser, ou "" pour rester en local."""
    if pid is not None and not nuage_actif(pid):
        return ""
    choix = fournisseur_dispo("llm") if pid is not None else CHOIX.get("llm", "local")
    if choix == "local" or choix not in fournisseurs.LLM or not cle_de(choix):
        return ""
    if adulte(texte):
        return ""
    return choix


# pid -> {"llm": False} : refus explicite du cloud pour CE navigateur. Absent
# veut dire « comme le reglage general », qui reste la reference.
NUAGE = {}
FICHIER_NUAGE = os.path.join(DOSSIER_CONV, "_nuage.json")


def charger_nuage():
    """Relit les interrupteurs poses par chacun.

    Un fichier illisible ne doit pas empecher le studio de demarrer : on repart
    sur les reglages generaux, ce qui est exactement le comportement d'avant.
    """
    try:
        with open(FICHIER_NUAGE, encoding="utf-8") as f:
            d = json.load(f)
    except FileNotFoundError:
        return
    except Exception as e:
        print(f"  interrupteurs du nuage illisibles ({e}) — reglages generaux",
              flush=True)
        return
    if isinstance(d, dict):
        NUAGE.update({k: v for k, v in d.items() if isinstance(v, dict)})


def sauver_nuage():
    """N'ecrit que ce qui s'ecarte du reglage general.

    Enregistrer les positions qui coincident avec le defaut ferait grossir le
    fichier sans rien apprendre, et surtout figerait ces gens-la : changer le
    reglage general dans /admin ne les toucherait plus.
    """
    utile = {}
    for pid, choix in NUAGE.items():
        garde = {m: v for m, v in choix.items()
                 if v != (CHOIX.get(m, "local") != "local")}
        if garde:
            utile[pid] = garde
    tmp = FICHIER_NUAGE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(utile, f, ensure_ascii=False, indent=1)
        os.replace(tmp, FICHIER_NUAGE)
    except OSError as e:
        print(f"  interrupteurs du nuage non enregistres : {e}", flush=True)


def fournisseur_dispo(modalite):
    """Le fournisseur joignable pour cette modalite, ou "".

    Celui que l'administration a choisi s'il a une cle ; sinon le premier de la
    table qui en a une. Une cle posee suffit donc a rendre la modalite
    activable depuis la page, sans repasser par /admin.
    """
    table = fournisseurs_de(modalite)
    prefere = CHOIX.get(modalite, "local")
    ordre = ([prefere] if prefere in table else []) + sorted(table)
    for nom in ordre:
        if cle_de(nom) or (cle_de("google") if nom in _PAR_GOOGLE else ""):
            return nom
    return ""


def nuage_actif(pid, modalite="llm"):
    """Position de l'interrupteur pour ce navigateur.

    Par defaut celle de l'administration : si elle a regle la modalite sur un
    fournisseur, l'interrupteur est allume ; sinon il est eteint. Un clic
    l'inverse, pour ce navigateur seulement.
    """
    defaut = CHOIX.get(modalite, "local") != "local"
    return (NUAGE.get(pid) or {}).get(modalite, defaut)


# Le signe de chaque modalite dans la barre du haut. Un dessin se reconnait
# plus vite qu'un mot, et la barre est etroite sur telephone.
SIGNES = {"llm": "☁", "image": "🖼", "audio": "♪",
          "video": "🎞", "objet3d": "▣"}


async def api_nuage(req):
    """Active ou coupe le cloud pour le navigateur qui appelle, et lui seul.

    Cet interrupteur est en facade, sans jeton : il ne peut donc pas etre
    global, sinon un visiteur du reseau depenserait les credits du proprietaire
    d'un seul clic. Le reglage general, lui, reste dans /admin.
    """
    pid = qui(req)
    if req.method == "POST":
        try:
            d = await req.json()
        except Exception:
            return web.json_response({"erreur": "corps illisible"}, status=400)
        modalite = str(d.get("modalite") or "llm")
        if modalite not in CHOIX:
            return web.json_response({"erreur": "modalite inconnue"}, status=400)
        NUAGE.setdefault(pid, {})[modalite] = bool(d.get("actif", True))
        sauver_nuage()

    etat = []
    for modalite, libelle, _ in MODALITES:
        dispo = fournisseur_dispo(modalite)
        conf = fournisseurs_de(modalite).get(dispo) or {}
        etat.append({
            "modalite": modalite, "libelle": libelle,
            "signe": SIGNES.get(modalite, "☁"),
            "actif": bool(dispo) and nuage_actif(pid, modalite),
            # Sans cle, il n'y a rien a activer : le bouton se cache plutot que
            # de promettre un ailleurs qui n'existe pas.
            "possible": bool(dispo),
            "titre": conf.get("titre", "local"),
        })
    return web.json_response({"modalites": etat})


def choix_distant(intention, texte, plan, pid=None):
    """Le moteur distant regle pour cette modalite, ou "" pour rester en local."""
    modalite = intention_vers_modalite(intention)
    if not modalite:
        return ""
    if pid is not None and not nuage_actif(pid, modalite):
        return ""
    choix = fournisseur_dispo(modalite) if pid is not None else CHOIX.get(modalite, "local")
    if choix == "local" or choix not in fournisseurs_de(modalite):
        return ""
    if adulte(texte, plan):
        return ""
    return choix


# Moteurs joignables par cle d'API, presentes a cote des moteurs locaux.
# « repli » est le moteur local qui prend la suite si l'appel echoue ou si la
# demande doit rester a la maison : il n'y a jamais de cul-de-sac.
MOTEURS_DISTANTS = {
    "nanobanana": {
        "titre": "Nano Banana (Gemini) — distant", "type": "image",
        "table": "IMAGE", "fournisseur": "nanobanana", "repli": "klein4b",
        "pour": "image rapide, excellente sur le texte et la retouche guidee",
        "duree": "10 s",
    },
    "lyria": {
        "titre": "Lyria 3 (Google) — distant", "type": "audio",
        "table": "AUDIO", "fournisseur": "lyria", "repli": "audioplus",
        "pour": "musique en une dizaine de secondes, clips d'environ 30 s",
        "duree": "10 s",
    },
    "meshy": {
        "titre": "Meshy — distant", "type": "objet3d",
        "table": "OBJET3D", "fournisseur": "meshy", "repli": "objet3d",
        "pour": "maillage texture a partir d'une image, rendu en .glb",
        "duree": "1 a 3 min",
    },
    "veo": {
        "titre": "Veo 3.1 (Google) — distant", "type": "video",
        "table": "VIDEO", "fournisseur": "veo", "repli": "wan5b",
        "pour": "video avec son, facturee a la seconde",
        "duree": "1 a 3 min",
    },
}


def table_distante(cle):
    return getattr(fournisseurs, MOTEURS_DISTANTS[cle]["table"])


def cle_distante(cle):
    """La cle a presenter. Les modeles Google partagent celle de Gemini."""
    nom = MOTEURS_DISTANTS[cle]["fournisseur"]
    return cle_de(nom) or (cle_de("google") if nom in _PAR_GOOGLE else "")


def moteur_distant_pret(cle):
    return cle in MOTEURS_DISTANTS and bool(cle_distante(cle))


# Ces moteurs sont servis par Gemini : inutile de resaisir la meme cle.
_PAR_GOOGLE = ("nanobanana", "lyria", "veo")


def cle_image(choix):
    return cle_de(choix) or cle_de("google")


MODELES_AUDIO = ("audio", "audioplus")

# Une demande de chanson : ce qui distingue « fais-moi un fond sonore » d'une
# piece qu'on va vraiment ecouter. Le moteur turbo, a 8 etapes, ne tient pas une
# chanson structuree — mesure sur un hommage rendu en 60 s d'instrumental plat.
_CHANSON = re.compile(r"\bchanson\b|\bparoles?\b|\bcouplets?\b|\brefrains?\b|"
                      r"\bchoeurs?\b|\bch[oœ]urs?\b|\bchante\b|\bchant[eé]e?\b|"
                      r"\bhommage\b|\bsong\b|\blyrics\b|\bchorus\b|\bverse\b", re.I)

# Une demande de texte visible dans l'image impose klein4b : c'est le seul
# modele installe qui ecrit lisiblement (mesure : les autres rendent du charabia).
# Guillemets APPARIES seulement : l'apostrophe droite servait de marque ouvrante
# et matchait toutes les elisions francaises (« bord d'un lac » -> faux positif).
_TEXTE_VISIBLE = re.compile(r"«[^»]{1,60}»|\"[^\"]{1,60}\"|“[^”]{1,60}”|"
                            r"pancarte|panneau|enseigne|affiche|[ée]criteau|"
                            r"inscription|banderole|\blogo\b|"
                            r"(mot|texte|titre|lettres?)\s+(sur|dans|[ée]crit)|"
                            r"sign\s+(reading|saying)|text\s+saying", re.I)
_TAILLE_EXPLICITE = re.compile(r"(\d{3,4})\s*[x×*]\s*(\d{3,4})")
_REPRISE = re.compile(r"\b(la|le) m[eê]me\b|\bcelle-ci\b|\bcelui-ci\b|\bcette image\b|"
                      r"\brends-?(la|le)\b|\brefais\b|\bremets\b|\bplus (sombre|clair|lumineux|"
                      r"contrast[ée]|net|flou|grand|petit|chaud|froid)\b|"
                      r"\bsans (le|la|les|l')\b|\bajoute\b|\benl[èe]ve\b|\bretire\b|"
                      r"\bchange (le|la|les|l')\b|\bremplace\b|\bmets-?y\b|\bau lieu de\b", re.I)
PIXELS_AUTO = 1216 * 832   # au-dela, le temps de rendu explose sans gain reel

# « 2/3 min », « trois minutes », « 1 min 30 », « 45 secondes ». Le petit modele
# laisse regulierement le defaut de 60 s en place malgre une duree demandee :
# on la lit nous-memes, c'est deterministe et ca ne coute rien.
_MOTS_NOMBRE = {"une": 1, "un": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5,
                "six": 6, "sept": 7, "huit": 8, "neuf": 9, "dix": 10, "quinze": 15,
                "vingt": 20, "trente": 30, "quarante": 40, "cinquante": 50}
_NOMBRE = r"(\d+|" + "|".join(_MOTS_NOMBRE) + r")"
_INTERVALLE_MIN = re.compile(_NOMBRE + r"\s*(?:a|à|/|-|ou)\s*" + _NOMBRE +
                             r"\s*min", re.I)
_MINUTES = re.compile(_NOMBRE + r"\s*min(?:ute)?s?(?:\s*(\d+))?", re.I)
_SECONDES = re.compile(_NOMBRE + r"\s*(?:s|sec|secondes?)\b", re.I)

def _nombre(m):
    m = (m or "").strip().lower()
    return float(_MOTS_NOMBRE.get(m, m)) if m else 0.0

def duree_demandee(texte):
    """Duree en secondes lue dans la demande, ou None si rien n'est demande."""
    t = texte or ""
    m = _INTERVALLE_MIN.search(t)
    if m:      # « 2 a 3 min » : on prend le milieu, pas le minimum
        return (_nombre(m.group(1)) + _nombre(m.group(2))) / 2 * 60
    m = _MINUTES.search(t)
    if m:
        return _nombre(m.group(1)) * 60 + float(m.group(2) or 0)
    m = _SECONDES.search(t)
    if m:
        return _nombre(m.group(1))
    return None

TAILLES = {"1920x1080", "1600x900", "1280x720", "1216x832", "1024x1024",
           "832x1216", "1080x1350", "768x1344"}

def caler_taille(plan, texte, taille=None):
    """Le petit modele reclame systematiquement du 1920x1080, ce qui triple le
    temps de rendu. On ne l'accorde que si l'utilisateur a demande une taille."""
    # Une taille choisie dans l'interface prime sur tout : c'est une consigne
    # explicite, elle echappe au plafond automatique comme une taille ecrite
    # dans la demande. Le decodage par tuiles se declenche seul au-dela de
    # 1216x832, donc le 1920x1080 passe sur 11 Go.
    if taille in TAILLES:
        plan["largeur"], plan["hauteur"] = (int(x) for x in taille.split("x"))
        return plan
    m = _TAILLE_EXPLICITE.search(texte or "")
    if m:
        plan["largeur"], plan["hauteur"] = int(m.group(1)), int(m.group(2))
        return plan
    w = cadrer(plan.get("largeur"), 512, 1920, 1216)
    h = cadrer(plan.get("hauteur"), 512, 1920, 832)
    if w * h > PIXELS_AUTO:
        f = (PIXELS_AUTO / (w * h)) ** 0.5
        w, h = cadrer(w * f, 512, 1920, 1216), cadrer(h * f, 512, 1920, 832)
    plan["largeur"], plan["hauteur"] = w, h
    return plan

# Bornes autorisees par intention. Le LLM propose, le code tranche : c'est ce qui
# permet de lui laisser la main sans qu'une valeur absurde casse une generation.
BORNES = {
    "image":       {"etapes": (4, 40),  "cfg": (1.0, 8.0)},
    "edition":     {"etapes": (2, 12),  "cfg": (1.0, 3.0)},
    "video":       {"images": (25, 121), "fps": (8, 30), "etapes": (8, 30), "cfg": (1.0, 8.0)},
    "video_image": {"images": (25, 81),  "fps": (8, 24), "etapes": (2, 10), "cfg": (1.0, 3.0)},
    "audio":       {"bpm": (40, 200), "duree_s": (20, 180), "etapes": (4, 60), "cfg": (1.0, 10.0)},
    "planche":     {"etapes": (15, 45), "cfg": (3.0, 10.0), "lora": (0.0, 0.5)},
    "objet3d":     {"etapes": (10, 40), "cfg": (2.0, 8.0), "finesse": (128, 512)},
}
# Defauts par modele : un modele distille ne se regle pas comme un modele complet.
REGLAGES = {
    "klein4b": {"etapes": 20, "cfg": 5.0},
    "klein9b": {"etapes": 20, "cfg": 5.0},
    "flux1":   {"etapes": 24, "cfg": 3.2},   # cfg sert ici de guidage FluxGuidance
    "klein9bhd": {"etapes": 24, "cfg": 5.0},
    "flux1hd":   {"etapes": 28, "cfg": 3.2},
    "realvis": {"etapes": 28, "cfg": 6.0},
    "pony":    {"etapes": 28, "cfg": 6.0},
    "edition": {"etapes": 4,  "cfg": 1.0},
    "wan5b":   {"etapes": 20, "cfg": 5.0, "images": 49, "fps": 24},
    "wan14b":  {"etapes": 4,  "cfg": 1.0, "images": 49, "fps": 16},
    "audio":     {"etapes": 8,  "cfg": 1.0, "bpm": 90, "duree_s": 60},
    "audioplus": {"etapes": 50, "cfg": 7.0, "bpm": 90, "duree_s": 60},
    "planche":   {"etapes": 30, "cfg": 7.0, "lora": 0.35},
    "objet3d":   {"etapes": 20, "cfg": 5.5, "finesse": 256},
}

PRIORITES = ("", "rapide", "soigne")
# Facteur applique au nombre d'etapes. Les bornes par intention gardent la main :
# « rapide » ne peut pas descendre sous le minimum qui produit encore une image.
_FACTEUR_ETAPES = {"rapide": 0.6, "soigne": 1.35}

def appliquer_parametres(plan):
    """Fusionne les reglages proposes par le LLM avec les defauts du modele,
    en bornant chaque valeur. Journalise ce qui a ete retenu.

    La priorite agit sur les etapes, la seule grandeur qui echange vraiment du
    temps contre de la qualite a modele constant. Le choix du modele, lui, reste
    a l'aiguilleur : c'est a lui qu'on dit ce que l'utilisateur privilegie.
    """
    intention, cle = plan.get("intention", "image"), plan.get("modele")
    priorite = plan.get("priorite") or ""
    bornes = BORNES.get(intention, {})
    reglages = dict(REGLAGES.get(cle, {}))
    # On memorise la proposition BRUTE du LLM : sans cela, un second appel
    # (changement de modele) relirait sa propre sortie et prendrait les valeurs
    # deja calculees pour des valeurs demandees, ecrasant les defauts du modele.
    if "parametres_bruts" not in plan:
        brut = plan.get("parametres")
        plan["parametres_bruts"] = brut if isinstance(brut, dict) else {}
    propose = plan["parametres_bruts"]
    retenu, ajustes = {}, []
    for nom, (mini, maxi) in bornes.items():
        defaut = reglages.get(nom)
        v = propose.get(nom, defaut)
        try:
            v = float(v)
        except (TypeError, ValueError):
            # « 40 s », « 62 bpm » : on recupere le nombre s'il y en a un
            trouve = re.search(r"-?\d+(?:[.,]\d+)?", str(v))
            v = float(trouve.group(0).replace(",", ".")) if trouve else defaut
        if v is None:
            continue
        borne = max(mini, min(maxi, v))
        if nom == "etapes" and priorite in _FACTEUR_ETAPES:
            borne = max(mini, min(maxi, borne * _FACTEUR_ETAPES[priorite]))
        if nom in ("etapes", "images", "bpm"):
            borne = int(round(borne))
        if nom == "images":
            # le VAE Wan exige un nombre d'images de la forme 4n+1
            borne = max(mini, ((borne - 1) // 4) * 4 + 1)
        if nom in propose:
            # le LLM renvoie parfois un mot ("low", "fast") au lieu d'un nombre :
            # la comparaison doit donc tolerer l'inconvertible.
            try:
                different = abs(borne - float(propose[nom])) > 1e-6
            except (TypeError, ValueError):
                different = True
            if different:
                ajustes.append(f"{nom} {propose[nom]!r} -> {borne}")
        retenu[nom] = borne
    plan["parametres"] = retenu
    plan["parametres_ajustes"] = ajustes
    return plan

def normaliser(plan, texte, a_une_image, conv, taille=None, priorite=""):
    plan["priorite"] = priorite
    intention = plan.get("intention")
    cle = plan.get("modele")
    if intention in MODELE_IMPOSE:
        plan["modele"] = MODELE_IMPOSE[intention]
    elif intention == "audio" and cle not in MODELES_AUDIO:
        plan["modele"] = "audio"
    elif cle in CATALOGUE and CATALOGUE[cle]["type"] != "image":
        plan["intention"] = CATALOGUE[cle]["type"]
    # "question" et "refus" doivent traverser : sans eux dans cette liste, une
    # demande ambigue repartait en "image" et le code qui pose les questions
    # n'etait jamais atteint. Les deux modeles savaient demander ; on jetait.
    elif intention in ("question", "refus"):
        pass
    elif cle not in CATALOGUE or intention not in (None, "image", "lecture"):
        s = secours(texte, a_une_image)
        plan["modele"] = s["modele"]
        plan["intention"] = s["intention"]
    plan.setdefault("intention", "image")

    # Le petit modele renvoie parfois un prompt vide, ou omet carrement la cle.
    # La demande brute de l'utilisateur est alors le meilleur repli disponible :
    # moins riche, mais fidele par construction — c'est LUI qui l'a ecrite.
    if not str(plan.get("prompt") or "").strip():
        plan["prompt"] = (texte or "").strip() or "une image"
        plan["prompt_repli"] = True

    # Une source d'image peut venir du televersement OU de la generation
    # precedente : « la meme mais en hiver » n'a pas d'image jointe et doit
    # pourtant emprunter le chemin edition.
    source = a_une_image or bool(conv.get("derniere_sortie"))
    # Une tournure de reprise devant une sortie existante veut dire « modifie »,
    # pas « refais » : le petit modele choisit souvent "image" a tort.
    if source and _REPRISE.search(texte or "") and plan["intention"] == "image":
        plan["intention"] = "edition"
        plan["modele"] = "edition"
        plan["raison"] = "reprise de l'image precedente detectee"
    if plan["intention"] in ("edition", "video_image") and not source:
        plan["intention"] = "image"
    if plan["intention"] == "lecture" and not a_une_image:
        plan["intention"] = "image"       # lire exige une image reellement jointe
    if plan["intention"] == "image" and (
            plan.get("modele") not in CATALOGUE
            or CATALOGUE[plan["modele"]]["type"] != "image"):
        plan["modele"] = secours(texte, False)["modele"]

    plan = appliquer_parametres(plan)

    if plan["intention"] == "audio":
        # Pour l'audio, « etapes » et « cfg » caracterisent le MOTEUR, pas
        # l'intention de l'utilisateur : les laisser au LLM lui faisait proposer
        # les valeurs du moteur rapide - 8 etapes - jusque sur le moteur soigne,
        # ce qui annulait tout l'interet du changement. On garde bpm et duree_s,
        # les deux seules grandeurs qui traduisent vraiment une demande.
        brut = dict(plan.get("parametres_bruts") or plan.get("parametres") or {})
        for technique in ("etapes", "cfg"):
            brut.pop(technique, None)
        plan["parametres_bruts"] = brut

        # Une chanson va sur le moteur soigne : cinquante etapes contre huit.
        if _CHANSON.search(texte or "") and plan.get("modele") != "audioplus" \
                and not manquants_partout("audioplus"):
            plan["modele"] = "audioplus"
            plan["raison"] = "chanson structuree : moteur soigne"
        voulue = duree_demandee(texte)
        if voulue:
            plan["parametres_bruts"]["duree_s"] = voulue
        plan = appliquer_parametres(plan)

    if plan["intention"] == "image":
        if _TEXTE_VISIBLE.search(texte or ""):
            plan["modele"] = "klein4b"
            plan["raison"] = "du texte doit apparaitre dans l'image : klein4b impose"
        plan = caler_taille(plan, texte, taille)
    return plan

def secours(texte, a_une_image=False):
    t = texte.lower()
    if re.search(r"musique|chanson|son |audio|melodie|instrumental", t):
        return dict(intention="audio", modele="audio", prompt=texte, tags_audio=texte,
                    paroles="", duree_s=60, negatif="", largeur=0, hauteur=0,
                    raison="musique detectee (mots-cles)")
    if re.search(r"anim(e|ation)|fais.? bouger|mets.? en mouvement", t) and a_une_image:
        return dict(intention="video_image", modele="wan14b", prompt=texte, negatif="",
                    largeur=1280, hauteur=704, raison="animation d'image (mots-cles)")
    if re.search(r"vid[ée]o|clip|anim", t):
        return dict(intention="video", modele="wan5b", prompt=texte, negatif="",
                    largeur=1280, hauteur=704, raison="video detectee (mots-cles)")
    if a_une_image:
        return dict(intention="edition", modele="edition", prompt=texte, negatif="",
                    largeur=1216, hauteur=832, raison="image fournie, mode edition")
    if re.search(r"manga|anime|illustration|dessin|fan.?art", t):
        cle, r = "pony", "style illustre (mots-cles)"
    elif re.search(r"photo|r[ée]aliste|portrait", t):
        cle, r = "realvis", "photorealisme (mots-cles)"
    else:
        cle, r = "klein4b", "modele polyvalent par defaut"
    return dict(intention="image", modele=cle, prompt=texte, negatif="",
                largeur=1216, hauteur=832, raison=r)

# ══════════════════════════════ graphes ════════════════════════════════
def cadrer(v, mini, maxi, defaut):
    try: v = int(v)
    except Exception: v = defaut
    return max(mini, min(maxi, (v // 64) * 64))

CLASSEMENT_PONY = {"safe": "rating_safe, ", "questionable": "rating_questionable, ",
                   "explicit": "rating_explicit, "}

def noms(cle, sous):
    """Fichiers du catalogue ranges dans ce dossier, dans l'ordre declare.

    Les constructeurs de graphe lisaient jusqu'ici des noms codes en dur :
    ajouter une variante d'un moteur (la meme architecture en plus haute
    precision, pour une carte plus grosse) demandait donc de toucher au code.
    En les lisant ici, une variante devient une simple entree de catalogue.
    """
    return [n for s_, n, _, _ in CATALOGUE[cle]["fichiers"] if s_ == sous]


def chargeur_diffusion(nom, cle_entree="unet_name"):
    """GGUF ou safetensors : c'est l'extension qui decide, comme chez ComfyUI."""
    if nom.lower().endswith(".gguf"):
        return {"class_type": "UnetLoaderGGUF", "inputs": {cle_entree: nom}}
    return {"class_type": "UNETLoader",
            "inputs": {cle_entree: nom, "weight_dtype": "default"}}


def g_image(cle, prompt, neg, w, h, seed, prefixe, classement="safe", par=None):
    par = par or {}
    etapes = int(par.get("etapes", REGLAGES[cle]["etapes"]))
    cfg = float(par.get("cfg", REGLAGES[cle]["cfg"]))
    tuiles = (w * h) > (1216 * 832)
    if "prefixe" in CATALOGUE[cle]:
        # Pony attend ses balises de score, puis sa balise de classement :
        # sans "rating_explicit" il edulcore de lui-meme.
        prompt = CATALOGUE[cle]["prefixe"] + CLASSEMENT_PONY.get(classement, "") + prompt
    if CATALOGUE[cle].get("famille") == "flux2":
        loader = chargeur_diffusion(noms(cle, "diffusion_models")[0])
        enc = noms(cle, "text_encoders")[0]
        g = {"1":loader,
         "2":{"class_type":"CLIPLoader","inputs":{"clip_name":enc,"type":"flux2","device":"default"}},
         "3":{"class_type":"VAELoader","inputs":{"vae_name":noms(cle, "vae")[0]}},
         "4":{"class_type":"CLIPTextEncode","inputs":{"text":prompt,"clip":["2",0]}},
         "5":{"class_type":"CLIPTextEncode","inputs":{"text":neg,"clip":["2",0]}},
         "6":{"class_type":"CFGGuider","inputs":{"model":["1",0],"positive":["4",0],"negative":["5",0],"cfg":cfg}},
         "7":{"class_type":"KSamplerSelect","inputs":{"sampler_name":"euler"}},
         "8":{"class_type":"Flux2Scheduler","inputs":{"steps":etapes,"width":w,"height":h}},
         "9":{"class_type":"EmptyFlux2LatentImage","inputs":{"width":w,"height":h,"batch_size":1}},
         "10":{"class_type":"RandomNoise","inputs":{"noise_seed":seed}},
         "11":{"class_type":"SamplerCustomAdvanced","inputs":{"noise":["10",0],"guider":["6",0],
               "sampler":["7",0],"sigmas":["8",0],"latent_image":["9",0]}}}
        lat, vae = ["11",0], ["3",0]
    elif CATALOGUE[cle].get("famille") == "flux1":
        encodeurs = noms(cle, "text_encoders")
        g = {"1":chargeur_diffusion(noms(cle, "diffusion_models")[0]),
         "2":{"class_type":"DualCLIPLoader","inputs":{"clip_name1":encodeurs[0],
              "clip_name2":encodeurs[1],"type":"flux","device":"default"}},
         "3":{"class_type":"VAELoader","inputs":{"vae_name":noms(cle, "vae")[0]}},
         "4":{"class_type":"CLIPTextEncode","inputs":{"text":prompt,"clip":["2",0]}},
         "5":{"class_type":"FluxGuidance","inputs":{"conditioning":["4",0],"guidance":cfg}},
         "6":{"class_type":"ConditioningZeroOut","inputs":{"conditioning":["4",0]}},
         "7":{"class_type":"EmptySD3LatentImage","inputs":{"width":w,"height":h,"batch_size":1}},
         "11":{"class_type":"KSampler","inputs":{"seed":seed,"steps":etapes,"cfg":1.0,"sampler_name":"euler",
               "scheduler":"simple","denoise":1.0,"model":["1",0],"positive":["5",0],
               "negative":["6",0],"latent_image":["7",0]}}}
        lat, vae = ["11",0], ["3",0]
    else:  # realvis / pony
        ckpt = "ponyDiffusionV6XL.safetensors" if cle=="pony" else "RealVisXL_V5.0.safetensors"
        g = {"1":{"class_type":"CheckpointLoaderSimple","inputs":{"ckpt_name":ckpt}},
         "2":{"class_type":"CLIPTextEncode","inputs":{"text":prompt,"clip":["1",1]}},
         "3":{"class_type":"CLIPTextEncode","inputs":{"text":neg,"clip":["1",1]}},
         "7":{"class_type":"EmptyLatentImage","inputs":{"width":w,"height":h,"batch_size":1}},
         "11":{"class_type":"KSampler","inputs":{"seed":seed,"steps":etapes,"cfg":cfg,
               "sampler_name":"dpmpp_2m","scheduler":"karras","denoise":1.0,"model":["1",0],
               "positive":["2",0],"negative":["3",0],"latent_image":["7",0]}}}
        if cle == "pony":
            g["3b"] = {"class_type":"VAELoader","inputs":{"vae_name":"sdxl_vae_fp16_fix.safetensors"}}
            vae = ["3b",0]
        else:
            vae = ["1",2]
        lat = ["11",0]
    g["12"] = ({"class_type":"VAEDecodeTiled","inputs":{"samples":lat,"vae":vae,"tile_size":512,
                "overlap":64,"temporal_size":64,"temporal_overlap":8}} if tuiles else
               {"class_type":"VAEDecode","inputs":{"samples":lat,"vae":vae}})
    g["13"] = {"class_type":"SaveImage","inputs":{"images":["12",0],"filename_prefix":prefixe}}
    return g

def g_edition(consigne, image, seed, prefixe, par=None):
    par = par or {}
    etapes = int(par.get("etapes", REGLAGES["edition"]["etapes"]))
    cfg = float(par.get("cfg", REGLAGES["edition"]["cfg"]))
    return {
     "1":{"class_type":"UNETLoader","inputs":{"unet_name":"flux-2-klein-4b.safetensors","weight_dtype":"default"}},
     "2":{"class_type":"CLIPLoader","inputs":{"clip_name":"qwen_3_4b.safetensors","type":"flux2","device":"default"}},
     "3":{"class_type":"VAELoader","inputs":{"vae_name":"flux2-vae.safetensors"}},
     "4":{"class_type":"LoadImage","inputs":{"image":image}},
     "5":{"class_type":"ImageScaleToTotalPixels","inputs":{"image":["4",0],
          "upscale_method":"nearest-exact","megapixels":1.0,"resolution_steps":1}},
     "6":{"class_type":"GetImageSize","inputs":{"image":["5",0]}},
     "7":{"class_type":"VAEEncode","inputs":{"pixels":["5",0],"vae":["3",0]}},
     "8":{"class_type":"CLIPTextEncode","inputs":{"text":consigne,"clip":["2",0]}},
     "9":{"class_type":"ReferenceLatent","inputs":{"conditioning":["8",0],"latent":["7",0]}},
     "10":{"class_type":"ConditioningZeroOut","inputs":{"conditioning":["8",0]}},
     "11":{"class_type":"CFGGuider","inputs":{"model":["1",0],"positive":["9",0],
           "negative":["10",0],"cfg":cfg}},
     "12":{"class_type":"KSamplerSelect","inputs":{"sampler_name":"euler"}},
     "13":{"class_type":"Flux2Scheduler","inputs":{"steps":etapes,"width":["6",0],"height":["6",1]}},
     "14":{"class_type":"EmptyFlux2LatentImage","inputs":{"width":["6",0],"height":["6",1],"batch_size":1}},
     "15":{"class_type":"RandomNoise","inputs":{"noise_seed":seed}},
     "16":{"class_type":"SamplerCustomAdvanced","inputs":{"noise":["15",0],"guider":["11",0],
           "sampler":["12",0],"sigmas":["13",0],"latent_image":["14",0]}},
     "17":{"class_type":"VAEDecode","inputs":{"samples":["16",0],"vae":["3",0]}},
     "18":{"class_type":"SaveImage","inputs":{"images":["17",0],"filename_prefix":prefixe}},
    }

def g_retouche_zone(description, image, seed, prefixe, sur_le_sujet=True,
                    par=None, cible="", region=False, cadre=None, reduite=False):
    """Retouche la seule zone designee, et recolle le reste a l'identique.

    « sur_le_sujet » choisit ce qu'on remplace : le sujet detoure (enlever,
    remplacer quelqu'un ou quelque chose) ou tout le reste (changer le fond).
    C'est la seule difference entre les deux usages — d'ou un seul graphe.

    « description » decrit ce qu'on veut VOIR dans la zone, pas ce qu'il faut y
    faire : sans ReferenceLatent, le moteur n'a que ce texte pour remplir le
    trou. « enleve la voiture » ne lui apprend rien ; « la route vide, asphalte
    mouille, meme lumiere » lui apprend tout.
    """
    par = par or {}
    # Une grande zone demande plus de pas : le moteur doit inventer davantage.
    # Mesure a masque et image constants : 4 pas -> texture a 0,59 du voisinage,
    # 8 -> 0,73, 16 -> 0,83. Pour une petite zone, 4 pas donnent deja 1,12,
    # c'est-a-dire mieux que le voisinage : monter serait payer pour rien.
    #
    # On ne connait pas l'aire du masque a ce stade — la calculer demanderait un
    # aller-retour de plus. Mais on sait ce qu'on VISE, et ça la predit : un fond
    # ou une etendue occupent une grande part du cadre par definition.
    grande = region or not sur_le_sujet
    etapes = int(par.get("etapes", 16 if grande else
                         REGLAGES["edition"]["etapes"]))
    # Le masque du sujet, puis son inverse quand c'est le fond qu'on change.
    masque = ["7", 0] if sur_le_sujet else ["8", 0]
    # Une cible nommee remplace BiRefNet par SAM 3.1, qui sait viser « le ciel »
    # ou « le panneau » et pas seulement « le sujet ».
    if cible:
        masque = ["32", 0]
    # Grossir le masque efface le fantome de ce qu'on RETIRE. Mais grossir mord
    # toujours sur l'autre cote : quand le masque est le FOND, les 24 pixels
    # entrent dans le sujet — celui-la meme qu'on jurait de garder. Mesure sur
    # une photo de cerf : 61,2 % du sujet detruit, un cerf sans tete ni bois.
    #
    # On ne dilate donc que lorsque le masque EST la chose a faire disparaitre :
    # un objet nomme, ou le sujet detoure. Jamais pour une etendue, jamais pour
    # un fond — la ou le masque est deja le complement de ce qu'on protege.
    objet_a_retirer = (cible and not region) or (not cible and sur_le_sujet)
    # Vingt-quatre pixels, mesures sur une image d'environ mille pixels de cote.
    # Ecrits en dur, ils ne veulent pas dire la meme chose partout : sur une
    # source de 2048 c'est un lisere qui laisse le fantome, sur une vignette de
    # 512 c'est une morsure deux fois trop large. On garde donc la PROPORTION,
    # avec un plancher — en deça de huit pixels, la dilatation ne sert plus a
    # rien.
    expand = 0
    if objet_a_retirer:
        cote = min(cadre) if cadre else 1024
        expand = max(8, round(cote * 24 / 1024))
    g = {
     "1":{"class_type":"UNETLoader","inputs":{"unet_name":"flux-2-klein-4b.safetensors","weight_dtype":"default"}},
     "2":{"class_type":"CLIPLoader","inputs":{"clip_name":"qwen_3_4b.safetensors","type":"flux2","device":"default"}},
     "3":{"class_type":"VAELoader","inputs":{"vae_name":"flux2-vae.safetensors"}},
     "4":{"class_type":"LoadImage","inputs":{"image":image}},
     # PAS de mise a l'echelle libre, contrairement a g_edition : elle rendait
     # 1238x847 pour une source de 1216x832, donc reechantillonnee PARTOUT, ce
     # qui casse en silence la promesse « le reste est identique ».
     #
     # Mais pas la source brute non plus. Deux mesures l'interdisent : une
     # entree de 4000 px a TUE ComfyUI (le VAE : 656 s a 2560 px, API bloquee),
     # et une taille non multiple de 16 decalait le recollage de quelques
     # pixels, laissant une bande sombre en bas de l'image.
     #
     # On rogne donc au multiple de 16 — au plus quinze pixels — et l'on reduit
     # seulement au-dela du plafond. Le calcul est fait en amont, sur les
     # dimensions lues dans le fichier.
     "5":({"class_type":"ImageScale",
           "inputs":{"image":["4",0],"upscale_method":"area",
                     "width":cadre[0],"height":cadre[1],"crop":"disabled"}}
          if reduite else
          {"class_type":"ImageCrop",
           "inputs":{"image":["4",0],"width":cadre[0],"height":cadre[1],
                     "x":0,"y":0}}) if cadre else
          {"class_type":"ImageScaleBy","inputs":{"image":["4",0],
           "upscale_method":"nearest-exact","scale_by":1.0}},
     "6":{"class_type":"GetImageSize","inputs":{"image":["5",0]}},
     # ── le masque ──────────────────────────────────────────────────────
     "50":{"class_type":"LoadBackgroundRemovalModel",
           "inputs":{"bg_removal_name":"birefnet.safetensors"}},
     "51":{"class_type":"RemoveBackground",
           "inputs":{"bg_removal_model":["50",0],"image":["5",0]}},
     # Seuillage indispensable : le masque n'est jamais nul loin du sujet, et
     # ces millimes suffisent a teinter toute l'image au recollage.
     "7":{"class_type":"ThresholdMask","inputs":{"mask":["51",0],"value":0.5}},
     "8":{"class_type":"InvertMask","inputs":{"mask":["7",0]}},
     # 24 mesure : a 0 il reste un fantome du sujet au bord de la zone.
     "9":{"class_type":"GrowMask","inputs":{"mask":masque,"expand":expand,
          "tapered_corners":True}},
     # ── masque DOUX, pour le recollage seulement ───────────────────────
     # FeatherMask ne convient pas : il degrade depuis les bords de l'IMAGE, pas
     # depuis le contour du masque. Le seul flou de contour passe par l'image.
     "10":{"class_type":"MaskToImage","inputs":{"mask":["9",0]}},
     "11":{"class_type":"ImageBlur","inputs":{"image":["10",0],
           "blur_radius":11,"sigma":5.5}},
     "12":{"class_type":"ImageToMask","inputs":{"image":["11",0],"channel":"red"}},
     # ── l'echantillonnage part de la source, avec le masque DUR ────────
     # Un masque doux ici ne ferait que diluer l'edition sans rien preserver de
     # plus : la preservation vient du recollage, pas du bruit.
     "13":{"class_type":"VAEEncode","inputs":{"pixels":["5",0],"vae":["3",0]}},
     "14":{"class_type":"SetLatentNoiseMask","inputs":{"samples":["13",0],
           "mask":["9",0]}},
     "15":{"class_type":"CLIPTextEncode","inputs":{"text":description,"clip":["2",0]}},
     "16":{"class_type":"ConditioningZeroOut","inputs":{"conditioning":["15",0]}},
     "17":{"class_type":"CFGGuider","inputs":{"model":["1",0],"positive":["15",0],
           "negative":["16",0],"cfg":1.0}},
     "18":{"class_type":"KSamplerSelect","inputs":{"sampler_name":"euler"}},
     "19":{"class_type":"Flux2Scheduler","inputs":{"steps":etapes,
           "width":["6",0],"height":["6",1]}},
     "20":{"class_type":"RandomNoise","inputs":{"noise_seed":seed}},
     "21":{"class_type":"SamplerCustomAdvanced","inputs":{"noise":["20",0],
           "guider":["17",0],"sampler":["18",0],"sigmas":["19",0],
           "latent_image":["14",0]}},
     "22":{"class_type":"VAEDecode","inputs":{"samples":["21",0],"vae":["3",0]}},
     # ── le recollage : c'est lui qui garantit le « seulement » ─────────
     "23":{"class_type":"ImageCompositeMasked","inputs":{"destination":["5",0],
           "source":["22",0],"x":0,"y":0,"resize_source":False,"mask":["12",0]}},
     "24":{"class_type":"SaveImage","inputs":{"images":["23",0],
           "filename_prefix":prefixe}},
    }
    if cible:
        # SAM 3.1 rend deja un masque binaire strict : pas de ThresholdMask ici,
        # contrairement a BiRefNet dont le masque vaut ~0,0015 loin du sujet.
        for mort in ("50", "51", "7", "8"):
            g.pop(mort, None)
        g["30"] = {"class_type":"CheckpointLoaderSimple",
                   "inputs":{"ckpt_name":"sam3.1_multiplex_fp16.safetensors"}}
        # Le CLIP doit venir de CE checkpoint : celui du moteur d'images leve
        # une erreur franche. La cible est en anglais, 32 jetons au plus —
        # au-dela, l'encodeur tronque sans le dire.
        g["31"] = {"class_type":"CLIPTextEncode","inputs":{"text":cible,"clip":["30",1]}}
        # 0,70 et non 0,50 : les vraies detections ne bougent pas d'un centieme
        # entre 0,30 et 0,95, et le charabia meurt a 0,70.
        g["32"] = {"class_type":"SAM3_Detect",
                   "inputs":{"model":["30",0],"image":["5",0],
                             "conditioning":["31",0],"threshold":0.70,
                             "refine_iterations":2,"individual_masks":False}}
    return g


# En dessous, il n'y a rien a retoucher : ni le modele ni l'utilisateur n'ont
# trouve ce qui etait demande. Un demi pour cent d'une image d'un megapixel fait
# encore cinq mille pixels — le seuil laisse passer une petite plaque, pas un
# masque vide.
AIRE_MINIMALE = 0.005
# Au-dela, le moteur doit inventer beaucoup : seize pas au lieu de quatre. Le
# seuil vient de la mesure de texture, pas d'une intuition.
AIRE_GRANDE = 0.15
# Au-dela, il ne reste presque rien a preserver : la promesse « le reste est
# intact » devient vraie et vide. Cinq cas mesures a 100,00 % — un ciel plein
# cadre, une image sans sujet — annonçaient une retouche locale en refaisant
# tout.
AIRE_TOTALE = 0.95


async def mesurer_puis_choisir(image, tid, cle, sur_le_sujet=True, cible="",
                               region=False, cadre=None, reduite=False):
    """Rend (aire, etapes) apres avoir mesure le masque. (None, None) si on n'a pas su.

    On choisit la machine ici pour la mesure seulement ; le rendu la choisira de
    nouveau, et rien n'oblige les deux a etre la meme — soumettre_robuste sait
    de toute facon changer de machine en route.
    """
    ou = choisir_noeud(cle)
    if ou is None:
        return None, None
    aire = await aire_du_masque(image, tid, ou["id"], cle, sur_le_sujet, cible,
                                region, cadre, reduite)
    if aire is None:
        return None, None
    return aire, (16 if aire >= AIRE_GRANDE else REGLAGES["edition"]["etapes"])


def g_masque_seul(image, prefixe, sur_le_sujet=True, cible="", region=False,
                  cadre=None, reduite=False):
    """Le meme masque que la retouche, reduit a un pixel et enregistre.

    On reprend g_retouche_zone plutot que de recopier ses noeuds : le masque
    mesure doit etre EXACTEMENT celui qui servira, dilatation comprise. Deux
    graphes ecrits separement finiraient par diverger, et l'on mesurerait alors
    un masque que personne n'utilise.
    """
    g = g_retouche_zone("", image, 0, prefixe, sur_le_sujet, None, cible, region,
                        cadre, reduite)
    # On coupe tout ce qui suit le masque : ni encodage, ni echantillonnage, ni
    # decodage. Il ne reste que ce qu'il faut pour connaitre l'aire.
    # Les chargeurs du moteur d'images partent aussi : ComfyUI n'execute que ce
    # qui alimente une sortie, mais les laisser ferait croire, a la lecture,
    # qu'on charge dix gigaoctets pour compter des pixels.
    for mort in ("1", "2", "3", "11", "12",
                 "13", "14", "15", "16", "17", "18", "19", "20", "21", "22",
                 "23", "24"):
        g.pop(mort, None)
    # Moyenne d'aire vers un seul pixel : sa valeur est la fraction couverte.
    g["40"] = {"class_type": "ImageScale",
               "inputs": {"image": ["10", 0], "upscale_method": "area",
                          "width": 1, "height": 1, "crop": "disabled"}}
    g["41"] = {"class_type": "SaveImage",
               "inputs": {"images": ["40", 0], "filename_prefix": prefixe}}
    return g


# Au-dela, le VAE devient le probleme : 3,5 s a 1216 px, 10,2 s a 1920, et
# 656 s a 2560 — pendant lesquelles ComfyUI entier cesse de repondre. Une entree
# de 4000 px l'a tue une fois. Deux megapixels laissent passer tout ce qu'un
# telephone produit en 16:9 ou en 4:3.
PIXELS_MAX = 2_100_000


def dimensions_image(chemin):
    """(largeur, hauteur) d'un fichier image, ou None si on ne sait pas lire.

    Les en-tetes suffisent : on ne decode rien. PNG, JPEG, BMP et WebP couvrent
    tout ce que le studio accepte en piece jointe. En bibliotheque standard,
    parce que l'image du studio ne contient ni PIL ni numpy et qu'on n'ajoute
    pas quarante megaoctets de dependance pour lire deux entiers.
    """
    import struct

    try:
        with open(chemin, "rb") as f:
            tete = f.read(32)
            if tete[:8] == b"\x89PNG\r\n\x1a\n":
                return struct.unpack(">II", tete[16:24])
            if tete[:2] == b"BM":
                return struct.unpack("<ii", tete[18:26])
            if tete[:4] == b"RIFF" and tete[8:12] == b"WEBP":
                if tete[12:16] == b"VP8X":
                    l = int.from_bytes(tete[24:27], "little") + 1
                    h = int.from_bytes(tete[27:30], "little") + 1
                    return l, h
                if tete[12:16] == b"VP8 ":
                    return struct.unpack("<HH", tete[26:30])
                if tete[12:16] == b"VP8L":
                    b = int.from_bytes(tete[21:25], "little")
                    return (b & 0x3FFF) + 1, ((b >> 14) & 0x3FFF) + 1
                return None
            if tete[:2] != b"\xff\xd8":
                return None
            # JPEG : on saute de marqueur en marqueur jusqu'au cadre, seul
            # endroit ou les dimensions sont ecrites.
            f.seek(2)
            while True:
                bloc = f.read(2)
                if len(bloc) < 2 or bloc[0] != 0xFF:
                    return None
                marque = bloc[1]
                if 0xC0 <= marque <= 0xCF and marque not in (0xC4, 0xC8, 0xCC):
                    f.read(3)
                    h, l = struct.unpack(">HH", f.read(4))
                    return l, h
                taille = struct.unpack(">H", f.read(2))[0]
                f.seek(taille - 2, 1)
    except (OSError, struct.error, IndexError):
        return None


def cadrage_source(chemin):
    """Ce qu'il faut faire de la source avant de la retoucher.

    Rend (largeur, hauteur, reduite) : la taille a laquelle travailler, et si
    l'on a du reduire. (None, None, False) quand on n'a pas su lire le fichier —
    on laisse alors passer, comme partout ailleurs : refuser a tort coute plus
    cher qu'un doute.
    """
    d = dimensions_image(chemin)
    if not d or min(d) < 32:
        return None, None, False
    l, h = d
    reduite = l * h > PIXELS_MAX
    if reduite:
        f = (PIXELS_MAX / (l * h)) ** 0.5
        l, h = int(l * f), int(h * f)
    # Multiple de 16 par le BAS : le VAE recadre au multiple de 16 centre, et
    # ce recadrage decalait le recollage. En rognant nous-memes, il n'a plus
    # rien a faire et le collage retombe en place. Au plus quinze pixels a
    # droite et en bas.
    return max(l - l % 16, 16), max(h - h % 16, 16), reduite


def _fraction_png_1x1(octets):
    """La valeur du pixel d'un PNG 1x1, entre 0 et 1. None si illisible.

    Ecrit a la main parce que le studio n'a ni PIL ni numpy : son image ne
    contient qu'aiohttp. Trente lignes valent mieux qu'une dependance de
    quarante megaoctets posee sur chaque installation pour lire un pixel.
    """
    import struct
    import zlib

    if not octets or octets[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    i, largeur, canaux, morceaux = 8, 0, 3, []
    while i + 8 <= len(octets):
        taille, genre = struct.unpack(">I4s", octets[i:i + 8])
        corps = octets[i + 8:i + 8 + taille]
        if genre == b"IHDR":
            largeur = struct.unpack(">I", corps[:4])[0]
            profondeur, couleur = corps[8], corps[9]
            if profondeur != 8:
                return None
            canaux = {0: 1, 2: 3, 4: 2, 6: 4}.get(couleur, 0)
            if not canaux:
                return None
        elif genre == b"IDAT":
            morceaux.append(corps)
        elif genre == b"IEND":
            break
        i += 12 + taille
    if largeur != 1 or not morceaux:
        return None
    try:
        brut = zlib.decompress(b"".join(morceaux))
    except zlib.error:
        return None
    # Une ligne d'un pixel : un octet de filtre, puis les canaux. Les filtres
    # PNG sont neutres sur le premier pixel d'une ligne, quel que soit leur type.
    if len(brut) < 1 + canaux:
        return None
    return brut[1] / 255.0


async def aire_du_masque(image, tid, ident, cle, sur_le_sujet=True, cible="",
                         region=False, cadre=None, reduite=False):
    """La fraction de l'image que le masque couvre, ou None si on n'a pas su.

    None et non zero : « je ne sais pas » et « il n'y a rien » n'appellent pas
    la meme suite. Sur un doute, on laisse passer le rendu — refuser a tort
    couterait plus cher que la seconde qu'on vient de perdre.
    """
    prefixe = f"masque/{tid[:8]}"
    # Le meme cadrage que le rendu : mesurer un masque calcule sur une autre
    # taille reviendrait a mesurer autre chose.
    g = g_masque_seul(image, prefixe, sur_le_sujet, cible, region, cadre, reduite)
    try:
        fichiers, _ = await soumettre_robuste(g, tid, ident, cle)
    except Exception as e:
        journal(tid, f"aire du masque inconnue ({type(e).__name__})")
        return None
    if not fichiers:
        return None
    try:
        octets = await lire_sortie(fichiers[0])
    except Exception:
        return None
    return _fraction_png_1x1(octets)


def g_personnage(prompt, reference, w, h, seed, prefixe, par=None):
    """Une image NEUVE, en gardant le personnage d'une image de reference.

    Meme squelette que l'edition, a une difference qui fait tout : la latente
    de depart et le programmeur de pas sont cales sur la taille DEMANDEE, pas
    sur celle de la reference. Sans cela on ne peut que retoucher l'image
    d'origine ; avec, on peut le montrer ailleurs, autrement cadre.

    La reference passe par ReferenceLatent, le noeud que le workflow officiel
    de Flux.2 Klein emploie pour cela.
    """
    par = par or {}
    # Reglages d'IMAGE et non d'edition : le moteur d'edition est distille a
    # quatre etapes, ce qui suffit a corriger un detail mais pas a dessiner une
    # scene entiere.
    etapes = int(par.get("etapes", REGLAGES["klein4b"]["etapes"]))
    cfg = float(par.get("cfg", REGLAGES["klein4b"]["cfg"]))
    return {
     "1":{"class_type":"UNETLoader","inputs":{"unet_name":"flux-2-klein-4b.safetensors","weight_dtype":"default"}},
     "2":{"class_type":"CLIPLoader","inputs":{"clip_name":"qwen_3_4b.safetensors","type":"flux2","device":"default"}},
     "3":{"class_type":"VAELoader","inputs":{"vae_name":"flux2-vae.safetensors"}},
     "4":{"class_type":"LoadImage","inputs":{"image":reference}},
     "5":{"class_type":"ImageScaleToTotalPixels","inputs":{"image":["4",0],
          "upscale_method":"nearest-exact","megapixels":1.0,"resolution_steps":1}},
     "7":{"class_type":"VAEEncode","inputs":{"pixels":["5",0],"vae":["3",0]}},
     "8":{"class_type":"CLIPTextEncode","inputs":{"text":prompt,"clip":["2",0]}},
     "9":{"class_type":"ReferenceLatent","inputs":{"conditioning":["8",0],"latent":["7",0]}},
     "10":{"class_type":"ConditioningZeroOut","inputs":{"conditioning":["8",0]}},
     "11":{"class_type":"CFGGuider","inputs":{"model":["1",0],"positive":["9",0],
           "negative":["10",0],"cfg":cfg}},
     "12":{"class_type":"KSamplerSelect","inputs":{"sampler_name":"euler"}},
     "13":{"class_type":"Flux2Scheduler","inputs":{"steps":etapes,"width":w,"height":h}},
     "14":{"class_type":"EmptyFlux2LatentImage","inputs":{"width":w,"height":h,"batch_size":1}},
     "15":{"class_type":"RandomNoise","inputs":{"noise_seed":seed}},
     "16":{"class_type":"SamplerCustomAdvanced","inputs":{"noise":["15",0],"guider":["11",0],
           "sampler":["12",0],"sigmas":["13",0],"latent_image":["14",0]}},
     "17":{"class_type":"VAEDecode","inputs":{"samples":["16",0],"vae":["3",0]}},
     "18":{"class_type":"SaveImage","inputs":{"images":["17",0],"filename_prefix":prefixe}},
    }


# « le meme », « garde ce personnage » : la demande porte sur QUI, pas sur quoi.
# Volontairement etroit — un « meme » de trop enverrait une image sans rapport
# sur la voie de la reference, et le resultat serait pire que sans elle.
# « le meme », « garde ce personnage » : la demande porte sur QUI, pas sur quoi.
# Volontairement etroit — un « meme » de trop enverrait une image sans rapport
# sur la voie de la reference, et le resultat serait pire que sans elle.
_MEME_SUR = re.compile(
    r"(meme (?:personnage|personne|heros|heroine|visage|tete|modele|tenue|"
    r"costume|allure)|"
    r"garde (?:ce|le|la|cette) (?:personnage|personne|visage|tete)|"
    r"conserve (?:son|le) (?:visage|apparence|allure))", re.I)

# « la meme, de profil » parle du personnage ; « la meme couleur de ciel que
# sur une photo de vacances » n'en parle pas. Seule la longueur les separe de
# facon fiable : une demande de continuite tient en quelques mots.
_MEME_FAIBLE = re.compile(r"((?:le|la) meme\b|avec (?:lui|elle)\b)", re.I)


def veut_meme_personnage(texte):
    """Vrai si la demande porte sur la continuite d'un personnage."""
    nu = sans_accents(texte or "")
    if _MEME_SUR.search(nu):
        return True
    return bool(_MEME_FAIBLE.search(nu)) and len(nu) <= 50


def g_planche(prompt, neg, w, h, seed, prefixe, par=None):
    """Planche complete en une passe : Pony + le LoRA m4ng4, entraine sur ce
    checkpoint. Les bulles sont volontairement VIDES — du texte cuit dans les
    pixels ne serait ni corrigeable ni traduisible."""
    par = par or {}
    etapes = int(par.get("etapes", 30))
    cfg = float(par.get("cfg", 7.0))
    force = float(par.get("lora", 0.35))
    return {
     "1":{"class_type":"CheckpointLoaderSimple","inputs":{"ckpt_name":"ponyDiffusionV6XL.safetensors"}},
     "2":{"class_type":"LoraLoader","inputs":{"model":["1",0],"clip":["1",1],
          "lora_name":"manga-panels-m4ng4.safetensors",
          "strength_model":force,"strength_clip":force}},
     "3":{"class_type":"VAELoader","inputs":{"vae_name":"sdxl_vae_fp16_fix.safetensors"}},
     "4":{"class_type":"CLIPTextEncode","inputs":{"text":prompt,"clip":["2",1]}},
     "5":{"class_type":"CLIPTextEncode","inputs":{"text":neg,"clip":["2",1]}},
     "6":{"class_type":"EmptyLatentImage","inputs":{"width":w,"height":h,"batch_size":1}},
     "11":{"class_type":"KSampler","inputs":{"seed":seed,"steps":etapes,"cfg":cfg,
           "sampler_name":"dpmpp_2m","scheduler":"karras","denoise":1.0,"model":["2",0],
           "positive":["4",0],"negative":["5",0],"latent_image":["6",0]}},
     "12":{"class_type":"VAEDecode","inputs":{"samples":["11",0],"vae":["3",0]}},
     "13":{"class_type":"SaveImage","inputs":{"images":["12",0],"filename_prefix":prefixe}},
    }

def g_case(prompt, neg, w, h, seed, prefixe, force=0.35):
    """Une case seule, plein cadre, sans bordure : elle recevra son cadre a la
    composition. Un megapixel entier par case, la ou une planche entiere n'en
    accorde que 0,16 — c'est toute la difference de lisibilite."""
    return {
     "1":{"class_type":"CheckpointLoaderSimple","inputs":{"ckpt_name":"ponyDiffusionV6XL.safetensors"}},
     "2":{"class_type":"LoraLoader","inputs":{"model":["1",0],"clip":["1",1],
          "lora_name":"manga-panels-m4ng4.safetensors",
          "strength_model":force,"strength_clip":force}},
     "3":{"class_type":"VAELoader","inputs":{"vae_name":"sdxl_vae_fp16_fix.safetensors"}},
     "4":{"class_type":"CLIPTextEncode","inputs":{"text":prompt,"clip":["2",1]}},
     "5":{"class_type":"CLIPTextEncode","inputs":{"text":neg,"clip":["2",1]}},
     "6":{"class_type":"EmptyLatentImage","inputs":{"width":w,"height":h,"batch_size":1}},
     "7":{"class_type":"KSampler","inputs":{"seed":seed,"steps":28,"cfg":7.0,
          "sampler_name":"dpmpp_2m","scheduler":"karras","denoise":1.0,"model":["2",0],
          "positive":["4",0],"negative":["5",0],"latent_image":["6",0]}},
     "8":{"class_type":"VAEDecode","inputs":{"samples":["7",0],"vae":["3",0]}},
     "9":{"class_type":"SaveImage","inputs":{"images":["8",0],"filename_prefix":prefixe}},
    }

def g_planche_composee(cases, neg, seed, prefixe, force=0.35, etapes=28, cfg=7.0,
                       cote=1024, gouttiere=16):
    """Toute la planche en UN seul graphe : le modele est charge une fois, les
    cases sont echantillonnees a la suite puis assemblees sans repasser par le
    disque.

    Ce n'est pas qu'une optimisation. Quatre soumissions separees rapprochees
    produisaient du bruit colore a partir de la deuxieme (mesure : la meme case
    lancee seule sort propre). Un graphe unique supprime le rechargement repete
    qui declenchait le probleme."""
    prefixe_tags = CATALOGUE["planche"]["prefixe"]
    g = {
     "L1":{"class_type":"CheckpointLoaderSimple","inputs":{"ckpt_name":"ponyDiffusionV6XL.safetensors"}},
     "L2":{"class_type":"LoraLoader","inputs":{"model":["L1",0],"clip":["L1",1],
           "lora_name":"manga-panels-m4ng4.safetensors",
           "strength_model":force,"strength_clip":force}},
     "L3":{"class_type":"VAELoader","inputs":{"vae_name":"sdxl_vae_fp16_fix.safetensors"}},
     "NEG":{"class_type":"CLIPTextEncode","inputs":{"text":neg,"clip":["L2",1]}},
    }
    images = []
    for i, desc in enumerate(cases):
        p, k, d = f"P{i}", f"K{i}", f"D{i}"
        g[p] = {"class_type":"CLIPTextEncode","inputs":{
                "text": prefixe_tags + desc + ", single panel, no panel borders, "
                        "full bleed, blank speech bubble", "clip":["L2",1]}}
        g[f"E{i}"] = {"class_type":"EmptyLatentImage","inputs":{
                      "width":cote,"height":cote,"batch_size":1}}
        g[k] = {"class_type":"KSampler","inputs":{
                "seed":seed + i * 1000, "steps":etapes, "cfg":cfg,
                "sampler_name":"dpmpp_2m","scheduler":"karras","denoise":1.0,
                "model":["L2",0],"positive":[p,0],"negative":["NEG",0],
                "latent_image":[f"E{i}",0]}}
        g[d] = {"class_type":"VAEDecode","inputs":{"samples":[k,0],"vae":["L3",0]}}
        images.append([d, 0])

    par_rangee = 2 if len(images) > 2 else len(images)
    rangees, n = [], 0
    for i in range(0, len(images), par_rangee):
        lot = images[i:i + par_rangee]
        courant = lot[0]
        for suivant in lot[1:]:
            n += 1
            g[f"S{n}"] = {"class_type":"ImageStitch","inputs":{
                          "image1":courant,"image2":suivant,"direction":"right",
                          "match_image_size":True,"spacing_width":gouttiere,
                          "spacing_color":"black"}}
            courant = [f"S{n}", 0]
        rangees.append(courant)
    page = rangees[0]
    for r in rangees[1:]:
        n += 1
        g[f"S{n}"] = {"class_type":"ImageStitch","inputs":{
                      "image1":page,"image2":r,"direction":"down",
                      "match_image_size":True,"spacing_width":gouttiere,
                      "spacing_color":"black"}}
        page = [f"S{n}", 0]
    g["OUT"] = {"class_type":"SaveImage","inputs":{"images":page,"filename_prefix":prefixe}}
    return g

def cadence_de(nom):
    """Cadence et nombre d'images d'une video du cache local.

    PyAV est livre avec ComfyUI : pas de dependance de plus. En cas de doute on
    rend 24 im/s, la cadence des videos du studio.
    """
    try:
        import av

        with av.open(os.path.join(DOSSIER_ENTREE, nom)) as c:
            v = c.streams.video[0]
            return float(v.average_rate or 24.0), int(v.frames or 0)
    except Exception:
        return 24.0, 0


def g_fluidite(video, prefixe, multiplicateur=2, fps_sortie=48.0):
    """Intercale des images. La cadence de sortie decide du resultat.

    Doublee, la video garde sa duree et gagne en fluidite. Conservee, elle
    dure deux fois plus longtemps : c'est un ralenti, et c'est le meme calcul.
    """
    return {
     "1": {"class_type": "LoadVideo", "inputs": {"file": video}},
     "2": {"class_type": "GetVideoComponents", "inputs": {"video": ["1", 0]}},
     "3": {"class_type": "FrameInterpolationModelLoader",
           "inputs": {"model_name": "film_net_fp16.safetensors"}},
     "4": {"class_type": "FrameInterpolate",
           "inputs": {"interp_model": ["3", 0], "images": ["2", 0],
                      "multiplier": int(multiplicateur)}},
     "5": {"class_type": "CreateVideo",
           "inputs": {"images": ["4", 0], "fps": float(fps_sortie)}},
     "6": {"class_type": "SaveVideo",
           "inputs": {"video": ["5", 0], "filename_prefix": prefixe,
                      "format": "auto", "codec": "auto"}},
    }


_FLUIDE = re.compile(
    r"(plus fluide|fluidifi|interpol|moins saccad|"
    r"(?:passe|mets|met).{0,12}(?:en )?(?:48|60|120) ?(?:fps|images)|"
    r"au ralenti|en ralenti|slow ?motion|ralentis)", re.I)
_RALENTI = re.compile(r"(ralenti|slow ?motion)", re.I)


def veut_fluidifier(texte):
    return bool(_FLUIDE.search(sans_accents(texte or "")))


def veut_ralenti(texte):
    """Le ralenti et la fluidite sont le meme calcul : seule la cadence de
    sortie les separe."""
    return bool(_RALENTI.search(sans_accents(texte or "")))


def g_detourage(image, prefixe):
    """Isole le sujet et rend le fond transparent.

    InvertMask n'est pas un ornement : le masque rendu designe le sujet, et
    l'omettre efface le personnage en gardant le decor. Mesure : 11 % de
    transparence sans, 87 % avec.
    """
    return {
     "1": {"class_type": "LoadImage", "inputs": {"image": image}},
     "2": {"class_type": "LoadBackgroundRemovalModel",
           "inputs": {"bg_removal_name": "birefnet.safetensors"}},
     "3": {"class_type": "RemoveBackground",
           "inputs": {"bg_removal_model": ["2", 0], "image": ["1", 0]}},
     "4": {"class_type": "InvertMask", "inputs": {"mask": ["3", 0]}},
     "5": {"class_type": "JoinImageWithAlpha",
           "inputs": {"image": ["1", 0], "alpha": ["4", 0]}},
     "6": {"class_type": "SaveImage",
           "inputs": {"images": ["5", 0], "filename_prefix": prefixe}},
    }


# « detoure », « enleve le fond » : comme l'agrandissement, il n'y a rien a
# interpreter. On tranche a l'ecrit plutot que d'envoyer la demande a un modele
# qui pourrait decider de redessiner l'image.
# « l.?arriere » et non « l arriere » : sans_accents() enleve les accents, pas
# les apostrophes. « retire l'arriere-plan » — la forme que tout le monde ecrit,
# et celle du corpus — ne correspondait a rien, et tombait depuis peu sur la
# retouche du SUJET : fond transparent demande, sujet efface obtenu.
_DETOURER = re.compile(
    r"(detour|"
    r"(?:enleve|enlever|retire|retirer|supprime|supprimer|vire|virer)"
    r".{0,12}(?:le fond|l.?arriere.?plan|le decor)|"
    r"sans (?:le )?fond\b|fond transparent|sur fond transparent|"
    r"isole (?:le|la) (?:sujet|personnage|personne))", re.I)


def veut_detourer(texte):
    return bool(_DETOURER.search(sans_accents(texte or "")))


# « le fond », « l'arriere-plan », « le decor » — et un verbe qui remplace.
# Le nom est pris nu — « un autre arriere-plan » n'a pas d'article devant — mais
# il faut un VERBE de remplacement a moins de quarante caracteres, sinon « une
# cabane au fond de la vallee » suffirait a declencher une retouche.
_FOND = re.compile(
    r"\b(chang|remplac|met[st]?|mettre|nouveau|nouvelle|autre)\w*\b[^.!?]{0,40}"
    r"\b(fond|arriere.plan|decor)\b"
    r"|\b(fond|arriere.plan|decor)\b[^.!?]{0,30}"
    r"\b(chang|remplac|devien|autre|nouveau|nouvelle)\w*", re.I)
# Effacer ou remplacer ce qui est AU PREMIER PLAN.
_SUJET = re.compile(
    r"\b(enleve|enlever|efface|effacer|supprime|supprimer|retire|retirer|"
    r"remplace|remplacer|vire|virer)\b", re.I)


def _deja_demande(conv):
    """Vrai si l'on a deja demande l'accord dans cette conversation, sans reponse.

    La reponse de l'utilisateur repasse par l'aiguillage, et l'enrichissement
    peut echouer de nouveau : sans cette garde, on redemanderait sans fin. On
    regarde le dernier tour, celui qui porte la question.
    """
    tours = (conv or {}).get("tours") or []
    for t in reversed(tours):
        if t.get("etat") == "question":
            return (t.get("parametres") or {}).get("attente") == "tel_quel" \
                or (t.get("raison") or "") == "tel_quel" \
                or t.get("type") == "question"
        if t.get("etat") in ("fini", "erreur"):
            return False
    return False


def veut_retoucher_fond(texte):
    return bool(_FOND.search(sans_accents(texte or "")))


def veut_retoucher_sujet(texte):
    t = sans_accents(texte or "")
    # Le fond passe avant : « remplace le fond » contient un verbe de
    # suppression, et les deux motifs y repondraient.
    return bool(_SUJET.search(t)) and not _FOND.search(t)


# « seulement », « juste », « uniquement » : le mot qui dit qu'on vise une zone
# et pas l'image entiere. C'est le signal le plus sur qu'on ait.
# « que » a ete retire : il attrapait « je voudrais QUE tu changes le style » et
# « est-ce QUE tu peux refaire cette image », deux editions globales envoyees en
# retouche localisee. Les trois autres ne se disent pas par hasard.
_SEULEMENT = re.compile(r"\b(seulement|uniquement|juste)\b", re.I)


def veut_zone_nommee(texte):
    """Vrai si la demande vise une zone DESIGNEE, et non « le sujet » ou « le fond ».

    Deux chemins : le mot « seulement » associe a un verbe de remplacement, ou
    un ordre de suppression qui NOMME sa cible. « enleve le chien » nomme sa
    cible ; « enleve le sujet » ne nomme rien de plus que ce que BiRefNet sait
    deja trouver.
    """
    t = sans_accents(texte or "")
    if _FOND.search(t):
        return False        # le fond a son propre chemin, sans modele en plus
    if _SEULEMENT.search(t) and re.search(r"\b(chang|remplac|refai|met[st]?)\w*", t, re.I):
        return True
    m = _SUJET.search(t)
    if not m:
        return False
    apres = t[m.end():].strip()
    # « enleve le sujet » ou « efface la personne » : rien de plus precis que ce
    # que le detourage sait faire, et il ne coute aucun modele supplementaire.
    return bool(apres) and not re.match(
        r"^(le|la|l.|les)?\s*(sujet|personnage|personne|fond|arriere)", apres, re.I)


SYS_ZONE = """Tu decris ce qu'il faut VOIR dans une zone d'image, et rien d'autre.

On va effacer une zone d'une photo et la redessiner. Le modele qui la redessine
ne recoit que ta phrase : il ne voit pas l'ordre donne par l'utilisateur, et il
ne sait pas ce qu'il y avait avant.

Rends UNE phrase courte, en francais, qui decrit la zone TELLE QU'ELLE DOIT
ETRE une fois refaite. Pas de verbe d'action, pas de commentaire, pas de
guillemets.

  « enleve la voiture »        -> « la route vide, asphalte mouille, meme lumiere »
  « change le fond »           -> attends la precision de l'utilisateur et
                                  decris-la : « une plage de sable au crepuscule,
                                  mer calme »
  « remplace le chien par un chat » -> « un chat assis au meme endroit, meme
                                  lumiere, meme perspective »

Deux interdits : ne dis jamais ce qu'il faut ENLEVER — la zone sera vide, il n'y
a plus rien a enlever — et ne decris pas le reste de l'image, seulement la zone."""


SYS_CIBLE = """Tu prepares une retouche d'image. Tu rends TROIS lignes, rien d'autre.

Ligne 1 — CIBLE : ce qu'il faut selectionner dans l'image, EN ANGLAIS, en trois
mots au plus, avec l'article. « the sky », « the car », « the road sign ».
L'anglais n'est pas negociable : l'outil de selection ne comprend que lui, et se
trompe en silence sinon.

Ligne 2 — un seul mot : OBJET si la cible est une chose delimitee (une voiture,
un panneau, un chien), REGION si c'est une etendue (le ciel, le sol, la mer, un
mur).

Ligne 3 — DESCRIPTION, en francais, de ce qu'il faut VOIR a la place une fois la
zone refaite. Pas de verbe d'action : la zone sera vide, il n'y a plus rien a
enlever. « un ciel d'orage, nuages sombres, lumiere basse ».

Exemple, pour « remplace le ciel par un ciel d'orage » :
the sky
REGION
un ciel d'orage, nuages sombres et lourds, lumiere basse"""


async def preparer_cible(texte, tid):
    """Rend (cible anglaise, region ?, description) ou ("", False, "").

    Les trois se decident ensemble : la categorie depend de la cible, et la
    description doit parler de la meme zone. Les separer en trois appels
    multiplierait les occasions de les voir diverger.
    """
    try:
        brut = await appeler_ollama(texte, None, SYS_CIBLE, json_mode=False,
                                    temperature=0.2, tid=tid,
                                    modele=choisir_modele_ecriture())
    except Exception as e:
        journal(tid, f"preparation de la cible indisponible ({type(e).__name__})")
        return "", False, ""
    lignes = [l.strip() for l in (brut or "").splitlines() if l.strip()]
    if len(lignes) < 3:
        journal(tid, f"cible mal formee ({len(lignes)} ligne(s) rendues sur 3)")
        return "", False, ""
    cible, genre, desc = lignes[0], lignes[1].upper(), " ".join(lignes[2:])
    # Trois controles, un par ligne. Une cible hors alphabet latin, une
    # categorie inventee ou une description qui donne un ordre valent mieux
    # d'etre refusees que payees quinze secondes de carte.
    if not cible or not latin(cible) or len(cible.split()) > 6:
        journal(tid, "cible inutilisable — la selection viserait n'importe quoi")
        return "", False, ""
    if "REGION" not in genre and "OBJET" not in genre:
        journal(tid, f"categorie inattendue : {genre[:20]}")
        return "", False, ""
    if not desc or not latin(desc) or _SUJET.search(sans_accents(desc)):
        journal(tid, "description rejetee : elle donne encore un ordre")
        return "", False, ""
    return cible, "REGION" in genre, desc


async def decrire_zone(texte, tid):
    """Traduit un ordre en description de ce qu'on veut voir. "" si ça echoue.

    Un appel a lui seul : c'est la piece qui manque au graphe, et la melanger a
    l'aiguillage revenait a ne l'obtenir jamais — on l'a mesure sur
    l'enrichissement du prompt.

    Le controle est en code : une description qui recopie l'ordre, ou qui garde
    un verbe de suppression, ne sert a rien. Mieux vaut le dire et rendre la
    main que remplir le trou avec un ordre que le moteur ne comprendra pas.
    """
    try:
        brut = await appeler_ollama(texte, None, SYS_ZONE, json_mode=False,
                                    temperature=0.3, tid=tid,
                                    modele=choisir_modele_ecriture())
    except Exception as e:
        journal(tid, f"description de la zone indisponible ({type(e).__name__})")
        return ""
    propose = " ".join((brut or "").split())
    if not latin(propose) or len(propose.split()) < 3:
        return ""
    if _SUJET.search(sans_accents(propose)):
        # « enleve la voiture » rendu tel quel : le moteur dessinerait une
        # voiture, puisque c'est le seul objet nomme.
        journal(tid, "description rejetee : elle donne encore un ordre")
        return ""
    return propose


def g_agrandir(image, prefixe, facteur=4.0):
    """Agrandit une image sans rien y ajouter.

    Le modele travaille toujours en 4x ; un facteur plus petit s'obtient en
    reduisant apres coup, ce qui rend mieux qu'un agrandissement direct — c'est
    ainsi que procedent les workflows publics.
    """
    g = {
        "1": {"class_type": "LoadImage", "inputs": {"image": image}},
        "2": {"class_type": "UpscaleModelLoader",
              "inputs": {"model_name": "4x-UltraSharp.pth"}},
        "3": {"class_type": "ImageUpscaleWithModel",
              "inputs": {"upscale_model": ["2", 0], "image": ["1", 0]}},
    }
    dernier = "3"
    if facteur < 4.0:
        g["4"] = {"class_type": "ImageScaleBy",
                  "inputs": {"image": ["3", 0], "upscale_method": "lanczos",
                             "scale_by": round(facteur / 4.0, 4)}}
        dernier = "4"
    g["5"] = {"class_type": "SaveImage",
              "inputs": {"images": [dernier, 0], "filename_prefix": prefixe}}
    return g


# « agrandis cette image » ne demande aucune interpretation : le reconnaitre
# ici evite un appel au modele, dix secondes d'attente, et surtout le risque
# qu'il decide de REGENERER l'image au lieu de l'agrandir.
# Deux niveaux de certitude. « agrandis », « upscale » ne veulent rien dire
# d'autre. « plus grande », « meilleure qualite » peuvent tres bien decrire le
# SUJET d'une image a creer — « un chat devant une plus grande maison » — et ne
# comptent donc que sur une phrase courte, ou il n'y a rien d'autre a decrire.
_AGRANDIR_SUR = re.compile(
    r"(agrandi|agrandis|agrandir|agrandissement|upscale|"
    r"haute definition|haute resolution|plus haute definition)", re.I)
_AGRANDIR_FAIBLE = re.compile(
    r"(plus grande?\b|plus gros\b|elargi|"
    r"meilleure? (?:qualite|definition|resolution)|"
    r"ameliore.{0,14}(?:qualite|definition|resolution)|"
    r"en (?:4k|8k)\b)", re.I)

_FACTEUR = re.compile(r"([234])\s*(?:x\b|fois\b)|\bx\s*([234])\b", re.I)


def veut_agrandir(texte):
    """Vrai si la demande porte sur la DEFINITION d'une image, pas son contenu."""
    nu = sans_accents(texte or "")
    if _AGRANDIR_SUR.search(nu):
        return True
    # Une demande de creation decrit un sujet, et c'est long. Une demande
    # d'agrandissement tient en quelques mots.
    return bool(_AGRANDIR_FAIBLE.search(nu)) and len(nu) <= 60


def facteur_demande(texte):
    """Le facteur reclame, borne a ce que le modele sait rendre."""
    m = _FACTEUR.search(sans_accents(texte or ""))
    if not m:
        return 4.0
    return float(m.group(1) or m.group(2))


def g_3d(image, seed, prefixe, par=None):
    """Image -> maillage .glb. Le maillage sort NU : ComfyUI n'embarque aucun
    noeud de texturage Hunyuan."""
    par = par or {}
    etapes = int(par.get("etapes", 20))
    cfg = float(par.get("cfg", 5.5))
    octree = int(par.get("finesse", 256))
    return {
     "1":{"class_type":"ImageOnlyCheckpointLoader","inputs":{"ckpt_name":"hunyuan3d-dit-v2_fp16.safetensors"}},
     "2":{"class_type":"LoadImage","inputs":{"image":image}},
     "3":{"class_type":"ModelSamplingAuraFlow","inputs":{"model":["1",0],"shift":1.0}},
     "4":{"class_type":"CLIPVisionEncode","inputs":{"clip_vision":["1",1],"image":["2",0],"crop":"none"}},
     "5":{"class_type":"Hunyuan3Dv2Conditioning","inputs":{"clip_vision_output":["4",0]}},
     "6":{"class_type":"EmptyLatentHunyuan3Dv2","inputs":{"resolution":3072,"batch_size":1}},
     "7":{"class_type":"KSampler","inputs":{"model":["3",0],"positive":["5",0],"negative":["5",1],
          "latent_image":["6",0],"seed":seed,"steps":etapes,"cfg":cfg,
          "sampler_name":"euler","scheduler":"normal","denoise":1.0}},
     "8":{"class_type":"VAEDecodeHunyuan3D","inputs":{"samples":["7",0],"vae":["1",2],
          "num_chunks":8000,"octree_resolution":octree}},
     "9":{"class_type":"VoxelToMesh","inputs":{"voxel":["8",0],"algorithm":"surface net","threshold":0.6}},
     "10":{"class_type":"SaveGLB","inputs":{"mesh":["9",0],"filename_prefix":prefixe}},
    }

def g_video(prompt, neg, seed, prefixe, par=None):
    par = par or {}
    r = REGLAGES["wan5b"]
    etapes, cfg = int(par.get("etapes", r["etapes"])), float(par.get("cfg", r["cfg"]))
    images, fps = int(par.get("images", r["images"])), float(par.get("fps", r["fps"]))
    return {
     "1":{"class_type":"UnetLoaderGGUF","inputs":{"unet_name":"Wan2.2-TI2V-5B-Q5_K_M.gguf"}},
     "2":{"class_type":"CLIPLoader","inputs":{"clip_name":"umt5_xxl_fp8_e4m3fn_scaled.safetensors","type":"wan","device":"default"}},
     "3":{"class_type":"VAELoader","inputs":{"vae_name":"wan2.2_vae.safetensors"}},
     "4":{"class_type":"ModelSamplingSD3","inputs":{"model":["1",0],"shift":8.0}},
     "5":{"class_type":"CLIPTextEncode","inputs":{"text":prompt,"clip":["2",0]}},
     "6":{"class_type":"CLIPTextEncode","inputs":{"text":neg or NEG_WAN,"clip":["2",0]}},
     "7":{"class_type":"Wan22ImageToVideoLatent","inputs":{"vae":["3",0],"width":1280,"height":704,
          "length":images,"batch_size":1}},
     "8":{"class_type":"KSampler","inputs":{"seed":seed,"steps":etapes,"cfg":cfg,"sampler_name":"uni_pc",
          "scheduler":"simple","denoise":1.0,"model":["4",0],"positive":["5",0],
          "negative":["6",0],"latent_image":["7",0]}},
     "9":{"class_type":"VAEDecode","inputs":{"samples":["8",0],"vae":["3",0]}},
     "10":{"class_type":"CreateVideo","inputs":{"images":["9",0],"fps":fps}},
     "11":{"class_type":"SaveVideo","inputs":{"video":["10",0],"filename_prefix":prefixe,
           "format":"auto","codec":"auto"}},
    }

def g_video_image(prompt, neg, image, seed, prefixe, par=None):
    par = par or {}
    r = REGLAGES["wan14b"]
    etapes, cfg = int(par.get("etapes", r["etapes"])), float(par.get("cfg", r["cfg"]))
    images, fps = int(par.get("images", r["images"])), float(par.get("fps", r["fps"]))
    mi = max(1, etapes // 2)   # bascule entre les deux experts
    return {
     "1":{"class_type":"UnetLoaderGGUF","inputs":{"unet_name":"Wan2.2-I2V-A14B-HighNoise-Q4_K_S.gguf"}},
     "2":{"class_type":"UnetLoaderGGUF","inputs":{"unet_name":"Wan2.2-I2V-A14B-LowNoise-Q4_K_S.gguf"}},
     "3":{"class_type":"LoraLoaderModelOnly","inputs":{"model":["1",0],
          "lora_name":"wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors","strength_model":1.0}},
     "4":{"class_type":"LoraLoaderModelOnly","inputs":{"model":["2",0],
          "lora_name":"wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors","strength_model":1.0}},
     "5":{"class_type":"ModelSamplingSD3","inputs":{"model":["3",0],"shift":5.0}},
     "6":{"class_type":"ModelSamplingSD3","inputs":{"model":["4",0],"shift":5.0}},
     "7":{"class_type":"CLIPLoader","inputs":{"clip_name":"umt5_xxl_fp8_e4m3fn_scaled.safetensors","type":"wan","device":"default"}},
     "8":{"class_type":"VAELoader","inputs":{"vae_name":"wan_2.1_vae.safetensors"}},
     "9":{"class_type":"LoadImage","inputs":{"image":image}},
     "10":{"class_type":"CLIPTextEncode","inputs":{"text":prompt,"clip":["7",0]}},
     "11":{"class_type":"CLIPTextEncode","inputs":{"text":neg or NEG_WAN,"clip":["7",0]}},
     "12":{"class_type":"WanImageToVideo","inputs":{"positive":["10",0],"negative":["11",0],
           "vae":["8",0],"width":1280,"height":704,"length":images,"batch_size":1,"start_image":["9",0]}},
     "13":{"class_type":"KSamplerAdvanced","inputs":{"model":["5",0],"add_noise":"enable",
           "noise_seed":seed,"steps":etapes,"cfg":cfg,"sampler_name":"euler","scheduler":"simple",
           "positive":["12",0],"negative":["12",1],"latent_image":["12",2],
           "start_at_step":0,"end_at_step":mi,"return_with_leftover_noise":"enable"}},
     "14":{"class_type":"KSamplerAdvanced","inputs":{"model":["6",0],"add_noise":"disable",
           "noise_seed":0,"steps":etapes,"cfg":cfg,"sampler_name":"euler","scheduler":"simple",
           "positive":["12",0],"negative":["12",1],"latent_image":["13",0],
           "start_at_step":mi,"end_at_step":10000,"return_with_leftover_noise":"disable"}},
     "15":{"class_type":"VAEDecode","inputs":{"samples":["14",0],"vae":["8",0]}},
     "16":{"class_type":"CreateVideo","inputs":{"images":["15",0],"fps":fps}},
     "17":{"class_type":"SaveVideo","inputs":{"video":["16",0],"filename_prefix":prefixe,
           "format":"auto","codec":"auto"}},
    }

LANGUES_ACE = {"ar","az","bg","bn","ca","cs","da","de","el","en","es","fa","fi","fr","he","hi",
               "hr","ht","hu","id","is","it","ja","ko","la","lt","ms","ne","nl","no","pa","pl",
               "pt","ro","ru","sa","sk","sr","sv","sw","ta","te","th","tl","tr","uk","ur","vi",
               "yue","zh","unknown"}
TONALITES_ACE = {f"{n} {m}" for m in ("major", "minor")
                 for n in ("C","C#","Db","D","D#","Eb","E","F","F#","Gb","G","G#","Ab",
                           "A","A#","Bb","B")}

def g_audio(cle, tags, paroles, seed, prefixe, langue="en", tonalite="C minor",
            par=None, source=None):
    """Un morceau, cree de rien ou retouche a partir de « source ».

    Toute la difference tient au point de depart du KSampler : une latente vide
    pour creer, la latente du morceau fourni pour retoucher.
    """
    par = par or {}
    r = REGLAGES.get(cle, REGLAGES["audio"])
    etapes = int(par.get("etapes", r["etapes"]))
    cfg    = float(par.get("cfg", r["cfg"]))
    bpm    = int(par.get("bpm", r["bpm"]))
    duree  = float(par.get("duree_s", r["duree_s"]))
    langue = langue if langue in LANGUES_ACE else "en"
    tonalite = tonalite if tonalite in TONALITES_ACE else "C minor"
    checkpoint = CATALOGUE[cle]["checkpoint"]
    # 0.5 mesure comme le meilleur compromis, et 0.7 rejete : voir la note en
    # tete de g_audio. Sans source, on part de rien, donc 1.0.
    denoise = float(par.get("denoise", 0.5)) if source else 1.0
    depart = ({"11":{"class_type":"VAEEncodeAudio","inputs":{"audio":["7",0],"vae":["2",0]}},
               "7":{"class_type":"LoadAudio","inputs":{"audio":source}}} if source else
              {"7":{"class_type":"EmptyAceStep1.5LatentAudio",
                    "inputs":{"seconds":duree,"batch_size":1}}})
    return {
     **depart,
     "1":{"class_type":"UNETLoader","inputs":{"unet_name":checkpoint,"weight_dtype":"default"}},
     "2":{"class_type":"VAELoader","inputs":{"vae_name":"ace_1.5_vae.safetensors"}},
     "3":{"class_type":"DualCLIPLoader","inputs":{"clip_name1":"qwen_0.6b_ace15.safetensors",
          "clip_name2":"qwen_4b_ace15.safetensors","type":"ace","device":"default"}},
     # Valeurs d'enumeration relevees dans /object_info : la mesure est "4" et non
     # "4/4", la tonalite s'ecrit "C major" avec majuscule, et la langue est un
     # code ISO deux lettres, pas "english".
     "4":{"class_type":"TextEncodeAceStepAudio1.5","inputs":{"clip":["3",0],"tags":tags,
          "lyrics":paroles,"seed":seed,"bpm":bpm,"duration":float(duree),
          "timesignature":"4","language":langue,"keyscale":tonalite,
          # Valeurs relevees dans les gabarits officiels sft et turbo.
          # top_k=0 signifie « pas de troncature » : a 50, l'echantillonnage des
          # codes audio s'appauvrit et la piste tourne en boucle sur quelques notes.
          # False des qu'un morceau est fourni : l'infobulle du noeud
          # (comfy_extras/nodes_ace.py:47) dit de le couper quand on donne une
          # reference audio. Dix fois plus rapide, et la structure mieux gardee.
          "generate_audio_codes":not source,"cfg_scale":2.0,"temperature":0.85,
          "top_p":1.0,"top_k":0,"min_p":0.0}},
     "5":{"class_type":"ConditioningZeroOut","inputs":{"conditioning":["4",0]}},
     "6":{"class_type":"ModelSamplingAuraFlow","inputs":{"model":["1",0],"shift":3.0}},
     "8":{"class_type":"KSampler","inputs":{"seed":seed,"steps":etapes,"cfg":cfg,"sampler_name":"euler",
          "scheduler":"simple","denoise":denoise,"model":["6",0],"positive":["4",0],
          "negative":["5",0],"latent_image":["11" if source else "7",0]}},
     "9":{"class_type":"VAEDecodeAudio","inputs":{"samples":["8",0],"vae":["2",0]}},
     "10":{"class_type":"SaveAudioMP3","inputs":{"audio":["9",0],"filename_prefix":prefixe,"quality":"V0"}},
    }

# ══════════════════════════════ execution ══════════════════════════════
def entrees_a_joindre(g):
    """Les fichiers du cache local que ce graphe va lire.

    Lus ici et joints au travail : une machine a agent n'a pas d'adresse, on ne
    peut rien lui deposer, il faut donc que tout parte avec la demande.
    """
    joint = {}
    for _, _, nom in entrees_du_graphe(g):
        if nom in joint:
            continue
        chemin = os.path.join(DOSSIER_ENTREE, nom)
        if not os.path.exists(chemin):
            continue
        with open(chemin, "rb") as f:
            joint[nom] = base64.b64encode(f.read()).decode()
    return joint


async def soumettre_a_agent(g, tid, ident):
    """Depose le travail et attend que l'agent le rende.

    Aucun appel sortant vers le noeud : il n'a pas d'adresse joignable, c'est
    tout l'interet. Le travail patiente dans TRAVAUX jusqu'a ce que l'agent
    vienne le prendre, puis le resultat arrive par api_noeud_resultat.
    """
    boucle = asyncio.get_running_loop()
    attente = boucle.create_future()
    RESULTATS[tid] = (ident, attente)
    entrees = entrees_a_joindre(g)
    if entrees:
        poids = sum(len(v) for v in entrees.values()) * 3 / 4
        journal(tid, f"{len(entrees)} fichier(s) d'entree joints au travail "
                     f"({poids / 1e6:.1f} Mo)")
    TRAVAUX.setdefault(ident, []).append({"tid": tid, "graphe": g,
                                          "entrees": entrees})
    titre_ = (noeud(ident) or {}).get("titre", ident)
    journal(tid, f"travail confie a {titre_} — en attente de sa reponse")
    t0 = time.time()
    try:
        d = await _attendre_le_noeud(attente, ident, titre_, tid)
    except asyncio.TimeoutError:
        raise RuntimeError(f"{titre_} n'a pas rendu de resultat en une heure")
    finally:
        RESULTATS.pop(tid, None)
        file = TRAVAUX.get(ident) or []
        TRAVAUX[ident] = [t for t in file if t["tid"] != tid]
    if d.get("etat") != "fini":
        detail = d.get("erreur") or f"echec sur {titre_}"
        # Les erreurs d'une machine a agent ne passaient pas par ce tri : elles
        # remontaient telles quelles, donc sans report sur une autre machine.
        if _machine_incapable(detail):
            raise MachineIncapable(detail[:220])
        verdict = _est_panne(detail)
        if verdict or verdict is None:
            raise PanneNoeud(detail[:220])
        raise RuntimeError(detail)
    sorties = [dict(f, noeud=ident) for f in d.get("fichiers", [])
               if isinstance(f, dict) and f.get("filename")]
    return sorties, d.get("secondes") or (time.time() - t0)


async def _attendre_le_noeud(attente, ident, titre, tid):
    """Attend le resultat, en surveillant que la machine parle encore.

    Une heure d'attente seche etait la seule borne. Constate : le ComfyUI d'une
    machine s'est arrete APRES avoir reçu le travail ; son agent continuait de
    battre et d'annoncer honnetement « ma carte ne repond pas », et le studio a
    attendu une reponse qui ne viendrait jamais. Deux demandes sont restees
    « en cours » plus de dix minutes, sans un mot.

    On regarde donc toutes les cinq secondes si la machine s'est tue. Le silence
    seul ne suffit pas — un agent peut manquer un battement pendant un rendu qui
    sature sa machine — d'ou une tolerance large, et une PanneNoeud plutot qu'une
    erreur : soumettre_robuste reprendra ailleurs, ce qu'il sait deja faire.
    """
    fin = time.time() + 3600
    while True:
        reste = fin - time.time()
        if reste <= 0:
            raise asyncio.TimeoutError()
        try:
            return await asyncio.wait_for(asyncio.shield(attente), timeout=min(5, reste))
        except asyncio.TimeoutError:
            pass
        e = ETAT_NOEUDS.get(ident) or {}
        mut = time.time() - (e.get("vu") or 0)
        if mut > 4 * SILENCE_MAX:
            journal(tid, f"{titre} ne donne plus signe de vie depuis {mut:.0f} s "
                         f"— on ne l'attend plus")
            raise PanneNoeud(f"{titre} s'est tue pendant le rendu")


class MachineIncapable(RuntimeError):
    """Cette machine ne peut pas executer ce travail, et ne le pourra pas.

    Carte trop ancienne pour la version de PyTorch installee, noeud absent de
    SON ComfyUI : reessayer n'a aucun sens, mais une autre machine reussira
    peut-etre. On l'ecarte donc, definitivement, sans abandonner la demande.
    """


class PanneNoeud(RuntimeError):
    """La machine n'a pas pu executer : injoignable, arretee, ou a court de
    memoire. La demande, elle, reste valable — d'ou une reprise."""


# Ce qui vient de la machine et non de la demande. Une memoire saturee tient
# dans cette liste : la meme demande passe souvent sur une carte plus grande,
# ou sur la meme une fois qu'elle s'est videe.
_PANNES = ("out of memory", "cuda error", "no cuda", "device-side assert",
           "connection", "timed out", "timeout", "broken pipe",
           "cannot allocate", "allocation on device", "unable to load",
           "server disconnected", "cannot connect")

# Ce qui condamne la MACHINE, pas la demande. « no kernel image » signifie que
# le PyTorch installe n'a pas de noyau pour cette carte : aucune attente n'y
# changera rien, mais une autre machine s'en tirera.
_INCAPABLES = ("no kernel image", "nokernelimage",
               "not compiled with cuda", "no cuda gpus are available",
               "torch not compiled")


def _machine_incapable(message):
    bas = (message or "").lower()
    return any(x in bas for x in _INCAPABLES)


# Ce qui vient de la demande. Reessayer ne changerait rien.
_FAUTES = ("value not in list", "required input is missing", "invalid prompt",
           "does not exist", "not a valid", "unknown node", "return type mismatch")


def _est_panne(message):
    """Vrai si l'echec est imputable a la machine plutot qu'a la demande.

    En cas de doute on repond « panne » : une reprise inutile coute quelques
    minutes, un abandon injustifie coute le travail de l'utilisateur.
    """
    bas = (message or "").lower()
    if any(x in bas for x in _FAUTES):
        return False
    return True if any(x in bas for x in _PANNES) else None


def entrees_du_graphe(g):
    """Les fichiers que ce graphe lit dans l'input de la machine qui execute."""
    trouves = []
    for cle, noeud in g.items():
        # LoadAudio range son fichier dans « audio », pas dans « image » ni
        # « file ». Sans lui, un graphe de retouche sonore partait vers une
        # machine a agent SANS le morceau a retoucher.
        for champ in ("image", "file", "audio", "video"):
            v = (noeud.get("inputs") or {}).get(champ)
            if isinstance(v, str) and v:
                trouves.append((cle, champ, v))
    return trouves


async def deplacer_entrees(g, ancien, nouveau, tid=None):
    """Renvoie les fichiers d'entree vers la machine qui va calculer.

    Le graphe porte des noms valables sur l'ANCIENNE machine ; ComfyUI renomme
    parfois a la reception, d'ou le registre qui garde la correspondance. Sans
    cette etape, changer de machine donne un graphe qui pointe dans le vide.
    """
    if ancien == nouveau:
        return g
    inverse = {v: k[0] for k, v in ENTREES_DISTANTES.items() if k[1] == ancien}
    for cle, champ, nom in entrees_du_graphe(g):
        local = inverse.get(nom, nom)      # sur la machine hote, c'est deja le nom du cache
        try:
            g[cle]["inputs"][champ] = await pousser_entree(local, nouveau, tid)
        except Exception as e:
            raise PanneNoeud(f"fichier d'entree non transmis a {nouveau} : {e}")
    return g


async def soumettre_robuste(g, tid, ident, cle, patience=1800):
    """Soumet, et reprend sur panne : ailleurs, ou ici des que possible.

    « patience » borne l'acharnement. Passe ce delai sans aucune machine, on
    rend la main avec un message qui dit ce qui s'est passe — c'est le seul cas
    ou un echec est acceptable.
    """
    debut = time.time()
    ecartes = set()
    incapables = set()          # ecartees pour de bon : elles ne peuvent pas
    inexpliques = 0
    while True:
        try:
            # Le verrou ici et pas plus haut : seule la carte se dispute, et une
            # reprise sur une autre machine prend ainsi le verrou de celle-la.
            # Pose autour du bloc entier, il serait reste tenu sur une carte qui
            # ne calcule plus des la premiere reprise.
            attendu = time.time()
            verrou = verrou_noeud(ident)
            if verrou.locked():
                # Un TROISIEME etat, ni file ni calcul : la demande a ete
                # analysee, sa machine est choisie, et cette machine travaille
                # pour quelqu'un d'autre. Affichee « en cours », elle promettait
                # un calcul qui n'avait pas commence.
                if tid in TACHES:
                    TACHES[tid]["attend_carte"] = True
                journal(tid, f"{(noeud(ident) or {}).get('titre', ident)} calcule "
                             f"deja pour quelqu'un — on prend le tour suivant")
            try:
                async with verrou:
                    if tid in TACHES:
                        TACHES[tid].pop("attend_carte", None)
                    if time.time() - attendu > 2:
                        journal(tid, f"la carte se libere apres "
                                     f"{time.time() - attendu:.0f} s d'attente")
                    return await soumettre(g, tid, ident)
            finally:
                # Aussi sur reprise et sur annulation : le drapeau ne doit pas
                # survivre au travail qu'il decrit.
                if tid in TACHES:
                    TACHES[tid].pop("attend_carte", None)
        except MachineIncapable as e:
            incapables.add(ident)
            ecartes.add(ident)
            titre_ = (noeud(ident) or {}).get("titre", ident)
            journal(tid, f"{titre_} ne peut pas executer ce travail ({e}) — "
                         f"ecartee, on cherche ailleurs")
        except PanneNoeud as e:
            # Un echec qu'on ne sait pas classer vaut UNE reprise, pas une
            # demi-heure d'acharnement : au deuxieme, c'est une vraie faute et
            # s'entêter ne ferait que retarder le message d'erreur.
            if str(e).startswith("echec inexplique"):
                inexpliques += 1
                if inexpliques > 1:
                    raise RuntimeError("echec de la generation " + str(e)[17:])
            ecartes.add(ident)
            journal(tid, f"{ident} a lache ({e}) — reprise en cours")

        # Une autre machine capable du meme moteur, jamais celle qui vient de
        # tomber tant qu'une autre existe.
        autres = [x for x in noeuds_pour(cle) if x["id"] not in ecartes]
        if autres:
            # Meme regle qu'au premier choix : la moins chargee d'abord. Une
            # reprise a deja perdu du temps ; la faire attendre derriere un rendu
            # en cours en perdrait deux fois.
            moindre_ = min(charge_noeud(x["id"]) for x in autres)
            autres = [x for x in autres if charge_noeud(x["id"]) == moindre_]
            neuf = (next((x for x in autres if x.get("local")), None)
                    or max(autres, key=lambda x: ETAT_NOEUDS.get(x["id"], {}).get("vram", 0)))
            journal(tid, f"la demande repart sur {neuf.get('titre', neuf['id'])}")
            g = await deplacer_entrees(g, ident, neuf["id"], tid)
            ident = neuf["id"]
            # La tache doit suivre : l'annulation, la progression et le verrou
            # lisent tous TACHES[tid]["noeud"]. Fige au premier choix, il faisait
            # frapper l'annulation a la porte d'une machine qui ne calculait plus.
            if tid in TACHES:
                TACHES[tid]["noeud"] = ident
            continue

        # Plus personne. Sur la machine hote, on tente de relever ComfyUI :
        # c'est la panne la plus frequente et la plus facile a reparer.
        if est_local(ident) and not await comfy_repond():
            if relancer_comfy_local():
                journal(tid, "ComfyUI relance sur cette machine — on patiente")

        reste = patience - (time.time() - debut)
        if reste <= 0:
            raise RuntimeError(
                f"aucune machine n'a pu executer la demande en "
                f"{patience // 60:.0f} minutes. Le travail n'est pas perdu : "
                f"relance-le quand une machine sera revenue.")
        journal(tid, f"aucune machine disponible — nouvelle tentative dans 30 s "
                     f"({reste / 60:.0f} min de patience restante)")
        await asyncio.sleep(30)
        await sonder_noeuds()
        # Au retour, on redonne sa chance a celles qui sont tombees : elles ont
        # pu redemarrer. Pas a celles qui sont INCAPABLES : leur carte ne
        # changera pas d'ici trente secondes.
        ecartes = set(incapables)
        if incapables and all(x["id"] in incapables for x in noeuds_pour(cle)):
            raise RuntimeError(
                "aucune machine ne peut executer ce moteur : "
                + ", ".join(sorted(incapables))
                + ". Verifie la version de PyTorch installee sur ces machines.")
        choisi = choisir_noeud(cle)
        ident = choisi["id"] if choisi else ident


def relancer_comfy_local():
    """Relance ComfyUI sur la machine hote. Vrai si la commande est partie.

    Meme mecanique que le bouton de l'interface, sans la requete : ici c'est le
    studio qui decide, parce que personne ne regarde l'ecran a trois heures du
    matin.
    """
    lanceur = lanceur_comfy()
    if not lanceur:
        return False
    try:
        cmd = commande_comfy()
        if os.name == "nt":
            drapeaux = 0x00000008 | 0x08000000
            if cmd:
                subprocess.Popen(cmd, cwd=DOSSIER_COMFY, creationflags=drapeaux,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 stdin=subprocess.DEVNULL)
            else:
                os.startfile(lanceur, cwd=DOSSIER_COMFY)
        else:
            subprocess.Popen(["/bin/sh", lanceur], cwd=DOSSIER_COMFY,
                             start_new_session=True)
        return True
    except Exception as e:
        print(f"relance de ComfyUI impossible : {e}", flush=True)
        return False


async def soumettre(g, tid, ident=None):
    ident = ident or noeud_local()["id"]
    if est_agent(ident):
        return await soumettre_a_agent(g, tid, ident)
    base = url_de(ident)
    to = aiohttp.ClientTimeout(total=4000)
    try:
        session = aiohttp.ClientSession(timeout=to)
    except Exception as e:
        raise PanneNoeud(str(e))
    async with session as s:
        try:
            async with s.post(f"{base}/prompt",
                              json={"prompt": g, "client_id": "studio"}) as r:
                texte_reponse = await r.text()
                if r.status >= 500:
                    # 5xx : ComfyUI est la mais en detresse (souvent au
                    # redemarrage). C'est une panne, pas une demande fautive.
                    raise PanneNoeud(f"HTTP {r.status}")
                if r.status != 200:
                    verdict = _est_panne(texte_reponse)
                    if verdict:
                        raise PanneNoeud(texte_reponse[:200])
                    raise RuntimeError("ComfyUI a refuse le graphe : "
                                       + texte_reponse[:400])
                pid = json.loads(texte_reponse)["prompt_id"]
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            raise PanneNoeud(f"injoignable ({type(e).__name__})")
        t0 = time.time()
        while True:
            try:
                async with s.get(f"{base}/history/{pid}") as r:
                    hist = await r.json()
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                # ComfyUI a disparu en cours de calcul : c'est le cas le plus
                # frequent, et celui qui faisait perdre le travail.
                raise PanneNoeud(f"perdu en cours de calcul ({type(e).__name__})")
            if pid in hist:
                st = hist[pid]["status"]
                if not st.get("completed"):
                    detail = ""
                    for m in st.get("messages", []):
                        if m[0] == "execution_error":
                            detail = json.dumps(m[1])[:300]
                    if _machine_incapable(detail):
                        raise MachineIncapable(detail[:220])
                    verdict = _est_panne(detail)
                    if verdict:
                        raise PanneNoeud(detail[:200] or "echec sans detail")
                    if verdict is None:
                        # Ni panne reconnue ni faute reconnue : on accorde UNE
                        # reprise. Un echec passager ne doit pas condamner la
                        # demande, mais une vraie faute ne doit pas boucler.
                        raise PanneNoeud("echec inexplique " + detail[:160])
                    raise RuntimeError("echec de la generation " + detail)
                # ComfyUI range les sorties sous une cle par type ("images",
                # "video", "audio", "3d"…). On ramasse tout ce qui ressemble a
                # un fichier plutot que d'enumerer des types qu'on oubliera.
                out = []
                for o in hist[pid]["outputs"].values():
                    for valeur in o.values():
                        if isinstance(valeur, list):
                            out += [dict(x, noeud=ident) for x in valeur
                                    if isinstance(x, dict) and "filename" in x]
                return out, time.time() - t0
            if time.time() - t0 > 3600:
                raise RuntimeError("delai depasse")
            await asyncio.sleep(2)

_MINEUR = re.compile(r"\b(enfant|gamin|gamine|fillette|garconnet|bambin|b[ée]b[ée]|mineur|"
                     r"coll[ée]gien|coll[ée]gienne|[ée]col(ier|iere)|child|kid|toddler|infant|"
                     r"minor|preteen|pre-teen|loli|shota|underage|schoolgirl|schoolboy|"
                     r"\b(\d|1[0-7])\s*ans?\b|\b(\d|1[0-7])\s*years?\s*old\b)", re.I)
_SEXUEL = re.compile(r"\b(nu|nue|nus|nues|nudit[ée]|seins|fesses|sexe|sexuel|sexuelle|[ée]rotique|"
                     r"porno|pornographique|explicit|nsfw|nude|naked|topless|lingerie|breasts|"
                     r"nipples|genital|penis|vagina|sex|erotic|porn|hentai|rating_explicit)", re.I)

# Fichiers d'entree deja pousses sur un noeud distant : (nom, id) -> nom reel
# la-bas. ComfyUI renomme en « x (1).png » quand le nom existe deja, il faut
# donc retenir ce qu'il a REELLEMENT accepte, pas ce qu'on lui a demande.
ENTREES_DISTANTES = {}

def _sous(base, *morceaux):
    """Assemble un chemin SOUS `base`, ou rend None.

    Toutes les pieces viennent d'ailleurs : `subfolder` et `filename` sont
    recopies du compte rendu d'une machine a agent, l'identifiant de noeud vient
    d'une requete. Un « subfolder » absolu, ou seulement un « .. » de trop, et le
    chemin sort du dossier — la purge des conversations fermees effaçait alors le
    fichier vise, y compris « conversations/_cles.json ».

    On refuse plutot que de corriger : un chemin qu'il faut redresser est un
    chemin qu'on n'aurait pas du recevoir, et le silence vaut mieux qu'une
    devinette. Le controle final porte sur le chemin RESOLU, seul moyen de tenir
    compte des liens symboliques.
    """
    racine = os.path.realpath(base)
    vise = os.path.realpath(os.path.join(racine, *[m or "" for m in morceaux]))
    if vise != racine and not vise.startswith(racine + os.sep):
        return None
    return vise


def chemin_agent(ident, nom):
    """Le fichier d'une machine dans le depot du studio, ou None.

    basename ne suffit pas : il rend « .. » pour « ../.. », si bien qu'un
    identifiant de noeud forge remontait quand meme d'un cran. On assemble donc
    par _sous(), qui verifie le chemin RESOLU au lieu de faire confiance a ses
    morceaux.
    """
    return _sous(SORTIES_AGENT, os.path.basename(ident or ""),
                 os.path.basename(nom or ""))


def chemin_sortie_locale(sous, nom):
    """Le fichier dans l'output du ComfyUI local — ou None s'il n'y est pas."""
    return _sous(os.path.join(BASE_COMFY, "output"), sous, os.path.basename(nom or ""))


def output_comfy_a_nous():
    """Vrai si l'on peut ecrire dans l'output du ComfyUI de cette machine.

    Sur un studio sans carte, ce dossier appartient a une image Docker qui n'est
    pas montee, ou a personne : on ne peut pas y deposer un resultat, et il n'y
    a de toute facon aucun ComfyUI pour le relire.
    """
    dossier = os.path.join(BASE_COMFY, "output")
    try:
        os.makedirs(dossier, exist_ok=True)
        return os.access(dossier, os.W_OK)
    except OSError:
        return False


async def lire_sortie(info):
    """Les octets d'une sortie, qu'elle soit sur cette machine ou ailleurs."""
    ident = info.get("noeud") or noeud_local()["id"]
    # Le depot du studio passe avant tout le reste : un resultat venu d'un
    # fournisseur y est pose sous l'identifiant local, et le chercher dans un
    # ComfyUI qui n'existe pas rendrait « introuvable » un fichier qu'on a.
    depot = chemin_agent(ident, info["filename"])
    if depot and os.path.exists(depot):
        with open(depot, "rb") as f:
            return f.read()
    if est_agent(ident):
        # l'agent a depose le fichier chez nous : il est deja local
        chemin = chemin_agent(ident, info["filename"])
        if not chemin or not os.path.exists(chemin):
            raise RuntimeError(f"fichier absent du depot de {ident} : {info['filename']}")
        with open(chemin, "rb") as f:
            return f.read()
    if est_local(ident):
        src = chemin_sortie_locale(info.get("subfolder", ""), info["filename"])
        if not src or not os.path.exists(src):
            raise RuntimeError(f"image precedente introuvable : {src}")
        with open(src, "rb") as f:
            return f.read()
    params = {"filename": info["filename"], "subfolder": info.get("subfolder", ""),
              "type": "output"}
    to = aiohttp.ClientTimeout(total=120)
    async with aiohttp.ClientSession(timeout=to) as s:
        async with s.get(f"{url_de(ident)}/view", params=params) as r:
            if r.status != 200:
                raise RuntimeError(f"image introuvable sur {ident} : {info['filename']}")
            return await r.read()

async def pousser_entree(nom, ident, tid=None):
    """Depose un fichier du cache local dans l'input d'un noeud distant.

    Le studio n'ecrit que sur son propre disque : pour toute autre machine, la
    seule voie est /upload/image. On retient le nom rendu par ComfyUI, qui n'est
    pas forcement celui qu'on a envoye.
    """
    if est_local(ident):
        return nom
    if est_agent(ident):
        # Rien a pousser : le fichier partira avec le travail, et c'est l'agent
        # qui le deposera dans l'input de son ComfyUI.
        return nom
    connu = ENTREES_DISTANTES.get((nom, ident))
    if connu:
        return connu
    chemin = os.path.join(DOSSIER_ENTREE, nom)
    with open(chemin, "rb") as f:
        octets = f.read()
    donnees = aiohttp.FormData()
    donnees.add_field("image", octets, filename=nom, content_type="application/octet-stream")
    donnees.add_field("type", "input")
    donnees.add_field("overwrite", "true")
    to = aiohttp.ClientTimeout(total=300)
    async with aiohttp.ClientSession(timeout=to) as s:
        async with s.post(f"{url_de(ident)}/upload/image", data=donnees) as r:
            if r.status != 200:
                raise RuntimeError(f"televersement refuse par {ident} : "
                                   + (await r.text())[:200])
            rendu = (await r.json()).get("name") or nom
    ENTREES_DISTANTES[(nom, ident)] = rendu
    if tid:
        journal(tid, f"image envoyee a {(noeud(ident) or {}).get('titre', ident)}")
    return rendu

async def recuperer_sortie(info, pid):
    """LoadImage ne lit que dans l'input du noeud qui execute. Une sortie vit
    dans output/, parfois sur une autre machine : on la rapatrie dans le cache
    local, d'ou elle sera poussee vers le noeud retenu si besoin."""
    octets = await lire_sortie(info)
    os.makedirs(DOSSIER_ENTREE, exist_ok=True)
    nom = f"reprise_{uuid.uuid4().hex[:10]}{os.path.splitext(info['filename'])[1]}"
    with open(os.path.join(DOSSIER_ENTREE, nom), "wb") as f:
        f.write(octets)
    # la copie appartient a celui dont on reprend la sortie : sans cela, la
    # purge par utilisateur ne la verrait pas et retomberait sur un plafond global
    ENTREES[nom] = pid
    purger_entrees(pid=pid)
    sauver_entrees()
    return nom

def entrees_reservees():
    """Images dont une tache a encore besoin. Sans cela, quarante televersements
    d'affilee effacaient le fichier d'une tache encore en file, qui echouait
    ensuite sur un LoadImage introuvable."""
    en_jeu = set(ATTENTE) | set(EN_VOL)
    return {TACHES[t].get("image") for t in en_jeu
            if t in TACHES and TACHES[t].get("image")}

def purger_entrees(garder=40, pid=None):
    """ComfyUI/input se remplit de nos copies de travail. On garde les plus
    recentes et on efface le reste : ces fichiers ne servent qu'une fois.

    Le plafond est par utilisateur. Global, un visiteur qui televerse en rafale
    effacait le fichier d'entree d'un autre dont la tache attendait encore son
    tour — un defaut d'execution, pas seulement de confidentialite.
    """
    try:
        notres = [f for f in os.listdir(DOSSIER_ENTREE)
                  if f.startswith(("studio_", "reprise_"))
                  and (pid is None or ENTREES.get(f) == pid)
                  and f not in entrees_reservees()]
    except OSError:
        return
    if len(notres) <= garder:
        return
    notres.sort(key=lambda f: os.path.getmtime(os.path.join(DOSSIER_ENTREE, f)))
    for f in notres[:-garder]:
        try:
            os.remove(os.path.join(DOSSIER_ENTREE, f))
            ENTREES.pop(f, None)
        except OSError:
            pass

def garde_fou(*textes):
    """Seule limite codee en dur : pas de contenu sexuel impliquant des mineurs.
    Tout le reste, y compris le contenu adulte, passe sans filtre."""
    joint = " ".join(t for t in textes if t)
    if _MINEUR.search(joint) and _SEXUEL.search(joint):
        raise RuntimeError("demande refusee : contenu sexuel impliquant des mineurs.")

FICHIER_AVIS = os.path.join(DOSSIER_DONNEES, "avis.jsonl")

def noter_avis(pid, conv, tour, avis, note):
    """Consigne un pouce a cote de l'historique, en ligne a ligne.

    Un fichier a part et non la conversation : celle-ci peut etre supprimee par
    son proprietaire, alors que le retour, lui, sert a corriger le code — c'est
    la seule mesure qu'on ait de ce qui marche. Le format « une ligne, un
    objet » se relit meme si l'ecriture a ete coupee en cours.
    """
    ligne = {
        "quand": time.strftime("%Y-%m-%d %H:%M:%S"), "avis": avis, "note": note,
        "utilisateur": (pid or "")[:12], "conversation": conv["id"],
        "tour": tour.get("id"), "demande": tour.get("demande"),
        "moteur": tour.get("modele"), "type": tour.get("type"),
        "parametres": tour.get("parametres"), "prompt": tour.get("prompt"),
        "paroles": tour.get("paroles"), "raison": tour.get("raison"),
        "etat": tour.get("etat"), "erreur": tour.get("erreur"),
        "fichiers": [f.get("filename") for f in (tour.get("fichiers") or [])],
    }
    try:
        with open(FICHIER_AVIS, "a", encoding="utf-8") as f:
            f.write(json.dumps(ligne, ensure_ascii=False) + chr(10))
    except Exception as e:
        print(f"avis non enregistre : {e}", flush=True)


def lire_avis(limite=200):
    lignes = []
    try:
        with open(FICHIER_AVIS, encoding="utf-8") as f:
            for l in f:
                l = l.strip()
                if not l:
                    continue
                try:
                    lignes.append(json.loads(l))
                except ValueError:
                    continue
    except FileNotFoundError:
        return []
    return lignes[-limite:][::-1]


async def api_avis(req):
    """Pouce en l'air, pouce en bas, et un mot si l'on veut."""
    pid = qui(req)
    try:
        d = await req.json()
    except Exception:
        return web.json_response({"erreur": "corps illisible"}, status=400)
    tid = str(d.get("tid") or "")
    try:
        avis = int(d.get("avis", 0))
    except (TypeError, ValueError):
        avis = 0
    if avis not in (-1, 0, 1):
        return web.json_response({"erreur": "avis attendu : -1, 0 ou 1"}, status=400)
    note = str(d.get("note") or "")[:2000]
    for conv in mes_conversations(pid):
        for tour in conv.get("tours", []):
            if tour.get("id") == tid:
                tour["avis"] = avis
                tour["note"] = note
                sauver(conv)
                if avis:
                    noter_avis(pid, conv, tour, avis, note)
                return web.json_response({"ok": True, "avis": avis})
    return web.json_response({"erreur": "echange inconnu"}, status=404)


def raison_du_local(texte, image_b64=None, pid=None):
    """Pourquoi cette demande n'est pas partie chez le fournisseur choisi."""
    choix = CHOIX.get("llm", "local")
    if choix == "local":
        return ""
    if pid is not None and not nuage_actif(pid):
        return "nuage coupe : le modele local est utilise"
    if pid is not None and not fournisseur_dispo("llm"):
        return ""
    if image_b64:
        return "lecture d'image : le modele de vision local est utilise"
    if adulte(texte):
        return "contenu adulte : l'analyse reste sur cette machine"
    if not cle_de(choix):
        return f"aucune cle pour {choix} : le modele local est utilise"
    return ""


def _cles_masquees():
    """Ce que l'administration a le droit de voir : jamais la cle elle-meme."""
    dit = {}
    for nom, conf in (list(fournisseurs.LLM.items())
                      + list(fournisseurs.IMAGE.items())
                      + list(fournisseurs.AUDIO.items())
                      + list(fournisseurs.VIDEO.items())
                      + list(fournisseurs.OBJET3D.items())):
        pose = cle_de(nom)
        dit[nom] = {"titre": conf["titre"], "aide": conf["aide"],
                    "modele_defaut": conf["modele"],
                    "modele": modele_de(nom), "posee": bool(pose),
                    "indice": fournisseurs.indice(pose) if pose else ""}
    return dit


async def api_admin_cles(req):
    if not admin_ok(req):
        return web.json_response({"erreur": "jeton invalide"}, status=403)
    return web.json_response({
        "fournisseurs": _cles_masquees(),
        "choix": dict(CHOIX),
        "modalites": [{"cle": m, "libelle": lib,
                       "fournisseurs": sorted(fournisseurs_de(m))}
                      for m, lib, _ in MODALITES],
    })


async def api_admin_modeles(req):
    """Les modeles que ce fournisseur declare, lus chez lui a l'instant.

    Interrogation a la demande et non au demarrage : les catalogues changent,
    et une liste mise en cache redeviendrait fausse sans prevenir.
    """
    if not admin_ok(req):
        return web.json_response({"erreur": "jeton invalide"}, status=403)
    nom = req.query.get("fournisseur", "")
    connus = (set(fournisseurs.LLM) | set(fournisseurs.IMAGE)
              | set(fournisseurs.AUDIO) | set(fournisseurs.VIDEO)
              | set(fournisseurs.OBJET3D))
    if nom not in connus:
        return web.json_response({"erreur": "fournisseur inconnu"}, status=400)
    cle = cle_de(nom) or (cle_de("google") if nom in _PAR_GOOGLE else "")
    if not cle:
        return web.json_response({"modeles": [], "raison": "aucune cle"})
    return web.json_response({"modeles": await fournisseurs.lister_modeles(nom, cle)})


async def api_admin_cles_poser(req):
    """Enregistre ou retire une cle, et le modele a employer avec elle."""
    if not admin_ok(req):
        return web.json_response({"erreur": "jeton invalide"}, status=403)
    try:
        d = await req.json()
    except Exception:
        return web.json_response({"erreur": "corps illisible"}, status=400)

    nom = str(d.get("fournisseur") or "")
    connus_tous = (set(fournisseurs.LLM) | set(fournisseurs.IMAGE)
                   | set(fournisseurs.AUDIO) | set(fournisseurs.VIDEO)
                   | set(fournisseurs.OBJET3D))
    if nom and nom not in connus_tous:
        return web.json_response({"erreur": "fournisseur inconnu"}, status=400)
    if nom:
        entree = CLES.setdefault(nom, {})
        if "cle" in d:
            # Chaine vide : retrait volontaire. Absente : on ne touche pas a la
            # cle en place, pour pouvoir ne changer que le nom du modele.
            cle = str(d.get("cle") or "").strip()
            if cle:
                entree["cle"] = cle
            else:
                entree.pop("cle", None)
        if "modele" in d:
            entree["modele"] = str(d.get("modele") or "").strip()
        if not entree.get("cle") and not entree.get("modele"):
            CLES.pop(nom, None)

    for quoi in CHOIX:
        if quoi in d:
            voulu = str(d.get(quoi) or "local")
            if voulu != "local" and voulu not in fournisseurs_de(quoi):
                return web.json_response({"erreur": f"{quoi} : choix inconnu"},
                                         status=400)
            CHOIX[quoi] = voulu
    try:
        sauver_cles()
    except OSError as e:
        return web.json_response({"erreur": f"enregistrement impossible ({e})"},
                                 status=500)
    return web.json_response({"ok": True, "fournisseurs": _cles_masquees(),
                              "choix": dict(CHOIX)})


def _etat_compte(req):
    nom = req.get("compte") or ""
    return {"connecte": bool(nom), "nom": nom,
            "admin": bool(nom) and COMPTES.est_admin(nom),
            # Sans aucun compte, l'interface n'a pas a proposer de se connecter :
            # la fonction n'existe pas encore pour cette installation.
            "comptes_existent": bool(COMPTES and COMPTES.gens),
            "obligatoire": AUTH == "obligatoire"}


async def api_compte(req):
    return web.json_response(_etat_compte(req))


# (compte, adresse) -> [nombre d'echecs, heure du dernier]. En memoire : une
# rafale traverse rarement un redemarrage, et persister des echecs ouvrirait la
# porte a un deni de service par un tiers qui bloquerait un compte a distance.
_ECHECS = {}
ATTENTE_MAX = 30.0          # secondes


def _freinage(cle):
    """Depuis combien de temps ce couple doit encore patienter.

    L'attente double a chaque echec — 1 s, 2, 4, 8… plafonnee. Un humain qui se
    trompe deux fois ne s'en apercoit pas ; une machine qui essaie un
    dictionnaire y passe des annees.
    """
    combien, quand = _ECHECS.get(cle, (0, 0.0))
    if combien < 3:
        return 0.0
    attente = min(2.0 ** (combien - 3), ATTENTE_MAX)
    return max(0.0, quand + attente - time.time())


async def api_entrer(req):
    """Ouvre une session. Le mot de passe ne transite qu'ici, et n'est pas garde."""
    try:
        d = await req.json()
    except Exception:
        return web.json_response({"erreur": "corps illisible"}, status=400)
    if not origine_sure(req):
        return web.json_response({"erreur": "origine refusee"}, status=403)
    hote = (req.transport.get_extra_info("peername") or ("",))[0] if req.transport else ""
    cle_freinage = (str(d.get("nom") or "").lower(), hote)
    reste = _freinage(cle_freinage)
    if reste > 0:
        return web.json_response(
            {"erreur": f"trop d'essais — reessaie dans {reste:.0f} s"}, status=429)

    c = COMPTES.authentifier(d.get("nom"), d.get("mdp"))
    if not c:
        combien = _ECHECS.get(cle_freinage, (0, 0.0))[0] + 1
        _ECHECS[cle_freinage] = (combien, time.time())
        if combien in (3, 10, 50):
            # Une rafale d'echecs doit se voir dans le journal du studio : c'est
            # le seul endroit ou son proprietaire la remarquera.
            print(f"  {combien} echecs de connexion pour « {cle_freinage[0]} » "
                  f"depuis {hote or 'origine inconnue'}", flush=True)
        # Un seul message pour « compte inconnu » et « mauvais mot de passe » :
        # les distinguer publierait la liste des comptes.
        return web.json_response({"erreur": "nom ou mot de passe incorrect"},
                                 status=403)

    _ECHECS.pop(cle_freinage, None)

    # Ce que ce navigateur avait accumule sans compte le rejoint : c'est la
    # premiere chose qu'on cherche apres s'etre connecte, et sans cela
    # l'historique semblerait perdu.
    ancien = req.cookies.get("studio") or ""
    repris = 0
    if _PID.fullmatch(ancien):
        neuf = _comptes.identifiant(c["nom"])
        for conv in list(CONVERSATIONS.values()):
            if conv.get("proprietaire") == ancien:
                conv["proprietaire"] = neuf
                sauver(conv)
                repris += 1

    rep_ = web.json_response({"ok": True, "nom": c["nom"],
                              "admin": bool(c.get("admin")), "reprises": repris})
    rep_.set_cookie("studio_compte", COMPTES.jeton(c["nom"]),
                    max_age=_comptes.DUREE_SESSION, httponly=True,
                    samesite="Lax", path="/")
    return rep_


async def api_sortir(req):
    rep_ = web.json_response({"ok": True})
    rep_.del_cookie("studio_compte", path="/")
    return rep_


async def api_mon_mdp(req):
    """Changer son propre mot de passe, en prouvant l'ancien."""
    nom = req.get("compte") or ""
    if not nom:
        return web.json_response({"erreur": "aucune session"}, status=403)
    try:
        d = await req.json()
    except Exception:
        return web.json_response({"erreur": "corps illisible"}, status=400)
    if not COMPTES.authentifier(nom, d.get("ancien")):
        return web.json_response({"erreur": "ancien mot de passe incorrect"},
                                 status=403)
    try:
        COMPTES.changer_mdp(nom, d.get("nouveau"))
    except _comptes.ErreurCompte as e:
        return web.json_response({"erreur": str(e)}, status=400)
    return web.json_response({"ok": True})


async def api_admin_comptes(req):
    if not admin_ok(req):
        return web.json_response({"erreur": "jeton invalide"}, status=403)
    return web.json_response({"comptes": COMPTES.liste(),
                              "mdp_minimum": _comptes.MDP_MINIMUM})


async def api_admin_compte_poser(req):
    """Creer un compte, changer son mot de passe, ou son role."""
    if not admin_ok(req):
        return web.json_response({"erreur": "jeton invalide"}, status=403)
    try:
        d = await req.json()
    except Exception:
        return web.json_response({"erreur": "corps illisible"}, status=400)
    nom = str(d.get("nom") or "")
    try:
        if d.get("creer"):
            COMPTES.creer(nom, str(d.get("mdp") or ""), bool(d.get("admin")))
        else:
            if d.get("mdp"):
                COMPTES.changer_mdp(nom, str(d.get("mdp")))
            if "admin" in d:
                COMPTES.changer_role(nom, bool(d.get("admin")))
    except _comptes.ErreurCompte as e:
        return web.json_response({"erreur": str(e)}, status=400)
    return web.json_response({"ok": True, "comptes": COMPTES.liste()})


async def api_admin_compte_supprimer(req):
    if not admin_ok(req):
        return web.json_response({"erreur": "jeton invalide"}, status=403)
    nom = req.match_info["nom"]
    try:
        COMPTES.supprimer(nom)
    except _comptes.ErreurCompte as e:
        return web.json_response({"erreur": str(e)}, status=400)
    # Les conversations du compte ne sont pas effacees : supprimer un acces
    # n'est pas supprimer un travail. Elles deviennent orphelines et restent
    # sur le disque, recuperables.
    perdu = _comptes.identifiant(nom)
    for conv in CONVERSATIONS.values():
        if conv.get("proprietaire") == perdu:
            conv["proprietaire"] = None
            sauver(conv)
    return web.json_response({"ok": True, "comptes": COMPTES.liste()})


async def api_fournisseurs(req):
    """Ce que l'interface a besoin de savoir : qui est disponible, et ou l'on va.

    Aucune cle, aucun indice de cle : cette route n'est pas protegee, elle sert
    a afficher un bandeau a tout le monde.
    """
    dit = {}
    for modalite, libelle, _ in MODALITES:
        choix = CHOIX.get(modalite, "local")
        conf = fournisseurs_de(modalite).get(choix) or {}
        cle = cle_de(choix) or (cle_de("google") if choix in _PAR_GOOGLE else "")
        dit[modalite] = {"libelle": libelle, "choix": choix,
                         "titre": conf.get("titre", "local"),
                         "distant": choix != "local" and bool(cle)}
    return web.json_response(dit)


def _mesurer_aiguilleur():
    """Entraine, ecrit, et rend la mesure. Bloquant : appele dans un fil."""
    import importlib

    entrainer = importlib.import_module("entrainer_aiguilleur")
    importlib.reload(entrainer)
    # corpus() rend desormais (exemples, du_reel) : le drapeau dit si des
    # demandes de CETTE installation sont entrees dans le melange. Ne pas le
    # lire faisait passer un tuple a apprendre() — le bouton « reentrainer »
    # rendait une erreur 500 a chaque clic.
    exemples, du_reel = entrainer.corpus()
    neuf = _aiguilleur.Aiguilleur().apprendre(exemples)
    # TOUJOURS le modele local, meme sans demande reelle : ce bouton entraine
    # POUR cette installation, il n'a aucune raison de toucher au modele publie.
    # Gele par PyInstaller, ce dernier vit d'ailleurs dans un dossier temporaire
    # efface a l'arret : y ecrire degradait le modele en memoire — 7 890 traits
    # tombes a 7 680 — au profit d'un fichier que personne ne relirait.
    neuf.ecrire(_aiguilleur.MODELE_LOCAL)
    bancs = []
    for nom in entrainer.BANCS:
        banc = entrainer._lire(nom)
        if not banc:
            continue
        bons, total, bons_surs, surs = entrainer.mesurer(neuf, banc)
        bancs.append({"nom": nom, "justes": bons, "total": total,
                      "justes_surs": bons_surs, "surs": surs})
    par = {}
    for x in exemples:
        par[x["intention"]] = par.get(x["intention"], 0) + 1
    return {"exemples": len(exemples), "traits": neuf.vocabulaire,
            "classes": par, "bancs": bancs}


async def api_admin_aiguilleur(req):
    """Etat de l'aiguilleur, et reentrainement a la demande."""
    if not admin_ok(req):
        return web.json_response({"erreur": "jeton invalide"}, status=403)
    global AIGUILLEUR
    if req.method == "POST":
        try:
            rendu = await asyncio.get_event_loop().run_in_executor(
                None, _mesurer_aiguilleur)
        except Exception as e:
            return web.json_response(
                {"erreur": f"entrainement impossible : {e}"}, status=500)
        # Recharge depuis le disque : le studio doit se servir de ce qui vient
        # d'etre ecrit, pas d'un objet garde en memoire.
        AIGUILLEUR = _aiguilleur.charger()
        rendu["ok"] = True
        return web.json_response(rendu)
    return web.json_response({
        "present": bool(AIGUILLEUR),
        "classes": (AIGUILLEUR.classes if AIGUILLEUR else {}),
        "traits": (AIGUILLEUR.vocabulaire if AIGUILLEUR else 0),
        "sans_ecriture": list(SANS_ECRITURE),
    })


async def api_admin_avis(req):
    if not admin_ok(req):
        return web.json_response({"erreur": "jeton invalide"}, status=403)
    tous = lire_avis(400)
    return web.json_response({
        "avis": tous,
        "pouces": {"haut": sum(1 for a in tous if a.get("avis") == 1),
                   "bas": sum(1 for a in tous if a.get("avis") == -1)},
    })


def enregistrer_tour(conv, tid, texte, plan, intention, cle, sorties, etat, erreur=None):
    """Ecrit le tour, ou met a jour celui qui porte deja cet identifiant.

    Mise a jour et non ajout : le tour est cree des la mise en file, pour que la
    demande reste visible pendant le rendu. L'ecrire deux fois afficherait la
    demande en double.
    """
    tour = {
        "id": tid, "heure": time.strftime("%H:%M"), "demande": texte,
        "prompt": (plan or {}).get("prompt"), "modele": cle, "type": intention,
        "parametres": (plan or {}).get("parametres"), "raison": (plan or {}).get("raison"),
        "fichiers": sorties or [], "description": TACHES.get(tid, {}).get("description"),
        "etat": etat, "erreur": erreur,
        # Les paroles ne sont ni le prompt ni la description : sans elles, un
        # pouce en bas sur une chanson ne dirait pas ce qui a deplu.
        "paroles": (plan or {}).get("paroles"),
        "questions": TACHES.get(tid, {}).get("questions"),
        "avis": 0, "note": "",
    }
    for i, ancien in enumerate(conv["tours"]):
        if ancien.get("id") == tid:
            # L'avis eventuellement pose ne doit pas etre efface par la mise a
            # jour : il appartient a l'utilisateur, pas au deroulement.
            tour["avis"] = ancien.get("avis", 0)
            tour["note"] = ancien.get("note", "")
            conv["tours"][i] = tour
            break
    else:
        conv["tours"].append(tour)
    conv["tours"] = conv["tours"][-60:]
    # le titre se fixe sur la premiere demande, comme dans une messagerie
    if conv["titre"] == "Nouvelle conversation" and texte:
        conv["titre"] = (texte[:46] + "…") if len(texte) > 46 else texte
    sauver(conv)

async def produire_distant(choix, plan, texte, entree, intention, tid, conv):
    """Demande le resultat au fournisseur et le depose la ou vont tous les autres.

    Le fichier atterrit dans output/studio comme une sortie de ComfyUI : tout
    ce qui suit — relais, proprietaire, purge, reprise pour une retouche —
    fonctionne alors sans rien savoir de son origine.
    """
    conf = MOTEURS_DISTANTS[choix]
    journal(tid, f"{conf['titre']} — envoi de la demande…")
    charge = None
    if entree:
        chemin = os.path.join(DOSSIER_ENTREE, entree)
        with open(chemin, "rb") as f:
            charge = (f.read(), mimetypes.guess_type(chemin)[0] or "image/png")
    if intention == "edition" and not charge:
        raise fournisseurs.EchecFournisseur("aucune image a modifier")
    if conf["type"] == "objet3d" and not charge:
        # La voie locale sait dessiner elle-meme une vue de reference avant de
        # sculpter ; Meshy, non. Plutot que d'inventer une image, on lui rend
        # la main.
        raise fournisseurs.EchecFournisseur(
            "aucune image de depart — depose une image, ou laisse le local "
            "dessiner d'abord une vue de reference")

    cle_api = cle_distante(choix)
    modele = modele_de(conf["fournisseur"]) or None
    debut = time.time()
    if conf["type"] == "audio":
        # Les paroles s'ecrivent ici et non plus bas : la branche locale qui
        # s'en charge d'ordinaire est en aval de cet aiguillage, et un morceau
        # chante partirait sans un mot.
        if not plan.get("paroles") and _CHANSON.search(texte or ""):
            duree = float((plan.get("parametres") or {}).get("duree_s", 60))
            plan["paroles"] = await ecrire_paroles(texte, duree, tid,
                                                   plan.get("langue") or "fr")
        # Le style et les paroles partent ensemble : ces modeles ne prennent
        # qu'un texte, contrairement a ACE-Step qui a deux champs distincts.
        morceaux = [style_musical(texte, plan.get("parametres")) or texte]
        if plan.get("paroles"):
            morceaux.append("Paroles a chanter :\n" + plan["paroles"])
        octets, mime = await fournisseurs.musique(conf["fournisseur"], cle_api,
                                                  "\n\n".join(morceaux), modele)
    elif conf["type"] == "objet3d":
        octets, mime = await fournisseurs.objet3d(
            conf["fournisseur"], cle_api, plan.get("prompt") or texte, modele,
            charge, tid=tid, dire=lambda m: journal(tid, m))
    elif conf["type"] == "video":
        octets, mime = await fournisseurs.video(
            conf["fournisseur"], cle_api, plan.get("prompt") or texte, modele,
            charge, tid=tid, dire=lambda m: journal(tid, m))
    else:
        octets, mime = await fournisseurs.image(conf["fournisseur"], cle_api,
                                                plan.get("prompt") or texte,
                                                modele, charge)
    ext = mimetypes.guess_extension(mime) or ".png"
    nom = f"{time.strftime('%Y%m%d')}_{choix}_{uuid.uuid4().hex[:8]}{ext}"
    # Meme rangement que les sorties calculees ici : ce qui vient d'un
    # fournisseur distant n'a aucune raison d'atterrir ailleurs, sinon la moitie
    # des images d'une personne serait dans son dossier et l'autre a cote.
    sous = os.path.dirname(prefixe_sortie(conv, intention, "", ""))
    # Sans ComfyUI sur cette machine, son output n'existe pas : le resultat
    # atterrit dans le depot du studio, la meme ou arrivent ceux des machines a
    # agent. Le lire fonctionne pareil ; c'est verifie a la lecture.
    if output_comfy_a_nous():
        dossier = os.path.join(BASE_COMFY, "output", *sous.split("/"))
    else:
        # noeud_local() a un identifiant que nous fabriquons : _sous() ne peut
        # pas le refuser. On reste explicite plutot que d'en dependre.
        depose = chemin_agent(noeud_local()["id"], nom)
        if not depose:
            raise RuntimeError(f"nom de fichier refuse : {nom}")
        dossier = os.path.dirname(depose)
    os.makedirs(dossier, exist_ok=True)
    with open(os.path.join(dossier, nom), "wb") as f:
        f.write(octets)
    journal(tid, f"recu en {time.time() - debut:.0f} s ({len(octets) / 1024:.0f} ko)")
    return [{"filename": nom, "subfolder": sous, "type": "output",
             "noeud": noeud_local()["id"]}]


# Le nom du type dans l'arborescence. On garde le mot de l'intention, sauf la
# ou il serait obscur pour qui parcourt le disque.
_DOSSIER_TYPE = {"video_image": "video", "personnage": "image",
                 "lecture": "lecture"}


def dossier_utilisateur(pid):
    """Le dossier de sortie de cette personne.

    Le nom du compte s'il y en a un — « Hogun974/image » se retrouve a l'oeil,
    trente-deux caracteres hexadecimaux non. Les noms de compte sont deja
    contraints par NOM_VALIDE a des lettres, chiffres, point, tiret et
    souligne : rien qui permette de remonter d'un dossier.
    """
    if COMPTES:
        for c in COMPTES.gens.values():
            if _comptes.identifiant(c["nom"]) == pid:
                return c["nom"]
    return (pid or "anonyme")[:32] or "anonyme"


def prefixe_sortie(conv, intention, horod, suffixe):
    """output/<utilisateur>/<type>/<horodatage>_<suffixe>.

    ComfyUI cree les sous-dossiers manquants tout seul, et rend le
    sous-dossier employe dans son historique : le studio n'a rien a retenir de
    plus pour relire le fichier ensuite.
    """
    qui_ = dossier_utilisateur(conv.get("proprietaire"))
    type_ = _DOSSIER_TYPE.get(intention, intention or "divers")
    return f"{qui_}/{type_}/{horod}_{suffixe}"


async def executer(tid, texte, conv, image=None, modele_force=None, taille=None,
                   priorite="", noeud_force=None):
    try:
        # Le tour a deja ete pose a la mise en file ; on le rafraichit pour
        # qu'il porte l'heure du debut reel du travail.
        enregistrer_tour(conv, tid, texte, {}, None, None, [], "en cours")
        garde_fou(texte)
        img_b64 = None
        if image and famille_du_fichier(image) == "image":
            with open(os.path.join(DOSSIER_ENTREE, image), "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()

        # Un moteur distant ne remplace pas un moteur du catalogue : il detourne
        # la seule production. On aiguille donc normalement, avec le moteur local
        # qui lui servira de repli — le prompt, la traduction et les paroles se
        # preparent exactement pareil.
        force_loin = modele_force if modele_force in MOTEURS_DISTANTS else None
        if force_loin:
            modele_force = MOTEURS_DISTANTS[force_loin]["repli"]

        # « quoi » plutot que « oui/non » : la suite du raisonnement n'est pas la
        # meme selon qu'on a joint une image, une video ou un morceau.
        plan = await aiguiller(texte, tid, conv, img_b64,
                               a_une_image=(famille_du_fichier(image) if image
                                            else False),
                               modele_force=modele_force, taille=taille,
                               priorite=priorite)
        if modele_force:
            plan["modele"] = modele_force
            plan["modele_impose"] = True
            plan["intention"] = CATALOGUE[modele_force]["type"]
            plan["raison"] = ("moteur distant impose depuis l'interface"
                              if force_loin else "modele impose depuis l'interface")
            # Les reglages techniques proposes par le LLM valaient pour le modele
            # QU'IL avait choisi. Quand l'utilisateur en impose un autre, ses
            # defauts a lui doivent primer ; on ne garde que les intentions de
            # l'utilisateur (tempo, duree, nombre d'images…).
            brut = dict(plan.get("parametres_bruts") or {})
            for technique in ("etapes", "cfg"):
                brut.pop(technique, None)
            plan["parametres_bruts"] = brut
            plan = appliquer_parametres(plan)
            # Le plan initial pouvait viser une autre modalite (audio, video) :
            # dans ce cas caler_taille() n'avait jamais tourne et le plan n'a ni
            # largeur ni hauteur. On les etablit maintenant.
            if plan["intention"] == "image":
                plan = caler_taille(plan, texte, taille)
        intention = plan.get("intention", "image")
        if intention == "refus":
            raise RuntimeError(plan.get("raison") or "demande refusee")
        if intention == "question":
            qs = plan.get("questions") or []
            if isinstance(qs, str):
                qs = [q.strip() for q in re.split(r"[|;?\n]+", qs) if len(q.strip()) > 8]
            # « ok », « Qu  » ou « Est quoi ? » ne sont pas des questions : sur les
            # demandes tres pauvres, le modele degenere en fragments. On exige
            # trois mots, et on retombe sur des questions ecrites a la main
            # plutot que d'inventer un sujet a la place de l'utilisateur.
            qs = [q.strip() for q in qs
                  if isinstance(q, str) and len(q.strip()) > 12
                  and len(q.split()) >= 3][:3]
            # Repli seulement quand c'est NOUS qui avons impose la question : si
            # l'aiguilleur a dit « question » a tort sur une demande claire, on
            # doit pouvoir retomber sur l'execution plutot que de l'interroger.
            if not qs and plan.get("questions_forcees"):
                qs = list(QUESTIONS_SANS_SUJET)
            if qs:
                plan.pop("prompt_repli", None)
                TACHES[tid].update(etat="question", questions=qs, plan=plan)
                enregistrer_tour(conv, tid, texte, plan, "question", None, [], "question")
                journal(tid, "precision demandee : " + " / ".join(qs), etat="question")
                return
            # pas de question exploitable -> on execute. L'intention "question"
            # n'ayant pas de modele, il faut en choisir un avant de continuer.
            intention = plan["intention"] = "image"
            if plan.get("modele") not in CATALOGUE:
                plan["modele"] = secours(texte, bool(image))["modele"]
            plan = caler_taille(plan, texte, taille)
        # le prompt reecrit passe aussi la garde
        garde_fou(texte, plan.get("prompt"), plan.get("tags_audio"), plan.get("paroles"))
        # apres l'aiguillage ET l'eventuel modele impose : le moteur est arrete,
        # on sait donc si sa langue impose une traduction.
        if plan.pop("prompt_repli", False):
            journal(tid, "prompt non enrichi par le modele — ta demande est reprise telle quelle")
        # la lecture d'image n'utilise pas le prompt : la traduire couterait
        # un appel Ollama complet pour rien.
        # Ni "lecture" ni "agrandir" n'envoient de texte a un moteur : traduire
        # couterait un appel complet pour un champ que personne ne lira.
        if plan.get("intention") not in ("lecture", "agrandir", "detourer",
                                         "fluidifier"):
            # Enrichir AVANT de traduire : traduire une demande de six mots
            # rendrait six mots anglais, et le moteur n'aurait toujours rien a
            # se mettre sous la dent.
            plan = await enrichir(plan, texte, tid)
            plan = await traduire(plan, tid)
        cle = plan["modele"]

        # Le studio n'a pas su preparer la demande : plutot que de l'envoyer
        # telle quelle et de laisser decouvrir le probleme dans le rendu, on
        # demande — en disant ce que CE moteur attend.
        if plan.get("enrichissement_rate") and not _deja_demande(conv):
            garde = mise_en_garde(cle)
            titre = CATALOGUE.get(cle, {}).get("titre", cle)
            qs = [f"Je n'ai pas reussi a etoffer ta demande : je l'enverrais "
                  f"telle quelle a {titre}."]
            if garde:
                qs.append(f"A savoir : {garde}")
            qs.append("Tu preferes la reecrire toi-meme, ou j'envoie tel quel ?")
            plan["attente"] = "tel_quel"
            TACHES[tid].update(etat="question", questions=qs, plan=plan)
            enregistrer_tour(conv, tid, texte, plan, "question", None, [], "question")
            journal(tid, "demande d'accord avant d'envoyer la demande telle quelle",
                    etat="question")
            return

        # Le meme personnage qu'avant : la reference est celle qu'on a retenue,
        # sinon la derniere image produite. On la retient au passage, pour que
        # les « le meme, mais... » suivants n'aient plus rien a designer.
        reference = None
        # « le meme personnage, au bord de la mer » decrit une scene neuve, pas
        # une retouche — l'aiguilleur y lit pourtant une edition une fois sur
        # deux. Les mots de l'utilisateur tranchent.
        if intention == "edition" and veut_meme_personnage(texte):
            intention = plan["intention"] = "image"
            plan["modele"] = "klein4b"
            # Les reglages proposes valaient pour le moteur d'edition : les
            # garder imposerait quatre etapes a une scene entiere.
            brut = dict(plan.get("parametres_bruts") or {})
            for technique in ("etapes", "cfg"):
                brut.pop(technique, None)
            plan["parametres_bruts"] = brut
            plan = appliquer_parametres(plan)
            plan = caler_taille(plan, texte, taille)
            journal(tid, "meme personnage : image neuve plutot que retouche")
        if intention == "image" and veut_meme_personnage(texte):
            source = conv.get("personnage") or conv.get("derniere_sortie")
            if source:
                reference = await recuperer_sortie(source, conv.get("proprietaire"))
                conv["personnage"] = dict(source)
                journal(tid, "meme personnage : la reference est reprise de "
                             f"{source.get('filename')}")
            else:
                journal(tid, "aucun personnage en memoire — image produite sans reference")

        # une modification sans image explicite reprend la derniere sortie
        if intention == "fluidifier" and not image and conv.get("derniere_video"):
            image = await recuperer_sortie(conv["derniere_video"],
                                           conv.get("proprietaire"))
            journal(tid, f"reprise de la video precedente : {image}")
        if intention in ("edition", "video_image", "agrandir", "detourer") \
                and not image and conv.get("derniere_sortie"):
            image = await recuperer_sortie(conv["derniere_sortie"], conv.get("proprietaire"))
            journal(tid, f"reprise de l'image precedente : {image}")

        if intention == "lecture":
            journal(tid, f"lecture de l'image par {MODELE_VISION}…")
            try:
                desc = await appeler_ollama(
                    texte or "Decris cette image en francais, precisement.",
                    img_b64, "Tu decris des images avec precision, en francais.",
                    json_mode=False, modele=MODELE_VISION, tid=tid)
            except Exception as e:
                raise RuntimeError(
                    f"le modele de vision « {MODELE_VISION} » n'a pas repondu ({type(e).__name__}). "
                    f"Verifie qu'il est installe : ollama pull {MODELE_VISION}") from None
            if not desc.strip():
                raise RuntimeError(f"« {MODELE_VISION} » n'a rien renvoye.")
            TACHES[tid].update(etat="fini", description=desc, plan=plan)
            enregistrer_tour(conv, tid, texte, plan, "lecture", cle, [], "fini")
            journal(tid, "description produite", etat="fini")
            return

        # Une taille choisie n'a de sens que la ou elle s'applique. Si la
        # demande part ailleurs, on le DIT : ignorer un reglage en silence
        # donne le sentiment de ne pas etre ecoute.
        if taille and intention not in ("image", "planche"):
            usage = {"edition": "la taille vient de l'image d'origine",
                     "video": "la taille est celle du format video",
                     "video_image": "la taille vient de l'image animee",
                     "objet3d": "un maillage n'a pas de resolution",
                     "audio": "un son n'a pas de resolution",
                     "lecture": "il n'y a rien a produire"}.get(intention, "")
            journal(tid, f"taille {taille} sans effet ici : {usage}")

        # Production confiee a un fournisseur. Passe avant le choix d'une
        # machine : il n'y a ni carte a reserver ni modele a telecharger.
        # Deux origines possibles : le moteur choisi dans la liste, ou le
        # reglage global quand rien n'est impose.
        loin = force_loin or ("" if plan.get("modele_impose")
                              else choix_distant(intention, texte, plan,
                                                 conv.get("proprietaire")))
        if loin and adulte(texte, plan):
            # Le dire, plutot que de basculer en silence : l'utilisateur a choisi
            # un fournisseur distant, il doit savoir pourquoi il n'est pas suivi.
            journal(tid, "contenu adulte : la generation reste sur cette machine")
            plan["raison"] = "contenu adulte : repli sur le moteur local"
            loin = ""
        if loin and not moteur_distant_pret(loin):
            journal(tid, f"aucune cle pour {loin} — calcul en local")
            plan["raison"] = "cle absente : repli sur le moteur local"
            loin = ""
        if loin:
            # Le dire AVANT l'appel : c'est la seule trace qui distingue « parti
            # au loin » de « reste ici », et son absence a rendu un aiguillage
            # muet impossible a diagnostiquer autrement qu'en lisant le code.
            journal(tid, f"confie a {MOTEURS_DISTANTS[loin]['titre']}…")
            try:
                sorties = await produire_distant(loin, plan, texte, image,
                                                 intention, tid, conv)
            except fournisseurs.EchecFournisseur as e:
                journal(tid, f"{MOTEURS_DISTANTS[loin]['titre']} indisponible "
                             f"({e}) — calcul en local")
                plan["raison"] = f"{MOTEURS_DISTANTS[loin]['titre']} a echoue : repli local"
            else:
                TACHES[tid]["fichiers"] = sorties
                if intention in ("image", "edition"):
                    conv["derniere_sortie"] = {"noeud": sorties[0]["noeud"],
                                               "filename": sorties[0]["filename"],
                                               "subfolder": sorties[0]["subfolder"]}
                plan["parametres"] = {"fournisseur": MOTEURS_DISTANTS[loin]["titre"]}
                enregistrer_tour(conv, tid, texte, plan, intention, cle, sorties, "fini")
                journal(tid, "resultat recu", etat="fini")
                return

        besoin = CATALOGUE[cle].get("vram", 0)
        # Machine imposee depuis l'interface : on respecte le choix, mais on
        # verifie qu'elle repond — sinon le travail attendrait indefiniment.
        cible = None
        if noeud_force:
            cible = noeud(noeud_force)
            titre_force = (cible or {}).get("titre", noeud_force)
            if cible and not ETAT_NOEUDS.get(noeud_force, {}).get("repond"):
                raise RuntimeError(f"{titre_force} ne repond pas")
            # Le choix automatique passe par noeuds_pour(), qui ecarte une
            # machine distante a qui il manque le modele — le studio n'ecrit que
            # sur son propre disque et ne peut pas l'y poser. Le choix impose
            # depuis l'interface contournait ce filtre : le graphe partait quand
            # meme, et ComfyUI rendait une erreur de chargeur que personne ne
            # savait lire. On refuse ici, en nommant les machines qui l'ont.
            if cible and not cible.get("local") and manquants(cle, noeud_force):
                # Un moteur EQUIVALENT que cette machine sait executer, plutot
                # qu'un refus. Choisir une machine, c'est vouloir epargner
                # l'autre : la renvoyer sur celle qu'on evitait annulerait le
                # choix, mais echouer alors qu'un moteur du meme type est
                # disponible ici ne sert personne.
                #
                # Meme « type » seulement — une demande d'image ne se rend pas
                # en video. La VRAM la plus proche par le haut : c'est le moteur
                # le plus capable que cette carte tienne.
                genre = CATALOGUE[cle].get("type")
                possibles = [c for c in CATALOGUE
                             if CATALOGUE[c].get("type") == genre
                             and not manquants(c, noeud_force)
                             and _vram_utile(noeud_force) >= CATALOGUE[c].get("vram", 0)]
                if possibles:
                    neuf_cle = max(possibles, key=lambda c: CATALOGUE[c].get("vram", 0))
                    journal(tid, f"{titre_force} n'a pas {CATALOGUE[cle]['titre']} — "
                                 f"{CATALOGUE[neuf_cle]['titre']} a sa place, "
                                 f"puisque c'est cette machine qui est demandee")
                    cle = neuf_cle
                    plan["modele"] = cle
                    # « besoin » a ete calcule au-dessus, pour l'ancien moteur :
                    # le laisser tel quel ferait juger la carte sur une exigence
                    # qui n'est plus la sienne.
                    besoin = CATALOGUE[cle].get("vram", 0)
                else:
                    ailleurs = [x.get("titre", x["id"]) for x in noeuds_pour(cle)]
                    raise RuntimeError(
                        f"{titre_force} n'a aucun moteur d'{genre} installe — "
                        + (f"a demander a {' ou '.join(ailleurs)}, ou laisser la "
                           f"machine sur « automatique »" if ailleurs else
                           "et aucune autre machine n'en a non plus"))
        cible = cible or choisir_noeud(cle)
        if cible is None:
            # Trois causes distinctes, trois messages : accuser la carte quand
            # c'est ComfyUI qui ne repond pas envoie chercher au mauvais endroit.
            # tous_les_noeuds() et non NOEUDS : sur un studio sans carte, ce
            # dernier ne contient que la machine locale, qui ne repond jamais.
            # Le message accusait donc ComfyUI pendant que deux machines
            # tournaient.
            vivantes = [x for x in tous_les_noeuds()
                        if ETAT_NOEUDS.get(x["id"], {}).get("repond")]
            if not vivantes:
                # Le bon geste n'est pas le meme selon le montage. Sur une
                # machine sans carte, il n'y a PAS de ComfyUI a demarrer : la
                # reponse est de declarer une machine dans /admin. Envoyer tout
                # le monde verifier un ComfyUI inexistant a ete releve comme le
                # message le plus decourageant d'une installation neuve.
                if output_comfy_a_nous():
                    raise RuntimeError(
                        "ComfyUI ne repond pas — est-il demarre ?"
                        + (" Les machines declarees non plus : leur agent "
                           "tourne-t-il ?" if REGISTRE else ""))
                if REGISTRE:
                    # Des machines sont declarees mais aucune ne s'annonce :
                    # c'est leur agent qu'il faut regarder, pas un ComfyUI qui
                    # n'existe pas ici.
                    raise RuntimeError(
                        "cette machine n'a pas de ComfyUI, et aucune des "
                        "machines declarees ne repond : leur agent tourne-t-il ? "
                        "L'etat de chacune est dans /admin.")
                raise RuntimeError(
                    "cette machine n'a pas de ComfyUI, et aucune machine a "
                    "carte n'est declaree. Ajoutes-en une dans /admin : elle "
                    "viendra chercher le travail d'elle-meme, sans rien ouvrir "
                    "sur le reseau.")
            if not any(x.get("local") for x in vivantes):
                # Des machines repondent, mais aucune ne convient a ce moteur.
                # Le dire, plutot que d'accuser un ComfyUI qui va tres bien.
                noms = ", ".join(x.get("titre", x["id"]) for x in vivantes)
                raise RuntimeError(
                    f"{CATALOGUE[cle]['titre']} n'est disponible sur aucune "
                    f"machine joignable ({noms}) : modele absent, ou carte trop "
                    f"petite. Le detail est dans /admin, en ouvrant la machine.")
            cible = noeud_local()
            dispo = vram_de(cible["id"])
            if besoin > dispo:
                grosse = max((vram_de(x["id"]) for x in NOEUDS), default=0.0)
                detail = (f"la plus grosse carte joignable en a {grosse}, mais il lui "
                          f"manque le modele" if grosse >= besoin else
                          f"la carte n'en a que {dispo}")
                raise RuntimeError(f"{CATALOGUE[cle]['titre']} reclame {besoin} Go de "
                                   f"VRAM : {detail}.")
        ident = cible["id"]
        # Retenu sur la tache : sans cela, interrompre un rendu frappait a la
        # porte de la machine du studio, qui n'est pas forcement celle qui
        # calcule — et ne l'est plus du tout sur un studio sans carte.
        TACHES[tid]["noeud"] = ident
        if len(NOEUDS) > 1:
            journal(tid, f"machine retenue : {cible.get('titre', ident)}")
        if not tient_vraiment(cle, ident):
            e = ETAT_NOEUDS.get(ident) or {}
            journal(tid, f"{CATALOGUE[cle]['titre']} demande "
                         f"{CATALOGUE[cle].get('vram', 0)} Go et la carte en offre "
                         f"{e.get('vram')} : debordement sur la RAM, plus lent")
        journal(tid, f"{CATALOGUE[cle]['titre']} — {plan.get('raison','')}", plan=plan)
        # Le telechargement n'est possible que sur le disque du studio : un noeud
        # distant s'approvisionne a la main, et reste inelegible en attendant.
        a_prendre = manquants(cle, ident) if cible.get("local") else []
        for sous, nom, repo, distant in a_prendre:
            # Un verrou par FICHIER : deux demandes qui reclament le meme modele
            # se le partageraient sinon, chacune avec son propre Range sur le
            # meme .part. La seconde trouve le fichier deja la et ressort aussitot
            # — telecharger() sort sur « os.path.exists(cible) ».
            async with verrou_modele(sous, nom):
                await asyncio.get_event_loop().run_in_executor(
                    None, telecharger, sous, nom, repo, distant, tid)
        if a_prendre:
            MODELES_NOEUD.pop(ident, None)      # le cache ne connait pas l'arrivant

        seed = int.from_bytes(os.urandom(4), "big") % (2**31)
        # Le compteur de ComfyUI (_00001_, _00002_…) repart de zero SUR CHAQUE
        # MACHINE : deux noeuds produiraient le meme nom le meme jour, et le
        # relais servirait silencieusement l'image de l'autre. L'identifiant du
        # noeud entre donc dans le prefixe des qu'il y en a plus d'un.
        # L'image d'entree vit dans le cache local du studio. La machine qui
        # execute doit l'avoir dans SON input : on la lui envoie si ce n'est pas
        # la meme machine. Sans image, il n'y a rien a faire.
        if image:
            image = await pousser_entree(image, ident, tid)
        if reference:
            # La machine qui calcule doit avoir la reference dans SON input :
            # sans cela, un noeud distant chercherait un fichier qui n'existe
            # que sur le studio.
            reference = await pousser_entree(reference, ident, tid)
        horod = time.strftime("%Y%m%d") + ("" if len(NOEUDS) < 2 else f"_{ident}")
        par = plan.get("parametres") or {}
        if par:
            journal(tid, "reglages : " + ", ".join(f"{k}={v}" for k, v in par.items()))
        if plan.get("parametres_ajustes"):
            journal(tid, "bornes appliquees : " + ", ".join(plan["parametres_ajustes"]))
        neg = plan.get("negatif") or NEG_DEFAUT

        if intention == "fluidifier":
            if not image:
                raise RuntimeError(
                    "aucune video a traiter : demande-le juste apres en avoir "
                    "produit une.")
            fps0, images0 = cadence_de(image)
            mult = 2
            ralenti = veut_ralenti(texte)
            fps = fps0 if ralenti else fps0 * mult
            g = g_fluidite(image, prefixe_sortie(conv, intention, horod, "fluide"), mult, fps)
            journal(tid, f"{images0} images a {fps0:.0f} im/s -> "
                         f"{(images0 - 1) * mult + 1} a {fps:.0f} im/s"
                         + (" (ralenti : deux fois plus long)" if ralenti
                            else " (meme duree, plus fluide)"))
        elif intention == "retoucher_zone":
            if not image:
                raise RuntimeError(
                    "aucune image a retoucher : depose une image, ou demande-le "
                    "juste apres en avoir produit une.")
            # Les dimensions se lisent dans le fichier, une fois : elles
            # bornent la taille — une entree de 4000 px a tue ComfyUI — et
            # alignent le recollage sur un multiple de 16, sans quoi le VAE
            # recadre de son cote et laisse une bande au bas de l'image.
            chemin_src = os.path.join(DOSSIER_ENTREE, os.path.basename(image))
            cadre_l, cadre_h, reduite = cadrage_source(chemin_src)
            cadre = (cadre_l, cadre_h) if cadre_l else None
            if reduite:
                journal(tid, f"image ramenee a {cadre_l}x{cadre_h} : au-dela, le "
                             f"decodeur bloque ComfyUI plusieurs minutes. "
                             f"L'image entiere est donc reechantillonnee.")
            cible, region, zone = await preparer_cible(texte, tid)
            if not cible:
                raise RuntimeError(
                    "je n'arrive pas a determiner quoi selectionner. Nomme la "
                    "zone et ce qu'elle doit devenir — par exemple « remplace le "
                    "ciel par un ciel d'orage ».")
            plan["prompt"] = zone
            journal(tid, f"zone visee : « {cible} » "
                         f"({'etendue' if region else 'objet'}) — a la place : {zone[:60]}")
            aire, etapes = await mesurer_puis_choisir(image, tid, cle,
                                                      cible=cible, region=region,
                                                      cadre=cadre, reduite=reduite)
            if aire is not None:
                journal(tid, f"le masque couvre {aire * 100:.1f} % de l'image")
                if aire > AIRE_TOTALE:
                    # « Hors du masque, l'image est recollee a l'identique » est
                    # vrai et vide s'il n'y a aucun pixel hors du masque. Le
                    # dire, plutot que de laisser croire a une retouche fine.
                    journal(tid, "cette zone couvre presque tout : le resultat "
                                 "sera une image neuve, pas une retouche locale")
                if aire < AIRE_MINIMALE:
                    # Le dire tout de suite, en nommant ce qu'on a cherche :
                    # quinze secondes pour rendre l'image inchangee ressemblent
                    # a une panne, et n'apprennent rien.
                    raise RuntimeError(
                        f"je n'ai pas trouve « {cible} » dans cette image. "
                        f"Nomme autrement ce qu'il faut changer, ou decris-le "
                        f"plus simplement.")
                par = dict(par or {}, etapes=etapes)
                if etapes > REGLAGES["edition"]["etapes"]:
                    journal(tid, f"grande zone : {etapes} etapes au lieu de "
                                 f"{REGLAGES['edition']['etapes']}, deux fois plus "
                                 f"long mais sans plaque floue")
            g = g_retouche_zone(zone, image, seed,
                                prefixe_sortie(conv, intention, horod, "retouche"),
                                par=par, cible=cible, region=region,
                                cadre=cadre, reduite=reduite)
            journal(tid, "retouche localisee — hors du masque, l'image est "
                         "recollee a l'identique")
        elif intention in ("retoucher_fond", "retoucher_sujet"):
            if not image:
                raise RuntimeError(
                    "aucune image a retoucher : depose une image, ou demande-le "
                    "juste apres en avoir produit une.")
            # Les dimensions se lisent dans le fichier, une fois : elles
            # bornent la taille — une entree de 4000 px a tue ComfyUI — et
            # alignent le recollage sur un multiple de 16, sans quoi le VAE
            # recadre de son cote et laisse une bande au bas de l'image.
            chemin_src = os.path.join(DOSSIER_ENTREE, os.path.basename(image))
            cadre_l, cadre_h, reduite = cadrage_source(chemin_src)
            cadre = (cadre_l, cadre_h) if cadre_l else None
            if reduite:
                journal(tid, f"image ramenee a {cadre_l}x{cadre_h} : au-dela, le "
                             f"decodeur bloque ComfyUI plusieurs minutes. "
                             f"L'image entiere est donc reechantillonnee.")
            zone = await decrire_zone(texte, tid)
            if not zone:
                raise RuntimeError(
                    "je n'arrive pas a decrire ce qu'il faut mettre a la place. "
                    "Dis-le en clair — par exemple « le fond devient une plage "
                    "au crepuscule » plutot que « change le fond ».")
            sur_le_sujet = intention == "retoucher_sujet"
            plan["prompt"] = zone
            journal(tid, f"zone a redessiner : {zone[:80]}")
            aire, etapes = await mesurer_puis_choisir(image, tid, cle,
                                                      sur_le_sujet=sur_le_sujet,
                                                      cadre=cadre, reduite=reduite)
            if aire is not None:
                journal(tid, f"le masque couvre {aire * 100:.1f} % de l'image")
                if aire > AIRE_TOTALE:
                    journal(tid, "cette zone couvre presque tout : le resultat "
                                 "sera une image neuve, pas une retouche locale")
                if aire < AIRE_MINIMALE:
                    raise RuntimeError(
                        "je ne distingue pas de sujet sur cette image : il n'y a "
                        "rien a separer du fond. Decris plutot ce que tu veux "
                        "changer, par exemple « change seulement le ciel ».")
                par = dict(par or {}, etapes=etapes)
            g = g_retouche_zone(zone, image, seed,
                                prefixe_sortie(conv, intention, horod, "retouche"),
                                sur_le_sujet, par, cadre=cadre, reduite=reduite)
            if not sur_le_sujet:
                journal(tid, "le fond occupe une grande part du cadre : "
                             "16 etapes au lieu de 4")
            journal(tid, "retouche localisee — hors du masque, l'image est "
                         "recollee a l'identique")
        elif intention == "detourer":
            if not image:
                raise RuntimeError(
                    "aucune image a detourer : depose une image, ou demande-le "
                    "juste apres en avoir produit une.")
            g = g_detourage(image, prefixe_sortie(conv, intention, horod, "detoure"))
            journal(tid, "detourage — le sujet est isole, le fond devient "
                         "transparent (PNG)")
        elif intention == "agrandir":
            if not image:
                raise RuntimeError(
                    "aucune image a agrandir : depose une image, ou demande-le "
                    "juste apres en avoir produit une.")
            facteur = facteur_demande(texte)
            g = g_agrandir(image, prefixe_sortie(conv, intention, horod, "agrandi"), facteur)
            journal(tid, f"agrandissement {facteur:.0f}x — le contenu n'est pas "
                         f"retouche, seule la definition monte")
        elif intention == "edition":
            if not image:
                raise RuntimeError("aucune image a modifier : depose une image d'abord.")
            g = g_edition(plan.get("prompt", texte), image, seed, prefixe_sortie(conv, intention, horod, "edition"), par)
            journal(tid, "modification en cours…")
        elif intention == "video":
            g = g_video(plan.get("prompt", texte), neg, seed, prefixe_sortie(conv, intention, horod, "video"), par)
            journal(tid, "video 1280x704, 49 images — compter environ 6 minutes…")
        elif intention == "video_image":
            if not image:
                raise RuntimeError("aucune image de depart pour l'animation.")
            g = g_video_image(plan.get("prompt", texte), neg, image, seed, prefixe_sortie(conv, intention, horod, "anim"), par)
            journal(tid, "animation 1280x704 — compter environ 12 minutes…")
        elif intention == "planche":
            # Une planche est un format page. On impose le portrait A4 (1:1.41)
            # sans quoi l'aiguilleur propose du carre et la mise en page tombe
            # a plat ; 832x1176 reste dans la plage native de SDXL.
            if taille in TAILLES:
                w, h = (int(x) for x in taille.split("x"))
            else:
                w = cadrer(plan.get("largeur"), 704, 960, 832)
                h = cadrer(w * 1.4142, 960, 1408, 1176)
            # Le LLM renvoie parfois "cases" en chaine au lieu d'une liste :
            # iterer dessus donnerait une case par CARACTERE.
            brutes = plan.get("cases")
            if isinstance(brutes, str):
                brutes = [m.strip() for m in re.split(r"[|;\n]+", brutes) if m.strip()]
            if not isinstance(brutes, list):
                brutes = []
            cases = [c.strip() for c in brutes
                     if isinstance(c, str) and len(c.strip()) >= 12][:6]
            if len(cases) >= 2:
                journal(tid, f"{len(cases)} cases dessinees et assemblees en un seul passage…")
                for i, c in enumerate(cases, 1):
                    journal(tid, f"  case {i} : {c[:66]}")
                neg_case = (neg + ", multiple panels, comic, grid, panel border, frame, "
                            "gutter, split screen, color, text, letters, words, signature")
                g = g_planche_composee(cases, neg_case, seed,
                                       prefixe_sortie(conv, intention, horod, "planche"),
                                       par.get("lora", 0.35),
                                       int(par.get("etapes", 28)),
                                       float(par.get("cfg", 7.0)))
            else:
                neg = (neg + ", single image, one panel, full page illustration, "
                       "seamless, no borders, color, text, letters, words, signature")
                g = g_planche(plan.get("prompt", texte), neg, w, h, seed,
                              prefixe_sortie(conv, intention, horod, "planche"), par)
                journal(tid, f"planche {w}x{h} d'un seul tenant, bulles vides…")
        elif intention == "objet3d":
            if not image:
                # « generation d'image puis image vers 3D » : on fabrique
                # d'abord une vue de reference, puis on la sculpte.
                journal(tid, "aucune image fournie — creation d'une vue de reference…")
                vue = g_image("klein4b", plan.get("prompt", texte)
                              + " Single object centred on a plain neutral background, "
                                "full view, even lighting, no shadows, product photo framing.",
                              NEG_DEFAUT, 1024, 1024, seed, prefixe_sortie(conv, intention, horod, "vue3d"),
                              "safe", {"etapes": 20, "cfg": 5.0})
                # La vue de reference merite la meme reprise que le reste :
                # perdre le maillage parce que ComfyUI est tombe a la premiere
                # des deux etapes serait absurde.
                fichiers_vue, _ = await soumettre_robuste(vue, tid, ident, "klein4b")
                if not fichiers_vue:
                    raise RuntimeError("la vue de reference n'a pas pu etre creee")
                image = await recuperer_sortie({"filename": fichiers_vue[0]["filename"],
                                          "noeud": fichiers_vue[0].get("noeud"),
                                          "subfolder": fichiers_vue[0].get("subfolder", "")},
                                         conv.get("proprietaire"))
                # la vue vient d'etre rapatriee dans le cache local : il faut la
                # renvoyer a la machine qui va sculpter le maillage
                image = await pousser_entree(image, ident, tid)
                journal(tid, f"vue de reference : {fichiers_vue[0]['filename']}")
            g = g_3d(image, seed, prefixe_sortie(conv, intention, horod, "maillage"), par)
            journal(tid, "sculpture du maillage — compter environ 3 minutes…")
        elif intention == "audio":
            # Les paroles ne viennent pas du plan : elles ont leur propre appel.
            chantee = bool(_CHANSON.search(texte or ""))
            if not plan.get("paroles") and chantee:
                duree = float((plan.get("parametres") or {}).get("duree_s", 60))
                plan["paroles"] = await ecrire_paroles(texte, duree, tid,
                                                       plan.get("langue") or "fr")
            if chantee and not plan.get("paroles"):
                # Rendre un instrumental laisserait croire que le modele audio
                # a ignore la demande, alors que c'est l'ecriture qui a lache :
                # dix minutes de calcul pour un fichier inutilisable.
                raise RuntimeError(
                    "les paroles n'ont pas pu etre ecrites — relance la demande, "
                    "ou precise le refrain que tu veux")
            # Ce que l'utilisateur nomme lui-meme prime sur ce que le routeur
            # propose : il a ecrit « rock, guitare, batterie, basse, piano »,
            # il n'y a rien a deviner.
            # Le tempo suit le genre, sauf si l'utilisateur a donne le sien :
            # « rock and roll » a 90 BPM traine, quels que soient les instruments.
            if par.get("bpm") == REGLAGES.get(cle, {}).get("bpm"):
                for genre in _trouves(sans_accents((texte or "").lower()), _GENRES):
                    if genre in _TEMPOS:
                        par["bpm"] = _TEMPOS[genre]
                        journal(tid, f"tempo du genre {genre} : {par['bpm']} BPM")
                        break
            style = style_musical(texte, par)
            if style:
                journal(tid, f"style lu dans la demande : {style}")
            elif _style_prose(plan.get("tags_audio")):
                journal(tid, "style propose inexploitable — il decrit l'histoire")
                style = ""
            else:
                style = plan.get("tags_audio")
            if not style:
                # Se rabattre sur le prompt enverrait l'HISTOIRE au lieu du STYLE :
                # c'est ainsi qu'une biographie a produit une musique sans rapport
                # avec le rock demande. Mieux vaut une consigne neutre.
                style = "A well-recorded song with clear vocals and a full band."
                journal(tid, "aucun style musical propose — consigne neutre utilisee")
            # La fiche de l'echange doit montrer ce qui a REELLEMENT ete envoye :
            # c'est sur elle que se fonde un pouce en bas.
            plan["tags_audio"] = plan["prompt"] = style
            source = image if image and famille_du_fichier(image) == "audio" else None
            g = g_audio(cle, style,
                        plan.get("paroles") or "", seed, prefixe_sortie(conv, intention, horod, "audio"),
                        plan.get("langue") or "en", plan.get("tonalite") or "C minor",
                        par, source)
            if source:
                # La duree vient de la latente d'entree, pas des reglages :
                # demander « fais-en trente secondes » sur un morceau d'une
                # minute rendrait une minute, et passerait pour une panne.
                journal(tid, f"retouche du morceau joint — sa duree est conservee, "
                             f"{par.get('etapes', 8)} etapes…")
            else:
                journal(tid, f"musique de {par.get('duree_s', 60):.0f} s a {par.get('bpm', 90)} BPM, "
                             f"{par.get('etapes', 8)} etapes…")
        elif reference:
            w, h = int(plan["largeur"]), int(plan["hauteur"])
            g = g_personnage(plan.get("prompt", texte), reference, w, h, seed,
                             prefixe_sortie(conv, "personnage", horod, "personnage"), par)
            journal(tid, f"generation {w}x{h} en gardant le personnage…",
                    largeur=w, hauteur=h)
        else:
            # caler_taille() a deja borne et preserve le ratio dans normaliser() ;
            # re-borner ici avec d'autres minimums casserait ce ratio.
            w, h = int(plan["largeur"]), int(plan["hauteur"])
            g = g_image(cle, plan.get("prompt", texte), neg, w, h, seed,
                        prefixe_sortie(conv, intention, horod, cle), plan.get("classement", "safe"), par)
            journal(tid, f"generation {w}x{h}…", largeur=w, hauteur=h)

        sorties, secondes = await soumettre_robuste(g, tid, ident, cle)
        TACHES[tid]["fichiers"] = sorties
        if sorties and intention in ("video", "video_image", "fluidifier"):
            # Les videos ont leur propre memoire : « agrandis-la » doit viser la
            # derniere IMAGE, « rends-la fluide » la derniere VIDEO.
            conv["derniere_video"] = {"noeud": sorties[0].get("noeud"),
                                      "filename": sorties[0]["filename"],
                                      "subfolder": sorties[0].get("subfolder", "")}
        if sorties and intention in ("image", "edition", "planche", "agrandir",
                                     "detourer"):
            # on garde le sous-dossier : il est indispensable pour retrouver le fichier
            conv["derniere_sortie"] = {"noeud": sorties[0].get("noeud"),
                                       "filename": sorties[0]["filename"],
                                       "subfolder": sorties[0].get("subfolder", "")}
        enregistrer_tour(conv, tid, texte, plan, intention, cle, sorties, "fini")
        journal(tid, f"termine en {secondes:.0f} s", etat="fini")
    except Exception as e:
        enregistrer_tour(conv, tid, texte, locals().get("plan") or {},
                         (locals().get("plan") or {}).get("intention"),
                         (locals().get("plan") or {}).get("modele"), [], "erreur", str(e))
        journal(tid, f"ERREUR : {e}", etat="erreur")

# ══════════════════════════════ routes ═════════════════════════════════
@web.middleware
async def identite(req, handler):   # aiohttp passe le second argument NOMME `handler`
    """Chaque navigateur recoit un identifiant opaque, sans compte ni mot de passe.

    Un cookie plutot qu'un en-tete : les images sont chargees par <img src>,
    qui n'envoie pas d'en-tete personnalise. Le cookie, lui, part tout seul —
    c'est la seule solution qui couvre aussi le proxy de fichiers.
    """
    pid = req.cookies.get("studio") or ""
    neuf = not _PID.fullmatch(pid)
    # Un compte connecte prime sur le cookie du navigateur : c'est ce qui fait
    # qu'on retrouve ses conversations depuis un autre appareil, et que deux
    # adresses du meme studio ne donnent plus deux historiques.
    nom = compte_de(req)
    if not neuf and not nom and COMPTES and COMPTES.est_espace_de_compte(pid):
        # L'espace d'un compte se calcule a partir du seul nom d'utilisateur
        # (voir est_espace_de_compte). Sans cette ligne, poser a la main le
        # cookie « studio » du compte « admin » donnait ses conversations et sa
        # mediatheque a un visiteur qui n'a jamais rien presente — pas en
        # STUDIO_AUTH=obligatoire, ou exiger_compte refuse tout, mais en
        # STUDIO_AUTH=libre, qui est un reglage documente.
        neuf = True
    if neuf:
        pid = uuid.uuid4().hex
    req["compte"] = nom
    req["pid"] = _comptes.identifiant(nom) if nom else pid
    rep_ = await handler(req)
    # req["pid"] et non pid : une connexion change l'identite en cours de route,
    # et le cookie pose doit etre celle-la, pas celle qu'on venait de tirer.
    if neuf or req["pid"] != pid:
        rep_.set_cookie("studio", req["pid"], max_age=10 * 365 * 24 * 3600,
                        httponly=True, samesite="Lax")
    return rep_

def qui(req):
    return req["pid"]


def local(req):
    hote = (req.transport.get_extra_info("peername") or ("",))[0] if req.transport else ""
    return hote in ADRESSES_MACHINE

async def page(req):
    # L'adoption se joue ici, et seulement ici : au chargement de l'interface,
    # depuis la machine qui heberge le studio. Un appel d'API ou un visiteur du
    # reseau ne peut pas s'attribuer l'historique par accident.
    # Seulement pour un visiteur qui presente DEJA un cookie valide, donc qui a
    # charge l'interface une premiere fois. Sans cela, un simple « curl / » ou un
    # apercu de lien attribuait tout l'historique a une identite jetable.
    if local(req) and _PID.fullmatch(req.cookies.get("studio") or ""):
        adopter(qui(req))
    return web.FileResponse(os.path.join(ICI, "web", "index.html"))

async def api_modeles(_):
    """Les moteurs locaux, puis ceux qu'une cle rend joignables.

    Un moteur distant sans cle n'est pas montre : proposer un choix qui echouera
    a coup sur ne rend service a personne.
    """
    liste = [dict(cle=c, titre=m["titre"], type=m["type"], pour=m["pour"],
                  duree=m["duree"], distant=False,
                  present=not manquants_partout(c)) for c, m in CATALOGUE.items()]
    liste += [dict(cle=c, titre=m["titre"], type=m["type"], pour=m["pour"],
                   duree=m["duree"], distant=True, present=True)
              for c, m in MOTEURS_DISTANTS.items() if moteur_distant_pret(c)]
    return web.json_response(liste)

EXT_IMAGE = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
EXT_VIDEO = {".mp4", ".webm", ".mkv", ".mov"}
EXT_AUDIO = {".mp3", ".wav", ".flac", ".ogg", ".opus", ".m4a"}

# Ce que le studio sait faire d'un fichier joint, par famille. On n'accepte que
# ce dont un moteur peut se servir : accepter un maillage pour le refuser
# ensuite serait une promesse rompue apres le temps de l'envoi.
FAMILLES = {
    "image": (EXT_IMAGE, 32 * 1024 ** 2),
    "video": (EXT_VIDEO, 512 * 1024 ** 2),
    "audio": (EXT_AUDIO, 64 * 1024 ** 2),
}


def famille_du_fichier(nom):
    """La famille d'un fichier d'apres son extension, ou "" si on n'en veut pas."""
    ext = os.path.splitext(nom or "")[1].lower()
    for famille, (extensions, _) in FAMILLES.items():
        if ext in extensions:
            return famille
    return ""

async def api_televerser(req):
    lecteur = await req.multipart()
    champ = await lecteur.next()
    if champ is None or not getattr(champ, "filename", None):
        return web.json_response({"erreur": "aucun fichier recu"}, status=400)
    ext = os.path.splitext(champ.filename)[1].lower()
    famille = famille_du_fichier(champ.filename)
    if not famille:
        acceptes = ", ".join(sorted(e for x, _ in FAMILLES.values() for e in x))
        return web.json_response(
            {"erreur": f"format non pris en charge ({ext or 'sans extension'}). "
                       f"Acceptes : {acceptes}"}, status=400)
    plafond = FAMILLES[famille][1]
    os.makedirs(DOSSIER_ENTREE, exist_ok=True)
    nom = f"studio_{uuid.uuid4().hex[:10]}{ext}"
    chemin = os.path.join(DOSSIER_ENTREE, nom)
    taille = 0
    with open(chemin, "wb") as f:
        while True:
            bloc = await champ.read_chunk()
            if not bloc: break
            taille += len(bloc)
            # On coupe pendant l'ecriture et non apres : un envoi de plusieurs
            # gigaoctets remplirait le disque avant d'etre refuse.
            if taille > plafond:
                f.close()
                os.remove(chemin)
                return web.json_response(
                    {"erreur": f"fichier trop lourd : {famille} limite a "
                               f"{plafond // 1024 ** 2} Mo"}, status=413)
            f.write(bloc)
    if taille == 0:
        os.remove(chemin)
        return web.json_response({"erreur": "fichier vide"}, status=400)
    ENTREES[nom] = qui(req)
    purger_entrees(pid=qui(req))
    sauver_entrees()
    return web.json_response({"image": nom, "octets": taille})

def _tid_sur(ident):
    """Le travail en vol confie a cette machine, s'il y en a un.

    Sert a la websocket du ComfyUI local, qui annonce une progression sans
    jamais nommer le travail : elle decrit sa machine, pas une demande. Rend le
    premier trouve — il n'y en aura jamais deux, le verrou par machine s'en
    chargera, et en attendant il n'y a de toute façon qu'un travail en vol.
    """
    for tid in EN_VOL:
        if (TACHES.get(tid) or {}).get("noeud") == ident:
            return tid
    return None


def purger_taches(garder=200):
    """TACHES ne se vidait jamais. Seul, l'utilisateur ne s'en apercevait pas ;
    a plusieurs le dict grossit d'autant plus vite. Les taches terminees ne
    servent qu'a l'affichage immediat : la conversation garde l'historique."""
    finies = [t for t, v in TACHES.items() if v.get("etat") in ("fini", "erreur")]
    for t in finies[:-garder]:
        TACHES.pop(t, None)

async def travailleur():
    """Un seul travail a la fois : le GPU ne se partage pas. Les demandes
    s'empilent, y compris celles venues d'autres conversations."""
    while True:
        job = await FILE_ATTENTE.get()
        tid = job["tid"]
        if tid in ATTENTE:
            ATTENTE.remove(tid)
        # Retirer de ATTENTE ne suffit pas : cette liste sert l'affichage, le
        # travail dort dans la file asyncio, qui ne se laisse pas fouiller. Sans
        # cette lecture, une demande « retiree » etait calculee quand meme et son
        # resultat surgissait bien plus tard.
        EN_FILE.pop(tid, None)
        sauver_file()
        if (TACHES.get(tid) or {}).get("annulee"):
            FILE_ATTENTE.task_done()
            continue

        # Une tache nommee plutot qu'un simple await : c'est le seul moyen
        # d'arreter un travail qui n'a pas encore atteint ComfyUI — analyse,
        # ecriture des paroles, attente d'un fournisseur.
        travail = asyncio.create_task(
            executer(tid, job["texte"], job["conv"], job["image"], job["modele"],
                     job.get("taille"), job.get("priorite", ""), job.get("noeud")))
        EN_VOL[tid] = travail
        try:
            await travail
        except asyncio.CancelledError:
            # Un « except » a elle seule : CancelledError n'est pas une
            # Exception, elle traverserait le filet ci-dessous et tuerait la
            # file entiere au premier retrait.
            conv = CONVERSATIONS.get((TACHES.get(tid) or {}).get("conversation"))
            if conv:
                enregistrer_tour(conv, tid, (TACHES.get(tid) or {}).get("demande", ""),
                                 {}, None, None, [], "erreur", "interrompue")
            # Le dernier mot revient a la machine quand c'est un agent qui
            # calcule : elle seule sait a quelle seconde sa carte s'est arretee,
            # et api_noeud_resultat l'ecrira a son retour. Poser « interrompue »
            # ici, c'etait l'ecrire pendant que le GPU du NAS tournait toujours.
            # ... a condition qu'elle puisse encore parler. Une machine deja
            # silencieuse ne rappellera pas : se taire ici laissait l'utilisateur
            # sur « sa carte s'arrete des qu'elle nous rappelle », au futur, pour
            # un rendu deja mort. La page relit une fois a huit secondes, ne
            # trouve rien de neuf, et abandonne sans rien dire.
            ident_t = (TACHES.get(tid) or {}).get("noeud") or ""
            if est_agent(ident_t) and ETAT_NOEUDS.get(ident_t, {}).get("repond"):
                TACHES.setdefault(tid, {"etapes": []}).update(etat="erreur")
            else:
                journal(tid, "interrompue", etat="erreur")
        except Exception as e:                       # filet : la file ne doit jamais mourir
            journal(tid, f"ERREUR inattendue : {e}", etat="erreur")
        finally:
            EN_VOL.pop(tid, None)
            # La progression d'une machine a agent n'a personne pour la remettre
            # a zero : le studio ecoute SA websocket, pas la sienne. Sans cette
            # ligne, la barre du travail suivant demarrait la ou le precedent
            # s'etait arrete.
            AVANCES.pop(tid, None)
            FILE_ATTENTE.task_done()
            purger_taches()

async def api_reprendre(req):
    """Remet une sortie deja produite dans le cache d'entree, et rend son nom.

    La page s'en sert pour « agrandir » : le fichier devient une piece jointe
    ordinaire, et toute la suite — envoi vers la machine qui calcule, controle
    de propriete — fonctionne sans rien savoir de son passe.
    """
    pid = qui(req)
    try:
        d = await req.json()
    except Exception:
        return web.json_response({"erreur": "corps illisible"}, status=400)
    nom = d.get("filename") or ""
    sous = d.get("subfolder") or ""
    ident = d.get("noeud") or noeud_local()["id"]
    # La meme autorisation que pour l'affichage : ni plus, ni moins.
    if noeud(ident) is None or (ident, sous, nom) not in mes_fichiers(pid):
        return web.json_response({"erreur": "inconnu"}, status=404)
    try:
        copie = await recuperer_sortie({"filename": nom, "subfolder": sous,
                                        "noeud": ident}, pid)
    except Exception as e:
        return web.json_response({"erreur": str(e)}, status=502)
    return web.json_response({"image": copie})


async def api_generer(req):
    try:
        d = await req.json()
    except Exception:
        return web.json_response({"erreur": "corps illisible"}, status=400)
    texte = (d.get("texte") or "").strip()
    image = d.get("image")
    if not texte and not image:
        return web.json_response({"erreur": "demande vide"}, status=400)
    pid = qui(req)
    taille = d.get("taille") or None
    if taille and taille not in TAILLES:
        return web.json_response({"erreur": "taille non prise en charge"}, status=400)
    modele = d.get("modele") or None
    if modele and modele not in CATALOGUE and modele not in MOTEURS_DISTANTS:
        return web.json_response({"erreur": "moteur inconnu"}, status=400)
    if modele in MOTEURS_DISTANTS and not moteur_distant_pret(modele):
        return web.json_response(
            {"erreur": "ce moteur demande une cle d API, a poser dans /admin"},
            status=400)
    priorite = d.get("priorite") or ""
    if priorite not in PRIORITES:
        return web.json_response({"erreur": "priorite inconnue"}, status=400)
    machine = d.get("noeud") or None
    if machine and noeud(machine) is None:
        return web.json_response({"erreur": "machine inconnue"}, status=400)
    # Une image appartient a celui qui l'a televersee. Deux pieges ici :
    # « != pid » et non « not in (None, pid) » — un nom absent du registre valait
    # laissez-passer ; et le nom doit rester un NOM, pas un chemin : « ../output/
    # studio/…png » sortait de ComfyUI/input et faisait decrire l'image d'un autre.
    if image and (os.path.basename(image) != image or ENTREES.get(image) != pid):
        return web.json_response({"erreur": "image inconnue"}, status=404)
    conv = conv_de(d.get("conversation"), pid)
    tid = uuid.uuid4().hex
    devant = len(ATTENTE) + len(EN_VOL)
    TACHES[tid] = {"etapes": [], "etat": "en cours", "demande": texte,
                   "conversation": conv["id"], "proprietaire": pid, "image": image}
    # Le tour est pose des maintenant : la conversation remonte dans la liste,
    # la demande s'affiche, et rien ne laisse croire qu'elle s'est perdue
    # pendant que la carte finit autre chose.
    enregistrer_tour(conv, tid, texte, {}, None, None, [], "en cours")
    if devant:
        journal(tid, f"en file d'attente — {devant} demande(s) devant")
    ATTENTE.append(tid)
    EN_FILE[tid] = {"tid": tid, "texte": texte, "conversation": conv["id"],
                    "proprietaire": pid, "image": image, "modele": modele,
                    "taille": taille, "priorite": priorite, "noeud": machine}
    sauver_file()
    await FILE_ATTENTE.put({"tid": tid, "texte": texte, "conv": conv, "taille": taille,
                            "image": image, "modele": modele, "priorite": priorite,
                            "noeud": machine})
    return web.json_response({"id": tid, "conversation": conv["id"], "position": devant})

async def api_etat(req):
    tid = req.match_info["tid"]
    tache = TACHES.get(tid)
    # 404 et non 403 : repondre « interdit » confirmerait que la tache existe.
    if not tache or tache.get("proprietaire") != qui(req):
        return web.json_response({"erreur": "inconnue"}, status=404)
    etat = dict(tache)
    etat.pop("proprietaire", None)
    # L'identifiant sert a poser un avis sur la reponse des qu'elle s'affiche,
    # sans attendre un rechargement de la conversation.
    etat["id"] = tid
    if tid in ATTENTE:
        # nombre de travaux DEVANT celui-ci : ceux qui le precedent dans la
        # file, plus celui qui occupe le GPU.
        etat["position"] = ATTENTE.index(tid) + len(EN_VOL)
    # Le pourcentage, pour CE travail seulement. api_file le servait deja pour
    # sa ligne « en cours » ; api_etat ne l'a jamais servi, si bien que la barre
    # posee ce matin dans la bulle lisait un champ qui n'existe pas et ne
    # s'affichait jamais.
    if AVANCES.get(tid, {}).get("total"):
        etat["avance"] = dict(AVANCES[tid])
    return web.json_response(etat)

def _ligne_file(tid, pid, admin, rang):
    """Une demande de la file, vue par quelqu'un.

    Le texte n'apparait qu'a son auteur et a un administrateur. Pour les
    autres, il reste la place et le type : de quoi comprendre l'attente sans
    lire par-dessus l'epaule du voisin.
    """
    t = TACHES.get(tid) or {}
    a_moi = t.get("proprietaire") == pid
    visible = a_moi or admin
    conv = CONVERSATIONS.get(t.get("conversation")) or {}
    etapes = t.get("etapes") or []
    ligne = {"tid": tid, "rang": rang, "a_moi": a_moi,
             "annulable": a_moi or admin,
             # « attend_carte » prime sur l'etat de la tache : elle est bien « en
             # cours » du point de vue du studio, mais aucune carte ne calcule
             # pour elle, et c'est ce que l'utilisateur regarde.
             "etat": ("attente carte" if t.get("attend_carte")
                      else t.get("etat") or "en attente"),
             # La derniere ligne du journal dit ou en est le travail bien mieux
             # qu'un pourcentage : « traduit pour flux1 », « 40 % telecharge ».
             "ou": (etapes[-1].get("msg", "")[:70] if etapes and visible else ""),
             "type": (t.get("plan") or {}).get("intention") or "en analyse"}
    ligne["demande"] = (t.get("demande", "")[:70] if visible
                        else "demande d'un autre utilisateur")
    if admin:
        # Un administrateur doit pouvoir dire A QUI parler quand la file est
        # bloquee ; les autres n'ont pas a savoir qui travaille.
        ligne["qui"] = dossier_utilisateur(t.get("proprietaire"))
        ligne["conversation"] = conv.get("titre", "")[:40]
    return ligne


async def api_file(req):
    """Etat de la file, tel que le demandeur a le droit de le voir.

    Les compteurs restent globaux — le GPU l'est aussi, et une position
    calculee sur sa propre file serait fausse.
    """
    pid = qui(req)
    admin = bool(req.get("compte")) and COMPTES.est_admin(req["compte"])
    mien = lambda t: TACHES.get(t, {}).get("proprietaire") == pid
    lignes = []
    for tid_vol in list(EN_VOL):
        a = AVANCES.get(tid_vol) or {}
        lignes.append(dict(_ligne_file(tid_vol, pid, admin, 0), en_cours=True,
                           avance=dict(a) if a.get("total") else None))
    for rang, tid in enumerate(ATTENTE, start=1):
        lignes.append(dict(_ligne_file(tid, pid, admin, rang), en_cours=False))
    return web.json_response({
        # Le premier des miens qui calcule : la page s'en sert pour savoir
        # qu'elle a quelque chose sur le feu, pas pour compter.
        "en_cours": next((t for t in EN_VOL if mien(t)), None),
        "occupe": bool(EN_VOL),
        "en_attente": len(ATTENTE),
        "a_moi": sum(1 for t in ATTENTE if mien(t)),
        "admin": admin,
        "lignes": lignes,
        # conserve : d'anciennes pages peuvent encore le lire
        "demandes": [TACHES[t].get("demande", "")[:60] for t in ATTENTE if mien(t)],
    })


async def api_file_annuler(req):
    """Retire une demande de la file, ou interrompt celle qui calcule."""
    pid = qui(req)
    admin = bool(req.get("compte")) and COMPTES.est_admin(req["compte"])
    tid = req.match_info["tid"]
    t = TACHES.get(tid)
    if not t:
        return web.json_response({"erreur": "demande inconnue"}, status=404)
    if t.get("proprietaire") != pid and not admin:
        # 404 et non 403 : repondre « interdit » confirmerait que la demande
        # existe, et permettrait de sonder la file d'un autre.
        return web.json_response({"erreur": "demande inconnue"}, status=404)

    if tid in ATTENTE or (t.get("etat") or "en attente") == "en attente":
        if tid in ATTENTE:
            ATTENTE.remove(tid)
        # La marque, et non l'etat : une tache peut etre en erreur pour dix
        # autres raisons, et confondre les deux ferait sauter des travaux
        # legitimes au moment ou le travailleur les sort de la file.
        t["annulee"] = True
        t["etat"] = "erreur"
        EN_FILE.pop(tid, None)
        sauver_file()
        conv = CONVERSATIONS.get(t.get("conversation"))
        if conv:
            enregistrer_tour(conv, tid, t.get("demande", ""), {}, None, None, [],
                             "erreur", "retiree de la file")
        journal(tid, "retiree de la file", etat="erreur")
        return web.json_response({"ok": True, "quoi": "retiree"})

    if tid in EN_VOL:
        t["annulee"] = True
        ident = t.get("noeud")
        # La ligne de journal AVANT tache.cancel() : celui-ci rend la main a
        # travailleur(), qui ecrit aussitot la sienne. Ecrite apres, la ligne
        # honnete se retrouvait DEVANT « interrompue » dans la liste, et la page
        # n'affiche que la derniere — le 29 aout a 13:07:40, l'utilisateur a lu
        # « interrompue » pendant que le NAS calculait encore 179 secondes.
        if ident and est_agent(ident):
            # Cette machine ne se joint pas : c'est elle qui appelle. Elle
            # apprend l'annulation a son prochain battement de progression et
            # coupe alors sa carte elle-meme ; la confirmation nous revient par
            # api_noeud_resultat. On promet donc un arret imminent, pas un arret
            # deja fait — c'est tout ce qu'on sait a cette seconde.
            journal(tid, f"arret demande a {(noeud(ident) or {}).get('titre', ident)}"
                         f" — sa carte s'arrete des qu'elle nous rappelle")
        else:
            # Une carte joignable s'arrete tout de suite : sans cela un rendu
            # dont plus personne ne veut occuperait le GPU jusqu'au bout.
            # Sans machine retenue, le travail en est a l'analyse ou a
            # l'ecriture : rien a interrompre dans ComfyUI, seulement ici.
            if ident:
                await interrompre_comfy(ident)
            journal(tid, "demande interrompue")
        # Puis le vrai levier : la tache du studio. Elle porte tout ce que
        # ComfyUI ne fait pas — l'analyse, les paroles, l'attente d'un
        # fournisseur — et c'est la qu'une demande pouvait tourner sans fin.
        tache = EN_VOL.get(tid)
        if tache is not None and not tache.done():
            tache.cancel()
        return web.json_response({"ok": True, "quoi": "interrompue"})

    return web.json_response({"erreur": "cette demande est deja terminee"},
                             status=409)


async def interrompre_comfy(ident=None):
    """Demande a un ComfyUI joignable d'abandonner ce qu'il calcule.

    L'adresse vient du noeud qui execute, et non plus systematiquement de la
    machine du studio : celle-ci n'a pas toujours de ComfyUI, et frapper a sa
    porte n'arretait alors rien du tout.
    """
    try:
        base = url_de(ident) if ident else url_locale()
        to = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=to) as s:
            await s.post(f"{base}/interrupt")
    except Exception as e:
        print(f"interruption impossible : {e}", flush=True)

async def api_conversations(req):
    pid = qui(req)
    if not mes_conversations(pid):
        conv_de(None, pid)          # tout arrivant repart avec une conversation
    liste = sorted(mes_conversations(pid), key=lambda c: c.get("modifie", 0), reverse=True)
    return web.json_response({
        "courante": COURANTE.get(pid) or (liste[0]["id"] if liste else None),
        "conversations": [{"id": c["id"], "titre": c["titre"], "cree": c["cree"],
                           "tours": len(c["tours"])} for c in liste]})

async def api_conversation(req):
    """Lecture pure : ne change pas la conversation courante du serveur.
    La bascule se fait explicitement par POST /api/conversation/{cid}/activer."""
    pid = qui(req)
    cid = req.match_info.get("cid")
    if cid and not ouvrable(CONVERSATIONS.get(cid), pid):
        return web.json_response({"erreur": "inconnue"}, status=404)
    return web.json_response(conv_de(cid, pid))

async def api_activer(req):
    pid = qui(req)
    cid = req.match_info["cid"]
    if not ouvrable(CONVERSATIONS.get(cid), pid):
        return web.json_response({"erreur": "inconnue"}, status=404)
    COURANTE[pid] = cid
    return web.json_response({"courante": cid})

async def api_nouvelle(req):
    pid = qui(req)
    c = _vide(proprietaire=pid)
    CONVERSATIONS[c["id"]] = c
    COURANTE[pid] = c["id"]
    sauver(c)
    return web.json_response(c)

# Une conversation fermee reste sur le disque un jour avant de disparaitre. La
# boite de dialogue n'est pas un filet : c'est un reflexe qu'on apprend a
# cliquer. Un jour suffit a s'apercevoir qu'on s'est trompe, et ne laisse pas
# s'accumuler ce que personne ne reverra.
GARDE_FERMEES = 24 * 3600


async def api_supprimer(req):
    """Ferme une conversation. Elle sort de la liste, et s'efface demain."""
    pid = qui(req)
    cid = req.match_info["cid"]
    conv = CONVERSATIONS.get(cid)
    if not a_moi(conv, pid):
        return web.json_response({"erreur": "inconnue"}, status=404)
    conv["ferme"] = time.time()
    sauver(conv)
    if COURANTE.get(pid) == cid:
        COURANTE.pop(pid, None)
    # La suivante est choisie ici, pas par la page : le serveur sait laquelle
    # reste, et la page doit afficher CE qu'elle vient de selectionner. Deux
    # decisions separees finissaient par diverger — on effaçait la courante et
    # l'ecran gardait l'ancienne.
    return web.json_response({"ok": True, "courante": conv_de(None, pid)["id"]})


def _fichiers_de(conv):
    """Les chemins sur disque des fichiers produits par cette conversation.

    Les deux copies possibles : celle qu'une machine a agent a deposee dans le
    depot du studio, et celle d'un ComfyUI local. On rend les deux ; celle qui
    n'existe pas sera simplement ignoree.
    """
    chemins = []
    for tour in conv.get("tours", []):
        for f in (tour.get("fichiers") or []):
            nom = f.get("filename")
            if not nom:
                continue
            ident = f.get("noeud") or noeud_local()["id"]
            depose = chemin_agent(ident, nom)
            if depose:
                chemins.append(depose)
            local = chemin_sortie_locale(f.get("subfolder", ""), nom)
            if local:
                chemins.append(local)
    return chemins


def purger_fermees():
    """Efface pour de bon les conversations fermees depuis plus d'un jour."""
    limite = time.time() - GARDE_FERMEES
    partis = 0
    for cid, conv in list(CONVERSATIONS.items()):
        quand = conv.get("ferme")
        if not quand or quand > limite:
            continue
        for chemin in _fichiers_de(conv):
            try:
                os.remove(chemin)
            except OSError:
                pass          # deja parti, ou sur une machine qu'on n'a pas
        CONVERSATIONS.pop(cid, None)
        try:
            os.remove(os.path.join(DOSSIER_CONV, cid + ".json"))
        except OSError:
            pass
        partis += 1
    if partis:
        print(f"  {partis} conversation(s) fermee(s) depuis plus de 24 h "
              f"effacee(s), images comprises", flush=True)
    purger_orphelins()
    return partis


# Efface, ou se contente de compter. DEFAUT : compter. Ce ramassage repare
# l'heritage d'une ancienne suppression immediate qui effaçait la conversation et
# laissait ses images ; sur une installation de reference, 5 fichiers et 12,8 Mo
# sur les 51 du depot. Ce sont des images que leur proprietaire n'a plus aucun
# moyen de voir — mais ce sont ses images, et elles existent par un bug, pas par
# un choix. On annonce donc ce qu'on liberait, et l'on attend qu'on nous le
# demande.
PURGE_ORPHELINS = os.environ.get("STUDIO_PURGE_ORPHELINS", "") == "1"

# Le dernier compte annonce, pour ne pas repeter une ligne identique toutes les
# 30 secondes. Une liste plutot qu'un entier : reassignable sans « global ».
_DERNIERS_ORPHELINS = [None]


def _reclames_sur_disque():
    """Les noms de fichiers que reclame une conversation, lues SUR LE DISQUE.

    charger_conversations() ne lit que les *.json de la RACINE de DOSSIER_CONV.
    C'est ce qu'il faut au demarrage ; c'est faux pour decider qu'un fichier
    n'appartient plus a personne. Sur l'installation de reference, 27
    conversations avaient ete rangees dans un sous-dossier d'archive du meme
    disque : invisibles en memoire, donc reputees inexistantes, alors que leurs
    images etaient bien la et toujours a leur proprietaire.

    Rend None — et non un ensemble vide — quand le parcours n'aboutit pas :
    dossier illisible, JSON tronque. Un ramassage qui se trompe efface pour de
    bon, donc l'appelant doit s'abstenir plutot que deviner. Une conversation
    illisible bloque le ramassage jusqu'a ce qu'on s'en occupe, et c'est le bon
    sens de l'erreur.
    """
    def _leve(e):
        raise e

    noms = set()
    try:
        for racine, dossiers, fichiers in os.walk(DOSSIER_CONV, onerror=_leve):
            # Le depot des sorties est souvent SOUS le dossier de donnees et ne
            # contient aucune conversation : le parcourir ne ferait qu'exposer
            # le ramassage aux JSON qu'une machine a agent y depose.
            dossiers[:] = [d for d in dossiers
                           if os.path.join(racine, d) != SORTIES_AGENT]
            for f in fichiers:
                # Les registres du studio (_cles.json, _noeuds.json…) ne sont
                # pas des conversations, et n'ont pas a etre ouverts ici.
                if not f.endswith(".json") or f.startswith("_"):
                    continue
                with open(os.path.join(racine, f), encoding="utf-8") as fh:
                    conv = json.load(fh)
                if not isinstance(conv, dict):
                    continue
                for tour in (conv.get("tours") or []):
                    for x in (tour.get("fichiers") or []):
                        nom = os.path.basename((x or {}).get("filename") or "")
                        if nom:
                            noms.add(nom)
    except Exception as e:
        print(f"  conversations illisibles sous {DOSSIER_CONV} ({e}) — "
              f"aucun fichier orphelin ne sera efface", flush=True)
        return None
    return noms


def purger_orphelins():
    """Efface du depot du studio les fichiers que plus rien ne reclame.

    Ils sont deja invisibles : la mediatheque lit les conversations, pas le
    disque. Les laisser fait grossir le disque sans que rien ne le montre — 51
    fichiers et 134,7 Mo sur l'installation de reference, tous herites de
    l'ancienne suppression immediate, qui effaçait la conversation et laissait
    ses images.

    Ce qu'on reclame se lit sur le DISQUE, pas dans CONVERSATIONS. La version
    qui interrogeait la memoire annonçait 38 orphelins (76,7 Mo) sur cette meme
    installation, alors que 46 des 51 fichiers (121,9 Mo) etaient reclames par
    l'une des 27 conversations rangees dans un dossier d'archive, et que 5
    seulement (12,8 Mo) n'appartenaient plus a personne : elle aurait efface les
    images de 22 conversations que leur proprietaire possede toujours.

    Seulement le depot du STUDIO : l'output d'un ComfyUI appartient a sa
    machine, qui fait son propre menage et y range aussi le travail fait a la
    main par son proprietaire.

    Et seulement au-dela du delai de garde : un fichier vient d'etre depose par
    un agent, le tour qui le reference s'ecrit une seconde plus tard. Effacer
    sur la seule absence de reference le supprimerait entre les deux.
    """
    if not os.path.isdir(SORTIES_AGENT):
        return 0
    reclames = _reclames_sur_disque()
    if reclames is None:
        return 0
    # La memoire par-dessus le disque : un tour tout juste enregistre peut
    # n'etre pas encore retombe dans son fichier.
    reclames |= {os.path.basename(f.get("filename") or "")
                 for conv in CONVERSATIONS.values()
                 for tour in conv.get("tours", [])
                 for f in (tour.get("fichiers") or [])}
    limite = time.time() - GARDE_FERMEES
    partis, octets = 0, 0
    for racine, _, fichiers in os.walk(SORTIES_AGENT):
        for nom in fichiers:
            if nom in reclames or nom.startswith("."):
                continue          # reference, ou registre d'un agent
            chemin = os.path.join(racine, nom)
            try:
                if os.path.getmtime(chemin) > limite:
                    continue
                octets += os.path.getsize(chemin)
                if PURGE_ORPHELINS:
                    os.remove(chemin)
                partis += 1
            except OSError:
                pass
    if partis and PURGE_ORPHELINS:
        print(f"  {partis} fichier(s) sans conversation efface(s) "
              f"({octets / 1e6:.1f} Mo)", flush=True)
    elif partis and partis != _DERNIERS_ORPHELINS[0]:
        # Compter sans effacer : c'est le seul moyen de voir combien pese
        # l'heritage avant de decider. Une installation neuve n'en a pas.
        #
        # Et seulement quand le nombre CHANGE : cette fonction tourne avec la
        # veille des machines, toutes les 30 s. La meme ligne repetee noyait le
        # journal — neuf lignes sur dix-sept pendant un rendu, mesure — au point
        # de cacher ce qu'on y cherchait vraiment.
        print(f"  {partis} fichier(s) sans conversation dorment ici "
              f"({octets / 1e6:.1f} Mo) — STUDIO_PURGE_ORPHELINS=1 pour les "
              f"effacer", flush=True)
    _DERNIERS_ORPHELINS[0] = partis
    return partis

def mes_fichiers(pid):
    """Tout ce que cet utilisateur a le droit de relire : ce que ses propres
    conversations ont produit, plus ce qu'il a lui-meme televerse.

    Le noeud fait partie de la cle. Les tours d'avant le multi-noeuds n'en ont
    pas : ils sont rattaches au noeud local, celui qui les a effectivement
    produits — d'ou l'interdiction de renommer l'identifiant "local".
    """
    defaut = noeud_local()["id"]
    permis = {(f.get("noeud") or defaut, f.get("subfolder", ""), f.get("filename"))
              for c in mes_conversations(pid) for t in c.get("tours", [])
              for f in (t.get("fichiers") or []) if f.get("filename")}
    permis |= {(defaut, "", nom) for nom, p in ENTREES.items() if p == pid}
    return permis

EXT_3D = {".glb", ".gltf", ".obj", ".ply", ".stl", ".fbx"}

# Ce qu'une machine a agent a le droit de deposer. Volontairement ferme : le
# studio sert ces fichiers sur sa propre origine.
# « .gif » explicitement : il n'est pas dans EXT_IMAGE, qui sert AUSSI a filtrer
# les pieces jointes en entree, et l'y ajouter accepterait des gif a retoucher,
# dont LoadImage ne lirait que la premiere image. Mais la page, elle, sait les
# afficher (EXT_IMG dans index.html), et une machine qui fait de l'animation en
# produit — VHS_VideoCombine ecrit du .gif par defaut. Sans cette ligne, un tel
# rendu se faisait refuser au depot APRES avoir paye tout le temps de carte.
EXT_DEPOT = EXT_IMAGE | EXT_VIDEO | EXT_AUDIO | EXT_3D | {".gif"}
# Deux gigaoctets : large pour la plus longue video qu'on sache produire, et
# borne quand meme. Sans borne, un seul depot remplissait le disque.
DEPOT_MAX = 2 * 1024 ** 3


def famille_sortie(nom):
    """La famille d'une sortie, d'apres son extension.

    D'apres l'extension et non l'intention : « video_image » produit une video,
    « personnage » une image, et un maillage arrive parfois d'un fournisseur qui
    ne dit pas ce qu'il envoie.
    """
    ext = os.path.splitext(nom or "")[1].lower()
    if ext in EXT_3D:
        return "objet3d"
    return famille_du_fichier(nom) or "autre"


def _date_sortie(f, conv):
    """La date d'une sortie, en secondes. Celle du fichier si on peut la lire.

    Les tours ne portent qu'une heure — « 10:51 » — sans date : ils ne peuvent
    pas servir a trier. Le fichier, lui, porte la sienne sur le disque. Faute de
    pouvoir la lire, la derniere activite de la conversation : approximative,
    mais du bon ordre de grandeur, et jamais nulle.
    """
    nom = f.get("filename") or ""
    ident = f.get("noeud") or noeud_local()["id"]
    for chemin in (chemin_agent(ident, nom),
                   chemin_sortie_locale(f.get("subfolder", ""), nom)):
        if not chemin:
            continue
        try:
            return os.path.getmtime(chemin)
        except OSError:
            continue
    return conv.get("modifie", 0)


async def api_mediatheque(req):
    """Tout ce que cet utilisateur a produit, range par famille.

    Lu dans les conversations et non sur le disque : elles seules savent a qui
    appartient un fichier, sur quelle machine il vit et ce qui avait ete
    demande. Un balayage du disque rendrait des noms sans histoire, et
    franchirait la frontiere entre utilisateurs.
    """
    pid = qui(req)
    items = []
    # mes_conversations() et non CONVERSATIONS : elle ecarte les fermees, comme
    # le fait mes_fichiers() du cote du service. Les deux divergeaient, et la
    # mediatheque affichait des vignettes que /api/fichier refusait ensuite —
    # image cassee, telechargement mort, « reprendre » mort, pour un fichier qui
    # est pourtant toujours la.
    for conv in mes_conversations(pid):
        for tour in conv.get("tours", []):
            for f in (tour.get("fichiers") or []):
                nom = f.get("filename") or ""
                items.append({
                    "filename": nom, "subfolder": f.get("subfolder", ""),
                    "type": f.get("type", "output"), "noeud": f.get("noeud"),
                    "famille": famille_sortie(nom),
                    "demande": (tour.get("demande") or "")[:120],
                    "moteur": tour.get("modele"),
                    "heure": tour.get("heure"),
                    "quand": _date_sortie(f, conv),
                    "conversation": conv["id"],
                    "titre": (conv.get("titre") or "")[:60],
                })
    # Les plus recents d'abord : c'est ce qu'on vient chercher neuf fois sur dix.
    # Trier sur la date du FICHIER et non sur l'ordre de CONVERSATIONS, qui est
    # celui d'os.listdir — c'est-a-dire aucun ordre.
    items.sort(key=lambda x: x["quand"], reverse=True)
    compte = {}
    for it in items:
        compte[it["famille"]] = compte.get(it["famille"], 0) + 1
    return web.json_response({"fichiers": items[:600], "compte": compte,
                              "total": len(items)})


async def api_fichier(req):
    """Relais vers ComfyUI/view. On propage le statut et l'en-tete Range :
    sans lui, impossible de naviguer dans une video, et le fichier entier
    transite en memoire.

    La requete n'est PLUS recopiee telle quelle : ComfyUI numerote ses sorties
    en sequence (_00011_, _00012_), il suffisait d'incrementer le compteur pour
    lire la production de tout le monde. On ne relaie que ce que le demandeur a
    lui-meme produit ou televerse.
    """
    nom = req.query.get("filename", "")
    sous = req.query.get("subfolder", "")
    genre = req.query.get("type", "output")
    # noeud absent : une page ouverte avant le multi-noeuds, ou un tour ancien
    ident = req.query.get("noeud") or noeud_local()["id"]
    if genre not in ("output", "input"):
        return web.json_response({"erreur": "inconnu"}, status=404)
    if noeud(ident) is None or (ident, sous, nom) not in mes_fichiers(qui(req)):
        return web.json_response({"erreur": "inconnu"}, status=404)
    # Depose ici — par un agent, ou par un fournisseur distant quand cette
    # machine n'a pas de ComfyUI : on sert du disque, sans relais.
    chemin = chemin_agent(ident, nom)
    if chemin and os.path.exists(chemin):
        # nosniff : ces fichiers viennent d'une machine a agent et sont servis
        # sur l'origine du studio. L'extension est deja filtree au depot ; on
        # empeche en plus le navigateur de deviner un type que l'extension ne
        # promet pas — deux verrous pour la meme porte, parce qu'elle donne sur
        # la session de l'utilisateur.
        return web.FileResponse(chemin,
                                headers={"X-Content-Type-Options": "nosniff"})
    if est_agent(ident):
        # un agent ne se relaie pas : le studio n'a pas son adresse
        return web.json_response({"erreur": "inconnu"}, status=404)
    entrants = {}
    if "Range" in req.headers:
        entrants["Range"] = req.headers["Range"]
    async with aiohttp.ClientSession() as s:
        params = {"filename": nom, "subfolder": sous, "type": genre}
        async with s.get(f"{url_de(ident)}/view", params=params, headers=entrants) as r:
            corps = await r.read()
            sortants = {}
            for h in ("Content-Type", "Content-Length", "Accept-Ranges", "Content-Range"):
                if h in r.headers:
                    sortants[h] = r.headers[h]
            sortants.setdefault("Accept-Ranges", "bytes")
            return web.Response(body=corps, status=r.status, headers=sortants)

# ══════════════════════ pilotage de ComfyUI ═══════════════════════════
# Reserve a la machine hote : un visiteur du reseau ne doit pas pouvoir
# arreter le moteur sous les pieds des autres.
DOSSIER_COMFY = os.path.dirname(BASE_COMFY)

def lanceur_comfy():
    """Trouve le script de lancement sans rien coder en dur : l'installation
    de chacun a son propre nom de fichier."""
    force = os.environ.get("COMFY_LANCEUR")
    if force:
        return force if os.path.exists(force) else None
    try:
        noms = os.listdir(DOSSIER_COMFY)
    except OSError:
        return None
    cand = [os.path.join(DOSSIER_COMFY, f) for f in noms
            if f.lower().endswith((".bat", ".sh"))
            and ("comfy" in f.lower() or f.lower().startswith("run_"))]
    # un lanceur personnalise (« LANCER ComfyUI … ») porte les bons arguments ;
    # run_nvidia_gpu.bat n'est qu'un repli generique.
    # « cpu » d'abord dans la cle : un lanceur personnalise nomme « LANCER
    # ComfyUI CPU.bat » aurait sinon battu run_nvidia_gpu.bat, et le rendu
    # serait cinquante fois plus lent sans un mot d'explication.
    cand.sort(key=lambda c: (1 if "cpu" in os.path.basename(c).lower() else 0,
                             0 if "lancer" in os.path.basename(c).lower() else 1, c))
    return cand[0] if cand else None

def commande_comfy():
    """Extrait la commande python du lanceur, sans modifier le fichier.

    Lancer le .bat tel quel ouvre une console a chaque demarrage et, avec
    --windows-standalone-build, rouvre le navigateur sur ComfyUI. En rejouant
    la commande qu'il contient on evite les deux, et le .bat reste intact pour
    un lancement manuel.
    """
    lanceur = lanceur_comfy()
    if not lanceur or not lanceur.lower().endswith(".bat"):
        return None
    try:
        with open(lanceur, encoding="utf-8", errors="replace") as f:
            texte = f.read()
    except OSError:
        return None
    # recoller les continuations de ligne du .bat (le caractere ^)
    texte = re.sub(r"\^\s*\r?\n\s*", " ", texte)
    for ligne in texte.splitlines():
        l = ligne.strip()
        if not l or l.lower().startswith("rem") or "python.exe" not in l.lower():
            continue
        try:
            args = shlex.split(l, posix=False)
        except ValueError:
            return None
        args = [a.strip('"') for a in args if a.strip()]
        exe = os.path.normpath(os.path.join(DOSSIER_COMFY, args[0]))
        if not os.path.exists(exe):
            return None
        args = [exe] + args[1:]
        if "--disable-auto-launch" not in args:
            args.append("--disable-auto-launch")
        return args
    return None

def port_comfy():
    # url_locale() et non COMFY : si noeuds.json place ComfyUI sur un autre
    # port, taskkill viserait le processus qui ecoute sur l'ancien — un tiers.
    m = re.search(r":(\d+)", url_locale().split("//")[-1])
    return int(m.group(1)) if m else 8188

def pid_du_port(port):
    """Le PID qui ecoute sur ce port, ou None.

    Get-NetTCPConnection plutot que netstat : la sortie de netstat est traduite
    (« LISTENING » devient « A L'ECOUTE ») et encodee dans la page de codes de
    la console, ce qui la rend illisible des que la machine n'est pas anglaise.
    """
    try:
        if os.name == "nt":
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"(Get-NetTCPConnection -LocalPort {port} -State Listen "
                 f"-ErrorAction SilentlyContinue | Select-Object -First 1).OwningProcess"],
                capture_output=True, text=True, errors="replace", timeout=30)
            sortie = (r.stdout or "").strip()
        else:
            r = subprocess.run(["lsof", "-ti", f"tcp:{port}", "-sTCP:LISTEN"],
                               capture_output=True, text=True, errors="replace", timeout=15)
            sortie = (r.stdout or "").splitlines()[0].strip() if r.stdout else ""
        return int(sortie) if sortie.isdigit() else None
    except Exception:
        return None

async def comfy_repond():
    try:
        to = aiohttp.ClientTimeout(total=4)
        async with aiohttp.ClientSession(timeout=to) as s:
            async with s.get(f"{url_locale()}/system_stats") as r:
                return (await r.json()) if r.status == 200 else None
    except Exception:
        return None

DUREE_CODE = 300         # cinq minutes

async def api_comfy(req):
    d = await comfy_repond()
    dev = (d or {}).get("devices", [{}])[0] if d else {}
    lanceur = lanceur_comfy()
    return web.json_response({
        "repond": bool(d),
        "url": url_locale(),
        "pilotable": local(req) and bool(lanceur),
        "lanceur": os.path.basename(lanceur) if lanceur else None,
        "carte": dev.get("name"),
        "vram_libre": round(dev.get("vram_free", 0) / 1e9, 1) if dev else None,
        "vram_totale": round(dev.get("vram_total", 0) / 1e9, 1) if dev else None,
    })

def origine_sure(req):
    """Un formulaire poste depuis n'importe quel site part du navigateur de
    l'utilisateur, donc depuis 127.0.0.1 : local(req) seul ne suffit pas a
    distinguer un clic dans l'interface d'un clic sur un site piege."""
    o = req.headers.get("Origin")
    if not o:
        return True
    # Depuis que cette verification s'applique a TOUTES les routes qui agissent,
    # un proxy qui ne preserve pas le Host du navigateur ne casse plus seulement
    # la connexion : il casse tout. On accepte donc aussi X-Forwarded-Host, que
    # ce proxy pose et qu'une page piegee ne peut pas forger — un formulaire
    # inter-site ne choisit pas ses en-tetes, et un fetch qui les choisit
    # declenche un prevol que le studio ne valide pas.
    vus = {req.headers.get("Host", ""),
           (req.headers.get("X-Forwarded-Host") or "").split(",")[0].strip()}
    # Comparaison a l'hote REELLEMENT utilise : une liste figee echouerait des
    # que le studio ecoute sur 0.0.0.0 et qu'on l'atteint par son adresse LAN.
    return o.split("//")[-1].rstrip("/") in {h for h in vus if h}

async def api_comfy_demarrer(req):
    if not origine_sure(req):
        return web.json_response({"erreur": "origine refusee"}, status=403)
    if not local(req):
        return web.json_response({"erreur": "pilotage reserve a la machine hote"}, status=403)
    if await comfy_repond():
        return web.json_response({"ok": True, "deja": True})
    lanceur = lanceur_comfy()
    if not lanceur:
        return web.json_response(
            {"erreur": "aucun script de lancement trouve a cote de ComfyUI ; "
                       "renseigne COMFY_LANCEUR"}, status=404)
    try:
        cmd = commande_comfy()
        if os.name == "nt":
            # DETACHED_PROCESS : ComfyUI survit a l'arret du studio.
            # CREATE_NO_WINDOW : pas de console qui surgit a chaque relance.
            drapeaux = 0x00000008 | 0x08000000
            if cmd:
                subprocess.Popen(cmd, cwd=DOSSIER_COMFY, creationflags=drapeaux,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 stdin=subprocess.DEVNULL)
            else:
                # lanceur illisible : on retombe sur le fichier, console comprise
                os.startfile(lanceur, cwd=DOSSIER_COMFY)
        else:
            subprocess.Popen(["/bin/sh", lanceur], cwd=DOSSIER_COMFY,
                             start_new_session=True)
    except Exception as e:
        return web.json_response({"erreur": f"lancement impossible : {e}"}, status=500)
    # ComfyUI met une trentaine de secondes a repondre : on rend la main tout de
    # suite, l'interface interroge l'etat toute seule.
    return web.json_response({"ok": True, "lanceur": os.path.basename(lanceur)})

async def api_comfy_arreter(req):
    if not origine_sure(req):
        return web.json_response({"erreur": "origine refusee"}, status=403)
    if not local(req):
        return web.json_response({"erreur": "pilotage reserve a la machine hote"}, status=403)
    # EN_VOL se vide entre deux taches : tester la file aussi, sinon
    # l'arret passe dans cet intervalle et les suivantes echouent en cascade.
    if EN_VOL or ATTENTE:
        return web.json_response(
            {"erreur": "des generations sont en cours ou en attente"}, status=409)
    pid = pid_du_port(port_comfy())
    if not pid:
        return web.json_response({"ok": True, "deja": True})
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                           capture_output=True, timeout=20)
        else:
            os.kill(pid, 15)
    except Exception as e:
        return web.json_response({"erreur": f"arret impossible : {e}"}, status=500)
    return web.json_response({"ok": True, "pid": pid})

async def veiller_noeuds():
    """Etat et catalogue de chaque machine, rafraichis en continu.

    Une machine peut s'allumer, s'eteindre, ou recevoir un modele pendant que le
    studio tourne : un releve fait une fois au demarrage se serait trompe des la
    premiere heure."""
    while True:
        try:
            purger_fermees()
            await sonder_noeuds()
            for x in NOEUDS:
                if ETAT_NOEUDS.get(x["id"], {}).get("repond"):
                    frais = MODELES_NOEUD.get(x["id"], {}).get("quand", 0)
                    if time.time() - frais > FRAICHEUR_MODELES:
                        await relever_modeles(x["id"])
        except asyncio.CancelledError:
            raise
        except Exception as e:
            # sans ce message, une erreur repetee figeait l'etat des machines
            # et personne ne pouvait le savoir
            print(f"veille des machines : {type(e).__name__} {e}", flush=True)
        await asyncio.sleep(30)


# ══════════════════ noeuds enregistres et jetons ═══════════════════════
# Ici, c'est le NOEUD qui appelle le serveur, jamais l'inverse. Une machine
# derriere une box, sur un portable qui s'endort ou sur un reseau qu'on ne
# maitrise pas ne peut pas etre jointe ; elle peut toujours sortir. L'agent
# s'annonce, reclame du travail, rend le resultat.
FICHIER_REGISTRE = os.path.join(DOSSIER_CONV, "_noeuds.json")
FICHIER_ADMIN = os.path.join(DOSSIER_CONV, "_admin.json")
FICHIER_COMPTES = os.path.join(DOSSIER_CONV, "_comptes.json")

# « obligatoire » : il faut un compte pour faire quoi que ce soit. C'est le
# defaut, parce qu'une installation neuve resterait sinon ouverte tant que
# personne n'y a pense — et personne n'y pense.
AUTH = (os.environ.get("STUDIO_AUTH") or "obligatoire").strip().lower()

# Mot de passe du compte « admin » cree au premier demarrage. Le renseigner
# permet de le fixer d'avance, dans un docker-compose par exemple ; sinon il
# est tire au sort et affiche une fois.
ADMIN_MDP = os.environ.get("STUDIO_ADMIN_MDP") or ""
COMPTES = None              # rempli par charger_registre, une fois le secret connu
REGISTRE = {}               # id -> {id, titre, jeton, cree}
SILENCE_MAX = 45            # secondes sans nouvelle avant de declarer perdu
TRAVAUX = {}                # id de noeud -> liste de travaux en attente
QUESTIONS = {}              # id de noeud -> questions en attente pour son LLM
# La machine attributaire est gardee A COTE du futur : un identifiant seul ne
# dit pas a qui le travail avait ete confie, et n'importe quelle machine
# authentifiee pouvait donc rendre le resultat d'une autre.
REPONSES = {}               # id de question -> (id de noeud, Future de la reponse)
RESULTATS = {}              # tid -> (id de noeud, Future du resultat)
SORTIES_AGENT = os.path.join(DOSSIER_DONNEES, "sorties")


def charger_registre():
    global ADMIN_JETON
    os.makedirs(DOSSIER_CONV, exist_ok=True)
    try:
        with open(FICHIER_REGISTRE, encoding="utf-8") as f:
            for x in json.load(f):
                REGISTRE[x["id"]] = x
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"registre des noeuds illisible ({e})", flush=True)
    # Jeton d'administration : celui de l'environnement s'il existe, sinon un
    # tire au sort et conserve. Il n'est affiche qu'a sa creation.
    ADMIN_JETON = os.environ.get("STUDIO_ADMIN") or ""
    if not ADMIN_JETON:
        try:
            with open(FICHIER_ADMIN, encoding="utf-8") as f:
                ADMIN_JETON = json.load(f)["jeton"]
        except Exception:
            ADMIN_JETON = secrets.token_urlsafe(24)
            try:
                with open(FICHIER_ADMIN, "w", encoding="utf-8") as f:
                    json.dump({"jeton": ADMIN_JETON}, f)
            except OSError:
                pass
            print(f"  Administration : jeton {ADMIN_JETON}", flush=True)
            print("  (a coller dans /admin ; conserve dans conversations/_admin.json)",
                  flush=True)


FICHIER_SESSION = os.path.join(DOSSIER_CONV, "_session.json")


def secret_de_session():
    """Le secret qui scelle les jetons de session. A LUI SEUL.

    Il valait autrefois le jeton d'administration. C'etait une erreur : ce
    jeton se colle dans une page, il se transmet, il a deja fuite une fois dans
    une sauvegarde committee par megarde — et qui l'obtenait pouvait alors
    forger une session pour n'importe quel compte, sans jamais connaitre un mot
    de passe. Administrer et s'authentifier sont deux roles ; ils ont
    desormais deux secrets.

    Il est tire au sort au premier demarrage et conserve. Le perdre ne coute
    que des reconnexions.
    """
    os.makedirs(DOSSIER_CONV, exist_ok=True)
    try:
        with open(FICHIER_SESSION, encoding="utf-8") as f:
            secret = json.load(f).get("secret")
        if secret:
            return secret
    except Exception:
        pass
    secret = secrets.token_urlsafe(32)
    try:
        tmp = FICHIER_SESSION + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"secret": secret}, f)
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        os.replace(tmp, FICHIER_SESSION)
    except OSError as e:
        # Sans fichier, le secret change a chaque demarrage : tout le monde est
        # deconnecte a chaque relance. Genant, pas dangereux — on le dit.
        print(f"secret de session non conserve ({e}) — les sessions ne "
              f"survivront pas au redemarrage", flush=True)
    return secret


def charger_comptes():
    """Le registre des comptes, scelle par le meme secret que l'administration.

    Ce secret sert a signer les jetons de session : le studio n'a alors rien a
    retenir en memoire, et une session survit a un redemarrage — ce qui compte
    ici, ou le studio redemarre souvent.
    """
    global COMPTES
    COMPTES = _comptes.Comptes(FICHIER_COMPTES, secret_de_session())
    if AUTH == "obligatoire" and not COMPTES.gens:
        # Sans ce compte, la porte serait fermee sans clef : plus personne ne
        # pourrait entrer, pas meme pour creer le premier compte.
        mdp = ADMIN_MDP or secrets.token_urlsafe(12)
        try:
            COMPTES.creer("admin", mdp, admin=True)
        except _comptes.ErreurCompte as e:
            print(f"  compte admin impossible a creer : {e}", flush=True)
        else:
            print("=" * 64, flush=True)
            print("  Compte administrateur cree : admin", flush=True)
            if ADMIN_MDP:
                print("  Mot de passe : celui de STUDIO_ADMIN_MDP", flush=True)
            else:
                print(f"  Mot de passe : {mdp}", flush=True)
                print("  Note-le : il n'est pas conserve en clair et ne sera",
                      flush=True)
                print("  plus jamais affiche. Change-le depuis l'interface.",
                      flush=True)
            print("=" * 64, flush=True)
    if COMPTES.gens:
        print(f"  Comptes   : {len(COMPTES.gens)} "
              f"({COMPTES.nombre_admins()} administrateur(s))"
              + ("   — connexion obligatoire" if AUTH == "obligatoire" else ""),
              flush=True)


@web.middleware
async def origine_verifiee(req, handler):
    """Aucune route qui AGIT ne s'ouvre a un formulaire poste d'ailleurs.

    SECURITY.md annonçait cette protection ; elle n'existait qu'a trois endroits
    — la connexion et les deux boutons de pilotage de ComfyUI. Ni « generer », ni
    « televerser », ni la fermeture d'une conversation, ni le changement de mot
    de passe, ni AUCUNE route d'administration ne la portaient. En pratique le
    « SameSite=Lax » des trois cookies bloque le POST inter-site sur les
    navigateurs actuels, mais c'etait la seule chose qui tenait, et ce n'etait pas
    ce qui etait ecrit. Un document de securite qui promet un controle inexistant
    est pire que le silence : on implemente donc ce qui etait promis.

    Ici plutot que route par route : c'est la seule forme qui ne s'oublie pas a
    la prochaine route ajoutee.

    Les machines a agent sont hors de portee de cette regle — elles n'ont pas de
    navigateur, n'envoient pas d'« Origin », et sont authentifiees par jeton.
    """
    if req.method in ("GET", "HEAD", "OPTIONS") or req.path.startswith("/api/noeud/"):
        return await handler(req)
    if not origine_sure(req):
        return web.json_response({"erreur": "origine refusee"}, status=403)
    return await handler(req)


@web.middleware
async def exiger_compte(req, handler):
    """Ferme tout ce qui fait ou montre quelque chose, tant qu'on n'est pas
    connecte.

    La page elle-meme reste ouverte : sans elle, impossible d'afficher le
    formulaire de connexion. Les routes de session aussi, evidemment, sinon on
    ne pourrait jamais se connecter.
    """
    if AUTH != "obligatoire":
        return await handler(req)
    chemin = req.path
    # Les routes d'administration verifient elles-memes le jeton (admin_ok) :
    # les fermer ici condamnerait le seul moyen d'entrer quand aucun compte
    # n'existe encore — c'est-a-dire l'amorçage d'une installation neuve.
    libre = (chemin == "/" or chemin.startswith("/api/compte")
             or chemin == "/admin" or chemin.startswith("/api/admin/")
             or chemin.startswith("/api/noeud/")
             or chemin == "/api/fournisseurs")
    if libre or req.get("compte"):
        return await handler(req)
    return web.json_response(
        {"erreur": "connexion requise", "connexion": True}, status=401)


def compte_de(req):
    """Le nom du compte connecte, ou "" pour un visiteur sans compte."""
    if not COMPTES:
        return ""
    return COMPTES.nom_du_jeton(req.cookies.get("studio_compte") or "") or ""


def sauver_registre():
    try:
        tmp = FICHIER_REGISTRE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(list(REGISTRE.values()), f, ensure_ascii=False, indent=1)
        os.replace(tmp, FICHIER_REGISTRE)
    except OSError:
        pass


def noeud_du_jeton(jeton):
    """Le noeud qui presente ce jeton. compare_digest : une comparaison qui
    s'arrete au premier caractere different laisse deviner le jeton."""
    if not jeton:
        return None
    for x in REGISTRE.values():
        if secrets.compare_digest(x.get("jeton", ""), jeton):
            return x
    return None


def admin_ok(req):
    """Administrateur connecte, ou porteur du jeton.

    Le jeton reste : c'est lui qui permet d'entrer la toute premiere fois,
    quand aucun compte n'existe encore.
    """
    nom = req.get("compte") or ""
    if nom and COMPTES and COMPTES.est_admin(nom):
        return True
    jeton = (req.headers.get("X-Admin") or req.cookies.get("studio_admin") or "")
    return bool(ADMIN_JETON) and secrets.compare_digest(jeton, ADMIN_JETON)


def moteurs_du_noeud(ident):
    """Les moteurs que cette machine peut executer, ici et maintenant.

    Deux conditions, les memes que pour l'attribution du travail : la carte
    tient le moteur, et les fichiers sont sur place. Une machine dont ce nombre
    est nul ne recevra jamais rien, quelle que soit la couleur de sa pastille.
    """
    dispo = _vram_utile(ident)
    prets = []
    for c, m in CATALOGUE.items():
        if m.get("vram", 0) > dispo:
            continue
        if manquants(c, ident):
            continue
        prets.append(c)
    return prets


def noeuds_agents():
    """Les noeuds enregistres, fusionnes avec leur dernier etat connu."""
    liste = []
    for x in REGISTRE.values():
        e = ETAT_NOEUDS.get(x["id"], {})
        vu = e.get("vu", 0)
        liste.append({"id": x["id"], "titre": x.get("titre") or x["id"],
                      "cree": x.get("cree"), "agent": True,
                      # « vu » ne suffit plus : depuis que l'agent s'annonce
                      # meme quand ComfyUI est mort — pour preter son modele de
                      # langage — une machine restait verte en permanence
                      # pendant que le repartiteur l'ecartait a juste titre.
                      "repond": bool(vu and time.time() - vu < SILENCE_MAX
                                     and e.get("repond")),
                      "vu_il_y_a": round(time.time() - vu) if vu else None,
                      "carte": e.get("carte"), "vram": e.get("vram"),
                      "moteurs": moteurs_du_noeud(x["id"]),
                      # None quand la machine ne dit rien : un agent d'avant le
                      # 31 aout n'annonce pas d'empreinte, et « inconnue » est
                      # plus honnete que « perime » ou que « a jour ».
                      "a_jour": (None if not e.get("empreinte")
                                 else e["empreinte"] == empreinte_agent()),
                      "en_travail": len(TRAVAUX.get(x["id"], []))})
    return liste


# ── ce que voit l'agent ───────────────────────────────────────────────
def _inventaire_connu(ident):
    """Vrai si l'on sait vraiment ce que porte cette machine."""
    connu = MODELES_NOEUD.get(ident)
    return bool(connu and any(connu.get("dossiers", {}).values()))


def _inventaire_a_rafraichir(ident):
    """Vrai s'il faut redemander l'inventaire a cette machine.

    Pas seulement quand on ne l'a jamais eu : AUSSI quand il approche de la
    peremption. manquants() jette le cache au-dela de 3 x FRAICHEUR_MODELES et
    declare alors tous les fichiers absents — la machine devient ineligible
    tout en restant verte. Mesure : elle disparaissait 120 s sur 300, et deux
    machines decalees laissaient 76 secondes ou plus rien n'etait eligible.

    On redemande a partir de FRAICHEUR_MODELES : l'agent bat toutes les dix
    secondes, il repond donc largement avant l'echeance.
    """
    connu = MODELES_NOEUD.get(ident)
    if not _inventaire_connu(ident):
        return True
    return time.time() - connu.get("quand", 0) > FRAICHEUR_MODELES


async def api_noeud_annonce(req):
    """Battement de coeur : l'agent dit qui il est et ce qu'il sait faire."""
    x = noeud_du_jeton(req.headers.get("X-Jeton"))
    if not x:
        return web.json_response({"erreur": "jeton inconnu"}, status=401)
    try:
        d = await req.json()
    except Exception:
        return web.json_response({"erreur": "corps illisible"}, status=400)
    etat = ETAT_NOEUDS.setdefault(x["id"], {})
    # L'empreinte du code qui tourne la-bas. Les agents d'avant le 31 aout n'en
    # envoient pas : absente, on ne conclut rien plutot que de les declarer
    # perimes sur une absence — mais ils le sont, et c'est justement pourquoi ils
    # ne l'annoncent pas. Le doute profite a la machine ; l'administration montre
    # « inconnue » et non « a jour ».
    if isinstance(d.get("empreinte"), str):
        etat["empreinte"] = d["empreinte"][:64]
    # D'ou elle nous parle. Sert a reconnaitre que l'Ollama du studio tourne sur
    # CETTE machine, et donc a reserver sa carte avant de l'interroger. Relue a
    # chaque annonce : une machine qui change de reseau change d'adresse, et une
    # adresse perimee ferait attendre la mauvaise carte.
    if req.remote:
        etat["ip"] = req.remote
    # Une annonce « comfy: False » dit : la machine est la, sa carte ne repond
    # pas. On note qu'on l'a vue et ce qu'elle porte cote langage, mais on
    # n'ecrase ni sa carte ni sa memoire par des zeros — ce qu'on savait d'elle
    # reste vrai, et le repartiteur doit continuer a l'ecarter.
    if d.get("comfy") is False:
        etat.update(vu=time.time(), agent=True, repond=False)
    else:
        etat.update(repond=True, vu=time.time(), agent=True,
                    carte=d.get("carte"), vram=float(d.get("vram") or 0),
                    libre=float(d.get("libre") or 0),
                    ram=float(d.get("ram") or 0))
    dossiers = d.get("modeles") or {}
    # Un dictionnaire de listes VIDES est bien forme et ne veut rien dire : il
    # arrive pendant que ComfyUI se releve. L'enregistrer effacait tout ce
    # qu'on savait de la machine, et pour cinq minutes.
    # Ce que porte la machine cote langage : le studio s'en sert quand le sien
    # ne repond plus.
    llm = d.get("llm")
    if isinstance(llm, dict):
        ETAT_NOEUDS.setdefault(x["id"], {}).update(
            llm=bool(llm.get("ok")), llm_modeles=llm.get("modeles") or [])
    if isinstance(dossiers, dict) and any(dossiers.values()):
        MODELES_NOEUD[x["id"]] = {"quand": time.time(),
                                  "dossiers": {k: set(v) for k, v in dossiers.items()}}
    # Tant qu'on ne connait pas ses modeles, on les reclame a chaque battement.
    # Sans cela, une machine bien equipee reste declaree incapable de tout
    # pendant les cinq minutes qui suivent un redemarrage du studio.
    return web.json_response({"ok": True, "intervalle": 10, "titre": x.get("titre"),
                              # Ce que le studio distribue. L'agent le compare a
                              # ce qu'il execute et se remplace tout seul — dire
                              # a une machine qu'elle est perimee ne sert a rien
                              # si personne ne lit la console.
                              "empreinte_agent": empreinte_agent(),
                              "modeles_demandes": _inventaire_a_rafraichir(x["id"])})


async def api_noeud_travail(req):
    """L'agent reclame du travail. Rien a faire : 204, il repassera."""
    x = noeud_du_jeton(req.headers.get("X-Jeton"))
    if not x:
        return web.json_response({"erreur": "jeton inconnu"}, status=401)
    # « vu » et non « repond » : cette route prouve que l'AGENT est la, pas que
    # ComfyUI l'est. Seule l'annonce le prouve, puisqu'elle l'a interroge. Les
    # confondre gardait verte une machine dont la carte etait morte, lui
    # envoyait du travail que personne ne venait chercher, et bloquait la file
    # une heure durant.
    ETAT_NOEUDS.setdefault(x["id"], {}).update(vu=time.time())
    file = TRAVAUX.get(x["id"]) or []
    if not file:
        return web.Response(status=204)
    travail = file.pop(0)
    # « entrees » n'etait pas transmis : le studio joignait bien les fichiers au
    # travail, et cette ligne les jetait juste avant de le remettre a l'agent.
    return web.json_response({"tid": travail["tid"], "graphe": travail["graphe"],
                              "entrees": travail.get("entrees") or {}})


async def api_noeud_question(req):
    """L'agent vient chercher une question pour son modele de langage."""
    x = noeud_du_jeton(req.headers.get("X-Jeton"))
    if not x:
        return web.json_response({"erreur": "jeton inconnu"}, status=401)
    ETAT_NOEUDS.setdefault(x["id"], {}).update(vu=time.time())
    file = QUESTIONS.get(x["id"]) or []
    if not file:
        return web.Response(status=204)
    # Retiree a la remise, et non au retour de la reponse : si ce retour se perd
    # — reseau, studio qui redemarre — l'agent reprenait la meme question et
    # relançait un appel de quinze minutes, indefiniment. Le studio a son propre
    # delai d'attente, c'est lui qui tranche.
    return web.json_response(file.pop(0))


async def api_noeud_reponse(req):
    """L'agent rapporte ce que son modele a repondu."""
    x = noeud_du_jeton(req.headers.get("X-Jeton"))
    if not x:
        return web.json_response({"erreur": "jeton inconnu"}, status=401)
    try:
        d = await req.json()
    except Exception:
        return web.json_response({"erreur": "corps illisible"}, status=400)
    attribue, futur = REPONSES.get(d.get("qid")) or (None, None)
    if futur is not None and attribue != x["id"]:
        # Une question n'est visible que dans la file de la machine a qui elle
        # a ete posee, donc ce cas ne s'atteint pas depuis l'exterieur — tant
        # qu'un qid ne fuit nulle part. La verification coute une comparaison.
        print(f"  reponse refusee : question posee a {attribue}, "
              f"repondue par {x['id']}", flush=True)
        return web.json_response({"erreur": "question posee a une autre machine"},
                                 status=403)
    if futur is not None and not futur.done():
        futur.set_result({"reponse": d.get("reponse") or "",
                          "erreur": d.get("erreur")})
    return web.json_response({"ok": True})


async def api_noeud_fichier(req):
    """L'agent depose un fichier produit. Il arrive par le reseau : le studio
    le range chez lui et le servira lui-meme, l'agent n'ayant aucune raison
    d'etre joignable."""
    x = noeud_du_jeton(req.headers.get("X-Jeton"))
    if not x:
        return web.json_response({"erreur": "jeton inconnu"}, status=401)
    nom = os.path.basename(req.query.get("nom") or "")
    tid = re.sub(r"[^0-9a-f]", "", req.query.get("tid") or "")[:32]
    if not nom or not tid:
        return web.json_response({"erreur": "requete incomplete"}, status=400)
    # Une extension qu'on sait servir, et rien d'autre. Le studio rend ces
    # fichiers sur SA propre origine : un « .html » ou un « .svg » depose ici
    # s'executerait dans la page du studio, avec sa session. Une machine a agent
    # produit des images, des videos, du son et des maillages ; elle n'a aucune
    # raison de deposer autre chose.
    if os.path.splitext(nom)[1].lower() not in EXT_DEPOT:
        return web.json_response({"erreur": "extension refusee"}, status=400)
    # Par chemin_agent(), qui verifie le chemin resolu : basename rend « .. »
    # pour « ../.. », et un identifiant de noeud forge remontait d'un cran.
    cible = chemin_agent(x["id"], nom)
    if not cible:
        return web.json_response({"erreur": "chemin refuse"}, status=400)
    os.makedirs(os.path.dirname(cible), exist_ok=True)
    # « client_max_size » ne s'applique PAS a req.content : en lisant le flux
    # nous-memes, on sortait de sa protection, et rien ne bornait plus ce qu'une
    # machine enregistree pouvait ecrire sur le disque du studio. On compte donc,
    # et on efface ce qu'on a commence a poser plutot que de laisser un fichier
    # tronque passer pour un rendu.
    taille = 0
    try:
        with open(cible, "wb") as f:
            async for bloc in req.content.iter_chunked(1 << 16):
                taille += len(bloc)
                if taille > DEPOT_MAX:
                    raise ValueError("trop gros")
                f.write(bloc)
    except ValueError:
        try:
            os.remove(cible)
        except OSError:
            pass
        print(f"  depot refuse de {x['id']} : {nom} depasse "
              f"{DEPOT_MAX / 1e9:.0f} Go", flush=True)
        return web.json_response({"erreur": "fichier trop gros"}, status=413)
    return web.json_response({"ok": True, "octets": taille})


async def api_noeud_progres(req):
    """Ou en est le rendu d'une machine a agent.

    ComfyUI n'annonce la progression que sur sa websocket, et le studio n'a
    acces qu'a la sienne. Sans ce relais, un rendu parti ailleurs affichait
    « en cours » sans jamais avancer — le cas ordinaire, desormais, puisque la
    machine du studio n'a plus de carte.
    """
    x = noeud_du_jeton(req.headers.get("X-Jeton"))
    if not x:
        return web.json_response({"erreur": "jeton inconnu"}, status=401)
    try:
        d = await req.json()
    except Exception:
        return web.json_response({"erreur": "corps illisible"}, status=400)
    # Seulement pour un travail en vol qui appartient a CETTE machine : une
    # annonce pour le travail d'une autre ecraserait sa barre.
    tid_dit = d.get("tid")
    if (isinstance(tid_dit, str) and tid_dit in EN_VOL
            and (TACHES.get(tid_dit) or {}).get("noeud") == x["id"]):
        AVANCES[tid_dit] = {"fait": int(d.get("fait") or 0),
                            "total": int(d.get("total") or 0),
                            "quoi": x.get("titre") or x["id"]}
    # La reponse de ce battement est le seul chemin par lequel une annulation
    # atteigne la machine : le studio n'a pas son adresse, et c'est elle qui
    # vient. Aucun autre appel de l'agent ne revient aussi souvent — il poste
    # sa progression toutes les deux secondes pendant un rendu. Faute de ce
    # mot, le 29 aout, la carte du NAS a calcule 179 s de plus pour une image
    # que plus personne n'attendait.
    # TACHES et non EN_VOL : l'annulation retire le travail du registre dans la
    # foulee, et la comparaison serait deja fausse au battement suivant.
    # La machine attributaire est verifiee, comme pour un resultat ou une
    # reponse : on ne renseigne une machine que sur le travail qu'on lui a
    # confie, et rien n'oblige a offrir ce booleen a qui n'y a pas droit.
    tache = TACHES.get(d.get("tid")) or {}
    annule = bool(tache.get("annulee")) and tache.get("noeud") == x["id"]
    return web.json_response({"ok": True, "annule": annule})


async def api_noeud_resultat(req):
    """Fin de travail : l'agent rend l'etat et la liste des fichiers deposes."""
    x = noeud_du_jeton(req.headers.get("X-Jeton"))
    if not x:
        return web.json_response({"erreur": "jeton inconnu"}, status=401)
    try:
        d = await req.json()
    except Exception:
        return web.json_response({"erreur": "corps illisible"}, status=400)
    # Une chaine, et rien d'autre : ce tid sert de cle a TACHES, et journal()
    # fait un setdefault. Un corps { "tid": {} } atteignait une cle non hachable
    # et rendait 500.
    tid = d.get("tid")
    if not isinstance(tid, str) or not tid:
        return web.json_response({"erreur": "tid absent"}, status=400)
    attribue, attente = RESULTATS.get(tid) or (None, None)
    # RESULTATS est vide des qu'un travail est fini : la verification ci-dessous
    # ne mordait donc plus, et une machine authentifiee pouvait ecrire dans le
    # journal d'un travail qui n'etait pas le sien. On se rabat sur la machine
    # retenue par la tache, qui survit, elle.
    if attribue is None:
        attribue = (TACHES.get(tid) or {}).get("noeud")
    if attribue is not None and attribue != x["id"]:
        # Un travail n'apparait que dans la file de la machine a qui il a ete
        # confie : aucun tid d'une autre ne fuit aujourd'hui. Mais rien ne
        # l'empechait de rendre a sa place — et un rendu accepte remplace les
        # fichiers montres a l'utilisateur.
        print(f"  [{str(tid)[:6]}] resultat refuse : travail confie a "
              f"{attribue}, rendu par {x['id']}", flush=True)
        return web.json_response({"erreur": "travail confie a une autre machine"},
                                 status=403)
    # « annule » : la machine confirme avoir coupe sa carte. C'est la seule
    # ligne du journal ecrite APRES l'arret, donc la seule qui puisse en parler
    # au passe. Elle arrive quelques secondes apres le clic, quand plus personne
    # n'attend le futur : rattacher_tardif n'a rien a en faire, on sort ici.
    if tid and d.get("etat") == "annule":
        journal(tid, f"{x.get('titre') or x['id']} a coupe son rendu — "
                     f"{float(d.get('secondes') or 0):.0f} s de calcul jetees",
                etat="erreur")
        if attente is not None and not attente.done():
            attente.set_result({"etat": "erreur", "erreur": "interrompue",
                                "secondes": d.get("secondes") or 0,
                                "fichiers": [], "noeud": x["id"]})
        return web.json_response({"ok": True})
    if attente is not None and not attente.done():
        attente.set_result({"etat": d.get("etat"), "erreur": d.get("erreur"),
                            "secondes": d.get("secondes") or 0,
                            "fichiers": d.get("fichiers") or [],
                            "noeud": x["id"]})
    else:
        # Personne n'attend plus : le studio a redemarre pendant le rendu. Les
        # fichiers sont pourtant sur son disque, deposes juste avant cet appel.
        # Les jeter serait perdre un travail qui a bel et bien ete fait.
        rattacher_tardif(tid, d, x)
    return web.json_response({"ok": True})


def rattacher_tardif(tid, d, x):
    """Recolle un resultat au tour qui l'attendait, apres un redemarrage.

    Sans verifier a qui le travail avait ete confie, contrairement a
    api_noeud_resultat : le redemarrage a emporte RESULTATS, et le tour ecrit
    sur le disque ne garde pas la machine attributaire. Le tid reste un uuid4
    — 128 bits qui ne se devinent pas — mais c'est la seule chose qui protege
    ce chemin-la ; faire mieux demanderait d'ecrire le noeud dans le tour.
    """
    for conv in CONVERSATIONS.values():
        for tour in conv.get("tours", []):
            if tour.get("id") != tid:
                continue
            if tour.get("etat") == "fini":
                return          # deja rattache : rien a refaire
            # La marque en memoire ET la trace sur le disque : rattacher_tardif
            # existe pour le cas « le studio a redemarre », et TACHES est vide
            # apres un redemarrage. Sans le second signal, une demande
            # interrompue puis suivie d'un redemarrage revenait terminee.
            if ((TACHES.get(tid) or {}).get("annulee")
                    or tour.get("erreur") == "interrompue"):
                # On a ecrit a l'utilisateur que le resultat serait ECARTE :
                # le recoller ferait reapparaitre, terminee et illustree, une
                # demande qu'il a lui-meme interrompue.
                print(f"  [{tid[:6]}] rendu tardif ignore : la demande avait "
                      f"ete interrompue", flush=True)
                return
            fichiers = [dict(f, noeud=x["id"]) for f in (d.get("fichiers") or [])]
            if d.get("etat") == "fini" and fichiers:
                tour.update(etat="fini", erreur=None, fichiers=fichiers)
                print(f"  [{tid[:6]}] rendu de {x['id']} rattache apres "
                      f"redemarrage — {len(fichiers)} fichier(s)", flush=True)
            else:
                tour.update(etat="erreur",
                            erreur=d.get("erreur") or "rendu perdu au redemarrage")
            sauver(conv)
            return


# ── ce que voit l'administrateur ──────────────────────────────────────
async def api_machines(_):
    """Les machines qu'un utilisateur peut viser depuis la page.

    On ne rend ici que ce qu'il faut pour choisir : un identifiant, un nom, si
    la machine repond, sa VRAM et ce qu'elle a sur le feu. Ni jeton, ni adresse,
    ni inventaire de modeles — ceux-la restent dans /api/admin/noeuds, derriere
    le jeton d'administration.

    Les machines qui ne repondent pas sont rendues quand meme, et marquees : les
    cacher ferait disparaitre le choix de l'utilisateur sans explication, juste
    parce qu'un agent s'est tu trois minutes.
    """
    local = noeud_local()
    e = ETAT_NOEUDS.get(local["id"], {})
    liste = [{"id": local["id"], "titre": local.get("titre") or local["id"],
              "local": True, "repond": bool(e.get("repond")),
              "vram": e.get("vram"), "en_travail": 0}]
    liste += [{"id": x["id"], "titre": x["titre"], "local": False,
               "repond": x["repond"], "vram": x["vram"],
               "en_travail": x["en_travail"]} for x in noeuds_agents()]
    return web.json_response(liste)


async def api_admin_noeuds(req):
    if not admin_ok(req):
        return web.json_response({"erreur": "acces refuse"}, status=403)
    local = noeud_local()
    e = ETAT_NOEUDS.get(local["id"], {})
    ligne_locale = {"id": local["id"], "titre": local.get("titre"), "agent": False,
                    "repond": bool(e.get("repond")), "carte": e.get("carte"),
                    "vram": e.get("vram"), "vu_il_y_a": 0,
                    # Zero en dur : la console affichait « en travail 0 » pendant
                    # qu'un rendu tournait sur cette machine.
                    "en_travail": len(TRAVAUX.get(local["id"], [])),
                    "moteurs": moteurs_du_noeud(local["id"])}
    return web.json_response({"noeuds": [ligne_locale] + noeuds_agents(),
                              # Un modele qui refuse de se charger degrade tout
                              # ce qui s'ecrit — enrichissement, traduction,
                              # paroles — sans jamais rien casser franchement.
                              # L'utilisateur ne voyait que « je n'ai pas reussi
                              # a etoffer ta demande », sans cause. Ici, la cause.
                              "modeles_casses": dict(MODELES_CASSES),
                              "modele_ecriture": choisir_modele_ecriture(),
                              "silence_max": SILENCE_MAX})


async def api_admin_noeud_detail(req):
    """Ce qu'une machine porte, et ce qui lui manque.

    On separe « la carte est trop petite » de « le modele n'est pas la » : le
    second se resout en telechargeant, le premier jamais. Les confondre envoyait
    chercher au mauvais endroit.
    """
    if not admin_ok(req):
        return web.json_response({"erreur": "acces refuse"}, status=403)
    ident = req.match_info["ident"]
    x = noeud(ident)
    if x is None:
        return web.json_response({"erreur": "machine inconnue"}, status=404)
    e = ETAT_NOEUDS.get(ident) or {}
    dispo = _vram_utile(ident)
    prets, absents, trop_gros = [], [], []
    for cle, m in CATALOGUE.items():
        fiche = {"cle": cle, "titre": m.get("titre", cle),
                 "vram": m.get("vram", 0), "type": m.get("type")}
        if m.get("vram", 0) > dispo:
            trop_gros.append(fiche)
        elif manquants(cle, ident):
            fiche["fichiers"] = [nom for _, nom, _, _ in manquants(cle, ident)]
            absents.append(fiche)
        else:
            prets.append(fiche)
    connu = MODELES_NOEUD.get(ident) or {}
    dossiers = {k: sorted(v) for k, v in (connu.get("dossiers") or {}).items() if v}
    return web.json_response({
        "id": ident, "titre": x.get("titre", ident), "agent": bool(x.get("agent")),
        "carte": e.get("carte"), "vram": e.get("vram"), "ram": e.get("ram"),
        "vram_utile": round(dispo, 1),
        "vu_il_y_a": round(time.time() - e["vu"]) if e.get("vu") else None,
        "llm": bool(e.get("llm")), "llm_modeles": e.get("llm_modeles") or [],
        "inventaire_connu": _inventaire_connu(ident),
        "releve_il_y_a": (round(time.time() - connu["quand"])
                          if connu.get("quand") else None),
        "prets": prets, "absents": absents, "trop_gros": trop_gros,
        "dossiers": dossiers,
    })


async def api_admin_essai_llm(req):
    """Pose une vraie question au modele d'une machine, et rend ce qu'elle dit.

    Par le MEME chemin que la bascule automatique, et non par une variante de
    test : une voie de secours qu'on verifie autrement que par son usage reel
    peut passer l'essai et echouer le jour venu.
    """
    if not admin_ok(req):
        return web.json_response({"erreur": "acces refuse"}, status=403)
    ident = req.match_info["ident"]
    if noeud(ident) is None:
        return web.json_response({"erreur": "machine inconnue"}, status=404)
    e = ETAT_NOEUDS.get(ident) or {}
    if not e.get("repond"):
        return web.json_response({"erreur": "cette machine ne repond pas"},
                                 status=409)
    corps = {"model": MODELE_LLM,
             "prompt": "Reponds en un seul mot : quelle est la couleur du ciel "
                       "par temps clair ?",
             "stream": False, "keep_alive": 0, "options": {"temperature": 0}}
    debut = time.time()
    reponse, erreur = await poser_a(ident, corps, secondes=180)
    return web.json_response({"modele": corps["model"],
                              "reponse": (reponse or "").strip()[:400],
                              "erreur": erreur,
                              "secondes": round(time.time() - debut, 1)})


async def api_admin_creer(req):
    if not admin_ok(req):
        return web.json_response({"erreur": "acces refuse"}, status=403)
    try:
        d = await req.json()
    except Exception:
        return web.json_response({"erreur": "corps illisible"}, status=400)
    titre = (d.get("titre") or "").strip()[:60]
    ident = re.sub(r"[^A-Za-z0-9_-]", "", (d.get("id") or "").strip())[:24]
    if not ident:
        return web.json_response({"erreur": "identifiant vide ou invalide"}, status=400)
    if ident in REGISTRE or ident == noeud_local()["id"]:
        return web.json_response({"erreur": "identifiant deja pris"}, status=409)
    jeton = secrets.token_urlsafe(24)
    REGISTRE[ident] = {"id": ident, "titre": titre or ident, "jeton": jeton,
                       "cree": time.strftime("%Y-%m-%d %H:%M")}
    sauver_registre()
    # Le jeton n'est rendu qu'ici : ensuite il n'est plus jamais renvoye.
    return web.json_response({"id": ident, "titre": titre or ident, "jeton": jeton})


async def api_admin_rejeton(req):
    if not admin_ok(req):
        return web.json_response({"erreur": "acces refuse"}, status=403)
    ident = req.match_info["ident"]
    if ident not in REGISTRE:
        return web.json_response({"erreur": "inconnu"}, status=404)
    jeton = secrets.token_urlsafe(24)
    REGISTRE[ident]["jeton"] = jeton
    sauver_registre()
    ETAT_NOEUDS.pop(ident, None)
    return web.json_response({"id": ident, "jeton": jeton})


async def api_admin_supprimer(req):
    if not admin_ok(req):
        return web.json_response({"erreur": "acces refuse"}, status=403)
    ident = req.match_info["ident"]
    if REGISTRE.pop(ident, None) is None:
        return web.json_response({"erreur": "inconnu"}, status=404)
    sauver_registre()
    ETAT_NOEUDS.pop(ident, None)
    MODELES_NOEUD.pop(ident, None)
    TRAVAUX.pop(ident, None)
    return web.json_response({"ok": True})


async def api_admin_entrer(req):
    """Depose le cookie d'administration si le jeton presente est le bon.

    Le meme freinage que la porte des comptes, et pour une raison plus forte :
    le jeton tire au sort fait 32 caracteres et n'est pas devinable, mais
    STUDIO_ADMIN laisse en imposer un choisi a la main, dont rien ne controle la
    longueur. Sans freinage, un jeton court se forçait a pleine vitesse et sans
    laisser une ligne de journal derriere lui.
    """
    try:
        d = await req.json()
    except Exception:
        return web.json_response({"erreur": "corps illisible"}, status=400)
    hote = (req.transport.get_extra_info("peername") or ("",))[0] if req.transport else ""
    cle_freinage = ("admin", hote)
    reste = _freinage(cle_freinage)
    if reste > 0:
        return web.json_response(
            {"erreur": f"trop d'essais — reessaie dans {reste:.0f} s"}, status=429)
    if not ADMIN_JETON or not secrets.compare_digest(d.get("jeton") or "", ADMIN_JETON):
        combien = _ECHECS.get(cle_freinage, (0, 0.0))[0] + 1
        _ECHECS[cle_freinage] = (combien, time.time())
        if combien in (3, 10, 50):
            # La console est le seul endroit ou le proprietaire du studio verra
            # qu'on essaie sa porte d'administration.
            print(f"  {combien} jetons d'administration refuses depuis "
                  f"{hote or 'origine inconnue'}", flush=True)
        return web.json_response({"erreur": "jeton refuse"}, status=403)
    _ECHECS.pop(cle_freinage, None)
    rep_ = web.json_response({"ok": True})
    rep_.set_cookie("studio_admin", ADMIN_JETON, max_age=7 * 24 * 3600,
                    httponly=True, samesite="Lax")
    return rep_


async def page_admin(req):
    return web.FileResponse(os.path.join(ICI, "web", "admin.html"))


# Les scripts qu'une machine-noeud a besoin de recuperer. Servis par le studio
# lui-meme : poser un noeud, c'est une commande, et le mettre a jour aussi.
_EMPREINTE_SERVIE = {"quand": 0.0, "valeur": ""}


def empreinte_agent():
    """Le sha256 de l'agent que ce studio distribue.

    Relue quand le fichier change — sous PyInstaller il ne change jamais, hors
    conteneur il change a chaque « git pull ». On compare le mtime plutot que de
    relire 40 ko a chaque battement de chaque machine.
    """
    chemin = os.path.join(ICI, "agent_noeud.py")
    try:
        quand = os.path.getmtime(chemin)
    except OSError:
        return ""
    if quand != _EMPREINTE_SERVIE["quand"]:
        try:
            with open(chemin, "rb") as f:
                _EMPREINTE_SERVIE["valeur"] = hashlib.sha256(f.read()).hexdigest()
        except OSError:
            return ""
        _EMPREINTE_SERVIE["quand"] = quand
    return _EMPREINTE_SERVIE["valeur"]


SCRIPTS_NOEUD = {"agent": "agent_noeud.py", "noeud.sh": "noeud.sh",
                 "noeud.bat": "noeud.bat",
                 # a coller dans « installer une application personnalisee »
                 "zimaos.yml": "zimaos-comfyui.yml",
                 "zimaos-registre.yml": "zimaos-registry.yml",
                 # de quoi telecharger les modeles depuis une machine-noeud
                 "installer.py": "installer.py",
                 "installation.py": "installation.py",
                 "catalogue.py": "catalogue.py",
                 "modeles.sh": "modeles.sh",
                 # noeud.sh et noeud.bat vont les chercher pour se mettre a
                 # jour. Ils sont copies dans l'image depuis toujours, avec un
                 # commentaire disant que le studio les sert — mais ils
                 # n'etaient pas dans cette table : /api/noeud/maj_noeud.sh
                 # rendait 404, et la mise a jour d'un agent echouait sans que
                 # rien ne dise pourquoi.
                 "maj_noeud.sh": "maj_noeud.sh",
                 "maj_noeud.bat": "maj_noeud.bat"}

async def api_agent_source(req):
    """Un script de mise en service, servi tel quel."""
    nom = SCRIPTS_NOEUD.get(req.match_info.get("quoi", "agent"))
    if not nom:
        return web.json_response({"erreur": "inconnu"}, status=404)
    chemin = os.path.join(ICI, nom)
    if not os.path.exists(chemin):
        return web.json_response({"erreur": "absent du studio"}, status=404)
    # texte brut : un navigateur l'affiche, curl l'enregistre
    return web.FileResponse(chemin, headers={"Content-Type": "text/plain; charset=utf-8"})


async def ecouter_comfy():
    """Relaie la progression que ComfyUI emet sur sa websocket.

    Elle est adressee au client qui a soumis le travail : le studio soumet avec
    client_id « studio », il lui suffit de se presenter sous le meme nom.

    La boucle se rattrape toute seule. ComfyUI redemarre, tombe, revient ; une
    ecoute qui abandonne au premier refus laisserait l'interface sans
    progression jusqu'au prochain redemarrage du studio, sans que rien ne le
    dise.
    """
    attente = 2
    while True:
        try:
            base = url_locale().replace("http://", "ws://").replace("https://", "wss://")
            to = aiohttp.ClientTimeout(total=None, sock_read=None)
            async with aiohttp.ClientSession(timeout=to) as s:
                async with s.ws_connect(f"{base}/ws?clientId=studio",
                                        heartbeat=30) as ws:
                    attente = 2
                    async for message in ws:
                        if message.type is not aiohttp.WSMsgType.TEXT:
                            continue
                        try:
                            d = json.loads(message.data)
                        except ValueError:
                            continue
                        genre, corps = d.get("type"), d.get("data") or {}
                        if genre == "progress":
                            # Cette websocket ne nomme pas le travail : elle
                            # decrit CE ComfyUI. On attribue donc a la tache qui
                            # tourne sur la machine du studio — au plus une, le
                            # verrou par machine y veillera.
                            cible_ws = _tid_sur(noeud_local()["id"])
                            if cible_ws:
                                AVANCES[cible_ws] = {
                                    "fait": int(corps.get("value") or 0),
                                    "total": int(corps.get("max") or 0),
                                    "quoi": str(corps.get("node") or "")}
                        elif genre in ("executing", "execution_success",
                                       "execution_error", "execution_interrupted"):
                            # « executing » avec un noeud nul signale la fin du
                            # graphe : la barre doit disparaitre, pas rester
                            # figee a 90 %.
                            if genre != "executing" or corps.get("node") is None:
                                AVANCES.pop(_tid_sur(noeud_local()["id"]), None)
        except asyncio.CancelledError:
            raise
        except Exception:
            AVANCES.pop(_tid_sur(noeud_local()["id"]), None)
        await asyncio.sleep(attente)
        attente = min(attente * 2, 30)


async def demarrer_file(a):
    global FILE_ATTENTE
    FILE_ATTENTE = asyncio.Queue()
    # Plusieurs travailleurs, pas un. Chacun prend une demande dans la meme
    # file ; le verrou par machine garantit qu'ils ne se disputent pas une carte.
    # Trois plutot que « autant que de machines » : les machines vont et
    # viennent, et il en faut un de plus que de cartes pour qu'une analyse
    # avance pendant que les autres calculent.
    for i in range(TRAVAILLEURS):
        a[f"travailleur{i}"] = asyncio.create_task(travailleur())
    await reprendre_file()
    a["veilleur"] = asyncio.create_task(veiller_noeuds())
    a["ecoute"] = asyncio.create_task(ecouter_comfy())

async def arreter_file(a):
    """Arrete tout ce que le studio a lance, sans supposer combien il y en a.

    « a["travailleur"] » n'existe plus depuis que les travailleurs sont
    numerotes : cette ligne levait un KeyError, et les DEUX suivantes — le
    veilleur des machines et l'ecoute de ComfyUI — n'etaient donc jamais
    atteintes. Un arret qui echoue a sa premiere ligne n'arrete rien, et il
    echouait en silence, dans le gestionnaire de fermeture d'aiohttp.

    On parcourt les clefs plutot que de les nommer : le prochain qui ajoute une
    tache de fond n'aura rien a penser ici.
    """
    for nom in [k for k in a if str(k).startswith("travailleur")] + ["veilleur",
                                                                     "ecoute"]:
        tache = a.get(nom)
        if tache is not None:
            tache.cancel()

def app():
    a = web.Application(client_max_size=128 * 1024 ** 2,
                        middlewares=[identite, origine_verifiee, exiger_compte])
    a.router.add_get("/", page)
    a.router.add_get("/api/modeles", api_modeles)
    a.router.add_get("/api/comfy", api_comfy)
    # l'agent d'un noeud : il appelle, on ne l'appelle jamais
    a.router.add_post("/api/noeud/annonce", api_noeud_annonce)
    a.router.add_get("/api/noeud/travail", api_noeud_travail)
    a.router.add_post("/api/noeud/progres", api_noeud_progres)
    a.router.add_get("/api/noeud/question", api_noeud_question)
    a.router.add_post("/api/noeud/reponse", api_noeud_reponse)
    a.router.add_post("/api/noeud/fichier", api_noeud_fichier)
    a.router.add_post("/api/noeud/resultat", api_noeud_resultat)
    a.router.add_get("/api/noeud/agent", api_agent_source)
    a.router.add_get("/api/noeud/{quoi}", api_agent_source)
    # administration
    a.router.add_get("/admin", page_admin)
    a.router.add_post("/api/admin/entrer", api_admin_entrer)
    a.router.add_get("/api/admin/noeuds", api_admin_noeuds)
    a.router.add_get("/api/admin/noeuds/{ident}/detail", api_admin_noeud_detail)
    a.router.add_post("/api/admin/noeuds/{ident}/llm", api_admin_essai_llm)
    a.router.add_post("/api/admin/noeuds", api_admin_creer)
    a.router.add_post("/api/admin/noeuds/{ident}/jeton", api_admin_rejeton)
    a.router.add_delete("/api/admin/noeuds/{ident}", api_admin_supprimer)
    a.router.add_post("/api/comfy/demarrer", api_comfy_demarrer)
    a.router.add_post("/api/comfy/arreter", api_comfy_arreter)
    a.router.add_post("/api/televerser", api_televerser)
    a.router.add_post("/api/generer", api_generer)
    a.router.add_get("/api/machines", api_machines)
    a.router.add_get("/api/etat/{tid}", api_etat)
    a.router.add_get("/api/file", api_file)
    a.router.add_post("/api/reprendre", api_reprendre)
    a.router.add_delete("/api/file/{tid}", api_file_annuler)
    a.router.add_get("/api/conversations", api_conversations)
    a.router.add_post("/api/conversations", api_nouvelle)
    a.router.add_get("/api/conversation", api_conversation)
    a.router.add_get("/api/conversation/{cid}", api_conversation)
    a.router.add_post("/api/conversation/{cid}/activer", api_activer)
    a.router.add_delete("/api/conversation/{cid}", api_supprimer)
    a.router.add_get("/api/fichier", api_fichier)
    a.router.add_get("/api/mediatheque", api_mediatheque)
    a.router.add_post("/api/avis", api_avis)
    a.router.add_get("/api/admin/avis", api_admin_avis)
    a.router.add_get("/api/admin/aiguilleur", api_admin_aiguilleur)
    a.router.add_post("/api/admin/aiguilleur", api_admin_aiguilleur)
    a.router.add_get("/api/admin/cles", api_admin_cles)
    a.router.add_post("/api/admin/cles", api_admin_cles_poser)
    a.router.add_get("/api/admin/cles/modeles", api_admin_modeles)
    a.router.add_get("/api/fournisseurs", api_fournisseurs)
    a.router.add_get("/api/compte", api_compte)
    a.router.add_post("/api/compte/entrer", api_entrer)
    a.router.add_post("/api/compte/sortir", api_sortir)
    a.router.add_post("/api/compte/mdp", api_mon_mdp)
    a.router.add_get("/api/admin/comptes", api_admin_comptes)
    a.router.add_post("/api/admin/comptes", api_admin_compte_poser)
    a.router.add_delete("/api/admin/comptes/{nom}", api_admin_compte_supprimer)
    a.router.add_get("/api/nuage", api_nuage)
    a.router.add_post("/api/nuage", api_nuage)
    a.on_startup.append(demarrer_file)
    a.on_cleanup.append(arreter_file)
    return a

if __name__ == "__main__":
    charger_conversations()
    charger_entrees()
    charger_registre()
    charger_comptes()
    charger_cles()
    charger_nuage()
    relever_vram()
    print(f"  Ecriture  : {choisir_modele_ecriture()}")
    print("  Aiguilleur: "
          + (f"{len(AIGUILLEUR.classes)} intentions apprises"
             if AIGUILLEUR else "absent — tout passe par le modele de langage"))
    print("=" * 64)
    print("  ComfyStudio")
    print(f"  ComfyUI   : {COMFY}")
    print(f"  Ollama    : {OLLAMA}   ({MODELE_LLM})")
    print(f"  Modeles   : {RACINE_MODELES}")
    # En conteneur, 127.0.0.1 designe le conteneur : l'adresse n'est utile
    # qu'a lui-meme. Et le port publie sur l'hote n'est pas forcement le notre —
    # sur une machine qui heberge deja un studio, annoncer 8199 envoie chez le
    # voisin, qui repond.
    _dans_conteneur = os.path.exists("/.dockerenv")
    _port_hote = os.environ.get("STUDIO_PORT_HOTE") or str(PORT)
    if _dans_conteneur:
        print(f"  Interface : http://ADRESSE-DE-L-HOTE:{_port_hote}"
              + (f"   (le conteneur, lui, ecoute sur {PORT})"
                 if _port_hote != str(PORT) else ""))
    else:
        print(f"  Interface : http://127.0.0.1:{PORT}")
    if HOTE in _HOTES_LOCAUX:
        # Le cas muet etait le piege : une relance sans STUDIO_HOTE coupait le
        # telephone et la tablette sans que rien ne le dise.
        print("  RESEAU    : ferme — cette machine seulement")
        print("              pour ouvrir : set STUDIO_HOTE=0.0.0.0 (ou "
              "« LANCER ComfyStudio.bat »)")
    else:
        # 0.0.0.0 ne se tape pas dans un navigateur : on donne les adresses
        # qu'on peut reellement lire sur un telephone.
        #
        # En conteneur, ces adresses sont celles du RESEAU DOCKER — 10.100.3.2,
        # 172.17.0.2 — que personne ne peut atteindre de l'exterieur. Les
        # annoncer envoyait taper une adresse qui ne repond pas. On dit alors ou
        # regarder vraiment : le port publie par le compose.
        if _dans_conteneur:
            print(f"  RESEAU    : port {PORT} du conteneur, publie par le "
                  f"compose sur le port {_port_hote} de l'hote")
            print(f"              depuis une autre machine : "
                  f"http://ADRESSE-DE-L-HOTE:{_port_hote}")
        else:
            for adr in sorted(a for a in ADRESSES_MACHINE if a not in _HOTES_LOCAUX):
                print(f"  RESEAU    : http://{adr}:{PORT}")
        print(f"  OUVERT AU RESEAU sur {HOTE}"
              + ("" if AUTH == "obligatoire"
                 else " — AUCUNE AUTHENTIFICATION (STUDIO_AUTH=libre)"))
    print(f"  Conversations : {len(CONVERSATIONS)} chargee(s)")
    print(f"  VRAM      : "
          + (f"{VRAM_GO['total']} Go" if VRAM_GO["total"]
             else "inconnue — aucun ComfyUI joignable au demarrage"))
    print("=" * 64, flush=True)
    web.run_app(app(), host=HOTE, port=PORT, print=None)
