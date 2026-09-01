# Combien de temps ça va prendre

« Pourquoi celle-ci a mis quatre minutes » est la question qu'on se pose après,
et la [médiathèque](mediatheque.md) y répond. « Combien de temps ça va prendre »
est celle qu'on se pose **avant**, et rien n'y répondait — alors que le studio a
la réponse depuis le début : chaque tour terminé porte sa machine, son moteur,
sa taille et sa durée. Il ne les relisait simplement jamais.

Une fois la machine choisie et avant que le calcul parte, le journal de la
demande annonce :

```
d'apres tes 7 rendus precedents, compte 3 min
```

La bulle affiche le même chiffre à côté d'une pastille, et passe au rouge quand
le rendu dure plus longtemps que prévu.

## Le champ fait foi, la phrase est un repli

La page a longtemps relu **la phrase française** pour en tirer le chiffre. Elle
le fait encore en dernier recours, mais `/api/etat` sert désormais le devis en
clair — `secondes`, `mesures`, et le **mot à mot** de la phrase, pour que la
page n'ait plus à le reconstruire.

Les deux divergeaient de **33 %** : la phrase passait aux minutes dès 90 s, et
« 2 min » n'est pas 90 s. Le seuil de passage aux minutes est monté à cinq
minutes le 1er septembre 2026 ; sur des devis de 5 à 1800 s, le pire écart entre
la phrase et le champ tombe de **33,3 % à 9,1 %**. La fin de rendu dit déjà
« terminé en 223 s » : devis et résultat se comparent maintenant sans
arithmétique mentale.

**Le devis est retiré dès que plus aucune médiane ne l'étaye.** Une tâche survit
à une relance — même identifiant, même entrée de file — et le champ y restait tel
quel : une demande repartie en brouillon, ou relancée après que ses rendus
comparables ont été effacés, gardait le devis de son essai précédent. La phrase
du journal, elle, ne ment jamais ainsi : elle n'est simplement pas réécrite. Un
champ qui fait foi doit valoir au moins autant que le repli qu'il remplace.

## Le temps écoulé vient du serveur

`/api/etat` sert aussi **`ecoule`**, en secondes depuis le début réel de la
tâche. La page comptait auparavant depuis l'instant où **elle** s'était mise à
suivre : un rechargement remettait le compteur à zéro, et « 89 % · 6 s »
s'affichait sur un rendu qui durait depuis une minute. Signalé par l'utilisateur,
capture à l'appui.

Le serveur est de toute façon le seul à savoir quand la tâche a vraiment
commencé : une demande reprise après un redémarrage, ou sortie de la file
d'attente, a un début que la page n'a jamais vu. Le compte local ne sert plus que
pour les vieilles réponses, qui ne portent pas le champ.

La pastille du dépassement avait le même défaut : « dépassé » se comparait au
temps écoulé depuis que la page avait **vu** le devis, si bien qu'un rechargement
en plein dépassement la faisait repasser au vert.

## Du plus précis au plus général

Le devis se lit dans cet ordre, et s'arrête au premier niveau qui a assez de
mesures :

1. **(machine, moteur, taille)** — le cas exact ;
2. **(machine, moteur)** — une taille jamais vue sur cette machine retombe sur
   ce qu'on sait d'elle ;
3. **(moteur)** seul.

Approximatif, mais mieux que se taire.

## La médiane, et le silence

**La médiane et non la moyenne.** Un rendu qui a attendu une carte occupée
tirerait la moyenne sans rien dire de ce qui va se passer maintenant. Mesuré au
banc (`banc_durees.py`) : quatre rendus dont un à 2400 s donnent **120 s, pas
682**.

**On se tait en dessous de trois mesures** (`ASSEZ_DE_MESURES = 3` dans
`serveur.py`). Annoncer « environ quatre minutes »
sur un seul échantillon, c'est promettre au hasard — et perdre la confiance à la
première surprise.

Trois sortes de rendus ne comptent pas :

- **les esquisses** — un quart des étapes ne prédit pas une image finie (voir
  [Le brouillon](brouillon.md)) ;
- **les rendus échoués** ;
- **ceux des autres comptes.** Le journal dit « d'après **tes** rendus
  précédents » : un chiffre annoncé comme personnel qui ne l'est pas fait perdre
  la confiance dès qu'il ne colle pas — et il révélerait accessoirement le
  volume d'activité de quelqu'un d'autre.

Un rendu confié à un fournisseur distant est enregistré sous **le moteur qui a
réellement servi**, et non sous son repli local. Sans cela, trois vidéos rendues
au loin comptaient comme des mesures de Wan 2.2 5B, et « compte 200 s » était
annoncé pour une carte qui n'avait jamais rien fait de tel.

Aucun devis n'est annoncé pour un brouillon lui-même : il coûte un quart des
étapes, et l'annonce lui donnerait le prix d'une image finie.

## Plusieurs tirages

Quand une demande part en plusieurs variantes, le devis reste honnête : quatre
variantes coûtent quatre rendus, et c'est dit en **temps de carte** et non en
temps d'attente.

```
4 variantes, donc autant de rendus — environ 3 min chacune, soit 12 min
de calcul en tout, reparti sur les machines libres
```

Combien de machines seront libres à cette seconde-là, personne ne le sait ; et
promettre la moitié parce qu'il y a deux cartes serait promettre à la place du
voisin qui a lui aussi une demande en file.

**Le devis de la bulle compte un seul rendu, même quand on en lance quatre**, et
c'est un choix. La page compare ce chiffre au temps écoulé **de cette bulle-là**
pour dire « plus long que d'habitude » ; un total de groupe y retarderait
l'alerte de quatre rendus, c'est-à-dire la supprimerait. Et chaque tirage a sa
bulle : mettre le total sur le seul premier donnerait quatre promesses
différentes pour quatre rendus identiques.

Le coût du groupe est donc un **autre** chiffre, posé à côté et non par-dessus :
`/api/etat` le sert nommément, `rendus` et `total_s`. Les deux étaient à l'écran
en même temps sans que rien ne dise qu'ils ne comptaient pas la même chose —
« 60 s » dans la pastille, « 3 min » dans le journal, pour un groupe de trois.

## D'où viennent les chiffres

De vos conversations, relues et rangées toutes les deux minutes. Rien n'est
mesuré à part : les durées y étaient déjà, sur chaque tour terminé.

Les durées de référence du parc, chacune avec sa date et sa machine, sont dans
[Mesures](mesures.md) — mais c'est le vôtre que le devis vous annonce.
