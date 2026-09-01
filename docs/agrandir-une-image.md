# Agrandir une image

Le studio savait produire une image, la modifier, l'animer, la sculpter — pas
l'agrandir. C'est pourtant la demande la plus banale une fois qu'une image
plaît, et l'index officiel des workflows ComfyUI en compte vingt-deux.

Il suffit de le dire : « agrandis-la », « en 2x », « passe-la en 4k ». La
demande est reconnue **à l'écrit**, sans passer par le modèle de langage — dix
secondes épargnées, et surtout aucun risque qu'il décide de *régénérer* l'image
au lieu de l'agrandir. Sans image jointe, la dernière sortie de la conversation
est reprise.

Deux niveaux de certitude, parce que la langue est ambiguë : « agrandis »,
« upscale », « haute résolution » ne veulent rien dire d'autre. « plus grande »,
« meilleure qualité » peuvent très bien décrire le *sujet* d'une image à créer
— « un chat devant une plus grande maison » — et ne comptent donc que sur une
phrase courte.

| | |
|---|---|
| Modèle | `4x-UltraSharp` (67 Mo), celui de son auteur |
| Mesuré | 1024×768 → 4096×3072 en 20 s ; 1216×832 → 2432×1664 en 26 s — **pc** (RTX 2080 Ti), 28 août 2026 |
| Facteurs | 2, 3 ou 4 — le modèle travaille en 4× et l'on réduit ensuite, ce qui rend mieux qu'un agrandissement direct |

Le contenu n'est pas retouché : c'est un agrandissement, pas une réinvention.
