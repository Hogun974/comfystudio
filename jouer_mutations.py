# -*- coding: utf-8 -*-
"""Joue UNE liste de mutations de banc_mutations.py, ou quelques-unes par leur
nom, sans lancer le banc complet — qui prend vingt minutes.

    python jouer_mutations.py LISTE [nom-de-mutation ...]

LISTE est le nom d'une des listes du fichier (CONSOLE, FICHIERS, SECURITE_SEPT…).
Sans nom : toutes les mutations de la liste. Le depot n'est jamais touche :
verdict() travaille dans un dossier temporaire, comme le lanceur complet.

Ni la CI ni le lanceur complet ne s'en servent : c'est l'outil de qui ECRIT une
mutation et veut la voir rougir tout de suite, avant de payer le tour complet.
Le prelude de banc_mutations.py — tout ce qui precede « depart = time.time() »,
donc les listes et verdict() — est execute tel quel ; on ne recopie rien.
"""
import io
import os
import shutil
import sys
import tempfile

ICI = os.path.dirname(os.path.abspath(__file__))
CHEMIN = os.path.join(ICI, "banc_mutations.py")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    with io.open(CHEMIN, encoding="utf-8", newline=None) as f:
        texte = f.read()
    prelude = texte.split("\ndepart = time.time()", 1)[0]
    espace = {"__file__": CHEMIN, "__name__": "banc_mutations_prelude"}
    exec(compile(prelude, CHEMIN, "exec"), espace)
    liste = espace.get(argv[1])
    if not isinstance(liste, list):
        print(f"  liste inconnue : {argv[1]}")
        return 2
    voulus = argv[2:]
    choisies = [m for m in liste if not voulus or m["nom"] in voulus]
    if voulus and len(choisies) != len(voulus):
        absents = sorted(set(voulus) - {m["nom"] for m in choisies})
        print(f"  mutation(s) introuvable(s) dans {argv[1]} : {', '.join(absents)}")
        return 2
    racine = tempfile.mkdtemp(prefix="jouer_mutations_")
    verdict = espace["verdict"]
    rouges = 0
    try:
        for mut in choisies:
            etat, detail = verdict(mut, racine)
            rouges += etat == "rouge"
            print(f"  {'ok ' if etat == 'rouge' else 'NON'}  [{etat}] {mut['banc']} / "
                  f"{mut['nom']}{' — ' + detail if detail else ''}", flush=True)
    finally:
        shutil.rmtree(racine, ignore_errors=True)
    print(f"\n  {rouges} rouges sur {len(choisies)}")
    return 0 if rouges == len(choisies) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
