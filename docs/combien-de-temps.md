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
4 variantes, donc autant de rendus — environ 12 min de calcul en tout,
reparti sur les machines libres
```

Combien de machines seront libres à cette seconde-là, personne ne le sait ; et
promettre la moitié parce qu'il y a deux cartes serait promettre à la place du
voisin qui a lui aussi une demande en file.

## D'où viennent les chiffres

De vos conversations, relues et rangées toutes les deux minutes. Rien n'est
mesuré à part : les durées y étaient déjà, sur chaque tour terminé.

Les durées de référence du parc, chacune avec sa date et sa machine, sont dans
[Mesures](mesures.md) — mais c'est le vôtre que le devis vous annonce.
