# -*- coding: utf-8 -*-
"""Que fait l'aiguilleur d'une demande qui n'est pas en francais ?

Trois chiffres par langue, et c'est le troisieme qui compte :
  - justes      : le classifieur a-t-il raison ;
  - d'office    : combien tranche-t-il seul (marge >= MARGE_SURE) ;
  - PANNES      : tranche d'office ET faux. C'est la panne silencieuse :
                  l'utilisateur recoit quelque chose, jamais ce qu'il voulait,
                  et rien ne le lui dit.
"""
import json
import os
import sys

DEPOT = r"D:\ComfyStudio"
sys.path.insert(0, DEPOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aiguilleur import Aiguilleur, MODELE, MARGE_SURE  # noqa: E402
import banc_langues                                    # noqa: E402

A = Aiguilleur.lire(MODELE)
LANGUES = ["fr", "en", "de", "es"]


def mesurer(cas, i):
    """cas = liste de (intention, fr, en, de, es). i = index de la langue."""
    bons = surs = bons_surs = pannes = 0
    detail = []
    for c in cas:
        attendu, texte = c[0], c[1 + i]
        propose, marge = A.classer(texte)
        sur = marge >= MARGE_SURE
        juste = propose == attendu
        bons += juste
        surs += sur
        bons_surs += juste and sur
        if sur and not juste:
            pannes += 1
            detail.append((texte, attendu, propose, marge))
    return bons, len(cas), bons_surs, surs, pannes, detail


def bloc(nom, cas):
    print(f"\n===== {nom} — {len(cas)} cas =====")
    print(f"{'langue':>7} {'justes':>12} {'tranches':>10} "
          f"{'justesse d office':>19} {'PANNES SILENCIEUSES':>21}")
    tout = {}
    for i, lg in enumerate(LANGUES):
        b, n, bs, s, p, d = mesurer(cas, i)
        tout[lg] = (b, n, bs, s, p, d)
        print(f"{lg:>7} {b:>5}/{n:<6} {s:>5}/{n:<4} "
              f"{bs:>10}/{s:<8} {p:>15} ({p * 100 / n:.0f} % des cas)")
    return tout


if __name__ == "__main__":
    f = bloc("banc_aiguillage (facile, verbes explicites)", banc_langues.FACILE)
    d = bloc("banc_neuf (dur, tournures indirectes)", banc_langues.DUR)

    print("\n\n===== Les pannes silencieuses, une a une =====")
    for nom, tout in (("FACILE", f), ("DUR", d)):
        for lg in ("en", "de", "es"):
            det = tout[lg][5]
            if not det:
                continue
            print(f"\n-- {nom} / {lg} : {len(det)} --")
            for texte, attendu, propose, marge in det:
                print(f"   [{attendu:>11} -> {propose:<11} marge {marge:5.1f}] {texte[:78]}")

    print("\n\n===== Ou part une demande etrangere quand elle est fausse =====")
    import collections
    for lg in ("en", "de", "es"):
        c = collections.Counter()
        for cas in (banc_langues.FACILE, banc_langues.DUR):
            i = LANGUES.index(lg)
            for x in cas:
                p, m = A.classer(x[1 + i])
                if p != x[0]:
                    c[p] += 1
        print(f"  {lg} : {dict(c.most_common())}")
