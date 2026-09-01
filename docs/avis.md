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

Il ne s'affiche que sur un tour **fini qui a produit quelque chose**, et
disparaît une fois utilisé : refaire un échec, c'est relancer la même panne.

L'escalade voyage sur l'entrée de file et non sur la conversation. Elle survit
donc à un redémarrage du studio comme le reste de la file, et une autre demande
lancée entre-temps ne peut pas se la prendre. La grosse carte se choisit **avant**
le filtre de charge : la prendre parmi les moins chargées seulement, c'est
retomber sur la petite dès qu'un rendu vise la grosse — voir [Qui prend le
travail](qui-prend-le-travail.md).
