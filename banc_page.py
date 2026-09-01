# -*- coding: utf-8 -*-
"""La feuille de style et le script de la page se contredisent-ils ?

    python banc_page.py

web/index.html porte le HTML, le CSS et le JS dans un seul fichier. Rien ne
relit l'ensemble : une regle peut y dormir sans element, deux classes peuvent
porter le meme nom pour deux choses differentes, et une table peut nommer un
menu qui n'existe pas. Aucun de ces trois defauts ne leve d'erreur — la page
s'affiche, simplement pas comme on croit.

Les trois sont arrives :

  - « .puce.moteur » colorait une pastille du nom de « .moteur », le panneau
    des machines de la colonne de gauche. Un element portant les deux classes
    heritait de « display:flex ; flex-direction:column » et des regles
    descendantes du panneau. La regle n'etait posee sur rien, ce qui l'a rendue
    invisible pendant des mois — et l'aurait rendue redoutable le jour ou
    quelqu'un s'en serait servi.
  - MENU_REGLAGE et CLE_REGLAGE sont deux tables inverses l'une de l'autre,
    ecrites a la main a deux cents lignes d'ecart. Une seule qui derive, et un
    reglage cesse d'etre retenu sans que rien ne le dise : c'est exactement le
    defaut que l'utilisateur a signale le 31 aout.

Statique, sans reseau, sans studio : ce banc entre dans la CI. Ce qu'il ne peut
PAS voir — un rendu, une largeur, un debordement — reste le travail de
recette_chemin_page.py et de l'oeil.
"""
import io
import os
import re
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
PAGE = io.open(os.path.join(ICI, "web", "index.html"), encoding="utf-8").read()
ok, rate = [], []


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


# Le CSS s'arrete au premier </style> : au-dela, « .puce » dans une chaine de
# caracteres n'est plus une regle.
# Les commentaires sont RETIRES : ils parlent des regles, et ce banc a commence
# par se signaler lui-meme, en lisant « .puce.moteur » dans le commentaire qui
# explique justement pourquoi la regle n'existe plus.
CSS = re.sub(r'/\*.*?\*/', "", PAGE.split("</style>", 1)[0], flags=re.S)

seules = set(re.findall(r'(?m)^\.([a-z][a-z0-9-]*)\s*[{,]', CSS))
modifs = set(re.findall(r'\.puce\.([a-z][a-z0-9-]*)', CSS))

collisions = sorted(modifs & seules)
dit(not collisions,
    "aucune pastille ne porte le nom d'une classe de mise en page",
    ", ".join(f".puce.{c} contre .{c}" for c in collisions) or "aucun doublon")

# Une pastille se pose dans une chaine du script : « class="puce cours" », mais
# aussi « class="puce devis${depasse ? " depasse" : ""}" ». Plutot que de
# pretendre analyser du JavaScript, on prend les lignes qui parlent de pastilles
# et l'on y cherche les noms connus. Grossier, et suffisant : ce qu'on veut
# savoir, c'est si un nom apparait quelque part hors de la feuille.
CORPS = PAGE.split("</style>", 1)[1]
posees = set()
for ligne in CORPS.splitlines():
    if "puce" not in ligne:
        continue
    posees |= modifs & set(re.findall(r'[a-z][a-z0-9-]*', ligne))

dormantes = sorted(modifs - posees)
dit(not dormantes, "aucune pastille decrite sans etre jamais posee",
    ", ".join(f".puce.{d}" for d in dormantes) or "toutes servent")

# Les deux tables des reglages, inverses l'une de l'autre, ecrites a deux cents
# lignes d'ecart. C'est la derive de l'une des deux qui a tue les reglages par
# conversation le 31 aout.
menu = dict(re.findall(r'(\w+):\s*"(#\w+)"',
                       PAGE.split("const MENU_REGLAGE = {", 1)[1].split("};", 1)[0]))
cle = dict(re.findall(r'"(#\w+)":\s*"(\w+)"',
                      PAGE.split("const CLE_REGLAGE = {", 1)[1].split("};", 1)[0]))
dit(menu and cle and {v: k for k, v in menu.items()} == cle,
    "MENU_REGLAGE et CLE_REGLAGE disent la meme chose",
    f"{len(menu)} contre {len(cle)}")

manquants = sorted(sel for sel in menu.values()
                   if not re.search(r'id="' + sel[1:] + r'"', PAGE))
dit(not manquants, "chaque reglage nomme un menu qui existe dans la page",
    ", ".join(manquants) or f"{len(menu)} menus trouves")

# « priorite » a vecu des mois dans le corps de /api/generer alors que les trois
# autres reglages avaient demenage sur la conversation. Un second onglet reste
# ouvert effaçait donc le cran du premier au simple envoi d'un message.
envois = re.findall(r'fetch\("/api/generer"[^;]*?\}\);', PAGE, re.S)
dit(len(envois) >= 2, f"{len(envois)} envois vers /api/generer reperes")
fautifs = [e for e in envois if re.search(r'priorite:\s*\$\("#priorite"\)', e)]
dit(not fautifs, "aucun envoi ne renvoie le cran de priorite du menu",
    f"{len(fautifs)} envoi(s) fautif(s)" if fautifs else "il vit sur la conversation")

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
for r in rate:
    print("    a regarder :", r)
sys.exit(1 if rate else 0)
