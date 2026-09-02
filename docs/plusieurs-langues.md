# Plusieurs langues

Le studio est en français de bout en bout. La question posée est : que faut-il
pour qu'on puisse s'en servir dans une autre langue, dans quel ordre, et à quel
prix.

Cette page tranche, et depuis le 2 septembre 2026 au soir elle décrit aussi ce
qui existe : **les travaux 1, 2, 3 et 5 sont faits**, le 4 a été mesuré puis
**refusé**, les 6 et 7 restent. Le détail est en bas de page ; ce qui change
tout de suite, c'est que le studio n'exécute plus une demande étrangère de
travers en silence — il la fait lire au modèle de langage, et il le dit.

> Ce qui suit a été mesuré une seconde fois **par le vrai chemin**, une fois la
> garde en place : `banc_multilingue.py` appelle `aiguiller()` et compte les
> appels au modèle. Il retrouve exactement les chiffres pris à la main —
> **26 pannes silencieuses sur 345 demandes étrangères, 1 avec la garde**, et
> le français décidé à l'identique des deux côtés.

## Quatre langues, et une seule qui presse

Il y a quatre choses distinctes dans ce dépôt, et les confondre fait prendre la
plus visible pour la plus urgente.

| | Quoi | Volume | État |
|---|---|---|---|
| 1 | **Ce que le studio écrit** — journal, erreurs d'API, page web, documentation | 163 messages de journal, 133 messages d'erreur, 103 lignes accentuées dans `web/index.html`, 38 625 mots de `docs/` | français |
| 2 | **Ce que le studio lit** — le classifieur, les raccourcis écrits | 2 899 exemples, 7 734 traits ; une douzaine d'expressions régulières | français, **et il ne le sait pas** |
| 3 | **Ce qu'il envoie au moteur** | `SYS_TRADUCTION`, `replier_sur_multilingue()` | déjà réglé |
| 4 | **Le code et les commentaires** | 12 583 lignes | français, et [CONTRIBUTING](../CONTRIBUTING.md) refuse de les angliciser |

**Le point 4 est hors sujet et le reste.** Le point 3 est fait : voir plus bas.
Restent le 1 et le 2, et c'est le 2 qui décide.

## Pourquoi l'entrée passe avant la sortie

Un utilisateur allemand devant des messages français est gêné. Il voit ses
images, il voit sa file, il devine « en attente » et « erreur ». Il travaille
mal, mais il travaille — et surtout, **il sait qu'il est gêné.**

Un utilisateur allemand dont la demande est mal aiguillée reçoit une image. Pas
la sienne. Rien ne le lui dit. C'est la panne que ce dépôt passe ses journées à
traquer : celle du 31 août, où un fond d'écran Halo est parti à
l'agrandissement avec assez de confiance pour court-circuiter le modèle de
langage, et où l'utilisateur a reçu « aucune image à agrandir » pour une demande
de création.

Cette page a mesuré exactement cela.

## Les mesures

### Comment elles ont été prises

Les deux bancs du dépôt — `banc_aiguillage.jsonl` (66 cas, verbes explicites,
registre familier) et `banc_neuf.jsonl` (49 cas, tournures indirectes) — ont été
traduits **à la main** en anglais, allemand et espagnol, dans le même registre.
115 cas par langue, 460 en tout. Le classifieur publié (`aiguilleur.json`,
2 899 exemples) a été chargé tel quel, sans réentraînement.

**Ces chiffres se revérifient depuis le dépôt** : les 460 cas sont dans
`mesures_langues/banc_langues.py`, et `banc_multilingue.py` les rejoue à chaque
CI. Ils ne l'étaient pas quand cette page a été écrite — c'était le premier
travail de la liste, et il est fait.

> **Une découverte en le faisant.** Le banc a d'abord mesuré le modèle de
> *cette installation-ci* — `charger()` prend `aiguilleur.local.json` s'il
> existe, et `aiguilleur.json` seulement sinon : l'un **ou** l'autre. Le
> premier est réentraîné sur les demandes réelles de la machine et `.gitignore`
> l'écarte ; il a donc vu des tournures que le modèle versionné n'a pas, et
> leur couverture y est plus haute. « De quoi ça
> parle » vaut 0,56 avec le modèle publié et 0,67 avec le modèle local de la
> machine de développement. Le même commit aurait donc rendu des verdicts
> différents sur deux machines. Le banc épingle désormais le modèle versionné,
> et c'est avec lui que tous les chiffres de cette page ont été repris.

### Le classifieur, langue par langue

Trois colonnes, et c'est la troisième qui compte. « Tranché d'office » est ce
que le classifieur décide seul, au-dessus de `MARGE_SURE`. Une erreur tranchée
d'office est **silencieuse** : elle produit quelque chose, et rien ne prévient.

| Banc | Langue | Justes | Tranchés d'office, justesse | Pannes silencieuses |
|---|---|---|---|---|
| facile | fr | 62/66 (94 %) | 62/64 (97 %) | **2** (3 %) |
| facile | es | 51/66 (77 %) | 48/55 (87 %) | **7** (11 %) |
| facile | en | 45/66 (68 %) | 39/44 (89 %) | **5** (8 %) |
| facile | de | 35/66 (53 %) | 30/38 (79 %) | **8** (12 %) |
| dur | fr | 43/49 (88 %) | 42/46 (91 %) | **4** (8 %) |
| dur | es | 30/49 (61 %) | 26/37 (70 %) | **11** (22 %) |
| dur | en | 26/49 (53 %) | 23/35 (66 %) | **12** (24 %) |
| dur | de | 17/49 (35 %) | 11/22 (50 %) | **11** (22 %) |

Sur le banc dur, une demande étrangère sur quatre est **exécutée de travers sans
qu'un mot le dise**. En français, c'est une sur douze.

### L'anglais n'est pas mieux traité que le reste

C'était l'hypothèse de départ : le corpus contient 66 exemples marqués
« anglicismes », donc l'anglais serait à demi couvert.

**Non.** Ces 66 exemples sont des phrases **françaises** portant des emprunts —
« Upscale cette image en 4K sans toucher au style », « Change la couleur du
background en bleu nuit ». Le corpus des 2 899 exemples est français à 100 %.

Et à l'usage, **l'espagnol s'en tire mieux que l'anglais** : 77 % contre 68 %
sur le banc facile, 61 % contre 53 % sur le banc dur. La raison est mécanique.
`traits()` découpe les mots de plus de quatre lettres en morceaux de quatre
lettres, et les racines latines passent — *ilustracion* partage `#illu`,
`#lust`, `#stra` avec *illustration* ; *animacion*, *video*, *musica*,
*personaje* passent de même. Les verbes anglais courants sont germaniques et ne
partagent rien : *make*, *remove*, *background*, *smooth*. L'allemand ne partage
rien du tout, et ses composés — *Hintergrundentfernung* pour « suppression du
fond » — ne produisent aucun morceau connu.

**La parenté lexicale décide, pas la popularité de la langue.** C'est un critère
utilisable pour choisir quelles langues sont bon marché.

### Où part une demande étrangère quand elle se trompe

| Langue | Les trois destinations les plus fréquentes |
|---|---|
| allemand | `detourer` 22, `agrandir` 13, `fluidifier` 11 |
| anglais | `lecture` 13, `video_image` 9, `detourer` 8 |
| espagnol | `detourer` 8, `agrandir` 7, `objet3d` 5 |

Ce n'est pas une répartition au hasard, et c'est ce qui rend l'affaire grave :
`SANS_ECRITURE = ("agrandir", "detourer", "fluidifier")` est **exactement** la
liste des trois intentions que le classifieur a le droit de trancher sans
appeler le modèle de langage. L'allemand se trompe précisément là où l'erreur ne
sera vue par personne.

### Les deux chemins qui tranchent sans modèle

Le studio décide sans appel par deux voies. Elles ont été mesurées séparément,
sur les 115 cas × 4 langues.

**A. `raccourci_ecrit()`** — les expressions régulières, avec une image jointe :

| Langue | Attrapé | Justes | Faux |
|---|---|---|---|
| fr | 20/115 | 16 | 4 |
| en | 2/115 | 2 | 0 |
| de | 1/115 | 1 | 0 |
| es | 2/115 | 1 | 1 |

**B. Le court-circuit du classifieur** (`SANS_ECRITURE`, marge ≥ 1,2, demande
courte, aucune image jointe) :

| Langue | Tiré | Justes | Faux |
|---|---|---|---|
| fr | 16 | 15 | **1** |
| en | 22 | 15 | **7** |
| de | 20 | 9 | **11** |
| es | 28 | 21 | **7** |

Voilà le résultat qui change le plan. **Les expressions régulières ne sont pas
le problème** : elles ne mordent que 5 fois sur 345 demandes étrangères, et se
trompent une seule fois. Le repli envisagé — sauter les raccourcis écrits pour
une demande non française — coûterait 4 raccourcis justes pour éviter 1 erreur.
Ce n'est pas là qu'est la panne.

**Le classifieur, lui, tire PLUS souvent sur de l'étranger que sur du
français** (22, 20 et 28 fois contre 16) **et se trompe la moitié du temps.**
Bayes naïf ne sait pas dire « je ne connais pas ces mots » : quand presque aucun
trait n'est reconnu, le lissage de Laplace et les probabilités a priori
départagent les classes tout seuls, et la marge peut être grande pour de mauvais
motifs. « brauche ein Video von null mit einem fliegenden Drachen » — une vidéo
à créer de zéro — part en `fluidifier` avec une marge de 3,9. L'utilisateur
demande une vidéo neuve, le studio interpole la sortie précédente.

## Ce que la page tranche

### Comment le studio sait dans quelle langue on lui parle

Trois candidats ont été mesurés. Aucun n'ajoute de dépendance.

| Moyen | Ce qu'il coûte | Ce qu'il rate |
|---|---|---|
| **Couverture du vocabulaire** — la part des traits de la demande que le classifieur connaît déjà | 0,0095 ms | rien à installer, rien à écrire : le vocabulaire est déjà dans `aiguilleur.json` |
| **Mots-outils français** — une liste de cinquante mots grammaticaux | 0,0048 ms | l'espagnol partage trop (*la*, *le*, *un*, *no*, *para*) |
| **En-tête `Accept-Language`** | nul | dit la langue du **navigateur**, pas celle de la demande. Un francophone sur un Windows anglais est classé anglais |

Mesure, seuil par seuil, sur les 460 cas :

| Moyen | Meilleur seuil | Français gardé | Étranger reconnu |
|---|---|---|---|
| couverture | 0,58 | 114/115 (99 %) | 338/345 (98 %) |
| mots-outils | 0,24 | 112/115 (97 %) | 298/345 (86 %) |

**La couverture gagne, et elle est gratuite.** Elle ne demande aucune donnée
nouvelle, aucune liste à maintenir, aucun modèle à charger : elle relit le
vocabulaire que le classifieur porte déjà. Elle coûte un cinquième de ce que
coûte `classer()` lui-même (0,0455 ms).

Elle ne dit pas *quelle* langue c'est. Elle dit « je ne connais pas ces mots »,
ce qui est précisément la condition sous laquelle la marge ne veut rien dire.
**C'est la bonne question, pas une approximation de la bonne question.**

Le seul cas français passé sous le seuil est « Diffusion du fichier, s'il te
plaît » (0,52), quatre mots dont deux hors corpus. Les sept cas étrangers passés
au-dessus sont chargés de cognats — *dragon*, *illustration*, *3d*,
*1920x1080* — et le classifieur les aiguille correctement de toute façon.

**Le réglage par conversation vient ensuite, pas d'abord.** `REGLAGES_CONV`
porte déjà quatre réglages (`modele`, `taille`, `priorite`, `noeud`) ; une
cinquième entrée `langue` s'y pose sans rien inventer. Mais un réglage explicite
règle la **sortie**, jamais l'entrée : quelqu'un qui a posé « allemand » peut
très bien taper sa demande suivante en français, et l'inverse. La détection
reste nécessaire. Le réglage sert à choisir la langue des messages.

### La garde, et ce qu'elle coûte

La règle éprouvée : **sous 0,58 de couverture, le classifieur ne tranche plus
seul.** La demande part au modèle de langage, qui est multilingue.

Trois politiques, mêmes 460 demandes :

| Politique | Pannes silencieuses (345 demandes étrangères) | Appels au modèle | Secondes à chaud |
|---|---|---|---|
| aujourd'hui | **26** | 270 | 432 s |
| garde de couverture | **1** | 340 | 544 s |
| garde + raccourcis écrits sautés | **0** | 345 | 552 s |

Et sur le français, les trois politiques donnent **exactement le même
résultat** : 34 demandes sur 115 tranchées sans appel, 5 fausses, 81 appels.
La garde ne coûte rien à personne qui écrit en français.

Le prix, pour un utilisateur étranger : 70 appels de plus sur 345 demandes,
soit **0,32 s de plus par demande en moyenne**, à 1,6 s l'appel à chaud
(mesure du 1<sup>er</sup> septembre, `serveur.py`). Sur la petite carte, ce
n'est plus 1,6 s mais 96 à 222 s — voir [Mesures](mesures.md). C'est cher, et
c'est pourtant le bon échange : une demande lente est visible, une demande mal
aiguillée ne l'est pas.

**Note sur un chiffre qui circule.** Les 115 s citées pour la petite carte n'en
sont pas une : le commentaire de `serveur.py` dit que c'était une carte **en
pause**, le travail retombant sur la GTX 1060. La mesure honnête pour zima est
96 à 222 s.

Sauter aussi les raccourcis écrits n'ajoute que 5 appels (8 s) et retire la
dernière panne. À prendre, mais **en second** : c'est un dixième du bénéfice.

### Combien de langues, et selon quel critère

**Deux niveaux, et le critère qui les sépare n'est pas le nombre de langues mais
la nature du travail.**

**Niveau 1 — n'importe quel nombre de langues, tout de suite.** La garde de
couverture ne connaît aucune langue. Elle dit « ces mots ne sont pas au
corpus » et passe la main au modèle de langage, qui est multilingue depuis
toujours. Coréen, arabe, néerlandais : même chemin, même coût. **Zéro donnée
nouvelle.** C'est le niveau qui rend le studio *utilisable* ailleurs.

**Niveau 2 — deux langues en plus, au maximum.** Faire *bien* aiguiller une
langue demande son propre corpus : traduire les ~90 gabarits de
`corpus_aiguillage.py` et ses neuf listes de vocabulaire (~167 chaînes), puis
écrire un banc dans cette langue **par quelqu'un d'autre que le traducteur** —
[CONTRIBUTING](../CONTRIBUTING.md) le dit : entraîné sur ses propres gabarits,
l'aiguilleur faisait 100 % sur les phrases de l'auteur et 74 % sur celles d'un
tiers. Un jeu de test écrit par soi-même ne vaut rien, et cette règle ne
s'assouplit pas parce qu'on change de langue.

Le critère de choix, mesuré plus haut : **la parenté lexicale.** L'espagnol
part de 77 % sans un seul exemple ; l'allemand part de 53 %. À budget égal, les
langues romanes rapportent plus.

### Le chemin qu'il ne faut PAS prendre

Le studio a déjà un mécanisme qui apprend des demandes réelles : `moissonner()`
récolte les tours confirmés d'un pouce en l'air, les pondère `POIDS_REEL = 8`,
et les plafonne à un dixième de leur classe. **Ce mécanisme ne regarde pas la
langue.** La tentation est évidente : laisser les utilisateurs étrangers
l'alimenter, et attendre.

Mesure — corpus français plus K exemples par classe dans la langue visée, avec
la pondération réelle, évalué sur les cas restants de cette langue, trois
tirages :

| Langue | K=0 | K=1 | K=3 | K=5 |
|---|---|---|---|---|
| anglais, justes | 62 % | 58 % | 63 % | 64 % |
| anglais, **pannes** | **15 %** | **28 %** | **28 %** | **27 %** |
| allemand, justes | 45 % | 44 % | 51 % | 51 % |
| allemand, **pannes** | **17 %** | **44 %** | **43 %** | **44 %** |
| espagnol, justes | 70 % | 61 % | 56 % | 59 % |
| espagnol, **pannes** | **16 %** | **27 %** | **33 %** | **33 %** |

**Onze demandes confirmées suffisent à faire doubler les pannes silencieuses.**
La justesse ne bouge presque pas ; c'est la confiance qui monte.

Le coupable est isolé. À K=3, en faisant varier la seule pondération :

| Langue | ×1 | ×2 | ×4 | ×8 |
|---|---|---|---|---|
| anglais, pannes | 17 % | 23 % | 29 % | 28 % |
| allemand, pannes | 27 % | 31 % | 39 % | 43 % |
| espagnol, pannes | 18 % | 22 % | 27 % | 33 % |

Monotone. `POIDS_REEL = 8` a été mesuré sur des demandes **françaises** entrant
dans un corpus français, et le commentaire d'`entrainer_aiguilleur.py` le dit
lui-même. Appliqué à une demande étrangère, il s'inverse : huit exemplaires
d'une phrase allemande créent des traits à fort poids que **toutes** les autres
phrases allemandes partagent — les fragments de mots grammaticaux — et qui les
tirent avec assurance vers la classe de ces huit exemplaires. Il achète de la
confiance plus vite que de la justesse.

Sur le banc français, l'ajout ne change rien (91 %, 90 %, 96 % pour K=0, 3, 5) :
**la dégradation est invisible depuis les bancs du dépôt.** C'est exactement le
profil d'une panne qu'on ne verrait pas.

### Ce qui se traduit et ce qui ne se traduit pas

Les 296 messages du serveur ne sont pas une population. Ils en sont deux, et la
mesure les sépare nettement :

| Famille | Nombre | Dont chaînes formatées (`f"…"`) |
|---|---|---|
| messages de journal | 163 | **110 (67 %)** |
| messages d'erreur d'API | 133 | **14 (11 %)** |

**Les erreurs d'API sont des étiquettes.** 119 sur 133 sont des chaînes
constantes. Elles se balaient mécaniquement vers un fichier de traductions, sans
rien perdre. C'est du travail de recopie, et c'est tout.

**Les messages de journal ne le sont pas.** Deux sur trois interpolent une
valeur calculée à l'exécution :

> RealVisXL demande 7,0 Go et la carte en offre 5,9 : débordement sur la RAM,
> plus lent

Cette phrase porte deux mesures, une conséquence et une raison. La réduire à
`{modele} demande {a} Go, la carte offre {b} Go` la vide de ce qui la rend
utile, et la réécrire dans une autre langue demande de savoir *pourquoi* elle
est là — pas de savoir traduire.

**La décision : le journal ne se traduit pas, et ce n'est pas un pis-aller.**

Trois raisons, dans l'ordre.

1. **C'est là que le prix est le plus élevé et le bénéfice le plus faible.** Le
   journal est ce qu'on lit quand on veut comprendre pourquoi une demande a
   pris ce chemin. Il sert à l'auteur, aux contributeurs, aux rapports de
   bogue. Un rapport de bogue en allemand traduit machinalement depuis un
   journal français serait plus difficile à traiter, pas moins.
2. **Un balayage mécanique casserait ce que le dépôt protège.** La convention
   de [CONTRIBUTING](../CONTRIBUTING.md) — « quand il y a une mesure, elle est
   dans le commentaire » — s'étend naturellement aux messages : ils disent le
   chiffre à l'endroit où quelqu'un voudra le contester. Un fichier de
   traductions les éloigne du code, et la première dérive ne se verra pas.
3. **Ce que l'utilisateur doit comprendre n'est pas là.** Ce qu'il lui faut, ce
   sont les erreurs, les états, les boutons. Ils sont ailleurs, ils sont
   constants, et ils se traduisent.

Ce qui se traduit, donc, par ordre de rapport :

| Quoi | Volume | Nature |
|---|---|---|
| messages d'erreur d'API | 119 chaînes constantes | mécanique |
| interface — textes, `placeholder`, `title` | ~103 lignes accentuées de `web/index.html` | mécanique |
| journal | 163 messages, dont 110 formatés | **non** |
| documentation | 38 625 mots | **non** — voir ci-dessous |

### Ce qu'il envoie au moteur : rien à faire

C'est le point le plus vite tranché. La chaîne normalise déjà tout vers le
français avant d'atteindre les moteurs :

- `SYSTEME` dit au modèle d'écrire le prompt enrichi **en français**, et lui
  interdit explicitement de traduire lui-même (« si tu traduis toi-même, tu te
  trompes de mot et un hibou devient un hippopotame ») ;
- `SYS_TRADUCTION` traduit ensuite français → anglais, pour les seuls moteurs
  marqués `traduire` au catalogue (FLUX.1, RealVisXL, les modèles à étiquettes) ;
- `replier_sur_multilingue()` bascule sur FLUX.2 klein, dont l'encodeur Qwen3-VL
  lit le français, quand la traduction échoue — mesure du 27 août : « un vieux
  hibou perché sur une branche moussue » envoyé tel quel à FLUX.1 donnait un
  hybride d'opossum et d'écureuil.

**Le studio a donc déjà un pivot, et c'est le français.** Une demande allemande
qui atteint le modèle de langage en ressort en français enrichi, puis suit le
chemin ordinaire. Aucun travail n'est nécessaire ici.

> **À vérifier.** Ce paragraphe est une lecture du code, pas une mesure : aucun
> appel au modèle n'a été passé, le studio en service ne devant pas être
> dérangé. `SYSTEME` annonce au modèle « on te donne une demande en français ».
> Ce que Qwen fait d'une demande allemande sous cette consigne n'est pas
> mesuré. C'est le premier essai à faire une fois le banc en place.

## L'ordre des travaux

Chacun avec ce qu'il coûte et ce qu'il ferme.

**1. Verser le banc traduit au dépôt. ✔ fait.** Les 460 cas sont dans
`mesures_langues/banc_langues.py` et `banc_multilingue.py` les rejoue :
12 vérifications, 2,3 s, aucune carte, aucun réseau. Il emprunte `aiguiller()`
au lieu de rejouer la séquence à la main — la seule façon de mesurer un
court-circuit, qui est par définition ce qui n'est *pas* appelé.

**2. La garde de couverture sur le court-circuit du classifieur. ✔ faite.**
`Aiguilleur.couverture()` et `connu()` dans `aiguilleur.py`, `SEUIL_LANGUE =
0.58` avec la mesure qui l'a décidé, une condition de plus dans `aiguiller()`.
Mesuré par le vrai chemin : **26 pannes silencieuses → 1**, et le français
décidé exactement à l'identique — les mêmes 28 demandes tranchées sans appel,
les mêmes 3 erreurs. 0,0083 ms par demande, un cinquième de `classer()`.

**3. Ses mutations dans `banc_mutations.py`. ✔ faites**, et il en a fallu
**trois**, pas une : la garde retirée, la garde muette, et la moisson qui
réapprend l'étranger. Preuve inverse prise sur le code de `2f46396` — le banc
neuf y rougit sur ces trois lignes-là, et sur elles seulement.

**4. Sauter les raccourcis écrits sous le seuil. ✘ refusé, après mesure.**
C'était le seul travail dont le prix n'avait pas été mesuré sur le bon jeu :
l'étude l'avait éprouvé sur les 460 cas d'aiguillage, jamais sur les 65
formulations de `banc_formulations.jsonl`. Avec le modèle publié — celui de la
CI, celui d'une installation neuve — **« de quoi ça parle » est à 0,556**, sous
le seuil, et `raccourci_ecrit()` le reconnaît aujourd'hui comme une lecture.
Le sauter coûterait donc **une formulation française** (`verifier_formulations`
passerait de 65/65 à 64/65) pour éviter **une panne étrangère sur 26**. La
phrase de l'étude, « sur le français les trois politiques donnent exactement le
même résultat », était vraie du jeu sur lequel elle a été mesurée et fausse
partout ailleurs. *Ce qui reste ouvert : la dernière panne. Elle est connue,
écrite, et moins chère que son remède.*

**5. Barrer la moisson aux demandes non françaises. ✔ faite**, dans `corpus()`
et non dans `moissonner()` : le filtre doit se faire contre le vocabulaire des
**gabarits**, pas contre le modèle en service. Le prendre sur le modèle ferait
une boucle — trois demandes allemandes admises relèvent la couverture de
l'allemand, ce qui en admet d'autres, et la garde s'érode sans qu'une ligne ait
bougé.

> **Elle a un prix en français, et il est écrit dans le code.** Sur les 295
> phrases françaises des bancs, **5 sont écartées (1,7 %)** — « ajoute des
> aurores boréales », « commente et recadre en carré », « de quoi ça parle ».
> Ce sont de vraies demandes, et la moisson existe précisément pour apprendre
> les tournures que le corpus n'a pas : la garde écarte donc une part de ce
> qu'elle devrait garder. On l'accepte parce que les deux erreurs ne coûtent
> pas pareil — écarter une demande française coûte un exemple sur des milliers,
> et la tournure suivante repassera ; en admettre une étrangère coûte huit
> exemplaires pondérés, et double les pannes silencieuses de cette langue.

**6. Les 119 messages d'erreur constants, et l'interface.** Un fichier de
traductions, une langue choisie par conversation (cinquième entrée de
`REGLAGES_CONV`), l'en-tête `Accept-Language` comme seule valeur de départ.
*Ferme la gêne. Pas une panne : la gêne.*

**7. Un corpus d'aiguillage dans une seconde langue, si le besoin est réel.**
~167 chaînes à traduire, plus un banc écrit par un tiers. L'espagnol d'abord :
il part de 77 % contre 53 % pour l'allemand. *Ferme les 70 appels
supplémentaires du point 2, pour cette langue seulement.*

Les points 1 à 5 ne demandent **aucune traduction**. Le studio devient
utilisable en toute langue avant qu'un seul mot ait été traduit.

## Ce qu'on ne fera pas

**On ne traduira pas la documentation.** 38 625 mots sur 38 pages, dont
l'essentiel est daté et lié à une mesure. Une traduction fige la version du jour
et vieillit sans le dire — le défaut exact que [Mesures](mesures.md) existe pour
empêcher, une page plus loin. Une documentation française à jour vaut mieux que
deux documentations dont une est fausse.

**On ne traduira pas le journal.** Argumenté plus haut. Il porte des mesures,
pas des étiquettes.

**On n'anglicisera ni le code ni les identifiants.** [CONTRIBUTING](../CONTRIBUTING.md)
le refuse, et rien dans ce qui précède ne le demande.

**On ne fera pas confiance à `Accept-Language` pour aiguiller.** Il dit la
langue du navigateur. Un francophone sur un Windows anglais serait classé
anglais et perdrait ses raccourcis ; un germanophone sur un Firefox français
garderait les siens à tort. Il peut servir à choisir la langue des **messages**
au premier chargement, rien de plus.

**On n'attendra pas que la moisson apprenne les langues.** Mesuré : onze
demandes confirmées font doubler les pannes, et les bancs français n'en voient
rien.

**On n'ajoutera pas de bibliothèque de détection de langue.** Le studio doit
démarrer sur un NAS sans `pip`. La couverture du vocabulaire fait le travail
demandé — dire « je ne connais pas ces mots » — pour 0,0095 ms et zéro
dépendance. Une bibliothèque saurait nommer la langue ; on n'a pas besoin de son
nom.

**On ne traduira pas vers plus de langues que ce qu'on sait éprouver.** Un banc
par langue, écrit par quelqu'un d'autre que le traducteur. Sans ce banc, la
langue n'est pas soutenue : elle est publiée.

## Ce qui reste ouvert

- **Ce que le modèle de langage fait vraiment d'une demande allemande.**
  `SYSTEME` lui annonce du français. Il est multilingue et rendra probablement
  quelque chose d'utilisable, mais rien ne l'a mesuré. Premier essai à faire.
- **La langue des mots-clés qui traversent la chaîne** — `negatif` et
  `tags_audio` sont demandés en anglais par `SYSTEME`. Sans doute sans effet,
  non vérifié.
- **Le seuil 0,58 tient sur 460 cas de quatre langues.** Il n'a pas été éprouvé
  sur une écriture non latine, ni sur un mélange de langues dans une même
  phrase — le cas très courant du francophone qui écrit « fais-moi un artwork
  cyberpunk, style cinematic ». La couverture y sera moyenne ; personne n'a
  regardé où elle tombe.
- **Le second chiffre du tableau des politiques suppose 1,6 s par appel.** Sur
  la petite carte, l'échange n'a pas été refait avec 96 à 222 s. Il tient
  probablement quand même — une erreur silencieuse coûte plus qu'une attente —
  mais ce n'est pas mesuré.
