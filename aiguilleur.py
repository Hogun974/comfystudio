# -*- coding: utf-8 -*-
"""Un classifieur d'intention, sans modele de langage.

Aiguiller, c'est ranger une phrase dans l'une de onze cases. Mesure du 29 aout
2026 sur vingt-quatre demandes reelles : le meilleur petit modele local en
place dix-sept correctement, en sept cents millisecondes chacune, et invente
regulierement des etiquettes qui n'existent pas — « modifier », « detour »,
« chanson ». Il faut ensuite deviner ce qu'il a voulu dire.

Un classifieur entraine ne peut PAS inventer d'etiquette : il choisit dans une
liste fermee. Il repond en une fraction de milliseconde, ne demande ni carte
graphique ni Ollama, et se comporte de la meme facon a chaque appel.

Ce qu'il ne sait pas faire, en revanche : ecrire le prompt enrichi, choisir le
cadrage, proposer un negatif. Ce travail-la reste au modele de langage. Le
classifieur ne repond qu'a « de quoi s'agit-il », ce qui suffit a decider s'il
faut appeler le grand modele — et, quand la reponse est franche, a s'en passer.

**Bayes naif multinomial**, sur des mots et des morceaux de mots. Le choix est
delibere : cent lignes lisibles, un entrainement d'une seconde, aucun paquet a
installer, et un modele qui tient dans un fichier texte qu'on peut relire. Un
reseau ferait peut-etre mieux d'un point ou deux, au prix d'une dependance et
d'une boite noire.

Les morceaux de mots comptent autant que les mots : « detoure-la »,
« detourage » et « detourez » n'ont aucun mot en commun mais partagent
« detour ». Sans eux, la moindre variation de conjugaison passe a cote.
"""
import json
import math
import os
import re
import unicodedata

ICI = os.path.dirname(os.path.abspath(__file__))
MODELE = os.path.join(ICI, "aiguilleur.json")

# En dessous de cette marge entre les deux meilleures hypotheses, on ne tranche
# pas : la demande part au modele de langage. Mieux vaut un appel de plus qu'une
# video generee quand on demandait une image.
MARGE_SURE = 1.2


def _sans_accents(t):
    return "".join(c for c in unicodedata.normalize("NFD", t or "")
                   if unicodedata.category(c) != "Mn")


_MOT = re.compile(r"[a-z0-9]+")


def traits(texte):
    """Les indices tires d'une phrase : mots, paires de mots, bouts de mots.

    Les bouts de mots (quatre lettres) rattrapent la conjugaison et les fautes
    de frappe, qui sont la regle dans une demande tapee vite.
    """
    nu = _sans_accents((texte or "").lower())
    mots = _MOT.findall(nu)
    sortie = list(mots)
    sortie += [f"{a}_{b}" for a, b in zip(mots, mots[1:])]
    for m in mots:
        if len(m) > 4:
            sortie += [f"#{m[i:i + 4]}" for i in range(len(m) - 3)]
    return sortie


class Aiguilleur:
    """Bayes naif multinomial, entraine sur des demandes d'exemple."""

    def __init__(self, poids=None, classes=None, total=None, vocabulaire=0):
        self.poids = poids or {}          # classe -> {trait: occurrences}
        self.classes = classes or {}      # classe -> nombre d'exemples
        self.total = total or {}          # classe -> total d'occurrences
        self.vocabulaire = vocabulaire

    # ── entrainement ────────────────────────────────────────────────────
    def apprendre(self, exemples):
        vus = set()
        for x in exemples:
            c = x["intention"]
            self.classes[c] = self.classes.get(c, 0) + 1
            sac = self.poids.setdefault(c, {})
            for t in traits(x["texte"]):
                sac[t] = sac.get(t, 0) + 1
                self.total[c] = self.total.get(c, 0) + 1
                vus.add(t)
        self.vocabulaire = len(vus)
        return self

    # ── usage ───────────────────────────────────────────────────────────
    def scores(self, texte):
        """Log-vraisemblance de chaque classe. Lissage de Laplace : un trait
        jamais vu ne doit pas annuler une classe entiere."""
        n = sum(self.classes.values()) or 1
        ts = traits(texte)
        rendu = {}
        for c, combien in self.classes.items():
            s = math.log(combien / n)
            total = self.total.get(c, 0) + self.vocabulaire
            sac = self.poids.get(c, {})
            for t in ts:
                s += math.log((sac.get(t, 0) + 1) / total)
            rendu[c] = s
        return rendu

    def classer(self, texte):
        """Rend (intention, marge). La marge dit a quel point c'est net.

        On rend la marge et non une « probabilite » : Bayes naif est connu pour
        rendre des probabilites tres proches de 0 ou 1, qui donneraient une
        confiance illusoire. L'ecart entre les deux meilleures hypotheses, lui,
        se compare a un seuil regle par la mesure.
        """
        s = self.scores(texte)
        if not s:
            return None, 0.0
        classe = sorted(s, key=s.get, reverse=True)
        if len(classe) == 1:
            return classe[0], 99.0
        return classe[0], s[classe[0]] - s[classe[1]]

    def sur(self, texte, marge=MARGE_SURE):
        """L'intention si elle est franche, sinon None — au modele de trancher."""
        c, m = self.classer(texte)
        return c if m >= marge else None

    # ── disque ──────────────────────────────────────────────────────────
    def ecrire(self, chemin=MODELE):
        with open(chemin, "w", encoding="utf-8") as f:
            json.dump({"poids": self.poids, "classes": self.classes,
                       "total": self.total, "vocabulaire": self.vocabulaire},
                      f, ensure_ascii=False)
        return chemin

    @staticmethod
    def lire(chemin=MODELE):
        with open(chemin, encoding="utf-8") as f:
            d = json.load(f)
        return Aiguilleur(d["poids"], d["classes"], d["total"], d["vocabulaire"])


def charger(chemin=MODELE):
    """L'aiguilleur entraine, ou None s'il n'a pas ete construit.

    Rendre None plutot que lever : le studio doit fonctionner sans lui, comme
    avant, et se contenter du modele de langage.
    """
    try:
        return Aiguilleur.lire(chemin)
    except Exception:
        return None
