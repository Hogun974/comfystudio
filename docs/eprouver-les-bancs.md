# Éprouver les bancs

Un banc vert ne prouve rien tant qu'on ne l'a pas vu rougir.

**Trois fois en une semaine, un banc vert a couvert une fonctionnalité morte.**
La dernière est la pire : `banc_page.py`, écrit exprès pour empêcher un défaut de
revenir, ne voyait pas ce défaut. Il cherchait `priorite: $("#priorite").value`
alors que le vrai code portait l'abréviation ES6, `priorite,`. La ligne fautive
remise en place, le banc est resté vert.

`banc_mutations.py` est la réponse du dépôt à cela. Il **mute le code et exige
que le banc visé rougisse**, sur la ligne nommée et pas une autre.

## Comment il s'y prend

Chaque mutation copie dans un dossier temporaire ce dont le banc visé a besoin,
y applique la mutation, lance **ce banc-là** — pas tous les autres — et attend
une ligne d'échec précise. **Le dépôt n'est jamais touché.**

Copier le strict nécessaire n'est pas une coquetterie : le dépôt entier fait
138 fichiers et 0,12 s de copie, les neuf fichiers dont `banc_conteneur.py` a
besoin en font 0,007 s. Sur l'ensemble des mutations, cela fait deux secondes de
CI contre un huitième de seconde.

**La ligne attendue, et pas seulement un code de retour non nul.** Une mutation
qui casse le banc par une exception rend elle aussi un code non nul, et se ferait
passer pour une réussite.

## Quatre façons d'échouer

| Ce qui arrive | Ce que cela veut dire |
|---|---|
| La mutation passe au **vert** | le filet a un trou — exactement celui qui a laissé passer `priorite,` |
| L'**ancre** de la mutation n'existe plus | elle ne mesure plus rien, et personne ne s'en apercevrait |
| Le dépôt **sain** rougit | un banc qui rougit sur tout n'attrape rien non plus |
| Le banc **pend** | il ne dit rien du défaut qu'on lui présente, et il emporte la CI avec lui |

La deuxième est la raison pour laquelle une mutation s'ancre sur **un motif de
texte et jamais sur un numéro de ligne** : `serveur.py` change plusieurs fois par
jour. Une ancre périmée est comptée en échec, pas en succès silencieux.

## Pendre n'est pas rougir

Le lanceur n'avait **aucun délai** jusqu'au 2 septembre 2026. Une mutation qui
fait *pendre* le banc au lieu de le faire rougir bloquait donc le lanceur pour
toujours, donc la CI, **sans un message**.

Ce n'est pas une hypothèse. Le 2 septembre, une mutation qui retirait un repli a
fait boucler `banc_refaire` : **six lancements empilés, deux depuis dix-sept
minutes**, et le travail arrêté autour. *(Le message du commit `20ccd77` compte
dix lancements empilés et trois agents paralysés ; le commentaire du code, à
l'endroit de la décision, en compte six. Les deux datent du même jour.)*

C'est la même famille que l'exigence de la ligne nommée — « une mutation qui
casse le banc par une exception rend elle aussi un code non nul, et se ferait
passer pour une réussite ». **Le pendage est pire : il ne se déclare pas du
tout.**

`DELAI_BANC` vaut trente secondes, et l'expiration porte son propre verdict :

```
la mutation fait PENDRE banc_refaire au lieu de le faire rougir
— plus de 30 s sans reponse
```

Trente secondes, et le chiffre a sa raison : le plus lent des bancs mutés met
3,5 s (`banc_variantes`), le suivant 2,9 s (`banc_cout`). Dix fois la marge. Et
cette marge est pour la **charge de la machine**, pas pour le banc — une
exécution mesurée à 77 s est passée au-dessus de 300 s sur une machine occupée.

C'est aussi pourquoi ce banc-là ne se lance pas à la légère : il dépasse **cent
secondes** au 2 septembre 2026, et il grossit à chaque banc couvert.

## La preuve inverse

**Une mutation qui rougit ne prouve pas qu'elle mesure le bon trou.** Elle peut
rougir pour une autre raison que celle qu'elle nomme. Ce qui le prouve, c'est
qu'elle passe au **vert** quand on défait la correction qu'elle garde. Rouge
avec la garde, verte sans : c'est la diagonale.

Dix-neuf mutations ont attendu cette preuve pendant deux jours. Le résultat dit
pourquoi elle n'est pas un raffinement :

- **16** rouges avec la garde, vertes sans — prouvées.
- **2** sont restées rouges, et elles avaient raison : elles étaient rattachées
  au **mauvais commit**. Rejouées contre le banc du vrai commit de leur garde,
  elles passent au vert. Une mutation mal datée se serait déclarée prouvée
  contre un filet qui la voyait déjà.
- **3** ne sont pas prouvables ainsi, et c'est écrit dans le fichier, section
  par section : leur banc est né **avec** la correction, il n'existe pas de
  filet d'avant.

**La méthode qui tient : rejouer contre le banc *et* le code pris au même
commit.** Le premier essai — vieux banc contre le `serveur.py` d'aujourd'hui —
était inutilisable : trente cas rougissaient sans rapport, trois mois de dérive.

Et le filet d'avant n'est pas toujours celui qu'on croit. Pour les mutations de
`banc_repartition`, la version du commit attendu s'arrêtait sur une
`AttributeError` — elle lisait déjà un attribut qu'un commit ultérieur devait
créer. C'est une version antérieure qui a servi : **35/35 vert** sur un serveur
qui porte pourtant les six défauts, chacun relevé à la main dessus.

### Quand le banc est né avec sa correction

Il n'y a alors pas de filet d'avant, et la diagonale n'a rien à mesurer. On
prend le sens inverse autrement : **on lance le banc NEUF sur le code d'AVANT**,
et l'on vérifie que les lignes que la mutation nomme y rougissent.

C'est ce qui a servi pour `banc_refaire`, dont les douze mutations n'ont aucun
filet antérieur : `serveur.py` restauré au commit d'avant la correction, le banc
neuf lancé dessus, **32 lignes rouges — et les douze attendues sont toutes
parmi elles**. C'est plus fort qu'une diagonale : cela ne dit pas seulement que
la mutation voit quelque chose, cela dit que le banc voit le vrai défaut.

Quand ni l'un ni l'autre n'est possible, **écris-le**. La règle complète est
dans [`CONTRIBUTING.md`](../CONTRIBUTING.md).

### Et parfois le sens inverse oblige à réparer le banc

Les dix-huit mutations de l'écran de
[première mise en route](premiere-mise-en-route.md) sont nées avec lui, donc par
ce second chemin : le dépôt reconstruit sans l'écran, sans ses routes, sans sa
famille du dictionnaire et sans le drapeau `origine` des comptes, et les bancs
neufs lancés dessus. Le 3 septembre 2026 :

- `banc_page.py` **rougit sur huit de ses dix lignes neuves**, et ne meurt pas —
  parce qu'il ouvre `web/demarrage.html` sous `try` et pose un cas nommé. Les
  deux qui restent vertes le sont **à vide** : « aucune clé `demarrage.` ne
  dort » est vraie d'un dictionnaire qui n'en porte aucune.
- `banc_comptes.py` **mourait**, sur `TypeError: Comptes.creer() got an
  unexpected keyword argument 'origine'`, et emportait ses soixante
  vérifications avec lui. `banc_mutations` rend alors « le banc s'est cassé au
  lieu de rougir », et le sens inverse ne mesure plus rien. La section lit
  désormais la **signature** avant d'appeler, et garde le reste derrière ; elle
  rougit sur trois lignes. La réparation a sa mutation.
- `banc_traductions.py` **rougit sur un défaut qui préexistait** : `rendre()` ne
  passait pas `nombre` à `T()`, donc toute marque plurielle prenait la mauvaise
  forme — « 1 accounts registered ». Personne ne pouvait le voir tant qu'aucune
  marque ne comptait quoi que ce soit.

Deux leçons, et ce sont les mêmes qu'ailleurs sous une autre forme : **un banc
qui meurt sur le code d'avant ne mesure pas le sens inverse**, et **une ligne
verte à vide n'est verte que faute d'objet** — il faut le dire, pas s'en
contenter.

### Et parfois il n'y a rien à nommer sur le code d'avant

Les quinze mutations de la [libération de la
VRAM](rendre-la-carte.md) gardent une règle qui **n'existait pas** : aucun
`/free` nulle part, ni dans `serveur.py` ni dans `agent_noeud.py`, et la mémoire
libre arrivait à chaque battement sans qu'aucune route ne la rende. Le sens
inverse a donc été pris par le second chemin, et il rend moins que pour
`banc_refaire` — c'est la limite du procédé, et elle mérite d'être écrite.

`serveur.py` reconstruit sans les **seize morceaux** de la libération, le banc
neuf lancé dessus le **3 septembre 2026** :

```
  NON  le studio sait rendre une carte laissee au repos
       — la machinerie entiere manque
  48 verifications passees, 1 echouee
```

Une ligne rouge, **une seule**, et les quarante-huit d'avant restent vertes : le
banc **distingue** les deux dépôts au lieu de mourir sur l'un des deux, parce
que la section neuve est gardée par un `hasattr` — le même tour que
`web/demarrage.html` sous `try`. Mais les vingt-sept cas de la section ne
s'exécutent pas, et les quinze lignes que les mutations nomment **n'ont rien à
nommer là-bas**. On ne peut donc pas les montrer rouges sur le code d'avant.

Ce qui porte la preuve, ici, c'est le sens **aller** et l'exigence de la ligne
nommée : `verdict()` rend « cassé » quand le rouge tombe ailleurs. Les quinze
sont rouges **sur la ligne qu'elles annoncent**, et **dix** d'entre elles sur
cette ligne **seule**. Les cinq autres en entraînent une à six de plus, et c'est
attendu : couper le **transport** de la consigne — la clef que la réponse à
l'annonce ne porte plus — fait tomber tout ce qui en dépend, là où couper une
seule **garde** ne fait tomber qu'elle.

Sur le dépôt d'aujourd'hui, le même banc rend **76/0**.

### Et le sens inverse trouve des trous que les mutations ne trouvent pas

`banc_multilingue` est né le même soir avec sa correction, donc par le second
chemin : le dépôt restauré à `2f46396`, le banc neuf lancé dessus. Il y rougit
sur **quatre** lignes — les trois que ses mutations nomment, **et une
quatrième**.

Cette quatrième est la leçon. « Chaque demande étrangère retenue par la garde le
dit dans le journal » se lisait d'abord `dits >= etr_avant - etr_apres`, et
c'était **vert** sur le code d'avant : *0 ligne de journal pour au moins
0 panne évitée*. Zéro est bien supérieur ou égal à zéro. L'assertion ne
distinguait pas « la garde le dit » de « il n'y a pas de garde » — le défaut
exact que [treize assertions de `banc_refaire`](ce-que-le-tour-garde.md)
portaient le matin même.

Sa mutation, elle, était **rouge** : en retirant la ligne de journal sur un code
qui garde, `dits` tombe à 0 pendant que `etr_avant - etr_apres` reste à 25. La
mutation ne pouvait donc pas voir le trou ; le sens inverse l'a vu tout de
suite. **Une mutation verte n'est pas la seule façon qu'un filet a d'avoir un
trou** — et c'est une raison de plus de prendre le sens inverse même quand les
mutations sont toutes rouges.

### Le cas le plus net : rougir sur toutes les lignes, sans mourir

Les dix-neuf mutations de [l'identifiant du studio](installation.md#quelle-version-tourne)
sont nées avec `banc_version.py`, donc par ce second chemin. Le résultat est le
plus franc que ce dépôt ait relevé, le **4 septembre 2026** : `serveur.py`,
`web/admin.html`, le `Dockerfile`, `paquet/comfystudio.spec`,
`construire_windows.bat` et le modèle d'issue repris **au commit d'avant**, le
banc neuf lancé dessus —

```
  0 verifications passees, 19 echouees
```

**Dix-neuf lignes rouges sur dix-neuf, et aucune mort.** Les dix-neuf que les
mutations nomment sont exactement celles-là. Ce n'est pas une chance : le banc
est écrit pour cela, comme `web/demarrage.html` sous `try` avant lui. La
fonction est cherchée par `getattr` et non importée, chaque fichier est ouvert
sous `try`, et toute absence pose **un cas nommé** au lieu d'une trace de pile —
« version_du_studio() n'existe pas », « serveur.py ne nomme aucun fichier ». Un
banc qui meurt sur le code d'avant ne mesure pas le sens inverse ; celui-ci en
mesure la totalité.

L'isolement a été relevé dans la foulée, mutation par mutation : **douze des
dix-neuf rougissent leur ligne et elle seule.** Les sept autres en entraînent
une à cinq de plus, et c'est voulu — elles touchent la **porte d'acceptation**,
`_identifiant_acceptable()`, que les deux sources traversent. Cette porte est
unique **exprès** : deux refus écrits à deux endroits se couvriraient l'un
l'autre, et l'on ne pourrait plus faire rougir ni l'un ni l'autre. Un filet
qu'on ne peut pas voir rougir ne mesure rien — c'est la phrase de ce fichier,
appliquée cette fois au code gardé et non au banc.

## Les trous qu'on connaît et qu'on n'a pas encore bouchés

`TROUS_CONNUS` rassemble les mutations qu'une relecture adverse a trouvées et que
le banc visé laisse **encore** passer. Elles sont écrites, nommées et signalées à
chaque exécution, mais ne font pas échouer : les compter en échec rendrait la CI
rouge en permanence, et une CI qui rougit pour rien finit ignorée. Les basculer
dans les mutations ordinaires est le geste qui clôt la réparation du filet.

Ce que les fermer a appris : un relevé par expression régulière décrit **une
façon d'écrire la panne, jamais la panne**. Fermer le premier a d'ailleurs révélé
qu'il n'imitait pas encore le vrai défaut, et la mutation qui manquait a été
ajoutée à son tour. **Une mutation aussi s'éprouve.**

## Ce qu'il a déjà attrapé

- **Un banc écrit le jour même.** Dix minutes après l'écriture de
  `banc_repartition.py`, deux de ses trois gardes du « pas de carte, pas de
  rendu » ne mesuraient rien : les corrections se recouvraient, et retirer l'une
  laissait les cas passer au vert. Chaque garde est depuis éprouvée **à la place
  des deux autres**.
- **La même faute, une seconde fois**, sur la mutation « une machine sans carte
  redevient candidate » : les deux gardes se recouvraient encore. Le cas isole
  désormais la seconde en remettant le défaut d'origine sur la première.
- **Deux mutations devenues sans objet.** Quand la préférence pour le studio a
  disparu du code, les deux mutations qui la visaient se sont déclarées
  **périmées d'elles-mêmes** — leur ancre n'existait plus. C'est le comportement
  voulu : une mutation qui ne mesure plus rien le dit.
- **Un garde-fou qui ne gardait rien.** Sur `banc_refaire`, le cas « un
  `release()` de trop » passait **même sans** le garde-fou qu'il prétendait
  éprouver : la promesse était résolue, la tâche pas encore réveillée. C'est
  `banc_mutations` qui l'a dit, pas la relecture.
- **Le plus vieux banc du dépôt n'avait jamais été éprouvé.**
  `verifier_formulations` a reçu ses premières mutations le 2 septembre 2026, et
  la première a montré qu'il ne voyait pas la panne pour laquelle il existe : il
  **recopiait** la séquence d'aiguillage au lieu de l'appeler. Il éprouvait donc
  les prédicats, et jamais leur **ordre** — c'est-à-dire exactement ce que son
  propre en-tête promet de garder. C'est le motif de `priorite,` une fois de
  plus : un banc qui redit le code au lieu de l'emprunter ne mesure que
  lui-même.

- **Un fichier entier hors de portée.** `agent_noeud.py` n'était copié par
  **aucun** banc, donc aucune de ses lignes n'était sous filet : les deux
  mutations qui le visaient revenaient « MUTATION PÉRIMÉE — `agent_noeud.py`
  n'est pas copié pour `banc_repartition.py` ». On pouvait couper `free_memory`
  du corps de `/free` et les dix-sept bancs restaient verts, alors que le
  commentaire de `liberer_carte()` dit que l'un sans l'autre laisse plusieurs
  gigaoctets, « ce qui donne exactement l'apparence d'un `/free` qui ne marche
  pas ». La périmée n'est **pas** un succès silencieux : c'est ce message-là,
  répété, qui a nommé le trou. `banc_agent.py` le ferme le 3 septembre 2026.
- **Un banc qui promettait une porte qu'il n'avait pas remplacée.** Le même
  jour, au soir, `banc_agent.py` annonçait dans son en-tête « une seule porte
  sur le monde, `appeler()` » — et l'étape de CI recopiait la phrase. Il y en a
  **trois** : `deposer_entrees()` appelle `urllib.request.urlopen` en direct
  (il lui faut du multipart) et `ecouter_progression()` ouvre une **socket
  nue**. Les deux portes oubliées sont précisément celles par lesquelles
  l'agent écrit sur le disque de la machine à carte et relaie la progression.
  Même reproche que celui de `SECURITY.md` à une politique qui promet un
  contrôle inexistant : la phrase faisait croire à une couverture qui
  n'existait pas.
- **Et la première chose que la troisième porte a montrée est un vrai défaut.**
  `ecouter_progression()` remettait le pourcentage à zéro dans son seul
  `except` — or les **deux sorties les plus fréquentes** de sa boucle de trames
  n'y passent pas : une fermeture propre (opcode `0x8`, ce qu'envoie un ComfyUI
  qui redémarre) et un flux qui s'arrête net sortent par un `break`. Mesuré au
  banc : **7/20 après la fermeture, 7/20 après la coupure, 0/0 après une
  poignée de main refusée**, pour trois pertes de connexion identiques. Le
  studio affichait 35 % sur un rendu mort jusqu'au délai d'`executer()`, soit
  une heure au pire, et le rendu **suivant** démarrait à 35 %. La remise à zéro
  est passée dans le `finally`. Sens inverse mesuré : le banc neuf sur l'agent
  d'avant rend **83/1**, rouge sur la ligne nommée.
- **La porte probabiliste qu'un seul tirage ne voit pas.** Le pong de la
  websocket est masqué par `os.urandom(4)`, comme l'exige la RFC 6455. Une clef
  **constante** passe le tour complet — XOR par zéro rend la charge intacte —
  et l'octet de tête déclare toujours le masque : deux cas sur trois restent
  verts. Il faut **cinquante tirages** pour la distinguer d'une clef tirée au
  hasard, et la mutation « clef constante » ne rougit que sur ce cas-là.
- **Un cas écrit pour un couplage qui n'en voyait que la moitié.** Le relevé
  « /admin et le serveur nomment les mêmes réglages » comparait les **noms** et
  pas les **bornes**, alors que les quatre paires `min`/`max` de la page sont
  recopiées à la main face à `BORNES_REGLAGES`. Mesuré : `max="1440"` passé à
  `max="720"` sur `#vramReposMin`, `banc_page.py` rend 66/0 sans une ligne
  rouge. Le même motif que `priorite,` — un banc écrit pour un défaut qui ne
  voit pas ce défaut — sur le couplage suivant.

- **Trois trous dans un banc, trouvés par ses propres mutations, le jour de son
  écriture.** `banc_boucle.py` couvre les six fonctions que `banc_agent.py`
  avait nommées en les laissant dehors. Il rendait 128/0, et trois de ses
  soixante-huit mutations sont revenues **vertes** :

  - deux cas de « pas de carte, pas de studio » : le faux réseau **retirait de
    sa trace** la demande de travail qui l'arrête, si bien que « aucun travail
    réclamé » restait vrai d'une boucle qui en réclamait un. Le filet ne
    pouvait pas voir le trou qu'il nomme ;
  - « un fichier illisible n'emporte pas les autres » : l'illisible était écrit
    **en second**, et remplacer le `continue` par un `break` ne changeait donc
    plus rien — le premier fichier était déjà parti.

  C'est trois fois le motif de `priorite,`, dans le banc qui vient le fermer.
  Deux autres trous du même banc ont été trouvés à la relecture et non par
  mutation, ce qui redit la leçon de `banc_multilingue` : une assertion sur
  l'espacement du fil des questions mesurait en réalité un `sleep` écrit en
  dur, et cinq corps de réponse trop anodins ne donnaient rien à refuser à la
  garde « on ne jette pas un rendu sur un doute ».

- **Et le même banc mourait sur le code d'avant.** `banc_boucle.py` naît bien
  après les six fonctions qu'il garde : la seule preuve inverse possible est le
  second chemin, le banc **neuf** sur l'agent d'**avant**. Au premier essai il
  s'arrêtait sur `AttributeError: module 'agent_noeud' has no attribute
  'PREMIERE_ANNONCE'` — **cinq commits sur six**, et « le banc s'est cassé au
  lieu de rougir » ne mesure rien. Chaque nom y est désormais lu par un
  accesseur tolérant, dont le défaut est un **témoin impossible** et jamais la
  valeur d'aujourd'hui — souffler la réponse rendrait le cas vert au lieu de
  rouge — et chaque absence pose un cas nommé. Repris à neuf commits, le
  4 septembre 2026 : `811677b` **115 lignes rouges**, `b717f11^` 111,
  `adca444^` **8 seulement, et 130 vertes** — le banc *distingue* les deux
  dépôts au lieu de mourir sur l'un des deux. **Cinquante-six** des
  soixante-huit lignes que ses mutations nomment y rougissent ; les douze
  autres gardent des règles aussi vieilles que le dépôt.

- **Et il a trouvé deux vrais défauts, corrigés le jour même.** C'est ce qu'on
  attend d'une couverture neuve, et cela se dit : couvrir n'est pas décrire ce
  que le code fait, c'est comparer ce qu'il fait à ce qu'il promet. Les deux
  vivaient exactement dans cet écart — une docstring et sa condition.

  `insister()` promettait « on ne recommence que sur un studio MUET ou en panne
  (0, ou 5xx) » et testait `st == 200 or (400 <= st < 500)` : un **204**, que le
  studio sert déjà ailleurs, repartait vingt-quatre fois sur dix minutes avant
  que le travail ne soit déclaré perdu. `trouver_ollama()` promettait
  « l'adresse où un modèle répond **vraiment** » et se contentait d'un
  dictionnaire non vide : un Ollama installé et **vide** arrêtait la recherche
  et masquait le voisin qui portait les modèles.

  **Une des deux explications était fausse, et la corriger valait le défaut.**
  Le premier était illustré par « un reverse proxy qui redirige http vers https
  répond 301 ». Mesure du 4 septembre 2026 contre un serveur d'essai : `urllib`
  **suit** les redirections, un 301 avec `Location` rend 200 à `appeler()`, et
  seule une *boucle* de redirections ressort en 301. Le déclencheur réel était
  204 — plus banal, moins spectaculaire, et bien plus probable. Un défaut qu'on
  explique de travers se corrige de travers.

Voir [Qui prend le travail](qui-prend-le-travail.md) pour les règles que ces
mutations éprouvent.

## Si tu ajoutes un banc

Ajoute-lui sa mutation. **Un filet qu'on n'a jamais vu rougir ne mesure rien.**
Le détail de ce qui est attendu d'une contribution est dans
[`CONTRIBUTING.md`](../CONTRIBUTING.md).
