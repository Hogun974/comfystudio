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
    tient, jusqu'a ce qu'on en designe une autre — et cela vaut AUSSI de
    l'autre cote d'un redemarrage, ou la marque du tirage ne survit que sur le
    tour ; c'est le seul endroit ou les deux garanties se croisent, et c'est
    celui qui manquait ;
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
import re
import sys
import tempfile
import time

os.environ["STUDIO_DONNEES"] = tempfile.mkdtemp(prefix="banc_variantes_")
os.environ["STUDIO_AUTH"] = "libre"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serveur as S  # noqa: E402

# La page est lue pour UNE chose : le devis affiche a cote de la barre n'est pas
# un champ de /api/etat, c'est la phrase du journal relue au vol (RE_DEVIS). Ce
# banc peut donc verifier que la phrase du serveur et le releve de la page
# parlent bien du meme rendu — ce qu'aucun des deux ne peut prouver seul.
PAGE = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "web", "index.html"), encoding="utf-8").read()

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
# Les rangs dont la carte refuse le rendu. Le premier tirage y a sa place : son
# echec est precisement le cas que « c'est la premiere qui tient le rang » ne
# savait pas traiter, et qu'aucun scenario n'atteignait — §8 retire une variante
# de la file, jamais la premiere, parce que c'est elle qui lance les autres.
ECHEC = set()
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


def rang_du_tirage(tid):
    """Le rang de ce tirage, retrouve PAR LE BANC et non par le serveur.

    Le faux soumetteur s'en sert pour savoir combien de temps trainer, et il ne
    peut pas appeler marque_variante() : les cas du reveil doivent pouvoir
    rougir sur le serveur d'AVANT cette fonction, et un banc qui leve
    AttributeError ne rougit pas, il se casse. Il relit donc lui-meme la tache
    puis le tour — apres un reveil, reprendre_file() reconstruit TACHES sans la
    marque et seul le tour, ecrit sur le disque, la porte encore. Sans ce repli,
    tous les tirages repris valaient « rang 1 » pour LENT et l'on ne pouvait
    plus faire finir un groupe dans le desordre apres un redemarrage — donc pas
    d'ordre d'arrivee a opposer a l'ordre des rangs.
    """
    m = (S.TACHES.get(tid) or {}).get("variantes")
    if not m:
        m = next((t.get("variantes") for t in tours()
                  if t.get("id") == tid and t.get("variantes")), None)
    return (m or {}).get("rang", 1)


# « viser » suit la vraie signature : soumettre_robuste le recoit depuis
# executer pour que la reprise sur une autre machine garde l'escalade du
# bouton « refaire sur la grosse carte ». Sans ce parametre ici, le banc
# mourait sur un TypeError au lieu de mesurer quoi que ce soit.
async def faux_soumettre(g, tid, ident, cle, patience=1800,
                         viser="petite", taille=None):
    GRAPHES.append((tid, ident, copy.deepcopy(g)))
    # Le premier tirage traine expres dans certains scenarios : c'est ainsi
    # qu'on montre que « l'image courante » ne se joue pas a la course.
    rang = rang_du_tirage(tid)
    if rang in ECHEC:
        # Une carte qui lache en plein rendu : le tour part en erreur, et le
        # groupe doit continuer a designer une image.
        raise RuntimeError("la carte a lache")
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
    ECHEC.clear()
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


async def reveil():
    """Rejoue un redemarrage : meme fichier de file, meme conversation, le reste
    vide. Rend la conversation RECHARGEE.

    Elle est rendue parce que c'est un autre objet que celui d'avant l'arret :
    garder l'ancien ferait lire un « derniere_sortie » que le studio redemarre
    n'a jamais vu. Le meme instantane peut etre rejoue plusieurs fois — c'est
    ce qui permet d'opposer deux deroulements au meme etat de disque.
    """
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
    return S.CONVERSATIONS["c1"]


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

    # DEUX CHIFFRES, DEUX CHOSES. Le devis pose sur la tache est le compte a
    # rebours de CETTE bulle-la : c'est a lui que la page compare le temps
    # ecoule pour dire « plus long que d'habitude ». Le total du groupe est un
    # autre chiffre. Les deux etaient a l'ecran en meme temps sans que rien ne
    # dise qu'ils ne comptent pas la meme chose — 60 s dans la pastille, 3 min
    # dans le journal, pour un groupe de trois.
    devis_ = (S.TACHES.get(chef) or {}).get("devis") or {}
    dit(devis_.get("secondes") == 60,
        "le devis de la tache compte UN rendu, pas le groupe", str(devis_))
    dit(devis_.get("rendus") == 3 and devis_.get("total_s") == 180,
        "et le cout du groupe est pose a cote, chiffre", str(devis_))
    dit("60 s chacune" in mots(chef),
        "le journal redit le chiffre de la pastille avant de le multiplier",
        mots(chef)[-200:])
    soeurs_ = [t["id"] for t in tours() if t["id"] != chef]
    devis_soeurs = [(S.TACHES.get(s) or {}).get("devis", {}).get("secondes")
                    for s in soeurs_]
    dit(devis_soeurs == [60] * len(soeurs_),
        "les autres tirages promettent le meme rendu : trois bulles, une seule "
        "promesse", str(devis_soeurs))

    # LA PASTILLE EST RELUE DANS LE TEXTE. /api/etat sert bien un champ
    # « devis », mais la page ne le lit pas : elle cherche la phrase du journal.
    # C'est donc cette phrase qui doit dire un rendu — et la ligne du groupe ne
    # doit surtout pas s'y substituer, sinon le compte a rebours de la bulle se
    # trompe de trois rendus.
    # Le releve tolere le reformatage, et l'absence est un ECHEC. L'ancien
    # « const RE_DEVIS = /(.+?)/([a-z]*); » exigeait une espace unique et une
    # seule ligne, et son absence n'imprimait qu'une remarque. Scenario rejoue :
    # la declaration coupee en deux lignes (« const RE_DEVIS = » puis le motif
    # au retour a la ligne, reflexe banal quand la ligne s'allonge) ET la phrase
    # du serveur passee de « compte » a « prevois » — le banc rendait 93
    # verifications, 0 echouee, en annonçant le couplage disparu alors qu'il
    # etait intact et la pastille du devis morte. L'echappatoire portait sur
    # l'orthographe de la declaration, pas sur l'absence du couplage.
    # \s* partout ou JS tolere du blanc ; « . » sans DOTALL pour le corps, car
    # un litteral d'expression reguliere JS ne peut pas contenir de retour a la
    # ligne — l'elargir ferait avaler la moitie du fichier au premier « / ».
    # Zero occurrence compte comme un NON, meme doctrine que les ancres
    # perimees de banc_mutations.py : une verification qui ne mesure plus rien
    # et se compte verte ment deux fois. Plusieurs occurrences valent refus
    # aussi — on ne saurait plus quel motif la page applique. Le cas reste UN
    # cas dans les deux branches : le total du banc ne bouge pas selon qu'on
    # mesure ou non, sinon la disparition se lit comme un simple 93 au lieu
    # de 94, que personne ne remarque.
    releves = re.findall(r"const\s+RE_DEVIS\s*=\s*/(.+?)/([a-z]*)\s*;", PAGE)
    motif = None
    if len(releves) != 1:
        dit(False, "la page releve le rendu, et lui seul : une phrase, pas deux",
            f"RE_DEVIS introuvable dans web/index.html ({len(releves)} "
            "declaration(s)) : ce banc NE MESURE PLUS le couplage page/serveur. "
            "Reparer le releve, ou retirer le cas en meme temps que le couplage")
    else:
        motif = re.compile(releves[0][0], re.I if "i" in releves[0][1] else 0)
        vus = [m for m in (motif.search(e["msg"])
                           for e in S.TACHES[chef]["etapes"]) if m]
        dit(len(vus) == 1 and vus[0].group(1) == "60" and vus[0].group(2) == "s",
            "la page releve le rendu, et lui seul : une phrase, pas deux",
            str([m.group(0) for m in vus]))

    # CE QUE LA PAGE DEVRAIT LIRE. Le champ existe, /api/etat le sert tel quel —
    # la page, elle, relit encore la phrase française. On verifie donc que le
    # champ est irreprochable AU BOUT DE LA ROUTE et pas seulement sur TACHES :
    # un banc qui lit S.TACHES prouve que le serveur calcule, pas que la page
    # peut l'atteindre, et c'est precisement la confusion qui a laisse « les
    # reglages par conversation » morts pendant sept bancs verts.
    st_, corps_ = lire(await S.api_etat(Req(match={"tid": chef})))
    devis_route = (corps_ or {}).get("devis") or {}
    dit(st_ == 200 and devis_route.get("secondes") == 60
        and devis_route.get("mesures") == 3,
        "/api/etat sert le devis en chiffres : c'est CE champ que la page a a lire",
        f"{st_} {devis_route}")
    dit(devis_route.get("rendus") == 3 and devis_route.get("total_s") == 180,
        "et le cout du groupe y est chiffre aussi : plus rien a deduire d'une "
        "phrase", str(devis_route))
    dit(devis_route.get("mot") == "60 s",
        "le champ porte meme le mot a mot de la phrase : la page n'a plus a le "
        "reconstruire", str(devis_route.get("mot")))

    # ══ L'ECART ENTRE LA PHRASE ET LE CHAMP ═════════════════════════════
    # LE DEFAUT QU'ON FERME, ET LE FILET QUI LE RATTRAPERA. Tant que la page
    # relit la phrase, le chiffre qu'elle affiche n'est pas celui que le serveur
    # a mesure — la phrase arrondissait en minutes des 90 s :
    #
    #     mediane =  90 s -> champ 90,  phrase « 2 min », la page lit 120  (+33 %)
    #     mediane = 100 s -> champ 100, phrase « 2 min », la page lit 120  (+20 %)
    #
    # Le seuil des minutes est passe a cinq minutes (DEVIS_EN_SECONDES_JUSQUA) :
    # sous ce seuil la phrase dit la seconde, donc l'ecart est nul, et au-dessus
    # la demi-minute d'arrondi ne pese plus que 9,1 % au pire (330 s annoncees
    # « 6 min »). Ce cas balaie une demi-heure de medianes, avec la PHRASE que le
    # serveur ecrit vraiment et le RELEVE que la page applique vraiment : le jour
    # ou l'un des deux rebouge, il rougit — et il rougira encore le jour ou la
    # page lira le champ, puisque le cas sera devenu sans objet et qu'il faudra
    # le retirer avec le couplage.
    ECART_TOLERE = 0.10
    if motif is None or not devis_route.get("mot"):
        dit(False, "la phrase ne s'ecarte jamais du champ de plus de 10 %",
            "RE_DEVIS ou le mot du devis manquent : l'ecart N'EST PLUS MESURE")
    else:
        gabarit = next((e["msg"] for e in S.TACHES[chef]["etapes"]
                        if motif.search(e["msg"])
                        and devis_route["mot"] in e["msg"]), "")
        pires = []
        for secondes in range(5, 1801, 5):
            # La tournure reste celle du serveur, seul l'arrondi change : on
            # eprouve le chiffre, pas la phrase — qui a deja son cas plus haut.
            phrase = gabarit.replace(devis_route["mot"], S.mot_du_devis(secondes))
            m = motif.search(phrase)
            if not m:
                pires.append((1.0, secondes, phrase))
                continue
            lu = (float(m.group(1).replace(",", "."))
                  * (60 if m.group(2).lower() == "min" else 1))
            pires.append((abs(lu - secondes) / secondes, secondes, phrase))
        pire = max(pires) if gabarit else (1.0, 0, "phrase du devis introuvable")
        dit(pire[0] <= ECART_TOLERE,
            "la phrase ne s'ecarte jamais du champ de plus de 10 %",
            f"pire ecart {pire[0] * 100:.1f} % a {pire[1]} s — « {pire[2]} »")
        dit(all(e == 0.0 for e, s, _ in pires if s < S.DEVIS_EN_SECONDES_JUSQUA),
            "et sous le seuil des minutes elle est EXACTE, pas approchee",
            str(sorted({s for e, s, _ in pires
                        if e and s < S.DEVIS_EN_SECONDES_JUSQUA})[:6]))

    # ET IL NE SURVIT PAS A CE QUI NE LE JUSTIFIE PLUS. La tache garde son
    # identifiant d'une relance a l'autre ; le champ, lui, restait ecrit. Une
    # demande relancee sans rendus comparables — ils ont ete effaces, ou elle
    # repart en brouillon — promettait encore le chiffre de son essai precedent,
    # que rien ne venait plus etayer. La phrase du journal ne ment pas ainsi :
    # elle n'est pas reecrite, et la page n'y trouve rien.
    poser()                                  # plus d'historique : plus de mediane
    S.FILE_ATTENTE = asyncio.Queue()
    S._DUREES["quand"] = 0.0
    st_, corps_ = await poster()
    perime = corps_["id"]
    S.TACHES.setdefault(perime, {})["devis"] = {"secondes": 999, "mesures": 9,
                                                "mot": "999 s"}
    await tourner()
    dit("devis" not in (S.TACHES.get(perime) or {}),
        "sans mediane, le devis d'avant est retire et non laisse la",
        str((S.TACHES.get(perime) or {}).get("devis")))

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

    # QUAND LE PREMIER TIRAGE N'ABOUTIT PAS. « C'est la premiere qui tient le
    # rang » ne disait rien de ce cas-la : aucune variante ne devenait l'image
    # courante, et « agrandis-la » visait en silence l'image d'AVANT le groupe.
    # Le rang 2 finit ici APRES les rangs 3 et 4 : si l'ordre d'arrivee decidait,
    # ce serait la troisieme.
    conv = poser()
    S.FILE_ATTENTE = asyncio.Queue()
    conv["derniere_sortie"] = {"noeud": "pc", "filename": "avant_le_groupe.png",
                               "subfolder": "u/image"}
    ECHEC.add(1)
    LENT.update({2: 0.30, 3: 0.02, 4: 0.05})
    await poster(variantes=4)
    await tourner()
    par_rang = {(t.get("variantes") or {}).get("rang"): t for t in tours()}
    dit(par_rang[1].get("etat") == "erreur",
        "le premier tirage a echoue", str(par_rang[1].get("etat")))
    dit(all(par_rang[r].get("etat") == "fini" for r in (2, 3, 4)),
        "les trois autres ont rendu leur image")
    dit(conv["derniere_sortie"]["filename"] != "avant_le_groupe.png",
        "le groupe designe quand meme une image",
        conv["derniere_sortie"]["filename"])
    dit(conv["derniere_sortie"]["filename"]
        == par_rang[2]["fichiers"][0]["filename"],
        "et c'est le plus petit rang abouti, pas le premier arrive",
        conv["derniere_sortie"]["filename"])

    # UN CHOIX A LA MAIN NE SE REPREND PAS. La troisieme est designee pendant
    # que la premiere calcule encore : celle-ci, en finissant, reprenait la place
    # que l'utilisateur venait de donner a une autre — l'inverse exact de ce que
    # la garde protege.
    conv = poser()
    S.FILE_ATTENTE = asyncio.Queue()
    LENT.update({1: 0.6})
    await poster(variantes=4)
    gens = [asyncio.create_task(S.travailleur()) for _ in range(4)]
    await asyncio.sleep(0.2)
    par_rang = {(t.get("variantes") or {}).get("rang"): t for t in tours()}
    dit(par_rang[3].get("etat") == "fini" and par_rang[1].get("etat") != "fini",
        "la troisieme est rendue, la premiere calcule encore",
        f"{par_rang[1].get('etat')} / {par_rang[3].get('etat')}")
    st, corps = lire(await S.api_variante_choisir(
        Req(corps={"conversation": "c1", "tour": par_rang[3]["id"]})))
    dit(st == 200, "on peut la designer sans attendre le groupe", str(corps))
    await asyncio.wait_for(S.FILE_ATTENTE.join(), timeout=30)
    for g in gens:
        g.cancel()
    await asyncio.gather(*gens, return_exceptions=True)
    # Relus : enregistrer_tour REMPLACE l'entree de la liste, il ne la modifie
    # pas — un tour garde en main pendant le rendu reste « en cours » pour
    # toujours.
    par_rang = {(t.get("variantes") or {}).get("rang"): t for t in tours()}
    dit(par_rang[1].get("etat") == "fini",
        "la premiere a fini apres le choix", str(par_rang[1].get("etat")))
    dit(conv["derniere_sortie"]["filename"]
        == par_rang[3]["fichiers"][0]["filename"],
        "et elle ne reprend pas la place donnee a la troisieme",
        conv["derniere_sortie"]["filename"])

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
    await reveil()
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

    # ══ 9 bis. apres le reveil, c'est encore le RANG qui commande ═══════
    # LE §9 NE REGARDAIT JAMAIS « derniere_sortie ». C'etait le seul scenario de
    # redemarrage du banc, et il eprouvait la file — trois rendus et non cinq,
    # les bonnes graines, un seul plan — sans demander qui, du groupe, devient
    # « l'image courante ». Le §6 pose cette question-la, mais sans redemarrage.
    # Entre les deux, le chemin du reveil n'etait tenu par personne, et le banc
    # est reste vert a 94 sur le defaut que le commit cac8aa7 disait fermer.
    #
    # LA PANNE. variante_tient_le_rang lisait la marque du tirage dans TACHES,
    # que reprendre_file() reconstruit SANS elle — la clef « variantes » de
    # EN_FILE porte tout autre chose, le nombre de tirages restant a lancer,
    # remis a 1 par lancer_variantes. Au reveil la marque etait donc vide, la
    # fonction rendait vrai pour CHAQUE tirage, et l'on retombait sur « le
    # dernier arrive gagne » — le defaut d'avant, plus la reprise silencieuse du
    # clic « celle-ci ». Le tour, lui, porte la marque et il est sur le disque :
    # c'est le repli que marque_variante() est alle chercher.
    #
    # LES DEUX SENS ONT ETE JOUES : sur le serveur d'avant la correction, les
    # deux cas de mesure ci-dessous rougissent (l'image courante est le rang 3,
    # dernier arrive, au lieu du rang 1 ; et le rang 1 reprend en finissant la
    # place donnee au rang 3) ; sur celui d'apres, ils passent. Un cas qu'on n'a
    # pas vu rougir ne mesure rien.
    print("\n  ── apres le reveil, le rang ──")
    poser()
    S.FILE_ATTENTE = asyncio.Queue()
    INSTANTANE["quand"] = "premier rendu"
    await poster(variantes=3)
    await tourner()
    conv = await reveil()
    # LA PREMISSE, PAS LA MESURE. Elle passe des deux cotes de la correction, et
    # c'est bien pour cela qu'elle est ecrite : si la marque cessait de survivre
    # sur le tour, les deux cas suivants ne mesureraient plus le bon defaut et
    # rien ne le dirait — ils rougiraient pour une autre raison que la leur.
    marques = [t.get("variantes") or {} for t in tours()]
    dit(len(marques) == 3 and len({m.get("groupe") for m in marques}) == 1
        and sorted(m.get("rang") for m in marques) == [1, 2, 3],
        "au reveil, chaque tirage retrouve son groupe et son rang", str(marques))

    # L'ORDRE D'ARRIVEE CONTRE L'ORDRE DES RANGS. Ils finissent 2, puis 1, puis
    # 3 : le dernier arrive est le rang 3, c'est lui que « le dernier gagne »
    # designerait, et c'est le rang 1 qui doit tenir la place.
    LENT.update({1: 0.12, 2: 0.02, 3: 0.30})
    await tourner()
    par_rang = {(t.get("variantes") or {}).get("rang"): t for t in tours()}
    dit(sorted(par_rang) == [1, 2, 3]
        and all(par_rang[r].get("etat") == "fini" and par_rang[r].get("fichiers")
                for r in (1, 2, 3)),
        "les trois tirages repris ont rendu leur image",
        str({r: par_rang[r].get("etat") for r in sorted(par_rang)}))
    arrivee = [(t.get("variantes") or {}).get("rang")
               for t in sorted(tours(), key=lambda t: LENT.get(
                   (t.get("variantes") or {}).get("rang", 1), 0.0))]
    dit((conv.get("derniere_sortie") or {}).get("filename")
        == par_rang[1]["fichiers"][0]["filename"],
        "l'image courante reste le plus petit rang abouti, et non le dernier "
        "arrive : un redemarrage ne remet pas le hasard aux commandes",
        f"{(conv.get('derniere_sortie') or {}).get('filename')} — arrivees "
        f"dans l'ordre {arrivee}, rang 1 = "
        f"{par_rang[1]['fichiers'][0]['filename']}")

    # UN CHOIX FAIT A LA MAIN NE SE REPREND PAS APRES UN REDEMARRAGE. Le MEME
    # instantane, rejoue une seconde fois : on clique sur le rang 3 pendant que
    # le rang 1 calcule encore. Le §6 garde ce geste, mais seulement quand le
    # studio n'a pas redemarre entre le clic et la fin du rendu — c'est-a-dire
    # pas dans le cas ou le rendu est long, qui est le seul ou l'on clique.
    conv = await reveil()
    LENT.update({1: 0.6, 2: 0.02, 3: 0.05})
    S.ARRET = False
    gens = [asyncio.create_task(S.travailleur()) for _ in range(4)]
    await asyncio.sleep(0.25)
    par_rang = {(t.get("variantes") or {}).get("rang"): t for t in tours()}
    dit(par_rang[3].get("etat") == "fini" and par_rang[1].get("etat") != "fini",
        "le rang 3 repris est rendu, le rang 1 calcule encore",
        f"{par_rang[1].get('etat')} / {par_rang[3].get('etat')}")
    st, corps = lire(await S.api_variante_choisir(
        Req(corps={"conversation": "c1", "tour": par_rang[3]["id"]})))
    dit(st == 200, "on designe la troisieme sans attendre le groupe", str(corps))
    await asyncio.wait_for(S.FILE_ATTENTE.join(), timeout=30)
    for g in gens:
        g.cancel()
    await asyncio.gather(*gens, return_exceptions=True)
    par_rang = {(t.get("variantes") or {}).get("rang"): t for t in tours()}
    dit(par_rang[1].get("etat") == "fini",
        "le rang 1 a fini apres le choix", str(par_rang[1].get("etat")))
    dit((conv.get("derniere_sortie") or {}).get("filename")
        == par_rang[3]["fichiers"][0]["filename"],
        "et le choix de l'utilisateur tient : le rang 1 ne le defait pas en "
        "finissant, redemarrage ou non",
        str((conv.get("derniere_sortie") or {}).get("filename")))

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

    # LE GESTE EST-IL APPELABLE D'ICI ? POST /api/variante reclame la
    # conversation ET le tour ; la mediatheque servait la premiere et pas le
    # second, si bien que « celle-ci » n'existait que dans le fil — c'est-a-dire
    # partout sauf a l'endroit ou l'on compare justement quatre images
    # indiscernables. On ne verifie pas la presence du champ, on s'en SERT.
    conv = S.CONVERSATIONS["c1"]
    connus = {t["id"] for t in tours()}
    dit(all(f.get("tour") in connus for f in miens),
        "chaque piece dit de quel tour elle sort",
        str([f.get("tour") for f in miens]))
    groupes = {f.get("groupe") for f in miens}
    dit(len(groupes) == 1 and None not in groupes,
        "et a quel groupe ce tour appartient : la grille peut repeindre les "
        "quatre rangees d'un clic", str(groupes))

    # PERSONNE N'A ENCORE DESIGNE. Le fil encadrait deja la premiere — c'est la
    # regle du serveur, le plus petit rang abouti — et la mediatheque n'en
    # marquait AUCUNE, faute de recevoir le groupe. Deux vues, deux reponses.
    par_rang_m = {f["variante"]: f for f in miens}
    marquees = sorted(f["variante"] for f in miens if f.get("choisie"))
    dit(marquees == [1],
        "sans aucun choix humain, la mediatheque marque la premiere — comme le "
        "fil, et non aucune", str(marquees))
    dit(all(f.get("choisie") == S.variante_tient_le_rang(conv, f["tour"])
            for f in miens),
        "et sa reponse est celle que « agrandis-la » suivra, piece par piece",
        str({f["variante"]: f.get("choisie") for f in miens}))
    dit(not any(t.get("choisie") for t in tours()),
        "sans que « choisie » soit pose sur le moindre tour : ce champ-la dit "
        "toujours « un humain a designe »",
        str([t.get("choisie") for t in tours()]))

    # LE CLIC, AVEC EXACTEMENT CE QUE LA MEDIATHEQUE A SERVI. Rien n'est
    # recompose ici : c'est le corps que la grille postera.
    st, corps = lire(await S.api_variante_choisir(
        Req(corps={"conversation": par_rang_m[3]["conversation"],
                   "tour": par_rang_m[3]["tour"]})))
    dit(st == 200, "designer la troisieme depuis la mediatheque repond 200",
        str(corps))
    rep = await S.api_mediatheque(Req())
    miens = [f for f in json.loads(rep.text).get("fichiers") or []
             if f.get("variante") and f.get("groupe") in groupes]
    dit(sorted(f["variante"] for f in miens if f.get("choisie")) == [3],
        "et la marque suit, sur celle-la et sur elle seule",
        str({f["variante"]: f.get("choisie") for f in miens}))
    dit(conv["derniere_sortie"]["filename"]
        == next(t for t in tours()
                if (t.get("variantes") or {}).get("rang") == 3)["fichiers"][0]["filename"],
        "le clic de la grille designe la meme image que celui du fil",
        conv["derniere_sortie"]["filename"])

    print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
    for r in rate:
        print("    a regarder :", r)
    return 1 if rate else 0


if __name__ == "__main__":
    # asyncio.get_event_loop() leve depuis Python 3.14 hors d'une boucle :
    # le banc passait dans le conteneur et echouait sur la machine de
    # celui qui l'ecrit.
    sys.exit(asyncio.run(main()))
