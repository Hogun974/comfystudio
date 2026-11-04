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
  4 par défaut) et `par_jour` (de 0 à 10 000, 0 pour « sans plafond »).

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
           "par_jour": 0, "generation": 0}}
```

`GET /api/compte/acces` liste les clés du compte, chacune avec `active` ;
`DELETE /api/compte/acces/{id}` en révoque une. Ces trois routes veulent une
**session**, jamais une clé : une clé qui listerait les clés en ferait
connaître l'existence à qui l'a volée.

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
de dernier usage et le nombre de rendus en cours de chacune — jamais la clé.

## Les quatre règles

1. **La clé ne vaut que sur `/api/v1/` et `/mcp`.** Présentée ailleurs, elle est
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

Pourquoi 600 secondes et pas une heure : le nœud HTTP Request de n8n coupe à
300 s par défaut (on peut le monter), et un rendu vidéo sur la 2080 Ti dure
trois à huit minutes ([Mesures](mesures.md)). Au-delà, sonde ou prends le
rappel : garder une connexion ouverte une heure n'est un service pour personne.

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
| `erreur` | **oui** | Lire `erreur.code` et `erreur.message`. Ne pas relancer en boucle : la même demande échouera de la même façon. |
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

`present: false` : ses modèles ne sont sur aucune machine. Les moteurs distants
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
         "par_jour": 0, "generation": 0},
 "en_cours": 0, "aujourdhui": 0, "attendre_max": 600}
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
rendrait `en_cours` sur-le-champ casserait le workflow qu'il devait sauver. Le
registre vit en mémoire : un redémarrage du studio l'oublie.

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
| `cle_hors_perimetre` | 403 | une clé présentée hors de `/api/v1` et `/mcp` |
| `trop_d_essais` | 429 | trop de clés refusées depuis cette adresse ; attendre |
| `corps_illisible` | 400 | le corps n'est pas un objet JSON |
| `attendre_bornes` | 400 | `attendre` hors de 0 à 600 |
| `idempotence_illisible` | 400 | `Idempotency-Key` de plus de 200 caractères |
| `cle_file_pleine` | 429 | plafond `en_file` atteint |
| `cle_plafond_jour` | 429 | plafond `par_jour` atteint |
| `champ_illisible` | 400 | un champ n'a pas la forme attendue (la phrase le nomme) |
| `rappel_refuse` | 400 | adresse de rappel refusée ; la phrase dit pourquoi : `hote`, `schema`, `identifiants`, `illisible` |
| `image_illisible` | 400 | `image_base64` n'est pas du base64 |
| `fichier_vide` | 400 | image vide |
| `fichier_trop_lourd` | 413 | image au-delà de 32 Mo |
| `conversation_inconnue` | 404 | aucune conversation ouverte **de cette clé** ne porte cet identifiant |
| `cle_sans_nuage` | 400 | moteur distant demandé, et la clé n'a pas droit au nuage |
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

Le contrat OpenAPI ne décrit que les codes propres aux programmes (la première
table) ; ceux-ci sont les mêmes que ceux de la page.

**Seuls les refus de `POST /api/v1/fichiers` n'ont pas de code** (aucun
fichier, format refusé, fichier vide : 400 ; trop lourd : 413) : cette route
est celle de la page, reprise telle quelle. Un corps JSON de plus de 4 Mio est
refusé en **413** par le serveur HTTP lui-même, avec un corps texte.

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
| 408, 425, 429, 5xx, délai dépassé, injoignable | nouvel essai |
| 3xx | **abandonne** : une redirection n'est jamais suivie |
| tout autre 4xx | abandonne : un refus raisonné (mauvaise signature, URL périmée) ne changera pas en insistant |

Le **journal du studio** — pas le fil du rendu, que la clé relit — dit ce qui
s'est passé : `rappel livre a n8n.maison (1 essai(s))`, ou `rappel non livre a
…` avec la raison et le nombre d'essais. Dans le fil du rendu, « injoignable »
ou « délai dépassé » auraient fait du rappel une sonde de ports : une clé volée
aurait balayé une machine déclarée et lu les réponses. **L'hôte, jamais
l'adresse** : une URL de webhook n8n porte un identifiant qui sert de secret. Une clé révoquée pendant
le rendu ne signe plus rien : le rappel n'est pas envoyé.

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

### Recette simple : demander, attendre, télécharger

Un workflow prêt à importer est dans le dépôt :
[`exemples/n8n-rendu-comfystudio.json`](../exemples/n8n-rendu-comfystudio.json)
(*Workflows → Import from File*). Remplace `http://STUDIO:8199` par l'adresse de
ton studio, et choisis ton credential dans les deux nœuds HTTP.

1. **Manual Trigger** (ou n'importe quel déclencheur).
2. **HTTP Request** — *Method* `POST`, *URL* `http://STUDIO:8199/api/v1/rendus`,
   *Authentication* « Generic Credential Type » → « Header Auth », *Send Body*
   en JSON :

   ```json
   {"demande": "un renard roux dans la neige au crépuscule", "attendre": 300}
   ```

   Dans *Options*, monte *Timeout* au-dessus d'`attendre` — 330 000 ms pour
   300 s —, sinon n8n coupe avant que le studio ait répondu.
3. **HTTP Request** — *Method* `GET`, *URL* `{{ $json.fichiers[0].url }}`, même
   credential, et dans *Options* → *Response* : *Response Format* « File ». Le
   fichier arrive en binaire dans `data`, prêt pour un nœud qui l'enregistre ou
   l'envoie.

Si le rendu n'est pas fini dans le délai, la réponse arrive quand même, en 202,
avec `fichiers` vide : place un nœud **If** sur `{{ $json.etat }}` égal à
`fini` avant le téléchargement, et traite `question` et `erreur` à part.

### Sans attendre : le rappel

Pour un rendu long, ne garde pas une connexion ouverte : laisse le studio
prévenir le workflow.

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
3. Un **Switch** sur `{{ $json.body.evenement }}`, puis le téléchargement de
   `{{ $json.body.rendu.fichiers[0].url }}` comme dans la recette simple.

Avec un nœud **Webhook** séparé plutôt que Wait, mets son *Production URL* dans
`rappel` et laisse *Respond* sur « Immediately ».

**L'hôte de cette URL doit être déclaré dans la clé.** `$execution.resumeUrl`
et l'URL d'un Webhook sont construites sur l'adresse publique que n8n se
connaît (`WEBHOOK_URL`) : c'est **cet** hôte-là, avec son port s'il en a un, qui
va dans la liste — pas l'adresse par laquelle tu ouvres l'éditeur, si elles
diffèrent.

### Les réessais

Sur le nœud qui lance le rendu, *Settings* → **Retry On Fail** (trois essais,
cinq secondes d'écart, par exemple) rattrape un studio qui redémarre. **Pose
alors un `Idempotency-Key`** — *Send Headers*, nom `Idempotency-Key`, valeur
`{{ $execution.id }}` : les essais d'une même exécution désignent le même rendu
au lieu d'en lancer trois. Ne reprends pas un 4xx en boucle : `code` dit
pourquoi, et la même requête aura la même réponse. Un 429 `cle_file_pleine`
se reprend plus tard ; `cle_refusee` jamais.

## Assistants IA par MCP

Un assistant IA — Claude Code, Claude Desktop, un agent n8n — sait appeler des
**outils**. Le studio en sert cinq, par le protocole MCP, à l'adresse
**`/mcp`**, avec la même clé dans le même en-tête.

| Outil | Rôle |
|---|---|
| `generer_rendu` | Lance un rendu (`demande`, et au choix `moteur`, `taille`, `priorite`, `image_base64` + `image_type`, `conversation`, `attendre`). Rend le résultat s'il est prêt dans le délai, sinon un identifiant. |
| `etat_rendu` | Donne l'état d'un rendu et ses fichiers, en attendant sa fin au plus `attendre` secondes. |
| `repondre_question` | Transmet la réponse de l'utilisateur à un rendu dans l'état `question` ; un nouveau rendu part. |
| `annuler_rendu` | Retire un rendu de la file, ou l'interrompt. |
| `lister_moteurs` | Les moteurs que cette clé peut demander, avec ce qu'ils font. |

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
haut. L'agent voit les cinq outils et choisit seul.

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
décrit chaque route de `/api/v1`, `/mcp`, les schémas `Rendu`, `Fichier`,
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
- **Pas de priorité entre programmes et humains.** La file est commune, dans
  l'ordre d'arrivée ; le plafond `en_file` est la seule chose qui empêche un
  workflow de passer devant tout le monde par le nombre.
- **Un rappel n'est pas persisté.** Un studio qui s'arrête pendant ses essais le
  perd. Le rendu, lui, se relit par son identifiant ; règle un délai au nœud
  Wait.
- **Les compteurs vivent en mémoire** : le freinage des clés refusées, le
  registre d'idempotence, le nombre de rendus en cours. Un redémarrage les remet
  à zéro. Le plafond `par_jour`, lui, est compté sur le disque.
- **Les refus de `POST /api/v1/fichiers` n'ont pas de code** (voir [Les
  refus](#les-refus)) : un programme ne peut s'y brancher que sur le statut.
