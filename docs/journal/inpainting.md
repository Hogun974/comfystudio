# Retouche localisee (inpainting) — ce que la mesure decide

> **Compte rendu daté du 30 août 2026, gardé tel quel.**
> Rien n'a bougé sur le fond. Suivi par
> [Un masque depuis une description](masque_texte.md) puis
> [Où la retouche casse](retouche_limites.md).
> Voir [le journal des essais](README.md) pour ce qui a bougé depuis, et
> [la documentation](../README.md) pour l'état actuel.

Essai mene le 30/08/2026 sur la machine du studio (RTX 2080 Ti 11 Go, ComfyUI
0.33.1, torch 2.13 / cu130). Aucun fichier du depot n'a ete modifie, aucun
commit. Les fichiers deposes dans `input/` et `output/` de ComfyUI ont ete
effaces en fin d'essai.

---

## 0. Reponse courte

Oui, une voie praticable existe, avec ce qui est deja installe, et elle ne
ressemble pas a ce qu'on aurait parie.

Le point de bascule n'est ni le masque ni le modele : c'est **`ReferenceLatent`**.
Le graphe `g_edition` actuel le branche pour donner l'image de depart au moteur.
Tant qu'il est la, le moteur redessine le contenu d'origine A L'INTERIEUR du
trou : on lui dit « remplace le cerf par un rocher », il dessine un rocher
DERRIERE le cerf. En le retirant et en decrivant la cible au lieu de donner un
ordre, FLUX.2 klein 4B devient un moteur d'inpainting correct.

Trois chiffres qui resument tout, sur la meme image et le meme masque :

| route | ecart moyen hors masque (niveaux /255) |
|---|---|
| edition globale d'aujourd'hui (temoin) | **27,10** — 99 % des pixels bougent |
| masquage dans le latent seul | **1,18** — soit le plancher du VAE (1,28) |
| masquage + recollage en pixels | **0,000** — identique bit a bit |

Ce qui NE marche pas avec ce qui est installe : produire un masque a partir
d'une description libre (« la voiture », « le panneau »). Il n'y a pas de
segmenteur ouvert. Voir §2.

---

## 1. Quels noeuds d'inpainting sont reellement disponibles

Releve sur `/object_info` (855 noeuds). Les noeuds utiles, et leur sort :

| noeud | present | utilisable ici | pourquoi |
|---|---|---|---|
| `SetLatentNoiseMask` | oui | **oui, retenu** | marche avec n'importe quel modele, ne demande pas de modele d'inpainting dedie |
| `ImageCompositeMasked` | oui | **oui, retenu** | recollage en pixels, seul moyen d'atteindre l'ecart nul |
| `GrowMask` | oui | **oui, retenu** | dilate le masque ; indispensable, cf. §6 |
| `ImageBlur` (+ `MaskToImage`/`ImageToMask`) | oui | **oui, retenu** | le seul flou de CONTOUR disponible |
| `ThresholdMask` | oui | **oui, retenu** | corrige un piege de BiRefNet, cf. §7 |
| `InvertMask`, `MaskComposite`, `SolidMask`, `CropMask`, `LoadImageMask` | oui | oui | briques de masque |
| `VAEEncodeForInpaint` | oui | non retenu | efface la zone avant encodage ; suppose un modele entraine pour l'inpainting (aucun ici) |
| `InpaintModelConditioning` | oui | non retenu | pose un `concat_latent_image` que seul un modele « fill / inpaint » consomme. Aucun modele de ce type n'est installe |
| `DifferentialDiffusion` | oui | **teste, rejete** | annule l'edition sur un programme a 4 pas, cf. §7 |
| `FeatherMask` | oui | **piege**, cf. §7 | ne fait pas ce que son nom dit |
| `SAM3_Detect` / `SAM3_VideoTrack` | oui (natifs ComfyUI) | **non** : aucun poids | cf. §2 |
| `MediaPipeFaceMask` / `LoadMediaPipeFaceLandmarker` | oui | **non** : aucun poids | `models/detection/` est vide, la liste deroulante du chargeur est vide |
| `ControlNetInpaintingAliMamaApply` | oui | **non** | `models/controlnet/` est vide |
| `BriaGenFill`, `FluxProFillNode`, `RecraftImageInpainting` | oui | **non** | noeuds d'API payante, pas de calcul local |

Inventaire des poids reellement presents (`models/`) : RealVisXL V5.0 et
Pony V6 XL en SDXL, FLUX.2 klein 4B (+ base 4B, + 9B GGUF), FLUX.1 dev,
z-image turbo, Wan 2.2, ACE-Step, hunyuan3d, BiRefNet, 4x-UltraSharp, film_net.
**Aucun** modele d'inpainting dedie, **aucun** ControlNet, **aucun** GLIGEN,
**aucun** modele de detection.

Conclusion : l'inpainting ici ne peut pas passer par un modele specialise. Il
doit passer par le masquage du bruit dans le latent, qui est agnostique au
modele. C'est ce que fait le graphe retenu.

---

## 2. Le masque : ce qui est possible sans que l'utilisateur dessine

### 2.1 Ce qui marche aujourd'hui : BiRefNet

`LoadBackgroundRemovalModel` + `RemoveBackground` rend un masque **du sujet**
(blanc = sujet). Attention : `g_detourage` inverse ensuite ce masque, et c'est
correct — `JoinImageWithAlpha` inverse a son tour en interne (convention
« masque = ce qu'on retire »). Les deux inversions se compensent.

Sur l'image d'essai (un cerf en contre-jour, 1216x832) le masque est net,
bois compris, en **2,0 s**. Surface : 6,10 % de l'image.

Cela couvre exactement deux demandes, et pas une de plus :

- « change le fond / le decor / l'arriere-plan » → masque = `InvertMask(sujet)`
- « enleve / remplace le sujet principal » → masque = `sujet`

### 2.2 Ce qui ne marche pas : un masque a partir d'une description

Il n'y a aucun segmenteur ouvert installe. `SAM3_Detect` est present dans
ComfyUI (natif, `comfy_extras/nodes_sam3.py`) et prendrait exactement ce qu'il
faut : une image + une `CONDITIONING` issue de `CLIPTextEncode`, et rendrait un
`MASK` et une `BOUNDING_BOX`. C'est la piste evidente et elle est propre.

Mais il lui faut un checkpoint SAM3 : `comfy/supported_models.py` declare une
classe `SAM3` chargee par `CheckpointLoaderSimple` (le fichier contient le
detecteur ET son encodeur de texte, `detector.backbone.language_backbone.*`).
La liste deroulante de `CheckpointLoaderSimple` ne contient que RealVisXL,
Pony et hunyuan3d : **le poids n'est pas la**. Meme constat pour MediaPipe,
dont le chargeur affiche une liste vide.

Prix a payer si on veut « le ciel », « la voiture », « le panneau » : un
telechargement dans `models/checkpoints/`. Je n'ai pas telecharge et **je ne
donne donc pas de taille verifiee** — a mesurer avant de l'inscrire au
`CATALOGUE`. C'est le seul manque, mais c'est celui qui separe « change le
fond » de « change seulement le ciel ».

### 2.3 Les deux replis sans telechargement, mesures

**Le rectangle.** Le studio a deja un LLM qui aiguille ; un modele de vision
peut rendre une boite pour « la voiture ». J'ai simule ce cas avec la boite
englobante du masque BiRefNet (19,5 % de l'image contre 6,1 % pour la
silhouette). Verdict : **ca marche mieux que la silhouette**, parce que le
modele a la place de dessiner autre chose que la forme d'origine. Contrepartie :
tout ce qui est dans la boite est refait, y compris le decor autour de l'objet.

**La bande geometrique.** « Le ciel » = les 300 premieres lignes, via
`SolidMask` + `MaskComposite`. Mecaniquement impeccable — tout ce qui est en
dessous est preserve au bit pres apres recollage. Visuellement, non : la
coupure est horizontale et rectiligne alors que la limite du ciel ne l'est pas,
les cimes d'arbres sont tranchees en plein milieu. Chiffre de la couture :
**exces de crete 3,59** (voir §6), la valeur la plus mauvaise de tout l'essai.
Utilisable seulement si le ciel occupe franchement le haut du cadre.

---

## 3. Le graphe retenu

Valide sur trois demandes (V1 effacer le sujet, V2 changer le fond,
V3 variante). JSON pret a etre construit par `serveur.py`. Les commentaires
sont hors du JSON, chaque bloc est repere par ses numeros de noeuds.

```jsonc
{
  // --- moteurs : exactement ceux de g_edition, rien a telecharger ---
  "1":  {"class_type":"UNETLoader",
         "inputs":{"unet_name":"flux-2-klein-4b.safetensors","weight_dtype":"default"}},
  "2":  {"class_type":"CLIPLoader",
         "inputs":{"clip_name":"qwen_3_4b.safetensors","type":"flux2","device":"default"}},
  "3":  {"class_type":"VAELoader","inputs":{"vae_name":"flux2-vae.safetensors"}},
  "4":  {"class_type":"LoadImage","inputs":{"image":"ENTREE.png"}},

  // --- le masque ---
  // RemoveBackground rend le masque DU SUJET (blanc = sujet).
  "5":  {"class_type":"LoadBackgroundRemovalModel",
         "inputs":{"bg_removal_name":"birefnet.safetensors"}},
  "6":  {"class_type":"RemoveBackground",
         "inputs":{"bg_removal_model":["5",0],"image":["4",0]}},
  // ThresholdMask n'est PAS decoratif : le masque BiRefNet vaut ~0,0015 loin
  // du sujet, jamais 0. Sans seuillage le recollage laisse 0,55/255 d'ecart
  // sur TOUTE l'image ; avec, on tombe a 0,000. Mesure au §7.
  "7":  {"class_type":"ThresholdMask","inputs":{"mask":["6",0],"value":0.5}},
  // Pour « change le fond », inserer ici :
  //   "8": {"class_type":"InvertMask","inputs":{"mask":["7",0]}}
  //   et faire pointer le noeud 9 sur ["8",0].
  // GrowMask=24 : avec 0, il reste un fantome du sujet, arete de crete 9,93
  // contre 0,89 a 24. C'est la mesure qui choisit cette valeur, pas le gout.
  "9":  {"class_type":"GrowMask","inputs":{"mask":["7",0],"expand":24,
         "tapered_corners":true}},

  // --- masque DOUX, pour le recollage seulement ---
  // FeatherMask ne convient pas : il degrade depuis les bords de l'IMAGE, pas
  // depuis le contour du masque. Le seul flou de contour passe par l'image.
  // blur_radius=11 : minimum mesure de l'exces de crete (§6).
  "10": {"class_type":"MaskToImage","inputs":{"mask":["9",0]}},
  "11": {"class_type":"ImageBlur","inputs":{"image":["10",0],
         "blur_radius":11,"sigma":5.5}},
  "12": {"class_type":"ImageToMask","inputs":{"image":["11",0],"channel":"red"}},

  // --- l'echantillonnage, sur la latente de la SOURCE ---
  // g_edition part d'une EmptyFlux2LatentImage : tout est regenere, il n'y a
  // rien a preserver. Ici on part de la source, et on masque le bruit.
  // Le masque DUR (noeud 9) est utilise ici, pas le doux : un masque doux dans
  // le latent ne fait que diluer l'edition.
  "13": {"class_type":"VAEEncode","inputs":{"pixels":["4",0],"vae":["3",0]}},
  "14": {"class_type":"SetLatentNoiseMask","inputs":{"samples":["13",0],
         "mask":["9",0]}},

  // --- le conditionnement : PAS de ReferenceLatent ---
  // C'est le seul changement qui fait passer le rendu de « inutilisable » a
  // « bon ». Avec ReferenceLatent le moteur redessine le contenu d'origine
  // dans le trou (le cerf reapparait devant le rocher) ; sans lui, il remplit
  // le trou d'apres la DESCRIPTION, le contexte lui venant de la latente non
  // masquee. Consequence de conception : le texte doit DECRIRE la zone voulue,
  // pas donner un ordre. « enleve la voiture » -> « la route vide, asphalte
  // mouille, meme lumiere ». C'est un appel LLM de plus, separe de
  // l'aiguillage.
  // Bonus mesure : sans ReferenceLatent le rendu tombe de 16,6 s a 10,1 s
  // (la latente de reference doublait la longueur de sequence en attention).
  "15": {"class_type":"CLIPTextEncode","inputs":{"text":"DESCRIPTION","clip":["2",0]}},
  "16": {"class_type":"ConditioningZeroOut","inputs":{"conditioning":["15",0]}},
  "17": {"class_type":"CFGGuider","inputs":{"model":["1",0],"positive":["15",0],
         "negative":["16",0],"cfg":1.0}},
  "18": {"class_type":"KSamplerSelect","inputs":{"sampler_name":"euler"}},
  // 4 pas : le reglage d'edition du studio. 8 pas ne corrigent RIEN au probleme
  // de ReferenceLatent (essai fait, le cerf reste) et coutent 29,2 s au lieu
  // de 16,6 s. Le nombre de pas n'etait pas la question.
  "19": {"class_type":"Flux2Scheduler","inputs":{"steps":4,"width":1216,"height":832}},
  "20": {"class_type":"RandomNoise","inputs":{"noise_seed":424242}},
  "21": {"class_type":"SamplerCustomAdvanced","inputs":{"noise":["20",0],
         "guider":["17",0],"sampler":["18",0],"sigmas":["19",0],
         "latent_image":["14",0]}},
  "22": {"class_type":"VAEDecode","inputs":{"samples":["21",0],"vae":["3",0]}},

  // --- le recollage en pixels ---
  // Non negociable. Le masquage dans le latent est EXACT dans le latent
  // (comfy/samplers.py:642 : out = out*masque + latente_origine*(1-masque)),
  // mais le decodeur du VAE n'est pas local : quand la zone masquee change
  // beaucoup, le decodage du reste bouge aussi. Mesure : 4,29/255 sur une
  // boite, 12,93 sur une bande. Le recollage ramene a 0,000.
  "23": {"class_type":"ImageCompositeMasked","inputs":{"destination":["4",0],
         "source":["22",0],"x":0,"y":0,"resize_source":false,"mask":["12",0]}},
  "24": {"class_type":"SaveImage","inputs":{"images":["23",0],
         "filename_prefix":"PREFIXE"}}
}
```

Le graphe suppose que l'image d'entree est deja a une taille multiple de 16.
J'ai volontairement retire le `ImageScaleToTotalPixels` de `g_edition` pendant
l'essai, pour que la source mesuree soit exactement celle qui entre dans
l'echantillonneur. En production il faut le remettre AVANT le noeud 4 (ou
redimensionner cote serveur), et alimenter `Flux2Scheduler` par un
`GetImageSize` comme le fait `g_edition`.

---

## 4. Ce qui est preserve hors du masque

Meme image, meme graine (424242), meme masque sauf mention contraire.
`dehors` = ecart moyen en niveaux 0-255, calcule sur les pixels situes a plus
de N px du masque (N=8 pour les routes sans recollage, 40 pour celles avec
recollage flou, afin d'exclure la bande de transition).
`%>2` = proportion de pixels dont un canal bouge de plus de 2 niveaux.
`dedans` = meme ecart, a l'interieur du masque : c'est le temoin que quelque
chose s'est bien passe.

| route | dehors | p99 | %>2 | dedans |
|---|---|---|---|---|
| **plancher** — VAE flux2 encode/decode seul | 1,281 | 8 | 25,70 | 1,83 |
| **plancher** — VAE sdxl encode/decode seul | 1,707 | 16 | 26,88 | 3,69 |
| **temoin** — edition globale (g_edition actuel) | **27,100** | 226 | **99,01** | 8,53 |
| edition globale + recollage | 0,555 | 1 | 0,00 | 8,52 |
| latent masque, silhouette | **1,183** | 8 | 21,40 | 12,59 |
| latent masque, silhouette + grow 8 | 1,197 | 8 | 22,29 | 10,50 |
| latent masque, silhouette + grow8 + flou + DiffDiff | 1,299 | 8 | 26,98 | 3,32 |
| latent masque, BOITE | 4,291 | 17 | 98,41 | 57,67 |
| latent masque, BOITE + recollage | **0,000** | 0 | 0,00 | 60,88 |
| latent masque, bande ciel h=300 | 12,928 | 46 | 99,99 | 83,53 |
| latent masque, bande ciel + recollage | **0,000** | 0 | 0,00 | 87,13 |
| SDXL RealVis, silhouette, denoise 0,75 | 1,740 | 17 | 27,67 | 69,05 |
| SDXL RealVis, silhouette grow8 + recollage | 0,160 | 1 | 0,00 | 48,57 |
| **RETENU** V1 effacer le sujet | **0,000** | 0 | 0,00 | 89,18 |
| **RETENU** V2 changer le fond | **0,000** | 0 | 0,00 | 99,04 |

Lecture :

1. **Le temoin fait son travail de temoin.** L'edition globale d'aujourd'hui
   deplace 99,01 % des pixels hors de la zone visee, de 27,10 niveaux en
   moyenne, avec un p99 a 226 : c'est une image neuve, pas une retouche. Le
   rapport au plancher du VAE est de 21 fois.

2. **Le masquage dans le latent est deja au plancher** quand la zone masquee est
   petite : 1,183 contre 1,281 pour le simple aller-retour VAE. Autrement dit
   il ne coute RIEN de plus que d'avoir encode l'image.

3. **Mais il fuit quand la zone masquee change beaucoup.** 4,29 sur une boite,
   12,93 sur une bande. Ce n'est pas un defaut du masquage : la lecture de
   `comfy/samplers.py` ligne 642 montre que la latente de sortie est
   exactement la latente d'origine hors masque. La derive vient du **decodeur
   du VAE, qui n'est pas local**.

   Le controle est dans le tableau : la ligne « BOITE + flou + DiffDiff »
   (non affichee ci-dessus, mesuree a `dehors` 1,42) a **exactement la meme
   geometrie de masque** que la ligne « BOITE » a 4,29, mais un changement
   interieur bien plus faible (dedans 11,67 contre 57,67). La derive suit
   l'AMPLEUR DU CHANGEMENT, pas la forme du masque. C'est la signature d'une
   non-localite du decodeur, pas d'une fuite de masque.

4. **Seul le recollage en pixels donne zero.** Et zero est vraiment zero :
   `dehors = 0,000`, `p99 = 0`, aucun pixel a plus de 0 niveau d'ecart. C'est
   pour cela que `ImageCompositeMasked` est dans le graphe retenu et pas en
   option.

---

## 5. La qualite du rendu a l'interieur du masque

Les chiffres ci-dessus ne disent pas si le resultat est bon, seulement si le
reste est intact. Ce que montre l'observation, appuyee par `dedans` :

| essai | ce qu'on voit |
|---|---|
| edition globale, « remplace le cerf par un rocher » | le rocher est ajoute DERRIERE le cerf ; le cerf reste. Tout le decor est refait |
| globale + recollage | le rocher disparait completement : il etait hors du masque. **Le recollage seul ne suffit pas** — un moteur global n'a aucune raison de poser son edition dans la zone |
| latent, masque = silhouette du cerf, klein + ReferenceLatent | une plaque de rocher collee sur le flanc du cerf. Le masque est respecte, l'edition est absurde |
| latent, masque = boite, klein + ReferenceLatent | vrai rocher, bien integre, mais le cerf est TOUJOURS la, devant |
| idem a 8 pas au lieu de 4 | le cerf est toujours la. Le nombre de pas n'est pas en cause |
| latent, masque = boite, klein **sans** ReferenceLatent, prompt descriptif | **le cerf a disparu, le rocher est net, l'eclairage suit la scene, la couture est invisible** |
| SDXL RealVis, masque = silhouette, denoise 0,75 | obeit tres bien a la description, mais le rocher a la forme d'un cerf : la silhouette contraint la geometrie |
| SDXL, silhouette dilatee de 40 | bon rocher, mais un fantome de bois subsiste dans la brume et un trou entre les pattes |
| **RETENU V2, changer le fond** | plage, mer, ciel bleu ; le cerf est preserve au pixel pres, ombre plausible, aucune couture |
| **RETENU V1, effacer le sujet** | le cerf est parti, remplace par brume et herbes ; un leger fantome subsiste |
| **V3, meme chose avec GrowMask = 0** | fantome tres marque, silhouette blanche du cerf : arete de crete 9,93 |

Deux enseignements de conception, pas de reglage :

- **Le masque doit etre plus large que l'objet.** Un rocher enferme dans une
  silhouette de cerf reste en forme de cerf. `GrowMask expand=24` corrige le
  fantome ; `expand=0` le laisse (crete 9,93 contre 0,89).
- **Le texte doit decrire, pas ordonner.** C'est la contrepartie du retrait de
  `ReferenceLatent`, et c'est un appel LLM separe : « ce que l'utilisateur veut
  voir dans la zone », a partir de sa demande et du masque choisi.

---

## 6. La couture au bord

### Comment la mesurer simplement

Une couture, c'est une arete qui tombe **exactement sur le contour du masque et
nulle part a cote**. Mesure retenue, robuste au fait que le contenu interieur a
change :

```
crete(image) = |gradient de Sobel| moyen sur le contour du masque (1 px)
             / |gradient de Sobel| moyen dans la bande 3-8 px de part et d'autre
exces        = crete(resultat) / crete(source)
```

Le rapport interne a l'image annule l'effet du changement de contenu ; le
rapport source/resultat annule l'effet d'une image globalement plus nette.
`exces` autour de 1 = pas de couture ajoutee. `exces` nettement au-dessus de 1
= couture. On lit aussi le **profil de l'ecart selon la distance signee au
bord**, qui montre directement la marche.

### Le compromis, mesure

Balayage du rayon de flou du masque de recollage, **a echantillonnage
strictement identique** : le masque dur de l'echantillonnage ne change pas, donc
ComfyUI met le sampler en cache et seul le recollage recalcule (23,8 s pour le
premier, 0,52 s pour chacun des suivants — la preuve que rien d'autre n'a bouge).

| `blur_radius` | dehors | exces de crete | largeur de la bande de transition |
|---|---|---|---|
| 0 (recollage dur) | 0,000 | **2,48** | 0 px |
| 5 | 0,000 | 1,00 | 4 px |
| **11** | 0,000 | **0,98** | 8 px |
| 21 | 0,000 | 1,04 | 16 px |
| 31 | 0,001 | 1,06 | 32 px |

Profil de l'ecart moyen selon la distance au bord (negatif = dedans) :

```
flou 0  : -32..-16 : 50,0 | -16..-8 : 39,8 | -8..-4 : 30,9 | -4..0 : 21,4 || 0..4 : 0,0  | 4..8 : 0,0
flou 11 : -32..-16 : 50,0 | -16..-8 : 38,6 | -8..-4 : 23,7 | -4..0 : 12,8 || 0..4 : 5,8  | 4..8 : 3,1 | 8..16 : 0,7
flou 31 : -32..-16 : 44,2 | -16..-8 : 27,6 | -8..-4 : 18,5 | -4..0 : 11,5 || 0..4 : 6,2  | 4..8 : 4,3 | 8..16 : 2,8 | 16..32 : 1,3
```

A flou 0 la marche est verticale : 21,4 d'un cote, 0,0 de l'autre. C'est la
couture. Des flou 5 elle disparait (exces 2,48 -> 1,00) sans que le champ
lointain bouge d'un millieme. **11 est le minimum mesure** (0,98) ; au-dela on
n'y gagne rien et on contamine une bande de plus en plus large de l'original.
D'ou la valeur du graphe retenu.

### Les autres coutures trouvees

| cas | exces | commentaire |
|---|---|---|
| bande ciel, recollage dur | **3,59** | le pire. Coupure horizontale au milieu des cimes |
| boite, recollage dur | 2,48 | visible |
| latent seul, sans recollage | 0,96 a 1,11 | **le masquage latent ne cree pas de couture** — il derive ailleurs a la place |
| RETENU V1 | 0,99 | rien |
| RETENU V2 | 0,31 | rien |
| V3 (grow=0) | 0,67 mais **crete brute 9,93** | l'exces est trompeur ici : le contour source etait deja tres marque. La crete brute, elle, revele le fantome |

Le dernier cas est la limite de la mesure : `exces` compare a la source, or ici
la source avait deja une arete forte au meme endroit (le cerf en contre-jour).
Il faut lire la crete brute en plus du rapport. Note pour qui reprendra ce
travail.

---

## 7. Les pieges rencontres

1. **`FeatherMask` ne fait pas ce que son nom dit.** Il degrade lineairement
   depuis les BORDS DE L'IMAGE (`left`, `top`, `right`, `bottom`), pas depuis
   le contour du masque (`comfy_extras/nodes_mask.py:303`). Ses alias de
   recherche (« soft edge mask », « blur mask edges ») entretiennent la
   confusion. Le seul flou de contour disponible est le detour
   `MaskToImage -> ImageBlur -> ImageToMask`.

2. **Le masque BiRefNet n'est jamais exactement nul.** Loin du sujet il vaut de
   l'ordre de 0,0015 — invisible quand on l'enregistre en PNG 8 bits (il
   s'arrondit a 0), bien present dans le graphe. Consequence mesuree, en gardant
   tout le reste identique (le sampler etait en cache, 37,5 s puis 0,51 s) :

   | recollage | ecart hors masque |
   |---|---|
   | sans `ThresholdMask` | **0,554** partout, p99 = 1 |
   | avec `ThresholdMask 0.5` | **0,000**, p99 = 0 |

   Un demi-niveau sur toute l'image, ce n'est pas grave en soi ; mais c'est la
   difference entre « on peut promettre que le reste est intact » et « presque ».

3. **`DifferentialDiffusion` annule l'edition sur un programme a 4 pas.**
   Il transforme le masque en calendrier de debruitage par pixel ; avec quatre
   pas seulement, il ne reste presque aucune etape ou le pixel est « ouvert ».
   Mesure : `dedans` tombe de 12,59 a 3,32 a masque egal, et l'image est
   visuellement inchangee. Utile avec 20-30 pas, inutile ici. Rejete.

4. **`RemoveBackground` rend le masque du SUJET, pas du fond.** Le nom et
   l'inversion de `g_detourage` laissent croire l'inverse. `JoinImageWithAlpha`
   inverse a son tour en interne : les deux inversions se compensent et le code
   existant est juste, mais on se trompe une fois avant de le comprendre.

5. **Un moteur global + recollage ne donne pas un inpainting.** C'etait la
   solution qui avait l'air la plus simple (garder `g_edition` tel quel et
   recoller). Mesure : preservation parfaite (0,555 puis 0,000 avec seuillage)
   et **edition nulle** — le rocher demande avait ete place hors du masque, le
   recollage l'a efface. La preservation seule ne prouve rien.

6. **Le cache de ComfyUI est un allie de mesure.** Deux graphes identiques en
   amont partagent le meme echantillonnage : le balayage de flou a coute
   23,8 s + 4 x 0,52 s, et surtout il garantit que la seule variable qui a bouge
   est celle qu'on voulait faire bouger. A exploiter pour tout balayage futur.

7. **La carte est partagee.** Au demarrage de l'essai le studio calculait un
   flux1-dev 1920x1080 : le harnais a attendu la fin de la file au lieu de
   passer devant. Cet enchainement a evince klein de la VRAM, ce qui explique le
   22,16 s du temoin (chargement compris). Toutes les comparaisons du §4 et du
   §6 ont ete faites en file vide et sans aucun travail du studio intercale
   (verifie sur `/history` : les entrees 16 a 41 sont toutes les miennes).

---

## 8. Temps de calcul, avec l'etat du cache

Image 1216x832. « chaud » = le moteur etait deja en VRAM du fait de l'essai
precedent. Ne pas comparer une ligne froide a une ligne chaude.

| route | s | etat |
|---|---|---|
| aller-retour VAE flux2 seul | 3,26 | VAE seul |
| masque BiRefNet seul | 2,04 | froid |
| edition globale (temoin) | 22,16 | **froid** (klein evince par flux1-dev) |
| latent masque, silhouette | 18,73 | chaud |
| latent masque, boite | 16,07 | chaud |
| bande ciel | 17,25 | chaud |
| klein, description **avec** ReferenceLatent | 16,60 | chaud |
| klein, description **sans** ReferenceLatent | **10,06** | chaud |
| klein, 8 pas (avec ReferenceLatent) | 29,22 | chaud |
| SDXL RealVis 28 pas | 24,44 puis 17,86 | froid puis chaud |
| **RETENU V1** (BiRefNet + inpaint + recollage) | 16,10 | chaud, BiRefNet a charger |
| **RETENU V2** | **14,07** | chaud |
| recollage seul (balayage de flou) | 0,52 | tout en cache |

Le graphe retenu coute donc **14 a 16 s** contre 20 s annonces pour l'edition
actuelle : retirer `ReferenceLatent` fait plus que compenser l'ajout de
BiRefNet et du recollage. Le gain vient de la longueur de sequence en
attention, que la latente de reference doublait.

---

## 9. Ce que je n'ai PAS tranche

- **La taille et la source exactes d'un checkpoint SAM3.** Je n'ai rien
  telecharge. Tant que ce chiffre n'est pas mesure, la ligne de `CATALOGUE`
  correspondante ne peut pas etre ecrite, et on ne sait pas si ca tient sur une
  carte de 11 Go a cote de klein.
- **Si SAM3 tourne effectivement sur cette carte** une fois telecharge, ni son
  temps, ni sa qualite sur des noms francais (« le panneau », « le lampadaire »).
  Le noeud accepte une `CONDITIONING` de `CLIPTextEncode` mais l'encodeur est
  celui embarque dans le checkpoint, pas `qwen_3_4b` : le comportement
  multilingue est inconnu.
- **La bonne valeur de `GrowMask` en general.** J'ai deux points (0 et 24) sur
  une seule image et un seul sujet. 24 est mieux que 0, ce n'est pas la preuve
  que 24 soit le bon reglage pour une voiture dans une rue.
- **La coherence d'eclairage.** Sur V2 (fond de plage), le cerf reste eclaire
  pour une brume de lever de soleil. Le recollage garantit la preservation, et
  la preservation garantit l'incoherence quand on change radicalement le decor.
  Il faudrait une passe basse-force sur l'image entiere apres coup — non testee,
  et elle reabimerait le chiffre de preservation.
- **Le fantome residuel sur V1.** Visible, pas mesure ; il faudrait une metrique
  de « forme residuelle » (correlation entre la carte d'ecart et le masque),
  que je n'ai pas ecrite.
- **Le comportement sur d'autres tailles et d'autres images.** Un seul cliche,
  une seule graine, une seule taille. Les ecarts hors masque sont structurels
  (VAE, recollage) et ne devraient pas bouger ; le jugement sur le rendu, si.
- **Pony et FLUX.1 dev comme moteurs de remplissage.** Non essayes. RealVis a
  ete essaye parce qu'il est le moteur photo du studio ; il obeit mieux que
  klein a une description mais reconstruit moins bien le contexte alentour.
- **Le decoupage des appels LLM.** Le graphe impose une conversion « demande ->
  description de la zone » et un choix « sujet / fond / boite ». J'ai suppose
  que ce sont deux taches distinctes de l'aiguillage, sans le verifier sur le
  corpus.

---

## 10. Protocole, pour rejouer

- Image d'essai : `input/essai_agent.png`, 1216x832 (multiple de 16, donc
  aucun redimensionnement ne s'intercale entre la source mesuree et
  l'echantillonneur).
- Graine unique : 424242. Consigne unique pour les comparaisons de route :
  « remplace le cerf par un gros rocher gris couvert de mousse ».
- Masque de reference exporte une fois (`MaskToImage` + `SaveImage`) et
  reutilise pour toutes les mesures, pour que le masque mesure soit celui
  employe.
- Mesures en numpy/scipy dans le python embarque de ComfyUI
  (`D:\ComfyUI_windows_portable\python_embeded\python.exe`, numpy 2.5.1,
  scipy 1.18.0), sur les PNG rapatries via `/view`.
- Le harnais attend systematiquement `/queue` vide avant d'envoyer, pour ne pas
  bousculer le studio.
