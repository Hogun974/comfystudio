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

## Trois façons d'échouer

| Ce qui arrive | Ce que cela veut dire |
|---|---|
| La mutation passe au **vert** | le filet a un trou — exactement celui qui a laissé passer `priorite,` |
| L'**ancre** de la mutation n'existe plus | elle ne mesure plus rien, et personne ne s'en apercevrait |
| Le dépôt **sain** rougit | un banc qui rougit sur tout n'attrape rien non plus |

La deuxième est la raison pour laquelle une mutation s'ancre sur **un motif de
texte et jamais sur un numéro de ligne** : `serveur.py` change plusieurs fois par
jour. Une ancre périmée est comptée en échec, pas en succès silencieux.

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

Voir [Qui prend le travail](qui-prend-le-travail.md) pour les règles que ces
mutations éprouvent.

## Si tu ajoutes un banc

Ajoute-lui sa mutation. **Un filet qu'on n'a jamais vu rougir ne mesure rien.**
Le détail de ce qui est attendu d'une contribution est dans
[`CONTRIBUTING.md`](../CONTRIBUTING.md).
