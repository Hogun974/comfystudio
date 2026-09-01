# Des machines qui viennent d'elles-memes

Il y a deux façons d'ajouter une machine.

**Par fichier** (`noeuds.json`) : le studio connaît son adresse et l'interroge.
Simple, mais il faut que la machine soit joignable — adresse fixe, port ouvert,
même réseau.

**Par agent** (recommandé) : un petit script tourne sur la machine, se présente
au studio avec un jeton, dit qu'il est en vie toutes les dix secondes, et vient
chercher le travail qu'on lui a attribué. **Le studio n'appelle jamais la
machine.** Elle peut donc être derrière une box, sur un portable qui s'endort,
sur un réseau qu'on ne maîtrise pas : tant qu'elle peut sortir, elle travaille.
C'est le modèle de Tdarr.

## Ajouter une machine

Dans <http://…:8199/admin> — le jeton d'administration est affiché dans la
console du studio à son premier démarrage, et conservé dans
`conversations/_admin.json`.

Crée la machine, note le jeton **affiché une seule fois**, puis sur la machine,
une seule commande :

```bash
# macOS et Linux
curl -fsS http://IP-DU-STUDIO:8199/api/noeud/noeud.sh -o noeud.sh
bash noeud.sh --studio http://IP-DU-STUDIO:8199 --jeton TON_JETON
```

```powershell
# Windows
curl.exe -fsS http://IP-DU-STUDIO:8199/api/noeud/noeud.bat -o noeud.bat
.\noeud.bat --studio http://IP-DU-STUDIO:8199 --jeton TON_JETON
```

`noeud.sh` et `noeud.bat` sont le seul fichier à poser sur une machine. Ils
vérifient Python, la carte, la mémoire, le disque, trouvent ComfyUI et
**proposent de le démarrer** s'il dort, testent le studio, téléchargent l'agent
et le lancent. Sans argument ils posent les questions ; le jeton est saisi en
aveugle, sans rester à l'écran.

```
Python
------
  ✓ Python 3.13.14

Materiel
--------
  ✓ carte : NVIDIA GeForce RTX 2080 Ti, 11264 MiB
  ✓ memoire : 64 Go

ComfyUI
-------
  ✓ deja en service sur http://127.0.0.1:8188
    modeles de diffusion vus : 6

Verdict
-------
  ✓ tout est pret
```

`--verifier` fait le diagnostic sans rien lancer, `--fond` laisse l'agent
tourner en tâche de fond. L'adresse et le jeton sont retenus : les lancements
suivants n'ont plus besoin d'arguments.

Pour ne mettre à jour que l'agent, sans le reste : `maj_noeud.sh` ou
`maj_noeud.bat`.

## Mettre à jour un parc

L'agent est servi par le studio (`/api/noeud/agent`). Mettre à jour revient donc
à relancer `maj_noeud` sur chaque machine, ou `python agent_noeud.py --maj`.
Aucun dépôt à cloner, aucun fichier à recopier.

Le script **vérifie que ce qu'il a reçu est du Python valide avant de
remplacer** : une page d'erreur du studio écraserait sinon un agent qui
fonctionnait. L'ancienne version reste à côté, en `.precedent`.

**Il faut le faire.** Un agent périmé ne ressemble pas à une panne : il répond,
il rend des images, et il lui manque en silence tout ce qui a été ajouté depuis.
Le 31 août, l'annulation d'un rendu n'atteignait pas une machine pour cette
seule raison — le studio demandait l'arrêt, la carte continuait, et le studio
écartait poliment le résultat tardif. Rien, nulle part, ne disait pourquoi.

Chaque agent annonce donc l'empreinte du code qu'il exécute, et `/admin`
affiche **« agent périmé — redémarre-le »** quand elle diffère de celle que le
studio distribue. Un agent antérieur à cette date n'annonce rien : la console
dit alors « version inconnue », ce qui est plus honnête que de conclure d'un
silence.

L'empreinte est celle du code **en cours d'exécution**, relevée au démarrage, et
non celle du fichier sur le disque : `--maj` remplace le fichier sous les pieds
d'un processus qui continue l'ancien code jusqu'à son redémarrage. Mettre à jour
sans relancer ne change donc rien, et la console continue — à juste titre — de
réclamer un redémarrage.

En conteneur, un `docker restart` suffit : l'agent va rechercher sa version au
studio à chaque démarrage.

**Et il n'y a en général rien à faire :** l'agent se met à jour tout seul. Le
studio lui donne à chaque battement l'empreinte de la version qu'il distribue ;
si elle diffère de celle qu'il exécute, l'agent la télécharge, la vérifie, se
remplace et redémarre — quelques secondes, sans intervention.

Quatre précautions, chacune pour un accident qu'on peut nommer :

- **Jamais au milieu d'un rendu.** Le remplacement n'a lieu qu'au battement, une
  fois le travail précédent rendu et avant d'en réclamer un autre.
- **Jamais sans avoir lu ce qu'on installe.** Un téléchargement tronqué ferait
  une brique : ce qui n'est pas du Python analysable est refusé, et l'ancienne
  version reste à côté en `.precedent`.
- **Jamais si une empreinte est épinglée.** `--empreinte` veut dire « n'exécute
  que celle-là » ; la mise à jour automatique se tait alors, et le dit.
- **Jamais deux fois pour la même.** Si après redémarrage l'empreinte ne
  correspond toujours pas, l'agent cesse d'essayer. Sans ce garde-fou, un studio
  qui sert un fichier légèrement différent — fins de ligne, encodage — ferait
  redémarrer la machine indéfiniment.

`--sans-maj-auto`, ou `AGENT_SANS_MAJ_AUTO=1`, désactive le tout.
`--empreinte SHA256`, ou `AGENT_EMPREINTE`, épingle une version.
`AGENT_LIVRAISON_MINUTES` borne l'insistance de l'agent lorsqu'il rend un travail
à un studio qui ne répond pas — dix minutes par défaut, largement de quoi
couvrir un redémarrage.

C'est du code téléchargé puis exécuté, et en HTTP simple si le studio n'est pas
derrière TLS : voir [`SECURITY.md`](../SECURITY.md). Épingler une empreinte, ou
couper la mise à jour automatique, est le choix à faire si ce réseau n'est pas
le vôtre.

## Ce qui circule

| Sens | Quoi |
|---|---|
| nœud → studio | « je suis là », carte, VRAM, modèles installés |
| nœud → studio | « du travail ? » toutes les 3 s |
| studio → nœud | le graphe à exécuter, en réponse à cette demande |
| nœud → studio | les fichiers produits, puis le résultat |

Le nœud n'ouvre aucun port. Les images qu'il produit sont **déposées chez le
studio**, qui les sert lui-même — l'agent n'a aucune raison d'être joignable.

## Pourquoi une demande toutes les 3 s plutôt qu'une poussée

Une connexion permanente (WebSocket) donnerait une latence nulle. Elle demande
en échange de gérer les reconnexions, les proxys et les coupures. Face à des
générations qui durent de 30 secondes à 6 minutes, 3 secondes d'attente ne se
voient pas — et une simple requête HTTP traverse tout sans configuration.

L'agent n'a **aucune dépendance** : la bibliothèque standard suffit. Une machine
qui fait tourner ComfyUI a forcément un Python.

## Un modèle de langage sur chaque machine

Le studio emprunte le modèle de langage d'une machine pour analyser une demande.
Depuis qu'une carte ne fait qu'une tâche à la fois, en avoir un **sur chaque
machine** change la donne : la petite carte réfléchit pendant que la grosse rend.
Sans cela, toutes les analyses passent par la seule machine qui en porte un, et
elle devient le goulot.

`noeud.sh` le vérifie et le dit, avec le modèle qui convient à la carte trouvée :

| Carte | Modèle conseillé |
|---|---|
| 20 Go et plus | `gemma3:27b` |
| 11 à 19 Go | `gemma3:12b` |
| 6 à 10 Go | `qwen3:8b` |
| moins de 6 Go | `qwen3:4b` |

**Ne prends pas plus gros que la carte** en comptant sur le débordement. Ollama y
arrive, mais l'analyse précède chaque rendu : mesuré sur une RTX 2080 Ti, un
modèle de 26 milliards a mis **165 secondes** à rendre son premier mot après
chargement. Un modèle qui écrit un peu mieux et coûte trois minutes de réveil
n'est pas le bon choix.

Sur ZimaOS, le service `ollama` est inclus dans `zimaos-comfyui.yml` — il ne
reste qu'à tirer le modèle une fois l'application installée :

```bash
docker exec -it ollama ollama pull qwen3:8b
```

## Mettre une machine en pause

Le bouton **pause**, dans `/admin`, retire une machine du service sans la
retirer du parc. « Je vais jouer un peu, mais le studio doit rester
utilisable » : elle continue de s'annoncer, garde son jeton, son inventaire et
sa mise à jour automatique, et ne reçoit simplement plus de travail. Les
demandes partent sur les autres.

Retirer la machine aurait le même effet immédiat, mais c'est un geste brutal :
il faut la redéclarer, avec un jeton neuf, et son agent perd sa configuration.

**Une demande qui réclame précisément cette carte ne se perd pas.** Deux temps :

- **pause récente** — la demande attend son retour devant l'écran, le dit dans
  son journal, et repart dès que la machine revient. L'annuler reste à un clic.
- **pause plus ancienne que le délai réglé** — le studio arrête de la faire
  attendre devant l'écran et la **garde armée** : elle sort de la file et
  repartira toute seule au réveil de la machine, pendant douze heures par
  défaut.

Les deux délais se règlent sous le tableau des machines — trente minutes et
douze heures, `STUDIO_PAUSE_PROPOSE` et `STUDIO_ARMEE_HEURES` pour les valeurs
de départ. Ce qui est « récent » dépend de l'usage qu'on fait de sa machine.

Le détail — les trois portes de réveil, ce qui survit à un redémarrage,
l'expiration, et le réglage à zéro qui rétablit le refus immédiat d'avant — est
dans [Attendre le retour d'une machine en pause](attendre-une-machine.md).

Une machine en pause **ne pense pas non plus** : si elle héberge un Ollama que
le studio connaît, il ne lui pose aucune question. Voir [Plusieurs
Ollama](plusieurs-ollama.md).

## Ce qu'un nœud ne peut pas faire

Installer ses propres modèles. Le studio n'écrit que sur son disque : une
machine à laquelle il manque un modèle est déclarée incapable de ce travail,
pas approvisionnée. Installe-les à la main, ou avec `installer.py` sur place.
