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
  - LE TOUR PORTE LE PLAN ENTIER depuis le 2 septembre 2026, et c'est le
    chemin normal : la liste de champs recopies s'etait allongee de six
    entrees en deux jours, une par defaut constate. Le repli champ par champ
    reste pour les tours d'AVANT, les deux chemins sont compares sur le meme
    graphe, et le plan n'emporte que ce qu'une liste nommee autorise — il sort
    de json.loads(reponse du modele) et c'est la seule chose du tour qui
    grossirait sans borne.
  - un tour SANS TAILLE rend quand meme une image — les tours d'avant le
    31 aout n'ont pas de champ « taille », et c'etait un KeyError: 'largeur' —
    et le studio ANNONCE la taille qu'il a reprise. Mais SEULEMENT a une
    image : la planche ignore cette taille et la ferait mentir jusque dans la
    table des durees, et une chanson n'a pas de resolution du tout.
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


def tour_de(tid):
    """Le tour qui porte cet identifiant, ou un tour VIDE.

    Vide et non « next(...) » nu : quand la route refuse la demande — ce que
    fait toute mutation qui coupe une garde en amont — il n'y a pas de tour, et
    le generateur leve StopIteration. Le banc s'ARRETE alors avant d'imprimer
    la ligne que la mutation nomme, et banc_mutations.py rend « le banc s'est
    casse » pour une mutation parfaitement attrapee dix cas plus loin. Un banc
    qui se casse ne mesure pas : il doit rougir jusqu'au bout.
    """
    return next((t for t in tours() if t.get("id") == tid), {})


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


async def _appeler(route, tour):
    """La reponse de la route, ou un 500 fabrique si elle a LEVE.

    Une exception qui remonte jusqu'ici tue le banc : il s'arrete avant
    d'imprimer la ligne que la mutation nomme, et banc_mutations.py rend « le
    banc s'est casse » pour une mutation parfaitement attrapee dix cas plus
    loin. C'est le faux positif que ce fichier-la existe pour interdire, et son
    en-tete le dit deja d'une exception : « elle rend elle aussi un code non
    nul, et se ferait passer pour une reussite ».

    Et ici, ce n'est pas theorique : « ERREUR inattendue : 'largeur' » est le
    defaut d'origine de cette route, un KeyError dans un chemin de repli. Le
    banc ecrit pour lui doit donc savoir le RECEVOIR et rougir en le nommant,
    pas mourir dessus. Mesure du 2 septembre : la mutation qui retirait la garde
    de l'annonce de taille cassait le banc au lieu de le faire rougir.
    """
    try:
        return lire(await route(Req(corps={"conversation": "c1",
                                           "tour": tour["id"]})))
    except Exception as e:
        return 500, {"erreur": f"la route a leve {type(e).__name__}: {e}"}


async def refaire(tour):
    return await _appeler(S.api_refaire, tour)


async def au_propre(tour):
    return await _appeler(S.api_au_propre, tour)


async def sortir_de_la_file():
    """La demande mise en file, ou None — jamais une attente sans fin.

    « await FILE_ATTENTE.get() » tout court PEND des que la route a refuse la
    demande au lieu de la mettre en file. Un banc qui pend ne rougit pas : il
    ne dit rien du defaut qu'on lui presente, et il emporte avec lui
    banc_mutations.py — qui lance chaque banc mute et attend sa reponse. Mesure
    du 2 septembre : six lancements empiles, deux depuis dix-sept minutes, sur
    la mutation qui retire le repli des tours d'avant. C'est exactement la
    famille de defaut que banc_mutations existe pour attraper, retournee contre
    le banc lui-meme.

    Deux secondes, et non trente : api_refaire met en file AVANT de repondre,
    si bien qu'a ce point la demande y est deja ou n'y sera jamais. Le delai
    n'attend rien, il borne — et il est appele deux fois, donc il compte deux
    fois dans le budget de trente secondes que banc_mutations accorde a un banc
    mute.
    """
    try:
        return await asyncio.wait_for(S.FILE_ATTENTE.get(), timeout=2)
    except asyncio.TimeoutError:
        return None


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


def resume_du_graphe(g):
    """Ce qui decide l'image, et rien de ce qui la date.

    La graine en est ABSENTE, et c'est voulu : « refaire » en tire justement
    une autre. Comparer les graphes entiers ferait donc rougir la comparaison
    des deux chemins pour la seule raison qui ne les distingue pas.
    """
    etapes = cfg = None
    for noeud in g.values():
        ins = noeud.get("inputs") or {}
        # Les deux sur le MEME noeud : un graphe porte plusieurs « cfg » — le
        # CFGGuider de flux2, le cfg_scale de l'encodeur ACE — et les lire
        # separement comparerait deux reglages sans rapport.
        if "steps" in ins and "cfg" in ins:
            etapes, cfg = ins["steps"], ins["cfg"]
    return {"positif": texte_du_graphe(g, "positive"),
            "negatif": texte_du_graphe(g, "negative"),
            "taille": taille_du_graphe(g), "etapes": etapes, "cfg": cfg}


def poser_tour_avec_plan(plan, tid=None, **champs):
    """Un tour TERMINE, ecrit par le VRAI enregistrer_tour, donc avec son plan.

    Par enregistrer_tour et non a la main : c'est LUI qu'on mesure ici. Un tour
    fabrique a la main porterait le plan par construction et ne dirait rien de
    ce que le studio ecrit reellement sur le disque de l'utilisateur.
    """
    tid = tid or "t" + os.urandom(8).hex()
    S.enregistrer_tour(S.CONVERSATIONS["c1"], tid,
                       champs.pop("demande", "une illustration de banc"),
                       plan, plan.get("intention"), plan.get("modele"),
                       [{"filename": "avecplan_00001_.png",
                         "subfolder": "u/image", "type": "output",
                         "noeud": "pc"}], "fini")
    tour = tour_de(tid)
    tour.update(champs)
    return tour


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
    job = await sortir_de_la_file()
    if job:
        S.FILE_ATTENTE.task_done()
        job["plan"].pop("modele_impose", None)
        S.EN_FILE[tid]["plan"].pop("modele_impose", None)
        await S.FILE_ATTENTE.put(job)
    rejoue_ = (job or {}).get("plan") or {}
    dit(rejoue_.get("classement") == "explicit",
        "le plan reconstruit garde le classement du tour",
        str(rejoue_.get("classement")) if job else "rien n'a ete mis en file")
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
    job = await sortir_de_la_file()
    if job:
        S.FILE_ATTENTE.task_done()
        job["plan"].pop("modele_impose", None)
        await S.FILE_ATTENTE.put(job)
    await tourner()
    dit(len(DISTANTS) == 1,
        "sans garde du tout, le meme rendu part bien chez le fournisseur",
        ", ".join(c for c, _ in DISTANTS) or "personne — le nuage etait ferme")
    # ET LE TOUR D'UN RENDU PARTI AU LOIN NE PORTE PAS DE PLAN. Sur ce chemin,
    # plan["modele"] porte le repli LOCAL — celui qui aurait servi si le
    # fournisseur avait echoue — et c'est « cle » qui nomme le fournisseur.
    # Ecrire ce plan-la ferait afficher le moteur de la maison sous une image
    # rendue au loin : la page lit « plan.modele » en premier.
    au_loin = tour_de(corps.get("id"))
    dit(au_loin.get("plan") is None,
        "un rendu confie au loin n'ecrit pas de plan sur son tour",
        str((au_loin.get("plan") or {}).get("modele")))
    dit(au_loin.get("modele") == "nanobanana",
        "et son tour nomme le FOURNISSEUR, pas le repli local",
        str(au_loin.get("modele")))
    # ET « en soigne » LE DIT ENCORE, sans plan a lire. C'est la contrepartie
    # du cas precedent : le controle du fournisseur doit passer AVANT celui du
    # plan, sinon une esquisse rendue au loin recoit « ce tour n'est pas une
    # esquisse qu'on sache refaire » — vrai de nulle part et utile a personne.
    au_loin["esquisse"] = True
    st, corps = await au_propre(au_loin)
    dit(st == 400, "passer au propre une esquisse rendue au loin repond 400",
        f"{st} {corps.get('erreur') or ''}")
    dit(S.MOTEURS_DISTANTS["nanobanana"]["titre"] in (corps.get("erreur") or ""),
        "et la phrase nomme le fournisseur, sans plan a lire",
        corps.get("erreur", ""))
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
    neuf = tour_de(tid)
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

    # ── ET LA PLANCHE N'EST PAS UNE IMAGE ──────────────────────────────
    # caler_taille() n'est jamais appele pour une planche sur le chemin normal,
    # et la branche planche d'executer n'en lirait pas le resultat : elle impose
    # son format page, plafonne la largeur a 960 et tire la hauteur d'un rapport
    # A4. Le 1216x832 pose par le repli ressortait en 960x1344, le journal se
    # contredisait a deux lignes d'intervalle, et ce 1216x832 mentait ensuite
    # dans la mediatheque ET dans la table des durees — celle sur laquelle
    # debordement_acceptable(exact=True) tranche un debordement de carte.
    #
    # On s'arrete au plan mis en file : rendre une planche demanderait son
    # moteur sur une machine du banc, et ce n'est pas ce qu'on mesure ici.
    conv = poser()
    bd = poser_tour(taille=None, type="planche", modele="planche",
                    demande="une planche de bande dessinee sur un chat")
    st, corps = await refaire(bd)
    dit(st == 200, "refaire une planche sans taille est accepte", str(corps))
    tid = corps.get("id")
    plan_bd = (S.EN_FILE.get(tid) or {}).get("plan") or {}
    dit(not plan_bd.get("largeur") and not plan_bd.get("hauteur"),
        "le repli de taille ne pose PAS 1216x832 sur une planche",
        f"{plan_bd.get('largeur')}x{plan_bd.get('hauteur')}")
    # « la demande est bien partie ET le journal ne dit pas ça », et non « il
    # ne dit pas ça » : un silence obtenu parce que la route a refuse n'est pas
    # le silence qu'on mesure, et ce cas resterait vert le jour ou le bouton
    # cesserait de marcher du tout. On exige le 200 et non un journal non vide :
    # rien n'est rendu ici, et sans rendu ni file d'attente devant, le journal
    # de cette demande est LEGITIMEMENT vide.
    dit(st == 200 and "la taille de ce tour" not in mots(tid),
        "et le journal n'annonce pas une taille que la planche ignorera",
        mots(tid)[:120] or f"aucun journal (reponse {st})")

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
    refait = tour_de(tid)
    dit(refait.get("paroles") == PAROLES,
        "le tour refait les porte aussi, pour le pouce en bas",
        (refait.get("paroles") or "aucune")[:40])
    # ET LE JOURNAL NE PARLE PAS DE TAILLE A QUI N'EN A PAS. Une chanson n'a pas
    # de resolution : « sans_taille » y est vrai par nature, et la PREMIERE
    # ligne que voyait quelqu'un qui refait une chanson etait « la taille de ce
    # tour n'avait pas ete conservee — on laisse le studio la choisir ». Rien
    # n'avait ete conserve ni choisi. Ce banc traversait deja ce cas et laissait
    # la ligne s'imprimer sans rien en dire.
    # Meme exigence que pour la planche : un journal qui EXISTE et qui se tait.
    dit(bool(mots(tid)) and "la taille de ce tour" not in mots(tid),
        "et le journal ne parle pas de taille a une chanson, qui n'en a pas",
        mots(tid)[:120] or "aucun journal — la demande n'est jamais partie")

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
    refait = tour_de(tid)
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
    rate_ = tour_de(tid)
    dit(rate_.get("etat") == "erreur", "le rendu a bien echoue",
        str(rate_.get("etat")))
    origine = tour_de(casse["id"])
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
    relu = tour_de(vieux2["id"])
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

    # ══ 11. le tour porte le plan ENTIER ════════════════════════════════
    # Depuis le 2 septembre 2026. Avant, il recopiait une LISTE de champs, et
    # cette liste s'est allongee de six entrees en deux jours — une par defaut
    # constate, dont un de surete. Ce que ces cas mesurent, c'est que la liste
    # n'existe plus sur le chemin normal : elle ne sert plus qu'aux tours ecrits
    # avant cette date, qui ne porteront jamais de plan.
    print("\n  ── le plan entier, sur le tour ──")
    DEMANDE = "un phare sur un ilot rocheux au coucher du soleil"
    NEG_2 = "flou, mains ratees, six doigts, filigrane"
    RAISON_2 = "scene realiste et detaillee : moteur a etiquettes"
    def plan_complet():
        return {"intention": "image", "modele": CLE,
                "prompt": "a lone lighthouse on a jagged rocky islet at sunset",
                "negatif": NEG_2, "classement": "explicit", "raison": RAISON_2,
                "largeur": 1216, "hauteur": 832,
                "parametres": {"etapes": 28, "cfg": 6.0},
                "parametres_bruts": {"etapes": 28, "cfg": 6.0}}

    conv = poser()
    plein = poser_tour_avec_plan(plan_complet(), demande=DEMANDE)
    ecrit = plein.get("plan") or {}
    dit(isinstance(plein.get("plan"), dict),
        "un tour ordinaire porte desormais son plan",
        "aucun plan" if not plein.get("plan") else str(sorted(ecrit)))
    manque = [c for c in ("intention", "modele", "prompt", "negatif",
                          "classement", "largeur", "hauteur", "parametres",
                          "parametres_bruts", "raison")
              if ecrit.get(c) != plan_complet().get(c)]
    dit(not manque, "et il le porte ENTIER, pas six champs sur douze",
        ", ".join(manque) or "rien ne manque")
    # LES CHAMPS PLATS QUI N'AVAIENT PAS D'AUTRE LECTEUR SONT PARTIS. Les garder
    # aux deux endroits, c'etait deux sources pour la meme chose — le defaut que
    # ce depot passe ses journees a fermer, et celui qui a produit les six.
    doubles = [c for c in ("negatif", "classement", "langue", "tonalite")
               if c in plein]
    dit(not doubles,
        "et ils ne sont plus recopies a plat a cote : une seule source",
        ", ".join(doubles) or "aucun doublon")

    # ── un tour d'AVANT passe toujours par le repli ────────────────────
    # Le repli n'est pas mort, il est RETROGRADE. Une conversation garde
    # soixante tours, et ceux d'avant le 2 septembre 2026 sont sur le disque de
    # l'utilisateur pour de bon : sans lui, le bouton devenait inoperant sur
    # tout l'historique.
    print("\n  ── un tour d'avant, sans plan, passe par le repli ──")
    conv = poser()
    ancien = poser_tour(demande=DEMANDE, prompt="a lone lighthouse",
                        negatif=NEG_2, classement="explicit", raison=RAISON_2)
    dit("plan" not in ancien,
        "le tour d'avant ne porte aucun plan, par construction du cas",
        "sinon ce serait le chemin normal qu'on mesurerait")
    st, corps = await refaire(ancien)
    dit(st == 200, "refaire y est accepte quand meme", str(corps))
    rejoue = (S.EN_FILE.get(corps.get("id")) or {}).get("plan") or {}
    dit(rejoue.get("classement") == "explicit" and rejoue.get("negatif") == NEG_2,
        "et le repli reconstruit bien le plan champ par champ",
        f"classement={rejoue.get('classement')}, "
        f"negatif={(rejoue.get('negatif') or 'aucun')[:24]}")
    await tourner()

    # ── ET LES DEUX CHEMINS RENDENT LA MEME CHOSE ─────────────────────
    # C'est le cas qui tient les deux ensemble. Le jour ou le repli et le plan
    # divergent, le bouton rendra une image differente selon l'AGE du tour sur
    # lequel on a clique — et rien ne le dira.
    print("\n  ── le plan et le repli rendent la meme image ──")
    conv = poser()
    par_plan = poser_tour_avec_plan(plan_complet(), demande=DEMANDE)
    st, _ = await refaire(par_plan)
    await tourner()
    resume_plan = resume_du_graphe(premier_graphe())
    conv = poser()
    par_repli = poser_tour(demande=DEMANDE,
                           prompt="a lone lighthouse on a jagged rocky islet "
                                  "at sunset",
                           negatif=NEG_2, classement="explicit",
                           raison=RAISON_2, taille="1216x832",
                           parametres={"etapes": 28, "cfg": 6.0})
    st, _ = await refaire(par_repli)
    await tourner()
    resume_repli = resume_du_graphe(premier_graphe())
    ecarts = [c for c in resume_plan if resume_plan[c] != resume_repli[c]]
    dit(not ecarts and resume_plan["positif"],
        "meme prompt, meme negatif, meme taille, memes etapes a la carte",
        ", ".join(f"{c} : {resume_plan[c]!r} contre {resume_repli[c]!r}"
                  for c in ecarts) or str(resume_plan["taille"]))
    dit(S.CLASSEMENT_PONY["explicit"] in (resume_plan["positif"] or ""),
        "et le classement arrive au graphe par le plan aussi",
        (resume_plan["positif"] or "aucun")[:70])

    # ── LA CHANSON, PAR LE PLAN CETTE FOIS ────────────────────────────
    # § 6 mesure les paroles reprises par le REPLI. Celui-ci mesure les trois
    # champs de la meme famille par le chemin normal, et jusqu'au graphe : sans
    # eux, g_audio retombe sur « en » et « C minor », et une chanson francaise
    # repart en anglais dans une autre tonalite, avec les paroles francaises que
    # la reprise venait de sauver.
    print("\n  ── une chanson refaite par son plan ──")
    conv = poser()
    PAROLES_2 = "[couplet]\nle vent se leve sur la digue\n[refrain]\nla mer revient"
    chantee = poser_tour_avec_plan(
        {"intention": "audio", "modele": AUDIO,
         "prompt": "rock, 122 BPM, electric guitars, drums",
         "tags_audio": "rock, 122 BPM, electric guitars, drums",
         "paroles": PAROLES_2, "langue": "fr", "tonalite": "A minor",
         "raison": "chanson structuree : moteur soigne",
         "parametres": {"etapes": 8, "cfg": 1.0, "bpm": 122, "duree_s": 60},
         "parametres_bruts": {"bpm": 122, "duree_s": 60}},
        demande="une chanson rock francaise sur la mer")
    dit(bool(S._CHANSON.search(chantee["demande"])),
        "la demande est bien reconnue comme une chanson",
        "sinon ecrire_paroles ne serait pas rappele, meme sans la reprise")
    st, corps = await refaire(chantee)
    dit(st == 200, "refaire la chanson est accepte", str(corps))
    await tourner()
    dit(APPELS["paroles"] == 0,
        "ecrire_paroles() n'est PAS rappele : le plan portait les paroles",
        str(APPELS["paroles"]))
    encodeur = next((n.get("inputs") or {} for n in premier_graphe().values()
                     if "lyrics" in (n.get("inputs") or {})), {})
    dit(encodeur.get("lyrics") == PAROLES_2,
        "les memes paroles partent a la carte",
        (encodeur.get("lyrics") or "aucune")[:40])
    dit(encodeur.get("language") == "fr"
        and encodeur.get("keyscale") == "A minor",
        "et dans la MEME langue et la meme tonalite, pas « en » et « C minor »",
        f"{encodeur.get('language')} / {encodeur.get('keyscale')}")

    # ── CE QUE LE PLAN N'EMPORTE PAS ──────────────────────────────────
    # Le tour est ecrit sur le disque de l'utilisateur et relu a chaque
    # ouverture de conversation. Le plan, lui, sort de json.loads(reponse du
    # modele) : il garde TOUTES les cles que le modele a emises, y compris
    # celles que personne ne lit. Sans liste nommee, c'est la seule chose du
    # tour qui grossisse sans borne.
    print("\n  ── ce que le plan ne doit pas emporter ──")
    conv = poser()
    sale = plan_complet()
    sale.update({
        # ce que le modele a invente, et que rien ne lit
        "explication": "voici pourquoi j'ai choisi ce moteur " + "x" * 4000,
        "confiance": 0.87,
        # des marques de GESTE, reposees a chaque rejeu
        "modele_impose": True, "refait": True, "variante": True,
        "priorite": "brouillon", "graine": 864102317,
        # des traces de l'analyse qui vient d'avoir lieu
        "enrichissement_rate": True, "attente": "tel_quel",
        "parametres_ajustes": ["cfg 12 -> 8"], "prompt_repli": True,
        "raccourci": True, "questions": ["que veux-tu voir ?"],
        "questions_forcees": True,
        # DES DESCRIPTIONS QUI PASSENT LE FILTRE : « case 0 » fait six
        # caracteres, et la normalisation ecarte tout ce qui en fait moins de
        # douze. Avec l'ancienne liste, ce cas mesurait le FILTRE en croyant
        # mesurer le plafond, et rendait zero.
        "cases": [f"la case numero {i} de la planche" for i in range(9)]})
    sale["parametres_bruts"] = {"etapes": 28, "cfg": 6.0,
                                "commentaire": "y" * 2000}
    trop = poser_tour_avec_plan(sale, demande=DEMANDE)
    porte = trop.get("plan") or {}
    indesirables = [c for c in ("explication", "confiance", "modele_impose",
                                # « priorite » N'EST PLUS indesirable, et
                                # l'exclure etait une regression : le refait
                                # d'un brouillon rendait toujours en brouillon
                                # — les etapes reduites voyagent dans
                                # « parametres » — mais ne le disait plus.
                                "refait", "variante", "graine",
                                "enrichissement_rate", "attente",
                                "parametres_ajustes", "prompt_repli",
                                "raccourci", "questions", "questions_forcees")
                    if c in porte]
    dit(not indesirables,
        "le plan ecrit ne porte que la liste nommee",
        ", ".join(indesirables) or "aucune cle en trop")
    dit("commentaire" not in (porte.get("parametres_bruts") or {}),
        "et « parametres_bruts » est borne a ce que BORNES sait lire",
        str(sorted(porte.get("parametres_bruts") or {})))
    dit(len(porte.get("cases") or []) == 6,
        "et les cases s'arretent aux six que la planche sait dessiner",
        str(len(porte.get("cases") or [])))
    # LA MESURE, ET C'EST ELLE QUI TRANCHE. Sans la liste nommee, ce seul tour
    # pesait six kilo-octets a lui tout seul — davantage que les quatre plus
    # grosses conversations reelles de cette machine reunies.
    entier = len(json.dumps(sale, ensure_ascii=False, indent=1).encode("utf-8"))
    borne = len(json.dumps(porte, ensure_ascii=False, indent=1).encode("utf-8"))
    dit(borne < 900 and entier > 6000,
        "et le plan pese moins d'un kilo-octet la ou le brut en pesait six",
        f"{borne} o ecrits pour {entier} o proposes")

    # ── ET LES DEUX DEFAUTS QUE CES EXCLUSIONS EVITENT ────────────────
    # Ce ne sont pas des cles « inutiles » : recopiees, elles cassent le bouton.
    # « priorite » ferait marquer le refait comme une esquisse et lui reposerait
    # le bouton « refaire en soigne » ; « enrichissement_rate » ferait reposer
    # la question « je l'envoie telle quelle ? » a la place de l'image, sur un
    # chemin qui ne repasse justement pas par l'enrichissement.
    st, corps = await refaire(trop)
    dit(st == 200, "refaire ce tour-la est accepte", str(corps))
    tid = corps.get("id")
    await tourner()
    refait_ = tour_de(tid)
    dit(refait_.get("etat") == "fini" and refait_.get("fichiers"),
        "il REND une image, au lieu de reposer la question de l'enrichissement",
        f"{refait_.get('etat')} {refait_.get('erreur') or ''}")
    # L'ASSERTION ETAIT RETOURNEE, et elle certifiait une regression. Le plan
    # porte « parametres: etapes 7 » : le refait d'un brouillon rend BEL ET BIEN
    # en brouillon, quoi qu'en dise son etiquette. Ne pas le marquer lui faisait
    # perdre sa pastille, son bouton « refaire en soigne » — le seul geste qui
    # donne la version soignee — et faisait entrer sa duree, mesuree a un quart
    # des etapes, dans la table qui decide ou placer les rendus suivants.
    #
    # Le banc ne pouvait pas le voir : son plan d'essai portait « brouillon »
    # AVEC « etapes: 28 », c'est-a-dire un plan qui n'est jamais sorti
    # d'appliquer_parametres.
    dit(refait_.get("esquisse"),
        "un brouillon refait reste un brouillon, et le DIT",
        str(refait_.get("esquisse")))

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
