# Une demande, plusieurs variantes

Chercher une image, c'est en voir plusieurs et choisir. Le studio n'en rendait
qu'une, et renvoyer la même phrase ne donnait pas un second tirage : l'aiguilleur
la relisait, et trois appels au modèle de langage rendent rarement deux fois le
même prompt. Une demande part désormais en plusieurs tirages : même prompt, même
moteur, même taille, seule la graine change.

## Quatre, pas davantage

`VARIANTES_MAX = 4`, vérifié avant l'entrée en file — au-delà, ou en dessous de
un : `de 1 a 4 variantes`. Zéro, la chaîne vide et le champ absent veulent tous
les trois dire « une seule », sans message : ce sont les trois façons dont une
page décrit un menu qu'on n'a pas touché.

Quatre, parce que quatre variantes sont quatre rendus. À quatorze secondes
l'esquisse sur la petite carte, quatre tiennent dans la minute ; à deux minutes
l'image finie, elles occupent les deux machines quatre minutes durant — et la
file de tout le monde avec.

## N demandes dans la file, et non un `batch_size`

C'est la décision qui porte tout le reste, et **ce n'est pas la vitesse qui l'a
prise**. Un graphe à `batch_size` 4 serait plus rapide sur une carte : un seul chargement
de modèle pour quatre images. Mais ComfyUI tire le bruit du lot entier d'un seul
coup, et **aucune de ses images ne porte alors de graine à elle**. Or la graine
est ce qui permet de choisir : c'est elle qu'on écrit dans la file pour qu'une
reprise après redémarrage refasse *la même* image, et c'est elle que vise
« refaire en soigné » sur la variante retenue (voir [Le
brouillon](brouillon.md)). Sans graine par image, il n'y a plus rien à viser. Un
lot est de surcroît indivisible : il ne se répartit pas sur deux machines et ne
s'annule pas à l'unité.

Le studio met donc **une entrée de file par tirage**. Le banc le vérifie sur le
graphe *réellement soumis* et non sur ce que le tour recopie — un tour peut
porter une graine que personne n'a employée : quatre graines distinctes,
`batch_size` à 1 partout.
Le parc de la maison le montre. Le plus petit moteur d'image du catalogue,
FLUX.2 klein 9B, demande 6,0 Go ; la carte du NAS ZimaOS — une GTX 1060 — en
offre 5,9. Elle n'en tient donc **aucun**, à plus forte raison pas quatre images
à la fois : les quatre tirages font la queue sur le PC. Qu'une seconde carte
capable arrive, et les mêmes quatre se répartissent tout seuls entre les deux
machines. Un lot n'aurait pas su le faire. Voir [Plusieurs
machines](plusieurs-machines.md).

## Le plan est établi une fois

L'aiguillage, l'enrichissement et la traduction tournent pour le premier tirage ;
les suivants reçoivent son plan tout fait, par `plan_impose` — le même chemin que
« refaire en soigné », à une différence près : celui-là impose aussi la graine,
celui-ci est le seul à la laisser libre. Trois appels au modèle de langage
économisés par variante, mais ce n'est pas l'argument : refaits, ils rendraient
un autre prompt, donc un autre sujet, et le groupe perdrait sa raison d'être. Le
journal de chaque tirage le dit — « meme prompt, meme moteur et meme taille pour
tout le groupe, seule la graine change d'une variante a l'autre ».

## Chaque tirage est un tour entier

Pas un tour à quatre fichiers : quatre tours, reliés par un marqueur.

```json
"variantes": {"groupe": "<id du premier tirage>", "rang": 2, "sur": 4}
```

Sur le **tour** et pas seulement sur la tâche : les tâches s'effacent au bout de
deux cents demandes, et c'est la conversation rechargée trois jours plus tard qui
doit encore savoir que ces quatre images étaient un seul geste. Le marqueur
survit à la réécriture du tour, comme le pouce — sans quoi un tour repris après
un redémarrage sortait de sa rangée : trois images côte à côte, la quatrième
toute seule plus bas.

D'où un effet qu'on n'a pas eu à écrire : **tout ce qui existait déjà
fonctionne**. Le pouce, la médiathèque, « refaire en soigné » qui vise le tour
cliqué — et le retrait d'un seul tirage : un `DELETE /api/file/<tid>` en retire
un, les autres restent, et la retirée garde son rang.

Après un redémarrage, **N images et non N + (N−1)** : le premier tirage retombe à
`variantes: 1` dans le fichier de file dès qu'il a lancé les autres, et le
fichier est écrit avant la mise en file. Il y garde aussi **son** plan, comme ses
sœurs — mesuré au banc, sans cette ligne un réveil en plein groupe le renvoyait à
l'aiguilleur et son prompt s'écartait des trois autres.

## « La » ne se joue pas à la course

« Agrandis-la », « rends-la fluide », « le même personnage » visent l'image
courante de la conversation. De quatre variantes, la courante était la dernière
**arrivée** — deux machines, deux vitesses, un ordre que personne ne choisit.
C'est donc **la première du groupe** qui tient le rang, même finie en dernier,
jusqu'à ce qu'on en désigne une autre : `POST /api/variante`, avec la
conversation et le tour. Choisir ne supprime rien — chaque variante reste un tour
entier — et une seule à la fois porte la marque, sinon deux images se disent
« la ». Le [personnage de référence](garder-le-meme-personnage.md) suit la
variante choisie, mais seulement s'il y en avait déjà un. La conversation d'un
autre, un tour inconnu, un tour qui n'a rien produit : `404` dans les trois cas.

## Où l'on s'arrête

`VARIANTES_POSSIBLE = ("image", "planche")`. **On ne multiplie que ce qui est
inventé.**

- Les [retouches](retouche-localisee.md), le [détourage](detourer.md),
  l'[agrandissement](agrandir-une-image.md) et la
  [fluidification](fluidifier-une-video.md) partent d'une image **donnée** : la
  graine n'y décide plus la composition, elle n'ajuste qu'un débruitage déjà
  contraint. Quatre tirages rendent quatre fois la même chose au bruit près.
- La vidéo et l'audio sont éligibles au [brouillon](brouillon.md) mais **pas**
  aux variantes : une vidéo coûte six minutes, une animation douze (voir
  [Mesures](mesures.md)). Quatre fermeraient les deux machines pour trois quarts
  d'heure sur un seul geste, et le studio n'a que trois travailleurs.
- Un [fournisseur distant](cles-api.md) facture chaque image, et le plafond du
  mois compte des appels : quatre variantes le videraient quatre fois plus vite,
  pour un geste dont personne ne voit le prix (voir [Ce que le nuage a
  coûté](cout-du-nuage.md)). Les cartes de la maison ne coûtent que du temps.

Dans les trois cas le studio le **dit** ; un réglage ignoré en silence donne le
sentiment de ne pas être écouté :

```
les variantes ne changent rien pour ce genre de demande — elle est rendue une seule fois
```

## Le devis compte les quatre

Le [devis annoncé avant le rendu](combien-de-temps.md) ne parlerait sinon que du
premier tirage. Il annonce le groupe, en **temps de carte** et non en temps
d'attente : combien de machines seront libres à cette seconde-là, personne ne le
sait, et promettre la moitié parce qu'il y a deux cartes serait promettre à la
place du voisin qui a lui aussi une demande en file.

```
4 variantes, donc autant de rendus — environ 12 min de calcul en tout,
reparti sur les machines libres
```

Le total n'est chiffré que s'il y a de quoi le chiffrer : trois rendus
comparables au moins, et jamais pour un brouillon.

## Les retrouver, et ne pas les garder

Quatre variantes ont le même prompt, le même moteur, la même taille et la même
minute : sans leur rang, la [médiathèque](mediatheque.md) en montrait quatre
lignes rigoureusement indiscernables. Chaque pièce porte donc son numéro —
**variante 2 sur 4** — et la marque de celle qui a été retenue.

Le nombre de variantes, lui, ne se retient **pas** sur la conversation,
contrairement au moteur, à la taille, à la priorité et à la machine (voir
[Moteur, priorité, taille](reglages-de-rendu.md)). C'est un geste, comme le
brouillon : le garder ferait partir en quatre exemplaires les cinq demandes
suivantes, sans que personne l'ait voulu.

## Ce que le banc vérifie

Tout ce qui précède est du serveur, et `banc_variantes.py` en vérifie
**quatre-vingt-quatorze décisions** — relevé le 1er septembre 2026 ; le banc
grossit, relance-le plutôt que de recopier ce nombre.

Le geste a longtemps existé sans que la page l'emprunte : `web/index.html` ne
postait aucun champ `variantes`, et la légende de la médiathèque laissait de
côté le rang et la marque que `/api/mediatheque` lui servait déjà. Un banc qui
teste un contrat que personne n'emprunte ne mesure rien — c'est le défaut que
décrit `CONTRIBUTING.md`, et c'est pour cela que `banc_page.py` relit désormais
la page elle-même : le menu envoie le nombre par les **deux** chemins d'envoi,
la bulle affiche « variante 2 sur 4 », et `POST /api/variante` part du bouton
qui désigne celle que « la » vise.
