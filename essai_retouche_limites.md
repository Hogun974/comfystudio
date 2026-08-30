# Retouche localisee — ou elle casse

Essai mene le 30/08/2026 sur la machine du studio (RTX 2080 Ti 11 Go, ComfyUI
0.33.1, torch 2.13.0+cu130, python 3.13.14). Suite de `essai_inpainting.md` et
`essai_masque_texte.md`, cette fois contre le code livre : les graphes mesures
sont ceux que `serveur.py` construit reellement (`g_retouche_zone`, `g_edition`,
`g_detourage` extraits du fichier et executes tels quels, sans les recopier).
Aucun fichier du depot n'a ete modifie hormis celui-ci, aucun commit. Les
16 entrees et 115 sorties d'essai deposees dans `input/` et `output/` de ComfyUI
ont ete effacees en fin d'essai.

**Un incident a signaler d'emblee : une entree de 4000 px a tue le processus
ComfyUI du studio.** Je l'ai relance avec `LANCER ComfyUI (2080 Ti).bat`, sans
rien changer a ses arguments. Detail au §1.4. Toutes les mesures des §2 a §5 qui
suivent cet incident ont ete prises sur ce serveur relance ; l'etat de cache est
indique a chaque fois.

---

## 0. Reponse courte

La promesse centrale tient : **le recollage rend `ecart hors masque = 0,000`,
p99 = 0, sur les 11 chaines completes mesurees dont la taille est multiple
de 16.** Rien de ce que j'ai essaye n'a fait mentir cette ligne-la.

Ce qui casse, c'est tout ce qui decide QUEL masque, et tout ce qui suppose que
l'image d'entree ressemble a celle des deux essais precedents.

Quatre defauts graves, tous reproductibles en une phrase :

| ce qu'on tape | ce qui se passe | le chiffre |
|---|---|---|
| « change le fond » sur une photo de cerf | le cerf perd sa tete, ses bois et ses pattes | **61,2 % du sujet est redessine**, 97,6 % dans la moitie haute |
| « remplace l'elephant par un rocher » sur une photo sans elephant | le cerf est efface et remplace par un rocher | masque « the elephant » vs « the deer » : **IoU 0,9906** |
| « change le ciel » sur un ciel plein cadre | l'image entiere est regeneree, annoncee comme retouche localisee | masque **99,96 %**, 100 % des pixels changes, 28,8 s |
| une photo de 4000 px | ComfyUI meurt ; a 2560 px il gele 11 minutes | VAE seul : 10,2 s a 1920 px, **656,4 s a 2560 px** |

Et un defaut moyen qui touche la taille d'image la plus repandue au monde :
**1920x1080 n'est pas multiple de 16 en hauteur**, donc le rendu est recolle
4 px trop haut et les 8 dernieres lignes ne sont jamais ecrites.

---

## 1. Les entrees hors norme

Toutes les chaines de ce paragraphe : `retoucher_zone`, cible `the deer`,
categorie OBJET (donc 4 etapes, `expand` 24), graine 424242, description
« un pre de brume doree au lever du soleil, herbes hautes ». Source :
`input/essai_agent.png`, le cerf de `essai_inpainting.md`, redimensionne.
Les sept lignes ont ete jouees a la suite sur un serveur chaud : elles sont
comparables entre elles, et `ref1216` est le temoin de la meme serie.

| entree | s | taille rendue | aire masque | dehors | p99 | %>2 | dedans |
|---|---|---|---|---|---|---|---|
| **ref1216** 1216x832 (temoin) | 12,18 | 1216x832 | 11,89 % | **0,000** | 0 | 0,00 | 46,26 |
| 128x128 | 7,69 | 128x128 | **43,35 %** | **0,000** | 0 | 0,00 | 27,66 |
| 1210x826 (ni mult. de 16 ni de 8) | 11,26 | 1210x826 | 11,92 % | **0,000** | 0 | 0,00 | 45,80 |
| 1208x832 (mult. de 8, pas de 16) | 11,11 | 1208x832 | 11,92 % | **0,000** | 0 | 0,00 | 50,85 |
| PNG RGBA (alpha en degrade) | 11,35 | 1216x832 **RGB** | 11,89 % | **0,000** | 0 | 0,00 | 46,26 |
| niveaux de gris (PNG mode `L`) | 11,57 | 1216x832 RGB | 11,90 % | **1,000** | 1 | 0,00 | 37,97 |
| quasi uniforme (gris 128 +/-1) | 11,88 | 1216x832 | **0,00 %** | 0,000 | 0 | 0,00 | 0,00 |
| 4000x2736 | — | — | — | — | — | — | — |

Le graphe passe partout, et le recollage tient sa promesse partout sauf en
niveaux de gris. Mais « le graphe passe » ne veut pas dire « le rendu est
utilisable » : trois lignes de ce tableau cachent un defaut.

### 1.1 128x128 — `GrowMask expand=24` est en pixels absolus

`expand` ne depend pas de la taille de l'image. Mesure du masque SAM 3.1 brut
puis du masque effectif (noeud 9 du graphe livre), meme sujet, quatre tailles :

| largeur | SAM 3.1 brut | apres `GrowMask(24)` | facteur | 24 px vaut |
|---|---|---|---|---|
| **128** | 6,26 % | **43,35 %** | **x6,92** | 18,8 % de la largeur |
| 1024 | 6,10 % | 12,62 % | x2,07 | 2,3 % |
| 1216 | 6,09 % | 11,89 % | x1,95 | 2,0 % |
| 1920 | 6,10 % | 10,26 % | x1,68 | 1,2 % |

A 128 px le masque du cerf n'est plus un cerf : c'est un polygone informe qui
couvre 43 % du cadre, bois et pattes noyes. Le rendu est correct comme image,
mais ce n'est plus une retouche localisee — 43 % du cadre a ete refait pour un
sujet qui en occupait 6,26 %.

`24` avait ete mesure sur une seule image de 1216 px, et `essai_inpainting.md`
§9 le disait deja : « J'ai deux points (0 et 24) sur une seule image et un seul
sujet ». Le chiffre ne se transporte pas d'une taille a l'autre non plus.

### 1.2 Largeur ou hauteur non multiple de 16 — le recollage est decale

**Cause, lue dans le code de ComfyUI.** `VAE.encode` appelle
`vae_encode_crop_pixels` (`comfy/sd.py:1087`), qui recadre au multiple de
`spacial_compression_encode()` — **16 pour le VAE flux2, pas 8** — en centrant
le recadrage : `x_offset = (dim % 16) // 2`. Le rendu decode est donc plus petit
que la source ET decale. `ImageCompositeMasked` le recolle ensuite a x=0, y=0
(`comfy_extras/nodes_mask.py`, fonction `composite`), et redimensionne le masque
en bilineaire a la taille de la SOURCE, pas de la DESTINATION.

**Mesure, sur la sortie recollee elle-meme.** Meme chemin que le graphe livre
(noeuds 4 -> 5 -> 13 -> 22 -> 23) avec un masque plein, pour que toute l'image
soit du rendu recolle et que le decalage devienne lisible :

| source | zone reellement recollee | % du cadre jamais recolle | meilleur recalage | ecart recale | ecart tel quel |
|---|---|---|---|---|---|
| 1216x832 | 1216x832 | 0,00 | dx 0, dy 0 | 1,38 | 1,38 |
| **1920x1080** | 1920x1072 | 0,74 | **dy = 4** | 1,25 | **3,39** |
| 1208x832 | 1200x832 | 0,66 | dx = 4 | 1,38 | 4,43 |
| 1210x826 | 1200x816 | **2,03** | **dx = 5, dy = 5** | 1,38 | **5,91** |

1,38 est le plancher de l'aller-retour VAE. Sans recalage on est de 2,5 a
4,3 fois au-dessus : le contenu retouche n'est pas la ou le masque le dit.

**Ce que ca donne a l'ecran.** « Refais l'herbe » (`the grass`, REGION) sur une
image 1920x1080, masque de 21,78 % qui touche la derniere ligne :

- les **8 dernieres lignes du cadre ne sont jamais recollees** — ecart 0,000 —
  alors que le masque y couvre 87,5 % ;
- juste au-dessus, lignes 1064 a 1072, l'ecart moyen est de **163,3 / 255**.

A l'oeil : une bande sombre parfaitement rectiligne de 8 px sur toute la
largeur, l'herbe d'origine sous la terre battue neuve. La meme demande sur la
meme image en 1216x832 ne montre rien (§5).

**Pourquoi ca n'a pas ete vu.** La metrique `dehors` des deux essais precedents
ne regarde qu'a plus de 40 px du masque. Elle donne 0,000 dans tous ces cas :
le decalage est un defaut *dans et autour* du masque. Elle est aveugle a ce
defaut par construction.

1920x1080 est la taille la plus courante du monde, et 1080 % 16 = 8.
Les sorties du studio, elles, sont des multiples de 16 : le defaut ne se
declenche que sur une image televersee. C'est exactement le cas d'usage vise.

### 1.3 Alpha, niveaux de gris, image quasi uniforme

- **PNG a canal alpha** : `LoadImage` rend un `IMAGE` en RGB et met l'alpha dans
  sa sortie `MASK`, que le graphe n'utilise pas. Entree RGBA, **sortie RGB** :
  la transparence est perdue sans un mot. Un sujet detoure par `g_detourage`
  ne peut donc pas etre retouche puis rester detoure.
- **Niveaux de gris** : `dehors = 1,000`, p99 = 1, **100 % des pixels a -1**.
  Ce n'est pas le graphe : un aller-retour `LoadImage -> SaveImage` seul, sans
  rien d'autre, donne deja 1,0000 sur 100 % des pixels pour un PNG mode `L`,
  contre 0,0000 pour un RGB, un RGBA et un 1210x826. C'est le chargeur d'images
  de ComfyUI (il passe par PyAV, `nodes.py:1760`). Rien a corriger dans
  `serveur.py`, mais la phrase « recollee a l'identique » est fausse dans ce cas.
- **Quasi uniforme** : SAM 3.1 ne trouve rien, masque a 0,00 %, et la chaine
  tourne quand meme **11,88 s** pour rendre la source au bit pres. Voir §2.2.

### 1.4 4000 px — le processus ComfyUI meurt

Le graphe `g_retouche_zone` n'a **pas** d'`ImageScaleToTotalPixels`,
contrairement a `g_edition`. Le choix est documente et il est bon : redimensionner
casserait silencieusement la promesse d'exactitude. Mais rien, ni dans le graphe
ni en amont dans `serveur.py`, ne borne la taille d'entree.

Mesures, VAE seul (encode + decode, sans echantillonneur ni masque) :

| largeur | Mpx | s | etat |
|---|---|---|---|
| 1216 | 1,01 | 3,54 | chaud |
| 1920 | 2,07 | 10,19 | chaud |
| **2560** | 3,60 | **656,43** | chaud |

Un facteur **64 pour 1,7 fois plus de pixels**. Et pendant ces 11 minutes,
**l'API HTTP de ComfyUI n'a plus repondu du tout** — ni `/queue`, ni
`/system_stats`, ni l'interface web. Le processus etait vivant et consommait du
CPU ; le serveur aiohttp etait affame. Sur une carte partagee, un utilisateur
qui depose une grande photo bloque tout le monde, y compris l'affichage.

Chaine complete, pour comparer :

| entree | s | etat |
|---|---|---|
| 1216x832 | 12,18 | chaud |
| 1920x1080 | 60,98 puis 66,56 | chaud |
| **4000x2736** | — | **le processus ComfyUI est mort** |

Apres environ neuf minutes sur le 4000x2736, plus de socket en ecoute sur 8188,
plus de processus `ComfyUI\main.py`, et **aucune trace dans le journal
d'evenements Windows** (verifie sur 40 minutes) : sortie silencieuse, pas de
crash signale. La memoire systeme n'etait pas en cause (27,5 Go libres au
moment du blocage a 2560 px).

Observe **une fois**. Je n'ai pas reprovoque le cas : la carte est celle du
studio. Le mecanisme est en revanche etabli par la ligne des 656 s.

Une photo de telephone recente fait 4032x3024, soit 12,2 Mpx — franchement
au-dela du point ou j'ai vu le serveur mourir.

---

## 2. Les masques degeneres

### 2.1 Cible absente — SAM 3.1 rend le sujet saillant, en silence

C'est le defaut le plus dangereux de la livraison, parce que le rendu est beau.

`essai_masque_texte.md` §4.2 avait mesure ce repli sur du charabia et conclu
que le seuil 0,70 le tuait. **Il ne le tue pas** : il tue le charabia, pas un
mot anglais valide qui designe un objet absent.

Masques seuls, seuil 0,70 (celui du graphe livre), sur `essai_agent.png` :

| consigne | aire | |
|---|---|---|
| `the deer` (reference) | 6,09 % | |
| **`the elephant`** | **6,05 %** | **IoU 0,9906 avec `the deer`** |

L'elephant hors du cerf : **0,008 % de l'image**. Le cerf hors de l'elephant :
0,049 %. Ce sont le meme masque.

Sur une image sans objet saillant (un mur de crepi), `the elephant` rend bien
0,00 % : le repli demande un sujet dominant, comme au §4.2 de l'essai. La photo
de cerf en a un ; une photo de voiture, de chien ou de portrait aussi.

**Chaine complete**, « remplace l'elephant par un rocher gris couvert de
mousse » : 14,88 s, masque 11,84 %, `dehors` 0,000, 14,98 % des pixels changes.
A l'ecran : le cerf a disparu, un rocher moussu se dresse a sa place, et la
conversation affiche « retouche localisee — hors du masque, l'image est
recollee a l'identique ».

**La verification prescrite n'existe pas.** `essai_masque_texte.md` §4.4 et §6
demandaient explicitement, en amont du graphe : lancer SAM 3.1 seul, lire l'aire,
et court-circuiter si elle est nulle ou enorme. Rien de tel dans `serveur.py` :
la branche `intention == "retoucher_zone"` (ligne 4861) passe de `preparer_cible`
directement a `g_retouche_zone`. Aucun repli BiRefNet non plus, alors que le §4.4
le demandait aussi. Le cout de la verification evitee est de **0,72 a 1,28 s**
(une passe SAM 3.1 seule, mesuree dix fois).

Une verification d'aire n'aurait rien change ici : 11,84 %, c'est une aire
parfaitement normale. Le seul controle qui attraperait ce cas est de comparer
la detection a la reference BiRefNet, ou de rendre la boite et son score.

### 2.2 Masque vide — une session GPU complete pour ne rien faire

| cas | etapes | s | masque | resultat |
|---|---|---|---|---|
| `the deer` sur image quasi uniforme | 4 | **11,88** | 0,00 % | identique au bit pres |
| `the elephant` sur un mur | 4 | **9,66** | 0,00 % | identique au bit pres |
| `retoucher_sujet` sur un mur | 4 | **11,14** | 0,00 % | identique au bit pres |
| `retoucher_sujet` sur un ciel vide | 4 | **11,10** | 0,00 % | identique au bit pres |
| `retoucher_sujet` sur quasi uniforme | 4 | **12,94** | 0,00 % | identique au bit pres |

Ecart moyen 0,000, ecart max 0, 0,00 % des pixels touches : cinq fois, la chaine
a rendu exactement son entree. L'utilisateur voit « retouche localisee », attend
dix a treize secondes, et recoit son image telle quelle, sans explication.

C'est exactement le §7.3 de `essai_masque_texte.md` (13,13 s mesurees), qui
concluait « il faut court-circuiter avant ». Non fait.

**Pire que vide.** `the ocean` (categorie REGION, donc 16 etapes) sur un mur de
crepi ne rend pas 0,00 % : il rend **99,96 %**. 23,88 s, 100 % des pixels
changes. Une cible absente sur une image sans structure peut donc produire
l'echec vide *ou* l'echec plein cadre, selon l'image.

### 2.3 Cible qui couvre tout le cadre

| cas | aire masque | etapes | s | % pixels changes | ecart max |
|---|---|---|---|---|---|
| `the sky` sur un ciel plein cadre | **99,96 %** | 16 | 28,79 | 100,00 | 219 |
| `the photograph` sur la photo de cerf | **99,90 %** | 16 | 29,09 | 100,00 | 253 |
| `the image` sur la photo de cerf | 99,82 % | — | — | — | — |
| `the ocean` (REGION) sur un mur | 99,96 % | 16 | 23,88 | 100,00 | 188 |

Et par BiRefNet, sur une image sans sujet identifiable, `retoucher_fond` donne
**100,00 %** exactement (§3).

Dans tous ces cas la metrique `dehors` n'a **aucun pixel a mesurer** : mon
harnais rend `None`. La phrase affichee a l'utilisateur — « hors du masque,
l'image est recollee a l'identique » — est litteralement vraie et entierement
vide. Il recoit une image neuve a 16 etapes dans une conversation qui lui a
promis le contraire.

`the photograph` et `the image` ne sont pas des cibles absurdes : ce sont
exactement le genre de mots que `SYS_CIBLE` peut faire produire quand la demande
est vague (« change l'ambiance de cette image »), d'autant que §4 attrape
justement ce genre de formulation.

Le controle « aire > 0,90 -> refuser » propose au §6 de `essai_masque_texte.md`
attraperait les quatre lignes ci-dessus. Il n'est pas ecrit.

### 2.4 Masque qui touche le bord

Tenu, quand la taille est multiple de 16. `the grass` sur `essai_agent.png`
(1216x832), masque 21,86 % touchant la derniere ligne : 24,25 s, `dehors`
0,000, aucune coupure visible au bas du cadre, l'herbe devient de la terre
battue et le cerf reste intact jusqu'aux sabots.

Le meme masque sur la meme image en 1920x1080 casse — mais c'est le defaut
du §1.2, pas celui du bord.

### 2.5 Masque en miettes — je n'ai pas su fabriquer le cas

`the trees`, `the leaves`, `the blades of grass:20` sur la photo d'essai rendent
tous **0,00 %** au seuil 0,70. Je n'ai pas trouve de cible qui rende beaucoup de
petites taches sur les images dont je disposais. **Je ne peux donc rien dire de
ce cas** — ni qu'il tient, ni qu'il casse. C'est un manque de cet essai.

Ce qu'on peut deduire sans le mesurer : un masque en miettes passerait par
`GrowMask(24)`, qui souderait des taches distantes de moins de 48 px, puis par
`ImageBlur 11`. Le recollage exact hors masque n'a aucune raison de bouger. La
question ouverte est le rendu a l'interieur, pas la preservation.

---

## 3. BiRefNet sans sujet — et le sujet detruit quand il y en a un

### 3.1 `retoucher_fond` detruit le sujet qu'il promet de preserver

C'est le defaut le plus grave de la livraison, et il frappe le cas nominal, pas
un cas limite.

`g_retouche_zone` fixe `expand = 0 if region else 24`. `region` n'est jamais
vrai pour `retoucher_fond` : la branche ligne 4883 appelle le graphe sans le
parametre. Le `GrowMask(24)` s'applique donc au masque **du fond**, et le dilate
**dans le sujet**.

Mesure sur `essai_agent.png`, masque effectif du graphe livre (noeud 9) :

| | % de l'image |
|---|---|
| sujet BiRefNet seuille | 6,10 % |
| masque redessine par `retoucher_fond` | **97,63 %** |
| reellement preserve | **2,37 %** |
| du sujet, redessine quand meme | **3,73 %** de l'image |

Soit **61,2 % du sujet redessine**. Reparti :

| | part du sujet effacee |
|---|---|
| moitie haute du cadre (les bois) | **97,6 %** |
| moitie basse (le corps) | 54,0 % |

Chaine complete : 25,95 s, 16 etapes, **98,64 % des pixels changent**, ecart
max 253. `dehors` vaut bien 0,000 — sur les 2,37 % de pixels qui restent.

A l'ecran, « change le fond » avec « une plage de sable au crepuscule, mer
calme » : le cerf n'a plus de tete, plus de bois, plus de pattes. Il reste un
tronc de fourrure brune sans forme, a moitie noye dans l'ecume. L'utilisateur a
demande a changer le decor.

**La regle enfreinte est ecrite dans l'essai que le code cite.**
`essai_masque_texte.md` §5.3 : dilater quand on remplace un OBJET, **ne pas
dilater quand on refait une REGION**. Le fond est une region par definition —
c'est la plus grande region possible. Le commentaire de `g_retouche_zone` cite
ce paragraphe a la ligne au-dessus et fait l'inverse.

`essai_inpainting.md` §5 avait pourtant note pour V2 « le cerf est preserve au
pixel pres ». Cette observation ne survit pas a la mesure du masque : avec le
graphe livre, 61,2 % du cerf est a l'interieur du masque.

Note secondaire : `retoucher_fond` force 16 etapes (`grande = region or not
sur_le_sujet`), d'ou 25,95 s. Les essais annoncaient 14 a 16 s pour V2.

### 3.2 Sans sujet identifiable, BiRefNet rend 0 % — donc le fond rend 100 %

Masque BiRefNet + `ThresholdMask 0.5`, images sans sujet :

| image | aire sujet |
|---|---|
| mur de crepi | **0,00 %** |
| ciel en degrade | **0,00 %** |
| gris 128 +/-1 | **0,00 %** |
| photo de cerf (temoin) | 6,10 % |

D'ou, apres `InvertMask` et `GrowMask(24)`, le masque effectif :

| image | `retoucher_sujet` | `retoucher_fond` |
|---|---|---|
| mur | 0,00 % | **100,00 %** |
| ciel | 0,00 % | **100,00 %** |
| quasi uniforme | 0,00 % | **100,00 %** |
| cerf (temoin) | 12,09 % | 97,63 % |

Chaines completes correspondantes :

| cas | etapes | s | % pixels changes | ecart max | ce que voit l'utilisateur |
|---|---|---|---|---|---|
| `fond` sur un mur | 16 | 28,54 | **100,00** | 188 | une image entierement neuve |
| `fond` sur un ciel | 16 | 28,16 | **100,00** | 240 | une image entierement neuve |
| `fond` sur quasi uniforme | 16 | 32,88 | **100,00** | 129 | une image entierement neuve |
| `sujet` sur un mur | 4 | 11,14 | 0,00 | 0 | son image inchangee |
| `sujet` sur un ciel | 4 | 11,10 | 0,00 | 0 | son image inchangee |
| `sujet` sur quasi uniforme | 4 | 12,94 | 0,00 | 0 | son image inchangee |

Les deux moteurs BiRefNet degenerent donc de facon symetrique et opposee sur la
meme image : `retoucher_sujet` ne fait rien pendant onze secondes,
`retoucher_fond` refait tout pendant trente. Les deux annoncent une retouche
localisee.

Le temoin `retoucher_sujet` sur la photo de cerf, lui, marche : 11,90 s, masque
12,09 %, `dehors` 0,000, le cerf remplace proprement.

---

## 4. L'aiguillage a l'ecrit attrape des demandes globales

Les trois motifs sont essayes dans l'ordre de `serveur.py:1874` des qu'une image
est jointe, **avant tout appel au modele**. Resultat sur des formulations
ordinaires :

| demande | route vers |
|---|---|
| enleve la voiture | retoucher_zone (correct) |
| change seulement le ciel | retoucher_zone (correct) |
| change le fond | retoucher_fond (correct) |
| **est-ce que tu peux refaire cette image en plus lumineux** | **retoucher_zone** |
| **il faudrait juste changer les couleurs de toute l'image** | **retoucher_zone** |
| **je voudrais que tu changes le style en aquarelle** | **retoucher_zone** |
| **il faut que tu changes tout** | **retoucher_zone** |
| **remplace cette image par une version carree** | **retoucher_zone** |
| **enleve le grain** / **enleve le flou** / **enleve le bruit de l'image** | **retoucher_zone** |
| **supprime le texte en bas** | retoucher_zone |
| **vire ce truc** | **retoucher_zone** |
| **efface** (mot seul) | **retoucher_sujet** |

Deux causes distinctes :

1. `_SEULEMENT` contient `\bque\b`. « est-ce **que** », « je voudrais **que** »,
   « il faut **que** » sont les tournures les plus courantes du francais parle.
   Associees a n'importe quel `chang|remplac|refai|met[st]?`, elles suffisent.
2. Le second chemin de `veut_zone_nommee` accepte tout verbe de suppression
   suivi de quoi que ce soit qui ne soit pas « le sujet / le personnage / la
   personne / le fond ». « le grain », « le flou », « le bruit », « ce truc »
   passent. `_SUJET` seul, sans complement, tombe dans `retoucher_sujet`.

Consequence : ces demandes ne partent plus vers `edition`. Combinees au §2.1,
elles finissent en masque sur l'objet saillant, et l'objet saillant est efface.
C'est une regression fonctionnelle sur ce que le studio savait faire — pas sur
le graphe de `g_edition`, qui est intact (§5).

**Note secondaire, dans l'autre sens.** `decrire_zone` et `preparer_cible`
cherchent `_SUJET` dans la DESCRIPTION rendue par le modele. Rejettent donc, a
tort : « un ciel **efface** par la brume », « un horizon **efface** dans le
brouillard », « une **vire** rocheuse couverte de mousse ». Le modele avait bien
repondu ; l'utilisateur recoit « je n'arrive pas a decrire ce qu'il faut mettre
a la place ».

---

## 5. Les regressions : il n'y en a pas

`g_edition` et `g_detourage` partagent BiRefNet, le VAE flux2, klein 4B et
`qwen_3_4b` avec les nouveaux moteurs. Les deux marchent toujours.

**`g_detourage`** — 1,78 s sur la photo de cerf (BiRefNet froid), sortie RGBA
1216x832, **93,90 % transparent / 6,10 % opaque**, coherent avec le masque
BiRefNet mesure separement et avec le docstring. Sur un PNG a canal alpha en
entree : meme resultat, l'alpha d'origine est ignore. Sur une image sans sujet :
100 % transparent — comportement anterieur, sans rapport avec cette livraison.

**`g_edition`** — 19,01 s au premier appel (klein froid), 16,4 a 16,5 s ensuite.
Sa mise a l'echelle a 1 Mpx fonctionne comme avant : 1216x832 -> 1232x832,
1210x826 -> 1232x832, 128x128 -> 1024x1024. Aucun signe de degradation.

**SAM 3.1 reste au niveau annonce** quand la cible existe : `the deer` en
1,08 a 2,01 s, **IoU 0,9711** avec le masque BiRefNet du meme sujet — meme
ordre de grandeur que le 0,9831 de `essai_masque_texte.md` §3.2.

---

## 6. Ce qui tient

Une ligne chacun, comme demande.

- **Le recollage est exact.** 11 chaines completes mesurees a taille multiple
  de 16 : `dehors = 0,000`, p99 = 0, %>2 = 0,00, sans une exception. La
  promesse centrale des deux essais precedents ne bouge pas.
- **Un masque qui touche le bord n'ajoute pas de couture**, a taille multiple
  de 16 (masque 21,86 % touchant la derniere ligne, rien de visible).
- **Une petite zone n'a pas besoin de plus de 4 etapes** : rapport de texture
  zone/anneau **1,85** a 4 etapes (9,87 s) contre 2,05 a 16 etapes (26,55 s),
  pour une zone de 11,89 %. Le pari du graphe est bon a cette taille ; je n'ai
  pas construit de cas OBJET assez grand pour le faire tomber.
- **Le graphe passe sur toutes les entrees hors norme sauf la plus grande** :
  128 px, 1208, 1210, 1080p, alpha, gris, quasi uniforme — aucune erreur
  d'execution, aucune taille de sortie perdue.
- **`g_edition` et `g_detourage` sont intacts.**

---

## 7. Ce que je n'ai PAS tranche

- **La reproductibilite de la mort de ComfyUI a 4000 px.** Observee une fois,
  non reprovoquee : c'est la carte du studio. Le mecanisme est etabli par les
  656 s a 2560 px, le seuil exact ne l'est pas.
- **Le masque en miettes.** Aucune cible de mon jeu d'images n'en a produit un.
  §2.5.
- **Le cas OBJET de grande aire.** Je n'avais pas de photo ou un objet nomme
  occupe 20 a 40 % du cadre ; l'arbitrage 4/16 etapes n'est donc eprouve que
  sur une zone de 11,89 %.
- **Les cibles produites par le vrai `preparer_cible`.** J'ai injecte les cibles
  a la main pour controler l'experience. Je n'ai pas mesure a quelle frequence
  le modele d'ecriture produit `the photograph`, `the image`, ou une cible
  absente. Le §2.3 montre ce que ca coute quand ca arrive, pas combien de fois
  ca arrive.
- **`individual_masks` et les boites de SAM 3.1.** Le noeud rend les boites avec
  leur score, seul endroit d'ou lire une confiance depuis un graphe. Ce serait
  la piste evidente contre le §2.1, et je ne l'ai pas essayee.
- **Le comportement en presence de plusieurs images ou d'un lot.** Non essaye.
- **Le seuil de taille exact ou la chaine cesse d'etre tenable.** J'ai trois
  points (1,01 / 2,07 / 3,60 Mpx) et une mort a 10,9. La courbe est franchement
  superlineaire, je ne lui donne pas de forme.
- **Une image dont la LARGEUR seule est non multiple de 16.** J'ai mesure la
  hauteur seule (1080p), les deux (1210x826), et la largeur seule a un multiple
  de 8 (1208x832). Le cas largeur non multiple de 8 avec hauteur correcte n'a
  pas ete isole ; rien ne laisse penser qu'il differe.

---

## 8. Protocole, pour rejouer

- Les graphes mesures sont ceux du depot : `g_retouche_zone`, `g_edition` et
  `g_detourage` sont extraits de `serveur.py` par `ast` et executes tels quels,
  jamais recopies. Un instantane du fichier a ete pris au debut de l'essai pour
  ne pas etre pris au milieu d'une edition en cours.
- Image de depart : `input/essai_agent.png` (1216x832, le cerf de
  `essai_inpainting.md`), redimensionnee en LANCZOS pour toutes les variantes
  de taille ; mur, ciel et image quasi uniforme fabriques en numpy.
- Graine unique : 424242. Cible unique pour les comparaisons de taille :
  `the deer`, categorie OBJET.
- Les masques mesures sont **toujours** ceux du graphe, exportes par un
  `MaskToImage` + `SaveImage` branches sur le noeud 9 en plus du graphe livre —
  jamais une reconstruction. L'ajout ne touche pas le chemin 23 -> 24.
- Mesures en numpy/scipy dans le python embarque de ComfyUI
  (`D:\ComfyUI_windows_portable\python_embeded\python.exe`), sur les PNG
  rapatries via `/view`. `dehors` = ecart moyen en niveaux 0-255 a plus de 40 px
  du masque, `p99`, `%>2`, `dedans` : memes definitions que
  `essai_inpainting.md` §4.
- Le harnais attend `/queue` vide avant chaque envoi, pour ne pas bousculer le
  studio. Une seule serie a ete interrompue, par la mort du serveur (§1.4).
- Etats de cache : la serie du §1 est chaude et homogene (`ref1216` en est le
  temoin). Les series des §2, §3 et §5 ont ete jouees a la suite sur le serveur
  relance : le premier appel de chaque famille de poids est froid
  (`g_detourage` 1,78 s, `g_edition` 19,01 s), tout le reste est chaud et
  comparable a l'interieur de sa serie. Ne pas comparer une ligne du §1 a une
  ligne du §3 sans le dire.
- Fichiers d'essai effaces : `input/lim_*.png` (16 fichiers) et
  `output/**/lim_*` (115 fichiers).
