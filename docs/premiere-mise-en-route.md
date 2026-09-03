# La première mise en route

Adresse : **`/demarrage`**. Le studio l'annonce lui-même au démarrage, tant que
personne ne l'a refermée :

```
  A FAIRE   : http://127.0.0.1:8199/demarrage   (langue, mot de passe, machines — ce qui manque, mesuré)
```

## Ce que c'est, et ce que ce n'est pas

C'est une **liste de contrôle qui mesure**. Chaque ligne interroge l'état réel
du studio à l'instant où on la demande — pas un réglage enregistré, pas une
intention — et renvoie à l'endroit qui la règle.

**Ce n'est pas un assistant d'installation.** [`/admin`](../README.md#et-ensuite-admin)
sait déjà tout poser : machines à carte, jetons d'agent, clés d'API et choix
local/distant par modalité, comptes, plafond du nuage, réentraînement de
l'aiguilleur. Un écran d'accueil qui redemanderait l'un de ces réglages serait
une **seconde table du même réglage** — et deux tables du même réglage
divergent. Ce dépôt l'a mesuré trois fois : `MENU_REGLAGE` et `CLE_REGLAGE`
écrites à deux cents lignes d'écart, les deux écritures des empreintes de codes
de secours, la séquence d'aiguillage recopiée dans un banc.

Cet écran ne pose donc que deux choses, celles que personne d'autre ne pose :
**la langue de l'interface**, et **son propre effacement**. Tout le reste, il
le mesure et il le montre du doigt. `banc_page.py` le vérifie : ses seuls
appels sont `/api/textes`, `/api/demarrage` et la porte d'administration.

## Les huit lignes

| Ligne | Ce qu'elle mesure | Bloquant ? |
|---|---|---|
| la langue de l'interface | la langue servie, et si le choix est **retenu** (cookie `studio_langue`) ou simplement **deviné** d'après `Accept-Language` | non |
| l'accès au studio | `STUDIO_AUTH`, et le nombre de comptes enregistrés | oui, si aucun compte en `obligatoire` |
| le mot de passe d'origine | reste-t-il un compte portant le mot de passe **tiré au premier démarrage** ? | non — mais c'est la première chose à faire |
| le second facteur | l'état TOTP du compte qui lit l'écran, et ses codes de secours restants | non |
| une machine qui calcule | une machine du parc qui **répond** et annonce une carte | **oui** |
| les fichiers des moteurs | combien de moteurs du catalogue ont leurs fichiers, **quelque part dans le parc** | **oui** |
| le modèle de langage | un Ollama joignable, et le modèle avec lequel il écrit | **non** |
| les clés d'API | les clés posées, et surtout : une modalité confiée à un fournisseur distant **sans clé** | non |

Quatre verdicts, et la distinction entre les deux du milieu porte tout l'écran :

- **fait** — mesuré présent ;
- **bloquant** — rien ne sortira tant que ce n'est pas fait ;
- **à faire** — rien ne t'attend, et pourtant fais-le tout de suite (le mot de
  passe d'origine, `STUDIO_AUTH=libre`, une modalité distante sans clé) ;
- **facultatif** — le studio marche sans.

Ranger « à faire » avec « bloquant » ferait de la liste un mur à franchir, et
l'on apprend à franchir un mur en cliquant.

## Ce qui bloque vraiment, et ce qui n'y ressemble que

**Trois choses seulement empêchent le studio de produire** : un compte quand
`STUDIO_AUTH` vaut `obligatoire` (le défaut), une machine dont la carte répond,
et les fichiers d'au moins un moteur sur cette machine-là.

**Le modèle de langage n'en fait pas partie**, et c'est la moitié du travail de
cet écran que de le dire. Si Ollama est injoignable, `aiguiller()` retombe sur
le classifieur de `aiguilleur.py` — 94 % de justesse sur `banc_aiguillage.jsonl`,
88 % sur `banc_neuf.jsonl`, 0,03 ms par demande, aucune dépendance. La demande
part, l'image sort. Sans cette ligne, on passe une soirée à chercher une panne
qui n'existe pas.

### L'état que rien ne signalait

Il y a **trois** états du modèle de langage, pas deux, et le troisième était
invisible : **Ollama répond et ne porte aucun modèle.**

Une liste de modèles vide se lisait jusqu'ici comme une machine éteinte. Or
`modele_ecriture_de()` retombe alors sur `MODELE_LLM`, et la bannière de
démarrage annonce `qwen2.5vl:7b` — un nom que personne n'a jamais téléchargé.
Les deux remèdes n'ont rien de commun : une machine éteinte se rallume, un
Ollama vide se remplit d'un `ollama pull`. Le studio distingue désormais les
deux (`cerveau(url)["repond"]`), et cet écran les nomme séparément.

### Où atterrit un téléchargement

Quand aucun moteur n'a ses fichiers, la ligne **nomme la machine** sur laquelle
le studio les téléchargera. Ce n'est pas cosmétique : le drapeau `local` de
`noeuds.json` n'est pas une position, c'est un **droit d'écriture sur le
disque**. Mal posé, il fait télécharger dix gigaoctets pour une machine qui ne
les verra jamais, et rien dans le studio ne le disait.

Voir [Télécharger les modèles](telecharger-les-modeles.md) et
[Déplacer le studio sur une machine sans carte](studio-sans-carte.md).

## Ce que l'écran ne prétend pas régler

`COMFY_URL`, `OLLAMA_URL`, `STUDIO_LLM` et `STUDIO_AUTH` sont lues **une seule
fois au chargement du module**. Aucune route ne les change, et un écran qui
offrirait de les poser mentirait. Les lignes qui en dépendent portent donc la
mention **« se pose au lancement du studio, pas depuis une page »** au lieu d'un
bouton.

Deux mécanismes changent réellement quelque chose : `noeuds.json`, relu au
démarrage (voir [Plusieurs machines](plusieurs-machines.md)), et les routes
`/api/admin/*`, qui écrivent à chaud. Les deux vivent ailleurs, et l'écran y
renvoie.

## Le mot de passe d'origine

Le studio tire un mot de passe au premier démarrage et l'affiche **une seule
fois** dans la console. Il défile dans un terminal, il se recolle dans un fil de
discussion, et il reste le seul secret du studio tant que personne ne l'a
changé — mais **rien ne savait dire s'il l'avait été**. « Change-le » était une
phrase de documentation ; c'est maintenant une ligne qui rougit.

Comment c'est mesuré : `comptes.py` pose un drapeau `origine` sur le compte à sa
création, et `changer_mdp()` l'efface — le seul endroit du dépôt où un mot de
passe est remplacé, emprunté par les deux portes qui en changent un
(`/api/compte/mdp` et `/api/admin/comptes`).

**Un drapeau, et non une comparaison.** Garder le mot de passe pour pouvoir dire
« c'est encore lui » reviendrait à le conserver en clair, ce que `comptes.py`
refuse en tête de fichier. Le drapeau ne dit rien du secret : il dit que
personne n'y a touché.

**`STUDIO_ADMIN_MDP` n'est pas marqué.** Un mot de passe posé par celui qui
héberge est une décision ; le marquer ferait rougir pour toujours une ligne que
personne ne peut éteindre autrement qu'en changeant un secret qu'il a choisi.

## Le second facteur

L'écran affiche l'état TOTP du **compte qui le lit**, et de lui seul. `/admin`
peut imposer un mot de passe ; il ne peut pas armer un facteur pour quelqu'un
d'autre — il faudrait son téléphone. Le renvoi va donc au studio, où vit le
panneau du compte. Détail : [Comptes](comptes.md).

## Qui peut le voir

La **page** `/demarrage` est servie à tout le monde, comme `/admin` : sans cela,
on ne pourrait pas afficher le formulaire qui demande le jeton.

La **mesure**, elle, est derrière `admin_ok()` — un compte administrateur
connecté, ou le jeton d'administration. Cette réponse dit qu'un compte porte
encore son mot de passe d'origine, qu'aucune carte ne répond et que
`STUDIO_AUTH` vaut `libre` : servie sans garde, elle serait la meilleure page de
reconnaissance qu'un studio puisse offrir.

Pour la même raison, le lien **« à faire »** de l'en-tête du studio n'apparaît
qu'aux administrateurs : `/api/compte` se lit **sans session** — il le faut, pour
afficher le formulaire de connexion — et « ce studio n'a jamais été configuré »
n'est pas une phrase à servir à un visiteur anonyme.

## La refermer, et la rouvrir

Le bouton **« ne plus afficher cet écran »** écrit
`<STUDIO_DONNEES>/_demarrage.json`. Le lien de l'en-tête du studio et la ligne
de la console disparaissent alors ; l'écran reste à `/demarrage`, et **`/admin`
en garde le lien en permanence** — refermer la liste ne doit pas revenir à la
perdre.

Le même bouton la rouvre.

### Le signal de « première fois »

C'est **l'absence de ce fichier**, et rien d'autre. Trois états du studio
ressemblent à « première fois », et aucun ne l'est :

- **`not COMPTES.gens`** est faux par construction dès le premier démarrage :
  `charger_comptes()` crée le compte `admin` avant que quiconque ait rien vu. Et
  en `STUDIO_AUTH=libre` il est vrai **pour toujours** — l'écran reviendrait à
  chaque lancement d'un studio qui a délibérément choisi de n'avoir aucun compte.
- **`comptes_existent`**, servi par `/api/compte`, dit la même chose et se lit
  sans session.
- **l'absence de `_admin.json`** est vraie une seule fois, mais pas au bon
  moment : `charger_registre()` l'écrit **au même démarrage** que celui qui crée
  le compte `admin`, donc avant que la page ait été servie une fois.

Les trois mesurent autre chose, et changeraient de sens le jour où ce qu'elles
mesurent changera. Un fichier dont c'est la seule raison d'être ne peut pas
dériver.

## Ce que les bancs en tiennent

`banc_page.py` applique à `web/demarrage.html` les mêmes relevés qu'à
`web/index.html` — le français du HTML est **exactement** celui du
dictionnaire, tout `title`, `placeholder` et `aria-label` passe par une clé,
aucune clé citée n'est inventée, aucune clé `demarrage.` ne dort — et deux
couplages qui n'existent que pour cet écran :

- **la table des verdicts, écrite des deux côtés** (`serveur.VERDICTS` les
  nomme, la page les peint). Même motif que `MENU_REGLAGE` / `CLE_REGLAGE` : un
  verdict connu du serveur et inconnu de la page donnerait une ligne sans
  couleur et sans étiquette, c'est-à-dire une ligne qu'on lit « tout va bien » ;
- **la règle qui le fait tenir à côté de `/admin`** : ses seuls appels sont la
  langue, sa propre mesure, et la porte d'administration.

`banc_comptes.py` tient le drapeau `origine` : marqué au bon endroit seulement,
effacé à **un** seul endroit, effacé **sur le disque**, et jamais posé sur un
mot de passe venu de `STUDIO_ADMIN_MDP`.

`banc_mutations.py` porte dix-huit mutations pour cet écran, une par règle, et
son en-tête garde le sens inverse mesuré le 3 septembre 2026 : les bancs neufs
lancés sur le code d'avant.

## Deux pièges du dictionnaire, trouvés en branchant cet écran

Les deux sont réparés, et chacun a son banc et sa mutation
(`banc_traductions.py`) :

1. **Une valeur interpolée qui porte le nom d'un paramètre de `T()` fait
   *lever* le rendu.** `rendre()` écrit `T(cle, langue, **valeurs)` : une valeur
   nommée `langue` — ou `nombre`, ou `cle` — arrive deux fois sur le même
   paramètre, et Python rend un `TypeError`. Pas une phrase fausse : une
   exception, au moment précis où l'on essayait de dire quelque chose à
   quelqu'un. Deux entrées de cet écran le faisaient.
2. **`rendre()` oubliait `nombre`.** Toute marque plurielle prenait la forme
   d'indice zéro en français et celle d'indice un en anglais, quel que soit le
   compte : « 1 accounts registered ». La page, elle, lit `v.n` et accordait
   juste — les deux moitiés du contrat divergeaient **là où `rendre()` se
   déclare leur spécification**. Le défaut préexistait ; rien ne pouvait le
   montrer tant qu'aucune marque ne comptait quelque chose.
