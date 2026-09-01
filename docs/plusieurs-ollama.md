# Plusieurs Ollama, et lequel le studio choisit

`OLLAMA_URL` accepte une **liste d'adresses séparées par des virgules** :

```
OLLAMA_URL=http://192.168.1.42:11434,http://192.168.1.191:11434
```

Une seule adresse obligeait à choisir une fois pour toutes la machine qui pense
— et celle qu'on choisit est la plus grosse, donc justement celle qu'on met en
pause pour jouer.

Passer par l'agent d'une autre machine n'est pas un repli acceptable pour ce
cas-là : mesure du 31 août, la même question coûte **3,8 s en direct, 74,8 s au
PC par son agent et 162,6 s au NAS**. Le studio parle donc à chaque Ollama en
direct, et choisit. (La bascule par l'agent reste utile quand il n'y a *pas*
d'adresse — voir [Le modèle de langage peut venir d'une autre
machine](modele-de-langage-distant.md).)

## L'ordre appliqué

Trois règles, dans cet ordre :

1. **Une machine en pause ne pense pas.** Son propriétaire s'en sert.
2. **Une carte libre passe devant une carte occupée.** Attendre deux minutes
   derrière un rendu quand une autre machine répond tout de suite n'a de sens
   pour personne.
3. **À égalité, la plus petite carte.** Une analyse tient sur n'importe
   laquelle ; occuper la meilleure pour réfléchir, c'est la retirer du rendu
   qu'elle seule fait vite.

**Sauf pour lire une image, où la troisième règle s'inverse.** C'est la seule
tâche où la taille de la carte décide vraiment : mesure du 31 août, la même
image lue en 19 s sur la 2080 Ti et toujours pas rendue après *neuf cents*
secondes sur la GTX 1060, où le modèle de vision déborde. « La plus petite qui
suffise » suppose qu'elles suffisent toutes ; ici, non.

Une adresse dont on ne reconnaît aucune machine du parc — l'Ollama du studio
lui-même, ou une machine sans agent — n'a pas de carte connue : elle est traitée
comme libre et de taille nulle. Aucune carte n'est alors réservée, puisqu'on ne
saurait pas laquelle.

## Le modèle se choisit par adresse

Deux machines ne portent pas les mêmes modèles, et le plus gros ici peut être
absent là-bas. Le studio ne fixe donc plus un nom de modèle une fois pour
toutes : les appels portent une **intention** — écrire, voir — résolue au dernier
moment, une fois l'adresse connue.

- **`STUDIO_LLM_ECRITURE` l'emporte là où le modèle existe, et est ignoré
  ailleurs.** Imposer un modèle qu'une seule machine porte rendrait l'autre
  muette.
- **Le modèle d'écriture est borné par la carte de la machine.** Sur une carte
  de 11 Go, `gemma4:26b` et ses 18,6 Go coûtaient cent soixante-cinq secondes par
  traduction. Une machine du parc annonce sa carte et sa RAM ; on s'en sert.
- **Le studio ne change de modèle que si le gain est net** (une fois et demie la
  taille du modèle courant) : recharger un modèle à peine plus gros coûte du
  temps sans rien apporter.

## Une image ne part jamais sur une machine qui ne voit pas

Si aucun modèle de l'adresse ne déclare la capacité `vision`, **l'adresse est
écartée** — jamais de substitution. Un modèle de texte à qui l'on envoie une
image ne refuse pas : il décrit ce qu'il imagine, sans erreur et sans une ligne
de journal. Une description inventée est pire qu'une erreur, parce que rien ne
la signale.

Quand Ollama ne déclare aucune capacité du tout — une version plus ancienne — on
ne bloque rien : la lecture d'image ne doit pas devenir impossible pour cette
raison.

Sur l'adresse retenue, c'est le **plus gros** modèle voyant qui lit l'image, et
non le modèle d'aiguillage, même quand celui-ci sait voir aussi. « Le plus
gros » est un mauvais mandataire de « le meilleur », mais c'est le seul
classement disponible sans faire passer un examen à chaque modèle, et il colle à
la seule mesure qu'on ait : `qwen2.5vl:7b` lit juste, `gemma3:4b` non — il
déclare pourtant la vision. **Une capacité déclarée n'est pas une compétence.**

## Ce que la bannière annonce au démarrage

Une ligne par adresse, avec le modèle d'écriture de chacune et le nom de la
machine quand on la reconnaît :

```
  Ollama    : http://192.168.1.42:11434     ecrit avec gemma4:26b   [PC du salon]
              http://192.168.1.191:11434    ecrit avec gemma3:4b    [NAS]
```

La ligne unique d'avant annonçait le modèle de la *première* adresse et laissait
croire que c'était celui du studio — alors que la machine réellement employée est
souvent l'autre.

## La pause est respectée dès le démarrage

L'adresse d'où une machine parle est le seul champ *vivant* dont dépende une
décision de sûreté : c'est par elle qu'on reconnaît la machine qui héberge un
Ollama, donc qu'on respecte sa pause et qu'on réserve sa carte. Elle est donc
conservée dans `_parc.json` avec le reste de l'inventaire.

Sans cela, pendant les secondes qui suivaient un redémarrage — jusqu'à la
première annonce d'agent — le studio ne reconnaissait aucune machine derrière ses
adresses : la pause ne protégeait rien, et une analyse pouvait tourner sur la
même carte qu'un rendu, chez quelqu'un qui joue, sans une ligne de journal. Une
adresse périmée, elle, ne fait courir aucun risque : la première annonce la
corrige.
