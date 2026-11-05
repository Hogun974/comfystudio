# Sécurité

## Signaler une faille

**Pas d'issue publique.** Une issue est visible de tous dès la seconde où elle
est ouverte, y compris de quelqu'un qui cherchait justement ce détail.

Passe par le signalement privé de GitHub :

> onglet **Security** du dépôt → **Report a vulnerability**
>
> <https://github.com/Hogun974/comfystudio/security/advisories/new>

Le fil est privé entre toi et le mainteneur jusqu'à publication.

Ce qui aide, dans l'ordre : la version, ce qu'un attaquant obtient,
et de quoi il a besoin au départ — être sur le même réseau, avoir un compte,
avoir déjà le jeton d'administration. Un exploit minimal vaut mieux qu'une
longue description.

La version, le studio la donne lui-même : elle est écrite au démarrage dans la
console et en haut de `/admin`. Recopie-la telle quelle, **`inconnue` comprise**
— c'est une réponse, elle dit que l'installation ne vient pas d'un clone git et
n'a pas été construite avec son identifiant. Ne va pas la deviner : un numéro
inventé coûte plus cher qu'une case vide.

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
neuve —, les routes des machines à agent (`/api/noeud/*`, authentifiées par
leur jeton), les routes des programmes (`/api/v1/*`, `/mcp` et la porte
compatible OpenAI `/openai/v1/*`), qui exigent
elles-mêmes une **clé d'accès** et répondent un 401 qu'un programme sait lire
(voir [plus bas](#les-clés-daccès-des-programmes)) — dont `/api/v1/lien/*`, qui
se lit sans en-tête parce que le lien est lui-même une **capacité signée**, et
`/api/v1/openapi.json`, la description de l'API, sans rien de propre à
l'installation que son adresse —, et une lecture sans effet ni secret :
`/api/textes`, le dictionnaire de la page, sans quoi l'écran de connexion
resterait français ; et le manifeste du studio installable
(`/manifest.webmanifest`) avec ses cinq icônes (`/icones/appli-*.png`), en
adresses exactes et non en préfixe, que le navigateur demande **sans cookie** —
un nom, trois couleurs, un dessin. Aucun service worker n'est enregistré : un
cache d'origine partagerait ce qu'un compte a vu avec le suivant sur le même
appareil.
(`/api/fournisseurs`, ouverte elle aussi, disait à un inconnu quelles modalités
partaient chez un tiers ; aucune page ne la lisait, elle a été retirée le
6 septembre 2026.)

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

- **Pas une session ouverte avant, tant qu'on ne touche à rien.** Le cookie
  `studio_compte` reste valable jusqu'à sa péremption — mais armer, désarmer
  ou changer de mot de passe ferme désormais toutes les sessions du compte.
  Voir « la révocation » ci-dessous.
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

Le cookie `studio_compte` contient `nom.péremption.génération.signature`, où
la signature est un **HMAC-SHA256 tronqué à 32 caractères hexadécimaux**. Le
serveur ne retient rien : une session survit à un redémarrage, ce qui compte
ici. La péremption est d'un mois. La *génération* est un compteur porté par le
compte ; un jeton dont la génération n'est plus celle du compte ne désigne
plus personne.

Le cookie `studio_admin` de la console n'est **plus le jeton d'administration
lui-même** : c'est `péremption.signature`, signé par ce jeton et valable sept
jours. Un navigateur qui fuit livre une session qui meurt, pas le secret qui
désarme le second facteur d'autrui.

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
- **La révocation passe par la génération.** Se déconnecter efface le cookie
  du navigateur, et lui seul : le jeton reste valide ailleurs jusqu'à sa
  péremption — sortir sur le téléphone ne ferme pas l'ordinateur du salon.
  Changer de mot de passe, armer ou désarmer le second facteur incrémentent la
  génération du compte, et **toutes** ses sessions d'avant tombent, sur tous
  les appareils : c'est le geste de qui croit son cookie volé. Supprimer un
  compte invalide aussi ses jetons (le nom n'est plus reconnu). Pour tout
  invalider d'un coup, supprimer `conversations/_session.json` : un nouveau
  secret est tiré au démarrage suivant, et tout le monde se reconnecte.
- **Toute réponse porte `X-Frame-Options: DENY`, `Referrer-Policy:
  no-referrer` et `X-Content-Type-Options: nosniff`.** Pas de
  `Content-Security-Policy` : les pages tiennent leur script en ligne, et une
  CSP qui l'autorise ne protège de rien.
- **Un corps JSON est borné à 4 Mo** (`CORPS_MAX`), routes sans session
  comprises. Les dépôts de fichiers ne passent pas par là : `/api/televerser`
  et `/api/noeud/fichier` lisent le flux eux-mêmes et se bornent seuls — par
  fichier, et en cumulé par travail pour les machines à agent.
- **Une machine à agent ne dépose que sous un travail qui lui a été confié et
  qui court encore.** Un dépôt sous le travail d'une autre machine rend 403,
  sous un travail fini 409, sous un identifiant inconnu 404 ; un nom déjà
  livré n'est recouvert que par le même travail, jamais par un autre — un
  rendu montré ne change plus de contenu après coup.

### Les secrets sont en clair sur le disque de l'hôte

Dans `conversations/`, en JSON lisible :

| Fichier | Contenu |
|---|---|
| `_cles.json` | **les clés d'API des fournisseurs, en clair** (Anthropic, OpenAI, Mistral, Google, Mammouth, Meshy) |
| `_admin.json` | le jeton d'administration, en clair |
| `_session.json` | le secret qui signe les sessions — et, dérivé de lui par HMAC, celui des liens signés des programmes |
| `_noeuds.json` | les jetons des machines à agent, en clair |
| `_comptes.json` | les empreintes scrypt et leurs sels — et **les secrets TOTP en clair**, qui ne peuvent pas être empreints (il faut les relire pour calculer le code). Les codes de secours, eux, sont empreints. |
| `_acces.json` | les clés d'accès des programmes : **leurs empreintes sha256**, jamais les clés — et **les secrets de rappel en clair**, qu'il faut relire pour signer chaque rappel. Qui lit ce fichier peut forger un rappel ; il ne peut pas, avec, se présenter au studio. |
| `_rappels.json` | les rappels en cours de livraison, le temps de leurs essais : **leurs adresses**, dont celle d'un webhook n8n porte un identifiant qui sert de secret. Vidé à chaque livraison finie ; il ne garde que ce qu'un arrêt a interrompu. `0600`. |
| `_idempotence.json` | les `Idempotency-Key` des programmes et le rendu que chacune désigne, 24 heures. Pas un secret — un identifiant d'exécution n8n, d'ordinaire — mais il dit quels workflows ont tourné et quand. `0600`. |
| `*.json` | les conversations : demandes, prompts, chemins des images |

Il n'y a **aucun chiffrement au repos**, et il n'y a rien pour en faire un :
le studio doit pouvoir se relancer tout seul, sans personne pour taper une
phrase de passe. `_cles.json`, `_comptes.json`, `_session.json` et `_acces.json`
sont écrits en `0600` — ce qui n'a d'effet que sur POSIX, et aucun sur Windows.

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

### Les clés d'accès des programmes

**Une voie d'entrée de plus, et la plus étroite.** Un workflow n8n, un
assistant IA par MCP ou un script présentent une clé d'accès — `cs_` + 8 hex
(l'identifiant, public) + 43 caractères tirés par `secrets` (256 bits). Le
détail d'usage est dans [Piloter le studio par
programme](docs/piloter-par-programme.md) ; voici ce qu'elle ouvre et ce
qu'elle n'ouvre pas.

- **Créée par son propriétaire seul, avec son mot de passe *et* son code** si le
  second facteur est armé, par la même porte et le même compteur d'essais que
  le changement de mot de passe : une clé contourne le second facteur pour
  toujours, elle ne doit pas naître d'un onglet resté ouvert ni d'un mot de
  passe volé seul. L'administrateur peut révoquer, pas créer. La clé n'est
  montrée qu'une fois (`Cache-Control: no-store`) ; le studio n'en garde que
  l'**empreinte sha256**. Pas scrypt, et ce n'est pas un oubli : scrypt protège
  un mot de passe qu'un dictionnaire devine, une clé de 256 bits n'en a pas — et
  un scrypt par requête donnerait à n'importe qui un moyen de geler le studio en
  envoyant des clés fausses à la chaîne.
- **Comparée en temps constant, et sans dire si l'identifiant existe** :
  l'empreinte est calculée et comparée même quand l'identifiant ne désigne
  aucune clé, pour que le chronomètre ne sépare pas « inconnue » de « fausse ».
- **Seulement sur `/api/v1/*`, `/mcp` et `/openai/v1/*`.** Présentée ailleurs,
  elle est refusée en 403 plutôt qu'ignorée. Elle ne vaut **jamais administration** —
  `admin_ok()` et `est_admin()` la refusent, même posée sur le compte `admin` —
  et ne voit que les rendus qu'**elle** a demandés : ni la médiathèque de son
  compte, ni les rendus d'une autre de ses clés. Réciproquement, une session de
  navigateur ne suffit pas sur `/api/v1/*` : une page piégée ne peut pas y
  lancer de rendu avec le cookie de son visiteur.
- **Seulement dans `Authorization: Bearer cs_…`** — jamais dans un cookie (il
  partirait tout seul depuis n'importe quel site), jamais dans l'adresse (elle
  finit dans les journaux). Un en-tête ne se pose pas depuis un autre site sans
  une requête préliminaire CORS que le studio n'approuve jamais.
- **Éteinte par la génération du compte** : changer de mot de passe, armer ou
  désarmer le second facteur éteint toutes les clés du compte, comme ses
  sessions. Supprimer le compte les efface.
- **Une date de fin, si l'on veut** (`expire_jours`, un an au plus) : passée,
  la clé est refusée en `cle_expiree` — le secret vérifié d'abord, pour ne rien
  apprendre à qui ne l'a pas — et ses liens signés, ses rappels et ses outils
  MCP meurent avec elle, même pendant une attente en cours.
- **Renouvelée sans coupure, ou coupée net.** Renouveler change le secret sous
  le même identifiant, par la porte de la création (mot de passe et code). Par
  défaut, l'**ancien secret vaut encore 24 heures** : c'est une fenêtre
  assumée, pour qu'un secret simplement *vu* se change sans casser le workflow.
  Pour un secret **volé**, la case « tout de suite » (`tout_de_suite: true`)
  le tue à la réponse, avec celui d'un renouvellement précédent. Une seule
  empreinte d'avance est gardée, effacée du fichier une fois sa grace passée ;
  une clé expirée ou éteinte ne se renouvelle pas. Pour une fuite avérée, la
  révocation reste le geste le plus sûr : elle ne demande que la session.
- **Bornée à ce qu'elle sert, si l'on veut** (`operations`) : une clé de
  détourage volée ne lance pas de vidéo. Refus en 403 dès l'entrée quand le
  moteur est imposé ; sinon juste après l'analyse, avant l'enrichissement par
  le modèle de langage et toute minute de carte. Un type de moteur sans famille connue
  est **fermé** à une clé restreinte, et une liste abîmée sur le disque rend
  le fichier des clés illisible plutôt que de se lire comme « tout ». Vide, la
  liste veut dire tout : c'est le défaut. Une image jointe à un moteur d'image
  du nuage compte comme une retouche — le fournisseur la modifie — et l'image
  d'une clé sans `retouche` ne part jamais chez lui.
- **Vérifiée avant d'être freinée** : une bonne clé passe toujours. Après trois
  secrets faux pour une même clé depuis une adresse, l'attente double (1 s, 2,
  4… plafonnée à 30), dans une **table à part** de celle des mots de passe — des
  clés au hasard ne peuvent pas en chasser les compteurs de connexion. Une clé
  inconnue ou révoquée n'inscrit rien : elle n'a pas de secret à deviner. Le
  journal écrit l'adresse, l'identifiant public et le nombre, **jamais la
  clé**. La table vit en mémoire, comme l'autre.
- **Bornée** : vingt clés par compte, `en_file` rendus en cours à la fois (4 par
  défaut, 20 au plus, variantes comprises), `par_jour` facultatif, compté sur
  le disque, variantes comprises, et `par_jour_familles` pour borner une
  famille à part (« 5 vidéos par jour ») — une clé volée ne prend pas la carte
  pour la nuit ; huit attentes ouvertes à la fois, qui
  s'arrêtent dès que la clé est révoquée ; cinq cents conversations ouvertes.
- **Le type d'une image envoyée en base64 vient d'une liste** (`png`, `jpg`,
  `webp`), jamais du client : il devient l'extension du fichier écrit, et un
  type comme `png\..\..\cible.png` écrivait — puis effaçait — un fichier hors
  du dossier d'entrée sous Windows (revue de sécurité du 4 novembre 2026).
- **Sans nuage par défaut**, et jusqu'à l'analyse : une demande d'une clé sans
  nuage n'appelle pas non plus le modèle de langage distant. Le contenu adulte
  ne sort jamais, le garde-fou des mineurs passe **avant la file**, le plafond
  du nuage du compte vaut pour ses clés.

**Les liens signés** (`/api/v1/lien/*`) se lisent sans en-tête : le jeton
porte la clé, le rendu, le fichier et une date de fin à 24 h, scellés par
HMAC-SHA256 sous un secret **dérivé** du secret de session — pas un fichier de
plus à protéger, et il ne peut pas servir à forger une session, ni l'inverse.
Un lien meurt **avec sa clé** — révoquée, ou seulement éteinte par un
changement de mot de passe ou de second facteur — et à sa date. La fiche d'une
clé éteinte existe encore (la liste la montre éteinte), et c'est pourquoi le
service du lien vérifie la génération du compte, pas seulement l'existence de
la fiche ; un rappel n'est plus signé en son nom non plus. Il est servi en
`Cache-Control: private, no-store`.

**Les rappels** sont la seule requête que le studio émet vers une adresse
fournie par un programme, et c'est la porte d'une **requête forgée côté
serveur** sur un réseau de maison. Elle est fermée ainsi :

- l'hôte de l'URL doit figurer dans une **liste déclarée à la création de la
  clé**, avec le mot de passe — qui vole la clé ne peut pas l'étendre ; liste
  vide, aucun rappel ;
- une entrée **avec port** ne vaut que pour ce port ; **sans port**, que pour
  le port par défaut du schéma (80, 443). Elle valait pour tous les ports :
  déclarer la machine de son n8n ouvrait aussi son ComfyUI ;
- l'issue d'une livraison va dans le journal du studio, **pas** dans le fil du
  rendu que la clé relit — sinon le rappel devenait une sonde de ports ;
- la comparaison est textuelle, sans résolution de nom : `127.1` ou
  `2130706433` ne correspondent à rien et échouent fermés ; un nom déclaré qui
  pointe ailleurs est le choix de celui qui l'a déclaré ;
- `http` et `https` seulement, pas d'identifiants dans l'URL, aucun caractère sur
  lequel deux lecteurs d'URL divergent (barre inverse, espace, contrôle) ;
- **aucune redirection suivie** ;
- le corps est signé (HMAC-SHA256, horodatage compris, format de Stripe) avec le
  secret de rappel de la clé, pour que le récepteur prouve que l'événement vient
  du studio. Le journal ne nomme que l'hôte : une URL de webhook porte souvent
  un identifiant qui sert de secret.

Le studio ne va **jamais** chercher une image à une adresse donnée par un
programme : ce serait la même requête forgée, par une autre porte.

**La porte compatible OpenAI** (`/openai/v1/images/generations`,
`/openai/v1/images/edits`, `/openai/v1/models`) existe pour qu'Open WebUI,
LibreChat ou un SDK openai se branchent avec une clé du studio. Ce n'est pas une
voie de plus pour la clé, c'est **la même** sous un autre format : même
middleware d'identité, même frein, même `lancer_pour_programme` (plafonds,
nuage, garde-fou des mineurs avant la file, validation de la page), même
registre d'idempotence. Ce qu'elle ajoute, et comment c'est tenu :

- **La famille de la route est exigée, puis imposée** : une clé sans « image »
  est refusée en 403 sur `generations`, sans « retouche » sur `edits` ; et la
  tâche lancée porte une liste d'opérations **réduite à cette famille**, même
  pour une clé qui permet tout — une demande que l'analyse lit comme une vidéo
  est arrêtée avant toute minute de carte, au lieu d'occuper une machine huit
  minutes pour un client qui attend une image.
- **Un formulaire multipart borné** (`edits`) : il se lit en flux, hors de
  `client_max_size` ; l'image est coupée au plafond de sa famille (32 Mio)
  pendant la lecture, un champ texte à 64 Kio, et le formulaire à 32 champs.
  Le type de l'image vient de la même liste fermée que le base64, jamais du
  nom de fichier tel quel ; le masque est lu et jeté.
- **Une attente synchrone bornée** (540 s), comptée dans les huit attentes par
  clé — et refusée en 429 **avant** de lancer quand elles sont prises, sinon le
  rendu partirait sans que personne n'en reçoive l'image.
- **Aucune trace dans les réponses** : une exception sous `/openai/v1/` rend un
  500 au format d'OpenAI avec une phrase fixe ; la trace reste dans le journal.
  Et `X-Should-Retry: false` sur tout 5xx : le SDK openai rejoue les 5xx de
  lui-même, et un rejeu après un lancement serait un second rendu facturé en
  temps de carte.
- Les images rendues en `url` sont les **liens signés** de toujours
  (`/api/v1/lien/*`), et meurent avec la clé.

**Ce que ça ne protège pas** : le transit — une clé passe en clair sur HTTP,
comme un cookie de session ; une clé volée, qui lance des rendus sur la carte
dans les limites de ses plafonds jusqu'à sa révocation ; l'hôte, qui lit les
secrets de rappel dans `_acces.json` ; et un rappel en `http://`, lisible en
route — la signature prouve l'origine, pas la confidentialité.

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
| Protégé | mots de passe (scrypt + sel), second facteur TOTP au choix de chacun, sessions (HMAC, révoquées par la génération du compte), cookie d'administration dérivé du jeton et non le jeton, cookies `HttpOnly` + `SameSite=Lax`, vérification de l'`Origin`, en-têtes anti-cadre et anti-devinette de type, jetons comparés en temps constant, clés d'API jamais renvoyées par l'API, secrets hors du dépôt, dépôts d'agent liés au travail confié, clés d'accès des programmes (empreintes sha256, créées avec mot de passe et second facteur, limitées à `/api/v1`, `/mcp` et `/openai/v1`, jamais administration, éteintes par la génération du compte, liens signés et rappels compris), rappels signés vers des hôtes déclarés seulement, sans redirection suivie |
| **Pas** protégé | le transit (HTTP simple, cookies sans `Secure`, clés d'accès comprises), les secrets au repos (JSON en clair, secrets TOTP et secrets de rappel compris), la déconnexion d'un seul appareil qui ne ferme pas les autres, l'hameçonnage en temps réel, l'hôte lui-même, la mise à jour automatique des agents (voir ci-dessous) |

### Ce qui reste ouvert : la mise à jour automatique des agents

Un agent compare à chaque annonce l'empreinte de son code à celle que le studio
annonce, télécharge `/api/noeud/agent` quand elles diffèrent, vérifie que c'est
du Python qui s'analyse, et se relance dessus. **Rien ne signe ce code.** Qui
tient le studio — ou le trajet réseau, en HTTP simple — tient donc toutes les
machines à agent, avec les droits de l'utilisateur qui les fait tourner. C'est
un choix : la mise à jour d'un parc à la main ne se fait pas, et un studio
compromis tient déjà les rendus, les fichiers et les clés. Deux parades
existent, désactivées par défaut : `--empreinte` (ou `AGENT_EMPREINTE`) épingle
l'agent sur une empreinte connue, `--sans-maj-auto` coupe tout. Une signature
par clé privée hors du studio serait la vraie réponse ; elle demanderait de
signer chaque version de l'agent à la main, et ce n'est pas tranché.

## Ce qui n'est pas une faille

- Que le studio ouvert au réseau avec `STUDIO_AUTH=libre` soit utilisable par
  tous : c'est écrit, et c'est le sens du réglage.
- Que l'administrateur voie les conversations : voir plus haut.
- Qu'un modèle génère un contenu qui déplaît. Le studio ne filtre pas, hormis la
  limite codée en dur.
- Une vulnérabilité de ComfyUI, d'Ollama ou de PyTorch : signale-la chez eux.
  Sauf, bien sûr, si c'est la façon dont le studio les appelle qui l'ouvre.
