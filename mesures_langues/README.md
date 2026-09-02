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
ils mesurent un état de fait, à une date. Le banc, lui, existe depuis le
2 septembre 2026 au soir : [`banc_multilingue.py`](../banc_multilingue.py), à
la racine, qui rejoue ces mêmes 460 cas **par le vrai chemin** — il appelle
`aiguiller()` et compte les appels au modèle, au lieu de rejouer la séquence à
la main comme le font les scripts d'ici. C'est lui que la CI lance, et trois
mutations de `banc_mutations.py` l'éprouvent.

Ces scripts restent parce qu'ils répondent à des questions que le banc ne pose
pas : quel seuil, quel moyen de détection, quelle pondération. Ils ont servi à
**décider**, il sert à **garder**.

> Une différence de chiffres entre les deux est normale et attendue : ces
> scripts rejouent la séquence à la main, le banc emprunte `aiguiller()` en
> entier. Le banc trouve 26 pannes sans la garde et 1 avec — les mêmes que
> `mesurer_garde.py`, parce que tous deux épinglent le modèle **publié**.
> `mesurer_detection.py` charge `aiguilleur.json` directement, ce qui revient
> au même ; si vous le modifiez pour passer par `charger()`, vous mesurerez le
> modèle local de votre machine et les chiffres bougeront.

**Et leur limite est écrite dans la page :** les 460 cas ont été traduits par
une seule personne, ce que `CONTRIBUTING.md` dénonce précisément (100 % de
justesse sur ses propres phrases, 74 % sur celles d'un tiers). Les valeurs
absolues sont donc à prendre avec réserve ; les **écarts** entre langues et
entre politiques, mesurés sur le même jeu, le sont beaucoup moins.
