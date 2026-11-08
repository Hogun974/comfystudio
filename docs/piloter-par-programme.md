# Piloter le studio par programme

**Un programme peut demander un rendu au studio sans navigateur** — un workflow
n8n, un assistant IA branché par MCP, un script `curl`. Il présente une **clé
d'accès** à lui, reçoit un identifiant, suit le rendu, télécharge les fichiers,
et peut être prévenu par un **rappel signé** quand c'est fini. Il ne voit que
les rendus qu'il a demandés, et jamais l'administration.

## Deux clés qui ne sont pas les mêmes

C'est la confusion la plus probable, alors tout de suite :

| | **Clé d'accès** (cette page) | **Clé d'API** ([Clés d'API](cles-api.md)) |
|---|---|---|
| Qui la présente | un programme, **au studio** | le studio, **au nuage** (Anthropic, Google, Meshy…) |
| Forme | `cs_92d11256_…` (préfixe `cs_`, 8 hex, 43 caractères) | celle du fournisseur |
| Qui la crée | chaque compte, pour lui-même | l'administrateur, dans `/admin` |
| Fichier | `conversations/_acces.json` | `conversations/_cles.json` |

Une clé d'accès ne donne aucun droit sur les clés d'API, et une clé d'API ne
sert à rien sur `/api/v1`. Les deux mots restent séparés dans tout le dépôt —
code, messages, pages — parce qu'un seul mot pour deux secrets finit toujours
par en faire coller un à la place de l'autre.

## Créer une clé

Dans la page, le bouton **« clés d'accès »** de la zone de compte, à côté de
« second facteur ». Il faut :

- un **nom** (40 caractères au plus) : « n8n maison », « agent du salon ». C'est
  lui qu'on relit dans la liste le jour où il faut en révoquer une ;
- **ton mot de passe, et ton code à six chiffres si ton second facteur est
  armé.** Une clé contourne le second facteur pour toujours : elle ne doit pas
  pouvoir naître d'un onglet resté ouvert ni d'un mot de passe volé seul. C'est
  la même porte, et le même compteur d'essais, que pour changer de mot de passe ;
- facultatif : les **hôtes de rappel** (voir [plus bas](#pourquoi-les-hôtes-sont-déclarés)),
  le **droit au nuage** (non par défaut), les **plafonds** `en_file` (de 1 à 20,
  4 par défaut) et `par_jour` (de 0 à 10 000, 0 pour « sans plafond »), la
  **durée de vie** (voir [plus bas](#une-date-de-fin)), et **ce que la clé
  peut faire** (voir [plus bas](#ce-que-la-clé-peut-faire)).

**La clé et le secret de rappel ne s'affichent qu'une fois.** Le studio ne
garde de la clé qu'une empreinte sha256 : perdue, elle se révoque et se refait,
elle ne se relit pas. La réponse porte `Cache-Control: no-store`, pour qu'aucun
cache ne la garde à ta place.

Vingt clés au plus par compte. Personne n'en branche vingt ; la borne existe
pour qu'un script qui en crée une à chaque lancement — l'erreur classique —
bute sur un refus nommé au lieu de faire grossir le fichier sans fin.

La même chose sans la page, avec une session ouverte (le cookie de connexion) :

```sh
curl -s "$STUDIO/api/compte/acces" -b "studio_compte=…" \
  -H "Content-Type: application/json" \
  -d '{"nom": "n8n maison", "mdp": "…", "code": "123456",
       "hotes": ["n8n.maison:5678"], "en_file": 4}'
```

```json
{"cle": "cs_92d11256_zjtwJKMBYwqvQ7gAZt0Wa34PXhlK5_0ibWF7LdPd4RY",
 "secret_rappel": "yvbokXFRNBNucgMlg90WW6G5i7MKbDJzm8bWuUxo5TM",
 "fiche": {"id": "92d11256", "compte": "jordan", "nom": "n8n maison",
           "apercu": "cs_92d11256_…", "cree": 1793757278.8, "vu": null,
           "nuage": false, "hotes": ["n8n.maison:5678"], "en_file": 4,
           "par_jour": 0, "generation": 0, "expire": null,
           "ancienne_jusqu": null, "operations": []}}
```

`GET /api/compte/acces` liste les clés du compte, chacune avec `active` ;
`DELETE /api/compte/acces/{id}` en révoque une. Ces trois routes veulent une
**session**, jamais une clé : une clé qui listerait les clés en ferait
connaître l'existence à qui l'a volée.

### Une date de fin

Une clé vit **sans fin** par défaut : une clé qui meurt en silence au bout de
trois mois casse le workflow qu'elle servait, sans que personne ne regarde.
Mais la clé d'un essai, d'une démonstration, de l'assistant d'un invite n'a pas
à rester ouverte après. Le menu **durée de vie** propose 7, 30, 90 ou 365
jours ; sans la page, `"expire_jours"` prend tout entier de 0 (sans fin) à 365.

Passée sa date, la clé est refusée en **401 `cle_expiree`** — son propre code,
pour que tu en crées une autre au lieu de chercher une faute de frappe. Ses
essais ne comptent pas comme des secrets faux : un n8n qui insiste avec elle
ne se fait pas freiner. Comme une clé éteinte, **ses liens signés et ses
rappels meurent avec elle**, et la liste la montre `expiree: true`. La date se
lit dans `expire` (secondes depuis 1970, ou `null`) de la fiche, et dans
`GET /api/v1/moi` : un workflow peut prévenir avant l'échéance. Elle revient
aussi sur **chaque réponse** à cette clé, dans l'en-tête
`X-ComfyStudio-Cle-Expire` (RFC 3339) : le workflow, ou le proxy qui
journalise, la voit venir sans rien demander.

### Renouveler sans coupure

Tu crois le secret vu — collé dans un ticket, affiché sur un écran partagé ?
Le bouton **« renouveler »** de la liste lui donne un **secret neuf, sous le
même identifiant** : ses rendus, ses conversations, ses liens signés, ses
plafonds, sa date de fin et son **secret de rappel ne changent pas**. Seul le
secret d'accès change, et il ne s'affiche qu'une fois, comme à la création.

**L'ancien secret vaut encore 24 heures** — le temps d'ouvrir n8n et d'y coller
le neuf —, puis plus rien. La fiche le dit dans `ancienne_jusqu`. Un second
renouvellement pendant ce délai ferme aussitôt le premier secret : on n'en
garde qu'un d'avance. **Volé, et pas seulement vu ?** Coche « couper l'ancien
secret tout de suite » (`"tout_de_suite": true`) : il meurt à la réponse. Pour
une fuite avérée, révoquer reste le plus sûr — la session suffit. Renouveler demande **ton mot de passe** (et le code du
second facteur s'il est armé), comme la création : la réponse porte un secret
en clair. Une clé expirée, ou éteinte par un changement de mot de passe, ne se
renouvelle pas — sa fermeture était voulue ; crées-en une autre.

```sh
curl -s -X POST "$STUDIO/api/compte/acces/92d11256/renouveler" \
  -b "studio_compte=…" -H "Content-Type: application/json" \
  -d '{"mdp": "…", "code": "123456"}'
```

La liste du propriétaire dit aussi, pour chaque clé, ce qu'elle a **lancé
aujourd'hui** (`aujourdhui`) et ce qu'elle a **en cours** (`en_cours`) : où
elle en est de ses plafonds avant le 429 — et, pour chaque famille qui a son
[plafond du jour](#un-plafond-par-famille), ce qu'elle a lancé et ce qui reste
(`par_famille`).

Elle dit enfin ce qui est **arrivé** à la clé aujourd'hui, dans `suivi` :

```json
"suivi": {"refus": {"cle_file_pleine": 3, "cle_operation_interdite": 1},
          "refus_total": 4, "dernier_refus": 1793757278.8,
          "dernier_code": "cle_operation_interdite",
          "echecs": 0, "dernier_echec": null}
```

- `refus` : les refus du jour, **par code** — ceux de l'entrée (le 429 d'une
  file pleine, le 403 d'une opération fermée, un champ illisible…) et ceux qui
  tombent après l'analyse (`cle_operation_interdite`, `cle_plafond_famille`,
  `refus_mineurs` sur le
  prompt réécrit). Une machine muette ou une carte trop petite ne comptent
  pas : ce n'est pas la clé qui est refusée, c'est le studio qui manque.
- `echecs` : les requêtes du jour qui portaient **l'identifiant de cette clé
  avec un secret faux** — une clé mal recopiée, un ancien secret après sa
  grâce, ou une clé volée à moitié (l'identifiant est public : il est dans
  chaque lien signé). Le studio compte, il ne garde rien de ce qui a été
  essayé. Un chiffre qui monte sans que tu reconnaisses l'erreur : renouvelle
  la clé en coupant l'ancien secret. L'adresse d'où viennent les essais est
  dans le journal du studio (« secrets faux pour la clé … depuis … »).
- Les compteurs repartent à zéro à minuit ; `dernier_refus` et `dernier_echec`
  passent la nuit. Ils sont écrits sur le disque au plus toutes les dix
  minutes et à l'arrêt du studio : un redémarrage ne les efface pas, une
  coupure de courant en perd au plus dix minutes.

`suivi` ne sort que vers le propriétaire et vers `/admin`, jamais par
`GET /api/v1/moi` : c'est ce qui est arrivé à la clé, pas ce qu'elle permet.

### Ce que la clé peut faire

Une clé branchée sur un workflow de détourage n'a aucune raison de pouvoir
lancer une vidéo de huit minutes. **Volée, elle ne doit ouvrir que ce qu'elle
servait.** À la création, coche ce qu'elle peut faire — ou, sans la page,
`"operations"` : une liste parmi

| Famille | Ce qu'elle couvre |
|---|---|
| `image` | créer une image, une planche |
| `retouche` | modifier l'image fournie, retoucher le fond, le sujet ou une zone |
| `video` | créer une vidéo, animer une image, fluidifier une vidéo |
| `audio` | la musique |
| `agrandir` | agrandir une image |
| `detourer` | détourer |
| `objet3d` | un objet 3D |
| `lecture` | décrire une image |

**Rien de coché, liste vide : tout**, y compris ce que le studio saura faire
demain. C'est le défaut, et une clé d'avant ce réglage peut donc tout. Huit
familles et non les treize types du catalogue : « retoucher le fond » sans
« retoucher le sujet » n'est une frontière pour personne. La liste se lit dans
`operations` de la fiche et de `GET /api/v1/moi` ; elle survit à un
renouvellement, et ne se change pas : une autre liste, c'est une autre clé.

La garde tient à **deux endroits**, parce que le studio ne sait pas toujours
d'avance ce qu'il va faire :

- **Avec un `moteur` imposé**, son type dit l'opération : refusé tout de suite
  en **403 `cle_operation_interdite`**, sans place dans la file ni unité du
  plafond du jour. Pas de `reessayer_dans` : attendre n'y changera rien.
- **Sans moteur**, c'est l'analyse de la demande qui décide. Si elle conclut à
  une famille que la clé ne permet pas, le rendu finit en **`erreur`** avec
  `erreur.code` = `cle_operation_interdite` — **avant** l'enrichissement par le
  modèle de langage et avant toute minute de carte. Il a compté dans le
  plafond du jour : la demande était entrée. Une question du studio, elle,
  passe toujours.

**Une image jointe à un moteur d'image du nuage est une retouche.** Nano
Banana reçoit la photo avec le texte et la rend modifiée : sur une clé `image`
sans `retouche`, `"moteur": "nanobanana"` avec une image est refusé en 403
comme une retouche, et sans image il passe — c'est une image neuve. Quand c'est
le studio qui choisit le nuage tout seul, l'image d'une clé sans `retouche` ne
part pas chez le fournisseur : il rend une image neuve, le fil le dit. Un moteur
d'image de la maison, lui, ne lit pas l'image jointe : il reste `image`.

`GET /api/v1/moteurs` ne montre à la clé que les moteurs qu'elle peut lancer :
un assistant qui choisit dans cette liste n'y trouve pas un refus.

#### Un plafond par famille

Un détourage prend deux secondes de carte, une vidéo huit minutes : un seul
`par_jour` assez large pour cinquante détourages laisse passer cinquante
vidéos. À la création, donne un plafond du jour **famille par famille** — dans
la page, une case par famille (0 : aucun) ; sans la page,
`"par_jour_familles"`, un objet des mêmes familles vers un nombre de rendus :

```json
{"nom": "détourage du salon", "par_jour": 0,
 "par_jour_familles": {"detourer": 50, "video": 5}}
```

**Absent ou vide : rien de plus que `par_jour`.** Les deux s'appliquent :
`par_jour` compte tous les rendus de la clé, `par_jour_familles` ceux d'une
famille. Une famille sans chiffre n'a que `par_jour`. Les variantes comptent
là où elles existent : quatre variantes d'une image sont quatre images ; une
vidéo ou une retouche ne se tire pas en variantes et compte une fois.
Compté sur le disque, de minuit à minuit à
l'heure du studio, comme `par_jour` ; il survit à un renouvellement, et ne se
change pas : d'autres plafonds, c'est une autre clé.

La garde tient aux **deux mêmes endroits** que les opérations :

- **Avec un `moteur` imposé**, sa famille est connue : refusé tout de suite en
  **429 `cle_plafond_famille`**, avec `Retry-After` jusqu'à minuit — sans
  `reessayer_dans` quand les variantes demandées dépassent le plafond lui-même :
  attendre n'y changera rien.
- **Sans moteur**, la famille n'est sue qu'après l'analyse : le rendu finit en
  **`erreur`** avec `erreur.code` = `cle_plafond_famille`, **avant**
  l'enrichissement et toute minute de carte. Il a compté dans `par_jour` (la
  demande était entrée), pas dans le plafond de sa famille. Le refus compte
  dans le `suivi` de la clé.

`GET /api/v1/moi` (et l'outil MCP `decrire_cle`) dit **ce qui reste** à chaque
famille bornée, dans `par_famille` :

```json
"par_famille": {"detourer": {"aujourdhui": 12, "plafond": 50, "reste": 38},
                "video": {"aujourdhui": 5, "plafond": 5, "reste": 0}}
```

## Révoquer, et ce qui éteint une clé

**Révoquer ne demande que la session**, pas le mot de passe. Fermer une porte
n'a jamais besoin d'être aussi difficile que de l'ouvrir — et c'est ce qu'on
fait quand on croit une clé fuitée, souvent sans le mot de passe sous la main.
Une clé révoquée cesse de valoir à la requête suivante, et **ses liens signés
avec elle**.

Trois gestes éteignent **toutes** les clés d'un compte, sans qu'on y touche :

- **changer de mot de passe** ;
- **armer ou désarmer le second facteur** ;
- **supprimer le compte** (ses clés sont alors effacées du fichier).

Les deux premiers incrémentent la *génération* du compte — le même compteur qui
ferme toutes ses sessions ([Comptes](comptes.md)) — et une clé née sous une
autre génération n'est plus reconnue. Sans ce lien, quelqu'un qui a volé le mot
de passe pouvait se fabriquer une clé dans la minute, et elle aurait survécu au
changement de mot de passe que le propriétaire fait justement pour le chasser.
La liste les montre alors `active: false` ; elles ne se rallument pas, il faut
en refaire.

**Ses liens signés et ses rappels s'éteignent avec elle.** Une clé éteinte
existe encore dans le fichier — c'est ce qui permet à la liste de te la montrer
éteinte —, mais le studio refuse les liens qu'elle a déjà distribués, et ne
signe plus de rappel en son nom. Ce n'était pas le cas au premier jet : la
relecture de cette page l'a relevé le 4 novembre 2026, et un lien donné avant
un changement de mot de passe restait une porte ouverte vingt-quatre heures de
plus — précisément ce que le changement devait fermer.

**L'administrateur peut révoquer n'importe quelle clé** (onglet « clés
d'accès » de `/admin`, routes `GET /api/admin/acces` et `DELETE
/api/admin/acces/{id}`), mais **il ne peut pas en créer** pour un autre : il
faudrait son mot de passe et son téléphone. Il voit le nom, le compte, la date
de dernier usage, le nombre de rendus en cours de chacune, ses refus du jour
par code et les secrets faux présentés sous son identifiant — jamais la clé.

## Les quatre règles

1. **La clé ne vaut que sur `/api/v1/`, `/mcp` et `/openai/v1/`** (la porte
   [compatible OpenAI](#brancher-open-webui-librechat-ou-un-sdk-openai)). Présentée ailleurs, elle est
   **refusée en 403** (`cle_hors_perimetre`) plutôt qu'ignorée : ignorée, elle
   laisserait croire à celui qui l'essaie sur `/api/generer` qu'elle marche,
   jusqu'au jour où un cookie oublié dans le même client la ferait passer pour
   lui. Réciproquement, une session de navigateur ne suffit pas sur `/api/v1` :
   il faut la clé.
2. **Elle ne vaut jamais administration**, même créée sur le compte `admin`.
   Sans cette règle, une clé collée dans un workflow ouvrait la médiathèque de
   tous les comptes.
3. **Un programme ne voit que les rendus de sa clé.** Pas ceux que son
   propriétaire fait à la main, pas ceux d'une autre de ses clés. Une clé qui
   fuit depuis un workflow ne doit pas lire les images de la maison.
4. **Chaque demande a sa propre conversation**, sauf si le programme en nomme
   une des siennes. La conversation porte le contexte — dernière image, cinq
   derniers tours, réglages — et un programme qui écrivait dans la conversation
   courante du navigateur voyait « la même en bleu » devenir une retouche de ce
   que l'humain venait de faire. Ces conversations **ne sont pas dans la
   liste** de la page (une par rendu, elles la noieraient), mais **leurs images
   sont dans la médiathèque**. Après **trente jours sans un tour**, elles sont
   fermées, puis effacées le lendemain avec leurs images, comme n'importe quelle
   [conversation fermée](fermer-une-conversation.md) : un workflow horaire
   laisserait sinon 720 conversations par mois que personne ne rouvrira.

## La référence de l'API

Les exemples supposent :

```sh
STUDIO=http://192.0.2.10:8199
CLE=cs_92d11256_…          # la tienne, entière
```

Le contrat complet, lisible par une machine, est servi par le studio lui-même :
`GET /api/v1/openapi.json`, sans clé ([plus bas](#le-contrat-openapi)).

### S'authentifier

Un seul en-tête, sur chaque requête :

```
Authorization: Bearer cs_…
```

**Jamais dans l'adresse ni dans un cookie.** Dans l'adresse, la clé finit dans
les journaux du proxy et dans l'historique ; dans un cookie, elle partirait
toute seule depuis n'importe quel site. Seul un `Bearer` qui commence par
`cs_` est lu comme une clé : un reverse proxy d'authentification (Authelia,
oauth2-proxy) qui pose son propre `Bearer` sur toutes les requêtes ne fait donc
pas refuser la page entière.

Sans clé, ou avec une clé refusée : **401**, avec `WWW-Authenticate: Bearer
realm="comfystudio"`. **Une bonne clé n'est jamais freinée** : le studio la
vérifie d'abord, et le frein ne vaut que pour l'échec. Après trois secrets faux
pour une même clé depuis une même adresse, l'attente double à chaque essai
(1 s, 2, 4… plafonnée à 30) et le studio répond **429** `trop_d_essais`. Une clé
inconnue ou révoquée n'a rien à deviner : elle est refusée en 401 et n'inscrit
rien. Le compteur est à part de celui des mots de passe, pour qu'un workflow mal
réglé ne freine pas les humains qui se connectent derrière le même proxy.

> **Ce n'était pas le cas au premier jet.** Le frein se lisait *avant* la
> vérification : l'identifiant public d'une clé — imprimé dans chaque lien
> signé — suffisait à la tenir en 429 avec un secret faux toutes les trente
> secondes. La revue de sécurité du 4 novembre 2026 l'a relevé.

Les phrases des refus suivent `Accept-Language` (français ou anglais) ; le
`code`, lui, ne change pas.

### Demander un rendu — `POST /api/v1/rendus`

```sh
curl -s "$STUDIO/api/v1/rendus" \
  -H "Authorization: Bearer $CLE" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: lot-du-4-novembre-0001" \
  -d '{"demande": "un renard roux dans la neige au crépuscule", "attendre": 300}'
```

| Champ | Ce qu'il fait |
|---|---|
| `demande` | La demande en langage naturel, **dans n'importe quelle langue** — ne la traduis pas, le studio s'en charge ([Plusieurs langues](plusieurs-langues.md)). 3 000 caractères au plus. Il faut `demande`, une image, ou les deux. |
| `moteur` | Une `cle` de `GET /api/v1/moteurs`. Imposer un moteur impose aussi l'opération (`agrandir`, `detourer`…). |
| `taille` | `1024x1024`, `1080x1350`, `1216x832`, `1280x720`, `1600x900`, `1920x1080`, `768x1344`, `832x1216`. |
| `priorite` | `brouillon`, `rapide` ou `soigne` ([Le brouillon](brouillon.md)). |
| `variantes` | De 1 à 4 tirages du même plan ([Variantes](variantes.md)). |
| `machine` | L'identifiant d'une machine du parc, pour l'imposer. |
| `image` | Le nom rendu par [`POST /api/v1/fichiers`](#envoyer-une-image--post-apiv1fichiers). |
| `image_base64`, `image_type` | Une image dans le corps, en base64 ou en URL `data:image/png;base64,…` ; `image_type` vaut `png` par défaut, et ne prend que `png`, `jpg`, `jpeg` ou `webp` — le type devient l'extension du fichier écrit, il vient donc d'une liste, jamais du client. Bornée par le corps JSON, 4 Mio : au-delà, passe par `/api/v1/fichiers`. |
| `conversation` | L'identifiant d'une conversation **de cette clé**, pour enchaîner (« la même en bleu »). Inconnue ou d'une autre clé : 404, et non une conversation neuve en silence. |
| `rappel` | Une URL à prévenir à la fin ([Les rappels](#les-rappels)). Son hôte doit être déclaré dans la clé. |
| `attendre` | Secondes à attendre un état final avant de répondre, de 0 à **600**. 0 par défaut : la réponse part tout de suite. |
| `nuage` | `false` interdit le nuage pour cette demande. `true` (le défaut) ne l'ouvre **pas** à une clé qui n'y a pas droit : la demande peut restreindre la clé, jamais l'élargir. |
| `style_audio` | Pour une musique : les étiquettes de style, en anglais, séparées par des virgules — `"dark ambient, low cello, hurdy-gurdy, 55 BPM"`. 300 caractères au plus. Elles partent **telles quelles** au moteur, avant tout ce que le studio lirait dans la demande ; le BPM s'y ajoute s'il n'y est pas, et jamais « clear vocals ». |
| `instrumental` | Pour une musique : `true` = sans voix ni paroles, même si la demande parle de chanson. Absent ou `false` : le studio lit la demande. |

**Une musique courte, pour un essai, se demande dans la phrase.** Il n'y a pas
de champ de durée : le studio la lit dans `demande` — « une musique calme de
30 secondes », « 45 s de piano », « a 30 seconds lofi track », « 30 segundos »,
« deux minutes ». Sans précision, un morceau dure **60 s** ; la durée reste
bornée de 20 à 180 s. Ce défaut n'a pas été raccourci, faute de mesure qui dise
combien trente secondes font gagner : le temps d'un morceau ne tient pas qu'à
sa longueur. Le moteur soigné (`audioplus`) fait 50 étapes au lieu de 8, une
chanson fait d'abord écrire ses paroles au modèle de langage, et la passe qui
invente les codes audio — toujours faite pour un morceau neuf — a coûté à elle
seule ~95 s sur 106 sur un morceau de 60 s (mesure du 30 août 2026, sur une
retouche où elle était forcée, [journal](journal/audio_retouche.md)) ; ce
qu'elle coûte pour 30 s n'a pas été mesuré. Pour juger vite, `priorite: "brouillon"`
divise les étapes par quatre ([Le brouillon](brouillon.md)).

**Ce que la demande exclut ne devient pas un style.** « sans voix », « pas de
batterie », « no vocals », « without drums », « sin voz » : le mot nié est
retiré des étiquettes envoyées au moteur de musique, même si l'analyse l'y
avait mis, et « sans voix » — comme « instrumental » hors d'une chanson — rend
un morceau instrumental, sans paroles. Le tempo se dit aussi dans la phrase :
« 60 BPM » d'abord, sinon « très lent » (55), « lent » (70), « modéré » (100),
« rapide » (130), « très rapide » (150), en français, anglais ou espagnol ; un
tempo écrit n'est jamais remplacé par celui du genre. Des étiquettes écrites
après **`Style :`** ou **`Tags :`** dans la demande, jusqu'à la fin de la phrase,
passent telles quelles, comme `style_audio`.
ACE-Step n'a pas de champ négatif : ce qu'on exclut ne peut que disparaître du
positif. Le journal du rendu le dit (« exclu par la demande : vocals, drums »).

Pourquoi 600 secondes et pas une heure : le nœud HTTP Request de n8n coupe à
300 s par défaut (on peut le monter), et un rendu vidéo sur la 2080 Ti dure
trois à huit minutes ([Mesures](mesures.md)). Au-delà, sonde ou prends le
rappel : garder une connexion ouverte une heure n'est un service pour personne.

**Derrière un reverse proxy, l'attente est bornée.** Un reverse proxy coupe une réponse qui tarde : 60 s pour un nginx laissé par
défaut, 90 s pour le nginx-proxy-manager qui publie le studio en https. Un
`attendre: 300` y finissait en **504 du proxy** — rien pour le client, et le
rendu continuait sans lui. Le studio reconnaît donc une requête arrivée par un
proxy (`X-Forwarded-For` ou `X-Forwarded-Proto` — nginx-proxy-manager, Caddy
et Traefik les posent ; un `proxy_pass` nu de nginx, **non** : ajoute-y
`proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`, sinon le studio
croit la requête directe et le 504 revient) et y borne l'attente à
**55 s** (`STUDIO_ATTENTE_PROXY`, [Réglages](reglages.md)) — `attendre` de
`GET /api/v1/rendus/{id}`, de `.../reponse` et des outils MCP compris. Au-delà,
c'est la réponse d'une attente expirée, pas une erreur : 202 (ou 200) avec
l'état courant. L'en-tête **`X-Attente-Bornee: 55`** est posé sur toute réponse
dont l'attente a été bornée, même si le rendu a fini avant. Relis le rendu
ensuite. Une requête directe garde son `attendre` ; un client qui pose ces
en-têtes lui-même ne fait que raccourcir sa propre attente. La recette n8n
plus bas relit déjà, jusqu'à vingt fois : derrière un proxy, cela fait
une vingtaine de minutes, de quoi finir une vidéo.

Réponse : **202** tant que le rendu n'est pas dans un état final, **200** s'il
l'est (fini dans le délai d'`attendre`), avec `Location: /api/v1/rendus/{id}`.
Le corps a la même forme partout — réponse de l'API, corps du rappel, contenu
structuré de l'outil MCP :

```json
{
 "id": "3f2a9c41d0e84b6f9a7215c3e8d06b11",
 "etat": "fini",
 "demande": "un renard roux dans la neige au crépuscule",
 "conversation": "8c1e…",
 "cree": "2026-11-04T14:03:12+01:00",
 "intention": "image",
 "moteur": "klein4b",
 "machine": "pc",
 "position": null,
 "avance": null,
 "secondes": 41.2,
 "estimation": null,
 "fichiers": [
  {"rang": 0, "variante": 1, "nom": "studio_00012_.png", "type": "image",
   "url": "http://192.0.2.10:8199/api/v1/rendus/3f2a9c41d0e84b6f9a7215c3e8d06b11/fichiers/0",
   "lien": "http://192.0.2.10:8199/api/v1/lien/92d11256.3f2a9c41d0e84b6f9a7215c3e8d06b11.0.1793843678.5e425a4a485e1918327edf5df68ef194"}
 ],
 "questions": [],
 "description": null,
 "erreur": null,
 "journal": ["en file d'attente — 0 demande(s) devant", "…"]
}
```

`cree` est l'heure locale du studio, au format RFC 3339 (`+01:00`). `journal` porte les cinq dernières lignes du fil, celles que la page
montre : un humain qui relit l'exécution n8n comprend ainsi *pourquoi* un rendu
a pris trois minutes, sans ouvrir le studio. Avec des variantes, `id` est celui
du premier tirage, `fichiers` rassemble ceux de tous les tirages (`variante`
dit lequel), et le groupe est `fini` dès qu'un tirage a abouti.

**`estimation`** dit, pendant le calcul, combien de temps un tel rendu prend
d'habitude — le devis que la page affiche à côté de la bulle
([Combien de temps ça va prendre](combien-de-temps.md)) :

```json
"estimation": {"secondes": 95, "mesures": 4, "ecoule_rendu": 12.0}
```

`secondes` est la médiane des rendus précédents de ce compte avec ce moteur,
`mesures` le nombre de rendus dont elle est tirée, `ecoule_rendu` le temps
depuis que la machine a pris le rendu (`null` tant qu'il attend), le seul
comparable à la médiane. `null` quand le studio ne sait pas — moins de trois
rendus comparables, un brouillon — et une fois le rendu achevé : `secondes`, au
premier niveau, dit alors la vraie durée. Pour une musique, la médiane ne
distingue pas encore une piste de 30 s d'une piste de trois minutes.

**Tout est vérifié avant la file**, dans cet ordre : les plafonds de la clé,
l'adresse de rappel, l'image, la conversation, la validation commune avec la
page, le droit au nuage, et le garde-fou des mineurs. Un refus coûte donc une
requête, pas une place dans la file ni une unité du plafond du jour.

### Les états, et quoi faire dans chacun

| `etat` | Final | Ce que le programme fait |
|---|---|---|
| `en_file` | non | Attendre. `position` dit combien de travaux sont devant, en vol compris. |
| `en_cours` | non | Attendre. `avance` va de 0 à 1 quand la machine la donne, `null` sinon. |
| `attente_machine` | non | La machine demandée est en pause : la demande repartira seule à son retour ([Attendre une machine](attendre-une-machine.md)). Attendre, ou annuler si c'est trop long pour toi. |
| `question` | **oui** | Le studio demande une précision avant de rien produire. Lire `questions`, répondre par [`.../reponse`](#répondre-à-une-question--post-apiv1rendusidreponse). |
| `fini` | **oui** | Télécharger `fichiers`. `description` porte le texte d'une lecture d'image. |
| `erreur` | **oui** | Lire `erreur.code` et `erreur.message`. `code` dit la **raison**, voir dessous. Ne pas relancer en boucle. |

**`erreur.code` dit pourquoi**, et deux familles ne se traitent pas pareil :

- **un refus** — `refus_mineurs`, `cle_operation_interdite`,
  `moteur_nulle_part` (aucune machine n'a ce moteur), `echec` (une panne sans
  phrase) : la même demande échouera de la même façon, **ne la relance pas** ;
- **une machine qui manquait** — `comfy_muet`, `machine_pas_revenue`,
  `vram_trop_petite`, `attente_expiree`… : la même demande peut passer **plus
  tard**, une fois la machine revenue. Une relance, pas une boucle.

Avant le 4 novembre 2026, presque tout se lisait `echec` : le code de
l'enveloppe, pas celui de la raison. Un workflow qui testait `echec` doit
maintenant tester les codes qui l'intéressent.
| `annule` | **oui** | Annulé, par toi ou depuis la page. |

Un rendu resté `en cours` quand le studio a redémarré, et qu'il n'a pas repris,
se lit `erreur` : mieux vaut le dire que laisser un workflow attendre pour
toujours un rendu que plus personne ne fait.

### Suivre un rendu — `GET /api/v1/rendus/{id}`

```sh
curl -s "$STUDIO/api/v1/rendus/3f2a9c41d0e84b6f9a7215c3e8d06b11?attendre=60" \
  -H "Authorization: Bearer $CLE"
```

Toujours **200**, avec le rendu. `attendre` (de 0 à 600) fait patienter la
réponse jusqu'à un état final. Un rendu fini hier se relit encore aujourd'hui,
même après un redémarrage : il vient alors du disque. Un identifiant inconnu, ou
celui d'un rendu d'une autre clé : **404** `rendu_inconnu`, la même réponse
dans les deux cas — distinguer « pas à toi » de « n'existe pas » renseignerait
un curieux.

### Récupérer les fichiers

Deux adresses par fichier, dans `fichiers[]` :

- **`url`** — `GET /api/v1/rendus/{id}/fichiers/{rang}`, **avec la clé** en
  en-tête. C'est celle d'un programme.
- **`lien`** — `GET /api/v1/lien/{jeton}`, **sans en-tête**, valable
  **24 heures**. C'est celle qu'un assistant IA donne à un humain, qu'une
  balise `<img>` ou un nœud n8n réglé au plus simple peuvent ouvrir. Le jeton
  porte sa propre preuve — quelle clé, quel rendu, quel fichier, jusqu'à quand —
  scellée par HMAC ; il meurt avec sa clé (révocation) et à sa date. Un jour :
  assez pour qu'un humain clique le soir sur le lien que son assistant lui a
  donné le matin, pas assez pour qu'un lien collé dans un ticket reste une porte
  ouverte. Servi avec `Cache-Control: private, no-store`, pour qu'aucun proxy
  partagé ne le resserve après sa date.

```sh
curl -s -o renard.png "$STUDIO/api/v1/rendus/3f2a9c41d0e84b6f9a7215c3e8d06b11/fichiers/0" \
  -H "Authorization: Bearer $CLE"
```

Supprimer `conversations/_session.json` invalide d'un coup, au redémarrage,
tous les liens signés : leur secret est dérivé du secret des sessions.

### Répondre à une question — `POST /api/v1/rendus/{id}/reponse`

```sh
curl -s "$STUDIO/api/v1/rendus/3f2a9c41d0e84b6f9a7215c3e8d06b11/reponse" \
  -H "Authorization: Bearer $CLE" -H "Content-Type: application/json" \
  -d '{"reponse": "une affiche, format portrait, style gravure", "attendre": 300}'
```

Un **nouveau rendu** part, dans la même conversation, avec « Précisions : »
ajouté à la demande — exactement ce que fait la page. **Lis son `id`** : c'est
lui qu'il faut suivre désormais. Le `rappel` du rendu d'origine est repris si tu
n'en donnes pas. Un rendu qui n'est pas dans l'état `question` : **409**
`pas_de_question`.

### Annuler — `DELETE /api/v1/rendus/{id}`

```sh
curl -s -X DELETE "$STUDIO/api/v1/rendus/3f2a9c41d0e84b6f9a7215c3e8d06b11" \
  -H "Authorization: Bearer $CLE"
```

La même annulation que la page, variantes comprises : retiré de la file, ou
interrompu sur la carte. Rend le rendu : `annule` tout de suite s'il était
en file ; s'il calculait sur une machine à agent, celle-ci apprend l'arrêt à son
prochain battement, et l'état passe à `annule` quelques secondes plus tard —
relis-le. Déjà terminé : **409** `rendu_termine`.

### Retrouver ses rendus — `GET /api/v1/rendus`

Les derniers rendus de **cette** clé, du plus récent au plus ancien, chacun
sous la même forme que `GET /api/v1/rendus/{id}`. Pour un workflow qui a perdu
un identifiant, ou un assistant à qui l'on demande « ce que j'ai fait tout à
l'heure ».

```bash
curl -H "Authorization: Bearer cs_…" "http://STUDIO:8199/api/v1/rendus?limite=5"
```

`limite` va de 1 à 100 (20 par défaut) ; au-delà, **400** `champ_illisible` —
chaque rendu porte ses fichiers et des liens signés, et une page de mille
rendus relue chaque minute deviendrait le travail principal du studio. Les
variantes viennent avec leur groupe, sous l'identifiant du premier tirage. Ni
les rendus d'une autre clé du même compte, ni ceux d'un autre compte.

### Envoyer une image — `POST /api/v1/fichiers`

```sh
curl -s "$STUDIO/api/v1/fichiers" -H "Authorization: Bearer $CLE" \
  -F "fichier=@photo.jpg"
```

```json
{"image": "studio_4b1d0c2a9e.jpg", "octets": 284113}
```

Puis `"image": "studio_4b1d0c2a9e.jpg"` dans `POST /api/v1/rendus`. Le même
registre que les images glissées dans la page : la retouche les voit de la même
façon. Une image se borne à 32 Mo.

### Les moteurs et la clé — `GET /api/v1/moteurs`, `GET /api/v1/moi`

```sh
curl -s "$STUDIO/api/v1/moteurs" -H "Authorization: Bearer $CLE"
```

```json
{"moteurs": [{"cle": "klein4b", "titre": "FLUX.2 klein 4B",
              "pour": "polyvalent, tres bon suivi du prompt, …",
              "type": "image", "distant": false, "present": true}, …],
 "tailles": ["1024x1024", …], "priorites": ["brouillon", "rapide", "soigne"],
 "variantes_max": 4}
```

`present: false` : ses modèles ne sont sur aucune machine. Un moteur qu'aucune
carte connue du parc ne porte — `klein9bhd` demande 18 Go, la 2080 Ti en tient
14,5 en débordant — n'est pas listé du tout ; imposé quand même, il est refusé
par une phrase qui nomme le moteur à prendre à sa place. Les moteurs distants
n'apparaissent qu'à une clé qui a droit au nuage, et seulement si leur clé
d'API est posée : proposer un choix qui sera refusé ne sert pas l'assistant qui
lit cette liste pour choisir.

```sh
curl -s "$STUDIO/api/v1/moi" -H "Authorization: Bearer $CLE"
```

```json
{"compte": "Jordan",
 "cle": {"id": "92d11256", "compte": "jordan", "nom": "n8n maison",
         "apercu": "cs_92d11256_…", "cree": 1793757278.8, "vu": 1793757278.8,
         "nuage": false, "hotes": ["n8n.maison:5678"], "en_file": 4,
         "par_jour": 0, "generation": 0, "expire": null,
         "ancienne_jusqu": null, "operations": [], "par_jour_familles": {}},
 "en_cours": 0, "aujourdhui": 0, "par_famille": {}, "attendre_max": 600}
```

C'est la route à appeler pour vérifier qu'une clé marche, avant de lancer quoi
que ce soit.

### Ne pas lancer deux fois le même rendu — `Idempotency-Key`

**n8n réessaie.** Un nœud HTTP réglé sur « Retry On Fail » renvoie la requête
quand la réponse tarde, et chaque renvoi était un rendu de plus — du temps de
carte pour une image que personne n'a demandée deux fois. Avec l'en-tête
`Idempotency-Key` (200 caractères au plus), **même clé d'accès et même valeur
donnent le même rendu pendant 24 heures** : la seconde requête ne lance rien et
rend le rendu existant, avec `Idempotent-Replayed: true`.

Le rejeu **attend comme la première fois** quand il porte `attendre` : n8n
réessaie justement parce que la première réponse a tardé, et un rejeu qui
rendrait `en_cours` sur-le-champ casserait le workflow qu'il devait sauver.

**Le registre survit à un redémarrage** du studio (`_idempotence.json`) :
c'est justement le moment que « Retry On Fail » doit rattraper. Si le rendu
qu'une clé désignait **n'existe plus** — conversation effacée, ou fermée parce
que la clé en avait trop —, la requête part comme neuve au lieu de rendre 404
pendant 24 heures.

### Les plafonds de la clé

- **`en_file`** — combien de rendus de cette clé peuvent être en cours à la
  fois (de 1 à 20, 4 par défaut). Au-delà : **429** `cle_file_pleine`. Quatre
  suffisent : la carte les traite un par un, et une seule clé ne doit pas
  occuper la file du studio pendant des heures, avec les humains derrière.
- **`par_jour`** — combien de rendus par jour, de minuit à minuit à l'heure du
  studio (0 : sans plafond, le défaut). Au-delà : **429** `cle_plafond_jour`.
  Compté sur le disque, pas en mémoire : un plafond qui repartirait à zéro à
  chaque redémarrage n'en serait pas un. **Les variantes comptent** : quatre
  variantes sont quatre rendus, pour `par_jour` comme pour `en_file` (code
  **429** `cle_file_variantes` quand elles dépasseraient `en_file`).
- **`par_jour_familles`** — le même plafond, [famille par
  famille](#un-plafond-par-famille) (« 50 détourages et 5 vidéos »), en plus
  de `par_jour`. Au-delà : **429** `cle_plafond_famille`, ou un rendu en
  `erreur` de ce code quand c'est l'analyse qui a lu la famille.

**Chaque 429 dit quand réessayer** : l'en-tête **`Retry-After`** (en secondes)
et le même nombre dans `reessayer_dans` du corps, pour un client qui ne lit que
le JSON. Il est **exact** pour le freinage (`trop_d_essais`) et pour les
plafonds du jour, de la clé ou d'une famille (jusqu'à minuit, heure du
studio) ; pour une file pleine, le
studio ne sait pas quand un rendu finira — de deux secondes à huit minutes — et
conseille **30 s** : le [rappel](#les-rappels) reste le bon outil. **Pas de
délai du tout** quand attendre ne servirait à rien — plus de variantes que le
plafond lui-même : la phrase dit quoi changer, et un `Retry-After` ferait
boucler le workflow pour toujours. Par MCP, la
phrase du refus le dit aussi : « (réessaie dans 30 s) ».

**Les humains passent d'abord.** La file des rendus est commune, mais une
demande tapée dans la page passe devant celles des programmes : l'humain attend
devant l'écran, le programme attend son rappel. Un lot n8n ne met donc plus
personne derrière lui. Pour qu'un jour chargé n'enterre pas un workflow, une
demande de programme qui a attendu **dix minutes** reprend son tour d'arrivée —
une demande humaine prend de quelques secondes à quelques minutes, dix minutes
ne font attendre un programme que pour les humains qui sont vraiment là. La
position que la page affiche suit la même règle. Ce n'était pas le cas au
premier jet : la file était strictement dans l'ordre d'arrivée.

Et deux bornes que la clé ne règle pas :

- **Huit attentes à la fois par clé** (`attendre`). Chacune tient une connexion
  ouverte ; au-delà, la requête rend l'état sur-le-champ au lieu d'attendre —
  elle n'est pas refusée. Une attente s'arrête aussi dès que la clé est
  révoquée ou éteinte : elle ne reçoit pas les images à la fin.
- **Cinq cents conversations ouvertes par clé.** Une par demande, gardées
  trente jours : au-delà, la plus ancienne est fermée, et la purge commune
  l'efface le lendemain, images comprises.

Ces plafonds passent **en premier**, avant même la lecture de l'image : un
workflow emballé doit être arrêté le plus tôt possible.

### Les refus

Un refus est un objet JSON : `erreur`, une phrase, et `code`, stable. **Branche
ton workflow sur `code`**, jamais sur la phrase : elle peut changer, être
traduite ; le code continue de marcher.

```json
{"erreur": "« attendre » se donne en secondes, de 0 à 600", "code": "attendre_bornes"}
```

| `code` | Statut | Quand |
|---|---|---|
| `cle_requise` | 401 | aucune clé sur une route qui en exige une |
| `cle_refusee` | 401 | clé inconnue, révoquée, ou éteinte (mot de passe, second facteur) — ne pas réessayer, en refaire une |
| `cle_expiree` | 401 | clé passée sa [date de fin](#une-date-de-fin) — ne pas réessayer, en refaire une |
| `cle_hors_perimetre` | 403 | une clé présentée hors de `/api/v1`, `/openai/v1` et `/mcp` |
| `trop_d_essais` | 429 | trop de clés refusées depuis cette adresse ; attendre |
| `corps_illisible` | 400 | le corps n'est pas un objet JSON |
| `attendre_bornes` | 400 | `attendre` hors de 0 à 600 |
| `idempotence_illisible` | 400 | `Idempotency-Key` de plus de 200 caractères |
| `cle_file_pleine` | 429 | plafond `en_file` atteint |
| `cle_file_variantes` | 429 | les `variantes` dépasseraient `en_file` ; sans `reessayer_dans` quand elles dépassent le plafond lui-même |
| `cle_plafond_jour` | 429 | plafond `par_jour` atteint |
| `cle_plafond_famille` | 429 | le moteur imposé est d'une famille qui a atteint [son plafond du jour](#un-plafond-par-famille) ; sans `reessayer_dans` quand les variantes dépassent le plafond lui-même. Sans moteur imposé : rendu en `erreur` de même code |
| `champ_illisible` | 400 | un champ n'a pas la forme attendue (la phrase le nomme) |
| `rappel_refuse` | 400 | adresse de rappel refusée ; la phrase dit pourquoi : `hote`, `schema`, `identifiants`, `illisible` |
| `image_illisible` | 400 | `image_base64` n'est pas du base64 |
| `fichier_vide` | 400 | image vide |
| `fichier_trop_lourd` | 413 | image au-delà de 32 Mo |
| `conversation_inconnue` | 404 | aucune conversation ouverte **de cette clé** ne porte cet identifiant |
| `cle_sans_nuage` | 400 | moteur distant demandé, et la clé n'a pas droit au nuage |
| `cle_operation_interdite` | 403 | le moteur imposé fait une opération que [la clé ne permet pas](#ce-que-la-clé-peut-faire) |
| `refus_mineurs` | 422 | contenu sexuel impliquant des mineurs |
| `rendu_inconnu` | 404 | aucun rendu de cette clé ne porte cet identifiant, ou ce fichier n'existe pas |
| `rendu_termine` | 409 | annulation d'un rendu déjà terminé |
| `pas_de_question` | 409 | réponse à un rendu qui n'attend pas de réponse |
| `reponse_vide` | 400 | réponse vide |

**La validation commune avec la page** porte aussi un code. Ces refus viennent
de la même fonction pour la page et pour les programmes — une seule suite de
gardes, pour qu'aucune borne ne vive d'un seul côté :

| `code` | Statut | Quand |
|---|---|---|
| `demande_vide` | 400 | ni `demande` ni image |
| `demande_trop_longue` | 400 | plus de 3 000 caractères |
| `taille_non_prise` | 400 | `taille` hors de la liste de `/api/v1/moteurs` |
| `moteur_inconnu` | 400 | `moteur` qui n'existe pas |
| `moteur_sans_cle` | 400 | moteur distant sans sa clé d'API de fournisseur |
| `priorite_inconnue` | 400 | `priorite` hors de la liste |
| `variantes_illisible` | 400 | `variantes` n'est pas un nombre |
| `variantes_bornes` | 400 | `variantes` hors de 1 à 4 |
| `machine_inconnue` | 400 | `machine` qui n'existe pas |
| `image_inconnue` | 404 | `image` qui n'a pas été envoyée par ce compte |
| `formulaire_attendu` | 400 | `POST /api/v1/fichiers` sans corps `multipart/form-data` |
| `aucun_fichier` | 400 | formulaire sans champ qui porte un nom de fichier |
| `format_refuse` | 400 | extension hors des familles acceptées (la phrase les liste) |

Les trois derniers viennent de `POST /api/v1/fichiers`, qui rend aussi
`fichier_vide` et `fichier_trop_lourd` (413) avec le même sens que pour
`image_base64`. Le contrat OpenAPI décrit les deux tables, et l'énumération de
`code` les contient toutes.

**Un seul refus n'a pas de code** : un corps JSON de plus de 4 Mio est refusé
en **413** par le serveur HTTP lui-même, avec un corps texte, avant que le
studio ne le lise.

## Les rappels

Un programme ne veut pas interroger le studio toutes les cinq secondes pendant
dix minutes. Il donne une URL dans `rappel` — typiquement celle d'un nœud
Webhook ou Wait de n8n — et le studio y POSTe **un événement, une fois**, quand
le rendu atteint un état final.

### L'événement

```
POST /webhook/… HTTP/1.1
Content-Type: application/json
X-ComfyStudio-Signature: t=1793757300,v1=6f1c…
X-ComfyStudio-Evenement: rendu.fini
X-ComfyStudio-Livraison: 0c9d4e7f8a2b4c1d9e3f5a6b7c8d9e0f
User-Agent: ComfyStudio-rappel

{"envoye":"2026-11-04T14:03:54+01:00","evenement":"rendu.fini","id":"3f2a…","rendu":{…}}
```

- `evenement` : `rendu.fini`, `rendu.erreur`, `rendu.question` ou
  `rendu.annule` — une liste fermée, pour que chaque branche du workflow sache
  ce qu'elle reçoit.
- `rendu` : le même objet que `GET /api/v1/rendus/{id}`, adresses comprises.
- Le corps est du JSON **compact, aux clés triées**, en UTF-8 : les mêmes
  octets pour le même événement, ce qui rend la signature recalculable.
- `X-ComfyStudio-Livraison` est **le même d'un essai à l'autre** : un essai
  dont la réponse s'est perdue a peut-être été traité, et c'est sur lui qu'on
  déduplique.

Sans rappel, rien n'est perdu : le rendu se relit par son identifiant. Le rappel
est une commodité, pas la seule voie.

### Vérifier la signature

L'URL d'un webhook est publique pour qui la connaît — elle passe dans les
journaux, dans les captures d'écran. **Vérifie la signature**, sinon n'importe
qui qui a lu l'URL peut te faire croire qu'un rendu est fini.

Le format est celui de Stripe, que GitHub et la plupart des recettes n8n
imitent : `t=<horodatage>,v1=<hex>`, où `<hex>` est le **HMAC-SHA256**, avec le
**secret de rappel** de la clé (montré une fois, à la création), de la chaîne
`<t>.` suivie des **octets bruts** du corps. L'horodatage est dans ce qui est
signé : un corps volé ne se rajeunit pas en changeant `t=`. Refuse un `t` à plus
de **cinq minutes** de ton horloge, dans un sens comme dans l'autre.

**Calcule sur les octets reçus, jamais sur le JSON relu puis réécrit** : un
espace de plus et la signature tombe à côté.

En Python, `rappels.signature_valide()` n'importe que la bibliothèque standard
et se recopie telle quelle :

```python
import rappels   # le fichier du dépôt, ou sa fonction recopiée

corps = await request.read()                        # les OCTETS reçus
entete = request.headers.get("X-ComfyStudio-Signature")
if not rappels.signature_valide(SECRET_DE_RAPPEL, entete, corps):
    return web.Response(status=401)
```

Ou son équivalent nu :

```python
import hashlib, hmac, time

def signature_valide(secret, entete, corps, tolerance=300):
    champs = [m.strip().partition("=") for m in (entete or "").split(",")]
    t = [v for k, _, v in champs if k == "t"]
    v1 = [v for k, _, v in champs if k == "v1"]
    if len(t) != 1 or not t[0].isdigit() or not v1:
        return False
    if abs(time.time() - int(t[0])) > tolerance:
        return False
    attendu = hmac.new(secret.encode(), t[0].encode() + b"." + corps,
                       hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(attendu, v) for v in v1)
```

Dans un nœud **Code** de n8n (JavaScript, mode « Run Once for All Items »),
derrière un nœud Webhook dont l'option **« Raw Body »** est cochée — sans elle, le corps arrive déjà décodé,
et un `JSON.stringify` ne redonne pas les mêmes octets. Le module `crypto` doit
être autorisé : `NODE_FUNCTION_ALLOW_BUILTIN=crypto` dans l'environnement de n8n.

```javascript
const crypto = require('crypto');
const secret = $env.COMFYSTUDIO_SECRET_RAPPEL;   // le secret de rappel de la clé
const entete = $input.first().json.headers['x-comfystudio-signature'] || '';
const brut = (await this.helpers.getBinaryDataBuffer(0, 'data')).toString('utf8');

const champs = Object.fromEntries(entete.split(',').map(m => m.trim().split('=')));
const t = Number(champs.t);
const attendu = crypto.createHmac('sha256', secret)
  .update(`${champs.t}.${brut}`).digest('hex');

const juste = champs.v1 && champs.v1.length === attendu.length
  && crypto.timingSafeEqual(Buffer.from(champs.v1), Buffer.from(attendu));
if (!juste || Math.abs(Date.now() / 1000 - t) > 300) {
  throw new Error('rappel ComfyStudio : signature refusée');
}
return [{ json: JSON.parse(brut) }];
```

Selon ta version de n8n, le corps brut se lit aussi dans
`$binary.data.data` (base64) ; l'important est de signer **ces octets-là**.

### Les essais

Quatre essais en deux minutes et demie : tout de suite, puis après **5 s**,
**30 s** et **120 s**. Chaque essai est **signé à nouveau** avec l'heure de
l'essai — l'horodatage d'origine approcherait sinon les cinq minutes de
tolérance. Le studio attend **10 s** une réponse : un nœud Webhook de n8n répond
dès réception ; un récepteur qui met plus longtemps doit faire son travail
lourd après avoir répondu.

| Réponse du récepteur | Ce que fait le studio |
|---|---|
| 2xx | livré, terminé |
| 408, 409, 425, 429, 5xx, délai dépassé, injoignable | nouvel essai |
| 3xx | **abandonne** : une redirection n'est jamais suivie |
| tout autre 4xx | abandonne : un refus raisonné (mauvaise signature, URL périmée) ne changera pas en insistant |

**409 est réessayé à cause de n8n.** L'adresse de reprise d'un nœud Wait existe
dès le début de l'exécution, avant que celle-ci ait *atteint* le Wait. Un rendu
qui finit dans cet intervalle trouve une exécution encore en cours, et n8n
répond **409** (« is running already ») — c'est son « pas encore ». Le même 409
veut aussi dire « exécution déjà finie », et n8n ne les distingue que par le
texte du message : le studio réessaie donc tout 409, quitte à envoyer trois
POST de trop à une exécution terminée, que n8n refuse sans rien exécuter. Les
vrais refus de n8n — **404** (exécution inconnue, ou Wait qui n'attend pas
cette méthode) et **401** (jeton de reprise invalide) — arrêtent les essais.
Corollaire pour ton propre récepteur : **un doublon reconnu sur
`X-ComfyStudio-Livraison` se répond en 2xx**, pas en 409, sinon le studio
insiste deux minutes et demie pour rien.

Le **journal du studio** — pas le fil du rendu, que la clé relit — dit ce qui
s'est passé : `rappel livre a n8n.maison (1 essai(s))`, ou `rappel non livre a
…` avec la raison et le nombre d'essais. Dans le fil du rendu, « injoignable »
ou « délai dépassé » auraient fait du rappel une sonde de ports : une clé volée
aurait balayé une machine déclarée et lu les réponses. **L'hôte, jamais
l'adresse** : une URL de webhook n8n porte un identifiant qui sert de secret. Une clé révoquée pendant
le rendu ne signe plus rien : le rappel n'est pas envoyé.

### Essayer son branchement — `POST /api/v1/rappels/essai`

Pour vérifier qu'un nœud Webhook de n8n reçoit le studio, et que ta
vérification de signature est juste, **sans lancer de rendu** :

```bash
curl -X POST -H "Authorization: Bearer cs_…" -H "Content-Type: application/json"   -d '{"rappel": "http://n8n.maison:5678/webhook-test/comfystudio"}'   http://STUDIO:8199/api/v1/rappels/essai
```

Le studio envoie un événement `rappel.essai`, signé exactement comme un vrai
(`id` vaut `null`, un champ `message` remplace `rendu`), en **un seul essai**,
et répond tout de suite :

```json
{"evenement": "rappel.essai", "livre": true, "statut": 200, "raison": "livre"}
```

L'hôte doit être déclaré dans la clé, comme pour un vrai rappel. Ici l'issue
**revient** au programme — sans elle l'essai ne sert à rien —, et ce n'est pas
la sonde de ports évoquée plus haut : on ne peut essayer que les hôtes et ports
que le propriétaire a nommés. Un essai toutes les dix secondes par clé, au-delà
**429** `trop_d_essais`. Un récepteur doit reconnaître `rappel.essai` et n'en
rien faire.

### Un redémarrage ne perd pas un rappel

Une livraison peut durer deux minutes et demie (quatre essais). Elle est
inscrite sur le disque (`_rappels.json`) **dès qu'elle commence**, et retirée
quand elle a fini — livrée, refusée, ou la clé révoquée —, mais **pas** quand le
studio s'arrête : c'est précisément le cas à rattraper. Au démarrage suivant, le
studio la reprend **avec le même identifiant de livraison** : si le premier
essai était arrivé avant l'arrêt, ton workflow reconnaît le doublon sur
`X-ComfyStudio-Livraison` au lieu de lancer deux fois sa suite. Déduplique donc
sur cet en-tête. Ce n'était pas le cas au premier jet : un arrêt pendant les
essais perdait le rappel, et le nœud Wait attendait jusqu'à son délai.

### Pourquoi les hôtes sont déclarés

**C'est la défense contre la requête forgée côté serveur.** Le studio vit sur
le réseau de la maison : une URL de rappel choisie librement le ferait POSTer
n'importe où chez toi — le routeur, une console d'administration, le NAS
lui-même — au nom de quiconque a une clé. L'URL de rappel n'est donc acceptée
que si son **hôte figure dans la liste déclarée à la création de la clé**, avec
le mot de passe : quelqu'un qui vole la clé ne peut pas l'étendre. **Liste
vide, aucun rappel** : « pas de liste, pas de restriction » serait exactement la
panne à empêcher.

- Un hôte, pas une URL : `n8n.maison:5678`, `172.20.1.50:5678`, `[::1]:5678`.
  **Avec un port, il vaut pour ce seul service ; sans port, pour le port par
  défaut du schéma seulement** — 80 en `http`, 443 en `https`. Un n8n qui
  écoute sur 5678 se déclare donc `hôte:5678`. Ce n'était pas le cas au premier
  jet : une entrée sans port valait pour tous les ports, et déclarer la machine
  de son n8n laissait une clé volée viser son ComfyUI (8188) ou sa console
  d'administration (revue de sécurité du 4 novembre 2026).
- La comparaison est **textuelle** : aucun nom n'est résolu. `localhost` et
  `127.0.0.1` sont deux hôtes ; déclare celui que l'URL portera.
- Sont refusés aussi : un autre schéma que `http` ou `https`, des identifiants
  dans l'URL (`http://hote.autorise@ailleurs/`, le piège classique), et toute
  URL qui contient une barre inverse, un espace ou un caractère de contrôle —
  deux lecteurs d'URL peuvent les découper différemment.
- **Aucune redirection n'est suivie** : sa cible n'est pas dans la liste.

## n8n pas à pas

D'abord, dans n8n : **Credentials → New → Header Auth**, nom « ComfyStudio »,
*Name* `Authorization`, *Value* `Bearer cs_…` (ta clé entière). Le credential
reste dans n8n ; le workflow exporté n'en porte que le nom.

### Recette prête à importer : demander, attendre, télécharger

Un workflow prêt à importer est dans le dépôt :
[`exemples/n8n-rendu-comfystudio.json`](../exemples/n8n-rendu-comfystudio.json)
(*Workflows → Import from File*). Remplace `http://STUDIO:8199` par l'adresse de
ton studio dans ses trois nœuds HTTP, et choisis-y le credential « ComfyStudio »
— le fichier n'en porte que le nom, jamais la clé.

Il est plus long que les trois nœuds qu'il faudrait pour un essai, parce qu'un
workflow qui tourne seul la nuit rencontre tout ce que cette page décrit. Chaque
nœud de plus répond à un cas réel :

1. **Demander le rendu** — `POST /api/v1/rendus` avec
   `{"demande": "…", "attendre": 300}`, et trois réglages :
   - l'en-tête **`Idempotency-Key: {{ $execution.id }}`**. Le nœud a *Retry On
     Fail* : sans l'en-tête, chaque essai lancerait un rendu de plus ; avec lui,
     les essais d'une même exécution désignent le même rendu, même après un
     redémarrage du studio ([plus haut](#ne-pas-lancer-deux-fois-le-même-rendu--idempotency-key)) ;
   - un **timeout de 330 000 ms**, au-dessus d'`attendre` : à 300 s, n8n
     couperait la connexion à la seconde où le studio répond. Si tu montes
     `attendre`, monte le timeout avec — dix secondes de marge au moins ;
   - dans *Options → Response*, **« Include Response Headers and Status »** et
     **« Never Error »**. Sans « Never Error », n8n lève sur un 429 avant
     qu'aucun nœud n'ait pu lire `reessayer_dans`, et la branche qui devait le
     traiter n'est jamais prise. Conséquence à ne pas oublier : le rendu est
     alors dans **`$json.body`**, et `$json.etat` ne vaut rien — c'est
     `$json.body.etat`.
2. **Statut de la réponse** — un Switch sur `{{ $json.statusCode }}` :
   - **200 ou 202** : le rendu, final ou pas encore ;
   - **429** : un If vérifie que **`reessayer_dans` existe** (et qu'il ne dépasse
     pas un quart d'heure), puis un Wait de `reessayer_dans` secondes ramène au
     POST, cinq fois au plus. **Sans `reessayer_dans`, on ne réessaie pas** : le
     studio l'omet exprès quand attendre n'y changerait rien (plus de variantes
     que le plafond `en_file` lui-même), et un réessai bouclerait jusqu'à sa
     borne. Le quart d'heure écarte `cle_plafond_jour`, dont le délai court
     jusqu'à minuit : une exécution qui dort dix heures n'aide personne ;
   - **tout le reste** s'arrête sur un nœud *Stop and Error* qui nomme le
     `code` : la même requête aurait la même réponse.
3. **Aiguiller sur l'état** — un Switch sur `{{ $json.body.etat }}`, une branche
   par état final :
   - `fini` → un If sur `fichiers.length` (une lecture d'image rend une
     `description` et aucun fichier), puis **Télécharger le premier fichier** :
     `GET /api/v1/rendus/{{ $json.body.id }}/fichiers/0`, *Response Format*
     « File », binaire dans `data` ;
   - `question` → un nœud à brancher sur ta réponse
     ([`.../reponse`](#répondre-à-une-question--post-apiv1rendusidreponse)) ;
   - `erreur` → *Stop and Error* avec `erreur.code` et `erreur.message`, sans
     relancer : la même demande échouerait de la même façon ;
   - `annule` → rien à faire.
4. **Pas encore final** (`en_file`, `en_cours`, `attente_machine`, la branche de
   repli du Switch) → **Relire le rendu**, `GET /api/v1/rendus/{id}?attendre=300`,
   et retour à l'aiguillage. **Six fois au plus**, par un If sur
   `{{ $runIndex }}` : un rendu en `attente_machine` peut attendre sa machine
   des heures, et une boucle sans borne relirait le studio jusqu'au lendemain.
   Au-delà, l'exécution s'arrête en le disant ; le rendu, lui, n'est pas perdu
   et se relit plus tard par son `id`.

L'adresse du téléchargement est **écrite**, l'`id` seul vient de la réponse :
le credential pose la clé sur toute requête du nœud, et une adresse lue dans un
corps la ferait partir là où ce corps le dit. C'est sans conséquence ici — la
réponse vient du studio —, mais c'est la règle qui protège la variante par
rappel, dont le corps n'est pas vérifié.

`banc_exemples.py` relit ce fichier et son voisin à chaque poussée et les
confronte au [contrat OpenAPI](#le-contrat-openapi) : une route renommée, un
champ que le studio ne lit pas, un état final ajouté au contrat sans branche
dans l'exemple, un 429 réessayé sans délai, un timeout sous `attendre` ou une
clé collée dans une note le font rougir.

### Sans attendre : le rappel

Pour un rendu long, ne garde pas une connexion ouverte : laisse le studio
prévenir le workflow.

La même chose prête à importer :
[`exemples/n8n-rappel-comfystudio.json`](../exemples/n8n-rappel-comfystudio.json)
— un Switch sur les quatre événements de fin plus `rappel.essai`, ignoré, une
relecture par `GET /api/v1/rendus/{id}` quand c'est le délai qui réveille
l'exécution, et un téléchargement construit sur l'`id` du POST plutôt que sur
l'adresse lue dans le rappel.

1. **HTTP Request** `POST /api/v1/rendus`, **sans** `attendre`, avec :

   ```json
   {"demande": "une petite vidéo d'un renard qui court",
    "rappel": "{{ $execution.resumeUrl }}"}
   ```

2. **Wait** — *Resume* « On Webhook Call », *HTTP Method* `POST`. L'exécution
   s'endort ; le rappel du studio la réveille, et l'événement arrive dans
   `$json.body` (`body.evenement`, `body.rendu.fichiers`…). Règle *Limit Wait
   Time* (une heure, par exemple) : un rappel peut se perdre (voir [Ce qui n'est
   pas fait](#ce-qui-nest-pas-fait)), et une exécution ne doit pas dormir pour
   toujours. Au réveil par le délai, lis le rendu par `GET /api/v1/rendus/{id}`.
   **Place le Wait juste après le POST.** Un rendu très court peut finir avant
   que l'exécution soit arrivée au Wait : n8n répond alors 409 au rappel, et le
   studio réessaie après 5 s, 30 s et 120 s ([Les essais](#les-essais)). Un
   nœud lent entre les deux allonge cette fenêtre ; au-delà de deux minutes et
   demie, c'est la limite d'attente et la relecture qui prennent le relais.
3. Un **Switch** sur `{{ $json.body.evenement }}`, puis le téléchargement de
   `http://STUDIO:8199/api/v1/rendus/{{ $('Demander le rendu').first().json.id }}/fichiers/0`
   — l'adresse du studio écrite, l'`id` du POST. **Ne fais pas suivre au
   credential une adresse lue dans le rappel** (`body.rendu.fichiers[0].url`)
   tant que la signature n'est pas vérifiée : le corps vient de qui connaît
   l'URL de reprise, et le credential y poserait ta clé.

Avec un nœud **Webhook** séparé plutôt que Wait, mets son *Production URL* dans
`rappel` et laisse *Respond* sur « Immediately ».

**L'hôte de cette URL doit être déclaré dans la clé.** `$execution.resumeUrl`
et l'URL d'un Webhook sont construites sur l'adresse publique que n8n se
connaît (`WEBHOOK_URL`) : c'est **cet** hôte-là, avec son port s'il en a un, qui
va dans la liste — pas l'adresse par laquelle tu ouvres l'éditeur, si elles
diffèrent.

### Les réessais

Sur le nœud qui lance le rendu, *Settings* → **Retry On Fail** (trois essais,
cinq secondes d'écart, par exemple) rattrape un studio qui redémarre. Pour un
429, lis plutôt `Retry-After` (ou `reessayer_dans`) : il dit combien attendre. **Pose
alors un `Idempotency-Key`** — *Send Headers*, nom `Idempotency-Key`, valeur
`{{ $execution.id }}` : les essais d'une même exécution désignent le même rendu
au lieu d'en lancer trois — **y compris après un redémarrage du studio** :
le registre des clés est sur le disque, et garde chacune 24 heures. Ne
reprends pas un 4xx en boucle : `code` dit pourquoi, et la même requête aura
la même réponse. Un 429 `cle_file_pleine`
se reprend plus tard ; `cle_refusee` jamais.

## Assistants IA par MCP

Un assistant IA — Claude Code, Claude Desktop, un agent n8n — sait appeler des
**outils**. Le studio en sert sept, par le protocole MCP, à l'adresse
**`/mcp`**, avec la même clé dans le même en-tête.

| Outil | Rôle |
|---|---|
| `generer_rendu` | Lance un rendu (`demande`, et au choix `moteur`, `taille`, `priorite`, `image_base64` + `image_type`, `conversation`, `attendre`). Rend le résultat s'il est prêt dans le délai, sinon un identifiant. |
| `etat_rendu` | Donne l'état d'un rendu et ses fichiers, en attendant sa fin au plus `attendre` secondes. |
| `repondre_question` | Transmet la réponse de l'utilisateur à un rendu dans l'état `question` ; un nouveau rendu part. |
| `annuler_rendu` | Retire un rendu de la file, ou l'interrompt. |
| `lister_rendus` | Les derniers rendus de cette clé — pour retrouver ce qui a été fait tout à l'heure. |
| `lister_moteurs` | Les moteurs que cette clé peut demander, avec ce qu'ils font. |
| `decrire_cle` | Ce que cette clé permet, **avant d'essayer** : opérations, nuage, rendus en file, plafond du jour et celui de chaque famille (et ce qui reste), date de fin. Les mêmes champs que `GET /api/v1/moi`. |

**Un outil attend 45 secondes par défaut**, et non dix minutes : le SDK MCP
TypeScript — celui de Claude Desktop et de la plupart des clients — annule une
requête au bout de 60 s. Un outil qui attend plus longtemps ne rend jamais rien
à l'assistant ; mieux vaut rendre l'identifiant et le laisser rappeler
`etat_rendu`. Les instructions servies à l'initialisation le lui disent.

Le résultat d'un outil porte un texte (l'état, les questions, et chaque **lien
signé** en clair, pour que l'assistant ait une adresse à donner), **les images
elles-mêmes** quand elles pèsent moins de 3 Mio — l'API de Claude refuse une
image de plus de 5 Mo une fois encodée, et le base64 grossit d'un tiers —, un
bloc `resource_link` par fichier, et le rendu entier en contenu structuré.

**Claude Code** :

```sh
claude mcp add --transport http comfystudio http://192.0.2.10:8199/mcp \
  --header "Authorization: Bearer cs_…"
```

**Un client qui lit un fichier JSON de serveurs MCP** — le `.mcp.json` d'un
projet Claude Code, et la plupart des clients qui acceptent le transport HTTP :

```json
{"mcpServers": {
  "comfystudio": {
    "type": "http",
    "url": "http://192.0.2.10:8199/mcp",
    "headers": {"Authorization": "Bearer cs_…"}}}}
```

**Un agent n8n** : sous le nœud *AI Agent*, ajoute un outil **MCP Client Tool**,
*Endpoint* `http://STUDIO:8199/mcp`, transport « HTTP Streamable » (les
versions de n8n qui n'offrent que « SSE » ne conviennent pas : le studio n'a
pas de flux SSE), et
l'authentification par en-tête — *Header Auth*, le même credential que plus
haut. L'agent voit les sept outils et choisit seul.

Pour vérifier à la main :

```sh
curl -s "$STUDIO/mcp" -H "Authorization: Bearer $CLE" \
  -H "Content-Type: application/json" -H "MCP-Protocol-Version: 2025-06-18" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}'
```

**Ce qui n'est pas pris en charge, franchement :**

- **La révision MCP 2026-07-28**, la plus récente de la spec. Le studio parle
  2025-11-25, 2025-06-18 et 2025-03-26, celles qui ouvrent par `initialize`.
  2026-07-28 supprime `initialize` et `ping`, et exige des champs dans chaque
  requête et chaque résultat : c'est un autre protocole, pas une option du
  premier, et le déclarer sans en suivre les règles mentirait au client. Un
  client des deux époques qui l'essaie d'abord reçoit un 400 dont le corps est
  une erreur JSON-RPC ordinaire (`-32600`) — **exprès**, et non l'erreur
  moderne `-32022` : c'est ce qui le fait retomber sur `initialize`, comme la
  spec le prévoit. Un client qui ne parle **que** 2026-07-28 ne se connectera
  pas.
- **Pas de flux SSE** : un message JSON-RPC par POST, une réponse JSON. Aucun
  outil d'ici n'a rien à pousser en cours de route ; un rendu long se suit par
  `etat_rendu`. `GET /mcp` répond 405.
- Pas de session (`MCP-Session-Id`), pas de lot JSON-RPC, ni ressources, ni
  prompts : des outils seulement.

## Brancher Open WebUI, LibreChat ou un SDK OpenAI

Beaucoup d'outils savent parler à « une API d'images OpenAI » dès qu'on leur
donne **une adresse de base et une clé**. Le studio leur ouvre cette porte :

| À renseigner | Valeur |
|---|---|
| Base URL | `http://STUDIO:8199/openai/v1` |
| Clé (API key) | une clé d'accès du studio, `cs_…` — avec la famille « créer une image » (et « retoucher une image » pour les retouches) |
| Modèle | `comfystudio` (le studio choisit), ou un moteur de `GET /openai/v1/models` |

La page les donne toutes faites : bouton **« clés d'accès »**, section
**« Brancher un outil »**, un bouton « copier » pour chacune des trois bases —
`/api/v1` (n8n, scripts), `/openai/v1` (cette porte-ci) et `/mcp` (Claude).
Elles partent de `STUDIO_ADRESSE_PUBLIQUE` si elle est posée
([Réglages](reglages.md)), sinon de l'adresse de la page ; aucune ne contient
la clé.

Les images sortent **des cartes de la maison**, sous les règles de la clé :
mêmes plafonds (`en_file`, `par_jour`), même droit au nuage, même garde-fou,
mêmes familles d'opérations — ce n'est pas une porte à côté, c'est la même
porte avec un autre accent. Trois routes :

- `POST /openai/v1/images/generations` — créer des images (famille « image ») ;
- `POST /openai/v1/images/edits` — retoucher une image envoyée en
  `multipart/form-data` (famille « retouche ») ;
- `GET /openai/v1/models` — la liste que les clients affichent.

**Open WebUI** : *Réglages d'administration > Images*, moteur « OpenAI »,
*OpenAI API Base URL* `http://STUDIO:8199/openai/v1`, la clé dans *OpenAI API
Key*, modèle `comfystudio`. Open WebUI demande du `b64_json` ; il recopie
l'image chez lui.

**LibreChat** : son outil d'images OpenAI se règle dans le `.env` —
`IMAGE_GEN_OAI_BASEURL=http://STUDIO:8199/openai/v1`,
`IMAGE_GEN_OAI_API_KEY=cs_…`, et `IMAGE_GEN_OAI_MODEL=comfystudio` (relu dans
son `.env.example` le 5 novembre 2026). Le même outil sert les retouches, par
`/images/edits`.

**Un SDK openai** (Python, mais le SDK Node prend les mêmes deux réglages) :

```python
from openai import OpenAI
client = OpenAI(base_url="http://STUDIO:8199/openai/v1", api_key="cs_…")
image = client.images.generate(model="comfystudio", prompt="un phare dans la brume",
                               size="1536x1024", response_format="b64_json")
```

**n8n** : le nœud *OpenAI* avec un credential dont la *Base URL* est la même ;
ou le nœud *HTTP Request* en `POST` sur `…/openai/v1/images/generations`, le
credential *Header Auth* déjà fait pour `/api/v1`.

**Ce que deviennent les champs d'OpenAI :**

| Champ | Ce que le studio en fait |
|---|---|
| `prompt` | la demande, analysée comme une demande de la page, dans sa langue |
| `model` | un moteur d'image du studio s'il existe (`klein4b`, `flux1`…) ; tout autre nom — `dall-e-3`, `gpt-image-1`, `comfystudio` — est **ignoré** : le studio choisit. Sur `/images/edits`, « le studio choisit » veut dire le moteur d'**édition** : la route ne laisse pas l'analyse décider, qui lisait « le ciel en rose » comme une image neuve |
| `n` | autant de variantes, de 1 à 4 ; chacune compte dans `en_file` et `par_jour`. Ignoré pour une retouche (une seule) |
| `size` | ramenée à la taille du studio la plus proche, **le cadrage d'abord** : `1536x1024` → `1216x832`, `1024x1536` → `832x1216`, `1024x1792` → `768x1344`, `512x512` → `1024x1024` ; `auto` laisse choisir. Ignorée pour une retouche |
| `response_format` | `b64_json` : l'image en base64 (au-delà de 16 Mio, un lien à la place) ; `url` : un **lien signé absolu**, valable 24 h, sans en-tête. Sans le champ : `url` pour un modèle `dall-e-*`, `b64_json` sinon — comme chez OpenAI |
| `quality` | `low` → rapide ; `high`, `hd` → soigné ; le reste, défaut |
| `style`, `user`, `background`, `moderation`, `output_format`… | acceptés, ignorés |
| `stream` | `true` est refusé : le studio ne diffuse pas d'images partielles |
| `mask` (edits) | lu et écarté : aucun moteur d'ici ne prend un masque OpenAI |

`revised_prompt` porte le prompt que le studio a réellement rendu — après
analyse, enrichissement et traduction.

**C'est synchrone** : la réponse attend la fin du rendu, **540 s au plus** —
sous les 600 s après lesquelles le SDK openai coupe, puis **réessaie**, ce qui
aurait lancé une seconde image. Au-delà, un 504 `delai_depasse` dont le
message donne l'identifiant du rendu : il continue, il se retrouve dans la
page ou par `GET /api/v1/rendus/{id}`. `Idempotency-Key` vaut ici comme sur
`/api/v1/rendus` (même registre).

**Derrière un proxy, son délai compte aussi.** nginx coupe une réponse au
bout de 60 s par défaut, nginx-proxy-manager au bout de 90 s : une image plus
longue revient en 504 du proxy, et le SDK la redemande. Le SDK openai
n'envoie pas d'`Idempotency-Key`, mais il numérote ses essais
(`x-stainless-retry-count`) : un essai qui se dit réessai, sous la même clé
et pour la même demande, **rejoint le rendu déjà lancé** au lieu d'en lancer
un autre. Deux demandes identiques qui ne se disent pas réessai restent deux
rendus. Le réessai ne fait pourtant que gagner du temps : pour qu'une image
longue arrive du premier coup, montez le délai du proxy au-dessus de 540 s —
dans nginx-proxy-manager, onglet *Advanced* de l'hôte :

```nginx
proxy_read_timeout 600s;
proxy_send_timeout 600s;
```

**Le studio ne pose pas de question à
ces clients** : Open WebUI ou un SDK n'ont aucune façon d'y répondre, et « un
chat » leur revenait en erreur. Là où la page demanderait une précision, il
rend sa meilleure lecture de la demande. Le 400 `question` ne reste qu'en filet,
pour un rendu repris d'avant cette règle.

**Les erreurs sont au format d'OpenAI**, `{"error": {"message", "type",
"param", "code"}}`, avec le statut qui va : 401 sans clé ou avec une clé
refusée, 403 pour une clé sans la famille de la route, 429 sur un plafond (avec
`Retry-After`), 400 sur un champ faux (`param` le nomme). `code` reste **le
code stable du studio** (`cle_file_pleine`, `refus_mineurs`…) : le tableau des
refus ci-dessus vaut, plus six codes propres à cette porte (`flux_refuse`,
`attentes_pleines`, `delai_depasse`, `question`, `sans_image`, `panne`),
décrits dans le contrat OpenAPI. **`X-Should-Retry: false`** accompagne tout ce
que le SDK ne doit pas rejouer de lui-même : un 5xx (le rendu est peut-être
déjà parti), un 429 sans délai, ou dont le délai dépasse une minute — le
plafond du jour ne se lève pas en huit secondes.

**Ce que cette porte ne fait pas** : le chat (`/chat/completions`), les
variations (`/images/variations`), le flux, l'image par URL ; une retouche ne
prend que la première image envoyée. Et la sécurité est celle de `/api/v1` :
**HTTP en clair** — derrière un reverse proxy TLS dès qu'on sort de la maison.

## Ce qui est gardé comme dans la page, et ce qui est propre aux programmes

**Comme dans la page** — une demande venue d'un programme passe par la même
validation et les mêmes règles :

- **le garde-fou des mineurs**, et ici **avant la file** : un refus en 422
  `refus_mineurs` au lieu d'un rendu `erreur` découvert au sondage suivant, déjà
  compté dans le plafond du jour ([Contenu adulte](contenu-adulte.md)) ;
- **le contenu adulte ne sort jamais vers le nuage**, quel que soit le moteur
  demandé et le droit de la clé ;
- **le plafond du nuage du compte** ([Ce que le nuage a coûté](cout-du-nuage.md))
  vaut pour ses programmes comme pour lui.

**Propre aux programmes** — **le nuage est interdit par défaut à une clé**, et
interdit **jusqu'à l'analyse** : une demande d'une clé sans nuage n'appelle pas
non plus le modèle de langage distant qui aiguille et réécrit. Garder seulement
le rendu en local aurait tenu la promesse à moitié — pas d'image facturée, mais
un appel facturé à chaque demande, et c'est le seul des deux qu'on ne voit pas.
Un moteur distant demandé explicitement par une telle clé est refusé
(`cle_sans_nuage`) ; un moteur distant que l'aiguillage aurait choisi retombe
sur le moteur local, et le journal du rendu le dit.

## Le chiffrement

**Une clé d'accès passe en clair sur le réseau, comme un cookie de session** :
le studio écoute en HTTP simple. Sur `127.0.0.1` ou un réseau dont tu réponds,
c'est le même risque que pour la page. Au-delà, mets le studio derrière un
reverse proxy qui termine le TLS ([SECURITY.md](../SECURITY.md)) ; les adresses
rendues (`url`, `lien`) suivent `X-Forwarded-Proto` et `X-Forwarded-Host`, et
seront donc en `https://` pour le programme.

Un rappel vers une URL `http://` se lit aussi en route : la signature prouve
l'origine et l'intégrité, pas la confidentialité.

## Le contrat OpenAPI

`GET /api/v1/openapi.json`, **sans clé**, rend un document **OpenAPI 3.1** qui
décrit chaque route de `/api/v1`, `/mcp`, les trois routes compatibles OpenAI
(`/openai/v1`, avec leurs schémas `OpenAI*` à part), les schémas `Rendu`, `Fichier`,
`Refus`, chaque code de refus avec son statut, et le rappel comme webhook. Il
porte l'adresse du studio telle que tu l'as jointe. C'est ce qu'un assistant IA
ou un outil qui importe une API (Postman, un générateur de client) sait lire.

Il est écrit à la main (`contrat.py`), et `banc_contrat.py` le confronte au
routeur et au texte de `serveur.py` dans les deux sens : une route, un état, un
champ ou un code ajoutés d'un seul côté le font rougir.

## Ce qui n'est pas fait

- **Pas d'image par URL.** Le studio ne va pas chercher une image à l'adresse
  qu'un programme lui donne : ce serait la requête forgée que la liste des
  hôtes de rappel empêche, par une autre porte. Envoie les octets —
  `POST /api/v1/fichiers` ou `image_base64`.
- **Le freinage des clés refusées vit en mémoire** : un redémarrage le remet
  à zéro. Le reste survit — le plafond `par_jour` est compté sur les
  conversations, le registre d'idempotence est sur le disque
  (`_idempotence.json`), les rendus en attente et les rappels en cours de
  livraison sont repris au démarrage.
