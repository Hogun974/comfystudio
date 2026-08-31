# Plusieurs utilisateurs

Le studio se partage sans comptes ni mots de passe. Au premier chargement, chaque
navigateur reçoit un cookie `studio` — un identifiant opaque de 32 caractères.
Toutes les conversations, tâches et images lui sont rattachées.

Concrètement : navigateur différent, machine différente, session privée
différente → espace différent. Personne ne voit les conversations, les demandes
ni les images des autres. **Le serveur, lui, voit tout** : les fichiers de
`conversations/` sont en clair et les journaux de la console listent chaque
demande, quel qu'en soit l'auteur.

Un cookie plutôt qu'un en-tête : les images sont chargées par `<img src>`, qui
n'envoie aucun en-tête personnalisé. Le cookie part tout seul et couvre donc
aussi le relais de fichiers — c'est ce qui a décidé du choix.

Ce qui reste **volontairement commun** : la file d'attente et son compteur.
Chacun voit « 3 en file », mais seul l'auteur voit le texte de ses demandes.

## Plusieurs demandes à la fois, une par carte

Le studio mène **plusieurs demandes de front**, mais **une seule par carte**.
Une carte ne se partage pas : deux rendus dessus ne vont pas deux fois plus
vite, ils rament tous les deux. La règle vaut pour tout ce qui l'occupe — image,
vidéo, son, maillage, et jusqu'aux questions posées à son modèle de langage.

Mesuré sur deux machines, deux demandes envoyées coup sur coup :

```
38 s   DEUX en cours : sur NAS ZimaOS (GTX 1060) · sur PC (RTX 2080 Ti)
79 s   DEUX en cours : sur NAS ZimaOS (GTX 1060) · sur PC (RTX 2080 Ti)
```

Et deux demandes qui visent la **même** carte, sur la même installation :

```
PC (RTX 2080 Ti) calcule deja pour quelqu'un — on prend le tour suivant
la carte se libere apres 139 s d'attente
termine en 62 s
```

Ce qui a décidé de ce montage : sur deux demandes complètes, 32 secondes hors
carte pour 304 secondes dessus. **Dix pour cent du temps seulement est de
l'analyse** — le plafond est la carte, et ajouter une machine ajoute donc bien
du débit, pas seulement des moteurs.

Trois conséquences visibles :

- **Une carte libre passe devant une grosse carte occupée.** Ce n'est pas
  toujours le plus rapide pour une demande isolée — attendre deux minutes la
  grosse carte peut battre un rendu lancé tout de suite sur la petite — mais
  c'est le plus rapide pour l'ensemble, et le seul choix possible sans prédire
  une durée qu'on ne connaît pas.
- **La file distingue trois états** : en attente, *attend une carte*, et en
  cours. Le deuxième est nouveau : la demande est analysée, sa machine est
  choisie, et cette machine finit le travail d'un autre.
- **Une question au modèle de langage n'attend une carte que vingt secondes.**
  Au-delà, elle va voir une autre machine, ou l'on s'en passe. Sans cette borne,
  une question de deux secondes attendait derrière un rendu de deux minutes en
  retenant un travailleur — trois demandes se sont ainsi bloquées mutuellement
  pendant dix minutes.

`STUDIO_TRAVAILLEURS` fixe le nombre de demandes menées de front (trois par
défaut). Il ne borne pas le matériel mais l'appétit : vingt demandes d'un coup
n'ouvrent pas vingt analyses simultanées.

## Ouvrir au réseau local

Par défaut le studio n'écoute que sur `127.0.0.1` : cette machine, et elle seule.

C'est activé dans `LANCER ComfyStudio.bat` :

```
set STUDIO_HOTE=0.0.0.0
```

Remets `127.0.0.1` pour refermer. Hors Windows, c'est la même variable :
`STUDIO_HOTE=0.0.0.0 python3 serveur.py`, ou `--hote 0.0.0.0` passé à
`service/installer_service.sh`. **En conteneur, la question ne se pose pas** :
`STUDIO_HOTE` y vaut déjà `0.0.0.0` — sinon le studio n'écouterait que la boucle
locale du conteneur et le port publié ne mènerait nulle part. C'est le port
publié par Compose qui décide de ce qui est joignable.

**Mesure ce que cela veut dire.** La connexion est obligatoire par défaut : sans
compte, une requête sur le port ne rend qu'un `401` (voir [Comptes](comptes.md)).
Ce qui reste vrai, c'est que le formulaire de connexion, lui, est exposé à tout
le réseau. À réserver à un réseau de confiance.

`STUDIO_AUTH=libre` rétablit l'ancien comportement — aucune authentification :
quiconque atteint le port peut alors générer (contenu adulte compris),
téléverser des images, occuper le GPU et dépenser les clés d'API posées dans
`/admin`. Ne le mets qu'en le sachant.

Le pilotage de ComfyUI, lui, reste refusé à distance dans tous les cas — un
visiteur ne peut pas arrêter le moteur sous les pieds des autres.

## Retrouver son espace sur un autre appareil

Le téléphone est un autre navigateur : il a sa propre identité, donc son propre
espace vide. C'est ce qui isole les gens entre eux — mais cela sépare aussi une
personne de ses propres conversations.

D'où l'appairage : sur l'ordinateur, **lier un appareil** affiche un code à six
chiffres valable cinq minutes. Sur le téléphone, **rejoindre** puis le code : les
deux appareils partagent alors le même espace. Le code n'est délivré que depuis
la machine hôte et ne sert qu'une fois.

## Les conversations sans propriétaire

Une conversation orpheline revient au navigateur de la machine hôte, dès qu'une
page y est ouverte. **Ce n'est pas un événement unique** : une adoption à un coup
rendait l'historique irrécupérable dès qu'un client quelconque avait touché la
page en premier — l'utilisateur se retrouvait devant une interface vide, sans
recours. Toute page ouverte depuis la machine reprend ce qui n'appartient à
personne ; s'il n'y a rien d'orphelin, il ne se passe rien.

« La machine hôte » signifie **toutes** ses adresses, pas seulement `127.0.0.1` :
une fois le studio ouvert au réseau, on atteint souvent sa propre machine par son
adresse LAN, et s'y limiter aurait fait perdre ce droit.

## Sur téléphone

Sous 820 px de large, la barre latérale devient un tiroir : le bouton ☰ en haut à
gauche l'ouvre, un appui à côté la referme, et choisir une conversation la referme
aussi. Auparavant elle était simplement masquée — ni les conversations, ni le
bouton d'en créer une, ni l'état du moteur n'étaient atteignables.
