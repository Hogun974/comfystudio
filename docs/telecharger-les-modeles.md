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

## Ce que le poids annoncé promet

Un seul endroit met un poids en phrase : `annonce_poids()` dans `catalogue.py`.
C'est ce qui a manqué la première fois — une correction précédente n'avait touché
que les lignes **par moteur**, et les deux **totaux** de l'installeur, dont celui
qui précède l'écriture sur le disque, annonçaient toujours « environ 0 Go ». Le
défaut se relisait mot pour mot une ligne avant le téléchargement.

Quatre formulations, parce qu'il y a quatre situations :

- **`~14,8 Go`** — toutes les tailles sont relevées. C'est le cas ordinaire.
- **`au moins N Go`** — un fichier au moins n'a pas de taille au catalogue. Un
  plancher, annoncé comme un plancher.
- **`taille inconnue`** — tout ce qui manque est justement ce qu'on ne sait pas
  mesurer. « Au moins 0 Go » n'annonce rien.
- **`à installer à la main`** — le moteur n'a aucune source automatique. Les
  quatre fichiers d'ACE-Step n'ont pas de dépôt : le moteur audio annonçait
  « ~0 Go à prendre », qui se lit « c'est gratuit », pour un moteur qui ne
  marchera pas après installation.

**Sous le demi-gigaoctet, on passe aux mégaoctets.** `detourer` pèse 0,44 Go
relevé et `agrandir` 0,07 ; tous deux s'affichaient « ~0 Go ». L'annonce ne passe
donc pas par l'arrondi au dixième de gigaoctet, où 0,44 devenait 0,4 — soit
« 400 Mo » au lieu de 440.

`banc_catalogue.py` tient cette règle, et il vérifie aussi qu'**aucun autre
fichier ne formate un poids à la main**. Le seul aveu encore ouvert est nommé
dans le banc, avec sa raison ; il rougit dès que cet aveu devient périmé.
