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
| demandes variées | 94 % | 98 % |
| tournures indirectes | 86 % | 90 % |

**0,05 ms par demande**, contre 700 ms. Le modèle fait 0,19 Mo.

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

Leur apport est **plafonné à un dixième par classe**. Sans ce plafond, dix-sept
demandes réelles dont onze images faisaient pencher tout le classifieur vers
« image », et la justesse sur les tournures indirectes tombait de 86 à 84 %.

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
