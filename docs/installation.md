# Installation

## Avant de commencer

Récupérer le code, quel que soit le chemin choisi ensuite :

```bash
git clone https://github.com/Hogun974/comfystudio.git comfystudio
cd comfystudio
```

Ce qu'il faut sur la machine, selon le chemin :

| Chemin | Ce qu'il faut |
|---|---|
| **Conteneur** — le studio seul, il pilote des cartes qui sont ailleurs | git, Docker Engine, et le plugin **Compose v2** |
| **Natif** — Windows, macOS, Linux, sur la machine à carte | git, Python **3.8 ou plus récent** |

`docker compose version` doit répondre `v2` **ou plus récent** — `v5.…` va
très bien. C'est bien `docker compose` en
deux mots : `docker-compose` en un mot est la v1, qui n'est plus maintenue.
Toutes les commandes de ce README sont écrites pour la v2 et ses suites.

Python 3.8 est le plancher, et les scripts d'installation le vérifient au lieu
de se contenter de trouver un `python` (voir [Installer](#installer)). Sur
Windows, rien à installer : le studio s'appuie sur le Python embarqué de
ComfyUI.

**Les commandes `docker` de ce README n'ont pas de `sudo`** : elles supposent ton
compte dans le groupe `docker`. Si `docker ps` répond « permission denied », deux
possibilités :

```bash
sudo docker compose up -d          # préfixer chaque commande
sudo usermod -aG docker "$USER"    # ou entrer dans le groupe, une fois
```

Le groupe n'est pas ajouté par l'installeur, et ce n'est pas un oubli :
appartenir au groupe `docker` équivaut à être root sur la machine — la socket
suffit à monter n'importe quel dossier dans un conteneur privilégié. C'est un
choix qui revient à l'administrateur, pas à un script. Après un `usermod`, il
faut refermer et rouvrir la session pour que le groupe soit pris en compte.

## Installer

Trois chemins, au choix : **en conteneur** (chapitre plus bas, le plus court sur
une machine sans carte), **par le script d'installation** ci-dessous, ou **par
un exécutable Windows** que tu construis toi-même.

### Un exécutable Windows, sans rien installer

```bash
paquet\construire_windows.bat
```

Il produit `paquet\dist\comfystudio.exe` — **45 Mo**, en 28 secondes à froid.
Un `set PAQUET_SANS_AV=1` avant de lancer descend à 17,6 Mo en 14 s, au prix de
la lecture des vidéos jointes. Il faut PyInstaller (`pip install pyinstaller`) ;
le reste voyage dans l'exe, pages web et modèle d'aiguillage compris.

*Ces trois durées et ces deux tailles ont été relevées le 30 août 2026 sur* pc
*(RTX 2080 Ti, 64 Go de RAM) — voir [Mesures](mesures.md).*

L'exe démarre en 5 à 6 secondes, sans ComfyUI ni Ollama, et **écrit à côté de
lui** : conversations, comptes, clés. C'est délibéré et ça vaut d'être su —
PyInstaller déplie le code dans un dossier temporaire qu'il efface à l'arrêt, et
tout ce qui y serait écrit disparaîtrait à la fermeture. Deux lancements
donnaient deux comptes administrateur différents avant que ce ne soit corrigé.

Corollaire : **pose-le dans son propre dossier**, pas dans une copie du dépôt.
Il y écrirait ses données par-dessus.

### Un seul script, les deux systèmes :

```bash
installer.bat            # Windows
./installer.sh           # macOS et Linux
```

**Passe par ces deux scripts** plutôt que d'appeler Python directement : ils
cherchent un Python 3.8 ou plus récent, et vérifient sa **version**, pas
seulement sa présence. Sur macOS, `python` désigne souvent le 2.7 du système,
qui démarre parfaitement puis s'arrête sur la première f-string avec un
`SyntaxError` qui ne dit rien de ce qui manque.

Si tu appelles Python à la main, prends `python3`.

Sans argument, il **propose et tu choisis**. Il commence par regarder la
machine :

```
Materiel detecte
  carte      NVIDIA GeForce RTX 2080 Ti — 11.0 Go de VRAM
  memoire    63.8 Go de RAM
  disque     308.0 Go libres
```

Puis il déroule trois questions, chacune avec une réponse par défaut :

```
ComfyUI
  1) reutiliser  D:\ComfyUI_windows_portable\ComfyUI (defaut)
  2) indiquer un autre dossier
  3) installer une copie neuve
  4) ne rien faire pour l'instant

Moteurs a telecharger
   1) klein4b     8.0 Go  ~16 Go a prendre  FLUX.2 klein 4B <-- propose
   2) klein9b     6.0 Go  ~15 Go a prendre  FLUX.2 klein 9B
   ...
  Proposition : klein4b, flux1, pony, edition  (environ 37 Go)
  entree = la proposition,  tout = tous,  rien = aucun
```

Il ne réinstalle jamais par-dessus une installation existante : il la détecte,
la propose, et te laisse en désigner une autre si elle est ailleurs.

Les tailles sont relevées sur Hugging Face, pas estimées. Et elles comptent
**l'union** des fichiers : `klein4b` et `edition` partagent les leurs, la paire
pèse 16 Go et non 32.

**Une taille annoncée ne promet que ce qu'on sait.** Quatre formulations, et une
seule fonction les produit toutes — `annonce_poids()` dans `catalogue.py`, y
compris les deux **totaux** de cet écran :

| Ce qu'on lit | Ce que ça veut dire |
|---|---|
| `~16 Go a prendre` | la taille de chaque fichier est relevée, le total est celui-là |
| `au moins 12 Go a prendre` | un fichier au moins n'a pas de taille au catalogue ; c'est un plancher, annoncé comme tel |
| `taille inconnue` | tout ce qui manque est justement ce qu'on ne sait pas mesurer — « au moins 0 Go » n'annonce rien |
| `a installer a la main` | ce moteur n'a aucune source automatique, et ne marchera pas après installation |

Les deux dernières étaient fausses jusqu'au 1er septembre 2026. Les quatre
fichiers d'ACE-Step n'ont pas de dépôt, si bien que le moteur audio annonçait
`~0 Go a prendre` — sans même le « au moins » — pour un moteur qu'il faut
installer soi-même. Et sous le demi-gigaoctet, l'affichage passe désormais aux
**mégaoctets** : `detourer` pèse 0,44 Go relevé et `agrandir` 0,07, tous deux
affichés « ~0 Go », qui se lit « c'est gratuit ». Le garde-fou d'alors
interdisait une taille *relevée* à zéro ; il n'interdisait pas un *affichage* à
zéro.

Pour les habitués, ou pour une installation sans clavier :

```bash
python3 installer.py --materiel              # diagnostic seulement
python3 installer.py --comfyui --ollama      # les deux moteurs
python3 installer.py --modeles klein4b,pony  # ces modèles-là
python3 installer.py --tout                  # tout ce que la carte tient
python3 installer.py --oui                   # sans confirmation
```

`installer.py` ne contient que le contrôle de version, dans une syntaxe que
**même Python 2 sait lire** — sans quoi le message d'erreur n'aurait jamais pu
s'afficher, le fichier échouant à la lecture avant la première instruction. Le
programme lui-même est dans `installation.py`.

### Il s'adapte à la machine

Trois catégories, pas deux. Un modèle plus gros que la carte n'est pas
forcément hors de portée : ComfyUI déborde sur la mémoire système, le rendu
ralentit mais aboutit. Écarter sur la seule VRAM refuserait des moteurs qui
tournent très bien — mesuré sur une 2080 Ti de 11 Go qui fait tourner un modèle
vidéo de 14 milliards de paramètres.

Le catalogue compte aujourd'hui **vingt entrées** ; ce tableau se recalcule à
partir de `catalogue.py` et de `installation.moteurs_possibles()`, il n'est pas
relevé à la main. Refais-le si tu ajoutes un moteur, sinon il ment sans le dire.

| Carte | RAM | Tiennent | Débordent | Écartés |
|---|---|---|---|---|
| aucune | 16 Go | 0 | 3 | 17 |
| 6 Go | 16 Go | 4 | 4 | 12 |
| 6 Go | 32 Go | 4 | 10 | 6 |
| 8 Go | 32 Go | 8 | 10 | 2 |
| 11 Go | 64 Go | 18 | 0 | 2 |
| 24 Go | 64 Go | 19 | 1 | 0 |
| 32 Go | 64 Go | 20 | 0 | 0 |

Sur une carte de 6 Go, passer de 16 à 32 Go de RAM fait passer de 8 à 14 moteurs
utilisables. C'est souvent la mise à niveau la moins chère.

### Les grosses cartes ont leurs propres moteurs

Le catalogue plafonnait à 9,5 Go : bâti pour une 2080 Ti, tout en versions
quantifiées. Sur une carte de 32 Go il aurait affiché « tout est possible » sans
rien proposer de mieux, ce qui n'aurait servi à rien.

Deux variantes pleine précision s'ajoutent au-delà de 18 Go de VRAM :

| Moteur | VRAM | Ce qu'il apporte |
|---|---|---|
| `klein9bhd` | 18 Go | klein 9B en Q8 avec l'encodeur de texte complet — le suivi du prompt monte d'un cran |
| `flux1hd` | 26 Go | FLUX.1 dev sans quantification, encodeur T5 complet |

La proposition en tient compte toute seule : `klein4b, flux1, pony, edition`
(37 Go) sur une carte de 11 Go, `klein9bhd, flux1hd, pony, edition` (84 Go) sur
une carte de 32.

Ces variantes sont de **simples entrées de catalogue** : les constructeurs de
graphe lisent désormais les noms de fichiers depuis le catalogue, et choisissent
le chargeur d'après l'extension. Ajouter une variante ne demande plus de toucher
au code. Le refactor a été vérifié en comparant les graphes produits avant et
après : les cinq moteurs existants sont **identiques au bit près**.

Le script réserve 0,8 Go à Windows et au bureau : une carte de 8 Go n'en offre
jamais 8.

### Ce qu'il installe

- **ComfyUI** — clone du dépôt, environnement Python dédié, PyTorch CUDA (ou
  processeur s'il n'y a pas de carte). Il détecte une installation existante et
  ne réinstalle jamais par-dessus.
- **Ollama** — `winget` sous Windows, script officiel sous Linux, qu'il affiche
  avant de l'exécuter et jamais sans confirmation.
- **Les modèles** — depuis Hugging Face, filtrés par ce que la machine tient.
  Ceux qui n'ont pas de source automatique (dépôt sous licence) sont listés pour
  installation manuelle plutôt que passés sous silence.

Le catalogue est lu depuis `catalogue.py`, le même fichier que le serveur : la
liste des modèles ne peut pas diverger entre l'installeur et le studio.

## Démarrer

**Windows**

1. Lance ComfyUI par ton lanceur habituel — celui que ComfyUI portable pose à
   côté de lui, dont le nom porte souvent le modèle de la carte.
2. Lance `LANCER ComfyStudio.bat`
3. L'interface s'ouvre sur <http://127.0.0.1:8199>

Le lanceur vérifie que ComfyUI répond avant de démarrer et te le dit sinon.

**macOS et Linux**

```bash
python3 serveur.py          # au premier plan, Ctrl+C pour arrêter
```

ComfyUI se lance à part, comme sous Windows. S'il n'est pas encore là, le studio
démarre quand même et annonce « VRAM inconnue » : c'est exact, et c'est son
interface qui sert ensuite à le démarrer (voir [Piloter ComfyUI depuis
l'interface](piloter-comfyui.md)).

Pour que le studio revienne tout seul au démarrage de la machine :

```bash
sudo sh service/installer_service.sh    # Linux — unité systemd
sh service/installer_service.sh         # macOS — agent launchd, SANS sudo
```

Le script pose l'unité, crée le dossier de données, et écrit les réglages dans
un fichier à part (`/etc/comfystudio.env` sous Linux) : une mise à jour peut
alors écraser l'unité sans effacer la configuration de la machine. Il
**n'écrase jamais** ce fichier d'environnement — c'est lui qui porte
`STUDIO_ADMIN_MDP`. `--desinstaller` retire tout.

Sous macOS, l'agent launchd ne tourne **que quand ta session est ouverte** :
c'est la contrepartie du « jamais root ». Survivre à la déconnexion demande un
`LaunchDaemon` dans `/Library/LaunchDaemons/`, qui tourne sous root tant qu'on
ne lui ajoute pas de compte — le script ne le pose donc pas tout seul.
`service/NOTES.md` donne les deux marches à suivre pour un Mac serveur.

**La première page est un écran de connexion.** La connexion est obligatoire par
défaut, y compris en local, et le mot de passe du compte `admin` est affiché
**une seule fois** au démarrage. Où le lire, selon le chemin :

| Démarrage | Où lire le mot de passe |
|---|---|
| au premier plan | dans le terminal, encadré, juste après la bannière |
| service systemd | `journalctl -u comfystudio \| grep -A3 'Compte administrateur'` |
| agent launchd | `grep -A3 'Compte administrateur' ~/Library/Logs/ComfyStudio/studio.log` |
| conteneur | voir [En conteneur](en-conteneur.md) |

Mieux vaut le poser d'avance : `STUDIO_ADMIN_MDP` dans le fichier
d'environnement du service, ou dans l'environnement avant `python3 serveur.py`.
Un mot de passe tiré au sort et manqué au vol ne se relit pas — il n'est pas
conservé en clair, seule une empreinte scrypt l'est.

**Une fois connecté, va voir `/demarrage`.** Le studio en donne l'adresse dans
sa bannière (`A FAIRE : http://…/demarrage`) tant que l'écran n'a pas été
refermé. C'est une liste de contrôle qui **mesure** ce qui manque encore — le
mot de passe d'origine, une carte qui répond, les fichiers des moteurs, la
langue de l'interface — et qui distingue ce qui bloque de ce qui n'y ressemble
que : [La première mise en route](premiere-mise-en-route.md).
