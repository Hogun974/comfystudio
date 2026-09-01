# Architecture

```
demande en français
        │
        ▼
  qwen2.5vl (6 Go)            aiguillage, 5-12 s, sortie JSON
        │
        ▼
  normalisation par code      corrige les erreurs du petit modèle
        │
        ▼
  y a-t-il un sujet ?         demandes de 8 mots ou moins seulement, ~4 s
        │                     sinon → question posée, rien n'est généré
        ▼
  traduction si nécessaire    FLUX.1 et RealVisXL seulement, ~5 s
        │                     refusée → bascule sur klein, qui lit le français
        │
        ▼
  téléchargement si besoin    modèle manquant → récupéré depuis Hugging Face
        │
        ▼
  ComfyUI (port 8188)         génération
```

Les trois durées de ce schéma ont été relevées le **28 août 2026 sur pc**
(RTX 2080 Ti) ; elles ne valent pas pour une petite carte, et elles ne se
revérifient pas depuis le code. Toutes les durées du parc, avec leur date et
leur machine, sont dans [Mesures](mesures.md).

**Le modèle se choisit par appel, et non une fois pour toutes.** C'était un seul
modèle pour quatre rôles ; la mesure a tranché autrement.

| Rôle | Quel modèle |
|---|---|
| Aiguillage, extraction du sujet | `STUDIO_LLM` — le **rapide** suffit à produire du JSON structuré |
| Écriture : enrichissement, traduction, paroles, description d'une zone | le plus gros modèle **tenable** de la machine retenue, ou `STUDIO_LLM_ECRITURE` |
| Lecture d'image | le plus gros modèle **voyant** de la machine retenue |

Même demande, nuage coupé, sur **zima** (le NAS), le 31 août 2026 :
`qwen2.5vl:7b` aiguille juste et décrit
juste — 96 s d'aiguillage puis 166 s de lecture, 263 s en tout ; `gemma3:4b`
répond en 1 s et classe « décris cette image » comme une demande de **rendu**,
l'image n'ayant jamais été regardée. Il porte pourtant la capacité `vision` :
le problème n'est pas qu'il ne peut pas voir, c'est qu'il ne comprend pas qu'on
le lui demande. **Une capacité déclarée n'est pas une compétence.**

Donc ni l'un ni l'autre en permanence : dès qu'un corps porte une image, on
prend le meilleur modèle voyant de la machine où l'on atterrit ; le texte, lui,
garde le rapide. La chaîne locale complète passe ainsi de 119 s à 29 s (31 août
2026), et
`STUDIO_LLM` peut être un petit modèle de texte sans casser la lecture d'image.

**La machine aussi se choisit par appel** quand `OLLAMA_URL` en liste plusieurs :
voir [Plusieurs Ollama](plusieurs-ollama.md).

`digitsflow/bonsai-8b` a été écarté après mesure : il remplace le sujet français
de façon reproductible (*hibou* → *hippopotamus* aux trois tirages, *blaireau* →
*fox* aux trois). Aucun garde-fou ne rattrape une erreur de sens. qwen reste
fidèle au sujet ; ses défauts sont de forme (JSON tronqué, prompt vide, dérive
vers le chinois) et le code les couvre un par un.

**Chaque appel ne fait qu'une chose.** C'est la leçon principale : quand le même
appel devait aiguiller, enrichir, traduire et produire du JSON, la traduction
lâchait en premier. Isolée, elle est correcte. Idem pour la détection du sujet :
noyée dans le reste, « une image sympa » passait trois fois sur trois ; posée
seule, elle est vue.

**Le français n'est pas traduit sans raison.** L'encodeur de FLUX.2 klein est
Qwen3-VL, celui de Wan est umT5 : tous deux multilingues. Le prompt leur est
transmis en français. Seuls FLUX.1 dev et RealVisXL exigent l'anglais, et une
étape de traduction dédiée s'en charge. Pony et les planches reçoivent des
étiquettes danbooru, qui sont anglaises par nature.

Si cette traduction échoue — qwen bascule parfois en chinois en cours de réponse
— le studio **change de moteur** au lieu d'insister. Envoyer du français à FLUX.1
ne dégrade pas l'image, cela change le sujet : « un vieux hibou perché sur une
branche moussue » a produit un hybride d'opossum et d'écureuil. Mieux vaut perdre
le grain photographique de FLUX.1 que le sujet demandé.

Le modèle est déchargé immédiatement après usage (`keep_alive: 0`) pour libérer
la VRAM avant que la diffusion démarre. **C'est essentiel sur 11 Go** : si un LLM
reste résident, la génération s'effondre.

## Pourquoi une normalisation par code

Un modèle de 8 milliards de paramètres se trompe régulièrement. Plutôt que
d'espérer sa docilité, ces règles sont appliquées après coup, en Python :

| Erreur observée | Correction automatique |
|---|---|
| `intention: audio` mais `modele: klein4b` | l'intention fait foi, le modèle suit |
| `lecture` sans image jointe | bascule en génération |
| texte demandé dans l'image | klein 4B imposé (seul lisible) |
| 1920×1080 réclamé systématiquement | plafonné à ~1 Mpx, ratio préservé |
| « la même mais… » routé en génération | bascule en édition |

Chaque règle a ses cas de test dans un dossier de travail hors du dépôt.

## Si Ollama est arrêté

L'interface continue de fonctionner : un aiguillage par mots-clés prend le
relais. Le prompt n'est alors ni traduit ni enrichi, mais rien ne casse.

## Poser une question plutôt que deviner

Une demande qui ne dit pas quoi produire ne déclenche aucune génération : le
studio pose une à trois questions et attend. Ta réponse est jointe à la demande
initiale, et le studio ré-aiguille si elle change la nature du travail — répondre
« une courte vidéo » à une demande partie sur une image bascule vers Wan.

Deux garde-fous se cumulent, parce que le petit modèle seul ne suffisait pas :

1. l'aiguilleur peut répondre `intention: "question"` ;
2. pour les demandes de huit mots ou moins qu'il a décidé d'exécuter, un second
   appel isolé extrait le sujet. Le code exige ensuite que ce sujet **figure dans
   ta demande** — sans quoi le modèle en inventait un (« une image sympa » lui
   inspirait « un paysage d'hiver »).

Une reprise (« rends-la plus sombre ») échappe au filet : son sujet est dans
l'image précédente, pas dans la phrase. Sans cette exception, toute conversation
se serait arrêtée au deuxième tour.

Mesure du 28 août 2026, sur 27 tirages : **27/27** — 15/15 demandes claires
exécutées sans
question parasite, y compris très courtes (« un chat noir », « un coq »), et
12/12 demandes vagues correctement interrogées.

La température de l'aiguilleur est à 0,15 — la valeur se relit dans
`serveur.py`. À 0,4 la même demande partait tantôt
en question, tantôt en image. Contre-intuitivement, la valeur basse enrichit
**mieux** les prompts (13/15 contre 10/15, même série du 28 août 2026) : la part créative revient au modèle
de diffusion, pas à l'aiguilleur.
