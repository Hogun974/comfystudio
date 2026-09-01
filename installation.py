#!/usr/bin/env python3
"""Installe ce dont ComfyStudio a besoin, en s'adaptant a la machine.

Un seul fichier pour Windows et Linux : les deux lanceurs (installer.bat et
installer.sh) ne font que trouver un Python et appeler celui-ci. Dupliquer la
logique dans deux scripts aurait garanti qu'ils divergent.

    python installer.py                  diagnostic, puis propositions
    python installer.py --materiel       diagnostic seulement
    python installer.py --dependances    aiohttp, av, huggingface_hub seulement
    python installer.py --comfyui        installe ComfyUI
    python installer.py --ollama         installe Ollama et ses modeles
    python installer.py --modeles A,B    telecharge ces moteurs
    python installer.py --tout           tout ce que la machine peut tenir
    python installer.py --oui            ne demande aucune confirmation

Aucune dependance : le catalogue est lu depuis catalogue.py, et le
telechargement des modeles installe huggingface_hub au besoin.
"""
import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
import textwrap

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
from catalogue import (CATALOGUE, POIDS, poids,   # noqa: E402
                       annonce_poids)

WINDOWS = os.name == "nt"


def _candidats_comfy():
    """Endroits ou une installation existante peut se trouver, du plus probable
    au moins probable. On ne devine pas : on regarde."""
    maison = os.path.expanduser("~")
    bruts = [os.path.join(ICI, "..", "ComfyUI_windows_portable", "ComfyUI"),
             os.path.join(ICI, "..", "ComfyUI"),
             os.path.join(ICI, "ComfyUI"),
             os.path.join(maison, "ComfyUI"),
             os.path.join(maison, "ComfyUI_windows_portable", "ComfyUI"),
             os.path.join(maison, "Documents", "ComfyUI")]
    if WINDOWS:
        for lettre in "CDEFG":
            bruts += [f"{lettre}:\\ComfyUI_windows_portable\\ComfyUI",
                      f"{lettre}:\\ComfyUI"]
    else:
        bruts += ["/opt/ComfyUI", "/srv/ComfyUI"]
    vus, trouves = set(), []
    for c in bruts:
        c = os.path.abspath(c)
        if c in vus:
            continue
        vus.add(c)
        if os.path.exists(os.path.join(c, "main.py")):
            trouves.append(c)
    return trouves


def _trouver_comfy():
    """Une installation existante avant tout : reinstaller par-dessus une
    installation deja en place serait le pire service a rendre."""
    force = os.environ.get("COMFY_DIR")
    if force:
        return os.path.abspath(force)
    trouves = _candidats_comfy()
    if trouves:
        return trouves[0]
    return os.path.abspath(os.path.join(ICI, "..", "ComfyUI"))


RACINE_COMFY = _trouver_comfy()
DEPOT_COMFY = "https://github.com/comfyanonymous/ComfyUI.git"
MODELES_OLLAMA = ["qwen2.5vl:7b"]

# Marge a laisser a Windows et au bureau : une carte de 8 Go n'en offre pas 8.
MARGE_VRAM = 0.8


# ══════════════════════════ presentation ══════════════════════════════
def titre(t):
    print("\n" + t)
    print("-" * len(t))


def demander(question, oui_partout=False):
    if oui_partout:
        print(f"  {question} — oui (sans confirmation)")
        return True
    try:
        return input(f"  {question} [o/N] ").strip().lower() in ("o", "oui", "y", "yes")
    except EOFError:
        return False


def lancer(cmd, **kw):
    """Execute et laisse la sortie s'afficher : une installation est longue,
    l'utilisateur doit voir qu'il se passe quelque chose."""
    print("  $ " + (cmd if isinstance(cmd, str) else " ".join(cmd)))
    return subprocess.call(cmd, shell=isinstance(cmd, str), **kw)


# ══════════════════════════ materiel ══════════════════════════════════
def cartes():
    """Cartes NVIDIA vues par nvidia-smi. Liste vide si aucune."""
    try:
        sortie = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, errors="replace", timeout=20).stdout
    except Exception:
        return []
    trouvees = []
    for ligne in sortie.splitlines():
        if "," not in ligne:
            continue
        nom, mo = ligne.rsplit(",", 1)
        try:
            trouvees.append((nom.strip(), round(int(mo.strip()) / 1024, 1)))
        except ValueError:
            pass
    return trouvees


def memoire_vive():
    """Gigaoctets de RAM. Sans psutil : il n'est pas forcement installe, et on
    ne va pas exiger une dependance pour lire un nombre."""
    try:
        if WINDOWS:
            sortie = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory"],
                capture_output=True, text=True, errors="replace", timeout=30).stdout
            return round(int(sortie.strip()) / 1024 ** 3, 1)
        if sys.platform == "darwin":
            sortie = subprocess.run(["sysctl", "-n", "hw.memsize"],
                                    capture_output=True, text=True, timeout=20).stdout
            return round(int(sortie.strip()) / 1024 ** 3, 1)
        with open("/proc/meminfo", encoding="utf-8") as f:
            for ligne in f:
                if ligne.startswith("MemTotal:"):
                    return round(int(ligne.split()[1]) / 1024 ** 2, 1)
    except Exception:
        pass
    return 0.0


def espace_libre(chemin):
    cible = chemin
    while cible and not os.path.exists(cible):
        parent = os.path.dirname(cible)
        if parent == cible:
            break
        cible = parent
    try:
        return round(shutil.disk_usage(cible or ".").free / 1024 ** 3, 1)
    except Exception:
        return 0.0


def diagnostic():
    gpus = cartes()
    vram = max((v for _, v in gpus), default=0.0)
    ram = memoire_vive()
    libre = espace_libre(RACINE_COMFY)
    titre("Materiel detecte")
    if gpus:
        for nom, v in gpus:
            print(f"  carte      {nom} — {v} Go de VRAM")
    else:
        print("  carte      aucune carte NVIDIA detectee (nvidia-smi absent ou "
              "pilote non installe)")
    print(f"  memoire    {ram or '?'} Go de RAM")
    print(f"  disque     {libre} Go libres sur {RACINE_COMFY}")
    print(f"  systeme    {platform.system()} {platform.release()}")
    return vram, ram, libre


def utilisable(vram):
    """La VRAM annoncee n'est jamais entierement disponible : le bureau en
    consomme, et ComfyUI en reserve une part."""
    return max(0.0, vram - MARGE_VRAM)


def tolerance(ram):
    """De combien la RAM permet de depasser la carte.

    ComfyUI deborde sur la memoire systeme quand un modele ne tient pas : le
    rendu ralentit mais aboutit. Un seuil binaire sur la seule VRAM ecarterait
    des moteurs qui tournent tres bien — mesure sur une 2080 Ti de 11 Go avec
    64 Go de RAM, qui fait tourner un modele video de 14 milliards de parametres.
    """
    if ram >= 64:
        return 5.0
    if ram >= 32:
        return 3.5
    if ram >= 16:
        # Mesure du 28 aout 2026 : une GTX 1060 de 6 Go avec 23 Go de RAM fait
        # tourner SDXL, qui est justement concu pour cette classe de carte. Un
        # palier a 32 Go l'aurait declaree incapable de tout.
        return 2.0
    return 0.0


# Modeles dont la licence n'est PAS libre. Cle : (sous-dossier, nom), donc le
# fichier reellement telecharge et non le moteur, parce que plusieurs moteurs
# partagent souvent un meme fichier. La table vit ici et non dans catalogue.py
# parce qu'elle repond a une question d'installeur - que faut-il faire accepter
# avant de telecharger - et non a « de quoi ce moteur a besoin ».
LICENCES = {
    ("checkpoints", "sam3.1_multiplex_fp16.safetensors"):
        "SAM License (Meta), 1,75 Go : l'usage commercial est autorise, mais la "
        "redistribution doit se faire aux memes termes et la retro-ingenierie "
        "est interdite. Meta peut en changer les termes unilateralement. Ce "
        "n'est pas une licence libre : l'AGPL-3.0 du studio ne la couvre pas, "
        "et ce modele est un telechargement que tu choisis, pas une dependance "
        "du logiciel.",
}


def licences(cle):
    """Les licences non libres qu'exige ce moteur, sans doublon."""
    return sorted({LICENCES[(s, n)] for s, n, _, _ in CATALOGUE[cle]["fichiers"]
                   if (s, n) in LICENCES})


def dire_licence(cle, retrait="    "):
    """Le texte de la licence, plie pour rester lisible dans un terminal."""
    for texte in licences(cle):
        for bout in textwrap.wrap(texte, 68):
            print(f"{retrait}{bout}")


def moteurs_possibles(vram, ram, avec_licence=False):
    """Trois categories : ce qui tient sur la carte, ce qui deborde en RAM sans
    cesser de fonctionner, et ce qui ne passe pas.

    Un moteur sous licence non libre est laisse DEHORS par defaut. Cette
    fonction dresse aussi la liste que modeles.sh telecharge sans poser de
    question sur une machine-noeud, et une licence ne s'accepte pas a la place
    de quelqu'un. avec_licence=True pour l'affichage, qui doit au contraire
    montrer que le moteur existe et a quel prix.
    """
    tenable = utilisable(vram)
    marge = tenable + tolerance(ram)
    tiennent, debordent, refuses = [], [], []
    for cle, m in CATALOGUE.items():
        if licences(cle) and not avec_licence:
            continue
        besoin = m.get("vram", 0)
        if besoin <= tenable:
            tiennent.append(cle)
        elif besoin <= marge:
            debordent.append(cle)
        else:
            refuses.append((cle, besoin))
    return tiennent, debordent, refuses


def afficher_moteurs(vram, ram):
    # avec_licence=True : montrer le moteur meme s'il ne partira jamais dans un
    # telechargement automatique. L'omettre ici ferait croire que la carte ne
    # le tient pas.
    tiennent, debordent, refuses = moteurs_possibles(vram, ram, avec_licence=True)

    def ligne(cle, note=""):
        m = CATALOGUE[cle]
        # « au moins » quand une taille manque au catalogue : poids() la compte
        # pour zero, et « ~0 Go a prendre » se lit comme « c'est gratuit »
        # devant un fichier qu'on va bel et bien telecharger.
        etat = ("deja la" if not manquants(cle)
                else f"{annonce_poids([cle])} a prendre")
        if licences(cle):
            note += "  (licence a accepter)"
        print(f"  {cle:16s} {m['vram']:4.1f} Go  {m['titre']:30s} {etat}{note}")

    titre("Moteurs que cette machine peut faire tourner")
    if not tiennent and not debordent:
        # Ne pas s'arreter la : c'est exactement la machine que le README
        # recommande pour heberger le studio, et lui dire « il faut une carte »
        # sans dire la suite decourage sur un montage qui marche tres bien.
        print("  aucun sur cette machine : il faudrait une carte NVIDIA d'au "
              "moins 6 Go.")
        print()
        print("  Ce n'est pas bloquant. Un studio sans carte reste utile :")
        print("    - il repartit le travail sur des machines A CARTE, chacune")
        print("      portant un agent qui l'appelle — rien a ouvrir sur le")
        print("      reseau. Voir « Des machines qui viennent d'elles-memes »")
        print("      dans le README ;")
        print("    - avec une cle d'API, il confie texte, images, musique ou")
        print("      video a un fournisseur. Voir « Cles d'API ».")
    for cle in tiennent:
        ligne(cle)
    if debordent:
        print(f"\n  Au-dela de la carte, mais tenables grace aux {ram} Go de RAM "
              f"(plus lents) :")
        for cle in debordent:
            ligne(cle, "  *")
    if refuses:
        print()
        for cle, besoin in refuses:
            print(f"  ecarte     {cle:16s} demande {besoin} Go, la carte en offre "
                  f"{utilisable(vram):.1f}")
    if ram and ram < 32:
        print(f"\n  {ram} Go de RAM : aucune marge de debordement. 32 Go la rendent "
              f"confortable,")
        print("  64 Go la rendent presque invisible.")
    # Nommer la licence ICI, pendant que quelqu'un lit l'ecran : le diagnostic
    # est la seule etape que tous les chemins d'installation traversent.
    lies = [c for c in tiennent + debordent if licences(c)]
    if lies:
        print()
        for cle in lies:
            print(f"  {cle} exige un modele sous licence particuliere :")
            dire_licence(cle)
        print(f"  Jamais pris automatiquement. Pour le demander : "
              f"--modeles {','.join(lies)}")
    return tiennent + debordent


# ═══════════════ dependances Python du studio ═════════════════════════
# Ce que serveur.py importe. Le tableau redit requirements.txt, plus ce que ce
# fichier ne sait pas exprimer : laquelle est bloquante, et ce que coute
# exactement l'absence des deux autres. Sans cette distinction, un echec sur
# « av » aurait la meme couleur qu'un echec sur aiohttp, alors que l'un degrade
# une fonction et l'autre empeche le studio de demarrer.
#   (module a importer, ce qu'on donne a pip, bloquante, ce que son absence coute)
DEPENDANCES = [
    ("aiohttp", "aiohttp>=3.9", True,
     "sert l'interface et parle a ComfyUI : rien ne demarre sans elle"),
    ("av", "av>=12", False,
     "lit la cadence d'une video ; sans elle le studio suppose 24 im/s, et une "
     "video en 16 im/s ressort acceleree sans le moindre message"),
    ("huggingface_hub", "huggingface_hub>=0.24", False,
     "confort de telechargement ; sans elle le studio tire les modeles en "
     "HTTPS direct, ce qui marche mais sans cache ni reprise"),
]


def _chemin_reel(py):
    """Le chemin absolu de l'executable, demande a l'interpreteur lui-meme.

    Un nom nu ne suffit pas : sous Windows « py » est un LANCEUR, qui peut fort
    bien demarrer une autre version que celle qu'on croit viser, et sous Linux
    « python3 » depend du PATH de qui l'appelle. sys.executable est le seul a
    designer sans ambiguite le fichier dans lequel pip va ecrire.
    """
    try:
        r = subprocess.run([py, "-c", "import sys;print(sys.executable)"],
                           capture_output=True, text=True, errors="replace",
                           timeout=180)
        vu = r.stdout.strip()
        if r.returncode == 0 and vu and os.path.exists(vu):
            return vu
    except Exception:
        pass
    return py


def python_du_studio():
    """L'interpreteur qui fera tourner serveur.py — rarement celui qui execute
    cet installeur.

    C'est le piege principal de toute cette section : pip repond « Successfully
    installed » et le studio echoue quand meme a l'import, parce que le paquet
    est arrive dans un AUTRE Python. Sous Windows le studio demarre avec le
    Python embarque de ComfyUI, jamais avec celui du PATH.

    Renvoie (chemin, comment on l'a trouve) — le second sert a l'afficher, pour
    que l'utilisateur puisse contredire la deduction s'il la trouve fausse.
    """
    force = os.environ.get("STUDIO_PYTHON")
    if force:
        # Pose par installer.bat, installer.sh et « LANCER ComfyStudio.bat » :
        # eux n'ont pas a deduire, ils savent quel interpreteur ils utilisent.
        # Ils ont le droit d'y mettre un nom du PATH ou un chemin relatif ; le
        # resoudre est notre travail, pas celui d'un script .bat.
        return _chemin_reel(force), "impose par STUDIO_PYTHON"
    if WINDOWS:
        # On le deduit du ComfyUI trouve plus haut plutot que de le coder en
        # dur : le dossier portable n'est pas toujours a cote du studio, et une
        # machine peut en heberger plusieurs.
        bases = [os.path.dirname(RACINE_COMFY)]
        bases += [os.path.dirname(c) for c in _candidats_comfy()]
        for base in bases:
            exe = os.path.join(base, "python_embeded", "python.exe")
            if os.path.exists(exe):
                return exe, ("Python embarque de ComfyUI, celui que lance "
                             "LANCER ComfyStudio.bat")
    return sys.executable, "celui qui execute cet installeur"


def _tester_import(py, module):
    """Vrai si « module » s'importe DANS cet interpreteur-la.

    On teste avec les memes options que le lanceur : « LANCER ComfyStudio.bat »
    demarre le studio par « python -s serveur.py », et -s masque le site
    utilisateur. Un paquet pose par « pip install --user » se verrait sans -s et
    resterait invisible au studio : le test dirait « present » et le demarrage
    echouerait quand meme. C'est aussi pourquoi on n'installe jamais --user.
    """
    drapeaux = ["-s"] if WINDOWS else []
    try:
        return subprocess.run([py] + drapeaux + ["-c", "import " + module],
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL,
                              timeout=180).returncode == 0
    except Exception:
        return False


def _pip_utilisable(py):
    """(vrai, ce qu'on a vu) ou (faux, la marche a suivre).

    Le Python embarque de ComfyUI est livre avec un fichier « ._pth » qui peut
    laisser « import site » en commentaire. Dans ce cas pip n'est ni importable
    ni installable, et « python -m pip » repond « No module named pip » : un
    message qui ne nomme ni la cause ni la reparation. On va donc lire ce
    fichier pour pouvoir les nommer a sa place.
    """
    try:
        r = subprocess.run([py, "-m", "pip", "--version"], capture_output=True,
                           text=True, errors="replace", timeout=180)
    except Exception as e:
        return False, [f"{py} ne repond pas ({type(e).__name__})"]
    if r.returncode == 0:
        return True, [r.stdout.strip()]

    detail = ["pip est absent de cet interpreteur."]
    dossier = os.path.dirname(os.path.abspath(py))
    pth = ""
    try:
        for nom in sorted(os.listdir(dossier)):
            if nom.endswith("._pth"):
                pth = os.path.join(dossier, nom)
                break
    except OSError:
        pass
    if pth:
        try:
            with open(pth, encoding="utf-8", errors="replace") as f:
                lignes = f.read().splitlines()
        except OSError:
            lignes = []
        if not any(l.strip() == "import site" for l in lignes):
            detail += [
                f"{os.path.basename(pth)} laisse la ligne 'import site' en "
                f"commentaire :",
                "tant qu'elle est commentee, pip reste introuvable meme une",
                "fois installe. Deux gestes, dans cet ordre :",
                f"  1. ouvre {pth}",
                "     et enleve le # devant la ligne 'import site'",
            ]
        else:
            detail.append(f"la ligne 'import site' est bien active dans "
                          f"{os.path.basename(pth)} : pip n'a jamais ete pose.")
    amorce = os.path.join(dossier, "get-pip.py")
    if os.path.exists(amorce):
        detail.append(f"  2. \"{py}\" \"{amorce}\"   (le fichier est deja la)")
    else:
        detail += ["  2. recupere https://bootstrap.pypa.io/get-pip.py",
                   f"     puis \"{py}\" get-pip.py"]
    return False, detail


def _reseau_ok():
    """Un aller-retour TCP vers PyPI, avant de laisser pip s'y casser les dents.

    Sans ce test, une machine hors ligne recoit les vingt lignes de pip
    (retries, NewConnectionError, ProxyError, une trace urllib3) ou le mot
    « reseau » n'apparait nulle part et le nom du paquet une seule fois.
    """
    import socket

    if os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy"):
        # Derriere un proxy, la connexion directe echoue toujours alors que pip
        # passe tres bien. On ne conclut donc rien et on le laisse essayer.
        return True
    try:
        socket.create_connection(("pypi.org", 443), 5).close()
        return True
    except OSError:
        return False


# Ce que pip dit quand c'est le reseau, et non le paquet, qui a echoue.
_MOTS_RESEAU = ("Temporary failure in name resolution", "Network is unreachable",
                "NewConnectionError", "Max retries exceeded", "getaddrinfo failed",
                "ProxyError", "Connection refused", "Read timed out")


def _resume_echec_pip(sortie):
    """Trois ou quatre lignes utiles, pas la trace entiere.

    pip echoue en trente lignes dont vingt-huit decrivent sa propre mecanique
    de reessai. Les trois cas ci-dessous couvrent presque tous les echecs
    reels, et chacun appelle une reparation differente."""
    if "externally-managed-environment" in sortie:
        return ["ce Python appartient au systeme (PEP 668) : pip refuse d'y ecrire.",
                "  Debian, Ubuntu   sudo apt install python3-aiohttp python3-av",
                "  Fedora           sudo dnf install python3-aiohttp",
                "  partout          python3 -m venv ~/comfystudio-venv puis lance",
                "                   le studio avec ~/comfystudio-venv/bin/python3"]
    if any(m in sortie for m in _MOTS_RESEAU):
        return ["pip n'a pas pu atteindre PyPI : reseau, proxy ou pare-feu."]
    if ("Permission denied" in sortie or "Access is denied" in sortie
            or "WinError 5" in sortie):
        return ["ecriture refusee dans ce Python : relance en administrateur,",
                "ou installe le studio dans un environnement qui t'appartient."]
    erreurs = [l.rstrip() for l in sortie.splitlines() if l.startswith("ERROR")]
    if erreurs:
        return erreurs[:4]
    utiles = [l.rstrip() for l in sortie.splitlines() if l.strip()]
    return utiles[-3:] or ["pip a echoue sans rien dire."]


def _verdict(py, restants):
    """Ce qui manque encore apres la tentative. aiohttp est le seul veto : les
    deux autres degradent une fonction, et refuser de demarrer pour ca ferait
    plus de mal que leur absence."""
    for module, spec, bloquante, cout in restants:
        if not bloquante:
            print(f"  attention  {module} reste absent — {cout}")
            print(f"             plus tard : \"{py}\" -m pip install \"{spec}\"")
    bloquantes = [d for d in restants if d[2]]
    if bloquantes:
        print()
        print("  ECHEC : aiohttp n'est pas installe pour cet interpreteur.")
        print("  serveur.py meurt a l'import, avant meme d'ouvrir son port :")
        print("  le studio ne demarrera pas tant que ce point n'est pas regle.")
        return False
    return True


def installer_dependances():
    """Verifie d'abord, et n'installe QUE ce qui manque.

    Un « pip install -r requirements.txt » inconditionnel a chaque lancement
    coute plusieurs secondes et un aller-retour vers PyPI pour ne rien faire
    dans la quasi-totalite des cas ; trois « import » testes coutent moins
    d'une seconde et ne touchent pas au reseau. C'est pour cela que le lanceur
    peut se permettre d'appeler cette fonction a CHAQUE demarrage.

    Renvoie vrai si le studio peut demarrer, c'est-a-dire si aiohttp est la.
    """
    titre("Dependances Python")
    py, raison = python_du_studio()
    print(f"  cible      {py}")
    print(f"             {raison}")
    if os.path.dirname(py) and not os.path.exists(py):
        print("  cet interpreteur n'existe pas : rien a verifier.")
        print("  designe le bon avec la variable STUDIO_PYTHON.")
        return False

    manque = []
    for entree in DEPENDANCES:
        module = entree[0]
        if _tester_import(py, module):
            print(f"  present    {module}")
        else:
            print(f"  manquant   {module}")
            manque.append(entree)
    if not manque:
        print("  rien a installer.")
        return True

    ok, detail = _pip_utilisable(py)
    if not ok:
        print()
        for ligne in detail:
            print("  " + ligne)
        print()
        return _verdict(py, manque)

    if not _reseau_ok():
        print()
        print("  Pas de reseau : pypi.org ne repond pas sur le port 443.")
        print("  Rien n'a ete installe. Depuis une machine reliee :")
        print("      pip download -d paquets " +
              " ".join('"%s"' % d[1] for d in manque))
        print("  copie le dossier paquets ici, puis :")
        print(f"      \"{py}\" -m pip install --no-index --find-links paquets " +
              " ".join('"%s"' % d[1] for d in manque))
        print()
        return _verdict(py, manque)

    restants = []
    for entree in manque:
        module, spec = entree[0], entree[1]
        print(f"  installation de {spec} ...", flush=True)
        # Jamais --user : le lanceur demarre le studio avec -s, qui ignore le
        # site utilisateur. Le paquet serait bien installe, visible depuis un
        # terminal, et introuvable au demarrage.
        cmd = [py, "-m", "pip", "install", "--no-input",
               "--disable-pip-version-check", spec]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True,
                               errors="replace", timeout=1800)
        except Exception as e:
            print(f"    echec : {type(e).__name__}")
            restants.append(entree)
            continue
        if r.returncode != 0:
            for ligne in _resume_echec_pip((r.stdout or "") + (r.stderr or "")):
                print("    " + ligne)
            restants.append(entree)
            continue
        # On ne croit pas pip sur parole. Il annonce « Successfully installed »
        # meme quand le paquet atterrit dans un site que CET interpreteur ne lit
        # pas ; seul un import reussi le prouve.
        if _tester_import(py, module):
            print(f"    {module} installe, et importable.")
        else:
            print(f"    pip a reussi, mais 'import {module}' echoue toujours.")
            print("    le paquet est arrive dans un autre site que celui-ci.")
            restants.append(entree)
    return _verdict(py, restants)


# ══════════════════════════ modeles ═══════════════════════════════════
def racine_modeles():
    return os.environ.get("COMFY_MODELES") or os.path.join(RACINE_COMFY, "models")


def manquants(cle):
    base = racine_modeles()
    return [(s, n, r, d) for s, n, r, d in CATALOGUE[cle]["fichiers"]
            if not os.path.exists(os.path.join(base, s, n))]


def telecharger_direct(repo, distant, cible):
    """Un fichier de Hugging Face, par une simple requete HTTPS.

    Ecrit d'abord dans un « .part » puis renomme : une coupure laisse ainsi un
    fichier visiblement incomplet plutot qu'un modele tronque que ComfyUI
    chargerait a moitie avant d'echouer sans expliquer pourquoi.
    """
    import urllib.request

    url = f"https://huggingface.co/{repo}/resolve/main/{distant}"
    partiel = cible + ".part"
    req = urllib.request.Request(url, headers={"User-Agent": "comfystudio"})
    with urllib.request.urlopen(req, timeout=120) as r:
        total = int(r.headers.get("Content-Length") or 0)
        fait = 0
        dernier = -1
        with open(partiel, "wb") as f:
            while True:
                bloc = r.read(1 << 20)
                if not bloc:
                    break
                f.write(bloc)
                fait += len(bloc)
                if total:
                    pourcent = fait * 100 // total
                    if pourcent >= dernier + 5:
                        dernier = pourcent
                        print(f"      {pourcent:3d} %  {fait / 1e9:5.1f} / "
                              f"{total / 1e9:.1f} Go", flush=True)
    os.replace(partiel, cible)
    return cible


def assurer_hub():
    try:
        import huggingface_hub  # noqa: F401
        return True
    except ImportError:
        # On tente de l'installer, mais son absence n'est plus bloquante : le
        # telechargement direct prend le relais. Sur un NAS sans pip et a racine
        # en lecture seule, c'est la seule voie.
        lancer([sys.executable, "-m", "pip", "install", "-q", "huggingface_hub"])
        try:
            import huggingface_hub  # noqa: F401
            return True
        except ImportError:
            print("  huggingface_hub indisponible — telechargement direct en HTTPS")
            return False


def telecharger(cles, oui, avec_hub=True):
    hf_hub_download = None
    if avec_hub:
        try:
            from huggingface_hub import hf_hub_download
        except ImportError:
            avec_hub = False

    a_faire = [(cle, f) for cle in cles for f in manquants(cle)]
    sans_source = [(cle, f) for cle, f in a_faire if not f[2]]
    faisables = [(cle, f) for cle, f in a_faire if f[2]]
    if not a_faire:
        print("  tous les modeles demandes sont deja la.")
        return
    total = annonce_poids({c for c, _ in faisables})
    titre("Telechargement")
    print(f"  {len(faisables)} fichier(s) a prendre, {total}.")
    if sans_source:
        print("  Ces fichiers n'ont pas de source automatique (depot sous licence "
              "ou modele a installer a la main) :")
        for cle, (sous, nom, _, _) in sans_source:
            print(f"    {cle:16s} {sous}/{nom}")
    # Redit ici, et pas seulement au diagnostic : --modeles court-circuite
    # l'affichage, et c'est la derniere marche avant l'ecriture sur disque.
    for cle in sorted({c for c, _ in faisables if licences(c)}):
        print(f"  {cle} : modele sous licence non libre.")
        dire_licence(cle)
    if not faisables or not demander("Lancer le telechargement ?", oui):
        return
    base = racine_modeles()
    for cle, (sous, nom, repo, distant) in faisables:
        dest = os.path.join(base, sous)
        os.makedirs(dest, exist_ok=True)
        print(f"  {cle} : {nom}")
        try:
            if not avec_hub:
                telecharger_direct(repo, distant, os.path.join(dest, nom))
                continue
            chemin = hf_hub_download(repo_id=repo, filename=distant, local_dir=dest)
            voulu = os.path.join(dest, nom)
            if os.path.abspath(chemin) != os.path.abspath(voulu):
                shutil.move(chemin, voulu)
                # hf_hub_download recree l'arborescence du depot : on la retire
                reste = os.path.dirname(chemin)
                while os.path.abspath(reste) != os.path.abspath(dest):
                    try:
                        os.rmdir(reste)
                    except OSError:
                        break
                    reste = os.path.dirname(reste)
            shutil.rmtree(os.path.join(dest, ".cache"), ignore_errors=True)
        except Exception as e:
            print(f"    echec : {type(e).__name__} {str(e)[:160]}")


# ══════════════════════════ ComfyUI ═══════════════════════════════════
def comfyui_present():
    return os.path.exists(os.path.join(RACINE_COMFY, "main.py"))


def installer_comfyui(vram, oui):
    titre("ComfyUI")
    if comfyui_present():
        print(f"  deja installe dans {RACINE_COMFY}")
        return True
    if not shutil.which("git"):
        print("  git est introuvable. Installe-le d'abord :")
        print("    Windows : winget install Git.Git")
        print("    Linux   : sudo apt install git   (ou l'equivalent)")
        return False
    print(f"  ComfyUI sera clone dans {RACINE_COMFY}")
    print("  puis un environnement Python dedie sera cree, avec PyTorch CUDA.")
    print("  Compter une dizaine de gigaoctets et un bon moment.")
    if not demander("Continuer ?", oui):
        return False
    if lancer(["git", "clone", "--depth", "1", DEPOT_COMFY, RACINE_COMFY]) != 0:
        return False

    venv = os.path.join(RACINE_COMFY, "venv")
    if lancer([sys.executable, "-m", "venv", venv]) != 0:
        print("  creation de l'environnement impossible.")
        return False
    py = os.path.join(venv, "Scripts" if WINDOWS else "bin",
                      "python.exe" if WINDOWS else "python")
    lancer([py, "-m", "pip", "install", "-q", "--upgrade", "pip"])
    # cu128 couvre les cartes de Turing a Blackwell ; sans carte, on prend la
    # version processeur, qui marche mais reste tres lente.
    roue = ("https://download.pytorch.org/whl/cu128" if vram
            else "https://download.pytorch.org/whl/cpu")
    if lancer([py, "-m", "pip", "install", "torch", "torchvision", "torchaudio",
               "--index-url", roue]) != 0:
        return False
    lancer([py, "-m", "pip", "install", "-r",
            os.path.join(RACINE_COMFY, "requirements.txt")])
    print(f"\n  ComfyUI installe. Pour le lancer :")
    print(f"    {py} {os.path.join(RACINE_COMFY, 'main.py')} --disable-auto-launch")
    return True


# ══════════════════════════ Ollama ════════════════════════════════════
def ollama_present():
    return shutil.which("ollama") is not None


def installer_ollama(oui):
    titre("Ollama")
    if ollama_present():
        print("  deja installe.")
    elif WINDOWS:
        if shutil.which("winget"):
            if demander("Installer Ollama par winget ?", oui):
                lancer(["winget", "install", "--id", "Ollama.Ollama",
                        "--accept-source-agreements", "--accept-package-agreements"])
        else:
            print("  winget est absent. Telecharge l'installeur ici :")
            print("    https://ollama.com/download/windows")
            return False
    else:
        print("  La methode officielle telecharge et execute un script :")
        print("    curl -fsSL https://ollama.com/install.sh | sh")
        print("  Lis-le avant si tu preferes : https://ollama.com/install.sh")
        if not demander("Executer cette commande ?", oui):
            return False
        lancer("curl -fsSL https://ollama.com/install.sh | sh")

    if not ollama_present():
        print("  ollama reste introuvable dans le PATH — ouvre un nouveau terminal "
              "puis relance avec --ollama.")
        return False
    for modele in MODELES_OLLAMA:
        print(f"  modele {modele} (environ 6 Go)")
        if demander(f"Telecharger {modele} ?", oui):
            lancer(["ollama", "pull", modele])
    return True


# ══════════════════════════ choix guide ═══════════════════════════════
# Ordre de preference par usage : on propose le meilleur que la machine tienne,
# pas une liste figee. Sur une grosse carte, klein9bhd remplace klein4b ; sur
# une petite, on se rabat sans rien dire de plus.
FAMILLES = [
    ("polyvalent, texte lisible", ["klein9bhd", "klein4b", "klein9b"]),
    ("photographie", ["flux1hd", "flux1", "realvis"]),
    ("illustration, manga", ["pony"]),
    ("retouche d'image", ["edition"]),
]


def proposition(possibles):
    """Un point de depart raisonnable : de quoi couvrir les usages courants
    sans telecharger tout le catalogue."""
    choix = []
    for _, candidats in FAMILLES:
        for cle in candidats:
            if cle in possibles:
                choix.append(cle)
                break
    if not choix and possibles:
        # aucune famille couverte : plutot que de ne rien proposer, on offre le
        # moins lourd de ce que la machine tient
        choix = [min(possibles, key=lambda c: POIDS.get(c, 0))]
    return choix


def choisir(question, options, defaut=1):
    """Un menu numerote. Entree vide = le defaut, qui est toujours le premier
    et toujours le moins destructeur."""
    for i, (libelle, _) in enumerate(options, 1):
        marque = " (defaut)" if i == defaut else ""
        print(f"    {i}) {libelle}{marque}")
    try:
        rep = input(f"  {question} [{defaut}] ").strip()
    except EOFError:
        rep = ""
    if not rep:
        return options[defaut - 1][1]
    if rep.isdigit() and 1 <= int(rep) <= len(options):
        return options[int(rep) - 1][1]
    print("  reponse non comprise — on garde le defaut.")
    return options[defaut - 1][1]


def menu_comfyui(vram, oui):
    """Reutiliser une installation, en designer une autre, ou en poser une neuve."""
    global RACINE_COMFY
    titre("ComfyUI")
    trouves = _candidats_comfy()
    options = [(f"reutiliser  {c}", ("garder", c)) for c in trouves]
    options.append(("indiquer un autre dossier", ("demander", None)))
    options.append((f"installer une copie neuve dans {RACINE_COMFY}", ("installer", None)))
    options.append(("ne rien faire pour l'instant", ("rien", None)))
    if not trouves:
        print("  aucune installation detectee.")
    action, valeur = choisir("Que faire ?", options,
                             defaut=1 if trouves else len(options) - 1)

    if action == "demander":
        try:
            valeur = input("  chemin du dossier ComfyUI : ").strip().strip('"')
        except EOFError:
            valeur = ""
        if not os.path.exists(os.path.join(valeur, "main.py")):
            print(f"  {valeur or '(vide)'} ne contient pas main.py — abandon.")
            return False
        action = "garder"
    if action == "garder":
        RACINE_COMFY = os.path.abspath(valeur)
        print(f"  retenu : {RACINE_COMFY}")
        return True
    if action == "installer":
        return installer_comfyui(vram, oui)
    return False


def menu_moteurs(possibles, oui):
    """Liste numerotee, avec une proposition prete a accepter."""
    titre("Moteurs a telecharger")
    absents = [c for c in possibles if manquants(c)]
    if not absents:
        print("  tout ce que cette machine peut tenir est deja installe.")
        return []
    conseil = [c for c in proposition(possibles) if c in absents]
    for i, cle in enumerate(absents, 1):
        m = CATALOGUE[cle]
        etoile = " <-- propose" if cle in conseil else ""
        if licences(cle):
            etoile += "  (licence a accepter)"
        print(f"    {i:2d}) {cle:16s} {m['vram']:4.1f} Go  "
              f"{annonce_poids([cle])} a prendre  {m['titre']}{etoile}")
    if conseil:
        total = annonce_poids(conseil)   # union : deux moteurs partagent des fichiers
        print(f"\n  Proposition : {', '.join(conseil)}  ({total})")
    print("  Reponds par des numeros separes par des espaces, ou :")
    print("    entree = la proposition,  tout = tous,  rien = aucun")
    try:
        rep = input("  ton choix : ").strip().lower()
    except EOFError:
        rep = ""
    if rep in ("rien", "aucun", "non", "n"):
        return []
    if rep in ("tout", "tous", "t"):
        # « tout » repond a « prends ce que ma carte tient », pas a « j'accepte
        # n'importe quelle licence ». Ce qui en exige une se demande par son
        # numero, apres avoir lu de quoi il s'agit.
        libres = [c for c in absents if not licences(c)]
        for cle in absents:
            if licences(cle):
                print(f"  {cle} laisse de cote : licence a accepter, "
                      f"designe-le par son numero pour le prendre")
        return libres
    if not rep:
        return conseil
    choisis = []
    for morceau in re.split(r"[\s,]+", rep):
        if morceau.isdigit() and 1 <= int(morceau) <= len(absents):
            choisis.append(absents[int(morceau) - 1])
        elif morceau in CATALOGUE and morceau in absents:
            choisis.append(morceau)
        elif morceau:
            print(f"  ignore : {morceau}")
    return list(dict.fromkeys(choisis))


def guide(vram, ram, possibles, oui):
    """Le parcours propose quand on lance l'installeur sans argument."""
    if not menu_comfyui(vram, oui):
        print("\n  Sans ComfyUI, les modeles n'auraient nulle part ou aller.")
        return
    if not ollama_present():
        installer_ollama(oui)
    else:
        titre("Ollama")
        print("  deja installe.")
        for modele in MODELES_OLLAMA:
            if not modele_ollama_present(modele) and demander(
                    f"Telecharger {modele} (environ 6 Go) ?", oui):
                lancer(["ollama", "pull", modele])
    cles = menu_moteurs(possibles, oui)
    if cles and assurer_hub():
        telecharger(cles, oui)


def modele_ollama_present(nom):
    try:
        sortie = subprocess.run(["ollama", "list"], capture_output=True, text=True,
                                errors="replace", timeout=30).stdout
        return nom.split(":")[0] in sortie
    except Exception:
        return False


# ══════════════════════════ enchainement ══════════════════════════════
def main():
    a = argparse.ArgumentParser(add_help=True, description=__doc__.splitlines()[0])
    a.add_argument("--materiel", action="store_true", help="diagnostic seulement")
    a.add_argument("--dependances", action="store_true",
                   help="verifie et installe les seules dependances Python")
    a.add_argument("--comfyui", action="store_true")
    a.add_argument("--ollama", action="store_true")
    a.add_argument("--modeles", default="", help="liste separee par des virgules")
    a.add_argument("--tout", action="store_true",
                   help="ComfyUI, Ollama et tous les moteurs que la carte tient")
    a.add_argument("--oui", action="store_true", help="aucune confirmation")
    args = a.parse_args()

    if args.dependances:
        # Chemin court, celui qu'emprunte « LANCER ComfyStudio.bat » a chaque
        # demarrage : ni banniere ni diagnostic materiel. nvidia-smi et
        # PowerShell coutent plusieurs secondes, et le studio n'a pas besoin de
        # connaitre la carte pour savoir s'il peut s'importer.
        return 0 if installer_dependances() else 1

    print("=" * 64)
    print("  Installeur ComfyStudio")
    print("=" * 64)
    vram, ram, libre = diagnostic()
    tiennent = afficher_moteurs(vram, ram)
    if args.materiel:
        return 0

    # Avant ComfyUI et avant les modeles : sans aiohttp, rien de ce qui suit ne
    # servirait jamais. On previent, mais on ne s'arrete pas — telecharger des
    # modeles depuis cette machine reste utile meme si son propre Python est mal
    # equipe (un noeud dont le studio tourne ailleurs, par exemple).
    if not installer_dependances():
        print("\n  On continue quand meme, mais relance "
              "'installer.py --dependances'")
        print("  une fois le probleme regle : sinon le studio ne demarrera pas.")

    cible = args.comfyui or args.ollama or args.modeles or args.tout
    if not cible:
        # Sans argument, on ne se contente pas d'afficher une aide : on propose,
        # et l'utilisateur choisit. Les drapeaux restent la pour les habitues et
        # pour les installations sans clavier.
        guide(vram, ram, tiennent, args.oui)
        titre("Ensuite")
        print("  1. lance ComfyUI")
        print("  2. lance ComfyStudio (LANCER ComfyStudio.bat, ou python serveur.py)")
        print("  3. ouvre http://127.0.0.1:8199")
        return 0

    if args.comfyui or args.tout:
        installer_comfyui(vram, args.oui)
    if args.ollama or args.tout:
        installer_ollama(args.oui)

    cles = []
    if args.tout:
        # Meme regle que le menu : « tout ce que la machine tient » ne vaut pas
        # acceptation d'une licence non libre.
        cles = [c for c in tiennent if not licences(c)]
        for c in tiennent:
            if licences(c):
                print(f"  {c} laisse de cote : licence a accepter "
                      f"(--modeles {c} pour le prendre)")
    elif args.modeles:
        for c in args.modeles.split(","):
            c = c.strip()
            if c not in CATALOGUE:
                print(f"  moteur inconnu : {c}")
            elif c not in tiennent:
                print(f"  {c} demande {CATALOGUE[c]['vram']} Go : la carte ne le tient pas")
            else:
                cles.append(c)
    if cles:
        # Un noeud a son ComfyUI en conteneur : main.py n existe pas sur l hote,
        # seul le dossier des modeles est monte. Exiger l un pour ecrire dans
        # l autre serait refuser de servir une machine capable.
        if not comfyui_present() and not os.environ.get("COMFY_MODELES"):
            print("\n  ComfyUI n'est pas installe : les modeles n'auraient nulle part "
                  "ou aller. Relance avec --comfyui d'abord.")
        else:
            telecharger(cles, args.oui, avec_hub=assurer_hub())

    titre("Ensuite")
    print("  1. lance ComfyUI")
    print("  2. lance ComfyStudio (LANCER ComfyStudio.bat, ou python serveur.py)")
    print("  3. ouvre http://127.0.0.1:8199")
    return 0


# Le point d entree est installer.py : il verifie la version de Python
# AVANT de lire ce fichier, qui est plein de f-strings.
