# Contenu adulte

Le studio ne filtre pas. L'aiguilleur a pour consigne de transcrire fidèlement la
demande, sans édulcorer. Pony reçoit automatiquement sa balise `rating_explicit`
quand c'est pertinent — sans elle il s'autocensure.

Une seule limite est codée en dur : le contenu sexuel impliquant des mineurs est
refusé, avant l'aiguillage et après la réécriture du prompt — **et sur le prompt
qui part vraiment au moteur**, enrichi et traduit, ainsi que sur la description
de zone qu'écrit le modèle pour une retouche. Ces deux textes-là, écrits par un
modèle de langage, partaient sans être relus jusqu'au 4 novembre 2026.

**En six langues** : français, anglais, et depuis le 4 novembre 2026 allemand,
espagnol, italien, portugais. Mesuré ce jour-là, avant le changement : sur dix-neuf
paires « mineur + sexuel » dans ces quatre langues, le garde-fou en refusait
**zéro** — il ne tenait que par le prompt traduit en anglais, et klein ou Qwen,
qui lisent la demande telle quelle, ne traduisent pas. Après : dix-neuf sur
dix-neuf, et aucun faux positif sur les demandes ordinaires du banc.

Deux mots sont laissés dehors exprès, parce qu'ils feraient refuser une demande
innocente dès qu'un enfant y figure : *nudo* (le nœud, en espagnol) et *teta* au
singulier (l'allaitement). Et un défaut est connu, affiché par le banc plutôt
que caché : *sexe*, *sexo*, *sesso* disent aussi le **genre** — « révéler le
sexe du bébé » est refusé. Le garde-fou ne retire pas ces mots : « montre le
sexe du bébé » porte les mêmes, et aucun motif ne sépare les deux sens. Mais
quand le refus ne tient **qu'à** l'un d'eux, il dit comment reformuler : « si tu
parlais du genre, écris *fille ou garçon* ». Et le refus se lit désormais dans
la langue de la page, au lieu de partir en français.

Une demande venue d'un programme ([Piloter le studio par
programme](piloter-par-programme.md)) suit exactement les mêmes règles, et le
garde-fou y est passé **avant la file** : le programme reçoit un refus `422`
(`refus_mineurs`) au lieu d'un rendu en erreur découvert plus tard, et rien
n'est compté dans le plafond de sa clé.

Une règle s'ajoute dès qu'une clé d'API est posée : **une demande adulte ne sort
jamais de la machine**, ni vers un LLM distant, ni vers un générateur d'images
distant. Elle est appliquée dans le code, avant l'appel, et le journal de la
tâche l'annonce. Elle lit les mêmes six langues : avant le 4 novembre 2026, cinq
demandes adultes sur vingt et une en allemand, espagnol, italien ou portugais
étaient reconnues — les autres pouvaient partir au nuage.

**L'image jointe aussi, depuis le 4 novembre 2026.** Avant de partir chez un
fournisseur distant, elle est montrée au **modèle de vision local**, une seule
question — nudité, contenu sexuel ou érotique — et une réponse en booléen :

- **adulte**, ou **une réponse illisible** : l'image reste à la maison, la
  retouche est faite sur une carte d'ici. Un modèle qui a répondu à côté ne doit
  pas laisser sortir une image dont personne n'a su dire si elle était adulte ;
- **saine** : elle part, comme avant ;
- **aucun modèle de vision joignable** — un studio sans carte, tout au nuage :
  elle part aussi, mais le fil de la demande le dit (« image jointe non
  inspectée »). Refuser là casserait toute retouche distante d'un studio qui n'a
  que le nuage.

L'image ne quitte pas la machine pour être jugée : avec une image, l'appel au
modèle de langage reste toujours local. Le jugement coûte quelques secondes,
seulement quand une image s'apprête à partir, et une fois par image. Une clé
d'accès sans droit au nuage, elle, n'y va jamais.
