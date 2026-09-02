# Les mesures du multilingue

Ce dossier porte le **banc d'aiguillage traduit à la main** en anglais, allemand
et espagnol — 460 cas, même registre que l'original — et les cinq scripts qui
ont mesuré ce qu'une demande étrangère devient aujourd'hui.

Il est ici parce qu'il a failli disparaître : il a été écrit dans un dossier de
session, et la page [Plusieurs langues](../docs/plusieurs-langues.md) ne vaut
rien sans lui. **Toute décision de cette page se refait depuis ces scripts.**

```bash
python mesurer.py              # ce que le classifieur fait de chaque langue
python mesurer_chemin.py       # par où passe une demande : raccourci, court-circuit, modèle
python mesurer_detection.py    # reconnaître une langue étrangère, et à quel prix
python mesurer_garde.py        # la garde de couverture : pannes, appels, secondes
python mesurer_apprentissage.py  # ce que la moisson fait d'une demande étrangère
```

Aucun réseau, aucune carte, aucun studio : le classifieur tourne hors ligne.

**Ce ne sont pas des bancs.** Ils ne gardent rien et n'entrent pas dans la CI :
ils mesurent un état de fait, à une date. Le banc qui gardera le multilingue
reste à écrire — c'est le premier des sept travaux de la page.

**Et leur limite est écrite dans la page :** les 460 cas ont été traduits par
une seule personne, ce que `CONTRIBUTING.md` dénonce précisément (100 % de
justesse sur ses propres phrases, 74 % sur celles d'un tiers). Les valeurs
absolues sont donc à prendre avec réserve ; les **écarts** entre langues et
entre politiques, mesurés sur le même jeu, le sont beaucoup moins.
