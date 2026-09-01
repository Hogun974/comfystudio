# Mesures

Une durée ne se revérifie pas depuis le code. Elle dépend de la carte, du modèle
chargé, de ce que la machine faisait à côté — et elle vieillit sans que rien ne
le signale. **Chaque ligne porte donc sa date et sa machine.** Sans elles, un
chiffre périmé se cite, se propage, et personne ne peut dire laquelle de deux
valeurs contradictoires est la bonne.

Les chiffres qui se **revérifient**, eux, n'ont pas leur place ici : une borne,
un seuil, une valeur par défaut se relisent dans le code à l'endroit de la
décision — [Réglages](reglages.md) en donne la table — et le nombre de cas d'un
banc s'obtient en lançant le banc. Recopier ceux-là, c'est se donner une seconde
source qui dérivera.

## Les machines

| Nom | Ce que c'est |
|---|---|
| **pc** | RTX 2080 Ti, 11 Go de VRAM, 64 Go de RAM — la machine de référence, celle de l'auteur |
| **zima** | NAS ZimaOS, GTX 1060, 5,9 Go de VRAM — la petite carte |
| **le studio** | `172.20.1.191`, en conteneur, **sans carte** : il aiguille, met en file et répartit |

Une mesure prise sur **pc** ne dit rien de **zima**, et l'écart n'est pas un
facteur constant qu'on pourrait appliquer d'une ligne à l'autre : un détourage
passe de 2 s à 30 s, tandis qu'une lecture d'image passe de dix-neuf secondes à
plus de neuf cents — parce que là, le modèle de vision déborde de la carte, et
un débordement ne se prédit pas par une règle de trois. Voir [Plusieurs
machines](plusieurs-machines.md).

## Avant le rendu : l'analyse

| Étape | Mesure | Machine | Date |
|---|---|---|---|
| Aiguillage par le modèle de langage | 5 à 12 s | pc | 28 août 2026 |
| Vérification du sujet (demandes courtes seulement) | ~4 s | pc | 28 août 2026 |
| Traduction (FLUX.1, RealVisXL) | ~5 s | pc | 28 août 2026 |
| Question posée, sans génération | ~8 s | pc | 28 août 2026 |
| Aiguillage par le **classifieur**, sans modèle | 0,03 à 0,05 ms | pc | 1er septembre 2026 |
| Lecture d'image | **19 s** | pc | 31 août 2026 |
| Lecture d'image | toujours rien après **900 s** | zima | 31 août 2026 |
| Aiguillage de « décris cette image » par un modèle de langage | 96 à 222 s | zima | 31 août 2026 |
| Lecture d'image par `qwen2.5vl:7b` | 166 s (263 s avec l'aiguillage) | zima | 31 août 2026 |
| Chaîne locale complète, avant puis après la séparation texte / vision | 119 s puis 29 s | pc + zima | 31 août 2026 |

**La ligne « lecture d'image » a longtemps annoncé ~25 s.** C'était le relevé du
28 août ; celui du 31 août donne 19 s sur la même carte, et c'est lui qui fait
foi. Les deux figuraient dans la documentation, à deux pages d'écart, sans date
ni machine — c'est exactement ce que cette page existe pour empêcher.

## Le rendu

| Opération | Mesure | Machine | Date |
|---|---|---|---|
| Image 1344×704 | 50 à 95 s | pc | 28 août 2026 |
| Image 1920×1080, décodage par tuiles | 156 s | pc | 28 août 2026 |
| Image 1024×1024, klein 4B, 12 étapes (« rapide ») | 60 s | pc | 28 août 2026 |
| Image 1024×1024, klein 9B, 40 étapes (« soigné ») | 162 s | pc | 28 août 2026 |
| Édition d'image | ~20 s | pc | 28 août 2026 |
| Vidéo de 2 s (Wan 2.2 5B) | ~6 min | pc | 28 août 2026 |
| Animation d'image (Wan 2.2 14B) | ~12 min | pc | 28 août 2026 |
| Brouillon contre image finie, même graine | 14 s contre 217 s | pc | 31 août 2026 |
| Une image finie, avant que le brouillon existe | 249 s | pc | 31 août 2026 |
| Une demande complète depuis l'interface | 157 s, dont 149 s de rendu | zima | 30 août 2026 |

Le 1344×704 de la première ligne n'est plus une taille que le studio propose :
le défaut est **1216×832** depuis. La mesure reste lisible comme ordre de
grandeur, pas comme référence.

## Retouche, agrandissement, détourage, fluidité

| Opération | Mesure | Machine | Date |
|---|---|---|---|
| Retouche localisée, 1216×832, à chaud, 4 étapes, masque compris | 6,5 à 11,6 s | pc | 30 août 2026 |
| La même sur une étendue, 16 étapes | 11,4 s puis 23,0 s | pc | 30 août 2026 |
| Masque BiRefNet | 1,23 s | pc | 30 août 2026 |
| Masque SAM 3.1 | 1,2 s | pc | 30 août 2026 |
| Masque mesuré seul, cible introuvable | 1,0 s — au lieu de 13,1 s de rendu pour rien | pc | 30 août 2026 |
| Retrait de `ReferenceLatent` | 16,60 s puis 10,06 s | pc | 30 août 2026 |
| Agrandissement 1024×768 → 4096×3072 | 20 s | pc | 28 août 2026 |
| Agrandissement 1216×832 → 2432×1664 | 26 s | pc | 28 août 2026 |
| Détourage | 2 s | pc | 28 août 2026 |
| Détourage exécuté à distance, fichier de 1,4 Mo transmis | 30 s | zima | 29 août 2026 |
| Fluidification, 121 images à 24 im/s → 241 à 48 im/s | 60 s | pc | 29 août 2026 |

Le détail de ce que ces mesures ont décidé est dans [Ne changer qu'une partie de
l'image](retouche-localisee.md) — toutes celles de la retouche viennent des deux
essais du 30 août 2026, chacun sur une ou deux images et une seule graine.

## Les modèles de langage

| Ce qui est mesuré | Combien | Date |
|---|---|---|
| La même question, posée en direct à un Ollama | 3,8 s | 31 août 2026 |
| La même, par l'agent de **pc** | 74,8 s | 31 août 2026 |
| La même, par l'agent de **zima** | 162,6 s | 31 août 2026 |
| Une analyse empruntée à **zima**, un seul appel | 500 s | 31 août 2026 |
| `gemma4:26b` (18,6 Go) sur les 11 Go de **pc** | 165 s par traduction | 31 août 2026 |
| `gemma4:26b` sur **pc** : chargement, puis débit | 14 s, ~58 jetons/s | 28 août 2026 |
| `digitsflow/bonsai-8b` (1,2 Go), `qwen2.5vl:7b` (6 Go) sur 24 demandes réelles | 17/24 en 680 ms, 15/24 en 705 ms | 29 août 2026 |

**Emprunter le modèle d'une autre machine coûte de vingt à quarante fois le prix
d'un appel direct.** C'est ce qui a décidé de `OLLAMA_URL` en liste — voir
[Plusieurs Ollama](plusieurs-ollama.md).

## Le studio lui-même, qui ne calcule rien

| Ce qui est mesuré | Combien | Machine | Date |
|---|---|---|---|
| Construction de l'image Docker, base `python:3.12-slim` en cache | 49 s, 46 Mo téléchargés — ~110 Mo sans le cache | une machine sans carte | 30 août 2026 |
| `up -d` puis la première page servie | 4 s | idem | 30 août 2026 |
| Exécutable Windows, à froid | 45 Mo en 28 s | pc | 30 août 2026 |
| Le même avec `PAQUET_SANS_AV=1` | 17,6 Mo en 14 s | pc | 30 août 2026 |
| Démarrage de l'exécutable | 5 à 6 s | pc | 30 août 2026 |
| Entraînement de l'aiguilleur, 2 899 exemples, 11 classes | 0,03 s | pc | 1er septembre 2026 |
| Taillage du journal des appels distants, avant correction | 97 ms par appel sur 11 091 lignes | le studio | 1er septembre 2026 |
| Écriture du journal hors de la boucle, disque ralenti à 50 ms la ligne | 40 appels en 2,0 ms au lieu de 2 s | pc, au banc | 1er septembre 2026 |

## Ce que ces chiffres ne disent pas

**Ne génère pas dans ComfyUI pendant que le studio travaille** : les deux se
disputent la carte et tout ralentit énormément. Aucune mesure de cette page n'a
été prise dans ces conditions.

Et c'est le vôtre, pas le mien, que le studio vous annonce avant un rendu : il
relit vos propres tours terminés, machine par machine et moteur par moteur —
voir [Combien de temps ça va prendre](combien-de-temps.md).
