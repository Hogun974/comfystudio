# Sécurité

## Signaler une faille

**Pas d'issue publique.** Une issue est visible de tous dès la seconde où elle
est ouverte, y compris de quelqu'un qui cherchait justement ce détail.

Passe par le signalement privé de GitHub :

> onglet **Security** du dépôt → **Report a vulnerability**
>
> <https://github.com/Hogun974/comfystudio/security/advisories/new>

Le fil est privé entre toi et le mainteneur jusqu'à publication.

Ce qui aide, dans l'ordre : la version (le commit), ce qu'un attaquant obtient,
et de quoi il a besoin au départ — être sur le même réseau, avoir un compte,
avoir déjà le jeton d'administration. Un exploit minimal vaut mieux qu'une
longue description.

Ce projet est tenu par une seule personne, sur son temps libre : compte en jours
plutôt qu'en heures. Il n'y a pas de programme de récompense.

**Versions suivies** : la branche principale, et elle seule. Il n'y a pas de
rétroportage — la correction sera un commit sur `main`.

## Ce que le studio protège, et ce qu'il ne protège pas

Rien de ce qui suit n'est une supposition : c'est ce que font `comptes.py` et
`serveur.py` aujourd'hui.

### Il n'y a aucun chiffrement en transit

Le studio écoute en **HTTP simple**. Il n'y a pas de `ssl_context`, pas de
certificat, pas de redirection : `web.run_app(app(), host=HOTE, port=PORT)`.

Conséquence directe : sur le trajet, **tout est lisible** — le mot de passe
envoyé au formulaire de connexion, le cookie de session, le jeton
d'administration, les demandes, les images. Les cookies sont posés `HttpOnly` et
`SameSite=Lax`, mais **sans l'attribut `Secure`**, puisqu'il n'y aurait rien
pour l'honorer.

C'est acceptable pour ce à quoi le studio est destiné : `127.0.0.1`, ou un
réseau local dont on répond. Ça ne l'est pas au-delà.

**Pour l'exposer sur Internet, mets-le derrière un reverse proxy** (Caddy, nginx,
Traefik) qui termine le TLS, et laisse le studio n'écouter que sur la boucle
locale. Le TLS n'est pas prévu dans le studio lui-même et ne le sera
probablement pas : un proxy le fait mieux, et le certificat n'a rien à faire
dans ce programme.

### Par défaut, il faut un compte

`STUDIO_AUTH` vaut `obligatoire` : sans session, aucune route qui fait ou montre
quelque chose ne répond. Restent ouvertes la page elle-même (sinon on ne
pourrait pas afficher le formulaire de connexion), les routes de session, et les
routes d'administration — qui vérifient elles-mêmes le jeton, et dont la
fermeture condamnerait le seul moyen d'entrer sur une installation neuve.

`STUDIO_AUTH=libre` rétablit l'ancien comportement : **plus aucune
authentification**, chaque navigateur reçoit un identifiant opaque et son espace
privé. Quiconque atteint le port peut alors générer, téléverser des images et
occuper le GPU. Ne le combine pas avec `STUDIO_HOTE=0.0.0.0` sur un réseau que
tu ne maîtrises pas.

Au premier démarrage sans compte, un compte `admin` est créé et son mot de passe
affiché une fois dans la console (ou fixé par `STUDIO_ADMIN_MDP`). Change-le.

### Les mots de passe ne sont pas conservés

Seulement une empreinte **scrypt** (`n=2**14`, `r=8`, `p=1`, 32 octets) avec un
**sel de 16 octets tiré au hasard par compte**, dans
`conversations/_comptes.json`. La vérification passe par `hmac.compare_digest`.
Longueur minimale imposée : 8 caractères — c'est peu, et c'est le seul contrôle.

Personne ne peut relire un mot de passe, pas même l'administrateur : il peut en
imposer un nouveau, pas consulter l'ancien. En cas de fuite du fichier, scrypt
rend le parcours d'un dictionnaire coûteux — il ne le rend pas impossible sur un
mot de passe faible.

**Ce qui existe** : après trois échecs, l'attente double à chaque essai
suivant (1 s, 2, 4, 8… plafonnée à 30), par couple compte + adresse. Un humain
qui se trompe deux fois ne s'en aperçoit pas ; une machine qui déroule un
dictionnaire y passe des années. Les rafales sont écrites dans le journal du
studio, seul endroit où son propriétaire les remarquera. Le compteur vit en
mémoire : le persister permettrait à un tiers de bloquer un compte à distance.

**Ce qui n'existe toujours pas** : aucun verrouillage définitif. Le freinage
ralentit, il n'arrête pas — et il vit en mémoire, donc un redémarrage le remet à
zéro. Si le studio est joignable au-delà de ta machine, mets une vraie
limitation dans le reverse proxy.

### Les sessions sont des jetons signés

Le cookie `studio_compte` contient `nom.péremption.signature`, où la signature
est un **HMAC-SHA256 tronqué à 32 caractères hexadécimaux**. Le serveur ne
retient rien : une session survit à un redémarrage, ce qui compte ici. La
péremption est d'un mois.

Deux choses à savoir :

- **Le secret de signature est propre aux sessions**, tiré au sort au premier
  démarrage et conservé dans `conversations/_session.json`. Il l'a longtemps
  été moins : c'était le jeton d'administration, si bien que l'obtenir
  permettait de **forger une session pour n'importe quel compte** sans jamais
  connaître un mot de passe. Administrer et s'authentifier sont deux rôles ;
  ils ont désormais deux secrets.
- **Contre le clic sur un site piégé**, deux garde-fous se cumulent :
  `SameSite=Lax` sur les cookies, et une vérification de l'en-tête `Origin`
  contre l'hôte réellement utilisé. `local(req)` seul n'aurait pas suffi : un
  formulaire posté depuis n'importe quel site part du navigateur de
  l'utilisateur, donc depuis `127.0.0.1`.

  Cette vérification est un **middleware** : toute requête autre que `GET`,
  `HEAD` ou `OPTIONS` y passe, y compris les routes d'administration. Ce document
  l'annonçait alors qu'elle ne couvrait que trois routes sur cinquante-trois — ni
  « générer », ni « téléverser », ni le changement de mot de passe. Elle a été
  écrite au lieu d'être promise. Les machines à agent en sont exclues : pas de
  navigateur, pas d'`Origin`, une authentification par jeton.
- **Il n'y a pas de révocation.** Se déconnecter efface le cookie du navigateur ;
  le jeton reste valide jusqu'à sa péremption. Supprimer un compte suffit à
  invalider ses jetons (le nom n'est plus reconnu), changer son mot de passe non.
  Pour tout invalider d'un coup, supprimer `conversations/_session.json` : un
  nouveau secret est tiré au démarrage suivant, et tout le monde se reconnecte.

### Les secrets sont en clair sur le disque de l'hôte

Dans `conversations/`, en JSON lisible :

| Fichier | Contenu |
|---|---|
| `_cles.json` | **les clés d'API des fournisseurs, en clair** (Anthropic, OpenAI, Mistral, Google, Mammouth, Meshy) |
| `_admin.json` | le jeton d'administration, en clair — et donc le secret de signature des sessions |
| `_noeuds.json` | les jetons des machines à agent, en clair |
| `_comptes.json` | les empreintes scrypt et leurs sels |
| `*.json` | les conversations : demandes, prompts, chemins des images |

Il n'y a **aucun chiffrement au repos**, et il n'y a rien pour en faire un :
le studio doit pouvoir se relancer tout seul, sans personne pour taper une
phrase de passe. `_cles.json` et `_comptes.json` sont écrits en `0600` — ce qui
n'a d'effet que sur POSIX, et aucun sur Windows.

Ce que ça veut dire concrètement : **qui lit le disque de l'hôte a les clés
d'API**, et peut dépenser sur les comptes correspondants. Traite ce dossier
comme un trousseau. Il est exclu du dépôt par `.gitignore`, et il doit le
rester — une sauvegarde de conversations s'est déjà retrouvée dans un commit
avec de vraies clés dedans, ce qui a valu les règles `*_sauvegarde*/` du
`.gitignore`. Si ça t'arrive, **révoque les clés**, ne te contente pas de
réécrire l'historique.

L'API d'administration, elle, ne renvoie jamais une clé : seulement ses quatre
derniers caractères.

### Le serveur voit tout

Ce n'est pas une faille, c'est le modèle. Les espaces par navigateur ou par
compte isolent les utilisateurs **entre eux** ; ils n'isolent personne de
l'hôte. Les fichiers de `conversations/` sont en clair, la console journalise
chaque demande quel qu'en soit l'auteur, et `avis.jsonl` conserve les retours
avec la demande complète.

Un administrateur peut, depuis `/admin`, poser des clés d'API, créer et
supprimer des comptes, déclarer des machines et relancer l'entraînement. C'est
un rôle de confiance, sans cloisonnement interne.

### Les machines à agent

Une machine se présente avec un jeton `token_urlsafe(24)`, comparé en
`compare_digest`. **Le studio n'appelle jamais la machine** : c'est elle qui
vient chercher le travail, elle n'ouvre aucun port. En sens inverse, un porteur
de jeton de nœud peut réclamer du travail et déposer des fichiers de sortie chez
le studio. Le jeton n'est affiché qu'une fois à la création, et conservé en clair
dans `_noeuds.json`.

Une machine est ajoutée depuis `/admin`, qui délivre son jeton — affiché une
seule fois. **Il n'y a pas d'autre appairage.** Ce document a longtemps décrit un
code à six chiffres valable cinq minutes : il n'a jamais existé. La variable qui
devait le porter était déclarée et référencée nulle part, et c'est tout ce qu'il
y a jamais eu. Une politique de sécurité qui promet un contrôle inexistant est
pire que le silence.

Ce qu'une machine à agent peut faire chez le studio est borné : elle dépose des
fichiers dont **l'extension est filtrée** — images, vidéos, sons, maillages, rien
d'autre, parce que le studio les sert ensuite sur sa propre origine — et **chaque
dépôt est plafonné à 2 Go**.

### Ce que le studio ne filtre pas

Le studio ne censure pas les demandes. **Une seule limite est codée en dur** :
le contenu sexuel impliquant des mineurs est refusé, avant l'aiguillage et après
la réécriture du prompt.

Une règle voisine, qui est de confidentialité : une demande à caractère adulte
**ne sort jamais de la machine**, ni vers un LLM distant ni vers un générateur
d'images distant, quel que soit le réglage de l'interface et même si un moteur
distant est imposé. C'est vérifié dans le code avant l'appel sortant, et annoncé
dans le journal de la tâche.

### Récapitulatif

| | |
|---|---|
| Protégé | mots de passe (scrypt + sel), sessions (HMAC), cookies `HttpOnly` + `SameSite=Lax`, vérification de l'`Origin`, jetons comparés en temps constant, clés d'API jamais renvoyées par l'API, secrets hors du dépôt |
| **Pas** protégé | le transit (HTTP simple, cookies sans `Secure`), les secrets au repos (JSON en clair), la révocation de session, l'hôte lui-même |

## Ce qui n'est pas une faille

- Que le studio ouvert au réseau avec `STUDIO_AUTH=libre` soit utilisable par
  tous : c'est écrit, et c'est le sens du réglage.
- Que l'administrateur voie les conversations : voir plus haut.
- Qu'un modèle génère un contenu qui déplaît. Le studio ne filtre pas, hormis la
  limite codée en dur.
- Une vulnérabilité de ComfyUI, d'Ollama ou de PyTorch : signale-la chez eux.
  Sauf, bien sûr, si c'est la façon dont le studio les appelle qui l'ouvre.
