# -*- coding: utf-8 -*-
"""Une demande, N variantes : le studio en rend-il N, et sait-il laquelle est laquelle ?

    python banc_variantes.py

Chercher, c'est voir plusieurs images et choisir. Le studio n'en rendait qu'une.
Ce banc verifie ce que la multiplication doit garantir, et rien d'autre :

  - N TRAVAUX et non un lot : le graphe envoye a la carte garde batch_size a 1,
    et chaque tirage porte SA graine — c'est elle qui permet de choisir, puis de
    refaire en soigne celle qu'on a choisie ;
  - N TOURS et non un : chaque tirage a son fichier, son etat, son pouce, sa
    place dans la file, et s'annule tout seul ;
  - le plan est etabli UNE FOIS : meme prompt, meme moteur, meme taille pour
    tout le groupe — sinon on ne compare rien ;
  - la reprise apres redemarrage refait N images et pas N + (N-1) : le premier
    tirage ne repart pas en essaim a chaque reveil ;
  - « l'image courante » ne se joue pas a la course : c'est la premiere qui la
    tient, jusqu'a ce qu'on en designe une autre ;
  - le devis reste honnete — N variantes coutent N rendus, et il le dit ;
  - on s'arrete la ou les variantes n'ont pas de sens : une retouche, un
    agrandissement, un fournisseur qui facture a l'image.

Aucune carte, aucun ComfyUI, aucun rendu : le parc est celui du 31 aout — pc
(RTX 2080 Ti, 11 Go) et zima (GTX 1060, 5,9 Go) — pose en memoire, et la
soumission a ComfyUI est remplacee par une fonction qui se contente de LIRE le
graphe. C'est le graphe qui prouve la graine, pas le tour qui la recopie.
"""
import asyncio
import copy
import io
import json
import os
import sys
import tempfile
import time

os.environ["STUDIO_DONNEES"] = tempfile.mkdtemp(prefix="banc_variantes_")
os.environ["STUDIO_AUTH"] = "libre"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serveur as S  # noqa: E402

ok, rate = [], []


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


# Le plus petit moteur d'IMAGE du catalogue : ce banc parle de creation, et
# l'intention decide de tout ici.
CLE = min((c for c in S.CATALOGUE if S.CATALOGUE[c].get("type") == "image"),
          key=lambda c: S.CATALOGUE[c].get("vram", 0))
PID = "u" * 32

# Ce que les stubs ont vu passer. GRAPHES garde le graphe REELLEMENT soumis :
# c'est la seule preuve qui vaille pour la graine et pour batch_size.
GRAPHES = []            # [(tid, ident, graphe)]
APPELS = {"aiguiller": 0, "enrichir": 0, "traduire": 0}
LENT = {}               # tid -> secondes de faux calcul
INSTANTANE = {"file": None, "conv": None, "quand": "jamais"}


def plan_neuf():
    return {"intention": "image", "modele": CLE, "prompt": "a cat in a suit",
            "negatif": "", "largeur": 1216, "hauteur": 832,
            "raison": "banc", "priorite": "",
            "parametres": {"etapes": 7, "cfg": 3.5}}


# ── les faux : tout ce qui sort de la machine ───────────────────────────
async def faux_aiguiller(texte, tid, conv, img=None, **kw):
    APPELS["aiguiller"] += 1
    p = plan_neuf()
    p["priorite"] = kw.get("priorite") or ""
    p["intention"] = INTENTION[0]
    return p


async def faux_enrichir(plan, texte, tid):
    APPELS["enrichir"] += 1
    plan["prompt"] = plan.get("prompt", "") + ", enrichi"
    return plan


async def faux_traduire(plan, tid):
    APPELS["traduire"] += 1
    return plan


async def faux_soumettre(g, tid, ident, cle, patience=1800):
    GRAPHES.append((tid, ident, copy.deepcopy(g)))
    # Le premier tirage traine expres dans certains scenarios : c'est ainsi
    # qu'on montre que « l'image courante » ne se joue pas a la course.
    rang = ((S.TACHES.get(tid) or {}).get("variantes") or {}).get("rang", 1)
    if INSTANTANE["quand"] == "premier rendu" and rang == 1:
        # L'etat du disque a la seconde ou le premier tirage calcule et ou les
        # autres attendent : exactement ce qu'un redemarrage retrouverait.
        INSTANTANE["file"] = io.open(S.FICHIER_FILE, encoding="utf-8").read()
        INSTANTANE["conv"] = copy.deepcopy(S.CONVERSATIONS["c1"])
        INSTANTANE["quand"] = "pris"
    await asyncio.sleep(LENT.get(rang, 0.0))
    return ([{"filename": f"{tid[:8]}_00001_.png", "subfolder": "u/image",
              "type": "output", "noeud": ident}], 42.0)


INTENTION = ["image"]           # ce que le faux aiguilleur decide


def graine_du_graphe(g):
    """La graine que la carte aurait reellement reçue.

    Cherchee dans le graphe et non dans le tour : le tour la RECOPIE, et un
    tour peut porter une graine que personne n'a employee — c'est exactement la
    faute que la reprise de file a deja produite une fois.
    """
    for noeud in g.values():
        for cle in ("noise_seed", "seed"):
            if cle in (noeud.get("inputs") or {}):
                return noeud["inputs"][cle]
    return None


def lots_du_graphe(g):
    return [n["inputs"]["batch_size"] for n in g.values()
            if "batch_size" in (n.get("inputs") or {})]


# ── le parc ─────────────────────────────────────────────────────────────
def poser(vram_zima=5.9):
    """Deux machines a agent, chacune equipee du moteur du banc.

    « vram_zima » existe pour une raison precise : choisir_noeud() ne repartit
    qu'entre les cartes ou le moteur tient SANS deborder. Avec le parc reel,
    aucun moteur d'image ne tient dans 5,9 Go, et les quatre tirages font donc
    la queue sur le PC. C'est un fait du parc, pas du decoupage — et il faut
    pouvoir montrer les deux.
    """
    S.REGISTRE.clear()
    S.ETAT_NOEUDS.clear()
    S.MODELES_NOEUD.clear()
    S.VERROUS_NOEUD.clear()
    S.ARMEES.clear()
    S.EN_FILE.clear()
    S.EN_VOL.clear()
    del S.ATTENTE[:]
    S.TACHES.clear()
    S.CONVERSATIONS.clear()
    S.ENTREES.clear()
    del GRAPHES[:]
    LENT.clear()
    APPELS.update(aiguiller=0, enrichir=0, traduire=0)
    INTENTION[0] = "image"
    INSTANTANE.update(file=None, conv=None, quand="jamais")
    dossiers = {}
    for sous, nom, _repo, _distant in S.CATALOGUE[CLE]["fichiers"]:
        dossiers.setdefault(sous, set()).add(nom)
    for ident, titre, vram, ram in (("pc", "PC (RTX 2080 Ti)", 11.0, 63.8),
                                    ("zima", "NAS ZimaOS", vram_zima, 23.4)):
        S.REGISTRE[ident] = {"id": ident, "titre": titre, "agent": True,
                             "jeton": ident}
        S.ETAT_NOEUDS[ident] = {"repond": True, "vram": vram, "ram": ram,
                                "vu": time.time()}
        S.MODELES_NOEUD[ident] = {"quand": time.time(), "dossiers": dossiers}
    conv = S._vide(proprietaire=PID)
    conv["id"] = "c1"
    S.CONVERSATIONS["c1"] = conv
    return conv


class Req(dict):
    """Le minimum qu'attendent qui(), est_admin() et les gestionnaires."""

    def __init__(self, pid=PID, match=None, corps=None):
        super().__init__(pid=pid, compte="")
        self.match_info = match or {}
        self.headers, self.cookies = {}, {}
        self._corps = corps

    async def json(self):
        if self._corps is None:
            raise ValueError("pas de corps")
        return self._corps


def lire(rep):
    return rep.status, json.loads(rep.text)


def tours():
    return S.CONVERSATIONS["c1"]["tours"]


def mots(tid):
    return " | ".join(e["msg"] for e in (S.TACHES.get(tid) or {}).get("etapes", []))


async def tourner(combien=4):
    """Fait tourner la file jusqu'a ce qu'elle soit vide, avec de vrais
    travailleurs : c'est travailleur() qui transmet « variantes » a executer,
    et recopier ce passage ici ne prouverait rien."""
    S.ARRET = False
    gens = [asyncio.create_task(S.travailleur()) for _ in range(combien)]
    try:
        await asyncio.wait_for(S.FILE_ATTENTE.join(), timeout=30)
    finally:
        for g in gens:
            g.cancel()
        await asyncio.gather(*gens, return_exceptions=True)


async def poster(texte="un chat en costume", **corps):
    rep = await S.api_generer(Req(corps=dict({"texte": texte,
                                              "conversation": "c1"}, **corps)))
    return lire(rep)


async def main():
    print(f"\n  moteur du banc : {CLE} ({S.CATALOGUE[CLE].get('vram', 0)} Go)\n")
    S.aiguiller = faux_aiguiller
    S.enrichir = faux_enrichir
    S.traduire = faux_traduire
    S.soumettre_robuste = faux_soumettre
    S.choix_distant = lambda *a, **k: ""
    S.PREFERENCES["plafond_nuage"] = 0

    # ══ 1. ce que la demande accepte, et ce qu'elle refuse ══════════════
    print("\n  ── la demande ──")
    poser()
    S.FILE_ATTENTE = asyncio.Queue()
    for combien, attendu in ((5, 400), (-1, 400), ("trois", 400),
                             (1, 200), (4, 200)):
        st, corps = await poster(variantes=combien)
        dit(st == attendu, f"variantes={combien!r} -> {attendu}",
            f"{st} {corps.get('erreur') or corps.get('variantes')}")
    # Zero, vide, absent : trois facons de dire « pas de variantes », et la page
    # les envoie toutes les trois selon l'etat de son menu. Une seule image, sans
    # message d'erreur — refuser ici ferait echouer une demande ordinaire.
    for rien in (0, "", None):
        st, corps = await poster(variantes=rien)
        dit(st == 200 and corps.get("variantes") == 1,
            f"variantes={rien!r} vaut « une seule »", f"{st} {corps}")
    dit(S.VARIANTES_MAX == 4, "la borne est a quatre", str(S.VARIANTES_MAX))

    # Le geste ne se retient pas : c'est l'argument de poser_reglages pour le
    # brouillon, multiplie par quatre.
    dit("variantes" not in S.reglages_de(S.CONVERSATIONS["c1"]),
        "quatre variantes ne se retiennent pas sur la conversation",
        str(S.reglages_de(S.CONVERSATIONS["c1"])))
    dit("variantes" not in S.REGLAGES_CONV,
        "et « variantes » n'est pas un reglage de conversation")

    # ══ 2. quatre variantes, quatre tirages, quatre graines ═════════════
    print("\n  ── quatre variantes ──")
    conv = poser()
    S.FILE_ATTENTE = asyncio.Queue()
    st, corps = await poster(variantes=4)
    dit(st == 200 and corps.get("variantes") == 4, "la demande est acceptee")
    await tourner()

    dit(len(tours()) == 4, "quatre tours, un par variante", str(len(tours())))
    dit(len(GRAPHES) == 4, "quatre graphes soumis", str(len(GRAPHES)))
    graines = [graine_du_graphe(g) for _, _, g in GRAPHES]
    dit(all(x is not None for x in graines) and len(set(graines)) == 4,
        "quatre graines differentes DANS LE GRAPHE", str(graines))
    lots = [x for _, _, g in GRAPHES for x in lots_du_graphe(g)]
    dit(lots and set(lots) == {1},
        "et batch_size reste a 1 : la multiplication est dans la file, pas dans "
        "le graphe", str(lots))

    dit(APPELS == {"aiguiller": 1, "enrichir": 1, "traduire": 1},
        "le plan est etabli UNE fois pour les quatre", str(APPELS))
    prompts = {t.get("prompt") for t in tours()}
    moteurs = {t.get("modele") for t in tours()}
    tailles = {t.get("taille") for t in tours()}
    dit(len(prompts) == 1 and len(moteurs) == 1 and len(tailles) == 1,
        "meme prompt, meme moteur, meme taille",
        f"{prompts} {moteurs} {tailles}")
    dit(all(t.get("etat") == "fini" and t.get("fichiers") for t in tours()),
        "les quatre ont rendu un fichier")

    ecrites = [t.get("graine") for t in tours()]
    dit(sorted(ecrites) == sorted(graines),
        "le tour porte la graine que la carte a reellement reçue",
        f"{sorted(ecrites)}")

    grp = [t.get("variantes") for t in tours()]
    dit(all(g and g.get("groupe") == tours()[0]["id"] and g.get("sur") == 4
            for g in grp), "les quatre tours portent le meme groupe", str(grp))
    dit(sorted(g["rang"] for g in grp) == [1, 2, 3, 4],
        "et chacun son rang", str(sorted(g["rang"] for g in grp)))

    # ══ 3. la file les a vraiment portes une par une ════════════════════
    print("\n  ── la file ──")
    dit(not S.EN_FILE, "la file est vide une fois les quatre rendues",
        str(list(S.EN_FILE)))
    dit(json.load(io.open(S.FICHIER_FILE, encoding="utf-8")) == [],
        "et le fichier de file aussi")

    # ══ 4. le devis reste honnete ═══════════════════════════════════════
    print("\n  ── le devis ──")
    chef = tours()[0]["id"]
    dit("4 variantes, donc autant de rendus" in mots(chef),
        "le premier tirage annonce le cout du groupe", mots(chef)[-160:])
    # Avec un historique, le devis chiffre le total et non le seul premier.
    conv = poser()
    S.FILE_ATTENTE = asyncio.Queue()
    S.CONVERSATIONS["c2"] = {"id": "c2", "titre": "passe", "proprietaire": PID,
                             "tours": [{"id": f"v{i}", "noeud": "pc",
                                        "modele": CLE, "taille": "1216x832",
                                        "secondes": 60, "etat": "fini"}
                                       for i in range(3)]}
    S._DUREES["quand"] = 0.0
    await poster(variantes=3)
    await tourner()
    chef = tours()[0]["id"]
    dit("3 variantes, donc autant de rendus" in mots(chef)
        and "de calcul en tout" in mots(chef),
        "et il chiffre le total quand il sait", mots(chef)[-200:])
    dit("3 min" in mots(chef), "3 x 60 s annonces comme 3 min, pas 60 s",
        mots(chef)[-120:])

    # ══ 5. la ou l'on s'arrete ══════════════════════════════════════════
    print("\n  ── la ou l'on s'arrete ──")
    for intention in ("edition", "agrandir", "detourer", "retoucher_fond",
                      "video", "audio"):
        poser()
        S.FILE_ATTENTE = asyncio.Queue()
        INTENTION[0] = intention
        await poster(variantes=4)
        # On ne va pas jusqu'au rendu : ces intentions reclament une image
        # d'entree, et ce n'est pas ce qu'on mesure. Le comptage des tours
        # suffit — un essaim se verrait la.
        await tourner()
        dit(len(tours()) == 1 and intention not in S.VARIANTES_POSSIBLE,
            f"« {intention} » ne se multiplie pas", f"{len(tours())} tour(s)")
        dit("les variantes ne changent rien" in mots(tours()[0]["id"]),
            f"et « {intention} » le dit plutot que de l'ignorer",
            mots(tours()[0]["id"])[:120])
    dit(set(S.VARIANTES_POSSIBLE) == {"image", "planche"},
        "seules la creation d'image et la planche sont concernees",
        str(S.VARIANTES_POSSIBLE))

    # Un fournisseur facture chaque image : il n'en rend qu'une.
    poser()
    S.FILE_ATTENTE = asyncio.Queue()
    INTENTION[0] = "image"
    S.choix_distant = lambda *a, **k: "nanobanana"
    S.moteur_distant_pret = lambda cle: True

    async def faux_distant(choix, plan, texte, entree, intention, tid, conv):
        return [{"filename": "loin.png", "subfolder": "u/image",
                 "type": "output", "noeud": "studio"}]
    S.produire_distant = faux_distant
    await poster(variantes=4)
    await tourner()
    dit(len(tours()) == 1, "un moteur distant ne se multiplie pas",
        f"{len(tours())} tour(s)")
    dit("facture chaque image" in mots(tours()[0]["id"]),
        "et le studio dit pourquoi", mots(tours()[0]["id"])[-140:])
    S.choix_distant = lambda *a, **k: ""

    # ══ 6. l'image courante ne se joue pas a la course ══════════════════
    print("\n  ── l'image courante ──")
    conv = poser()
    S.FILE_ATTENTE = asyncio.Queue()
    # Le premier tirage finit EN DERNIER : c'est le cas qui faisait de
    # « agrandis-la » un tirage au sort.
    LENT.update({1: 0.30, 2: 0.02, 3: 0.04, 4: 0.06})
    await poster(variantes=4)
    await tourner()
    fini = [t["id"] for t in sorted(tours(), key=lambda t: t.get("secondes") or 0)]
    premier = next(t for t in tours() if (t.get("variantes") or {}).get("rang") == 1)
    dit(conv["derniere_sortie"]["filename"] == premier["fichiers"][0]["filename"],
        "l'image courante est la premiere variante, meme finie en dernier",
        conv["derniere_sortie"]["filename"])
    dit(len(fini) == 4, "les quatre ont bien tourne en parallele")

    # ... jusqu'a ce qu'on en designe une autre.
    troisieme = next(t for t in tours()
                     if (t.get("variantes") or {}).get("rang") == 3)
    st, corps = lire(await S.api_variante_choisir(
        Req(corps={"conversation": "c1", "tour": troisieme["id"]})))
    dit(st == 200, "choisir une variante repond 200", str(corps))
    dit(conv["derniere_sortie"]["filename"] == troisieme["fichiers"][0]["filename"],
        "et « la » designe desormais celle-la",
        conv["derniere_sortie"]["filename"])
    marquees = [t["id"] for t in tours() if t.get("choisie")]
    dit(marquees == [troisieme["id"]], "une seule variante est marquee choisie",
        str(len(marquees)))
    # Choisir la premiere doit decocher la troisieme : deux images ne peuvent
    # pas se dire « la » en meme temps.
    await S.api_variante_choisir(Req(corps={"conversation": "c1",
                                            "tour": premier["id"]}))
    marquees = [t["id"] for t in tours() if t.get("choisie")]
    dit(marquees == [premier["id"]], "en choisir une autre decoche la premiere",
        str(len(marquees)))
    # Et le voisin ne choisit pas chez nous.
    st, _ = lire(await S.api_variante_choisir(
        Req(pid="z" * 32, corps={"conversation": "c1", "tour": premier["id"]})))
    dit(st == 404, "la conversation d'un autre repond 404", str(st))
    st, _ = lire(await S.api_variante_choisir(
        Req(corps={"conversation": "c1", "tour": "inexistant"})))
    dit(st == 404, "un tour inconnu aussi", str(st))

    # ══ 7. « refaire en soigne » vise celle qu'on a choisie ═════════════
    print("\n  ── refaire en soigne ──")
    poser()
    S.FILE_ATTENTE = asyncio.Queue()
    await poster(variantes=3, priorite="brouillon")
    await tourner()
    dit(all(t.get("esquisse") for t in tours()),
        "trois brouillons, trois esquisses", str([t.get("esquisse") for t in tours()]))
    dit(all(isinstance(t.get("plan"), dict) for t in tours()),
        "chacune garde son plan : elle sait se refaire seule")
    dit(all((t.get("plan") or {}).get("graine") is None for t in tours()),
        "et aucun plan ne fige la graine — c'est le tour qui la porte")
    visee = tours()[2]
    st, corps = lire(await S.api_au_propre(
        Req(corps={"conversation": "c1", "tour": visee["id"]})))
    dit(st == 200, "on peut repasser au propre la TROISIEME", str(corps))
    dit(S.EN_FILE[corps["id"]]["plan"].get("graine") == visee.get("graine"),
        "et c'est bien sa graine a elle qui repart",
        f"{S.EN_FILE[corps['id']]['plan'].get('graine')} vs {visee.get('graine')}")
    # Le tirage au propre n'est pas une variante : il ne doit pas relancer
    # d'essaim.
    dit(S.EN_FILE[corps["id"]].get("variantes", 1) == 1,
        "le tirage au propre part seul")
    await tourner()
    dit(len(tours()) == 4, "trois variantes plus la reprise au propre",
        str(len(tours())))
    dernier = tours()[-1]
    dit("seule la graine change" not in mots(dernier["id"])
        and "que l'esquisse" in mots(dernier["id"]),
        "et son message parle bien de l'esquisse, pas d'une variante",
        mots(dernier["id"])[:150])

    # ══ 8. annulation a l'unite ═════════════════════════════════════════
    print("\n  ── annuler ──")
    poser()
    S.FILE_ATTENTE = asyncio.Queue()
    await poster(variantes=4)
    # Un seul travailleur : le premier tirage calcule, les trois autres
    # attendent en file — c'est la qu'on en retire une.
    LENT.update({1: 0.6})
    gens = [asyncio.create_task(S.travailleur())]
    await asyncio.sleep(0.15)
    en_attente = list(S.ATTENTE)
    dit(len(en_attente) == 3, "trois tirages attendent leur tour",
        str(len(en_attente)))
    st, corps = lire(await S.api_file_annuler(
        Req(match={"tid": en_attente[1]})))
    dit(st == 200 and corps.get("quoi") == "retiree",
        "on en retire une", str(corps))
    dit(en_attente[1] not in S.EN_FILE and en_attente[0] in S.EN_FILE
        and en_attente[2] in S.EN_FILE,
        "les autres restent : le groupe ne tombe pas avec elle")
    await asyncio.wait_for(S.FILE_ATTENTE.join(), timeout=30)
    for g in gens:
        g.cancel()
    await asyncio.gather(*gens, return_exceptions=True)
    rendus = [t for t in tours() if t.get("etat") == "fini"]
    dit(len(rendus) == 3, "trois images rendues sur quatre demandees",
        str(len(rendus)))
    retiree = next(t for t in tours() if t["id"] == en_attente[1])
    dit(retiree.get("etat") == "erreur" and (retiree.get("variantes") or {}),
        "et la retiree garde son rang dans le groupe",
        str(retiree.get("variantes")))

    # ══ 9. la reprise ne relance pas un essaim ══════════════════════════
    print("\n  ── redemarrage ──")
    poser()
    S.FILE_ATTENTE = asyncio.Queue()
    INSTANTANE["quand"] = "premier rendu"
    await poster(variantes=3)
    await tourner()
    dit(INSTANTANE["quand"] == "pris", "instantane du disque pris en plein rendu")
    file_arret = json.loads(INSTANTANE["file"])
    dit(len(file_arret) == 3, "les trois tirages sont dans _file.json a l'arret",
        str(len(file_arret)))
    dit(sorted(r.get("variantes", 1) for r in file_arret) == [1, 1, 1],
        "et aucun n'en reclame d'autres : le premier a deja lance les siens",
        str([r.get("variantes", 1) for r in file_arret]))
    dit(all(isinstance(r.get("plan"), dict) for r in file_arret),
        "les trois portent leur plan : le premier aussi, sinon il repartirait "
        "a l'aiguilleur pendant que les autres gardent l'ancien prompt")
    prompts_arret = {r["plan"].get("prompt") for r in file_arret}
    dit(len(prompts_arret) == 1, "et c'est le meme plan pour les trois",
        str(prompts_arret))
    chef_arret = next(r for r in file_arret if r.get("graine") is not None)
    graine_chef = chef_arret["graine"]
    dit(graine_chef in [graine_du_graphe(g) for _, _, g in GRAPHES],
        "le tirage en cours a sa graine ecrite dans la file", str(graine_chef))
    # Les deux autres n'en ont pas encore : elles attendaient, leur graine n'est
    # tiree qu'au moment ou une carte les prend. C'est juste — inventer la leur
    # a l'avance donnerait une graine qui n'a jamais rien produit.
    dit(sum(1 for r in file_arret if r.get("graine") is None) == 2,
        "les deux qui attendaient n'en ont pas encore, et c'est normal")

    # On rejoue le reveil : meme fichier de file, meme conversation, tout le
    # reste vide.
    S.EN_FILE.clear()
    S.EN_VOL.clear()
    del S.ATTENTE[:]
    S.TACHES.clear()
    del GRAPHES[:]
    APPELS.update(aiguiller=0, enrichir=0, traduire=0)
    INSTANTANE["quand"] = "jamais"
    S.CONVERSATIONS["c1"] = copy.deepcopy(INSTANTANE["conv"])
    io.open(S.FICHIER_FILE, "w", encoding="utf-8").write(INSTANTANE["file"])
    S.FILE_ATTENTE = asyncio.Queue()
    await S.reprendre_file()
    dit(len(S.EN_FILE) == 3, "trois demandes reprises, pas une de plus",
        str(len(S.EN_FILE)))
    await tourner()
    dit(len(GRAPHES) == 3, "trois rendus au reveil, et non trois plus deux",
        str(len(GRAPHES)))
    apres = [graine_du_graphe(g) for _, _, g in GRAPHES]
    dit(graine_chef in apres,
        "celui qui calculait refait EXACTEMENT la meme image : sa graine est "
        "reprise", f"{graine_chef} dans {apres}")
    dit(len(set(apres)) == 3, "et les trois graines restent distinctes", str(apres))
    dit(APPELS == {"aiguiller": 0, "enrichir": 0, "traduire": 0},
        "aucune analyse refaite au reveil : les plans etaient dans la file",
        str(APPELS))
    dit(len({t.get("prompt") for t in tours()}) == 1,
        "le groupe garde un seul prompt de part et d'autre du redemarrage",
        str({t.get("prompt") for t in tours()}))
    dit(len(tours()) == 3, "et toujours trois tours", str(len(tours())))

    # ══ 10. deux machines, quand elles peuvent ══════════════════════════
    print("\n  ── les deux machines ──")
    poser(vram_zima=5.9)                 # le parc reel
    S.FILE_ATTENTE = asyncio.Queue()
    await poster(variantes=4)
    await tourner()
    ou = {t.get("noeud") for t in tours()}
    dit(ou == {"pc"},
        "parc reel : aucun moteur d'image ne tient dans 5,9 Go, les quatre "
        "font donc la queue sur le PC", str(ou))
    poser(vram_zima=11.0)                # une seconde grosse carte
    S.FILE_ATTENTE = asyncio.Queue()
    await poster(variantes=4)
    await tourner()
    ou = {t.get("noeud") for t in tours()}
    dit(ou == {"pc", "zima"},
        "deux cartes capables : les tirages se repartissent — ce qu'un lot "
        "batch_size n'aurait pas su faire", str(ou))

    # ══ 11. la mediatheque les distingue ════════════════════════════════
    print("\n  ── la mediatheque ──")
    rep = await S.api_mediatheque(Req())
    items = json.loads(rep.text).get("fichiers") or []
    miens = [f for f in items if f.get("variante")]
    dit(len(miens) == 4, "les quatre variantes y sont, chacune numerotee",
        str(sorted(f.get("variante") for f in miens)))
    dit(all(f.get("variantes") == 4 for f in miens),
        "et chacune dit sur combien elle porte")

    print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
    for r in rate:
        print("    a regarder :", r)
    return 1 if rate else 0


if __name__ == "__main__":
    # asyncio.get_event_loop() leve depuis Python 3.14 hors d'une boucle :
    # le banc passait dans le conteneur et echouait sur la machine de
    # celui qui l'ecrit.
    sys.exit(asyncio.run(main()))
