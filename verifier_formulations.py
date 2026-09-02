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

    ON EMPRUNTE LA SEQUENCE, ON NE LA RECOPIE PLUS. Ce banc la reecrivait, tout
    en promettant ici meme que « toute permutation la-bas doit se voir ici » :
    il eprouvait les predicats veut_* un par un, jamais leur ordre ni les
    gardes qui les entourent. Il est donc reste vert sur LA PANNE QU'IL EXISTE
    POUR EMPECHER, celle de son propre en-tete — le detourage remis APRES la
    retouche localisee (25ce7d2), « enleve le fond » qui efface le SUJET.
    Mesure : cette mutation-la etait signalee comme trou ouvert par
    banc_mutations.py, et le banc rendait 64/64 malgre elle. Depuis qu'il
    appelle serveur.raccourci_ecrit(), elle rougit sur « enleve le fond ».

    Les deux ecritures avaient d'ailleurs deja diverge sur deux points que
    personne n'avait vus, faute de les lire cote a cote : la copie ignorait
    « modele_choisi », qui desarme TOUS ces raccourcis quand l'utilisateur a
    impose un moteur pour cette demande, et elle appelait en plus
    veut_ralenti() la ou le studio ne consulte que veut_fluidifier(). Aucun des
    deux ne changeait un verdict — _FLUIDE contient deja le ralenti — mais
    c'est exactement ainsi qu'une copie s'ecarte : sans que rien ne rougisse.

    Rien n'oblige a monter un studio pour cela, et c'est la raison d'etre des
    raccourcis ecrits : ils tranchent AVANT tout appel a un modele de langage.
    La fonction empruntee ne rend qu'un nom d'intention — le journal, le tid et
    les phrases montrees a l'utilisateur restent dans aiguiller(), qui, lui, ne
    se teste pas sans studio.

    « a_une_image » porte la FAMILLE de la piece jointe, comme dans le studio —
    « image », « video », « audio » ou False. Le banc passait un booleen, donc
    il ne pouvait pas montrer qu'une video declenchait une lecture.

    « zone_servie » est laisse par defaut : la disponibilite de SAM 3.1 est un
    etat de machine, et la calculer ferait passer ou echouer les six cas
    « retoucher_zone » selon les modeles telecharges sur la machine qui lance
    le banc. Voir la docstring de raccourci_ecrit().
    """
    return serveur.raccourci_ecrit(texte, a_une_image) or "aucun"


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
