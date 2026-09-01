# Quand une machine tombe

Un ComfyUI qui s'arrête en cours de calcul rendait « échec de la génération »,
et la demande était perdue. C'est la mauvaise réponse : la demande était bonne,
c'est la machine qui a lâché. Le studio reprend donc de lui-même — sur une
autre machine capable du même moteur, ou sur la même dès qu'elle revient — et
**n'échoue qu'après trente minutes sans aucune machine**.

Ce qui a demandé le plus de soin n'est pas la boucle, c'est de séparer deux
sortes d'échec :

| | |
|---|---|
| **Panne** | machine injoignable, ComfyUI arrêté, mémoire saturée. Réessayer a un sens. |
| **Faute** | nœud inconnu, modèle absent, paramètre refusé. Réessayer ne changera rien, et ferait tourner la demande une demi-heure avant de rendre la même erreur. |

En cas de doute, le studio répond « panne » : une reprise inutile coûte
quelques minutes, un abandon injustifié coûte le travail. Mais un échec qu'on
ne sait pas classer ne vaut qu'**une** reprise — au second, c'est une vraie
faute.

Deux détails qui comptent :

- **Les fichiers d'entrée suivent.** Ils vivent dans l'`input` de la machine
  qui calcule ; changer de machine oblige à les y renvoyer et à corriger le
  graphe, sinon la nouvelle cherche un fichier qui n'existe que chez l'ancienne.
- **Sur la machine hôte, le studio relance ComfyUI lui-même.** C'est la panne
  la plus fréquente et la plus facile à réparer, et personne ne regarde l'écran
  à trois heures du matin.

Vérifié le 29 août 2026 sur **pc**, en tuant ComfyUI en plein calcul : reprise
annoncée, ComfyUI relancé, image produite 80 secondes plus tard sans
intervention.

Les trente minutes sont la `patience` de `soumettre_robuste()` dans
`serveur.py` : 1800 secondes, écrites en dur. **Ce n'est pas
`STUDIO_ATTENTE_CARTE`**, qui vaut la même chose mais borne l'attente d'une
carte *occupée* — voir [Réglages](reglages.md).
