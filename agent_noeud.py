#!/usr/bin/env python3
"""Agent ComfyStudio : fait travailler un ComfyUI local pour un studio distant.

C'est l'agent qui appelle le studio, jamais l'inverse. Une machine derriere une
box, sur un portable qui s'endort, ou sur un reseau qu'on ne maitrise pas ne
peut pas etre jointe de l'exterieur ; elle peut toujours sortir. L'agent
s'annonce, reclame du travail, le fait executer par son ComfyUI, puis renvoie
les fichiers produits.

    python agent_noeud.py --studio http://192.0.2.10:8199 --jeton XXXX
    python agent_noeud.py --maj          # se remplace par la derniere version

Le studio et le jeton sont retenus dans agent_noeud.json, a cote de ce fichier :
les lancements suivants n'ont plus besoin d'arguments. En conteneur, ou il n'y a
pas de fichier, les variables STUDIO_URL, STUDIO_JETON et COMFY_URL font le meme
office.

Aucune dependance : seulement la bibliotheque standard. Une machine qui fait
tourner ComfyUI a forcement un Python.
"""
import base64
import argparse
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
GARDE_DEFAUT = 24           # heures avant d'effacer une sortie deja au studio
PURGE_TOUS_LES = 600        # secondes entre deux passages de menage
PAUSE_COURTE = 3            # entre deux demandes de travail
PAUSE_LONGUE = 20           # apres une erreur : on n'insiste pas
CONTEXTE = ssl.create_default_context()

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
                for champ in ("image", "file"):
                    if (noeud.get("inputs") or {}).get(champ) == nom:
                        noeud["inputs"][champ] = vrai
    return None


def executer(comfy, graphe, dire=None):
    """Soumet le graphe et attend la fin. Rend (fichiers, secondes, erreur).

    « dire » recoit la progression a chaque tour de boucle : c'est ce qui rend
    la barre de la file vivante quand le rendu se fait ailleurs que sur la
    machine du studio.
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
        if dire and PROGRES["total"]:
            dire(PROGRES["fait"], PROGRES["total"])
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
    while True:
        try:
            st, q = appeler(f"{studio}/api/noeud/question", jeton, secondes=30)
            if st != 200 or not isinstance(q, dict) or "qid" not in q:
                time.sleep(PAUSE_COURTE)
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
    return os.path.join(sorties or ICI, "." + DEPOSEES if sorties else DEPOSEES)


def _registre(sorties=""):
    try:
        with open(_registre_chemin(sorties), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, list) else []
    except Exception:
        return []


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
def se_mettre_a_jour(studio):
    """Recupere la derniere version du script depuis le studio.

    Le studio sert l'agent : mettre a jour une machine revient a relancer ce
    script avec --maj, sans depot a cloner ni fichier a recopier a la main.
    """
    st, octets = appeler(f"{studio}/api/noeud/agent", secondes=60)
    if st != 200 or not isinstance(octets, (bytes, bytearray)):
        print(f"  mise a jour impossible : {st} {str(octets)[:120]}")
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
    print(f"  mis a jour ({len(octets)} octets). L'ancienne version est dans "
          f"{os.path.basename(moi)}.precedent")
    return 0


# ══════════════════════════ boucle ════════════════════════════════════
def boucle(studio, jeton, comfy, sorties="", garder=GARDE_DEFAUT, ollama=""):
    print(f"  studio  : {studio}", flush=True)
    print(f"  ComfyUI : {comfy}", flush=True)
    print("  en service — ctrl+C pour arreter\n", flush=True)
    derniere_annonce = 0.0
    modeles_envoyes = 0.0
    # Vrai au premier tour : le studio ne sait rien de cette machine tant qu'on
    # ne lui a rien dit, et attendre cinq minutes la rendrait inutilisable
    # d'autant.
    reclame_modeles = True
    connu = False
    dernier_menage = 0.0
    # Un fil a part, en arriere-plan : la progression ne doit jamais retarder la
    # demande de travail, et son echec ne coute qu'un pourcentage.
    threading.Thread(target=ecouter_progression, args=(comfy,), daemon=True).start()
    if ollama:
        threading.Thread(target=servir_le_langage, args=(studio, jeton, ollama),
                         daemon=True).start()
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
            # 1. s'annoncer regulierement : c'est ce qui rend le noeud visible
            if maintenant - derniere_annonce > 10:
                etat = etat_comfy(comfy)
                if not etat:
                    if connu:
                        print("  ComfyUI ne repond plus — on attend")
                        connu = False
                    # On s'annonce quand meme, avec ce qu'on a : cette machine
                    # porte peut-etre un modele de langage, et c'est justement
                    # celle dont le studio a besoin quand le sien tombe. Se
                    # taire la rendait invisible pour ça aussi.
                    if ollama:
                        appeler(f"{studio}/api/noeud/annonce", jeton,
                                {"comfy": False,
                                 "llm": etat_ollama(ollama) or {"ok": False,
                                                                "modeles": []}})
                    derniere_annonce = maintenant
                    time.sleep(PAUSE_LONGUE)
                    continue
                corps = dict(etat)
                # Reevalue a chaque annonce : un modele peut etre telecharge ou
                # retire pendant que l'agent tourne.
                if ollama:
                    corps["llm"] = etat_ollama(ollama) or {"ok": False,
                                                           "modeles": []}
                # la liste des modeles change rarement : toutes les cinq minutes
                # Le studio peut reclamer l'inventaire : il vient de redemarrer
                # et ne connait plus rien de cette machine. Repondre tout de
                # suite evite cinq minutes pendant lesquelles il la croit vide.
                if maintenant - modeles_envoyes > 300 or reclame_modeles:
                    corps["modeles"] = modeles_comfy(comfy)
                    modeles_envoyes = maintenant
                st, d = appeler(f"{studio}/api/noeud/annonce", jeton, corps)
                derniere_annonce = maintenant
                if st == 401:
                    print("  jeton refuse par le studio — verifie l'administration")
                    time.sleep(30)
                    continue
                if st != 200:
                    if connu:
                        print(f"  studio injoignable ({st}) — on reessaie")
                        connu = False
                    time.sleep(PAUSE_LONGUE)
                    continue
                # Le studio dit s'il connait nos modeles. Il ne les connait
                # plus apres chacun de ses redemarrages.
                reclame_modeles = bool((d or {}).get("modeles_demandes"))
                if not connu:
                    nom = (d or {}).get("titre") or "?"
                    print(f"  connecte au studio en tant que « {nom} » "
                          f"— {etat['carte']}, {etat['vram']} Go", flush=True)
                    connu = True

            # 2. reclamer du travail
            st, travail = appeler(f"{studio}/api/noeud/travail", jeton, secondes=30)
            if st == 204 or not travail:
                time.sleep(PAUSE_COURTE)
                continue
            if st != 200 or "graphe" not in travail:
                time.sleep(PAUSE_LONGUE)
                continue

            tid = travail["tid"]
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
                    if time.time() - dernier[0] < 2:
                        return
                    dernier[0] = time.time()
                    appeler(f"{studio}/api/noeud/progres", jeton,
                            {"tid": tid, "fait": fait, "total": total}, secondes=10)

                fichiers, secondes, erreur = executer(comfy, travail["graphe"], dire)

            # 3. deposer les fichiers produits, puis rendre le resultat
            deposes = []
            for f in fichiers:
                octets = lire_sortie(comfy, f)
                if octets is None:
                    erreur = erreur or f"fichier illisible : {f['filename']}"
                    continue
                q = urllib.parse.urlencode({"tid": tid, "nom": f["filename"]})
                st, _ = appeler(f"{studio}/api/noeud/fichier?{q}", jeton,
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
            appeler(f"{studio}/api/noeud/resultat", jeton,
                    {"tid": tid, "etat": "erreur" if erreur else "fini",
                     "erreur": erreur, "secondes": round(secondes, 1),
                     "fichiers": deposes})
            print(f"  travail {tid[:8]} {'echoue' if erreur else 'rendu'} "
                  f"en {secondes:.0f} s — {len(deposes)} fichier(s)", flush=True)
        except KeyboardInterrupt:
            raise
        except Exception as e:
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
    args = a.parse_args()

    studio = args.studio.rstrip("/")
    if not studio:
        print("  Il manque l'adresse du studio : --studio http://...:8199")
        return 1
    if args.maj:
        return se_mettre_a_jour(studio)
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
    boucle(studio, args.jeton, args.comfy.rstrip("/"), sorties, args.garder, ollama)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\narrete.")
        sys.exit(0)
