# -*- coding: utf-8 -*-
"""Les DEUX chemins qui tranchent sans appeler le modele de langage.

A. raccourci_ecrit()  — expressions regulieres francaises, aucune marge,
   aucun garde-fou. Ce qu'elle rate part au modele ; ce qu'elle attrape a tort
   est execute tel quel.
B. le court-circuit du classifieur dans aiguiller() — seulement pour
   SANS_ECRITURE (agrandir, detourer, fluidifier), marge >= MARGE_SURE,
   demande courte (<= 70), sans image jointe, avec une sortie precedente.

On mesure sur les memes cas, en quatre langues.
"""
import os
import sys

DEPOT = r"D:\ComfyStudio"
sys.path.insert(0, DEPOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import serveur                                          # noqa: E402
from aiguilleur import Aiguilleur, MODELE, MARGE_SURE   # noqa: E402
import banc_langues                                     # noqa: E402

A = Aiguilleur.lire(MODELE)
LANGUES = ["fr", "en", "de", "es"]
# raccourci_ecrit rend des noms de MODELE ; le banc porte des INTENTIONS.
EQUIV = {"retoucher_zone": "edition", "retoucher_fond": "edition",
         "retoucher_sujet": "edition", "detourer": "detourer",
         "agrandir": "agrandir", "fluidifier": "fluidifier",
         "lecture": "lecture"}

CAS = banc_langues.FACILE + banc_langues.DUR


def chemin_a(i):
    """raccourci_ecrit avec une image jointe : le cas le plus courant."""
    attrape = justes = faux = 0
    faux_detail = []
    for c in CAS:
        attendu, texte = c[0], c[1 + i]
        # zone_servie=lambda: True — SAM 3.1 present. On mesure la regle,
        # pas les modeles telecharges sur cette machine.
        quoi = serveur.raccourci_ecrit(texte, "image", False, lambda: True)
        if not quoi:
            continue
        attrape += 1
        if EQUIV.get(quoi) == attendu:
            justes += 1
        else:
            faux += 1
            faux_detail.append((texte, attendu, quoi))
    return attrape, justes, faux, faux_detail


def chemin_b(i):
    """Le court-circuit du classifieur, aux conditions exactes d'aiguiller()."""
    tire = justes = faux = 0
    faux_detail = []
    for c in CAS:
        attendu, texte = c[0], c[1 + i]
        if len(texte.strip()) > 70:          # « court »
            continue
        propose, marge = A.classer(texte)
        if propose not in serveur.SANS_ECRITURE or marge < MARGE_SURE:
            continue
        if (serveur.veut_fluidifier(texte) or serveur.veut_detourer(texte)
                or serveur.veut_agrandir(texte)):
            continue                          # l'ecrit confirme, pas une devinette
        tire += 1
        if propose == attendu:
            justes += 1
        else:
            faux += 1
            faux_detail.append((texte, attendu, propose, marge))
    return tire, justes, faux, faux_detail


if __name__ == "__main__":
    print(f"{len(CAS)} cas par langue "
          f"({len(banc_langues.FACILE)} faciles + {len(banc_langues.DUR)} durs)")

    print("\n===== A. raccourci_ecrit() — expressions regulieres, image jointe =====")
    print(f"{'langue':>7} {'attrape':>9} {'justes':>8} {'FAUX (silencieux)':>19}")
    a = {}
    for i, lg in enumerate(LANGUES):
        n, j, f, d = chemin_a(i)
        a[lg] = (n, j, f, d)
        print(f"{lg:>7} {n:>6}/{len(CAS):<3} {j:>7} {f:>15}")

    print("\n===== B. court-circuit du classifieur (agrandir/detourer/fluidifier) =====")
    print(f"{'langue':>7} {'tire':>7} {'justes':>8} {'FAUX (silencieux)':>19}")
    b = {}
    for i, lg in enumerate(LANGUES):
        n, j, f, d = chemin_b(i)
        b[lg] = (n, j, f, d)
        print(f"{lg:>7} {n:>6} {j:>8} {f:>15}")

    print("\n===== Les faux du chemin B, un a un =====")
    for lg in LANGUES:
        for texte, attendu, propose, marge in b[lg][3]:
            print(f"  {lg} [{attendu:>11} -> {propose:<10} marge {marge:4.1f}] {texte[:70]}")

    print("\n===== Les faux du chemin A, un a un =====")
    for lg in LANGUES:
        for texte, attendu, quoi in a[lg][3]:
            print(f"  {lg} [{attendu:>11} -> {quoi:<15}] {texte[:70]}")

    print("\n===== Le repli propose : sauter les raccourcis si non francais =====")
    tot_a = sum(a[lg][0] for lg in ("en", "de", "es"))
    jus_a = sum(a[lg][1] for lg in ("en", "de", "es"))
    tot_b = sum(b[lg][0] for lg in ("en", "de", "es"))
    jus_b = sum(b[lg][1] for lg in ("en", "de", "es"))
    print(f"  Ce qu'on PERD (raccourcis justes, donc appels epargnes) : "
          f"A {jus_a} + B {jus_b} = {jus_a + jus_b} sur {3 * len(CAS)} demandes")
    print(f"  Ce qu'on GAGNE (raccourcis faux, donc pannes evitees)  : "
          f"A {tot_a - jus_a} + B {tot_b - jus_b} = "
          f"{tot_a - jus_a + tot_b - jus_b} sur {3 * len(CAS)} demandes")
    print(f"  En francais, ce meme repli couterait : A {a['fr'][0]} + "
          f"B {b['fr'][0]} = {a['fr'][0] + b['fr'][0]} raccourcis "
          f"(dont {a['fr'][2] + b['fr'][2]} faux) sur {len(CAS)}")
