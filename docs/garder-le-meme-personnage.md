# Garder le même personnage

Le studio savait modifier une image ; il ne savait pas en produire une
**nouvelle** en gardant quelqu'un. C'est pourtant ce qu'on demande dès qu'on
travaille sur un personnage : une fiche, puis le même en pied, puis le même
sous la pluie.

Il suffit de l'écrire : « le même personnage, sous la pluie », « garde ce
personnage », « la même, de profil ». La première image devient la référence de
la conversation, et les demandes suivantes s'y rapportent sans avoir à la
redésigner.

Le mécanisme vient du workflow officiel *Flux.2 Klein : Image Edit*, qui
enchaîne des nœuds `ReferenceLatent`. Le studio s'en servait déjà pour
l'édition, avec une limite qui interdisait cet usage : **la taille de sortie y
est prise sur l'image d'entrée**. Pour une scène neuve il faut découpler les
deux — la référence dit *qui*, le format dit *comment on cadre*.

Deux pièges traités :

- L'aiguilleur lit « le même personnage, au bord de la mer » comme une
  **retouche** une fois sur deux. Les mots de l'utilisateur tranchent : c'est
  une image neuve.
- Le moteur d'édition est distillé à **quatre étapes**. Assez pour corriger un
  détail, très insuffisant pour dessiner une scène entière : la voie du
  personnage prend les réglages d'image (20 étapes, cfg 5).

Ce qu'on obtient, mesuré : le costume, la coiffure, la silhouette et les
cicatrices se conservent nettement ; le visage reste ressemblant mais rajeunit
un peu, et les teintes suivent l'éclairage de la nouvelle scène.
