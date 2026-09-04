# Essai du chemin « exécutable Windows »

> **Compte rendu daté du 30 août 2026, gardé tel quel.**
> Les chiffres tiennent. Depuis, le script de construction ne code plus
> le chemin de Python en dur.
> Voir [le journal des essais](README.md) pour ce qui a bougé depuis, et
> [la documentation](../README.md) pour l'état actuel.

Tout ce qui suit a été mesuré le **30 août 2026 entre 15 h 12 et 15 h 30**, sur
ce poste (Windows 11 Pro 26200, `D:\ComfyUI_windows_portable\python_embeded\python.exe`
3.13.14, PyInstaller 6.22.2), à partir de l'état du dépôt à cette heure-là.
Aucun fichier du dépôt n'a été modifié par cet essai. Le port **8399** a été
utilisé partout ; rien n'a touché 8199 ni `D:\ComfyStudio\conversations\`.

> **Numéros de ligne.** `serveur.py` et `web/index.html` ont été modifiés par
> quelqu'un d'autre à **15 h 31**, après mes mesures. Les numéros cités
> ci-dessous valent pour l'état de 15 h 12 ; les noms de symboles, eux, restent
> justes. C'est d'ailleurs l'objet de **F3**.

## Réponse courte

**Ça se construit et ça se lance.** Quatre constructions de suite, aucune en
échec ; l'exe démarre dans un dossier vide sans ComfyUI ni Ollama, crée son
compte administrateur, sert ses pages et ses vingt fichiers embarqués, et
**garde ses données d'un lancement à l'autre** — la correction `ICI_DATA` tient,
y compris celle d'`aiguilleur.py`.

Il reste **un défaut fonctionnel** (le bouton « réentraîner » écrit dans le
temporaire et dégrade le classifieur sur une installation neuve), **un problème
de publication** (le README ne mentionne nulle part ce chemin d'installation),
**une donnée d'utilisateurs dans un fichier suivi par git**, **un faux dossier
ComfyUI planté au-dessus de l'exe à chaque démarrage**, et une poignée d'écarts
entre ce que `NOTES.md` annonce et ce que la machine fait.

---

## 1. Est-ce que ça se construit ? — oui

### Commande

```
D:\ComfyStudio\paquet\construire_windows.bat
```

Lancée telle quelle, sans argument, depuis n'importe où (le `.bat` se replace).

### PyInstaller

Déjà installé : `PyInstaller 6.22.2`, et le script affiche
`[1/3] PyInstaller deja present.` La branche d'installation n'a donc **pas** été
exercée. Elle est viable : le Python embarqué a bien `pip 26.2.1`
(`D:\ComfyUI_windows_portable\python_embeded\Lib\site-packages\pip`), et la
commande exacte que le `.bat` exécuterait est

```
"D:\ComfyStudio\paquet\..\..\ComfyUI_windows_portable\python_embeded\python.exe" -m pip install pyinstaller
```

### Durées et tailles mesurées

| Construction | Durée | Taille de `dist\ComfyStudio.exe` |
|---|---|---|
| à froid (`build\` et `dist\` vides) | **28 s** | 44 876 982 o |
| à chaud, par défaut | 21 s | 44 876 830 o |
| à chaud, `PAQUET_SANS_AV=1` | **14 s** | **17 574 701 o** |
| à chaud, par défaut (artefact final laissé en place) | 20 s | 44 876 924 o |

Trois constructions de configuration identique donnent 44 876 830, 44 876 924 et
44 876 982 octets : **± 160 octets**, ce qui correspond à ce que `NOTES.md`
décrit. Le `.bat` nettoie bien `build\` et `dist\` à chaque fois.

### Ce que contient l'exe

Table des matières lue avec `PyInstaller.archive.readers.CArchiveReader` :
**222 entrées**, dont les **20 fichiers de données** attendus, tous présents —
`web/index.html`, `web/admin.html`, `aiguilleur.json`, `noeuds.exemple.json`,
les onze scripts de nœud (`agent_noeud.py`, `noeud.sh`, `noeud.bat`,
`zimaos-comfyui.yml`, `zimaos-registry.yml`, `installer.py`, `installation.py`,
`catalogue.py`, `modeles.sh`, `maj_noeud.sh`, `maj_noeud.bat`) et les cinq
corpus `.jsonl`.

- `torch`, `numpy` : **aucune entrée**. La liste `excludes` fait son travail.
- `aiguilleur.local.json` : **absent**, comme voulu.
- 73 entrées `av.libs` — les 27 Mo de DLL ffmpeg.
- `build\comfystudio\warn-comfystudio.txt` : 67 lignes `missing module`, aucune
  gênante (les seules qui touchent le studio sont `av.video._VideoCodecName` et
  `av.audio._AudioCodecName`, des noms de typage).

---

## 2. Est-ce que ça se lance ? — oui

### Protocole

L'exe a été copié dans un dossier **vide**, hors du dépôt
(`…\scratchpad\essai_neuf\`), et lancé avec :

```
STUDIO_PORT=8399
COMFY_URL=http://127.0.0.1:18188     (rien n'écoute)
OLLAMA_URL=http://127.0.0.1:11439    (rien n'écoute)
```

ComfyUI (8188) et Ollama (11434) tournent réellement sur ce poste ; les pointer
sur des ports morts était le seul moyen de reproduire une machine nue sans
arrêter le travail des autres. `STUDIO_PORT` est bien la variable qui règle le
port (`serveur.py:47`, `PORT = int(os.environ.get("STUDIO_PORT", "8199"))`).

### Ce qu'on voit — sortie intégrale du premier lancement

```
  Administration : jeton <jeton-32-caracteres>
  (a coller dans /admin ; conserve dans conversations/_admin.json)
================================================================
  Compte administrateur cree : admin
  Mot de passe : <mot-de-passe-16-caracteres>
  Note-le : il n'est pas conserve en clair et ne sera
  plus jamais affiche. Change-le depuis l'interface.
================================================================
  Comptes   : 1 (1 administrateur(s))   — connexion obligatoire
  Ecriture  : qwen2.5vl:7b
  Aiguilleur: 11 intentions apprises
================================================================
  ComfyStudio
  ComfyUI   : http://127.0.0.1:18188
  Ollama    : http://127.0.0.1:11439   (qwen2.5vl:7b)
  Modeles   : …\scratchpad\ComfyUI_windows_portable\ComfyUI\models
  Interface : http://127.0.0.1:8399
  RESEAU    : ferme — cette machine seulement
              pour ouvrir : set STUDIO_HOTE=0.0.0.0 (ou « LANCER ComfyStudio.bat »)
  Conversations : 0 chargee(s)
  VRAM      : inconnue — aucun ComfyUI joignable au demarrage
================================================================
```

- Le compte administrateur **est créé**, le mot de passe **est affiché**, le
  jeton d'administration aussi. Les accents et le tiret cadratin sortent
  correctement.
- **Sortie d'erreur vide**, aucune trace de pile, sur les six lancements.
- L'absence de ComfyUI et d'Ollama est annoncée sans casser le démarrage
  (« VRAM : inconnue — aucun ComfyUI joignable »).
- La page répond : `GET /` → **200, 64 697 octets**.

### Temps de démarrage

Mesuré du `Start-Process` au premier `HTTP 200` sur `/api/compte` :

| Lancement | Emplacement de l'exe | Délai |
|---|---|---|
| 1 (à froid) | `C:\…\scratchpad\essai_neuf` | 5,98 s |
| 2 | idem | 5,82 s |
| 3 | idem | 5,84 s |
| 4 | idem | 5,31 s |
| 5 | `D:\ComfyStudio\paquet\dist` | 5,50 s |
| 6 (sans PyAV, 17 Mo) | `D:\ComfyStudio\paquet\dist` | 4,98 s |
| 7 (artefact final) | `D:\ComfyStudio\paquet\dist` | 5,38 s |

Voir le point **F1** : ce n'est pas 1,5 s.

---

## 3. Le piège du gel — la correction tient

### Où atterrissent les données

Le dossier ne contenait que `ComfyStudio.exe` avant l'essai. Après le premier
arrêt :

```
essai_neuf\ComfyStudio.exe
essai_neuf\conversations\_admin.json     (45 o)
essai_neuf\conversations\_comptes.json  (194 o)
essai_neuf\conversations\_session.json   (57 o)
```

À côté de l'exe, pas dans le temporaire. Les autres chemins d'écriture sont
alignés eux aussi : `FICHIER_NOEUDS` (`serveur.py:207`), `FICHIER_AVIS` (4164)
et `SORTIES_AGENT` (6141) dérivent tous de `DOSSIER_DONNEES` (99), lui-même
`ICI_DATA`.

### Deux lancements créent-ils deux comptes admin ? — non

| | lancement 1 | lancement 2 |
|---|---|---|
| « Compte administrateur cree » | 1 fois | **0 fois** |
| « Mot de passe : » | `<mot-de-passe-16-caracteres>` | **aucune ligne** |
| « Administration : jeton » | affiché | **aucune ligne** |
| SHA-256 de `_admin.json` | `04066A8F…` | `04066A8F…` (identique) |

Preuve fonctionnelle, pas seulement de fichier :

- connexion `POST /api/compte/entrer` avec `admin` / `<mot-de-passe-16-caracteres>` au
  **second** lancement → `{"ok": true, "nom": "admin", "admin": true}` ;
- le jeton d'administration affiché au **premier** lancement ouvre encore
  `/api/admin/*` au second ;
- une conversation créée au lancement 2 (`8efb406c8f99.json`) est retrouvée au
  lancement 3 : `Conversations : 1 chargee(s)`.

`_comptes.json` passe de 194 à 210 octets entre les deux — c'est l'horodatage
`vu` de la connexion, pas une recréation.

### Le modèle d'aiguillage — lequel est chargé

`Aiguilleur: 11 intentions apprises`, et `GET /api/admin/aiguilleur` rend
`traits = 7890`. C'est **`aiguilleur.json` embarqué** (7 890 traits, 2 942
exemples), pas `aiguilleur.local.json` (7 902 traits), qui n'est pas dans l'exe.

**L'alignement d'`aiguilleur.py` sur `ICI_DATA` fonctionne, vérifié.** Un
`aiguilleur.local.json` factice de vocabulaire `4242` posé **à côté de l'exe**
est bien préféré au modèle embarqué :

```
  Aiguilleur: 2 intentions apprises
  traits chargés : 4242
```

`NOTES.md` affirme le contraire (« un `aiguilleur.local.json` posé à côté de
l'exe n'est jamais lu ») : cette phrase est **périmée** depuis la correction
d'`aiguilleur.py` (lignes 42 et 51).

---

## 4. Ce qui manque à l'intérieur — rien, sauf le comportement du bouton

Toutes les routes interrogées sur l'exe gelé, jeton d'administration en en-tête
`X-Admin`. **Aucun 404 inattendu, aucune trace de pile.**

| Route | Code | Taille / réponse |
|---|---|---|
| `GET /` | 200 | 64 697 o |
| `GET /admin` | 200 | 35 809 o |
| `GET /api/compte` | 200 | JSON |
| `GET /api/noeud/agent` | 200 | 35 757 o |
| `GET /api/noeud/noeud.sh` | 200 | 9 219 o |
| `GET /api/noeud/noeud.bat` | 200 | 9 890 o |
| `GET /api/noeud/zimaos.yml` | 200 | 8 565 o |
| `GET /api/noeud/zimaos-registre.yml` | 200 | 3 194 o |
| `GET /api/noeud/installer.py` | 200 | 1 833 o |
| `GET /api/noeud/installation.py` | 200 | 44 966 o |
| `GET /api/noeud/catalogue.py` | 200 | 16 899 o |
| `GET /api/noeud/modeles.sh` | 200 | 3 401 o |
| `GET /api/noeud/maj_noeud.sh` | 200 | 2 816 o |
| `GET /api/noeud/maj_noeud.bat` | 200 | 2 253 o |
| `GET /api/noeud/inexistant` | 404 | `{"erreur": "inconnu"}` — attendu |
| `GET /api/admin/noeuds` | 200 | JSON |
| `GET /api/admin/aiguilleur` | 200 | JSON |
| `GET /api/admin/avis` | 200 | JSON |
| `GET /api/admin/comptes` | 200 | JSON |
| `GET /api/admin/cles` | 200 | 2 147 o |
| `POST /api/admin/aiguilleur` | 200 | 0,1 s — mais voir **G1** |

Les onze fichiers de `SCRIPTS_NOEUD` sont servis, à leur taille exacte. La
couverture de la spec est complète : les 13 clés de `SCRIPTS_NOEUD`
(`serveur.py:6714`) pointent sur 11 fichiers distincts, tous embarqués.

`/api/etat` rend 404 : cette route n'existe pas dans `serveur.py`, ce n'est pas
un effet du gel.

---

## Problèmes, par gravité

### G1 — GRAVE : « réentraîner » écrit dans le temporaire et dégrade le classifieur

**Ce qui a été mesuré.** Sur une installation neuve (aucune conversation
validée), `POST /api/admin/aiguilleur` rend `HTTP 200` avec de belles mesures,
puis :

- le fichier écrit est
  `C:\Users\<toi>\AppData\Local\Temp\_MEI0000c6602\aiguilleur.json`
  (192 338 o, horodaté 15:15) — la copie **embarquée**, dans le dossier
  temporaire effacé à l'arrêt ;
- rien n'apparaît à côté de l'exe ;
- le modèle **en mémoire** passe de **7 890 traits à 7 680** : le studio se sert
  aussitôt d'un classifieur *plus pauvre* que celui qu'il portait ;
- au redémarrage suivant, retour à 7 890. Le clic n'a servi à rien, et rien ne
  le dit.

**Ce qui marche déjà.** Dès qu'une conversation récoltable existe (un tour
`etat: "fini"`, `avis: 1`, `type` connu), le chemin est correct : `moissonner()`
trouve bien `…\essai_neuf\conversations` (`entrainer_aiguilleur.py:59`, tiré de
`_aiguilleur.ICI_DATA`), `corpus()` rend 2 907 exemples au lieu de 2 899, et
`aiguilleur.local.json` est écrit **à côté de l'exe** (192 357 o) et **relu au
redémarrage**. La moitié du défaut décrit dans `NOTES.md` est donc corrigée.

**Cause exacte.** `serveur.py:4538` :

```python
neuf.ecrire(_aiguilleur.MODELE_LOCAL if du_reel else _aiguilleur.MODELE)
```

et `entrainer_aiguilleur.py:159-160` fait le même choix. Or
`_aiguilleur.MODELE` vaut `os.path.join(ICI, "aiguilleur.json")`
(`aiguilleur.py:45`), et `ICI` gelé est le `_MEIxxxxxx`. Quand `du_reel` est
faux — c'est-à-dire **toujours**, sur une installation neuve — on écrit dans le
jetable.

**Correction possible (non appliquée).** Gelé, il n'existe aucun cas où écrire
`MODELE` ait un sens : le paquet est en lecture seule par nature. Dans
`serveur.py:4538` et `entrainer_aiguilleur.py:159` :

```python
ou = (_aiguilleur.MODELE_LOCAL
      if (du_reel or getattr(sys, "frozen", False))
      else _aiguilleur.MODELE)
```

Plus propre encore : donner à `Aiguilleur.ecrire` (`aiguilleur.py:144`) le
défaut `MODELE_LOCAL` quand `sys.frozen`, pour que le mauvais chemin ne soit
plus atteignable.

**Deuxième moitié du problème, indépendante du gel.** Même si l'écriture
atterrissait au bon endroit, le réentraînement produit un modèle **plus faible**
que celui livré : 2 899 exemples / 7 680 traits contre 2 942 / 7 890. Voir
**G3**. Tant que cet écart existe, le bouton « réentraîner » d'une installation
neuve est une régression, pas une amélioration.

---

### G2 — GRAVE (publication) : le README ne mentionne pas l'exe

État du `README.md` à 15 h 10 aujourd'hui : `comfystudio.exe`,
`construire_windows.bat`, `paquet`, `PyInstaller`, « exécutable » —
**aucune occurrence**. Le sommaire propose « Installer » (`installer.bat` /
`installer.sh`) et « En conteneur ». Le troisième chemin n'existe nulle part
pour un lecteur du dépôt : ni comment le construire, ni où le poser, ni qu'il
existe.

`paquet/NOTES.md` est complet mais c'est un document de paquetage, pas une
notice d'installation, et rien ne pointe vers lui.

**Correction.** Une section « Un seul exécutable Windows » dans le README, entre
« Installer » et « En conteneur », avec au minimum : la commande de
construction, l'endroit où poser l'exe, le fait qu'il écrit **à côté de lui**,
et l'avertissement SmartScreen.

---

### G3 — GRAVE (dépôt public) : `aiguilleur.json` suivi par git contient des demandes réelles

Reproduction, sans rien écrire : entraînement sur les **seuls fichiers suivis
par git**, moisson neutralisée.

```
reproduit depuis les corpus suivis : 2899 exemples, 7680 traits
aiguilleur.json publie             : 2942 exemples, 7890 traits

classe         corpus  publie  ecart
audio             270     286     +16
image             271     298     +27
(les neuf autres classes : ecart 0)
```

Les 43 exemplaires en trop, concentrés sur deux classes, sont la signature de
`moissonner()` avec `POIDS_REEL = 8`. Autrement dit : **le modèle publié n'est
pas reproductible depuis le dépôt**, et il porte le vocabulaire d'utilisateurs
réels — exactement ce que la séparation `aiguilleur.json` / `aiguilleur.local.json`
a été conçue pour éviter. Un modèle bayésien ne garde pas les phrases, mais il
garde les mots.

C'est en dehors du paquetage, mais c'est l'exe qui l'emporte tel quel chez ses
utilisateurs, et le dépôt doit devenir public.

**Correction.** Régénérer `aiguilleur.json` avec la moisson désactivée
(`python entrainer_aiguilleur.py` depuis une copie sans `conversations/`, ou un
drapeau `--sans-moisson`), et vérifier en intégration continue que le modèle
suivi est bien celui que les corpus suivis produisent.

---

### M1 — MOYEN : `PAQUET_SANS_AV=1` ignoré en silence sur une ligne

**Commande.**

```
cmd /c "set PAQUET_SANS_AV=1 && D:\ComfyStudio\paquet\construire_windows.bat"
```

**Résultat mesuré.** `Taille : 44 876 830 octets` — l'exe complet, PyAV inclus.
Aucun avertissement, aucune trace : on croit avoir la version légère.

**Cause.** `cmd` affecte tout ce qui suit le `=` jusqu'au `&&`, espace compris :
la variable vaut `"1 "`. La spec compare à `"1"` exactement
(`comfystudio.spec:31`, `os.environ.get("PAQUET_SANS_AV", "0") == "1"`).

Avec `set PAQUET_SANS_AV=1&&…` (sans espace), tout va bien :
**17 574 701 octets**, construit en 14 s, et l'exe démarre normalement (4,98 s).

**Corrections.**
- `comfystudio.spec:31` → `os.environ.get("PAQUET_SANS_AV", "0").strip() == "1"`.
- `construire_windows.bat` : accepter un argument (`construire_windows.bat sans-av`)
  plutôt qu'une variable d'environnement, et **afficher** la variante choisie
  au début de la construction. Aujourd'hui rien dans la sortie ne dit si PyAV
  est dedans ou non.

---

### M2 — MOYEN : arrêter l'exe ne l'arrête pas

Le mode un-seul-fichier lance **deux processus** : le lanceur, et l'enfant qui
sert le studio. Mesures :

| Geste | Résultat |
|---|---|
| `Stop-Process -Id <pid lancé> -Force` | l'enfant survit et **répond encore HTTP 200** sur 8399 |
| `taskkill /PID <pid>` (sans `/F`) | les deux processus survivent, le studio **répond encore** |
| `taskkill /F /T /PID <pid>` | arrêt complet |

Conséquence pratique : tout script d'arrêt, tout enveloppeur de service, tout
`LANCER ComfyStudio.bat` qui tue le PID visible laisse un studio en écoute sur
le port — et le lancement suivant échouera à prendre le port, ou pire, on
croira parler au neuf.

*Non vérifié :* le `Ctrl-C` au clavier dans une vraie console. Cette session
n'est pas interactive ; `bootloader_ignore_signals=False` dans la spec laisse
penser que le signal est bien relayé, mais ce n'est pas mesuré.

**Correction.** Documenter `taskkill /F /T /PID` dans `NOTES.md` et dans le
README, et vérifier que tout lanceur fourni arrête l'arbre, pas le père.

---

### M3 — MOYEN : chaque arrêt brutal laisse 90,6 Mo dans `%TEMP%`

Chaque `_MEIxxxxxx` non nettoyé pèse **90,6 Mo** (25,2 Mo pour la variante sans
PyAV) — l'exe de 45 Mo décompressé. À la fin de mes essais, `%TEMP%` contenait
**six dossiers du 29 août** (11 h 11 à 11 h 19, ~544 Mo), laissés par les essais
précédents et **toujours là**, plus les sept des miens que j'ai supprimés.

Combiné à **M2** (le geste d'arrêt naturel est brutal), ça se remplit vite et
personne ne le voit. `NOTES.md` mentionne la ré-extraction mais pas la fuite.

**Correction.** Le mentionner dans `NOTES.md` avec le chiffre, et donner la
commande de ménage. Le passage en `COLLECT` (déjà envisagé dans `NOTES.md`)
supprime la question entièrement, au prix du fichier unique.

---

### M4 — MOYEN : « poser l'exe dans `D:\ComfyStudio\` » entre en collision avec `ICI_DATA`

Le `.bat` conclut par : *« Le poser dans D:\ComfyStudio\ pour qu'il retrouve son
voisin ComfyUI_windows_portable »*. Or `ICI_DATA` vaut le dossier de l'exe :
posé là, l'exe écrirait ses conversations dans **`D:\ComfyStudio\conversations\`**
— le dossier du dépôt, qui est ici la sauvegarde d'avant le déménagement — et
lirait le `aiguilleur.local.json` du dépôt (vérifié : un modèle local à côté de
l'exe est bien préféré, § 3).

Les deux conseils sont justes séparément et dangereux ensemble. Pour un exe
distribué, le second l'emporte : le dossier de l'exe est le dossier de données.

**Correction.** Remplacer le conseil par : poser l'exe dans un dossier **à lui**,
et renseigner `COMFY_DIR` pour désigner ComfyUI. C'est déjà la variable prévue
(`serveur.py:63`), et le message de fin du `.bat` la cite ; il suffit d'en faire
la voie normale plutôt que le repli.

---

### M5 — MOYEN : l'exe plante un faux arbre ComfyUI **au-dessus** de son dossier

Découvert au ménage, pas à l'essai : après les lancements, ces arborescences
vides existaient, créées à 15:14 et 15:20 :

```
…\scratchpad\ComfyUI_windows_portable\ComfyUI\input        (exe lancé depuis …\scratchpad\essai_neuf\)
D:\ComfyStudio\paquet\ComfyUI_windows_portable\ComfyUI\input   (exe lancé depuis …\paquet\dist\)
```

L'exe crée donc un dossier **dans le répertoire parent du sien**, sans le dire.
La deuxième ligne est du détritus déposé **dans le dépôt**, dans `paquet\`, qui
n'est pas ignoré par git — invisible à `git status` seulement parce que git ne
suit pas les dossiers vides.

**Cause exacte.** `serveur.py:110-119` :

```python
def _entree_utilisable(dossier):
    try:
        os.makedirs(dossier, exist_ok=True)     # ← crée l'arbre avant de tester
        return os.access(dossier, os.W_OK)
    ...
if not _entree_utilisable(DOSSIER_ENTREE):
    DOSSIER_ENTREE = os.path.join(DOSSIER_DONNEES, "entrees")
```

`DOSSIER_ENTREE` vaut `ICI_DATA\..\ComfyUI_windows_portable\ComfyUI\input`. La
sonde **crée** le chemin au lieu de constater son absence : `makedirs` réussit,
`os.access` répond « inscriptible », et le repli sur `DOSSIER_DONNEES\entrees`
— écrit précisément pour le cas « cette machine n'a pas de ComfyUI » — **ne se
déclenche jamais** sur Windows. Le studio range ensuite les images jointes dans
ce faux `input`, à côté du dossier de l'utilisateur et non dans ses données.

Pour quelqu'un qui découvre et lance l'exe depuis `Téléchargements\studio\`,
cela crée `Téléchargements\ComfyUI_windows_portable\ComfyUI\input`.

**Correction.** Ne créer que ce qu'on possède : tester l'existence d'abord, et
ne tenter `makedirs` que sur le dossier de repli.

```python
def _entree_utilisable(dossier):
    if not os.path.isdir(dossier):
        return False            # ComfyUI n'est pas la : on ne l'invente pas
    return os.access(dossier, os.W_OK)
```

Ce n'est pas un défaut du paquetage — il existe aussi hors gel — mais le gel le
rend visible et nuisible, parce que l'exe se promène et que `ICI_DATA\..` n'est
plus le dossier parent du dépôt mais celui où l'utilisateur l'a posé.

---

### F1 — FAIBLE : le démarrage n'est pas de 1,5 s

`NOTES.md` annonce « 1,5 s entre le lancement et la première réponse HTTP ».
**Sept mesures**, deux disques, à froid et à chaud : **4,98 s à 5,98 s**. La
variante sans PyAV (17 Mo au lieu de 45) ne gagne que 0,5 s — l'extraction n'est
donc pas le poste dominant, c'est l'initialisation de Python et l'import
d'aiohttp. Le chiffre de 1,5 s n'est pas reproductible aujourd'hui et devrait
être corrigé, ou accompagné de sa méthode de mesure.

---

### F2 — FAIBLE : les tailles documentées ont dérivé

| Source | Annoncé | Mesuré aujourd'hui |
|---|---|---|
| `NOTES.md`, tableau de résumé | 44 818 700 o | 44 876 924 o |
| `construire_windows.bat`, ligne 5 | 44 818 543 o | idem |
| sans PyAV (les deux) | 17 517 471 o | 17 574 701 o |

Écart de +58 000 octets, cohérent avec la croissance de `serveur.py` et des
pages web depuis le 29 août. Les deux documents donnent d'ailleurs **deux
chiffres différents** pour la même chose. À aligner, ou à remplacer par un ordre
de grandeur (« ~45 Mo », « ~17 Mo sans PyAV ») qui ne périmera pas.

---

### F3 — FAIBLE : `NOTES.md` et la spec décrivent un code qui a changé

- La section « Ce que l'exe ne peut pas faire, et qu'il ne dit pas » est fausse
  sur deux de ses trois affirmations depuis la correction d'`aiguilleur.py` :
  le modèle local à côté de l'exe **est** lu, et `moissonner()` cherche les
  conversations **au bon endroit**. Seule l'écriture dans le temporaire subsiste
  (**G1**), et pour une autre raison que celle décrite.
- Le commentaire de `comfystudio.spec` (lignes 51-56) justifie l'exclusion
  d'`aiguilleur.local.json` par « gelé il n'existe jamais à côté d'`aiguilleur.py`
  (les deux chemins sortent de `ICI`) » : ce n'est plus vrai. L'exclusion reste
  la bonne décision, mais le motif est à réécrire — sinon quelqu'un le
  « corrigera » sur la foi d'un raisonnement caduc.
- « `ICI_DATA` remplace `ICI` aux cinq endroits qui écrivent » : le résultat est
  bon, mais `FICHIER_NOEUDS`, `FICHIER_AVIS` et `SORTIES_AGENT` passent
  maintenant par `DOSSIER_DONNEES`, pas par `ICI_DATA` directement.
- **Tous** les numéros de ligne cités dans `NOTES.md` et dans l'en-tête de la
  spec sont périmés. Correspondances actuelles :

  | Cité | Réel |
  |---|---|
  | `web/index.html` servi ligne 4239 / 4246 | **5370** |
  | `web/admin.html` servi ligne 5076 / 5083 | **6709** |
  | `SCRIPTS_NOEUD` ligne 5081 | **6714** |
  | scripts servis ligne 5104 | **6738** |
  | `import_module` ligne 3593 | **4528** |
  | `_mesurer_aiguilleur` ligne 4494 | **4524** |
  | `DOSSIER_CONV` ligne 95 | **104** |
  | `FICHIER_NOEUDS` ligne 116 | **207** |
  | `FICHIER_AVIS` ligne 3273 | **4164** |
  | `SORTIES_AGENT` ligne 4759 | **6141** |

  Citer des numéros de ligne dans un fichier de 6 900 lignes qui bouge tous les
  jours coûte plus qu'il ne rapporte : mieux vaut citer le **nom** du symbole.

---

### F4 — FAIBLE : la construction exige ComfyUI portable comme voisin du dépôt

`construire_windows.bat` calcule `PY = %PAQUET%..\..\ComfyUI_windows_portable\…`,
c'est-à-dire le **parent du dépôt**. Un contributeur qui clone ailleurs obtient,
vérifié en copiant le `.bat` dans un autre dossier :

```
[erreur] Python embarque introuvable : C:\…\ailleurs\..\..\ComfyUI_windows_portable\python_embeded\python.exe
         Corrigez la variable PY en tete de ce script.
```

Le message est clair et le code de sortie est bien 1. Mais pour un dépôt public,
**personne ne peut construire l'exe sans avoir ComfyUI portable rangé au bon
endroit**, alors que rien dans la spec ne l'exige : elle ne dépend que de
`SPECPATH`. Un repli sur `py -3` ou `python` du `PATH`, avec un message
expliquant qu'il faut alors `pip install aiohttp`, ouvrirait le chemin.

Accessoirement, le message affiche le chemin non résolu (`…\ailleurs\..\..\…`),
lisible mais inélégant : `for %%I in ("%PY%") do echo %%~fI` le simplifierait.

---

### F5 — INFO : non vérifié

- **SmartScreen.** L'exe n'est pas signé ; `NOTES.md` annonce l'avertissement
  « Windows a protégé votre ordinateur ». Tous mes lancements sont passés par
  `Start-Process`, jamais par un double-clic depuis l'explorateur : je n'ai donc
  ni confirmé ni infirmé l'avertissement.
- **`Ctrl-C` clavier**, voir M2.
- **Production réelle.** Aucune image, aucune vidéo, aucun nœud distant piloté
  depuis l'exe : ComfyUI et Ollama étaient délibérément débranchés. Le point
  ouvert de `NOTES.md` (« générer une image depuis l'exe reste à essayer ») le
  reste.
- **`mesurer_cadence()` sans PyAV** : le repli à 24 im/s est documenté, pas
  mesuré ici (il faudrait téléverser une vidéo).

---

## 5. Le ménage

- Aucun fichier du dépôt modifié. `git status --porcelain` à la fin ne montre
  que `essai_installation.md` et `essai_retouche_limites.md`, livrables d'autres
  agents, plus ce fichier une fois écrit.
- `D:\ComfyStudio\conversations\` : **intacte**, aucun fichier modifié après
  15 h 10 (`find … -newermt`).
- Dossiers d'essai supprimés (`…\scratchpad\essai_neuf`, `…\scratchpad\ailleurs`,
  la copie de l'exe qu'ils contenaient), ainsi que mes scripts et journaux
  d'essai dans le scratchpad.
- Les deux arborescences `ComfyUI_windows_portable\ComfyUI\input` créées par
  l'exe lui-même (voir **M5**) ont été supprimées, **y compris celle qu'il avait
  déposée dans `D:\ComfyStudio\paquet\`**. `paquet\` ne contient plus que
  `NOTES.md`, `comfystudio.spec`, `construire_windows.bat`, `build\` et `dist\`.
- `D:\ComfyStudio\paquet\dist\` contient **le seul `ComfyStudio.exe`**
  (44 876 924 o, construction par défaut, démarrage vérifié) ; le
  `dist\conversations\` créé par un essai a été supprimé. `paquet\build\` est
  laissé tel quel, comme le `.bat` le produit.
- **Aucun processus `ComfyStudio` ne tourne**, les ports 8399 et 8199 ne sont
  pas en écoute localement.
- Les sept `%TEMP%\_MEI*` créés par mes essais sont supprimés. **Les six du
  29 août sont laissés en place** (≈ 544 Mo) : ils ne viennent pas de moi, et
  leur suppression n'est pas à moi de la décider — voir **M3**.
