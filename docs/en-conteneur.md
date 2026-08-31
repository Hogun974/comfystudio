# En conteneur

Le studio ne calcule rien : il pilote un ComfyUI et un Ollama qui vivent
ailleurs. L'image est donc minuscule, sans CUDA. Mesuré sur une machine sans
carte : **49 s** de construction et **46 Mo** téléchargés avec l'image de base
`python:3.12-slim` déjà en cache, environ **110 Mo** sans — puis **4 s** entre
`up -d` et la première page servie.

C'est le montage décrit dans [Déplacer le studio sur une machine sans
carte](studio-sans-carte.md) : sans carte ici, il
faudra des machines à agent pour que quoi que ce soit se génère.

Le dépôt est cloné et l'on est dans son dossier (voir [Avant de
commencer](installation.md#avant-de-commencer)) :

```bash
cp .env.exemple .env       # y mettre au moins STUDIO_ADMIN_MDP
docker compose up -d --build
```

`.env.exemple` est un fichier caché : un `ls` ne le montre pas, `ls -a` si.

**Si un studio tourne déjà sur cette machine**, ne lance rien avant d'avoir lu
[Deux studios sur la même machine](deux-studios-sur-la-meme-machine.md) : par
défaut, le second écrit dans le volume du premier.

Puis <http://localhost:8199> — ou l'adresse de la machine, si le studio tourne
sur un serveur, ce qui est le cas recommandé.

**Une connexion est demandée immédiatement**, et c'est là qu'on croit le studio
cassé alors qu'il tourne. Le compte `admin` est créé au premier démarrage. Si tu
as renseigné `STUDIO_ADMIN_MDP` dans `.env`, c'est ce mot de passe-là. Sinon il
est tiré au sort et affiché **une seule fois** dans le journal du conteneur :

```bash
docker compose logs comfystudio | grep -A3 'Compte administrateur'
```

Le tirage au sort est le bon défaut — un mot de passe par défaut identique pour
tout le monde serait pire — mais il n'est conservé nulle part en clair. Manqué,
il ne se relit plus : le renseigner d'avance dans `.env` évite la question.

Par défaut il cherche ComfyUI et Ollama **sur la machine hôte**
(`host.docker.internal`). Change `COMFY_URL` et `OLLAMA_URL` s'ils sont
ailleurs.

## ComfyUI aussi, si tu veux

`Dockerfile.comfyui` construit un ComfyUI conteneurisé. Le service est écrit,
commenté, dans `docker-compose.yml` : décommente-le et le moteur monte avec le
studio.

L'image part de `python:3.12-slim`, pas d'une base CUDA complète : le pilote et
les bibliothèques CUDA viennent de l'hôte par le **nvidia-container-toolkit**.
Les embarquer ferait plusieurs gigaoctets pour rien.

```bash
sudo apt install nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

Sans ce paquet, le conteneur **ne voit pas la carte** — il démarre et répond,
mais génère sur le processeur, à une vitesse inutilisable en pratique. Construis
alors avec `ROUE=cpu` pour ne pas télécharger un PyTorch CUDA de 3 Go qui ne
servira à rien.

Deux détails qui font échouer sans rien dire :

- **`--listen 0.0.0.0`** est indispensable dans un conteneur. Sans lui ComfyUI
  n'écoute que la boucle locale *du conteneur*, et le port publié ne mène nulle
  part. C'est dans la commande par défaut de l'image.
- Les modèles vivent dans un **volume**, jamais dans l'image : des dizaines de
  gigaoctets rebâtis à chaque modification du Dockerfile.

## Ce que le conteneur ne peut pas faire sans volumes

Sans montage des dossiers de ComfyUI, le studio le traite comme une **machine
distante** : tout passe par HTTP et fonctionne — sauf le téléchargement
automatique des modèles, qui exige d'écrire sur le disque de ComfyUI. Les
modèles doivent alors être installés à la main, et le studio dira simplement
qu'ils manquent.

Pour retrouver le téléchargement automatique, monte le dossier de ComfyUI :
décommente la ligne `- /chemin/vers/ComfyUI:/comfy` dans `docker-compose.yml` et
mets-y ton chemin. Rien d'autre à renseigner — l'image pose déjà
`COMFY_DIR=/comfy`, et `models/` comme `input/` en découlent.

C'est la seule exception au « rien à modifier dans ce YAML » : Compose ne sait
pas ajouter un montage depuis `.env`. `COMFY_MODELES` et `COMFY_ENTREE` restent
disponibles (voir le tableau des variables) pour une installation où ces deux
dossiers ne sont pas là où ComfyUI les met d'habitude.

## Le volume qui compte

`comfystudio-donnees` porte les conversations et le registre des
téléversements. **Sans lui, tout disparaît au redémarrage du conteneur.**

## Variables reconnues

| Variable | Rôle |
|---|---|
| `COMFY_URL`, `OLLAMA_URL` | où joindre les deux services |
| `STUDIO_HOTE`, `STUDIO_PORT` | adresse et port d'écoute |
| `STUDIO_AUTH` | `obligatoire` (défaut) ou `libre` |
| `STUDIO_ADMIN_MDP` | mot de passe du compte `admin`, posé avant le premier démarrage |
| `STUDIO_LLM`, `STUDIO_VISION` | modèles Ollama |
| `STUDIO_DONNEES` | dossier des conversations |
| `COMFY_DIR` | racine de ComfyUI, si elle est montée |
| `COMFY_MODELES`, `COMFY_ENTREE` | ou directement ces deux dossiers |
| `COMFY_LANCEUR` | script de démarrage de ComfyUI (hors conteneur) |
| `STUDIO_PURGE_ORPHELINS` | `1` pour effacer les fichiers que plus aucune conversation ne réclame |
| `STUDIO_TRAVAILLEURS` | demandes menées de front (3 par défaut) — une seule par carte quoi qu'il arrive |
| `STUDIO_PAUSE_PROPOSE` | minutes qu'une demande patiente pour une machine en pause (30) |
| `STUDIO_ANALYSE_PETITE` | `0` pour analyser sur la plus grosse carte plutôt que la plus petite |
| `STUDIO_ATTENTE_CARTE` | secondes qu'une analyse attend une carte occupée avant d'abandonner (1800) |
| `STUDIO_LLM_GARDER` | combien de temps Ollama garde le modèle chargé entre deux appels (`60s`) |
| `COMPOSE_PROJECT_NAME` | **le nom qui décide du volume** — à changer pour tout second studio |
| `STUDIO_NOM`, `STUDIO_IMAGE` | nom du conteneur et tag de l'image |
