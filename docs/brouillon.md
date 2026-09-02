# Le brouillon, et « refaire en soigné »

Quand on cherche une image, on cherche un cadrage, une lumière, une posture. Les
détails ne comptent qu'à la fin, et on les paie pourtant à chaque essai — 249 s
mesurées le 31 août 2026 sur **pc** (RTX 2080 Ti) pour une image dont on ne
savait pas encore si la composition convenait.

Le bouton **≈**, à côté de la flèche d'envoi, lance la demande **au quart des
étapes** : même moteur, même graine, même taille, quatorze secondes au lieu de
deux cent dix-sept sur la même carte, le même jour.

Il est à côté de la flèche et non dans le tiroir des réglages parce que ce n'est
pas un réglage, c'est un geste : creux là où l'envoi est plein, pour qu'on ne se
demande pas lequel presser.

## Ce qu'il ne fait pas

**Il ne prédit pas le cadrage.** C'est le point à ne pas manquer, et le code a
prétendu le contraire pendant une heure avant que quelqu'un regarde les images.

Mesure du 31 août 2026, sur **pc** : même graine 864102317, même prompt, même moteur, même
taille, sept étapes contre vingt-huit. Deux phares contre un, l'îlot centré
contre une falaise à gauche, l'éclair à gauche contre à droite. **Deux images
sans rapport.**

Le nombre d'étapes définit l'échelonnement du bruit, donc la trajectoire diverge
dès le premier pas ; la graine fixe le point de départ, pas la destination.

Le brouillon sert quand même, et c'est pour cela qu'il reste : quatorze secondes
contre deux cent dix-sept pour juger **un prompt, un moteur, une ambiance**. Ce
qu'il ne juge pas, c'est une composition.

## Refaire en soigné

Sous une esquisse terminée, un bouton **refaire en soigné** relance la même
demande avec tout le soin : même prompt, même moteur, même graine, même taille,
et le nombre d'étapes recalculé comme si le cran « brouillon » n'avait jamais
été demandé.

Le studio **ne repasse pas par l'analyse**. Elle rendrait un autre prompt, donc
un autre sujet, et l'on ne saurait plus ce qu'on compare — trois appels au
modèle de langage économisés au passage. C'est pourquoi le plan complet et la
graine sont écrits sur le tour de l'esquisse, et pourquoi ils traversent la file
d'attente : un redémarrage du studio ne fait pas perdre le bouton.

Le bouton s'appelle « refaire en soigné » et non « passer au propre » : le second
promettrait *cette* image en mieux. Son infobulle le redit, le journal de la
demande aussi — « même prompt et même moteur que l'esquisse, tout le soin — la
composition, elle, sera différente ».

Une esquisse déjà refaite porte la mention **refait en soigné** à la place du
bouton. Insister depuis un second onglet répond `409` plutôt que de lancer une
seconde grande image identique.

### Trois refus, et un seul met la coche

Le serveur refuse aussi une esquisse **non terminée** et une esquisse dont le
**moteur a quitté le catalogue**. La page traduisait ces trois refus par la même
chose : « ✓ déjà refait en soigné », coche verte et bouton retiré, alors que
**rien n'avait été rendu**. Elle ne pose désormais la coche que sur le refus qui
la mérite ; les deux autres affichent leur phrase et laissent le bouton.

Le banc certifiait pourtant le texte de ces messages — un banc vert sur un
contrat que la page n'empruntait pas, dans le banc écrit pour fermer ce
motif-là. Voir [Éprouver les bancs](eprouver-les-bancs.md).

### Une esquisse rendue au loin n'a pas de version soignée

Elle est refusée **avant** les contrôles du plan et de l'esquisse, et avec sa
vraie raison : « *cette esquisse a été rendue par …* ». Placée après eux, cette
phrase devenait injoignable et l'on recevait « ce tour n'est pas une esquisse
qu'on sache refaire » — vrai de nulle part et utile à personne. Les deux leviers
de ce bouton sont la **graine** et le **nombre d'étapes**, et un [fournisseur
distant](cles-api.md) n'expose ni l'une ni l'autre.

Le contrôle lit le moteur **du tour** et non celui du plan : sur le chemin
distant, le plan porte le repli local (voir [Ce que le tour garde du
plan](ce-que-le-tour-garde.md)). Lu sur le plan, il ne mordait jamais, et une
esquisse rendue par un fournisseur se serait refaite sur son repli — encore un
autre moteur.

Et le geste **ne part pas au loin** non plus. Ici la raison n'est pas la sûreté
— le plan d'une esquisse est complet, il porte son classement — c'est la
**comparabilité** : le studio relit le tiroir « nuage » tel qu'il est **au
clic**. Esquisse rendue à la maison, tiroir basculé trois jours plus tard, clic :
le soigné partait chez le fournisseur. Autre moteur, graine ignorée, étapes
ignorées — les trois promesses de l'infobulle rompues d'un coup, en silence, et
une ligne de facture en prime.

Ce refus-là répond **`400` et non `409`** : la page a longtemps traduit tout
`409` de cette route par « déjà refait », et un refus qui se déguise en réussite
est pire qu'un refus. La page a été corrigée depuis ; le code de retour reste
distinct, parce qu'une page se réécrit plus souvent qu'un contrat.

**À ne pas confondre avec « refaire sur la grosse carte »**, qui apparaît après
un pouce en bas. Celui-là garde la graine et change le soin ; celui-ci change la
carte et **abandonne** la graine — refaire à l'identique ailleurs rendrait la
même image, or ce qu'on demande alors est un autre tirage. Voir [Pouce en l'air,
pouce en bas](avis.md).

Le plan n'était longtemps écrit **que** sur les tours d'esquisse, au motif que
personne d'autre n'en avait l'usage. Cet argument est mort le jour où « refaire
sur la grosse carte » est né. **Depuis le 2 septembre 2026, tout tour rendu à la
maison porte son plan** — +776 o par tour d'image, mesuré, et une conversation
plafonnée à soixante tours ne dépasse pas 150 ko. Voir [Ce que le tour garde du
plan](ce-que-le-tour-garde.md).

Ce n'est pas ce plan-là qui garde la porte de ce bouton-ci : c'est la marque
**esquisse**. L'ouvrir à un rendu ordinaire promettrait « le même, avec toutes
les étapes » sur un rendu qui les avait déjà toutes.

## Où le brouillon veut dire quelque chose

Le quart des étapes ne s'applique qu'aux intentions qui reçoivent réellement des
paramètres : **image, planche, vidéo, audio**. Le détourage, l'agrandissement et
la fluidification n'en reçoivent aucun, et les trois retouches écrasent les
étapes juste après.

Marquer « esquisse » sur ces demandes-là promettait un rendu de quatorze
secondes qui en mettait deux cents, et posait un bouton « refaire en soigné » qui
échouait faute d'image source à reprendre. Le studio le dit plutôt que d'ignorer
le geste en silence :

```
le brouillon ne change rien pour ce genre de demande — elle est rendue au soin habituel
```

## Trois conséquences ailleurs

- **Le brouillon ne se retient jamais** sur la conversation, contrairement au
  moteur, à la taille, à la priorité et à la machine (voir [Moteur, priorité,
  taille](reglages-de-rendu.md)). Le garder ferait partir en brouillon les cinq
  demandes suivantes sans que personne l'ait voulu.
- **Il ne dit rien à l'aiguilleur**, contrairement à « rapide ». Un brouillon
  rendu par un *autre* moteur ne dirait rien du moteur qu'on juge.
- **Il ne compte pas dans les durées.** Ni le devis annoncé avant le rendu
  (voir [Combien de temps ça va prendre](combien-de-temps.md)), ni la médiane
  des rendus passés ne tiennent compte d'une esquisse : un quart des étapes ne
  prédit pas une image finie. Et aucun devis n'est annoncé *pour* un brouillon —
  il lui donnerait le prix d'une image finie, quatre fois trop.

## Le retrouver trois jours plus tard

Un brouillon réussi n'a aucune marque propre : même cadre, même légende, même
taille qu'une image finie. Seul le soin change, et cela ne se voit pas.

La bulle porte donc une pastille **brouillon**, la médiathèque un bandeau, et
elle sait filtrer « brouillons / images finies » — voir [Retrouver ce qu'on a
produit](mediatheque.md).
