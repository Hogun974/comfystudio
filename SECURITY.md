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
pourrait pas afficher le formulaire de connexion), les routes de session, les
routes d'administration et `/demarrage` — qui vérifient elles-mêmes le jeton, et
dont la fermeture condamnerait le seul moyen d'entrer sur une installation
neuve.

**`/api/demarrage` est de celles-là, et c'est la plus bavarde.** Elle sert la
liste de contrôle de la [première mise en route](docs/premiere-mise-en-route.md) :
qu'un compte porte encore le mot de passe tiré au premier démarrage, qu'aucune
carte ne répond, que `STUDIO_AUTH` vaut `libre`. Elle est libre de session parce
qu'il faut pouvoir amorcer une installation neuve, et **gardée par `admin_ok()`**
— compte administrateur connecté, ou jeton d'administration. Servie sans cette
garde, elle serait la meilleure page de reconnaissance qu'un studio puisse
offrir ; `banc_page.py` relève les deux moitiés ensemble, la porte ouverte et le
verrou derrière. Pour la même raison, `/api/compte` — qui se lit sans session —
ne dit `demarrage` qu'à un administrateur.

`STUDIO_AUTH=libre` rétablit l'ancien comportement : **plus aucune
authentification**, chaque navigateur reçoit un identifiant opaque et son espace
privé. Quiconque atteint le port peut alors générer, téléverser des images et
occuper le GPU. Ne le combine pas avec `STUDIO_HOTE=0.0.0.0` sur un réseau que
tu ne maîtrises pas.

Au premier démarrage sans compte, un compte `admin` est créé et son mot de passe
affiché une fois dans la console (ou fixé par `STUDIO_ADMIN_MDP`). Change-le —
et **le studio le mesure maintenant** : un mot de passe qu'il a tiré lui-même
porte un drapeau `origine`, effacé par `changer_mdp()` et par lui seul, et
`/demarrage` en fait une ligne qui rougit tant que personne n'y a touché. Le
drapeau ne dit rien du secret ; garder le mot de passe pour pouvoir comparer
reviendrait à le conserver en clair. Un mot de passe posé par
`STUDIO_ADMIN_MDP` n'est pas marqué : c'est une décision de celui qui héberge.

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

### Le second facteur (TOTP), s'il est armé

**Il n'est pas armé par défaut, et il ne l'est jamais pour quelqu'un d'autre.**
Chacun l'arme sur son propre compte, depuis le bouton « second facteur » du
bandeau. L'administrateur ne peut pas l'armer à la place d'un autre — il
faudrait son téléphone.

Un code à six chiffres qui change toutes les trente secondes, calculé hors ligne
(RFC 6238, HMAC-SHA1, aucune dépendance, aucun service tiers). L'implémentation
est mesurée contre **les vecteurs de test publiés par la RFC**, pas seulement
contre elle-même.

**Ce que ça protège** : une fuite du mot de passe seul. Un mot de passe volé,
deviné, réutilisé d'un autre site, ou lu dans un journal ne suffit plus à entrer.

**Ce que ça ne protège pas** — et c'est plus long que la liste d'au-dessus :

- **Pas une session déjà ouverte.** Le cookie `studio_compte` reste valable
  jusqu'à sa péremption ; armer, désarmer ou changer de mot de passe ne le
  révoque pas. Voir « il n'y a pas de révocation » ci-dessous.
- **Pas l'hôte.** Le secret est en clair sur le disque (voir plus bas) : qui lit
  `conversations/_comptes.json` calcule les codes lui-même.
- **Pas l'hameçonnage en temps réel.** Un code recopié dans une page qui imite
  le studio est utilisable pendant sa fenêtre de 90 s. TOTP ne défend pas
  contre ça — seule une clef matérielle liée à l'origine le ferait.
- **Pas le transit.** Sans HTTPS, le code passe en clair comme le mot de passe.
- **Pas le jeton d'administration.** `/admin` s'ouvre avec `STUDIO_ADMIN`, sans
  second facteur : c'est le seul moyen d'entrer sur une installation neuve, et
  le fermer condamnerait l'amorçage.

**Le freinage est le même que celui de la porte d'entrée, et c'est délibéré.**
Six chiffres font un million de possibilités, ce qui paraît beaucoup — mais la
fenêtre de vérification est de 90 s, donc trois codes valent à chaque instant,
et un code de secours ne pèse qu'une quarantaine de bits. Sans limite, on les
essaie. Le code se saisit donc **sur la même route que le mot de passe**
(`/api/compte/entrer`), sous le **même compteur**, indexé par le couple
`(compte, adresse)` : après trois échecs, l'attente double — 1 s, 2, 4, 8…
plafonnée à 30. Une route séparée pour le code aurait eu son propre compteur, ou
pas de compteur du tout, et il aurait suffi de frapper à l'autre porte.

Le refus « il manque le code » ne compte **ni comme un échec ni comme une
réussite** : le compter freinerait la connexion normale d'un compte armé, qui
fait deux appels à chaque fois ; le laisser remettre le compteur à zéro
permettrait d'effacer l'ardoise entre deux essais de code.

Les cinq routes du second facteur passent toutes par la même fonction, et
`banc_comptes.py` lit `serveur.py` pour l'exiger : **un seul site d'appel** à la
vérification, dans une porte qui freine **avant** de vérifier, et aucune route
qui vérifie un secret à côté d'elle.

**Le secret est en clair dans `_comptes.json`, et il ne peut pas en être
autrement.** Ce n'est pas un mot de passe : il faut le relire pour recalculer le
code attendu, donc il ne peut pas être gardé sous forme d'empreinte. C'est vrai
de toutes les implémentations de TOTP. Le fichier est écrit en `0600` (sans
effet sur Windows) et le secret ne sort jamais par une route, sauf la réponse de
l'enrôlement qui vient de le tirer. Les **codes de secours**, eux, se comparent :
ils sont empreints avec scrypt, exactement comme des mots de passe, et ne sont
jamais relisibles.

**Le QR code de l'enrôlement *est* le secret.** Depuis le 3 septembre 2026, la
réponse d'enrôlement porte aussi la matrice d'un QR code, calculée par
`qr.py` — du Python nu, aucune dépendance ajoutée, rien qui parte sur le réseau,
et le calcul se fait **sur le serveur du studio**, jamais chez un service
d'images tiers. Deux conséquences à connaître :

- Il encode exactement l'URI `otpauth://`, donc **le secret en clair sous une
  autre forme**. Une photo de l'écran, une capture partagée, un écran filmé par
  une caméra de bureau valent le secret lui-même. C'est aussi vrai du secret
  écrit en toutes lettres à côté ; le QR ne change pas la nature du risque, il
  le rend simplement plus facile à emporter.
- Il n'ajoute **aucune surface d'attaque côté serveur** : `qr.py` ne lit rien,
  n'écrit rien, ne prend que du texte et rend une grille de booléens. La page,
  elle, n'accepte de la matrice que des « 0 » et des « 1 » en carré avant de la
  dessiner, et retombe sur le secret écrit si elle reçoit autre chose.

Un encodeur QR écrit à la main peut être parfaitement cohérent avec lui-même et
produire une image qu'aucun téléphone ne lit ; `banc_qr.py` le compare donc
**module par module** à quatre matrices produites par une implémentation
indépendante (segno), et recalcule les syndromes de Reed-Solomon avec sa propre
arithmétique. Même raisonnement que les vecteurs de la RFC 6238 pour le TOTP.

**Dix codes de secours, à usage unique**, affichés **une seule fois**. Un second
facteur sans porte de sortie enferme son propriétaire : téléphone perdu,
remplacé ou réinitialisé, et le compte serait mort — personne ne pourrait le
rouvrir, pas même l'administrateur, puisque c'est justement ce qu'on vient
d'empêcher. Voir `docs/comptes.md` pour la procédure quand ils sont épuisés
eux aussi.

**Désarmer et régénérer exigent le mot de passe courant *et* un code**, c'est-à-dire
la même preuve qu'à la porte d'entrée. Sans cela, un onglet laissé ouvert sur une
machine partagée suffirait à retirer le second facteur, ce qui le viderait de son
sens. **Préparer un enrôlement l'exige aussi**, pour la raison symétrique : sans
mot de passe, quelqu'un qui trouve un onglet ouvert armerait le facteur avec
*son* téléphone, garderait l'accès et enfermerait le propriétaire dehors.

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
| `_comptes.json` | les empreintes scrypt et leurs sels — et **les secrets TOTP en clair**, qui ne peuvent pas être empreints (il faut les relire pour calculer le code). Les codes de secours, eux, sont empreints. |
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

**L'agent est du code téléchargé puis exécuté, en HTTP simple.** `noeud.sh`,
`noeud.bat`, `maj_noeud.sh`, `maj_noeud.bat` et `agent_noeud.py --maj` vont
chercher `agent_noeud.py` sur `/api/noeud/agent`, une route délibérément
ouverte — c'est ce qui permet d'installer une machine neuve qui n'a encore
aucun jeton. Conséquence : **qui peut s'intercaler sur le réseau choisit le code
qui tournera sur chaque machine à agent**, et l'obtient sur toutes à la fois à
la prochaine mise à jour. C'est le même réseau que celui du reste de ce
document : on n'en répond pas, et il n'y a rien dans le studio pour le
compenser.

Les scripts refusent d'installer ce qui n'est pas du Python analysable, et
affichent le sha256 de ce qu'ils ont posé. On peut leur imposer l'empreinte
attendue — `--empreinte`, troisième argument, ou `AGENT_EMPREINTE` — auquel cas
rien d'autre ne sera installé. **Cette empreinte ne vaut que relevée ailleurs
que sur ce lien HTTP** : `sha256sum agent_noeud.py` sur l'hôte du studio, par
SSH. Servie par le studio, elle serait réécrite par le même attaquant que le
fichier, et ne protégerait de rien. Contre un réseau hostile, la seule vraie
réponse reste le reverse proxy TLS de plus haut, et `--studio https://…`.

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
| Protégé | mots de passe (scrypt + sel), second facteur TOTP au choix de chacun, sessions (HMAC), cookies `HttpOnly` + `SameSite=Lax`, vérification de l'`Origin`, jetons comparés en temps constant, clés d'API jamais renvoyées par l'API, secrets hors du dépôt |
| **Pas** protégé | le transit (HTTP simple, cookies sans `Secure`), les secrets au repos (JSON en clair, secrets TOTP compris), la révocation de session, l'hameçonnage en temps réel, l'hôte lui-même |

## Ce qui n'est pas une faille

- Que le studio ouvert au réseau avec `STUDIO_AUTH=libre` soit utilisable par
  tous : c'est écrit, et c'est le sens du réglage.
- Que l'administrateur voie les conversations : voir plus haut.
- Qu'un modèle génère un contenu qui déplaît. Le studio ne filtre pas, hormis la
  limite codée en dur.
- Une vulnérabilité de ComfyUI, d'Ollama ou de PyTorch : signale-la chez eux.
  Sauf, bien sûr, si c'est la façon dont le studio les appelle qui l'ouvre.
