# -*- coding: utf-8 -*-
"""Une variable posee dans .env atteint-elle vraiment le studio ?

    python banc_conteneur.py

Compose ne transmet QUE ce qu'il nomme. Une variable posee dans .env et absente
du bloc « environment: » est lue hors conteneur et ignoree dedans, sans un mot
— et le studio du reseau tourne en conteneur. Dix reglages etaient dans ce cas
pendant que la documentation les donnait pour reconnus.

Ce banc a ete ecrit pour empecher ce defaut de revenir, et TROIS relectures
adverses lui ont montre par quelles portes il revenait quand meme. Chacune est
fermee ici, et chaque fermeture a sa mutation :

  - OLLAMA_URL etait invisible : le releve ne regardait que STUDIO_ et COMFY_.
  - une ligne « ENV » du Dockerfile suffisait a rendre une variable « arrivee ».
    Elle arrive, en effet, avec la valeur de l'image, et .env reste lettre
    morte : c'est le degat qu'on veut interdire, pas son contraire.
  - seule la clef etait lue. « STUDIO_ANALYSE_MAX: "${STUDIO_ANALYSE_MAXX:-}" »
    passait : relayee, vide pour toujours.
  - « os.getenv » et les apostrophes SIMPLES echappaient au releve. Un reglage
    neuf ecrit sous cette forme n'arrivait pas au conteneur, et le banc restait
    vert — le scenario d'origine, rejoue sous le nez du filet.
  - le bloc du service etait delimite par un bandeau de commentaire decoratif.
    Le retirer — un nettoyage anodin — rattachait au studio les variables du
    conteneur voisin. La frontiere est desormais l'indentation, qui est du YAML
    et non de la decoration.
  - le piege des deux defauts vivait encore dans .env.exemple pour les reglages
    dont le defaut est ecrit dans le COMPOSE et non dans le code.
  - le releve des imports s'ancrait en colonne 0. serveur.py compte DOUZE
    imports paresseux indentes — c'est le style de la maison — et un module
    neuf importe a cote de l'un d'eux sortait du suivi : sa variable, absente
    du compose, passait au vert. Le scenario d'origine rejoue entier. Le NOMBRE
    de fichiers suivis n'etait d'ailleurs asserte nulle part, et aucun des
    quatre modules importes ne lit d'environnement a lui seul : une retombee de
    cinq fichiers a un serait restee verte elle aussi.
  - defaut_du_code rendait un FRAGMENT d'expression la ou le code n'a pas de
    defaut litteral — « os.path.join(BASE_COMFY, », « str(PORT », « ICI_DATA ».
    Un fragment est pire que rien : truthy, il court-circuitait le repli sur le
    defaut du compose et se comparait a tout sans jamais l'egaler. Cinq
    reglages sur vingt-cinq echappaient ainsi aux DEUX pieges des defauts.

Toute exception se nomme ici, avec sa raison. C'est le seul endroit ou l'on peut
en ajouter une, et il faut l'ecrire.
"""
import ast
import fnmatch
import io
import os
import posixpath
import re
import sys

# LA CONSOLE WINDOWS ECRIT EN cp1252, et ce banc n'importe pas serveur.py —
# c'est serveur.py qui reconfigure la sortie pour tout le reste du depot. Le
# tiret cadratin passait (il est dans cp1252), le trait de tableau « U+2500 »
# non : le banc est MORT sur son propre titre de section le 5 septembre 2026,
# une pile d'appels a la place du verdict. Meme correction que dans
# banc_comptes.py, et pour la meme raison.
for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ICI = os.path.dirname(os.path.abspath(__file__))
ok, rate = [], []

# L'IMAGE impose la valeur, .env n'y peut rien. Une entree ici est un aveu :
# « ce reglage n'est pas reglable en conteneur, et voici pourquoi. »
IMPOSEES = {
    "STUDIO_HOTE": "127.0.0.1 dans un conteneur ne repond a personne : le port "
                   "publie tomberait dans le vide",
    "STUDIO_PORT": "le conteneur ecoute TOUJOURS sur 8199 ; c'est le compose "
                   "qui le publie ailleurs, et STUDIO_PORT_HOTE le lui dit",
    "STUDIO_DONNEES": "/donnees est le point de montage du volume : le changer "
                      "ferait ecrire les conversations dans la couche jetable",
    "COMFY_DIR": "/comfy est le point de montage de ComfyUI, meme raison",
}

# Relayees par une AUTRE variable, volontairement. On ecrit LAQUELLE et non une
# phrase : une dispense en bloc laissait passer « ${STUDIO_PORTT:-8199} », la
# faute de frappe que la verification existe justement pour attraper.
DERIVEES = {"STUDIO_PORT_HOTE": "STUDIO_PORT"}


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


def lire(nom):
    return io.open(os.path.join(ICI, nom), encoding="utf-8").read()


SRV = lire("serveur.py")

# Le studio, ET les modules qu'il importe. L'image copie tous les .py, mais
# agent_noeud.py ne tourne PAS dans ce conteneur : n'en relever les variables
# donnerait des oublis imaginaires. On suit donc les imports plutot que le
# repertoire.
#
# « ^\s* » et non « ^ » : serveur.py compte DOUZE imports indentes en cours de
# fonction (import av, import struct, import socket...). Un module neuf importe
# a cote de l'un d'eux echappait au suivi, et sa variable absente du compose ne
# faisait rougir personne — le commit f6a30ba, rejoue sous le nez du filet.
# L'ARBRE DE SYNTAXE ET NON UN MOTIF DE TEXTE, depuis le 3 septembre 2026 — et
# le motif avait un angle mort OCCUPE. serveur.py charge
# « entrainer_aiguilleur » par importlib.import_module (le reentrainement
# depuis /admin) : neuf modules chargés, huit suivis. Le neuvieme echappait donc
# aussi au controle des variables d'environnement, qui est tout l'objet de ce
# banc — et le motif ne pouvait pas le voir, par construction.
#
# C'est la forme meme que la mutation « un module suivi charge par importlib »
# imitait depuis des semaines pour montrer le danger. Elle imitait un defaut qui
# existait deja, dix lignes plus loin, en vrai.
def _modules_charges(source):
    """Les modules du depot que serveur.py charge, vus par ast.

    « import x », « from x import y », ET « importlib.import_module("x") » avec
    un argument litteral : c'est la seule forme dynamique du depot. Un nom
    CALCULE resterait invisible — on ne pretend pas le voir, et il n'en existe
    aucun ici.
    """
    vus = set()
    for n in ast.walk(ast.parse(source)):
        noms = []
        if isinstance(n, ast.Import):
            noms = [a.name.split(".")[0] for a in n.names]
        elif isinstance(n, ast.ImportFrom) and n.module and not n.level:
            noms = [n.module.split(".")[0]]
        elif (isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute)
                and n.func.attr == "import_module"
                and n.args and isinstance(n.args[0], ast.Constant)
                and isinstance(n.args[0].value, str)):
            noms = [n.args[0].value.split(".")[0]]
        for nom in noms:
            if os.path.exists(os.path.join(ICI, nom + ".py")):
                vus.add(nom + ".py")
    return vus


FICHIERS = ["serveur.py"] + sorted(_modules_charges(SRV))
CODE = "\n".join(lire(f) for f in FICHIERS)

# L'HISTOIRE DE CE PASSAGE, parce qu'elle explique la forme actuelle. Un
# « FICHIERS_SUIVIS » ecrit a la main a garde ce suivi de fin aout au
# 3 septembre 2026 : il fallait le monter a CHAQUE module ajoute a serveur.py,
# faute de quoi retirer un module du suivi en laissait encore assez, le seuil
# restait atteint, et la mutation « un module suivi charge par importlib »
# passait au VERT. Il s'est fait oublier trois fois en deux jours — cinq a six,
# six a sept, sept a huit — et chaque fois c'est banc_mutations.py qui l'a dit.
#
# Ce n'etait pas un reglage mal tenu : c'etait un SECOND COMPTAGE de ce que la
# ligne du dessus venait de calculer, et deux ecritures du meme fait divergent.
# La lecon est la meme que RE_DEVIS, que la marque du « deja refait » et que le
# libelle des reglages ; elle a simplement mis plus longtemps a se voir ici,
# parce qu'un nombre ne ressemble pas a une recopie.

# SANS CE PLANCHER, TOUT CE QUI SUIT SERAIT VRAI DE RIEN. Le controle des
# variables d'environnement lit « CODE », c'est-a-dire ces fichiers-la : un jeu
# vide n'a aucune variable non declaree, et le banc se compterait vert sur un
# serveur.py qui n'importerait plus rien — ou sur un ast.parse qui aurait cesse
# de rendre quoi que ce soit. Quatre, et non le compte exact : ce nombre-ci ne
# suit AUCUN ajout de module, il dit seulement « le suivi n'est pas tombe a
# rien ». C'est ce qui le distingue du seuil qu'il remplace, oublie trois fois
# en deux jours parce qu'il recomptait a la main ce que le code venait de
# compter.
dit(len(FICHIERS) >= 4,
    f"les {len(FICHIERS)} fichiers du conteneur sont suivis",
    ", ".join(FICHIERS[1:]) or "aucun module importe")

# ET AUCUN LECTEUR D'ENVIRONNEMENT NE S'ECHAPPE. Voila la verification que le
# seuil ecrit a la main essayait de rendre, sans y arriver : ce qui compte n'est
# pas COMBIEN de fichiers sont suivis, c'est qu'aucun de ceux qui lisent
# l'environnement ne sorte du suivi — puisque c'est leur lecture, et elle seule,
# que ce banc confronte au compose.
#
# La liste des dispenses ne grandit PAS a chaque module ajoute au studio : elle
# nomme ce qui ne tourne pas dans CE conteneur, et cela ne bouge presque jamais.
# C'est ce qui la distingue d'un nombre a monter a chaque import.
HORS_CONTENEUR = {
    "agent_noeud.py": "tourne sur la machine a carte, pas ici — l'image le "
                      "copie pour le SERVIR aux noeuds, jamais pour l'executer",
    "installation.py": "l'installeur natif ; en conteneur, c'est le Dockerfile "
                       "qui installe",
    "outils_etalons_qr.py": "un outil de developpement, lance a la main avec "
                            "une dependance qui n'est pas au depot",
}
_lecteurs = []
for _f in sorted(os.listdir(ICI)):
    if not _f.endswith(".py") or _f in FICHIERS or _f in HORS_CONTENEUR:
        continue
    # Les bancs et les recettes ne tournent pas dans le conteneur non plus, et
    # les nommer un par un ferait exactement la liste qui rouille. Le motif du
    # nom suffit, et il est la convention du depot.
    if _f.startswith(("banc_", "recette_", "verifier_")):
        continue
    if re.search(r"environ\.get|environ\[|os\.getenv", lire(_f)):
        _lecteurs.append(_f)
dit(not _lecteurs,
    "et aucun fichier qui lit l'environnement n'echappe au suivi",
    ", ".join(_lecteurs) + " — lu par personne ici" if _lecteurs
    else f"{len(HORS_CONTENEUR)} dispense(s) nommee(s)")

# ET L'IMAGE LES EMPORTE TOUS. C'est la moitie qui manquait : suivre un module
# ne sert a rien s'il n'arrive pas dans le conteneur, et le Dockerfile pourrait
# tres bien nommer ses fichiers un par un — c'est ce qu'il fait deja pour les
# scripts d'enrolement, ligne « COPY noeud.sh noeud.bat … ». La regle se lit
# donc dans le Dockerfile, jamais dans une liste ecrite ici.
_copies = []
for ligne in lire("Dockerfile").splitlines():
    if ligne.strip().startswith("COPY "):
        _copies += ligne.split()[1:-1]
_absents = [f for f in FICHIERS
            if not any(fnmatch.fnmatch(f, m) for m in _copies)]
dit(not _absents,
    "et l'image emporte chacun d'eux",
    ", ".join(_absents) + " — absent(s) des lignes COPY" if _absents
    else " ".join(_copies[:3]) + " …")

# ET LES DEUX EMPAQUETAGES EMPORTENT LES MEMES DONNEES. Ils n'en disaient pas
# autant : paquet/comfystudio.spec embarque les cinq .jsonl depuis toujours,
# avec la raison ecrite a cote — « le reentrainement depuis l'admin n'a de sens
# que si les corpus suivent » — et le Dockerfile n'en copiait AUCUN.
#
# CE QUE CA COUTAIT, mesure le 3 septembre 2026 en reconstruisant le systeme de
# fichiers de l'image : le bouton « reentrainer » de /admin faisait tomber le
# classifieur de 94 % a 74 % sur banc_aiguillage et de 88 % a 53 % sur
# banc_neuf — sous les planchers que la CI se donne elle-meme — en ecrivant le
# resultat dans le volume PERSISTANT, que charger() prefere au modele publie a
# chaque demarrage. Et les deux bancs manquant aussi, /admin n'affichait aucune
# mesure : rien ne pouvait le dire.
#
# On ne compare pas a une liste ecrite ici — ce serait un troisieme comptage du
# meme fait, et le depot en a corrige quatre en deux jours. On confronte les
# deux empaquetages l'un a l'autre.
_spec = lire("paquet/comfystudio.spec")
# « [a-z0-9_]+ » ET NON « [a-z_]+ » : le premier releve rendait QUATRE corpus
# sur cinq, parce que « corpus_llm2.jsonl » porte un chiffre. Le cas passait
# vert en ne mesurant que quatre cinquiemes de ce qu'il annonce — et le
# cinquieme est justement celui dont le nom sort du motif le plus naturel.
# C'est la faute que ce depot reproche aux expressions regulieres depuis le
# premier jour, commise en ecrivant la regle qui la denonce.
_embarques = set(re.findall(r'"([a-z0-9_]+\.jsonl)"', _spec))
_oublies = sorted(d for d in _embarques
                  if not any(fnmatch.fnmatch(d, m) for m in _copies))
# SANS CE PLANCHER, LA REGLE SERAIT VRAIE DE RIEN : une spec qui n'embarquerait
# plus aucun corpus rendrait les deux ensembles vides et ce cas vert.
dit(len(_embarques) >= 3,
    "l'executable embarque bien les corpus qui font le classifieur",
    ", ".join(sorted(_embarques)) or "aucun")
dit(not _oublies,
    "et l'image en conteneur emporte les MEMES",
    ", ".join(_oublies) + " — dans la spec, pas dans le Dockerfile"
    if _oublies else f"{len(_embarques)} corpus des deux cotes")

# AUCUN prefixe de nom, les DEUX sortes de guillemets, et « os.getenv » autant
# que « os.environ.get ». Chacune de ces trois largesses ferme une mutation qui
# passait au vert.
_LECTURE = (r'os[.](?:environ[.]get|getenv)[(]\s*[\'"]([A-Z][A-Z0-9_]*)[\'"]'
            r'|os[.]environ\[\s*[\'"]([A-Z][A-Z0-9_]*)[\'"]')
lues = {a or b for a, b in re.findall(_LECTURE, CODE)}
dit(len(lues) >= 25 and "OLLAMA_URL" in lues,
    f"{len(lues)} variables relevees dans {len(FICHIERS)} fichier(s)",
    "sans filtre de nom, OLLAMA_URL comprise")

compose = lire("docker-compose.yml")
# LE BLOC DU SERVICE, delimite par l'INDENTATION. Un bandeau de commentaire
# n'est pas une frontiere : le retirer rattachait au studio les variables du
# conteneur voisin, et le banc n'y voyait rien.
_svc = re.search(r'(?ms)^  comfystudio:\n(.*?)(?=^  \S|\Z)', compose)
bloc = _svc.group(1) if _svc else ""
lignes = dict(re.findall(r'^\s{6}([A-Z][A-Z0-9_]*):\s*(.*?)\s*$', bloc, re.M))
relayees = set(lignes)
dit(bool(bloc) and "COMFY_URL" in relayees and "ROUE" not in relayees,
    "le bloc du service est delimite par l'indentation, pas par un commentaire",
    f"{len(relayees)} variables dans comfystudio, et rien du voisin")

# Le Dockerfile n'est PAS une facon d'arriver au conteneur : c'est une facon de
# n'en jamais repartir. Une variable qu'il pose et que le compose ne relaie pas
# est figee dans l'image — ce que .env en dit n'a plus aucun effet.
DOCKER = lire("Dockerfile")
posees = set(re.findall(r'^ENV\s+([A-Z][A-Z0-9_]*)=', DOCKER, re.M))
posees |= set(re.findall(r'^\s+([A-Z][A-Z0-9_]*)=', DOCKER, re.M))

oubliees = sorted(lues - relayees - set(IMPOSEES))
dit(not oubliees, "tout ce qui est lu arrive au conteneur par le compose",
    ", ".join(oubliees) or "aucun oubli")


def _val(n):
    """La valeur d'une ligne du compose, guillemets retires."""
    return lignes[n].strip().strip('"').strip("'")


# Une exception qui ne correspond a RIEN est un mensonge : elle affirme qu'un
# reglage est impose par l'image alors qu'il ne l'est plus.
menteuses = sorted(n for n in IMPOSEES
                   if n not in posees
                   and not (n in relayees and not _val(n).startswith("${")))
dit(not menteuses, "chaque exception decrit un reglage reellement impose",
    ", ".join(menteuses) or "les quatre tiennent")

mortes = sorted((set(IMPOSEES) | set(DERIVEES)) - lues)
dit(not mortes, "aucune exception perimee", ", ".join(mortes) or "aucune")

# Guillemets RETIRES avant l'examen, comme pour « figees » plus bas : sans cela,
# « STUDIO_HOTE: ${STUDIO_HOTE:-0.0.0.0} » sans guillemets faisait passer une
# exception devenue inutile pour une exception encore valable.
inutiles = sorted(n for n in IMPOSEES if n in relayees and _val(n).startswith("${"))
dit(not inutiles, "aucune exception inutile",
    ", ".join(inutiles) or "chacune sert encore")


# Un defaut n'est un defaut que s'il est LITTERAL : chaine entre guillemets, ou
# nombre nu. Les guillemets etaient facultatifs, et le releve rendait alors le
# debut de l'expression — « os.path.join(BASE_COMFY, » pour COMFY_MODELES,
# « str(PORT » pour STUDIO_PORT_HOTE, « ICI_DATA » pour STUDIO_DONNEES. Une
# bouillie pareille est pire qu'un None : elle est truthy, donc elle
# court-circuitait le repli sur le defaut du compose plus bas, et elle se
# comparait au compose sans jamais l'egaler. Cinq reglages sur vingt-cinq
# passaient a travers les deux verifications ecrites pour eux.
#
# La negative en queue refuse « or 3600 * 2 » et « or "a" + b » : le premier
# morceau d'un calcul n'est pas plus une valeur que le premier morceau d'un
# appel.
_LITTERAL = r'(?:[\'"]([^\'"]*)[\'"]|(-?\d+(?:[.]\d+)?))(?!\s*[-+*/%.\w])'


# ── EVALUER LES DEFAUTS CALCULES, PARCE QUE CE SONT EUX QUI PIEGENT ────
# Le trou connu du 3 septembre 2026, ferme ici : « pas deux defauts pour un
# meme reglage » ne voyait que les defauts LITTERAUX. Or COMFY_MODELES vaut
# « os.path.join(BASE_COMFY, "models") », que le releve rendait tel quel — donc
# jamais egal a « /comfy/models » ecrit dans le compose. Le piege exact que la
# verification existe pour attraper lui echappait, et quatre chemins et un port
# avec lui.
#
# ON EVALUE COMME L'IMAGE, PAS COMME CETTE MACHINE. Deux consequences, et les
# deux comptent :
#
#   - posixpath et non os.path. Le compose decrit un conteneur Linux. Sur
#     Windows, os.path.join rendrait « /comfy\\models » et os.path.abspath
#     collerait « C:\\ » devant : le banc serait vert ici et rouge sur la CI,
#     ou l'inverse, pour une raison qui n'a rien a voir avec le depot.
#   - l'environnement est celui des lignes ENV du Dockerfile, pas le notre.
#     BASE_COMFY lit COMFY_DIR, que l'image pose a « /comfy » ; sans cela on
#     evaluerait le defaut Windows — « ComfyUI_windows_portable » — et l'on
#     comparerait au compose une valeur qu'aucun conteneur n'a jamais vue.
DOCKERFILE = lire("Dockerfile")
_TRAVAIL = (re.search(r"^WORKDIR\s+(\S+)", DOCKERFILE, re.M) or [None, "/"])[1]


def _env_de_l_image():
    """Ce que les lignes ENV du Dockerfile posent, continuations comprises."""
    dedans, brut = {}, DOCKERFILE.replace("\\\n", " ")
    for ligne in re.findall(r"^ENV\s+(.*)$", brut, re.M):
        for cle, val in re.findall(r"([A-Z][A-Z0-9_]*)=(\S*)", ligne):
            dedans[cle] = val.strip('"').strip("'")
    return dedans


ENV_IMAGE = _env_de_l_image()

_ARBRE_CODE = ast.parse(CODE)
# Les affectations de PREMIER NIVEAU seulement : une variable posee dans une
# fonction n'est pas un reglage du studio, et la confondre avec un ferait
# resoudre un nom par la mauvaise valeur.
_POSES = {}
for _n in _ARBRE_CODE.body:
    if isinstance(_n, ast.Assign):
        for _c in _n.targets:
            if isinstance(_c, ast.Name):
                _POSES.setdefault(_c.id, _n.value)


class _Inconnu(Exception):
    """Ce qu'on ne sait pas evaluer. Mieux vaut le dire que le deviner."""


def _evaluer(noeud, sans, vus=()):
    """La valeur de cette expression quand la variable « sans » est absente.

    « sans » et elle seule : les AUTRES variables gardent ce que l'image leur
    donne. C'est bien la question posee — « que vaut ce reglage si personne ne
    le pose » — et non « que vaut-il dans le vide ».
    """
    if isinstance(noeud, ast.Constant):
        return noeud.value
    if isinstance(noeud, ast.Name):
        if noeud.id in vus or noeud.id not in _POSES:
            raise _Inconnu(noeud.id)
        return _evaluer(_POSES[noeud.id], sans, vus + (noeud.id,))
    if isinstance(noeud, ast.BoolOp) and isinstance(noeud.op, ast.Or):
        val = None
        for morceau in noeud.values:
            val = _evaluer(morceau, sans, vus)
            if val:
                return val
        return val
    if isinstance(noeud, ast.Call):
        quoi = ast.unparse(noeud.func)
        args = [_evaluer(a, sans, vus) for a in noeud.args]
        if quoi in ("os.environ.get", "os.getenv"):
            if not args or not isinstance(args[0], str):
                raise _Inconnu(quoi)
            if args[0] == sans:
                return args[1] if len(args) > 1 else None
            return ENV_IMAGE.get(args[0], args[1] if len(args) > 1 else None)
        if quoi == "os.path.join":
            return posixpath.join(*[str(a) for a in args])
        if quoi == "os.path.abspath":
            return posixpath.normpath(posixpath.join(_TRAVAIL, str(args[0])))
        if quoi in ("int", "float", "str", "bool"):
            return {"int": int, "float": float, "str": str, "bool": bool}[quoi](args[0])
        if quoi in ("max", "min"):
            return {"max": max, "min": min}[quoi](*args)
        if quoi.endswith((".strip", ".lower", ".rstrip", ".upper")):
            socle = _evaluer(noeud.func.value, sans, vus)
            return getattr(str(socle), quoi.rsplit(".", 1)[1])(*args)
    raise _Inconnu(ast.dump(noeud)[:40])


def defaut_du_code(n):
    """La valeur que le code retient quand la variable est absente.

    Rend None quand on ne sait toujours pas evaluer : c'est honnete, et c'est
    ce que faisait la version d'avant pour TOUT ce qui n'etait pas litteral.
    """
    for nom, expression in _POSES.items():
        texte = ast.unparse(expression)
        if f'"{n}"' not in texte and f"'{n}'" not in texte:
            continue
        if not re.search(r"os[.](?:environ[.]get|getenv)", texte):
            continue
        try:
            valeur = _evaluer(expression, n)
        except (_Inconnu, TypeError, ValueError, RecursionError):
            break
        # « bool(os.environ.get(X)) » rend False quand X manque, et « False »
        # n'est pas un defaut qu'un compose puisse recopier : on ne compare que
        # ce qui s'ecrit dans un YAML.
        if isinstance(valeur, bool) or valeur is None:
            break
        return str(valeur)
    return _defaut_litteral(n)


def _defaut_litteral(n):
    """L'ancien releve, garde comme repli.

    Il attrape ce que l'evaluateur ne voit pas : un « os.environ.get » ecrit
    dans une fonction, donc absent des affectations de premier niveau.
    """
    appel = r'os[.](?:environ[.]get|getenv)[(]\s*[\'"]' + n + r'[\'"]\s*'
    for motif in (appel + r',\s*' + _LITTERAL,
                  appel + r'[)]\s*or\s+' + _LITTERAL):
        m = re.search(motif, CODE)
        if m:
            # Une seule des deux alternatives de _LITTERAL capture a la fois.
            return next(g for g in m.groups() if g is not None)
    return None


# Le cote DROIT de la ligne, celui que la premiere version ne lisait pas.
mauvais_renvoi, figees, repetes = [], [], []
defauts_compose = {}
for n in sorted(relayees):
    val = _val(n)
    m = re.match(r'^[$][{]([A-Z][A-Z0-9_]*)(?::-(.*))?[}]$', val)
    if not m:
        if n in lues and n not in IMPOSEES:
            figees.append(f"{n}={val}")
        continue
    defauts_compose[m.group(1)] = m.group(2) or ""
    if m.group(1) != n and DERIVEES.get(n) != m.group(1):
        mauvais_renvoi.append(f"{n} <- {m.group(1)}")
    if n in lues and m.group(2) and m.group(2) == defaut_du_code(n):
        repetes.append(f"{n}={m.group(2)}")
# Les ports publies et la roue vivent hors du bloc « environment: » ; leur
# defaut est ecrit dans le compose et nulle part ailleurs.
for nom, valeur in re.findall(r'[$][{]([A-Z][A-Z0-9_]*):-([^}]*)[}]', compose):
    defauts_compose.setdefault(nom, valeur)

dit(not mauvais_renvoi, "chaque ligne renvoie a SA variable",
    ", ".join(mauvais_renvoi) or "aucune faute de frappe")
dit(not figees, "aucune valeur figee sans raison ecrite",
    ", ".join(figees) or "toutes viennent de .env")

# Une valeur en dur dans le compose est bonne quand elle DIFFERE du defaut du
# code — c'est alors un choix propre au conteneur, et il se lit. Elle est un
# piege quand elle le REPETE : deux maitres pour un reglage, et le jour ou le
# code change, l'image garde l'ancien sans un mot.
dit(not repetes, "pas deux defauts pour un meme reglage dans le compose",
    ", ".join(repetes) or "un seul endroit chacun")

# Meme piege, deplace d'un fichier. .env.exemple est copie tel quel — une ligne
# ACTIVE qui recopie un defaut ecrit ailleurs le fige dans toutes les
# installations nees d'un « cp .env.exemple .env ».
#
# Le defaut peut vivre dans le CODE (STUDIO_LLM) ou dans le COMPOSE (ROUE,
# COMFY_PORT) : ne comparer qu'au code laissait trois lignes passer. Et Compose
# retire guillemets et commentaire de fin de ligne a la lecture : les comparer
# tels quels laissait passer « STUDIO_LLM="qwen2.5vl:7b" ».
recopies = []
for ligne in lire(".env.exemple").splitlines():
    m = re.match(r'^([A-Z][A-Z0-9_]*)=(.*)$', ligne.strip())
    if not m:
        continue
    val = re.sub(r'\s+#.*$', "", m.group(2)).strip().strip('"').strip("'")
    # Les DEUX defauts sont compares, pas le premier trouve : « or » sautait le
    # defaut du compose des que le code en avait un, et le repli ajoute par
    # 77fb1ef ne servait qu'aux reglages sans aucun defaut ecrit dans le code.
    attendus = {defaut_du_code(m.group(1)), defauts_compose.get(m.group(1))}
    if val and val in attendus:
        recopies.append(m.group(0))
dit(not recopies, "aucun defaut recopie en dur dans .env.exemple",
    ", ".join(recopies) or "aucune ligne active redondante")

# ══════════════════════════════════════════════════════════════════════
#  LE WORKFLOW LUI-MEME DOIT POUVOIR SE LIRE
# ══════════════════════════════════════════════════════════════════════
# LA PANNE DU 5 SEPTEMBRE 2026, ET SA FORME EST CE QUI COMPTE. Une etape nommee
# « La seance : sortir, changer de fil » — un deux-points suivi d'une espace
# dans un scalaire YAML non protege — a rendu le fichier illisible. La CI a
# rendu « failure » avec ZERO job et AUCUNE etape rouge : rien a lire dans le
# rapport, rien de rouge a corriger.
#
# ET L'AUTO-CONTROLE DU WORKFLOW — celui qui exige une etape par banc — VIT
# DANS LE WORKFLOW. Il ne peut rien dire d'un fichier qui ne s'analyse pas :
# une garde logee dans ce qu'elle garde ne garde rien. Le controle devait donc
# venir d'ailleurs, et un banc est le seul « ailleurs » du depot.
#
# LE MOTIF PLUTOT QU'UN ANALYSEUR YAML : PyYAML n'est pas une dependance de ce
# depot, et le studio doit demarrer sur un NAS sans pip. On ne verifie donc pas
# « le YAML est valide » mais la faute EXACTE qui s'est produite — celle qu'un
# titre francais appelle naturellement, parce qu'on ecrit « La seance :
# sortir » comme on parle.
print("\n  ── le workflow doit pouvoir se lire ──")
_wf = lire(os.path.join(".github", "workflows", "verification.yml"))
_titres = re.findall(r"^\s*- name:\s*(.+?)\s*$", _wf, re.M)
_casses = [n for n in _titres
           if ": " in n and not (n[:1] in "\"'" and n[-1:] == n[:1])]
dit(bool(_titres) and not _casses,
    "aucun nom d'etape ne porte un deux-points nu : YAML y lit une clef, et le "
    "fichier entier devient illisible",
    ", ".join(_casses) or f"{len(_titres)} etapes relues")

# LE TEMOIN : sans lui, le cas ci-dessus serait vrai d'un fichier vide, ou
# d'une expression reguliere qui aurait cesse de trouver quoi que ce soit.
dit(len(_titres) >= 20,
    "et le releve trouve bien les etapes : le cas ci-dessus n'est pas vrai de "
    "rien", f"{len(_titres)} etapes")

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
for r in rate:
    print("    a regarder :", r)
sys.exit(1 if rate else 0)
