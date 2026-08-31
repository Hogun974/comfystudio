# Deux studios sur la même machine

**Le nom du projet Compose décide du volume.** Pas le nom des services, pas
celui des conteneurs : le projet. Et par défaut, il vaut le nom du dossier. Deux
clones nommés `comfystudio` partagent donc **le même volume** — un `docker
compose down -v` dans le second efface les conversations, les comptes et les
clés du premier, et un `up -d` y remplace le conteneur en service. Vérifié en
`--dry-run` : `Container comfystudio Recreate`, `Volume
comfystudio_comfystudio-donnees Removed`.

Ce README a donné le mauvais conseil : il disait que `-p` « ne suffit pas », ce
qui est vrai mais incomplet, et le lecteur l'abandonnait pour se retrouver collé
au volume de production **en croyant être isolé**. La ligne qui compte est la
première :

```bash
COMPOSE_PROJECT_NAME=studio-essai
STUDIO_NOM=comfystudio-essai
STUDIO_IMAGE=comfystudio-essai:latest
STUDIO_PORT=8299
```

La première sépare le volume et le réseau. Les deux suivantes sont nécessaires
en plus, parce que le nom du conteneur et le tag de l'image ne dépendent pas du
projet : sans elles, un `--build` retaguerait l'image du studio en service —
vérifié, ça s'est produit pendant le premier essai d'installation. La dernière
évite que les deux se disputent le port.

Contrôle avant d'exécuter quoi que ce soit — il coûte une seconde et il montre
le volume qui serait touché :

```bash
docker compose up -d --dry-run
```
