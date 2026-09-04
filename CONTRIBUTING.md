# Contribuer à ComfyStudio

Merci de passer par ici. Ce document dit comment lancer le studio pour
travailler dessus, quelles conventions suivre, et surtout **ce qui distingue
une contribution qu'on peut accepter d'une qu'on ne peut pas** : une mesure.

Le projet est en français — le code est commenté en français, l'interface est en
français, ce fichier l'est aussi. C'est délibéré. Les contributions suivent la
même règle.

## Lancer le studio pour développer

Le studio ne calcule rien lui-même : il pilote un ComfyUI et, si tu en as un, un
Ollama. Il démarre donc sans eux — l'interface s'ouvre, l'aiguillage par
classifieur fonctionne, seule la génération manque.

**Une seule dépendance obligatoire : `aiohttp`.**

```bash
pip install aiohttp
python serveur.py
```

Puis <http://127.0.0.1:8199>.

`huggingface_hub` et `av` (PyAV) sont utilisés s'ils sont présents et ignorés
sinon : le téléchargement des modèles retombe sur du HTTPS direct, et la lecture
de cadence vidéo est simplement indisponible. N'en fais pas des dépendances.

Sur Windows, `LANCER ComfyStudio.bat` fait la même chose avec le Python embarqué
de ComfyUI — pratique pour reproduire l'environnement d'un utilisateur, qui n'a
souvent aucun Python installé par ailleurs.

Les réglages passent par des variables d'environnement, jamais par un fichier de
configuration à éditer :

```bash
STUDIO_PORT=8199          # port d'écoute
STUDIO_HOTE=127.0.0.1     # 0.0.0.0 pour ouvrir au réseau local
STUDIO_AUTH=obligatoire   # « libre » pour développer sans se connecter
COMFY_URL=http://127.0.0.1:8188
OLLAMA_URL=http://localhost:11434
```

`.env.exemple` les liste toutes. Au premier démarrage sans compte, le studio en
crée un (`admin`) et affiche son mot de passe **une seule fois** dans la
console : note-le, il n'est pas conservé en clair.

Les données de travail vivent dans `conversations/` — conversations, clés d'API,
jeton d'administration, registre des comptes. **Ce dossier est exclu du dépôt**,
et il doit le rester : il contient les demandes de l'utilisateur et ses secrets.
Regarde `.gitignore` avant d'ajouter quoi que ce soit.

## Convention de style

### Les identifiants sont en français

`aiguiller`, `moissonner`, `empreinte`, `noeud_du_jeton`, `CLES`, `BANCS`. Un
code moitié français moitié anglais oblige à deviner, à chaque nom, dans quelle
langue il a été pensé. Le seul anglais toléré est celui qui vient d'ailleurs :
les noms de nœuds ComfyUI, les clés d'API HTTP, `aiohttp`.

### Pas d'accents dans le code Python

Les identifiants et les commentaires s'écrivent sans accents :

```python
# Le mot de passe n'est jamais conserve, seulement une empreinte scrypt.
```

Ce n'est pas une coquetterie : ces fichiers voyagent entre une console Windows
en cp1252, un Python embarqué et un conteneur Linux, et un accent mal décodé
transforme un message d'erreur utile en charabia. Les neuf modules sur dix sont
en ASCII pur.

**L'exception, c'est la donnée.** Les accents restent partout où ils sont le
sujet et non le commentaire : les expressions régulières qui reconnaissent une
demande française (`vid[ée]o|clip|anim`), les prompts envoyés aux modèles, les
textes affichés à l'utilisateur. Là, les enlever changerait le comportement.

Ce fichier-ci, le README, les gabarits d'issue sont du Markdown : ils gardent
leurs accents.

### Les commentaires disent POURQUOI, jamais QUOI

Un commentaire qui paraphrase la ligne suivante ne sert à rien — la ligne est
déjà là. Ce qu'on ne peut pas relire dans le code, c'est la raison.

```python
# Non :
# On compare avec compare_digest.
if hmac.compare_digest(signature, attendu):

# Oui :
# compare_digest : une comparaison qui s'arrete au premier octet different
# laisse mesurer combien de tete est juste.
if hmac.compare_digest(signature, attendu):
```

### Quand il y a une mesure, elle est dans le commentaire

C'est la convention la plus importante du projet. Une décision prise après essai
porte le chiffre qui l'a décidée, à l'endroit où quelqu'un voudra la remettre en
cause :

```python
# Les demandes reelles sont rares et precieuses : on les compte plusieurs fois,
# sinon trois mille exemples fabriques les noieraient. Mais on plafonne leur
# apport par classe — mesure : sans plafond, dix-sept demandes reelles dont
# onze images faisaient pencher tout le classifieur vers « image », et la
# justesse sur les tournures indirectes tombait de 86 a 84 %.
POIDS_REEL = 8
PART_REELLE = 0.10
```

Sans le chiffre, le prochain lecteur — toi dans six mois — enlève le plafond
« pour simplifier » et personne ne voit rien pendant des semaines.

Une constante numérique sans justification est un défaut : `0.15` pour la
température, `45` secondes de silence avant de déclarer un nœud perdu, `2**14`
pour scrypt — chacune dit d'où elle vient.

### Une tâche par appel au modèle de langage

C'est la leçon structurante du projet, et elle vaut comme règle de conception :
quand le même appel devait aiguiller, enrichir, traduire et rendre du JSON, la
traduction lâchait la première. Isolée, elle est correcte. Un nouvel appel qui
fait deux choses sera refusé.

Corollaire : **ce qui peut être vérifié en Python l'est en Python**, pas demandé
au modèle. La normalisation qui suit l'aiguillage — plafonner une résolution,
corriger une intention incohérente, exiger que le sujet extrait figure vraiment
dans la demande — est du code, parce qu'un modèle de 7 milliards de paramètres
n'est pas docile et qu'on ne peut pas le tester.

## Réentraîner l'aiguilleur, et lire ses mesures

L'aiguilleur est un Bayes naïf multinomial, sans aucune dépendance
(`aiguilleur.py`), entraîné hors ligne et livré dans `aiguilleur.json`.
**Ce fichier est le produit d'un entraînement : ne l'édite jamais à la main.**

Dès que tu touches au corpus (`corpus_aiguillage.py` et les `corpus_*.jsonl`) ou
au classifieur lui-même :

```bash
python entrainer_aiguilleur.py
```

Trois centièmes de seconde, aucune dépendance, aucun réseau. Sortie actuelle :

```
  2899 exemples, 11 classes
  entraine en 0.03 s — 7680 traits
  ecrit : aiguilleur.json (0.19 Mo)

  banc_aiguillage.jsonl
     62/66 justes (94 %), 0.031 ms par demande
     tranches d'office : 62/64 (97 %) — 2 renvoyes au modele de langage

  banc_neuf.jsonl
     43/49 justes (88 %), 0.053 ms par demande
     tranches d'office : 42/46 (91 %) — 3 renvoyes au modele de langage
```

Relevé le 1er septembre 2026. Ces chiffres-là sont ceux de la CI, qui n'a pas
de `conversations/` : pour les reproduire, lance l'entraînement avec un
`STUDIO_DONNEES` vide, sinon `moissonner()` ajoute tes demandes réelles au
corpus et tu mesures autre chose. Le banc dur est passé de 44 à 49 cas le
31 août, et cette page ne l'avait pas suivi pendant deux jours.

Comment lire ça :

- **`banc_aiguillage.jsonl` et `banc_neuf.jsonl` ne sont jamais appris.** Ils
  sont écrits à part, et `banc_neuf` rassemble des tournures indirectes où le
  verbe manque (« il me faudrait la sortir de son décor »). C'est le banc dur ;
  c'est celui qui bouge quand on casse quelque chose.
- **« justes » mesure le classifieur. « tranchés d'office » mesure ce qu'on lui
  laisse décider seul** — au-dessous de `MARGE_SURE`, la demande part au modèle
  de langage. C'est le second chiffre qui compte pour l'utilisateur : une erreur
  sur un cas tranché est une erreur visible, un cas renvoyé ne coûte que du
  temps.
- **Un chiffre qui monte sur un banc et descend sur l'autre n'est pas une
  amélioration.** Les deux se lisent ensemble.

Si tu ajoutes des exemples, écris-les **avec ton vocabulaire à toi, pas le
mien** : entraîné sur mes seuls gabarits, l'aiguilleur atteignait 100 % sur mes
propres phrases et 74 % sur celles écrites par quelqu'un d'autre. Un jeu de test
écrit par soi-même ne vaut rien.

Le corpus du dépôt ne contient **que** des exemples fabriqués. Les demandes
réelles passées par le studio sont récoltées localement, depuis `conversations/`,
et ne partent jamais dans le dépôt : ce sont celles de l'utilisateur.

L'intégration continue (`.github/workflows/verification.yml`) rejoue cet
entraînement à chaque poussée et échoue si la justesse tombe sous les seuils.
Une contribution qui abaisse la justesse doit dire pourquoi c'est un bon
échange.

## Ce qu'on attend d'une contribution

**Une mesure plutôt qu'une opinion.** C'est la seule exigence vraiment ferme.

« Ce modèle est meilleur », « ce serait plus propre », « ce serait plus rapide »
ne se discutent pas : on ne sait pas comment vous répondre. Le même propos avec
un chiffre se discute tout de suite, et se tranche.

Le projet entier est bâti là-dessus. `digitsflow/bonsai-8b` n'a pas été écarté
parce qu'il déplaisait, mais parce qu'il remplace le sujet français de façon
reproductible — *hibou* → *hippopotamus* aux trois tirages. La température est à
0,15 et non 0,4 parce qu'à 0,4 la même demande partait tantôt en question,
tantôt en image. Le classifieur a remplacé le modèle de langage sur trois
intentions parce qu'il fait 0,05 ms contre 700 ms, sans perte de justesse.

Concrètement, dans ta pull request :

1. **Dis ce que tu as mesuré, comment, et sur quoi.** Le banc, le nombre de cas,
   la machine s'il s'agit d'un temps. « Vérifié en tuant ComfyUI en plein
   calcul » vaut mieux qu'un long paragraphe.
2. **Donne l'avant et l'après.** Un chiffre seul ne dit rien.
3. **Mets la mesure dans le code**, en commentaire, à l'endroit de la décision —
   pas seulement dans la discussion de la PR, que personne ne relira.
4. **Une seule idée par PR.** Un correctif et un refactor mêlés ne peuvent plus
   être annulés séparément.
5. **Fais tourner la vérification avant de proposer** :
   `python -m compileall -q .` et `python entrainer_aiguilleur.py`. **Tous les
   `banc_*.py` du dépôt**, plus `verifier_formulations.py`, tournent tout seuls,
   sans réseau ni studio, et la CI les lance tous.

   *Cette phrase nommait les bancs un par un jusqu'au 3 septembre 2026, et la
   liste a rouillé deux fois — elle en annonçait treize quand le dépôt en
   comptait dix-sept, et n'y trouvait ni le second facteur, ni les traductions,
   ni le QR code. Une énumération que rien ne vérifie ne survit pas au dépôt
   qu'elle décrit : on nomme donc le motif, qui ne peut pas se démoder.*

   **Un dernier les éprouve.** `banc_mutations.py` mute le code et exige que le
   banc visé rougisse, sur la ligne nommée et pas une autre. Il existe parce
   que trois fois en une semaine un banc vert a couvert une fonctionnalité
   morte — dont un banc écrit exprès pour le défaut qu'il ne voyait pas. Si tu
   ajoutes un banc, ajoute-lui sa mutation : un filet qu'on n'a jamais vu
   rougir ne mesure rien.

   Et **éprouve-la dans les deux sens** : elle doit rougir sur le dépôt
   d'aujourd'hui, et passer au vert quand on défait la correction qu'elle
   garde. Une mutation qui reste rouge dans les deux cas mesure autre chose que
   ce qu'elle nomme — c'est arrivé trois fois, dont une où elle était datée du
   mauvais commit et se serait déclarée prouvée contre un filet qui la voyait
   déjà. Quand le banc est né avec la correction, il n'y a pas de filet
   d'avant : lance le banc NEUF sur le code d'AVANT et vérifie que les lignes
   que ta mutation nomme y rougissent. Écris-le quand tu ne peux ni l'un ni
   l'autre.
6. **Si tu touches à l'interface, lance la recette.** `recette_chemin_page.py`
   a besoin d'un studio qui tourne, et c'est pour cela qu'elle n'est pas dans
   la CI : elle refait les gestes de la page dans l'ordre réel, appel par
   appel. Elle existe parce que sept bancs sont restés verts pendant que les
   réglages par conversation étaient entièrement morts — aucun n'empruntait le
   chemin du navigateur, ils appelaient tous une route que la page n'utilise
   plus. Un banc qui teste un contrat que personne n'emprunte ne mesure rien.

   Il y en a trois, toutes lancées de la même façon :

   ```bash
   sudo docker exec comfystudio python /app/recette_chemin_page.py
   ```

   `recette_grille_variantes.py` pour les variantes,
   `recette_facteur_admin.py` pour le retrait du second facteur — celle-là
   parce que ce que `banc_comptes.py` sait de `serveur.py`, il le sait par
   l'arbre de syntaxe : il peut voir qu'une garde est écrite avant le retrait,
   pas qu'une requête refusée laisse vraiment le facteur en place.

Ce qui est accueilli sans mesure : les corrections de fautes, la documentation,
un rapport de bogue clair, un cas de test qui échoue.

Ce qui ne l'est pas : l'anglicisation du code ou de l'interface, l'ajout d'une
dépendance qui n'est pas indispensable (le studio doit démarrer sur un NAS sans
`pip`), et la suppression d'un garde-fou parce qu'il paraît superflu — ils sont
tous là parce que quelque chose a échoué.

## Signaler un problème

Un bogue : `.github/ISSUE_TEMPLATE/bogue.md`. Une idée :
`.github/ISSUE_TEMPLATE/idee.md`. Une faille de sécurité : **pas d'issue
publique**, lis [SECURITY.md](SECURITY.md).

## Licence

ComfyStudio est sous **AGPL-3.0** (voir [LICENSE](LICENSE)). En contribuant, tu
acceptes que ton apport soit distribué sous cette licence.

Ce que l'AGPL impose, et qu'il vaut mieux savoir avant de commencer :

- Toute version modifiée que tu **redistribues** doit rester sous AGPL-3.0, avec
  son code source complet.
- **Et l'héberger suffit.** C'est l'article 13, la différence avec la GPL
  ordinaire : si tu fais tourner une version modifiée du studio et que d'autres
  s'en servent à travers le réseau — un service en ligne, un studio ouvert au
  LAN d'une entreprise, une offre payante — tu dois proposer à ces
  utilisateurs-là le code source de ta version. Ne rien distribuer de fichier
  n'y change rien.

Personne ne peut donc en faire un produit fermé, et c'est exactement le but.
