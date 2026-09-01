# -*- coding: utf-8 -*-
"""Le catalogue promet-il ce qu'il va vraiment telecharger ?

    python banc_catalogue.py

L'installeur annonce « ~N Go a prendre » avant de lancer un telechargement de
plusieurs dizaines de minutes. Ce chiffre est la seule chose sur laquelle
quelqu'un decide, et il se fabrique par une somme : un fichier absent de la
table des tailles y compte pour ZERO, en silence.

C'est arrive. « fluidifier » annonçait « ~0 Go a prendre » — la taille de
film_net n'avait jamais ete relevee. Un plancher presente comme un total est
une promesse qu'on ne tient pas, et celle-la se lisait « c'est gratuit ».

Ce banc refuse desormais qu'un fichier requis n'ait pas de taille, sauf a etre
NOMME dans catalogue.SANS_TAILLE avec sa raison. Il verifie aussi les deux
sens : une exception qui ne correspond plus a rien se retire, sinon elle
couvrira un jour un fichier neuf portant le meme nom.

Statique, sans reseau : il entre dans la CI. Ce qu'il ne peut pas savoir, c'est
si une taille RELEVEE est juste — seul un telechargement le dirait.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import catalogue as C  # noqa: E402

ok, rate = [], []


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


REQUIS = C.fichiers_requis(C.CATALOGUE)
dit(len(REQUIS) >= 20, f"{len(REQUIS)} fichiers a telecharger dans le catalogue",
    f"{len(C.CATALOGUE)} moteurs")

sans = sorted(f"{s}/{n}" for s, n in REQUIS - set(C.TAILLES) - set(C.SANS_TAILLE))
dit(not sans, "chaque fichier requis a une taille, ou une raison de ne pas en avoir",
    ", ".join(sans) or "aucun trou muet")

mortes = sorted(f"{s}/{n}" for s, n in set(C.SANS_TAILLE) - REQUIS)
dit(not mortes, "aucune exception perimee dans SANS_TAILLE",
    ", ".join(mortes) or "aucune")

muettes = [f"{s}/{n}" for (s, n), pourquoi in C.SANS_TAILLE.items()
           if not (pourquoi or "").strip()]
dit(not muettes, "chaque exception dit POURQUOI la taille manque",
    ", ".join(muettes) or "toutes")

# Une taille relevee a zero ne se distingue pas d'une taille absente, et c'est
# le defaut d'origine sous une autre forme.
nulles = sorted(f"{s}/{n}" for (s, n), go in C.TAILLES.items() if not go)
dit(not nulles, "aucune taille relevee a zero", ", ".join(nulles) or "aucune")

# Une taille pour un fichier que plus personne ne telecharge est du poids mort
# qui fausse les sommes le jour ou un moteur reprend ce nom.
orphelines = sorted(f"{s}/{n}" for s, n in set(C.TAILLES) - REQUIS)
dit(not orphelines, "aucune taille orpheline", ", ".join(orphelines) or "aucune")

# Le drapeau doit dire vrai dans les deux sens : c'est lui qui fait ecrire
# « au moins » au lieu de « ~ » dans l'installeur.
faux = [c for c in C.CATALOGUE
        if C.poids_incertain([c])
        != bool(C.fichiers_requis([c]) & set(C.SANS_TAILLE))]
dit(not faux, "poids_incertain dit vrai pour chaque moteur", ", ".join(faux) or "les 20")

# L'union et non la somme : deux moteurs partagent des fichiers, et les
# additionner surestimerait le telechargement — c'est la raison d'etre de
# poids(), et rien ne la verifiait.
paires = [(a, b) for a in C.CATALOGUE for b in C.CATALOGUE
          if a < b and (C.fichiers_requis([a]) & C.fichiers_requis([b]))]
dit(bool(paires), f"{len(paires)} paires de moteurs partagent des fichiers",
    "l'union a donc un sens")
if paires:
    # LA PAIRE QUI PARTAGE LE PLUS, et une inegalite STRICTE. « < somme + 0,05 »
    # etait inerte : une somme naive vaut exactement la somme, donc la
    # verification passait aussi sans l'union. Et une paire au recouvrement
    # negligeable ne prouve rien non plus.
    a, b = max(paires, key=lambda p: sum(
        C.TAILLES.get(f, 0.0)
        for f in C.fichiers_requis([p[0]]) & C.fichiers_requis([p[1]])))
    ensemble, separes = C.poids([a, b]), C.poids([a]) + C.poids([b])
    dit(ensemble < separes - 0.5, f"et poids() les compte une seule fois — {a} + {b}",
        f"{ensemble} Go ensemble contre {separes:.1f} additionnes")

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
for r in rate:
    print("    a regarder :", r)
sys.exit(1 if rate else 0)
