# -*- mode: python ; coding: utf-8 -*-
"""Recette PyInstaller : ComfyStudio en un seul .exe Windows.

Construire depuis paquet\\ :
    ..\\..\\ComfyUI_windows_portable\\python_embeded\\python.exe -m PyInstaller comfystudio.spec

Quatre choses ne se devinent pas et sont donc ecrites ici :

1. serveur.py fait « from catalogue import ... » sur des modules VOISINS, pas
   installes. Sans pathex, l'analyse ne les trouve pas et l'exe plante a la
   premiere ligne d'import.
2. Le studio ne sert pas que du code : web/, aiguilleur.json et les dix scripts
   de mise en service des machines-noeuds sont ouverts a l'execution par un
   chemin construit a la main. PyInstaller ne peut pas les voir : ils sont
   listes un par un dans DONNEES.
3. entrainer_aiguilleur est charge par importlib.import_module() (serveur.py
   ligne 3593), un nom construit a l'execution que l'analyse statique ne suit
   pas. D'ou hiddenimports.
4. L'exe n'a AUCUN moyen de savoir quelle version il est : pas de .git, et le
   code est deplie dans un dossier temporaire. La spec grave donc l'identifiant
   a la construction, dans le fichier que serveur.py lit — voir « Ce que l'exe
   annoncera » plus bas, et docs/installation.md.
"""
import os

ICI = os.path.abspath(SPECPATH)             # noqa: F821 — fourni par PyInstaller
SOURCE = os.path.dirname(ICI)               # D:\ComfyStudio

# Mettre a 1 pour laisser PyAV dehors. Mesure sur cette machine : l'exe tombe
# de 45 120 925 a 17 817 972 octets (mesure du 5 septembre 2026), soit 27 Mo
# pour les DLL ffmpeg de av.libs.
# Le prix est mesurer_cadence() qui rend alors toujours 24 im/s (le repli deja
# prevu par le try/except de serveur.py ligne 2547) : une video televersee a
# une autre cadence serait rejouee a 24. Defaut 0 : on paie les 27 Mo plutot
# que de degrader une fonction en silence.
SANS_AV = os.environ.get("PAQUET_SANS_AV", "0") == "1"


def _f(nom, dest="."):
    """Un fichier a embarquer, en echouant tot s'il a disparu.

    Une donnee manquante ne se voit pas a la construction : elle donne un 404
    des mois plus tard, sur une machine-noeud, sans rien dans le journal du
    studio. On prefere casser la construction ici.
    """
    chemin = os.path.join(SOURCE, nom)
    if not os.path.exists(chemin):
        raise SystemExit("paquet : fichier absent de la source -> " + nom)
    return (chemin, dest)


DONNEES = [
    # Les deux pages servies par FileResponse(ICI/web/...), lignes 4239 et 5076.
    _f("web/index.html", "web"),
    _f("web/admin.html", "web"),
    # Le classifieur d'intention, lu par aiguilleur.charger() au demarrage.
    # Absent, le studio marche encore mais tout passe par le modele de langage.
    #
    # Le SECOND modele, aiguilleur.local.json, n'est PAS ici et ne doit pas y
    # entrer : entraine avec les demandes reelles de cette installation, il en
    # porte le vocabulaire. charger() le prefere quand il existe, mais gele il
    # n'existe jamais a cote de aiguilleur.py (les deux chemins sortent de ICI,
    # donc du _MEIxxx temporaire) et le repli sur celui-ci est verifie.
    _f("aiguilleur.json"),
    _f("noeuds.exemple.json"),
]

# SCRIPTS_NOEUD (serveur.py ligne 5081) : servis en texte brut par
# /api/agent/<quoi>. Ce sont des DONNEES, pas du code, meme pour les .py :
# catalogue.py est a la fois un module importe ET un fichier telecharge par les
# machines-noeuds, il figure donc deux fois dans le paquet, sous deux formes.
for _script in ("agent_noeud.py", "noeud.sh", "noeud.bat",
                "zimaos-comfyui.yml", "zimaos-registry.yml",
                "installer.py", "installation.py", "catalogue.py",
                "modeles.sh",
                # non references par SCRIPTS_NOEUD mais cites par noeud.sh /
                # noeud.bat pour la mise a jour ; les omettre casse la mise a
                # jour d'un noeud deja pose.
                "maj_noeud.sh", "maj_noeud.bat"):
    DONNEES.append(_f(_script))

# entrainer_aiguilleur tire corpus_aiguillage, et les deux lisent des .jsonl
# a cote d'eux. Le reentrainement depuis l'admin n'a donc de sens que si les
# corpus suivent. Ils sont volumineux (570 Ko) mais restent negligeables devant
# le reste, et sans eux /api/aiguilleur/mesurer rend une trace de pile.
for _corpus in ("corpus_aiguillage.jsonl", "corpus_llm.jsonl",
                "corpus_llm2.jsonl", "banc_aiguillage.jsonl",
                "banc_neuf.jsonl"):
    DONNEES.append(_f(_corpus))

# ── Ce que l'exe annoncera ────────────────────────────────────────────
# Un exe n'emporte pas .git, et sous PyInstaller ICI pointe sur un _MEIxxx
# temporaire ou il n'y a rien a lire : _version_du_depot() y est muet, ce qui
# est la verite. La seule facon pour l'executable de savoir ce qu'il est, c'est
# qu'on le lui grave ICI, a la construction.
#
# ET SURTOUT PAS RELU A L'EXECUTION dans le dossier de l'exe. Ce .bat
# recommande de poser l'exe dans D:\ComfyStudio, qui EST un clone : mesure du
# 4 septembre 2026, l'executable construit le 30 aout a 15 h 22 y annoncerait
# le commit du jour, 187 commits plus loin. Un identifiant faux est pire que
# « inconnue ».
def _identifiant_de_construction():
    """Le commit court de la SOURCE, ou "" si on ne peut pas savoir.

    On ne casse PAS la construction quand git manque, contrairement a _f() :
    une donnee absente donne un 404 des mois plus tard et se cache, alors qu'un
    identifiant absent se voit du premier coup — le studio imprime « Version :
    inconnue » a chaque demarrage. Le refus tardif n'a rien a garder ici.
    """
    import subprocess
    try:
        fini = subprocess.run(["git", "-C", SOURCE, "rev-parse", "--short", "HEAD"],
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              timeout=5)
    except Exception:
        return ""
    return (fini.stdout.decode("utf-8", "replace").strip()
            if fini.returncode == 0 else "")


# Dans build\, qui est deja hors du depot (.gitignore) et que
# construire_windows.bat efface avant chaque construction : ecrire a la racine
# de la source y laisserait un fichier que le studio LU DEPUIS LE CLONE
# prefererait un jour a son propre depot. Le nom du fichier est celui que
# serveur.py lit — FICHIER_VERSION — et le Dockerfile grave le meme.
VERSION_GRAVEE = os.path.join(ICI, "build", "version.txt")
os.makedirs(os.path.dirname(VERSION_GRAVEE), exist_ok=True)
with open(VERSION_GRAVEE, "w", encoding="utf-8") as _sortie_version:
    _sortie_version.write(_identifiant_de_construction() + "\n")
# Pas _f() : ce fichier vient d'etre ecrit, il ne peut pas manquer, et son
# absence ne serait de toute facon pas une raison de casser la construction.
DONNEES.append((VERSION_GRAVEE, "."))

CACHES = [
    # importlib.import_module("entrainer_aiguilleur") : nom en chaine, invisible
    # a l'analyse statique.
    "entrainer_aiguilleur",
    "corpus_aiguillage",
    # aiohttp choisit son analyseur HTTP a l'execution ; l'extension C n'est
    # atteinte par aucun import litteral au niveau module.
    "aiohttp._http_parser",
    "aiohttp._websocket.mask",
    "aiohttp._websocket.reader_c",
    # multidict/yarl ont chacun une version C et une version pure Python
    # selectionnees par try/except a l'import.
    "multidict._multidict",
    "yarl._quoting_c",
]

EXCLUS = [
    # Le Python embarque de ComfyUI heberge torch, numpy, transformers... Rien
    # de tout cela n'est importe par le studio, mais un seul faux positif de
    # l'analyse ferait passer l'exe de 100 Mo a plusieurs gigaoctets. On coupe
    # explicitement.
    "torch", "torchvision", "torchaudio", "numpy", "scipy", "transformers",
    "safetensors", "PIL", "cv2", "matplotlib", "pandas", "sklearn",
    "tkinter", "IPython", "pytest", "setuptools", "pip",
]
if SANS_AV:
    EXCLUS.append("av")

a = Analysis(                                              # noqa: F821
    [os.path.join(SOURCE, "serveur.py")],
    pathex=[SOURCE],          # voir point 1 de l'en-tete
    binaries=[],
    datas=DONNEES,
    hiddenimports=CACHES,
    hookspath=[],
    runtime_hooks=[],
    excludes=EXCLUS,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)                                          # noqa: F821

exe = EXE(                                                 # noqa: F821
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="ComfyStudio",
    debug=False,
    bootloader_ignore_signals=False,
    # UPX est absent de cette machine et compresser un exe reseau le fait
    # signaler par les antivirus : on s'en passe.
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    # Le studio parle par sa console (adresses reseau, VRAM, file d'attente).
    # En mode fenetre on perdrait le seul journal que l'utilisateur ait.
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
