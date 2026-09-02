# -*- coding: utf-8 -*-
"""« Refaire sur la grosse carte » refait-il LA MEME demande, et rien d'autre ?

    python banc_refaire.py

POST /api/refaire n'etait eprouve par rien, et c'est la route la plus fragile
du depot : trois defauts d'affilee en deux jours, dont un de surete. Elle
reconstruit un plan a partir d'un tour ecrit il y a peut-etre des semaines,
puis le rejoue sans repasser par l'analyse — donc tout ce que le tour ne porte
pas est perdu en silence, et tout ce que le catalogue a perdu depuis explose en
KeyError.

Ce que ce banc mesure, dans l'ordre de gravite :

  - LA SURETE D'ABORD. Le plan reconstruit garde « classement » : un rendu
    marque explicite ne repart pas chez un fournisseur distant. Les DEUX gardes
    sont eprouvees SEPAREMENT — « modele_impose », qui coupe choix_distant sans
    rien savoir du contenu, et le champ repris, que adulte() lit. La premiere
    suffit a elle seule, et c'est voulu : les tours ecrits avant le 1er
    septembre ne porteront jamais le second.
  - un moteur qui a quitte le catalogue, un rendu confie a un fournisseur : une
    phrase, et non « ERREUR : 'sdxl_vieux' » ni « ERREUR : 'veo' ». Le meme trou
    existait a l'identique dans api_au_propre ; il est eprouve ici aussi.
  - un tour SANS TAILLE rend quand meme une image — les tours d'avant le
    31 aout n'ont pas de champ « taille », et c'etait un KeyError: 'largeur' —
    et le studio ANNONCE la taille qu'il a reprise.
  - le plan garde les paroles, le negatif et la raison : une chanson refaite ne
    se reecrit pas, un negatif ne retombe pas sur le defaut du moteur.
  - un refait qui echoue REND SON BOUTON, et la marque « refait » survit a une
    reecriture du tour d'origine.
  - « ecoule_rendu » ne compte plus l'attente de la carte : c'est le seul
    chiffre comparable au devis, qui est une mediane de rendus.

Aucune carte, aucun ComfyUI, aucun fournisseur : le parc est pose en memoire —
pc (11 Go) et zima (5,9 Go) — et la soumission est remplacee par une fonction
qui se contente de LIRE le graphe. C'est le graphe qui prouve le classement et
le negatif, pas le tour qui les recopie : un tour peut porter un champ que la
carte n'a jamais recu.
"""
import asyncio
import copy
import io
import json
import os
import sys
import tempfile
import time

os.environ["STUDIO_DONNEES"] = tempfile.mkdtemp(prefix="banc_refaire_")
os.environ["STUDIO_AUTH"] = "libre"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serveur as S  # noqa: E402

ok, rate = [], []


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


# LE MOTEUR A BALISE DE SCORE, et non « pony » ecrit en dur. C'est le seul
# genre de moteur ou le classement se VOIT dans le graphe : CLASSEMENT_PONY est
# colle au prompt positif par g_image. Sur tout autre moteur, un classement
# perdu ne laisse aucune trace mesurable, et le cas de surete ne prouverait que
# la recopie d'un champ de dictionnaire.
CLE = next(c for c in S.CATALOGUE
           if "prefixe" in S.CATALOGUE[c] and S.CATALOGUE[c].get("type") == "image")
# Le plus petit moteur d'AUDIO : les paroles n'existent que la.
AUDIO = min((c for c in S.CATALOGUE if S.CATALOGUE[c].get("type") == "audio"),
            key=lambda c: S.CATALOGUE[c].get("vram", 0))
PID = "u" * 32

GRAPHES = []            # [(tid, ident, graphe)] : ce que la carte a VRAIMENT recu
DISTANTS = []           # [(fournisseur, plan)] : ce qui est parti au loin
APPELS = {"paroles": 0, "aiguiller": 0}
ECHEC = {"soumettre": False}


# ── les faux : tout ce qui sort de la machine ───────────────────────────
# LA VRAIE SIGNATURE, ET ELLE BOUGE. « viser » vient de l'escalade du bouton
# « refaire sur la grosse carte », « taille » du plan, pour que la reprise
# compare des durees mesurees sur des rendus comparables. Les deux ont ete
# ajoutes a deux jours d'intervalle, et chaque fois les faux des bancs sont
# morts sur un TypeError AU LIEU DE MESURER — c'est arrive a banc_variantes.py,
# puis ici. Un faux qui ne suit pas la signature ne rate pas un cas : il les
# rate tous, et il ressemble a une panne du studio.
async def faux_soumettre(g, tid, ident, cle, patience=1800, viser="petite",
                         taille=None):
    GRAPHES.append((tid, ident, copy.deepcopy(g)))
    if ECHEC["soumettre"]:
        raise RuntimeError("la carte a lache")
    return ([{"filename": f"{tid[:8]}_00001_.png", "subfolder": "u/image",
              "type": "output", "noeud": ident}], 42.0)


# Le soumetteur NU, celui qu'appelle le VRAI soumettre_robuste : §10 a besoin
# du verrou de carte que soumettre_robuste contient, donc il ne peut pas le
# remplacer. Il remplace ce qu'il y a en dessous.
async def faux_soumettre_nu(g, tid, ident=None):
    GRAPHES.append((tid, ident, copy.deepcopy(g)))
    return ([{"filename": f"{tid[:8]}_00001_.png", "subfolder": "u/image",
              "type": "output", "noeud": ident}], 42.0)


async def faux_ecrire_paroles(texte, duree, tid, langue_voulue="fr"):
    APPELS["paroles"] += 1
    return "D'AUTRES PAROLES, ecrites a la place des tiennes"


async def faux_aiguiller(texte, tid, conv, img=None, **kw):
    # Il ne doit JAMAIS etre appele : « refaire » promet de ne pas repasser par
    # l'analyse. S'il l'est, le compteur le dira au lieu d'un plan plausible.
    APPELS["aiguiller"] += 1
    return {"intention": "image", "modele": CLE, "prompt": "un plan invente",
            "largeur": 512, "hauteur": 512, "parametres": {}}


async def faux_distant(choix, plan, texte, entree, intention, tid, conv):
    DISTANTS.append((choix, copy.deepcopy(plan)))
    return [{"filename": "loin_00001_.png", "subfolder": "u/image",
             "type": "output", "noeud": None}]


# ── le parc ─────────────────────────────────────────────────────────────
def poser():
    """Deux machines a agent, chacune equipee de tous les moteurs du banc.

    zima ne tient aucun des deux moteurs employes ici (5,9 Go contre 7 et 9,4) :
    le rendu part donc sur le pc, et « refaire sur la grosse carte » y part
    aussi. C'est un fait du parc reel, pas un decoupage de confort.
    """
    S.REGISTRE.clear()
    S.ETAT_NOEUDS.clear()
    S.MODELES_NOEUD.clear()
    S.VERROUS_NOEUD.clear()
    S.EN_FILE.clear()
    S.EN_VOL.clear()
    del S.ATTENTE[:]
    S.TACHES.clear()
    S.CONVERSATIONS.clear()
    S.ENTREES.clear()
    S.NUAGE.clear()
    del GRAPHES[:]
    del DISTANTS[:]
    APPELS.update(paroles=0, aiguiller=0)
    ECHEC["soumettre"] = False
    dossiers = {}
    for cle in (CLE, AUDIO):
        for sous, nom, _repo, _distant in S.CATALOGUE[cle]["fichiers"]:
            dossiers.setdefault(sous, set()).add(nom)
    for ident, titre, vram, ram in (("pc", "PC (RTX 2080 Ti)", 11.0, 63.8),
                                    ("zima", "NAS ZimaOS", 5.9, 23.4)):
        S.REGISTRE[ident] = {"id": ident, "titre": titre, "agent": True,
                             "jeton": ident}
        S.ETAT_NOEUDS[ident] = {"repond": True, "vram": vram, "ram": ram,
                                "vu": time.time()}
        S.MODELES_NOEUD[ident] = {"quand": time.time(), "dossiers": dossiers}
    conv = S._vide(proprietaire=PID)
    conv["id"] = "c1"
    S.CONVERSATIONS["c1"] = conv
    S.FILE_ATTENTE = asyncio.Queue()
    return conv


def nuage(actif):
    """Le robinet du nuage, ouvert ou ferme pour les images.

    Ouvert, il est la CONTRE-EPREUVE des deux gardes de surete : sans lui, un
    « rien n'est parti au loin » serait vrai parce que rien ne pouvait partir,
    et les trois cas de §1 ne mesureraient rien du tout.
    """
    S.CHOIX["image"] = "nanobanana" if actif else "local"
    if actif:
        S.CLES["nanobanana"] = {"cle": "une-cle-de-banc"}
    else:
        S.CLES.pop("nanobanana", None)
    S.PREFERENCES["plafond_nuage"] = 0


class Req(dict):
    """Le minimum qu'attendent qui() et les gestionnaires."""

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


def poser_tour(**champs):
    """Un tour TERMINE, ecrit a la main comme le disque en garde soixante.

    Ecrit a la main et non produit par une demande : c'est justement ce que les
    tours d'AVANT portent — ou ne portent pas — qui fait rougir cette route, et
    un tour produit aujourd'hui porterait tout par construction.
    """
    tour = {"id": "t" + os.urandom(4).hex(), "heure": "12:00",
            "demande": "une illustration de banc", "prompt": "a test bench",
            "modele": CLE, "type": "image", "parametres": {},
            "taille": "1216x832", "etat": "fini", "avis": 0, "note": "",
            "fichiers": [{"filename": "ancien_00001_.png",
                          "subfolder": "u/image", "type": "output",
                          "noeud": "pc"}]}
    tour.update(champs)
    S.CONVERSATIONS["c1"]["tours"].append(tour)
    return tour


async def refaire(tour):
    return lire(await S.api_refaire(Req(corps={"conversation": "c1",
                                               "tour": tour["id"]})))


async def au_propre(tour):
    return lire(await S.api_au_propre(Req(corps={"conversation": "c1",
                                                 "tour": tour["id"]})))


async def tourner(combien=2):
    """Vide la file avec de VRAIS travailleurs : c'est travailleur() qui passe
    le plan a executer, et recopier ce passage ici ne prouverait rien."""
    S.ARRET = False
    gens = [asyncio.create_task(S.travailleur()) for _ in range(combien)]
    try:
        await asyncio.wait_for(S.FILE_ATTENTE.join(), timeout=30)
    finally:
        for g in gens:
            g.cancel()
        await asyncio.gather(*gens, return_exceptions=True)


def premier_graphe():
    """Le premier graphe soumis, ou un graphe VIDE s'il n'y en a pas.

    Vide et non GRAPHES[0][2] : quand la mutation — ou le code d'avant — envoie
    le rendu au loin, rien n'est soumis a une carte, et « GRAPHES[0] » leve
    IndexError. Un banc qui leve ne rougit pas, il se casse, et la mutation qui
    l'a fait lever passerait pour attrapee alors qu'on ne saurait rien.
    """
    return GRAPHES[0][2] if GRAPHES else {}


def texte_du_graphe(g, quoi):
    """Le texte positif ou negatif REELLEMENT envoye a la carte.

    Les deux sont des CLIPTextEncode ; on les distingue par le lien qu'en fait
    le KSampler, et non par leur numero de noeud — les numeros changent d'une
    famille de moteur a l'autre.
    """
    for noeud in g.values():
        ins = noeud.get("inputs") or {}
        cible = ins.get(quoi)
        if cible and isinstance(cible, list) and cible[0] in g:
            source = g[cible[0]]
            if source.get("class_type") == "CLIPTextEncode":
                return (source.get("inputs") or {}).get("text", "")
    return None


def paroles_du_graphe(g):
    for noeud in g.values():
        if "lyrics" in (noeud.get("inputs") or {}):
            return noeud["inputs"]["lyrics"]
    return None


def taille_du_graphe(g):
    for noeud in g.values():
        ins = noeud.get("inputs") or {}
        if "width" in ins and "height" in ins and "batch_size" in ins:
            return (ins["width"], ins["height"])
    return None


async def main():
    print(f"\n  moteurs du banc : {CLE} (image, classement) "
          f"et {AUDIO} (audio, paroles)\n")
    S.soumettre_robuste = faux_soumettre
    S.ecrire_paroles = faux_ecrire_paroles
    S.aiguiller = faux_aiguiller
    S.produire_distant = faux_distant

    # ══ 1. LA SURETE : ce qui est adulte ne sort pas de la maison ═══════
    print("\n  ── le classement, et les deux gardes qui le tiennent ──")
    # Le texte de la demande ne mord PAS sur le motif de adulte() : c'est tout
    # le cas. Un rendu marque explicite dont la demande est anodine est
    # exactement celui qui partait au loin.
    ANODIN = "une pin-up des annees 50 sur une plage"
    dit(not S._SEXUEL.search(ANODIN),
        "la demande du cas de surete ne mord pas sur le motif adulte",
        "sinon ce sont deux autres gardes qu'on mesurerait")

    # LA CONTRE-EPREUVE D'ABORD. Sans elle, « rien n'est parti au loin » serait
    # vrai parce que rien ne POUVAIT partir, et les trois cas suivants seraient
    # verts sur un depot ou la surete n'existe pas.
    conv = poser()
    nuage(True)
    plan_nu = {"intention": "image", "modele": CLE, "prompt": "a pin-up",
               "largeur": 1216, "hauteur": 832, "parametres": {}}
    dit(S.choix_distant("image", ANODIN, plan_nu, PID) == "nanobanana",
        "le robinet du nuage est bien ouvert pour ce banc",
        S.choix_distant("image", ANODIN, plan_nu, PID) or "ferme")

    # ── garde 1, SEULE : « modele_impose », sur un tour d'AVANT ────────
    # Le tour ne porte AUCUN classement — c'est le cas de tous les tours ecrits
    # avant le 1er septembre, et ils ne le porteront jamais. adulte() n'a donc
    # rien a lire : seul « modele_impose » peut retenir ce rendu a la maison.
    conv = poser()
    nuage(True)
    vieux = poser_tour(demande=ANODIN, prompt="a pin-up on a beach")
    dit("classement" not in vieux,
        "le tour d'avant ne porte pas de classement : adulte() est aveugle")
    st, corps = await refaire(vieux)
    dit(st == 200, "refaire est accepte", str(corps))
    tid = corps.get("id")
    dit((S.EN_FILE.get(tid) or {}).get("plan", {}).get("modele_impose") is True,
        "le plan reconstruit porte « modele_impose »",
        str((S.EN_FILE.get(tid) or {}).get("plan", {}).get("modele_impose")))
    await tourner()
    dit(not DISTANTS, "et le rendu ne part pas chez un fournisseur",
        ", ".join(c for c, _ in DISTANTS) or "personne")
    dit(len(GRAPHES) == 1 and GRAPHES[0][1] == "pc",
        "il est calcule sur une carte de la maison",
        str([i for _, i, _ in GRAPHES]))

    # ── garde 2, SEULE : le classement repris, « modele_impose » retire ─
    # LES DEUX CORRECTIONS SE RECOUVRENT — la premiere suffit a elle seule, le
    # message de 1ad6c0d le dit. Laisser « modele_impose » en place rendrait ce
    # cas-ci vert quoi qu'il arrive au champ « classement », et il ne mesurerait
    # RIEN. On retire donc la premiere garde de l'entree de file, comme
    # banc_repartition.py remet le defaut d'origine pour eprouver la seconde.
    conv = poser()
    nuage(True)
    marque = poser_tour(demande=ANODIN, prompt="a pin-up on a beach",
                        classement="explicit")
    st, corps = await refaire(marque)
    tid = corps.get("id")
    job = await S.FILE_ATTENTE.get()
    S.FILE_ATTENTE.task_done()
    job["plan"].pop("modele_impose", None)
    S.EN_FILE[tid]["plan"].pop("modele_impose", None)
    await S.FILE_ATTENTE.put(job)
    dit(job["plan"].get("classement") == "explicit",
        "le plan reconstruit garde le classement du tour",
        str(job["plan"].get("classement")))
    await tourner()
    dit(not DISTANTS,
        "et sans « modele_impose », c'est le classement qui le retient ici",
        ", ".join(c for c, _ in DISTANTS) or "personne")

    # ── et le classement arrive JUSQU'A LA CARTE ───────────────────────
    # Sur le tour, il pourrait n'etre qu'un champ recopie. Dans le graphe, il
    # devient la balise de score que le moteur lit : c'est la seule preuve que
    # l'image rendue est bien la meme.
    positif = texte_du_graphe(premier_graphe(), "positive")
    dit(positif is not None
        and S.CLASSEMENT_PONY["explicit"] in positif,
        "et il arrive jusqu'au graphe, en balise de score",
        (positif or "aucun prompt positif")[:70])

    # ── LA CONTRE-EPREUVE, sans aucune des deux gardes ─────────────────
    # Ni classement, ni « modele_impose » : le rendu DOIT partir au loin. Si ce
    # cas-ci passe au vert avec les autres, c'est que le nuage etait ferme et
    # que les trois precedents ne mesuraient rien.
    conv = poser()
    nuage(True)
    banal = poser_tour(demande=ANODIN, prompt="a pin-up on a beach")
    st, corps = await refaire(banal)
    job = await S.FILE_ATTENTE.get()
    S.FILE_ATTENTE.task_done()
    job["plan"].pop("modele_impose", None)
    await S.FILE_ATTENTE.put(job)
    await tourner()
    dit(len(DISTANTS) == 1,
        "sans garde du tout, le meme rendu part bien chez le fournisseur",
        ", ".join(c for c, _ in DISTANTS) or "personne — le nuage etait ferme")
    nuage(False)

    # ══ 2. un moteur qui a quitte le catalogue ══════════════════════════
    print("\n  ── le catalogue bouge, le tour non ──")
    conv = poser()
    perdu = poser_tour(modele="sdxl_vieux")
    st, corps = await refaire(perdu)
    dit(st == 409, "refaire un tour dont le moteur a disparu repond 409", str(st))
    dit("sdxl_vieux" in (corps.get("erreur") or "")
        and "catalogue" in (corps.get("erreur") or ""),
        "et il le DIT, au lieu de « ERREUR : 'sdxl_vieux' »",
        corps.get("erreur", ""))
    dit(not S.ATTENTE and not perdu.get("refait"),
        "rien n'est mis en file, et le bouton reste disponible",
        f"file={len(S.ATTENTE)}, refait={perdu.get('refait')}")

    # ══ 3. le meme trou dans api_au_propre ══════════════════════════════
    # Les deux boutons rejouent un plan garde ; ils avaient donc tous les deux
    # besoin de la garde, et api_au_propre ne l'avait pas.
    conv = poser()
    esquisse = poser_tour(esquisse=True, modele="sdxl_vieux",
                          plan={"intention": "image", "modele": "sdxl_vieux",
                                "prompt": "a test bench", "priorite": "brouillon",
                                "largeur": 1216, "hauteur": 832,
                                "parametres": {"etapes": 5}})
    st, corps = await au_propre(esquisse)
    dit(st == 409, "passer au propre une esquisse au moteur disparu repond 409",
        str(st))
    dit("sdxl_vieux" in (corps.get("erreur") or "")
        and "catalogue" in (corps.get("erreur") or ""),
        "et le meme message, au mot « esquisse » pres",
        corps.get("erreur", ""))
    dit(not S.ATTENTE and not esquisse.get("au_propre"),
        "rien en file, et le bouton reste",
        f"file={len(S.ATTENTE)}, au_propre={esquisse.get('au_propre')}")

    # ══ 4. un rendu confie a un fournisseur distant ═════════════════════
    # Le tour porte le nom du FOURNISSEUR dans « modele », et ce bouton-ci
    # demande une carte de la maison. Sans garde, c'etait « ERREUR : 'veo' » un
    # cran plus loin.
    print("\n  ── ce qui a ete rendu au loin ──")
    conv = poser()
    loin = poser_tour(modele="veo", type="video")
    st, corps = await refaire(loin)
    dit(st == 409, "refaire un rendu confie a un fournisseur repond 409", str(st))
    dit(S.MOTEURS_DISTANTS["veo"]["titre"] in (corps.get("erreur") or ""),
        "et la phrase nomme le fournisseur, au lieu de « ERREUR : 'veo' »",
        corps.get("erreur", ""))
    dit("carte" in (corps.get("erreur") or ""),
        "en disant ce que le bouton demande : une carte de la maison",
        corps.get("erreur", ""))
    # Un moteur distant n'est PAS au catalogue : sans son test a lui, il serait
    # tombe dans le message du catalogue, qui conseille de « choisir un autre
    # moteur » alors qu'il n'y a rien a choisir.
    dit("catalogue" not in (corps.get("erreur") or ""),
        "et ce n'est pas le message du catalogue qui repond a sa place",
        corps.get("erreur", ""))

    # ══ 5. un tour SANS TAILLE ══════════════════════════════════════════
    # « taille » n'est ecrit sur le tour que depuis le 31 aout, et une
    # conversation en garde soixante : sur tout tour anterieur, executer levait
    # KeyError: 'largeur' — « ERREUR inattendue : 'largeur' », un plantage muet
    # sur le cas le plus frequent du bouton.
    print("\n  ── un tour d'avant le 31 aout, sans taille ──")
    conv = poser()
    nu = poser_tour(taille=None, demande="une illustration de banc")
    st, corps = await refaire(nu)
    dit(st == 200, "refaire un tour sans taille est accepte", str(corps))
    tid = corps.get("id")
    await tourner()
    neuf = next(t for t in tours() if t.get("id") == tid)
    dit(neuf.get("etat") == "fini" and neuf.get("fichiers"),
        "il rend une image, au lieu de « ERREUR inattendue : 'largeur' »",
        f"{neuf.get('etat')} {neuf.get('erreur') or ''}")
    dit(taille_du_graphe(premier_graphe()) == (1216, 832),
        "la taille du studio est rejouee, et elle arrive au graphe",
        str(taille_du_graphe(premier_graphe())))
    dit("n'avait pas ete conservee" in mots(tid)
        and "1216x832" in mots(tid),
        "et le studio ANNONCE la taille qu'il a reprise",
        mots(tid)[:130])
    dit(APPELS["aiguiller"] == 0,
        "sans repasser par l'analyse, qui rendrait une autre image",
        str(APPELS["aiguiller"]))

    # ── une taille ecrite dans la demande est relue, pas inventee ──────
    # caler_taille() commence par chercher une taille noir sur blanc : c'est
    # exactement ce que la demande d'origine a fait, et c'est le seul repli qui
    # puisse tomber juste.
    conv = poser()
    nu2 = poser_tour(taille=None, demande="une illustration de banc en 1024x1024")
    st, corps = await refaire(nu2)
    await tourner()
    dit(taille_du_graphe(premier_graphe()) == (1024, 1024),
        "la taille ecrite dans la demande d'origine est relue",
        str(taille_du_graphe(premier_graphe())))

    # ══ 6. les paroles ══════════════════════════════════════════════════
    # Sans elles dans le plan reconstruit, ecrire_paroles() est rappele et la
    # chanson repart sur d'AUTRES paroles : c'est mot pour mot le passage par
    # l'analyse que la docstring promet d'eviter.
    print("\n  ── une chanson refaite ne se reecrit pas ──")
    conv = poser()
    PAROLES = "[couplet]\nle banc mesure ce qu'il dit\n[refrain]\net rien d'autre"
    chanson = poser_tour(modele=AUDIO, type="audio", taille=None,
                         demande="une chanson rock sur la mer",
                         prompt="rock, guitare, batterie",
                         paroles=PAROLES,
                         parametres={"etapes": 8, "cfg": 1.0, "bpm": 90,
                                     "duree_s": 60})
    dit(bool(S._CHANSON.search(chanson["demande"])),
        "la demande est bien reconnue comme une chanson",
        "sinon ecrire_paroles ne serait pas rappele, meme sans la reprise")
    st, corps = await refaire(chanson)
    dit(st == 200, "refaire une chanson est accepte", str(corps))
    tid = corps.get("id")
    await tourner()
    dit(APPELS["paroles"] == 0,
        "ecrire_paroles() n'est PAS rappele", str(APPELS["paroles"]))
    dit(paroles_du_graphe(premier_graphe()) == PAROLES,
        "et ce sont les memes paroles qui partent a la carte",
        (paroles_du_graphe(premier_graphe()) or "aucune")[:60])
    refait = next(t for t in tours() if t.get("id") == tid)
    dit(refait.get("paroles") == PAROLES,
        "le tour refait les porte aussi, pour le pouce en bas",
        (refait.get("paroles") or "aucune")[:40])

    # ══ 7. le negatif et la raison ══════════════════════════════════════
    print("\n  ── le negatif et la raison ──")
    conv = poser()
    NEG = "flou, mains ratees, six doigts"
    RAISON = "moteur a etiquettes : la demande decrit un personnage stylise"
    detaille = poser_tour(negatif=NEG, raison=RAISON)
    st, corps = await refaire(detaille)
    tid = corps.get("id")
    await tourner()
    negatif = texte_du_graphe(premier_graphe(), "negative")
    dit(negatif == NEG,
        "le negatif du tour est celui qui part a la carte, pas NEG_DEFAUT",
        (negatif or "aucun")[:60])
    dit(negatif != S.NEG_DEFAUT,
        "et NEG_DEFAUT, justement, ne l'a pas remplace",
        "il l'avait remplace, donc une autre image" if negatif == S.NEG_DEFAUT
        else "")
    refait = next(t for t in tours() if t.get("id") == tid)
    dit(refait.get("raison") == RAISON,
        "et la raison suit : le journal ne montre plus un tiret nu",
        str(refait.get("raison")))

    # ══ 8. un refait qui echoue rend son bouton ═════════════════════════
    # La marque est posee AVANT le rendu — c'est elle qui empeche deux onglets
    # d'en lancer deux — mais laissee la sur un echec elle faisait disparaitre
    # le bouton pour toujours, alors que ce geste EST la reparation d'un rendu
    # rate.
    print("\n  ── un refait qui echoue ──")
    conv = poser()
    casse = poser_tour()
    st, corps = await refaire(casse)
    tid = corps.get("id")
    dit(casse.get("refait") == tid,
        "la marque est posee AVANT le rendu, contre le second onglet",
        str(casse.get("refait")))
    st2, corps2 = await refaire(casse)
    dit(st2 == 409, "et un second clic est refuse pendant le rendu", str(st2))
    ECHEC["soumettre"] = True
    await tourner()
    rate_ = next(t for t in tours() if t.get("id") == tid)
    dit(rate_.get("etat") == "erreur", "le rendu a bien echoue",
        str(rate_.get("etat")))
    origine = next(t for t in tours() if t.get("id") == casse["id"])
    dit(not origine.get("refait"),
        "la marque est retiree du tour d'origine : le bouton revient",
        str(origine.get("refait")))
    ECHEC["soumettre"] = False
    st3, corps3 = await refaire(origine)
    dit(st3 == 200, "et le geste se rejoue, au lieu de repondre 409 a jamais",
        f"{st3} {corps3.get('erreur') or ''}")
    await tourner()

    # ══ 9. la marque « refait » survit a une reecriture du tour ═════════
    # Le tour d'origine est reecrit par d'autres chemins que celui qui l'a
    # produit — rattacher_tardif(), une reprise apres redemarrage. Sans la
    # reprise de la marque, chacun de ces chemins reproposait le bouton, donc un
    # second rendu sur la grosse carte.
    print("\n  ── la marque survit a une reecriture ──")
    conv = poser()
    vieux2 = poser_tour()
    st, corps = await refaire(vieux2)
    tid = corps.get("id")
    await tourner()
    dit(vieux2.get("refait") == tid, "le tour est marque refait",
        str(vieux2.get("refait")))
    # La reecriture, par la fonction que TOUS ces chemins empruntent, et avec
    # l'etat qu'ils y posent : « fini », comme un resultat recolle.
    S.enregistrer_tour(conv, vieux2["id"], vieux2["demande"],
                       {"prompt": vieux2["prompt"]}, "image", CLE,
                       vieux2["fichiers"], "fini")
    relu = next(t for t in tours() if t.get("id") == vieux2["id"])
    dit(relu.get("refait") == tid,
        "et la marque est toujours la apres la reecriture",
        str(relu.get("refait")))
    st4, corps4 = await refaire(relu)
    dit(st4 == 409,
        "donc le bouton ne repropose pas un second rendu sur la grosse carte",
        f"{st4} {corps4.get('erreur') or ''}")

    # ══ 10. ecoule_rendu ne compte plus l'attente de la carte ═══════════
    # Le devis auquel la page compare ce chiffre est une mediane de
    # tour["secondes"], dont le chrono demarre APRES la prise de la carte. Sur
    # un parc a une seule carte, le second rendu etait donc rouge avant sa
    # premiere etape.
    #
    # Le VRAI soumettre_robuste ici : c'est lui qui contient le verrou, donc lui
    # qu'on mesure. Seule la soumission nue est remplacee.
    print("\n  ── le chrono du rendu part la carte en main ──")
    S.soumettre_robuste = _VRAI_SOUMETTRE_ROBUSTE
    S.soumettre = faux_soumettre_nu
    try:
        conv = poser()
        lent = poser_tour()
        # Quelqu'un d'autre calcule deja sur la seule carte capable.
        verrou = S.verrou_noeud("pc")
        await verrou.acquire()
        st, corps = await refaire(lent)
        tid = corps.get("id")
        depart = time.time()
        gens = [asyncio.create_task(S.travailleur())]
        # Assez long pour se distinguer du bruit de la boucle, assez court pour
        # que le banc reste sous la seconde.
        ATTENTE_CARTE = 0.4
        await asyncio.sleep(ATTENTE_CARTE)
        dit((S.TACHES.get(tid) or {}).get("attend_carte") is True,
            "la demande attend la carte, et le dit",
            str((S.TACHES.get(tid) or {}).get("attend_carte")))
        # ET PENDANT L'ATTENTE, IL NE COURT PAS DU TOUT. executer posait le
        # chrono avant l'appel : la pastille passait au rouge AVANT la premiere
        # etape, puis le compteur retombait a zero a la prise de la carte, sous
        # les yeux. Le champ est simplement ABSENT tant que la carte n'est pas
        # en main — la page n'a alors rien a comparer au devis, ce qui est la
        # verite.
        st_, etat = lire(await S.api_etat(Req(match={"tid": tid})))
        dit(etat.get("ecoule_rendu") is None,
            "tant que la carte n'est pas en main, il n'y a pas de temps de "
            "rendu a montrer", str(etat.get("ecoule_rendu")))
        verrou.release()
        try:
            await asyncio.wait_for(S.FILE_ATTENTE.join(), timeout=30)
        finally:
            for g in gens:
                g.cancel()
            await asyncio.gather(*gens, return_exceptions=True)
        pose = (S.TACHES.get(tid) or {}).get("debut_rendu") or 0
        dit(pose - depart >= ATTENTE_CARTE,
            "le chrono est repose la carte EN MAIN, apres l'attente",
            f"{pose - depart:.2f} s apres le depart, pour "
            f"{ATTENTE_CARTE} s d'attente")
        st_, etat = lire(await S.api_etat(Req(match={"tid": tid})))
        dit(etat.get("ecoule", 0) - etat.get("ecoule_rendu", 0) >= ATTENTE_CARTE,
            "et « ecoule » et « ecoule_rendu » ne comptent plus la meme chose",
            f"ecoule={etat.get('ecoule')} s, "
            f"ecoule_rendu={etat.get('ecoule_rendu')} s")
    finally:
        S.soumettre_robuste = faux_soumettre

    print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
    for r in rate:
        print("    a regarder :", r)
    return 1 if rate else 0


# Pris AVANT que main() ne pose les faux : §10 en a besoin intact.
_VRAI_SOUMETTRE_ROBUSTE = S.soumettre_robuste

if __name__ == "__main__":
    # asyncio.get_event_loop() leve depuis Python 3.14 hors d'une boucle : le
    # banc passait dans le conteneur et echouait sur la machine de celui qui
    # l'ecrit.
    sys.exit(asyncio.run(main()))
