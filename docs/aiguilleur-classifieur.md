# Un classifieur plutôt qu'un modèle, quand il n'y a rien à écrire

Aiguiller, c'est ranger une phrase dans l'une de onze cases. Mesuré le 29 août
2026 sur vingt-quatre demandes réelles, avec une consigne courte :

| | |
|---|---|
| `liquidai/lfm2.5-350m` (0,4 Go) | 5/24 — et il recopie la demande au lieu de répondre |
| `digitsflow/bonsai-8b` (1,2 Go) | 17/24, 680 ms |
| `qwen2.5vl:7b` (6 Go) | 15/24, 705 ms |

Tous inventent des étiquettes qui n'existent pas — « modifier », « détour »,
« chanson » — qu'il faut ensuite deviner.

Un classifieur entraîné ne le peut pas : il choisit dans une liste fermée.
**Bayes naïf multinomial**, cent lignes de Python sans aucune dépendance, sur
des mots, des paires de mots et des morceaux de quatre lettres — ces derniers
rattrapent la conjugaison et les fautes de frappe, qui sont la règle dans une
demande tapée vite.

| Jeu de test (jamais appris) | Justesse | Sur les cas tranchés |
|---|---|---|
| `banc_aiguillage.jsonl` — demandes variées | 62/66, soit 94 % | 62/64, soit 97 % |
| `banc_neuf.jsonl` — tournures indirectes | 43/49, soit 88 % | 42/46, soit 91 % |

Relevé le **1er septembre 2026** par `python entrainer_aiguilleur.py
--sans-reel`, c'est-à-dire sur le seul corpus du dépôt — le même calcul que la
CI. Un studio qui a moissonné des demandes réelles donne d'autres chiffres, et
c'est voulu : ce sont celles de son utilisateur. Les deux bancs grossissent, il
faut donc relire les fractions et pas seulement les pourcentages.

**0,03 à 0,05 ms par demande** (pc, 1er septembre 2026), contre 700 ms. Le
modèle fait 0,19 Mo.

## Ce que la mesure a appris

Entraîné sur mes seuls gabarits, il atteignait **100 % sur mes propres phrases
et 74 % sur celles écrites par quelqu'un d'autre**. Il ne connaissait que mon
vocabulaire : « visuel », « artwork », « clip », « beat », « figurine »,
« slowmo », « fps » n'y figuraient pas, et chacun coûtait une erreur. C'est
exactement pourquoi un jeu de test écrit par soi-même ne vaut rien.

Le corpus mêle donc des gabarits (reproductibles, sans réseau) et des demandes
écrites par un modèle distant, en variant les consignes à chaque fournée —
registre familier, soutenu, anglicismes, fautes de frappe, tournures
indirectes. Une seule consigne aurait produit un corpus aussi étroit que le
mien, avec d'autres angles morts. `python entrainer_aiguilleur.py` refait le
tout en trois centièmes de seconde.

## Il apprend de l'usage

Un corpus fabriqué, même varié, reste celui de qui l'a fabriqué. Les demandes
qui passent par le studio, elles, sont écrites par celui qui s'en sert.
L'entraînement les récolte — mais seulement celles dont l'intention est
**certaine** :

- **le moteur imposé depuis l'interface** : l'utilisateur a choisi lui-même
  dans la liste, ce n'est pas une supposition ;
- **un pouce en l'air** : il a vu le résultat et l'a validé ;
- rien d'autre. Un tour « fini » sans pouce ne prouve rien — le studio a pu se
  tromper de modalité et produire quand même quelque chose. L'apprendre
  reviendrait à lui enseigner ses propres erreurs.

Leur apport est **plafonné à un dixième par classe** (`PART_REELLE = 0.10`,
`POIDS_REEL = 8`). Sans ce plafond, dix-sept demandes réelles dont onze images
faisaient pencher tout le classifieur vers « image », et la justesse sur les
tournures indirectes tombait de 86 à 84 % — mesure du 29 août 2026, quand le
banc dur valait encore 86 % et comptait 44 cas.

Ces demandes ne partent pas dans le dépôt : ce sont celles de l'utilisateur. Un
bouton dans `/admin` relance l'entraînement et affiche la mesure à côté — sans
elle, on ne saurait pas si le réentraînement a amélioré ou abîmé quelque chose.

## Où il sert, et où il ne sert pas

Trois intentions ne demandent **aucune écriture** : agrandir, détourer,
fluidifier. L'objet existe déjà, il n'y a ni sujet à décrire, ni cadrage, ni
style. Reconnaître suffit, et le classifieur s'en charge — sans appeler le
moindre modèle.

Pour image, vidéo, musique ou planche, le modèle de langage reste
indispensable : il faut écrire un prompt. L'y remplacer ne ferait rien gagner.

Les expressions écrites à la main restent en première ligne ; le classifieur
les complète. C'est lui qui rattrape « il me faudrait la sortir de son décor »,
qu'aucune expression ne prévoyait.

### Et il se tait quand il ne connaît pas les mots

Trancher sans appeler le modèle demande une marge d'au moins `MARGE_SURE = 1.2`
entre les deux meilleures hypothèses — **et que le corpus reconnaisse la
phrase**, au moins `SEUIL_LANGUE = 0.58` de ses traits.

La seconde condition est là parce que la première ne dit pas ce qu'on croit.
Bayes naïf ne sait pas répondre « je ne connais pas ces mots » : quand presque
aucun trait n'est au corpus, le lissage de Laplace et les probabilités a priori
départagent les classes tout seuls, et **la marge peut être grande pour de
mauvais motifs**. Une demande de vidéo en allemand partait en `fluidifier` avec
une marge de 3,9.

La couverture coûte **0,0083 ms**, un cinquième du classement lui-même, et ne
demande aucune donnée nouvelle : c'est le vocabulaire déjà présent dans
`aiguilleur.json`. Voir [Plusieurs langues](plusieurs-langues.md) pour ce
qu'elle a fermé et ce qu'elle coûte.

## « Décris cette image » ne passe plus par un modèle

C'est la formulation la plus courante quand on joint une image, et de loin la
plus chère à faire trancher : **96 à 222 s** d'aiguillage sur **zima** (le NAS),
mesurées le 31 août 2026. Et la plus fragile — `gemma3:4b`, quatre fois plus
rapide sur tout le
reste, l'a classée « édition », et l'image n'a jamais été regardée. Une décision
qui dépend du modèle du jour n'en est pas une.

Elle rejoint donc la famille des raccourcis écrits — détourer, agrandir,
fluidifier — qui tranchent sur la seule formulation, avant le classifieur et
avant le modèle. Zéro seconde, et le même résultat à chaque fois.

Trois gardes, parce qu'un raccourci trop large est pire que pas de raccourci :

- **il ne s'applique que si une image est réellement jointe.** Sans image,
  « décris-la » est une demande de création ;
- **il refuse tout ce qui trahit une transformation** : un verbe qui modifie
  (`corrige`, `supprime`, `recadre`, `améliore`…), ou un support nommé après le
  verbe. « décris-la en aquarelle » n'est pas une demande de description, et
  « analyse cette photo et corrige les couleurs » non plus. La liste est courte
  à dessein — ce raccourci vise la justesse, pas la couverture : ce qu'il ne
  reconnaît pas part au modèle, comme avant. Passé quatre-vingt-dix caractères,
  il se tait également : une demande de lecture tient en quelques mots ;
- **aucun autre raccourci ne doit répondre vrai.** « décris cette image puis
  supprime le fond » déclenchait à la fois la lecture et le détourage, et la
  lecture étant placée avant, l'utilisateur recevait un paragraphe de texte au
  lieu de son image détourée. Une phrase qui réveille deux raccourcis est
  ambiguë : elle appartient au modèle, pas à une expression régulière.

Il est placé **avant les autres** : « décris-la » est sans ambiguïté dès lors
qu'une image est jointe, et deux des raccourcis suivants mordent sur des
formulations courtes du même genre.

`detaille` est volontairement absent de la liste : avec une image jointe,
« détaille davantage le visage » demande *plus de détail*, pas une description.
Un verbe ambigu dans un raccourci écrit coûte plus qu'il ne rapporte.

Un moteur seulement **hérité** de la conversation ne désarme pas ce raccourci —
voir [Moteur, priorité, taille, machine](reglages-de-rendu.md#quand-un-réglage-nest-pas-suivi).
