# Attendre le retour d'une machine en pause

Une demande qui réclame une carte précise — le seul moteur qui tienne, la seule
machine qui porte le modèle — n'a nulle part où aller quand cette carte est en
[pause](machines-a-agent.md#mettre-une-machine-en-pause). Le studio a trois
réponses, et elles se suivent dans le temps.

| | |
|---|---|
| **Pause récente** | la demande patiente devant l'écran, le dit dans son journal, et repart dès que la machine revient. |
| **Pause plus ancienne que le délai réglé** | la demande est **gardée armée** : elle sort de la file d'attente et repartira toute seule au réveil de la machine. |
| **Réglage à zéro heure** | le refus d'avant, mot pour mot — pour qui préfère qu'un refus soit un refus. |

Le refus était volontaire : faire patienter une demi-heure devant l'écran pour
une machine que personne ne compte rallumer, c'est perdre le temps de quelqu'un
poliment. Mais il laissait sans recours — la demande était perdue, il fallait la
retaper au retour.

## Ce que « armée » veut dire

Le studio écrit dans le fil ce qu'il fait, avec le temps qui reste :

```
PC du salon pourrait faire ce travail, mais elle est en pause depuis plus de
30 minutes. Ta demande est gardée en attente : elle partira toute seule dès
que la machine reviendra, pendant encore 12 h. Retire-la de la file si tu
préfères demander autre chose.
```

**Elle apparaît dans le panneau de la file**, en dernier et sans rang : elle
n'attend pas la carte mais son propriétaire, et se ranger devant ou derrière
quelqu'un n'aurait aucun sens. C'est de cette ligne que part le bouton
**retirer**, le seul recours — et elle compte dans le compteur de la file, sans
quoi une demande armée seule donnait un panneau de largeur nulle, donc
inatteignable, pendant douze heures. La bulle porte une pastille tiretée avec le
même bouton, et pas de chronomètre : un compteur qui monte pour un travail qui
ne partira peut-être que demain ne dit rien de vrai.

**Elle survit à un redémarrage du studio.** Une demande armée reste dans
`_file.json` comme les autres, avec tout ce qu'elle portait — texte, image
jointe, moteur imposé, taille, priorité, machine, plan. L'échéance est écrite
sur l'entrée de file et non gardée en mémoire : un redémarrage ne remet pas le
compteur à zéro, et une machine qui sort de pause puis y retourne ne réarme pas
la demande à chaque aller-retour.

Corollaire : **un studio arrêté plus longtemps que l'échéance ne réarme pas.**
Vingt heures d'arrêt sur une échéance de douze, et la demande est terminée tout
de suite plutôt que remise en file — une analyse complète économisée, et plus de
« pendant encore -480 min » suivi d'une mort trente secondes plus tard.

**Une conversation purgée pendant l'attente ne laisse pas de zombie.** La
corbeille des conversations fermées tourne dans le même veilleur, et l'attente
peut monter à une semaine. La demande est alors abandonnée en le disant, plutôt
que de rester « en cours » pour toujours dans un fichier de file que le
démarrage suivant aurait déplacé en entier.

**Elle n'immobilise aucun travailleur.** Le studio en mène trois de front ; une
demande mise de côté rend la main aussitôt, et la file continue de se vider.
Mesuré au banc : cinq demandes en attente d'une machine éteinte, trois
travailleurs, la file se vide et rien ne reste en vol.

## Trois portes de réveil, une seule question

La sortie de pause dans `/admin`, l'annonce d'une machine qui revient, et un
veilleur toutes les trente secondes. Toutes les trois posent la même question :
**« y a-t-il maintenant une machine pour ce travail ? »** — et non « la pause
est-elle finie ? ».

C'est la seule question dont la réponse fasse repartir le travail. Un modèle
arrivé entre-temps, une machine rallumée qui s'annonce, une autre carte devenue
éligible réveillent donc aussi bien qu'un clic dans `/admin` ; et un battement
d'une machine **toujours** en pause ne déclenche rien.

Deux précautions : le désarmement est posé avant toute attente, pour que deux
réveils dans la même seconde ne relancent pas deux fois la même demande ; et un
plancher de quinze secondes protège d'une machine qui fait la navette, chaque
relance coûtant une analyse complète.

La demande relancée repart **à la queue** de la file, pas en tête : elle a
attendu des heures, quelques minutes de plus ne se sentent pas, et passer devant
ceux qui patientent depuis dix minutes serait plus surprenant que juste.

## L'expiration se dit

Passé le délai, la demande est retirée et **on le dit** :

```
ERREUR : PC du salon n'est pas revenue en 12 h : ta demande a été retirée de
l'attente. Relance-la quand la machine sera là.
```

Une demande qui aurait silencieusement disparu du panneau serait pire que le
refus qu'elle remplace : au moins le refus arrivait pendant que l'utilisateur
regardait.

## Les deux réglages

Sous le tableau des machines, dans `/admin` :

| Réglage | Défaut | Variable de départ |
|---|---|---|
| Minutes qu'une demande patiente devant l'écran | 30 | `STUDIO_PAUSE_PROPOSE` |
| Heures qu'elle reste ensuite armée | 12 | `STUDIO_ARMEE_HEURES` |

Douze heures : une pause commencée le soir se termine le lendemain matin, et
c'est la plus longue absence au bout de laquelle une image qui arrive toute
seule fait encore plaisir plutôt que peur. Le maximum réglable est de 168 heures
(une semaine) ; **zéro supprime le second temps** et rétablit le refus immédiat.
