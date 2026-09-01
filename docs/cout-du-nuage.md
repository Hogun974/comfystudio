# Ce que le nuage a coûté

Rien ne disait ce que les appels distants coûtent : ni combien, ni par qui, ni
ce que ça représente. L'onglet **coût du nuage** de `/admin` le montre, et un
plafond mensuel permet de s'arrêter.

## Aucun euro nulle part

**Aucun prix n'est affiché, nulle part, et ce n'est pas un manque.** Les tarifs
changent d'un trimestre à l'autre, ce logiciel ne les suit pas, et il n'y a ici
aucune source fiable : un montant en euros serait faux sans que personne ne s'en
aperçoive. On compte ce qui est vrai et l'on laisse convertir — au moins, qui
tient la facture sait par quoi multiplier.

Ce qui est montré est mesuré : les appels, les jetons **quand l'API les rend**,
les octets reçus, la durée.

## Ce qui est compté, et ce qui ne l'est pas

Une ligne par appel **abouti**, dans `nuage.jsonl`, à côté de `avis.jsonl` et
dans le même format « une ligne, un objet » : le fichier se relit entièrement
même si l'écriture a été coupée au milieu de la dernière ligne, ce qui arrive
quand on arrête le conteneur.

| Champ | |
|---|---|
| `quand`, `mois` | la date de l'appel, et le mois qui sert de clé |
| `fournisseur` | `anthropic`, `google`, `meshy`… |
| `modalite` | `llm`, `image`, `audio`, `video`, `objet3d` |
| `compte` | le **nom** du compte, pas son identifiant — douze caractères hexadécimaux ne se reconnaissent pas dans un tableau |
| `jetons_entree`, `jetons_sortie` | tels que le fournisseur les compte, ou `null` |
| `octets` | ce qui a été reçu |
| `secondes` | la durée de l'appel |

**Un appel qui échoue n'est pas compté.** Il n'est pas facturé, et le compter
fermerait le robinet pour une dépense qui n'a pas eu lieu : la panne du
fournisseur se paierait deux fois.

**Les jetons sont pris là où l'API les donne, et écrits nuls sinon — jamais
estimés.** `usage` chez Anthropic, OpenAI, Mistral et les agrégateurs en
dialecte OpenAI ; `usageMetadata` chez Google. Compter les caractères pour en
faire des jetons donnerait un nombre qui a l'air juste et qui ne l'est pas.

**Veo et Meshy ne rendent qu'un nom de tâche.** Leurs appels comptent en
« *N* appel(s) sans décompte », et la vue le dit — sans ce nombre, une somme
basse passerait pour une petite facture alors qu'elle ne compte que les
fournisseurs bavards.

Les **octets** sont là pour cette raison aussi : un agrégateur ne rend pas
toujours d'`usage`, et une réponse mesurée en octets vaut mieux qu'une case vide.

## Deux mois, et pas plus

La vue montre le mois en cours et le précédent. Garder plus, en mémoire comme
sur le disque, ce serait un compteur qui grossit sans fin sur un studio qui
tourne des mois d'affilée.

Le fichier est donc réécrit sans les mois hors de portée de la vue dès qu'il
dépasse **deux mébioctets** — environ dix mille appels, bien plus qu'un studio
n'en fait en deux mois, donc un seuil qu'on n'atteint qu'anormalement. Mesuré le
1er septembre 2026 : 1 737 868 octets ramenés à 794, les lignes du mois en cours
intactes.

On ne tronque pas à l'aveugle : on jette d'abord ce qui est déjà hors de portée
de la vue, ce qui laisse intact tout ce qui reste consultable. Un plafond en
nombre de lignes n'intervient qu'ensuite, si deux mois d'appels ne tiennent
toujours pas dans la taille — le disque passe avant. Il est **dérivé du seuil**
et non posé à côté : à 20 000 lignes de 198 octets il en gardait 3,96 Mo pour un
seuil de 2, la taille ne redescendait donc jamais dessous et le fichier entier
était relu et réécrit **à chaque appel distant** — 97 ms mesurées sur 11 091
lignes le 1er septembre 2026, de quoi saturer la file d'écriture sur un volume
monté. Le taillage est en outre limité à une fois par minute.

## L'écriture est hors de la boucle

Un disque bloqué doit coûter une ligne de comptabilité, jamais figer une
génération en cours. L'écriture passe par une **file bornée** et un **fil
dédié** ; quand la file est pleine, la ligne est perdue et le studio le dit sur
sa sortie standard. Mesuré au banc (`banc_cout.py`), disque ralenti à 50 ms la
ligne : quarante appels en 2,0 ms au lieu de deux secondes — **pc**, 1er
septembre 2026. Le banc se rejoue, contrairement aux durées de carte : c'est
lui qu'il faut relancer plutôt que recopier ce chiffre.

Le total en mémoire, lui, est mis à jour tout de suite — c'est lui que le
plafond interroge, et il ne doit pas dépendre du moment où le disque aura
répondu.

La comptabilité est sur le chemin critique : un décompte inattendu ne doit pas
faire perdre un rendu **déjà généré, déjà payé et déjà écrit**. Elle est donc
protégée de bout en bout — une comptabilité fausse vaut mieux qu'une image
perdue.

## Le plafond mensuel

Au-delà de *N* appels distants dans le mois, **ce compte-là** revient au modèle
local. Zéro, le défaut, veut dire aucune limite : un studio qui se mettrait à
refuser le nuage sans qu'on le lui ait demandé serait une mauvaise surprise, pas
une protection.

Il se règle dans l'onglet **coût du nuage** de `/admin`, de 0 à 100 000, et sa
valeur de départ vient de `STUDIO_PLAFOND_NUAGE`.

Ce qu'il fait exactement, quand il est atteint :

- **toutes les modalités s'éteignent ensemble** — texte, images, musique, vidéo,
  objets 3D. Le plafond passe par le seul point où se décide « au loin ou à la
  maison », et l'interrupteur du nuage de la barre du haut s'éteint avec ;
- **un moteur distant choisi à la main dans la liste des moteurs est refusé lui
  aussi.** Sans ce contrôle-là, le robinet se rouvrait d'un clic dans le menu ;
- **la demande en cours n'est pas cassée** : le repli local du moteur distant
  prend simplement la suite ;
- **le journal de la demande dit pourquoi**, et ne laisse pas croire que
  l'utilisateur a coupé le nuage lui-même :

```
plafond du mois atteint (200 appels distants) — la generation reste sur cette machine
```

Le tableau signale le compte concerné par un « plafond atteint — retour au
local ».

## Voir aussi

- [Clés d'API : LLM et images](cles-api.md) — les fournisseurs, l'interrupteur
  par navigateur et le choix demande par demande.
- [Comptes](comptes.md) — c'est le compte qui porte la consommation.
