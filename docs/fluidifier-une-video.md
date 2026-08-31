# Fluidifier une vidéo, ou la passer au ralenti

« rends-la plus fluide », « mets-la en 60 fps », « passe-la au ralenti ». Le
modèle FILM intercale des images calculées entre celles qui existent.

**C'est le même calcul dans les deux cas** — seule la cadence de sortie les
sépare : doublée, la vidéo garde sa durée et gagne en fluidité ; conservée,
elle dure deux fois plus longtemps et devient un ralenti propre.

Mesuré de bout en bout : 121 images à 24 im/s → 241 à 48 im/s, même durée de
5 s, **60 secondes** de calcul, pour un modèle de 69 Mo.

La cadence de la source est lue avec PyAV, déjà livré avec ComfyUI. Le nœud de
calcul officiel qui la multiplierait dans le graphe attend un type d'entrée
dynamique malcommode à construire par l'API : la lire côté studio et passer un
nombre revient au même, en plus simple.

Le studio retient la dernière **vidéo** séparément de la dernière **image** :
« agrandis-la » vise l'image, « rends-la fluide » vise la vidéo.
