# Déplacer le studio sur une machine sans carte

Le studio ne calcule rien : il aiguille, met en file et répartit. Sa place
naturelle est donc une machine allumée en permanence — un NAS, un petit
serveur — pendant que les cartes graphiques restent où elles sont.

C'est le même montage que [En conteneur](en-conteneur.md), vu de l'autre bout :
là-bas on démarre le studio et on entre dedans, ici on lui donne les machines
qui calculent.

**Le chemin évident est le mauvais.** On pense d'abord à exposer ComfyUI au
réseau (`--listen 0.0.0.0`) pour que le studio l'atteigne. C'est une carte et
une API sans authentification ouvertes sur le réseau local, plus une règle de
pare-feu à maintenir sur chaque machine.

**Faites l'inverse : posez un agent sur chaque machine à carte.** L'agent
appelle le studio, jamais le contraire. Rien n'est exposé, aucune règle de
pare-feu, et une machine peut même vivre derrière une autre box.

```
    ┌──────────────┐        ┌──────────────────────────┐
    │ Navigateurs  │───────▶│  ComfyStudio (sans carte)│
    └──────────────┘        │  Docker, allumé en perm. │
                            └────────────▲─────────────┘
                    l'agent appelle ─────┤
              ┌──────────────────────────┴──────────────┐
    ┌─────────┴──────────┐                  ┌───────────┴────────┐
    │ PC · RTX 2080 Ti   │                  │ NAS · GTX 1060     │
    │ ComfyUI en 127.0.0.1│                 │ ComfyUI local      │
    └────────────────────┘                  └────────────────────┘
```

## La marche à suivre

1. **Sur la machine d'accueil**, déployer le studio seul :
   ```bash
   git clone https://github.com/Hogun974/comfystudio.git comfystudio
   cd comfystudio
   cp .env.exemple .env      # y mettre au moins STUDIO_ADMIN_MDP
   docker compose up -d
   ```
   Laisser `COMFY_URL` par défaut : sans ComfyUI local, le studio dira « VRAM
   inconnue » au démarrage, ce qui est exact et sans conséquence — les machines
   à agent annoncent la leur.

2. **Reprendre les données**, si l'on veut garder conversations, comptes et
   clés. Attention : `conversations/` n'est pas seul — les avis et les sorties
   déjà rapatriées vivent à côté, et les oublier laisse une installation qui
   a l'air complète, sans ses pouces ni ses images :
   ```bash
   # sur l'ancienne machine — TOUT le dossier de données, pas seulement
   # conversations/ : les avis et les sorties déjà rapatriées sont à côté
   tar -czf donnees.tgz conversations avis.jsonl sorties
   # sur la nouvelle
   docker compose stop comfystudio
   docker run --rm -v comfystudio_comfystudio-donnees:/d -v "$PWD":/s \
     alpine sh -c 'tar -xzf /s/donnees.tgz -C /tmp && cp -a /tmp/conversations/. /d/ && cp -a /tmp/avis.jsonl /tmp/sorties /d/'
   docker compose start comfystudio
   ```
   **Rendre ensuite le dossier au studio**, sinon rien de ce qui suit ne sera
   enregistré :
   ```bash
   docker run --rm -v comfystudio_comfystudio-donnees:/d alpine chown -R 10001:10001 /d
   ```
   Le studio tourne sous un utilisateur sans privilèges ; les fichiers repris
   portent le propriétaire de la machine d'origine. Sans cette ligne il démarre,
   se déclare en bonne santé, affiche les conversations reprises — et perd
   silencieusement tout ce qu'on fait ensuite.

   Le secret de session est dans ce dossier : les sessions ouvertes survivent
   au déménagement, personne n'a à se reconnecter.

3. **Déclarer chaque machine à carte** dans `/admin`, récupérer son jeton, puis
   sur cette machine :
   ```bash
   curl -fsS http://IP-DU-STUDIO:8199/api/noeud/noeud.sh -o noeud.sh
   bash noeud.sh --studio http://IP-DU-STUDIO:8199 --jeton SON_JETON
   ```
   (`noeud.bat` sous Windows.) L'agent démarre ComfyUI si besoin, se présente,
   et vient chercher du travail toutes les dix secondes.

4. **Ne rien changer à ComfyUI.** Il continue d'écouter sur `127.0.0.1` : seul
   l'agent, qui tourne sur la même machine, lui parle.

## Ce qui change une fois déplacé

- **Le studio ne se choisit jamais pour un rendu.** « Pas de carte, pas de
  rendu » vaut pour tout le monde, lui compris. Il l'a fallu : depuis que le
  rendu prend la plus petite carte, une machine à zéro gigaoctet serait choisie
  **la première**, étant la plus petite de toutes. Signalé par l'utilisateur —
  *« il m'affiche souvent moteur local, et du coup attend dans le vide »* : le
  studio se désignait, la demande partait sur une machine incapable, et le studio
  patientait une demi-heure. Voir [Qui prend le
  travail](qui-prend-le-travail.md).
- **Le studio ne télécharge plus de modèles pour personne.** Il n'écrit que sur
  son propre disque, et il n'a plus de ComfyUI dessus. Chaque machine à carte
  s'approvisionne elle-même : `curl -fsS http://IP-DU-STUDIO:8199/api/noeud/modeles.sh | bash -s -- http://IP-DU-STUDIO:8199`
- **Le bouton « démarrer ComfyUI » de l'interface ne sert plus.** Il pilote le
  ComfyUI de la machine hôte, qui n'existe plus. Ce sont les agents qui
  démarrent le leur.
- **Les fichiers joints voyagent avec le travail** vers la machine qui calcule,
  et les sorties sont rapatriées vers le studio. Rien à monter en réseau.
