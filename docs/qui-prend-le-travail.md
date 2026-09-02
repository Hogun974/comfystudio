# Qui prend le travail

Une demande occupe une carte deux fois : d'abord quelques secondes pour être
**analysée**, puis des minutes pour être **rendue**. Ce sont deux besoins
opposés, et le studio leur répond par deux règles opposées.

| | Ce qu'il prend | Pourquoi |
|---|---|---|
| **Analyse** | la **plus grosse** carte libre | elle dure quelques secondes, et tout attend qu'elle finisse |
| **Rendu** | la **plus petite** qui tient le moteur | ce qu'on achète est la grosse carte laissée libre pour la suite |

Les deux ordres disaient l'inverse jusqu'au **1er septembre 2026** ; ils ont été
retournés sur demande de l'utilisateur, et cette page décrit l'état d'après.

## L'analyse prend la plus grosse carte libre

Trois règles, dans cet ordre (`cerveaux_utilisables()` dans `serveur.py`) :

1. **Une machine en pause ne pense pas.** Son propriétaire s'en sert.
2. **Une carte libre passe devant une carte occupée.** Attendre deux minutes
   derrière un rendu quand une autre machine répond tout de suite n'a de sens
   pour personne.
3. **À égalité, la plus grosse carte.**

La troisième disait l'inverse : *« occuper la meilleure pour réfléchir, c'est la
retirer du rendu qu'elle seule fait vite »*. Ce raisonnement suppose que
l'analyse et le rendu se disputent la carte **pendant le même temps**. Ils ne se
la disputent pas : une analyse dure quelques secondes, un rendu des minutes.
Plus tôt l'analyse rend la carte, plus tôt le rendu part.

La lecture d'image était déjà l'exception, pour une raison qui vaut maintenant
partout : mesure du 31 août 2026, la même image lue en **19 s** sur la 2080 Ti
de **pc** et **toujours pas rendue après 900 s** sur la GTX 1060 de **zima**, où
le modèle de vision déborde. « La plus petite qui suffise » suppose qu'elles
suffisent toutes ; ici, non. Il n'y a donc plus deux règles, il n'y en a qu'une.

Une adresse dont on ne reconnaît aucune machine du parc n'a pas de carte connue :
elle est traitée comme libre et de taille nulle — voir [Plusieurs
Ollama](plusieurs-ollama.md).

**Les deux chemins d'analyse suivent la même règle**, et ce n'était pas le cas
au départ : quand aucune adresse Ollama ne répond en direct, le studio emprunte
le modèle d'une machine **par son agent**, et ce chemin-là a gardé l'ancien
ordre pendant une journée. Ce dernier recours coûte de toute façon vingt à
quarante fois le prix d'un appel direct — mesure du 31 août 2026, 3,8 s en
direct contre 162,6 s par l'agent de **zima** — et il est borné par
`STUDIO_ANALYSE_MAX`. `STUDIO_ANALYSE_PETITE=1` y remet la plus petite ; voir
[Réglages](reglages.md) et [Le modèle de langage peut venir d'une autre
machine](modele-de-langage-distant.md).

## Le rendu prend la plus petite qui tient

`choisir_noeud()` retient d'abord les machines qui peuvent vraiment faire le
travail — le modèle est sur **leur** disque, leur carte tient le moteur — puis :

1. **Une machine où le moteur tient *vraiment* passe devant.** Le débordement
   sur la RAM est un recours, pas un choix par défaut.
2. **La carte la moins chargée passe devant.** On compte les travaux qui la
   **visent**, pas le verrou qu'elle tient : le verrou n'est pris qu'au moment
   de soumettre, bien après le choix. Sans cela, deux demandes envoyées à deux
   secondes d'écart voyaient toutes deux une carte libre, visaient la même, et
   la seconde attendait pendant que l'autre machine dormait — constaté par
   l'utilisateur.
3. **À égalité, la plus petite carte.**

Le troisième point disait « la plus grosse ». Une grosse carte prise pour un
rendu qu'une petite aurait fait est une grosse carte qui manquera au rendu
suivant, celui qui en a besoin.

## Pas de carte, pas de rendu

La garde était « sauf le local », ce qui posait la question à l'envers : ce n'est
pas d'**être le studio** qui empêche de rendre, c'est de **n'avoir pas de
carte**. Elle vaut maintenant pour tout le monde, et il le fallait — depuis que
le rendu prend la plus petite, une machine à zéro gigaoctet serait choisie **la
première**, étant la plus petite de toutes.

Le studio garde une seule dispense : il n'a pas à posséder le modèle, puisqu'il
peut le télécharger sur son propre disque. La carte, elle, lui est demandée comme
aux autres.

C'est le défaut signalé par l'utilisateur — *« il m'affiche souvent moteur local
(le studio n'en a pas, uniquement les nœuds), et du coup attend dans le vide »* :
le studio se désignait, la demande partait sur une machine incapable, et le
studio patientait une demi-heure. Voir [Déplacer le studio sur une machine sans
carte](studio-sans-carte.md).

## Le studio est un nœud comme les autres

Il passait devant tout le monde à égalité de charge, au motif qu'il n'a pas de
réseau à traverser. Cette préférence sans condition le faisait gagner contre la
2080 Ti. Règle de l'utilisateur : *« si le studio a un nœud (llm + comfy), il est
considéré comme un nœud comme les autres avec ses caractéristiques »*. Il gagne
donc quand sa carte est la bonne, et pas parce que c'est lui.

## Le débordement s'apprend

Une carte plus petite encore peut faire l'affaire en débordant sur la RAM. Le
studio ne le devine pas, il l'apprend :

- **Sans mesure, on reste sur la carte qui tient.** C'est la réponse la plus
  fréquente au début, et c'est voulu.
- **Dès que la durée typique de ce moteur est connue sur les deux cartes**, on
  descend tant que le débordement ne coûte pas plus de la moitié de temps en
  plus (`SURCOUT_DEBORDEMENT` dans `serveur.py`).
- **Et l'on descend au plus bas, pas d'un cran.** Les cartes qui débordent sont
  triées par mémoire **croissante**, et c'est la **première** qui passe le seuil
  qui est prise : la plus petite acceptable, et non la voisine du dessous de la
  carte qui tient. Même raison que le seuil lui-même — ce qu'on achète en
  débordant, c'est de la carte laissée libre, et s'arrêter au premier cran quand
  deux passent le seuil en achète moins.

Le seuil est un **choix, pas une mesure**, et c'est écrit à côté de lui :
au-delà, on paie deux fois — le rendu est lent **et** la grosse carte dormait.

Il ne se cumule pas non plus d'une marche à l'autre : chaque candidate est
comparée à la carte **qui tient**, jamais à sa voisine du dessus. Il n'y a donc
pas d'escalier où l'on perdrait une fois et demie à chaque cran — deux crans
plus bas restent bornés à une fois et demie la carte qui tient.

« Connue » veut dire **trois rendus comparables au moins**, par la même prudence
que le devis : un chiffre tiré d'un seul rendu ne vaut rien. La comparaison lit
en revanche les rendus de **tout le studio**, et non les vôtres seuls — le devis
qu'on vous annonce est personnel parce qu'il vous est annoncé ; une décision de
répartition n'a pas de raison de l'être. Voir [Combien de temps ça va
prendre](combien-de-temps.md).

## Une analyse passe devant un rendu, jamais en plein rendu

Une carte ne fait qu'une chose à la fois, et les deux moitiés de cette phrase
comptent autant l'une que l'autre.

- **« Passe devant »** — le verrou d'une carte a désormais **une file par rang**
  (`VerrouCarte`). Un simple verrou servait dans l'ordre d'arrivée : une analyse
  de trois secondes patientait derrière deux rendus de quatre minutes, soit
  **huit minutes sans que rien ne parte**, pour une demande que le studio n'avait
  même pas encore lue.
- **« Jamais en plein rendu »** — rien n'interrompt le travail qui tient la
  carte. La priorité ne joue qu'entre ceux qui **attendent**.
- **Une carte rendue deux fois n'est pas donnée à deux.** Le passage de relais
  ne repasse jamais par « libre » : la carte va d'un porteur au suivant sans
  fenêtre où un nouveau venu pourrait s'y glisser, si bien que « la carte
  est-elle tenue ? » ne suffit plus à distinguer le second relâchement de A du
  premier de B. Un drapeau dédié les sépare. Un relâchement en trop est
  **ignoré** — la carte reste à son porteur — et nomme son site d'appel dans le
  journal, sans lever : les trois sites la rendent depuis un `finally`, où lever
  remplacerait *« le modèle de vision n'a pas répondu »* par *« verrou non
  tenu »* au moment précis où le diagnostic compte.

**La famine était possible**, et l'argument qui figurait ici — *« les analyses
d'une demande sont en nombre borné, donc la file des rendus finit par passer »* —
ne tenait pas : il borne **une** demande, pas le flux. Il y a huit sites d'appel
au modèle de langage, une chanson en fait cinq ou six, et chaque adresse Ollama
essayée reprend le verrou. Mesure d'une relecture adverse : trois travailleurs
qui enchaînent leurs analyses, et le rendu est servi **61ᵉ sur 61**.

D'où le **vieillissement** : passé `ATTENTE_MAX_RENDU` — deux minutes — le rendu
le plus ancien cesse d'être doublé. Il prend **un tour, pas la main**, et cette
nuance est tout le correctif : le renversement s'entretenait sinon lui-même,
puisque la nouvelle tête de la file des rendus a elle aussi attendu longtemps.
Toute la file des rendus passait alors avant toute celle des analyses — trois
rendus de quatre minutes, et le message qu'on venait de taper attendait douze
minutes avant d'être seulement lu, le symptôme exact que ce verrou existe pour
empêcher. Avec l'alternance : quatre minutes, un rendu.

Quand il n'y a plus d'autre machine, une analyse attend la carte occupée pendant
`STUDIO_ATTENTE_CARTE` — trente minutes par défaut, voir
[Réglages](reglages.md) — puis renonce en le disant.

## Refaire sur la grosse carte

Après un pouce en bas, un bouton **« refaire sur la grosse carte »** apparaît
sous la réponse. Il vise la plus grande carte du parc, **quitte à l'attendre**.

La plus grosse se choisit **avant** le filtre de charge. La prendre parmi les
moins chargées seulement, c'est retomber sur la petite dès qu'un rendu vise la
grosse — exactement ce que le geste cherche à éviter.

**Et la visée survit aux reprises.** Une machine qui lâche, ou un tour de
patience quand plus aucune ne répond, faisaient repartir le travail par le choix
ordinaire : le bouton promettait la grosse carte, le journal venait de
l'annoncer, et le rendu finissait sur la petite. La reprise vise donc la même
chose que le premier choix.

Le détail du bouton — ce qu'il reprend, ce qu'il ne reprend pas, et pourquoi il
est séparé du pouce — est dans [Pouce en l'air, pouce en bas](avis.md).

## Ce que les bancs vérifient

`banc_repartition.py` (**48** vérifications) et `banc_cerveaux.py` (**39**)
tiennent cette page : relevé le **2 septembre 2026**, sans carte, sans ComfyUI
et sans réseau — le parc y est posé en mémoire. Les bancs grossissent ;
lance-les plutôt que de recopier ces nombres.

Deux des cas de `banc_repartition.py` ne mesuraient rien à l'origine : les trois
gardes du « pas de carte, pas de rendu » se recouvrent, la première suffit à
écarter une machine sans carte, et retirer l'une des deux autres laissait le banc
au vert. C'est le banc des mutations qui l'a montré, dix minutes après l'écriture
du banc ; chaque garde est depuis éprouvée à la place des deux autres — voir
[Éprouver les bancs](eprouver-les-bancs.md).

## Où lire la suite

- [Plusieurs machines, de puissances différentes](plusieurs-machines.md) — le
  parc, le débordement sur la RAM, et comment imposer une machine.
- [Plusieurs Ollama](plusieurs-ollama.md) — les adresses qui pensent, et le
  choix du modèle une fois l'adresse connue.
- [Attendre le retour d'une machine en pause](attendre-une-machine.md) — ce qui
  arrive à une demande qui réclame une carte qu'on a mise en pause.
- [Mesures](mesures.md) — les durées citées ici, avec leur date et leur machine.
