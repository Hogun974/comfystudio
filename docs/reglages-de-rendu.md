# Moteur, priorité, taille

## Choisir la résolution

Le menu à côté du moteur impose une taille : 1920×1080, 1280×720, carré,
portrait… « automatique » laisse le studio décider (1216×832 par défaut, au-delà
le temps de rendu explose sans gain réel).

Une taille choisie ici échappe à ce plafond, comme une taille écrite dans la
demande. Le décodage par tuiles s'enclenche seul au-delà de 1216×832 : mesuré,
un 1920×1080 sort propre en 156 s sur 11 Go.

## Rapide ou soigné

Le menu de priorité arbitre entre temps et qualité. Il agit à deux endroits :

- **l'aiguilleur** reçoit la consigne et choisit son moteur en conséquence ;
- **le code** ajuste les étapes, la seule grandeur qui échange vraiment du temps
  contre de la qualité à modèle constant. Les bornes par intention gardent la
  main : « rapide » ne descend jamais sous le minimum qui produit encore
  quelque chose.

Mesuré sur la même demande, en 1024×1024 :

| Priorité | Moteur retenu | Étapes | Durée |
|---|---|---|---|
| rapide | FLUX.2 klein 4B | 12 | 60 s |
| soigné | FLUX.2 klein 9B | 40 | 162 s |

L'aiguilleur n'a pas seulement changé le nombre d'étapes : il a pris un modèle
plus riche. C'est le comportement voulu — la priorité porte sur le résultat, pas
sur un réglage.

## Quand un réglage n'est pas suivi

Trois réglages sont à toi : le moteur, la priorité et la taille. Ils sont
respectés — avec deux exceptions, qui se disent maintenant dans le déroulé
technique plutôt que de passer sous silence.

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
