# Retrouver ce qu'on a produit

Une sortie ne se retrouvait qu'en remontant la conversation qui l'avait
produite. Passé une vingtaine d'échanges c'est fastidieux ; passé trois
semaines, c'est perdu.

Le bouton **médiathèque**, dans la barre du haut, ouvre tout ce que vous avez
produit, rangé par famille — images, vidéos, musiques, objets 3D. Sous chaque
pièce : télécharger, voir en grand, et **reprendre**, qui la joint à la demande
suivante pour la retravailler.

La liste est lue dans vos **conversations**, jamais sur le disque : elles seules
savent à qui appartient un fichier et ce qui avait été demandé. Un balayage du
disque rendrait des noms sans histoire — et franchirait la frontière entre
utilisateurs, que le contrôle de propriété existe précisément pour tenir.

**Trier, filtrer, chercher.** Passé quelques semaines, une grille ne suffit
plus. On trie par date — dans les deux sens —, par moteur, par demande, **par
durée de rendu** ; on filtre par moteur, par machine, et par **brouillons /
images finies** ; et l'on cherche dans le texte : la demande écrite, **le prompt
envoyé** et le nom du fichier, les trois façons dont on se souvient d'une image
produite il y a trois semaines. Les sélecteurs ne proposent que ce qui existe,
et le compteur affiche « 12 sur 340 » dès qu'un filtre mord — pour qu'on
n'attribue jamais à une panne ce qu'un filtre oublié a produit.

**« Le plus long d'abord »** répond à « qu'est-ce qui coûte cher chez moi » —
c'est le seul tri qui le disait, et il n'existait pas.

**La taille et la durée sont sur chaque pièce.** « Pourquoi celle-ci a mis
quatre minutes ? » se répond neuf fois sur dix par la résolution, et la
médiathèque est justement l'endroit où l'on se pose cette question des jours
plus tard. La taille n'existait nulle part : elle ne vivait que dans le plan,
que le tour ne gardait pas. Le tour la porte désormais **à plat**, et ce n'est
pas une redite du plan qu'il garde depuis : c'est la clé de la table des durées,
et la médiathèque comme cette table sont deux lecteurs qui n'ouvrent jamais le
plan (voir [Ce que le tour garde du plan](ce-que-le-tour-garde.md)). La légende
l'affiche avec le temps de rendu à côté.

**Un bandeau « brouillon »** distingue les esquisses. Trente pièces plus tard,
« lesquelles sont finies ? » est la première question devant une médiathèque où
l'on a beaucoup essayé — et un brouillon garde la taille et le cadrage d'une
image finie : même prompt, même moteur, même taille, seul le soin change et cela
ne se voit pas. Voir [Le brouillon](brouillon.md).

**Les variantes portent leur rang** — « variante 2 sur 4 » — et la marque de
celle dont on repart. Quatre variantes ont le même prompt, le même moteur, la
même taille et la même minute : sans leur rang, la grille en montrait quatre
lignes rigoureusement indiscernables.

**Et le geste est là aussi.** Sous chaque variante non retenue, un bouton
**« repartir de celle-ci »** (`POST /api/variante`). Il n'existait que dans le
fil de la conversation, alors que **c'est ici qu'on compare** : le fil montre
les tirages l'un sous l'autre, la grille côte à côte, et quatre images
indiscernables ne se départagent qu'à l'œil — qui a besoin de les voir ensemble.
La médiathèque servait déjà l'identifiant du tour et celui du groupe ; la grille
les jetait. Un banc était vert sur ce contrat, que personne n'empruntait.

Deux défauts ont suivi le bouton, tous deux relevés après coup :

- **Il ne s'affichait sur aucun brouillon.** La condition écartait toute pièce
  portant une marque ; « retenue » étant déjà écartée par ailleurs, la seule
  marque restante était « brouillon ». Une variante rendue en brouillon
  n'obtenait donc jamais son bouton — le cas exact que sa propre recette lance,
  et la recette était verte parce qu'elle n'ouvre jamais la page.
- **Après le clic, la grille se repeignait depuis un cache périmé.** Rien ne
  changeait à l'écran : l'ancienne marque restait, le bouton revenait neuf, et
  l'on recliquait. On relit avant de repeindre — **et l'on garde la position de
  défilement**, parce que deux cents vignettes qu'on est en train de comparer ne
  doivent pas sauter en haut.

Voir [Une demande, plusieurs variantes](variantes.md).

**Le prompt envoyé est visible**, replié sous chaque légende. Ce que le moteur a
réellement reçu — après enrichissement et traduction — n'apparaissait nulle part
une fois la conversation refermée. C'est pourtant lui qui explique un rendu
qu'on ne s'explique pas.

**Un administrateur voit tout le studio**, chaque pièce nommée par son
propriétaire, avec un tri et un filtre de plus. La médiathèque l'annonce en
clair : regarder la production de tout le monde ne devrait jamais se faire sans
le savoir. Le nom du propriétaire n'est servi qu'à lui.

## Une médiathèque vide n'est jamais un silence

La grille garde en mémoire la liste qu'elle a lue. Deux chemins la
remplissaient d'un objet qui n'en était pas une, **après un geste qui avait
pourtant réussi** :

- une réponse qui n'est pas du JSON — le studio redémarré pendant le clic —
  faisait écrire « impossible » sur un geste qui avait marché, donc on
  recliquait ;
- un `401` « connexion requise » est un JSON **valide**, sans liste de
  fichiers : rien ne se déclenchait, le cache prenait cet objet, et la
  médiathèque **entière** affichait « rien de ce type pour l'instant », sans un
  mot. Le cache empoisonné survivait, la lecture n'étant refaite que si le
  cache est vide.

La lecture n'est désormais retenue que si elle a réussi **et** qu'elle porte
bien une liste. Quand elle échoue, la marque bougera au prochain chargement —
mais la médiathèque ne prétend jamais être vide.

Une conversation fermée en sort aussitôt, avec ses pièces : la médiathèque et le
service des fichiers lisent la même liste. Ils ont divergé un temps, et la
médiathèque affichait alors des vignettes que le studio refusait ensuite de
servir — image cassée, bouton mort, pour un fichier pourtant toujours là.
