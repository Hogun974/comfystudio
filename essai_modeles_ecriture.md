# Quel modèle de langage écrit le mieux pour le studio

Mesure du 31 août 2026, sur l'Ollama du PC (`http://172.20.1.21:11434`, version
0.33.2) et sur le fournisseur distant configuré dans le studio.

Corpus fixe de 24 demandes françaises, le même pour tous les candidats, rejouable :
`banc_ecriture/corpus_ecriture.jsonl`. Le banc (`banc_ecriture/banc.py`) importe
`serveur.py` et juge avec **ses** fonctions — `_enrichi()`, `latin()`, et le
contrôle de lignes de `traduire()`. Aucun critère n'a été réinventé.

Les appels reproduisent `enrichir()` (consigne `SYS_ENRICHIR + _A_DECIDER[quoi] +
_cadre_technique(plan)`, température 0,4, deux tentatives dont la seconde avec
`SYS_ENRICHIR_DUR`) et `traduire()` (consigne `SYS_TRADUCTION`, température 0,1,
format numéroté, deux tentatives).

Aucun rendu n'a été lancé, aucun ComfyUI interrogé, aucun fichier du dépôt modifié.

---

## 1. Le résultat en une table

| modèle | enrichir | traduire | latence réelle par appel | verdict |
|---|---:|---:|---:|---|
| `liquidai/lfm2.5-350m` | **42 %** | 54 % (29 % réels) | ~1,5 s | inutilisable |
| `digitsflow/bonsai-8b` | **96 %** | 100 % | ~4,9 s | conforme, écrit mal |
| `qwen2.5vl:7b` | **100 %** | 100 % | ~3,8 s | meilleur local |
| `gemma4:26b` | **0 %** | — | — | **ne se charge pas** |
| Anthropic (`claude-haiku-4-5`) | **100 %** | 100 % | ~2,3 s / 1,2 s | référence, sans carte |

« Latence réelle » = le régime dans lequel le studio tourne aujourd'hui
(`keep_alive: 0`), détaillé au § 4.

---

## 2. Taux de réussite, jugés par le code du studio

### Enrichir

| modèle | réussite | 1er essai seul | médiane/appel | p90 | max |
|---|---:|---:|---:|---:|---:|
| lfm2.5-350m | 10/24 (42 %) | 1/24 | 0,1 s | 0,1 s | 0,1 s |
| bonsai-8b | 23/24 (96 %) | 19/24 | 1,7 s | 2,9 s | 3,8 s |
| qwen2.5vl:7b | 24/24 (100 %) | 18/24 | 0,7 s | 1,3 s | 1,8 s |
| gemma4:26b | 0/5 (0 %) | 0/5 | — | — | — |
| Anthropic haiku-4.5 | 24/24 (100 %) | **24/24** | 2,3 s | 2,7 s | 3,0 s |

Le « 1er essai seul » compte les demandes réglées sans passer par
`SYS_ENRICHIR_DUR`. Anthropic est le seul à n'avoir jamais eu besoin de la
seconde tentative ; qwen et bonsai en dépendent pour un quart des demandes,
ce qui double leur coût réel sur ces cas-là.

### Traduire

| modèle | réussite | 1er essai seul | médiane/appel | p90 | max |
|---|---:|---:|---:|---:|---:|
| lfm2.5-350m | 13/24 (54 %) | 10/24 | 0,1 s | 0,2 s | 0,3 s |
| bonsai-8b | 24/24 (100 %) | 24/24 | 0,4 s | 1,0 s | 1,2 s |
| qwen2.5vl:7b | 24/24 (100 %) | 24/24 | 0,2 s | 0,6 s | 0,8 s |
| Anthropic haiku-4.5 | 24/24 (100 %) | 24/24 | 1,2 s | 1,5 s | 1,6 s |

Les 20/20 d'hier sur la traduction distante se confirment : 24/24, du premier coup.

### Par famille de demande (enrichir · traduire)

| modèle | animal | cadrage | objet | paysage | portrait | texte affiché |
|---|---|---|---|---|---|---|
| lfm2.5-350m | 3/5 · 4/5 | 0/3 · 3/3 | 0/4 · 2/4 | 2/4 · 1/4 | 3/4 · 2/4 | 2/4 · 1/4 |
| bonsai-8b | 5/5 · 5/5 | 3/3 · 3/3 | 3/4 · 4/4 | 4/4 · 4/4 | 4/4 · 4/4 | 4/4 · 4/4 |
| qwen2.5vl:7b | 5/5 · 5/5 | 3/3 · 3/3 | 4/4 · 4/4 | 4/4 · 4/4 | 4/4 · 4/4 | 4/4 · 4/4 |
| Anthropic | 5/5 · 5/5 | 3/3 · 3/3 | 4/4 · 4/4 | 4/4 · 4/4 | 4/4 · 4/4 | 4/4 · 4/4 |

lfm s'effondre exactement là où il y a du travail à faire : le cadrage (0/3) et
les objets (0/4), c'est-à-dire les demandes courtes qu'il faut vraiment étoffer.

---

## 3. `gemma4:26b` ne se charge plus du tout

Le plus gros candidat est hors course, et pas pour une question de vitesse :

```
HTTP 500 — llama_init_from_model: failed to initialize the context:
Gemma4Assistant requires ctx_other to be set
```

14,5 s pour échouer, à chaque appel, sans jamais produire un jeton. Le journal du
studio contient déjà la même erreur, avec la mise à l'écart par `MODELES_CASSES`.
J'ai arrêté le banc après 5 demandes identiquement échouées plutôt que
d'enchaîner 20 minutes de tentatives de chargement de 18,6 Go sur la carte du
propriétaire : la conclusion était acquise.

**Les 165 s de « bonjour » ne sont plus reproductibles** — non parce que le modèle
serait devenu rapide, mais parce qu'il ne s'initialise plus depuis la mise à jour
d'Ollama. C'est une régression de la mise à jour, pas un réglage.

### Conséquence directe, et c'est le vrai problème

`STUDIO_LLM_ECRITURE` est **vide** dans le conteneur en production. Donc
`choisir_modele_ecriture()` prend « le plus gros modèle installé » — soit
`gemma4:26b`, soit précisément celui qui est cassé. Le studio perd 14 s, le
marque cassé, puis retombe sur `MODELE_LLM` = `qwen2.5vl:7b`. `MODELES_CASSES`
étant une variable de module, **ce détour est repayé à chaque redémarrage**.

Autre piège du même choix automatique : `digitsflow/bonsai-8b` s'annonce à
**1,2 Go** dans `/api/tags` alors qu'il en occupe **9,5 Go** en VRAM. Le tri par
taille le classe donc bon dernier, derrière un modèle de 350 M. La sélection
automatique par la taille déclarée n'est pas fiable sur cet Ollama.

---

## 4. Le temps : c'est le réglage `keep_alive`, pas le modèle, qui coûte

Les médianes du § 2 sont mesurées **modèle déjà chaud**. Or `corps_ollama()` pose
`keep_alive: 0` par défaut (`garder=0`), et ni `enrichir()` ni `traduire()` ne
lèvent `garder`. **Chaque appel de production recharge donc le modèle.**

Quatre appels d'affilée, même demande, deux régimes :

| modèle | `keep_alive=0` (réglage actuel) | `keep_alive=10m` (gardé) | surcoût par appel |
|---|---|---|---:|
| lfm2.5-350m | 1,6 / 1,3 / 1,5 s | 1,3 / 0,1 / 0,1 / 0,0 s | ~1,4 s |
| bonsai-8b | 5,9 / 4,8 / 4,8 / 4,9 s | 4,9 / 0,2 / 0,2 / 0,2 s | ~4,6 s |
| qwen2.5vl:7b | 4,6 / 3,8 / 3,8 / 3,8 s | 3,9 / 0,4 / 0,4 / 0,4 s | ~3,4 s |

Une demande vers un moteur anglophone fait deux appels (enrichir + traduire), et
trois si `SYS_ENRICHIR_DUR` sert. En l'état, cela fait **8 à 15 s de rechargement
pur** avant chaque rendu avec qwen, **10 à 15 s** avec bonsai. Garder le modèle
10 minutes ramènerait ce coût à moins d'une seconde après le premier appel.

C'est le levier le plus rentable de tout ce rapport, et il ne dépend pas du
modèle retenu.

### Premier appel après déchargement

| modèle | « bonjour » à froid |
|---|---:|
| lfm2.5-350m | 2,0 s |
| qwen2.5vl:7b | 3,6 s |
| bonsai-8b | 4,1 – 6,5 s |
| gemma4:26b | 14,5 s (échec) |

Réserve honnête : « à froid » veut dire ici *déchargé de la VRAM*, le fichier
restant dans le cache disque de la machine. Un vrai premier chargement après
redémarrage du PC sera plus lent. Je n'ai pas pu vider le cache de la machine
d'en face, et je ne l'ai pas tenté : ce n'est pas la mienne.

### Un modèle qui part en réflexion sans fin

`digitsflow/bonsai-8b` (famille qwen3, donc à chaîne de pensée) a **bloqué 900 s
sur un seul appel** — la demande 15, seconde tentative avec `SYS_ENRICHIR_DUR` —
avant d'être coupé. 900 s, c'est exactement le `ClientTimeout` de
`_ollama_local()` : en production, ce cas fige l'analyse un quart d'heure, puis
rend une erreur. Une fois sur 48 appels, mais c'est le genre de panne qu'on ne
voit qu'en production. J'ai plafonné la suite du banc à 240 s et compté tout
dépassement comme un échec.

---

## 5. `latin()` : le nom est trompeur, il refuse **quatre** choses

Le nom ne décrit que la deuxième. Les quatre branches ont toutes tiré pendant la
mesure (250 appels jugés) :

| # | branche | ce qu'elle refuse vraiment | exemple mesuré |
|---|---|---|---|
| 1 | `sum(c.isalpha()) < 3` | moins de 3 lettres — une ligne qui n'a pas de mot | `---` (séparateur markdown), 5 fois |
| 2 | `_PLAGES_NON_LATINES` | cyrillique, hébreu, arabe, kana, han, hangul | qwen : `brou蛹e légère flottant au-dessus` |
| 3 | `(.)\1{3,}` | **quatre** occurrences du même caractère (1 + 3 répétitions) | lfm : `***…***anseanseanse***…` |
| 4 | `utiles >= 0.8 * len(t)` | majorité de symboles | `### Traduction`, `- **Explication :**`, 34 fois |

Deux remarques que la mesure impose :

- **La branche 4 est en pratique un détecteur de bavardage markdown**, pas de
  texte dégénéré. Sur 35 déclenchements, 34 sont des en-têtes `###` ou des puces
  `- **…**` : c'est-à-dire un modèle qui explique sa traduction au lieu de la
  rendre. Elle fait un travail utile, mais pas celui que son commentaire décrit.
- **Aucune des quatre ne vérifie que le texte est en anglais.** C'est le trou du
  § 6.

Attribution des refus : lfm2.5-350m en concentre 40 sur 42. qwen en a produit
**un seul** — un idéogramme inséré au milieu d'un mot français, au tout premier
appel, rattrapé par la seconde tentative. C'est très exactement le cas pour
lequel `latin()` a été écrite, et elle l'a attrapé.

---

## 6. La qualité, qui n'est pas la conformité

Ce paragraphe est un jugement, pas une mesure. Je l'assume comme tel et je le
sépare des chiffres. J'ai lu les 24 enrichissements de chaque candidat.

### Le trou du juge de traduction : le français qui passe

`latin()` accepte le français — c'est délibéré, pour ne pas recaler « a café ».
Mais rien en aval ne vérifie qu'une traduction a bien été traduite. Résultat :

| modèle | acceptées | dont **restées en français** | réellement utiles |
|---|---:|---:|---:|
| lfm2.5-350m | 13/24 | **6** | 7/24 (29 %) |
| bonsai-8b | 24/24 | 0 | 24/24 (100 %) |
| qwen2.5vl:7b | 24/24 | 0 | 24/24 (100 %) |
| Anthropic | 24/24 | 0 | 24/24 (100 %) |

lfm rend `un escalier en colimacon photographie en contre-plongee depuis le
rez-de-chaussee` comme « traduction anglaise ». Les contrôles la valident, elle
part vers FLUX.1, et on retombe pile sur le problème que `replier_sur_multilingue()`
documente : le mauvais sujet. **Le taux affiché de lfm est faux de moitié.**
(Détection par mots-outils français, heuristique à moi, pas un juge du studio.)

### Contamination par l'exemple du prompt

`SYS_ENRICHIR` contient l'exemple du renard — « clairière enneigée », « lumière
rasante et dorée », « souffle visible dans l'air froid », « sapins flous ». Les
petits modèles le recopient dans des scènes qui n'ont rien à voir :

| modèle | enrichissements où l'exemple déteint |
|---|---:|
| lfm2.5-350m | 3 |
| bonsai-8b | **4** |
| qwen2.5vl:7b | **0** |
| Anthropic | 1 |

bonsai met des « sapins flous à la base » dans un **salon** (demande 5, portrait
de vieille femme), et rend la mésange givrée avec « lumière rasante et dorée,
souffle visible dans l'air froid » — copié mot pour mot. Il neige aussi dans son
ciel de buse (« des vagues de neige dans le fond ») et sur son chemin de
blaireau. L'unique cas d'Anthropic est une clairière enneigée pour un chevreuil :
invention, mais cohérente.

### Le cadre technique recopié dans la description

`_cadre_technique()` dit au modèle la taille et le moteur *pour qu'il compose en
conséquence* — pas pour qu'il les récite. Ce qui part alors dans le prompt de
rendu :

| modèle | acceptés | dont recopient la taille ou le moteur |
|---|---:|---:|
| bonsai-8b | 23/24 | **6** |
| qwen2.5vl:7b | 24/24 | 2 |
| Anthropic | 24/24 | 0 |

bonsai : « …le hibou en relief avec la neige floue, **la composition horizontale
de 1216x832** ». qwen : « …fond neutre, **rendu en 3D au format .glb** ». Ces
chaînes partent telles quelles dans l'encodeur de texte du moteur d'image.

### L'échec que rien n'attrape

Demande 21, « une buse variable en vol, vue de dessous, ailes deployees ».
qwen2.5vl:7b rend :

> **Un avion** à ailes déployées en vol, vue de dessous, ailes en extension,
> moteur en marche, ciel clair et lumineux.

L'oiseau est devenu un avion. C'est plus long, il y a plus de cinq mots
nouveaux, c'est en alphabet latin : **`_enrichi()` et `latin()` la valident
toutes les deux**. Le rendu partira sur un avion. C'est la démonstration la plus
nette que la conformité ne dit rien de la valeur — et le seul défaut grave de
qwen sur ce corpus.

À la traduction, en revanche, qwen est le seul local à rendre correctement
« buse variable » → *variable buzzard* (bonsai : *variable hawk*, faux ; lfm :
*a variable buse en vol*, pas traduit).

### Ce que chacun vaut, en une phrase

- **lfm2.5-350m** — invente des mots qui n'existent pas (« silenprod »,
  « dorumpant », « une laiere jap lett »), recopie la demande sans rien ajouter,
  ou répond à côté. Sur la demande 24 il a rendu *« un renard roux au crépuscule,
  tremblant sur les os »* : l'exemple du prompt, avec le sujet perdu. À 350 M,
  la tâche n'est pas à sa portée. Rapide et sans valeur.
- **bonsai-8b** — passe les contrôles presque partout, mais écrit du remplissage
  peu fiable : rizières « recouvertes de laine de soie », « des coups de feu dans
  le ciel », machine à écrire **en bois**, théière en fonte devenue « verre et
  acier inoxydable » avec un « visage en verre », « un sanglier de chiens »,
  « l'ombre de l'ombre ». Il étoffe, mais il étoffe faux, et il récite le cadre
  technique. Bon traducteur, mauvais rédacteur.
- **qwen2.5vl:7b** — le plus propre des locaux et le plus rapide. Descriptions
  sobres, fidèles, sans contamination. Défauts : une substitution de sujet
  catastrophique sur 24 (l'avion), deux fuites techniques, un mot anglais
  (« perched ») et un idéogramme rattrapé au second essai. C'est un modèle de
  vision employé à écrire, et cela se voit à sa tendance à dériver sur les
  sujets qu'il connaît mal.
- **Anthropic haiku-4.5** — au-dessus, nettement. Fidèle au sujet dans les
  24 cas, riche sans remplissage, aucune fuite technique, du premier coup à
  chaque fois. « Vieille machine à écrire » devient « machine à écrire mécanique
  des années 1950, en acier noir et chromé terni, vue de trois quarts, touches
  ivoire jaunies, rouleau de papier visible, ressorts et leviers apparents ».
  C'est ce que `SYS_ENRICHIR` décrit et que les locaux approchent sans l'atteindre.

---

## 7. Recommandation

**Garder le nuage comme voie principale d'écriture — il l'est déjà
(`CHOIX['llm'] = 'anthropic'`) — et poser `STUDIO_LLM_ECRITURE=qwen2.5vl:7b`
comme repli local.**

Le raisonnement :

1. **Poser la variable est nécessaire quoi qu'il arrive.** Laissée vide, elle
   fait choisir `gemma4:26b`, qui ne se charge plus. Le studio le redécouvre à
   chaque redémarrage, au prix de 14 s et d'un journal alarmant.
2. **Parmi les locaux, qwen2.5vl:7b gagne sur tous les axes mesurés** : 100 %
   contre 96 % à l'enrichissement, 100 % partout à la traduction, deux fois
   moins de latence que bonsai, trois fois moins de fuites techniques, aucune
   contamination par l'exemple, et pas de risque de blocage à 900 s. Que ce soit
   déjà `MODELE_LLM` est un avantage supplémentaire : un seul modèle en mémoire
   au lieu de deux.
3. **Mais il ne remplace pas le nuage.** L'avion à la place de la buse n'est pas
   un détail de style : c'est le sujet perdu, et aucun contrôle du studio ne
   l'arrête. Sur 24 demandes, un rendu part faux sans que rien ne le signale.
   Anthropic n'a pas commis cette faute une seule fois.

Donc : nuage quand il est actif, qwen2.5vl:7b quand il est coupé, et le
propriétaire prévenu que le repli local se trompe parfois de sujet.

**`digitsflow/bonsai-8b` mérite d'être écarté explicitement**, malgré son 96 %.
Il est plus lent, il écrit faux, il récite les dimensions dans le prompt, et il
peut figer une analyse 15 minutes. Son seul domaine solide est la traduction, où
qwen fait aussi bien et plus vite.

### Deux réglages qui valent plus que le choix du modèle

- **`keep_alive`** : lever `garder` sur la suite enrichir → traduire ferait
  gagner 3 à 5 s **par appel** (§ 4). C'est le plus gros gain disponible, et il
  est indépendant du modèle.
- **Un contrôle « est-ce vraiment de l'anglais ? »** après `traduire()`. Trois
  mots-outils français dans la sortie suffiraient à rattraper les 6 traductions
  fantômes de lfm, et protégeraient n'importe quel futur petit modèle. `latin()`
  ne peut pas le faire : elle doit accepter « a café ».

### Un modèle absent qui vaudrait le téléchargement

Je n'ai rien téléchargé — c'est la machine de quelqu'un. Sous réserve, donc :

- **`gemma3:12b`** (~8 Go en Q4) est mon premier choix. La carte est une
  RTX 2080 Ti, 11 Go : un 12B en Q4 tient entièrement en VRAM, là où
  `mistral-small` (24B, ~14 Go) déborderait sur le processeur et perdrait
  l'avantage de vitesse. gemma3 est un modèle de texte natif — pas un modèle de
  vision détourné comme qwen2.5vl — et il est réputé solide en français, ce qui
  est exactement l'axe où le repli local pèche.
- **`qwen3:14b`** serait le second, avec une réserve nette : `bonsai-8b` est de
  la famille qwen3 et c'est lui qui a bloqué 900 s en réflexion. Le même risque
  s'appliquerait, à moins de couper explicitement le mode « thinking ».
- **`mistral-small`** : à écarter ici pour la VRAM, pas pour la qualité.

Le test décisif serait la demande 21 (« une buse variable en vol ») : si un
candidat garde l'oiseau, il remplace qwen comme repli local.

---

## 8. Ce dont je ne suis pas sûr

- **Le « froid » mesuré n'est pas le pire cas.** Déchargé de la VRAM, oui ; sorti
  du cache disque de la machine, non. Un premier rendu après démarrage du PC sera
  plus lent que mes chiffres, surtout pour les gros modèles.
- **24 demandes, ce n'est pas beaucoup** pour séparer 96 % de 100 %. L'écart
  bonsai/qwen à l'enrichissement tient à une seule demande et n'est pas
  significatif en soi ; ce qui départage ces deux-là, c'est la lecture du § 6,
  pas le taux.
- **Le blocage à 900 s de bonsai est arrivé une fois.** Je ne sais pas s'il est
  fréquent, ni s'il dépend de la demande ou du hasard d'échantillonnage. Je ne
  l'ai pas cherché à reproduire pour ne pas monopoliser la carte.
- **`gemma4:26b` n'a eu que 5 demandes** avant que j'arrête. L'erreur était
  strictement identique aux 5 fois plus au démarrage à froid, et le journal du
  studio la montrait déjà : je considère le point acquis, mais je n'ai pas fait
  tourner les 24.
- **La détection « resté en français » est mon heuristique**, à base de
  mots-outils. Elle est fiable sur des écarts francs comme ceux de lfm ; elle ne
  vaudrait rien pour arbitrer une traduction partielle.
- **Je n'ai pas mesuré le coût monétaire** de la voie Anthropic, ni son
  comportement quand le réseau est lent. Les latences distantes du § 2 ont été
  prises sur une connexion qui allait bien.
- **`gemma3:12b` est une recommandation par raisonnement, pas par mesure.**
  Je ne l'ai pas essayé.

---

## Rejouer la mesure

```
# corpus + scripts : banc_ecriture/ (nouveaux fichiers, non commités)
sudo -n docker run --rm \
  -v /tmp/banc_ecriture:/banc \
  -v comfystudio_comfystudio-donnees:/donnees \
  -w /app -e PYTHONPATH=/app \
  -e OLLAMA_URL=http://172.20.1.21:11434 -e STUDIO_DONNEES=/donnees \
  --entrypoint python comfystudio:latest /banc/banc.py [modèle…]

python3 analyse.py resultats.jsonl
```

`banc.py` accepte les noms de modèles en arguments (`anthropic` compris),
`BANC_TACHES=enrichir,traduire` pour restreindre, `BANC_PLAFOND` pour le délai
maximum par appel (240 s par défaut). Les mesures brutes de cette session sont
dans `/tmp/banc_ecriture/resultats.jsonl` sur 172.20.1.191.
