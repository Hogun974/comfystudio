# Pouce en l'air, pouce en bas

Chaque réponse porte 👍 / 👎, et un pouce en bas ouvre un champ libre. Le retour
est consigné dans `avis.jsonl` — pas dans la conversation, que son propriétaire
peut supprimer — avec la demande, le moteur, les réglages, le style envoyé et
les paroles : de quoi refaire le cas sans redemander à personne. La page
`/admin` en donne le récapitulatif.

Le fichier est exclu du dépôt : il contient les demandes des utilisateurs.

## « Refaire sur la grosse carte »

Un pouce en bas fait apparaître un bouton **« refaire sur la grosse carte »**
(`POST /api/refaire`). Il reprend le prompt, le moteur et la taille, ne repasse
pas par l'analyse, et vise la plus grande carte du parc — **quitte à
l'attendre**.

Ce qu'il rejoue, c'est le **plan écrit sur le tour** : le prompt traduit, le
moteur, la taille, les paramètres, le classement, les paroles et leur langue.
Depuis le 2 septembre 2026 tout tour rendu à la maison en porte un, et il n'y a
donc plus rien à reconstruire — donc plus rien à oublier de reconstruire. Six
défauts en deux jours, dont un de sûreté, sont venus de cette reconstruction :
voir [Ce que le tour garde du plan](ce-que-le-tour-garde.md), qui décrit aussi
le repli pour les tours plus anciens.

**Deux gestes, parce que ce sont deux décisions.** Le pouce dit que c'est raté,
le bouton dit quoi faire. Le pouce en bas armait auparavant la demande
*suivante*, quelle qu'elle soit : « et maintenant de nuit » repartait sur la
grosse carte sans que personne l'ait voulu, et le signal se perdait si l'on ne
redemandait pas tout de suite.

**La graine n'est pas reprise**, et c'est la différence avec « refaire en
soigné » (voir [Le brouillon](brouillon.md)). Refaire à l'identique sur une autre
carte rendrait la même image ; ce qu'on demande ici est un **autre tirage**. Le
bouton dit « refaire » et non « améliorer » — le studio ne sait pas améliorer, il
sait recommencer avec plus de carte.

Il ne s'affiche que sur un tour **fini qui a produit quelque chose** : refaire
un échec, c'est relancer la même panne.

## Deux refus, et ce qu'ils disent

Le plan rejoué a été écrit il y a peut-être des semaines, et le studio, lui, a
bougé. Deux cas sont refusés avec une phrase, là où le studio répondait
auparavant « ERREUR : 'sdxl_vieux' » ou « ERREUR : 'veo' » — un message qui
n'apprend rien, et surtout pas ce qui a changé :

- **Le moteur a quitté le catalogue.** « le moteur de ce tour (…) n'est plus au
  catalogue : relance la demande pour en choisir un autre ».
- **Le rendu avait été confié à un fournisseur distant.** Ce bouton-ci demande
  une carte de la maison — c'est ce que son libellé dit. « Relance la demande
  pour repartir chez lui. »

Le geste **ne part jamais au loin**, et c'est posé explicitement sur le plan
(`modele_impose`) plutôt que déduit. Sans cette marque, le studio rappelait son
choix de fournisseur sur le plan rejoué, et `adulte()` y lit `classement` — que
les tours écrits avant le 1er septembre 2026 ne portent pas. Un rendu marqué
explicite dont le texte est anodin serait parti chez un fournisseur, contre la
règle « ce qui est adulte ne sort pas de la maison ». Le moteur vient du tour,
pas de l'aiguillage : il n'y a rien à re-router.

## Un refait raté rend son bouton

La marque est posée **avant** le rendu — c'est elle qui empêche deux onglets
d'en lancer deux, comme pour « refaire en soigné ». Mais insister depuis un
second onglet répond `409` seulement tant que le premier essai tient.

**Un refait qui échoue rend son bouton.** Ce geste *est* la réparation d'un
rendu raté : le condamner sur un échec serait l'inverse de « refaire en
soigné », où le premier essai, lui, a réussi.

**Une annulation aussi.** Le `409` est là pour empêcher deux rendus sur la
grosse carte, pas pour punir. Une annulation ne laisse aucune image ; refuser le
geste ensuite retirerait pour toujours la réparation d'un rendu raté à cause
d'un clic sur « retirer ».

**Sauf quand la demande va repartir toute seule.** L'arrêt du studio et
l'annulation par l'utilisateur passent par la même interruption, et le studio
les sépare par le test exact du travailleur. Coupée par l'arrêt, la demande
reste dans `_file.json` et repart au réveil — rendre le bouton là, c'était
l'offrir au moment précis où le refait redémarre seul, donc les deux rendus que
le `409` existe pour empêcher.

Reste une fenêtre qu'on ne ferme pas, et il vaut mieux la connaître : un rendu
qui échoue **vraiment** pendant les quelques secondes de l'arrêt garde sa marque
et perd son bouton. C'est la mauvaise moitié du choix, et c'est celle de
« refaire en soigné » — un bouton disparu plutôt qu'un second rendu.

Une machine qui lâche sans que la demande meure ne passe pas par là : le studio
reprend sur une autre carte sans rien écrire, et la marque doit rester — c'est
le même travail qui continue.

## Où l'escalade voyage

L'escalade voyage sur l'entrée de file et non sur la conversation. Elle survit
donc à un redémarrage du studio comme le reste de la file, et une autre demande
lancée entre-temps ne peut pas se la prendre. La grosse carte se choisit **avant**
le filtre de charge : la prendre parmi les moins chargées seulement, c'est
retomber sur la petite dès qu'un rendu vise la grosse — voir [Qui prend le
travail](qui-prend-le-travail.md).
