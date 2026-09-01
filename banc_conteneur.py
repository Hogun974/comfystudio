# -*- coding: utf-8 -*-
"""Une variable posee dans .env atteint-elle vraiment le studio ?

    python banc_conteneur.py

Compose ne transmet QUE ce qu'il nomme. Une variable posee dans .env et absente
du bloc « environment: » est lue hors conteneur et ignoree dedans, sans un mot
— et le studio du reseau tourne en conteneur. Dix reglages etaient dans ce cas
pendant que la documentation les donnait pour reconnus.

La premiere version de ce banc laissait passer trois choses, et une relecture
adverse les a demontrees une par une. Elles sont fermees ici, chacune par une
verification qui echoue sur la mutation correspondante :

  - OLLAMA_URL etait invisible : le releve ne regardait que STUDIO_ et COMFY_.
    On pouvait la retirer du compose ET du Dockerfile, le banc restait vert.
    C'est la variable la plus importante d'un studio en conteneur.
  - une ligne « ENV » du Dockerfile suffisait a rendre une variable « arrivee ».
    Elle arrive, en effet — avec la valeur de l'image, et .env reste lettre
    morte. C'est exactement le degat qu'on veut interdire, pas son contraire.
  - seule la clef etait lue. « STUDIO_ANALYSE_MAX: "${STUDIO_ANALYSE_MAXX:-}" »
    passait : la clef est bien relayee, sa valeur est vide pour toujours.

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

# Relayees par une AUTRE variable, volontairement. Le nom de gauche et celui de
# droite different, et c'est le sujet.
DERIVEES = {
    "STUDIO_PORT_HOTE": "le studio doit annoncer le port de l'HOTE, qui est "
                        "STUDIO_PORT — sans quoi la banniere envoie sur 8199, "
                        "et sur une machine qui heberge deja un studio, cette "
                        "adresse repond : c'est le studio d'a cote",
}


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


def lire(nom):
    return io.open(os.path.join(ICI, nom), encoding="utf-8").read()


SRV = lire("serveur.py")

# AUCUN prefixe. Le filtre « STUDIO_|COMFY_ » de la premiere version rendait
# OLLAMA_URL invisible — et c'est celle sans laquelle le studio ne pense plus.
lues = set(re.findall(r'os[.]environ[.]get[(]\s*"([A-Z][A-Z0-9_]*)"', SRV))
lues |= set(re.findall(r'os[.]environ\[\s*"([A-Z][A-Z0-9_]*)"', SRV))
dit(len(lues) >= 25 and "OLLAMA_URL" in lues,
    f"{len(lues)} variables relevees dans serveur.py, sans filtre de nom",
    "OLLAMA_URL comprise")

compose = lire("docker-compose.yml")
# Uniquement le service du studio : les conteneurs voisins ont les leurs.
bloc = compose.split("comfystudio:", 1)[1].split("\n  # ", 1)[0]
# Valeur quotee OU NON : « STUDIO_ADMIN: jeton-en-dur » sans guillemets
# echappait a la verification des valeurs figees.
lignes = dict(re.findall(r'^\s{6}([A-Z][A-Z0-9_]*):\s*(.*?)\s*$', bloc, re.M))
relayees = set(lignes)

# Le Dockerfile n'est PAS une facon d'arriver au conteneur : c'est une facon de
# n'en jamais repartir. Une variable qu'il pose et que le compose ne relaie pas
# est figee dans l'image — ce que .env en dit n'a plus aucun effet.
posees = set(re.findall(r'^ENV\s+([A-Z][A-Z0-9_]*)=', lire("Dockerfile"), re.M))
posees |= set(re.findall(r'^\s+([A-Z][A-Z0-9_]*)=', lire("Dockerfile"), re.M))

oubliees = sorted(lues - relayees - set(IMPOSEES))
dit(not oubliees, "tout ce qui est lu arrive au conteneur par le compose",
    ", ".join(oubliees) or "aucun oubli")

muettes = sorted((posees & lues) - relayees - set(IMPOSEES))
dit(not muettes, "aucune variable figee par l'image sans raison ecrite",
    ", ".join(muettes) or "aucune")

mortes = sorted((set(IMPOSEES) | set(DERIVEES)) - lues)
dit(not mortes, "aucune exception perimee", ", ".join(mortes) or "aucune")

inutiles = sorted(n for n in IMPOSEES
                  if n in relayees and lignes[n].startswith('"${'))
dit(not inutiles, "aucune exception inutile",
    ", ".join(inutiles) or "chacune sert encore")


def defaut_du_code(n):
    """La valeur que serveur.py retient quand la variable est absente."""
    m = re.search(r'os[.]environ[.]get[(]\s*"' + n + r'"\s*,\s*"([^"]*)"', SRV)
    if m:
        return m.group(1)
    m = re.search(r'os[.]environ[.]get[(]\s*"' + n + r'"\s*[)]\s*or\s+"?([^\s")]+)',
                  SRV)
    return m.group(1) if m else None


# Le cote DROIT de la ligne, celui que la premiere version ne lisait pas.
mauvais_renvoi, figees, repetes = [], [], []
for n in sorted(relayees & lues):
    val = lignes[n].strip('"')
    m = re.match(r'^[$][{]([A-Z][A-Z0-9_]*)(?::-(.*))?[}]$', val)
    if not m:
        if n not in IMPOSEES:
            figees.append(f"{n}={val}")
        continue
    if m.group(1) != n and n not in DERIVEES:
        mauvais_renvoi.append(f"{n} <- {m.group(1)}")
    if m.group(2) and m.group(2) == defaut_du_code(n):
        repetes.append(f"{n}={m.group(2)}")

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
# ACTIVE qui recopie le defaut du code le fige dans toutes les installations
# nees d'un « cp .env.exemple .env ».
recopies = []
for ligne in lire(".env.exemple").splitlines():
    m = re.match(r'^([A-Z][A-Z0-9_]*)=(.*)$', ligne.strip())
    if m and m.group(1) in lues and m.group(2) \
            and m.group(2) == defaut_du_code(m.group(1)):
        recopies.append(m.group(0))
dit(not recopies, "aucun defaut du code recopie en dur dans .env.exemple",
    ", ".join(recopies) or "aucune ligne active redondante")

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
for r in rate:
    print("    a regarder :", r)
sys.exit(1 if rate else 0)
