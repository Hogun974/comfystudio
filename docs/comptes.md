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

## Le second facteur

**Facultatif, et armé par chacun sur son propre compte.** Le bouton « second
facteur » du bandeau, à côté de « sortir ». L'administrateur ne peut pas
l'armer pour quelqu'un d'autre : il faudrait son téléphone.

Un code à six chiffres qui change toutes les trente secondes, que ton
application d'authentification calcule hors ligne. Le studio n'appelle aucun
service, n'envoie aucun SMS, et n'a rien à installer pour ça.

### L'enrôlement, en deux temps

1. **Commencer.** Tu donnes ton mot de passe courant ; le studio tire un secret
   et te l'affiche.
2. **Le recopier** dans ton application. Il n'y a **pas de QR code** : le
   dessiner demanderait une bibliothèque, et la page du studio n'a aucune
   dépendance. Deux façons de faire à la place :
   - recopier le secret à la main. Il est affiché par groupes de quatre pour
     qu'on ne se perde pas ; **les espaces ne comptent pas**, la casse non plus,
     et le studio les pardonne quand tu le retapes.
   - ou ouvrir le lien `otpauth://` juste en dessous, que le téléphone passe
     directement à l'application.
3. **Confirmer** avec un code. Tant que ce n'est pas fait, **rien n'est armé** :
   ton mot de passe seul continue d'ouvrir le studio.

Ces deux temps ne sont pas une politesse. Armer au moment où l'on tire le secret
enfermerait dehors quiconque a mal recopié, fermé l'onglet trop tôt, ou dont
l'horloge de téléphone est fausse — et **personne ne pourrait le faire rentrer**,
pas même l'administrateur, puisque c'est justement ce qu'on vient d'empêcher.

**Après avoir confirmé, attends le code suivant.** Celui que tu viens de taper
est déjà consommé : sans cela, il rouvrirait une session dans la minute, et le
rejeu rentrerait par la porte de l'enrôlement. Trente secondes au plus. L'écran
le dit, parce que sinon on croit que l'enrôlement a raté.

### Les dix codes de secours

Ils s'affichent **une seule fois**, à la confirmation. **Note-les tout de
suite** : ce qui est gardé n'est pas eux, c'est leur empreinte scrypt — comme
pour un mot de passe. Personne ne peut te les redonner, pas même
l'administrateur.

Chacun ne sert qu'une fois. Ils s'épuisent, et c'est voulu : dix codes qu'on
raye au fur et à mesure disent qu'ils s'épuisent, là où un « code maître »
unique finirait noté quelque part comme un second mot de passe permanent.

Le bandeau affiche combien il en reste (« armé · 3 codes de secours restants sur
10 »). Quand il en reste peu, **régénère un jeu** : le bouton « de nouveaux
codes de secours » en tire dix neufs et **annule les anciens**. Le secret, lui,
ne change pas — ton téléphone continue de servir, tu n'as rien à rescanner.

### Se connecter, une fois le facteur armé

L'écran de connexion se fait en deux temps : nom et mot de passe, puis la case
du code si le studio la demande. Un **code de secours convient aussi** — c'est
ce qu'on tape quand le téléphone n'est pas là.

Le studio ne dit jamais lequel des trois est faux. « nom, mot de passe ou code
incorrect » couvre les trois cas, et c'est délibéré : distinguer publierait la
liste des comptes, et dire « le mot de passe était bon » à qui se trompe de code
ferait de cette porte un moyen d'essayer des mots de passe.

Après trois échecs, l'attente double à chaque essai — 1 s, 2, 4, 8… plafonnée à
30 —, par couple compte + adresse. C'est le **même compteur** que pour le mot de
passe : le code passe par la même route, et non par une porte à lui qui n'aurait
rien freiné.

### Rouvrir un compte dont le téléphone est perdu

Dans l'ordre, du moins coûteux au plus :

1. **Un code de secours.** Tape-le à la place du code à six chiffres, dans la
   même case. Puis, une fois entré, désarme le facteur ou régénère un jeu.
2. **Plus de codes de secours non plus.** Le compte ne peut plus s'ouvrir seul,
   et c'est exactement ce que le second facteur promet. Il faut alors la main
   sur la machine :
   - **par `/admin`**, avec le jeton d'administration (`STUDIO_ADMIN`) : la
     seule porte qui n'ait pas de second facteur, parce que c'est celle de
     l'amorçage. Elle permet d'imposer un nouveau mot de passe — mais **pas** de
     désarmer le facteur de quelqu'un d'autre.
   - **par le fichier**, et c'est le vrai remède : arrête le studio, ouvre
     `conversations/_comptes.json`, **retire le bloc `"mfa"`** du compte
     concerné, relance. Le compte redevient un compte à mot de passe simple, et
     son propriétaire peut réenrôler.

   Sauvegarde le fichier avant d'y toucher, et n'y touche pas pendant que le
   studio tourne : il le réécrit en entier à chaque changement.

### Ce qu'il faut savoir sur le stockage

**Le secret TOTP est en clair** dans `conversations/_comptes.json`. Ce n'est pas
une négligence et ça ne peut pas être autrement : à la différence d'un mot de
passe, il faut le **relire** pour recalculer le code attendu, donc il ne peut pas
être gardé sous forme d'empreinte. C'est vrai de toutes les implémentations de
TOTP.

Ce qui est fait à la place : le fichier est écrit en **`0600`** — lisible par le
seul compte qui fait tourner le studio, ce qui n'a d'effet que sur POSIX et
aucun sur Windows —, le secret **ne sort jamais** par une route (ni par la liste
des comptes de `/admin`, ni par l'état du facteur), et les **codes de secours**,
eux, sont empreints avec scrypt comme des mots de passe.

Conséquence à connaître : **qui lit le disque de l'hôte peut calculer tes
codes**. Le second facteur protège d'un mot de passe qui fuit, pas de quelqu'un
qui a la machine. `SECURITY.md` détaille ce qu'il protège et ce qu'il ne
protège pas.

**Il ne révoque pas les sessions ouvertes.** Armer, désarmer ou changer de mot
de passe ne déconnecte personne : le cookie reste valable jusqu'à sa péremption.
Pour tout invalider d'un coup, supprime `conversations/_session.json` et
relance.
