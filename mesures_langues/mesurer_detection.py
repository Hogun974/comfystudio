# -*- coding: utf-8 -*-
"""Combien coute-t-il de savoir que la demande n'est pas en francais ?

Trois candidats, tous en Python pur, tous sans dependance :

  1. COUVERTURE — la part des traits de la phrase que le classifieur connait
     deja. Aucune donnee nouvelle : le vocabulaire est dans aiguilleur.json.
  2. MOTS-OUTILS — les mots grammaticaux francais (le, la, de, une, sur, avec).
     Une liste de cinquante mots, ecrite a la main.
  3. Les deux ensemble.

On cherche un seuil qui separe le francais du reste, et on mesure ce qu'il
coute : combien de demandes FRANCAISES seraient prises pour de l'etranger.
"""
import os
import re
import sys
import time

DEPOT = r"D:\ComfyStudio"
sys.path.insert(0, DEPOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aiguilleur import Aiguilleur, MODELE, traits  # noqa: E402
import banc_langues                                # noqa: E402

A = Aiguilleur.lire(MODELE)
VOC = set()
for sac in A.poids.values():
    VOC |= set(sac)

CAS = banc_langues.FACILE + banc_langues.DUR
LANGUES = ["fr", "en", "de", "es"]

# Les mots grammaticaux francais. Ils ne portent aucun sens et c'est justement
# pour cela qu'ils marchent : ils sont les plus frequents de la langue, et
# aucune autre langue ne les partage tous.
_OUTILS = set("""le la les un une des du de d au aux et ou ni mais donc car
je tu il elle on nous vous ils elles me te se moi toi lui leur y en
ce cet cette ces cela ca celui celle qui que quoi dont ou
mon ma mes ton ta tes son sa ses notre votre leurs
est sont etre suis es sommes etes ai as avons avez ont avait etait
pour avec sans sur sous dans par vers chez entre depuis pendant
plus moins tres trop peu bien tout toute tous toutes meme aussi
ne pas plus jamais rien
peux peut pourrais saurais voudrais faudrait aimerais veux faut
stp svp merci""".split())
_MOT = re.compile(r"[a-z0-9]+")


def couverture(t):
    ts = traits(t)
    if not ts:
        return 0.0
    return sum(1 for x in ts if x in VOC) / len(ts)


def part_outils(t):
    import unicodedata
    nu = "".join(c for c in unicodedata.normalize("NFD", (t or "").lower())
                 if unicodedata.category(c) != "Mn")
    mots = _MOT.findall(nu)
    if not mots:
        return 0.0
    return sum(1 for m in mots if m in _OUTILS) / len(mots)


if __name__ == "__main__":
    print(f"vocabulaire du classifieur : {len(VOC)} traits\n")

    print("===== 1. COUVERTURE (part des traits deja connus) =====")
    print(f"{'langue':>7} {'moyenne':>9} {'min':>7} {'max':>7} "
          f"{'sous 0.55':>11} {'sous 0.65':>11}")
    vals = {}
    for i, lg in enumerate(LANGUES):
        v = [couverture(c[1 + i]) for c in CAS]
        vals[lg] = v
        print(f"{lg:>7} {sum(v) / len(v):>9.2f} {min(v):>7.2f} {max(v):>7.2f} "
              f"{sum(1 for x in v if x < 0.55):>8}/{len(v):<3}"
              f"{sum(1 for x in v if x < 0.65):>8}/{len(v):<3}")

    print("\n===== 2. MOTS-OUTILS francais (part des mots de la phrase) =====")
    print(f"{'langue':>7} {'moyenne':>9} {'>= 0.10':>9} {'>= 0.15':>9} {'>= 0.20':>9}")
    outils = {}
    for i, lg in enumerate(LANGUES):
        v = [part_outils(c[1 + i]) for c in CAS]
        outils[lg] = v
        print(f"{lg:>7} {sum(v) / len(v):>9.2f} "
              f"{sum(1 for x in v if x >= 0.10):>6}/{len(v):<3}"
              f"{sum(1 for x in v if x >= 0.15):>6}/{len(v):<3}"
              f"{sum(1 for x in v if x >= 0.20):>6}/{len(v):<3}")

    print("\n===== 3. Le meilleur seuil de chaque candidat =====")
    for nom, table, sens in (("couverture", vals, "<"),
                             ("mots-outils", outils, ">=")):
        best = None
        bornes = [x / 100 for x in range(1, 100)]
        for s in bornes:
            if sens == "<":
                fr_ok = sum(1 for x in table["fr"] if x >= s)      # garde le fr
                etr_pris = sum(sum(1 for x in table[l] if x < s)
                               for l in ("en", "de", "es"))
            else:
                fr_ok = sum(1 for x in table["fr"] if x >= s)
                etr_pris = sum(sum(1 for x in table[l] if x < s)
                               for l in ("en", "de", "es"))
            # On veut garder tout le francais et attraper tout le reste.
            score = fr_ok / len(CAS) + etr_pris / (3 * len(CAS))
            if best is None or score > best[0]:
                best = (score, s, fr_ok, etr_pris)
        _, s, fr_ok, etr = best
        print(f"  {nom:>12} seuil {s:.2f} : "
              f"francais garde {fr_ok}/{len(CAS)} ({fr_ok * 100 / len(CAS):.0f} %), "
              f"etranger reconnu {etr}/{3 * len(CAS)} "
              f"({etr * 100 / (3 * len(CAS)):.0f} %)")

    print("\n===== 4. Combien ca coute en temps =====")
    tous = [c[1 + i] for c in CAS for i in range(4)]
    for nom, f in (("couverture", couverture), ("mots-outils", part_outils)):
        t0 = time.perf_counter()
        for _ in range(20):
            for t in tous:
                f(t)
        ms = (time.perf_counter() - t0) / (20 * len(tous)) * 1000
        print(f"  {nom:>12} : {ms:.4f} ms par demande")
    t0 = time.perf_counter()
    for _ in range(20):
        for t in tous:
            A.classer(t)
    ms = (time.perf_counter() - t0) / (20 * len(tous)) * 1000
    print(f"  {'classer':>12} : {ms:.4f} ms par demande (pour comparaison)")
