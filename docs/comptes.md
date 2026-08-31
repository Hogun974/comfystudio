# Comptes

**Obligatoires par défaut.** Il faut être connecté pour lancer la moindre
demande. L'inverse laisserait une installation neuve ouverte tant que personne
n'y a pensé — et personne n'y pense. `STUDIO_AUTH=libre` rétablit l'ancien
comportement pour qui le veut vraiment.

Au premier démarrage, si aucun compte n'existe, un compte **`admin`** est créé
tout seul : sans lui, la porte serait fermée sans clef. Son mot de passe vient
de `STUDIO_ADMIN_MDP` — c'est ce qui permet de le fixer d'avance dans un
`docker-compose` — et à défaut il est tiré au sort et affiché **une seule
fois** au démarrage : dans la console si le studio tourne au premier plan, dans
le journal sinon (`docker compose logs comfystudio`, `journalctl -u
comfystudio`).

Ce qui reste ouvert sans session : la page elle-même (sinon on ne pourrait pas
afficher le formulaire de connexion), les routes de session, et les routes
d'administration — celles-ci vérifient elles-mêmes le jeton, et les fermer
condamnerait le seul moyen d'entrer quand aucun compte n'existe encore.

**Autrefois facultatifs.** Sans compte, le studio est celui d'avant : chaque navigateur
reçoit un identifiant opaque et garde son espace privé. Créer des comptes dans
`/admin` n'oblige personne à s'en servir.

Ce qu'un compte apporte, c'est que **l'espace suit la personne et non le
navigateur**. Deux limites disparaissent : le même historique sur l'ordinateur
et sur le téléphone, et surtout la fin d'un piège discret — `127.0.0.1:8199` et
`192.0.2.10:8199` sont le même studio mais deux cookies, donc deux historiques
séparés. C'est ainsi qu'on peut croire avoir « perdu ses conversations » en
changeant simplement d'adresse.

À la première connexion depuis un navigateur, ce qu'il avait accumulé sans
compte est rattaché au compte, et le nombre repris est annoncé. Sans cela
l'historique semblerait perdu au moment même où l'on se connecte pour le
retrouver.

Trois choix à connaître :

- **Le mot de passe n'est jamais conservé**, seule une empreinte scrypt avec un
  sel par compte. Personne ne peut le relire, pas même l'administrateur : il
  peut en imposer un nouveau, pas consulter l'ancien.
- **La session est un jeton signé**, pas une entrée en mémoire — sinon chaque
  redémarrage du studio déconnecterait tout le monde, et il redémarre souvent.
  Le cookie est `HttpOnly`.
- **Supprimer un compte n'efface pas son travail.** Ses conversations
  redeviennent sans propriétaire et restent sur le disque, récupérables.

Le jeton d'administration continue de fonctionner : c'est lui qui permet
d'entrer la toute première fois, quand aucun compte n'existe encore. Un
administrateur connecté n'a plus à le coller.
