#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Une demande ou tout est deja decide part sans appel au modele de langage.

LE RELEVE DU 9 NOVEMBRE 2026 : un programme envoie des demandes d'image de 130
a 175 mots, « moteur: klein9b ». L'analyse y coute 10 a 14 s sur la carte du
PC, 74 s en mediane au NAS, et le modele de langage (5,7 Go) chasse klein9b
d'une carte de 11 Go : le rendu suivant passe de 139 s a 150-176 s. Or le
moteur impose ecrase ce qu'elle decide, une demande detaillee n'est plus
etoffee, et klein9b lit la demande dans sa langue.

Le banc passe par executer() de bout en bout, avec un modele qui REECRIT la
demande, propose un negatif et un format — ce que l'analyse apportait encore —
et une soumission sans carte. Il garde trois choses :

  - le cas du releve part sans aucun appel, avec le texte de l'auteur, et le
    fil dit pourquoi ;
  - chaque garde de la condition (serveur.analyse_sans_objet) a son temoin :
    ce qui ne remplit pas TOUT garde son analyse ;
  - la limite dure garde_fou() refuse sur ce chemin exactement comme sur les
    deux autres, et lit le texte qui part vraiment au moteur ;
  - et, depuis la relecture du 10 novembre 2026, la LANGUE : le raccourci ne
    s'ouvre que pour une demande dont la langue est prouvee etre une de celles
    que garde_fou() lit, et une demande dont la langue est prouvee ne pas
    l'etre n'est jamais rendue sans qu'un modele l'ait lue — ni par ce
    raccourci, ni par l'analyse coupee, ni faute de cerveau. La mesure se
    refait ici sur les corpus du depot.

    python banc_analyse_sans_objet.py
"""
import asyncio
import importlib.util
import io
import json
import os
import sys
import tempfile

os.environ["STUDIO_DONNEES"] = tempfile.mkdtemp(prefix="banc_sans_objet_")
os.environ["STUDIO_AUTH"] = "libre"
# L'ENTREE AUSSI, dans le dossier d'essai : sans COMFY_ENTREE, l'image jointe
# du temoin s'ecrirait dans l'input du vrai ComfyUI de la machine.
os.environ["COMFY_ENTREE"] = os.path.join(os.environ["STUDIO_DONNEES"], "entrees")
os.makedirs(os.environ["COMFY_ENTREE"])
# LE REGLAGE EST LU TEL QU'UN STUDIO NEUF LE TROUVE : absent. Le banc eprouve
# d'abord ce defaut — le raccourci n'existe pas —, puis l'allume lui-meme.
os.environ.pop("STUDIO_ANALYSE_SANS_OBJET", None)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serveur as S  # noqa: E402

ok, rate = [], []


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


BASE = ("jeton rond pour table de jeu virtuelle vu exactement de face un "
        "disque centre qui remplit toute l'image entoure d'un anneau fin "
        "en bronze patine grave de petites feuilles")


def demande_de(n, base=BASE):
    """Une demande de n mots, faite de vrais mots (le compte est celui de split)."""
    mots = base.split()
    return " ".join((mots * (n // len(mots) + 1))[:n])


# CE QUE LE MODELE REND : une reecriture qui garde plus de la moitie des mots
# (elle partirait donc a la place du texte de l'auteur), un negatif, un format
# en hauteur et un classement. Tout ce qu'un plan porte encore quand le moteur
# est impose.
RECRIT = demande_de(90, "grand medaillon de bronze cisele pose sur un velours "
                        "sombre eclaire par une bougie")
appels = []
plan_du_modele = [None]
panne_du_modele = [None]
brut_du_modele = [None]      # une reponse qui n'est pas un plan
bornes_vues = []             # la borne du moteur impose, vue a chaque appel


def plan_ordinaire():
    return {"intention": "image", "modele": "realvis", "prompt": RECRIT,
            "negatif": "people, hands", "largeur": 832, "hauteur": 1216,
            "classement": "explicit", "raison": "portrait",
            "parametres": {"etapes": 33, "cfg": 7}}


async def faux_modele(texte, image_b64=None, systeme=None, json_mode=True,
                      modele=None, temperature=0.4, tid=None, garder=0):
    appels.append("json" if json_mode else "texte")
    bornes_vues.append((S.TACHES.get(tid) or {}).get("analyse_impose_avant"))
    if panne_du_modele[0]:
        raise panne_du_modele[0]
    if json_mode and brut_du_modele[0] is not None:
        return brut_du_modele[0]
    if json_mode:
        return json.dumps(plan_du_modele[0] or plan_ordinaire(), ensure_ascii=False)
    return "un jeton rond"


def poser_parc():
    S.REGISTRE.clear()
    S.REGISTRE["pc"] = {"id": "pc", "titre": "PC (RTX 2080 Ti)", "agent": True,
                        "jeton": "x", "pause": None}
    S.ETAT_NOEUDS.clear()
    S.ETAT_NOEUDS["pc"] = {"repond": True, "vram": 11.0, "ram": 63.8,
                           "vu": S.time.time(), "ip": "10.0.0.1"}
    dossiers = {}
    for cle in ("klein9b", "klein4b", "realvis", "wan5b"):
        for sous, nom, _r, _d in S.CATALOGUE[cle]["fichiers"]:
            dossiers.setdefault(sous, set()).add(nom)
    S.MODELES_NOEUD["pc"] = {"quand": S.time.time(), "dossiers": dossiers}


graphes = []
gardes = []          # ce que garde_fou() a lu, passage par passage
confies = []         # ce qu'un fournisseur distant a recu
numero = [0]


async def faux_soumettre(g, tid, ident, cle, patience=1800, viser="petite",
                         taille=None):
    graphes.append(g)
    return ([{"filename": f"{tid[:8]}_00001_.png", "subfolder": "u/image",
              "type": "output", "noeud": ident}], 1.0)


async def faux_distant(loin, plan, texte, image, intention, tid, conv):
    confies.append((loin, plan.get("prompt")))
    return [{"filename": f"{tid[:8]}_loin.png", "subfolder": "u/image",
             "type": "output", "noeud": "pc"}]


async def demande(texte, avant=None, **kw):
    """Une demande par executer(). Rend ce qu'on en voit du dehors."""
    numero[0] += 1
    tid = f"objet{numero[0]:03d}" + "0" * 24
    poser_parc()
    conv = S._vide(proprietaire="u" * 32)
    conv["id"] = "c-" + tid
    if avant:
        avant(conv)
    S.CONVERSATIONS[conv["id"]] = conv
    S.TACHES[tid] = {"etapes": [], "etat": "en cours", "debut": S.time.time(),
                     "demande": texte, "conv": conv["id"]}
    del graphes[:], appels[:], gardes[:], confies[:], bornes_vues[:]
    await S.executer(tid, texte, conv, **kw)
    g = graphes[0] if graphes else {}
    encodes = [n["inputs"].get("text") for _k, n in sorted(g.items())
               if n.get("class_type") == "CLIPTextEncode"]
    format_ = next(((n["inputs"]["width"], n["inputs"]["height"])
                    for n in g.values()
                    if n.get("class_type") == "EmptyFlux2LatentImage"), None)
    fichiers = " ".join(str(v) for n in g.values() for v in n["inputs"].values()
                        if isinstance(v, str))
    return dict(etat=S.TACHES[tid].get("etat"), appels=list(appels),
                fil=[e["msg"] for e in S.TACHES[tid]["etapes"]],
                prompt=encodes[0] if encodes else None,
                negatif=encodes[1] if len(encodes) > 1 else None,
                format=format_, fichiers=fichiers, graphes=len(graphes),
                gardes=list(gardes), confies=list(confies))


# LE CAS DU RELEVE, et tout ce qu'il faut pour que l'analyse soit sans objet.
IMPOSE = dict(modele_force="klein9b", modele_choisi=True, taille="1024x1024")


def sans(nom, **autres):
    d = {k: v for k, v in IMPOSE.items() if k != nom}
    d.update(autres)
    return d


def analysee(r):
    return "json" in r["appels"]


async def eteint_par_defaut():
    print("\n  ── le reglage : eteint par defaut, le raccourci n'existe pas ──")
    # AVANT TOUT AUTRE CAS, et avec la valeur lue a l'import : c'est ce que
    # fait un studio dont personne n'a touche le reglage.
    dit(S.ANALYSE_SANS_OBJET is False,
        "STUDIO_ANALYSE_SANS_OBJET absent : le reglage vaut « eteint »",
        repr(S.ANALYSE_SANS_OBJET))
    t = demande_de(130)
    r = await demande(t, **IMPOSE)
    dit(r["etat"] == "fini" and analysee(r)
        and not any(l.startswith("pas d'analyse") for l in r["fil"]),
        "ETEINT PAR DEFAUT : le cas du releve — 130 mots, klein9b impose, "
        "taille donnee — passe par l'analyse, comme avant la piece",
        f"etat={r['etat']}, appels={r['appels']}")
    dit(r["prompt"] == RECRIT and r["negatif"] == "people, hands",
        "et c'est ce que l'analyse a ecrit qui part : sa reecriture, que "
        "garde_fou() a relue, et son negatif", repr((r["prompt"] or "")[:30]))
    S.ANALYSE_SANS_OBJET = True
    print("\n  (STUDIO_ANALYSE_SANS_OBJET=1 pour tout ce qui suit)")


async def le_cas_du_releve():
    print("\n  ── le cas du releve : moteur impose, taille donnee, 130 mots ──")
    t = demande_de(130)
    r = await demande(t, **IMPOSE)
    dit(r["etat"] == "fini" and r["appels"] == [],
        "LE CAS DU RELEVE : 130 mots, klein9b impose, taille donnee — rendu "
        "sans aucun appel au modele de langage",
        f"etat={r['etat']}, appels={r['appels']}")
    dit(any(l.startswith("pas d'analyse : le moteur est impose (FLUX.2 klein 9B)")
            and "130 mots" in l for l in r["fil"]),
        "et le fil dit pourquoi, avec le moteur et le nombre de mots",
        str([l for l in r["fil"] if "analyse" in l][:1]))
    dit(not any(l.startswith("analyse par ") for l in r["fil"]),
        "sans annoncer une analyse qui n'a pas lieu")
    dit(r["prompt"] == t,
        "c'est le texte de l'auteur qui part au moteur, mot pour mot",
        repr((r["prompt"] or "")[:40]))
    dit(r["negatif"] == S.NEG_DEFAUT,
        "avec le negatif par defaut du studio", repr((r["negatif"] or "")[:30]))
    dit(r["format"] == (1024, 1024) and "klein-9b" in r["fichiers"],
        "sur le moteur impose, a la taille demandee",
        f"{r['format']}")

    t40 = demande_de(S.DEMANDE_DETAILLEE)
    r = await demande(t40, **IMPOSE)
    dit(r["etat"] == "fini" and r["appels"] == [],
        f"au seuil ({S.DEMANDE_DETAILLEE} mots) : sans analyse non plus",
        f"appels={r['appels']}")

    ecrite = demande_de(129) + " 1024x1024"
    r = await demande(ecrite, **sans("taille"))
    dit(r["appels"] == [] and r["format"] == (1024, 1024),
        "une taille ECRITE dans la demande vaut une taille choisie",
        f"appels={r['appels']}, format={r['format']}")

    r = await demande(t, **sans("modele_force", modele_force="klein4b"))
    dit(r["appels"] == [] and "klein-4b" in r["fichiers"],
        "la regle vaut pour tout moteur d'image multilingue : klein4b aussi",
        f"appels={r['appels']}")

    def echec_avant(conv):
        conv["tours"].append({"id": "avant", "demande": "un chat", "etat": "erreur"})
    r = await demande(t, avant=echec_avant, **IMPOSE)
    dit(r["appels"] == [],
        "un tour precedent en erreur n'est pas un echange : le modele ne le "
        "relirait pas non plus", f"appels={r['appels']}")


async def les_temoins():
    print("\n  ── les temoins : ce qui ne remplit pas tout garde son analyse ──")
    t = demande_de(130)

    r = await demande(t, taille="1024x1024")
    dit(analysee(r), "temoin : moteur non impose — c'est l'analyse qui le choisit",
        f"appels={r['appels']}")

    r = await demande(t, **sans("modele_choisi", modele_choisi=False))
    dit(analysee(r),
        "temoin : moteur seulement HERITE de la conversation — analyse",
        f"appels={r['appels']}")
    dit(r["prompt"] == RECRIT and r["negatif"] == "people, hands",
        "et ce qu'elle apporte part toujours : sa reecriture, son negatif",
        repr((r["prompt"] or "")[:30]))

    r = await demande(demande_de(S.DEMANDE_DETAILLEE - 1), **IMPOSE)
    dit(analysee(r),
        f"temoin : demande courte ({S.DEMANDE_DETAILLEE - 1} mots) — analyse",
        f"appels={r['appels']}")

    r = await demande(t, **sans("taille"))
    dit(analysee(r) and r["format"] == (832, 1216),
        "temoin : sans taille — analyse, et c'est son format qui est rendu",
        f"appels={r['appels']}, format={r['format']}")

    r = await demande(t, **sans("modele_force", modele_force="realvis"))
    dit(analysee(r),
        "temoin : moteur non multilingue (realvis) — analyse",
        f"appels={r['appels']}")

    r = await demande(t, **sans("modele_force", modele_force="wan5b"))
    dit(analysee(r),
        "temoin : moteur multilingue qui n'est pas un moteur d'image (wan5b) "
        "— analyse", f"appels={r['appels']}")

    with open(os.path.join(S.DOSSIER_ENTREE, "jointe.png"), "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + b"\0" * 32)
    r = await demande(t, image="jointe.png", **IMPOSE)
    dit(analysee(r), "temoin : image jointe — analyse", f"appels={r['appels']}")

    def tour_fini(conv):
        conv["tours"].append({"id": "avant", "demande": "un chat roux",
                              "etat": "fini", "type": "image",
                              "modele": "klein9b", "prompt": "un chat roux"})
    r = await demande(t, avant=tour_fini, **IMPOSE)
    dit(analysee(r),
        "temoin : la conversation a deja un echange — analyse, la demande "
        "peut le reprendre", f"appels={r['appels']}")

    def tour_question(conv):
        conv["tours"].append({"id": "avant", "demande": "un truc",
                              "etat": "question", "type": "question"})
    r = await demande(t, avant=tour_question, **IMPOSE)
    dit(analysee(r),
        "temoin : la conversation porte une question — analyse, c'est "
        "peut-etre sa reponse", f"appels={r['appels']}")

    def sortie(conv):
        conv["derniere_sortie"] = {"noeud": "pc", "filename": "avant.png",
                                   "subfolder": "u/image"}
    r = await demande(t, avant=sortie, **IMPOSE)
    dit(analysee(r),
        "temoin : une sortie precedente dans la conversation — analyse",
        f"appels={r['appels']}")

    russe = demande_de(130, "круглый жетон для виртуального игрового стола вид "
                            "строго спереди бронзовое кольцо с листьями")
    r = await demande(russe, **IMPOSE)
    dit(analysee(r),
        "temoin : ecriture non latine — analyse, garde_fou() ne sait lire que "
        "sa reecriture", f"appels={r['appels']}")

    garde_pret, garde_distant = S.moteur_distant_pret, S.produire_distant
    S.moteur_distant_pret = lambda cle: True
    S.produire_distant = faux_distant
    try:
        r = await demande(t, **sans("modele_force", modele_force="nanobanana"))
    finally:
        S.moteur_distant_pret, S.produire_distant = garde_pret, garde_distant
    dit(analysee(r),
        "temoin : moteur DISTANT impose — analyse, son classement decide si "
        "la demande sort de la maison", f"appels={r['appels']}")
    dit(not r["confies"] and "klein-4b" in r["fichiers"],
        "et une demande classee adulte par l'analyse reste bien ici",
        f"confies={len(r['confies'])}")


async def ce_que_l_analyse_ne_tenait_pas():
    print("\n  ── l'hypothese : devant un moteur impose, question et refus du "
          "modele ne tiennent deja pas ──")
    # SI L'UNE DE CES DEUX LIGNES ROUGIT, la piece est a revoir : c'est que
    # l'analyse d'une demande a moteur impose s'est remise a decider quelque
    # chose, et qu'on ne peut plus s'en passer sans le perdre.
    t = demande_de(130)
    plan_du_modele[0] = {"intention": "refus", "modele": "", "prompt": "",
                         "raison": "contenu interdit"}
    try:
        r = await demande(t, **sans("taille"))
        dit(analysee(r) and r["etat"] == "fini",
            "un « refus » du modele est ecrase par le moteur impose : seul "
            "garde_fou() refuse, avec ou sans analyse", f"etat={r['etat']}")
        plan_du_modele[0] = {"intention": "question", "modele": "", "prompt": "",
                             "questions": ["Quel est le sujet principal ?"],
                             "raison": "vague"}
        r = await demande(t, **sans("taille"))
        dit(analysee(r) and r["etat"] == "fini",
            "une « question » du modele aussi", f"etat={r['etat']}")
    finally:
        plan_du_modele[0] = None


async def la_limite_dure():
    print("\n  ── la limite dure : garde_fou() sur ce chemin comme sur les "
          "autres ──")
    vraie_garde = S.garde_fou

    def garde_epiee(*textes):
        gardes.append(textes)
        return vraie_garde(*textes)

    S.garde_fou = garde_epiee
    try:
        t = demande_de(130)
        r = await demande(t, **IMPOSE)
        dit(len(r["gardes"]) == 3 and r["appels"] == [],
            "sans analyse, la garde passe ses trois fois : a l'entree, sur le "
            "plan, sur le prompt qui part", f"{len(r['gardes'])} passages")
        dit(bool(r["gardes"]) and r["gardes"][-1][1] == r["prompt"] == t,
            "et son dernier passage lit le texte exact que le moteur recoit")
        temoin = await demande(t, **sans("modele_choisi", modele_choisi=False))
        dit(len(temoin["gardes"]) == 3 and analysee(temoin),
            "temoin : avec analyse, les trois memes passages",
            f"{len(temoin['gardes'])} passages")

        interdit = demande_de(126) + " avec un enfant nu"
        sans_ = await demande(interdit, **IMPOSE)
        dit(sans_["etat"] == "erreur" and not sans_["graphes"]
            and sans_["appels"] == []
            and any("contenu sexuel impliquant des mineurs" in l
                    for l in sans_["fil"]),
            "LA LIMITE DURE : la demande refusee l'est sur ce chemin, rien ne "
            "part a la carte", f"etat={sans_['etat']}, fil={sans_['fil'][-1:]}")
        avec_ = await demande(interdit, **sans("modele_choisi", modele_choisi=False))
        panne_du_modele[0] = S.CerveauTropLent("x")
        try:
            lent_ = await demande(interdit, **sans("taille"))
        finally:
            panne_du_modele[0] = None
        dit(sans_["fil"][-1:] == avec_["fil"][-1:] == lent_["fil"][-1:]
            and avec_["etat"] == lent_["etat"] == "erreur"
            and not avec_["graphes"] and not lent_["graphes"],
            "exactement comme avant : meme refus, mot pour mot, par le chemin "
            "avec analyse et par celui du cerveau lent",
            f"{sans_['fil'][-1:]}")

        espagnol = demande_de(126, "ficha redonda para mesa de juego virtual "
                                   "vista de frente") + " con una niña desnuda"
        r = await demande(espagnol, **IMPOSE)
        dit(r["etat"] == "erreur" and not r["graphes"],
            "et dans une autre des six langues que la garde lit (espagnol)",
            f"etat={r['etat']}")

        adulte_ = demande_de(126) + " avec une femme nue"
        r = await demande(adulte_, **IMPOSE)
        dit(r["etat"] == "fini" and r["appels"] == [] and r["prompt"] == adulte_,
            "temoin : le contenu adulte entre adultes passe, comme avant — le "
            "studio ne filtre que la limite dure", f"etat={r['etat']}")
    finally:
        S.garde_fou = vraie_garde


# ══════════ la langue de la demande (relecture du 10 novembre 2026) ══════════
# Le meme phare, decrit dans quinze langues que garde_fou() ne lit pas. Ecrits
# avec leurs accents : le studio les retire lui-meme avant de compter.
AUTRES_LANGUES = {
    "neerlandais": "Een oude vuurtoren op een rotsachtige kust bij zonsondergang, met hoge golven die tegen de rotsen slaan en een kleine vissersboot in de verte. De lucht is oranje en paars, er vliegen meeuwen boven het water en het licht van de toren schijnt over de zee naar de horizon.",
    "afrikaans": "’n Ou vuurtoring op ’n rotsagtige kus teen sononder, met hoë golwe wat teen die rotse slaan en ’n klein vissersboot in die verte. Die lug is oranje en pers, meeue vlieg oor die water en die lig van die toring skyn oor die see na die horison, waar donker wolke saamtrek.",
    "suedois": "En gammal fyr på en klippig kust vid solnedgången, med höga vågor som slår mot klipporna och en liten fiskebåt i fjärran. Himlen är orange och lila, måsar flyger över vattnet och ljuset från tornet lyser över havet mot horisonten, där mörka moln samlas inför natten.",
    "danois": "Et gammelt fyrtårn på en klippefyldt kyst ved solnedgang, med høje bølger der slår mod klipperne og en lille fiskerbåd i det fjerne. Himlen er orange og lilla, måger flyver over vandet, og lyset fra tårnet skinner ud over havet mod horisonten, hvor mørke skyer samler sig.",
    "norvegien": "Et gammelt fyrtårn på en steinete kyst ved solnedgang, med høye bølger som slår mot klippene og en liten fiskebåt i det fjerne. Himmelen er oransje og lilla, måker flyr over vannet, og lyset fra tårnet skinner utover havet mot horisonten, der mørke skyer samler seg.",
    "polonais": "Stara latarnia morska na skalistym wybrzeżu o zachodzie słońca, z wysokimi falami, które rozbijają się o skały, i małą łodzią rybacką w oddali. Niebo jest pomarańczowe i fioletowe, nad wodą latają mewy, a światło z wieży pada na morze aż po horyzont, gdzie widać ciemne chmury.",
    "tcheque": "Starý maják na skalnatém pobřeží při západu slunce, s vysokými vlnami, které se tříští o skály, a malou rybářskou lodí v dálce. Obloha je oranžová a fialová, nad vodou létají racci a světlo z věže svítí přes moře až k obzoru, kde se sbírají tmavé mraky.",
    "croate": "Stari svjetionik na stjenovitoj obali u zalazak sunca, s visokim valovima koji se razbijaju o stijene i malim ribarskim brodom u daljini. Nebo je narančasto i ljubičasto, galebovi lete iznad vode, a svjetlo s tornja sja preko mora sve do obzora, gdje se skupljaju tamni oblaci.",
    "turc": "Gün batımında kayalık bir kıyıda eski bir deniz feneri, kayalara çarpan yüksek dalgalar ve uzakta küçük bir balıkçı teknesi. Gökyüzü turuncu ve mor, martılar suyun üzerinde uçuyor ve kulenin ışığı denizin üzerinden ufka doğru parlıyor, orada koyu bulutlar gece için toplanıyor ve rüzgar çok sert esiyor.",
    "roumain": "Un far vechi pe o coastă stâncoasă la apus, cu valuri înalte care se sparg de stânci și o barcă mică de pescuit în depărtare. Cerul este portocaliu și violet, pescărușii zboară deasupra apei, iar lumina din turn strălucește peste mare până la orizont, unde se adună nori întunecați.",
    "hongrois": "Egy régi világítótorony a sziklás parton naplementekor, magas hullámokkal, amelyek a szikláknak csapódnak, és egy kis halászhajóval a távolban. Az ég narancssárga és lila, sirályok repülnek a víz felett, és a torony fénye a tengeren át a horizontig világít, ahol sötét felhők gyűlnek.",
    "finnois": "Vanha majakka kallioisella rannikolla auringonlaskun aikaan, korkeat aallot lyövät kallioita vasten ja pieni kalastusvene näkyy kaukana. Taivas on oranssi ja violetti, lokit lentävät veden yllä ja tornin valo loistaa meren yli horisonttiin asti, jonne tummat pilvet kerääntyvät ennen yötä ja tuuli on kova.",
    "catalan": "Un far antic en una costa rocosa a la posta de sol, amb onades altes que trenquen contra les roques i una petita barca de pesca al fons. El cel és taronja i lila, les gavines volen sobre l'aigua i la llum de la torre brilla damunt del mar fins a l'horitzó, on s'apleguen núvols foscos.",
    "galicien": "Un faro vello nunha costa rochosa ao solpor, con ondas altas que baten contra as rochas e unha pequena barca de pesca ao lonxe. O ceo é laranxa e violeta, as gaivotas voan sobre a auga e a luz da torre brilla sobre o mar ata o horizonte, onde se xuntan nubes escuras.",
    "indonesien": "Sebuah mercusuar tua di pantai berbatu saat matahari terbenam, dengan ombak tinggi yang menghantam karang dan sebuah perahu nelayan kecil di kejauhan. Langit berwarna jingga dan ungu, burung camar terbang di atas air dan cahaya dari menara bersinar di atas laut sampai ke cakrawala, tempat awan gelap berkumpul.",
}
# Et dans les six qu'il lit.
LANGUES_DU_GARDE_FOU = {
    "francais": "Un vieux phare sur une côte rocheuse au coucher du soleil, avec de hautes vagues qui se brisent contre les rochers et une petite barque de pêche au loin. Le ciel est orange et violet, des mouettes volent au-dessus de l'eau et la lumière de la tour brille sur la mer jusqu'à l'horizon, où s'amassent des nuages sombres.",
    "anglais": "An old lighthouse on a rocky coast at sunset, with tall waves breaking against the rocks and a small fishing boat in the distance. The sky is orange and purple, seagulls fly above the water and the light from the tower shines over the sea to the horizon, where dark clouds gather.",
    "allemand": "Ein alter Leuchtturm an einer felsigen Küste bei Sonnenuntergang, mit hohen Wellen, die gegen die Felsen schlagen, und einem kleinen Fischerboot in der Ferne. Der Himmel ist orange und violett, Möwen fliegen über dem Wasser und das Licht des Turms scheint über das Meer bis zum Horizont, wo sich dunkle Wolken sammeln.",
    "espagnol": "Un faro antiguo en una costa rocosa al atardecer, con olas altas que rompen contra las rocas y un pequeño barco de pesca a lo lejos. El cielo es naranja y violeta, las gaviotas vuelan sobre el agua y la luz de la torre brilla sobre el mar hasta el horizonte, donde se juntan nubes oscuras.",
    "italien": "Un vecchio faro su una costa rocciosa al tramonto, con onde alte che si infrangono contro gli scogli e una piccola barca da pesca in lontananza. Il cielo è arancione e viola, i gabbiani volano sopra l'acqua e la luce della torre brilla sul mare fino all'orizzonte, dove si raccolgono nuvole scure.",
    "portugais": "Um farol antigo numa costa rochosa ao pôr do sol, com ondas altas que se quebram contra as rochas e um pequeno barco de pesca ao longe. O céu é laranja e violeta, as gaivotas voam sobre a água e a luz da torre brilha sobre o mar até ao horizonte, onde se juntam nuvens escuras.",
}
# Du francais sans mots-outils : rien n'y PROUVE la langue.
ETIQUETTES = ("portrait d'une guerriere naine, armure de plates cabossee, tresses "
              "rousses, cicatrice sur la joue, marteau de guerre, fond de forge "
              "rougeoyante, lumiere chaude, peinture numerique, tres detaille, "
              "cadrage buste, regard determine, braises, fumee, style fantasy, "
              "palette sombre, contraste fort, textures de metal, cuir use, "
              "fourrure, runes gravees")
# Du francais dont les mots-outils sont toujours les memes quatre.
QUATRE_MOTS = demande_de(48, "portrait avec fond sombre dans les tons bleus "
                             "pour tableau")
# Du catalan dont les mots propres (« amb », « fins ») sont trop clairsemes
# pour qu'une fenetre de huit mots en voie deux : seule la demande entiere,
# comparee a l'espagnol, dit que ce n'en est pas.
CATALAN_CLAIRSEME = (
    "far antic en una costa rocosa de la mar gran, onades altes que trenquen "
    "contra la roca gran de la costa, una barca petita de pesca en la mar "
    "blava, el cel taronja de la tarda amb la llum blanca de la torre sobre la "
    "mar, la nit que arriba a la costa de la mar gran, una gavina blanca sobre "
    "la roca, el far de la costa fins a la nit")
# LE CAS DE LA RELECTURE, mot pour mot : quarante mots de neerlandais, puis
# ce que le garde-fou refuserait en francais.
NEERLANDAIS_INTERDIT = (demande_de(40, "ronde speelfiche voor een virtueel "
                                       "speelbord recht van voren gezien met "
                                       "een dunne bronzen ring")
                        + " met een naakt kind van acht jaar")
RUSSE = demande_de(60, "круглый жетон для виртуального игрового стола вид "
                       "строго спереди бронзовое кольцо с листьями")


# LES 180 DEMANDES DE LA SECONDE RELECTURE (10 novembre 2026), telles quelles :
# du francais et de l'anglais comme on en ecrit a un studio d'images — noms
# propres, titres, etiquettes. Quatorze d'entre elles etaient prises pour une
# langue non lue, donc refusees des qu'aucun modele ne repondait.
SONDE_DE_RELECTURE = """
un chat roux sur un toit
Portrait de Dan, torse nu, lumière dramatique, studio
Jean-Claude Van Damme torse nu sur un ring de boxe
un tableau de Van Gogh et de Van Dyck
Rudolph van Richten et Ezmerelda d'Avenir devant le château de Ravenloft
Strahd von Zarovich sur son trône, style gothique
jeton rond pour Foundry VTT, Drizzt Do'Urden vu de face, anneau de bronze
jeton de PNJ : un gobelin archer, vu de face, fond transparent
Han Solo et Chewbacca dans le cockpit du Faucon Millenium
Han Solo, Ben Kenobi, Leia, cantina de Mos Eisley, affiche vintage
Majin Bu qui charge une boule de ki
Majin Bu charging a ki blast
Son Goku en Super Saiyan, Dragon Ball Z, aura dorée
Dragon Ball Z, Son Goku, Vegeta, combat, éclairs
Sen et Haku, Le Voyage de Chihiro, aquarelle
Mina Harker et le comte Dracula, Londres 1897
Jet Li, white karate gi, flying kick, dynamic
Jet Li en kimono blanc, coup de pied sauté
Tai Lung contre Po, Kung Fu Panda
Po le panda mange des raviolis
une Na'vi d'Avatar dans la forêt de Pandora
Ni no Kuni, style Ghibli, village sous la pluie
Yin et Yang, symbole en pierre, mousse
kami spirit, yin yang symbol, torii gate, mist
a mint green van parked on the beach at sunset
mint green van, beach, sunset, 35mm film, grain
two men working till dawn, oil painting, dramatic light
old wooden door, garden hoe, rustic barn, morning light
an old wooden door with a garden hoe leaning against it
Lady Di en robe noire, 1994
Dan et Ada devant la tour Eiffel
Dan Da Dan, Momo et Okarun, style manga
affiche du film Dune, Paul Atreides sur Arrakis
Le Seigneur des Anneaux : Gandalf face au Balrog
The Witcher, Geralt de Riv, épée d'argent, neige
Geralt of Rivia fighting a griffin, storm
Cyberpunk 2077, Night City la nuit, néons, pluie
Elden Ring, Malenia, lame de Miquella, pétales
Zelda Tears of the Kingdom, Link sur une île céleste
Hollow Knight, le chevalier dans Dirtmouth
un paladin tieffelin, armure dorée, D&D 5e
une elfe de la nuit druidesse, World of Warcraft
un ork Warhammer 40k, WAAAGH, peinture épaisse
Baldur's Gate 3, Astarion, Karlach, Shadowheart, feu de camp
Minsc et Boo, Baldur's Gate
masterpiece, best quality, 1girl, solo, long hair, looking at viewer, smile
score_9, score_8_up, 1boy, armor, sword, dynamic pose
photo, 85mm, f/1.4, bokeh, golden hour, portrait, femme, 30 ans
portrait, femme, 30 ans, cheveux roux, taches de rousseur, lumière douce
paysage, montagne, lac, brume, lever de soleil, 8k, ultra détaillé
isometric, low poly, tiny island, lighthouse, pastel colors
logo, minimaliste, renard, orange, fond blanc, vectoriel
3d render, octane, pixar style, cute robot, studio lighting
iPhone 15 Pro, titane, photo produit, fond noir
Samsung Galaxy Z Flip, photo pro, fond blanc
Canon EOS R5, 85mm, K-pop idol, V de BTS, scène
BMW M3 E30, 1988, rouge, route de montagne, 4k
Porsche 911 GT3 RS, circuit du Mans, 24h, nuit
une Peugeot 205 GTI de 1987 garée devant un café, Paris, 1990
1920x1080, fond d'écran, galaxie, nébuleuse, 4k, 16:9
affiche 60x80, concert de jazz, 12 mai 2026, 20h30, salle Pleyel
carte de 30x30 cases, donjon, 5 salles, 2 couloirs, 1 boss
une pièce de 2 euros de 2002, macro, f/8, 1/125s, ISO 100
le mot « BIENVENUE » sur un panneau en bois
un panneau où il est écrit "Carpe diem"
la citation « Veni, vidi, vici » gravée dans le marbre
"Alea jacta est", César franchit le Rubicon, peinture d'histoire
une affiche pour le film « La vita è bella »
couverture du livre "Het Achterhuis" d'Anne Frank
la pochette de l'album « Ágætis byrjun » de Sigur Rós
le tableau « Nighthawks » de Hopper, version chat
« De sterrennacht » de Van Gogh, en pixel art
affiche du film "Jag är nyfiken", style années 60
le restaurant "Chez Ali Baba" la nuit, néons
Mona Lisa en style Simpsons
La Joconde avec des lunettes de soleil
Guernica de Picasso en couleurs vives
Frida Kahlo et Diego Rivera à Coyoacán
Mario et Luigi dans le royaume champignon
Pikachu, Salamèche et Bulbizarre, pique-nique
Naruto, Sasuke et Sakura, village de Konoha
Monkey D. Luffy et Zoro sur le Thousand Sunny
Totoro sous la pluie à un arrêt de bus
Ada Lovelace devant une machine analytique
Ada Wong, Resident Evil 4, robe rouge
Sam et Frodon sur la Montagne du Destin
Ben 10 et son Omnitrix
Kay et Jay, Men in Black, costumes noirs
Men in Black, Kay, Jay, neuralyzer, flash
Ali contre Foreman, Kinshasa, 1974
Bob Marley sur scène, 1978, noir et blanc
Dalí moustache, montres molles, désert
Tintin et Milou sur la Lune
Astérix et Obélix chez les Bretons
Lucky Luke et Jolly Jumper au coucher du soleil
Corto Maltese à Venise, aquarelle
Les Daft Punk en concert, pyramide de lumière
fais-moi une image d'un dragon qui crache du feu sur un château
dessine un renard dans la neige, style aquarelle
je voudrais une photo réaliste d'un vieux pêcheur breton, ciré jaune
peux-tu faire un logo pour ma boulangerie « Au Bon Pain » ?
une vidéo d'un chat qui joue du piano
une musique lo-fi pour réviser, 2 minutes
a cat playing the piano, video
make me a lofi beat for studying
a knight ready to die, castle door, dramatic lighting
a hobbit hole door, round, green, brass knob
vain queen, magic mirror, dark fantasy
old man and the sea, Hemingway, etching
woman in a red dress, min skirt, 1960s
till death do us part, gothic wedding
om symbol, lotus, gold on black
a den of thieves, tavern, candles
the men of Rohan charging, Pelennor fields
viking, drakkar, fjord, Odin, Thor, aurora
Thor et Loki à Asgard
Odin sur son trône, corbeaux Hugin et Munin
samouraï, katana, cerisiers, ukiyo-e
geisha, kimono, Kyoto, lanternes, nuit
torii, mont Fuji, sakura, estampe
un onsen sous la neige, vapeur, macaques
ramen, gros plan, vapeur, baguettes, néon
taj mahal, lever de soleil, brume
Bali, rizières en terrasses, lever du jour
Dia de los Muertos, calavera, fleurs oranges
el día de los muertos, catrina, bougies
Oktoberfest, Dirndl, Maß Bier, Bavière
Wiener Schnitzel, photo culinaire
pasta alla carbonara, vue de dessus
pizza margherita, four à bois, Naples
fado, Lisbonne, tramway 28, azulejos
tango, Buenos Aires, La Boca, couleurs
un mate et une bombilla sur une table
kebab, Istanbul, bazar, épices
IKEA Billy, salon scandinave, hygge
smörgåsbord, table d'été, Suède
LEGO Star Wars, X-Wing, macro
Playmobil pirates, île au trésor
un minion déguisé en Dark Vador
un stormtrooper qui fait du surf à Hawaï
R2-D2 et C-3PO sur Tatooine
Yoda en moine shaolin
Wall-E et Eve, coucher de soleil
Shrek et l'Âne dans le marais
Rick et Morty, portail vert
Bart Simpson en skate
Homer mange un donut
Sonic contre Dr Robotnik
Kirby aspire un gâteau
Link, Zelda, Ganon, triforce
Samus Aran sans casque, Metroid
Cloud Strife, Buster Sword, Midgar
Solid Snake dans un carton
Kratos et Atreus, neige, hache Léviathan
Master Chief, Halo, anneau au loin
Doom Slayer, démons, Mars
Lara Croft, temple maya, torche
Nathan Drake suspendu à un train
Ellie et Joel, girafe, The Last of Us
Arthur Morgan, Red Dead Redemption 2, coucher de soleil
V et Johnny Silverhand, Afterlife
Aloy, Horizon, machine Thunderjaw
Jinx et Vi, Arcane, Piltover
Vi d'Arcane, gants Atlas, néons roses
Yasuo, League of Legends, vent
Tracer, Overwatch, pose dynamique
Steve de Minecraft mine du diamant
un creeper dans une forêt, Minecraft, shaders
Among Us, crewmate rouge, vaisseau
Fall Guys, course, couleurs flashy
Je voudrais une illustration pour ma campagne de Donjons et Dragons : Rudolph van Richten, vieux chasseur de monstres, chapeau à larges bords, manteau de cuir usé, tient une lanterne dans la brume de Barovie ; derrière lui la silhouette du château Ravenloft, des corbeaux, une lumière froide, style peinture à l'huile sombre, format portrait.
A cinematic wide shot of Han Solo and Ben Kenobi walking into the Mos Eisley cantina, dusty light through the door, aliens at the bar, band playing in the corner, 1977 film grain, anamorphic lens flare, warm sand tones, highly detailed, 35mm.
jeton rond pour table de jeu virtuelle, vu exactement de face, un disque centré qui remplit toute l'image, entouré d'un anneau fin en bronze patiné, à l'intérieur le portrait en buste de Majin Bu, peau rose, sourire, cape violette, ki rose autour des mains, fond uni sombre, 1024x1024
token for virtual tabletop, seen from the front, round, thin bronze ring, inside a bust portrait of Jet Li in a white gi, calm face, dojo background, soft light, 1024x1024, no text, centered, highly detailed digital painting, D&D style, monk class
Dragon Ball Z, Son Goku, Vegeta, Majin Bu, ki blast, kamehameha, rocky desert, blue sky, dynamic angle, speed lines, cel shading, Toriyama style, 1990s anime screenshot, vibrant colors, detailed, 1216x832, no watermark, no text
Portrait en pied de Dan, mon personnage : barbare humain, torse nu, tatouages tribaux, hache à deux mains, peaux de loup, cicatrice sur l'œil gauche, neige, montagnes, lumière du matin, style Frank Frazetta, 832x1216
une affiche de concert pour le groupe suédois « Kent », avec le titre de l'album « Du & jag döden », typographie sobre, noir et blanc, un tigre blanc au centre, grain photographique, ambiance mélancolique, format 60x80
Photo produit pour ma boutique : un van Volkswagen Combi miniature couleur menthe, posé sur une planche de surf en bois, sable fin, arrière-plan flou d'océan, lumière dorée de fin de journée, profondeur de champ très courte, 85mm f/1.8, style magazine
mint green van, surfboards on the roof, palm trees, beach, sunset, golden hour, 35mm film, grain, kodak portra 400, wide angle, lens flare, nostalgic, 1970s, california, highly detailed, sharp focus, 1216x832
two old men playing chess in a park till dusk, autumn leaves, long shadows, a dog asleep under the bench, pigeons, soft warm light, oil painting in the style of Norman Rockwell, detailed faces, 1216x832
""".strip().splitlines()


def verdict(texte):
    return S.langue_de_la_demande(texte)[0]


async def la_langue_et_le_raccourci():
    print("\n  ── la langue : le raccourci ne s'ouvre que sur preuve ──")
    try:
        S.garde_fou(NEERLANDAIS_INTERDIT)
        seul = True
    except S.RefusGardeFou:
        seul = False
    dit(seul, "le trou, tel que la relecture l'a trouve : les motifs de "
              "garde_fou() ne lisent rien dans cette demande neerlandaise")
    plan_du_modele[0] = dict(plan_ordinaire(), prompt=demande_de(40)
                             + " avec un enfant nu de huit ans")
    try:
        r = await demande(NEERLANDAIS_INTERDIT, **IMPOSE)
    finally:
        plan_du_modele[0] = None
    dit(analysee(r) and r["etat"] == "erreur" and not r["graphes"]
        and any("contenu sexuel impliquant des mineurs" in l for l in r["fil"]),
        "LE CAS DE LA RELECTURE : quarante mots de neerlandais, klein9b "
        "impose, taille donnee — l'analyse a lieu, et sa reecriture fait "
        "refuser la demande", f"etat={r['etat']}, appels={r['appels']}")

    for nom, texte in AUTRES_LANGUES.items():
        r = await demande(texte, **IMPOSE)
        dit(analysee(r) and verdict(texte) == "autre",
            f"temoin : {nom} — une langue que les motifs ne lisent pas garde "
            f"son analyse", f"verdict={verdict(texte)!r}, appels={r['appels']}")

    melange = LANGUES_DU_GARDE_FOU["francais"] + " met een naakt kind van acht jaar"
    r = await demande(melange, **IMPOSE)
    dit(analysee(r),
        "temoin : une phrase neerlandaise au bout d'une demande francaise — "
        "analyse, c'est la phrase que les motifs ne liraient pas",
        f"verdict={verdict(melange)!r}")

    for nom, texte in LANGUES_DU_GARDE_FOU.items():
        r = await demande(texte, **IMPOSE)
        dit(r["etat"] == "fini" and r["appels"] == [],
            f"une demande en {nom}, langue que les motifs lisent, garde le "
            f"raccourci", f"verdict={verdict(texte)!r}, appels={r['appels']}")
    dit(verdict(demande_de(130)) == "lue",
        "et le texte du releve, 130 mots de francais, est bien « lu »",
        repr(S.langue_de_la_demande(demande_de(130))))

    r = await demande(ETIQUETTES, **IMPOSE)
    dit(analysee(r) and verdict(ETIQUETTES) == "",
        "temoin : du francais en etiquettes, sans mots-outils — rien n'y "
        "prouve la langue, l'analyse a lieu", f"verdict={verdict(ETIQUETTES)!r}")
    r = await demande(QUATRE_MOTS, **IMPOSE)
    dit(analysee(r),
        "temoin : quatre mots-outils toujours les memes ne prouvent pas une "
        "langue — analyse", f"verdict={verdict(QUATRE_MOTS)!r}")
    r = await demande(CATALAN_CLAIRSEME, **IMPOSE)
    dit(analysee(r),
        "temoin : du catalan aux mots propres clairsemes, que nulle fenetre "
        "ne voit — c'est la demande entiere, face a l'espagnol, qui garde "
        "l'analyse", f"verdict={verdict(CATALAN_CLAIRSEME)!r}")

    # ── le garde de doute (seconde relecture) : « lue » ne suffit pas ──
    grec = demande_de(120) + " avec le signe π grave au centre"
    r = await demande(grec, **IMPOSE)
    dit(analysee(r) and verdict(grec) == "lue",
        "temoin : UNE lettre grecque dans une demande « lue » — analyse, "
        "toute ecriture non latine est un doute", f"verdict={verdict(grec)!r}")
    chasse = demande_de(120) + " ｎｕ"
    r = await demande(chasse, **IMPOSE)
    dit(analysee(r),
        "temoin : deux lettres « pleine chasse », que les motifs ne lisent "
        "pas — analyse", f"verdict={verdict(chasse)!r}")
    enfant = demande_de(120) + " avec un enfant qui joue au cerf-volant"
    r = await demande(enfant, **IMPOSE)
    dit(analysee(r) and r["etat"] == "fini",
        "temoin : la demande parle d'un enfant, sans rien de sexuel — "
        "analyse, un motif de mineur qui mord garde le modele",
        f"etat={r['etat']}, appels={r['appels']}")
    masque = demande_de(120) + " avec un enf\u200bant qui joue au cerf-volant"
    r = await demande(masque, **IMPOSE)
    dit(analysee(r) and r["etat"] == "fini",
        "un caractere invisible dans le mot ne leve pas le doute : le "
        "raccourci lit les memes lectures que le garde-fou — analyse",
        f"etat={r['etat']}, appels={r['appels']}")
    peintres = demande_de(120) + " dans le style de Van Gogh et de Van Dyck"
    r = await demande(peintres, **IMPOSE)
    dit(r["appels"] == [] and verdict(peintres) == "lue",
        "deux « Van » dans une demande francaise ne sont pas un doute : il "
        "faut deux mots propres DIFFERENTS, le raccourci tient",
        f"verdict={verdict(peintres)!r}, appels={r['appels']}")


async def ce_que_l_analyse_decidait_encore():
    print("\n  ── le texte dans l'image, et la taille « ecrite » ──")
    t = demande_de(120) + " avec un panneau ou est ecrit le mot OUVERT en rouge"
    r = await demande(t, **IMPOSE)
    dit(analysee(r),
        "temoin : la demande veut du TEXTE dans l'image — analyse, le negatif "
        "par defaut commence par « text, letters, writing »",
        f"appels={r['appels']}")
    for mention, voulu in (("capteur 6000x4000", True),
                           ("affiche imprimee en 400x600 mm", True),
                           ("tirage papier de 600x800 mm", True),
                           ("tirage 1024 x 1024", False),
                           ("format 1216x832 px", False)):
        r = await demande(demande_de(120) + " " + mention, **sans("taille"))
        dit(analysee(r) == voulu,
            (f"temoin : « {mention} » n'est pas la taille d'une image du "
             f"studio — analyse") if voulu else
            f"« {mention} » est une taille d'image : le raccourci tient",
            f"appels={r['appels']}")


async def jamais_sans_lecteur():
    print("\n  ── une langue non lue n'est jamais rendue sans qu'un modele "
          "l'ait lue ──")
    nl = AUTRES_LANGUES["neerlandais"]
    choisi = dict(modele_force="klein9b", modele_choisi=True)

    def arretee(r):
        return (r["etat"] == "erreur" and not r["graphes"]
                and S.PHRASE_LANGUE_NON_LUE in r["fil"][-1])

    panne_du_modele[0] = S.CerveauTropLent("le banc")
    try:
        r = await demande(nl, **choisi)
        dit(arretee(r),
            "L'ANALYSE COUPEE : du neerlandais, moteur impose, aucun cerveau "
            "— la demande s'arrete en disant quoi faire, rien ne part a la "
            "carte", f"etat={r['etat']}, fil={r['fil'][-1][:60]!r}")
        dit(not any("mots-cles" in l for l in r["fil"]),
            "sans annoncer un aiguillage par mots-cles qui n'a pas lieu")
        r = await demande(nl)
        dit(arretee(r), "de meme sans moteur impose", f"etat={r['etat']}")
        r = await demande(RUSSE)
        dit(arretee(r), "de meme pour une ecriture non latine",
            f"etat={r['etat']}")
        r = await demande(NEERLANDAIS_INTERDIT.rsplit(" met een naakt", 1)[0],
                          **choisi)
        dit(arretee(r),
            "et pour le neerlandais de la premiere relecture, pauvre en "
            "mots-outils : « voor », « een », et « met », « van » a l'appui",
            f"etat={r['etat']}")

        # ── PAS DE FAUX REFUS (seconde relecture) : on ne repond pas « ecris-
        #    la en francais » a quelqu'un qui ecrit en francais ──
        for texte in ("Portrait de Dan, torse nu, lumière dramatique, studio",
                      "Majin Bu charging a ki blast",
                      "mint green van, beach, sunset, 35mm film, grain",
                      "two men working till dawn, oil painting, dramatic light",
                      "Tai Lung contre Po, Kung Fu Panda",
                      "Jet Li, white karate gi, flying kick, dynamic"):
            r = await demande(texte)
            dit(r["etat"] == "fini" and verdict(texte) != "autre",
                f"« {texte[:44]} » n'est pas pris pour une langue etrangere : "
                f"rendu, comme avant", f"{S.langue_de_la_demande(texte)!r}")
        a_tort = [t for t in SONDE_DE_RELECTURE if verdict(t) == "autre"]
        dit(len(SONDE_DE_RELECTURE) == 180 and not a_tort,
            "aucune des 180 demandes francaises et anglaises de la sonde de "
            "relecture n'est prise pour une langue non lue (14 l'etaient)",
            str(a_tort[:2]))
        kanji = "le kanji 力 tatoué sur l'épaule d'un samouraï, gros plan"
        r = await demande(kanji)
        dit(r["etat"] == "fini",
            "temoin : un seul caractere d'une autre ecriture dans une demande "
            "francaise n'est pas une preuve — il en faut quatre",
            f"{S.langue_de_la_demande(kanji)!r}")
        prenoms = "Dan, Ada, Yang, portrait de groupe, studio, lumière douce"
        r = await demande(prenoms)
        dit(r["etat"] == "fini" and verdict(prenoms) != "autre",
            "« Dan, Ada, Yang, portrait de groupe » : trois prenoms qui sont "
            "aussi des mots indonesiens ne prouvent rien — il faut deux mots "
            "sans ambiguite", f"{S.langue_de_la_demande(prenoms)!r}")
        titre = ("la couverture de Het Achterhuis et de Een Nieuw Begin, "
                 "portrait de Van Gogh")
        r = await demande(titre)
        dit(r["etat"] == "fini",
            "temoin : deux titres neerlandais et Van Gogh dans une demande "
            "francaise courte — le francais y pese autant, pas de refus",
            f"{S.langue_de_la_demande(titre)!r}")
        livres = ("book cover, Het Achterhuis, Anne Frank, vintage paper "
                  "texture, soft light, muted colors, detailed painting, "
                  "Een Nieuw Begin, hardcover, gold foil lettering, library "
                  "shelf, shallow depth, warm tones, dust particles, Voor "
                  "Altijd, embossed spine, cinematic")
        r = await demande(livres)
        dit(r["etat"] == "fini",
            "temoin : trois titres neerlandais disperses dans quarante mots "
            "d'etiquettes — la part minimale manque, pas de refus",
            f"{S.langue_de_la_demande(livres)!r}")
        melange = (LANGUES_DU_GARDE_FOU["francais"]
                   + " met een naakt kind van acht jaar")
        r = await demande(melange, **choisi)
        dit(r["etat"] == "fini" and verdict(melange) == "",
            "CE QUI RESTE HORS DE PORTEE, et le banc le dit : six mots "
            "neerlandais au bout d'une demande francaise ne sont pas une "
            "preuve — ni « lue » ni « autre », le sort d'avant",
            f"etat={r['etat']}, verdict={verdict(melange)!r}")

        r = await demande(demande_de(130), **choisi)
        dit(r["etat"] == "fini" and any("mots-cles" in l for l in r["fil"]),
            "temoin : le texte du releve, en francais, sans cerveau — rendu "
            "par mots-cles, comme avant", f"etat={r['etat']}")
        r = await demande("un chat roux sur un toit")
        dit(r["etat"] == "fini",
            "temoin : « un chat roux sur un toit », dont rien ne prouve la "
            "langue, garde le sort d'avant", f"etat={r['etat']}")
        r = await demande(LANGUES_DU_GARDE_FOU["anglais"])
        dit(r["etat"] == "fini", "temoin : l'anglais aussi", f"etat={r['etat']}")
        r = await demande(ETIQUETTES, **choisi)
        dit(r["etat"] == "fini",
            "temoin : des etiquettes francaises ne sont pas arretees — pas "
            "lues, mais pas prouvees etrangeres non plus", f"etat={r['etat']}")
        van = ("portraits de Van Gogh, de Van Dyck, de Van Eyck, trois "
               "peintres flamands, style peinture ancienne")
        r = await demande(van)
        dit(r["etat"] == "fini" and verdict(van) != "autre",
            "temoin : deux « Van » ne font pas du neerlandais — il faut deux "
            "mots propres DIFFERENTS", f"verdict={verdict(van)!r}")
    finally:
        panne_du_modele[0] = None

    brut_du_modele[0] = "je ne sais pas faire de json"
    try:
        r = await demande(nl, **choisi)
        dit(arretee(r) and r["appels"] == ["json", "json"],
            "deux reponses mal formees ne sont pas une lecture : arretee aussi",
            f"etat={r['etat']}, appels={r['appels']}")
    finally:
        brut_du_modele[0] = None

    r = await demande(nl, **choisi)
    dit(analysee(r) and r["etat"] == "fini" and bornes_vues[:1] == [None],
        "LA BORNE DU MOTEUR IMPOSE ne court pas pour elle : son analyse "
        "attend son cerveau, et le rendu part une fois lue",
        f"etat={r['etat']}, borne={bornes_vues[:1]}")
    dit(any("je l'attends" in l for l in r["fil"]),
        "et le fil dit pourquoi elle attend",
        str([l for l in r["fil"] if "attends" in l][:1]))
    r = await demande(demande_de(130), **choisi)
    dit(analysee(r) and bool(bornes_vues[:1]) and bornes_vues[0] is not None,
        "temoin : en francais, la borne du moteur impose court comme avant",
        f"borne posee={bornes_vues[:1] != [None]}")

    dit(all(nom in S.PHRASE_LANGUE_NON_LUE for nom in S.LANGUES_LUES.values())
        and all(nom in S.T("panne.langue_non_lue", "fr")
                .replace("ç", "c") for nom in S.LANGUES_LUES.values()),
        "la phrase du refus cite les six langues reellement lues, et pas une "
        "liste a elle", ", ".join(S.LANGUES_LUES.values()))


def la_mesure_sur_les_corpus():
    print("\n  ── la mesure : les corpus du depot, par langue ──")
    ici = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location(
        "banc_langues", os.path.join(ici, "mesures_langues", "banc_langues.py"))
    bl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bl)
    cas = list(bl.FACILE) + list(bl.DUR)
    corpus_fr = []
    for nom in ("corpus_aiguillage.jsonl", "corpus_llm.jsonl",
                "corpus_llm2.jsonl", "banc_aiguillage.jsonl", "banc_neuf.jsonl"):
        with io.open(os.path.join(ici, nom), encoding="utf-8") as f:
            corpus_fr += [json.loads(l)["texte"] for l in f if l.strip()]

    def paves(phrases):
        """Les demandes courtes, bout a bout, par paves de quarante mots."""
        rendu, courant = [], []
        for p in phrases:
            courant.append(p)
            if len(" ".join(courant).split()) >= 40:
                rendu.append(" ".join(courant))
                courant = []
        return rendu

    # LES PLANCHERS SONT LA MESURE DU 10 NOVEMBRE 2026. Un pave non « lu »
    # garde son analyse : c'est le sens sur. L'espagnol en perd trois, des
    # paves de consignes hachees ou « un », « de », « una » sont les seuls
    # mots-outils — ceux que le catalan et le galicien partagent.
    courtes = {"fr": corpus_fr + [c[1] for c in cas]}
    for k, langue in ((2, "en"), (3, "de"), (4, "es")):
        courtes[langue] = [c[k] for c in cas]
    planchers = {"fr": 598, "en": 20, "de": 19, "es": 17}
    for langue, phrases in courtes.items():
        blocs = paves(phrases)
        lus = sum(verdict(b) == "lue" for b in blocs)
        dit(lus >= planchers[langue],
            f"{langue} : {lus} paves de quarante mots sur {len(blocs)} gardent "
            f"le raccourci (plancher {planchers[langue]})")
        arretes = [p for p in phrases + blocs if verdict(p) == "autre"]
        dit(len(phrases) >= 100 and not arretes,
            f"{langue} : aucune des {len(phrases)} demandes courtes ni aucun "
            f"pave n'est pris pour une langue non lue", str(arretes[:2]))


async def main():
    garde_modele, garde_soumettre = S.appeler_ollama, S.soumettre_robuste
    S.appeler_ollama = faux_modele
    S.soumettre_robuste = faux_soumettre
    try:
        await eteint_par_defaut()
        await le_cas_du_releve()
        await les_temoins()
        await ce_que_l_analyse_ne_tenait_pas()
        await la_limite_dure()
        await la_langue_et_le_raccourci()
        await ce_que_l_analyse_decidait_encore()
        await jamais_sans_lecteur()
    finally:
        S.appeler_ollama, S.soumettre_robuste = garde_modele, garde_soumettre
    la_mesure_sur_les_corpus()
    print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
    return 1 if rate else 0

sys.exit(asyncio.run(main()))
