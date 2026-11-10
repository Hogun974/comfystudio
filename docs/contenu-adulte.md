# Contenu adulte

Le studio ne filtre pas. L'aiguilleur a pour consigne de transcrire fidèlement la
demande, sans édulcorer. Pony reçoit automatiquement sa balise `rating_explicit`
quand c'est pertinent — sans elle il s'autocensure.

Une seule limite est codée en dur : le contenu sexuel impliquant des mineurs est
refusé, avant l'aiguillage et après la réécriture du prompt — **et sur le prompt
qui part vraiment au moteur**, enrichi et traduit, ainsi que sur la description
de zone qu'écrit le modèle pour une retouche. Ces deux textes-là, écrits par un
modèle de langage, partaient sans être relus jusqu'au 4 novembre 2026.

**En six langues** : français, anglais, et depuis le 4 novembre 2026 allemand,
espagnol, italien, portugais. Mesuré ce jour-là, avant le changement : sur dix-neuf
paires « mineur + sexuel » dans ces quatre langues, le garde-fou en refusait
**zéro** — il ne tenait que par le prompt traduit en anglais, et klein ou Qwen,
qui lisent la demande telle quelle, ne traduisent pas. Après : dix-neuf sur
dix-neuf, et aucun faux positif sur les demandes ordinaires du banc.

**Et dans les autres langues, c'est le modèle de langage qui lit.** Une demande
en néerlandais, en polonais ou en turc ne dit rien aux motifs ; ce qui la fait
refuser, c'est l'analyse, qui la réécrit en français, et le garde-fou qui relit
cette réécriture. **Le modèle est donc, sans qu'on l'ait voulu, un filet de la
limite dure** : il donne aux motifs une seconde lecture, en français courant,
de ce qu'ils n'ont pas su lire tel quel. Depuis le 10 novembre 2026, trois
règles en découlent.

- **L'analyse ne se saute pas par défaut.** Le raccourci qui fait partir sans
  analyse une demande où tout est décidé est un réglage,
  [`STUDIO_ANALYSE_SANS_OBJET`](reglages.md), **éteint par défaut** : il
  échange dix à quatorze secondes par demande contre cette relecture. Allumé,
  il ne s'ouvre que si la langue de la demande est **prouvée** être l'une des
  six — six mots-outils différents au moins, un mot sur cinq, et deux fois
  plus de mots propres à elle qu'à une langue voisine (le catalan face à
  l'espagnol, le néerlandais face à l'allemand) —, s'il n'y a **aucune lettre
  non latine**, et si **aucun mot de mineur** n'y figure. Ce que cette preuve
  ne prouve pas, et pourquoi le réglage est éteint : elle dit la langue du
  texte, pas que les motifs lisent la partie qui compte — trois mots d'une
  autre langue au milieu d'une demande française lui échappent.
- **Le texte de l'auteur ne remplace un résumé que s'il peut être relu.** À
  quarante mots et plus, quand l'analyse a réduit la demande de plus de moitié,
  c'est le texte de l'auteur qui part ([`STUDIO_DEMANDE_DETAILLEE`](reglages.md))
  — mais le garde-fou n'avait lu que le résumé. Hors d'une langue prouvée lue,
  ou dès qu'une lettre n'est pas latine, c'est donc le résumé qui part, et le
  fil le dit.
- **Une langue prouvée non lue n'est jamais rendue sans qu'un modèle l'ait
  lue.** La preuve : quatre lettres d'une écriture non latine, ou trois mots
  différents propres à une même langue voisine, qui compte pour un mot sur
  cinq, dans la demande entière ou dans une fenêtre de huit mots. Pour cette
  demande-là, l'analyse n'est plus coupée par la borne du moteur imposé
  (`STUDIO_ANALYSE_IMPOSE_DELAI`), et si aucun modèle ne répond, elle s'arrête
  au lieu de partir par mots-clés : « je ne peux pas vérifier cette demande :
  elle est écrite dans une langue que je ne sais lire qu'avec un modèle de
  langage… » (code `langue_non_lue` pour un programme). Quand **rien n'est
  prouvé** — « un chat roux », trop court —, rien ne change.

Mesuré sur les corpus du dépôt : aucune des 3 540 demandes françaises,
anglaises, allemandes et espagnoles n'est prise pour une langue non lue, ni
aucune des 180 demandes de la relecture, pleines de noms propres (« Portrait de
Dan, torse nu », « Majin Bu charging a ki blast » : la première version en
refusait quatorze, faute d'exiger trois mots et d'écarter ceux qui sont aussi
des noms) ; regroupées en pavés de quarante mots, 599 sur 599 sont reconnues en
français, 20 sur 21 en anglais, 19 sur 19 en allemand, 17 sur 20 en espagnol.
Ses limites sont écrites dans le code : une langue latine absente des listes et
proche de l'une des six (l'occitan, le corse) peut passer pour lue ; et une
demande courte dans une langue non lue, ou quelques mots étrangers au bout
d'une demande française, dont rien ne se prouve, partent encore comme avant
quand aucun modèle ne répond.

Deux mots sont laissés dehors exprès, parce qu'ils feraient refuser une demande
innocente dès qu'un enfant y figure : *nudo* (le nœud, en espagnol) et *teta* au
singulier (l'allaitement). Et un défaut est connu, affiché par le banc plutôt
que caché : *sexe*, *sexo*, *sesso* disent aussi le **genre** — « révéler le
sexe du bébé » est refusé. Le garde-fou ne retire pas ces mots : « montre le
sexe du bébé » porte les mêmes, et aucun motif ne sépare les deux sens. Mais
quand le refus ne tient **qu'à** l'un d'eux, il dit comment reformuler : « si tu
parlais du genre, écris *fille ou garçon* ». Et le refus se lit désormais dans
la langue de la page, au lieu de partir en français.

**Relu le 10 novembre 2026**, par une relecture indépendante qui a prouvé que
des formulations ordinaires passaient. Des quatre-vingt-neuf paires ajoutées au
banc ce jour-là, le garde-fou d'avant en refusait une. Trois familles :

- **l'âge** n'était lu qu'en chiffres suivis d'une espace. Il l'est maintenant
  en lettres dans les six langues (« de huit ans », « eight year old », « von
  acht Jahren »), à tirets (« 8-year-old »), abrégé (« 8yo », « aged 8 »). Un
  âge n'est pas une durée : « marié depuis huit ans », « un whisky de douze
  ans », « vingt-huit ans » ne disent pas un mineur ;
- **les noms** les plus courants manquaient : « petite fille », « little boy »,
  « baby », « teenage », « bimba », « una nina » sans tilde, « ein nacktes
  Kind » — *Kind* et *nina* comptent par ce qui les entoure, parce que *kind*
  est un mot anglais et *Nina* un prénom. *nudo* aussi compte désormais par sa
  place : l'adjectif italien (« un bambino nudo »), pas le nœud espagnol ;
- **l'écriture** : le texte est mis en plusieurs *lectures* avant d'être lu —
  accents décomposés, caractères invisibles, pleine chasse, chiffre à la place
  d'une lettre (« enf4nt »), mot coupé ou épelé. La règle adulte lit les mêmes.

Et l'autre moitié de la conjonction : le garde-fou lit, **lui seul**, une liste
de mots crus que la règle adulte ne connaît pas (« déshabillé », les actes, les
étiquettes des moteurs à étiquettes). Ce que la règle adulte doit en connaître
n'a pas été décidé — le banc affiche le compte.

Les locutions où « nu » ne dit pas la nudité ne comptent pas pour cette
moitié-là : « pieds nus », « tête nue », « à mains nues », « bras nus », « à
l'œil nu », et leurs équivalentes (« the naked eye », « nackte Füße », « pies
desnudos », « a piedi nudi », « a olho nu »). « Un enfant pieds nus sur la
plage » était refusé, depuis toujours. Elles sont retirées du texte, elles
seules : « petite fille nue, pieds nus » reste refusée, comme « torse nu ». Et
une locution coordonnée à une autre partie du corps n'en est plus une : dans
« torse et pieds nus », l'adjectif vaut aussi pour le torse.

Ce que ce filtre **ne fait pas**, et il faut le savoir : il lit des mots, dans
six langues. Une demande en néerlandais, en polonais ou en grec n'a aucun mot
qu'il connaisse ; elle n'est gardée que par le prompt traduit en anglais.
« fille », « girl », « Mädchen », « jeune fille » seuls ne disent pas un
mineur, et un âge dit sans le dire (« en CE2 », « née en 2018 ») n'est pas lu.
`banc_adulte.py` porte chaque cas, dans les deux sens, et affiche les prix
connus.

Une demande venue d'un programme ([Piloter le studio par
programme](piloter-par-programme.md)) suit exactement les mêmes règles, et le
garde-fou y est passé **avant la file** : le programme reçoit un refus `422`
(`refus_mineurs`) au lieu d'un rendu en erreur découvert plus tard, et rien
n'est compté dans le plafond de sa clé.

Une règle s'ajoute dès qu'une clé d'API est posée : **une demande adulte ne sort
jamais de la machine**, ni vers un LLM distant, ni vers un générateur d'images
distant. Elle est appliquée dans le code, avant l'appel, et le journal de la
tâche l'annonce. Elle lit les mêmes six langues : avant le 4 novembre 2026, cinq
demandes adultes sur vingt et une en allemand, espagnol, italien ou portugais
étaient reconnues — les autres pouvaient partir au nuage.

**L'image jointe aussi, depuis le 4 novembre 2026.** Avant de partir chez un
fournisseur distant, elle est montrée au **modèle de vision local**, une seule
question — nudité, contenu sexuel ou érotique — et une réponse en booléen :

- **adulte**, ou **une réponse illisible** : l'image reste à la maison, la
  retouche est faite sur une carte d'ici. Un modèle qui a répondu à côté ne doit
  pas laisser sortir une image dont personne n'a su dire si elle était adulte ;
- **saine** : elle part, comme avant ;
- **aucun modèle de vision joignable** — un studio sans carte, tout au nuage :
  elle part aussi, mais le fil de la demande le dit (« image jointe non
  inspectée »). Refuser là casserait toute retouche distante d'un studio qui n'a
  que le nuage.

L'image ne quitte pas la machine pour être jugée : avec une image, l'appel au
modèle de langage reste toujours local. Le jugement coûte quelques secondes,
seulement quand une image s'apprête à partir, et une fois par image. Une clé
d'accès sans droit au nuage, elle, n'y va jamais.
