# -*- coding: utf-8 -*-
"""Quelle machine recoit le travail, et le studio sans carte s'abstient-il ?

    python banc_repartition.py

Le studio du reseau tourne dans un conteneur sur une machine SANS GPU : il ne
fait que repartir le travail sur les noeuds. Trois endroits du code supposaient
pourtant qu'il pouvait calculer, et aucun ne posait la question.

Le defaut, signale par l'utilisateur — « il m'affiche souvent moteur local, le
studio n'en a pas, uniquement les noeuds, et du coup attend dans le vide » :

  - _vram_utile accordait la tolerance RAM a une machine SANS carte. La
    tolerance dit de combien on peut DEPASSER la carte ; sans carte, il n'y a
    rien a depasser. Un studio a 16 Go de RAM se presentait donc comme une
    carte de 2 Go, et a 64 Go comme une carte de 5 Go.
  - noeuds_pour dispense le studio du « le modele est-il la ? », parce qu'il
    peut le telecharger sur son disque. Sans carte, cette dispense le faisait
    retenir pour des moteurs qu'il n'a pas et ne saurait pas faire tourner.
  - choisir_noeud preferait le noeud local SANS CONDITION. Il gagnait donc
    contre la 2080 Ti, et le rendu partait sur une machine incapable.

Les trois ensemble donnent exactement le symptome decrit. Aucun banc ne
regardait la repartition ; celui-ci le fait.
"""
import asyncio
import contextlib
import inspect
import io
import json
import os
import sys
import tempfile

os.environ["STUDIO_DONNEES"] = tempfile.mkdtemp(prefix="banc_repartition_")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serveur as S  # noqa: E402

ok, rate = [], []


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


# Le moteur le plus leger du catalogue : c'est celui pour lequel une machine
# sans carte avait le plus de chances de passer.
CLE = min(S.CATALOGUE, key=lambda c: S.CATALOGUE[c].get("vram", 0) or 99)
BESOIN = S.CATALOGUE[CLE].get("vram", 0)


def poser(vram_studio=0.0, ram_studio=64.0, vram_pc=11.0, vram_zima=5.9):
    """Le parc reel : un studio en conteneur, et deux machines a agent."""
    S.NOEUDS[:] = [{"id": "local", "url": "http://127.0.0.1:8188",
                    "titre": "cette machine", "local": True}]
    S.REGISTRE.clear()
    S.REGISTRE["pc"] = {"id": "pc", "titre": "PC (RTX 2080 Ti)", "agent": True,
                        "jeton": "x", "pause": None}
    S.REGISTRE["zima"] = {"id": "zima", "titre": "NAS ZimaOS (GTX 1060)",
                          "agent": True, "jeton": "y", "pause": None}
    S.ETAT_NOEUDS.clear()
    S.ETAT_NOEUDS["local"] = {"repond": True, "vram": vram_studio,
                              "ram": ram_studio, "vu": S.time.time()}
    S.ETAT_NOEUDS["pc"] = {"repond": True, "vram": vram_pc, "ram": 63.8,
                           "vu": S.time.time()}
    S.ETAT_NOEUDS["zima"] = {"repond": True, "vram": vram_zima, "ram": 23.4,
                             "vu": S.time.time()}
    S.VERROUS_NOEUD.clear()
    S.EN_VOL.clear()
    S.TACHES.clear()
    # Le moteur present PARTOUT : ce qu'on mesure ici est le choix, pas
    # l'inventaire. La dispense du local est eprouvee a part, plus bas.
    S.manquants = lambda cle, ident=None: []


print(f"\n  moteur du banc : {CLE} ({BESOIN} Go)\n")

# ── un studio SANS carte ne se choisit pas lui-meme ─────────────────────
poser(vram_studio=0.0, ram_studio=64.0)
dit(not S.carte_locale(), "sans VRAM, le studio sait qu'il n'a pas de carte")
dit(S._vram_utile("local") == 0.0,
    "et la tolerance RAM ne lui invente pas une carte de 5 Go",
    f"{S._vram_utile('local')} Go")
choisi = S.choisir_noeud(CLE)
dit(choisi is not None and choisi["id"] != "local",
    "le travail part sur une machine a carte, pas sur le studio",
    str(choisi and choisi["id"]))
dit("local" not in [x["id"] for x in S.noeuds_pour(CLE)],
    "il ne figure meme pas parmi les machines capables")

# ── et la dispense d'inventaire ne le sauve pas non plus ────────────────
# Sans carte, « il peut telecharger le modele sur son disque » ne veut plus
# rien dire : il ne le fera tourner nulle part.
S.manquants = lambda cle, ident=None: ["un_fichier.safetensors"] if ident != "pc" else []
dit("local" not in [x["id"] for x in S.noeuds_pour(CLE)],
    "un moteur absent partout ne le fait pas revenir dans la liste",
    ", ".join(x["id"] for x in S.noeuds_pour(CLE)) or "aucune")
S.manquants = lambda cle, ident=None: []

# ── la tolerance RAM reste entiere pour une VRAIE carte ─────────────────
poser(vram_studio=0.0)
# Les paliers sont 64 / 32 / 16 Go de RAM pour 5 / 3,5 / 2 Go de tolerance.
# 63,8 Go tombent donc dans le palier des 32, pas dans celui des 64 : c'est mon
# calcul qui etait faux, pas le code, et le banc l'a dit avant moi.
dit(S._vram_utile("pc") == 14.5, "11 Go de carte et 63,8 de RAM font 14,5 utiles",
    f"{S._vram_utile('pc')} Go")
dit(S._vram_utile("zima") == 7.9, "5,9 Go et 23,4 de RAM en font 7,9",
    f"{S._vram_utile('zima')} Go")

# ── la charge passe avant la taille ─────────────────────────────────────
poser(vram_studio=0.0)
# charge_noeud compte les taches EN VOL qui VISENT la machine, et lit le noeud
# sur TACHES et non sur EN_VOL : c'est l'intention, posee bien avant le verrou.
S.EN_VOL["t1"] = {}
S.TACHES["t1"] = {"noeud": "pc"}
choisi = S.choisir_noeud(CLE)
dit(choisi is not None and choisi["id"] == "zima",
    "une carte libre passe devant une plus grosse deja visee",
    str(choisi and choisi["id"]))

# ── chaque garde tient SEULE ────────────────────────────────────────────
# Les deux corrections se recouvrent : « pas de tolerance sans carte » suffit
# a ecarter le studio, donc retirer « pas de carte, pas de rendu » ne changeait
# rien et le cas ne mesurait RIEN. banc_mutations me l'a dit, une seconde fois
# et pour la meme raison. On remet donc le defaut d'origine — la tolerance RAM
# accordee sans carte — et l'on verifie que la seconde garde tient a elle
# seule. C'est un calcul, il rebougera un jour.
_vrai_vram = S._vram_utile
S._vram_utile = lambda i: ((S.ETAT_NOEUDS.get(i) or {}).get("vram") or 0)     + S.tolerance_ram((S.ETAT_NOEUDS.get(i) or {}).get("ram") or 0)
poser(vram_studio=0.0, ram_studio=64.0)
dit(S._vram_utile("local") == 5.0,
    "le defaut d'origine remis : le studio se croit une carte de 5 Go",
    f"{S._vram_utile('local')} Go")
dit("local" not in [x["id"] for x in S.noeuds_pour(CLE)],
    "mais « pas de carte, pas de rendu » l'ecarte quand meme",
    ", ".join(x["id"] for x in S.noeuds_pour(CLE)) or "aucune")
S._vram_utile = _vrai_vram

# ── LE RENDU PREND LA PLUS PETITE QUI FAIT L'AFFAIRE ────────────────────
# Regle de l'utilisateur, qui INVERSE celle d'avant : « si rendu, prendre la
# plus petite possible (disponible) pour faire le rendu ». Ce qu'on achete est
# la grosse carte laissee libre pour la suite.
poser(vram_studio=0.0)
choisi = S.choisir_noeud(CLE)
dit(choisi is not None and choisi["id"] == "zima",
    "a cartes libres, le rendu prend la PLUS PETITE qui tient",
    str(choisi and choisi["id"]))

# ── L'ANALYSE PREND LA PLUS GROSSE LIBRE ────────────────────────────────
# L'autre moitie de la regle, et l'autre inversion : « si analyse, prendre la
# plus grosse (libre) pour l'analyse (rapide) ». L'ancien raisonnement
# supposait que l'analyse et le rendu se disputent la carte pendant le meme
# temps ; une analyse dure quelques secondes, un rendu des minutes.
S.OLLAMAS[:] = ["http://pc.local:11434", "http://nas.local:11434"]
for url, ident in (("http://pc.local:11434", "pc"),
                   ("http://nas.local:11434", "zima")):
    S._CERVEAUX[url] = {"quand": S.time.time(), "noeud": ident,
                        "modeles": [{"name": "qwen2.5vl:7b", "size": 5_970_000_000,
                                     "capabilities": ["vision", "completion"]}]}
ordre = [i for _, i in S.cerveaux_utilisables()]
dit(ordre[:1] == ["pc"], "a cartes libres, l'analyse prend la PLUS GROSSE",
    ", ".join(ordre))

# ── LE MODELE EMPRUNTE SUIT LA MEME REGLE ───────────────────────────────
# Il y a DEUX chemins d'analyse : l'Ollama en direct (cerveaux_utilisables) et
# le modele emprunte a une machine par son agent (noeuds_a_llm). 2d654ec avait
# redresse le premier et oublie le second — deux regles opposees dans le meme
# fichier, releve en relisant la documentation et non par un banc. C'est le
# meme travail : il n'a aucune raison de suivre deux regles.
poser(vram_studio=0.0)
for i in ("pc", "zima"):
    S.ETAT_NOEUDS[i]["llm"] = True
dit(S.noeuds_a_llm()[:1] == ["pc"],
    "le modele emprunte part lui aussi sur la PLUS GROSSE",
    ", ".join(S.noeuds_a_llm()))
S.verrou_noeud("pc")._tenu = True
dit(S.noeuds_a_llm()[:1] == ["zima"],
    "et la carte libre passe toujours devant la grosse occupee",
    ", ".join(S.noeuds_a_llm()))
S.verrou_noeud("pc")._tenu = False

# ── LE STUDIO EST UN NOEUD COMME LES AUTRES ─────────────────────────────
# « Si le studio a un noeud (llm + comfy), il est considere comme un noeud
# comme les autres avec ses caracteristiques. » Il ne passe donc plus devant
# personne : avec une carte de 24 Go il PERD le rendu — il est le plus gros —
# et il gagne l'analyse, pour la meme raison.
poser(vram_studio=24.0)
choisi = S.choisir_noeud(CLE)
dit(choisi is not None and choisi["id"] != "local",
    "avec la plus grosse carte, le studio ne prend PAS le rendu",
    str(choisi and choisi["id"]))
choisi = S.choisir_noeud(CLE, viser="grosse")
dit(choisi is not None and choisi["id"] == "local",
    "et il le prend quand c'est la grosse carte qu'on veut",
    str(choisi and choisi["id"]))

# ── LE POUCE EN BAS : la grosse carte, meme occupee ─────────────────────
# « Si l'utilisateur signale pas bien fait, rendu sur grosse carte, attendre
# s'il le faut. » La choisir parmi les moins chargees seulement, c'est
# retomber sur la petite des qu'un rendu vise la grosse — exactement ce que
# l'escalade cherche a eviter.
poser(vram_studio=0.0)
S.EN_VOL["t1"] = {}
S.TACHES["t1"] = {"noeud": "pc"}
choisi = S.choisir_noeud(CLE, viser="grosse")
dit(choisi is not None and choisi["id"] == "pc",
    "l'escalade prend la grosse carte meme si un rendu la vise deja",
    str(choisi and choisi["id"]))

# ── LE DEBORDEMENT S'APPREND, il ne se devine pas ───────────────────────
# « Le 3, mais il faut le temps d'apprendre, donc le 2/1 en fonction de ce
# qu'il apprendra au fur et a mesure. » Sans mesure, on reste sur la carte qui
# TIENT ; des qu'on sait ce que le debordement coute, on descend sur la PLUS
# PETITE carte qui passe le seuil.
#
# ET NON « d'un cran », qui etait ecrit ici et qui decrit un autre code : le tri
# de choisir_noeud est par VRAM CROISSANTE et l'on prend la PREMIERE acceptable.
# C'est celui-ci qui a raison, pour la raison meme de la regle — ce qu'on achete
# en debordant, c'est de la carte laissee libre, et s'arreter au premier cran
# quand deux crans passent le seuil en achete moins. Le seuil, lui, protege
# chaque candidate separement : debordement_acceptable compare TOUJOURS a la
# carte qui tient, jamais a la voisine du dessus, donc il n'y a pas d'escalier
# ou l'on gagnerait 1,5 fois a chaque marche.
poser(vram_studio=0.0, vram_zima=0.4)      # zima ne tient plus le moteur
dit(S.debordement_acceptable("zima", "pc", CLE) is None,
    "sans mesure, on ne sait pas — et on ne devine pas")
choisi = S.choisir_noeud(CLE)
dit(choisi is not None and choisi["id"] == "pc",
    "donc le rendu reste sur la carte qui tient", str(choisi and choisi["id"]))

S.CONVERSATIONS.clear()
S.CONVERSATIONS["c1"] = {"id": "c1", "titre": "banc", "tours": [
    {"id": f"t{n}", "noeud": i, "modele": CLE, "taille": None, "secondes": sec,
     "etat": "fini"}
    for n, (i, sec) in enumerate([("zima", 70), ("zima", 72), ("zima", 74),
                                  ("pc", 60), ("pc", 62), ("pc", 64)])]}
S._DUREES["quand"] = 0.0
dit(S.debordement_acceptable("zima", "pc", CLE) is True,
    "72 s en debordant contre 62 sur la grosse : ca vaut la peine")
choisi = S.choisir_noeud(CLE)
dit(choisi is not None and choisi["id"] == "zima",
    "et le rendu descend sur la petite, la grosse reste libre",
    str(choisi and choisi["id"]))

S.CONVERSATIONS["c1"]["tours"] = [
    {"id": f"t{n}", "noeud": i, "modele": CLE, "taille": None, "secondes": sec,
     "etat": "fini"}
    for n, (i, sec) in enumerate([("zima", 400), ("zima", 410), ("zima", 420),
                                  ("pc", 60), ("pc", 62), ("pc", 64)])]
S._DUREES["quand"] = 0.0
dit(S.debordement_acceptable("zima", "pc", CLE) is False,
    "410 s contre 62, en revanche, on paie deux fois")
choisi = S.choisir_noeud(CLE)
dit(choisi is not None and choisi["id"] == "pc",
    "et le rendu remonte sur celle qui tient", str(choisi and choisi["id"]))

# ── DEUX MEDIANES QUI NE SE COMPARENT PAS ───────────────────────────────
# duree_typique replie de (machine, moteur, taille) sur (moteur) : pratique
# pour AFFICHER un devis, faux pour COMPARER deux machines. La petite carte qui
# n'a jamais rendu ce moteur — par definition, la premiere fois — heritait des
# chiffres de la GROSSE, et l'on concluait que le debordement ne coutait rien.
# Le tout premier debordement etait donc TOUJOURS autorise, sur la foi des
# mesures de celle qu'on cherchait a epargner.
poser(vram_studio=0.0, vram_zima=0.4)
S.CONVERSATIONS.clear()
S.CONVERSATIONS["c1"] = {"id": "c1", "titre": "banc", "tours": [
    {"id": f"t{n}", "noeud": "pc", "modele": CLE, "taille": None,
     "secondes": sec, "etat": "fini"}
    for n, sec in enumerate([60, 62, 64])]}      # zima n'a JAMAIS rendu
S._DUREES["quand"] = 0.0
dit(S.duree_typique("zima", CLE, exact=True)[0] is None,
    "sans mesure sur zima, on ne lui prete pas celles du pc",
    str(S.duree_typique("zima", CLE, exact=True)))
dit(S.debordement_acceptable("zima", "pc", CLE) is None,
    "donc on ne sait pas si le debordement vaut la peine")
choisi = S.choisir_noeud(CLE)
dit(choisi is not None and choisi["id"] == "pc",
    "et le rendu reste sur la carte qui tient", str(choisi and choisi["id"]))

# ── QUAND PERSONNE NE TIENT LE MOTEUR ───────────────────────────────────
# Elles debordent toutes, et la plus grosse deborde le moins. Prendre la plus
# petite « par principe » choisissait la pire carte, sans aucune mesure — une
# regression franche sur le comportement d'avant.
LOURD = max(S.CATALOGUE, key=lambda c: S.CATALOGUE[c].get("vram", 0) or 0)
poser(vram_studio=0.0, vram_pc=25.0, vram_zima=22.0)
dit(not any(S.tient_vraiment(LOURD, i) for i in ("pc", "zima")),
    f"aucune carte ne tient {LOURD} sans deborder")
choisi = S.choisir_noeud(LOURD)
dit(choisi is not None and choisi["id"] == "pc",
    "le rendu part sur la plus GROSSE : elle deborde le moins",
    str(choisi and choisi["id"]))

# ── et le mot dit la verite dans les deux cas ───────────────────────────
poser(vram_studio=0.0)
dit(S._mot_local() == "un modele du parc",
    "sans carte, on ne parle plus de « modele local »", S._mot_local())
poser(vram_studio=24.0)
dit(S._mot_local() == "le modele local",
    "avec une carte, le mot reste juste", S._mot_local())

# ── L'ANALYSE PASSE DEVANT LE RENDU, JAMAIS EN PLEIN RENDU ──────────────
# « Une analyse peut passer devant un rendu si plusieurs demandes en meme
# temps (sans couper un rendu deja en cours). » Les deux moities comptent :
# asyncio.Lock servait dans l'ordre d'arrivee, donc une analyse de trois
# secondes patientait derriere deux rendus de quatre minutes — huit minutes
# sans que rien ne parte, pour une demande que le studio n'avait pas lue.
async def _priorite():
    v = S.VerrouCarte()
    servis = []

    async def demander(nom, prioritaire):
        await v.acquire(prioritaire=prioritaire)
        servis.append(nom)
        v.release()

    await v.acquire()                      # un rendu tient deja la carte
    taches = [asyncio.create_task(demander("rendu 1", False))]
    await asyncio.sleep(0)
    taches.append(asyncio.create_task(demander("analyse", True)))
    taches.append(asyncio.create_task(demander("rendu 2", False)))
    await asyncio.sleep(0)
    dit(servis == [], "le travail en cours n'est pas coupe : personne n'est servi",
        ", ".join(servis) or "personne")
    v.release()                            # le rendu en cours rend la carte
    await asyncio.gather(*taches)
    dit(servis == ["analyse", "rendu 1", "rendu 2"],
        "puis l'analyse passe devant, et les rendus gardent leur ordre",
        " puis ".join(servis))

    # LA FAMINE. « Les analyses d'une demande sont en nombre borne » bornait UNE
    # demande, pas le flux : trois travailleurs qui enchainent leurs analyses, et
    # le rendu etait servi 61e sur 61. Passe ATTENTE_MAX_RENDU, le rendu le plus
    # ancien cesse d'etre double.
    v3 = S.VerrouCarte()
    servis3 = []

    async def prendre(nom, prioritaire):
        await v3.acquire(prioritaire=prioritaire)
        servis3.append(nom)
        v3.release()

    await v3.acquire()
    lent = asyncio.create_task(prendre("rendu", False))
    await asyncio.sleep(0)
    # Le rendu attend depuis plus longtemps que le plancher : on vieillit son
    # entree a la main plutot que d'immobiliser le banc deux minutes.
    v3._attente[1][0] = (v3._attente[1][0][0],
                         S.time.time() - S.ATTENTE_MAX_RENDU - 1)
    flot = [asyncio.create_task(prendre(f"analyse {n}", True)) for n in range(3)]
    await asyncio.sleep(0)
    v3.release()
    await asyncio.gather(lent, *flot)
    dit(servis3[0] == "rendu",
        "un rendu qui a trop attendu cesse d'etre double par les analyses",
        " puis ".join(servis3))

    # ET IL PREND UN TOUR, IL NE PREND PAS LA MAIN. Le renversement
    # s'entretenait tout seul : une fois le seuil franchi, la nouvelle tete de
    # la file des rendus a forcement attendu longtemps elle aussi, donc la
    # condition restait vraie et TOUTE la file des rendus passait avant TOUTE
    # celle des analyses. Mesure d'une relecture adverse : trois rendus de
    # quatre minutes en file, et le message qu'on vient de taper attend douze
    # minutes avant d'etre seulement lu — le symptome exact que cette classe
    # existe pour empecher. « Cesse d'etre double » se lit au singulier.
    #
    # Le cas au-dessus ne peut pas le voir : avec UN seul rendu en file, il n'y
    # a pas de seconde tete a laisser passer, et le defaut est invisible. Il en
    # faut deux.
    v4 = S.VerrouCarte()
    servis4 = []

    async def prendre4(nom, prioritaire):
        await v4.acquire(prioritaire=prioritaire)
        servis4.append(nom)
        v4.release()

    await v4.acquire()
    lents = []
    for n in (1, 2):
        lents.append(asyncio.create_task(prendre4(f"rendu {n}", False)))
        await asyncio.sleep(0)
    # Les DEUX rendus attendent depuis plus longtemps que le plancher : on les
    # vieillit a la main plutot que d'immobiliser le banc quatre minutes.
    v4._attente[1][:] = [(p, S.time.time() - S.ATTENTE_MAX_RENDU - 1)
                         for p, _ in v4._attente[1]]
    flot4 = []
    for n in (1, 2):
        flot4.append(asyncio.create_task(prendre4(f"analyse {n}", True)))
        await asyncio.sleep(0)
    v4.release()
    await asyncio.gather(*lents, *flot4)
    dit(servis4 == ["rendu 1", "analyse 1", "rendu 2", "analyse 2"],
        "un rendu qui a trop attendu prend UN tour, pas la main",
        " puis ".join(servis4))

    # ── LE GARDE-FOU DU VERROU ──────────────────────────────────────────
    # Le cas rejoue par une relecture adverse, et que « if not _tenu: raise »
    # n'aurait PAS attrape : le passage de relais ne repasse jamais par
    # « libre » — _tenu reste vrai d'un porteur au suivant, pour qu'un nouveau
    # venu ne se glisse pas entre les deux — donc « est-elle tenue ? » ne
    # distingue pas le second release() de A du premier de B.
    #
    # A tient, B et C attendent, A relache DEUX fois. Sans le drapeau _en_vol,
    # le second relachement sert C : deux taches calculent sur les memes
    # gigaoctets, en silence et sans retour.
    lignes = []
    _vrai_journal = S.journal

    def journal_espion(tid, msg, **extra):
        lignes.append(msg)
        return _vrai_journal(tid, msg, **extra)

    S.journal = journal_espion
    try:
        v7 = S.VerrouCarte()
        await v7.acquire()                      # A tient
        b = asyncio.create_task(v7.acquire())   # B attend
        await asyncio.sleep(0)
        c = asyncio.create_task(v7.acquire())   # C attend derriere lui
        await asyncio.sleep(0)
        v7.release()                            # A rend : le relais part vers B
        dit(v7._en_vol and not b.done(),
            "le relais est en vol vers B, qui ne s'est pas encore reveille",
            f"en_vol={v7._en_vol}")
        v7.release()                            # LE RELEASE() DE TROP
        # On laisse les deux attentes se reveiller avant de compter : la
        # promesse resolue ne suffit pas, c'est la TACHE qui doit avoir repris
        # la main pour qu'on puisse dire qu'elle tient la carte. Sans ce tour de
        # boucle, « C n'est pas servi » etait vrai meme quand il venait de
        # l'etre, et le cas passait sur un depot ou le garde-fou n'existe pas.
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        dit(not c.done(),
            "un release() de trop ne donne pas la carte a un second titulaire",
            "C est servi pendant que B calcule" if c.done() else "C attend")
        # La fonction d'ou part le relachement de trop, et non un simple
        # « quelque chose a mal tourne » : sans elle, la faute est muette dans
        # un fichier de onze mille lignes.
        dit(any("GARDE-FOU" in l and "_priorite:" in l for l in lignes),
            "et il le dit au lieu de se taire — la ligne nomme le site fautif",
            next((l[-100:] for l in lignes if "GARDE-FOU" in l), "rien de dit"))
        # Et la carte n'est pas perdue pour autant : B se reveille, rend, C est
        # servi. Ne rien faire repare ; lever aurait remplace le diagnostic.
        await b
        v7.release()
        await asyncio.sleep(0)
        dit(c.done(), "puis B rend la carte, et C est servi : rien n'est perdu",
            "servi" if c.done() else "toujours en attente")
        await c
        v7.release()

        # UNE CARTE QUE PERSONNE NE TENAIT. L'autre moitie du garde-fou : ici
        # « not _tenu » suffit, et ce qui repare est encore de NE RIEN FAIRE —
        # servir un attendant donnerait la carte a quelqu'un qui ne l'a pas
        # demandee, lever remplacerait le vrai diagnostic dans un finally.
        del lignes[:]
        v8 = S.VerrouCarte()
        v8.release()
        await v8.acquire()
        dit(v8.locked() and any("GARDE-FOU" in l for l in lignes),
            "une carte que personne ne tenait reste libre, et se reprend "
            "normalement apres",
            f"tenue={v8.locked()}, dit={any('GARDE-FOU' in l for l in lignes)}")
        v8.release()
    finally:
        S.journal = _vrai_journal

    # Une attente annulee ne doit pas emporter la carte avec elle : c'est le
    # cas d'un wait_for qui expire a la seconde ou le verrou se libere.
    v2 = S.VerrouCarte()
    await v2.acquire()
    perdue = asyncio.create_task(v2.acquire())
    await asyncio.sleep(0)
    perdue.cancel()
    try:
        await perdue
    except asyncio.CancelledError:
        pass
    v2.release()
    dit(not v2.locked(), "une attente annulee ne bloque pas la carte")
    await v2.acquire()
    dit(v2.locked(), "et la carte se reprend normalement apres")
    v2.release()

    # LE RELAIS DEJA RECU, ET L'ATTENTE ANNULEE QUAND MEME. Le cas ci-dessus
    # dit dans son commentaire qu'il joue « le wait_for qui expire a la seconde
    # ou le verrou se libere » ; il n'en joue rien. Il annule pendant que la
    # promesse est ENCORE DANS LA FILE, donc il n'exerce que le « remove » —
    # et son assertion passerait meme si le except ne faisait rien du tout,
    # puisque la carte n'a jamais quitte son porteur. La branche
    # « elif not promesse.cancelled() » n'etait eprouvee par rien, alors que
    # c'est la SEULE qui puisse fermer une machine pour de bon : la carte y a
    # deja ete donnee, et personne ne reviendra la rendre.
    #
    # On la force sans course et sans sommeil : release() resout la promesse et
    # leve _en_vol, puis cancel() arrive avant que la tache n'ait repris la
    # main. La promesse porte alors un RESULTAT — elle n'est pas cancelled() —
    # et elle a quitte la file : c'est mot pour mot l'entree de la branche.
    v5 = S.VerrouCarte()
    await v5.acquire()
    recevante = asyncio.create_task(v5.acquire())
    await asyncio.sleep(0)
    v5.release()                     # le relais part vers « recevante »
    dit(not v5._attente[1] and v5._en_vol,
        "le relais est bien EN VOL vers l'attente qu'on va annuler",
        f"file={len(v5._attente[1])}, en_vol={v5._en_vol}")
    recevante.cancel()
    try:
        await recevante
    except asyncio.CancelledError:
        pass
    # Sans la branche, _tenu et _en_vol restent leves sur une carte que plus
    # personne ne tient : la machine est fermee pour de bon.
    dit(not v5.locked() and not v5._en_vol,
        "un relais recu par une attente annulee est RENDU, pas emporte",
        f"tenue={v5.locked()}, en_vol={v5._en_vol}")

    # Et le relais ne se perd pas non plus : celui qui attendait derriere est
    # servi. Sans la branche, il attendrait pour toujours — c'est la meme
    # panne vue du cote de la file plutot que du cote de la carte.
    v6 = S.VerrouCarte()
    await v6.acquire()
    partante = asyncio.create_task(v6.acquire())
    await asyncio.sleep(0)
    suivante = asyncio.create_task(v6.acquire())
    await asyncio.sleep(0)
    v6.release()                     # le relais part vers « partante »
    partante.cancel()
    try:
        await partante
    except asyncio.CancelledError:
        pass
    dit(suivante.done(), "et le relais passe a celui qui attendait derriere",
        "servi" if suivante.done() else "toujours en attente")
    if suivante.done():
        await suivante
        v6.release()


asyncio.run(_priorite())


# ── LA REPRISE CHOISIT COMME LE PREMIER CHOIX ───────────────────────────
# soumettre_robuste choisissait la machine de reprise avec sa PROPRE copie du
# corps de choisir_noeud, et la copie avait deja diverge trois fois : elle
# filtrait la charge AVANT le natif — l'inverse de choisir_noeud — ignorait
# debordement_acceptable, et son « viser="grosse" » retombait sur la plus petite
# des qu'aucune machine ne tenait le moteur. Une regle ecrite deux fois est une
# regle qu'on corrige une fois sur deux : la correction de la repartition
# n'avait ete posee que sur l'AUTRE appel, celui du bas, atteint seulement quand
# plus aucune machine ne repond.
#
# On appelle donc le VRAI soumettre_robuste et l'on regarde ou il repart. Seule
# la soumission nue et le transfert des entrees sont remplaces : recopier ici la
# regle de reprise ne prouverait rien.
async def _reprise():
    envois = []
    tombee = [""]

    async def faux_soumettre(g, tid, ident=None):
        envois.append(ident)
        if ident == tombee[0]:
            raise S.PanneNoeud("la carte ne repond plus")
        return ([{"filename": "x_00001_.png", "subfolder": "", "type": "output",
                  "noeud": ident}], 1.0)

    async def faux_deplacer(g, ancien, nouveau, tid):
        return g

    _vrai_soumettre, _vrai_deplacer = S.soumettre, S.deplacer_entrees
    S.soumettre, S.deplacer_entrees = faux_soumettre, faux_deplacer
    try:
        # ── « viser=grosse » garde la grosse carte, meme visee ──────────
        # Mesure du defaut : la copie rendait la carte MOYENNE quand on
        # demandait la grosse, parce qu'elle ecartait la grosse au filtre de
        # charge avant de regarder sa taille. C'est le contraire exact de ce que
        # « refaire sur la grosse carte, quitte a l'attendre » promet, et de ce
        # que le journal vient d'annoncer a l'utilisateur.
        poser(vram_studio=0.0)
        S.CONVERSATIONS.clear()
        S._DUREES["quand"] = 0.0
        S.REGISTRE["geante"] = {"id": "geante", "titre": "station (RTX 5090)",
                                "agent": True, "jeton": "z", "pause": None}
        S.ETAT_NOEUDS["geante"] = {"repond": True, "vram": 24.0, "ram": 127.0,
                                   "vu": S.time.time()}
        # Un rendu vise deja la grosse carte : c'est ce qui l'ecartait.
        S.EN_VOL["t1"] = {}
        S.TACHES["t1"] = {"noeud": "geante"}
        S.TACHES["r1"] = {"etapes": [], "noeud": "zima"}
        del envois[:]
        tombee[0] = "zima"
        await S.soumettre_robuste({}, "r1", "zima", CLE, viser="grosse")
        dit(envois[-1:] == ["geante"],
            "la reprise choisit comme le premier choix : viser=grosse garde la "
            "grosse carte", " puis ".join(envois))

        # ── et elle ne descend pas sur une carte ou le moteur ne tient pas ─
        # L'autre moitie de la meme divergence : la copie filtrait la charge
        # AVANT le natif, si bien qu'une carte libre trop petite battait une
        # carte chargee ou le moteur tient. choisir_noeud fait l'inverse — le
        # debordement est un recours, pas un choix par defaut — et il ne
        # l'accorde que sur mesure, qu'on n'a pas ici.
        poser(vram_studio=0.0, vram_zima=0.4)     # zima ne tient plus le moteur
        S.CONVERSATIONS.clear()
        S._DUREES["quand"] = 0.0
        S.REGISTRE["vieille"] = {"id": "vieille", "titre": "portable (GTX 1660)",
                                 "agent": True, "jeton": "w", "pause": None}
        S.ETAT_NOEUDS["vieille"] = {"repond": True, "vram": 8.0, "ram": 15.5,
                                    "vu": S.time.time()}
        dit(not S.tient_vraiment(CLE, "zima") and S.tient_vraiment(CLE, "pc"),
            f"zima ne tient plus {CLE}, le pc si",
            f"zima={S.ETAT_NOEUDS['zima']['vram']} Go")
        # Le pc est deja vise par un rendu, zima est libre : c'est exactement la
        # configuration ou la copie descendait.
        S.EN_VOL["t1"] = {}
        S.TACHES["t1"] = {"noeud": "pc"}
        S.TACHES["r2"] = {"etapes": [], "noeud": "vieille"}
        del envois[:]
        tombee[0] = "vieille"
        dit(S.debordement_acceptable("zima", "pc", CLE) is None,
            "et l'on n'a aucune mesure de ce que le debordement couterait")
        await S.soumettre_robuste({}, "r2", "vieille", CLE, viser="petite")
        dit(envois[-1:] == ["pc"],
            "et la reprise ne descend pas sur une carte ou le moteur ne tient pas",
            " puis ".join(envois))
    finally:
        S.soumettre, S.deplacer_entrees = _vrai_soumettre, _vrai_deplacer


asyncio.run(_reprise())


# ══ RENDRE LA CARTE QUAND PLUS RIEN NE LA DEMANDE ══════════════════════
# « Si rien n'est demande, j'aimerais que les cartes soient liberees au bout de
# X min. » Le studio n'appelle JAMAIS une machine a agent : la consigne descend
# donc dans la REPONSE a l'annonce, et c'est cette route-la qu'on eprouve ici,
# pas une fonction interne — « un banc qui teste un contrat que personne
# n'emprunte ne mesure rien ».
#
# MEFIANCE ENVERS L'ASSERTION CREUSE. La moitie des cas ci-dessous verifient
# qu'AUCUNE consigne ne part : verts parce que rien ne s'est passe, ils ne
# mesureraient rien du tout — un jeton refuse, une route morte, un typo dans le
# nom de la cle les rendraient tous verts a la fois. Chacun exige donc en plus
# le TEMOIN que le battement a bel et bien eu lieu : 200, « ok », l'intervalle
# servi, et l'heure de derniere vue qui a AVANCE.
#
# LE BANC EST NE AVEC LA CORRECTION : il n'y a pas de filet d'avant. Le releve
# du sens inverse est ecrit dans banc_mutations.py, a la tete de LIBERATION.
_A_LA_LIBERATION = all(hasattr(S, n) for n in
                       ("_doit_liberer", "_au_repos", "_horloge_repos",
                        "_tient_quelque_chose", "liberer_noeuds_a_url"))
# ZERO FONCTION VAUT NON, ET EXPLICITEMENT — le meme tour que banc_page.py avec
# web/demarrage.html. Sans ce garde, ce banc MOURRAIT sur un AttributeError
# quand la liberation n'est pas la, et « le banc s'est casse » ne dit rien la
# ou « le banc rougit » dit tout. C'est ce qui rend le sens inverse mesurable.
dit(_A_LA_LIBERATION,
    "le studio sait rendre une carte laissee au repos",
    "presente" if _A_LA_LIBERATION else "la machinerie entiere manque")


class ReqAnnonce:
    """Le minimum qu'attend api_noeud_annonce : un jeton, un corps, une IP."""

    def __init__(self, jeton, corps):
        self.headers = {"X-Jeton": jeton}
        self.cookies = {}
        self.remote = "10.0.0.9"
        self._corps = corps

    async def json(self):
        return self._corps


async def battre(ident, **sup):
    """Un vrai battement, par la vraie route. Rend (reponse, temoin).

    « temoin » est ce qui empeche l'assertion creuse : il dit que le studio a
    REPONDU a ce battement-ci — 200, « ok », la cadence servie — et qu'il a
    note l'heure a laquelle il a vu la machine. Un cas qui verifie l'absence de
    consigne sans lui serait vert sur une route qui refuse tout.
    """
    e = S.ETAT_NOEUDS.setdefault(ident, {})
    vu_avant = e.get("vu") or 0
    # La cle « vu » est ecrite avec time.time() : sans ce recul, deux appels
    # dans la meme milliseconde rendraient le temoin faux sur une route qui a
    # pourtant repondu.
    e["vu"] = vu_avant - 1 if vu_avant else 0
    corps = dict({"carte": "RTX 2080 Ti", "vram": 11.0, "libre": 1.0,
                  "travaux": []}, **sup)
    rep = await S.api_noeud_annonce(ReqAnnonce(S.REGISTRE[ident]["jeton"], corps))
    d = json.loads(rep.text)
    temoin = (rep.status == 200 and d.get("ok") is True
              and d.get("intervalle") == 10
              and (S.ETAT_NOEUDS[ident].get("vu") or 0) > vu_avant - 1)
    return d, temoin


def poser_repos(minutes_de_repos=5.0, repos_min=1):
    """Le parc, plus une machine « pc » oisive depuis un moment."""
    poser()
    S.PREFERENCES["vram_repos_min"] = repos_min
    S.ARMEES.clear()
    S.TRAVAUX.clear()
    S.EN_VOL.clear()
    S.TACHES.clear()
    S.VERROUS_NOEUD.clear()
    e = S.ETAT_NOEUDS["pc"]
    e.update(travaux=[], libre=1.0, repond=True, vu=S.time.time(),
             repos_depuis=S.time.time() - minutes_de_repos * 60)
    for k in ("libere_demande", "libere_avant", "libere_dit",
              "liberation_refusee"):
        e.pop(k, None)


class _FauxPost:
    def __init__(self, statut):
        self.status = statut

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False


APPELS_FREE = []
STATUT_FREE = [200]


class _FausseSession:
    """Le ComfyUI local, sans ComfyUI. Retient ce qu'on lui a POSTe."""

    def __init__(self, *_a, **_k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    def post(self, url, json=None):
        APPELS_FREE.append((url, json))
        return _FauxPost(STATUT_FREE[0])


async def _liberation():
    print("\n  ── rendre la carte quand plus rien ne la demande ──")

    # ── la consigne part, et elle part par l'annonce ────────────────────
    poser_repos()
    d, temoin = await battre("pc")
    dit(temoin and d.get("liberer") is True,
        "au repos, la carte pleine, la consigne descend dans la reponse a "
        "l'annonce", str(d))

    # ── une carte DEJA VIDE ne recoit rien, et le battement a bien eu lieu ──
    # Le seuil vaut 2 Go : au-dessous, il n'y a aucun moteur du catalogue sur
    # la carte, et /free ne rendrait rien.
    poser_repos()
    d, temoin = await battre("pc", libre=10.8)
    dit(temoin and not d.get("liberer"),
        "sur une carte deja vide il ne se passe rien — et le battement a eu lieu",
        f"temoin={temoin}, reponse={d}")

    # ── « libre » ABSENT N'EST PAS UN ZERO ──────────────────────────────
    # L'agent d'avant ce jour n'annonce pas ce champ. Le lire comme un zero
    # ferait croire la carte pleine, donc candidate, a CHAQUE battement et pour
    # toujours — sur la machine precisement trop vieille pour comprendre la
    # consigne.
    poser_repos()
    corps = {"carte": "RTX 2080 Ti", "vram": 11.0, "travaux": []}
    rep = await S.api_noeud_annonce(ReqAnnonce(S.REGISTRE["pc"]["jeton"], corps))
    d = json.loads(rep.text)
    dit(rep.status == 200 and d.get("ok") is True and not d.get("liberer")
        and S.ETAT_NOEUDS["pc"].get("libre") is None,
        "un agent qui ne dit pas sa VRAM libre n'est pas une carte pleine",
        f"libre={S.ETAT_NOEUDS['pc'].get('libre')!r}, reponse={d}")

    # ── le delai se compte, et depuis la FIN DU DERNIER TRAVAIL ─────────
    poser_repos(minutes_de_repos=0.3)
    d, temoin = await battre("pc")
    dit(temoin and not d.get("liberer"),
        "vingt secondes de repos ne suffisent pas quand le reglage en demande "
        "soixante", f"temoin={temoin}")

    poser_repos(minutes_de_repos=5.0)
    d, _ = await battre("pc", travaux=["t1"])
    dit(not d.get("liberer") and not S.ETAT_NOEUDS["pc"]["repos_depuis"],
        "un travail en cours remet le compteur de repos a zero",
        f"repos_depuis={S.ETAT_NOEUDS['pc']['repos_depuis']}")
    d, temoin = await battre("pc")
    dit(temoin and not d.get("liberer"),
        "et le battement suivant repart de zero, il ne rattrape pas le repos "
        "d'avant", f"temoin={temoin}")

    # ── ce qui vise la machine l'empeche, et chaque garde tient SEULE ───
    poser_repos()
    S.TRAVAUX["pc"] = [{"tid": "t1", "graphe": {}}]
    d, temoin = await battre("pc")
    dit(temoin and not d.get("liberer"),
        "un travail depose et pas encore reclame retient la carte")

    poser_repos()
    S.EN_VOL["t1"] = {}
    S.TACHES["t1"] = {"noeud": "pc"}
    d, temoin = await battre("pc")
    dit(temoin and not d.get("liberer"),
        "une demande qui a CHOISI cette machine la retient, avant meme d'avoir "
        "depose son travail")

    poser_repos()
    await S.verrou_noeud("pc").acquire()
    try:
        d, temoin = await battre("pc")
        dit(temoin and not d.get("liberer"),
            "un verrou tenu la retient — l'analyse le prend avant qu'un travail "
            "existe")
    finally:
        S.verrou_noeud("pc").release()

    poser_repos()
    S.ARMEES["t9"] = {"quand": S.time.time(), "depuis": S.time.time(),
                      "jusqua": S.time.time() + 3600, "cle": CLE,
                      "noeuds": ["pc"], "titres": ["PC"]}
    d, temoin = await battre("pc")
    dit(temoin and not d.get("liberer"),
        "et une demande ARMEE qui attend cette machine la retient aussi")
    S.ARMEES.clear()

    # ── LA PAUSE, ELLE, N'EMPECHE RIEN ─────────────────────────────────
    # C'est le cas pour lequel tout ceci existe : « je vais jouer un peu ». Une
    # machine en pause ne recevra pas de travail, donc rien ne viendra
    # reprendre la carte — c'est la que la rendre vaut le plus.
    poser_repos()
    S.REGISTRE["pc"]["pause"] = S.time.time()
    d, temoin = await battre("pc")
    dit(temoin and d.get("liberer") is True,
        "une machine en pause rend sa carte : c'est le cas pour lequel le "
        "reglage existe", str(d))
    S.REGISTRE["pc"]["pause"] = None

    # ── le reglage a zero retablit exactement le studio d'avant ─────────
    poser_repos(repos_min=0)
    d, temoin = await battre("pc")
    dit(temoin and not d.get("liberer"),
        "a zero, plus rien n'est jamais libere")
    S.PREFERENCES["vram_repos_min"] = 1

    # ── UNE SEULE CONSIGNE PAR PERIODE DE REPOS ────────────────────────
    # « Ne pas redemander sans fin » : une fois la consigne envoyee, le studio
    # sait qu'il l'a envoyee. Si la VRAM ne bouge pas, il ne recommence pas.
    poser_repos()
    d1, _ = await battre("pc")
    d2, temoin = await battre("pc")
    dit(d1.get("liberer") is True and temoin and not d2.get("liberer"),
        "la consigne ne part qu'UNE fois, meme si la VRAM n'a pas bouge",
        f"1er={d1.get('liberer')}, 2e={d2.get('liberer')}")
    # ... mais un nouveau travail rouvre le droit a une consigne.
    await battre("pc", travaux=["t2"])
    S.ETAT_NOEUDS["pc"]["repos_depuis"] = S.time.time() - 300
    d3, temoin = await battre("pc")
    dit(temoin and d3.get("liberer") is True,
        "et un travail passe par la rouvre le droit a une nouvelle consigne")

    # ── LA MESURE EST GRATUITE : le battement suivant la donne ──────────
    poser_repos()
    d1, _ = await battre("pc")
    S.ETAT_NOEUDS["pc"]["libere_demande"] = S.time.time() - 10
    sortie = io.StringIO()
    with contextlib.redirect_stdout(sortie):
        await battre("pc", libre=10.9)
    dit(d1.get("liberer") is True and "9.9 Go" in sortie.getvalue(),
        "le battement d'apres dit COMBIEN la carte a rendu, sans rien mesurer "
        "de plus", sortie.getvalue().strip() or "rien ecrit")

    # ── et un agent PERIME n'est pas un ComfyUI qui refuse ─────────────
    # Le cas le plus frequent le jour de la mise a jour : l'agent recoit la
    # consigne et ne la lit pas. Accuser son ComfyUI enverrait chercher au
    # mauvais endroit — et l'empreinte, qu'on a deja, tranche.
    poser_repos()
    d1, _ = await battre("pc", empreinte="ceci-n-est-pas-l-empreinte-servie")
    S.ETAT_NOEUDS["pc"]["libere_demande"] = S.time.time() - 10
    sortie = io.StringIO()
    with contextlib.redirect_stdout(sortie):
        await battre("pc", empreinte="ceci-n-est-pas-l-empreinte-servie")
    dit(d1.get("liberer") is True and "agent est perime" in sortie.getvalue(),
        "une carte qui n'a rien rendu sous un agent perime accuse l'AGENT, pas "
        "ComfyUI", sortie.getvalue().strip()[:90] or "rien ecrit")

    # ── un ComfyUI qui ne connait pas /free : une fois, puis on se tait ─
    poser_repos()
    d1, _ = await battre("pc")
    sortie = io.StringIO()
    with contextlib.redirect_stdout(sortie):
        await battre("pc", libere={"ok": False, "statut": 404})
    dit(d1.get("liberer") is True
        and S.ETAT_NOEUDS["pc"].get("liberation_refusee") == 404
        and "404" in sortie.getvalue(),
        "un ComfyUI qui repond 404 est note, et la raison est ecrite",
        sortie.getvalue().strip()[:90] or "rien ecrit")
    # Et l'on ne redemande plus, meme apres un nouveau cycle de travail.
    await battre("pc", travaux=["t3"])
    S.ETAT_NOEUDS["pc"]["repos_depuis"] = S.time.time() - 300
    sortie = io.StringIO()
    with contextlib.redirect_stdout(sortie):
        d, temoin = await battre("pc")
    dit(temoin and not d.get("liberer") and not sortie.getvalue().strip(),
        "puis on cesse de demander, et l'on cesse aussi de l'ecrire",
        sortie.getvalue().strip()[:90] or "journal muet")
    # Le retour de son ComfyUI rouvre la question : c'est le seul evenement
    # apres lequel un 404 peut avoir cesse d'etre vrai.
    await battre("pc", comfy=False)
    S.ETAT_NOEUDS["pc"]["repos_depuis"] = S.time.time() - 300
    d, temoin = await battre("pc")
    dit(temoin and d.get("liberer") is True
        and not S.ETAT_NOEUDS["pc"].get("liberation_refusee"),
        "et le retour de son ComfyUI rouvre la question — c'est ce qui suit "
        "une mise a jour")

    # ── LE NOEUD LOCAL : meme regle, autre transport ────────────────────
    # Le studio a son adresse, il peut l'appeler lui-meme. Ce qui change n'est
    # pas la decision — c'est la meme fonction — mais le chemin.
    poser_repos()
    S.ETAT_NOEUDS["local"].update(repond=True, vram=24.0, libre=3.0,
                                  travaux=[],
                                  repos_depuis=S.time.time() - 300)
    dit(S._doit_liberer("local"),
        "le noeud local est soumis a la MEME regle, sans exception")
    del APPELS_FREE[:]
    STATUT_FREE[0] = 200
    _vraie_session = S.aiohttp.ClientSession
    S.aiohttp.ClientSession = _FausseSession
    try:
        await S.liberer_noeuds_a_url()
        dit(len(APPELS_FREE) == 1
            and APPELS_FREE[0][0] == "http://127.0.0.1:8188/free"
            and APPELS_FREE[0][1] == {"unload_models": True,
                                      "free_memory": True},
            "et le studio le POSTe lui-meme, avec les DEUX moities du "
            "dechargement", str(APPELS_FREE))
        # Une seule fois, la aussi.
        await S.liberer_noeuds_a_url()
        dit(len(APPELS_FREE) == 1,
            "une seule consigne par repos, du cote local comme de l'autre",
            f"{len(APPELS_FREE)} appel(s)")
        # Et un 404 local ferme la porte pareillement.
        S.ETAT_NOEUDS["local"].update(travaux=["t4"])
        await S.liberer_noeuds_a_url()
        S.ETAT_NOEUDS["local"].update(travaux=[],
                                      repos_depuis=S.time.time() - 300)
        STATUT_FREE[0] = 404
        del APPELS_FREE[:]
        sortie = io.StringIO()
        with contextlib.redirect_stdout(sortie):
            await S.liberer_noeuds_a_url()
        refuse = S.ETAT_NOEUDS["local"].get("liberation_refusee")
        S.ETAT_NOEUDS["local"].update(travaux=["t5"])
        await S.liberer_noeuds_a_url()
        S.ETAT_NOEUDS["local"].update(travaux=[],
                                      repos_depuis=S.time.time() - 300)
        del APPELS_FREE[:]
        await S.liberer_noeuds_a_url()
        dit(refuse == 404 and not APPELS_FREE,
            "un ComfyUI local qui refuse /free n'est plus sollicite",
            f"refus={refuse}, rappels={len(APPELS_FREE)}")
    finally:
        S.aiohttp.ClientSession = _vraie_session

    # LE VEILLEUR L'APPELLE VRAIMENT. Sans cette ligne, tout ce qui precede
    # mesurerait une fonction que personne n'appelle — « sept bancs sont restes
    # verts pendant que les reglages par conversation etaient morts ».
    dit("liberer_noeuds_a_url()" in inspect.getsource(S.veiller_noeuds),
        "et la ronde du veilleur l'appelle a chaque tour")

    # ── ET LA VRAM LIBRE EST ENFIN EXPOSEE ─────────────────────────────
    # Elle arrivait toutes les dix secondes depuis toujours et aucune route ne
    # la rendait : c'est pourtant la seule chose qui permette de VOIR qu'une
    # carte a ete rendue.
    poser_repos()
    await battre("pc", libre=7.5)
    lignes = {x["id"]: x for x in S.machines_connues()}
    dit(lignes["pc"].get("libre") == 7.5,
        "/api/admin/noeuds rend la VRAM libre de chaque machine",
        str(lignes["pc"].get("libre")))
    dit("libre" in lignes["local"],
        "la machine locale comprise — les deux lignes sortent du meme releve")
    S.ETAT_NOEUDS["pc"]["libre"] = None
    dit(S.machines_connues()[1].get("libre") is None,
        "et « on ne sait pas » se rend tel quel, jamais comme un zero")


if _A_LA_LIBERATION:
    asyncio.run(_liberation())

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
for r in rate:
    print("    a regarder :", r)
sys.exit(1 if rate else 0)
