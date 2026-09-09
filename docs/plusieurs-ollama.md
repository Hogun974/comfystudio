# Plusieurs Ollama, et lequel le studio choisit

`OLLAMA_URL` accepte une **liste d'adresses séparées par des virgules** :

```
OLLAMA_URL=http://192.168.1.42:11434,http://192.168.1.191:11434
```

Une seule adresse obligeait à choisir une fois pour toutes la machine qui pense
— et celle qu'on choisit est la plus grosse, donc justement celle qu'on met en
pause pour jouer.

Passer par l'agent d'une autre machine n'est pas un repli acceptable pour ce
cas-là : mesure du 31 août 2026, la même question coûte **3,8 s en direct,
74,8 s à pc par son agent et 162,6 s à zima**. Le studio parle donc à chaque Ollama en
direct, et choisit. (La bascule par l'agent reste utile quand il n'y a *pas*
d'adresse — voir [Le modèle de langage peut venir d'une autre
machine](modele-de-langage-distant.md).)

## L'ordre appliqué

Trois règles, dans cet ordre :

1. **Une machine en pause ne pense pas.** Son propriétaire s'en sert.
2. **Une carte libre passe devant une carte occupée.** Attendre deux minutes
   derrière un rendu quand une autre machine répond tout de suite n'a de sens
   pour personne.
3. **À égalité, la plus grosse carte.** L'analyse est courte et tout le reste
   l'attend : plus tôt elle finit, plus tôt la carte repart au travail.

**La troisième règle disait l'inverse jusqu'au 1er septembre 2026**, et elle
n'était retournée que pour la lecture d'image. C'est cette exception qui est
devenue la règle : mesure du 31 août 2026, la même image lue en 19 s sur la
2080 Ti de **pc** et toujours pas rendue après *neuf cents* secondes sur la
GTX 1060 de **zima**, où le modèle de vision déborde. « La plus petite qui
suffise » suppose qu'elles suffisent toutes ; ici, non — et l'ancien
raisonnement, « occuper la meilleure pour réfléchir, c'est la retirer du rendu »,
supposait que l'analyse et le rendu se disputent la carte pendant le même temps.
Une analyse dure quelques secondes, un rendu des minutes.

Le rendu, lui, suit la règle opposée. Les deux sont dans [Qui prend le
travail](qui-prend-le-travail.md).

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
- **Le modèle d'écriture est borné par la carte de la machine.** Sur la carte
  de 11 Go de **pc**, `gemma4:26b` et ses 18,6 Go coûtaient cent soixante-cinq
  secondes par traduction — mesure du 31 août 2026. Une machine du parc annonce
  sa carte et sa RAM ; on s'en sert, avec un plafond à **60 % de la RAM** —
  la valeur est dans `serveur.py`.
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

## Un Ollama peut avoir une carte et ne pas s'en servir

C'est la panne la plus coûteuse qu'on ait rencontrée, parce que rien ne la
signale : la machine répond, elle annonce ses modèles, le studio la choisit
comme cerveau, et chaque analyse prend deux à cinq minutes au lieu de deux
secondes.

Relevé du 7 septembre 2026 sur **zima** (NAS ZimaOS, GTX 1060 de 6,3 Go) :

| | |
|---|---|
| ComfyUI, même machine | `cuda:0 NVIDIA GeForce GTX 1060`, 6,28 Go libres |
| Ollama, `/api/ps`, `gemma3:4b` | 5,25 Go en mémoire, **0,00 Go sur la carte** |
| Une analyse du studio | 119 à 300 s, contre 1 à 2 s sur la RTX 2080 Ti |

Le modèle le plus petit installé, qui tient trois fois dans la carte, est
entièrement sur le processeur. **Ce n'est donc pas un modèle trop gros**, et
`PART_CARTE_ANALYSE` n'y peut rien : cet Ollama-là n'a aucune carte. Le
`zimaos-comfyui.yml` de ce dépôt lui déclare pourtant le GPU exactement comme à
ComfyUI, qui l'obtient — les deux blocs `deploy.resources.reservations.devices`
sont identiques. La cause est donc dans le conteneur Ollama, pas dans la
déclaration.

**Le diagnostic, depuis n'importe quelle machine du réseau**, sans rien
installer :

```bash
curl -s http://LA_MACHINE:11434/api/ps
```

`size_vram` à `0` alors que `size` est plein, c'est un Ollama sur processeur.
Rien d'autre ne le dit : ni la bannière, ni `/api/tags`, ni la console.

**La réparation se fait sur la machine**, et elle demande son terminal :

```bash
docker logs ollama 2>&1 | grep -i "gpu\|cuda\|driver"
```

Trois réponses possibles, trois remèdes :

- *« no compatible GPUs were discovered »* — le conteneur n'a pas reçu la
  carte. Vérifier que l'installateur d'applications a bien honoré le bloc
  `deploy` (certains le suppriment), et que `nvidia-container-toolkit` est
  installé sur l'hôte.
- une erreur CUDA nommant une version de pilote — l'image est plus récente que
  le pilote de la machine. `ollama/ollama:latest` change sous les pieds :
  épingler une version qui marchait (`ollama/ollama:0.x.y`) est le seul remède
  durable.
- rien du tout — l'Ollama tourne peut-être hors du conteneur qu'on croit.

Tant que ce n'est pas réparé, la machine reste un cerveau **utilisable mais
lent**. Le studio ne la met pas dehors — un cerveau lent vaut mieux que pas de
cerveau — mais `STUDIO_ANALYSE_DELAI` (180 s) borne ce qu'une demande accepte
de l'attendre, et le reste se fait par mots-clés. Voir
[Réglages](reglages.md).

## Deux voies vers le modèle d'une machine, et un essai qui n'en teste qu'une

Le studio parle **en direct** à chaque Ollama dont `OLLAMA_URL` porte
l'adresse : c'est le chemin de toutes les analyses, 3,8 s mesurées le 31 août.
Il peut aussi **emprunter le modèle par l'agent** — le studio dépose une
question, l'agent vient la chercher et la porte à son Ollama local. Cette
seconde voie existe pour les machines que le studio ne peut pas joindre ; elle
coûtait 74,8 s sur le PC et 162,6 s sur le NAS.

L'essai de modèle de `/admin` emprunte la seconde, et il le dit désormais dans
sa réponse. **Sans le dire, son verdict se lisait comme celui du modèle
lui-même** — et il s'est trompé dans les deux sens en deux jours : vert le
8 septembre 2026 quand toute analyse revenait vide, rouge le 9 quand elle
répondait en 1,7 s.

## Une machine qui prête son langage peut se taire pour toujours

Défaut du 9 septembre 2026, sur `pc`, et **rien nulle part ne le disait**.
L'agent cherchait son Ollama **une seule fois**, au démarrage : le réglage,
puis les deux voisins de conteneur, huit secondes chacun. Ce matin-là il
redémarre à 09:27 après sa mise à jour, `/api/tags` ne répond pas dans ce
délai, et la machine se déclare sans langage **pour toute la vie du
processus** — quatre modèles installés, un Ollama qui répondait à la seconde
suivante, et le studio prévenu qu'elle n'en prêtait aucun.

Rien ne cassait : la voie directe marchait, les analyses tombaient en 1,7 s.
Seule la voie de secours était morte, et le seul symptôme visible était un
essai de modèle qui attendait ses 180 s puis rendait « n'a pas répondu à
temps ».

L'adresse est donc **cherchée à nouveau à chaque annonce** tant qu'elle
manque ou qu'elle ne répond plus, le fil des questions part toujours et
attend qu'une adresse paraisse, et le changement est **écrit sur la
console**. Le dictionnaire `llm` part avec chaque annonce, même vide : ne pas
l'envoyer laissait le studio sur ce qu'il avait appris une heure plus tôt.

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
