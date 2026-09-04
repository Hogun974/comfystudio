# Le journal des essais

Ces pages ne décrivent pas le studio d'aujourd'hui. **Ce sont des mesures prises
à une date, sur une machine nommée, et gardées telles quelles.**

Elles vivaient à la racine du dépôt, liées depuis nulle part. Ce n'était pas leur
contenu qui gênait — ce dépôt vit de mesures datées — mais leur **absence de
contexte** : un lecteur tombait dessus sans savoir s'il lisait l'état actuel ou
un relevé d'il y a une semaine. L'une d'elles conclut d'ailleurs « le chemin
d'installation ne fonctionne pas », ce qui était vrai le 30 août et faux depuis.

**On ne les corrige pas et on ne les met pas à jour.** Une mesure qu'on retouche
après coup n'est plus une mesure : c'est un souvenir. Chacune porte donc, en
tête de cette page, ce qui a changé depuis — et le corps du fichier reste ce
qu'il était.

Pour l'état actuel, c'est [la documentation](../README.md) qui fait foi, et
[Mesures](../mesures.md) qui porte les chiffres qu'on cite.

## Ce qui a changé depuis

| Essai | Date | Ce qui a bougé depuis |
|---|---|---|
| [Installation par un inconnu](installation.md) | 30 août 2026 | **Son verdict est périmé.** Il conclut « le produit fonctionne, le chemin d'installation non ». Le README a été refait depuis, et trois blocages réels ont été corrigés le 4 septembre : la commande d'enrôlement que le studio distribue échouait à tous les coups, un avertissement consultatif empêchait la mise en service, et le lanceur Windows exigeait un ComfyUI que l'installeur n'installe pas. `banc_noeud.py` les garde. |
| [L'exécutable Windows](exe_windows.md) | 30 août 2026 | Les chiffres tiennent (45 Mo, 28 s). Le script de construction ne code plus le chemin de Python en dur : il passe par `installation.py:python_du_studio()`. |
| [Retouche localisée](inpainting.md) | 30 août 2026 | Rien sur le fond. Voir [Retouche localisée](../retouche-localisee.md) pour l'état actuel. |
| [Où la retouche casse](retouche_limites.md) | 30 août 2026 | Rien sur le fond. Cite un lanceur (`LANCER ComfyUI (2080 Ti).bat`) qui n'est pas au dépôt : c'était un fichier local de l'auteur. |
| [Un masque depuis une description](masque_texte.md) | 30 août 2026 | Rien sur le fond. |
| [Retouche d'un morceau](audio_retouche.md) | 30 août 2026 | Rien sur le fond. |

## Ce qu'ils valent, et ce qu'ils ne valent pas

Ils valent leurs **mesures** : des durées, des tailles, des taux de réussite,
avec la carte et la date. C'est ce que [`CONTRIBUTING`](../../CONTRIBUTING.md)
demande, et c'est ce qui ne se refait pas — une mesure perdue est perdue.

Ils ne valent **rien comme documentation** : ils décrivent un état, pas une
règle, et plusieurs contiennent des verdicts que le code a démentis depuis. Ne
cite jamais un essai pour dire ce que le studio fait ; cite le code, ou la page
de documentation qui le décrit.
