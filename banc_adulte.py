# -*- coding: utf-8 -*-
"""Le motif qui decide ce qui reste a la maison, et ce qui est refuse.

Deux choses en dependent, et ce sont les deux plus serieuses du projet :

  - « adulte() » : ce qui est adulte ne sort pas de la maison, jamais vers un
    fournisseur distant. C'est une regle posee par l'utilisateur et tenue en
    code, pas une case a cocher.
  - « garde_fou() » : la seule limite codee en dur, le refus du contenu sexuel
    impliquant des mineurs.

Ce motif s'est trompe DEUX FOIS le meme jour. D'abord en mordant trop large —
« nuit », « nuage », « nuance » classes adultes, ce qui envoyait chaque
traduction sur un modele local a cent soixante secondes. Puis, en corrigeant
cela, en mordant trop court : les formes anglaises derivees, que l'ancien motif
attrapait par prefixe, avaient disparu de la liste ecrite a la main. « a child
in a sexual pose » passait au travers de garde_fou().

D'ou ce banc, et sa place dans la CI. Un motif de surete ne se relit pas, il
s'eprouve — dans les DEUX sens, a chaque fois.

    python banc_adulte.py
"""
import ast
import io
import re
import sys

# ── ce qui doit passer : des demandes ordinaires ────────────────────────
# Chacune a ete un vrai faux positif, ou en est a un caractere.
ORDINAIRES = [
    "une scene de nuit sous la pluie",
    "un nuage au dessus de la montagne",
    "une nuance de bleu tres douce",
    "un paysage numerique",
    "une nuee d'oiseaux au couchant",
    "les nutriments d'une plante",
    "a majestic lighthouse, nuanced lighting",
    "un sexagenaire assis sur un banc",
    "au sein de la foret",
    "il continue sa route",
    "le menu du jour",
    "dis-le explicitement",
    "une explication du schema",
    "un vaincu qui se releve",
    "la nuque d'une statue",
    "numero sept",
    # Des demandes reellement passees par ce studio le 31 aout, pendant que le
    # motif venait d'etre reecrit. « seinen » est a une lettre de « seins », et
    # c'est un genre de manga : le classer adulte aurait tenu la demande en
    # local pour rien, plusieurs minutes.
    "Dark fantasy seinen art style, alluring character",
    "Atmospheric chiaroscuro portrait, female silhouette",
    "un manga seinen des annees 90",
]

# ── ce qui doit etre reconnu : francais, anglais, et etiquettes booru ────
# Les moteurs a etiquettes reçoivent des mots colles par un souligne — et le
# souligne est un caractere de mot, donc « \b » ne separe pas « nude » de
# « _body ». C'est par la que tout un pan passait.
ADULTES = [
    # francais
    "une femme nue", "des seins", "les fesses", "nudite", "contenu erotique",
    "une scene sexuelle", "sexuellement explicite", "pornographique",
    "des photos pornos", "l'erotisme du tableau", "des nudistes",
    # anglais
    "a nude portrait", "nudes", "sexy pose", "topless", "erotic art",
    "erotically charged", "hentai", "porn", "pornography", "pornographic scene",
    "naked", "nakedness", "nudity", "nudism", "sexual content", "sexually",
    "sexualized", "sexting", "breast", "breasts", "nipples", "genitals",
    "genitalia", "penis", "vagina", "nsfw", "explicit content",
    # etiquettes collees
    "1girl, nude_body", "sex_scene", "breasts_visible", "explicit_content",
    "naked_body", "rating_explicit", "nsfw_content",
]

# ── ce que garde_fou() doit refuser ─────────────────────────────────────
# Un mineur ET du sexuel dans la meme demande. Chacune de ces lignes est passee
# au travers apres la correction du 31 aout au matin.
REFUS = [
    "a child in a sexual pose",
    "schoolgirl, sexual content",
    "child nudity",
    "toddler, nudism",
    "kid, pornographic scene",
    "1girl, loli, nude_body, explicit_content",
    "underage, sexting",
    "une enfant nue",
    "un adolescent torse nu dans une scene sexuelle",
]


def motifs():
    """Extrait les deux motifs de serveur.py sans importer le studio.

    L'importer demarrerait ses chargements et toucherait au dossier de donnees ;
    on ne veut ici que deux expressions regulieres. On les preleve par l'arbre
    syntaxique plutot qu'en decoupant du texte : le decoupage se casse au
    premier changement d'ecriture, et il s'est deja casse une fois.
    """
    src = io.open("serveur.py", encoding="utf-8").read()
    arbre = ast.parse(src)
    voulu = ("_BORD", "_FIN", "_motif", "_MINEUR", "_SEXUEL")
    espace = {"re": re}
    for noeud in arbre.body:
        nom = None
        if isinstance(noeud, ast.FunctionDef):
            nom = noeud.name
        elif isinstance(noeud, ast.Assign) and len(noeud.targets) == 1:
            cible = noeud.targets[0]
            nom = cible.id if isinstance(cible, ast.Name) else None
        if nom in voulu:
            exec(ast.get_source_segment(src, noeud), espace)
    manque = [n for n in voulu if n not in espace]
    if manque:
        raise SystemExit(f"  introuvable dans serveur.py : {manque}")
    return espace["_SEXUEL"], espace["_MINEUR"]


def main():
    sexuel, mineur = motifs()
    fautes = []

    for t in ORDINAIRES:
        m = sexuel.search(t)
        if m:
            fautes.append(f"faux positif : « {t} » pris pour « {m.group(0)} »")
    for t in ADULTES:
        if not sexuel.search(t):
            fautes.append(f"adulte NON reconnu : « {t} »")
    for t in REFUS:
        # La meme conjonction que garde_fou().
        if not (mineur.search(t) and sexuel.search(t)):
            manque = "mineur" if not mineur.search(t) else "sexuel"
            fautes.append(f"NON REFUSE (rien ne matche « {manque} ») : « {t} »")

    total = len(ORDINAIRES) + len(ADULTES) + len(REFUS)
    if fautes:
        print(f"  {len(fautes)} faute(s) sur {total} cas :")
        for f in fautes:
            print(f"    {f}")
        return 1
    print(f"  {total} cas verifies : {len(ORDINAIRES)} demandes ordinaires "
          f"laissees passer, {len(ADULTES)} reconnues adultes, "
          f"{len(REFUS)} refusees par le garde-fou.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
