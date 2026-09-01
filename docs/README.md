# Documentation ComfyStudio

Ces pages sont la matière du wiki, qui n'est pas encore monté. Une page par
sujet ; le [README](../README.md) ne garde que la présentation et l'installation.

## Installer et démarrer

- [Installation](installation.md) — prérequis, installeur, exécutable Windows, ce qu'il télécharge selon la carte, et le premier démarrage.
- [En conteneur](en-conteneur.md) — Docker et Compose, ComfyUI conteneurisé, volumes, et le tableau complet des variables d'environnement.
- [Deux studios sur la même machine](deux-studios-sur-la-meme-machine.md) — **à lire avant de lancer un second studio** : par défaut il écrit dans le volume du premier et un `down -v` efface les données de l'autre.
- [Réglages](reglages.md) — les variables d'environnement à poser avant de lancer, hors conteneur.

## Comprendre ce qui se passe

- [Architecture](architecture.md) — le chemin d'une demande, du français jusqu'à ComfyUI, et pourquoi chaque appel ne fait qu'une chose.
- [Un classifieur plutôt qu'un modèle](aiguilleur-classifieur.md) — pourquoi l'aiguillage passe par un Bayes naïf de 0,19 Mo plutôt que par un LLM, les raccourcis écrits, et ce que la mesure a appris.
- [Le modèle qui écrit n'est pas celui qui aiguille](modele-qui-ecrit.md) — pourquoi le studio choisit tout seul un gros modèle pour les paroles.
- [Plusieurs Ollama, et lequel le studio choisit](plusieurs-ollama.md) — `OLLAMA_URL` en liste, l'ordre appliqué, et pourquoi une image ne part jamais sur une machine qui ne voit pas.
- [Mesures](mesures.md) — les durées relevées, chacune avec **sa date et sa machine** : une durée ne se revérifie pas depuis le code, elle vieillit en silence.
- [Combien de temps ça va prendre](combien-de-temps.md) — le devis annoncé avant le rendu, la médiane, le silence en dessous de trois mesures, et le temps écoulé servi par le serveur.
- [Éprouver les bancs](eprouver-les-bancs.md) — `banc_mutations.py`, qui casse le code exprès pour vérifier que les bancs le voient : trois fois en une semaine, un banc vert a couvert une fonctionnalité morte.

## Plusieurs machines

- [Qui prend le travail](qui-prend-le-travail.md) — l'analyse prend la plus grosse carte, le rendu la plus petite qui tient, et pourquoi ces deux règles sont opposées.
- [Des machines qui viennent d'elles-mêmes](machines-a-agent.md) — l'agent, son installation en une commande, la mise à jour d'un parc, la mise en pause.
- [Plusieurs machines, de puissances différentes](plusieurs-machines.md) — qui reçoit quoi, comment imposer une machine, et les pièges du multi-machines.
- [Déplacer le studio sur une machine sans carte](studio-sans-carte.md) — poser le studio sur un NAS et laisser les cartes où elles sont, données comprises.
- [Quand une machine tombe](quand-une-machine-tombe.md) — la reprise automatique, et comment une panne est distinguée d'une faute.
- [Attendre le retour d'une machine en pause](attendre-une-machine.md) — la demande gardée armée, les trois portes de réveil, et le réglage `armee_heures`.
- [Le modèle de langage peut venir d'une autre machine](modele-de-langage-distant.md) — la bascule vers l'Ollama d'un nœud quand le sien ne répond plus.

## Utiliser le studio

- [Plusieurs utilisateurs](plusieurs-utilisateurs.md) — les espaces séparés par navigateur, l'ouverture au réseau local, et pourquoi retrouver son espace sur un téléphone passe par un compte.
- [Comptes](comptes.md) — l'authentification obligatoire par défaut, le compte `admin`, et ce qu'un compte apporte.
- [Piloter ComfyUI depuis l'interface](piloter-comfyui.md) — démarrer et arrêter le moteur depuis la barre latérale.
- [Moteur, priorité, taille, machine](reglages-de-rendu.md) — les quatre réglages qui sont à toi, portés par la conversation, et les cas où ils ne s'appliquent pas.
- [Le brouillon, et « refaire en soigné »](brouillon.md) — un rendu au quart des étapes pour juger un prompt, et pourquoi il ne prédit pas le cadrage.
- [Une demande, plusieurs variantes](variantes.md) — jusqu'à quatre tirages du même plan, pourquoi ce sont N demandes dans la file et non un lot, et laquelle « la » désigne ensuite.
- [Retrouver ce qu'on a produit](mediatheque.md) — la médiathèque, son tri, ses filtres — brouillons ou finies, durée de rendu — et sa recherche.
- [Fermer une conversation](fermer-une-conversation.md) — la corbeille de vingt-quatre heures, et les fichiers que plus rien ne réclame.
- [Pouce en l'air, pouce en bas](avis.md) — où va le retour, à quoi il sert, et le bouton « refaire sur la grosse carte ».

## Ce que le studio sait faire

- [Ne changer qu'une partie de l'image](retouche-localisee.md) — la retouche localisée, le recollage exact, et la zone désignée par sa description.
- [Garder le même personnage](garder-le-meme-personnage.md) — produire une image neuve en conservant quelqu'un.
- [Agrandir une image](agrandir-une-image.md) — l'agrandissement 2×, 3× ou 4×, reconnu à l'écrit.
- [Détourer](detourer.md) — isoler le sujet et rendre le fond transparent, en deux secondes.
- [Fluidifier une vidéo, ou la passer au ralenti](fluidifier-une-video.md) — le même calcul dans les deux cas, seule la cadence de sortie les sépare.
- [Contenu adulte](contenu-adulte.md) — ce qui n'est pas filtré, la seule limite codée en dur, et ce qui ne sort jamais de la machine.

## Aller chercher ailleurs

- [Clés d'API : LLM et images](cles-api.md) — les fournisseurs distants, le choix demande par demande, et le local comme repli de tout.
- [Ce que le nuage a coûté](cout-du-nuage.md) — le compteur d'appels distants par compte et par fournisseur, le plafond mensuel, et pourquoi aucun euro n'y figure.
- [Télécharger les modèles](telecharger-les-modeles.md) — la récupération en HTTPS direct, la reprise après coupure, la vérification de taille.
