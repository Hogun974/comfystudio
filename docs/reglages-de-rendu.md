# Moteur, priorité, taille, machine

## Les réglages appartiennent à la conversation

Quatre réglages sont à toi : le **moteur**, la **taille**, la **priorité** et la
**machine**. Ils vivent sur la **conversation**, pas sur la fenêtre : une
conversation travaille en FLUX.1 1920×1080, une autre en RealVis 1024×720, et
chacune garde le sien tant que son propriétaire ne le change pas. Les menus
reprennent l'état de la conversation qu'on ouvre.

Ils l'étaient à la fenêtre, et deux choses cassaient. Changer de conversation
emportait le réglage de la précédente. Et surtout, le formulaire de réponse à
une question n'envoyait que la taille et la priorité : le moteur imposé et la
machine choisie disparaissaient à la seconde où l'on répondait. Corriger cette
liste-là aurait fermé ce cas et laissé le suivant ouvert — sur la conversation,
**aucun chemin d'envoi ne peut plus les oublier**, celui qui tait un réglage
hérite.

**Présence et non valeur.** Une clé absente est héritée ; une clé présente, même
vide, remplace. C'est la seule façon de distinguer « je n'en parle pas » de
« remets sur automatique », et les deux arrivent.

**Choisir, c'est déjà décider.** Un réglage pris dans le menu est posé sur la
conversation tout de suite, sans rien lancer — avec les mêmes contrôles que pour
une demande : un moteur inconnu ne doit pas dormir sur une conversation en
attendant de la faire échouer plus tard. Avant, il n'était écrit qu'au moment de
générer, et le choix n'existait plus si l'on passait voir ailleurs entre-temps.

**Le brouillon ne se retient jamais** : c'est un geste, pas un réglage. Le garder
ferait partir en brouillon les cinq demandes suivantes sans que personne l'ait
voulu. Voir [Le brouillon](brouillon.md).

La machine retenue dans le navigateur ne sert plus que de point de départ à une
conversation neuve.

Laissée sur **automatique**, la machine est choisie par le studio : la plus
petite carte qui tient le moteur pour un rendu, la plus grosse libre pour
l'analyse qui le précède. La règle entière est dans [Qui prend le
travail](qui-prend-le-travail.md).

## Un changement s'écrit dans le fil, chuchoté

Un réglage qui change laisse une trace dans la conversation elle-même — pas
seulement à l'écran. La question « pourquoi cette image est-elle en 1024 ? » se
pose des jours plus tard, quand le journal du studio a disparu depuis longtemps.

```
                              moteur : RealVisXL V5.0 · taille : 1024 × 1024
```

Ni bulle, ni auteur, ni horodatage en évidence : une didascalie en italique pâle,
assez discrète pour qu'on la lise seulement quand on la cherche. Elle s'ancre
**après le dernier tour existant** et se relit à sa place dans le fil.

Un seul murmure par geste, même s'il porte sur plusieurs réglages — la page les
envoie ensemble, et quatre lignes pour un geste seraient du bruit. Les valeurs
sont nommées en clair, « RealVisXL V5.0 » et non `realvis`, « 1024 × 1024 » et
non `1024x1024` : une clé ne veut rien dire trois jours après.

Les murmures sont bornés à soixante par conversation, comme les tours.

## Choisir la résolution

Le menu à côté du moteur impose une taille : 1920×1080, 1280×720, carré,
portrait… « automatique » laisse le studio décider (1216×832 par défaut, au-delà
le temps de rendu explose sans gain réel).

Une taille choisie ici échappe à ce plafond, comme une taille écrite dans la
demande. Le décodage par tuiles s'enclenche seul au-delà de 1216×832 : mesuré le
28 août 2026 sur **pc**, un 1920×1080 sort propre en 156 s sur 11 Go.

## Rapide, soigné — et le brouillon à part

Le menu de priorité arbitre entre temps et qualité. Il agit à deux endroits :

- **l'aiguilleur** reçoit la consigne et choisit son moteur en conséquence ;
- **le code** ajuste les étapes, la seule grandeur qui échange vraiment du temps
  contre de la qualité à modèle constant. Les bornes par intention gardent la
  main : « rapide » ne descend jamais sous le minimum qui produit encore
  quelque chose.

Mesuré le **28 août 2026 sur pc** (RTX 2080 Ti), sur la même demande, en
1024×1024 :

| Priorité | Moteur retenu | Étapes | Durée |
|---|---|---|---|
| rapide | FLUX.2 klein 4B | 12 | 60 s |
| soigné | FLUX.2 klein 9B | 40 | 162 s |

L'aiguilleur n'a pas seulement changé le nombre d'étapes : il a pris un modèle
plus riche. C'est le comportement voulu — la priorité porte sur le résultat, pas
sur un réglage.

Le facteur appliqué aux étapes est de **0,6 pour « rapide » et 1,35 pour
« soigné »**, borné par intention : « rapide » ne descend jamais sous le minimum
qui produit encore quelque chose.

Un troisième cran existe, **le brouillon à 0,25** — mais il n'est pas dans ce
menu, il a son propre bouton à côté de la flèche d'envoi, il ne se retient pas
sur la conversation et il ne dit rien à l'aiguilleur. Il a sa page :
[Le brouillon](brouillon.md).

## Quand un réglage n'est pas suivi

Les quatre réglages sont respectés — avec trois exceptions, qui se disent
maintenant dans le déroulé technique plutôt que de passer sous silence.

**Le moteur imposé ne change plus jamais.** Il pouvait l'être : quand la
traduction du prompt échouait, le studio basculait sur FLUX.2 klein, qui
comprend le français. Bonne idée quand c'est lui qui a choisi le moteur,
mauvaise quand c'est toi. Désormais ton choix l'emporte, le prompt reste en
français, et le déroulé dit pourquoi.

**La taille ne s'applique pas partout.** Une édition reprend la taille de
l'image d'origine, une vidéo celle de son format, un maillage et un son n'ont
pas de résolution. Le studio l'écrit maintenant noir sur blanc :

```
taille 1920x1080 sans effet ici : un son n'a pas de resolution
```

Le menu de taille se grise déjà quand tu imposes un moteur concerné — mais en
mode automatique, c'est l'aiguilleur qui décide, et le message est le seul moyen
de le savoir.

**Un moteur ne recouvre pas une demande qui n'en a pas besoin.** Décrire une
image ne produit rien, aucun moteur ne s'y applique ; et un moteur seulement
*hérité* de la conversation ne défait pas ce qu'un raccourci écrit — détourer,
agrandir, fluidifier — vient de trancher. S'il avait été choisi pour cette
demande, le raccourci ne se serait pas déclenché du tout. Là encore, on le dit
plutôt que d'ignorer un réglage en silence :

```
Veo 3.1 est le moteur de cette conversation, mais cette demande n'en a pas besoin
```

Un moteur **distant** hérité tombe avec lui. Sans cela, une vidéo jointe avec
« rends-la fluide », sur une conversation réglée sur Veo, partait produire une
vidéo neuve chez Veo — facturée à la seconde, et sans rapport avec la demande.
