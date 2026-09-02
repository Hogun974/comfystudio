# ComfyStudio

> Interface en langage naturel pour ComfyUI — sous licence **AGPL-3.0**.
> Copyright © 2026 Hogun974.
>
> Vous pouvez l'utiliser, l'étudier, le modifier et le redistribuer. En
> revanche, toute version modifiée doit rester sous la même licence et rester
> accessible — **y compris si vous vous contentez de l'héberger en ligne**
> (article 13). Personne ne peut donc en faire un produit fermé.
> Texte complet : [LICENSE](LICENSE).

Interface en langage naturel pour ComfyUI. Tu écris ce que tu veux en français ;
un modèle local comprend l'intention, complète le prompt, pose une question si
la demande est trop vague, choisit le moteur adapté et règle ses paramètres.

**En un mot** : tu écris « un renard roux dans la neige au crépuscule » et le
studio choisit le moteur, écrit le prompt anglais s'il le faut, règle les
étapes, lance le calcul sur la machine la mieux placée, et te rend l'image.
Puis « agrandis-la », « détoure-la », « le même personnage sous la pluie ».

Il sait produire des **images**, les **retoucher**, les **agrandir**, les
**détourer**, des **vidéos** (et les fluidifier), de la **musique chantée**,
des **planches de BD** et des **objets 3D** — en local, sur plusieurs machines
à la fois, ou chez un fournisseur distant si l'on pose une clé d'API.

**Portable** : rien n'est installé sur la machine. Tout tient dans ce dossier et
s'appuie sur le Python embarqué de ComfyUI. Déplace `D:\ComfyStudio` à côté de
`ComfyUI_windows_portable` et ça fonctionne.

## Ce que tu peux demander

| Tu écris | Ce qui se passe |
|---|---|
| « un phare dans la tempête, très cinématographique » | image, FLUX.1 dev |
| « une guerrière manga, fiche personnage » | image, Pony |
| « une pancarte gravée "Bienvenue" » | image, klein 4B (imposé) |
| « la même mais en hiver » | édition de l'image précédente |
| « ajoute des aurores boréales » | édition en chaîne |
| « une petite vidéo d'un renard qui court » | vidéo, Wan 2.2 5B |
| « anime cette image » *(avec une image jointe)* | vidéo, Wan 2.2 14B |
| « une musique de piano mélancolique » | audio, ACE-Step |
| « rends-la plus acoustique » *(avec un morceau joint)* | retouche du morceau, sa durée est conservée |
| « décris cette image » *(avec une image jointe)* | lecture, sans passer par l'aiguillage |
| « une planche de manga en 4 cases : … » | planche BD, cases assemblées en un passage |
| « un modèle 3D d'un casque de chevalier » | image de référence puis Hunyuan3D, fichier .glb |
| « fais-moi un truc pour mon projet » | **rien n'est généré** : le studio pose des questions |

## Ce qui le distingue

**Le français est une entrée, pas une traduction à faire.** L'encodeur de
FLUX.2 klein est Qwen3-VL, celui de Wan est umT5 : tous deux multilingues, et le
prompt leur est transmis en français. Seuls FLUX.1 dev et RealVisXL exigent
l'anglais, et une étape de traduction dédiée s'en charge — si elle échoue, le
studio change de moteur plutôt que d'envoyer du français à un moteur qui n'en
veut pas et de changer le sujet en silence.

**Une demande vague ne produit rien.** Elle déclenche une à trois questions, et
le studio attend la réponse. Mesuré le 28 août 2026 sur 27 tirages : 15/15
demandes claires exécutées sans question parasite, 12/12 demandes vagues
correctement interrogées.

**Un brouillon avant de payer le rendu.** Un bouton à côté de la flèche d'envoi
lance la demande au quart des étapes — quatorze secondes au lieu de deux cent
dix-sept sur la même carte, mesuré le 31 août 2026 sur la RTX 2080 Ti — de quoi juger un prompt, un moteur, une ambiance.
Puis « refaire en soigné » reprend le même prompt, le même moteur et la même
graine avec tout le soin. **Le cadrage, lui, sera différent** : le nombre
d'étapes change la trajectoire du calcul, et la graine ne fixe que son point de
départ. C'est mesuré, et le studio le dit avant de lancer plutôt qu'après.

**Les machines viennent d'elles-mêmes.** Un petit script tourne sur chaque
machine à carte, se présente au studio avec un jeton, dit qu'il est en vie
toutes les dix secondes, et vient chercher le travail qu'on lui a attribué.
**Le studio n'appelle jamais la machine.** Elle peut donc être derrière une box,
sur un portable qui s'endort, sur un réseau qu'on ne maîtrise pas : tant qu'elle
peut sortir, elle travaille. Le studio mène plusieurs demandes de front, mais
une seule par carte — une carte ne se partage pas.

**Deux règles opposées pour la même demande.** L'analyse prend la plus grosse
carte libre : elle dure quelques secondes et tout l'attend. Le rendu prend la
plus petite qui tient le moteur, pour laisser la grosse au rendu suivant. Le
studio lui-même n'a aucune préférence — c'est un nœud comme les autres, et sans
carte il ne rend rien. Voir [Qui prend le
travail](docs/qui-prend-le-travail.md).

**Rien n'est exposé.** Le nœud n'ouvre aucun port et le studio n'écoute que sur
`127.0.0.1` par défaut. La connexion est obligatoire, y compris en local. Tout
fonctionne sans aucune clé d'API, et quand une clé est posée, une demande adulte
ne sort jamais de la machine — c'est vérifié en code, avant l'appel.

## Installer

Quatre chemins, selon la machine. Windows, Linux et macOS passent par
l'installeur, qui pose aussi ComfyUI, Ollama et les modèles ; Docker installe le
studio seul, qui pilote des cartes vivant ailleurs.

Récupérer le code, quel que soit le chemin choisi ensuite :

```bash
git clone https://github.com/Hogun974/comfystudio.git comfystudio
cd comfystudio
```

| Chemin | Ce qu'il faut |
|---|---|
| **Conteneur** — le studio seul, il pilote des cartes qui sont ailleurs | git, Docker Engine, et le plugin **Compose v2** |
| **Natif** — Windows, macOS, Linux, sur la machine à carte | git, Python **3.8 ou plus récent** |

### Windows

```bash
installer.bat
```

Sans argument, il regarde la machine — carte, RAM, disque — puis propose et tu
choisis : réutiliser un ComfyUI existant ou en installer un, et quels moteurs
télécharger parmi ceux que la carte tient. Il ne réinstalle jamais par-dessus
une installation existante. Rien à installer avant : il prend le Python embarqué
de `ComfyUI_windows_portable` s'il le trouve.

Ensuite, lance ComfyUI par son lanceur habituel, puis :

```
LANCER ComfyStudio.bat
```

L'interface s'ouvre sur <http://127.0.0.1:8199>. Le lanceur vérifie que ComfyUI
répond avant de démarrer et te le dit sinon.

**Ou bien un exécutable, sans rien installer du tout :**

```bash
paquet\construire_windows.bat
```

Il produit `paquet\dist\comfystudio.exe` — 45 Mo, en 28 secondes à froid
(mesuré le 30 août 2026 sur la RTX 2080 Ti). Il
faut PyInstaller (`pip install pyinstaller`) ; le reste voyage dans l'exe, pages
web et modèle d'aiguillage compris. **Pose-le dans son propre dossier**, pas
dans une copie du dépôt : il écrit à côté de lui — conversations, comptes, clés
— et il écraserait celles du dépôt.

Détails, options et catalogue : [Installation](docs/installation.md).

### Linux

```bash
./installer.sh
```

**Passe par ce script** plutôt que d'appeler Python directement : il cherche un
Python 3.8 ou plus récent et vérifie sa **version**, pas seulement sa présence.
Il pose ensuite les mêmes questions que sous Windows.

ComfyUI se lance à part. Puis :

```bash
python3 serveur.py          # au premier plan, Ctrl+C pour arrêter
```

Pour que le studio revienne tout seul au démarrage de la machine :

```bash
sudo sh service/installer_service.sh    # unité systemd
```

Le script pose l'unité, crée le dossier de données, et écrit les réglages dans
un fichier à part (`/etc/comfystudio.env`) : une mise à jour peut alors écraser
l'unité sans effacer la configuration de la machine. `--desinstaller` retire
tout.

### macOS

**Il n'y a pas d'installation macOS distincte.** `installer.sh` est le lanceur
des deux systèmes, macOS et Linux, et c'est bien lui qu'il faut appeler :

```bash
./installer.sh
python3 serveur.py
```

Trois choses sont réellement propres au Mac :

- **Le contrôle de version de Python existe pour lui.** Sous macOS, `python`
  désigne souvent le 2.7 du système, qui démarre parfaitement puis s'arrête sur
  la première f-string avec un `SyntaxError` qui ne dit rien de ce qui manque.
  Si tu appelles Python à la main, prends `python3`.
- **Le service est un agent launchd, posé sans `sudo`** :
  `sh service/installer_service.sh`. Il ne tourne **que quand ta session est
  ouverte** — c'est la contrepartie du « jamais root ». Survivre à la
  déconnexion demande un `LaunchDaemon`, qui tourne sous root tant qu'on ne lui
  ajoute pas de compte : le script ne le pose donc pas tout seul.
  [`service/NOTES.md`](service/NOTES.md) donne les deux marches à suivre pour un
  Mac serveur.
- **`noeud.sh` fonctionne aussi**, si le Mac doit être une machine à carte
  déclarée auprès d'un studio (voir [Des machines qui viennent
  d'elles-mêmes](docs/machines-a-agent.md)).

Et deux limites, plutôt que de laisser croire :

- **L'installeur ne cherche que des cartes NVIDIA**, par `nvidia-smi`. Sur un
  Mac il n'en voit aucune et prend donc la roue PyTorch `cpu` ; sans carte, le
  catalogue écarte tous les moteurs et n'en propose aucun. Rien dans le dépôt ne
  vise Metal ni Apple Silicon.
- **Ollama n'a pas de chemin macOS dans l'installeur.** Hors Windows, il propose
  le script officiel, qui est celui de Linux. Installe Ollama toi-même depuis
  <https://ollama.com/download> avant de lancer l'installeur.

La place naturelle d'un Mac est donc celle du studio, qui ne calcule rien : il
aiguille, met en file et répartit pendant que les cartes restent où elles sont.
C'est le montage décrit dans [Déplacer le studio sur une machine sans
carte](docs/studio-sans-carte.md).

### Docker

Le studio ne calcule rien : il pilote un ComfyUI et un Ollama qui vivent
ailleurs. L'image est donc minuscule, sans CUDA — 49 s de construction et 46 Mo
téléchargés avec `python:3.12-slim` déjà en cache, puis 4 s entre `up -d` et la
première page servie (mesuré le 30 août 2026 sur une machine sans carte).

```bash
cp .env.exemple .env       # y mettre au moins STUDIO_ADMIN_MDP
docker compose up -d --build
```

`.env.exemple` est un fichier caché : un `ls` ne le montre pas, `ls -a` si.
`docker compose version` doit répondre `v2` ou plus récent — c'est bien
`docker compose` en deux mots, `docker-compose` en un mot étant la v1, qui n'est
plus maintenue.

**Ces commandes n'ont pas de `sudo`** : elles supposent ton compte dans le
groupe `docker`. Le groupe n'est pas ajouté par l'installeur, et ce n'est pas un
oubli — appartenir au groupe `docker` équivaut à être root sur la machine. C'est
un choix qui revient à l'administrateur, pas à un script.

Puis <http://localhost:8199> — ou l'adresse de la machine, si le studio tourne
sur un serveur, ce qui est le cas recommandé.

Par défaut il cherche ComfyUI et Ollama **sur la machine hôte**
(`host.docker.internal`). Change `COMFY_URL` et `OLLAMA_URL` s'ils sont
ailleurs. `OLLAMA_URL` accepte **plusieurs adresses séparées par des virgules** :
le studio parle à chacune en direct et choisit laquelle il emploie, en évitant
les machines en pause — [Plusieurs Ollama](docs/plusieurs-ollama.md).

> **Si un studio tourne déjà sur cette machine**, ne lance rien avant d'avoir lu
> [Deux studios sur la même
> machine](docs/deux-studios-sur-la-meme-machine.md) : par défaut, le second
> écrit dans le volume du premier, et un `docker compose down -v` dans le second
> efface les conversations, les comptes et les clés du premier.

Volumes, ComfyUI conteneurisé et tableau complet des variables :
[En conteneur](docs/en-conteneur.md).

## Le premier démarrage demande un mot de passe

**La première page est un écran de connexion**, et c'est là qu'on croit le
studio cassé alors qu'il tourne. La connexion est obligatoire par défaut, y
compris en local. Le compte `admin` est créé au premier démarrage : sans lui, la
porte serait fermée sans clef.

Son mot de passe vient de `STUDIO_ADMIN_MDP` — dans `.env`, dans le fichier
d'environnement du service, ou dans l'environnement avant `python3 serveur.py`.
À défaut il est tiré au sort et affiché **une seule fois** au démarrage : dans
la console au premier plan, dans le journal sinon
(`docker compose logs comfystudio`, `journalctl -u comfystudio`).

Mieux vaut le poser d'avance. Un mot de passe tiré au sort et manqué au vol ne
se relit pas : il n'est pas conservé en clair, seule une empreinte scrypt l'est.

Où le lire selon le chemin de démarrage :
[Installation](docs/installation.md#démarrer).

## La documentation détaillée

Les explications détaillées vivront dans un **wiki**, qui n'est pas encore
monté ; le dossier [`docs/`](docs/README.md) en est la matière, une page par
sujet.

Quelques portes d'entrée :

- [Installation](docs/installation.md) — l'installeur en détail, ce qu'il
  télécharge selon la carte, et le premier démarrage.
- [Architecture](docs/architecture.md) — le chemin d'une demande, du français
  jusqu'à ComfyUI.
- [Des machines qui viennent d'elles-mêmes](docs/machines-a-agent.md) — ajouter
  une machine à carte en une commande, et tenir un parc à jour.
- [Qui prend le travail](docs/qui-prend-le-travail.md) — quelle carte reçoit
  quoi, et pourquoi l'analyse et le rendu ne veulent pas la même.
- [Ne changer qu'une partie de l'image](docs/retouche-localisee.md) — la
  retouche localisée, mesurée pixel par pixel.
- [Le brouillon, et « refaire en soigné »](docs/brouillon.md) — le rendu au
  quart des étapes, ce qu'il juge et ce qu'il ne prédit pas.
- [Clés d'API : LLM et images](docs/cles-api.md) — les fournisseurs distants, et
  le local comme repli de tout.
- [Ce que le nuage a coûté](docs/cout-du-nuage.md) — le compteur d'appels
  distants et le plafond mensuel. Aucun euro nulle part : les tarifs changent,
  ce logiciel ne les suit pas.
- [Réglages](docs/reglages.md) — toutes les variables d'environnement, ce
  qu'elles valent par défaut et ce qu'elles changent.
- [Plusieurs langues](docs/plusieurs-langues.md) — **le studio est en français,
  mais on peut lui écrire dans n'importe quelle langue** : quand il ne reconnaît
  pas les mots, il ne devine plus, il fait lire la demande au modèle de langage
  — et il le dit. Ce que cela a fermé (26 pannes silencieuses sur 345 devenues
  1), ce que cela coûte, et ce qu'on ne fera pas.

## Contribuer, signaler

[`CONTRIBUTING.md`](CONTRIBUTING.md) pour le style du dépôt et la façon de
proposer un changement. [`SECURITY.md`](SECURITY.md) pour ce qui touche à la
sécurité — en particulier le code d'agent téléchargé puis exécuté sur les
machines à carte.

## Licence

AGPL-3.0. Toute version modifiée doit rester sous la même licence et rester
accessible, y compris si vous vous contentez de l'héberger en ligne.
Texte complet : [LICENSE](LICENSE).

Copyright © 2026 Hogun974.
