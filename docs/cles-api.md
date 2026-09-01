# Clés d'API : LLM et images

Tout fonctionne en local sans aucune clé. Une clé n'est qu'une option, posée
depuis `/admin`, et le local reste le **repli de tout** : si le fournisseur
refuse, tarde ou ne connaît pas le modèle demandé, le studio continue sur la
machine et écrit dans le journal de la tâche le message d'erreur du fournisseur,
tel quel — « clé refusée » et « modèle inconnu » ne se corrigent pas pareil.

| Usage | Fournisseurs |
|---|---|
| Texte (aiguillage, paroles, traduction) | Anthropic, OpenAI, Mistral, Google, Mammouth |
| Images | Nano Banana (Gemini Image) |
| Musique | Lyria 3 (Google) |
| Vidéo | Veo 3.1 (Google) |
| Objets 3D | Meshy |

Mammouth est un agrégateur : une seule clé pour GPT, Claude, Gemini et d'autres,
en dialecte OpenAI. Texte seulement — ni image, ni son, ni vidéo.

On choisit indépendamment pour le texte et pour l'image : les deux, l'un, ou
aucun. Nano Banana accepte la clé Google déjà posée, il n'y a pas à la saisir
deux fois.

Le **nom du modèle est un réglage**, pas une constante : les catalogues des
fournisseurs changent plus vite que ce logiciel. Chaque ligne du tableau
d'administration a son champ ; vide, le défaut s'applique.

Ce qui ne part jamais :

- **Le contenu adulte.** Vérifié en code avant tout appel sortant. Aucun réglage
  d'interface ne peut lever la règle, et le journal de la tâche le dit :
  « contenu adulte : la génération reste sur cette machine ».
- **La lecture d'image.** Elle utilise un modèle de vision local — le plus gros
  qui sache voir sur la machine retenue, voir [Plusieurs
  Ollama](plusieurs-ollama.md).
- **La clé elle-même.** L'API d'administration ne la renvoie jamais, seulement
  ses quatre derniers caractères. Le fichier `conversations/_cles.json` est
  exclu du dépôt.

Quand une destination distante est active, l'en-tête de l'interface l'affiche —
« texte → Anthropic (Claude) ». Rien ne s'affiche tant que tout est local.

## Le nuage dans la barre du haut

Une icône par modalité, **visible seulement si une clé la rend joignable** :
☁ texte, 🖼 images, ♪ musique, 🎞 vidéo, ▣ objets 3D. Allumée, la demande part
chez le fournisseur ; éteinte, elle reste sur la machine.

L'interrupteur est **propre à chaque navigateur**, et c'est délibéré : il est en
façade, sans jeton, alors que le réglage de `/admin` est protégé. Global, il
laisserait n'importe quel visiteur du réseau dépenser les crédits du
propriétaire d'un seul clic. Le réglage de `/admin` donne sa position par
défaut ; chacun l'inverse pour ses propres demandes.

## Choisir le cloud demande par demande

Un réglage global ne suffit pas : on veut souvent l'inverse — cette image-ci
chez Nano Banana parce qu'elle presse, la suivante en local parce qu'on a le
temps. Les moteurs distants apparaissent donc **dans la liste des moteurs**, à
côté des locaux, et se choisissent comme eux. Ils n'apparaissent que si une clé
les rend joignables.

| Moteur | Modalité | Repli local |
|---|---|---|
| Nano Banana (Gemini) | image | FLUX.2 klein 4B |
| Lyria 3 (Google) | musique | ACE-Step 1.5 SFT |
| Veo 3.1 (Google) | vidéo | Wan 2.2 5B |
| Meshy | objets 3D | Hunyuan3D 2 |

Meshy part d'une **image** et non d'un texte. Sans image fournie, il rend la
main : la voie locale, elle, sait dessiner d'abord une vue de référence puis la
sculpter.

Un moteur distant n'entre pas au catalogue — celui-ci décrit des fichiers à
télécharger et sert aussi à l'installeur. Il se contente de détourner la
**production** : l'aiguillage, la traduction et l'écriture des paroles se font
comme d'habitude, si bien qu'un échec distant retombe sur le moteur local de
repli sans que rien d'autre ne change. Le journal dit toujours lequel a servi.

Forcer un moteur distant **ne lève pas** la règle sur le contenu adulte : la
demande reste alors sur la machine, et le studio l'annonce.

Mesuré le 28 août 2026, depuis le studio et donc sans aucune carte : Nano
Banana 8 s pour une image, Lyria 3 25 s pour un clip de 30 s, paroles
comprises. Ces deux durées-là ne dépendent pas du parc, mais de la charge du
fournisseur ce jour-là.

## Ce que tout cela consomme

Chaque appel distant **abouti** est consigné — quand, quel fournisseur, quelle
modalité, quel compte, les jetons quand l'API les rend, les octets, la durée.
`/admin` en donne la vue par compte et par fournisseur sur deux mois, et un
**plafond mensuel** ramène un compte au local au-delà d'un nombre d'appels.
Aucun euro nulle part : voir [Ce que le nuage a coûté](cout-du-nuage.md).
