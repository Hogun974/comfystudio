# Un masque a partir d'une description — ce que la mesure decide

Essai mene le 30/08/2026 sur la machine du studio (RTX 2080 Ti 11 Go, ComfyUI
0.33.1, torch 2.13.0+cu130). Suite directe de `essai_inpainting.md`, qui avait
etabli que la retouche localisee tient et que le seul verrou restant etait le
masque. Aucun fichier du depot n'a ete modifie hormis celui-ci, aucun commit.
Un poids a ete telecharge (§2). Les fichiers deposes dans `input/` et `output/`
de ComfyUI ont ete effaces en fin d'essai.

---

## 0. Reponse courte

Le verrou saute. « Change seulement le ciel », « enleve le panneau »,
« enleve la voiture » fonctionnent, avec **preservation exacte** du reste
(ecart 0,000 / 255, p99 = 0, aucun pixel modifie hors du masque).

Il faut un telechargement : **1,63 Gio**, licence Meta non libre mais **sans
restriction commerciale** (§2). Le cout de calcul est **nul en pratique** :
le masque SAM 3.1 coute 1,2 s a chaud, exactement comme BiRefNet aujourd'hui.

Trois chiffres qui resument tout :

| ce qu'on mesure | valeur |
|---|---|
| masque « the sky » contre une reference couleur independante | **IoU 0,905** |
| meilleure bande geometrique possible (le repli d'hier) sur la meme reference | **IoU 0,584** |
| masque « the car » contre le masque BiRefNet du meme sujet | **IoU 0,983** |

**Mais le modele ne comprend pas le francais, et il echoue en silence.** Sur
l'image 2, « le ciel » ne rend pas un masque vide : il rend **la voiture**,
avec un score qui survit a un seuil de 0,95 (IoU 0,9975 avec « the car »).
C'est le resultat le plus important de cet essai. Il impose deux regles :
traduire avant d'appeler, et **verifier l'aire du masque en code** avant de
lancer l'echantillonneur. Details et tableaux au §4.

---

## 1. Ce que le noeud attend exactement

Releve sur `/object_info/SAM3_Detect` et lecture de
`comfy_extras/nodes_sam3.py`.

### Signature

| entree | type | requis | defaut |
|---|---|---|---|
| `model` | `MODEL` | oui | — |
| `image` | `IMAGE` | oui | — |
| `threshold` | `FLOAT` 0–1 | oui | 0.5 |
| `refine_iterations` | `INT` 0–5 | oui | 2 — passes du decodeur SAM ; 0 = masques bruts du detecteur |
| `individual_masks` | `BOOLEAN` | oui | false — un masque par objet au lieu de l'union |
| `conditioning` | `CONDITIONING` | non | issu de `CLIPTextEncode` |
| `bboxes` | `BOUNDING_BOX` | non | segmenter a l'interieur de boites |
| `positive_coords` / `negative_coords` | `STRING` | non | points JSON `[{"x":..,"y":..}]` |

Sorties : `masks` (`MASK`) et `bboxes` (`BOUNDING_BOX`). Par defaut le masque
est **l'union** de toutes les detections retenues, en `[1, H, W]` a la taille
de l'image d'entree. Avec `individual_masks`, c'est un lot `[N, H, W]`.

Les boites sont une liste de dictionnaires `{"x","y","width","height","score"}`
par image — c'est le seul endroit ou le score de detection est lisible depuis
un graphe.

### D'ou vient le modele — et ce n'est PAS `models/detection/`

`models/detection/` n'est utilise que par MediaPipe
(`comfy_extras/nodes_mediapipe.py:210` et `:218`, via
`folder_paths.py:67`). SAM3 n'y touche pas.

Le poids SAM3 se charge par **`CheckpointLoaderSimple`**, donc depuis
`models/checkpoints/`. Le fichier contient le detecteur **et** son encodeur de
texte ; `CheckpointLoaderSimple` rend un `MODEL` et un `CLIP` qui vont
ensemble. Chaine de reconnaissance :

- `comfy/model_detection.py:1096` — la cle
  `detector.backbone.vision_backbone.trunk.blocks.0.attn.qkv.weight` declenche
  `image_model = "SAM3"` ; la presence de
  `detector.backbone.vision_backbone.propagation_convs.0.conv_1x1.weight`
  bascule en `"SAM31"`.
- `comfy/supported_models.py:2321` (`SAM3`) et `:2368` (`SAM31`), avec
  `text_encoder_key_prefix = ["detector.backbone.language_backbone."]`.
- `comfy/text_encoders/sam3_clip.py` pour l'encodeur.

### L'encodeur de texte : la cause de tout le §4

`sam3_clip.py` declare un `CLIPTextModel` de 1024 de largeur, 24 couches,
`vocab_size` 49408, `max_position_embeddings` **32**. C'est un **CLIP-L
d'origine OpenAI**, anglais, et **32 jetons au maximum**. Ce n'est ni T5 ni
Qwen : aucune raison structurelle qu'il comprenne le francais.

Deux consequences verifiees :

- **Le `CLIP` doit venir du checkpoint SAM3.** Brancher `qwen_3_4b` a la place
  ne degrade pas doucement : ca leve une `RuntimeError`, `mat1 and mat2 shapes
  cannot be multiplied (512x7680 and 1024x256)`, dans
  `comfy/ldm/sam3/detector.py:518`. Echec franc, tant mieux.
- **La syntaxe du prompt est particuliere** (`_parse_prompts`, `sam3_clip.py`) :
  les virgules separent des **categories** distinctes, et `texte:N` fixe le
  nombre maximum de detections pour cette categorie. Mesure :

  | consigne | aire du masque | remarque |
  |---|---|---|
  | `the sky` | 38,76 % | |
  | `the road` | 15,09 % | |
  | `the sky, the road` | **53,85 %** | soit 38,76 + 15,09 a 0,00 pres : union exacte |
  | `the utility pole` | 0,08 % | un seul poteau |
  | `the utility pole:6` | 0,28 % | plusieurs poteaux |

  Une seule passe suffit donc pour un masque compose. C'est utile : « enleve
  la voiture et le panneau » ne demande pas deux appels.

### Ce que fait le noeud, en interne

L'image est ramenee a **1008x1008** en bilineaire sans recadrage
(`comfy.utils.common_upscale(..., crop="disabled")`) : le rapport d'aspect est
donc ecrase pour le detecteur, puis les masques sont ramenes a `H, W`. Avec
`refine_iterations > 0`, chaque detection est reprise par le decodeur SAM sur
un recadrage de sa boite elargie de 10 %, ce qui explique la finesse des
contours (§3).

### Les voisins, et pourquoi ils ne repondent pas a la question

| noeud | verdict |
|---|---|
| `RTDETR_detect` | **vocabulaire ferme** : une liste COCO figee (`person`, `car`, `bus`…) dans un menu deroulant. Ne rend que des boites, pas de masque, et exige son propre poids. Ne repond pas a « une description libre ». |
| `SDPoseKeypointExtractor` / `SDPoseFaceBBoxes` | poses et visages seulement |
| `MediaPipeFaceLandmarker` / `MediaPipeFaceMask` | visages seulement, et `models/detection/` est vide : la liste deroulante du chargeur est vide |
| `SAM3_VideoTrack` / `SAM3_TrackToMask` | meme poids, pour la video — hors sujet ici, mais **gratuit** une fois le poids pose |

---

## 2. Les poids : ou, combien, sous quelle licence

**Ce que j'ai pose, exactement :**

```
D:\ComfyUI_windows_portable\ComfyUI\models\checkpoints\sam3.1_multiplex_fp16.safetensors
```

- depot : **`Comfy-Org/sam3.1`**, fichier `checkpoints/sam3.1_multiplex_fp16.safetensors`
- taille : **1 745 546 848 octets** = 1,626 Gio (verifie sur le fichier telecharge, pas seulement annonce)
- telechargement : 101,5 s, HTTP 200, sans jeton ni compte
- effacer = supprimer ce seul fichier ; rien d'autre n'a ete ajoute

C'est le **repackage officiel de Comfy-Org**, non verrouille. Le depot amont
`facebook/sam3.1` est en revanche `gated: "manual"` (formulaire nom, date de
naissance, pays, employeur, acceptation de la politique de confidentialite
Meta) : passer par Comfy-Org evite ce formulaire a l'utilisateur du studio.
`facebook/sam3.1` declare `language: ["en"]` — l'anglais est annonce des la
fiche du modele.

### La licence

**« SAM License », derniere mise a jour du 19 novembre 2025**, 7 352 octets,
recopiee dans le depot Comfy-Org (`LICENSE`), `license_name: sam-license`.

Ce qu'elle dit, et qui compte pour un projet AGPL-3.0 qui annonce du local :

- **Aucune restriction commerciale.** Le mot « commercial » n'apparait pas une
  seule fois dans le texte. Pas de seuil d'utilisateurs a la Llama. Licence
  « non-exclusive, worldwide, non-transferable and royalty-free » pour
  utiliser, reproduire, distribuer, modifier.
- **Mais ce n'est pas une licence libre**, et il ne faut pas l'inscrire comme
  telle au `CATALOGUE` :
  - toute redistribution des poids ou d'un derive doit se faire **sous cette
    meme licence, copie jointe** (§1.b.i) ;
  - interdiction de retro-ingenierie ou de « decouvrir les composants
    sous-jacents » (§1.b.iv) — clause etrangere a l'esprit du libre ;
  - restrictions ITAR / sanctions / armes (§1.b.v) ;
  - **Meta peut modifier l'accord unilateralement**, effet immediat (§8) ;
  - resiliation automatique en cas de litige de brevet (§5.b) ;
  - droit californien, juridiction exclusive de Californie (§7).

**Conclusion pour le depot.** L'AGPL du studio n'est pas en cause : les poids
ne sont ni du code source du studio ni lies a lui, ils sont telecharges
separement par l'installeur. Rien a changer au README : tout continue de
tourner en local. En revanche la ligne de `CATALOGUE` doit **nommer la licence
et pointer son texte**, et ne pas laisser croire a du libre. C'est la
difference avec les autres entrees, qui sont Apache ou CreativeML.

---

## 3. Ce que le masque vaut, mesure

Deux images d'essai que j'ai generees moi-meme avec RealVisXL V5.0 (1216x832,
graine 424242, 28 pas, cfg 5,0) :

- **image 1** — route de campagne, ciel bleu nuageux **avec une limite de ciel
  tres decoupee** (une grande cime d'arbre au milieu du cadre, des lignes
  electriques, des poteaux, un panneau bleu a droite). Choisie exactement parce
  que c'est le cas ou la bande geometrique d'hier echoue.
- **image 2** — une berline bordeaux garee au bord d'une route mouillee, haie
  verte derriere, ciel gris couvert.

### 3.1 « the sky », contre une reference independante

Reference construite **sans SAM3** : regle de couleur (bleu dominant, ou
pixels tres clairs) puis composante connexe atteignant le bord haut, fermeture
3x3. Aire 41,04 % de l'image.

| masque | IoU avec la reference |
|---|---|
| **SAM3 « the sky »** | **0,9048** |
| bande geometrique h=300 (le repli du §2.3 d'hier) | 0,3879 |
| bande geometrique h=585, la meilleure possible | 0,5835 |

Aire SAM3 38,76 %, reference 41,04 %. Les desaccords : SAM3 revendique
0,86 % de l'image que la reference refuse, la reference revendique 3,14 % que
SAM3 refuse — et ce 3,14 % est **la brume claire de l'horizon**, que la regle
de couleur prend pour du ciel et que SAM3 attribue correctement aux arbres
lointains. Autrement dit, la ou les deux different, c'est plutot SAM3 qui a
raison : 0,905 est un plancher, pas un plafond.

A l'oeil, sur le masque exporte : la cime de l'arbre est decoupee feuille par
feuille, les trois poteaux sont exclus, et **les lignes electriques sont
exclues** — des traits d'un ou deux pixels de large en travers du ciel.

### 3.2 « the car », contre BiRefNet

Sur l'image 2, la voiture est le sujet saillant : BiRefNet et SAM3 devraient
tomber d'accord. Ils le font.

| | aire | |
|---|---|---|
| SAM3 « the car » | 15,39 % | |
| BiRefNet + `ThresholdMask 0.5` | 15,64 % | |
| **IoU** | **0,9831** | SAM3 hors BiRefNet 0,01 % ; BiRefNet hors SAM3 0,26 % |

Le petit surplus de BiRefNet est un lisere autour du vehicule. Les deux
routes designent le meme objet ; SAM3 fait donc **au moins aussi bien que ce
qui est installe** sur le seul cas que ce qui est installe savait traiter, et
en plus il sait dire « le panneau », « le ciel », « la haie ».

### 3.3 La finesse : ce que le detourage ne savait pas faire

« the road sign » rend **le panneau seul, 1,07 % de l'image, sans le mat**.
« the license plate » rend la plaque, 0,30 %. « the wheels » rend les roues,
0,36 %. Ce n'est plus « le sujet contre le fond » : c'est une partie nommee.

---

## 4. La langue : le seul vrai verrou, et il mord en silence

C'est la section a lire avant d'ecrire une ligne de code.

### 4.1 Le francais echoue — et pas en rendant un masque vide

Image 1 (objet saillant : le panneau) et image 2 (objet saillant : la
voiture), au seuil par defaut 0,5. Aire du masque en % de l'image.

| description | anglais | francais | verdict |
|---|---|---|---|
| ciel (img 1) | 38,76 | **1,07 → c'est le PANNEAU** (IoU 0,996 avec « the road sign ») | **faux positif** |
| ciel (img 2) | 15,36 | **15,39 → c'est la VOITURE** (IoU 0,9975 avec « the car ») | **faux positif** |
| haie (img 2) | 30,10 | **15,40 → la VOITURE** (IoU 0,9968) | **faux positif** |
| roues (img 2) | 0,36 | **15,45 → la VOITURE** (IoU 0,9950) | **faux positif** |
| nuages (img 1) | 2,60 | 0,00 | echec franc |
| herbe (img 1) | 2,99 | 0,00 | echec franc |
| poteau electrique (img 1) | 0,08 | 0,00 | echec franc |
| panneau (img 1) | 1,07 | 0,00 | echec franc |
| arbres (img 1) | 10,49 | 10,60 (IoU 0,9851) | **passe** |
| route (img 1) | 15,09 | 15,10 (IoU 0,9770) | **passe** |
| route (img 2) | 30,25 | 29,82 | **passe** |
| plaque d'immatriculation (img 2) | 0,30 | 0,30, meme boite | **passe** |

Les rares mots qui passent sont ceux qui sont des **cognats** de l'anglais
(*route*, *plate*, *arbor*). Ce n'est pas du multilinguisme, c'est une
coincidence de vocabulaire. On ne peut pas construire une fonctionnalite
dessus.

### 4.2 Pourquoi c'est pire qu'un simple echec : le repli sur l'objet saillant

Temoins passes sur l'image 2, tous au seuil 0,5 :

| consigne | aire | IoU avec « the car » |
|---|---|---|
| `xyzzy plough qwerty` (charabia) | 15,45 % | 0,9943 |
| `blorpf` (charabia) | 15,44 % | 0,9948 |
| `a giraffe` | 15,49 % | 0,9927 |
| `un chat` | 15,52 % | 0,9901 |
| `le ciel bleu au dessus de la route` | 15,44 % | 0,9946 |

**Du charabia rend la voiture.** Le detecteur a une propension a poser une
detection sur l'objet dominant quoi qu'on lui demande. Ce n'est pas universel :
sur l'image 1, `a giraffe` rend 0,02 % au seuil 0,3 et 0,00 % au seuil 0,5, et
le charabia 1,08 % puis 0,00 %. Le repli apparait quand l'image est dominee
par un objet unique et net.

### 4.3 Le seuil repare presque tout — presque

Balayage de `threshold`, aire du masque en % :

| consigne | 0,30 | 0,50 | **0,70** | 0,85 | 0,95 |
|---|---|---|---|---|---|
| img2 `the car` | 15,39 | 15,39 | **15,39** | 15,39 | 15,39 |
| img2 `the sky` | 15,36 | 15,36 | **15,36** | 15,36 | 15,36 |
| img1 `the sky` | 38,76 | 38,76 | **38,76** | 38,76 | 38,76 |
| img2 `a giraffe` | 15,49 | 15,49 | **0,00** | 0,00 | 0,00 |
| img2 charabia | 15,45 | 15,45 | **0,00** | 0,00 | 0,00 |
| img1 charabia | 1,08 | 0,00 | **0,00** | 0,00 | 0,00 |
| img1 `le ciel` | 1,07 | 1,07 | **0,00** | 0,00 | 0,00 |
| img2 `le ciel` | 15,39 | 15,39 | **15,39** | 15,38 | **15,39** |

Lecture :

1. **Les vraies detections sont insensibles au seuil.** Aire strictement
   identique de 0,30 a 0,95. Le detecteur est tres confiant quand il a
   compris. Monter le seuil ne coute donc rien.
2. **0,70 elimine tous les faux positifs de charabia**, sur les deux images.
   C'est le reglage a retenir, et il est gratuit.
3. **Il en reste un.** `le ciel` sur l'image 2 rend la voiture avec un score
   qui tient jusqu'a 0,95. Le seuil ne suffit donc pas : il faut traduire.

### 4.4 Ce que ca impose au studio

- **Traduire la description vers l'anglais avant l'appel.** Le studio a deja
  ce chemin : `traduire=True` existe dans `catalogue.py` pour `realvis`,
  `pony`, `flux1`. C'est une contrainte connue et geree, pas un obstacle. Ce
  n'est pas le meme appel LLM que la conversion « demande → description de la
  zone » du §3 d'hier : c'est une traduction courte, sur trois mots, et
  **32 jetons au maximum** (§1).
- **Verifier l'aire du masque en code, pas dans le prompt.** Trois cas a
  traiter cote serveur, avant d'envoyer quoi que ce soit au sampler :
  aire nulle → dire « je n'ai pas trouve », ne pas lancer ; aire enorme
  (disons > 90 %) → probablement un contresens ; sinon, y aller.
  Ce n'est pas cosmetique : voir §7.3, un masque vide coute **13,13 s de GPU
  pour ne rien faire**.
- **Garder BiRefNet** comme repli quand SAM3 ne trouve rien et que la demande
  designe manifestement « le sujet ». Il ne coute rien de plus (§8).

---

## 5. La chaine complete : masque par description, puis retouche

On reprend `g_retouche_zone` du depot tel quel, en remplacant les seuls noeuds
50/51/7 (BiRefNet + seuillage) par le bloc SAM3. Tout le reste — masque dur
pour l'echantillonnage, masque flou pour le recollage, absence de
`ReferenceLatent`, `ImageCompositeMasked` — est celui qui avait ete mesure
hier. Klein 4B, 4 pas, graine 424242, 1216x832.

Meme protocole de mesure qu'au §4 d'hier. `dehors` = ecart moyen en niveaux
0-255 a plus de 40 px du masque (8 px pour les lignes sans recollage) ;
`dedans` = meme ecart au coeur de la zone ; `exces` = rapport de crete de
Sobel sur le contour (§6 d'hier).

| cas | dehors | p99 | %>2 | dedans | aire masque | exces crete |
|---|---|---|---|---|---|---|
| **« change le ciel »** (grow 0) | **0,000** | 0 | 0,00 | 58,86 | 38,76 % | 0,75 |
| meme chose, grow 24 | **0,000** | 0 | 0,00 | 57,72 | **48,09 %** | 1,03 |
| meme chose, **sans recollage** | 7,715 | 31 | 76,93 | 57,26 | 38,76 % | 0,81 |
| **« enleve le panneau »** (grow 24) | **0,000** | 0 | 0,00 | 98,05 | 2,15 % | 0,97 |
| **« enleve la voiture »** (grow 24) | **0,000** | 0 | 0,00 | 58,80 | 19,51 % | 0,98 |
| meme chose, **sans recollage** | 4,701 | 16 | 69,16 | 57,49 | 19,51 % | 0,99 |

Trois choses a lire :

1. **La chaine complete tient.** `dehors = 0,000`, `p99 = 0`, `%>2 = 0,00` :
   pas un pixel ne bouge hors du masque, exactement comme hier. Le masque par
   description n'a rien degrade.
2. **Le recollage reste non negociable, et sa necessite grandit avec l'aire.**
   Sans lui : 4,70 sur 19,5 % de l'image, **7,72 sur 38,8 %**. C'est la meme
   non-localite du decodeur VAE qu'hier (4,29 sur une boite, 12,93 sur une
   bande) : la derive suit l'ampleur du changement.
3. **Aucune couture ajoutee** : exces entre 0,75 et 1,03, avec le
   `blur_radius = 11` retenu hier. Rien a rejouer de ce cote.

### 5.1 Ce que ca donne a l'oeil

- **« change seulement le ciel »** — ciel d'orage au crepuscule, nuages
  sombres et lisere orange. **Le feuillage de la cime est intact feuille par
  feuille, les lignes electriques traversent toujours le ciel neuf, le
  panneau, la route et l'herbe n'ont pas bouge d'un niveau.** C'est
  exactement la demande que le studio ne savait pas servir. Reserve honnete :
  la lumiere au sol reste celle du plein jour sous un ciel d'orage — c'est le
  point de coherence d'eclairage deja ouvert au §9 d'hier, le masque ne le
  regle pas.
- **« enleve le panneau »** — le panneau disparait, **le mat reste** (SAM3 a
  masque la plaque, pas le poteau : segmentation fidele au mot), ciel et
  feuillage se referment sans trace. C'est le meilleur resultat de l'essai.
- **« enleve la voiture »** — la voiture est bien partie, le bas-cote, la
  cloture et la base de la haie sont reconstruits de facon convaincante,
  **mais le bas de la zone est une plaque grise floue** ou l'on devine encore
  la silhouette. Voir 5.2.

### 5.2 La limite qui reste, chiffree : le remplissage, pas le masque

Mesure de texture : `|Sobel|` moyen au coeur de la zone (a plus de 12 px du
bord), compare a un anneau de reference de 12 a 80 px autour du masque, dans
la meme image.

| cas | texture zone, source | texture zone, resultat | anneau | rapport zone/anneau |
|---|---|---|---|---|
| « change le ciel » | 16,27 | **14,56** | 105,4 | — (le ciel est lisse par nature ; **0,89 du niveau d'origine**, c'est le bon rapport ici) |
| « enleve le panneau » | 106,60 | **112,67** | 100,8 | **1,12** — aussi texture que son voisinage |
| « enleve la voiture », 4 pas | 61,61 | 26,38 | 44,5 | **0,59** |
| idem, 8 pas (18,52 s) | 61,61 | 32,56 | 44,5 | 0,73 |
| idem, 16 pas (22,95 s) | 61,61 | 36,99 | 44,5 | 0,83 |

Le flou est reel et il se chiffre. Il **ne vient pas du masque** : sur la meme
image, le meme graphe, le meme masque, passer de 4 a 16 pas remonte le rapport
de 0,59 a 0,83. C'est le moteur qui n'a pas assez de pas pour inventer 19,5 %
d'image a partir de rien. Deux consequences de conception :

- pour les **petites zones** (panneau, plaque, lampadaire), 4 pas suffisent
  largement — 1,12, c'est mieux que le voisinage ;
- pour les **grandes zones** (une voiture au premier plan), il faut monter les
  pas, et ca double le temps. C'est un arbitrage a exposer, pas un defaut a
  cacher. A 16 pas le rapport plafonne encore a 0,83 : klein a 1216x832 ne
  rend pas de l'asphalte convaincant sur 19 % du cadre. **Piste non essayee :
  RealVis en `denoise` partiel sur cette zone**, qui obeissait mieux aux
  descriptions hier.

### 5.3 `GrowMask` n'a pas une bonne valeur : il en a deux

Hier, `expand = 24` etait la bonne valeur, mesuree, pour effacer un sujet — un
rocher enferme dans une silhouette de cerf reste en forme de cerf. Cet essai
montre que la regle ne se transporte pas :

| intention | masque a expand 0 | a expand 24 | verdict |
|---|---|---|---|
| **remplacer un objet** (voiture, panneau) | fantome de silhouette (mesure d'hier : crete 9,93 contre 0,89) | correct | **24** |
| **changer une region en place** (le ciel) | correct | 38,76 % → **48,09 %**, soit **9,33 % de l'image mangee sur les arbres** | **0** |

A l'oeil, le ciel a `expand = 24` est sans appel : la canopee est rongee, les
branches fines ont disparu, la ligne d'arbres lointaine est effacee. Toute la
finesse du §3.1 est detruite par la dilatation.

**Regle a retenir** : dilater quand on remplace un OBJET par autre chose,
ne pas dilater quand on refait une REGION a l'identique de sa nature (ciel,
route, mur). C'est un troisieme choix a faire quelque part — a cote de
« quelle cible » et « quelle description ». Trois decisions, donc, et le §9
d'hier avait raison de dire qu'il faut les separer.

---

## 6. Le graphe retenu

Diff par rapport a `g_retouche_zone` (`serveur.py:2764`) : les noeuds 50, 51 et
7 disparaissent, trois noeuds 30/31/32 les remplacent, et `expand` devient un
parametre. Tout le reste est inchange.

```jsonc
{
  // ── inchange : moteur, encodeur, VAE, image, mise a l'echelle, taille ──
  // "1" UNETLoader flux-2-klein-4b, "2" CLIPLoader qwen_3_4b,
  // "3" VAELoader flux2-vae, "4" LoadImage, "5" ImageScaleToTotalPixels,
  // "6" GetImageSize  — exactement comme aujourd'hui.

  // ── le masque, par DESCRIPTION ──────────────────────────────────────
  // Remplace LoadBackgroundRemovalModel + RemoveBackground + ThresholdMask.
  // Pas de ThresholdMask ici : SAM3 rend deja un masque binaire strict
  // (`(mask > 0).float()`, nodes_sam3.py), pas les millimes de BiRefNet.
  "30": {"class_type":"CheckpointLoaderSimple",
         "inputs":{"ckpt_name":"sam3.1_multiplex_fp16.safetensors"}},
  // Le CLIP DOIT venir de "30". qwen_3_4b leve une RuntimeError (§1).
  // CIBLE est en ANGLAIS, 32 jetons au maximum, sinon faux positif silencieux.
  // Virgule = plusieurs categories, « the car, the road sign » rend l'union.
  "31": {"class_type":"CLIPTextEncode","inputs":{"text":"CIBLE","clip":["30",1]}},
  // 0.70 et pas 0.50 : mesure au §4.3. Les vraies detections ne bougent pas
  // d'un centieme de 0,30 a 0,95 ; le charabia meurt a 0,70.
  "32": {"class_type":"SAM3_Detect",
         "inputs":{"model":["30",0],"image":["5",0],"conditioning":["31",0],
                   "threshold":0.70,"refine_iterations":2,"individual_masks":false}},

  // ── EXPAND depend de l'intention, pas de l'image (§5.3) ─────────────
  //   remplacer un OBJET  -> 24
  //   refaire une REGION  ->  0   (a 24, le ciel mange 9,33 % d'arbres)
  "9":  {"class_type":"GrowMask","inputs":{"mask":["32",0],"expand":"EXPAND",
         "tapered_corners":true}},

  // ── inchange a partir d'ici ─────────────────────────────────────────
  // "10" MaskToImage, "11" ImageBlur 11/5.5, "12" ImageToMask,
  // "13" VAEEncode, "14" SetLatentNoiseMask, "15".."22" echantillonnage,
  // "23" ImageCompositeMasked, "24" SaveImage.
  // Rappel : "19" Flux2Scheduler steps=4 convient aux petites zones ; pour
  // une grande zone (> ~15 % du cadre) monter a 16, cf. §5.2.
}
```

Et, **en amont du graphe, dans `serveur.py`** — pas dans le prompt :

```python
# 1. traduire CIBLE vers l'anglais (appel court, 32 jetons max)
# 2. lancer un mini-graphe SAM3 seul (1,2 s) et lire l'aire du masque
# 3. aire == 0        -> repli BiRefNet si la demande vise « le sujet »,
#                        sinon rendre la main : « je n'ai pas trouve X »
#    aire > 0,90      -> refuser : contresens probable
#    sinon            -> lancer la chaine complete
```

Cette separation coute une passe SAM3 de 1,2 s et evite 13 s de sampler pour
rien (§7.3). Elle suit la note de conception deja retenue ailleurs : une tache
par appel, et la verification en code plutot que dans le prompt.

---

## 7. Les pieges rencontres

1. **`models/detection/` est une fausse piste.** Le dossier existe, il est
   vide, et il ne concerne que MediaPipe. SAM3 se charge depuis
   `models/checkpoints/` par `CheckpointLoaderSimple`. Corollaire genant :
   **le poids SAM3 apparait dans la meme liste deroulante que RealVisXL et
   Pony**. Ici c'est sans consequence, `catalogue.py` etant un dictionnaire
   statique ; mais toute future enumeration dynamique des checkpoints devra
   l'exclure, sous peine de proposer « SAM 3.1 » comme moteur d'image.

2. **L'echec du francais ne ressemble pas a un echec.** C'est le piege
   principal. Un masque de 15 % d'aire, net, bien decoupe, sur le mauvais
   objet, avec un score qui survit a un seuil de 0,95. Aucune inspection
   superficielle ne le detecte. Seule la comparaison avec la version anglaise
   le revele.

3. **Un masque vide coute une session complete de GPU.** Mesure : masque a
   0,000 % d'aire, resultat **identique au bit pres** a la source (ecart max 0,
   ecart moyen 0,0000) — donc echec silencieux et sans degat — mais
   **13,13 s** consommees. `SetLatentNoiseMask` avec un masque nul ne debruite
   rien et `ImageCompositeMasked` recolle la source sur la source. Il faut
   court-circuiter avant.

4. **`ThresholdMask` ne sert plus.** C'etait indispensable derriere BiRefNet
   (le masque valait ~0,0015 loin du sujet, ce qui teintait toute l'image au
   recollage). SAM3 rend `(mask > 0).float()`, un binaire strict. Le garder ne
   nuit pas, mais ne repare rien.

5. **Le mauvais `CLIP` ne degrade pas, il casse.** `RuntimeError` franche.
   C'est une bonne nouvelle : impossible de se tromper a moitie.

6. **La cible et la description sont deux textes differents, dans deux
   langues.** `"31"` recoit la CIBLE en anglais (« the sky »), `"15"` recoit
   la DESCRIPTION de ce qu'on veut voir, dans la langue que klein preferera —
   klein est multilingue, lui. Confondre les deux fait echouer l'un ou l'autre.

7. **La carte est partagee.** Au demarrage de l'essai le studio calculait un
   flux1-dev en GGUF : le harnais a attendu 126 s que la file se vide au lieu
   de passer devant. Tous les chiffres des §3 a §5 ont ete pris file vide.

---

## 8. Temps de calcul, avec l'etat du cache

Image 1216x832. « froid » = le poids etait a charger depuis le disque.

| operation | s | etat |
|---|---|---|
| masque SAM3 seul, tout premier appel | 4,05 | froid, checkpoint a charger |
| **masque SAM3 seul** | **0,81 a 1,25** | chaud |
| masque BiRefNet seul (pour comparer) | 1,23 | chaud |
| chaine complete, 1er appel | 17,25 | froid, klein **et** SAM3 a charger |
| **chaine « change le ciel »** | **6,46 a 8,67** | chaud |
| **chaine « enleve le panneau »** | **11,41 a 11,56** | chaud |
| **chaine « enleve la voiture »**, 4 pas | 11,42 a 11,64 | chaud |
| idem, 8 pas | 18,52 | chaud |
| idem, 16 pas | 22,95 | chaud |
| chaine sur masque vide (rien a faire) | 13,13 | chaud — du temps perdu |

**SAM3 coute le meme temps que BiRefNet** : 1,2 s a chaud dans les deux cas.
Le remplacement est donc gratuit en calcul. La chaine complete reste dans
l'enveloppe mesuree hier (14 a 16 s pour V1/V2), et descend meme en dessous
pour le ciel.

**VRAM** : la chaine charge simultanement klein 4B, `qwen_3_4b`, le VAE flux2
et SAM 3.1. Elle passe sur la carte de 11 Go ; `/system_stats` rapporte
**3,2 Go libres** apres les rendus. Le poids fait 1,63 Gio sur disque et
l'occupation reelle en VRAM n'a pas ete isolee — je donne la place restante,
pas le cout marginal.

---

## 9. La ligne de `CATALOGUE`, prete a coller

Chiffres verifies sur le fichier telecharge, pas repris d'une fiche.

```python
 "masque": dict(titre="Masque par description (SAM 3.1)", famille="sam3",
   type="masque", duree="2 s", vram=2.0, traduire=True,
   pour="designer une zone d'image en la nommant : le ciel, la voiture, "
        "le panneau. Sert de masque a la retouche localisee",
   licence=("SAM License (Meta) — usage commercial autorise, mais licence "
            "non libre : redistribution sous les memes termes, pas de "
            "retro-ingenierie, restrictions ITAR. "
            "https://huggingface.co/Comfy-Org/sam3.1/blob/main/LICENSE"),
   fichiers=[("checkpoints","sam3.1_multiplex_fp16.safetensors",
              "Comfy-Org/sam3.1","checkpoints/sam3.1_multiplex_fp16.safetensors")]),
```

```python
    ('checkpoints', 'sam3.1_multiplex_fp16.safetensors'): 1.63,   # dans TAILLES
```

`traduire=True` est deja compris par le studio (`realvis`, `pony`, `flux1`
l'utilisent). La cle `licence` n'existe pas encore dans `catalogue.py` : c'est
la seule addition de structure, et elle me semble due — c'est le premier
modele du catalogue dont la licence merite d'etre lue avant installation.
`vram=2.0` est une estimation prudente a partir de la taille du fichier, pas
une mesure ; voir §10.

---

## 10. Ce que je n'ai PAS tranche

- **Le cout VRAM propre de SAM 3.1.** Je sais que la chaine complete tient sur
  11 Go et laisse 3,2 Go libres. Je n'ai pas isole l'occupation du seul
  detecteur, donc le `vram=2.0` de la ligne de catalogue est deduit de la
  taille du fichier, pas mesure.
- **Si « la voiture » est comprise ou chanceuse.** Sur l'image 2, la voiture
  etait aussi l'objet saillant : impossible de distinguer une vraie
  comprehension d'un repli reussi par hasard. La question est sans importance
  pratique — on traduira de toute facon — mais elle n'est pas tranchee.
- **Le seuil 0,70 sur d'autres images.** Deux images, un balayage a cinq
  points. Le fait que les vraies detections soient rigoureusement constantes
  de 0,30 a 0,95 est un argument fort, pas une preuve generale.
- **La liste des mots francais qui passent.** Douze paires sur deux images.
  Assez pour conclure « il faut traduire », pas assez pour dresser une
  frontiere.
- **`individual_masks`, les boites et les points.** Le noeud accepte des
  boites en entree (par exemple issues de `RTDETR_detect`) et des points
  cliques. Non essayes. `individual_masks` permettrait « enleve la 2e
  voiture » — non essaye non plus.
- **`SAM3_VideoTrack`.** Le meme poids sert au suivi video image par image. La
  retouche localisee sur une video devient donc atteignable sans nouveau
  telechargement. Rien mesure.
- **Le remplissage des grandes zones.** Mesure a 0,59 / 0,73 / 0,83 de la
  texture voisine a 4 / 8 / 16 pas. Je n'ai essaye ni RealVis en `denoise`
  partiel, ni klein 9B, ni un second passage sur la zone.
- **La coherence d'eclairage.** Toujours ouverte, comme hier : un ciel
  d'orage au-dessus d'une route en plein soleil reste incoherent, et le
  recollage exact est precisement ce qui garantit cette incoherence.
- **La verification du masque cote serveur.** Proposee au §6, non implementee
  ni eprouvee sur le corpus.

---

## 11. Protocole, pour rejouer

- Poids : `Comfy-Org/sam3.1`, `checkpoints/sam3.1_multiplex_fp16.safetensors`,
  pose dans `D:\ComfyUI_windows_portable\ComfyUI\models\checkpoints\`.
  1 745 546 848 octets. Sans jeton. Supprimer ce fichier annule tout.
- Images d'essai generees sur place (RealVisXL V5.0, 1216x832, graine 424242,
  28 pas, cfg 5,0, `dpmpp_2m` / `karras`), multiples de 16 pour qu'aucun
  redimensionnement ne s'intercale entre la source mesuree et
  l'echantillonneur.
- Graine unique pour toutes les retouches : 424242.
- Masque de reference exporte a chaque fois par `MaskToImage` + `SaveImage`,
  et c'est ce masque-la qui sert aux mesures — jamais une reconstruction.
- Reference « ciel » independante : regle de couleur
  `(B > R+20 et B > 90) ou (min(R,G,B) > 185 et B >= R)`, puis composantes
  connexes touchant la premiere ligne, fermeture 3x3.
- Mesures en numpy/scipy dans le python embarque de ComfyUI
  (`D:\ComfyUI_windows_portable\python_embeded\python.exe`), sur les PNG
  rapatries via `/view`.
- Le harnais attend `/queue` vide avant chaque envoi, pour ne pas bousculer le
  studio.
- Fichiers d'essai effaces : `input/essai_masque_src.png`,
  `input/essai_masque_src2.png`, et les 130 sorties `output/masque_essai_*`.
