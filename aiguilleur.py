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
import sys
import unicodedata

ICI = os.path.dirname(os.path.abspath(__file__))
# Ou ECRIRE, par opposition a ou lire le code. Gele par PyInstaller, ICI pointe
# sur un dossier temporaire efface a l'arret : un modele local pose a cote de
# l'executable n'y etait jamais lu, et le bouton « reentrainer » y ecrivait pour
# rien — pire, faute d'y trouver les conversations, il ecrasait la copie
# EMBARQUEE du modele publie. Meme distinction que ICI_DATA dans serveur.py.
ICI_DATA = (os.path.dirname(os.path.abspath(sys.executable))
            if getattr(sys, "frozen", False) else ICI)
# Le modele PUBLIE est du code : il voyage avec le paquet.
MODELE = os.path.join(ICI, "aiguilleur.json")
# Le modele LOCAL est une donnee : il vit a cote de l'executable, comme les
# conversations et les cles. Entraine avec les demandes reelles de CETTE
# installation, et ignore par git — un modele bayesien ne garde pas les
# phrases, mais il garde les mots, assez pour qu'un depot public n'ait pas a
# les porter.
MODELE_LOCAL = os.path.join(ICI_DATA, "aiguilleur.local.json")

# En dessous de cette marge entre les deux meilleures hypotheses, on ne tranche
# pas : la demande part au modele de langage. Mieux vaut un appel de plus qu'une
# video generee quand on demandait une image.
MARGE_SURE = 1.2

# ── « je ne connais pas ces mots » ──────────────────────────────────────
# EN DESSOUS DE CETTE PART DE VOCABULAIRE CONNU, LA MARGE NE VEUT RIEN DIRE.
# Bayes naif ne sait pas dire qu'il ignore une phrase : quand presque aucun
# trait n'est reconnu, le lissage de Laplace et les probabilites a priori
# departagent les classes tout seuls, et l'ecart entre les deux meilleures
# peut etre grand pour de mauvais motifs. « brauche ein Video von null mit
# einem fliegenden Drachen » — une video a creer de zero — part en
# « fluidifier » avec une marge de 3,9.
#
# CE QUE CELA A COUTE, mesure le 2 septembre 2026 sur 460 demandes (les deux
# bancs du depot traduits a la main en anglais, allemand et espagnol,
# mesures_langues/) : sur 345 demandes etrangeres, le court-circuit du
# classifieur tirait 70 fois et se trompait 25 fois, sans qu'un mot le dise.
# Une demande etrangere sur quatre etait executee de travers, en silence.
#
# LE SEUIL A ETE CHOISI PAR MESURE, seuil par seuil : a 0,58, le francais est
# garde a 114/115 et l'etranger reconnu a 338/345. Deux autres moyens ont ete
# eprouves et ecartes — une liste de mots grammaticaux francais (l'espagnol en
# partage trop : la, le, un, no, para) et l'en-tete « Accept-Language » (il dit
# la langue du NAVIGATEUR : un francophone sur un Windows anglais serait classe
# anglais). Celui-ci ne demande aucune donnee nouvelle : le vocabulaire est
# deja dans aiguilleur.json, et il coute 0,0095 ms, un cinquieme de classer().
#
# IL NE DIT PAS QUELLE LANGUE C'EST, et c'est voulu : il dit « je ne connais
# pas ces mots », ce qui est exactement la condition sous laquelle la marge ne
# se lit plus. N'importe quelle langue passe donc au modele de langage, qui est
# multilingue — sans un seul exemple nouveau. Voir docs/plusieurs-langues.md.
SEUIL_LANGUE = 0.58


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
        self._connus = None               # le vocabulaire en SET, bati au besoin

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
        self._connus = None
        return self

    # ── usage ───────────────────────────────────────────────────────────
    def couverture(self, texte):
        """La part des traits de cette phrase que le corpus connait deja.

        « self.vocabulaire » est un NOMBRE, employe par le lissage de Laplace :
        il ne dit pas QUELS traits sont connus. On prend donc l'union des sacs,
        une fois, et on la garde — 7 734 traits pour le modele publie, bati en
        0,6 ms. Le cache est vide par apprendre(), le seul endroit qui ajoute des
        traits.

        Une phrase vide rend 0,0 : « je ne connais pas ces mots » est vrai de
        rien, et c'est le bon sens ici — la garde renvoie au modele de langage,
        qui verra bien qu'il n'y a rien a lire.
        """
        if self._connus is None:
            connus = set()
            for sac in self.poids.values():
                connus |= set(sac)
            self._connus = connus
        ts = traits(texte)
        if not ts:
            return 0.0
        return sum(1 for t in ts if t in self._connus) / len(ts)

    def connu(self, texte, seuil=None):
        """Le corpus reconnait-il assez cette phrase pour qu'on s'y fie ?

        Le seuil est relu A CHAQUE APPEL et non fige en valeur par defaut :
        banc_multilingue.py le descend a 0 pour rejouer la politique d'AVANT
        la garde sur les memes 460 demandes, et c'est cette comparaison-la —
        le francais decide exactement pareil des deux cotes — qui est la moitie
        importante de ce que le banc mesure. Avec « seuil=SEUIL_LANGUE » en
        valeur par defaut, la liaison se ferait a la definition et le banc
        aurait compare deux fois la meme politique, sans rien dire.
        """
        return self.couverture(texte) >= (SEUIL_LANGUE if seuil is None
                                          else seuil)

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


def charger(chemin=None):
    """L'aiguilleur entraine, ou None s'il n'a pas ete construit.

    Le modele local d'abord : il a vu les demandes de cette installation, il est
    donc meilleur ici. Celui du depot ensuite, qui suffit a une installation
    neuve.

    Rendre None plutot que lever : le studio doit fonctionner sans lui, comme
    avant, et se contenter du modele de langage.
    """
    for essai in ([chemin] if chemin else [MODELE_LOCAL, MODELE]):
        try:
            return Aiguilleur.lire(essai)
        except Exception:
            continue
    return None
