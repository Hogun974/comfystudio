# -*- coding: utf-8 -*-
"""Ce que coute et ce que rapporte une garde de couverture.

La regle eprouvee : si moins de 58 % des traits de la demande sont connus du
classifieur, on ne le laisse plus trancher seul — la demande part au modele de
langage, qui est multilingue.

On compare trois politiques sur les memes 460 demandes :
  0. aujourd'hui                     — aucune garde
  1. garde de couverture             — le court-circuit exige 0.58
  2. garde + raccourcis ecrits sautes — la proposition d'origine, en plus
"""
import os
import sys

DEPOT = r"D:\ComfyStudio"
sys.path.insert(0, DEPOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import serveur                                          # noqa: E402
from aiguilleur import Aiguilleur, MODELE, MARGE_SURE   # noqa: E402
import banc_langues                                     # noqa: E402
from mesurer_detection import couverture                # noqa: E402

A = Aiguilleur.lire(MODELE)
CAS = banc_langues.FACILE + banc_langues.DUR
LANGUES = ["fr", "en", "de", "es"]
SEUIL = 0.58
EQUIV = {"retoucher_zone": "edition", "retoucher_fond": "edition",
         "retoucher_sujet": "edition", "detourer": "detourer",
         "agrandir": "agrandir", "fluidifier": "fluidifier",
         "lecture": "lecture"}


def tour(texte, attendu, garde_classifieur, garde_ecrit):
    """Rend ('appel', None) si la demande part au modele de langage, sinon
    ('tranche', juste)."""
    connu = couverture(texte) >= SEUIL
    if not (garde_ecrit and not connu):
        quoi = serveur.raccourci_ecrit(texte, "image", False, lambda: True)
        if quoi:
            return "tranche", EQUIV.get(quoi) == attendu
    if len(texte.strip()) <= 70:
        propose, marge = A.classer(texte)
        if propose in serveur.SANS_ECRITURE and marge >= MARGE_SURE \
                and not (serveur.veut_fluidifier(texte)
                         or serveur.veut_detourer(texte)
                         or serveur.veut_agrandir(texte)):
            if not (garde_classifieur and not connu):
                return "tranche", propose == attendu
    return "appel", None


def politique(nom, gc, ge):
    print(f"\n----- {nom} -----")
    print(f"{'langue':>7} {'tranche sans appel':>19} {'dont FAUX':>11} "
          f"{'appels au modele':>18}")
    tot_faux = tot_app = 0
    for i, lg in enumerate(LANGUES):
        tr = fx = ap = 0
        for c in CAS:
            quoi, juste = tour(c[1 + i], c[0], gc, ge)
            if quoi == "appel":
                ap += 1
            else:
                tr += 1
                fx += not juste
        if lg != "fr":
            tot_faux += fx
            tot_app += ap
        print(f"{lg:>7} {tr:>13}/{len(CAS):<4} {fx:>10} {ap:>15}/{len(CAS)}")
    print(f"  etranger (345 demandes) : {tot_faux} pannes silencieuses, "
          f"{tot_app} appels au modele")
    return tot_faux, tot_app


if __name__ == "__main__":
    print(f"{len(CAS)} cas par langue, seuil de couverture {SEUIL}")
    a = politique("0. aujourd'hui — aucune garde", False, False)
    b = politique("1. garde de couverture sur le court-circuit", True, False)
    c = politique("2. garde + raccourcis ecrits sautes", True, True)

    print("\n\n===== Bilan sur les 345 demandes etrangeres =====")
    print(f"{'politique':>46} {'pannes':>8} {'appels':>8} "
          f"{'secondes a chaud':>18}")
    for nom, (f, ap) in (("0. aujourd'hui", a),
                         ("1. garde de couverture", b),
                         ("2. garde + raccourcis sautes", c)):
        print(f"{nom:>46} {f:>8} {ap:>8} {ap * 1.6:>15.0f} s")
    print("\n  Ce que la politique 2 ajoute a la 1 : "
          f"{c[1] - b[1]} appels de plus "
          f"({(c[1] - b[1]) * 1.6:.0f} s a chaud), "
          f"{b[0] - c[0]} panne(s) de moins.")

    print("\n===== Et le francais ? =====")
    for nom, gc, ge in (("0. aujourd'hui", False, False),
                        ("1. garde", True, False),
                        ("2. garde + raccourcis sautes", True, True)):
        tr = fx = ap = 0
        for cas in CAS:
            quoi, juste = tour(cas[1], cas[0], gc, ge)
            if quoi == "appel":
                ap += 1
            else:
                tr += 1
                fx += not juste
        print(f"  {nom:>30} : {tr}/{len(CAS)} tranches sans appel "
              f"({fx} faux), {ap} appels")
