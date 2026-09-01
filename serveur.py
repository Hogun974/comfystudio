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
# Le journal des appels distants s'ecrit depuis un fil a lui. Une ecriture
# disque synchrone dans la boucle d'evenements suspend TOUTES les demandes en
# cours le temps que le disque reponde, et ce studio tourne en conteneur, sur
# un volume monte dont la latence n'est pas la notre.
import queue
import threading

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
# Une adresse, ou plusieurs separees par des virgules. Plusieurs, parce qu'une
# seule obligeait a choisir une fois pour toutes la machine qui pense — et celle
# qu'on choisit est la plus grosse, donc celle qu'on met en pause pour jouer.
# Passer par l'agent d'une autre machine n'est pas un repli acceptable : mesure
# du 31 aout, la meme question coute 3,8 s en direct, 74,8 s au PC par son agent
# et 162,6 s au NAS. Le studio parle donc a chaque Ollama en direct, et choisit.
OLLAMAS = [u.strip().rstrip("/")
           for u in os.environ.get("OLLAMA_URL", "http://localhost:11434").split(",")
           if u.strip()] or ["http://localhost:11434"]
# La premiere reste « OLLAMA » : tout ce qui n'a pas besoin de choisir — la
# banniere, un dechargement — continue de la nommer sans rien savoir des autres.
OLLAMA     = OLLAMAS[0]
# Deux modeles, deux roles. L'aiguillage doit etre rapide : un petit modele suffit
# a produire du JSON structure. La lecture d'image exige la vision, d'ou un second
# modele, charge seulement quand une image doit etre decrite.
# qwen2.5vl plutot que bonsai-8b : mesure sur 16 tirages, bonsai remplace le
# sujet francais de facon reproductible (hibou -> hippopotamus aux 3 tirages,
# blaireau -> fox aux 3), ce qu'aucun garde-fou ne peut rattraper. qwen reste
# fidele au sujet ; ses defauts sont de forme (JSON tronque, prompt vide) et
# sont couverts par la relance de aiguiller() et le repli de normaliser().
# C'est aussi le modele de vision : un seul modele a charger.
MODELE_LLM    = os.environ.get("STUDIO_LLM") or "qwen2.5vl:7b"
# Vide : le plus gros modele installe qui tienne en memoire sera pris au
# demarrage. Le renseigner impose un choix.
MODELE_ECRITURE = os.environ.get("STUDIO_LLM_ECRITURE", "")
# Pose a la main, ou devine ? Un choix explicite ne doit pas etre efface par un
# echec passager sur une machine.
MODELE_ECRITURE_IMPOSE = bool(MODELE_ECRITURE)
MODELE_VISION = os.environ.get("STUDIO_VISION") or "qwen2.5vl:7b"
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
# Vrai a partir du moment ou le studio s'arrete. Un travailleur annule doit
# savoir POURQUOI il l'est : une annulation d'utilisateur ne vise que le travail
# en cours et le travailleur doit continuer a servir la file, tandis que l'arret
# vise le travailleur lui-meme, qui doit alors vraiment s'arreter au lieu de
# retourner attendre un travail que plus personne ne lui donnera.
ARRET = False
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
# Combien de temps une question accepte d'attendre AVANT d'aller voir une autre
# machine. Court : ce n'est pas un abandon, c'est un changement de file.
ATTENTE_LLM = 20
# Et combien de temps elle attend quand il n'y a PLUS d'autre machine. Une carte
# ne fait qu'une chose a la fois — c'est la regle, elle ne souffre pas
# d'exception : on attend que le rendu finisse, on ne s'installe pas a cote de
# lui. Une demi-heure est la meme patience que pour une soumission ; au-dela,
# c'est que quelque chose ne se libere plus, et il vaut mieux le dire.
ATTENTE_CARTE = int(os.environ.get("STUDIO_ATTENTE_CARTE") or 1800)


def verrou_noeud(ident):
    """Le verrou de cette carte. Cree a la demande : les machines vont et
    viennent, et une machine qu'on n'a jamais vue n'a pas besoin du sien."""
    return VERROUS_NOEUD.setdefault(ident, asyncio.Lock())


def verrou_modele(sous, nom):
    return VERROUS_MODELE.setdefault((sous, nom), asyncio.Lock())
FICHIER_FILE = os.path.join(DOSSIER_CONV, "_file.json")
EN_FILE = {}                # tid -> de quoi refaire la demande apres un arret
# Les demandes ARMEES : celles qui attendent qu'une machine en pause revienne.
# Elles n'occupent aucun travailleur — il n'y en a que trois, et en immobiliser
# un devant une carte que personne ne compte rallumer, c'est fermer un tiers du
# studio pour une demande qui, elle, ne coute rien a garder.
#
# Rien de plus a persister : elles restent dans EN_FILE, donc dans _file.json,
# et reprendre_file() les remet en file au reveil — ou elles se rearment d'elles
# memes si la machine dort encore. Ce registre-ci ne vit que le temps du
# processus, et c'est suffisant.
ARMEES = {}                 # tid -> {"quand", "depuis", "jusqua", "cle", "noeuds", "titres"}


def sauver_file():
    """Ecrit ce qui reste a faire — y compris ce qui est DEJA COMMENCE.

    Le travailleur retirait la demande du fichier des qu'il la prenait : un
    redemarrage pendant un rendu la perdait donc entierement, alors que c'est
    exactement le moment ou elle vaut le plus cher. Elle n'est retiree qu'une
    fois rendue.

    Les travaux en vol d'abord : ils etaient partis les premiers, ils repartent
    les premiers. Et si une machine les calcule encore, le studio s'y rebranche
    au lieu de les relancer — voir noeud_qui_travaille().
    """
    tmp = FICHIER_FILE + ".tmp"
    # EN_FILE fait foi, EN_VOL et ATTENTE ne donnent que l'ORDRE. La version
    # precedente n'ecrivait que l'intersection, et omettait donc tout travail
    # present dans EN_FILE sans etre dans l'un des deux — un etat qui existe
    # reellement : le « finally » du travailleur retire de EN_VOL avant de
    # decider s'il retire de EN_FILE. Deux travaux en vol, l'utilisateur en
    # annule un pendant l'arret du studio, et le travailleur de celui-la
    # reecrivait le fichier alors que l'autre n'etait plus nulle part : file
    # vide au reveil, exactement le symptome qu'on croyait avoir corrige.
    ordre = ([t for t in EN_VOL if t in EN_FILE]
             + [t for t in ATTENTE if t in EN_FILE and t not in EN_VOL])
    ordre += [t for t in EN_FILE if t not in ordre]
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump([EN_FILE[t] for t in ordre], f,
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
    repris, perdues, finies = 0, 0, 0
    for r in restes if isinstance(restes, list) else []:
        # « r » vient d'un fichier : rien ne garantit que c'est un objet. Un
        # « [null] » levait un AttributeError dans un gestionnaire on_startup,
        # et aiohttp abandonnait le demarrage — un studio en conteneur tournait
        # alors en boucle de redemarrage, sans autre symptome qu'une trace.
        if not isinstance(r, dict):
            perdues += 1
            continue
        conv = CONVERSATIONS.get(r.get("conversation"))
        if not conv or not isinstance(r.get("tid"), str):
            # Une conversation illisible emportait sans un mot les demandes qui
            # l'attendaient, et le sauver_file() de fin enterinait la perte.
            perdues += 1
            continue
        tid = r["tid"]
        # Deja reprise : un fichier portant deux fois le meme identifiant aurait
        # lance deux executer() concurrents sur une seule entree de EN_VOL.
        if tid in EN_FILE:
            continue
        # Deja livree. rattacher_tardif() peut avoir recolle le resultat pendant
        # que la demande etait encore en file ; la remettre en cours renverrait
        # a la carte un travail termine, avec une graine neuve — donc une AUTRE
        # image, qui remplacerait celle qui a ete livree.
        if any(t.get("id") == tid and t.get("etat") == "fini"
               for t in conv.get("tours", [])):
            finies += 1
            continue
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
                                "noeud": r.get("noeud"), "plan": r.get("plan"),
                                "modele_choisi": r.get("modele_choisi", False),
                                # LA GRAINE DEJA TIREE. Sans elle, la reprise en
                                # tirait une neuve pendant que la carte finissait
                                # l'image faite avec l'ancienne : le tour gardait
                                # une graine qui n'avait produit aucune image, et
                                # « refaire en soigne » serait reparti d'un
                                # fantome. Releve par la recette.
                                "graine": r.get("graine"),
                                # COMBIEN DE TIRAGES RESTENT A LANCER. Le premier
                                # l'a ramene a 1 des qu'il a lance les autres :
                                # sans cela, un studio redemarre trois fois
                                # pendant une file chargee aurait relance N-1
                                # travaux a chaque reveil.
                                "variantes": r.get("variantes", 1)})
        repris += 1
    if repris:
        print(f"  {repris} demande(s) reprise(s) de la file d'avant l'arret",
              flush=True)
    if finies:
        print(f"  {finies} demande(s) etaient deja livrees — laissees telles "
              f"quelles", flush=True)
    if perdues:
        # On le dit, et on garde le fichier : sans cela la perte etait
        # silencieuse des deux cotes, pour l'utilisateur comme pour le
        # diagnostic.
        try:
            # Deplace, pas copie : le fichier va etre reecrit juste apres par
            # sauver_file(), donc rien n'est ecrase et l'original est garde.
            os.replace(FICHIER_FILE, FICHIER_FILE + ".perdu")
        except OSError:
            pass
        print(f"  {perdues} demande(s) de la file n'ont pas pu etre rattachees "
              f"— l'ancien fichier est garde sous _file.json.perdu", flush=True)
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
               "local": False, "agent": True, "pause": x.get("pause")}
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


def _ollama_ici(url=None):
    """Vrai si Ollama tourne sur la machine du studio.

    On ne peut pas connaitre la memoire d'une machine qu'on ne fait qu'appeler :
    on lui fait confiance. Une machine ne telecharge pas un modele de vingt-six
    milliards de parametres si elle ne peut pas le charger.
    """
    hote = (urllib.parse.urlparse(url or OLLAMA).hostname or "").lower()
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
    """Le modele d'ecriture de la PREMIERE adresse — pour la banniere et pour
    /admin, qui ont besoin d'un nom a montrer.

    Le choix reel se fait par adresse, au moment de l'appel : deux machines ne
    portent pas les memes modeles, et le plus gros ici peut etre absent la-bas.
    Voir modele_ecriture_de().
    """
    return modele_ecriture_de(OLLAMA)


# « Le meilleur modele d'ecriture, la ou tu iras. » Le modele ne peut plus etre
# choisi par l'appelant : il depend de l'adresse, et l'adresse n'est connue
# qu'apres. On passe donc une intention, resolue au dernier moment.
MODELE_POUR_ECRIRE = "@ecriture"
# tid -> (adresse, modele) laisse CHAUD par cette demande. Sur la tache et non
# dans un dictionnaire global indexe par nom : deux demandes simultanees
# emploient le meme modele, parfois sur deux machines, et un registre partage ne
# peut pas dire lequel decharger. Pire, la branche « tout decharger » vidait le
# registre entier — la chanson de l'un dechargeait, donc RECHARGEAIT, le modele
# de vision de l'autre, sur la carte que son rendu allait reclamer.
_CHAUD = {}
# url -> {"quand", "modeles", "noeud"}. Relu rarement : la liste des modeles
# d'une machine ne change qu'a la main, et resoudre un nom d'hote a chaque appel
# se paierait des centaines de fois pour rien.
_CERVEAUX = {}
FRAICHEUR_CERVEAU = 120


def _relever_cerveau(url):
    """Interroge cet Ollama. BLOQUANT — a n'appeler que hors boucle."""
    c = _CERVEAUX.setdefault(url, {"quand": 0.0, "modeles": [], "noeud": None,
                                   "en_cours": False})
    try:
        import urllib.request

        with urllib.request.urlopen(f"{url}/api/tags", timeout=8) as r:
            c["modeles"] = json.load(r).get("models", []) or []
    except Exception:
        # On garde ce qu'on savait : une machine qui ne repond pas a CET instant
        # n'a pas desinstalle ses modeles.
        pass
    hote = urllib.parse.urlparse(url).hostname
    if hote:
        import socket
        try:
            ip = socket.gethostbyname(hote)
        except OSError:
            ip = None
        if ip:
            c["noeud"] = next((x["id"] for x in tous_les_noeuds()
                               if x.get("agent")
                               and (ETAT_NOEUDS.get(x["id"]) or {}).get("ip") == ip),
                              c.get("noeud"))
    c["quand"] = time.time()
    c["en_cours"] = False
    return c


async def _rafraichir_cerveau(url):
    """Le meme relevé, hors de la boucle d'evenements."""
    try:
        await asyncio.get_running_loop().run_in_executor(
            None, _relever_cerveau, url)
    except Exception:
        (_CERVEAUX.get(url) or {})["en_cours"] = False


def cerveau(url):
    """Ce que porte cet Ollama, et sur quelle machine du parc il tourne.

    NE BLOQUE JAMAIS. La version precedente faisait un urlopen synchrone de huit
    secondes depuis la boucle d'evenements : une machine eteinte gelait tout le
    studio a chaque expiration du cache — plus de page servie, plus de /api/etat,
    et surtout plus d'annonce d'agent reçue, assez pour approcher SILENCE_MAX sur
    des machines qui allaient tres bien. Le fichier portait deja la mise en garde
    deux fonctions plus bas, pour le demarrage.

    On rend donc ce qu'on sait, et l'on va chercher la suite a cote. Un
    inventaire perime d'une minute ne coute rien : il ne change qu'a la main.

    « noeud » vaut None quand on ne reconnait pas la machine : c'est le cas de
    l'Ollama du studio lui-meme, et d'une machine qui n'a pas d'agent. On ne
    reserve alors aucune carte — on ne saurait pas laquelle.
    """
    c = _CERVEAUX.get(url)
    if c is None:
        c = _CERVEAUX[url] = {"quand": 0.0, "modeles": [], "noeud": None,
                              "en_cours": False}
    if time.time() - c["quand"] >= FRAICHEUR_CERVEAU and not c.get("en_cours"):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # Hors boucle : le demarrage. C'est le seul moment ou bloquer est
            # acceptable, et c'est aussi lui qui remplit le cache pour que la
            # premiere demande ne trouve pas une liste vide.
            return _relever_cerveau(url)
        c["en_cours"] = True
        asyncio.get_running_loop().create_task(_rafraichir_cerveau(url))
    return c


def _sait_lire_ici(url, modele):
    """Ce modele est-il installe sur cet Ollama."""
    return any(m.get("name") == modele for m in cerveau(url)["modeles"])


def _sait_voir_ici(url, modele):
    """Ce modele sait-il REGARDER une image, et pas seulement lire du texte.

    Installe ne veut pas dire capable. Un modele de texte a qui l'on envoie une
    image ne refuse pas : il decrit ce qu'il imagine, et rien ne le signale —
    ni erreur, ni ligne de journal. C'est le pire des trois resultats
    possibles. Ollama declare la capacite dans /api/tags depuis sa mise a jour ;
    quand il ne la declare pas du tout, on ne bloque rien plutot que de rendre
    la lecture d'image impossible sur une version plus ancienne.
    """
    for m in cerveau(url)["modeles"]:
        if m.get("name") != modele:
            continue
        capacites = m.get("capabilities")
        return True if capacites is None else ("vision" in capacites)
    return False


def cerveaux_utilisables(image=False):
    """Les Ollama qu'on a le droit d'employer, dans l'ordre ou les employer.

    Trois regles, dans cet ordre, et ce sont celles de l'utilisateur :

      - une machine EN PAUSE ne pense pas. Son proprietaire s'en sert.
      - une carte LIBRE passe devant une carte occupee. Attendre deux minutes
        derriere un rendu quand une autre machine repond tout de suite n'a de
        sens pour personne.
      - a egalite, la PLUS PETITE carte. Une analyse tient sur n'importe
        laquelle ; occuper la meilleure pour reflechir, c'est la retirer du
        rendu qu'elle seule fait vite.

    SAUF POUR UNE IMAGE, ou la derniere regle s'inverse. Lire une image est la
    seule tache ou la taille de la carte decide vraiment : mesure du 31 aout,
    la meme image lue en 19 s sur la 2080 Ti et toujours pas rendue apres
    NEUF CENTS secondes sur la GTX 1060, ou le modele de vision deborde.
    « La plus petite qui suffise » suppose qu'elles suffisent toutes ; ici,
    non.
    """
    bons = []
    for url in OLLAMAS:
        c = cerveau(url)
        ident = c.get("noeud")
        if ident and (noeud(ident) or {}).get("pause"):
            continue
        if not c["modeles"]:
            continue
        libre = not (ident and verrou_noeud(ident).locked())
        taille = (ETAT_NOEUDS.get(ident) or {}).get("vram") or 0 if ident else 0
        bons.append((0 if libre else 1, -taille if image else taille, url, ident))
    bons.sort(key=lambda x: (x[0], x[1]))
    return [(url, ident) for _, _, url, ident in bons]


def modele_vision_de(url):
    """Le meilleur modele de CETTE adresse qui sache regarder une image.

    Le plus gros, parce que la vision est la tache ou la taille se voit le plus
    — et parce qu'on ne lit pas une image a chaque demande. Rend "" quand
    aucun modele de cette machine ne sait voir.
    """
    ident = cerveau(url).get("noeud")
    # BORNE PAR LA CARTE. « Le plus gros » est un mauvais mandataire de « le
    # meilleur » : sur le PC, gemma4:26b declare « vision » et pese 18,6 Go pour
    # une carte de 11 — le studio y aurait charge 18,6 Go la ou qwen2.5vl:7b en
    # met 6, et c'est justement lui que la mesure du 31 aout a trouve correct.
    # On ne retient donc que ce que la machine peut tenir, debordement compris.
    plafond = _vram_utile(ident) if ident else float("inf")
    voyants = [m for m in cerveau(url)["modeles"]
               if not _casse_ici(url, m.get("name"))
               and _sait_voir_ici(url, m.get("name"))]
    tenables = [m for m in voyants if m.get("size", 0) / 1e9 <= plafond] or voyants
    return max(tenables, key=lambda m: m.get("size", 0))["name"] if tenables else ""


def modele_ecriture_de(url):
    """Le meilleur modele d'ecriture installe sur CET Ollama.

    Par adresse, et non une fois pour toutes : deux machines ne portent pas les
    memes modeles, et celui qui est le plus gros ici peut etre absent la-bas.
    """
    # Le reglage l'emporte — la ou le modele existe. Un parc n'est pas
    # homogene : imposer gemma3:4b parce qu'une machine l'a rendrait l'autre
    # muette, alors qu'elle porte autre chose de tenable.
    if MODELE_ECRITURE and _sait_lire_ici(url, MODELE_ECRITURE):
        return MODELE_ECRITURE
    modeles = [m for m in cerveau(url)["modeles"]
               if not _casse_ici(url, m.get("name"))]
    # Le plafond : la memoire de CETTE machine quand l'Ollama est ici, la carte
    # de la machine du parc quand on la reconnait, et rien du tout sinon —
    # on ne devine pas ce qu'une machine inconnue peut charger.
    #
    # Il ne valait qu'en local, et « rien du tout » ailleurs faisait choisir
    # gemma4:26b, 18,6 Go, sur une carte de 11 : cent soixante-cinq secondes par
    # traduction, mesurees. Une machine du parc annonce sa carte et sa RAM ; on
    # s'en sert.
    ident_ = cerveau(url).get("noeud")
    if _ollama_ici(url):
        plafond = (memoire_vive() or 16.0) * 0.6
    elif ident_ and _vram_utile(ident_):
        plafond = _vram_utile(ident_)
    else:
        plafond = float("inf")
    tenables = [m for m in modeles if 0 < m.get("size", 0) / 1e9 <= plafond]
    if not tenables:
        return MODELE_LLM
    gros = max(tenables, key=lambda m: m.get("size", 0))
    courant = next((m for m in modeles if m.get("name") == MODELE_LLM), None)
    # Ne changer que si le gain est net : recharger un modele a peine plus gros
    # coute du temps sans rien apporter a l'ecriture.
    if courant and gros.get("size", 0) < courant.get("size", 0) * 1.5:
        return MODELE_LLM
    return gros["name"]


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

# Les reglages appartiennent a la CONVERSATION, et non a la page. Une
# conversation travaille en FLUX.1 1920x1080, une autre en RealVis 1024x720, et
# chacune garde le sien tant que son proprietaire ne le change pas.
#
# Ils vivaient dans les menus de la page, donc dans un seul jeu partage par
# toutes les conversations — et surtout, chaque chemin d'envoi devait penser a
# les recopier. Le formulaire de reponse a une precision n'envoyait que la
# taille et la priorite : le moteur impose et la machine choisie disparaissaient
# a la seconde ou l'on repondait a une question. Constate par l'utilisateur.
# Sur la conversation, aucun chemin ne peut plus les oublier.
REGLAGES_CONV = ("modele", "taille", "priorite", "noeud")


def reglages_de(conv):
    r = (conv or {}).get("reglages")
    return dict(r) if isinstance(r, dict) else {}


def _dit_reglage(cle, valeur):
    """Le nom humain d'un reglage. « realvis » ne veut rien dire trois jours
    plus tard ; « RealVisXL V5.0 » si."""
    if not valeur:
        return "automatique"
    if cle == "modele":
        return (CATALOGUE.get(valeur) or MOTEURS_DISTANTS.get(valeur)
                or {}).get("titre", valeur)
    if cle == "noeud":
        return (noeud(valeur) or {}).get("titre", valeur)
    if cle == "taille":
        return valeur.replace("x", " × ")
    if cle == "priorite":
        return {"rapide": "rapide", "soigne": "soigne"}.get(valeur, valeur)
    return valeur


_NOM_REGLAGE = {"modele": "moteur", "taille": "taille", "priorite": "priorite",
                "noeud": "machine"}


def murmurer(conv, change):
    """Ecrit dans la conversation qu'un reglage a change.

    Ecrit, et pas seulement affiche : la question « pourquoi cette image est-elle
    en 1024 ? » se pose des jours plus tard, quand le journal du studio a disparu
    depuis longtemps. Le changement s'ancre APRES le dernier tour existant, pour
    se relire a sa place dans le fil.

    Un seul murmure par changement, meme s'il porte sur plusieurs reglages : la
    page les envoie ensemble, et quatre lignes pour un geste seraient du bruit.
    """
    if not change:
        return None
    tours = conv.get("tours") or []
    m = {"quand": time.strftime("%H:%M"),
         "apres": tours[-1].get("id") if tours else None,
         "texte": " · ".join(f"{_NOM_REGLAGE.get(k, k)} : {_dit_reglage(k, v)}"
                             for k, v in change)}
    liste = conv.setdefault("murmures", [])
    if not isinstance(liste, list):
        liste = conv["murmures"] = []
    liste.append(m)
    # Meme borne que les tours : une conversation ne doit pas grossir sans fin.
    conv["murmures"] = liste[-60:]
    return m


def poser_reglages(conv, d, ecrire=True):
    """Fusionne ce que la demande dit avec ce que la conversation retient.

    PRESENCE et non valeur : une cle absente est heritee, une cle presente —
    meme vide — remplace. C'est la seule facon de distinguer « je n'en parle
    pas » de « remets sur automatique », et les deux arrivent.

    « brouillon » ne se retient jamais. C'est un geste, pas un reglage : le
    garder ferait partir en brouillon les cinq demandes suivantes sans que
    personne l'ait voulu.
    """
    avant = reglages_de(conv)
    garde = dict(avant)
    for cle in REGLAGES_CONV:
        if cle not in d:
            continue
        valeur = d.get(cle) or None
        if cle == "priorite" and valeur == "brouillon":
            continue
        if valeur is None:
            garde.pop(cle, None)
        else:
            garde[cle] = valeur
    if garde != avant and ecrire:
        change = [(k, garde.get(k)) for k in REGLAGES_CONV
                  if garde.get(k) != avant.get(k)]
        conv["reglages"] = garde
        murmurer(conv, change)
        sauver(conv)
    # Ce qui part vraiment : l'heritage, mais le brouillon de CETTE demande
    # l'emporte puisqu'on vient de le demander explicitement.
    effectif = dict(garde)
    if d.get("priorite") == "brouillon":
        effectif["priorite"] = "brouillon"
    return effectif


def _vide(titre="Nouvelle conversation", proprietaire=None):
    return {"id": uuid.uuid4().hex[:12], "titre": titre, "proprietaire": proprietaire,
            "cree": time.strftime("%Y-%m-%d %H:%M"), "modifie": time.time(),
            "tours": [], "derniere_sortie": None, "reglages": {},
            "murmures": []}

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
FICHIER_PARC = os.path.join(DOSSIER_CONV, "_parc.json")
# L'instant du reveil. Pendant les premieres secondes, le studio ne sait encore
# rien de personne : les machines s'annoncent toutes les dix secondes et il faut
# les attendre plutot que de conclure a leur absence.
DEMARRE = time.time()
_PARC_ECRIT = [0.0]


def sauver_parc():
    """Ce que le studio sait des machines : carte, memoire, modeles portes.

    Rien de vivant — ni « repond », ni « vu ». Une capacite ne change pas parce
    que le studio a redemarre ; une presence, si. Sans ce fichier, un studio qui
    redemarre ne sait plus rien de personne pendant dix a vingt secondes, et
    refuse pendant ce temps des demandes qu'une machine declaree savait faire.
    Constate le 31 aout : « realvis » demande, le NAS l'a, refus immediat.
    """
    if time.time() - _PARC_ECRIT[0] < 30:
        return
    _PARC_ECRIT[0] = time.time()
    d = {}
    for ident, e in ETAT_NOEUDS.items():
        # « ip » est le seul champ VIVANT qu'on garde, et c'est deliberе : sans
        # elle, le studio ne reconnait pas la machine qui heberge un Ollama tant
        # qu'elle ne s'est pas reannoncee. Pendant cette minute-la, la pause de
        # cette machine ne la protegeait pas et sa carte n'etait pas reservee —
        # une analyse et un rendu se partageaient la carte de quelqu'un qui
        # jouait, sans une ligne de journal. Une adresse perimee ne fait courir
        # aucun risque : la premiere annonce la corrige.
        garde = {k: e[k] for k in ("carte", "vram", "ram", "libre", "ip")
                 if e.get(k) is not None}
        inv = MODELES_NOEUD.get(ident)
        if inv and inv.get("dossiers"):
            garde["dossiers"] = {k: sorted(v)
                                 for k, v in inv["dossiers"].items()}
            garde["quand"] = inv.get("quand")
        if garde:
            d[ident] = garde
    try:
        tmp = FICHIER_PARC + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        os.replace(tmp, FICHIER_PARC)
    except OSError:
        pass


def charger_parc():
    """Relit ce qu'on savait des machines. Aucune n'est declaree presente."""
    try:
        with open(FICHIER_PARC, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return
    if not isinstance(d, dict):
        return
    for ident, garde in d.items():
        if not isinstance(garde, dict):
            continue
        e = ETAT_NOEUDS.setdefault(ident, {})
        for k in ("carte", "vram", "ram", "libre", "ip"):
            if k in garde:
                e[k] = garde[k]
        # Muette jusqu'a preuve du contraire : la premiere annonce dira si elle
        # est la. Ce fichier dit ce qu'elle SAIT FAIRE, pas qu'elle est reveillee.
        e.setdefault("repond", False)
        e.setdefault("vu", 0)
        if isinstance(garde.get("dossiers"), dict):
            MODELES_NOEUD[ident] = {
                "quand": garde.get("quand") or 0,
                "dossiers": {k: set(v) for k, v in garde["dossiers"].items()
                             if isinstance(v, list)}}
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
        # En pause : la machine repond, sa carte va bien, son proprietaire s'en
        # sert. On ne la sert pas.
        if x.get("pause"):
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


async def patienter_machine(cle, tid):
    """Attend une machine capable qui ne repond pas EN CE MOMENT.

    Une machine a agent se tait des qu'elle travaille : sa boucle est
    sequentielle, elle rend ou elle reflechit, elle ne s'annonce pas. Passe
    quarante-cinq secondes de silence, noeuds_pour() la retire — et le studio
    refusait alors la demande en bloc, en accusant au passage une autre machine
    mise en pause. Constate le 31 aout : « realvis » demande explicitement, le
    NAS l'a et travaille, et l'utilisateur s'entend repondre que le PC est en
    pause depuis plus de trente minutes.

    Une indisponibilite passagere n'est pas une absence. On attend tant qu'une
    machine capable donne signe de vie, et l'on rend la main quand elle se tait
    vraiment — les messages d'erreur habituels reprennent alors leur role.
    """
    def occupees():
        besoin = CATALOGUE[cle].get("vram", 0)
        vues = []
        for x in tous_les_noeuds():
            if x.get("pause") or x.get("local"):
                continue
            e = ETAT_NOEUDS.get(x["id"]) or {}
            # Jamais vue depuis le demarrage : on ne sait rien d'elle, ni sa
            # carte ni ce qu'elle porte. L'attendre serait attendre au hasard.
            if not e.get("vram") or _vram_utile(x["id"]) < besoin:
                continue
            if manquants(cle, x["id"]):
                continue
            # La meme tolerance que _attendre_le_noeud : un agent occupe peut
            # manquer plusieurs battements, un agent mort n'en donne plus aucun.
            # Vivante, ou pas encore revenue d'un redemarrage du studio. Dans
            # les premieres secondes ETAT_NOEUDS ne porte que ce qui vient du
            # disque, et « vu » vaut zero pour tout le monde : conclure a
            # l'absence a cet instant, c'est refuser une demande parce que le
            # studio vient de repartir.
            if (time.time() - (e.get("vu") or 0) < 4 * SILENCE_MAX
                    or time.time() - DEMARRE < 4 * SILENCE_MAX):
                vues.append(x)
        return vues

    dort = occupees()
    if not dort:
        return None
    noms = " ou ".join(x.get("titre", x["id"]) for x in dort)
    journal(tid, f"{noms} travaille — ta demande attend son tour")
    fin = time.time() + ATTENTE_CARTE
    while time.time() < fin:
        await asyncio.sleep(5)
        cible = choisir_noeud(cle)
        if cible:
            journal(tid, f"{cible.get('titre', cible['id'])} s'est liberee")
            return cible
        if not occupees():
            return None
    return None


class MachineEnPause(Exception):
    """Une machine EN PAUSE saurait faire ce travail, et aucune autre.

    Ni un echec ni une attente : une demande a mettre de cote. Portee jusqu'a
    travailleur(), qui l'arme au lieu de l'echouer. Le refus d'avant rendait la
    main a l'utilisateur avec sa demande a retaper le jour ou la machine
    revenait — et personne ne se souvient d'une demande une demi-heure plus tard.

    Une Exception et non une RuntimeError : PanneNoeud et MachineIncapable en
    heritent, et soumettre_robuste les rattrape pour reprendre AILLEURS. Passer
    par la meme porte enverrait chercher une autre machine a une demande dont on
    vient justement d'etablir qu'il n'y en a pas.
    """

    def __init__(self, cle, dormantes):
        self.cle = cle
        self.noeuds = [x["id"] for x in dormantes]
        self.titres = [x.get("titre", x["id"]) for x in dormantes]
        super().__init__(" et ".join(self.titres) + " est en pause")

    @property
    def refus(self):
        """Le message d'avant, garde pour le reglage a zero : quand personne ne
        veut de l'attente, refuser tout de suite reste la bonne reponse."""
        return (f"{' et '.join(self.titres)} pourrait faire ce travail, mais "
                f"elle est en pause depuis plus de "
                f"{PREFERENCES['pause_propose']} minutes. Reactive-la dans "
                f"/admin, ou demande quelque chose qu'une autre machine sait "
                f"faire.")


async def patienter_pause(cle, tid):
    """Attend qu'une machine en pause revienne, si l'attente a un sens.

    Rend la machine des qu'elle est de nouveau eligible, ou None s'il n'y a
    aucune machine en pause capable de ce travail — les messages d'erreur
    habituels reprennent alors la main.

    Leve si la pause dure depuis plus longtemps que le reglage : faire patienter
    une demi-heure pour une machine que personne ne compte rallumer, c'est
    perdre le temps de quelqu'un poliment.
    """
    def dormantes():
        besoin = CATALOGUE[cle].get("vram", 0)
        return [x for x in tous_les_noeuds()
                if x.get("pause")
                and ETAT_NOEUDS.get(x["id"], {}).get("repond")
                and _vram_utile(x["id"]) >= besoin
                and (x.get("local") or not manquants(cle, x["id"]))]

    en_pause_ = dormantes()
    if not en_pause_:
        return None
    limite = PREFERENCES["pause_propose"] * 60
    if all(time.time() - x["pause"] >= limite for x in en_pause_):
        # Plus un refus : une demande a mettre de cote. travailleur() decide
        # quoi en faire — c'est lui qui sait qu'il ne doit pas rester la.
        raise MachineEnPause(cle, en_pause_)
    noms = " ou ".join(x.get("titre", x["id"]) for x in en_pause_)
    journal(tid, f"{noms} en pause — ta demande attend son retour, "
                 f"annule-la si tu preferes")
    while True:
        await asyncio.sleep(15)
        cible = choisir_noeud(cle)
        if cible:
            journal(tid, f"{cible.get('titre', cible['id'])} est revenue")
            return cible
        restantes = dormantes()
        if not restantes:
            return None
        if all(time.time() - x["pause"] >= limite for x in restantes):
            # On a patiente le temps prevu et la pause n'a pas bouge : la meme
            # mise de cote que si elle avait ete longue des le depart. Le
            # travailleur retourne servir la file au lieu de dormir ici.
            raise MachineEnPause(cle, restantes)


def echouer(tid, quoi):
    """Termine une demande en erreur, le tour de la conversation compris.

    Le « except Exception » d'executer() le fait deja pour ce qui casse pendant
    le travail. Une demande armee, elle, n'est plus dans aucun executer quand
    son attente expire : sans cette fonction elle serait restee « en cours »
    pour toujours dans la conversation, ce qui est la pire des trois fins.
    """
    t = TACHES.get(tid) or {}
    conv = CONVERSATIONS.get(t.get("conversation"))
    if conv:
        enregistrer_tour(conv, tid, t.get("demande", ""), {}, None, None, [],
                         "erreur", quoi)
    journal(tid, f"ERREUR : {quoi}", etat="erreur")


def armer(tid, e):
    """Met la demande de cote jusqu'au retour de la machine. Vrai si c'est fait.

    « arme_depuis » vit sur l'entree de file et non dans ARMEES, pour deux
    raisons. L'echeance se compte depuis la PREMIERE mise de cote : une machine
    qui sort de pause puis y retourne rearmerait sinon la demande a chaque
    aller-retour, et l'expiration n'arriverait jamais. Et elle est ecrite dans
    _file.json, donc un redemarrage du studio ne remet pas le compteur a zero.
    """
    heures = PREFERENCES["armee_heures"]
    if heures <= 0 or (TACHES.get(tid) or {}).get("annulee") or tid not in EN_FILE:
        return False
    depuis = EN_FILE[tid].get("arme_depuis")
    if not isinstance(depuis, (int, float)):
        depuis = EN_FILE[tid]["arme_depuis"] = time.time()
        sauver_file()
    ARMEES[tid] = {"quand": time.time(), "depuis": depuis, "cle": e.cle,
                   "noeuds": list(e.noeuds), "titres": list(e.titres),
                   "jusqua": depuis + heures * 3600}
    # DEJA EXPIREE. « depuis » est persiste dans la file : un studio arrete
    # vingt heures avec une demande armee a douze la remet en file au reveil,
    # refait une analyse complete au modele de langage, et annonçait
    # « pendant encore -480 min » avant de la tuer trente secondes plus tard.
    # On ne l'arme pas, on la termine — et l'analyse est economisee.
    reste = depuis + heures * 3600 - time.time()
    if reste <= 0:
        ARMEES.pop(tid, None)
        journal(tid, f"{' et '.join(e.titres)} n'est pas revenue dans le delai "
                     f"prevu — la demande est abandonnee", etat="erreur")
        echouer(tid, "la machine n'est pas revenue a temps")
        EN_FILE.pop(tid, None)
        sauver_file()
        return
    journal(tid, f"{' et '.join(e.titres)} pourrait faire ce travail, mais elle "
                 f"est en pause depuis plus de {PREFERENCES['pause_propose']} "
                 f"minutes. Ta demande est gardee en attente : elle partira "
                 f"toute seule des que la machine reviendra, pendant encore "
                 + (f"{reste / 3600:.0f} h" if reste >= 5400
                    else f"{reste / 60:.0f} min")
                 + ". Retire-la de la file si tu preferes demander autre chose.")
    return True


async def _relancer_armee(tid, msg):
    """Remet une demande armee dans la file, avec exactement ce qu'elle portait.

    A la QUEUE de la file et non en tete : elle a attendu des heures, quelques
    minutes de plus ne se sentent pas, et passer devant ceux qui patientent
    depuis dix minutes serait plus surprenant que juste.
    """
    # Desarmee AVANT le moindre await : la fin de pause et le battement de la
    # machine arrivent souvent dans la meme seconde, et les deux reveils
    # auraient mis la meme demande deux fois dans la file — donc deux images.
    a = ARMEES.pop(tid, None)
    if a is None:
        return False
    r = EN_FILE.get(tid)
    conv = CONVERSATIONS.get((r or {}).get("conversation"))
    if (TACHES.get(tid) or {}).get("annulee"):
        return False
    if not r or not conv:
        # NI ZOMBIE, NI SILENCE. La conversation peut avoir ete purgee pendant
        # l'attente — purger_fermees() tourne dans le meme veilleur, et
        # « armee_heures » monte a 168. On sortait alors sans rien dire, en
        # laissant l'entree dans EN_FILE : elle etait reecrite dans _file.json
        # a chaque sauvegarde, la tache restait « en cours » pour toujours, et
        # au demarrage suivant reprendre_file() la comptait perdue puis
        # deplaçait TOUT le fichier en .perdu.
        journal(tid, "la conversation de cette demande a disparu pendant "
                     "l'attente — elle est abandonnee", etat="erreur")
        echouer(tid, "conversation fermee pendant l'attente")
        EN_FILE.pop(tid, None)
        sauver_file()
        return False
    journal(tid, msg, etat="en cours")
    ATTENTE.append(tid)
    sauver_file()
    await FILE_ATTENTE.put({"tid": tid, "texte": r.get("texte", ""), "conv": conv,
                            "image": r.get("image"), "modele": r.get("modele"),
                            "taille": r.get("taille"),
                            "priorite": r.get("priorite", ""),
                            "noeud": r.get("noeud"), "plan": r.get("plan"),
                            "modele_choisi": r.get("modele_choisi", False),
                            "graine": r.get("graine")})
    return True


async def reveiller_armees(ident=None, plancher=True):
    """Relance les demandes armees qu'une machine peut enfin servir.

    On ne demande pas « la pause est-elle finie ? » mais « choisir_noeud rend-il
    quelque chose ? » : c'est la seule question dont la reponse fasse repartir le
    travail. Un modele arrive entre-temps, une machine rallumee qui s'annonce,
    une autre carte devenue eligible reveillent donc aussi bien qu'un clic dans
    /admin — et un battement de machine TOUJOURS en pause ne declenche rien.

    « ident » restreint aux demandes qui attendaient CETTE machine : l'annonce
    arrive six fois par minute et par machine, et il n'y a pas de raison de
    reexaminer tout le monde a chaque battement.

    « plancher » vaut pour les battements, pas pour un geste. Le plancher de
    quinze secondes protege d'une machine qui flotte entre pause et travail ;
    un administrateur qui clique « remettre au travail » ne flotte pas, et
    l'attendre faisait annoncer « 0 relancee » a api_admin_pause pendant que
    les demandes repartaient trente secondes plus tard par le veilleur. Mesure
    du 1er septembre : trois demandes armees, reponse « reveillees: 0 », trois
    departs une fois le plancher passe. Un chiffre faux est pire que pas de
    chiffre.
    """
    if not ARMEES or FILE_ATTENTE is None:
        return 0
    partis = 0
    for tid in list(ARMEES):
        a = ARMEES.get(tid) or {}
        if ident and ident not in a.get("noeuds", ()):
            continue
        # Quinze secondes de plancher. Une machine qui bascule entre pause et
        # travail relancerait sinon la demande a chaque aller-retour, et chaque
        # relance coute une analyse complete au modele de langage.
        if plancher and time.time() - a.get("quand", 0) < 15:
            continue
        cible = choisir_noeud(a["cle"]) if a.get("cle") in CATALOGUE else None
        if not cible:
            continue
        if await _relancer_armee(
                tid, f"{cible.get('titre', cible['id'])} est revenue — ta "
                     f"demande repart d'elle-meme"):
            partis += 1
    return partis


def reviser_echeances():
    """Reporte l'echeance des demandes DEJA armees sur le reglage du moment.

    « armee_heures » ne valait que pour les demandes a venir : l'echeance etait
    figee a l'armement, et baisser le reglage ne raccourcissait rien. Mesure du
    1er septembre — douze heures ramenees a une, la demande deja armee gardait
    12,00 h devant elle. Un reglage qui ment sur ce qu'il fait est pire qu'un
    reglage absent : l'administrateur croit avoir coupe l'attente et s'en va.

    Le calcul repart de « depuis », la PREMIERE mise de cote, et jamais de
    maintenant : sinon un simple passage dans /admin repousserait l'attente de
    toutes les demandes en cours, ce qui est exactement le rearmement que
    « depuis » avait ete introduit pour empecher.
    """
    heures = PREFERENCES["armee_heures"]
    for a in ARMEES.values():
        neuve = a.get("depuis", 0) + heures * 3600
        # Marquee quand c'est le REGLAGE qui vient de faire passer l'echeance,
        # et non le temps : expirer_armees ne doit pas accuser une machine de
        # n'etre pas revenue quand c'est l'administration qui a coupe court.
        #
        # EFFACEE dans le cas contraire, et c'est le point : remonter le delai
        # apres l'avoir baisse laissait la marque en place, et la demande, en
        # expirant des heures plus tard pour la vraie raison, accusait encore
        # un raccourcissement qui n'existait plus.
        if neuve <= time.time() < a.get("jusqua", 0):
            a["raccourcie"] = True
        else:
            a.pop("raccourcie", None)
        a["jusqua"] = neuve


async def expirer_armees():
    """Une demande gardee en attente n'est pas gardee pour toujours.

    Passe le delai, on le DIT et on rend la main. Une demande qui aurait
    silencieusement disparu du panneau serait pire que le refus qu'on vient de
    remplacer : au moins le refus arrivait pendant que l'utilisateur regardait.
    """
    for tid in list(ARMEES):
        a = ARMEES.get(tid) or {}
        if time.time() < a.get("jusqua", 0):
            continue
        ARMEES.pop(tid, None)
        EN_FILE.pop(tid, None)
        sauver_file()
        if a.get("raccourcie"):
            echouer(tid, "le delai d'attente a ete raccourci dans /admin : ta "
                         "demande a ete retiree de l'attente. Relance-la quand "
                         "la machine sera la.")
            continue
        heures = max(1, round((a.get("jusqua", 0) - a.get("depuis", 0)) / 3600))
        echouer(tid, f"{' et '.join(a.get('titres') or ['la machine'])} n'est "
                     f"pas revenue en {heures} h : ta demande a ete retiree de "
                     f"l'attente. Relance-la quand la machine sera la.")


# Ce qu'on a mesure, par (machine, moteur, taille). Reconstruit depuis les
# conversations, qui portent deja tout : « noeud », « modele », « taille » et
# « secondes » sont sur chaque tour termine.
_DUREES = {"quand": 0.0, "table": {}}
FRAICHEUR_DUREES = 120
# En dessous, on se tait. Deux rendus ne font pas une mediane : annoncer
# « environ quatre minutes » sur un seul echantillon, c'est promettre au hasard.
ASSEZ_DE_MESURES = 3


def _relever_durees(pid=None):
    """Range les durees passees par (machine, moteur, taille), puis par
    (machine, moteur), puis par moteur seul — du plus precis au plus general.

    PAR PERSONNE. Le journal dit « d'apres TES rendus precedents » : il ne peut
    pas compter ceux d'un autre compte. C'etait faux — CONVERSATIONS porte tout
    le studio — et ça revelait accessoirement le volume d'activite de quelqu'un
    d'autre. Un chiffre annonce comme personnel qui ne l'est pas fait perdre la
    confiance des qu'il ne colle pas.
    """
    table = {}
    for conv in CONVERSATIONS.values():
        if pid is not None and conv.get("proprietaire") != pid:
            continue
        for t in conv.get("tours") or []:
            s_ = t.get("secondes")
            cle_, ou = t.get("modele"), t.get("noeud")
            if not s_ or not cle_ or t.get("etat") != "fini":
                continue
            # L'esquisse ne predit pas la version soignee : un quart des etapes,
            # et c'est justement ce qu'on cherche a comparer.
            if t.get("esquisse"):
                continue
            for k in ((ou, cle_, t.get("taille")), (ou, cle_), (cle_,)):
                table.setdefault(k, []).append(float(s_))
    return table


def duree_typique(ident, cle, taille=None, pid=None):
    """Combien ça a pris les fois d'avant, ou None si l'on ne sait pas.

    La mediane et non la moyenne : un rendu qui a attendu une carte occupee
    tirerait la moyenne sans rien dire de ce qui va se passer maintenant.
    """
    if (time.time() - _DUREES["quand"] > FRAICHEUR_DUREES
            or _DUREES.get("qui") != pid):
        _DUREES["table"], _DUREES["quand"] = _relever_durees(pid), time.time()
        _DUREES["qui"] = pid
    for k in ((ident, cle, taille), (ident, cle), (cle,)):
        v = _DUREES["table"].get(k)
        if v and len(v) >= ASSEZ_DE_MESURES:
            v = sorted(v)
            return v[len(v) // 2], len(v)
    return None, 0


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
            # Plus d'echappatoire ici non plus. Lancer l'analyse « malgre tout »
            # revenait a la poser a cote d'un rendu sur la meme carte, ce que la
            # regle interdit sans exception. Vingt minutes d'occupation ne sont
            # pas une attente, c'est une panne : on la nomme.
            raise RuntimeError(
                "ComfyUI occupe cette carte depuis vingt minutes — rien n'a ete "
                "lance dessus. Regarde ce qu'il calcule.")
        if tid and time.time() - dernier > 60:
            dernier = time.time()
            journal(tid, f"toujours en attente de la carte ({int(time.time()-debut)} s)")
        await asyncio.sleep(2)

def noeud_de_l_ollama():
    """La machine a agent qui heberge l'adresse PRINCIPALE, s'il y en a une.

    Il y a maintenant plusieurs adresses et cerveau() les reconnait toutes ;
    cette fonction ne sert plus qu'aux quelques endroits qui parlent de « l'
    Ollama du studio » au singulier. Deux facons de reconnaitre une machine,
    c'etait une de trop.
    """
    return cerveau(OLLAMA).get("noeud")


async def appeler_ollama(texte, image_b64=None, systeme=None, json_mode=True,
                         modele=None, temperature=0.4, tid=None, garder=0):
    """Un appel au modele de langage, chronometre.

    Une demande en fait trois — aiguillage, enrichissement, traduction — et le
    journal n'en montrait qu'un seul horodatage : cent secondes disparaissaient
    entre deux lignes sans qu'on sache lesquelles. On ne peut pas reduire ce
    qu'on ne mesure pas.

    Le compte est ecrit une seule fois, ici, plutot qu'a chaque appelant : trois
    endroits a instrumenter, c'est deux occasions d'en oublier un.
    """
    depart_ = time.time()
    try:
        return await _appeler_llm(texte, image_b64, systeme, json_mode, modele,
                                  temperature, tid, garder)
    finally:
        mis = time.time() - depart_
        # Sous la seconde, la ligne n'apprend rien et encombre le fil.
        if tid and mis >= 1:
            journal(tid, f"  … {mis:.0f} s")


def consigner_appel_distant(*a, **kw):
    """Le meme, mais qui ne peut pas emporter la demande avec lui.

    L'image est deja generee, payee et ecrite sur le disque quand on arrive
    ici : perdre le rendu parce qu'un fournisseur a rendu un decompte de jetons
    inattendu serait payer deux fois. Une comptabilite fausse vaut mieux qu'un
    rendu perdu — et elle le dit.
    """
    try:
        return _consigner_sans_filet(*a, **kw)
    except Exception as e:
        print(f"  cout non consigne ({type(e).__name__} : {str(e)[:120]})",
              flush=True)


async def _appeler_llm(texte, image_b64=None, systeme=None, json_mode=True,
                       modele=None, temperature=0.4, tid=None, garder=0):
    """temperature : 0.4 convient a la description libre d'une image. L'aiguillage
    et la traduction sont des taches de classification, pas de creation — a 0.4 la
    meme demande partait tantot en question, tantot en image (mesure). La part
    creative revient au modele de diffusion, pas a l'aiguilleur."""
    # Un appel distant ne touche pas la carte : ni attente, ni chargement de
    # 18 Go. C'est aussi pour cela qu'il est tente AVANT la mise en file.
    loin = ("" if image_b64
            else llm_distant_possible(texte, (TACHES.get(tid) or {}).get("proprietaire")))
    # La place se prend AVANT le depart, pas au retour. llm_distant_possible a
    # beau dire oui, le compteur qu'il interroge ne bougera qu'une fois la
    # reponse revenue : sans cette reservation, trois travailleurs partis
    # ensemble franchissaient tous les trois un plafond d'un seul appel.
    _place = (reserver_nuage((TACHES.get(tid) or {}).get("proprietaire"))
              if loin else None)
    if loin and _place is None:
        journal(tid, f"plafond du mois atteint "
                     f"({PREFERENCES.get('plafond_nuage')} appels distants) "
                     f"— le modele local prend le relais")
        loin = ""
    if loin:
        _depart_loin = time.time()
        try:
            rendu = await fournisseurs.texte(
                loin, cle_de(loin), texte, systeme, temperature, json_mode,
                modele_de(loin) or None)
            # Ce que cet appel aura coute, tel que le fournisseur le compte
            # lui-meme. Les octets en plus des jetons : Mammouth et les
            # agregateurs ne rendent pas toujours d'usage, et une reponse
            # mesuree en octets vaut mieux qu'une case vide.
            consigner_appel_distant(
                loin, "llm", (TACHES.get(tid) or {}).get("proprietaire"),
                time.time() - _depart_loin,
                octets=len(rendu.encode("utf-8")),
                jetons=fournisseurs.jetons_du_dernier_appel())
            return rendu
        except fournisseurs.EchecFournisseur as e:
            # Le message du fournisseur remonte tel quel : « modele inconnu » et
            # « cle refusee » ne se corrigent pas de la meme facon.
            journal(tid, f"{fournisseurs.LLM[loin]['titre']} indisponible ({e})"
                         f" — le modele local prend le relais")
        finally:
            # Apres consigner_appel_distant, donc : la place ne se rend qu'une
            # fois le compteur a jour, sinon le suivant retrouverait le trou
            # qu'on vient de boucher.
            liberer_nuage(_place)

    # POURQUOI cet appel n'est pas parti au loin. La question s'est posee ce
    # matin et le journal ne savait pas y repondre : l'analyse est partie chez
    # Anthropic en 5 s, et l'appel SUIVANT — meme demande, meme compte, sans
    # image — est reste local pour soixante-quinze secondes, sans un mot. Une
    # chaine dont on ignore quel maillon est local ne se regle pas. La raison
    # etait deja calculee, mais seule l'analyse la disait : les deux autres
    # appels de la chaine se taisaient.
    if not loin and tid:
        pourquoi_ = raison_du_local(texte, image_b64,
                                    (TACHES.get(tid) or {}).get("proprietaire"))
        if not pourquoi_ and fournisseur_dispo("llm"):
            # Un fournisseur est configure et pourtant on reste ici : le dire
            # sans savoir pourquoi vaut mieux que se taire.
            pourquoi_ = "cet appel reste sur le modele local"
        if pourquoi_:
            journal(tid, pourquoi_)
    corps = corps_ollama(texte, image_b64, systeme, json_mode, modele,
                         temperature, garder)
    # La plus petite carte capable, AVANT celle du studio. Une analyse tient sur
    # n'importe quelle carte ; occuper la meilleure pour reflechir, c'est la
    # retirer du rendu qu'elle seule fait vite.
    #
    # Jamais pour une image : le modele de vision n'est pas celui d'ecriture, et
    # une machine peut porter l'un sans l'autre. On garde alors l'Ollama du
    # studio, dont on sait ce qu'il contient.
    # EMPRUNTER COUTE CHER. Mesure du 31 aout, la meme question a chaque
    # machine : 3,8 s par l'Ollama du studio en direct, 74,8 s en la posant au PC
    # par son agent, 162,6 s au NAS. Le chemin de l'agent ajoute son sondage, son
    # chargement de modele et son tour de boucle. Une demande complete est passee
    # de vingt secondes d'analyse a CINQ MINUTES QUARANTE.
    #
    # « La petite carte reflechit pendant que la grosse rend » reste la regle,
    # mais elle ne vaut qu'a partir du moment ou la carte du studio est prise.
    # Tant qu'elle est libre, router ailleurs ferait perdre deux minutes pour
    # epargner une carte que personne ne reclame.
    await attendre_carte_libre(tid)
    # CHAQUE Ollama en direct, dans l'ordre rendu par cerveaux_utilisables() :
    # jamais une machine en pause, une carte libre avant une carte occupee, et a
    # egalite la plus petite. Le detour par l'agent d'une machine reste en
    # dernier recours — mesure du 31 aout, la meme question coute 3,8 s en
    # direct, 74,8 s au PC par son agent et 162,6 s au NAS.
    cerveaux = cerveaux_utilisables(image=bool(corps.get("images")))
    if not cerveaux:
        journal(tid, _pourquoi_aucun_cerveau())
    panne = None
    # UNE echeance pour toute la boucle, et non une par adresse. Attendre
    # ATTENTE_CARTE a chaque adresse faisait, a trois adresses et trois appels
    # par demande, jusqu'a quatre heures avant le premier repli.
    echeance = time.time() + ATTENTE_CARTE
    for rang_, (url, ident) in enumerate(cerveaux):
        titre_ol = (noeud(ident) or {}).get("titre", ident) if ident else url
        ici = corps_ici(corps, url, tid if len(cerveaux) == 1 else None)
        if ici is None:
            # Une image a lire et pas de modele de vision ici : substituer en
            # rendrait une description inventee, sans que rien ne le dise.
            continue
        # La carte de la machine qui heberge cet Ollama : une carte ne fait
        # qu'une tache a la fois, analyse comprise. PAS d'echappatoire — la
        # version qui lançait l'analyse « malgre tout » au bout de vingt
        # secondes s'installait a cote d'un rendu sur la meme carte.
        verrou_ol = verrou_noeud(ident) if ident else None
        if verrou_ol is not None:
            if verrou_ol.locked() and tid:
                journal(tid, f"{titre_ol} calcule — l'analyse attend que sa "
                             f"carte se libere")
            reste = echeance - time.time()
            if reste <= 0:
                panne = panne or RuntimeError(
                    f"aucune carte ne s'est liberee en "
                    f"{ATTENTE_CARTE // 60} minutes — rien n'a ete lance.")
                continue
            try:
                await asyncio.wait_for(verrou_ol.acquire(), timeout=reste)
            except asyncio.TimeoutError:
                panne = RuntimeError(
                    f"{titre_ol} n'a pas libere sa carte en "
                    f"{ATTENTE_CARTE // 60} minutes — rien n'a ete lance dessus.")
                continue
            # LA PAUSE A PU ARRIVER PENDANT L'ATTENTE. On a pu patienter une
            # demi-heure derriere un rendu ; entre-temps son proprietaire a très
            # bien pu mettre la machine en pause pour jouer, et le filtre du
            # debut de boucle date d'avant l'attente. Charger un modele
            # maintenant, ce serait exactement ce que la pause interdit.
            if (noeud(ident) or {}).get("pause"):
                journal(tid, f"{titre_ol} est passee en pause pendant l'attente "
                             f"— on cherche ailleurs")
                verrou_ol.release()
                continue
        try:
            # BORNE PLUS COURTE POUR UNE IMAGE. Les neuf cents secondes du
            # delai ordinaire sont la pour qu'une chanson longue aboutisse ;
            # appliquees a une lecture d'image sur une carte qui deborde, elles
            # font perdre un quart d'heure avant d'essayer la machine d'a cote,
            # qui repond en dix-neuf secondes. Mesure du 31 aout : 919 s, dont
            # 900 perdues.
            # « Reste-t-il un repli » ne se compte pas en RANGS. Une adresse
            # plus loin dans la liste peut n'avoir aucun modele qui sache voir —
            # corps_ici() rend None et la boucle passe — ou etre passee en
            # pause. On comptait donc un repli qui n'existait pas, et la borne
            # courte transformait une lecture lente en echec sec : « le modele
            # de vision n'a pas repondu » au bout de cinq minutes, la ou neuf
            # cents secondes auraient rendu la description.
            reste_ = any(corps_ici(corps, u) is not None
                         and not (i and (noeud(i) or {}).get("pause"))
                         for u, i in cerveaux[rang_ + 1:])
            rendu = await _ollama_local(
                ici, url, 300 if (ici.get("images") and reste_) else 900)
            # Seulement si on l'a demande CHAUD : sans « garder », Ollama l'a
            # deja relache et il n'y a rien a fermer derriere nous.
            if garder and tid:
                _CHAUD[tid] = (url, ici.get("model") or "")
            return rendu
        except Exception as e:
            panne = e
            if len(cerveaux) > 1:
                journal(tid, f"{titre_ol} n'a pas repondu "
                             f"({type(e).__name__}) — on essaie ailleurs")
        finally:
            if verrou_ol is not None:
                verrou_ol.release()
    if panne is None:
        panne = RuntimeError(_pourquoi_aucun_cerveau())
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
    # « garder » a zero dechargeait le modele apres CHAQUE appel. Mesure : 3,8 s
    # par appel contre 0,4 s a chaud — huit a quinze secondes de rechargement pur
    # avant chaque rendu, une demande en faisant trois (aiguillage,
    # enrichissement, traduction). C'etait le plus gros gain disponible, et il ne
    # depend d'aucun modele.
    #
    # Une minute, pas davantage : le modele occupe la memoire de la carte tant
    # qu'il y reste, et cette carte sert aussi a rendre. Une minute couvre la
    # rafale d'une demande sans immobiliser la machine pour la suivante.
    corps = {"model": modele or MODELE_LLM, "prompt": texte, "stream": False,
             "keep_alive": garder or GARDER_LLM,
             "options": {"temperature": temperature}}
    if systeme: corps["system"] = systeme
    if json_mode: corps["format"] = "json"
    if image_b64: corps["images"] = [image_b64]
    return corps


def _echec_de_chargement(texte):
    """Ce message dit-il que le modele n'a pas pu etre charge.

    On n'ecarte pas un modele sur une panne passagere — reseau coupe, Ollama qui
    redemarre. Ces trois formules sont celles du chargement impossible, et elles
    ne varient pas d'une version a l'autre.
    """
    t = (texte or "").lower()
    return any(m in t for m in ("error loading model", "process has terminated",
                                "failed to initialize"))


def _casse_ici(url, nom):
    """Ce modele a-t-il deja echoue A CETTE ADRESSE."""
    return (url or OLLAMA, nom) in MODELES_CASSES


def _ecarter_modele(nom, pourquoi, url=None):
    """Retire un modele du choix SUR CETTE MACHINE, une fois, en le disant.

    Par machine, et non pour tout le studio. qwen2.5vl:7b fait 5,97 Go : il ne
    se charge pas sur la GTX 1060 de 5,9 Go et tourne tres bien sur la 2080 Ti.
    L'ecarter partout au premier echec interdisait, pour tout le studio et
    jusqu'au redemarrage, le seul modele mesure comme correct en lecture
    d'image. Tant qu'il n'y avait qu'une adresse la question ne se posait pas.
    """
    global MODELE_ECRITURE
    cle = (url or OLLAMA, nom)
    if not nom or cle in MODELES_CASSES:
        return
    MODELES_CASSES[cle] = (pourquoi or "")[:200]
    print(f"  [ollama] {nom} ne se charge pas sur {cle[0]}, il y est ecarte "
          f"— {MODELES_CASSES[cle]}", flush=True)
    # Un CACHE s'oublie, un REGLAGE non. « MODELE_ECRITURE » etait un cache
    # quand cette ligne a ete ecrite ; depuis, STUDIO_LLM_ECRITURE le pose
    # explicitement. Un seul echec de chargement — une carte pleine par un rendu
    # concurrent suffit — effaçait alors le choix de l'utilisateur jusqu'au
    # prochain redemarrage, sans un mot.
    if MODELE_ECRITURE == nom and not MODELE_ECRITURE_IMPOSE:
        MODELE_ECRITURE = ""      # le prochain appel en choisira un autre


def corps_ici(corps, url, tid=None):
    """Le meme corps, avec un modele que CET Ollama porte vraiment.

    Rend None quand cette adresse ne convient pas — le seul cas est celui d'une
    image a lire sur une machine sans modele de vision. Substituer alors un
    modele d'ecriture rendrait une description inventee, sans que rien ne
    l'indique : c'est le pire des trois resultats possibles, devant l'erreur et
    devant l'absence de reponse.
    """
    voulu = corps.get("model") or MODELE_LLM
    if voulu == MODELE_POUR_ECRIRE:
        return dict(corps, model=modele_ecriture_de(url))
    if corps.get("images"):
        # DES QU'IL Y A UNE IMAGE, le meilleur modele voyant de cette machine —
        # meme si celui qu'on demandait sait voir aussi.
        #
        # La capacite n'est pas la competence, et c'est la mesure qui l'a dit.
        # gemma3:4b declare « vision » et repond en une seconde ; il a pourtant
        # classe « decris cette image » comme une demande de RENDU, et l'image
        # n'a jamais ete regardee. qwen2.5vl:7b, deux fois plus gros, l'a lue
        # correctement. Se contenter de « sait-il voir ? » laissait donc passer
        # exactement le defaut qu'on croyait fermer.
        #
        # Le plus gros, faute de mieux : c'est le seul classement dont on
        # dispose sans faire passer un examen a chaque modele, et il colle a la
        # seule mesure qu'on ait. Le texte, lui, garde le modele rapide — c'est
        # tout l'interet de choisir par appel plutot qu'une fois pour toutes.
        # Sauf si le reglage NOMME le modele voyant : STUDIO_VISION existe
        # pour ca, et le passer sous silence en faisait un reglage mort. La
        # regle du plus gros reste le defaut, pas un veto.
        if voulu == MODELE_VISION and not _casse_ici(url, voulu)                 and _sait_voir_ici(url, voulu):
            return corps
        voyant = modele_vision_de(url)
        if not voyant:
            return None
        if voyant != voulu:
            journal(tid, f"une image est jointe : {voyant} plutot que {voulu}")
        return corps if voyant == voulu else dict(corps, model=voyant)
    if _sait_lire_ici(url, voulu):
        return corps
    remplacant = modele_ecriture_de(url)
    if not remplacant or remplacant == voulu:
        return corps
    journal(tid, f"{voulu} n'est pas installe la — {remplacant} a sa place")
    return dict(corps, model=remplacant)


def _pourquoi_aucun_cerveau():
    """Aucun Ollama utilisable : dire lequel, et pourquoi.

    « Le modele local ne repond pas » n'aide personne quand la cause est une
    machine que son proprietaire vient de mettre en pause pour jouer.
    """
    dorment = []
    for url in OLLAMAS:
        ident = cerveau(url).get("noeud")
        if ident and (noeud(ident) or {}).get("pause"):
            dorment.append((noeud(ident) or {}).get("titre", ident))
    if dorment:
        quoi = ("sont en pause — leurs modeles de langage avec elles"
                if len(dorment) > 1 else
                "est en pause — son modele de langage avec elle")
        return f"{' et '.join(dorment)} {quoi}"
    return "aucun modele de langage joignable"


async def _ollama_local(corps, url=None, secondes=900):
    """L'appel lui-meme, une fois la carte reservee.

    Il ne rattrape rien : le repli sur une autre machine appartient a
    appeler_ollama, qui doit d'abord relacher la carte — sans quoi le repli
    demanderait la carte qu'on tient encore, et s'attendrait lui-meme.
    """
    # 900 s par defaut : un gros modele qui deborde sur le processeur met plus
    # longtemps que la minute d'un 7B, et une coupure ici rend une chanson
    # muette. L'appelant raccourcit quand il a une machine de rechange sous la
    # main — voir la lecture d'image.
    to = aiohttp.ClientTimeout(total=secondes)
    async with aiohttp.ClientSession(timeout=to) as s:
        async with s.post(f"{url or OLLAMA}/api/generate", json=corps) as r:
            if r.status >= 400:
                # Depuis la mise a jour d'Ollama, un modele qui ne s'initialise
                # pas rend un 500 au lieu d'un 200 avec un champ « error ». Le
                # tri ci-dessous ne le voyait donc plus, et le modele etait
                # redemande a chaque appel — quatorze secondes perdues a chaque
                # fois, pour la meme panne definitive.
                brut_ = (await r.text())[:300]
                if _echec_de_chargement(brut_):
                    _ecarter_modele(corps.get("model") or "", brut_, url)
                raise RuntimeError(f"ollama {r.status} : {brut_[:160]}")
            d = await r.json()
            rep_ = d.get("response", "")
            if not rep_.strip() and d.get("error"):
                # Ollama a repondu 200 avec un champ « error » : le modele
                # existe, il ne se CHARGE pas.
                _ecarter_modele(corps.get("model") or "", str(d["error"]), url)
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


# Analyser sur la plus PETITE carte capable, plutot que sur la plus grosse.
# C'est contre-intuitif et c'est le bon sens du parc : une analyse coute
# quelques secondes a n'importe quelle carte, un rendu coute des minutes a la
# meilleure. Occuper la grosse pour reflechir, c'est la retirer du travail
# qu'elle seule sait faire vite. STUDIO_ANALYSE_PETITE=0 revient a l'ancien
# ordre, si la mesure devait donner tort a la regle.
ANALYSE_PETITE = os.environ.get("STUDIO_ANALYSE_PETITE", "1") != "0"
# Combien de temps Ollama garde le modele en memoire entre deux appels.
GARDER_LLM = os.environ.get("STUDIO_LLM_GARDER") or "60s"
# Au-dela, une analyse empruntee ne vaut plus la peine. Mesure du 31 aout : un
# seul appel au modele du NAS a mis 500 SECONDES — le studio l'avait choisi
# parce que sa propre carte etait prise, ce qui etait juste, mais rien ne bornait
# l'emprunt. Attendre cent secondes une carte occupee vaut mieux que cinq cents
# secondes ailleurs. Passe ce delai on renonce et l'on attend la sienne.
ANALYSE_MAX = int(os.environ.get("STUDIO_ANALYSE_MAX") or 90)


def noeuds_a_llm():
    """Les machines joignables qui portent un modele de langage.

    Les plus PETITES d'abord : une analyse tient sur n'importe quelle carte, et
    laisser les grosses libres pour les rendus vaut mieux que quelques secondes
    gagnees sur une reflexion. Une machine en pause n'en est pas : son
    proprietaire s'en sert.
    """
    bons = []
    for x in REGISTRE.values():
        e = ETAT_NOEUDS.get(x["id"]) or {}
        if x.get("pause"):
            continue
        if e.get("repond") and e.get("llm") and time.time() - (e.get("vu") or 0) < SILENCE_MAX:
            # LIBRE d'abord, petite ensuite. Prendre la plus petite sans regarder
            # si elle travaille faisait s'empiler trois demandes sur elle pendant
            # que la grosse dormait — la regle « la petite reflechit » devenait
            # « une seule machine reflechit ».
            occupee = 1 if verrou_noeud(x["id"]).locked() else 0
            taille = e.get("vram") or 0
            bons.append((occupee, taille if ANALYSE_PETITE else -taille, x["id"]))
    return [i for _, _, i in sorted(bons)]


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


async def poser_a(ident, corps, tid=None, secondes=900, patience=None):
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
    # « patience » a zero : on ne prend cette carte que si elle est libre TOUT DE
    # SUITE. C'est ce qui permet a l'appelant d'essayer les machines l'une apres
    # l'autre sans perdre vingt secondes sur chacune — la premiere libre repond,
    # et l'on n'attend que si toutes travaillent.
    # None : on attend qu'elle se libere, aussi longtemps qu'il faut. Zero : on
    # ne la prend que si elle est libre a l'instant. Une valeur : ce delai-la.
    attente_ = ATTENTE_CARTE if patience is None else patience
    verrou = verrou_noeud(ident)
    if verrou.locked() and tid and attente_:
        journal(tid, f"{titre} calcule — la question attend sa carte "
                     f"({attente_} s au plus)")
    # Un delai de ZERO ne se passe pas a wait_for : il expire avant d'avoir rien
    # tente, si bien qu'une carte libre repondait « occupee ». Le premier tour
    # echouait donc toujours, et toutes les analyses finissaient par attendre —
    # exactement ce que ce tour existe pour eviter. Sur un verrou libre,
    # acquire() rend la main sans point d'attente : la prise est atomique, et le
    # test qui la precede reste vrai.
    if not attente_:
        if verrou.locked():
            return "", "carte occupee"
        await verrou.acquire()
    else:
        try:
            await asyncio.wait_for(verrou.acquire(), timeout=attente_)
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


async def demander_a_un_noeud(corps, tid=None, secondes=None):
    """La premiere machine qui sait repondre. Rend le texte, ou ""."""
    # Celles dont la carte est libre d'abord. Depuis qu'une carte ne fait qu'une
    # chose a la fois, prendre les machines dans l'ordre du registre faisait
    # attendre deux minutes derriere un rendu alors qu'une autre machine
    # repondait tout de suite. L'ordre relatif est conserve a l'interieur de
    # chaque groupe : le premier de la liste reste le premier des libres.
    # UNE IMAGE NE PASSE PAS PAR ICI. La regle « jamais un modele qui ne sait pas
    # voir » vit dans corps_ici(), et ce chemin-la ne la traverse pas : poser_a
    # remet le corps tel quel a l'agent, qui prend « le premier modele annonce »
    # quand celui demande manque. Sur le NAS, c'est qwen3:4b — aveugle. On
    # obtenait alors une description fluide, confiante et entierement inventee,
    # sans erreur ni ligne de journal. Le studio n'apprend pas d'un agent quels
    # modeles savent voir : il n'annonce que des noms. Tant que ce n'est pas le
    # cas, on refuse plutot que d'inventer.
    if corps.get("images"):
        journal(tid, "lecture d'image : aucune machine joignable en direct, et "
                     "on ne devine pas ce que les autres savent voir")
        return ""
    # PATIENCE nulle, mais PLAFOND large. Zero patience parce qu'attendre une
    # demi-heure la carte d'une machine, par appel, ferait deux heures pour une
    # demande. Mais le plafond de reponse, lui, doit tenir compte de ce que ce
    # chemin coute vraiment : mesure du 31 aout, 162,6 s par l'agent du NAS. Le
    # borner a ANALYSE_MAX (90 s) le condamnait a echouer systematiquement sur
    # cette machine — et il n'y a rien apres lui.
    a_llm = list(noeuds_a_llm())
    libres = [i for i in a_llm if not verrou_noeud(i).locked()]
    for ident in libres + [i for i in a_llm if i not in libres]:
        reponse, erreur = await poser_a(ident, corps, tid,
                                        secondes or 900, patience=0)
        if erreur:
            journal(tid, f"{(noeud(ident) or {}).get('titre', ident)} : {erreur}")
            continue
        if reponse:
            return reponse
    return ""


async def liberer_modele(tid):
    """Referme la rafale de CETTE demande : decharge ce qu'elle a laisse chaud.

    Par demande, et non par nom de modele : deux demandes emploient le meme
    modele, parfois sur deux machines, et l'on ne saurait pas laquelle refermer.
    Rien a faire si elle n'a rien laisse chaud — c'est le cas ordinaire.
    """
    ou = _CHAUD.pop(tid, None)
    if ou:
        await liberer_modele_a(ou[0], ou[1])


async def liberer_modele_a(url, modele):
    """Le dechargement lui-meme, a une adresse precise."""
    ident = cerveau(url).get("noeud")
    if ident and (noeud(ident) or {}).get("pause"):
        # Une machine en pause n'a rien de chaud a nous : on ne s'y adresse plus.
        return
    try:
        to = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=to) as s:
            await s.post(f"{url}/api/generate",
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
                                        modele=MODELE_POUR_ECRIRE)
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
                                        modele=MODELE_POUR_ECRIRE)
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
                                        modele=MODELE_POUR_ECRIRE,
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
        await liberer_modele(tid)


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
                                        modele=MODELE_POUR_ECRIRE,
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
                    modele_force=None, taille=None, priorite="",
                    modele_choisi=False):
    pid = (TACHES.get(tid) or {}).get("proprietaire")
    # Un agrandissement se reconnait a l'ecrit et ne demande rien au modele :
    # ni sujet, ni cadrage, ni style. On tranche donc AVANT de l'appeler — dix
    # secondes epargnees, et surtout aucun risque qu'il decide de REGENERER
    # l'image au lieu de l'agrandir. Sans image jointe, l'execution reprendra la
    # derniere sortie de la conversation ; s'il n'y en a pas, elle le dira.
    # Le classifieur, en second rideau : les expressions ci-dessous couvrent
    # les formulations courantes, lui rattrape les autres — « il me faudrait
    # des mouvements plus naturels » n'etait prevu par aucune.
    # Agrandir, detourer, fluidifier portent tous les trois sur une image qui
    # EXISTE. Sans image jointe ni sortie precedente dans la conversation, ces
    # intentions n'ont aucun sens, et le classifieur n'a pas a pouvoir les
    # proposer : le 31 aout, « un magnifique fond d'ecran du jeu Halo avec
    # Masterchief, pleins de details en bonne qualite et en 1920x1080 » a ete
    # classe « agrandir » avec assez de confiance pour court-circuiter le
    # modele. L'utilisateur a reçu « aucune image a agrandir » pour une demande
    # de CREATION — le studio avait refuse de produire ce qu'on lui demandait,
    # sur la foi d'une devinette.
    #
    # Le garde-fou est structurel plutot que lexical : aucune formule ajoutee au
    # corpus ne rendra jamais un agrandissement possible sans image.
    source_dispo = a_une_image or bool(conv.get("derniere_sortie"))
    # Et une demande COURTE. Le critere est deja celui de veut_agrandir() :
    # « une demande de creation decrit un sujet, et c'est long ; une demande
    # d'agrandissement tient en quelques mots ». Il valait pour les expressions
    # ecrites, il vaut tout autant pour le classifieur, qui voit « 1920x1080 »,
    # « haute definition », « bonne qualite » et conclut « agrandir » sans
    # remarquer qu'on lui a decrit un sujet pendant cent quinze caracteres.
    #
    # Au-dela, on n'ecarte pas l'intention : on la fait confirmer par le modele
    # de langage, dont c'est le travail. Le raccourci n'existe que pour epargner
    # dix secondes sur les cas evidents.
    court = len((texte or "").strip()) <= 70
    # « choisi » et non « force » : depuis que les reglages vivent sur la
    # conversation, « modele_force » peut etre un moteur HERITE de trois
    # demandes plus tot. Ces raccourcis ont ete ecrits pour un moteur choisi
    # POUR CETTE DEMANDE — le desarmer sur un heritage, c'est refuser
    # « detoure-la » a quelqu'un qui a regle un moteur hier. Constate par la
    # recette : « decris cette image » reprenait le chemin long, l'enrichissement
    # etait appele SANS l'image, repondait « je ne vois pas d'image attachee »,
    # et le studio adoptait cette phrase comme prompt.
    if (AIGUILLEUR and not modele_choisi and not a_une_image
            and source_dispo and court):
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
    if a_une_image == "image" and not modele_choisi and not veut_detourer(texte):
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

    if veut_fluidifier(texte) and not modele_choisi:
        journal(tid, "fluidite video reconnue — aucune analyse necessaire")
        return {"intention": "fluidifier", "modele": "fluidifier", "raccourci": True,
                "prompt": texte,
                "parametres": {}, "parametres_bruts": {},
                "raison": "images intercalees dans la video precedente"}

    # AVANT les autres : « decris-la » est sans ambiguite des lors qu'une image
    # est jointe, et deux des raccourcis suivants mordent sur des formulations
    # courtes du meme genre.
    if a_une_image == "image" and veut_lire(texte) and not modele_choisi:
        journal(tid, "lecture d'image reconnue — aucune analyse necessaire")
        return {"intention": "lecture", "modele": None, "prompt": texte,
                "parametres": {}, "parametres_bruts": {},
                "raison": "lecture : on decrit ce que l'image montre", "raccourci": True}

    if veut_detourer(texte) and not modele_choisi:
        journal(tid, "detourage reconnu — aucune analyse necessaire")
        return {"intention": "detourer", "modele": "detourer", "prompt": texte,
                "parametres": {}, "parametres_bruts": {},
                "raison": "detourage : le sujet est isole, le fond devient transparent", "raccourci": True}

    if veut_agrandir(texte) and not modele_choisi:
        journal(tid, "agrandissement reconnu — aucune analyse necessaire")
        return {"intention": "agrandir", "modele": "agrandir", "prompt": texte,
                "parametres": {}, "parametres_bruts": {},
                "raison": "agrandissement : l'image est reprise telle quelle", "raccourci": True}

    loin = "" if image_b64 else llm_distant_possible(texte, pid)
    # La raison du local n'est plus dite ici : appeler_ollama la dit pour TOUS
    # les appels de la chaine, celui-ci compris. La repeter ferait deux lignes
    # identiques a la suite.
    journal(tid, "analyse par " + (fournisseurs.LLM[loin]["titre"] if loin
                                   else MODELE_LLM) + "…")
    sys_p = SYSTEME.format(catalogue=catalogue_texte(), contexte=bloc_contexte(conv))
    # La consigne depend de CE QUI est joint : dire « une image est fournie »
    # quand c'est une video faisait proposer de retoucher une image qui n'existe
    # pas.
    if a_une_image == "video":
        # PAS « lecture ». Le studio ne sait lire qu'une IMAGE : img_b64 n'est
        # calcule que pour elle, et le modele de vision recevait donc un
        # corps sans piece jointe — il decrivait alors ce qu'il imaginait.
        # Proposer une intention qu'on ne sait pas honorer, c'est demander
        # au modele de se tromper.
        sys_p += ("\nUne VIDEO est fournie par l'utilisateur : la seule "
                  "intention possible est 'fluidifier' (plus fluide, ou au "
                  "ralenti). Tu ne sais pas REGARDER une video : si on te "
                  "demande de la decrire, reponds intention 'refus'.")
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
            and not a_une_image and not modele_choisi
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


# ── Ce que le nuage aura coute ───────────────────────────────────────────
#
# Un appel distant se paie, et rien ici ne le disait : ni combien, ni par qui,
# ni pour quoi. On consigne donc ce qui est VERIFIABLE — la date, le
# fournisseur, la modalite, le compte, les jetons quand l'API les rend, les
# octets recus, la duree. Aucun prix en euros : les tarifs changent d'un
# trimestre a l'autre, ce fichier ne les suivrait pas, et un chiffre faux en
# euros est pire que pas de chiffre du tout. La conversion appartient a qui
# tient la facture — au moins il saura par quoi multiplier.
#
# Meme format que avis.jsonl, pour la meme raison : une ligne, un objet. Le
# fichier se relit entierement meme si l'ecriture a ete coupee au milieu de la
# derniere ligne — ce qui arrive quand on arrete le conteneur.
FICHIER_COUTS = os.path.join(DOSSIER_DONNEES, "nuage.jsonl")

# mois "AAAA-MM" -> compte -> "fournisseur/modalite" -> mesures cumulees.
COMPTEUR = {}

# La page ne montre que le mois en cours et le precedent. Garder plus, en
# memoire comme sur le disque, ce serait un compteur qui grossit sans fin sur
# un studio qui tourne des mois d'affilee.
MOIS_GARDES = 2

# Au-dela, le fichier est reecrit sans les mois hors de portee de la vue. Deux
# Mio font environ dix mille appels : bien plus qu'un studio n'en fait en deux
# mois, donc un seuil qu'on n'atteint qu'anormalement.
TAILLE_COUTS = 2 * 1024 ** 2

# Le garde-fou de dernier recours, quand meme deux mois ne tiennent pas dans la
# taille : on garde les lignes les plus recentes. Une comptabilite bornee et
# amputee vaut mieux qu'un disque plein.
#
# DERIVE DU SEUIL, et non pose a cote. A 20 000 lignes de 198 octets, le
# garde-fou en gardait 3,96 Mo pour un seuil de 2 : la taille ne redescendait
# jamais dessous, donc _tailler() relisait et reecrivait le fichier ENTIER a
# chaque appel distant. Mesure : 11 091 lignes, aucune retiree, 97 ms par
# appel — et sur un volume monte dont la latence n'est pas la notre, la file
# bornee sature et l'on perd des lignes. Le seuil et le garde-fou doivent
# parler de la meme chose.
OCTETS_PAR_LIGNE = 256          # mesure : 198 octets, on arrondit vers le haut
LIGNES_COUTS = TAILLE_COUTS // OCTETS_PAR_LIGNE

# File bornee, et on jette plutot que d'attendre : un disque bloque doit couter
# une ligne de comptabilite, jamais figer une generation en cours.
_A_ECRIRE = queue.Queue(maxsize=2000)
_ECRIVAIN = None

# Combien de temps l'arret attend ce fil. Mesure sur le volume monte du 191 :
# 50 ms la ligne, donc cinq secondes couvrent une centaine de lignes en retard
# — bien plus qu'un studio n'en accumule — et restent sous les dix secondes que
# « docker stop » laisse avant le SIGKILL. Au-dela, on abandonne EN LE DISANT :
# une comptabilite amputee qui s'annonce vaut mieux qu'une qui se tait.
ATTENTE_JOURNAL = 5.0

# Combien d'appels distants sont PARTIS et pas encore consignes, par compte.
#
# Sans ce registre, le plafond etait un « verifier puis agir » : le compteur
# n'est ecrit qu'au RETOUR du fournisseur, donc tout ce qui part pendant
# l'aller-retour voit la meme place libre. Mesure du 1er septembre, plafond a
# un seul appel : trois travailleurs qui demarrent ensemble font TROIS appels
# factures, une rafale de dix en fait dix. Le depassement vaut donc
# STUDIO_TRAVAILLEURS — trois par defaut, davantage des qu'on releve le
# reglage — et il se paie a chaque fois.
_EN_VOL_NUAGE = {}          # compte -> appels partis, pas encore consignes


def _mois(quand=None):
    return time.strftime("%Y-%m", time.localtime(quand))


def mois_montres():
    """Le mois en cours et le precedent, du plus recent au plus ancien."""
    m = time.localtime()
    annee, mois, liste = m.tm_year, m.tm_mon, []
    for _ in range(MOIS_GARDES):
        liste.append(f"{annee:04d}-{mois:02d}")
        mois -= 1
        if mois == 0:
            annee, mois = annee - 1, 12
    return liste


def _cumuler(ligne):
    """Ajoute une ligne — relue au demarrage ou fraiche — aux totaux en memoire."""
    gardes = mois_montres()
    mois = ligne.get("mois") or _mois()
    if mois not in gardes:
        return
    # Le studio tourne des mois d'affilee sans redemarrer : sans cette purge,
    # chaque mois ecoule laisserait sa table derriere lui pour toujours.
    for passe in [m for m in COMPTEUR if m not in gardes]:
        del COMPTEUR[passe]
    par_compte = (COMPTEUR.setdefault(mois, {})
                  .setdefault(ligne.get("compte") or "anonyme", {}))
    mesures = par_compte.setdefault(
        f"{ligne.get('fournisseur')}/{ligne.get('modalite')}",
        {"appels": 0, "jetons_entree": 0, "jetons_sortie": 0,
         "sans_jetons": 0, "octets": 0, "secondes": 0.0})
    mesures["appels"] += 1
    entree, sortie = ligne.get("jetons_entree"), ligne.get("jetons_sortie")
    if entree is None and sortie is None:
        # Combien d'appels dont on ne SAIT PAS le cout en jetons. Sans ce
        # nombre, une somme basse passerait pour une petite facture alors
        # qu'elle ne compte que les fournisseurs bavards.
        mesures["sans_jetons"] += 1
    else:
        mesures["jetons_entree"] += int(entree or 0)
        mesures["jetons_sortie"] += int(sortie or 0)
    mesures["octets"] += int(ligne.get("octets") or 0)
    mesures["secondes"] += float(ligne.get("secondes") or 0)


def charger_compteur():
    """Relit le journal des appels distants au demarrage.

    Une ligne illisible est sautee sans un mot : c'est le prix du format qui
    survit a une ecriture coupee, et une comptabilite a laquelle il manque la
    derniere ligne vaut mieux qu'un studio qui refuse de demarrer.
    """
    COMPTEUR.clear()
    gardes = set(mois_montres())
    try:
        with open(FICHIER_COUTS, encoding="utf-8") as f:
            for l in f:
                l = l.strip()
                if not l:
                    continue
                try:
                    d = json.loads(l)
                except ValueError:
                    continue
                if isinstance(d, dict) and d.get("mois") in gardes:
                    _cumuler(d)
    except FileNotFoundError:
        return
    except OSError as e:
        print(f"  journal des couts illisible ({e}) — compteur reparti de zero",
              flush=True)


_TAILLE_FAITE = [0.0]


def _tailler():
    """Reecrit le fichier sans les mois que la page ne montre plus.

    On ne tronque pas a l'aveugle : on jette d'abord ce qui est deja hors de
    portee de la vue, ce qui laisse intact tout ce qui reste consultable. Le
    plafond en nombre de lignes n'intervient que si deux mois d'appels ne
    tiennent toujours pas — et il fait alors perdre les plus vieux d'entre eux
    au prochain demarrage. C'est assume : le disque passe avant.
    """
    try:
        if os.path.getsize(FICHIER_COUTS) < TAILLE_COUTS:
            return
    except OSError:
        return
    # Une seule taille par minute au plus. _fil_ecriture appelle celle-ci apres
    # CHAQUE ligne : quand le fichier reste au-dessus du seuil — un mois en
    # cours plus gros que la vue, par exemple — c'est une relecture complete
    # par appel distant.
    if time.time() - _TAILLE_FAITE[0] < 60:
        return
    _TAILLE_FAITE[0] = time.time()
    gardes = set(mois_montres())
    tenues = []
    try:
        with open(FICHIER_COUTS, encoding="utf-8") as f:
            for l in f:
                try:
                    d = json.loads(l)
                except ValueError:
                    continue
                if isinstance(d, dict) and d.get("mois") in gardes:
                    tenues.append(l if l.endswith(chr(10)) else l + chr(10))
        tmp = FICHIER_COUTS + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.writelines(tenues[-LIGNES_COUTS:])
        os.replace(tmp, FICHIER_COUTS)
    except OSError as e:
        print(f"journal des couts non taille : {e}", flush=True)


def _fil_ecriture():
    """Le seul fil qui touche au fichier : ni verrou, ni lignes entremelees."""
    while True:
        ligne = _A_ECRIRE.get()
        try:
            with open(FICHIER_COUTS, "a", encoding="utf-8") as f:
                f.write(json.dumps(ligne, ensure_ascii=False) + chr(10))
            _tailler()
        except OSError as e:
            print(f"cout non enregistre : {e}", flush=True)
        finally:
            _A_ECRIRE.task_done()


def vider_journal(secondes=None):
    """Attend que le fil d'ecriture ait pose la file sur le disque.

    Rend le nombre de lignes encore en attente — zero quand tout est ecrit.

    Le fil est un DEMON : l'interpreteur ne l'attend pas, et sans cette
    fonction l'arret du studio emportait tout ce qui restait en file. Mesure du
    1er septembre, quarante appels consignes sur un disque a 50 ms la ligne :
    l'arret en laissait TRENTE-NEUF derriere lui, sans un mot. Un compte
    plafonne se remboursait donc ses appels en redemarrant le studio, puisque
    charger_compteur() ne relit que ce qui a ete ecrit.

    L'attente passe par un fil et non par « _A_ECRIRE.join() » : join() n'a pas
    de delai, et un volume monte qui ne repond plus figerait l'arret pour
    toujours — le contraire de ce que la file bornee cherche a garantir.
    """
    if _ECRIVAIN is None:
        return 0
    veille = threading.Thread(target=_A_ECRIRE.join, daemon=True,
                              name="couts-vidange")
    veille.start()
    veille.join(ATTENTE_JOURNAL if secondes is None else secondes)
    return _A_ECRIRE.qsize()


def _consigner_sans_filet(fournisseur, modalite, pid, secondes,
                            octets=0, jetons=(None, None)):
    """Un appel distant ABOUTI, et ce qu'on peut en mesurer objectivement.

    Appele apres coup, jamais avant : un appel qui echoue n'est pas facture, et
    le compter fermerait le robinet pour une depense qui n'a pas eu lieu — la
    panne du fournisseur se paierait deux fois.
    """
    global _ECRIVAIN
    entree, sortie = jetons if jetons else (None, None)
    ligne = {
        "quand": time.strftime("%Y-%m-%d %H:%M:%S"), "mois": _mois(),
        "fournisseur": fournisseur, "modalite": modalite,
        # Le NOM du compte quand il y en a un : douze caracteres hexadecimaux
        # ne se reconnaissent pas dans un tableau. Meme regle que les dossiers
        # de sortie, pour que la facture et la mediatheque se lisent ensemble.
        "compte": dossier_utilisateur(pid),
        "jetons_entree": entree, "jetons_sortie": sortie,
        "octets": int(octets or 0), "secondes": round(float(secondes or 0), 1),
    }
    # Le total en memoire d'abord : c'est lui que le plafond interroge, et il ne
    # doit pas dependre du moment ou le disque aura repondu.
    _cumuler(ligne)
    # Demarrage au premier appel : un studio qui ne sort jamais de la maison n'a
    # pas a porter un fil de plus. Sans verrou, parce que seule la boucle
    # d'evenements appelle cette fonction — un seul fil, donc pas de course.
    if _ECRIVAIN is None:
        _ECRIVAIN = threading.Thread(target=_fil_ecriture, daemon=True,
                                     name="couts-nuage")
        _ECRIVAIN.start()
    try:
        _A_ECRIRE.put_nowait(ligne)
    except queue.Full:
        print("journal des couts sature — une ligne perdue", flush=True)


def appels_du_mois(compte, mois=None):
    """Combien d'appels distants ce compte a faits ce mois-ci."""
    par_compte = (COMPTEUR.get(mois or _mois()) or {}).get(compte) or {}
    return sum(m["appels"] for m in par_compte.values())


def engages(compte):
    """Les appels du mois deja consignes, PLUS ceux qui sont encore en vol.

    C'est ce nombre-la que le plafond doit regarder, et pas le seul compteur :
    un appel parti est un appel paye, meme si le fournisseur n'a pas encore
    repondu.
    """
    return appels_du_mois(compte) + _EN_VOL_NUAGE.get(compte, 0)


def reserver_nuage(pid):
    """Prend une place sous le plafond du mois, ou None s'il n'y en a plus.

    Le decompte est atomique parce que RIEN ICI N'ATTEND : la boucle
    d'evenements ne rend la main qu'a un « await », donc aucun autre appel ne
    peut s'intercaler entre la lecture et l'increment. Toute la correction
    tient dans cette absence d'await — deplacer une seule ligne asynchrone
    dans cette fonction rouvrirait la course.
    """
    compte = dossier_utilisateur(pid)
    limite = PREFERENCES.get("plafond_nuage") or 0
    if 0 < limite <= engages(compte):
        return None
    _EN_VOL_NUAGE[compte] = _EN_VOL_NUAGE.get(compte, 0) + 1
    return compte


def liberer_nuage(place):
    """Rend la place, que l'appel ait abouti, echoue ou ete annule.

    TOUJOURS dans un « finally ». Une place jamais rendue fermerait le robinet
    jusqu'a la fin du mois pour ce compte, et cette panne-la serait pire que le
    depassement qu'on corrige.
    """
    if place is None:
        return
    reste = _EN_VOL_NUAGE.get(place, 0) - 1
    if reste > 0:
        _EN_VOL_NUAGE[place] = reste
    else:
        _EN_VOL_NUAGE.pop(place, None)


def plafond_atteint(pid):
    """Vrai si ce compte a epuise son quota d'appels distants du mois.

    Zero veut dire « aucun plafond », et c'est le reglage d'origine : un studio
    qui se mettrait a refuser le nuage sans qu'on le lui ait demande serait une
    mauvaise surprise, pas une protection.
    """
    limite = PREFERENCES.get("plafond_nuage") or 0
    if limite <= 0:
        return False
    return engages(dossier_utilisateur(pid)) >= limite


def etat_plafond(pid):
    """Ou en est ce compte de son quota, ou None s'il n'y en a pas."""
    limite = PREFERENCES.get("plafond_nuage") or 0
    if limite <= 0:
        return None
    compte = dossier_utilisateur(pid)
    # « faits » compte ce qui est ECRIT : c'est le chiffre que la page montre a
    # cote de la limite, et il doit correspondre a la ligne du journal. Le
    # « atteint », lui, tient compte des appels en vol, sinon la page dirait
    # « 2 sur 3, il reste de la place » a l'instant meme ou le troisieme part.
    faits = appels_du_mois(compte)
    return {"compte": compte, "mois": _mois(), "limite": limite,
            "faits": faits, "atteint": engages(compte) >= limite}


def avertissement_plafond():
    """Ce que le plafond ne protege pas en STUDIO_AUTH=libre, dit en francais.

    LA MESURE D'ABORD, parce qu'elle contredit ce qu'on croyait. Le reproche
    etait « en mode libre, tout le monde tombe dans le meme seau anonyme ».
    C'est faux : dossier_utilisateur() rend le cookie du navigateur des qu'il
    y en a un, et trois navigateurs mesures le 1er septembre donnaient bien
    trois seaux distincts. « anonyme » n'apparait que pour un pid absent —
    une conversation orpheline d'avant les comptes.

    Le seau par session existe donc deja. Ce qu'il ne fait pas, c'est
    proteger : le cookie appartient au visiteur, qui le vide et repart a zero.
    Un seau par session de plus n'y changerait rien — le probleme n'est pas le
    decoupage, c'est que l'identite est declarative tant qu'aucun compte ne la
    porte. On garde donc le decoupage, qui evite deja qu'un utilisateur affame
    les autres, et ON LE DIT : un plafond qu'on croit etanche est plus
    dangereux qu'un plafond dont on connait le trou.
    """
    if AUTH == "libre" and (PREFERENCES.get("plafond_nuage") or 0) > 0:
        return ("STUDIO_AUTH=libre : le plafond du nuage se compte par "
                "navigateur, et un visiteur qui vide ses cookies repart a "
                "zero. Il repartit la depense, il ne la borne pas — pour "
                "cela, il faut des comptes.")
    return ""


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
    # LE PLAFOND PASSE PAR ICI, ET NULLE PART AILLEURS. C'est deja le point de
    # passage de toutes les decisions « au loin ou a la maison » —
    # llm_distant_possible, choix_distant, l'interrupteur de la barre du haut.
    # Lui ajouter un second chemin, c'est un jour en oublier un, et laisser une
    # modalite depenser apres la fermeture du robinet.
    if plafond_atteint(pid):
        return False
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
    # Le plafond voyage avec l'etat des interrupteurs : c'est la seule reponse
    # qui dise a la fois « eteint » et pourquoi.
    return web.json_response({"modalites": etat, "plafond": etat_plafond(pid)})


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

PRIORITES = ("", "brouillon", "rapide", "soigne")
# Facteur applique au nombre d'etapes. Les bornes par intention gardent la main :
# « rapide » ne peut pas descendre sous le minimum qui produit encore une image.
#
# « brouillon » n'est pas un « rapide » plus fort : un quart des etapes, quatorze
# secondes contre deux cent dix-sept sur la meme carte. Il sert a juger vite un
# prompt, un moteur, une ambiance — pas a choisir un cadrage.
#
# CE QU'IL NE FAIT PAS, et je l'ai cru avant de regarder les images : il ne
# predit PAS la composition finale. J'avais ecrit ici que « le chemin de
# debruitage est le meme, simplement plus grossier ». C'est faux. Le nombre
# d'etapes definit l'echelonnement du bruit, donc la trajectoire diverge des le
# premier pas ; la graine fixe le point de depart, pas la destination. Mesure du
# 31 aout, meme graine 864102317, meme prompt, meme moteur, meme taille : deux
# phares contre un, l'ilot centre contre une falaise a gauche. Deux images sans
# rapport.
#
# Il ne dit quand meme rien a l'aiguilleur, contrairement a « rapide » : un
# brouillon rendu par un AUTRE moteur ne dirait rien du moteur qu'on juge.
_FACTEUR_ETAPES = {"brouillon": 0.25, "rapide": 0.6, "soigne": 1.35}
# LA OU LE BROUILLON VEUT DIRE QUELQUE CHOSE. Le facteur ne passe que par
# appliquer_parametres : le detourage, l'agrandissement et la fluidification ne
# reçoivent pas de parametres du tout, et les trois retouches ecrasent les
# etapes juste apres. Marquer « esquisse » sur ces intentions-la promettait un
# rendu de quatorze secondes qui en mettait deux cents, posait le bouton
# « refaire en soigne » — et ce bouton echouait, faute d'image source a
# reprendre. On ne marque donc que ce qui tient la promesse et se refait sans
# source.
ESQUISSE_POSSIBLE = ("image", "planche", "video", "audio")
# LA OU PLUSIEURS TIRAGES VEULENT DIRE QUELQUE CHOSE. Meme arbitrage que
# ESQUISSE_POSSIBLE juste au-dessus, et la meme question tranchee : une retouche,
# un detourage, un agrandissement, une fluidification partent d'une image DONNEE.
# Quatre tirages de la meme retouche rendent quatre fois la meme chose au bruit
# pres — la graine n'y decide plus la composition, elle n'ajuste qu'un debruitage
# deja contraint par l'image d'origine — et coutent quatre fois le temps de carte.
# On ne multiplie que ce qui est invente : une creation.
#
# La video et l'audio sont eligibles a l'esquisse mais PAS aux variantes, et ce
# n'est pas un oubli : une video coute six minutes, une animation douze. Quatre
# d'entre elles fermeraient les deux machines pour trois quarts d'heure sur un
# seul geste, et le studio n'a que trois travailleurs.
VARIANTES_POSSIBLE = ("image", "planche")
# Combien de tirages une demande peut porter. Quatre, pas davantage : c'est N
# rendus et non un. A quatorze secondes l'esquisse sur la petite carte, quatre
# tiennent dans la minute ; a deux minutes l'image finie, quatre occupent les
# deux machines quatre minutes durant — et la file de tout le monde avec.
VARIANTES_MAX = 4

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
    # UNE IMAGE, et pas « une piece jointe ». « a_une_image » porte la famille :
    # « video » et « audio » sont vrais eux aussi, et le prompt systeme annonce
    # justement « lecture » comme intention possible pour une video. On partait
    # alors decrire un fichier que le modele de vision n'a jamais reçu —
    # img_b64 n'est calcule que pour une image — et il rendait une description
    # plausible, detaillee, entierement inventee, marquee « description
    # produite » et « fini ». Rien ne la signalait.
    if plan["intention"] == "lecture" and a_une_image != "image":
        # Ni « image » en silence. Basculer vers une generation, c'etait rendre
        # une image sans rapport a quelqu'un qui demandait ce que son fichier
        # CONTIENT — et lui laisser croire que c'etait la reponse. On le dit.
        if a_une_image:
            plan["intention"] = "refus"
            plan["raison"] = (
                "je sais decrire une image, pas encore un fichier "
                + {"video": "video", "audio": "audio"}.get(a_une_image, "de ce type")
                + ". Extrais-en une image et redepose-la, et je te la decris.")
        else:
            plan["intention"] = "image"   # lire exige une image reellement jointe
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
                                    modele=MODELE_POUR_ECRIRE)
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
                                    modele=MODELE_POUR_ECRIRE)
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


# « Decris cette image » : la formulation la plus courante quand on joint une
# image, et de loin la plus chere a faire trancher par un modele — 96 a 222 s
# d'aiguillage en local, mesures le 31 aout. Et la plus fragile : gemma3:4b,
# quatre fois plus rapide sur le reste, l'a classee « edition » et l'image n'a
# jamais ete regardee. Une decision qui depend du modele du jour n'en est pas
# une ; celle-ci s'ecrit.
_LIRE = re.compile(
    # « detaille » est parti : avec une image jointe, « detaille davantage le
    # visage » demande PLUS DE DETAIL, pas une description. Un verbe ambigu
    # dans un raccourci ecrit coute plus qu'il ne rapporte — les autres
    # suffisent, et ce qu'on ne reconnait pas part au modele.
    r"\b(decri[st]|decrire|raconte|analyse|commente|explique)\b"
    r"|\bque\s+(vois|voit)\b"
    r"|\bqu'?est[- ]ce\s+(que\s+)?(c'est|tu\s+vois|ca\s+represente)"
    r"|\bc'?est\s+quoi\b"
    r"|\bqu'?y\s*a[- ]t[- ]il\b"
    r"|\bde\s+quoi\s+(s'agit|ca\s+parle)")
# Ce qui trahit une TRANSFORMATION et non une lecture. « decris-la en aquarelle »
# n'est pas une demande de description, et « analyse et ameliore » non plus.
_PAS_LIRE = re.compile(
    r"\b(fai[ts]|transforme|met[st]?|mettre|change|ajoute|enleve|retire|"
    r"remplace|refai[ts]|redessine|colorie|ameliore|agrandi[st]?|style|"
    r"maniere|version|comme\s+si)\b"
    # « decris-la EN AQUARELLE » : le support nomme apres le verbe dit une
    # transformation, pas une lecture. La liste est courte a dessein — ce
    # raccourci vise la justesse, pas la couverture : ce qu'il ne reconnait
    # pas part au modele, comme avant.
    # Les verbes de transformation les plus courants manquaient : mesure,
    # « analyse cette photo et corrige les couleurs » partait en description.
    r"|\b(corrige|supprime|efface|recadre|eclairci[st]?|assombri[st]?|floute?s?|"
    r"applique|rends|augmente|reduis|nettoie|repare|detoure|isole|recolore|"
    r"agrandis|reduis|coupe|rogne)\b"
    r"|\ben\s+(aquarelle|peinture|dessin|croquis|manga|bd|3ds?|pixel|"
    r"anime|huile|encre|noir\s+et\s+blanc|couleurs?|sepia)\b")


def veut_lire(texte):
    """Vrai si la demande porte sur ce que l'image MONTRE.

    N'a de sens qu'avec une image reellement jointe — c'est a l'appelant de le
    verifier, comme pour les autres raccourcis qui dependent d'une source.

    Court, et sans verbe de transformation : les deux conditions ensemble. Une
    demande de lecture tient en quelques mots ; passe une ligne, on decrit
    plutot ce qu'on veut obtenir, et c'est au modele de trancher.

    ET AUCUN AUTRE RACCOURCI NE DOIT REPONDRE VRAI. Allonger la liste des verbes
    interdits ne suffisait pas — mesure : « decris cette image puis supprime le
    fond » declenchait a la fois la lecture et le detourage, et la lecture etant
    placee avant, l'utilisateur recevait un paragraphe de texte au lieu de son
    image detouree. Une phrase qui reveille deux raccourcis est ambigue : elle
    appartient au modele, pas a une expression reguliere.
    """
    nu = sans_accents(texte or "")
    if len(nu) > 90 or _PAS_LIRE.search(nu):
        return False
    if not _LIRE.search(nu):
        return False
    return not (veut_detourer(texte) or veut_agrandir(texte)
                or veut_fluidifier(texte) or veut_ralenti(texte)
                or veut_zone_nommee(texte) or veut_retoucher_fond(texte)
                or veut_retoucher_sujet(texte))


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


def noeud_qui_travaille(tid):
    """La machine qui dit calculer deja ce travail, s'il y en a une.

    Une machine qui s'est tue ne compte pas : son dernier « je calcule » vaut ce
    que vaut sa derniere nouvelle. Sans ce controle, un agent tue en plein rendu
    laissait sa demande marquee « chez lui » pour toujours, et le studio
    l'attendait une heure au lieu de la confier a quelqu'un d'autre.
    """
    for x in tous_les_noeuds():
        e = ETAT_NOEUDS.get(x["id"]) or {}
        if tid in (e.get("travaux") or []):
            if time.time() - (e.get("vu") or 0) < SILENCE_MAX:
                return x["id"]
    return None


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
    titre_ = (noeud(ident) or {}).get("titre", ident)
    # Deja en cours la-bas ? Alors on ne le renvoie pas : on se rebranche sur ce
    # qui tourne. C'est le cas apres un redemarrage du studio — sa table des
    # travaux est perdue, reprendre_file() remet la demande en file, et la
    # machine, elle, n'a jamais cesse de calculer. Sans cette verification la
    # carte refaisait tout, et le premier resultat arrivait quand meme.
    deja = noeud_qui_travaille(tid)
    rebranche = deja == ident
    if rebranche:
        journal(tid, f"{titre_} calcule deja cette demande — on attend son "
                     f"resultat plutot que de la relancer")
    else:
        TRAVAUX.setdefault(ident, []).append({"tid": tid, "graphe": g,
                                              "entrees": entrees})
        journal(tid, f"travail confie a {titre_} — en attente de sa reponse")
    t0 = time.time()
    try:
        d = await _attendre_le_noeud(attente, ident, titre_, tid, rebranche)
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


def _deja_livre(tid):
    """Le tour de ce travail s'il a DEJA ete livre, par un autre chemin.

    Il y en a un : rattacher_tardif(), quand une machine rend un resultat que
    plus personne n'attendait parce que le studio avait redemarre.
    """
    for conv in CONVERSATIONS.values():
        for t in conv.get("tours", []):
            if (t.get("id") == tid and t.get("etat") == "fini"
                    and t.get("fichiers")):
                return t
    return None


async def _attendre_le_noeud(attente, ident, titre, tid, rebranche=False):
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
        # On s'est rebranche sur un rendu deja parti, sans rien deposer : c'est
        # une promesse qu'on n'a pas faite, et elle peut etre deja tenue ou deja
        # morte. Il faut donc la reverifier, sinon on attend une heure — pendant
        # laquelle le verrou de cette carte est tenu pour rien.
        if rebranche:
            livre = _deja_livre(tid)
            if livre:
                journal(tid, f"{titre} avait deja rendu pendant l'arret — "
                             f"on reprend son resultat")
                return {"etat": "fini", "fichiers": livre["fichiers"],
                        "secondes": livre.get("secondes")}
            if noeud_qui_travaille(tid) != ident:
                journal(tid, f"{titre} ne calcule plus cette demande — "
                             f"on ne l'attend pas davantage")
                raise PanneNoeud(f"{titre} n'a pas garde cette demande")
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

# UNE FRONTIERE QUI TIENT COMPTE DU SOULIGNE. « \b » ne separe pas « nude » de
# « _body » : le souligne est un caractere de mot. Or les moteurs a etiquettes
# reçoivent exactement cela — « nude_body », « explicit_content ». Et « \b » a
# droite laissait passer « nuee », l'accent n'etant pas une lettre pour [a-z].
# « [^\W_] » veut dire « une lettre ou un chiffre, souligne exclu » : c'est la
# seule frontiere qui convienne aux deux ecritures.
_BORD = r"(?<![^\W_])"
_FIN = r"(?![^\W_])"


def _motif(racines, mots):
    """Un motif de surete : des racines permissives, des mots stricts.

    Les deux formes sont necessaires, et l'histoire de ce fichier le prouve.
    « \b(nu|…) » sans frontiere a droite mordait sur « nuit » et « nuage » —
    neuf faux positifs sur treize demandes ordinaires, et cent soixante
    secondes perdues par demande. Puis, en fermant la frontiere des deux cotes
    et en ecrivant les formes a la main, les derivees ANGLAISES ont disparu :
    « a child in a sexual pose » n'etait plus refuse, parce que « sexual »
    n'etait pas dans la liste et que « sex » ne mordait plus dessus.

    La bonne reponse n'est ni l'un ni l'autre : une racine sans ambiguite prend
    ce qui la suit (« sexual », « sexuellement », « nudity », « nudism »), un
    mot court ou ambigu s'arrete ou il finit (« nu », « sex », « kid »).
    """
    return re.compile(
        _BORD + "(?:" + "|".join([r + r"\w*" for r in racines] + mots) + ")"
        + _FIN, re.I)


# Volontairement large, et large dans le bon sens : ce motif ne refuse rien a
# lui seul, il ne refuse qu'en presence de l'autre.
_MINEUR = _motif(
    racines=[r"enfant", r"gamin", r"fillette", r"gar[cç]onnet", r"bambin",
             r"b[ée]b[ée]", r"mineur", r"coll[ée]gien", r"[ée]col[ie]",
             r"child", r"toddler", r"infant", r"preteen", r"pre-teen",
             r"underage", r"schoolgirl", r"schoolboy", r"adolescent",
             r"teenager", r"pr[ée]pub", r"prepub", r"loli", r"shota"],
    mots=[r"kid", r"kids", r"minor", r"minors", r"teen", r"teens", r"ado",
          r"ados", r"(?:\d|1[0-7])\s*ans?", r"(?:\d|1[0-7])\s*years?\s*old"])

# Ce qui est adulte ne sort pas de la maison. Le meme motif sert au garde-fou,
# ou il ne pese qu'avec _MINEUR — d'ou l'importance de ne rien laisser filer
# cote anglais : le prompt envoye a la carte est TOUJOURS traduit en anglais,
# et les moteurs a etiquettes reçoivent du danbooru colle par des soulignes.
_SEXUEL = _motif(
    racines=[r"sexuel", r"sexual", r"nudit", r"nudis", r"pornograph", r"porno",
             r"[ée]roti", r"naked", r"nipple", r"breast", r"genital", r"fesse",
             r"topless", r"lingerie", r"hentai", r"sexting"],
    # Ceux-la et pas un caractere de plus : « nu » ne doit pas mordre sur
    # « nuit », ni « sex » sur « sexagenaire », ni « explicit » sur
    # « explicitement ».
    mots=[r"nu", r"nue", r"nus", r"nues", r"nude", r"nudes", r"sex", r"sexe",
          r"sexes", r"sexy", r"porn", r"porns", r"seins", r"penis", r"vagina",
          r"nsfw", r"explicit", r"explicite", r"explicites"])

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
        "intention_voulue": tour.get("intention_voulue"),
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


# Les intentions que l'aiguilleur sait distinguer, en français. Le pouce en bas
# ne servait a rien de plus qu'a RETIRER un exemple : « ce tour ne prouve
# rien ». Or c'est le cas le plus precieux — celui ou le studio s'est trompe —
# et la seule chose qui manquait etait de savoir ce que c'etait VRAIMENT. Une
# correction vaut dix exemples fabriques : elle porte une formulation que le
# classifieur a deja ratee.
INTENTIONS_LISIBLES = {
    "image": "une image a creer",
    "edition": "modifier l'image fournie",
    "planche": "une planche, plusieurs cases",
    "video": "une video a creer",
    "video_image": "animer l'image fournie",
    "audio": "de la musique",
    "objet3d": "un objet en 3D",
    "lecture": "decrire l'image fournie",
    "agrandir": "agrandir sans rien changer",
    "detourer": "detourer le sujet",
    "fluidifier": "rendre la video plus fluide",
}


async def api_intentions(_):
    """Ce qu'on peut repondre a « c'etait plutot quoi ? ».

    On ne rend que les classes que l'aiguilleur connait REELLEMENT : proposer
    une correction qu'il ne saurait pas apprendre serait demander pour rien.
    """
    # Sans aiguilleur, RIEN. « or INTENTIONS_LISIBLES » faisait exactement
    # l'inverse de ce que la docstring promet : les onze classes proposees a un
    # studio qui n'a aucun classifieur pour les apprendre. La page n'affiche
    # alors pas la question, ce qui est la bonne reponse — mieux vaut ne pas
    # demander que demander pour rien.
    connues = set((AIGUILLEUR.classes if AIGUILLEUR else {}) or {})
    return web.json_response(
        [{"cle": k, "titre": v} for k, v in INTENTIONS_LISIBLES.items()
         if k in connues])


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
    # « C'etait plutot quoi ? » — la reponse a la seule question qui rende un
    # pouce en bas utile. Refusee si l'aiguilleur ne connait pas cette classe :
    # on n'ecrit pas sur un tour une etiquette qu'il ne saura jamais apprendre.
    voulue = str(d.get("intention") or "")
    if voulue and voulue not in INTENTIONS_LISIBLES:
        return web.json_response({"erreur": "intention inconnue"}, status=400)
    for conv in mes_conversations(pid):
        for tour in conv.get("tours", []):
            if tour.get("id") == tid:
                tour["avis"] = avis
                tour["note"] = note
                if voulue:
                    tour["intention_voulue"] = voulue
                elif avis != -1:
                    # Un pouce retire ou repasse en haut efface la correction :
                    # elle ne valait que pour le reproche.
                    tour.pop("intention_voulue", None)
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
    # AVANT « nuage coupe » : le plafond eteint justement l'interrupteur, et
    # sans cette ligne l'utilisateur lirait qu'il l'a coupe lui-meme.
    if pid is not None and plafond_atteint(pid):
        return (f"plafond du mois atteint ({PREFERENCES.get('plafond_nuage')} "
                f"appels distants) : le modele local est utilise")
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


_VERROU_AIGUILLEUR = asyncio.Lock()


async def api_admin_aiguilleur(req):
    """Etat de l'aiguilleur, et reentrainement a la demande."""
    if not admin_ok(req):
        return web.json_response({"erreur": "jeton invalide"}, status=403)
    global AIGUILLEUR
    if req.method == "POST":
        # UN SEUL A LA FOIS. Deux POST concurrents partaient dans deux fils du
        # pool : l'un regenerait le corpus pendant que l'autre le relisait.
        # Depuis que corpus() reecrit toujours le fichier, la course est reelle.
        if _VERROU_AIGUILLEUR.locked():
            return web.json_response(
                {"erreur": "un entrainement est deja en cours"}, status=409)
        async with _VERROU_AIGUILLEUR:
            try:
                rendu = await asyncio.get_event_loop().run_in_executor(
                    None, _mesurer_aiguilleur)
            except Exception as e:
                return web.json_response(
                    {"erreur": f"entrainement impossible : {e}"}, status=500)
            # Recharge depuis le disque : le studio doit se servir de ce qui
            # vient d'etre ecrit, pas d'un objet garde en memoire.
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


async def api_admin_couts(req):
    """Ce que le nuage a coute, par compte et par fournisseur, sur deux mois.

    Des nombres bruts et aucun prix. Un tableau de bord qui afficherait des
    euros les afficherait faux le jour ou un tarif change, sans que personne ne
    s'en apercoive ; ici, qui veut des euros multiplie par le tarif de sa
    facture, et sait au moins par quoi il multiplie.
    """
    if not admin_ok(req):
        return web.json_response({"erreur": "acces refuse"}, status=403)
    mois = []
    for m in mois_montres():
        comptes = []
        for compte, par_cle in (COMPTEUR.get(m) or {}).items():
            detail = []
            for cle, mesures in sorted(par_cle.items()):
                fourn, _, modalite = cle.partition("/")
                detail.append(dict(mesures, fournisseur=fourn, modalite=modalite))
            comptes.append({
                "compte": compte, "detail": detail,
                "appels": sum(x["appels"] for x in detail),
                "jetons_entree": sum(x["jetons_entree"] for x in detail),
                "jetons_sortie": sum(x["jetons_sortie"] for x in detail),
                "sans_jetons": sum(x["sans_jetons"] for x in detail),
                "octets": sum(x["octets"] for x in detail),
                "secondes": round(sum(x["secondes"] for x in detail), 1),
            })
        mois.append({"mois": m,
                     "comptes": sorted(comptes, key=lambda c: -c["appels"])})
    return web.json_response({"mois": mois,
                              "plafond": PREFERENCES.get("plafond_nuage", 0)})


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
        # LA TAILLE RENDUE. Elle vivait dans le plan, qui ne survit pas au tour,
        # et nulle part ailleurs : « pourquoi celle-ci a mis quatre minutes ? »
        # se repond neuf fois sur dix par la resolution, et rien ne la montrait.
        "taille": (f"{(plan or {}).get('largeur')}x{(plan or {}).get('hauteur')}"
                   if (plan or {}).get("largeur") and (plan or {}).get("hauteur")
                   else None),
        "fichiers": sorties or [], "description": TACHES.get(tid, {}).get("description"),
        # La machine et le temps. Ils vivaient dans le journal du studio, qui se
        # perd a chaque redemarrage, et dans le fil de la tache, qui s'efface au
        # bout de deux cents demandes. Sur le tour, ils survivent aussi longtemps
        # que le rendu qu'ils expliquent — et « pourquoi celle-ci a mis quatre
        # minutes » est une question qu'on se pose une semaine plus tard.
        "noeud": TACHES.get(tid, {}).get("noeud"),
        "secondes": TACHES.get(tid, {}).get("secondes"),
        # La graine, pour pouvoir refaire EXACTEMENT la meme image avec tout le
        # soin. Sans elle, « passer au propre » rendrait une autre image — et
        # l'esquisse n'aurait servi a rien.
        "graine": TACHES.get(tid, {}).get("graine"),
        # A QUEL GROUPE DE TIRAGES CE TOUR APPARTIENT, s'il en est un :
        # {"groupe": tid du premier, "rang": 1..N, "sur": N}. Sur le tour et pas
        # seulement sur la tache : les taches s'effacent au bout de deux cents
        # demandes, et c'est la conversation rechargee trois jours plus tard qui
        # doit encore savoir que ces quatre images etaient un seul geste.
        "variantes": (TACHES.get(tid) or {}).get("variantes"),
        "esquisse": ((plan or {}).get("priorite") == "brouillon"
                     and (plan or {}).get("intention") in ESQUISSE_POSSIBLE) or None,
        # Le plan entier, mais SEULEMENT pour une esquisse : c'est ce qui permet
        # de la repasser au propre a l'identique, sans refaire l'analyse — donc
        # sans risquer un autre prompt, donc une autre image. L'ecrire sur tous
        # les tours grossirait chaque conversation pour un usage que personne
        # n'en a.
        "plan": (plan or None) if ((plan or {}).get("priorite") == "brouillon"
                                   and (plan or {}).get("intention")
                                   in ESQUISSE_POSSIBLE) else None,
        "etat": etat, "erreur": erreur,
        # Les paroles ne sont ni le prompt ni la description : sans elles, un
        # pouce en bas sur une chanson ne dirait pas ce qui a deplu.
        "paroles": (plan or {}).get("paroles"),
        "questions": TACHES.get(tid, {}).get("questions"),
        "avis": 0, "note": "",
    }
    for i, ancien in enumerate(conv["tours"]):
        if ancien.get("id") == tid:
            # UNE LIVRAISON NE SE REMPLACE PAS PAR UNE ERREUR. Le tour peut
            # avoir ete termine par un autre chemin que celui qui ecrit ici —
            # rattacher_tardif() recolle le resultat d'une machine qui a fini
            # pendant que le studio redemarrait, et le travailleur qui refaisait
            # le meme travail arrivait ensuite avec son echec. L'utilisateur
            # voyait son image apparaitre, puis disparaitre.
            if (etat == "erreur" and ancien.get("etat") == "fini"
                    and ancien.get("fichiers")):
                return
            # L'avis eventuellement pose ne doit pas etre efface par la mise a
            # jour : il appartient a l'utilisateur, pas au deroulement.
            tour["avis"] = ancien.get("avis", 0)
            tour["note"] = ancien.get("note", "")
            # Une esquisse deja passee au propre le reste : cette marque ne se
            # deduit d'aucun plan, elle a ete posee par un geste de
            # l'utilisateur. La perdre reproposerait le bouton, et une seconde
            # grande image identique.
            if ancien.get("au_propre"):
                tour["au_propre"] = ancien["au_propre"]
            # La correction du pouce non plus : elle appartient a
            # l'utilisateur, pas au deroulement. Un tour en erreur corrige puis
            # repris par la file au redemarrage la perdait sans un mot.
            if ancien.get("intention_voulue"):
                tour["intention_voulue"] = ancien["intention_voulue"]
            # Le groupe de variantes se pose une fois et ne bouge plus. Il vit
            # sur la tache, qui ne survit pas a une reprise apres redemarrage :
            # sans cette ligne, un tour repris se reecrivait sans son groupe et
            # sortait de la rangee — trois images cote a cote, la quatrieme
            # toute seule plus bas, sans que rien ne l'explique.
            if ancien.get("variantes"):
                tour["variantes"] = ancien["variantes"]
            # La variante RETENUE, elle, est un geste de l'utilisateur : elle
            # ne se deduit d'aucun plan et ne doit pas etre effacee par une
            # reecriture du tour.
            if ancien.get("choisie"):
                tour["choisie"] = ancien["choisie"]
            conv["tours"][i] = tour
            break
    else:
        conv["tours"].append(tour)
    coupes = {t.get("id") for t in conv["tours"][:-60]}
    conv["tours"] = conv["tours"][-60:]
    # LES MURMURES SUIVENT LEURS ANCRES. Un murmure s'ancre « apres » un tour ;
    # quand ce tour sort des soixante derniers, la page n'a plus ou le poser et
    # ne l'affiche nulle part — il reste dans le fichier, invisible, sans que
    # rien ne le dise. Et c'est justement la conversation longue, celle ou
    # « pourquoi celle-ci est en 1024 ? » se pose des jours plus tard, qui perd
    # sa trace. On les rerattache en tete plutot que de les perdre.
    if coupes:
        for m in conv.get("murmures") or []:
            if m.get("apres") in coupes:
                m["apres"] = None
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
    # LA PLACE SOUS LE PLAFOND SE PREND ICI, au ras du premier octet envoye, et
    # non a l'examen du plan : entre les deux passent l'enrichissement et la
    # traduction, soit des dizaines de secondes pendant lesquelles le compteur
    # ne bouge pas. Elle est prise avant les paroles d'une chanson, a dessein :
    # c'est le morceau que l'utilisateur a demande, et il vaut mieux lui garder
    # la derniere place que la donner a l'appel de texte qui le prepare.
    place = reserver_nuage(conv.get("proprietaire"))
    if place is None:
        raise fournisseurs.EchecFournisseur(
            f"plafond du mois atteint ({PREFERENCES.get('plafond_nuage')} "
            f"appels distants)")
    try:
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
        # Le temps sur la TACHE, comme pour une machine du parc : sans cette ligne,
        # une piece produite au loin n'avait jamais de duree, ni dans le detail du
        # tour ni dans la mediatheque — alors que ce sont justement celles qu'on
        # paie a la seconde.
        TACHES.setdefault(tid, {})["secondes"] = round(time.time() - debut, 1)
        # Le proprietaire de la CONVERSATION et non celui de la tache : les deux
        # sont le meme, mais c'est la conversation qui porte l'information jusqu'ici
        # sans dependre de l'etat de TACHES au moment ou l'on ecrit.
        consigner_appel_distant(conf["fournisseur"], conf["type"],
                                conv.get("proprietaire"), time.time() - debut,
                                octets=len(octets),
                                jetons=fournisseurs.jetons_du_dernier_appel())
        journal(tid, f"recu en {time.time() - debut:.0f} s "
                     f"({len(octets) / 1024:.0f} ko)")
        return [{"filename": nom, "subfolder": sous, "type": "output",
                 "noeud": noeud_local()["id"]}]
    finally:
        liberer_nuage(place)


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


async def lancer_variantes(tid, texte, conv, plan, combien, taille=None,
                           priorite="", noeud_force=None, image=None):
    """Met en file les autres tirages de la meme demande, et rend leurs identifiants.

    N TRAVAUX, ET NON UN GRAPHE A « batch_size » N. Le lot serait plus rapide
    sur une carte — un seul chargement de modele pour quatre images — mais il
    est indivisible : il ne se repartit pas sur les deux machines, il ne
    s'annule pas a l'unite, et surtout ComfyUI tire le bruit du lot entier d'un
    seul coup. Aucune de ses images ne porte alors de graine a elle : le studio
    ne saurait ni l'ecrire dans la file — donc une reprise apres redemarrage
    refait autre chose — ni la rendre a « refais celle-ci en soigne », qui
    n'aurait plus rien a viser. La graine par tirage est exactement ce qui fait
    qu'on peut CHOISIR ; c'est elle qui decide, pas la vitesse.

    LE PLAN EST IMPOSE, PAS REFAIT. L'aiguillage, l'enrichissement et la
    traduction ont deja tourne pour le premier tirage ; les refaire rendrait un
    autre prompt, donc un autre sujet, et l'on ne comparerait plus rien. C'est
    le meme chemin que « repasser au propre », a une difference pres : celui-la
    impose aussi la graine, celui-ci est le seul a la laisser libre. Trois
    appels au modele de langage economises par variante, au passage.

    Chaque tirage est un TOUR ENTIER, et non un fichier de plus sur un tour
    commun. C'est ce qui fait que tout ce qui existe deja marche sans une ligne :
    la reprise apres redemarrage (une entree de file par tirage, avec sa graine),
    l'annulation a l'unite, le pouce, la mediatheque, et « refais en soigne »
    qui vise le tour sur lequel on a clique — donc la variante qu'on a choisie.
    """
    pid = conv.get("proprietaire")
    modele = dict(plan)
    # LA GRAINE NE SE RECOPIE PAS : c'est la seule chose qui doit differer. Elle
    # est tiree par executer, une par tirage, puis ecrite dans la file — une
    # reprise apres redemarrage refait donc la meme image, tirage par tirage.
    modele.pop("graine", None)
    # Deux chemins arrivent a executer avec un plan tout fait, et ils ne
    # promettent pas la meme chose : la reprise au propre d'une esquisse et un
    # tirage de plus. Le plan le dit, sinon le journal annonçait un geste que
    # l'utilisateur n'avait pas fait.
    modele["variante"] = True
    groupe = {"groupe": tid, "sur": combien}
    TACHES.setdefault(tid, {})["variantes"] = dict(groupe, rang=1)
    lances = []
    for rang in range(2, combien + 1):
        autre = uuid.uuid4().hex
        TACHES[autre] = {"etapes": [], "etat": "en cours", "demande": texte,
                         "conversation": conv["id"], "proprietaire": pid,
                         "image": image, "variantes": dict(groupe, rang=rang)}
        enregistrer_tour(conv, autre, texte, {}, None, None, [], "en cours")
        journal(autre, f"variante {rang} sur {combien} — meme demande, meme "
                       f"prompt, autre graine")
        ATTENTE.append(autre)
        EN_FILE[autre] = {"tid": autre, "texte": texte, "conversation": conv["id"],
                          "proprietaire": pid, "image": image, "modele": None,
                          "taille": taille, "priorite": priorite,
                          "noeud": noeud_force, "plan": modele, "variantes": 1}
        lances.append(autre)
    # LE PREMIER TIRAGE NE REPART PAS EN ESSAIM AU REVEIL : sa part est faite.
    # Ecrit avant la mise en file — c'est le fichier qui fait foi apres un arret,
    # et une reprise qui relancerait N-1 travaux de plus a chaque redemarrage est
    # le genre de faute qui ne se voit qu'une fois les deux cartes prises pour
    # une heure.
    #
    # ET IL GARDE SON PLAN DANS LA FILE, comme ses variantes. Sans cette ligne,
    # un redemarrage en plein groupe le renvoyait a l'aiguilleur : il repartait
    # avec un prompt refait — trois appels au modele de langage rendent rarement
    # deux fois la meme phrase — pendant que ses variantes gardaient l'ancien.
    # Les quatre images cessaient alors d'etre comparables, c'est-a-dire que le
    # groupe perdait sa seule raison d'etre. Mesure au banc : aiguiller rappele
    # une fois au reveil, et le prompt du premier tirage s'ecartait des autres.
    # Sa graine, elle, est deja ecrite par executer quelques lignes plus bas : il
    # refait donc exactement la meme image, pas seulement le meme sujet.
    if tid in EN_FILE:
        EN_FILE[tid]["variantes"] = 1
        EN_FILE[tid]["plan"] = modele
    sauver_file()
    # Le fichier d'abord, la file ensuite : un arret entre les deux laisse les
    # tirages dans _file.json, et reprendre_file() les remet en route. L'inverse
    # les aurait lances sans trace, donc perdus.
    for autre in lances:
        await FILE_ATTENTE.put({"tid": autre, "texte": texte, "conv": conv,
                                "taille": taille, "image": image, "modele": None,
                                "priorite": priorite, "noeud": noeud_force,
                                "plan": modele, "variantes": 1})
    # Le tour du premier tirage porte le groupe des maintenant. Sans cette
    # reecriture il restait seul a l'ecran pendant tout son rendu, pendant que
    # les autres s'affichaient deja groupees, puis les rejoignait a la fin —
    # c'est-a-dire qu'il bougeait sous les yeux, a la minute ou l'on regarde.
    enregistrer_tour(conv, tid, texte, plan, plan.get("intention"),
                     plan.get("modele"), [], "en cours")
    return lances


def variante_tient_le_rang(conv, tid, marque):
    """Ce tirage-ci devient-il « l'image courante » de la conversation ?

    LE PLUS PETIT RANG ABOUTI, et non le premier arrive. Les tirages d'un groupe
    finissent dans un ordre que personne ne choisit — deux machines, deux
    vitesses — et « agrandis-la » viserait sinon une image tiree au sort,
    differente a chaque fois pour le meme geste. Le rang, lui, ne depend
    d'aucune vitesse : le groupe designe donc toujours la meme image, quel que
    soit l'ordre d'arrivee.

    Le rang 1 tout court ne suffisait pas : quand ce tirage-la echoue ou qu'on
    le retire de la file — ce qui arrive apres un redemarrage, ou il attend dans
    _file.json comme les autres — plus AUCUNE variante ne devenait l'image
    courante, et « agrandis-la » visait en silence l'image d'avant le groupe.

    Un choix fait a la main (api_variante_choisir) prime sur tout : le rang 1
    qui finissait apres le clic reprenait la place que l'utilisateur venait de
    donner a une autre.
    """
    if not (marque or {}).get("groupe"):
        return True
    rang = marque.get("rang", 1)
    for t in conv.get("tours", []):
        if t.get("id") == tid:
            continue
        if (t.get("variantes") or {}).get("groupe") != marque["groupe"]:
            continue
        if t.get("choisie"):
            return False
        if (t.get("etat") == "fini" and t.get("fichiers")
                and (t.get("variantes") or {}).get("rang", 1) < rang):
            return False
    return True


async def executer(tid, texte, conv, image=None, modele_force=None, taille=None,
                   priorite="", noeud_force=None, plan_impose=None,
                   modele_choisi=False, graine=None, variantes=1):
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
        if plan_impose:
            # Rien a decider : ce plan a deja ete etabli, et son image regardee.
            # Refaire l'analyse rendrait un AUTRE prompt, donc une autre image —
            # et l'esquisse n'aurait servi a rien. Trois appels au modele de
            # langage economises au passage.
            plan = dict(plan_impose)
            # Deux gestes arrivent ici avec un plan tout fait, et ils ne
            # promettent pas la meme chose : repasser une esquisse au propre
            # (meme graine, plus d'etapes) et tirer une variante de plus (meme
            # plan, autre graine). Annoncer l'esquisse sur une variante decrivait
            # un geste que l'utilisateur n'avait pas fait, et un « tout le soin »
            # qui n'arrivait pas.
            if plan.pop("variante", None):
                journal(tid, "meme prompt, meme moteur et meme taille pour tout "
                             "le groupe — seule la graine change d'une variante "
                             "a l'autre")
            else:
                journal(tid, "meme prompt et meme moteur que l'esquisse, tout le "
                             "soin — la composition, elle, sera differente")
        else:
            plan = await aiguiller(texte, tid, conv, img_b64,
                                   a_une_image=(famille_du_fichier(image) if image
                                                else False),
                                   modele_force=modele_force, taille=taille,
                                   priorite=priorite,
                                   modele_choisi=modele_choisi)
        # UN MOTEUR IMPOSE NE RECOUVRE PAS UNE LECTURE. Decrire une image ne
        # produit rien : aucun moteur ne s'y applique, et lui en coller un
        # ramenait l'intention a « image ». Le raccourci tirait donc bien, et la
        # ligne suivante defaisait son travail — la demande repartait en
        # generation, l'enrichissement etait appele sans l'image et repondait
        # « je ne vois pas d'image attachee ». Constate deux fois : par la
        # recette, puis apres une premiere correction incomplete.
        #
        # Et plus largement : un moteur seulement HERITE de la conversation ne
        # defait pas ce qu'un raccourci ecrit a tranche. S'il avait ete choisi
        # pour cette demande, le raccourci ne se serait pas declenche.
        if modele_force and (plan.get("intention") == "lecture"
                             or (plan.get("raccourci") and not modele_choisi)):
            # Le NOM du moteur de la conversation, pas celui de son repli local.
            # « force_loin » a deja remplace modele_force par le repli plus haut :
            # sur une conversation reglee sur Veo, le message annonçait
            # « Wan 2.2 5B », et l'on cherchait le reglage au mauvais endroit.
            dit_ = force_loin or modele_force
            journal(tid, f"{(CATALOGUE.get(dit_) or MOTEURS_DISTANTS.get(dit_) or {}).get('titre', dit_)}"
                         f" est le moteur de cette conversation, mais cette "
                         f"demande n'en a pas besoin")
            modele_force = None
            # ET LE MOTEUR DISTANT AVEC. Sans cette ligne, « loin = force_loin »
            # reprenait la main six lignes plus bas : une video jointe avec
            # « rends-la fluide », sur une conversation reglee sur Veo, partait
            # produire une video NEUVE chez Veo — facturee a la seconde, et sans
            # rapport avec la demande.
            force_loin = None
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
        # Le dire plutot que de laisser croire. Un brouillon demande sur une
        # retouche coute son temps plein : le nombre d'etapes n'y est pas suivi.
        if priorite == "brouillon" and intention not in ESQUISSE_POSSIBLE:
            journal(tid, "le brouillon ne change rien pour ce genre de "
                         "demande — elle est rendue au soin habituel")
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
        if (not plan_impose
                and plan.get("intention") not in ("lecture", "agrandir",
                                                  "detourer", "fluidifier")):
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
            # CEINTURE. La bretelle est plus haut (normaliser) ; celle-ci existe
            # parce qu'une description inventee ne se signale pas, et qu'il y a
            # deux chemins pour arriver ici — le raccourci ecrit et le modele.
            if not img_b64:
                raise RuntimeError(
                    "il n'y a pas d'image a lire : joins une image, ou dis ce "
                    "que tu veux produire.")
            journal(tid, "lecture de l'image…")
            try:
                desc = await appeler_ollama(
                    texte or "Decris cette image en francais, precisement.",
                    img_b64, "Tu decris des images avec precision, en francais.",
                    json_mode=False, modele=MODELE_VISION, tid=tid)
            except Exception as e:
                # NE PAS nommer MODELE_VISION ici : chaque machine lit avec
                # SON modele voyant, et l'ancien message envoyait installer un
                # modele qui n'avait jamais ete essaye.
                raise RuntimeError(
                    f"aucune machine n'a su lire l'image ({type(e).__name__}). "
                    f"Il faut un modele qui sache voir, par exemple : "
                    f"ollama pull {MODELE_VISION}") from None
            if not desc.strip():
                raise RuntimeError("le modele de vision n'a rien renvoye.")
            TACHES[tid].update(etat="fini", description=desc, plan=plan)
            enregistrer_tour(conv, tid, texte, plan, "lecture", cle, [], "fini")
            journal(tid, "description produite", etat="fini")
            return

        # Les variantes ne valent que pour une creation, et le dire vaut mieux
        # que de rendre une seule image sans expliquer pourquoi. Meme forme que
        # le message du brouillon plus haut, pour la meme raison : un reglage
        # ignore en silence donne le sentiment de ne pas etre ecoute.
        if variantes > 1 and intention not in VARIANTES_POSSIBLE:
            journal(tid, "les variantes ne changent rien pour ce genre de "
                         "demande — elle est rendue une seule fois")
            variantes = 1

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
        # Le plafond vaut AUSSI pour un moteur distant choisi a la main dans la
        # liste : choix_distant passe par nuage_actif, force_loin non. Sans
        # cette ligne, le robinet se rouvrait d'un clic dans le menu des
        # moteurs. La demande en cours n'est pas cassee pour autant : le repli
        # local du moteur distant a deja ete pose plus haut.
        if loin and plafond_atteint(conv.get("proprietaire")):
            journal(tid, f"plafond du mois atteint "
                         f"({PREFERENCES.get('plafond_nuage')} appels distants) "
                         f"— la generation reste sur cette machine")
            plan["raison"] = "plafond du nuage atteint : repli sur le moteur local"
            loin = ""
        # UN FOURNISSEUR FACTURE CHAQUE IMAGE. Le plafond du mois compte des
        # appels, pas ce qu'on en attend : quatre variantes le viderait quatre
        # fois plus vite, pour un geste dont l'utilisateur ne voit pas le prix.
        # Les cartes de la maison, elles, ne coutent que du temps — c'est la que
        # les variantes ont leur place.
        if loin and variantes > 1:
            journal(tid, f"{MOTEURS_DISTANTS[loin]['titre']} facture chaque "
                         f"image : les variantes restent pour les cartes de la "
                         f"maison, cette demande en rend une")
            variantes = 1
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
                # LE MOTEUR REELLEMENT EMPLOYE, et non son repli local. « cle »
                # porte encore le moteur du catalogue qui aurait servi si le
                # fournisseur avait echoue : le tour l'enregistrait, et le devis
                # comptait donc trois videos rendues au loin comme des mesures
                # de Wan 2.2 5B — « compte 200 s » annonce pour une carte qui
                # n'a jamais rien fait de tel.
                enregistrer_tour(conv, tid, texte, plan, intention, loin,
                                 sorties, "fini")
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
        # Une machine dit calculer deja ce travail : c'est elle qu'il faut, et
        # aucune autre. Apres un redemarrage du studio, le repartiteur aurait
        # sinon pu en choisir une seconde — deux cartes sur la meme demande, et
        # le resultat de la premiere arrivant de toute façon.
        occupee_par = noeud_qui_travaille(tid)
        if occupee_par and noeud(occupee_par):
            cible = noeud(occupee_par)
            journal(tid, f"{cible.get('titre', occupee_par)} n'a jamais arrete "
                         f"cette demande — on la lui laisse")
        cible = cible or choisir_noeud(cle)
        if cible is None:
            # D'ABORD une machine vivante qui travaille, ENSUITE seulement une
            # machine en pause. L'ordre inverse faisait refuser une demande que
            # le NAS savait faire, au motif que le PC dormait.
            cible = await patienter_machine(cle, tid)
        if cible is None:
            # Peut-etre pas « aucune machine » : peut-etre « pas maintenant ».
            cible = await patienter_pause(cle, tid)
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
        # LE DEVIS. « Pourquoi celle-ci a mis quatre minutes » est une question
        # qu'on se pose apres ; « combien de temps ça va prendre » est celle
        # qu'on se pose avant, et rien n'y repondait. Le studio a pourtant la
        # reponse : chaque tour termine porte sa machine, son moteur, sa taille
        # et sa duree. On la lit.
        # Pas de devis pour un brouillon : il coute un quart des etapes, et
        # l'annonce lui donnerait le prix d'une image finie — quatre fois trop.
        mediane_, combien_ = (None, 0) if priorite == "brouillon" else duree_typique(
            ident, cle, f"{plan.get('largeur')}x{plan.get('hauteur')}"
            if plan.get("largeur") else None,
            pid=(TACHES.get(tid) or {}).get("proprietaire"))
        # LE DEVIS COMPTE UN SEUL RENDU, MEME QUAND ON EN LANCE QUATRE. C'est un
        # choix, pas un oubli, et il se tranche par l'usage qu'on en fait :
        # la page compare ce chiffre au TEMPS ECOULE DE CETTE BULLE pour dire
        # « plus long que d'habitude ». Un total de groupe y retarderait
        # l'alerte de quatre rendus — c'est-a-dire la supprimerait. Et chaque
        # tirage a sa bulle et son devis : mettre le total sur le seul premier
        # donnerait quatre promesses differentes pour quatre rendus identiques.
        # Le cout du GROUPE est un autre chiffre ; il est pose A COTE et non
        # par-dessus. Les deux etaient a l'ecran en meme temps sans que rien ne
        # dise qu'ils ne comptaient pas la meme chose : « 60 s » dans la
        # pastille, « 3 min » dans le journal, pour un groupe de trois.
        mot_devis = ""
        if mediane_:
            mot_devis = (f"{mediane_ / 60:.0f} min" if mediane_ >= 90
                         else f"{mediane_:.0f} s")
            # SUR LA TACHE, et pas seulement dans le journal. La page lisait la
            # phrase française pour en tirer le chiffre : reformuler cette
            # ligne aurait fait disparaitre la pastille en silence.
            devis_ = {"secondes": round(mediane_), "mesures": combien_}
            if variantes > 1:
                # Nommes, pour que le total n'ait plus a se deviner dans une
                # phrase française. Du temps de CARTE et non une duree
                # d'attente : la ligne de journal plus bas dit pourquoi on ne le
                # divise pas par le nombre de machines.
                devis_["rendus"] = variantes
                devis_["total_s"] = round(mediane_ * variantes)
            TACHES.setdefault(tid, {})["devis"] = devis_
            journal(tid, f"d'apres tes {combien_} rendus precedents, compte "
                         f"{mot_devis}")
        # « en offre None » : la taille de la carte vient de l'annonce, et une
        # machine qui rendait deja avant un redemarrage du studio ne s'est pas
        # encore reannoncee. Annoncer un debordement qu'on n'a pas constate,
        # c'est inquieter pour rien — et le rendu qui suivait ce message a mis
        # 223 s, soit son temps ordinaire.
        if not tient_vraiment(cle, ident) and (ETAT_NOEUDS.get(ident) or {}).get("vram"):
            journal(tid, f"{CATALOGUE[cle]['titre']} demande "
                         f"{CATALOGUE[cle].get('vram', 0)} Go et la carte en offre "
                         f"{ETAT_NOEUDS[ident]['vram']} Go : debordement sur la "
                         f"RAM, plus lent")
        journal(tid, f"{CATALOGUE[cle]['titre']} — {plan.get('raison','')}", plan=plan)
        # LES AUTRES TIRAGES PARTENT ICI, et le choix de l'endroit compte.
        # Pas plus tot : le plan est arrete, le moteur tient sur une carte, et la
        # machine de CE tirage est deja inscrite sur sa tache — choisir_noeud()
        # comptant les travaux qui visent chaque machine, les suivants iront donc
        # sur l'autre plutot que de s'empiler derriere celui-ci.
        # Pas plus tard non plus : le telechargement d'un modele absent peut
        # durer des minutes, et la seconde carte resterait a ne rien faire.
        if variantes > 1:
            soeurs = await lancer_variantes(tid, texte, conv, plan, variantes,
                                            taille, priorite, noeud_force, image)
            # LE DEVIS RESTE HONNETE : quatre variantes coutent quatre rendus, et
            # l'annonce d'au-dessus ne parlait que du premier. On le dit en temps
            # de CARTE et non en temps d'attente : combien de machines seront
            # libres a cette seconde-la, personne ne le sait — et promettre la
            # moitie parce qu'il y a deux cartes serait promettre a la place du
            # voisin qui a lui aussi une demande en file.
            #
            # LES DEUX CHIFFRES DANS LA MEME PHRASE, et le mot a mot de la
            # pastille en premier. Sans « chacune », l'utilisateur lisait
            # « 60 s » a cote de « 3 min » sans rien pour les rapprocher : deux
            # nombres qui se contredisent au lieu de deux nombres qui se
            # completent. Le seul cout est un « soit » de plus dans la ligne.
            journal(tid, f"{len(soeurs) + 1} variantes, donc autant de rendus"
                         + (f" — environ {mot_devis} chacune, soit "
                            f"{_duree_lisible(mediane_ * (len(soeurs) + 1))}"
                            f" de calcul en tout, reparti sur les machines libres"
                            if mediane_ else ""))
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

        # Imposee quand on repasse une esquisse au propre : c'est elle qui fait
        # que la grande image est bien celle qu'on a choisie en petit.
        seed = (int(plan.get("graine") or graine or 0)
                or int.from_bytes(os.urandom(4), "big") % (2**31))
        TACHES.setdefault(tid, {})["graine"] = seed
        # Ecrite dans la file : une reprise apres redemarrage doit refaire LA
        # MEME image, pas une autre. C'est aussi ce qui permet au tour de porter
        # la graine qui a reellement produit son image.
        if tid in EN_FILE and EN_FILE[tid].get("graine") != seed:
            EN_FILE[tid]["graine"] = seed
            sauver_file()
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
        # UNE SEULE DES VARIANTES DEVIENT « L'IMAGE COURANTE ». Elles finissent
        # dans un ordre que personne ne choisit — deux machines, deux vitesses —
        # et « agrandis-la » aurait donc vise une image tiree au sort, differente
        # a chaque fois pour le meme geste. C'est le plus petit rang abouti qui
        # la tient, jusqu'a ce que l'utilisateur en designe une autre
        # (api_variante_choisir) — la regle et ses deux raisons sont dans
        # variante_tient_le_rang.
        marque_ = (TACHES.get(tid) or {}).get("variantes") or {}
        if sorties and intention in ("image", "edition", "planche",
                                     "agrandir", "detourer") \
                and variante_tient_le_rang(conv, tid, marque_):
            # on garde le sous-dossier : il est indispensable pour retrouver le fichier
            conv["derniere_sortie"] = {"noeud": sorties[0].get("noeud"),
                                       "filename": sorties[0]["filename"],
                                       "subfolder": sorties[0].get("subfolder", "")}
        TACHES.setdefault(tid, {})["secondes"] = secondes
        enregistrer_tour(conv, tid, texte, plan, intention, cle, sorties, "fini")
        journal(tid, f"termine en {secondes:.0f} s", etat="fini")
    except MachineEnPause:
        # Elle ne dit pas un echec mais une remise a plus tard : le tour reste
        # « en cours », et c'est travailleur() qui met la demande de cote. Sans
        # ce relais, le filet ci-dessous l'ecrivait en erreur — exactement le
        # refus qu'on remplace, avec un autre texte.
        raise
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
        # On NE retire PAS de EN_FILE ici : la demande est commencee, pas finie,
        # et un redemarrage pendant son rendu la perdrait — le moment ou elle
        # vaut le plus cher. Elle sort du fichier quand elle est rendue.
        #
        # Et l'on n'ecrit PAS le fichier maintenant : a cet instant precis la
        # demande n'est plus dans ATTENTE et pas encore dans EN_VOL, donc
        # sauver_file() l'omettrait — c'est exactement ce qui a fait perdre un
        # rendu au premier essai. On ecrit une fois qu'elle est inscrite, plus
        # bas.
        if (TACHES.get(tid) or {}).get("annulee"):
            EN_FILE.pop(tid, None)
            sauver_file()
            FILE_ATTENTE.task_done()
            continue

        # Une tache nommee plutot qu'un simple await : c'est le seul moyen
        # d'arreter un travail qui n'a pas encore atteint ComfyUI — analyse,
        # ecriture des paroles, attente d'un fournisseur.
        # Une demande n'est retiree du fichier que si elle est VRAIMENT finie.
        # L'arret du studio annule les travailleurs, ce qui passe par le meme
        # « except CancelledError » qu'une annulation d'utilisateur — et le
        # « finally » effaçait alors la demande du fichier a la seconde meme ou
        # la persistance devait la sauver. Mesure : redemarrage en plein rendu,
        # fichier vide au reveil, demande perdue.
        fini_pour_de_bon = True
        travail = asyncio.create_task(
            executer(tid, job["texte"], job["conv"], job["image"], job["modele"],
                     job.get("taille"), job.get("priorite", ""), job.get("noeud"),
                     job.get("plan"), job.get("modele_choisi", False),
                     job.get("graine"), job.get("variantes", 1)))
        EN_VOL[tid] = travail
        # ICI, et pas avant : la demande appartient maintenant au registre des
        # travaux en vol, donc le fichier la portera.
        sauver_file()
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
            # Annulee PAR QUI ? Si l'utilisateur l'a retiree, elle est finie et
            # ne doit pas revenir. Si c'est l'arret du studio, elle n'a rien
            # demande a personne : elle reste dans le fichier et repartira au
            # reveil.
            fini_pour_de_bon = bool((TACHES.get(tid) or {}).get("annulee"))
            ident_t = (TACHES.get(tid) or {}).get("noeud") or ""
            if est_agent(ident_t) and ETAT_NOEUDS.get(ident_t, {}).get("repond"):
                TACHES.setdefault(tid, {"etapes": []}).update(etat="erreur")
            else:
                journal(tid, "interrompue", etat="erreur")
            if ARRET:
                # On relaie : sans ce « raise », le travailleur avalait son
                # propre arret et repartait attendre a la porte. Le « finally »
                # ci-dessous tourne quand meme.
                raise
        except MachineEnPause as e:
            # Ni un echec ni une fin : la demande est mise de cote et le
            # travailleur repart AUSSITOT chercher la suivante. Il n'y en a que
            # trois, et rester la a guetter une carte que son proprietaire ne
            # rallumera peut-etre pas ce soir fermerait un tiers du studio.
            #
            # « fini_pour_de_bon » reste faux : la demande garde sa place dans
            # EN_FILE, donc dans _file.json, et un redemarrage la retrouve.
            fini_pour_de_bon = not armer(tid, e)
            if fini_pour_de_bon:
                # Reglage a zero, ou demande deja retiree pendant l'analyse : le
                # refus d'avant reste le bon message dans ces deux cas-la.
                echouer(tid, e.refus)
        except Exception as e:                       # filet : la file ne doit jamais mourir
            journal(tid, f"ERREUR inattendue : {e}", etat="erreur")
            fini_pour_de_bon = True
        finally:
            EN_VOL.pop(tid, None)
            # La progression d'une machine a agent n'a personne pour la remettre
            # a zero : le studio ecoute SA websocket, pas la sienne. Sans cette
            # ligne, la barre du travail suivant demarrait la ou le precedent
            # s'etait arrete.
            AVANCES.pop(tid, None)
            if fini_pour_de_bon:
                EN_FILE.pop(tid, None)
                sauver_file()
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


async def api_au_propre(req):
    """Refait la demande d'une esquisse avec tout le soin.

    Meme prompt, meme moteur, meme graine, meme taille : tout ce qui a ete
    etabli est repris tel quel, et seul le nombre d'etapes remonte. On ne
    repasse pas par l'analyse — elle rendrait un autre prompt, donc un autre
    sujet, et l'on ne saurait plus ce qu'on compare. Trois appels au modele de
    langage economises au passage.

    Ce que cette route NE PROMET PAS : la meme image en mieux. Le nombre
    d'etapes change la trajectoire du debruitage, et la graine ne fixe que son
    point de depart. L'image soignee traite le meme sujet, dans le meme style,
    avec le meme moteur — mais sa composition sera differente. Mesure du
    31 aout. Le libelle du bouton le dit, et cette docstring aussi, parce que
    l'inverse a ete ecrit ici pendant une heure.
    """
    pid = qui(req)
    try:
        d = await req.json()
    except Exception:
        return web.json_response({"erreur": "corps illisible"}, status=400)
    # ouvrable() et non une formule recopiee : « a moi ET pas fermee ». La
    # version d'avant acceptait une conversation FERMEE — un second onglet reste
    # dessus relançait un rendu de plusieurs minutes vers une image que
    # purger_fermees() effacerait le lendemain — et une conversation orpheline,
    # que api_conversation refuse pourtant de laisser lire.
    conv = CONVERSATIONS.get(d.get("conversation") or "")
    if not ouvrable(conv, pid):
        return web.json_response({"erreur": "inconnue"}, status=404)
    tour = next((t for t in conv.get("tours", [])
                 if t.get("id") == d.get("tour")), None)
    if not tour:
        return web.json_response({"erreur": "inconnue"}, status=404)
    if tour.get("au_propre"):
        return web.json_response(
            {"erreur": "cette esquisse a deja ete passee au propre"}, status=409)
    plan_ = tour.get("plan")
    if not tour.get("esquisse") or not isinstance(plan_, dict):
        return web.json_response(
            {"erreur": "ce tour n'est pas une esquisse qu'on sache refaire"},
            status=400)
    if tour.get("etat") != "fini":
        return web.json_response(
            {"erreur": "l'esquisse n'est pas terminee"}, status=409)
    plan = dict(plan_)
    # Les etapes se recalculent depuis la proposition BRUTE du modele : c'est
    # exactement ce que la demande aurait donne sans le cran « brouillon ».
    plan["priorite"] = ""
    plan = appliquer_parametres(plan)
    plan["graine"] = tour.get("graine")
    texte = tour.get("demande") or ""
    tid = uuid.uuid4().hex
    devant = len(ATTENTE) + len(EN_VOL)
    TACHES[tid] = {"etapes": [], "etat": "en cours", "demande": texte,
                   "conversation": conv["id"], "proprietaire": pid, "image": None}
    enregistrer_tour(conv, tid, texte, {}, None, None, [], "en cours")
    # La marque sur l'esquisse, pour ne pas la reproposer indefiniment. Posee
    # AVANT la mise en file : si le studio s'arrete entre les deux, mieux vaut un
    # bouton disparu qu'une seconde grande image identique.
    tour["au_propre"] = tid
    sauver(conv)
    if devant:
        journal(tid, f"en file d'attente — {devant} demande(s) devant")
    ATTENTE.append(tid)
    EN_FILE[tid] = {"tid": tid, "texte": texte, "conversation": conv["id"],
                    "proprietaire": pid, "image": None, "modele": None,
                    "taille": None, "priorite": "", "noeud": None, "plan": plan}
    sauver_file()
    await FILE_ATTENTE.put({"tid": tid, "texte": texte, "conv": conv, "taille": None,
                            "image": None, "modele": None, "priorite": "",
                            "noeud": None, "plan": plan})
    return web.json_response({"id": tid, "conversation": conv["id"],
                              "position": devant})


async def api_variante_choisir(req):
    """Designe la variante retenue : c'est elle que « la » designera ensuite.

    Sans ce geste, « agrandis-la », « rends-la fluide » ou « le meme personnage »
    visaient l'image courante de la conversation — et de quatre variantes, la
    courante etait la derniere ARRIVEE : deux machines, deux vitesses, un ordre
    que personne ne choisit. Le studio s'en tient donc au plus petit rang abouti
    (voir variante_tient_le_rang) jusqu'a ce qu'on en designe une autre ici. Et
    ce geste-ci prime : la meme garde empeche un tirage plus petit, qui finit
    apres le clic, de reprendre la place qu'on vient de donner.

    Choisir ne supprime rien : chaque variante reste un tour entier, avec son
    fichier, son pouce et son bouton « refaire en soigne ». Ce bouton-la n'a
    jamais eu besoin de cette route — il vise le tour sur lequel on clique.
    """
    pid = qui(req)
    try:
        d = await req.json()
    except Exception:
        return web.json_response({"erreur": "corps illisible"}, status=400)
    # ouvrable() et non une formule recopiee, comme api_au_propre : « a moi ET
    # pas fermee ». Une conversation fermee ou orpheline ne se modifie pas.
    conv = CONVERSATIONS.get(d.get("conversation") or "")
    if not ouvrable(conv, pid):
        return web.json_response({"erreur": "inconnue"}, status=404)
    tour = next((t for t in conv.get("tours", [])
                 if t.get("id") == d.get("tour")), None)
    if not tour or tour.get("etat") != "fini" or not tour.get("fichiers"):
        # 404 et non 400 : un tour qui n'a rien produit n'est rien a designer,
        # et distinguer « pas a toi » de « pas fini » renseignerait un curieux.
        return web.json_response({"erreur": "inconnue"}, status=404)
    f = tour["fichiers"][0]
    conv["derniere_sortie"] = {"noeud": f.get("noeud"), "filename": f["filename"],
                               "subfolder": f.get("subfolder", "")}
    # Le personnage suit la variante choisie, mais SEULEMENT s'il y en avait
    # deja un : poser une reference que personne n'a demandee ferait basculer
    # les demandes suivantes dans un chemin qu'elles n'empruntaient pas.
    if conv.get("personnage"):
        conv["personnage"] = dict(conv["derniere_sortie"])
    # La marque sur le tour, pour que la page sache laquelle est encadree apres
    # un rechargement. Une seule a la fois dans un groupe : choisir la troisieme
    # doit decocher la premiere, sinon deux images se disent « la ».
    groupe = (tour.get("variantes") or {}).get("groupe")
    if groupe:
        for t in conv.get("tours", []):
            if (t.get("variantes") or {}).get("groupe") == groupe:
                t["choisie"] = True if t.get("id") == tour["id"] else None
    else:
        tour["choisie"] = True
    sauver(conv)
    return web.json_response({"ok": True, "tour": tour["id"]})


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
    # La conversation d'abord : c'est elle qui porte les reglages, et une
    # demande qui n'en parle pas herite des siens. Mais on FUSIONNE sans ecrire
    # tant que la demande n'est pas validee : un « priorite: urgent » refuse en
    # 400 laissait sinon son reglage sur la conversation, et sauvait au passage
    # une conversation que conv_de() garde volontairement en memoire — sans quoi
    # chaque requete sans cookie deposait un fichier de plus.
    conv = conv_de(d.get("conversation"), pid)
    # CHOISI MAINTENANT, ou seulement herite ? Deux versions se sont trompees
    # avant celle-ci, et toutes deux DEDUISAIENT.
    #
    # « une cle modele presente » : toujours vrai, la page renvoie l'etat de ses
    # menus, qu'elle vient de remplir depuis la conversation.
    # « la valeur differe de celle de la conversation » : toujours FAUX, parce
    # que le menu poste son reglage des qu'il change — au moment de la demande,
    # la conversation porte deja la valeur. Et cette version-la etait pire que
    # la premiere : a faux permanent, un moteur explicitement choisi se faisait
    # jeter par les raccourcis.
    #
    # Le serveur ne peut pas savoir : seule la page sait laquelle des deux
    # choses elle fait. Elle le dit. On garde la comparaison en repli pour un
    # client qui n'est pas la page — imparfaite, mais mieux que rien.
    if "modele_choisi" in d:
        choisi = bool(d.get("modele_choisi"))
    else:
        choisi = bool(d.get("modele")) and d["modele"] != reglages_de(conv).get("modele")
    reglages = poser_reglages(conv, d, ecrire=False)
    taille = reglages.get("taille") or None
    if taille and taille not in TAILLES:
        return web.json_response({"erreur": "taille non prise en charge"}, status=400)
    modele = reglages.get("modele") or None
    if modele and modele not in CATALOGUE and modele not in MOTEURS_DISTANTS:
        return web.json_response({"erreur": "moteur inconnu"}, status=400)
    if modele in MOTEURS_DISTANTS and not moteur_distant_pret(modele):
        return web.json_response(
            {"erreur": "ce moteur demande une cle d API, a poser dans /admin"},
            status=400)
    priorite = reglages.get("priorite") or ""
    if priorite not in PRIORITES:
        return web.json_response({"erreur": "priorite inconnue"}, status=400)
    # « variantes » NE PASSE PAS PAR poser_reglages, et c'est delibere : comme le
    # brouillon, c'est un geste et non un reglage. Le retenir sur la conversation
    # ferait partir en quatre exemplaires les cinq demandes suivantes — quatre
    # fois le temps de carte, pour tout le monde — sans que personne l'ait voulu.
    # Le commentaire de poser_reglages dit deja pourquoi pour le brouillon ; ici
    # l'argument est le meme, multiplie par quatre.
    try:
        variantes = int(d.get("variantes") or 1)
    except (TypeError, ValueError):
        return web.json_response({"erreur": "nombre de variantes illisible"},
                                 status=400)
    if not 1 <= variantes <= VARIANTES_MAX:
        return web.json_response(
            {"erreur": f"de 1 a {VARIANTES_MAX} variantes"}, status=400)
    machine = reglages.get("noeud") or None
    if machine and noeud(machine) is None:
        return web.json_response({"erreur": "machine inconnue"}, status=400)
    # Une image appartient a celui qui l'a televersee. Deux pieges ici :
    # « != pid » et non « not in (None, pid) » — un nom absent du registre valait
    # laissez-passer ; et le nom doit rester un NOM, pas un chemin : « ../output/
    # studio/…png » sortait de ComfyUI/input et faisait decrire l'image d'un autre.
    if image and (os.path.basename(image) != image or ENTREES.get(image) != pid):
        return web.json_response({"erreur": "image inconnue"}, status=404)
    # Tout est valide : maintenant seulement, la conversation retient.
    poser_reglages(conv, d)
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
                    "taille": taille, "priorite": priorite, "noeud": machine,
                    "modele_choisi": choisi, "variantes": variantes}
    sauver_file()
    await FILE_ATTENTE.put({"tid": tid, "texte": texte, "conv": conv, "taille": taille,
                            "image": image, "modele": modele, "priorite": priorite,
                            "noeud": machine, "modele_choisi": choisi,
                            "variantes": variantes})
    # Le nombre DEMANDE, pas le nombre qui partira : l'aiguillage n'a pas encore
    # tourne, et une demande qui se revele etre une retouche n'en rendra qu'une.
    # La page peut reserver la place ; c'est api_etat, une fois le groupe pose,
    # qui dira ce qu'il en est reellement.
    return web.json_response({"id": tid, "conversation": conv["id"],
                              "position": devant, "variantes": variantes})

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
    # Esquisse ou non, et deja repassee au propre ou non. Ces deux marques
    # vivent sur le TOUR et pas sur la tache, si bien que la page ne les
    # apprenait qu'au rechargement suivant de la conversation — c'est-a-dire pas
    # au moment ou l'on vient de lancer un brouillon et ou l'on en a justement
    # besoin. Une page rechargee pendant le calcul voyait la bulle se terminer
    # sans pastille ni bouton.
    tour_ = next((t for t in (CONVERSATIONS.get(tache.get("conversation"))
                              or {}).get("tours", [])
                  if t.get("id") == tid), None) or {}
    etat["esquisse"] = bool(tour_.get("esquisse"))
    etat["au_propre"] = tour_.get("au_propre")
    # ARMEE, et pour combien de temps encore. La marque ne vivait que sur
    # /api/file : la bulle dependait donc d'un sondage separe, et une page
    # rechargee affichait « en cours » pendant deux secondes et demie — assez
    # pour le lire et le croire.
    a_ = ARMEES.get(tid)
    if a_:
        etat["armee"] = {"reste_h": max(0.0, (a_["jusqua"] - time.time()) / 3600)}
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
             # « attente machine » avant tout le reste : la demande est
             # armee, elle n'est ni dans la file ni sur une carte, elle attend
             # qu'une machine en pause revienne. C'est le seul etat ou l'attente
             # se compte en heures, donc le seul qu'il faille vraiment nommer.
             "etat": ("attente machine" if tid in ARMEES
                      else "attente carte" if t.get("attend_carte")
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
    admin = est_admin(req)
    mien = lambda t: TACHES.get(t, {}).get("proprietaire") == pid
    lignes = []
    for tid_vol in list(EN_VOL):
        a = AVANCES.get(tid_vol) or {}
        lignes.append(dict(_ligne_file(tid_vol, pid, admin, 0), en_cours=True,
                           avance=dict(a) if a.get("total") else None))
    for rang, tid in enumerate(ATTENTE, start=1):
        lignes.append(dict(_ligne_file(tid, pid, admin, rang), en_cours=False))
    # Les armees en dernier, et sans rang : elles n'attendent pas la carte mais
    # son proprietaire, et se ranger devant ou derriere quelqu'un n'a aucun sens
    # pour elles. Les montrer est indispensable — c'est de cette ligne que part
    # le bouton « retirer », le seul recours de l'utilisateur.
    for tid_arme in list(ARMEES):
        reste = (ARMEES[tid_arme].get("jusqua", 0) - time.time()) / 3600
        lignes.append(dict(_ligne_file(tid_arme, pid, admin, 0), en_cours=False,
                           armee=True, reste_h=max(0.0, reste)))
    return web.json_response({
        # Le premier des miens qui calcule : la page s'en sert pour savoir
        # qu'elle a quelque chose sur le feu, pas pour compter.
        "en_cours": next((t for t in EN_VOL if mien(t)), None),
        "occupe": bool(EN_VOL),
        "en_attente": len(ATTENTE),
        # Les travaux EN VOL comptent aussi. Le compteur de l'en-tete ajoutait
        # « 1 si occupe » a la file d'attente : c'etait juste du temps ou un seul
        # travail pouvait courir. Avec trois travailleurs, l'utilisateur lisait
        # « 1 en file » et voyait trois lignes dans le panneau — le compteur et
        # la liste ne comptaient pas la meme chose.
        "en_vol": len(EN_VOL),
        # Combien attendent une machine en pause. Sert a l'en-tete : une file
        # vide avec trois demandes armees n'est pas une file vide.
        "armees": len(ARMEES),
        # Les armees comptent dans « a moi » : la demande n'est pas perdue, et
        # ce compteur est le seul endroit ou l'utilisateur peut s'en souvenir.
        "a_moi": sum(1 for t in list(ATTENTE) + list(EN_VOL) + list(ARMEES)
                     if mien(t)),
        "admin": admin,
        "lignes": lignes,
        # conserve : d'anciennes pages peuvent encore le lire
        "demandes": [TACHES[t].get("demande", "")[:60] for t in ATTENTE if mien(t)],
    })


async def api_file_annuler(req):
    """Retire une demande de la file, ou interrompt celle qui calcule."""
    pid = qui(req)
    admin = est_admin(req)
    tid = req.match_info["tid"]
    t = TACHES.get(tid)
    if not t:
        return web.json_response({"erreur": "demande inconnue"}, status=404)
    if t.get("proprietaire") != pid and not admin:
        # 404 et non 403 : repondre « interdit » confirmerait que la demande
        # existe, et permettrait de sonder la file d'un autre.
        return web.json_response({"erreur": "demande inconnue"}, status=404)

    if (tid in ATTENTE or tid in ARMEES
            or (t.get("etat") or "en attente") == "en attente"):
        if tid in ATTENTE:
            ATTENTE.remove(tid)
        # Une demande armee attend une machine, pas un travailleur : il n'y a
        # rien a interrompre, il suffit de la desarmer. Sans cette ligne le
        # retrait repondait « cette demande est deja terminee » — son etat est
        # « en cours » — et la demande repartait a la sortie de pause, des
        # heures apres que l'utilisateur l'a retiree.
        ARMEES.pop(tid, None)
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
        # Les reglages voyagent avec la liste : la page les remet dans ses menus
        # au changement de conversation, sans un second aller-retour.
        "conversations": [{"id": c["id"], "titre": c["titre"], "cree": c["cree"],
                           "tours": len(c["tours"]),
                           "reglages": reglages_de(c)} for c in liste]})

async def api_conversation(req):
    """Lecture pure : ne change pas la conversation courante du serveur.
    La bascule se fait explicitement par POST /api/conversation/{cid}/activer."""
    pid = qui(req)
    cid = req.match_info.get("cid")
    if cid and not ouvrable(CONVERSATIONS.get(cid), pid):
        return web.json_response({"erreur": "inconnue"}, status=404)
    return web.json_response(conv_de(cid, pid))

async def api_conv_reglages(req):
    """Pose les reglages d'une conversation sans rien lancer.

    Choisir un moteur dans le menu, c'est deja decider — et ce choix se perdait
    tant qu'aucune demande n'etait envoyee : les reglages n'etaient ecrits que
    par /api/generer. On ouvrait le tiroir, on prenait FLUX.1 en 1920x1080, on
    passait voir une autre conversation, et le choix n'existait plus au retour.
    """
    pid = qui(req)
    cid = req.match_info["cid"]
    conv = CONVERSATIONS.get(cid)
    if not ouvrable(conv, pid):
        return web.json_response({"erreur": "inconnue"}, status=404)
    try:
        d = await req.json()
    except Exception:
        return web.json_response({"erreur": "corps illisible"}, status=400)
    # Les memes controles que pour une demande : un reglage qui nomme un moteur
    # inconnu ne doit pas dormir sur une conversation en attendant de la faire
    # echouer plus tard.
    if d.get("modele") and d["modele"] not in CATALOGUE             and d["modele"] not in MOTEURS_DISTANTS:
        return web.json_response({"erreur": "moteur inconnu"}, status=400)
    if d.get("taille") and d["taille"] not in TAILLES:
        return web.json_response({"erreur": "taille non prise en charge"}, status=400)
    if d.get("priorite") and d["priorite"] not in PRIORITES:
        return web.json_response({"erreur": "priorite inconnue"}, status=400)
    if d.get("noeud") and noeud(d["noeud"]) is None:
        return web.json_response({"erreur": "machine inconnue"}, status=400)
    avant = (conv.get("murmures") or [])[-1:]
    poser_reglages(conv, d)
    apres = (conv.get("murmures") or [])[-1:]
    # Le murmure tout juste ecrit, s'il y en a un : la page l'ajoute au fil sans
    # avoir a tout recharger.
    return web.json_response({"reglages": reglages_de(conv),
                              "murmure": apres[0] if apres != avant else None})


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

def est_admin(req):
    """Le compte connecte administre-t-il ce studio.

    La meme formule etait recopiee a chaque usage ; elle en a trois de plus
    aujourd'hui, et une regle de visibilite ne doit pas dependre d'une recopie
    fidele.
    """
    return bool(req.get("compte")) and COMPTES.est_admin(req["compte"])


def tous_les_fichiers():
    """Tout ce que ce studio a produit, pour un administrateur.

    Il voit deja les conversations, les retours et les rendus depuis sa
    console : lui refuser la mediatheque relevait de l'oubli, pas d'une
    protection. Les conversations FERMEES en sont exclues comme pour tout le
    monde — elles attendent leur effacement, elles ne sont plus a personne.
    """
    defaut = noeud_local()["id"]
    return {(f.get("noeud") or defaut, f.get("subfolder", ""), f.get("filename"))
            for c in CONVERSATIONS.values() if not c.get("ferme")
            for t in c.get("tours", []) for f in (t.get("fichiers") or [])
            if f.get("filename")}


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
    admin = est_admin(req)
    items = []
    # mes_conversations() et non CONVERSATIONS : elle ecarte les fermees, comme
    # le fait mes_fichiers() du cote du service. Les deux divergeaient, et la
    # mediatheque affichait des vignettes que /api/fichier refusait ensuite —
    # image cassee, telechargement mort, « reprendre » mort, pour un fichier qui
    # est pourtant toujours la.
    #
    # Un administrateur voit tout le studio, chaque piece nommee par son
    # proprietaire. Il voit deja les conversations et les retours dans sa
    # console : lui refuser la mediatheque relevait de l'oubli.
    vues = ([c for c in CONVERSATIONS.values() if not c.get("ferme")] if admin
            else mes_conversations(pid))
    for conv in vues:
        for tour in conv.get("tours", []):
            for f in (tour.get("fichiers") or []):
                nom = f.get("filename") or ""
                items.append({
                    "filename": nom, "subfolder": f.get("subfolder", ""),
                    "type": f.get("type", "output"), "noeud": f.get("noeud"),
                    "famille": famille_sortie(nom),
                    "demande": (tour.get("demande") or "")[:120],
                    # Le prompt REELLEMENT envoye au moteur, apres
                    # enrichissement et traduction. C'est lui qui explique un
                    # rendu qu'on ne s'explique pas, et il n'etait visible nulle
                    # part une fois la conversation refermee.
                    "prompt": (tour.get("prompt") or "")[:400],
                    "moteur": tour.get("modele"),
                    # Une esquisse ne se confond pas avec une image finie. Trois
                    # jours plus tard, rien d'autre ne permet de les distinguer
                    # dans une mediatheque — meme prompt, meme moteur, meme
                    # taille, seul le soin change.
                    "esquisse": bool(tour.get("esquisse")),
                    # QUEL TIRAGE, SUR COMBIEN. Quatre variantes d'une meme
                    # demande ont le meme prompt, le meme moteur, la meme taille
                    # et la meme minute : sans ce rang, la mediatheque en montrait
                    # quatre lignes rigoureusement indiscernables.
                    "variante": ((tour.get("variantes") or {}).get("rang")
                                 if (tour.get("variantes") or {}).get("sur", 1) > 1
                                 else None),
                    "variantes": (tour.get("variantes") or {}).get("sur"),
                    "choisie": bool(tour.get("choisie")),
                    "taille": tour.get("taille"),
                    "secondes": tour.get("secondes"),
                    "heure": tour.get("heure"),
                    "quand": _date_sortie(f, conv),
                    "conversation": conv["id"],
                    "titre": (conv.get("titre") or "")[:60],
                    # Seulement pour un administrateur : personne d'autre n'a a
                    # savoir qui a produit quoi.
                    "a": (dossier_utilisateur(conv.get("proprietaire"))
                          if admin else None),
                })
    # Les plus recents d'abord : c'est ce qu'on vient chercher neuf fois sur dix.
    # Trier sur la date du FICHIER et non sur l'ordre de CONVERSATIONS, qui est
    # celui d'os.listdir — c'est-a-dire aucun ordre.
    items.sort(key=lambda x: x["quand"], reverse=True)
    compte = {}
    for it in items:
        compte[it["famille"]] = compte.get(it["famille"], 0) + 1
    return web.json_response({"fichiers": items[:600], "compte": compte,
                              "total": len(items), "tout": admin})


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
    permis = tous_les_fichiers() if est_admin(req) else mes_fichiers(qui(req))
    if noeud(ident) is None or (ident, sous, nom) not in permis:
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
            # Le filet des demandes armees. Les deux reveils precis — la sortie
            # de pause et le battement de la machine — couvrent ce qu'on sait
            # anticiper ; celui-ci couvre le reste : un registre modifie a la
            # main, un modele arrive, une autre machine devenue capable. Et
            # c'est le seul endroit ou une attente expiree peut etre dite.
            await expirer_armees()
            await reveiller_armees()
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


# PREFERENCES et non REGLAGES : ce dernier existe depuis longtemps dans ce
# fichier, et porte les parametres PAR MOTEUR — etapes, cfg. Le reutiliser ici
# l'a purement et simplement ecrase : « REGLAGES["klein9b"] » levait un KeyError
# au milieu d'une generation, et l'utilisateur l'a vu dans la minute.
FICHIER_PREFERENCES = os.path.join(DOSSIER_CONV, "_reglages.json")
# Combien de minutes une machine peut rester en pause en continuant de faire
# patienter les demandes qui la reclament. Au-dela, on refuse plutot que de
# laisser esperer : personne ne surveille une pause d'une heure.
# Et combien d'HEURES la demande reste ensuite armee, prete a repartir toute
# seule au retour de la machine. Douze : une pause commencee le soir se termine
# le lendemain matin, et c'est la plus longue absence au bout de laquelle une
# image qui arrive toute seule fait encore plaisir plutot que peur. A zero, on
# retrouve le refus immediat d'avant — pour qui prefere qu'un refus soit un refus.
#
# « plafond_nuage » : combien d'appels distants un compte peut faire dans le
# mois. Zero, le defaut, veut dire aucune limite — le studio se comporte alors
# exactement comme avant.
# Les memes bornes a la lecture et a l'ecriture : deux tables se seraient
# separees, et c'est par la que le fichier acceptait ce que le POST refusait.
BORNES_REGLAGES = {
    "pause_propose": (0, 1440, "une duree en minutes, de 0 a 1440"),
    "armee_heures": (0, 168, "une duree en heures, de 0 a 168"),
    "plafond_nuage": (0, 100000, "un nombre d'appels, de 0 a 100000")}
PREFERENCES = {"pause_propose": int(os.environ.get("STUDIO_PAUSE_PROPOSE") or 30),
               "armee_heures": int(os.environ.get("STUDIO_ARMEE_HEURES") or 12),
               "plafond_nuage": int(os.environ.get("STUDIO_PLAFOND_NUAGE") or 0)}


def charger_reglages():
    """Relit les reglages, CLEF PAR CLEF.

    La comprehension d'avant etait evaluee entierement avant l'update : une
    seule valeur illisible — un « null » laisse par une version anterieure —
    et les TROIS reglages repartaient a leur defaut, en silence. Les
    quarante-cinq minutes posees par l'administrateur disparaissaient sans que
    rien ne le dise.

    Et les memes bornes qu'a l'ecriture, dont le refus des booleens :
    « isinstance(True, int) » vaut vrai, donc un JSON portant « true » posait
    le reglage a une heure. Le POST s'en protegeait, la lecture non.
    """
    try:
        with open(FICHIER_PREFERENCES, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return
    if not isinstance(d, dict):
        return
    for k, v in d.items():
        if k not in PREFERENCES or k not in BORNES_REGLAGES:
            continue
        bas, haut, _ = BORNES_REGLAGES[k]
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            print(f"  reglage « {k} » illisible dans le fichier — on garde "
                  f"{PREFERENCES[k]}", flush=True)
            continue
        if not bas <= v <= haut:
            print(f"  reglage « {k} » hors bornes ({v}) — on garde "
                  f"{PREFERENCES[k]}", flush=True)
            continue
        PREFERENCES[k] = int(v)


def sauver_reglages():
    try:
        tmp = FICHIER_PREFERENCES + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(PREFERENCES, f, ensure_ascii=False, indent=1)
        os.replace(tmp, FICHIER_PREFERENCES)
    except OSError:
        pass


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
                      "pause": x.get("pause"),
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
    # Ce qu'elle calcule en ce moment. Le studio perd sa table des travaux a
    # chaque redemarrage ; sans cette liste, reprendre_file() renvoyait une
    # demande dont le rendu tournait encore la-bas, et la carte faisait deux fois
    # le meme travail — la seconde fois pour rien.
    # Ecrite a CHAQUE annonce, cle absente valant liste vide. Ne l'ecrire que
    # lorsqu'elle est presente laissait une revendication vivre pour toujours :
    # l'annonce « comfy: False », celle d'une machine dont la carte vient de
    # tomber, ne porte pas cette cle. Le studio croyait donc qu'elle calculait
    # encore, s'y rebranchait, et attendait une heure une reponse qui ne
    # viendrait pas — alors qu'une autre machine etait libre. Un agent d'avant
    # le 31 aout, qui ne connait pas ce champ, produisait le meme blocage.
    etat["travaux"] = [t for t in (d.get("travaux") or [])
                       if isinstance(t, str)][:8]
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
    # Ce qu'on vient d'apprendre d'elle, garde pour le prochain reveil. Ecrit au
    # plus une fois toutes les trente secondes : trois machines qui battent
    # toutes les dix secondes ecriraient sinon ce fichier neuf fois par minute
    # pour rien.
    sauver_parc()
    # Une machine eteinte pendant sa pause ne repasse pas par /admin en
    # revenant : elle se contente de s'annoncer. C'est donc ici aussi que se
    # reveille ce qui l'attendait. Le test vit dans reveiller_armees(), qui ne
    # relance que si une machine est VRAIMENT eligible — le battement d'une
    # machine encore en pause ne declenche rien, six fois par minute.
    if ARMEES:
        await reveiller_armees(x["id"])
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
    # « vu », ici aussi. Pendant un rendu l'agent ne s'annonce plus : sa boucle
    # est occupee a rendre, et seule cette route bat. Une machine qui calcule
    # depuis plus de quarante-cinq secondes etait donc declaree perdue, et le
    # repartiteur repondait « aucune machine ne repond » pendant qu'une carte
    # tournait. Ce battement-la prouve davantage qu'une annonce : il vient de la
    # boucle d'echantillonnage de ComfyUI.
    #
    # Et l'on retient CE QU'ELLE CALCULE. C'etait annonce, mais l'annonce
    # n'arrive qu'entre deux travaux — quand la liste est deja vide. Le seul
    # moment ou cette information existe est donc le seul ou personne ne
    # l'ecrivait : noeud_qui_travaille() ne pouvait rien rendre, et le
    # rattachement d'apres redemarrage n'a jamais servi. Mesure du 31 aout : le
    # studio a repris une demande que le NAS rendait encore, a refait son
    # analyse, puis a cherche une SECONDE carte pour la meme image.
    if isinstance(tid_dit, str):
        etat_ = ETAT_NOEUDS.setdefault(x["id"], {})
        # « repond » et pas seulement « vu ». Contrairement a la reclamation de
        # travail, ce battement-ci ne prouve pas que l'agent est la : il prouve
        # que SA CARTE tourne, puisqu'il sort de la boucle d'echantillonnage de
        # ComfyUI. Apres un redemarrage du studio, la machine qui reprend son
        # propre rendu restait sinon marquee muette pendant toute la duree de ce
        # rendu, et le repartiteur repondait « aucune machine ne repond » a la
        # demande suivante.
        etat_.update(vu=time.time(), repond=True, agent=True)
        # Une demande que le studio connait, et pas n'importe laquelle : ce
        # qu'on ecrit ici sert a lui rendre un resultat sans verifier a qui le
        # travail avait ete confie. Une machine ne peut donc pas se declarer
        # occupee par un identifiant de son choix.
        if tid_dit in EN_FILE or tid_dit in TACHES:
            etat_["travaux"] = [tid_dit]
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
                # La machine et la duree viennent de l'agent : TACHES est vide
                # apres un redemarrage, et enregistrer_tour() les y aurait
                # cherchees en vain. Sans ces deux champs, le detail d'un rendu
                # rattache restait muet sur qui l'avait fait et en combien de
                # temps — les deux choses qu'on lui demande.
                tour.update(etat="fini", erreur=None, fichiers=fichiers,
                            noeud=x["id"], secondes=d.get("secondes"))
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
                              # Une clef (adresse, modele) ne se serialise pas
                              # en JSON, et « qwen2.5vl:7b » seul ne dirait plus
                              # la verite depuis qu'un modele peut echouer ici
                              # et tourner ailleurs. On nomme la machine.
                              "modeles_casses": {
                                  f"{nom} — sur "
                                  + ((noeud(cerveau(u).get('noeud')) or {})
                                     .get("titre") or u): p
                                  for (u, nom), p in MODELES_CASSES.items()},
                              "pause_propose": PREFERENCES["pause_propose"],
                              "armee_heures": PREFERENCES["armee_heures"],
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


async def api_admin_pause(req):
    """Met une machine en pause, ou l'en sort. Elle continue de s'annoncer.

    Une pause n'est pas un retrait : le jeton reste valable, l'agent garde sa
    configuration, la machine reste visible et son inventaire a jour. Elle ne
    reçoit simplement plus de travail — « je vais jouer un peu, mais le studio
    doit rester utilisable ».
    """
    if not admin_ok(req):
        return web.json_response({"erreur": "acces refuse"}, status=403)
    x = REGISTRE.get(req.match_info["ident"])
    if not x:
        return web.json_response({"erreur": "machine inconnue"}, status=404)
    try:
        d = await req.json()
    except Exception:
        d = {}
    if d.get("pause"):
        x["pause"] = time.time()
    else:
        x.pop("pause", None)
    sauver_registre()
    print(f"  {x.get('titre', x['id'])} "
          + ("mise en pause" if x.get("pause") else "remise au travail"), flush=True)
    # Le geste qui rend la machine est aussi celui qui libere ce qui l'attendait.
    # Le veilleur le ferait trente secondes plus tard ; ici c'est immediat, et
    # l'administrateur voit la file repartir dans le meme rafraichissement que
    # le bouton qu'il vient de cliquer.
    #
    # « plancher=False » : sans lui, une demande armee depuis moins de quinze
    # secondes etait ecartee et la reponse annoncait « 0 relancee » alors
    # qu'elle repartait au battement suivant. Le clic est deliberatif, pas un
    # va-et-vient de machine — et _relancer_armee desarme avant le premier
    # await, donc un double reveil ne peut de toute facon pas dedoubler l'envoi.
    reveillees = (0 if x.get("pause")
                  else await reveiller_armees(x["id"], plancher=False))
    return web.json_response({"ok": True, "pause": x.get("pause"),
                              "reveillees": reveillees})


async def api_admin_reglages(req):
    """Les reglages qui n'ont pas leur place dans une variable d'environnement.

    Trois : combien de temps une machine en pause fait patienter la demande qui
    la reclame, combien de temps cette demande reste ensuite gardee en attente
    de son retour, et combien d'appels distants un compte peut faire dans le
    mois avant de revenir au local.
    """
    if not admin_ok(req):
        return web.json_response({"erreur": "acces refuse"}, status=403)
    if req.method == "POST":
        try:
            d = await req.json()
        except Exception:
            d = {}
        # Chaque clef est facultative : la carte « pause » de /admin n'envoie
        # que la sienne. Exiger pause_propose, comme le faisait la version d'un
        # seul reglage, aurait refuse en 400 toute requete venue d'un champ
        # ajoute apres elle.
        change = False
        for clef, (bas, haut, dit_) in BORNES_REGLAGES.items():
            if clef not in d:
                continue
            v = d.get(clef)
            # « isinstance(True, int) » vaut vrai : sans ce garde-fou, un JSON
            # portant « true » posait le reglage a une heure.
            if (isinstance(v, bool) or not isinstance(v, (int, float))
                    or not bas <= v <= haut):
                return web.json_response({"erreur": dit_}, status=400)
            PREFERENCES[clef] = int(v)
            change = True
        if not change:
            return web.json_response(
                {"erreur": "aucun reglage connu dans cette demande"}, status=400)
        sauver_reglages()
        if "armee_heures" in d:
            # Le reglage vaut pour les demandes DEJA armees, pas seulement pour
            # les suivantes — et celles que le nouveau delai met hors jeu
            # sortent tout de suite, plutot qu'a la ronde du veilleur.
            reviser_echeances()
            await expirer_armees()
    reponse = dict(PREFERENCES)
    avertit = avertissement_plafond()
    if avertit:
        reponse["avertissement"] = avertit
    return web.json_response(reponse)


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
    global ARRET
    ARRET = True
    for nom in [k for k in a if str(k).startswith("travailleur")] + ["veilleur",
                                                                     "ecoute"]:
        tache = a.get(nom)
        if tache is not None:
            tache.cancel()
    # APRES l'annulation, pour que plus personne n'ajoute de ligne pendant la
    # vidange. Dans un executeur, parce que l'attente est bloquante et qu'on est
    # encore dans la boucle d'evenements : la figer ici retarderait la fermeture
    # des connexions qu'aiohttp est en train de faire.
    reste = await asyncio.get_running_loop().run_in_executor(None, vider_journal)
    if reste:
        # LE DIRE. Une comptabilite amputee qui s'annonce se rattrape ; celle
        # qui se tait donne un studio ou l'on croit compter les appels distants.
        print(f"  journal des couts : {reste} ligne(s) perdue(s) — le disque "
              f"n'a pas suivi en {ATTENTE_JOURNAL:.0f} s", flush=True)

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
    a.router.add_post("/api/admin/noeuds/{ident}/pause", api_admin_pause)
    a.router.add_get("/api/admin/reglages", api_admin_reglages)
    a.router.add_post("/api/admin/reglages", api_admin_reglages)
    a.router.add_delete("/api/admin/noeuds/{ident}", api_admin_supprimer)
    a.router.add_post("/api/comfy/demarrer", api_comfy_demarrer)
    a.router.add_post("/api/comfy/arreter", api_comfy_arreter)
    a.router.add_post("/api/televerser", api_televerser)
    a.router.add_post("/api/generer", api_generer)
    a.router.add_post("/api/au_propre", api_au_propre)
    a.router.add_post("/api/variante", api_variante_choisir)
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
    a.router.add_post("/api/conversation/{cid}/reglages", api_conv_reglages)
    a.router.add_delete("/api/conversation/{cid}", api_supprimer)
    a.router.add_get("/api/fichier", api_fichier)
    a.router.add_get("/api/mediatheque", api_mediatheque)
    a.router.add_post("/api/avis", api_avis)
    a.router.add_get("/api/intentions", api_intentions)
    a.router.add_get("/api/admin/avis", api_admin_avis)
    a.router.add_get("/api/admin/couts", api_admin_couts)
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
    charger_parc()
    charger_reglages()
    charger_comptes()
    charger_cles()
    charger_nuage()
    charger_compteur()
    relever_vram()
    # Le modele d'ecriture est desormais annonce par adresse, juste au-dessus.
    print("  Aiguilleur: "
          + (f"{len(AIGUILLEUR.classes)} intentions apprises"
             if AIGUILLEUR else "absent — tout passe par le modele de langage"))
    print("=" * 64)
    print("  ComfyStudio")
    print(f"  ComfyUI   : {COMFY}")
    # Une ligne par adresse, avec le modele d'ecriture de CHACUNE. La ligne
    # unique annonçait celui de la premiere et laissait croire que c'etait
    # celui du studio — alors que la machine reellement employee est souvent
    # une autre, et qu'elle ne porte pas les memes modeles.
    for i, u in enumerate(OLLAMAS):
        chez_ = cerveau(u).get("noeud")
        ou = f"  [{(noeud(chez_) or {}).get('titre', chez_)}]" if chez_ else ""
        print(f"  {'Ollama    :' if i == 0 else '             '} {u}"
              f"   ecrit avec {modele_ecriture_de(u)}{ou}")
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
    # Au demarrage et pas seulement dans /admin : un plafond pose une fois puis
    # oublie est justement celui qu'on croit etanche des mois durant.
    _avertit = avertissement_plafond()
    if _avertit:
        print(f"  PLAFOND   : {_avertit}")
    print(f"  Conversations : {len(CONVERSATIONS)} chargee(s)")
    print(f"  VRAM      : "
          + (f"{VRAM_GO['total']} Go" if VRAM_GO["total"]
             else "inconnue — aucun ComfyUI joignable au demarrage"))
    print("=" * 64, flush=True)
    web.run_app(app(), host=HOTE, port=PORT, print=None)
