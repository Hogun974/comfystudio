#!/usr/bin/env python3
"""Verifie que les formulations reconnues A L'ECRIT partent au bon endroit.

Avant le classifieur et avant le modele de langage, le studio tranche certaines
demandes sur leur seule formulation : detourer, agrandir, fluidifier, et les
trois retouches localisees. C'est ce qui epargne dix secondes d'appel a chaque
fois — et c'est aussi ce qui casse en silence quand deux motifs se recouvrent.

Ce banc existe pour une faute precise, qui a eu lieu : les retouches ont ete
reconnues AVANT le detourage, alors que « enleve le fond », « retire
l'arriere-plan » et « mets-la sur fond transparent » sont les formulations du
detourage depuis le premier jour. « Enleve le fond » remplaçait donc le SUJET —
l'inverse exact de la demande. Rien ne l'aurait signale : le studio rendait une
image, simplement pas la bonne.

Les bancs du classifieur ne couvrent pas ce chemin : ils mesurent ce que le
modele bayesien decide, pas ce que les expressions regulieres court-circuitent
avant lui.

    python verifier_formulations.py
"""
import io
import json
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)

import serveur  # noqa: E402

BANC = os.path.join(ICI, "banc_formulations.jsonl")


def aiguillage_ecrit(texte, a_une_image=False):
    """Ce que le studio decide sur la seule formulation, dans SON ordre.

    L'ordre est ce qu'on verifie : le recopier ici serait sans valeur. On appelle
    donc les memes fonctions, dans la sequence du fichier serveur.py — toute
    permutation la-bas doit se voir ici.

    « a_une_image » porte la FAMILLE de la piece jointe, comme dans le studio —
    « image », « video », « audio » ou False. Le banc passait un booleen, donc
    il ne pouvait pas montrer qu'une video declenchait une lecture.

    L'ORDRE EST CELUI DE serveur.py, et il ne l'etait pas : les trois retouches
    localisees s'executent AVANT tous les raccourcis testes ici, et la lecture
    APRES la fluidification. Un banc qui recopie un ordre faux ne prouve rien —
    55/55 en vert ne disait alors rien de la sequence reelle.
    """
    if a_une_image == "image" and not serveur.veut_detourer(texte):
        for reconnait, quoi in ((serveur.veut_zone_nommee, "retoucher_zone"),
                                (serveur.veut_retoucher_fond, "retoucher_fond"),
                                (serveur.veut_retoucher_sujet, "retoucher_sujet")):
            if reconnait(texte):
                return quoi
    if serveur.veut_fluidifier(texte) or serveur.veut_ralenti(texte):
        return "fluidifier"
    if a_une_image == "image" and serveur.veut_lire(texte):
        return "lecture"
    if serveur.veut_detourer(texte):
        return "detourer"
    if serveur.veut_agrandir(texte):
        return "agrandir"
    return "aucun"


def main():
    cas = []
    with io.open(BANC, encoding="utf-8") as f:
        for n, ligne in enumerate(f, 1):
            if ligne.strip():
                cas.append((n, json.loads(ligne)))
    fautes = []
    for n, c in cas:
        obtenu = aiguillage_ecrit(c["texte"], c.get("image") or False)
        if obtenu != c["attendu"]:
            fautes.append((n, c["texte"], c["attendu"], obtenu))
    print(f"  {len(cas) - len(fautes)}/{len(cas)} formulations aiguillees comme prevu")
    for n, texte, attendu, obtenu in fautes:
        print(f"    ligne {n} : « {texte} »")
        print(f"      attendu {attendu}, obtenu {obtenu}")
    # Aucune tolerance : ce banc ne mesure pas une justesse statistique, il
    # protege des decisions ecrites a la main. Une seule qui change est une
    # regression, pas du bruit.
    return 1 if fautes else 0


if __name__ == "__main__":
    sys.exit(main())
