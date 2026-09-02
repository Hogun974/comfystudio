# -*- coding: utf-8 -*-
"""Combien d'exemples faut-il pour qu'une langue cesse d'etre devinee ?

Le studio a DEJA un chemin pour apprendre une langue : moissonner(). Une
demande confirmee d'un pouce en l'air entre au corpus, ponderee huit fois,
plafonnee a un dixieme de sa classe. Ce chemin ne regarde pas la langue.

On l'eprouve : on ajoute K exemples par classe dans une langue, avec la
ponderation reelle du studio, et on mesure sur les exemples RESTANTS de cette
langue — jamais appris.

RIEN N'EST ECRIT SUR LE DISQUE. On n'appelle ni ecrire() ni
corpus_aiguillage.ecrire() : le depot ne doit pas bouger.
"""
import json
import os
import random
import sys

DEPOT = r"D:\ComfyStudio"
sys.path.insert(0, DEPOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aiguilleur import Aiguilleur, MARGE_SURE  # noqa: E402
import banc_langues                            # noqa: E402

POIDS_REEL = 8          # la meme ponderation que entrainer_aiguilleur.py
CAS = banc_langues.FACILE + banc_langues.DUR
# L'index dans le tuple (intention, fr, en, de, es), decale de 1 par c[1 + i].
LANGUES = {"en": 1, "de": 2, "es": 3}


def corpus_francais():
    """Le corpus du depot, lu tel quel. On ne le regenere pas."""
    tout, vus = [], set()
    for nom in ("corpus_aiguillage.jsonl", "corpus_llm.jsonl",
                "corpus_llm2.jsonl"):
        with open(os.path.join(DEPOT, nom), encoding="utf-8") as f:
            for l in f:
                if not l.strip():
                    continue
                x = json.loads(l)
                cle = (x.get("texte") or "").strip().lower()
                if cle and cle not in vus:
                    vus.add(cle)
                    tout.append(x)
    return tout


FR = corpus_francais()
print(f"corpus francais lu : {len(FR)} exemples")


def par_classe(i):
    d = {}
    for c in CAS:
        d.setdefault(c[0], []).append(c[1 + i])
    return d


def essai(i, k, graine):
    """K exemples par classe appris, le reste evalue."""
    hasard = random.Random(graine)
    groupes = par_classe(i)
    appris, tenus = [], []
    for intention, textes in groupes.items():
        t = list(textes)
        hasard.shuffle(t)
        for x in t[:k]:
            appris += [{"texte": x, "intention": intention}] * POIDS_REEL
        tenus += [(x, intention) for x in t[k:]]
    a = Aiguilleur().apprendre(FR + appris)
    bons = surs = pannes = 0
    for texte, attendu in tenus:
        propose, marge = a.classer(texte)
        sur = marge >= MARGE_SURE
        juste = propose == attendu
        bons += juste
        surs += sur
        pannes += sur and not juste
    return bons, len(tenus), pannes


if __name__ == "__main__":
    print("\nK = exemples appris par classe (11 classes)."
          "\nOn mesure sur les cas RESTANTS de la meme langue.\n")
    print(f"{'langue':>7} {'K':>3} {'exemples ajoutes':>17} "
          f"{'justes':>14} {'pannes silencieuses':>21}")
    for lg, i in LANGUES.items():
        for k in (0, 1, 2, 3, 5):
            r = [essai(i, k, g) for g in (1, 2, 3)]
            bons = sum(x[0] for x in r)
            n = sum(x[1] for x in r)
            p = sum(x[2] for x in r)
            print(f"{lg:>7} {k:>3} {k * 11:>13} demandes "
                  f"{bons:>7}/{n:<6} ({bons * 100 / n:>3.0f} %) "
                  f"{p:>10} ({p * 100 / n:.0f} %)")
        print()

    print("\n===== Ce que l'ajout coute au FRANCAIS =====")
    banc_fr = []
    for nom in ("banc_aiguillage.jsonl", "banc_neuf.jsonl"):
        with open(os.path.join(DEPOT, nom), encoding="utf-8") as f:
            banc_fr += [json.loads(l) for l in f if l.strip()]
    for k in (0, 3, 5):
        appris = []
        hasard = random.Random(7)
        for i in LANGUES.values():
            for intention, textes in par_classe(i).items():
                t = list(textes)
                hasard.shuffle(t)
                for x in t[:k]:
                    appris += [{"texte": x, "intention": intention}] * POIDS_REEL
        a = Aiguilleur().apprendre(FR + appris)
        bons = pannes = 0
        for x in banc_fr:
            propose, marge = a.classer(x["texte"])
            juste = propose == x["intention"]
            bons += juste
            pannes += (marge >= MARGE_SURE) and not juste
        print(f"  K={k} par classe et par langue "
              f"({k * 11 * 3} demandes etrangeres apprises) : "
              f"banc francais {bons}/{len(banc_fr)} "
              f"({bons * 100 / len(banc_fr):.0f} %), {pannes} pannes")
