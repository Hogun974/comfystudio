# Rendre la carte quand plus rien ne la demande

> **Ce réglage change le comportement de toute installation existante à la mise
> à jour.** Il arrive **armé à une minute**. Si tu ne rends qu'une image de
> temps en temps, tu paieras désormais un rechargement du modèle à chaque fois
> — de vingt à quarante secondes selon le moteur et le disque — parce que la
> carte aura été rendue entre-temps. Mets le réglage à **0** dans `/admin` pour
> l'annuler complètement et retrouver exactement le studio d'avant, où rien
> n'est jamais libéré.

## Le problème

ComfyUI garde le modèle sur la carte après un rendu. C'est délibéré de sa
part : le rendu suivant repart tout de suite. Mais entre deux rendus, six à
douze gigaoctets de mémoire vive de la carte sont pris pour rien — et si tu
veux jouer, ou lancer autre chose sur cette machine, il faut aller couper
ComfyUI à la main.

La seule réponse du studio jusqu'ici était la **pause** : un bouton dans
`/admin` qui empêche la machine de recevoir du travail. Mais une pause ne rend
pas la mémoire ; elle empêche seulement d'en reprendre. Et il faut y penser.

## Ce que fait le studio

Quand une machine n'a **plus rien à faire** depuis le délai réglé, le studio
lui demande de rendre sa mémoire. La machine **continue d'accepter du travail**
— ce n'est pas une pause, il ne se passe rien d'autre que la mémoire qui se
libère. La demande suivante rechargera le modèle, et c'est tout ce qu'elle
coûtera.

Il y a **un seul réglage pour tout le parc**, sous le tableau des machines dans
`/admin`, et sa valeur de départ vient de `STUDIO_VRAM_REPOS`.

**Une minute par défaut, comme Ollama.** Le studio demande déjà à Ollama de
rendre la carte au bout de soixante secondes (`STUDIO_LLM_GARDER`), et pour
exactement la même raison : *ComfyUI reprend la carte juste après*. Les deux
gros consommateurs de la même carte la rendent maintenant au même rythme.

## Quand la consigne ne part pas

Cinq situations retiennent la carte, et chacune est là parce que la libérer
coûterait un rechargement juste avant l'usage :

- un travail **tourne** sur la machine ;
- un travail lui a été **déposé** et elle n'est pas encore venue le chercher ;
- son **verrou** est tenu — une analyse le prend avant même qu'un travail
  existe ;
- une demande a **choisi** cette machine et télécharge encore ses modèles :
  entre le choix et le dépôt il y a des minutes ;
- une demande **armée** attend son réveil (voir [Attendre le retour d'une
  machine en pause](attendre-une-machine.md)).

Deux autres cas, plus discrets :

- **la carte est déjà vide.** Le studio regarde ce qu'elle tient réellement ;
  au-dessous de deux gigaoctets, il n'y a aucun moteur du catalogue dessus et
  il ne se passe rien du tout. Un appel qui ne rend rien ne se distinguerait
  plus d'un échec le jour où l'on lit le journal.
- **on ne sait pas ce qu'elle tient.** Un agent d'avant cette version n'annonce
  pas sa mémoire libre. L'absence n'est pas un zéro : le studio ne conclut
  rien, donc ne demande rien.

**La pause, elle, n'empêche rien** — et c'est voulu. Une machine en pause ne
recevra pas de travail, donc rien ne viendra reprendre sa carte : c'est
précisément le cas *« je vais jouer un peu »* pour lequel ce réglage existe.

## Comment ça voyage

Le studio **n'appelle jamais** une machine à agent : c'est elle qui l'appelle,
toutes les dix secondes. La consigne descend donc dans la **réponse à
l'annonce**, à côté de la cadence et de la demande d'inventaire, et l'agent
exécute chez lui un `POST /free` sur son propre ComfyUI. L'agent revérifie au
passage qu'il n'a pas pris un travail entre-temps — c'est la seule chose que
le studio ne peut pas savoir à temps.

La machine **hôte**, elle, est appelée directement : le studio a son adresse.
La décision est la même fonction dans les deux cas, seul le transport change.

**Une consigne au plus par période de repos.** Une fois qu'elle est partie, le
studio sait qu'elle est partie et ne recommence pas. Un travail qui passe
rouvre le droit à une nouvelle consigne.

## Comment on voit que ça marche

La colonne « carte » de `/admin` affiche maintenant la **mémoire libre** de
chaque machine, à côté de sa taille totale : `3.2 / 11 Go libres`. La donnée
arrivait à chaque battement depuis toujours et n'était affichée nulle part.

Un `?` à la place du chiffre veut dire que la machine ne le dit pas — ce n'est
pas la même chose que `0`.

Et la console du studio écrit une ligne, **une seule**, par libération :

```
  PC (RTX 2080 Ti) a rendu 9.9 Go de carte apres 1 min sans travail
```

## Si ton ComfyUI ne connaît pas `/free`

C'est possible : `/free` est la première route neuve que le studio emploie
depuis longtemps, et un ComfyUI assez ancien répond `404`. Ça se voit alors
**une fois** dans la console :

```
  NAS ZimaOS : son ComfyUI a refuse /free (404) — la carte ne sera plus
  liberee sur cette machine. Un ComfyUI trop ancien ne connait pas cette
  route ; mets-le a jour et relance-le.
```

Puis le studio **cesse de demander** à cette machine : sans cette mémoire, la
même ligne s'écrirait six fois par minute, ce qui est exactement la façon dont
on cesse de lire un journal. La question se rouvre toute seule au **retour de
son ComfyUI** — c'est l'événement qui suit une mise à jour.

Il reste un cas que le code de retour ne dit pas : un ComfyUI qui répond `200`
et ne libère rien, parce qu'autre chose tient la carte. C'est la mémoire libre
du battement suivant qui l'attrape, et la console l'écrit :

```
  PC (RTX 2080 Ti) n'a rendu que 0.1 Go — son ComfyUI accepte /free sans rien
  liberer, ou quelque chose d'autre tient la carte
```

Et si la machine n'a rien rendu **parce que son agent est périmé**, le studio le
dit plutôt que d'accuser ComfyUI — il compare l'empreinte qu'elle annonce à
celle qu'il distribue :

```
  NAS ZimaOS n'a rien rendu : son agent est perime et ne connait pas encore
  cette consigne — voir /admin
```

## Mettre les agents à jour

Une machine à agent ne comprend la consigne que si son agent est à jour.
L'agent se remplace **tout seul** : il compare son empreinte à celle que le
studio distribue et se met à jour entre deux travaux, jamais pendant un rendu.
Il suffit donc de redémarrer le studio avec cette version et de laisser les
machines s'annoncer — quelques minutes.

Deux cas où ça ne se fait pas tout seul, et `/admin` les montre en marquant la
machine « agent périmé » :

- l'agent tourne avec `--sans-maj-auto` (ou `AGENT_SANS_MAJ_AUTO`) ;
- une empreinte est **épinglée** par `--empreinte` : l'agent refuse alors toute
  version qui ne correspond pas, et le dit dans sa console.

Dans ces cas-là, sur la machine concernée :

```
python agent_noeud.py --maj      # puis relancer l'agent
```

ou, plus simplement, `./maj_noeud.sh http://adresse-du-studio:8199` (Linux,
macOS) et `maj_noeud.bat` sous Windows, qui font la même chose depuis le studio.

Tant qu'un agent n'est pas à jour, il **ignore simplement** la consigne : rien
ne casse, sa carte n'est pas libérée, et le reste continue comme avant.

## Le réglage

| Où | |
|---|---|
| `/admin` | carte « rendre la carte au repos », sous le tableau des machines |
| `STUDIO_VRAM_REPOS` | la valeur du **premier** démarrage seulement — ensuite `/admin` fait foi |
| `0` | annule complètement le réglage : plus rien n'est jamais libéré |

Voir aussi [Réglages](reglages.md), [Des machines qui viennent
d'elles-mêmes](machines-a-agent.md) et [Attendre le retour d'une machine en
pause](attendre-une-machine.md).
