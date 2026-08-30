# ComfyStudio en un seul .exe — notes de paquetage

Tout ce qui suit a été **mesuré sur cette machine** (Windows 11 Pro 26200,
Python 3.13.14 embarqué de ComfyUI, PyInstaller 6.22.2), pas supposé.

## Résumé

| | |
|---|---|
| Interpréteur retenu | `D:\ComfyUI_windows_portable\python_embeded\python.exe` (3.13.14) |
| PyInstaller | 6.22.2, installé par `pip` **sans problème** dans le Python embarqué |
| Taille de l'exe | **~44 818 700 octets** (42,7 Mio) — varie de quelques centaines d'octets d'une construction a l'autre |
| Taille sans PyAV (`PAQUET_SANS_AV=1`) | **17 517 471 octets** (16,7 Mio) |
| Durée de construction | ~40 s à froid, ~25 s ensuite |
| Démarrage à froid de l'exe | **1,5 s** entre le lancement et la première réponse HTTP |
| Test de démarrage | `GET /api/compte` → **HTTP 200** |
| Persistance des données | **corrigée et vérifiée** (voir plus bas) |

Construire : `paquet\construire_windows.bat`. Résultat dans `paquet\dist\ComfyStudio.exe`.

## Le Python embarqué suffit

Contrairement à ce qu'on pouvait craindre, `python_embeded` a bien `pip`
(26.2.1) et `pip install pyinstaller` fonctionne sans rien contourner :

```
Successfully installed altgraph-0.17.5 pefile-2024.8.26
pyinstaller-6.22.2 pyinstaller-hooks-contrib-2026.7 pywin32-ctypes-0.2.3
```

Aucun autre Python n'a été nécessaire. C'est d'ailleurs **le bon choix** : c'est
l'interpréteur qui fait tourner le studio au quotidien, donc la version
d'aiohttp gelée dans l'exe est exactement celle qui est testée en usage réel.
Le seul avertissement de `pip` est cosmétique (`Scripts\` hors du `PATH`) ; on
appelle PyInstaller par `python.exe -m PyInstaller`, ce qui l'évite.

## La correction `ICI_DATA` — appliquée et vérifiée

### Ce qu'était le problème

Gelé en un seul fichier, PyInstaller extrait le paquet dans un dossier
temporaire jetable et y pose `__file__`. `ICI` (`serveur.py` ligne 27) valait
donc `...\Temp\_MEIxxxxxx`, **effacé à l'arrêt du programme**. Or `ICI` servait
à deux choses incompatibles : lire des ressources embarquées (correct) et
choisir où écrire les données de l'utilisateur (destructeur).

Mesuré sur le build d'avant correction, deux lancements successifs :

```
lancement 1:   Mot de passe : <mot-de-passe-lancement-1>
lancement 2:   Mot de passe : <mot-de-passe-lancement-2>
```

Un compte administrateur neuf à chaque démarrage : conversations, comptes,
nœuds et avis perdus entre deux lancements, **en silence**.

### Ce qui a été fait

`serveur.py` distingue désormais les deux notions, juste après `ICI` :

```python
ICI_DATA   = (os.path.dirname(os.path.abspath(sys.executable))
              if getattr(sys, "frozen", False) else ICI)
```

`ICI_DATA` remplace `ICI` aux **cinq** endroits qui écrivent — `BASE_COMFY`
(63), `DOSSIER_CONV` (95), `FICHIER_NOEUDS` (116), `FICHIER_AVIS` (3273),
`SORTIES_AGENT` (4759). `ICI` reste inchangé partout où l'on **lit** depuis le
paquet : `web/index.html` (4246), `web/admin.html` (5083), les scripts servis
aux nœuds (5104) et `aiguilleur.py` ligne 36. Hors gel, les deux valent la même
chose et rien ne change pour un lancement Python normal.

### Vérification

Exe reconstruit, lancé **sans `STUDIO_DONNEES`**, depuis `paquet\dist\`,
sur `STUDIO_PORT=8299`, arrêté, puis relancé à l'identique.

**Où atterrissent les données** — `paquet\dist\` ne contenait que
`ComfyStudio.exe` avant le test ; après le premier arrêt :

```
paquet\dist\conversations\_admin.json     (45 octets)
paquet\dist\conversations\_comptes.json  (194 octets)
```

À côté de l'exe, plus dans le temporaire.

**Le compte admin est-il le même aux deux lancements — oui :**

| | lancement 1 | lancement 2 |
|---|---|---|
| « Compte administrateur cree » | 1 fois | **0 fois** |
| Mot de passe affiché | `hKuoNfYVcpPXctQO` | **aucun** |
| `Comptes   :` | 1 (1 administrateur(s)) | 1 (1 administrateur(s)) |

Empreinte SHA-256 de `_comptes.json`, avant et après le second lancement :
`b52e7bc0dc48598c2923548632c36ac9` dans les deux cas — fichier inchangé, le
compte `admin` est bien relu et non recréé. À comparer aux deux mots de passe
différents du build d'avant correction. **La correction tient.**

**Le chemin des modèles n'est plus dans le temporaire :**

```
avant : C:\Users\Hogun974\AppData\Local\Temp\ComfyUI_windows_portable\ComfyUI\models
apres : D:\ComfyStudio\paquet\ComfyUI_windows_portable\ComfyUI\models
```

Il suit maintenant l'emplacement de l'exe, comme voulu. Attention à la
conséquence pratique : **l'exe doit être posé dans `D:\ComfyStudio\`** pour que
`ICI_DATA\..` retombe sur le voisin `ComfyUI_windows_portable`. Laissé dans
`paquet\dist\`, il cherche ComfyUI dans `paquet\` et ne le trouve pas — c'est ce
que montre la mesure ci-dessus, faite depuis `dist\`. Le studio démarre quand
même et pilote par HTTP un ComfyUI déjà lancé ; seuls le téléchargement de
modèles, le dossier `input` et le lancement automatique de ComfyUI en dépendent.
`COMFY_DIR` reste disponible pour forcer le chemin.

**Ce qui est lu depuis le paquet fonctionne toujours**, aux deux lancements :

- `GET /` → **200**, 50 107 octets (`web/index.html`)
- `GET /admin` → **200**, 24 142 octets (`web/admin.html`)
- `GET /api/compte` → **200**
- journal : `Aiguilleur: 11 intentions apprises` (`aiguilleur.json` lu depuis le paquet)
- sortie d'erreur vide, aucune trace de pile

Les 15 fichiers de données ont par ailleurs été vérifiés un par un dans la table
des matières de l'exe (`CArchiveReader`) : `web\index.html`, `web\admin.html`,
`aiguilleur.json`, `noeuds.exemple.json`, `agent_noeud.py`, `noeud.sh`,
`noeud.bat`, `modeles.sh`, `maj_noeud.sh`, `maj_noeud.bat`, `installer.py`,
`installation.py`, `zimaos-comfyui.yml`, `zimaos-registry.yml`, `catalogue.py`.

## L'aiguilleur a deux fichiers, l'exe n'en embarque qu'un

Depuis le 29 août, `aiguilleur.py` connaît deux modèles : `aiguilleur.json`,
publié et suivi par git, et `aiguilleur.local.json`, entraîné avec les demandes
réelles de l'installation et ignoré par git. `charger()` prend le local en
priorité. **Seul `aiguilleur.json` est dans la spec, et c'est voulu** : le local
porte le vocabulaire des utilisateurs de cette machine, il n'a rien à faire dans
un exe qu'on distribue.

Rien ne casse dans un cas comme dans l'autre — vérifié, pas supposé, en
exerçant `charger()` dans les cinq états possibles :

| État du disque | `charger()` rend |
|---|---|
| aucun des deux fichiers | `None` — le studio se rabat sur le modèle de langage |
| `aiguilleur.json` seul | le modèle publié |
| les deux | le **local**, comme voulu |
| local tronqué ou vide | le publié, sans lever |

La boucle de `charger()` avale toute exception et passe au suivant : un
`aiguilleur.local.json` à moitié écrit dégrade au lieu de tuer le démarrage.

### Ce que l'exe ne peut pas faire, et qu'il ne dit pas

`aiguilleur.py` calcule ses deux chemins depuis `ICI`, jamais depuis `ICI_DATA`
— correct pour **lire** le modèle embarqué, puisque c'est une ressource du
paquet. Mais gelé, `ICI` vaut le `_MEIxxxxxx` temporaire, et il en découle deux
choses mesurées sur une reproduction de cette disposition :

- un `aiguilleur.local.json` posé **à côté de l'exe** n'est jamais lu. L'exe se
  sert toujours du modèle publié qu'il porte.
- le bouton « réentraîner » de l'administration (`_mesurer_aiguilleur`, ligne
  4494) écrit dans `_MEIxxxxxx\`, effacé à la fermeture. Pire : son
  `moissonner()` cherche les conversations dans `_MEIxxxxxx\conversations`, qui
  n'existe pas ; il ne récolte donc jamais rien, `du_reel` reste faux, et c'est
  `aiguilleur.json` — la copie embarquée, dans le temporaire — qu'il écrase. Le
  bouton rend de belles mesures et **ne change rien**.

C'est exactement la faute qu'`ICI_DATA` a corrigée dans `serveur.py`, restée en
place ailleurs. La corriger demande de toucher à `aiguilleur.py` et
à `entrainer_aiguilleur.py` (chemins d'écriture et dossier moissonné tirés de
l'emplacement de l'exe, pas du paquet) : ce n'est pas un travail de
paquetage, et rien ici ne peut le rattraper.

## Pièges rencontrés à la construction

### Les modules voisins ne sont pas trouvés

`serveur.py` fait `from catalogue import ...`, `import fournisseurs`,
`import comptes`, `import aiguilleur` sur des fichiers voisins, pas installés.
Sans `pathex=[SOURCE]` dans la spec, l'analyse ne les voit pas et l'exe meurt
sur `ModuleNotFoundError` à la première ligne. Le `sys.path.insert(ICI)` de la
ligne 72 n'aide pas : il s'exécute trop tard, à l'exécution, alors que le
problème est à l'analyse.

### `entrainer_aiguilleur` est chargé par son nom

`importlib.import_module("entrainer_aiguilleur")` : un nom en chaîne de
caractères, que l'analyse statique ne peut pas suivre. Il est déclaré en
`hiddenimports`, avec `corpus_aiguillage` qu'il tire, et les cinq `.jsonl` qu'ils
lisent sont embarqués. Sans cela, `/api/aiguilleur/mesurer` rendrait une trace
de pile.

### Les imports cachés d'aiohttp

aiohttp choisit à l'exécution entre son analyseur HTTP en C et celui en Python,
et `multidict`/`yarl` font pareil par `try/except`. Ces extensions ne sont
atteintes par aucun import littéral : elles sont listées en `hiddenimports`
(`aiohttp._http_parser`, `aiohttp._websocket.mask`, `aiohttp._websocket.reader_c`,
`multidict._multidict`, `yarl._quoting_c`). En pratique PyInstaller 6.22 les
récupérait déjà seul ici, mais les nommer coûte zéro et protège d'une
régression de hook.

### Le Python embarqué contient torch — il faut l'exclure

C'est le piège le plus coûteux. `python_embeded` héberge torch, numpy,
transformers, safetensors, PIL… Le studio n'en importe aucun, mais un seul faux
positif de l'analyse ferait passer l'exe de 45 Mo à plusieurs gigaoctets. La
spec les coupe explicitement par `excludes`. **Ne pas retirer cette liste.**

### `catalogue.py` est à la fois du code et une donnée

Il est importé comme module **et** téléchargé en texte brut par les
machines-nœuds (`SCRIPTS_NOEUD`). Il figure donc deux fois dans le paquet, sous
deux formes. Ne pas s'en étonner en lisant la table des matières.

### `maj_noeud.sh` / `maj_noeud.bat` ne sont pas dans `SCRIPTS_NOEUD`

Ils ne sont référencés par aucune route, mais `noeud.sh` et `noeud.bat` les
citent pour la mise à jour. Ils sont embarqués quand même : les omettre
casserait la mise à jour d'un nœud déjà posé, et l'erreur ne se verrait que des
mois plus tard.

### PyAV pèse 27 Mo

`import av` est dans un `try/except` mais l'analyse statique le trouve, et
embarque les DLL ffmpeg d'`av.libs`. D'où les deux tailles mesurées.
`PAQUET_SANS_AV=1` les retire, au prix de `mesurer_cadence()` qui rend alors
toujours 24 im/s. Le défaut garde PyAV : mieux vaut 27 Mo qu'une fonction
dégradée en silence.

### `build\` doit être nettoyé entre deux constructions

PyInstaller garde en cache la liste des modules analysés. Un fichier de données
retiré de la spec resterait dans l'exe. `construire_windows.bat` efface
`build\` et `dist\` à chaque fois ; la construction ne dure que ~40 s.
Conséquence à connaître maintenant que l'exe écrit à côté de lui :
**reconstruire efface aussi les données** qu'un exe laissé dans `dist\` y aurait
écrites. Raison de plus pour déployer l'exe ailleurs que dans `dist\`.

## Reste à faire

- `paquet/build/` et `paquet/dist/` sont désormais dans le `.gitignore`
  (lignes 34-35) : plus de risque qu'un exe de 45 Mo entre dans le dépôt.
- L'exe n'est pas signé : au premier lancement, SmartScreen affichera
  « Windows a protégé votre ordinateur ». Rien à faire sans certificat de
  signature de code. Ne pas compresser par UPX : cela ne réduirait presque rien
  ici et ferait signaler l'exe par les antivirus.
- Le mode un-seul-fichier ré-extrait ~45 Mo dans `%TEMP%` à chaque lancement.
  Mesuré à 1,5 s, c'est acceptable. Un antivirus agressif peut allonger cela
  nettement ; si le démarrage devient pénible, passer en `COLLECT` (un dossier
  au lieu d'un fichier) supprime l'extraction — mais ce n'est plus « un seul
  exécutable ».
- Rien n'a été vérifié au-delà du démarrage et de la persistance : générer une
  image ou piloter un nœud distant depuis l'exe restent à essayer.
  Réentraîner l'aiguilleur, en revanche, ne marche pas — voir plus haut.
- La spec embarque **20** fichiers de données aujourd'hui (les 15 de la
  vérification ci-dessus, plus les cinq `.jsonl` de corpus). Rejouée hors
  PyInstaller, elle les trouve tous, et sa liste couvre encore l'intégralité de
  `SCRIPTS_NOEUD` — y compris `modeles.sh`, ajouté depuis.
