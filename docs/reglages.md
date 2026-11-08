# Réglages

Par variables d'environnement, avant de lancer. En service systemd, elles se
posent dans `/etc/comfystudio.env`.

> **En conteneur, `.env` n'en atteint qu'une poignée.** `docker-compose.yml` ne
> relaie que ce que son bloc `environment:` nomme — les autres restent lettre
> morte, sans un mot. Voir [En
> conteneur](en-conteneur.md#variables-reconnues) pour la liste exacte et pour
> les quatre réglages qui passent par `/admin`.

```
set STUDIO_LLM=qwen2.5vl:7b
set STUDIO_LLM_ECRITURE=
set STUDIO_HOTE=127.0.0.1
set COMFY_LANCEUR=
set STUDIO_VISION=qwen2.5vl:7b
set STUDIO_PORT=8199
set COMFY_URL=http://127.0.0.1:8188
set OLLAMA_URL=http://localhost:11434
```

## Où joindre les services

| Variable | Défaut | |
|---|---|---|
| `COMFY_URL` | `http://127.0.0.1:8188` | l'adresse de ComfyUI |
| `OLLAMA_URL` | `http://localhost:11434` | **une ou plusieurs adresses séparées par des virgules** — le studio parle à chacune en direct et choisit laquelle emploie, voir [Plusieurs Ollama](plusieurs-ollama.md) |
| `STUDIO_HOTE` | `127.0.0.1` | `0.0.0.0` ouvre au réseau local |
| `STUDIO_PORT` | `8199` | le port d'écoute |
| `STUDIO_PORT_HOTE` | *le port d'écoute* | le port **publié** quand il diffère de celui d'écoute — posé par Compose, sert aux commandes affichées à l'écran |
| `STUDIO_ATTENTE_PROXY` | `55` | secondes, au plus, qu'une requête de programme arrivée **par un reverse proxy** (`X-Forwarded-For` ou `X-Forwarded-Proto`) attend un rendu, quoi que demande `attendre` : sous les 60 s d'un nginx laissé par défaut et les 90 s du nginx-proxy-manager, qui couperaient sinon en 504. La réponse rend alors l'état courant, avec l'en-tête `X-Attente-Bornee`. Une requête directe garde son `attendre`. `0` : aucune attente derrière un proxy — voir [Piloter par programme](piloter-par-programme.md#demander-un-rendu--post-apiv1rendus) |

## Modèles de langage

| Variable | Défaut | |
|---|---|---|
| `STUDIO_LLM` | `qwen2.5vl:7b` | le modèle **rapide** : aiguillage, extraction du sujet. Depuis que la lecture d'image prend son propre modèle, il peut être un petit modèle de texte |
| `STUDIO_LLM_ECRITURE` | *(vide)* | impose le modèle d'**écriture** — enrichissement, traduction, paroles. Vide, le studio prend le plus gros modèle installé qui tienne, machine par machine. Il est ignoré sur une machine qui ne le porte pas |
| `STUDIO_VISION` | `qwen2.5vl:7b` | le modèle qui lit les images. **Posé explicitement**, il est honoré partout où il est installé et déclare savoir voir — y compris s'il déborde la carte, parce qu'un nom écrit à la main est un choix ; le journal l'écrit alors (« lecture par X — modèle de vision imposé »). **Laissé au défaut**, il ne s'impose pas : c'est le plus gros modèle *voyant* que la carte de la machine peut tenir qui répond |
| `STUDIO_LLM_GARDER` | `60s` | combien de temps Ollama garde le modèle chargé entre deux appels |
| `STUDIO_LLM_CONTEXTE` | `8192` | le contexte (`num_ctx`) annoncé à Ollama à chaque appel. Sans lui, Ollama 0.40 le choisit d'après la carte — 4096 sur une 2080 Ti, et le gabarit de l'analyse en pèse déjà ~3900 : le plan était coupé en plein JSON. Le même pour tous les appels, sinon Ollama recharge le modèle |

## File, cartes et patience

| Variable | Défaut | |
|---|---|---|
| `STUDIO_TRAVAILLEURS` | `3` | demandes menées de front — une seule par carte quoi qu'il arrive |
| `STUDIO_ATTENTE_CARTE` | `1800` | secondes qu'une analyse attend une carte occupée quand il n'y a plus d'autre machine |
| `STUDIO_ANALYSE_PETITE` | `0` | `1` pour analyser sur la plus **petite** carte plutôt que la plus grosse — l'ordre d'avant le 1er septembre 2026. **Ne concerne que l'analyse empruntée à une machine par son agent** ; en direct, la règle est la même et ne se règle pas. Voir [Qui prend le travail](qui-prend-le-travail.md) |
| `STUDIO_PAUSE_PROPOSE` | `30` | minutes qu'une demande patiente devant l'écran pour une machine en pause |
| `STUDIO_ARMEE_HEURES` | `12` | heures pendant lesquelles elle reste ensuite **armée**, prête à repartir seule au réveil. `0` rétablit le refus immédiat — voir [Attendre le retour d'une machine en pause](attendre-une-machine.md) |
| `STUDIO_VRAM_REPOS` | `1` | minutes sans travail au bout desquelles une carte **rend sa mémoire**. Un seul réglage pour tout le parc. **Ce défaut change le comportement de toute installation existante à la mise à jour** : qui ne rend qu'une image de temps en temps paiera un rechargement du modèle à chaque fois — **coût non mesuré**, voir [Mesures](mesures.md). `0` annule complètement le réglage — voir [Rendre la carte quand plus rien ne la demande](rendre-la-carte.md) |

`STUDIO_PAUSE_PROPOSE`, `STUDIO_ARMEE_HEURES`, `STUDIO_VRAM_REPOS` et
`STUDIO_PLAFOND_NUAGE` ne donnent que la valeur de **départ** : les quatre se
règlent ensuite dans `/admin` et sont conservés d'un démarrage à l'autre.

## Nuage

| Variable | Défaut | |
|---|---|---|
| `STUDIO_PLAFOND_NUAGE` | `0` | appels distants qu'un compte peut faire dans le mois avant de revenir au local. `0` = aucune limite — voir [Ce que le nuage a coûté](cout-du-nuage.md) |

Les clés d'API elles-mêmes ne passent **pas** par l'environnement : elles se
posent dans `/admin` et vivent dans `conversations/_cles.json`, exclu du dépôt.
Voir [Clés d'API](cles-api.md).

## Connexion et administration

| Variable | Défaut | |
|---|---|---|
| `STUDIO_AUTH` | `obligatoire` | `libre` supprime la connexion — quiconque atteint le port peut alors tout faire, clés comprises |
| `STUDIO_ADRESSE_PUBLIQUE` | *(absent)* | l'adresse du studio derrière un reverse proxy TLS, schéma et nom seulement : `https://studio.maison`, sans chemin ni identifiants. Ouverte en http, la page y propose un lien là où le navigateur refuse (notifications, installation comme application), et les adresses à coller dans un outil (*clés d'accès › Brancher un outil*) partent d'elle. Mal formée, elle est ignorée et la bannière de démarrage dit pourquoi |
| `STUDIO_ADMIN_MDP` | *(tiré au sort)* | mot de passe du compte `admin`, posé avant le premier démarrage |
| `STUDIO_ADMIN` | *(tiré au sort et conservé)* | le jeton de `/admin`. En imposer un à la main est possible ; rien n'en contrôle la longueur, et un jeton court se force — la porte freine à partir du troisième essai, l'attente doublant à chaque échec, mais cela reste un mauvais choix |

## Disque

| Variable | Défaut | |
|---|---|---|
| `STUDIO_DONNEES` | *à côté du studio* | dossier des conversations et du registre |
| `COMFY_DIR` | *deviné* | racine de ComfyUI |
| `COMFY_MODELES`, `COMFY_ENTREE` | *sous `COMFY_DIR`* | ou directement ces deux dossiers |
| `COMFY_LANCEUR` | *deviné* | script de démarrage de ComfyUI |
| `STUDIO_PURGE_ORPHELINS` | *(absent)* | `1` pour effacer au démarrage les fichiers que plus aucune conversation ne réclame |
| `STUDIO_ANALYSE_DELAI` | `180` | secondes au-delà desquelles un modèle local qui n'a pas répondu à une analyse de **texte** est abandonné **pour cette demande** : l'aiguillage par mots-clés prend le relais, sans enrichissement ni traduction. Mesure du 7 septembre 2026 : 119 à 300 s par appel sur la GTX 1060 de **zima**, dont la carte ne tient aucun modèle de 7 milliards. La lecture d'image garde ses 300 ou 900 s |
| `STUDIO_ANALYSE_IMPOSE_DELAI` | `45` | secondes que l'analyse d'une demande au **moteur imposé** (choisi dans la page, ou `moteur` d'un programme) peut passer à **attendre** : la carte d'une machine qui calcule, un autre cerveau que le premier, un Ollama sur processeur. Au-delà, le rendu part avec la demande telle quelle, sur le moteur imposé, sans enrichissement ; la traduction, qui demande un modèle, n'est pas faite — sans gêne pour un moteur qui lit le français (FLUX.2 klein) ; pour un moteur qui ne lit que l'anglais, c'est le chemin d'une traduction ratée : moteur gardé, prompt en français, et la question « je l'envoie tel quel ? » à qui sait y répondre. Le premier cerveau, libre et sur sa carte, n'est jamais coupé. Sans moteur imposé, rien ne change : c'est l'analyse qui choisit le moteur. Incident du 8 novembre 2026 : dix minutes et plus d'analyse pour `moteur: klein9b`, le PC mis de côté et le NAS servant cinq demandes l'une après l'autre |

## L'installeur, pas le studio

Deux variables ne sont lues que par `installation.py`, au moment d'installer ou
de construire, jamais par le serveur :

| Variable | Défaut | |
|---|---|---|
| `STUDIO_PYTHON` | *deviné* | l'interpréteur à retenir quand plusieurs conviennent — `LANCER ComfyStudio.bat` la pose lui-même |
| `HTTPS_PROXY` (ou `https_proxy`) | *(absent)* | le mandataire par lequel passent les téléchargements de l'installeur |

## Sur une machine à carte, pas sur le studio

L'agent lit les siennes — les neuf que `agent_noeud.py` interroge : `STUDIO_URL`,
`STUDIO_JETON`, `COMFY_URL`, `OLLAMA_URL`, `COMFY_SORTIES`,
`COMFY_GARDER_HEURES`, `AGENT_EMPREINTE`,
`AGENT_LIVRAISON_MINUTES`, `AGENT_SANS_MAJ_AUTO` — plus `AGENT_MAJ_TENTEE`,
qu'il pose et lit lui-même pour ne pas se réinstaller en boucle, et qu'on ne
règle pas. Elles remplacent
`agent_noeud.json` quand il n'y a pas de fichier. Voir [Des machines qui
viennent d'elles-mêmes](machines-a-agent.md).
