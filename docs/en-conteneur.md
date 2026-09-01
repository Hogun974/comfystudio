# En conteneur

Le studio ne calcule rien : il pilote un ComfyUI et un Ollama qui vivent
ailleurs. L'image est donc minuscule, sans CUDA. Mesuré le **30 août 2026** sur
une machine sans carte : **49 s** de construction et **46 Mo** téléchargés avec
l'image de base `python:3.12-slim` déjà en cache, environ **110 Mo** sans —
puis **4 s** entre `up -d` et la première page servie. Ces quatre chiffres, et
tous les autres du parc, sont rassemblés dans [Mesures](mesures.md).

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

`comfystudio-donnees` porte tout ce que le studio écrit : conversations,
comptes, clés, registre des machines, avis, journal des appels distants
(`nuage.jsonl`), sorties rapatriées. **Sans lui, tout disparaît au redémarrage
du conteneur.**

## Variables reconnues

**Tout ce que le studio lit est relayé.** `docker-compose.yml` ne transmet au
conteneur que ce que son bloc `environment:` nomme — et il les nomme désormais
toutes. Ce n'a pas toujours été vrai : dix réglages étaient lus hors conteneur
et ignorés en silence dedans, pendant que cette page les donnait pour reconnus.
`banc_conteneur.py` relit maintenant `serveur.py` à chaque vérification et
refuse tout nom qui n'arriverait pas jusqu'ici.

Les plus courantes :

| Variable | Rôle |
|---|---|
| `COMFY_URL` | où joindre ComfyUI |
| `OLLAMA_URL` | où joindre Ollama — **une ou plusieurs adresses séparées par des virgules**, voir [Plusieurs Ollama](plusieurs-ollama.md) |
| `STUDIO_AUTH` | `obligatoire` (défaut) ou `libre` |
| `STUDIO_ADMIN_MDP` | mot de passe du compte `admin`, posé avant le premier démarrage |
| `STUDIO_LLM`, `STUDIO_VISION` | modèles Ollama |
| `STUDIO_LLM_ECRITURE` | impose le modèle d'écriture ; vide, le studio prend le plus gros qui tienne |

Les autres, plus rares, passent de la même façon : `STUDIO_TRAVAILLEURS`,
`STUDIO_ATTENTE_CARTE`, `STUDIO_ANALYSE_MAX`, `STUDIO_ANALYSE_PETITE`,
`STUDIO_LLM_GARDER`, `STUDIO_PURGE_ORPHELINS`, `STUDIO_ADMIN`,
`COMFY_MODELES`, `COMFY_ENTREE`, `COMFY_LANCEUR`. Leur détail est dans
[Réglages](reglages.md).

**Quatre exceptions**, nommées une à une dans le banc avec leur raison — il
refuse toute entrée qui ne correspondrait plus à rien. Deux sont imposées par
Compose : `STUDIO_PORT` n'est **pas** relayé — le conteneur écoute toujours sur
8199, et c'est Compose qui le publie ailleurs, `STUDIO_PORT_HOTE` servant à ce
que la bannière annonce le bon port ; `STUDIO_HOTE` est forcé à `0.0.0.0`, sans
quoi le port publié ne mènerait nulle part. Les deux autres viennent de l'image :
`COMFY_DIR` et `STUDIO_DONNEES` sont les points de montage (`/comfy` et
`/donnees`) et n'ont pas à être touchés.

**Un seul endroit pour chaque défaut.** Quand `.env` ne dit rien, Compose relaie
une valeur vide et c'est le défaut de `serveur.py` qui s'applique. Deux valeurs
en dur seulement, et elles sont voulues : `COMFY_URL` et `OLLAMA_URL` visent
`host.docker.internal` au lieu de `127.0.0.1`, parce que dans un conteneur la
machine hôte n'est pas soi. Le banc refuse toute autre valeur figée — répéter
dans le compose un défaut déjà écrit dans le code, c'est deux maîtres pour un
réglage, et le jour où le code change l'image garde l'ancien sans un mot.

Ces quatre-là ne sont pas lus par le studio mais par **Compose** :

| Variable | Rôle |
|---|---|
| `STUDIO_PORT`, `COMFY_PORT`, `OLLAMA_PORT` | les ports publiés sur l'hôte |
| `COMPOSE_PROJECT_NAME` | **le nom qui décide du volume** — à changer pour tout second studio |
| `STUDIO_NOM`, `STUDIO_IMAGE` | nom du conteneur et tag de l'image |
| `ROUE`, `COMFY_ARGS` | construction et arguments du ComfyUI conteneurisé |

**Trois réglages ont aussi leur champ dans `/admin`.** Les deux délais de pause
(`STUDIO_PAUSE_PROPOSE`, `STUDIO_ARMEE_HEURES`, voir [Attendre le retour d'une
machine en pause](attendre-une-machine.md)) et le plafond du nuage
(`STUDIO_PLAFOND_NUAGE`, voir [Ce que le nuage a coûté](cout-du-nuage.md)). La
variable ne donne que la valeur du **premier** démarrage ; ensuite c'est la
valeur posée dans `/admin` qui fait foi, et elle survit aux redémarrages.
