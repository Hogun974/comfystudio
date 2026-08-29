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
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ICI = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(ICI, "agent_noeud.json")
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


def executer(comfy, graphe):
    """Soumet le graphe et attend la fin. Rend (fichiers, secondes, erreur)."""
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
        time.sleep(2)


def lire_sortie(comfy, f):
    """Recupere les octets d'un fichier produit, pour les envoyer au studio."""
    q = urllib.parse.urlencode({"filename": f["filename"],
                                "subfolder": f.get("subfolder", ""),
                                "type": f.get("type", "output")})
    st, octets = appeler(f"{comfy}/view?{q}", secondes=300)
    return octets if st == 200 and isinstance(octets, (bytes, bytearray)) else None


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
def boucle(studio, jeton, comfy):
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
    while True:
        try:
            maintenant = time.time()
            # 1. s'annoncer regulierement : c'est ce qui rend le noeud visible
            if maintenant - derniere_annonce > 10:
                etat = etat_comfy(comfy)
                if not etat:
                    if connu:
                        print("  ComfyUI ne repond plus — on attend")
                        connu = False
                    time.sleep(PAUSE_LONGUE)
                    continue
                corps = dict(etat)
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
                fichiers, secondes, erreur = executer(comfy, travail["graphe"])

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
                                                          "http://127.0.0.1:8188")}
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--studio", default=cfg.get("studio", ""),
                   help="adresse du studio, par exemple http://192.0.2.10:8199")
    a.add_argument("--jeton", default=cfg.get("jeton", ""),
                   help="jeton delivre par l'administration du studio")
    a.add_argument("--comfy", default=cfg.get("comfy"),
                   help="adresse du ComfyUI local")
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

    if (studio, args.jeton, args.comfy) != (cfg.get("studio"), cfg.get("jeton"),
                                            cfg.get("comfy")):
        ecrire_config({"studio": studio, "jeton": args.jeton, "comfy": args.comfy})
    print("=" * 60)
    print("  Agent ComfyStudio")
    print("=" * 60)
    boucle(studio, args.jeton, args.comfy.rstrip("/"))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\narrete.")
        sys.exit(0)
