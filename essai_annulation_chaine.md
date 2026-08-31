# Essai — « annuler au LLM n'arrête pas le rendu »

Mission de reproduction et de diagnostic. Aucun fichier du dépôt modifié.

## Le chiffre

**0 reproduction sur 15 annulations tirées pendant la phase d'analyse.**
Aucune demande annulée pendant l'analyse n'a jamais atteint `travail confie a`,
sur 120 secondes d'observation à chaque fois.

En prime : 3 annulations de demandes encore en file (`retiree`) — aucune n'a
redémarré ensuite. Total 21 appels `DELETE /api/file/{tid}`, 0 chaîne survivante.

**Le symptôme décrit est réel, mais il a été corrigé le 29 août à 16:33**, par le
commit `26e6c5e` « Interruption demandee ne demandait rien a personne ». Le code
d'aujourd'hui ne le porte plus. Détail en fin de document.

## Environnement

- Studio `http://127.0.0.1:8199` depuis le conteneur `comfystudio` sur 172.20.1.191.
- Python 3.12.14. Trois travailleurs (`STUDIO_TRAVAILLEURS`, défaut 3).
- LLM nuage : Anthropic (Claude). LLM local : `qwen2.5vl:7b` sur 172.20.1.21.
- Machines de rendu joignables : `zima` (GTX 1060), `pc` (RTX 2080 Ti).
  Le ComfyUI local ne répond pas — tous les rendus partent donc chez un agent.
- Le studio a été redéployé deux fois pendant l'essai (par le propriétaire) :
  - `39faa20e6860a54bae3ca8f9b3a98658` (7893 lignes) — essais 1 à 4
  - `593c0a2401ad84443d41ced29258f79e` (7932 lignes) — essais 5 à 21
  Le diff entre les deux ne touche QUE le rejet des modèles Ollama qui ne se
  chargent pas et `journal(tid=None)` ; rien de l'annulation. Les mesures des
  deux séries sont donc comparables, et les deux séries donnent le même résultat.

## Méthode

Un script posé dans `/tmp` du conteneur (hors dépôt) qui :

1. ouvre une session sur un compte de test, règle `/api/nuage` ;
2. poste `/api/generer` ;
3. sonde `/api/etat/{tid}` toutes les 100 ms ;
4. tire `DELETE /api/file/{tid}` au moment voulu — soit dès que le journal
   montre `analyse par …`, soit N secondes après, soit à 0,4 s sans rien attendre ;
5. observe 120 secondes, en guettant `travail confie a` ;
6. si `travail confie a` apparaît malgré tout, annule immédiatement une seconde
   fois (les cartes ne sont pas à moi).

La fenêtre d'analyse mesurée est étroite mais confortable : de 0,01 s à
**6,4 s** (nuage) / **6,6 s** (Ollama) / **5,9 s** (Ollama + image). Entre
`analyse par …` et `travail confie a` il n'y a qu'UN point d'attente ; tout le
reste (choix du moteur, réglages, graphe, dépôt du travail) tombe dans le même
centième de seconde.

## Les essais

| # | chemin LLM | pièce jointe | annulation à | réponse du DELETE | `travail confie a` après ? |
|---|---|---|---|---|---|
| 1 | Anthropic | — | 0,01 s | `interrompue` | non |
| 2 | Anthropic | — | 3,05 s | `interrompue` | non |
| 3 | Anthropic | — | *6,39 s — trop tard, hors fenêtre* | `interrompue` | (déjà confié) |
| 4 | Anthropic | — | 0,44 s | `interrompue` | non |
| 5 | qwen2.5vl:7b | — | 0,03 s | `interrompue` | non |
| 6 | qwen2.5vl:7b | — | 0,12 s | `interrompue` | non |
| 7 | qwen2.5vl:7b | — | 2,07 s | `interrompue` | non |
| 8 | qwen2.5vl:7b | — | 5,06 s | `interrompue` | non |
| 9 | qwen2.5vl:7b | — | *6,64 s — trop tard* | `interrompue` | (déjà confié) |
| 10 | qwen2.5vl:7b | image | 0,12 s | `interrompue` | non |
| 11 | qwen2.5vl:7b | image | 3,11 s | `interrompue` | non |
| 12 | qwen2.5vl:7b | image | *5,88 s — trop tard* | `interrompue` | (déjà confié) |
| 13-15 | qwen2.5vl:7b | — | ~0,1 s (3 demandes en vol simultanées) | `interrompue` ×3 | non ×3 |
| 16-18 | — | — | ~0,1 s (3 demandes encore en file) | `retiree` ×3 | non ×3 |
| 19 | Anthropic | — | 0,02 s | `interrompue` | non |
| 20 | Anthropic | — | 1,61 s | `interrompue` | non |
| 21 | Anthropic | — | 4,06 s | `interrompue` | non |

15 tirs dans la fenêtre d'analyse (1, 2, 4, 5, 6, 7, 8, 10, 11, 13, 14, 15,
19, 20, 21), 15 arrêts nets. Journal type :

```
0.02  analyse par Anthropic (Claude)…
0.03  demande interrompue
0.03  interrompue
```

Les trois essais « trop tard » (3, 9, 12) sont instructifs à l'envers : quand
l'annulation arrive APRÈS le dépôt, la seconde annulation rend **409 « cette
demande est deja terminee »**. Le studio ne propose donc jamais deux annulations
réussies d'affilée sur une même demande — ce que le symptôme rapporté suppose.

## Ce que fait le code d'aujourd'hui — et pourquoi il tient

`serveur.py` md5 `593c0a24…`, 7932 lignes.

- `api_file_annuler` (l. 6196) : branche « en vol » l. 6224-6256. Journal, puis
  `interrompre_comfy` si la machine est joignable, puis `tache.cancel()` l. 6255
  sur la tâche prise dans `EN_VOL`.
- `travailleur()` (l. 5970) : `EN_VOL[tid] = travail` l. 5994, `await travail`,
  `except asyncio.CancelledError` l. 5997. Entre le retrait de `ATTENTE` et
  l'inscription dans `EN_VOL` il n'y a **aucun point d'attente** — pas de fenêtre
  où la demande serait invisible aux deux branches de l'annulation.
- Aucun `except BaseException` et **aucun `except:` nu** dans `/app/*.py`
  (vérifié par grep sur les modules du conteneur). En Python 3.12
  `CancelledError` dérive de `BaseException` : aucun `except Exception` du dépôt
  ne peut donc l'avaler. C'est vrai en particulier pour les trois endroits qui
  ressemblaient le plus à un piège :
  - `appeler_ollama` l. 1249 `except Exception` → repli `demander_a_un_noeud` ;
  - `aire_du_masque` l. 3336 `except Exception` → « aire du masque inconnue » ;
  - `soumettre_robuste` l. 4216-4232 `except MachineIncapable / PanneNoeud` → reprise ailleurs.

  Une annulation traverse les trois.

### Les motifs `asyncio` suspectés, mesurés

`_attendre_le_noeud` (l. 4059) utilise `asyncio.wait_for(asyncio.shield(attente),
timeout=5)` dans une boucle avec `except asyncio.TimeoutError: pass`, et
`poser_a` (l. 1291) fait `wait_for(verrou.acquire(), ATTENTE_LLM)` avec
`except asyncio.TimeoutError: return "", "carte occupee"`. Ce sont des motifs où
une annulation externe *peut* en théorie être requalifiée en `TimeoutError` par
`asyncio.timeout` (course entre le `cancel()` externe et l'expiration du délai),
et donc perdue dans le `pass` ou le `return`.

Éprouvé dans le Python du conteneur, sur les deux motifs recopiés à l'identique :

```
python 3.12.14
A. annulation loin du délai     attendre_le_noeud : 0 perdue / 600
                                poser_a           : 0 perdue / 600
B. annulation pile sur le délai attendre_le_noeud : 0 perdue / 600
                                poser_a           : 0 perdue / 600
```

**0 annulation perdue sur 2400.** L'`uncancel()` de `asyncio.timeout` fait son
travail sur cette version. Ces deux motifs sont hors de cause.

(Note : `poser_a` et `demander_a_un_noeud` ne sont de toute façon PAS sur le
chemin d'analyse tant qu'Ollama répond — `appeler_ollama` ne s'y replie que dans
son `except Exception` l. 1249. Ils n'ont donc pas été exercés en vrai ici, et je
ne les ai éprouvés que par le banc ci-dessus.)

## L'explication : le symptôme date d'avant le 29 août 16:33

Le comportement décrit par l'utilisateur est **exactement** celui du code
antérieur au commit `26e6c5e` (29 août, 16:33), dont le message dit la chose
mot pour mot :

> « Le message promettait que le calcul allait s'arreter. En realite on posait une
> marque et on frappait a la porte d'un ComfyUI — pendant que le studio continuait
> sa besogne : l'analyse, l'ecriture des paroles, l'attente d'un fournisseur. Rien
> de tout cela n'est un rendu ComfyUI, et rien ne regardait la marque. Une demande
> interrompue avant d'avoir touche la moindre carte ne s'arretait donc jamais. »

Dans `git show 26e6c5e^:serveur.py`, la branche « en vol » de `api_file_annuler`
faisait, et rien d'autre :

```python
t["annulee"] = True
ident = t.get("noeud") or noeud_local()["id"]
...
await interrompre_comfy(ident)
journal(tid, "interruption demandee — le calcul en cours s'arrete")
```

Trois faits qui, ensemble, produisent le symptôme :

1. **Aucun `cancel()`.** La chaîne `executer()` était `await`ée directement par
   `travailleur()`, sans tâche nommée : rien ne permettait de l'arrêter.
2. **`interrompre_comfy` ne pouvait rien arrêter pendant l'analyse.** Pendant
   l'analyse, aucune carte ne calcule : le `/interrupt` partait dans le vide.
3. **La marque `annulee` n'était lue qu'à UN endroit** — dans `travailleur()`, au
   moment de sortir le travail de la file, avant de le démarrer (l. 4636 de
   l'ancienne version). Une fois la demande partie, plus personne ne la relisait.

D'où la séquence vécue : on annule pendant l'analyse → le journal ment
(« interruption demandee — le calcul en cours s'arrete ») → l'analyse va au bout,
le prompt est enrichi, le graphe part vers la carte → **il faut annuler une
seconde fois**, et cette fois-ci ça marche, parce que cette fois-ci il y a bien un
rendu ComfyUI à interrompre. « Il annule que ce qui est en cours (llm ou rendu) »
décrit précisément un `/interrupt` qui ne sait viser que le rendu.

Deux commits ont ensuite consolidé la chose :

- `f138069` (30 août 18:02) « Annuler arrete enfin la carte » — l'annulation
  d'une machine à agent, qui n'avait aucune route.
- `03ab648` (30 août 21:10) « Un registre des travaux en vol » — `EN_VOL` en
  dictionnaire, pour que l'annulation vise la bonne tâche quand plusieurs
  travaillent en parallèle. Avant, avec `EN_COURS["tache"]` en place unique et
  trois travailleurs, annuler la demande A pouvait tuer la tâche de la demande B.
  **Ce commit-là est un second candidat sérieux** si l'observation date du 30 août
  entre 18:02 et 21:10.

## Ce dont je ne suis pas sûr

- **Je n'ai pas la date de l'observation.** Ma reconstruction historique est
  cohérente mot pour mot avec le symptôme, mais c'est une inférence à partir des
  commits, pas une reproduction sur l'ancien code. Je n'ai pas déployé de version
  antérieure — cela aurait demandé de toucher au conteneur. Si tu veux la preuve,
  un `git checkout 26e6c5e^` sur un port de test la donnerait en un essai.
- **Le chemin `poser_a` / `demander_a_un_noeud` n'a pas été exercé en vrai**, faute
  de pouvoir rendre Ollama injoignable sans toucher à la configuration. Le banc
  isolé le disculpe, pas la mesure en situation.
- **Fenêtre non couverte** : entre le retour de `executer()` et le
  `EN_VOL.pop(tid)` du `finally`, `api_file_annuler` répond `{"ok": true, "quoi":
  "interrompue"}` et journalise « demande interrompue » alors que
  `tache.done()` est vrai et que rien n'est annulé. C'est une réponse fausse, dans
  une fenêtre de l'ordre de la microseconde. Je ne l'ai pas vue se produire.
- **Un vrai « ça continue » subsiste, mais ailleurs** : quand la demande est déjà
  confiée à un agent, `tache.cancel()` tue la tâche du studio mais **la carte de
  l'agent continue** jusqu'à son prochain battement (journal : « sa carte s'arrete
  des qu'elle nous rappelle »). Vu 3 fois sur 3 dans les essais « trop tard ». Ce
  n'est pas le symptôme rapporté — la seconde annulation rend 409 — mais c'est le
  seul endroit où, aujourd'hui, annuler n'arrête pas tout de suite.

## Trouvaille annexe

`arreter_file()` (l. 7805) fait `a["travailleur"].cancel()`, mais depuis que les
travailleurs sont enregistrés sous `travailleur0…travailleur{N-1}` (l. 7794),
cette clé n'existe plus : `KeyError` à l'arrêt propre de l'application, et ni le
veilleur ni l'écoute ne sont annulés non plus. Sans conséquence visible (le
conteneur est tué), mais la ligne ne fait plus ce qu'elle dit.

## Ménage

Compte de test `essai_annul` supprimé, file vidée, scripts d'essai retirés du
conteneur. Aucun rendu n'a été mené à son terme : toutes les demandes parties en
rendu ont été annulées dans la seconde.
