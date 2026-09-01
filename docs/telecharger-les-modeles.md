# Télécharger les modèles

Le studio récupère lui-même les modèles manquants, en **HTTPS direct** — sans
`huggingface_hub`, qui n'est pas installable partout (un NAS sans `pip`, une
racine en lecture seule) et rendait alors le studio incapable de terminer une
installation.

Trois choses que l'ancienne version ne faisait pas :

- **Il dit où il en est.** klein 9B pèse **14,8 Go** — le chiffre se relit dans
  `catalogue.py`, qui compte l'union des fichiers réellement manquants, et il
  bouge quand le catalogue bouge : ne le recopie pas, lis-le. On voyait
  « téléchargement de… » puis plus rien pendant vingt minutes. Le journal
  annonce maintenant le pourcentage, le débit et le temps restant, tous les
  10 % et au moins toutes les 30 s.
- **Il reprend.** Une coupure à 90 % faisait tout recommencer. L'écriture se
  fait dans un `.part` et la suite est redemandée par un en-tête `Range` —
  vérifié en tronquant volontairement un fichier à 40 %.
- **Il vérifie la taille reçue.** Un fichier tronqué n'est pas refusé à
  l'ouverture : il échoue plus tard, avec un message qui ne parle pas de
  téléchargement, et on cherche ailleurs.

Un dépôt privé, renommé ou inexistant (401/403/404) échoue **immédiatement** :
réessayer trois fois ne ferait que retarder le message.
