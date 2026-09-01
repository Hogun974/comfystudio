# Ne changer qu'une partie de l'image

« change le fond », « enlève la personne », « change seulement le ciel »,
« enlève le panneau ». Le studio refait la zone visée et recolle le reste à
l'identique. La demande est reconnue **à l'écrit**, comme le détourage et
l'agrandissement.

| Tu écris | Ce qui est refait | Ce qui trouve la zone |
|---|---|---|
| « change le fond », « mets un autre arrière-plan » | le décor ; le sujet est gardé | BiRefNet |
| « enlève le sujet », « efface la personne » | le sujet ; le décor est gardé | BiRefNet |
| « change seulement le ciel », « enlève le chien », « remplace le panneau » | la zone **nommée** | SAM 3.1 |

Les deux premiers n'exigent rien de plus que ce qui sert déjà au détourage. Le
troisième demande un téléchargement de 1,63 Gio, et n'apparaît dans la liste
des moteurs que si une machine du parc le porte.

Sur **pc** (RTX 2080 Ti), en 1216×832 et à chaud, la chaîne complète a été mesurée entre
6,5 et 11,6 s aux 4 étapes du moteur d'édition, masque compris. Une étendue à
refaire monte à 16 étapes et double à peu près ce temps — 11,4 s puis 23,0 s
sur la même image. Toutes les mesures de ce chapitre viennent des deux essais
menés le 30 août 2026 — l'un sur la retouche, l'autre sur le masque par
description — chacun sur une ou deux images et une seule graine.

## Hors du masque, l'image est identique

Pas « presque ». Même image, même graine, écart moyen en niveaux 0-255 sur les
pixels situés hors du masque ; `p99` est le 99ᵉ centile de cet écart, `%>2` la
part des pixels dont un canal bouge de plus de deux niveaux.

| Route | Écart hors masque | p99 | %>2 |
|---|---|---|---|
| l'édition d'image ordinaire (témoin) | 27,100 | 226 | 99,01 |
| plancher : un simple aller-retour par le VAE | 1,281 | 8 | 25,70 |
| masquage du bruit dans le latent, seul | 1,183 | 8 | 21,40 |
| le même, sur une grande zone (le ciel, 38,8 % du cadre) | 7,715 | 31 | 76,93 |
| **retenu — masquage + recollage en pixels** | **0,000** | **0** | **0,00** |

L'édition ordinaire déplace 99 % des pixels : elle rend une image neuve, pas
une retouche. Deux pièces obtiennent le zéro, et aucune n'est décorative.

- **Le recollage en pixels.** Le masquage du bruit est exact *dans le latent*,
  mais le décodeur du VAE n'est pas local : quand la zone masquée change
  beaucoup, le décodage du reste bouge aussi — 4,29 sur une boîte, 7,72 sur le
  ciel, 12,93 sur une bande. Le recollage ramène à 0,000.
- **Le seuillage du masque BiRefNet.** Loin du sujet, ce masque ne vaut pas 0
  mais 0,0015 — invisible dans un PNG 8 bits, bien présent dans le graphe.
  Sans seuillage, le recollage laisse 0,554 niveau d'écart sur **toute**
  l'image ; avec, 0,000. C'est la différence entre « le reste est intact » et
  « presque ».

Une troisième par soustraction : **l'image n'est pas remise à l'échelle.** Le
graphe d'édition ramène tout à 1 Mpx ; mesuré, une source de 1216×832 en
ressortait en 1238×847, donc rééchantillonnée partout. L'échantillonneur
travaille ici à la taille de la source.

Le bord ne se voit pas non plus. Le masque de recollage est flouté sur 11 px :
à échantillonnage strictement identique, l'excès de crête au contour tombe de
2,48 (recollage dur) à 0,98. Au-delà de 11 on ne gagne plus rien et on
contamine une bande de plus en plus large de l'original.

## Pourquoi ne pas garder le graphe d'édition et recoller

C'était la voie la plus simple, et elle a été mesurée avant d'être écartée. Sur
« remplace le cerf par un gros rocher » : préservation parfaite (0,000 après
seuillage) et **édition nulle**. Le moteur global avait posé le rocher hors du
masque, et le recollage l'a effacé. Un moteur global n'a aucune raison de
placer son édition là où on l'attend. La préservation seule ne prouve rien.

## `ReferenceLatent` est retiré, et le studio décrit au lieu d'ordonner

Le graphe d'édition branche un nœud `ReferenceLatent` pour donner l'image de
départ au moteur. Tant qu'il est là, le moteur redessine le contenu d'origine
**à l'intérieur du trou** : on demande de remplacer le cerf par un rocher, il
dessine un rocher derrière le cerf, qui reste. Ce n'est pas une question de
pas — à 8 étapes au lieu de 4 le cerf est toujours là, et le rendu passe de
16,6 à 29,2 s.

Retiré, le moteur n'a plus que le texte pour remplir le trou. La conséquence
est pour toi : **le texte doit décrire, pas ordonner.** « enlève la voiture »
ne lui apprend rien — c'est même le seul objet nommé, il en dessinerait une. Le
studio fait donc un appel de langage séparé qui traduit ton ordre en
description de ce qu'il faut voir : « la route vide, asphalte mouillé, même
lumière ». Le contrôle est en code, pas dans la consigne : une description qui
garde un verbe de suppression est refusée, et le studio rend la main plutôt que
de payer un rendu pour rien.

C'est cette phrase-là qui décide de l'image, et non la tienne. Elle est donc
écrite dans le déroulé de la tâche :

```
zone visee : « the sky » (etendue) — a la place : un ciel d'orage, nuages
sombres, lumiere basse
```

Le retrait paie aussi son propre coût : le rendu tombe de 16,60 à 10,06 s, la
latente de référence doublant la longueur de séquence en attention.

## La cible est traduite en anglais, et le français ne rend pas un masque vide

SAM 3.1 embarque son propre encodeur de texte : un CLIP-L d'origine OpenAI,
anglais, 32 jetons au maximum. **Il ne rend pas un masque vide sur du français.
Il rend la mauvaise zone, sans rien signaler.** Aire du masque, en % du cadre,
sur une image dont l'objet dominant est une voiture :

| Demandé | En anglais | En français |
|---|---|---|
| le ciel | 15,36 | 15,39 — **c'est la voiture** (IoU 0,9975 avec « the car ») |
| la haie | 30,10 | 15,40 — la voiture |
| les roues | 0,36 | 15,45 — la voiture |
| les nuages, l'herbe, le panneau | 2,60 / 2,99 / 1,07 | 0,00 |

Le détecteur pose volontiers une détection sur l'objet dominant quoi qu'on lui
demande : `blorpf` rend la voiture avec un IoU de 0,9948. Un masque net, bien
découpé, sur le mauvais objet — aucune inspection rapide ne le rattrape.

Deux réglages en découlent. Le seuil de détection est à **0,70** et non 0,50 :
les vraies détections ne bougent pas d'un centième entre 0,30 et 0,95, tandis
que le charabia meurt à 0,70. Il ne suffit pourtant pas — « le ciel » rendant
la voiture survit à un seuil de 0,95. D'où la traduction, faite avant l'appel,
en trois mots au plus.

Une fois la cible en anglais, le masque tient : IoU **0,905** pour « the sky »
contre une référence construite sans SAM, là où la meilleure bande horizontale
possible — le repli géométrique qu'on aurait pris à défaut — plafonne à 0,584.
Sur un sujet que BiRefNet sait déjà trouver, les deux s'accordent à 0,983. Et
« the road sign » rend le panneau sans son mât.

Le masque n'est pas dilaté de la même façon selon la cible, et il n'y a pas une
bonne valeur mais deux : 24 px pour remplacer un **objet**, sinon il reste un
fantôme de la silhouette (crête 9,93 contre 0,89) ; 0 px pour refaire une
**étendue**, parce qu'à 24 le masque du ciel mange 9,33 % de l'image sur les
arbres — branches fines et ligne d'arbres lointaine effacées. C'est le même
appel de langage qui tranche, en même temps que la cible et la description.

Ces 24 pixels ont été mesurés sur une image d'environ mille pixels de côté, et
le code garde donc la **proportion** — `cote × 24 / 1024`, au moins huit
pixels. Écrits en dur, ils feraient un liseré qui laisse le fantôme sur une
source de 2048, et une morsure deux fois trop large sur une vignette de 512.

## SAM 3.1 : un téléchargement optionnel, sous une licence qui n'est pas libre

Le fichier est `sam3.1_multiplex_fp16.safetensors`, **1,63 Gio** — 1 745 546 848
octets vérifiés sur le fichier téléchargé, pas repris d'une fiche. Il vient du
repaquetage `Comfy-Org/sam3.1`, sans jeton ni formulaire, contrairement au
dépôt Meta d'origine. En calcul il ne coûte rien de plus que l'existant : 1,2 s
à chaud pour le masque, contre 1,23 s pour BiRefNet.

Sa licence — la « SAM License » de Meta — mérite d'être lue avant l'installation :

- **l'usage commercial est autorisé.** Le mot « commercial » n'apparaît pas une
  fois dans le texte, et il n'y a pas de seuil d'utilisateurs.
- **Mais ce n'est pas une licence libre.** Toute redistribution des poids ou
  d'un dérivé doit se faire sous ces mêmes termes ; la rétro-ingénierie est
  interdite ; des clauses ITAR et de sanctions s'appliquent ; Meta peut
  modifier l'accord unilatéralement, avec effet immédiat.

Le studio est sous AGPL-3.0, et les deux ne se contredisent pas : les poids ne
sont ni du code du studio ni liés à lui, c'est l'utilisateur qui va les
chercher. Ce n'est pas pour autant la même chose que les autres entrées du
catalogue, qui sont Apache ou CreativeML, et l'entrée le dit. Le moteur de zone
nommée n'apparaît donc que si une machine porte déjà ce fichier ; sans lui,
« change le fond » et « enlève le sujet » fonctionnent comme avant.

## Ce qui ne marche pas encore

- **Le masque est mesuré avant le rendu, et cette mesure sert deux fois.**
  Une cible que le modèle ne trouve pas rendait, avant, une image identique au
  bit près après **13,1 s** de carte — une panne muette. Le masque seul est
  maintenant réduit à un pixel et lu : « the elephant » sur une photo de route
  donne 0,00 % en **1,0 s**, et le studio le dit en nommant ce qu'il a cherché.
  La même mesure choisit le nombre d'étapes, sur l'aire réelle plutôt que sur la
  catégorie de la cible : « the sky » 52,6 %, « the road sign » 2,0 %, le sujet
  3,1 %, le fond 99,6 %.
- **Effacer un gros objet laisse une zone moins texturée que son voisinage.**
  Gradient moyen au cœur de la zone, rapporté à un anneau de 12 à 80 px autour :
  **0,59** pour une voiture occupant 19,5 % du cadre, aux 4 étapes du moteur
  d'édition. À 8 puis 16 étapes on remonte à 0,73 puis 0,83, et le rendu passe
  de 11,4 à 23,0 s — sans jamais rejoindre le voisinage. Sur une petite zone le
  problème n'existe pas : le panneau effacé donne 1,12, soit un peu plus de
  texture que ce qui l'entoure. Le studio monte donc à 16 étapes au-delà de 15 %
  du cadre, et le dit dans le déroulé — l'arbitrage est exposé, pas subi.
- **L'éclairage ne suit pas.** Un ciel d'orage posé au-dessus d'une route en
  plein soleil reste incohérent. C'est la contrepartie directe de la promesse :
  le recollage exact garantit que le reste ne bouge pas, donc qu'il ne se met
  pas d'accord avec la zone neuve.
