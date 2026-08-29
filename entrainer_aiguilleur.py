# -*- coding: utf-8 -*-
"""Entraine l'aiguilleur et le mesure. A relancer quand le corpus change.

    python entrainer_aiguilleur.py

Le corpus a deux sources : des gabarits ecrits a la main (reproductibles, sans
reseau) et des demandes ecrites par un modele distant si une cle est posee. Les
secondes sont indispensables — mesure : entraine sur les seuls gabarits,
l'aiguilleur atteint 100 % sur mes propres phrases et 74 % sur celles ecrites
par quelqu'un d'autre. Il ne connaissait que mon vocabulaire.

La mesure qui compte est celle du banc, ecrit ailleurs et jamais appris.
"""
import json
import os
import sys
import time

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)

from aiguilleur import Aiguilleur, MARGE_SURE          # noqa: E402
import corpus_aiguillage                                # noqa: E402

CORPUS = [
    "corpus_aiguillage.jsonl",   # gabarits, produits par corpus_aiguillage.py
    "corpus_llm.jsonl",          # demandes variees ecrites par un modele
    "corpus_llm2.jsonl",         # tournures indirectes, ou le verbe est absent
]
BANCS = ["banc_aiguillage.jsonl", "banc_neuf.jsonl"]


def _lire(nom):
    chemin = os.path.join(ICI, nom)
    if not os.path.exists(chemin):
        return []
    with open(chemin, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


# Les demandes reelles sont rares et precieuses : on les compte plusieurs fois,
# sinon trois mille exemples fabriques les noieraient. Mais on plafonne leur
# apport par classe — mesure : sans plafond, dix-sept demandes reelles dont
# onze images faisaient pencher tout le classifieur vers « image », et la
# justesse sur les tournures indirectes tombait de 86 a 84 %.
POIDS_REEL = 8
PART_REELLE = 0.10          # au plus un dixieme d'une classe


def moissonner(dossier=None):
    """Les demandes passees par le studio dont l'intention est certaine.

    On ne prend que ce que l'utilisateur a lui-meme decide ou valide. Un tour
    « fini » sans pouce ne prouve rien : le studio a pu se tromper de modalite
    et produire quand meme quelque chose ; l'apprendre reviendrait a lui
    enseigner ses propres erreurs.
    """
    dossier = dossier or os.path.join(ICI, "conversations")
    if not os.path.isdir(dossier):
        return []
    connues = set(corpus_aiguillage.__dict__.get("_CLASSES", []) or
                  {e for _, e in corpus_aiguillage.GABARITS})
    recolte = []
    for nom in os.listdir(dossier):
        if not nom.endswith(".json") or nom.startswith("_"):
            continue
        try:
            with open(os.path.join(dossier, nom), encoding="utf-8") as f:
                conv = json.load(f)
        except Exception:
            continue
        for t in conv.get("tours", []):
            texte = (t.get("demande") or "").strip()
            intention = t.get("type")
            if not texte or intention not in connues:
                continue
            if t.get("etat") != "fini" or t.get("avis") == -1:
                continue
            impose = str(t.get("raison") or "").startswith(
                ("modele impose", "moteur distant impose"))
            if not impose and t.get("avis") != 1:
                continue
            recolte.append({"texte": texte, "intention": intention,
                            "source": "reel"})
    return recolte


def corpus():
    """Tous les exemples, sans doublon. L'ordre des fichiers ne compte pas."""
    if not os.path.exists(os.path.join(ICI, "corpus_aiguillage.jsonl")):
        corpus_aiguillage.ecrire(corpus_aiguillage.depuis_gabarits())
    tout, vus = [], set()
    for nom in CORPUS:
        for x in _lire(nom):
            cle = (x.get("texte") or "").strip().lower()
            if cle and cle not in vus:
                vus.add(cle)
                tout.append(x)
    fabriques = {}
    for x in tout:
        fabriques[x["intention"]] = fabriques.get(x["intention"], 0) + 1

    reels, ajoutes = moissonner(), {}
    for x in reels:
        cle = x["texte"].strip().lower()
        if cle in vus:
            continue
        plafond = int(fabriques.get(x["intention"], 0) * PART_REELLE)
        deja = ajoutes.get(x["intention"], 0)
        if deja >= plafond:
            continue
        vus.add(cle)
        combien = min(POIDS_REEL, plafond - deja)
        ajoutes[x["intention"]] = deja + combien
        tout += [x] * combien
    if reels:
        print(f"  {len(reels)} demandes reelles recoltees, "
              f"{sum(ajoutes.values())} exemplaires retenus "
              f"(plafond : {PART_REELLE:.0%} par classe)")
    return tout


def mesurer(a, banc):
    """Justesse globale, et justesse sur les seuls cas tranches d'office.

    Les deux chiffres disent des choses differentes : le premier mesure le
    classifieur, le second mesure ce qu'on lui laisse decider tout seul. C'est
    le second qui compte pour l'utilisateur, puisque les cas incertains partent
    au modele de langage.
    """
    bons = surs = bons_surs = 0
    for x in banc:
        c, marge = a.classer(x["texte"])
        sur = marge >= MARGE_SURE
        juste = c == x["intention"]
        bons += juste
        surs += sur
        bons_surs += juste and sur
    return bons, len(banc), bons_surs, surs


if __name__ == "__main__":
    exemples = corpus()
    par = {}
    for x in exemples:
        par[x["intention"]] = par.get(x["intention"], 0) + 1
    print(f"  {len(exemples)} exemples, {len(par)} classes")
    print("  ", ", ".join(f"{k} {v}" for k, v in sorted(par.items())))

    t0 = time.time()
    a = Aiguilleur().apprendre(exemples)
    print(f"\n  entraine en {time.time() - t0:.2f} s — {a.vocabulaire} traits")
    a.ecrire()
    print(f"  ecrit : aiguilleur.json "
          f"({os.path.getsize(os.path.join(ICI, 'aiguilleur.json')) / 1e6:.2f} Mo)")

    for nom in BANCS:
        banc = _lire(nom)
        if not banc:
            continue
        t0 = time.time()
        bons, total, bons_surs, surs = mesurer(a, banc)
        ms = (time.time() - t0) / max(total, 1) * 1000
        print(f"\n  {nom}")
        print(f"     {bons}/{total} justes ({bons * 100 / total:.0f} %), "
              f"{ms:.3f} ms par demande")
        print(f"     tranches d'office : {bons_surs}/{surs} "
              f"({bons_surs * 100 / max(surs, 1):.0f} %) — "
              f"{total - surs} renvoyes au modele de langage")
