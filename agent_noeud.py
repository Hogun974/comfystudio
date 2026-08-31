#!/usr/bin/env python3
"""Agent ComfyStudio : fait travailler un ComfyUI local pour un studio distant.

C'est l'agent qui appelle le studio, jamais l'inverse. Une machine derriere une
box, sur un portable qui s'endort, ou sur un reseau qu'on ne maitrise pas ne
peut pas etre jointe de l'exterieur ; elle peut toujours sortir. L'agent
s'annonce, reclame du travail, le fait executer par son ComfyUI, puis renvoie
les fichiers produits.

    python agent_noeud.py --studio http://192.0.2.10:8199 --jeton XXXX
    python agent_noeud.py --maj          # se remplace par la derniere version
    python agent_noeud.py --maj --empreinte SHA256   # ... si c'est bien celui-la

Le studio et le jeton sont retenus dans agent_noeud.json, a cote de ce fichier :
les lancements suivants n'ont plus besoin d'arguments. En conteneur, ou il n'y a
pas de fichier, les variables STUDIO_URL, STUDIO_JETON et COMFY_URL font le meme
office.

Aucune dependance : seulement la bibliotheque standard. Une machine qui fait
tourner ComfyUI a forcement un Python.
"""
import argparse
import ast
import base64
import hashlib
import json
import os
import ssl
import threading
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ICI = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(ICI, "agent_noeud.json")
DEPOSEES = "sorties_deposees.json"
# Les champs par lesquels un graphe nomme un fichier d'entree : la meme liste
# que entrees_du_graphe() dans serveur.py. Les deux cotes doivent bouger
# ensemble — un champ que le studio joint mais que l'agent ne corrige pas
# laisse le graphe pointer sur un nom que ComfyUI n'a pas retenu.
CHAMPS_ENTREE = ("image", "file", "audio", "video")
GARDE_DEFAUT = 24           # heures avant d'effacer une sortie deja au studio
PURGE_TOUS_LES = 600        # secondes entre deux passages de menage
PAUSE_COURTE = 3            # entre deux demandes de travail
PAUSE_LONGUE = 20           # apres une erreur : on n'insiste pas
# Ce que executer() rend quand le studio a dit « annule ». Une valeur a part et
# non une erreur ordinaire : elle ne doit ni compter comme une panne de la
# machine, ni la faire ecarter par le repartiteur du studio.
ANNULE = "annulee par le studio"
# Ce que CETTE machine calcule en ce moment. Annonce au studio a chaque
# battement : c'est le seul moyen qu'il ait de savoir, apres un redemarrage,
# qu'un rendu tourne deja ici — sinon il remet la demande en file et la carte
# fait deux fois le meme travail, la seconde fois pour rien.
#
# Une liste, alors que l'agent est strictement sequentiel : elle porte au plus
# un element, et rendre une liste evite au studio d'avoir a supposer cela.
EN_COURS_ICI = []
CONTEXTE = ssl.create_default_context()

# Ce que le fil d'annonce a appris, et dont la boucle de travail a besoin.
#
# Un dictionnaire nu, sans verrou : chaque champ est pose par UNE seule
# ecriture, dans le fil d'annonce, et lu par UNE seule autre, dans la boucle.
# En CPython chacune de ces deux operations est atomique, et une valeur en
# retard d'un battement ne coute qu'un tour d'attente. Ce qui ne serait pas sur
# — lire puis reecrire le meme champ depuis les deux fils — n'existe pas ici :
# la boucle ne fait que lire. Un verrou, lui, serait tenu pendant un appel HTTP
# de soixante secondes et bloquerait justement la boucle qu'on libere.
DEPUIS_L_ANNONCE = {
    # Le dernier etat_comfy() connu, None quand la carte ne repond pas. La
    # boucle s'en sert pour ne pas reclamer un travail qu'elle ne peut pas
    # faire.
    "comfy": None,
    # Vrai quand la derniere annonce a eu 200. Faux sur jeton refuse ou studio
    # muet : inutile d'aller reclamer du travail a un studio qui ne repond pas.
    "studio": False,
    # L'empreinte de l'agent que le studio distribue. POSEE ici, jamais
    # appliquee ici : voir battre_annonce().
    "empreinte_agent": "",
}
# Pose des que le premier battement est retombe, abouti ou non. La boucle
# l'attend avant de reclamer du travail : sans cela elle prendrait un rendu
# avant de savoir si la carte de cette machine repond.
PREMIERE_ANNONCE = threading.Event()

# Dossiers de modeles que le studio veut connaitre. unet_gguf et clip_gguf sont
# des dossiers virtuels du noeud ComfyUI-GGUF : les .gguf n'apparaissent que la.
DOSSIERS = ["checkpoints", "diffusion_models", "loras", "text_encoders", "vae",
            "unet_gguf", "clip_gguf",
            # moteurs ajoutes apres coup : sans ces dossiers, une machine
            # distante ne pouvait jamais servir l'agrandissement, le detourage
            # ni la fluidite video, meme avec les fichiers sur son disque.
            "upscale_models", "background_removal", "frame_interpolation"]


# ══════════════════════════ reglages ══════════════════════════════════
def lire_config():
    try:
        with open(CONFIG, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def ecrire_config(d):
    try:
        with open(CONFIG, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=1)
    except OSError as e:
        print(f"  reglages non enregistres : {e}")


# ══════════════════════════ reseau ════════════════════════════════════
def appeler(url, jeton=None, corps=None, methode=None, brut=None, secondes=60):
    """Un appel HTTP, avec le jeton en en-tete. Rend (statut, objet)."""
    entetes = {}
    if jeton:
        entetes["X-Jeton"] = jeton
    donnees = None
    if brut is not None:
        donnees = brut
        entetes["Content-Type"] = "application/octet-stream"
    elif corps is not None:
        donnees = json.dumps(corps).encode()
        entetes["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=donnees, headers=entetes,
                                 method=methode or ("POST" if donnees else "GET"))
    try:
        with urllib.request.urlopen(req, timeout=secondes, context=CONTEXTE) as r:
            octets = r.read()
            if r.status == 204 or not octets:
                return r.status, None
            try:
                return r.status, json.loads(octets.decode())
            except Exception:
                return r.status, octets
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:300]
    except Exception as e:
        return 0, f"{type(e).__name__}: {str(e)[:160]}"


# ══════════════════════════ ComfyUI local ═════════════════════════════
def etat_comfy(comfy):
    st, d = appeler(f"{comfy}/system_stats", secondes=8)
    if st != 200 or not isinstance(d, dict):
        return None
    dev = next((v for v in d.get("devices", []) if v.get("vram_total")), {})
    # La RAM compte autant que la VRAM : c'est elle qui dit de combien ComfyUI
    # peut deborder quand un modele ne tient pas sur la carte.
    ram = (d.get("system") or {}).get("ram_total") or 0
    return {"carte": dev.get("name"),
            "vram": round(dev.get("vram_total", 0) / 1024 ** 3, 1),
            "libre": round(dev.get("vram_free", 0) / 1024 ** 3, 1),
            "ram": round(ram / 1024 ** 3, 1)}


def modeles_comfy(comfy):
    """Ce que ce ComfyUI sait charger, dossier par dossier."""
    trouve = {}
    for d in DOSSIERS:
        st, liste = appeler(f"{comfy}/models/{d}", secondes=10)
        if st == 200 and isinstance(liste, list):
            trouve[d] = liste
    return trouve


def deposer_entrees(comfy, entrees, graphe):
    """Ecrit dans l'input de CE ComfyUI les fichiers venus avec le travail.

    ComfyUI renomme en « x (1).png » quand le nom existe deja : on corrige donc
    le graphe avec le nom qu'il a REELLEMENT accepte, sinon il chercherait un
    fichier qui n'est pas celui qu'on vient d'ecrire.
    """
    import uuid

    for nom, donnees in (entrees or {}).items():
        octets = base64.b64decode(donnees)
        limite = "----" + uuid.uuid4().hex
        corps = (
            f"--{limite}\r\n"
            f'Content-Disposition: form-data; name="image"; filename="{nom}"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n").encode()
        corps += octets
        corps += (f"\r\n--{limite}\r\n"
                  f'Content-Disposition: form-data; name="type"\r\n\r\ninput\r\n'
                  f"--{limite}\r\n"
                  f'Content-Disposition: form-data; name="overwrite"\r\n\r\ntrue\r\n'
                  f"--{limite}--\r\n").encode()
        req = urllib.request.Request(
            f"{comfy}/upload/image", data=corps,
            headers={"Content-Type": f"multipart/form-data; boundary={limite}"})
        try:
            with urllib.request.urlopen(req, timeout=120, context=CONTEXTE) as r:
                rendu = json.loads(r.read().decode() or "{}")
        except Exception as e:
            return f"fichier d'entree refuse par ComfyUI : {e}"
        vrai = rendu.get("name") or nom
        if vrai != nom:
            for noeud in graphe.values():
                for champ in CHAMPS_ENTREE:
                    if (noeud.get("inputs") or {}).get(champ) == nom:
                        noeud["inputs"][champ] = vrai
    return None


def interrompre(comfy, pid):
    """Coupe notre rendu sur le ComfyUI local. Rend ce qui a ete fait, en clair.

    On regarde /queue avant de tirer : POST /interrupt ne nomme pas le travail
    qu'il coupe, il coupe ce qui tourne. Sur une carte que son proprietaire peut
    aussi faire travailler depuis l'interface de ComfyUI, tirer sans regarder
    reviendrait a lui voler son rendu a lui.

    Un element encore en attente se retire de la file sans reveiller la carte ;
    mesure du 30 aout : la suppression prend moins de dix millisecondes, et
    l'interruption d'un travail deja au GPU rend la carte en moins de 2,1 s
    sans ecrire le moindre fichier.
    """
    st, q = appeler(f"{comfy}/queue", secondes=10)
    if st != 200 or not isinstance(q, dict):
        return "file illisible, rien coupe"

    def _dedans(cle):
        return any(x[1] == pid for x in (q.get(cle) or [])
                   if isinstance(x, (list, tuple)) and len(x) > 1)

    if _dedans("queue_pending"):
        appeler(f"{comfy}/queue", corps={"delete": [pid]}, secondes=10)
        return "retire de la file avant le GPU"
    if _dedans("queue_running"):
        appeler(f"{comfy}/interrupt", corps={}, secondes=10)
        return "carte interrompue"
    return "deja fini, rien a couper"


def executer(comfy, graphe, dire=None):
    """Soumet le graphe et attend la fin. Rend (fichiers, secondes, erreur).

    « dire » recoit la progression a chaque tour de boucle : c'est ce qui rend
    la barre de la file vivante quand le rendu se fait ailleurs que sur la
    machine du studio. Il rend vrai quand le studio annonce que la demande a
    ete annulee ; l'erreur rendue vaut alors ANNULE.
    """
    st, d = appeler(f"{comfy}/prompt", corps={"prompt": graphe, "client_id": "agent"},
                    secondes=120)
    if st != 200 or not isinstance(d, dict) or "prompt_id" not in d:
        return [], 0, f"ComfyUI a refuse le graphe : {str(d)[:200]}"
    pid = d["prompt_id"]
    t0 = time.time()
    while True:
        st, hist = appeler(f"{comfy}/history/{pid}", secondes=30)
        if st == 200 and isinstance(hist, dict) and pid in hist:
            statut = hist[pid].get("status", {})
            if not statut.get("completed"):
                detail = ""
                for m in statut.get("messages", []):
                    if m and m[0] == "execution_error":
                        detail = json.dumps(m[1])[:300]
                return [], time.time() - t0, "echec de la generation " + detail
            sorties = []
            for o in hist[pid].get("outputs", {}).values():
                for valeur in o.values():
                    if isinstance(valeur, list):
                        sorties += [x for x in valeur
                                    if isinstance(x, dict) and "filename" in x]
            return sorties, time.time() - t0, None
        if time.time() - t0 > 3600:
            return [], time.time() - t0, "delai depasse"
        # Appele a chaque tour, meme sans pourcentage a montrer : c'est la
        # REPONSE a cette annonce qui apporte l'annulation, et les premieres
        # dizaines de secondes d'un rendu — le chargement du modele — n'ont
        # aucun pourcentage. Ne l'appeler que sur progression laissait ce
        # trou-la sans aucun moyen d'apprendre qu'on calcule pour rien.
        if dire and dire(PROGRES["fait"], PROGRES["total"]):
            print(f"  annulation recue du studio — {interrompre(comfy, pid)}",
                  flush=True)
            return [], time.time() - t0, ANNULE
        time.sleep(2)


def lire_sortie(comfy, f):
    """Recupere les octets d'un fichier produit, pour les envoyer au studio."""
    q = urllib.parse.urlencode({"filename": f["filename"],
                                "subfolder": f.get("subfolder", ""),
                                "type": f.get("type", "output")})
    st, octets = appeler(f"{comfy}/view?{q}", secondes=300)
    return octets if st == 200 and isinstance(octets, (bytes, bytearray)) else None


# ══════════════════════════ modele de langage ═════════════════════════
# Dans un conteneur, 127.0.0.1 designe le conteneur lui-meme : les services de
# la machine sont a un saut de la, et Docker nomme ce saut. On essaie donc les
# adresses usuelles avant de conclure qu'il n'y a pas de modele — sans quoi un
# agent en conteneur se declare muet a cote d'un Ollama qui tourne.
VOISINS_OLLAMA = ("http://host.docker.internal:11434",
                  "http://172.17.0.1:11434")


def etat_ollama(ollama):
    """Ce que cette machine sait charger cote langage, ou None."""
    st, d = appeler(f"{ollama}/api/tags", secondes=8)
    if st != 200 or not isinstance(d, dict):
        return None
    noms = [m.get("name") for m in (d.get("models") or []) if m.get("name")]
    return {"ok": bool(noms), "modeles": noms[:40]}


def trouver_ollama(prefere):
    """L'adresse ou un modele repond vraiment, ou "" s'il n'y en a aucun.

    Le reglage d'abord — s'il a ete pose, c'est qu'on sait ou l'on va. Les
    voisins de conteneur ensuite, et seulement en dernier recours : les essayer
    d'emblee masquerait une faute de frappe dans le reglage.
    """
    for adresse in (prefere,) + VOISINS_OLLAMA:
        if adresse and etat_ollama(adresse.rstrip("/")):
            return adresse.rstrip("/")
    return ""


def servir_le_langage(studio, jeton, ollama):
    """Vient chercher les questions du studio et rapporte les reponses.

    Un fil a part : la boucle de travail est bloquee pendant un rendu, et une
    question posee au milieu d'une video attendrait sa fin.
    """
    attente = PAUSE_COURTE
    while True:
        try:
            st, q = appeler(f"{studio}/api/noeud/question", jeton, secondes=30)
            if st not in (200, 204):
                # Studio injoignable, ou jeton refuse : ca ne guerit pas en trois
                # secondes. Sans cet espacement, le fil interroge un studio mort
                # mille fois par heure, sans que rien ne le dise jamais.
                time.sleep(attente)
                attente = min(attente * 2, PAUSE_LONGUE)
                continue
            attente = PAUSE_COURTE
            if not isinstance(q, dict) or "qid" not in q:
                time.sleep(PAUSE_COURTE)      # pas de question en attente
                continue
            corps = q.get("corps") or {}
            st2, d = appeler(f"{ollama}/api/generate", corps=corps, secondes=900)
            if st2 == 200 and isinstance(d, dict):
                appeler(f"{studio}/api/noeud/reponse", jeton,
                        {"qid": q["qid"], "reponse": d.get("response", "")},
                        secondes=60)
            else:
                appeler(f"{studio}/api/noeud/reponse", jeton,
                        {"qid": q["qid"],
                         "erreur": f"ollama a repondu {st2}"}, secondes=60)
        except Exception:
            # Ce fil ne doit jamais emporter l'agent : au pire le studio se
            # passe de cette machine pour ses questions.
            time.sleep(PAUSE_LONGUE)


# ══════════════════════════ progression ═══════════════════════════════
# Rempli par le fil d'ecoute, lu par la boucle. Un dictionnaire suffit : une
# seule ecriture, une seule lecture, et une valeur perimee ne coute qu'un
# pourcentage legerement en retard.
PROGRES = {"fait": 0, "total": 0}


def _trame(sock):
    """Lit une trame websocket du serveur. Rend (opcode, donnees) ou None."""
    def lire(k):
        bout = b""
        while len(bout) < k:
            m = sock.recv(k - len(bout))
            if not m:
                return None
            bout += m
        return bout

    tete = lire(2)
    if not tete:
        return None
    opcode = tete[0] & 0x0F
    taille = tete[1] & 0x7F
    masque = tete[1] & 0x80
    if taille == 126:
        t = lire(2)
        taille = int.from_bytes(t, "big") if t else 0
    elif taille == 127:
        t = lire(8)
        taille = int.from_bytes(t, "big") if t else 0
    cle = lire(4) if masque else b""
    corps = lire(taille) if taille else b""
    if corps is None:
        return None
    if masque and cle:
        corps = bytes(o ^ cle[i % 4] for i, o in enumerate(corps))
    return opcode, corps


def ecouter_progression(comfy):
    """Relaie la progression annoncee par ComfyUI. Se rattrape toute seule.

    Ecrit a la main parce que l'agent doit rester un fichier unique, sans
    dependance a installer sur une machine qu'on ne maitrise pas.
    """
    import base64
    import socket
    from urllib.parse import urlparse

    u = urlparse(comfy)
    if u.scheme not in ("http", "https"):
        return
    attente = 2
    while True:
        sock = None
        try:
            port = u.port or (443 if u.scheme == "https" else 80)
            sock = socket.create_connection((u.hostname, port), timeout=10)
            if u.scheme == "https":
                sock = ssl.create_default_context().wrap_socket(
                    sock, server_hostname=u.hostname)
            cle = base64.b64encode(os.urandom(16)).decode()
            sock.sendall((
                f"GET /ws?clientId=agent HTTP/1.1\r\n"
                f"Host: {u.hostname}:{port}\r\n"
                f"Upgrade: websocket\r\nConnection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {cle}\r\nSec-WebSocket-Version: 13\r\n\r\n"
            ).encode())
            entete = b""
            while b"\r\n\r\n" not in entete:
                m = sock.recv(1024)
                if not m:
                    raise OSError("connexion fermee pendant la poignee de main")
                entete += m
            if b"101" not in entete.split(b"\r\n", 1)[0]:
                raise OSError("websocket refusee par ComfyUI")
            sock.settimeout(120)
            attente = 2
            while True:
                t = _trame(sock)
                if t is None:
                    break
                opcode, corps = t
                if opcode == 0x9:      # ping : la reponse doit etre masquee
                    cle4 = os.urandom(4)
                    charge = bytes(o ^ cle4[i % 4] for i, o in enumerate(corps))
                    sock.sendall(bytes([0x8A, 0x80 | len(charge)]) + cle4 + charge)
                    continue
                if opcode == 0x8:      # fermeture
                    break
                if opcode != 0x1:      # on ne lit que le texte
                    continue
                try:
                    d = json.loads(corps.decode("utf-8", "replace"))
                except ValueError:
                    continue
                genre, data = d.get("type"), d.get("data") or {}
                if genre == "progress":
                    PROGRES.update(fait=int(data.get("value") or 0),
                                   total=int(data.get("max") or 0))
                elif genre in ("execution_success", "execution_error",
                               "execution_interrupted"):
                    PROGRES.update(fait=0, total=0)
        except Exception:
            PROGRES.update(fait=0, total=0)
        finally:
            try:
                if sock:
                    sock.close()
            except OSError:
                pass
        time.sleep(attente)
        attente = min(attente * 2, 30)


# ══════════════════════════ menage ════════════════════════════════════
def _registre_chemin(sorties):
    """Ou vit le registre des depots.

    DANS le dossier des sorties quand on le connait : c'est le seul endroit
    persistant dont un agent en conteneur soit sur — son script, ses reglages et
    son /tmp repartent a zero a chaque demarrage. Ecrit a cote du script, le
    registre serait perdu a chaque redemarrage, et le menage n'effacerait jamais
    rien sans que personne ne s'en apercoive.
    """
    chemin = os.path.join(sorties or ICI,
                          "." + DEPOSEES if sorties else DEPOSEES)
    _reprendre_ancien_registre(chemin)
    return chemin


# Une seule fois par execution : le registre ne redemenage pas en cours de
# route, et retester a chaque depot coute un acces disque pour rien.
_ancien_registre_repris = False


def _reprendre_ancien_registre(neuf):
    """Ramene le registre qui vivait a cote du script vers son nouvel endroit.

    Sans cette reprise, les depots notes avant le demenagement ne seraient
    jamais effaces : le menage ne regarde que le registre courant, et l'ancien
    resterait la a decrire des fichiers que plus personne ne surveille.

    On fusionne au lieu de deplacer, parce que le nouveau registre existe deja
    des que l'agent a tourne une fois depuis le demenagement — un simple
    deplacement ecraserait alors les depots recents, et refuser de reprendre
    abandonnerait les anciens. Les entrees portent un chemin absolu : elles
    restent justes quel que soit le fichier qui les heberge.
    """
    global _ancien_registre_repris
    if _ancien_registre_repris:
        return
    _ancien_registre_repris = True
    ancien = os.path.join(ICI, DEPOSEES)
    if os.path.abspath(ancien) == os.path.abspath(neuf):
        return                      # sans dossier de sorties, c'est le meme
    if not os.path.exists(ancien):
        return
    try:
        with open(ancien, encoding="utf-8") as f:
            vieilles = json.load(f)
    except Exception as e:
        # Illisible : on n'efface pas ce qu'on n'a pas su lire, le proprietaire
        # de la machine pourra toujours y jeter un oeil.
        print(f"  ancien registre illisible ({e}) — laisse en place", flush=True)
        return
    fusion = {}
    for e in (vieilles if isinstance(vieilles, list) else []) + _lire_registre(neuf):
        if not isinstance(e, dict) or not e.get("chemin"):
            continue
        # Deux notes pour un meme fichier : la plus recente gagne, sinon la
        # plus ancienne ferait effacer avant l'heure un fichier redepose entre
        # temps.
        vue = fusion.get(e["chemin"])
        if vue is None or e.get("quand", 0) >= vue.get("quand", 0):
            fusion[e["chemin"]] = e
    try:
        with open(neuf, "w", encoding="utf-8") as g:
            json.dump(list(fusion.values())[-5000:], g, ensure_ascii=False)
    except OSError as e:
        print(f"  reprise de l'ancien registre impossible : {e}", flush=True)
        return
    try:
        os.remove(ancien)
    except OSError as e:
        # Repris quand meme : le nouveau registre existe, l'ancien ne sera plus
        # relu. On le signale pour qu'il ne traine pas sans raison.
        print(f"  ancien registre a effacer a la main : {ancien} ({e})", flush=True)
    print(f"  registre des depots repris ({len(fusion)} entree(s))", flush=True)


def _lire_registre(chemin):
    try:
        with open(chemin, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, list) else []
    except Exception:
        return []


def _registre(sorties=""):
    return _lire_registre(_registre_chemin(sorties))


def noter_depot(sorties, f, quand):
    """Retient qu'on a envoye ce fichier au studio, et quand.

    Le registre est la garantie qu'on n'effacera pas le travail personnel du
    proprietaire de la machine : on ne supprime que ce qui y figure.
    """
    if not sorties:
        return
    chemin = os.path.join(sorties, f.get("subfolder", ""), f["filename"])
    d = _registre(sorties)
    d.append({"chemin": chemin, "quand": quand})
    try:
        with open(_registre_chemin(sorties), "w", encoding="utf-8") as g:
            json.dump(d[-5000:], g, ensure_ascii=False)
    except OSError as e:
        print(f"  registre des depots non ecrit : {e}", flush=True)


def faire_le_menage(garde_h, sorties=""):
    """Efface les sorties deja au studio et assez vieilles. Rend le compte."""
    limite = time.time() - garde_h * 3600
    d = _registre(sorties)
    if not d:
        return 0
    restant, efface = [], 0
    for e in d:
        if e.get("quand", 0) > limite:
            restant.append(e)
            continue
        try:
            os.remove(e["chemin"])
            efface += 1
        except FileNotFoundError:
            # Deja parti — a la main, ou par un menage precedent. On oublie
            # l'entree : la garder ferait retenter la suppression sans fin.
            efface += 0
        except OSError as err:
            # Un fichier qu'on n'arrive pas a effacer reste au registre : on
            # reessaiera, plutot que de le perdre de vue en le rayant.
            print(f"  suppression impossible ({err}) — on garde la trace",
                  flush=True)
            restant.append(e)
    try:
        with open(_registre_chemin(sorties), "w", encoding="utf-8") as g:
            json.dump(restant, g, ensure_ascii=False)
    except OSError:
        pass
    return efface


# ══════════════════════════ mise a jour ═══════════════════════════════
try:
    with open(os.path.abspath(__file__), "rb") as _f:
        _EMPREINTE_AU_DEMARRAGE = hashlib.sha256(_f.read()).hexdigest()
except OSError:
    _EMPREINTE_AU_DEMARRAGE = ""


def _mon_empreinte():
    """Le sha256 du code REELLEMENT en cours d'execution.

    Lu une seule fois, au chargement, et retenu. C'est le contraire de ce qu'on
    ferait par reflexe : « --maj » remplace le fichier sous nos pieds, mais le
    processus qui tourne continue d'executer l'ancien code jusqu'a son
    redemarrage. Relire le disque annoncerait donc une version a jour pendant
    qu'une version perimee travaille — exactement le mensonge que cette
    empreinte existe pour empecher.
    """
    return _EMPREINTE_AU_DEMARRAGE


def se_mettre_a_jour(studio, empreinte=""):
    """Recupere la derniere version du script depuis le studio.

    Le studio sert l'agent : mettre a jour une machine revient a relancer ce
    script avec --maj, sans depot a cloner ni fichier a recopier a la main.

    C'est aussi du code telecharge puis execute. En HTTP simple, celui qui
    s'intercale sur le reseau decide de ce code : --empreinte impose le sha256
    attendu, et n'a de valeur que releve AILLEURS que sur ce meme lien — par
    « sha256sum agent_noeud.py » sur l'hote du studio, en SSH. L'empreinte
    installee est affichee dans tous les cas, pour pouvoir la comparer d'une
    machine a l'autre.
    """
    st, octets = appeler(f"{studio}/api/noeud/agent", secondes=60)
    if st != 200 or not isinstance(octets, (bytes, bytearray)):
        print(f"  mise a jour impossible : {st} {str(octets)[:120]}")
        return 1
    recue = hashlib.sha256(octets).hexdigest()
    attendue = (empreinte or "").strip().lower()
    if attendue and attendue != recue:
        print("  EMPREINTE INATTENDUE — rien n'a ete remplace")
        print(f"    recue    : {recue}")
        print(f"    attendue : {attendue}")
        return 1
    # Le fichier n'etait pas relu avant d'ecraser un agent qui fonctionnait :
    # les scripts shell le faisaient, pas celui-ci. Anodin tant qu'un humain
    # lançait « --maj » et voyait l'erreur au redemarrage ; inacceptable depuis
    # que la mise a jour est automatique, ou un telechargement tronque ferait
    # une brique sans personne pour le voir.
    try:
        ast.parse(octets.decode("utf-8"))
    except (UnicodeDecodeError, SyntaxError) as e:
        print(f"  ce que le studio a renvoye n'est pas un agent valide ({e}) "
              f"— rien n'a ete remplace")
        return 1
    moi = os.path.abspath(__file__)
    if octets == open(moi, "rb").read():
        print("  deja a jour.")
        return 0
    # copie de secours : si la nouvelle version est cassee, il reste la
    # precedente a cote, sans avoir a la retelecharger.
    try:
        with open(moi + ".precedent", "wb") as f:
            f.write(open(moi, "rb").read())
        with open(moi, "wb") as f:
            f.write(octets)
    except OSError as e:
        print(f"  ecriture impossible : {e}")
        return 1
    print(f"  mis a jour ({len(octets)} octets, sha256 {recue}). L'ancienne "
          f"version est dans {os.path.basename(moi)}.precedent")
    return 0


# Marqueur transmis a la version suivante par l'environnement : il survit a
# os.execv, qui remplace le processus sans rien perdre de son environnement.
# C'est ce qui distingue « je viens d'essayer et ça n'a pas pris » de « je
# decouvre qu'une version existe ».
MARQUE_MAJ = "AGENT_MAJ_TENTEE"


def se_mettre_a_jour_seul(studio, attendue, epinglee):
    """Se remplacer par la version du studio, puis redemarrer. Ne rend jamais.

    Rend None quand il n'y a rien a faire — c'est le cas courant, appele a
    chaque battement.
    """
    if not attendue or attendue == _EMPREINTE_AU_DEMARRAGE:
        return None
    if epinglee:
        print(f"  le studio sert un agent different (sha256 {attendue[:12]}…), "
              f"mais une empreinte est epinglee : rien ne sera remplace",
              flush=True)
        return None
    if os.environ.get(MARQUE_MAJ) == attendue:
        # Deja essaye pour CETTE empreinte, et nous voila encore differents.
        # Insister ferait redemarrer la machine en boucle.
        print(f"  mise a jour deja tentee pour {attendue[:12]}… et l'empreinte "
              f"ne correspond toujours pas — on s'arrete d'essayer",
              flush=True)
        return None
    print(f"  le studio sert un agent plus recent (sha256 {attendue[:12]}…) "
          f"— mise a jour", flush=True)
    if se_mettre_a_jour(studio, attendue) != 0:
        return None
    print("  redemarrage sur la nouvelle version", flush=True)
    os.environ[MARQUE_MAJ] = attendue
    try:
        os.execv(sys.executable, [sys.executable, os.path.abspath(__file__)]
                 + sys.argv[1:])
    except OSError as e:
        # execv a echoue : le processus est intact, sur l'ANCIEN code, avec le
        # nouveau fichier sur le disque. Le dire, et continuer de travailler —
        # le prochain demarrage prendra la nouvelle version.
        print(f"  redemarrage impossible ({e}) — la nouvelle version prendra "
              f"effet au prochain lancement", flush=True)
    return None


# Combien de temps insister pour livrer un travail deja fait. Dix minutes
# couvrent largement le redemarrage d'un studio, qui prend une dizaine de
# secondes ; au-dela, c'est que le studio n'est pas la, et le travail est perdu
# de toute façon.
LIVRAISON_MINUTES = int(os.environ.get("AGENT_LIVRAISON_MINUTES") or 10)


def insister(url, jeton, corps=None, brut=None, secondes=60):
    """Livre au studio, et recommence tant qu'il ne repond pas.

    Un travail DEJA FAIT ne doit pas etre perdu parce que le studio redemarrait
    a la seconde ou l'on rendait. C'etait le cas : un seul appel, et si le
    studio ne repondait pas, la carte avait tourne pour rien et l'utilisateur
    lisait « echec » pour un travail que sa machine avait bel et bien mene a
    terme.

    On ne recommence que sur un studio MUET ou en panne (0, ou 5xx). Un refus
    franc — jeton invalide, extension refusee, fichier trop gros — ne se repare
    pas en le repetant : on rend la main tout de suite.
    """
    fin = time.time() + LIVRAISON_MINUTES * 60
    attente, dit = 2, False
    while True:
        st, _ = appeler(url, jeton, corps, brut=brut, secondes=secondes)
        if st == 200 or (400 <= st < 500):
            if dit:
                print(f"  studio revenu — {url.split('/')[-1].split('?')[0]} "
                      f"livre ({st})", flush=True)
            return st
        if time.time() >= fin:
            print(f"  studio injoignable depuis {LIVRAISON_MINUTES} min — "
                  f"travail perdu ({st})", flush=True)
            return st
        if not dit:
            print(f"  studio muet ({st}) — on garde le travail et l'on insiste",
                  flush=True)
            dit = True
        time.sleep(attente)
        attente = min(attente * 2, 30)


# ══════════════════════════ annonce ════════════════════════════
# Secondes entre deux annonces quand le studio n'en dit rien. Chez lui
# SILENCE_MAX vaut 45 s : trois battements peuvent se perdre avant qu'il ne
# declare la machine morte.
ANNONCE_DEFAUT = 10
# Le studio fixe la cadence par « intervalle », mais on ne le suit que pour
# RALENTIR, jamais pour accelerer : un agent plus bavard que dix secondes
# n'apporte rien et multiplie les ecritures de sauver_parc() cote studio. Et
# jamais au-dela de 30 s — a 45 s, un seul battement perdu suffirait a franchir
# SILENCE_MAX et a faire disparaitre une machine qui obeit.
ANNONCE_MAX = 30
# Pendant un rendu, on ne redemande pas /system_stats a chaque battement. Ni la
# carte ni la VRAM totale ne changent pendant qu'elle calcule, et cette route
# traverse la boucle asyncio de ComfyUI — celle qui sert aussi la websocket de
# progression. Avant ce fil, l'agent ne l'interrogeait pas du tout pendant un
# rendu : six fois par minute serait une regression pour une information qu'on
# a deja. Une fois par minute borne a soixante secondes le retard sur une carte
# qui tomberait en cours de route.
ETAT_PENDANT_TRAVAIL = 60


def battre_annonce(studio, jeton, comfy, ollama):
    """S'annonce au studio sans jamais s'interrompre, quoi que fasse la boucle.

    L'annonce est ce qui rend la machine VISIBLE, et la boucle de travail, elle,
    se bloque : de trente secondes a plusieurs minutes pour un rendu, jusqu'a
    cent soixante secondes pour une reponse du modele de langage, deux minutes
    pour deposer une entree volumineuse. Passe les quarante-cinq secondes de
    SILENCE_MAX, le studio retire la machine de noeuds_pour() et repond
    « aucune machine ne repond » pendant qu'une carte tourne. Les deux rustines
    en place — le battement de /api/noeud/progres et patienter_machine() — ne
    couvrent que le rendu ; la question posee au modele de langage laissait la
    machine muette pendant tout le temps de la reponse.

    Ce fil ne fait QUE s'annoncer. Il n'applique pas la mise a jour, alors que
    c'est lui qui apprend l'empreinte servie par le studio : se_mettre_a_jour_seul()
    finit par un os.execv, qui remplace le processus d'un bloc, sans deroulement
    ni fils survivants. Declenche depuis ici, il couperait un rendu en cours
    sans rien rendre au studio — une image perdue chez l'utilisateur, pour une
    mise a jour qui pouvait attendre dix minutes. L'empreinte est donc reposee
    dans DEPUIS_L_ANNONCE, et la boucle s'en saisit entre deux travaux.
    """
    intervalle = ANNONCE_DEFAUT
    modeles_envoyes = 0.0
    etat_mesure = 0.0
    etat = None
    # Vrai au premier tour : le studio ne sait rien de cette machine tant qu'on
    # ne lui a rien dit, et attendre cinq minutes la rendrait inutilisable
    # d'autant.
    reclame_modeles = True
    connu = False
    while True:
        debut = time.time()
        attente = intervalle
        try:
            if not EN_COURS_ICI or debut - etat_mesure > ETAT_PENDANT_TRAVAIL:
                etat = etat_comfy(comfy)
                etat_mesure = debut
            DEPUIS_L_ANNONCE["comfy"] = etat
            if not etat:
                if connu:
                    print("  ComfyUI ne repond plus — on attend", flush=True)
                    connu = False
                # On s'annonce quand meme, avec ce qu'on a : cette machine
                # porte peut-etre un modele de langage, et c'est justement
                # celle dont le studio a besoin quand le sien tombe. Se taire
                # la rendait invisible pour ça aussi.
                if ollama:
                    st, _ = appeler(f"{studio}/api/noeud/annonce", jeton,
                                    {"comfy": False,
                                     "llm": etat_ollama(ollama) or {"ok": False,
                                                                    "modeles": []}})
                    DEPUIS_L_ANNONCE["studio"] = st == 200
                attente = PAUSE_LONGUE
                continue
            corps = dict(etat)
            # Notre propre empreinte, a chaque annonce. Le studio la compare a
            # celle de l'agent qu'il sert : c'est le seul moyen qu'il ait de
            # savoir qu'une machine porte une version perimee. Constate le
            # 31 aout : l'annulation d'un rendu ne fonctionnait pas sur une
            # machine, parce que son agent datait d'avant le protocole
            # d'annulation. Rien ne le disait — elle repondait, elle rendait
            # des images, et une fonction entiere manquait en silence.
            corps["empreinte"] = _mon_empreinte()
            # Copiee au plus tard, juste avant l'envoi. La boucle pose et
            # retire cette liste sans nous prevenir ; une copie prise plus haut
            # annoncerait libre une machine qui vient de recevoir un travail.
            # list() d'une liste est une operation unique, donc sure meme si la
            # boucle ecrit au meme instant : au pire on lit l'etat d'avant.
            corps["travaux"] = list(EN_COURS_ICI)
            # Reevalue a chaque annonce : un modele peut etre telecharge ou
            # retire pendant que l'agent tourne.
            if ollama:
                corps["llm"] = etat_ollama(ollama) or {"ok": False,
                                                       "modeles": []}
            # la liste des modeles change rarement : toutes les cinq minutes
            # Le studio peut reclamer l'inventaire : il vient de redemarrer
            # et ne connait plus rien de cette machine. Repondre tout de
            # suite evite cinq minutes pendant lesquelles il la croit vide.
            #
            # Il part desormais AUSSI pendant un rendu, ce qui n'arrivait
            # jamais avant ce fil. C'est voulu : cote studio manquants() jette
            # l'inventaire au-dela de 3 x FRAICHEUR_MODELES, soit 180 s, et une
            # machine qui rendait pendant une heure ressortait de noeuds_pour()
            # ET de patienter_machine() — le studio refusait la demande suivante
            # en bloc. Le studio ne le reclame qu'une fois par minute, et ce
            # sont dix listages de dossier que ComfyUI sert de son cache.
            if debut - modeles_envoyes > 300 or reclame_modeles:
                corps["modeles"] = modeles_comfy(comfy)
                modeles_envoyes = debut
            st, d = appeler(f"{studio}/api/noeud/annonce", jeton, corps)
            DEPUIS_L_ANNONCE["studio"] = st == 200
            if st == 401:
                print("  jeton refuse par le studio — verifie l'administration",
                      flush=True)
                attente = 30
                continue
            if st != 200:
                if connu:
                    print(f"  studio injoignable ({st}) — on reessaie",
                          flush=True)
                    connu = False
                attente = PAUSE_LONGUE
                continue
            d = d if isinstance(d, dict) else {}
            # Le studio dit s'il connait nos modeles. Il ne les connait
            # plus apres chacun de ses redemarrages.
            reclame_modeles = bool(d.get("modeles_demandes"))
            try:
                intervalle = min(max(int(d.get("intervalle") or ANNONCE_DEFAUT),
                                     ANNONCE_DEFAUT), ANNONCE_MAX)
            except (TypeError, ValueError):
                intervalle = ANNONCE_DEFAUT
            attente = intervalle
            DEPUIS_L_ANNONCE["empreinte_agent"] = d.get("empreinte_agent") or ""
            if not connu:
                nom = d.get("titre") or "?"
                print(f"  connecte au studio en tant que « {nom} » "
                      f"— {etat['carte']}, {etat['vram']} Go", flush=True)
                connu = True
        except Exception as e:
            # Ce fil ne doit jamais emporter l'agent, ni s'arreter : s'il meurt,
            # la machine devient invisible en quarante-cinq secondes et plus
            # rien ne le dit. On le note et l'on rebat.
            print(f"  incident dans l'annonce : {type(e).__name__} "
                  f"{str(e)[:160]}", flush=True)
            attente = PAUSE_LONGUE
        finally:
            PREMIERE_ANNONCE.set()
            # Le temps de l'appel est DEDANS l'intervalle, pas en plus : une
            # annonce qui met huit secondes ne doit pas repousser la suivante a
            # dix-huit. Une seconde de plancher pour qu'un studio qui refuse
            # instantanement ne fasse pas tourner ce fil a vide.
            time.sleep(max(1.0, attente - (time.time() - debut)))


# ══════════════════════════ boucle ════════════════════════════════════
def boucle(studio, jeton, comfy, sorties="", garder=GARDE_DEFAUT, ollama="",
           epinglee="", maj_auto=True):
    print(f"  studio  : {studio}", flush=True)
    print(f"  ComfyUI : {comfy}", flush=True)
    print("  en service — ctrl+C pour arreter\n", flush=True)
    dernier_menage = 0.0
    # Trois fils de fond, tous daemon : ils ne detiennent rien qu'il faille
    # rendre, et le processus se termine sans les attendre.
    #
    # La progression : elle ne doit jamais retarder la demande de travail, et
    # son echec ne coute qu'un pourcentage.
    threading.Thread(target=ecouter_progression, args=(comfy,), daemon=True).start()
    # L'annonce : voir battre_annonce(). C'est elle qui rend la machine
    # visible, et la boucle ci-dessous se bloque des qu'elle travaille.
    threading.Thread(target=battre_annonce, args=(studio, jeton, comfy, ollama),
                     daemon=True).start()
    if ollama:
        threading.Thread(target=servir_le_langage, args=(studio, jeton, ollama),
                         daemon=True).start()
    # Le premier battement dit si la carte repond et si le studio nous accepte.
    # Reclamer du travail avant de le savoir, c'est prendre un rendu qu'on ne
    # peut pas faire. Soixante secondes de plafond : au-dela, le battement est
    # en peine et la boucle se debrouillera avec ce qu'elle a.
    PREMIERE_ANNONCE.wait(60)
    while True:
        try:
            maintenant = time.time()
            # Le menage passe entre deux travaux, pas pendant : effacer sous les
            # pieds d'un rendu en cours n'apporterait rien de bon.
            if sorties and maintenant - dernier_menage > PURGE_TOUS_LES:
                dernier_menage = maintenant
                partis = faire_le_menage(garder, sorties)
                if partis:
                    print(f"  {partis} sortie(s) effacee(s) ici — le studio les a",
                          flush=True)
            # 1. l'annonce bat dans son propre fil ; ici on ne fait que
            # relever ce qu'elle en a rapporte.
            #
            # ICI et nulle part ailleurs : le travail precedent est rendu, le
            # suivant pas encore reclame. C'est le seul instant ou se remplacer
            # ne trahit personne, et c'est pourquoi le fil d'annonce se contente
            # de poser l'empreinte au lieu de l'appliquer — son os.execv, tire
            # pendant un rendu, emporterait l'image avec le processus.
            if maj_auto:
                se_mettre_a_jour_seul(studio,
                                      DEPUIS_L_ANNONCE["empreinte_agent"],
                                      epinglee)
            # Pas de carte, ou pas de studio : on ne reclame rien. Prendre un
            # travail qu'on ne peut pas faire le ferait echouer chez
            # l'utilisateur alors qu'une autre machine l'aurait pris. Le fil
            # d'annonce, lui, continue de battre — la machine reste visible, et
            # le studio sait qu'elle est la sans sa carte.
            if DEPUIS_L_ANNONCE["comfy"] is None or not DEPUIS_L_ANNONCE["studio"]:
                time.sleep(PAUSE_LONGUE)
                continue

            # 2. reclamer du travail
            st, travail = appeler(f"{studio}/api/noeud/travail", jeton, secondes=30)
            if st == 204 or not travail:
                time.sleep(PAUSE_COURTE)
                continue
            if st != 200 or "graphe" not in travail:
                time.sleep(PAUSE_LONGUE)
                continue

            tid = travail["tid"]
            EN_COURS_ICI[:] = [tid]
            print(f"  travail {tid[:8]} recu", flush=True)
            erreur = deposer_entrees(comfy, travail.get("entrees"),
                                     travail["graphe"])
            if erreur:
                fichiers, secondes = [], 0
            else:
                dernier = [0.0]

                def dire(fait, total):
                    # Une annonce toutes les deux secondes au plus : le studio
                    # n'a pas besoin de plus, et une machine lente ne doit pas
                    # passer son temps a poster des pourcentages.
                    # 1,5 s et non 2 : la boucle d'executer() tourne
                    # toutes les deux secondes, et un frein regle sur la meme
                    # duree laissait passer un tour sur deux. L'annonce ne porte
                    # plus seulement un pourcentage, elle rapporte l'annulation :
                    # un tour saute, ce sont deux secondes de GPU de plus.
                    if time.time() - dernier[0] < 1.5:
                        return False
                    dernier[0] = time.time()
                    st_, rep = appeler(f"{studio}/api/noeud/progres", jeton,
                                       {"tid": tid, "fait": fait, "total": total},
                                       secondes=10)
                    # Le retour de cette annonce est le seul chemin par lequel
                    # une annulation nous parvienne : le studio n'a pas notre
                    # adresse. Un studio muet ou en erreur ne vaut donc jamais
                    # « annule » — on ne jette pas un rendu sur un doute.
                    return (st_ == 200 and isinstance(rep, dict)
                            and bool(rep.get("annule")))

                fichiers, secondes, erreur = executer(comfy, travail["graphe"], dire)

            # Une demande annulee ne rend rien : ni fichier a televerser, ni
            # erreur a imputer a la machine — l'imputer la ferait ecarter du
            # repartiteur pour un incident qui n'est pas le sien. On le dit au
            # studio, qui ecrira la derniere ligne de son journal (la seule qui
            # parle de l'arret au passe), et on repart chercher du travail.
            if erreur == ANNULE:
                appeler(f"{studio}/api/noeud/resultat", jeton,
                        {"tid": tid, "etat": "annule", "erreur": None,
                         "secondes": round(secondes, 1), "fichiers": []})
                print(f"  travail {tid[:8]} annule par le studio apres "
                      f"{secondes:.0f} s", flush=True)
                EN_COURS_ICI.clear()
                continue

            # 3. deposer les fichiers produits, puis rendre le resultat
            deposes = []
            for f in fichiers:
                octets = lire_sortie(comfy, f)
                if octets is None:
                    erreur = erreur or f"fichier illisible : {f['filename']}"
                    continue
                q = urllib.parse.urlencode({"tid": tid, "nom": f["filename"]})
                st = insister(f"{studio}/api/noeud/fichier?{q}", jeton,
                              brut=octets, secondes=600)
                if st == 200:
                    deposes.append({"filename": f["filename"],
                                    "subfolder": f.get("subfolder", ""),
                                    "type": f.get("type", "output")})
                    # Le studio en a une copie : la notre peut vieillir et
                    # disparaitre. On ne note QUE ce qui est bien arrive.
                    noter_depot(sorties, f, time.time())
                else:
                    erreur = erreur or f"envoi refuse par le studio ({st})"
            insister(f"{studio}/api/noeud/resultat", jeton,
                     {"tid": tid, "etat": "erreur" if erreur else "fini",
                      "erreur": erreur, "secondes": round(secondes, 1),
                      "fichiers": deposes})
            print(f"  travail {tid[:8]} {'echoue' if erreur else 'rendu'} "
                  f"en {secondes:.0f} s — {len(deposes)} fichier(s)", flush=True)
            EN_COURS_ICI.clear()
        except KeyboardInterrupt:
            raise
        except Exception as e:
            # Vider ici aussi : une liste qui ne se vide pas ferait croire au
            # studio qu'un rendu tourne encore, et il attendrait un resultat qui
            # ne viendra jamais.
            EN_COURS_ICI.clear()
            print(f"  incident : {type(e).__name__} {str(e)[:160]}", flush=True)
            time.sleep(PAUSE_LONGUE)


def main():
    cfg = lire_config()
    # L'environnement avant le fichier de reglages : en conteneur, il n'y a pas
    # de fichier, et transmettre des arguments par un compose est fragile — un
    # « $VAR » y est resolu au mauvais moment et arrive vide.
    cfg = {"studio": os.environ.get("STUDIO_URL") or cfg.get("studio", ""),
           "jeton": os.environ.get("STUDIO_JETON") or cfg.get("jeton", ""),
           "comfy": os.environ.get("COMFY_URL") or cfg.get("comfy",
                                                          "http://127.0.0.1:8188"),
           "sorties": os.environ.get("COMFY_SORTIES") or cfg.get("sorties", ""),
           # En conteneur il n'y a pas de fichier de reglages qui survive : tout
           # doit pouvoir se dire par l'environnement, sinon le delai n'est pas
           # reglable du tout la ou il sert le plus.
           "garder_heures": float(os.environ.get("COMFY_GARDER_HEURES")
                                  or cfg.get("garder_heures", GARDE_DEFAUT)),
           "ollama": os.environ.get("OLLAMA_URL")
                     or cfg.get("ollama", "http://127.0.0.1:11434"),
           }
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--studio", default=cfg.get("studio", ""),
                   help="adresse du studio, par exemple http://192.0.2.10:8199")
    a.add_argument("--jeton", default=cfg.get("jeton", ""),
                   help="jeton delivre par l'administration du studio")
    a.add_argument("--comfy", default=cfg.get("comfy"),
                   help="adresse du ComfyUI local")
    a.add_argument("--ollama", default=cfg.get("ollama", "http://127.0.0.1:11434"),
                   help="adresse du modele de langage local, prete au studio "
                        "quand le sien ne repond plus")
    a.add_argument("--sorties", default=cfg.get("sorties", ""),
                   help="dossier output de ComfyUI, pour effacer ce qui est deja "
                        "au studio (sans lui, aucun menage)")
    a.add_argument("--garder-heures", type=float, dest="garder",
                   default=cfg.get("garder_heures", GARDE_DEFAUT),
                   help=f"heures avant d'effacer une sortie deja deposee "
                        f"(defaut {GARDE_DEFAUT})")
    a.add_argument("--maj", action="store_true",
                   help="se remplacer par la derniere version servie par le studio")
    a.add_argument("--sans-maj-auto", action="store_true",
                   default=bool(os.environ.get("AGENT_SANS_MAJ_AUTO")),
                   help="ne pas se mettre a jour tout seul quand le studio sert "
                        "une version plus recente")
    a.add_argument("--empreinte", default=os.environ.get("AGENT_EMPREINTE", ""),
                   help="sha256 attendu de l'agent telecharge par --maj ; "
                        "a relever sur l'hote du studio, pas sur ce lien HTTP")
    args = a.parse_args()

    studio = args.studio.rstrip("/")
    if not studio:
        print("  Il manque l'adresse du studio : --studio http://...:8199")
        return 1
    if args.maj:
        return se_mettre_a_jour(studio, args.empreinte)
    if not args.jeton:
        print("  Il manque le jeton : --jeton XXXX (cree dans /admin du studio)")
        return 1

    sorties = os.path.abspath(args.sorties) if args.sorties else ""
    if sorties and not os.path.isdir(sorties):
        # Refuser tout de suite : un chemin faux ferait croire au menage sans
        # que rien ne soit jamais efface.
        print(f"  dossier de sorties introuvable : {sorties}")
        return 1
    ecrire_config({"studio": studio, "jeton": args.jeton, "comfy": args.comfy,
                   "sorties": sorties, "garder_heures": args.garder,
                   "ollama": args.ollama})
    print("=" * 60)
    print("  Agent ComfyStudio")
    print("=" * 60)
    if sorties:
        print(f"  Sorties   : {sorties} — effacees {args.garder:.0f} h apres depot")
    else:
        # Le dire une fois, au demarrage : un disque qui se remplit en silence
        # est plus penible qu'un dossier suppose, mais effacer au hasard le
        # serait bien davantage.
        print("  Sorties   : dossier inconnu — rien ne sera efface ici "
              "(--sorties CHEMIN pour l'activer)")
    ollama = trouver_ollama(args.ollama)
    if ollama:
        lang = etat_ollama(ollama) or {"modeles": []}
        print(f"  Langage   : {ollama} — {len(lang['modeles'])} modele(s), "
              f"pretes au studio si le sien tombe")
    else:
        print(f"  Langage   : aucun modele joignable (essaye {args.ollama} "
              f"puis les voisins de conteneur)")
    boucle(studio, args.jeton, args.comfy.rstrip("/"), sorties, args.garder,
           ollama, args.empreinte, not args.sans_maj_auto)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\narrete.")
        sys.exit(0)
