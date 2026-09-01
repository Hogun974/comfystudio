# -*- coding: utf-8 -*-
"""Fabrique des demandes d'exemple pour entrainer l'aiguilleur.

Aiguiller, c'est ranger une phrase dans l'une de onze cases. Un modele de
langage sait le faire, mal et lentement : mesure du 29 aout 2026, 17 bonnes
reponses sur 24 pour le meilleur des petits modeles, et sept cents millisecondes
a chaque fois. Surtout, il invente des mots hors de la liste — « modifier »,
« detour », « chanson » — qu'il faut ensuite deviner.

Un classifieur entraine sur des exemples n'a pas ce defaut : il ne peut rendre
qu'une etiquette existante, il repond en une fraction de milliseconde, et il ne
demande ni carte graphique ni Ollama.

Ce fichier ne fait que produire les exemples. Deux sources, volontairement :

  - **des gabarits**, ecrits ici. Ils couvrent le vocabulaire sur lequel on ne
    veut aucune erreur, et ils sont reproductibles.
  - **un modele distant**, si une cle est posee. Il apporte les tournures
    auxquelles on ne pense pas — c'est justement ce qui manque a des gabarits
    ecrits par une seule personne.

Sans cle, les gabarits seuls suffisent a entrainer quelque chose d'utilisable :
le corpus distant est un supplement, jamais une dependance.
"""
import itertools
import json
import os
import random

ICI = os.path.dirname(os.path.abspath(__file__))
FICHIER = os.path.join(ICI, "corpus_aiguillage.jsonl")

# ── vocabulaire ──────────────────────────────────────────────────────────
SUJETS = [
    "un renard roux", "un vieux phare", "une guerriere en armure", "un cerf",
    "une ruelle sous la pluie", "un chat endormi", "un heron dans les roseaux",
    "un portrait de vieil homme", "une foret en automne", "un dragon",
    "une voiture de sport", "un bol de ramen", "une cabane en montagne",
    "un astronaute", "une danseuse", "un marche de nuit", "un phare breton",
    "un ecureuil sur une branche", "une plage au couchant", "un chevalier",
]
LIEUX = [
    "dans la neige", "au crepuscule", "sous la pluie", "au bord de la mer",
    "dans une foret brumeuse", "sur un toit", "au petit matin",
    "dans un atelier", "sous un ciel d'orage", "au milieu des champs",
]
STYLES = [
    "photo realiste", "style manga", "en aquarelle", "style cinema",
    "en noir et blanc", "illustration", "peinture a l'huile", "style bd",
]

CIBLES = ["le ciel", "le fond", "sa veste", "la couleur de ses yeux",
          "l'eclairage", "la voiture au second plan", "son chapeau",
          "la couleur du mur", "l'arriere-plan"]
CHANGEMENTS = ["en bleu", "en nuit etoilee", "en rouge", "plus lumineux",
               "plus sombre", "en hiver", "en version doree"]

GENRES = ["rock", "jazz", "electro", "classique", "folk", "reggae", "pop",
          "metal", "blues", "une berceuse"]
INSTRUMENTS = ["au piano", "a la guitare", "avec des cordes", "au saxophone",
               "avec batterie et basse", "a l'accordeon"]

OBJETS3D = ["une theiere", "un casque", "une chaise", "une statuette",
            "un vase", "une epee", "un buste"]

# ── gabarits : (modele de phrase, intention) ─────────────────────────────
GABARITS = [
    # image
    ("{sujet} {lieu}, {style}", "image"),
    ("dessine-moi {sujet} {lieu}", "image"),
    ("je voudrais {sujet}, {style}", "image"),
    ("fais {sujet} {lieu}", "image"),
    ("genere une image de {sujet}", "image"),
    ("{sujet}, {style}, format portrait", "image"),
    ("une affiche avec {sujet}", "image"),
    ("peux-tu me faire {sujet} {lieu} ?", "image"),
    ("le meme personnage, {lieu}", "image"),
    ("la meme, mais {lieu}", "image"),
    ("{sujet} devant une plus grande maison", "image"),
    # Une CREATION qui parle de definition, de qualite ou de detail. Le
    # classifieur voyait « 1920x1080 », « haute definition », « bonne qualite »
    # et concluait « agrandir » — le 31 aout, une demande de fond d'ecran Halo
    # est partie a l'agrandissement, avec assez de confiance pour court-circuiter
    # le modele de langage. Les mots de la definition appartiennent aux deux
    # intentions : ce qui les separe est qu'on DECRIT un sujet.
    ("{sujet} {lieu}, en 1920x1080", "image"),
    ("{sujet} {lieu}, en haute definition", "image"),
    ("{sujet}, {style}, tres detaille", "image"),
    ("{sujet} {lieu}, de bonne qualite", "image"),
    ("un fond d'ecran avec {sujet} {lieu}, plein de details", "image"),
    ("{sujet}, {style}, qualite professionnelle", "image"),
    ("une affiche de {sujet}, en 4k", "image"),
    # edition
    ("change {cible} {changement}", "edition"),
    ("mets {cible} {changement}", "edition"),
    ("remplace {cible} par autre chose", "edition"),
    ("enleve {cible}", "edition"),
    ("retouche {cible}", "edition"),
    ("rajoute-lui un chapeau", "edition"),
    ("ajoute une cicatrice sur sa joue", "edition"),
    ("corrige {cible}", "edition"),
    ("modifie {cible} {changement}", "edition"),
    # agrandir
    ("agrandis-la", "agrandir"),
    ("agrandis cette image", "agrandir"),
    ("agrandis-la en 2x", "agrandir"),
    ("passe-la en haute resolution", "agrandir"),
    ("mets-la en haute definition", "agrandir"),
    ("upscale", "agrandir"),
    ("je la veux plus grande", "agrandir"),
    ("ameliore la definition", "agrandir"),
    ("passe-la en 4k", "agrandir"),
    # detourer
    ("detoure-la", "detourer"),
    ("detoure le personnage", "detourer"),
    ("enleve le fond", "detourer"),
    ("retire l'arriere-plan", "detourer"),
    ("mets-la sur fond transparent", "detourer"),
    ("isole le sujet", "detourer"),
    ("supprime le fond de cette image", "detourer"),
    # video
    ("une video de {sujet} {lieu}", "video"),
    ("fais une video : {sujet} {lieu}", "video"),
    ("anime une scene avec {sujet}", "video"),
    ("un petit film de {sujet}", "video"),
    ("une sequence video de {sujet} {lieu}", "video"),
    # video_image
    ("anime cette image", "video_image"),
    ("anime cette photo, fais bouger les nuages", "video_image"),
    ("fais bouger ce dessin", "video_image"),
    ("mets du mouvement dans cette image", "video_image"),
    ("anime-la", "video_image"),
    # fluidifier
    ("rends la video plus fluide", "fluidifier"),
    ("fluidifie la video", "fluidifier"),
    ("passe-la au ralenti", "fluidifier"),
    ("mets-la en 60 fps", "fluidifier"),
    ("elle est saccadee, rends-la plus fluide", "fluidifier"),
    ("un ralenti s'il te plait", "fluidifier"),
    # audio
    ("fais-moi une musique {genre}", "audio"),
    ("une chanson {genre} {instrument}", "audio"),
    ("compose un morceau {genre}", "audio"),
    ("une musique {genre} de deux minutes", "audio"),
    ("je veux une chanson sur mon ami disparu, {genre}", "audio"),
    ("un instrumental {genre} {instrument}", "audio"),
    # planche
    ("une planche de bd en quatre cases", "planche"),
    ("fais-moi une page de manga", "planche"),
    ("une bande dessinee de trois cases sur {sujet}", "planche"),
    ("une planche avec plusieurs vignettes", "planche"),
    # objet3d
    ("un modele 3d de {objet3d}", "objet3d"),
    ("transforme ce dessin en objet 3d", "objet3d"),
    ("fais {objet3d} en trois dimensions", "objet3d"),
    ("un maillage 3d de {objet3d}", "objet3d"),
    ("je voudrais {objet3d} imprimable en 3d", "objet3d"),
    # lecture
    ("qu'est-ce qu'il y a sur cette image ?", "lecture"),
    ("decris-moi cette photo", "lecture"),
    ("que vois-tu la ?", "lecture"),
    ("explique-moi ce qui est represente", "lecture"),
    ("c'est quoi cette image ?", "lecture"),
    ("lis ce qui est ecrit dessus", "lecture"),
]


def _remplir(gabarit, hasard):
    return gabarit.format(
        sujet=hasard.choice(SUJETS), lieu=hasard.choice(LIEUX),
        style=hasard.choice(STYLES), cible=hasard.choice(CIBLES),
        changement=hasard.choice(CHANGEMENTS), genre=hasard.choice(GENRES),
        instrument=hasard.choice(INSTRUMENTS), objet3d=hasard.choice(OBJETS3D))


# De quoi varier la formulation sans changer le sens. Les gabarits sans trou
# ne produisent qu'une phrase chacun ; sans ces habillages, « detourer » aurait
# six exemples quand « image » en aurait trois cents, et le classifieur
# apprendrait surtout a repondre « image ».
_AVANT = ["", "", "", "stp ", "s'il te plait ", "peux-tu ", "j'aimerais ",
          "je voudrais ", "tu peux ", "il me faudrait ", "alors, ",
          "maintenant ", "et ", "bon, "]
_APRES = ["", "", "", " s'il te plait", " stp", " merci", " ?", " !",
          " pour moi", " maintenant", " vite fait"]


def _habiller(phrase, hasard):
    """Une meme demande, dite autrement. On ne touche pas au sens."""
    avant, apres = hasard.choice(_AVANT), hasard.choice(_APRES)
    phrase = (avant + phrase + apres).strip()
    if hasard.random() < 0.12:
        phrase = phrase.upper()
    elif hasard.random() < 0.10:
        phrase = phrase.replace("'", "")
    return phrase


def depuis_gabarits(par_classe=200, graine=20260829):
    """Le corpus reproductible. La graine est fixe : deux entrainements sur la
    meme version doivent donner le meme classifieur, sinon on ne peut rien
    comparer."""
    hasard = random.Random(graine)
    par_etiquette = {}
    for gabarit, etiquette in GABARITS:
        par_etiquette.setdefault(etiquette, []).append(gabarit)

    vus, sortie = set(), []
    for etiquette, gabarits in par_etiquette.items():
        # Autant d'exemples par classe : un corpus qui compte trois cents
        # images pour six detourages apprend surtout a repondre « image ».
        pris, essais = 0, 0
        while pris < par_classe and essais < par_classe * 40:
            essais += 1
            phrase = _habiller(_remplir(hasard.choice(gabarits), hasard), hasard)
            if phrase in vus:
                continue
            vus.add(phrase)
            sortie.append({"texte": phrase, "intention": etiquette,
                           "source": "gabarit"})
            pris += 1
    hasard.shuffle(sortie)
    return sortie


def ecrire(exemples, chemin=FICHIER):
    """Ecrit le corpus, en une seule fois vue du dehors.

    Un fichier temporaire puis os.replace : depuis que le corpus est
    regenere a CHAQUE entrainement, deux reentrainements lances coup sur
    coup — deux onglets d'administration, un double-clic — se croisaient.
    L'un tronquait le fichier pendant que l'autre le relisait, et le
    second apprenait sur un corpus ampute puis ecrivait son modele, que le
    studio rechargeait aussitot. Rien ne le disait.
    """
    tmp = chemin + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for x in exemples:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    os.replace(tmp, chemin)
    return chemin


if __name__ == "__main__":
    ex = depuis_gabarits()
    ecrire(ex)
    par = {}
    for x in ex:
        par[x["intention"]] = par.get(x["intention"], 0) + 1
    print(f"  {len(ex)} exemples ecrits dans {os.path.basename(FICHIER)}")
    for k, v in sorted(par.items(), key=lambda kv: -kv[1]):
        print(f"     {k:12s} {v}")
