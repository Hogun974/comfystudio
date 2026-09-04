# Retouche d'un morceau existant (audio2audio) — essai et mesures

> **Compte rendu daté du 30 août 2026, gardé tel quel.**
> Rien n'a bougé sur le fond.
> Voir [le journal des essais](README.md) pour ce qui a bougé depuis, et
> [la documentation](../README.md) pour l'état actuel.

Question posee : peut-on reprendre un morceau deja rendu et lui changer de style
en gardant sa structure, comme on fait de l'img2img sur une image ?

**Reponse : oui.** La piste `LoadAudio -> VAEEncodeAudio -> KSampler.latent_image`
avec `denoise < 1` fonctionne sur le ComfyUI installe (0.33.1) avec les modeles
ACE-Step 1.5 deja en place. 15 rendus soumis, 15 aboutis, aucun echec.

**Defaut recommande : `denoise = 0.5` avec `generate_audio_codes = False`.**
Justification chiffree plus bas.

---

## 1. Le graphe retenu

Il derive de `g_audio` (serveur.py). Deux differences seulement :

- le noeud 7 n'est plus `EmptyAceStep1.5LatentAudio` mais `LoadAudio` + `VAEEncodeAudio` ;
- `denoise` passe de 1.0 a 0.5, et `generate_audio_codes` de True a False.

Tout le reste — modeles, encodeur, `ModelSamplingAuraFlow` shift 3.0, sampler
euler/simple — est identique, volontairement : le but etait d'isoler l'effet de
la retouche, pas de re-regler le moteur.

```python
def g_audio_retouche(cle, source, tags, paroles, seed, prefixe,
                     langue="en", tonalite="C minor", par=None):
    """Retravaille un morceau existant au lieu d'en creer un.

    `source` est un fichier deja depose dans l'input de ComfyUI. La latente de
    depart vient de lui (noeuds 7 et 11) au lieu d'etre du bruit : c'est ce qui
    fait tenir la structure du morceau d'origine.
    """
    par = par or {}
    r = REGLAGES.get(cle, REGLAGES["audio"])
    etapes = int(par.get("etapes", r["etapes"]))
    cfg    = float(par.get("cfg", r["cfg"]))
    bpm    = int(par.get("bpm", r["bpm"]))
    # 0.5 mesure comme le meilleur compromis : voir le tableau du §3. En dessous
    # de 0.4 le morceau bouge a peine, a 0.7 il ne reste rien de l'original.
    denoise = float(par.get("denoise", 0.5))
    # La duree ne vient PAS d'ici : elle est imposee par la latente d'entree
    # (mesure du §5). On la recopie quand meme pour que le conditionnement soit
    # coherent avec ce que le modele entend.
    duree  = float(par.get("duree_s", r["duree_s"]))
    langue = langue if langue in LANGUES_ACE else "en"
    tonalite = tonalite if tonalite in TONALITES_ACE else "C minor"
    checkpoint = CATALOGUE[cle]["checkpoint"]
    return {
     "1":{"class_type":"UNETLoader","inputs":{"unet_name":checkpoint,"weight_dtype":"default"}},
     "2":{"class_type":"VAELoader","inputs":{"vae_name":"ace_1.5_vae.safetensors"}},
     "3":{"class_type":"DualCLIPLoader","inputs":{"clip_name1":"qwen_0.6b_ace15.safetensors",
          "clip_name2":"qwen_4b_ace15.safetensors","type":"ace","device":"default"}},
     "4":{"class_type":"TextEncodeAceStepAudio1.5","inputs":{"clip":["3",0],"tags":tags,
          "lyrics":paroles,"seed":seed,"bpm":bpm,"duration":float(duree),
          "timesignature":"4","language":langue,"keyscale":tonalite,
          # False, et pas le True de g_audio. L'infobulle du noeud
          # (comfy_extras/nodes_ace.py:47) dit « Turn this off if you are giving
          # the model an audio reference » — c'est exactement le cas ici. Mesure
          # a conditions egales : 106.33 s avec, 10.75 s sans, soit 10x, et la
          # structure est MIEUX gardee sans (0.913 contre 0.876). Voir §4.
          "generate_audio_codes":False,"cfg_scale":2.0,"temperature":0.85,
          "top_p":1.0,"top_k":0,"min_p":0.0}},
     "5":{"class_type":"ConditioningZeroOut","inputs":{"conditioning":["4",0]}},
     "6":{"class_type":"ModelSamplingAuraFlow","inputs":{"model":["1",0],"shift":3.0}},
     # Le couple 7+11 remplace EmptyAceStep1.5LatentAudio : c'est toute la
     # difference entre creer et retoucher.
     "7":{"class_type":"LoadAudio","inputs":{"audio":source}},
     "11":{"class_type":"VAEEncodeAudio","inputs":{"audio":["7",0],"vae":["2",0]}},
     "8":{"class_type":"KSampler","inputs":{"seed":seed,"steps":etapes,"cfg":cfg,
          "sampler_name":"euler","scheduler":"simple","denoise":denoise,
          "model":["6",0],"positive":["4",0],"negative":["5",0],
          "latent_image":["11",0]}},
     "9":{"class_type":"VAEDecodeAudio","inputs":{"samples":["8",0],"vae":["2",0]}},
     "10":{"class_type":"SaveAudioMP3","inputs":{"audio":["9",0],"filename_prefix":prefixe,"quality":"V0"}},
    }
```

---

## 2. Comment « ca ressemble encore » a ete mesure

Ecouter n'etant pas possible ici, deux chiffres objectifs, sur des trames de 100 ms :

- **correlation d'enveloppe** — correlation des RMS trame a trame entre l'original
  et la retouche. Elle suit le rythme et la structure (entrees, ruptures, refrains).
- **forme spectrale (cosinus)** — cosinus entre les spectres moyens en bandes de
  tiers d'octave. Elle suit le timbre, donc le changement d'instruments.

**Le chiffre le plus important du rapport est le plancher de bruit.** A `denoise = 1.0`
la latente d'entree est integralement remplacee : il ne reste rien de l'original,
par construction. Or ce cas mesure quand meme **0.447 et 0.527** de correlation
d'enveloppe (deux graines). Deux morceaux ACE sans aucun rapport, mais de memes
tags/bpm/duree, partagent donc deja une enveloppe generique a ~0.50.

Sans ce temoin on lirait « 0.548 » a denoise 0.7 comme « la moitie du morceau est
gardee », alors que cela veut dire « rien n'est garde ». Toute correlation proche
de 0.50 doit se lire comme un echec de la retouche.

---

## 3. Les mesures par denoise

Source : `output/studio/20260828_audio_00001.mp3`, 60.00 s, 48 kHz, 1 889 489 o,
recopiee en `input/retouche_source.mp3`. Graine 777, `generate_audio_codes=False`,
8 etapes, cfg 1.0 — donc seul `denoise` change d'une ligne a l'autre.

| denoise | duree obtenue | taille | calcul | correlation enveloppe | forme spectrale |
|---------|---------------|--------|--------|-----------------------|-----------------|
| 0.3 | 60.00 s | 1 783 138 o | 10.79 s | 0.943 | 0.998 |
| 0.4 | 60.00 s | 1 756 828 o | 9.76 s | 0.889 | 0.996 |
| **0.5** | **60.00 s** | **1 725 052 o** | **9.39 s** | **0.786** | **0.995** |
| 0.6 | 60.00 s | 1 739 836 o | 9.56 s | 0.655 | 0.991 |
| 0.7 | 60.00 s | 1 799 932 o | 9.57 s | 0.548 | 0.988 |
| 1.0 *(temoin)* | 60.00 s | 1 931 839 o | — | 0.527 | 0.919 |

Les trois valeurs demandees, sur la premiere serie (graine 424242, avec codes) :
0.3 -> 0.855, 0.5 -> 0.499, 0.7 -> 0.333. L'ordre est le meme sur les deux graines,
seul le niveau bouge — c'est pourquoi la recommandation s'appuie sur l'ecart au
plancher et non sur la valeur absolue.

**Ce que chaque valeur donne :**

- **0.3** — 0.943, tres au-dessus du plancher : le morceau est integralement
  reconnaissable. Mais la forme spectrale reste a 0.998, c'est-a-dire quasiment
  celle de l'original : on a retouche l'interpretation, pas le style. Utile pour
  un rafraichissement, insuffisant pour « change-moi les instruments ».
- **0.5** — 0.786, soit encore 0.29 au-dessus du plancher : la structure tient
  nettement. La forme spectrale a bouge (0.995 contre 0.998), toujours loin d'un
  morceau neuf (0.919). C'est le plus grand deplacement de style qui laisse la
  structure hors de portee du plancher.
- **0.7** — 0.548, soit 0.02 au-dessus du plancher de 0.527 : **l'original est
  perdu**. Le fichier est bon, la duree est bonne, mais ce n'est plus une retouche,
  c'est une generation neuve qui a coute un fichier d'entree pour rien.

**Donc 0.5 par defaut**, 0.3 quand l'utilisateur demande une retouche legere, et
0.6 comme plafond a ne pas depasser. Au-dela, autant appeler `g_audio`.

**La duree est exactement preservee dans les 15 rendus** : 60.00 s en entree,
60.00 s en sortie, sans exception. C'est la propriete attendue d'une retouche.

**Le denoise ne change pas le temps de calcul** : 9.39 s a 10.79 s, sans tendance
(0.5 est la plus rapide, 0.3 la plus lente). Avec 8 etapes turbo, l'echantillonnage
ne pese presque rien face au VAE et au chargement. Inutile de baisser le denoise
pour aller plus vite : ca ne marche pas, ca ne fait que moins retoucher.

---

## 4. generate_audio_codes : a mettre a False

Mesure appariee, modele deja resident, graine neuve des deux cotes pour forcer le
recalcul de l'encodeur, seul le drapeau change :

| generate_audio_codes | calcul | correlation enveloppe |
|----------------------|--------|-----------------------|
| True | 106.33 s | 0.876 |
| False | **10.75 s** | **0.913** |

La passe LLM des codes audio coute donc ~95 s sur 106, soit 90 % du temps, pour un
morceau de 60 s — et elle degrade la tenue de la structure. C'est logique : ces
codes decrivent un morceau a inventer, ce qui entre en concurrence avec la latente
de reference. `g_audio` a raison de les garder pour la creation ; la retouche doit
les couper.

---

## 5. Les pieges rencontres

**Le gabarit officiel ne vise pas cette version.**
`comfyui_workflow_templates_json/templates/audio_ace_step_1_m2m_editing.json` est
un graphe **ACE-Step v1** : `CheckpointLoaderSimple` sur `ace_step_v1_3.5b.safetensors`,
`TextEncodeAceStepAudio` (sans le « 1.5 »), `ModelSamplingSD3` shift 5.0. Les types
de noeuds existent bien dans ce ComfyUI (verifie via `/object_info`), mais ni ce
checkpoint ni cet encodeur ne sont installes. Seul le cablage se transpose :
`LoadAudio -> VAEEncodeAudio -> KSampler.latent_image`, et son `denoise` de 0.30.

**Le cache de noeuds de ComfyUI fausse toute comparaison de temps.**
Premiere serie : 111.86 s pour denoise 0.3 puis 9.89 s pour 0.7 — soit un rapport
de 11 qui n'a rien a voir avec le denoise. Le premier rendu avait 0 noeud en cache
(le travail Flux du studio avait chasse ACE de la carte), les suivants en avaient 8,
dont l'encodeur de texte. Toutes les mesures du §3 ont ete refaites a etat de cache
identique. **Un temps de rendu ne se compare qu'a nombre de noeuds caches egal**, et
`/history` le donne (`status.messages.execution_cached`).

**Le champ `duration` de l'encodeur ne pilote pas la longueur en retouche.**
Teste a 30 et a 120 sur une source de 60 s : les deux rendent **60.00 s**. C'est la
latente d'entree qui impose la longueur. Sans effet mesurable non plus sur le
resultat (correlation 0.791 / 0.784 contre 0.786 a duration correcte, soit du bruit).
Rassurant : une retouche ne peut pas changer la duree du morceau, meme si le plan
porte une `duree_s` incoherente.

**`entrees_du_graphe` ne verrait pas le fichier source.** *(a corriger avant de
brancher ceci dans le studio — non fait ici, aucun fichier du depot n'a ete modifie)*
`serveur.py` ne scanne que deux champs :

```python
for champ in ("image", "file"):
```

`LoadVideo` utilise bien `file` et les noeuds d'image `image`, mais **`LoadAudio`
utilise `audio`**. Consequence : un graphe de retouche confie a une machine a agent
partirait **sans son fichier source**, et echouerait a l'autre bout sur un fichier
introuvable. Il faut ajouter `"audio"` a ce tuple — ce qui suffit, puisque
`entrees_a_joindre`, `deplacer_entrees` et `pousser_entree` passent tous par la.

**Le fichier doit etre dans l'input avant la soumission.** L'entree `audio` de
`LoadAudio` est un COMBO valide contre le contenu du dossier input. Un nom absent
est refuse a la soumission — c'est une faute de demande (`value not in list`), donc
non reprise par `_est_panne` : correct, mais ca casse net.

---

## 6. Ce qui n'a pas ete tranche

La correlation d'enveloppe mesure la structure de facon fiable — le temoin a
denoise 1.0 la calibre. La **forme spectrale bouge peu** sur la plage utilisable
(0.998 a 0.991 pour 0.3 a 0.6, contre 0.919 pour un morceau neuf) : le changement
de style est reel et monotone, mais modeste. Dire si « acoustic folk » s'entend
vraiment demande une oreille humaine ; les mesures disent seulement que quelque
chose a change dans la bonne direction, et que la structure a tenu.

Essais menes sur une seule source de 60 s et deux graines. Une source plus longue
(150 s, il y en a dans l'output) et un ecart de style plus violent restent a verifier.

---

## Annexe — reproduire

Rendus dans `output/verif/` : `nc_dn*.mp3` (balayage retenu), `paire_*.mp3`
(codes True/False), `duree_*.mp3` (test de longueur), `chaud_*.mp3` et
`retouche_*.mp3` (premiere serie, avec codes).

Avant toute soumission, `GET /queue` doit avoir `queue_running` **et**
`queue_pending` vides : la carte est partagee avec le studio, et un rendu audio de
60 s prend 10 s a chaud mais 106 s si le modele a ete chasse entre-temps.
