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

Voir [Qui prend le travail](qui-prend-le-travail.md) pour les règles que ces
mutations éprouvent.

## Si tu ajoutes un banc

Ajoute-lui sa mutation. **Un filet qu'on n'a jamais vu rougir ne mesure rien.**
Le détail de ce qui est attendu d'une contribution est dans
[`CONTRIBUTING.md`](../CONTRIBUTING.md).
