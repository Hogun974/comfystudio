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


# ── UNE TABLE PAR LECTEUR, ET NON UNE CASE CLEFEE SUR « QUI » ───────────
# Deux lecteurs se croisent dans la MEME demande et ne posent pas la meme
# question : le devis lit les rendus du proprietaire, la repartition ceux de
# tout le studio. Avec une case unique, chacun chassait l'autre et
# _relever_durees() reparcourait TOUTES les conversations a chaque appel —
# FRAICHEUR_DUREES ne servait jamais.
#
# Mesure du 1er septembre, quatre demandes jouees de bout en bout :
#   avant — 2, 2, 2, 8 relevees, soit 2 par TIRAGE, indefiniment ;
#   apres — 2, 0, 0, 0.
def poser_a(qui_a_quoi):
    """Des conversations a plusieurs proprietaires. {pid: [tours]}"""
    S.CONVERSATIONS.clear()
    for n, (pid, tours) in enumerate(qui_a_quoi.items()):
        S.CONVERSATIONS[f"c{n}"] = {"id": f"c{n}", "titre": "banc",
                                    "proprietaire": pid, "tours": tours}
    S._DUREES["quand"] = 0.0
    S._DUREES["tables"].clear()


MOI, VOISIN = "m" * 32, "v" * 32
poser_a({MOI: [tour("pc", "realvis", "1216x832", 100),
               tour("pc", "realvis", "1216x832", 110),
               tour("pc", "realvis", "1216x832", 120)],
         VOISIN: [tour("pc", "realvis", "1216x832", 300),
                  tour("pc", "realvis", "1216x832", 310),
                  tour("pc", "realvis", "1216x832", 320)]})

_appels = {"n": 0}
_vrai_relever = S._relever_durees


def relever_espion(pid=None):
    _appels["n"] += 1
    return _vrai_relever(pid)


S._relever_durees = relever_espion
try:
    # Quatre demandes de suite, chacune posant les DEUX questions : celle du
    # devis, personnelle, et celle du placement, qui ne l'est pas.
    for _ in range(4):
        S.duree_typique("pc", "realvis", "1216x832", pid=MOI)
        S.duree_typique("pc", "realvis", "1216x832")
    dit(_appels["n"] == 2,
        "deux lecteurs dans la meme demande ne relisent les conversations "
        "qu'une fois chacun", f"{_appels['n']} relevees pour huit lectures")
    # Et la fraicheur perime bien TOUTE la reserve d'un coup : « quand » est le
    # tampon de la reserve, pas d'une table. C'est ce que les bancs emploient
    # pour forcer la relecture apres avoir change les conversations.
    S._DUREES["quand"] = 0.0
    S.duree_typique("pc", "realvis", "1216x832", pid=MOI)
    S.duree_typique("pc", "realvis", "1216x832")
    dit(_appels["n"] == 4, "et la fraicheur les perime toutes ensemble",
        str(_appels["n"]))
finally:
    S._relever_durees = _vrai_relever


# ── LE DEVIS EST PERSONNEL, LE PLACEMENT NE L'EST PAS ───────────────────
# Ce qu'on ANNONCE a quelqu'un est a lui : « d'apres tes 3 rendus precedents »
# ne peut pas compter ceux du voisin, sous peine de mentir et de dire au passage
# combien le voisin travaille. OU L'ON POSE un rendu ne regarde personne en
# particulier : « cette carte-la met-elle beaucoup plus de temps que celle-ci
# sur ce moteur » est un fait de la MACHINE. Restreindre le placement au
# proprietaire ferait attendre trois rendus PAR PERSONNE avant de savoir ce que
# le studio sait deja, et deux comptes repartiraient differemment sur le meme
# parc.
m_moi, _ = S.duree_typique("pc", "realvis", "1216x832", pid=MOI)
m_voisin, _ = S.duree_typique("pc", "realvis", "1216x832", pid=VOISIN)
m_tous, n_tous = S.duree_typique("pc", "realvis", "1216x832")
dit(m_moi == 110 and m_voisin == 310 and n_tous == 6,
    "le devis est personnel, la decision de placement ne l'est pas",
    f"moi {m_moi} s, voisin {m_voisin} s, le studio {n_tous} rendus")

# Le nouveau venu, qui est le cas qui tranche : il n'a rien rendu, donc rien a
# lui annoncer — et pourtant le studio sait deja ou poser son rendu.
NEUF = "n" * 32
poser_a({VOISIN: [tour("zima", "realvis", "1216x832", 70),
                  tour("zima", "realvis", "1216x832", 72),
                  tour("zima", "realvis", "1216x832", 74),
                  tour("pc", "realvis", "1216x832", 60),
                  tour("pc", "realvis", "1216x832", 62),
                  tour("pc", "realvis", "1216x832", 64)],
         NEUF: []})
dit(S.duree_typique("zima", "realvis", "1216x832", pid=NEUF)[0] is None,
    "au nouveau venu, on n'annonce rien : ce sont SES rendus qu'on lui promet")
dit(S.debordement_acceptable("zima", "pc", "realvis", "1216x832") is True,
    "mais on sait deja ou poser le sien — le parc, lui, a ete mesure",
    str(S.debordement_acceptable("zima", "pc", "realvis", "1216x832")))

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
for r in rate:
    print("    a regarder :", r)
sys.exit(1 if rate else 0)
