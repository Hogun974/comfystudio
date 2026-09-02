# Ce que le tour garde du plan

Une conversation est un fichier sur le disque. Chaque échange y laisse un
**tour** : la demande, le prompt envoyé, le moteur, les fichiers produits, la
machine, le temps. Depuis le **2 septembre 2026**, le tour garde aussi le
**plan** — ce que l'analyse avait décidé — et plus seulement sur les esquisses.

C'est un changement de **format sur disque**. Les conversations écrites avant
cette date ne portent pas de plan ; elles continuent de fonctionner, par un repli
qui a sa propre limite, écrite plus bas.

## Pourquoi : six champs en deux jours, six défauts

Avant, `enregistrer_tour` recopiait du plan une **liste de champs**, allongée
d'une entrée après chaque défaut constaté. Son commentaire refusait le plan
entier au motif que « personne n'en a l'usage ». Cet argument est mort le jour
où `POST /api/refaire` est né : le tour a eu un second relecteur, qui rejoue le
plan sans repasser par l'analyse. Ce que le tour ne porte pas est alors perdu en
silence.

Six ajouts, six pannes réelles, en deux jours :

| Champ manquant | Ce que le refait rendait |
|---|---|
| `negatif` | retombait sur `NEG_DEFAUT`, donc une autre image |
| `classement` | retombait sur « safe » — **un défaut de sûreté**, voir plus bas |
| `paroles` | la chanson réécrite par `ecrire_paroles()`, d'autres paroles |
| `langue`, `tonalite` | la chanson repartait en anglais, dans une autre tonalité |
| `raison` | un tiret nu dans le journal : « FLUX.2 klein 9B — » |

**Le cas du classement est le plus grave, et c'est pour lui que la liste ne
pouvait pas tenir.** « safe » ne pose pas la balise de score de Pony : la table
la **retire**. Et `adulte()` lit ce champ. Un rendu marqué explicite dont le
texte ne mord sur aucun motif pouvait donc repartir chez un fournisseur distant,
contre la règle « ce qui est adulte ne sort pas de la maison » — voir [Contenu
adulte](contenu-adulte.md).

Six fois la même panne, six correctifs au cas par cas. Porter le plan entier
supprime la **classe** de défaut au lieu de traiter chaque défaut.

## Ce que cela pèse

Mesuré le 2 septembre 2026 à travers le vrai `enregistrer_tour` et le vrai
`sauver` — `json.dump(ensure_ascii=False, indent=1)`, l'indentation compte, elle
ajoute une ligne par clé :

| | Avant | Après | Écart |
|---|---|---|---|
| Un tour d'image | | | **+776 o** |
| Un tour de chanson | | | **+1053 o** |
| Soixante tours d'images | 77,5 ko | 124,1 ko | +60 % |
| Soixante chansons | 86,8 ko | 150,0 ko | +73 % |

Les vingt conversations réelles de la machine d'essai pèsent 1184 o par tour en
moyenne ; la plus grosse, 16,3 ko pour onze tours. Le **plafond de soixante
tours** de `enregistrer_tour` borne le tout : une conversation ne dépassera pas
150 ko.

Le coût est inférieur au « environ un kilo-octet par tour » qui avait été
annoncé avant la mesure, et c'est la seule raison pour laquelle la décision
tient.

> Le message du commit `20ccd77`, du même jour, donne des chiffres plus bas —
> +596 o par tour d'image, +910 o par chanson, soixante tours de 77 503 à
> 113 263 o. Ils ont été relevés **avant** l'écriture, sur une liste de champs
> plus courte que celle qui a été retenue. Les chiffres du tableau ci-dessus
> sont ceux du commentaire de `serveur.py`, à l'endroit de la décision, et ce
> sont eux qui font foi.

## Pas le plan tel quel : quinze clés nommées

Le plan sort de `json.loads(réponse du modèle)` et garde **toutes** les clés que
le modèle a émises, y compris celles que personne ne lit. Le tour est écrit sur
le disque de l'utilisateur et relu à chaque ouverture de conversation : ce qui y
entre doit être **borné**. `PLAN_SUR_LE_TOUR` nomme quinze clés, et rien d'autre.

```
intention  modele  prompt  negatif  classement  largeur  hauteur
parametres  parametres_bruts  paroles  langue  tonalite  tags_audio
cases  raison
```

Sur un plan bavard, cela fait **486 o écrits pour 6 941 proposés** (relevé du
2 septembre 2026, message de `20ccd77`).

Deux bornes de plus à l'intérieur de la liste : `parametres` et
`parametres_bruts` sont réduits aux noms que `BORNES` sait lire — le second est
la proposition **brute** du modèle et peut porter n'importe quelle clé — et
`cases` est plafonné à six, le plafond que `g_planche_composee` applique déjà.

### Ce qui reste dehors, et pourquoi

- **`graine`** — le tour la porte déjà, prise sur la tâche. Deux sources pour la
  même graine, c'est deux graines le jour où l'une se décale.
- **`modele_impose`, `refait`, `variante`** — des marques du **geste**, reposées
  à chaque rejeu. Écrites sur le tour, elles seraient héritées en silence par le
  rejeu suivant.
- **`priorite`** — même nature, et un défaut concret : « brouillon » recopié sur
  le tour d'un refait ferait marquer ce refait comme une esquisse et lui
  reposerait le bouton « refaire en soigné ».
- **`enrichissement_rate`** — celui-là **casserait le bouton**. `executer` le
  relit *après* la branche du plan imposé : un refait reposerait la question
  « je l'envoie telle quelle ? » au lieu de rendre l'image, sur un chemin qui ne
  repasse justement pas par l'enrichissement.
- **`parametres_ajustes`** — la trace des bornes appliquées à l'analyse
  d'origine. Rejouée, elle ferait annoncer « bornes appliquées : cfg 12 → 8 »
  pour un ajustement qui n'a pas eu lieu cette fois.
- **`attente`, `raccourci`, `prompt_repli`, `questions`, `questions_forcees`** —
  des traces de l'analyse qui vient d'avoir lieu, et le rejeu ne refait pas
  d'analyse.
- **Tout le reste**, c'est-à-dire ce que le modèle a inventé. C'est la seule
  chose ici qui grossirait sans borne.

### Ce qui n'a jamais eu l'occasion d'y entrer

Vérifié clé par clé : **aucune image encodée en base64** (`img_b64` est calculé
dans `executer` et n'est jamais posé sur le plan), **aucun jeton ni clé d'API**
(ils vivent dans `_cles.json` et dans le registre des machines), **aucun chemin
absolu** — l'image de départ voyage en nom de fichier relatif à
`DOSSIER_ENTREE`, sur le champ `entree`. C'est le banc qui le tient désormais.

## Un rendu confié au loin n'écrit aucun plan

Sur le chemin d'un [fournisseur distant](cles-api.md), le plan ne décrit pas ce
qui a tourné : `plan["modele"]` porte le **repli local**, celui qui aurait servi
si le fournisseur avait échoué, et `plan["parametres"]` est remplacé par le seul
titre du fournisseur. C'est l'argument `cle` qui nomme le moteur réellement
employé.

Écrire ce plan-là ferait afficher « FLUX.2 klein 9B » sous une image rendue par
Nano Banana — la page lit `plan.modele` en premier et ne retombe sur le champ du
tour qu'à défaut — et la ligne « fournisseur » disparaîtrait. Le tour d'un rendu
distant ne porte donc **pas** de plan. Il n'y a rien à y perdre : les deux
boutons qui relisent le plan refusent justement un rendu confié au loin, chacun
avec sa phrase (voir [Pouce en l'air, pouce en bas](avis.md) et [Le
brouillon](brouillon.md)).

## Ce que le tour garde à plat, et qui n'est pas une redite

Quatre champs ont **cessé** d'être écrits à plat le 2 septembre 2026 —
`negatif`, `classement`, `langue`, `tonalite` — parce qu'ils n'avaient jamais eu
d'autre lecteur que la reconstruction de `api_refaire`. Les garder aux deux
endroits, c'était deux sources pour la même chose.

Trois restent en double, et chacun a un lecteur qui **n'ouvre jamais le plan** :

- **`taille`** est la clé de la table des durées (`durees_par_modele`) et ce que
  sert la [médiathèque](mediatheque.md). « Pourquoi celle-ci a mis quatre
  minutes ? » se répond neuf fois sur dix par la résolution.
- **`paroles`** est ce que la fiche d'avis écrit dans `avis.jsonl`, qui ne lit
  pas le plan. Sans elles, un pouce en bas sur une chanson ne dirait pas ce qui
  a déplu.
- **`graine`** vient de la tâche, et c'est celle-là que « refaire en soigné »
  relit.

## Le repli daté, et la fenêtre qu'il laisse ouverte

Un tour écrit avant le 2 septembre 2026 n'a pas de plan. Ce n'est plus le chemin
normal, mais il ne peut pas disparaître : une conversation garde soixante tours,
et ceux-là sont sur le disque de l'utilisateur pour de bon.

`api_refaire` reconstruit alors le plan à partir des champs plats du tour —
`prompt`, `modele`, `type`, `parametres`, puis `negatif`, `paroles`,
`classement`, `raison`, `langue`, `tonalite` quand le tour les porte.

**Les clés absentes ne sont pas posées à `None`.** `plan.get(cle, defaut)` rend
`None` quand la clé existe, et `classement` à `None` ne vaut pas « safe » :
`CLASSEMENT_PONY.get(None)` retire la balise de score au lieu de poser
`rating_safe`. C'est le même piège que celui qui a coûté le défaut de sûreté.

**Ce que ce repli ne sait pas reprendre**, et c'est la limite à connaître :

- `langue`, `tonalite` et `classement` ne sont écrits à plat sur le tour que
  depuis le **1er septembre 2026**. Une chanson d'avant cette date, refaite par
  ce chemin, **repart en `en` et `C minor`**. On ne le devine pas, et on ne le
  refuse pas : un bouton inopérant sur tout l'historique serait pire.
- `taille` n'est écrit que depuis le **31 août 2026**. Avant, le plan repartait
  sans largeur ni hauteur et `executer` levait `KeyError: 'largeur'` — affiché
  « ERREUR inattendue : 'largeur' », un plantage muet, sur ce qui était alors le
  cas le plus fréquent du bouton. On ne refuse pas et on n'invente pas de
  taille : on rejoue `caler_taille()` sur le même texte, c'est-à-dire le calcul
  que la demande d'origine a fait, et **le studio annonce la reprise** dans le
  journal.

**Cette reprise de taille ne vaut que pour une image.** Elle a été étendue un
temps à la planche, au motif qu'une planche refaite changeait de format. Le
motif était faux et le remède pire :

- `caler_taille()` n'est jamais appelé pour une planche sur le chemin normal —
  ses quatre sites d'appel sont tous gardés par `intention == "image"`. Le
  rejouer ici ne rejoue aucun calcul d'origine : il remplace une constante par
  une autre.
- La branche planche d'`executer` n'en lit pas le résultat. Elle impose son
  format page, plafonné à 960 de large, la hauteur venant d'un rapport A4. Le
  `1216x832` posé ici ressortait en `960x1344`, et le journal se contredisait à
  deux lignes d'intervalle.
- Et ce `1216x832` mentait ensuite **deux fois** : `enregistrer_tour` l'écrit
  dans `tour["taille"]`, donc la médiathèque affichait une résolution jamais
  rendue, et `_relever_durees` rangeait la durée sous cette clé — celle que
  `debordement_acceptable(exact=True)` relit pour trancher un débordement de
  carte. Une mesure fausse qui décide d'un placement.

L'annonce suit la même garde que le repli, et c'est le point : « si sans taille »
tout court parlait de taille à qui n'en a pas. La première ligne que voyait
quelqu'un qui refaisait une chanson était « la taille de ce tour n'avait pas été
conservée ». Une chanson, une vidéo, un objet 3D n'ont pas de résolution.

Ce repli se périme de lui-même, à mesure que les soixante tours d'une
conversation se renouvellent. Le jour où plus aucune conversation ne contient de
tour antérieur au 2 septembre 2026, il peut partir avec son repli de taille.

## Ce que le banc vérifie

`banc_refaire.py` éprouve la route qui relit tout cela, studio hors ligne, sans
carte et sans réseau — **75 vérifications** relevées le 2 septembre 2026 ; le
banc grossit, relance-le plutôt que de recopier ce nombre. Les preuves portent
sur le **graphe réellement soumis**, pas sur le tour qui le recopie : un tour
peut porter un champ que la carte n'a jamais reçu.

Voir [Éprouver les bancs](eprouver-les-bancs.md).
