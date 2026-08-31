# -*- coding: utf-8 -*-
"""Le devis dit-il quelque chose de vrai, et se tait-il quand il ne sait pas ?

    python banc_durees.py

Le studio annonce, avant de lancer, combien de temps ça a pris les fois
d'avant. Deux facons de se tromper, et elles sont aussi graves l'une que
l'autre : promettre un chiffre tire d'un seul rendu, et se taire alors qu'on
sait. La premiere fait perdre confiance a la premiere surprise ; la seconde
laisse la question sans reponse alors qu'elle en a une.

La mediane et non la moyenne : un rendu qui a attendu une carte occupee
tirerait la moyenne sans rien dire de ce qui va se passer maintenant.
"""
import os
import sys
import tempfile

os.environ["STUDIO_DONNEES"] = tempfile.mkdtemp(prefix="banc_durees_")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serveur as S  # noqa: E402

ok, rate = [], []


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


def tour(ident, cle, taille, secondes, etat="fini", esquisse=None):
    return {"id": os.urandom(6).hex(), "noeud": ident, "modele": cle,
            "taille": taille, "secondes": secondes, "etat": etat,
            "esquisse": esquisse}


def poser(tours):
    S.CONVERSATIONS.clear()
    S.CONVERSATIONS["c1"] = {"id": "c1", "titre": "banc", "tours": tours}
    S._DUREES["quand"] = 0.0        # force la relecture


# ── on ne parle pas pour deux mesures ───────────────────────────────────
poser([tour("pc", "realvis", "1216x832", 100),
       tour("pc", "realvis", "1216x832", 120)])
m, c = S.duree_typique("pc", "realvis", "1216x832")
dit(m is None, "deux rendus ne font pas une mediane — on se tait", str(m))

# ── a partir de trois, on repond ────────────────────────────────────────
poser([tour("pc", "realvis", "1216x832", 100),
       tour("pc", "realvis", "1216x832", 120),
       tour("pc", "realvis", "1216x832", 110)])
m, c = S.duree_typique("pc", "realvis", "1216x832")
dit(m == 110 and c == 3, "trois rendus donnent leur mediane", f"{m} s sur {c}")

# ── la mediane resiste a un rendu qui a attendu une carte ───────────────
poser([tour("pc", "realvis", "1216x832", 100),
       tour("pc", "realvis", "1216x832", 110),
       tour("pc", "realvis", "1216x832", 120),
       tour("pc", "realvis", "1216x832", 2400)])   # a attendu une demi-heure
m, _ = S.duree_typique("pc", "realvis", "1216x832")
dit(m <= 130, "un rendu qui a attendu ne fausse pas le devis", f"{m} s")

# ── du plus precis au plus general ──────────────────────────────────────
poser([tour("pc", "realvis", "1024x1024", 60),
       tour("pc", "realvis", "1024x1024", 62),
       tour("pc", "realvis", "1024x1024", 64),
       tour("zima", "realvis", "1216x832", 240),
       tour("zima", "realvis", "1216x832", 250),
       tour("zima", "realvis", "1216x832", 260)])
m, _ = S.duree_typique("pc", "realvis", "1024x1024")
dit(m == 62, "la taille exacte d'abord", f"{m} s")
m, _ = S.duree_typique("zima", "realvis", "1216x832")
dit(m == 250, "et la machine compte", f"{m} s")
# Taille inconnue sur cette machine : on retombe sur le moteur, toutes tailles
# confondues — approximatif, mais mieux que se taire.
m, _ = S.duree_typique("pc", "realvis", "1920x1080")
dit(m is not None, "une taille jamais vue retombe sur ce qu'on sait", f"{m} s")
# Machine jamais vue : le moteur seul, toutes machines confondues.
m, _ = S.duree_typique("inconnue", "realvis", None)
dit(m is not None, "une machine jamais vue aussi", f"{m} s")

# ── ce qui ne doit pas compter ──────────────────────────────────────────
poser([tour("pc", "realvis", "1216x832", 14, esquisse=True),
       tour("pc", "realvis", "1216x832", 15, esquisse=True),
       tour("pc", "realvis", "1216x832", 16, esquisse=True)])
m, _ = S.duree_typique("pc", "realvis", "1216x832")
dit(m is None, "une esquisse ne predit pas une image finie", str(m))

poser([tour("pc", "realvis", "1216x832", 100, etat="erreur"),
       tour("pc", "realvis", "1216x832", 110, etat="erreur"),
       tour("pc", "realvis", "1216x832", 120, etat="erreur")])
m, _ = S.duree_typique("pc", "realvis", "1216x832")
dit(m is None, "un rendu echoue ne compte pas", str(m))

poser([])
m, _ = S.duree_typique("pc", "realvis", None)
dit(m is None, "sans aucune mesure, aucun devis")

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
for r in rate:
    print("    a regarder :", r)
sys.exit(1 if rate else 0)
