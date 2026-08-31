# Le modèle qui écrit n'est pas celui qui aiguille

Aiguiller est une classification : un modèle de 7 B y suffit, et il doit savoir
lire une image. Écrire des paroles est un autre métier. Sur la même demande,
avec la même consigne :

| Modèle | Ce qu'il écrit |
|---|---|
| `qwen2.5vl:7b` | « Martin, menuisier avec talent / Aider son ami, sa single » |
| `gemma4:26b` | « L'odeur du cèdre et la poussière d'or, / Il taillait le bois pour son propre décor » |

Le prénom est changé : la demande d'origine était réelle, et c'était un hommage
à quelqu'un. Le reste des deux vers est ce que les modèles ont écrit.

Le studio choisit donc **tout seul** le plus gros modèle Ollama installé qui
tienne dans 60 % de la RAM, et ne s'en sert que pour écrire. Il le garde chargé
le temps du refrain **et** des couplets, puis le décharge explicitement — sinon
ComfyUI trouverait la carte déjà pleine.

`STUDIO_LLM_ECRITURE` impose un modèle précis et court-circuite ce choix.

> **Note historique.** Ce README a longtemps porté que `gemma4:26b` était
> inutilisable avec Ollama 0.33.1 (`Gemma4Assistant requires ctx_other to be
> set`). Sur la même version d'Ollama, le 28 août 2026, il charge en 14 s et
> génère à environ 58 jetons/s. Le téléchargement précédent était donc bien en
> cause, contrairement à ce qui avait été conclu.
