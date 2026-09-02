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

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
for r in rate:
    print("    a regarder :", r)
sys.exit(1 if rate else 0)
