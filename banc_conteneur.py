# -*- coding: utf-8 -*-
"""Une variable lue par le studio arrive-t-elle jusqu'au conteneur ?

    python banc_conteneur.py

Compose ne transmet QUE ce qu'il nomme. Une variable posee dans .env et absente
du bloc « environment: » est lue hors conteneur et ignoree dedans, sans un mot
— et le studio du reseau tourne en conteneur. Neuf reglages etaient dans ce cas
pendant que la documentation les donnait pour reconnus.

Ce banc relit serveur.py, releve tout ce qu'il consulte, et exige que chaque nom
soit relaye par le compose ou pose par l'image. Les exceptions sont nommees ici,
avec leur raison : c'est le seul endroit ou l'on peut en ajouter une, et il faut
l'ecrire.
"""
import io
import os
import re
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
ok, rate = [], []

# Deliberement NON relayees. Une exception sans raison est un oubli.
EXPRES = {
    "STUDIO_PORT": "le conteneur ecoute toujours sur 8199 ; c'est le compose "
                   "qui publie ailleurs, et STUDIO_PORT_HOTE le lui dit",
}

# Relayees mais NON reglables : l'image impose la valeur, .env n'y peut rien.
IMPOSEES = {
    "STUDIO_HOTE": "127.0.0.1 dans un conteneur ne repond a personne : le port "
                   "publie tomberait dans le vide",
}


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


def lire(nom):
    return io.open(os.path.join(ICI, nom), encoding="utf-8").read()


SRV = lire("serveur.py")
lues = set(re.findall(r'os[.]environ[.]get[(]\s*"((?:STUDIO|COMFY)_[A-Z_]+)"', SRV))
dit(len(lues) >= 15, f"{len(lues)} variables relevees dans serveur.py")

compose = lire("docker-compose.yml")
# Uniquement le service du studio : les conteneurs voisins ont les leurs.
bloc = compose.split("comfystudio:", 1)[1].split("\n  # ", 1)[0]
relayees = set(re.findall(r'^\s{6}((?:STUDIO|COMFY)_[A-Z_]+):', bloc, re.M))
posees = set(re.findall(r'((?:STUDIO|COMFY)_[A-Z_]+)=', lire("Dockerfile")))

oubliees = sorted(lues - relayees - posees - set(EXPRES))
dit(not oubliees, "tout ce qui est lu arrive au conteneur",
    ", ".join(oubliees) or "aucun oubli")

# Une exception qui n'existe plus se retire : sinon elle couvre un jour une
# variable neuve portant le meme nom.
mortes = sorted((set(EXPRES) | set(IMPOSEES)) - lues)
dit(not mortes, "aucune exception perimee", ", ".join(mortes) or "aucune")


def defaut_du_code(n):
    """La valeur que serveur.py retient quand la variable est absente."""
    m = re.search(r'os[.]environ[.]get[(]\s*"' + n + r'"\s*,\s*"([^"]*)"', SRV)
    if m:
        return m.group(1)
    m = re.search(r'os[.]environ[.]get[(]\s*"' + n + r'"\s*[)]\s*or\s+"?([^\s")]+)',
                  SRV)
    return m.group(1) if m else None


# Une valeur en dur dans le compose est bonne quand elle DIFFERE du defaut du
# code — c'est alors un choix propre au conteneur, et il se lit. Elle est un
# piege quand elle le REPETE : deux maitres pour un reglage, et le jour ou le
# code change, l'image garde l'ancien sans un mot.
repetes, figees = [], []
for n in sorted(relayees & lues):
    m = re.search(r'^\s{6}' + n + r': "([^"]*)"', bloc, re.M)
    if not m:
        continue
    val = m.group(1)
    if not val.startswith("${"):
        if n not in IMPOSEES:
            figees.append(n)
        continue
    d = re.match(r'^[$][{]' + n + r':-(.*)[}]$', val)
    if d and d.group(1) and d.group(1) == defaut_du_code(n):
        repetes.append(f"{n}={d.group(1)}")

dit(not figees, "aucune valeur figee sans raison ecrite",
    ", ".join(figees) or "toutes viennent de .env")
dit(not repetes, "pas deux defauts pour un meme reglage",
    ", ".join(repetes) or "un seul endroit chacun")

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
for r in rate:
    print("    a regarder :", r)
sys.exit(1 if rate else 0)
