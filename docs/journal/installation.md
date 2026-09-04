# Essai d'installation de ComfyStudio par un inconnu

**Date** : 30 août 2026
**Machine d'essai** : une machine Linux sans carte graphique (Ubuntu 24.04, 4 cœurs, 15,6 Go de RAM, 164 Go libres, **aucune carte NVIDIA**)
**Méthode** : clone git propre du dépôt dans `/tmp/essai-neuf`, lecture du README à partir de « Installer », puis exécution du chemin Docker.
**Bac à sable** : projet Compose `essaineuf`, port 8299, image `essaineuf-comfystudio:latest`. Le studio en service (port 8199, projet `comfystudio`, volume `comfystudio_comfystudio-donnees`) n'a pas été touché.

---

## Verdict

**Le produit fonctionne. Le chemin d'installation, non.**

Une fois le conteneur lancé, tout ce qui a été testé se comporte correctement : construction sans accroc, démarrage en 4 secondes, `healthcheck` vert, compte administrateur créé, connexion opérationnelle, routes d'agent protégées par jeton, messages d'erreur honnêtes quand il n'y a pas de carte. Le chapitre « Déplacer le studio sur une machine sans carte » est de loin le meilleur du README : il anticipe le piège du `chown 10001`, celui du `tar` incomplet, et explique pourquoi l'agent appelle le studio plutôt que l'inverse.

Mais un inconnu n'arrive jamais jusque-là. Il bute sur trois murs successifs :

1. **Il ne peut pas obtenir le code** — aucune URL de dépôt n'existe dans le README.
2. **Il ne sait pas ce qu'il lui faut** — aucun chapitre de prérequis.
3. **S'il franchit les deux premiers, il arrive sur un écran de connexion et n'a pas le mot de passe.** C'est là qu'il abandonne, et c'est le point le plus grave : le studio a l'air cassé alors qu'il fonctionne parfaitement.

Ces trois points se corrigent en une vingtaine de lignes de README. Le reste est du polissage.

---

## Chronométrage et volumes

Chiffres mesurés sur la machine d'essai (réseau local, image de base `python:3.12-slim` **déjà en cache**).

| Étape | Mesure |
|---|---|
| `docker compose build --no-cache` | **49 s** |
| Octets reçus pendant la construction | **64,6 Mo** (dont `av` 35,8 Mo, `aiohttp` 1,8 Mo, `huggingface_hub` 795 ko) |
| Premier démarrage (`up -d` → HTTP 200) | **4 s** |
| Taille de l'image construite | ~277 Mo sur disque |

**Pour un inconnu, ajouter le tirage de `python:3.12-slim`** (~45 Mo compressés, 119 Mo sur disque), absent de ma mesure car déjà présent. Total réaliste : **environ 110 Mo à télécharger, une à deux minutes** sur une connexion correcte.

À corriger dans le README (l. 1173-1175) : « L'image est donc minuscule, sans CUDA, et **se construit en quelques secondes** ». C'est 49 secondes hors tirage de l'image de base. Remplacer par « se construit en moins d'une minute, pour une centaine de mégaoctets à télécharger ».

---

## Gravité 1 — Empêchent d'installer

### B1. Aucune URL de dépôt. Le lecteur ne peut pas obtenir le code.

La seule occurrence d'un clone dans tout le README (l. 633) :

```bash
git clone <ce dépôt> comfystudio && cd comfystudio
```

`<ce dépôt>` n'est jamais remplacé, et aucune adresse (GitHub, Forgejo, autre) n'apparaît ailleurs dans le fichier. Vérifié :

```bash
grep -n -iE 'git clone|github\.com|forgejo|https://[a-z0-9./-]*comfystudio' README.md
# → une seule ligne, la 633, avec le placeholder
```

**Correction** : remplacer le placeholder par l'URL réelle, et ajouter cette commande en tête du chapitre « Installer » — c'est la toute première chose que fait un inconnu, et elle manque.

### B2. Aucun chapitre de prérequis.

Le README passe du texte de présentation à `./installer.sh` sans jamais dire ce qu'il faut avoir sur la machine. Rien sur Docker, Docker Compose, git. Le seul prérequis évoqué est Python, et uniquement en creux, dans le message d'erreur de `installer.sh`.

Le chapitre « En conteneur » suppose `docker compose` installé et l'utilisateur dans le groupe `docker` (aucune de ses commandes n'a de `sudo`) — deux hypothèses fausses sur une machine vierge, et fausses sur cette machine-ci.

**Correction** : un court chapitre « Avant de commencer » juste avant « Installer », listant : git ; Docker Engine + plugin Compose v2 pour le chemin conteneur ; Python ≥ 3.8 pour le chemin natif ; et la note que les commandes `docker` demandent `sudo` tant qu'on n'est pas dans le groupe `docker`.

### B3. Le chemin conteneur mène à un écran de connexion sans dire où est le mot de passe. **C'est ici qu'on abandonne.**

Le chapitre « En conteneur » (l. 1171-1185) tient en une commande :

```bash
docker compose up -d --build
```

« Puis <http://localhost:8199>. »

Suivi à la lettre, voici ce qui se passe réellement (reproduit) : la page se charge, et un formulaire « Se connecter » s'ouvre par-dessus la zone de saisie, qui est désactivée avec le texte « connecte-toi pour commencer… ». `STUDIO_AUTH` vaut `obligatoire` par défaut. L'utilisateur n'a ni nom ni mot de passe.

Le mot de passe existe, et il est **très bien présenté** — mais dans le journal du conteneur, dans un encadré explicite avec l'avertissement qu'il ne sera plus jamais affiché. Le problème est qu'aucune ligne du README ne dit d'aller l'y chercher :

```bash
grep -n -iE 'docker logs|journal du conteneur|STUDIO_ADMIN_MDP|env.exemple' README.md
# → l.634 (cp .env.exemple .env), l.909 (STUDIO_ADMIN_MDP)
#   « docker logs » : AUCUNE occurrence dans tout le README
```

Les deux seules mentions utiles sont dans le chapitre « Déplacer le studio », 540 lignes **au-dessus**, que rien ne lie à « En conteneur ». Le chapitre « Comptes » (l. 911) dit « affiché une seule fois dans **la console** » — mais en conteneur détaché il n'y a pas de console, et le fichier `.env.exemple` est un fichier caché qu'un `ls` ne montre pas.

Un inconnu se retrouve donc devant un studio qui a l'air cassé, sans piste. C'est le point d'abandon.

**Correction** — remplacer le bloc du chapitre « En conteneur » par :

```bash
cp .env.exemple .env       # y mettre au moins STUDIO_ADMIN_MDP
docker compose up -d --build
```

et ajouter dessous :

> Si vous n'avez pas renseigné `STUDIO_ADMIN_MDP`, le mot de passe du compte
> `admin` est tiré au sort et affiché une seule fois au démarrage. Pour le
> relire :
> ```bash
> docker logs comfystudio | grep -A3 'Compte administrateur'
> ```

### B4. « Démarrer » est exclusivement Windows, et cite un fichier qui n'existe pas.

Chapitre « Démarrer » (l. 190-196), immédiatement après « Installer » :

> 1. Lance ComfyUI (`LANCER ComfyUI (2080 Ti).bat`)
> 2. Lance `LANCER ComfyStudio.bat`

Deux problèmes :

- **`LANCER ComfyUI (2080 Ti).bat` n'existe pas dans le dépôt.** Seul `LANCER ComfyStudio.bat` est livré. Le nom porte le modèle de carte de la machine de l'auteur.
- **Il n'existe aucune instruction de démarrage pour macOS ou Linux hors conteneur.** Ni `python3 serveur.py`, ni `service/installer_service.sh` n'apparaissent dans le README :

```bash
grep -n -iE 'python3 serveur.py|systemd|installer_service' README.md
# → aucun résultat
```

Le dépôt livre pourtant `service/comfystudio.service`, `service/com.comfystudio.plist` et `service/installer_service.sh`, et `installer.sh` y fait explicitement référence dans ses commentaires (« l'unité systemd que pose `service/installer_service.sh` »).

Le README annonce « Un seul script, les deux systèmes » pour installer, puis n'explique le démarrage que sur un seul des deux. Un utilisateur Linux qui suit le chemin natif est bloqué net juste après l'installation.

**Correction** : supprimer la référence à `LANCER ComfyUI (2080 Ti).bat` (ou la remplacer par « ton lanceur ComfyUI habituel »), et ajouter le pendant macOS/Linux :
```bash
python3 serveur.py                     # au premier plan
./service/installer_service.sh         # en service, au démarrage de la machine
```

### B5. `docker-compose.yml` fige le nom du conteneur et le tag de l'image : impossible de cohabiter, et un `--build` écrase l'installation existante.

Le fichier porte en en-tête « Trois façons de s'en servir, **sans jamais modifier ce fichier** » et « Aucune raison d'éditer ce YAML ». Or il contient :

```yaml
container_name: comfystudio
image: comfystudio:latest
```

Ni `-p` ni `COMPOSE_PROJECT_NAME` ne les changent. Vérifié :

```bash
docker compose -p essaineuf config | grep -E 'image:|container_name:|published:'
#   container_name: comfystudio
#   image: comfystudio:latest
#   published: "8199"
```

Trois conséquences :

- **`docker compose up -d --build` dans un clone neuf retague `comfystudio:latest`**, c'est-à-dire l'image d'une installation déjà en service sur la même machine. L'ancienne devient `<none>` et le premier `docker image prune` l'efface. C'est précisément pour cela que cet essai a dû poser un `docker-compose.override.yml` au lieu de suivre le README littéralement.
- **Le conteneur ne peut pas être créé** si un `comfystudio` existe déjà : Docker refuse les noms en double.
- **Le port 8199 est repris en dur** par défaut, donc en conflit lui aussi.

Ce n'est pas un cas tordu : c'est exactement ce qui arrive à qui essaie une nouvelle version à côté de la sienne, ou à qui fait tourner une CI de construction sur la machine d'hébergement. Sur cette machine-ci, une chaîne d'intégration continue auto-hébergée tournait déjà et reconstruit et redéploie `comfystudio:latest` toutes les quelques minutes — un essai naïf serait entré en collision frontale avec elle.

**Correction** dans `docker-compose.yml` :
```yaml
# supprimer container_name (Compose nomme d'après le projet)
image: comfystudio:${TAG:-latest}
```
Et, à défaut, dire dans le README qu'on ne peut pas faire tourner deux installations sur la même machine sans éditer le YAML.

---

## Gravité 2 — Font perdre du temps

### T2. Le README envoie chercher deux variables qui n'existent nulle part.

l. 1224 :

> Pour retrouver le téléchargement automatique, monte les deux dossiers et renseigne `COMFY_MODELES` et `COMFY_ENTREE` — **les lignes sont déjà écrites, commentées, dans `docker-compose.yml`.**

Elles n'y sont pas :

```bash
grep -n 'COMFY_MODELES\|COMFY_ENTREE' docker-compose.yml .env.exemple
# → ABSENT des deux fichiers
```

`docker-compose.yml` propose une seule ligne commentée (`- /chemin/vers/ComfyUI:/comfy`) et dit explicitement l'inverse : « L'image pose `COMFY_DIR=/comfy`, monter le dossier entier suffit — `models/` et `input/` en découlent. »

Le lecteur cherche des lignes qui n'existent pas dans un fichier qu'on lui dit de ne pas éditer.

**Correction** : aligner le README sur le compose — « décommente la ligne de montage `- /chemin/vers/ComfyUI:/comfy` dans `docker-compose.yml` ; `COMFY_DIR` est déjà posé par l'image ». Garder `COMFY_MODELES`/`COMFY_ENTREE` uniquement dans le tableau des variables, pour les montages non standard.

### T2bis. `maj_noeud.sh` est livré dans l'image mais le studio ne le sert pas — 404.

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://IP:8199/api/noeud/maj_noeud.sh
# → 404, corps : {"erreur": "inconnu"}
# (noeud.sh, noeud.bat, modeles.sh répondent bien 200)
```

Cause : `SCRIPTS_NOEUD` dans `serveur.py` (l. 6620-6629) ne liste pas `maj_noeud.sh` / `maj_noeud.bat`, alors que le `Dockerfile` les copie explicitement dans l'image avec le commentaire « Le studio **SERT** ces fichiers aux machines qui viennent s'enrôler ».

Le README (l. 503) dit « Pour ne mettre à jour que l'agent, sans le reste : `maj_noeud.sh` ou `maj_noeud.bat` » et (l. 508) « **Aucun dépôt à cloner, aucun fichier à recopier** » — mais depuis un studio en conteneur, il n'existe aucun moyen de récupérer ces fichiers.

**Correction** dans `serveur.py`, ajouter à `SCRIPTS_NOEUD` :
```python
"maj_noeud.sh": "maj_noeud.sh", "maj_noeud.bat": "maj_noeud.bat",
```
et donner la commande `curl` dans le README, comme pour `noeud.sh`.

### T3. La bannière de démarrage affiche deux adresses inutilisables.

Avec `STUDIO_PORT=8299` dans `.env` (donc publié sur 8299), le journal annonce :

```
  Interface : http://127.0.0.1:8199
  RESEAU    : http://10.100.7.2:8199
```

`8199` est le port **interne** au conteneur, et `10.100.7.2` l'IP **interne** du conteneur. Les deux mènent nulle part depuis l'extérieur. L'utilisateur qui vient de choisir son port se voit proposer l'ancien.

**Correction** : en conteneur, ne pas afficher l'IP interne. Le plus simple est de lire une variable posée par le compose (`STUDIO_URL_PUBLIQUE`), ou à défaut d'écrire « port interne 8199 — voir le port publié par `docker compose ps` ».

### T4. Un paragraphe de sécurité périmé affirme le contraire du comportement réel.

l. 353-355, chapitre « Ouvrir au réseau local » :

> **Mesure ce que cela veut dire.** Il n'y a **aucune authentification** : quiconque atteint le port peut générer (contenu adulte compris), téléverser des images et occuper le GPU.

C'est faux depuis que la connexion est obligatoire par défaut. Vérifié sur l'installation d'essai :

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8299/api/modeles
# → 401
```

Le chapitre « Comptes » (l. 902) dit d'ailleurs l'inverse, correctement. Le paragraphe est un reste d'avant `STUDIO_AUTH`. Il est alarmant à tort et contredit le reste du document — exactement le genre de contradiction qui fait douter un lecteur de tout le README.

Le même chapitre explique par ailleurs comment ouvrir au réseau via `LANCER ComfyStudio.bat` (Windows uniquement), alors qu'en conteneur `STUDIO_HOTE` vaut déjà `0.0.0.0`.

**Correction** : réécrire le paragraphe en renvoyant à `STUDIO_AUTH` — « la connexion est obligatoire par défaut ; ne mets `STUDIO_AUTH=libre` qu'en sachant que quiconque atteint le port pourra tout faire, clés d'API comprises », et mentionner le cas conteneur.

### T5. Sur une machine sans carte, l'installeur décourage au lieu d'orienter.

```bash
python3 installer.py --materiel
```

```
  carte      aucune carte NVIDIA detectee (nvidia-smi absent ou pilote non installe)

Moteurs que cette machine peut faire tourner
--------------------------------------------
  aucun : il faut une carte NVIDIA d'au moins 6 Go.
```

Suivent 20 lignes `ecarte`. Le diagnostic est juste et bien présenté, mais il s'arrête sur « aucun » — alors que **c'est précisément la machine que le README recommande** au chapitre « Déplacer le studio sur une machine sans carte » (un NAS, un petit serveur allumé en permanence). Deux usages parfaitement valides ne sont pas évoqués : les machines à agent, et les clés d'API.

Quelqu'un qui installe sur son serveur — le cas nominal — lit « cette machine ne peut rien faire » et s'arrête.

**Correction** : quand aucune carte n'est détectée, remplacer la conclusion par
> Aucune carte ici — ce n'est pas bloquant. Le studio ne calcule rien lui-même. Deux options : poser un agent sur chaque machine à carte (voir « Déplacer le studio sur une machine sans carte »), ou piloter le studio avec une clé d'API (voir « Clés d'API »).

---

## Gravité 3 — Inélégant

- **I1.** `.env.exemple` est un fichier caché : invisible d'un `ls`, et le README ne dit jamais qu'il existe hors du chapitre « Déplacer le studio ».
- **I2.** Le `Dockerfile` réinstalle les dépendances en dur (`pip install "aiohttp>=3.9" "huggingface_hub>=0.24" "av>=12"`) au lieu d'utiliser `requirements.txt`, qui est dans le dépôt et contient exactement les trois mêmes. Deux listes à maintenir — la faute que le `Dockerfile` dénonce lui-même trois lignes plus bas à propos du `COPY *.py`. Aucune version n'étant figée, deux constructions à un mois d'écart n'installent pas la même chose (ici : `aiohttp` 3.14.3, `av` 18.1.0, `huggingface_hub` 1.29.0).
- **I3.** Les étapes affichées à l'utilisateur exposent des noms d'exceptions Python. Sans ComfyUI ni Ollama, une demande produit cinq lignes de ce genre :
  ```
  modele local injoignable (ClientConnectorError) — on cherche une machine qui en porte un
  Ollama indisponible (ClientConnectorError) — aiguillage par mots-cles
  enrichissement indisponible (ClientConnectorError) — demande gardee telle quelle
  ```
  `ClientConnectorError` ne veut rien dire pour l'utilisateur ; « injoignable » suffisait.
- **I4.** `/api/etat/{id}` renvoie `"etat": "erreur"` mais pas de champ `erreur` au niveau racine : le message n'existe que dans la dernière entrée de `etapes`. Un client qui lit `d.erreur` obtient `null`.
- **I5.** « En conteneur » conclut par « Puis <http://localhost:8199> », alors que le déploiement que le README recommande est un serveur distant, où `localhost` est faux.

---

## Ce qui s'est bien passé

Une ligne chacun, comme demandé.

- Construction de l'image : aucune erreur, aucun avertissement, 49 s.
- Démarrage : conteneur `healthy` en 4 s, `healthcheck` correctement calibré sur `/api/compte`.
- Compte `admin` créé automatiquement au premier démarrage ; **le mot de passe est affiché de façon très lisible**, dans un encadré dédié du journal, avec l'avertissement qu'il ne sera plus jamais montré et l'invitation à le changer. La présentation n'est pas en cause — seule sa découvrabilité l'est (voir B3).
- Le jeton d'administration est affiché au même endroit et conservé dans `conversations/_admin.json`, comme annoncé.
- Connexion : `POST /api/compte/entrer` → `{"ok": true, "nom": "admin", "admin": true}`, puis `/api/modeles` et `/admin` passent de 401 à 200.
- Les routes d'agent sont correctement protégées : `/api/noeud/travail` et `/api/noeud/annonce` renvoient 401 `{"erreur": "jeton inconnu"}` sans jeton, malgré leur exemption d'authentification de session.
- Le service de fichiers `/api/noeud/{quoi}` passe par une liste blanche : pas de traversée de chemin possible.
- `VRAM : inconnue — aucun ComfyUI joignable au demarrage` : exactement ce que le README annonce.
- Le bouton « démarrer ComfyUI » répond `403 {"erreur": "pilotage reserve a la machine hote"}` — message honnête, conforme au chapitre « Déplacer le studio ».
- Le chapitre « Déplacer le studio sur une machine sans carte » est excellent et mérite d'être remonté : le `chown -R 10001:10001`, l'avertissement sur le `tar` qui oublie `avis.jsonl` et `sorties`, et l'explication du sens d'appel de l'agent sont trois pièges réels, tous trois désamorcés.

### Et sans aucune machine à agent ?

Question du protocole. Une demande réelle est **acceptée** (`200`, avec un identifiant et une position en file), puis échoue proprement. Message final :

```
aucune machine ne repond — ComfyUI est-il demarre ?
```

C'est utile mais **mal orienté** dans ce contexte : sur une installation sans carte — le déploiement recommandé — il n'y a pas de ComfyUI local à démarrer, et la bonne action est d'aller déclarer une machine dans `/admin`. L'utilisateur est envoyé chercher un problème qui n'existe pas.

**Correction** : quand aucun nœud n'est déclaré (`/api/admin/noeuds` ne contient que `local` avec `agent: false`), remplacer par
> aucune machine de calcul déclarée — ajoute-en une dans /admin, ou démarre ComfyUI sur cette machine.

Les deux chapitres « Déplacer le studio » et « En conteneur » suffisent techniquement, mais **ils ne se citent jamais l'un l'autre** alors qu'ils décrivent la même installation. Celui qui lit « En conteneur » ne saura pas qu'il lui faut des agents ; celui qui lit « Déplacer le studio » a les bonnes commandes mais elles sont enfouies 540 lignes plus haut.

---

## Nettoyage

Tout ce qui a été créé pour cet essai a été supprimé et vérifié :

```bash
docker compose -p essaineuf down -v     # conteneur, volume, réseau
docker rmi essaineuf-comfystudio:latest # Deleted: sha256:0434dece…
rm -rf /tmp/essai-neuf
```

Contrôles finaux : aucun conteneur, aucun volume, aucune image portant `essai`.

**État du studio en service** : `comfystudio` — `Up (healthy)`, `0.0.0.0:8199->8199/tcp`, HTTP 200, volume `comfystudio_comfystudio-donnees` intact.

### Une remarque à ne pas mal lire

Pendant l'essai, l'identifiant de l'image `comfystudio:latest` a changé (`4060b1f3…` → `60016962…`) et le conteneur en service a été recréé. **Ce n'est pas le fait de cet essai** :

- le conteneur en service porte `com.docker.compose.project=comfystudio` et `working_dir=/home/<toi>/comfystudio` — pas le projet `essaineuf` ;
- la construction de cet essai a produit `sha256:0434dece…`, taguée uniquement `essaineuf-comfystudio:latest`, et supprimée depuis ;
- la chaîne d'intégration continue auto-hébergée a lancé une tâche de construction à 10:55:47, et l'image a été reconstruite à 10:56:07 — huit tâches se sont enchaînées en vingt minutes.

C'est la CI du dépôt qui redéploie le studio en continu. Cela illustre au passage **B5** : parce que `docker-compose.yml` fige `image: comfystudio:latest`, cette CI et n'importe quel essai sur la même machine se disputent le même tag. Un inconnu qui aurait suivi le README à la lettre aurait écrasé l'image du studio en service, sans le savoir et sans le moindre avertissement.
