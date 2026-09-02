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
import io
import os
import re
import sys

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
FICHIERS = ["serveur.py"]
for mod in re.findall(r'(?m)^\s*(?:import|from)\s+([a-z_][a-z0-9_]*)', SRV):
    if os.path.exists(os.path.join(ICI, mod + ".py")) and mod + ".py" not in FICHIERS:
        FICHIERS.append(mod + ".py")
CODE = "\n".join(lire(f) for f in FICHIERS)

# Le COMPTE, et pas seulement le contenu. Le releve de variables ne protege pas
# le suivi : aucun des cinq modules importes ne lit d'environnement, les 25
# variables sont toutes dans serveur.py. Passer « import comptes as _comptes »
# en try/except, ou le remplacer par un import_module — deux nettoyages banals
# — faisait tomber le suivi a quatre fichiers, puis a un, sans changer un seul
# chiffre de la ligne qui les compte.
#
# CINQ, PUIS SIX le 2 septembre 2026 au soir : serveur.py importe desormais
# traductions.py. Ce chiffre se monte a chaque module ajoute, et il DOIT se
# monter — laisse a cinq, il rendait vraie la mutation « un module suivi
# charge par importlib » : le suivi tombait a cinq fichiers, le seuil etait
# atteint, et le filet ecrit exactement pour ce nettoyage-la passait au vert.
FICHIERS_SUIVIS = 6
dit(len(FICHIERS) >= FICHIERS_SUIVIS,
    f"les {len(FICHIERS)} fichiers du conteneur sont suivis",
    ", ".join(FICHIERS[1:]) or "aucun module importe")

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


def defaut_du_code(n):
    """La valeur LITTERALE que le code retient quand la variable est absente.

    Rend None des que le defaut est calcule : on ne sait pas l'evaluer, et
    pretendre le contraire est ce qui rendait les deux pieges invisibles.
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

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
for r in rate:
    print("    a regarder :", r)
sys.exit(1 if rate else 0)
