#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sans modele de langage, une image reste une image, a un format d'image.

LE DEFAUT MESURE LE 10 NOVEMBRE 2026, sur le chemin que 206 demandes a moteur
impose ont pris en 72 h (analyse coupee par la borne de 45 s) : le repli par
mots-cles, secours(), lisait de la musique dans « son  » — « son tablier »,
« une plus grande maison » — et une video dans « anim » — « un animal ». Il
posait alors 0x0 ou 1280x704, et le moteur d'image impose gardait ces
dimensions : une image en 512x512 ou en 1280x704, sans que rien ne le dise.

Deux corrections, et ce banc tient les deux separement :

  - executer() ne garde plus, sous un moteur d'image impose, les dimensions
    d'une musique ou d'une video — que ce soit le repli ou le modele qui ait
    lu la demande ainsi ;
  - secours() lit ses mots de plus pres : « son » avec un article, « anim »
    la ou il dit animer — dans les quatre langues du banc traduit, pas
    seulement en francais —, « clip » en mot entier.

Il passe par executer() de bout en bout, avec un modele qui ne repond pas
(l'analyse coupee) et une soumission sans carte, puis mesure secours() sur
les corpus etiquetes du depot.

    python banc_repli_mots_cles.py
"""
import asyncio
import importlib.util
import io
import json
import os
import sys
import tempfile

os.environ["STUDIO_DONNEES"] = tempfile.mkdtemp(prefix="banc_repli_")
os.environ["STUDIO_AUTH"] = "libre"
os.environ["COMFY_ENTREE"] = os.path.join(os.environ["STUDIO_DONNEES"], "entrees")
os.makedirs(os.environ["COMFY_ENTREE"])
ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import serveur as S  # noqa: E402

ok, rate = [], []


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


def demande_de(n, base):
    """Une demande de n mots, faite de vrais mots (le compte est celui de split)."""
    mots = base.split()
    return " ".join((mots * (n // len(mots) + 1))[:n])


# LE CAS DU RELEVE : une description d'image, longue, avec un possessif.
TABLIER = demande_de(130, "un forgeron nain devant sa forge rougeoyante avec son "
                          "tablier de cuir epais et de lourdes pinces dans une "
                          "caverne de pierre sombre")
ANIMAL = demande_de(130, "un animal fantastique a plumes bleues perche sur un "
                         "rocher moussu au bord d'un lac de montagne")
AFFICHE = demande_de(60, "une affiche ancienne pour un concert de musique de "
                         "chambre avec un violoncelle dessine a l'encre")
EXTRAIT = demande_de(60, "une image fixe comme tiree d'une video de surveillance "
                         "granuleuse dans un parking desert la nuit")

appels = []
plan_du_modele = [None]      # None : le modele ne repond pas (analyse coupee)


async def faux_modele(texte, image_b64=None, systeme=None, json_mode=True,
                      modele=None, temperature=0.4, tid=None, garder=0):
    appels.append("json" if json_mode else "texte")
    if plan_du_modele[0] is None:
        raise S.CerveauTropLent("le banc")
    if json_mode:
        return json.dumps(plan_du_modele[0], ensure_ascii=False)
    return "un forgeron"


def poser_parc():
    S.REGISTRE.clear()
    S.REGISTRE["pc"] = {"id": "pc", "titre": "PC (RTX 2080 Ti)", "agent": True,
                        "jeton": "x", "pause": None}
    S.ETAT_NOEUDS.clear()
    S.ETAT_NOEUDS["pc"] = {"repond": True, "vram": 11.0, "ram": 63.8,
                           "vu": S.time.time(), "ip": "10.0.0.1"}
    dossiers = {}
    for cle in ("klein9b", "klein4b", "wan5b", "audio"):
        for sous, nom, _r, _d in S.CATALOGUE[cle]["fichiers"]:
            dossiers.setdefault(sous, set()).add(nom)
    S.MODELES_NOEUD["pc"] = {"quand": S.time.time(), "dossiers": dossiers}


graphes = []
numero = [0]


async def faux_soumettre(g, tid, ident, cle, patience=1800, viser="petite",
                         taille=None):
    graphes.append((cle, g))
    return ([{"filename": f"{tid[:8]}_00001_.png", "subfolder": "u/image",
              "type": "output", "noeud": ident}], 1.0)


async def demande(texte, avant=None, **kw):
    """Une demande par executer(). Rend ce qu'on en voit du dehors."""
    numero[0] += 1
    tid = f"repli{numero[0]:03d}" + "0" * 24
    poser_parc()
    conv = S._vide(proprietaire="u" * 32)
    conv["id"] = "c-" + tid
    if avant:
        avant(conv)
    S.CONVERSATIONS[conv["id"]] = conv
    S.TACHES[tid] = {"etapes": [], "etat": "en cours", "debut": S.time.time(),
                     "demande": texte, "conv": conv["id"]}
    del graphes[:], appels[:]
    await S.executer(tid, texte, conv, **kw)
    cle, g = graphes[0] if graphes else (None, {})
    format_ = next(((n["inputs"]["width"], n["inputs"]["height"])
                    for n in g.values()
                    if n.get("class_type") == "EmptyFlux2LatentImage"), None)
    tour = next((t for t in conv["tours"] if t.get("id") == tid), {})
    return dict(etat=S.TACHES[tid].get("etat"), moteur=cle, format=format_,
                type=tour.get("type"),
                fil=[e["msg"] for e in S.TACHES[tid]["etapes"]])


IMPOSE = dict(modele_force="klein9b", modele_choisi=True)


async def le_cas_du_releve():
    print("\n  ── le cas du releve : moteur d'image impose, analyse coupee, "
          "aucune taille ──")
    r = await demande(TABLIER, **IMPOSE)
    dit(r["etat"] == "fini" and r["format"] == (1216, 832) and r["moteur"] == "klein9b",
        "LE CAS DU RELEVE : « son tablier », klein9b impose, analyse coupee — "
        "l'image sort au format d'une image, 1216x832",
        f"etat={r['etat']}, format={r['format']}")
    dit(any("aiguillage par mots-cles" in l for l in r["fil"]),
        "et c'est bien le chemin sans modele qui a ete pris",
        str([l for l in r["fil"] if "mots-cles" in l][:1]))
    r = await demande(ANIMAL, **IMPOSE)
    dit(r["format"] == (1216, 832),
        "« un animal », meme chemin : 1216x832, pas le format d'une video",
        f"format={r['format']}")

    r = await demande(TABLIER, taille="1024x1024", **IMPOSE)
    dit(r["format"] == (1024, 1024),
        "temoin : une taille donnee est respectee", f"format={r['format']}")
    r = await demande(TABLIER + " en 832x1216", **IMPOSE)
    dit(r["format"] == (832, 1216),
        "temoin : une taille ecrite dans la demande aussi", f"format={r['format']}")


async def les_dimensions_d_une_autre_modalite():
    print("\n  ── sous un moteur d'image impose, les dimensions d'une musique ou "
          "d'une video ne survivent pas ──")
    # Ici le repli lit VRAIMENT une musique ou une video — « musique »,
    # « video » sont dans la demande — et c'est executer() qui doit tenir.
    dit(S.secours(AFFICHE)["intention"] == "audio"
        and S.secours(EXTRAIT)["intention"] == "video",
        "les deux demandes d'essai sont bien lues musique et video par le repli",
        f"{S.secours(AFFICHE)['intention']}, {S.secours(EXTRAIT)['intention']}")
    r = await demande(AFFICHE, **IMPOSE)
    dit(r["etat"] == "fini" and r["format"] == (1216, 832),
        "une demande lue comme une MUSIQUE par le repli, moteur d'image "
        "impose : 1216x832, pas 512x512", f"format={r['format']}")
    r = await demande(EXTRAIT, **IMPOSE)
    dit(r["etat"] == "fini" and r["format"] == (1216, 832),
        "une demande lue comme une VIDEO par le repli, moteur d'image "
        "impose : 1216x832, pas 1280x704", f"format={r['format']}")
    r = await demande(AFFICHE, taille="1024x1024", **IMPOSE)
    dit(r["format"] == (1024, 1024),
        "temoin : la taille donnee prime toujours", f"format={r['format']}")

    plan_du_modele[0] = {"intention": "audio", "modele": "audio",
                         "prompt": AFFICHE, "tags_audio": "chamber music",
                         "largeur": 0, "hauteur": 0, "raison": "musique"}
    try:
        r = await demande(AFFICHE, **IMPOSE)
        dit(r["etat"] == "fini" and r["format"] == (1216, 832),
            "la meme regle quand c'est le MODELE qui a lu une musique",
            f"format={r['format']}")
        plan_du_modele[0] = {"intention": "image", "modele": "realvis",
                             "prompt": TABLIER, "largeur": 832, "hauteur": 1216,
                             "raison": "portrait"}
        r = await demande(TABLIER, **IMPOSE)
        dit(r["format"] == (832, 1216),
            "temoin : le format que le modele propose pour une IMAGE est "
            "garde", f"format={r['format']}")

        def sortie(conv):
            conv["derniere_sortie"] = {"noeud": "pc", "filename": "avant.png",
                                       "subfolder": "u/image"}
        # Quarante-cinq mots : au-dela de DEMANDE_DETAILLEE, rien n'est
        # etoffe, et le faux modele n'a pas a savoir ecrire.
        retouche = demande_de(45, "ajoute un grand chapeau de paille au "
                                  "forgeron devant sa forge")
        plan_du_modele[0]["prompt"] = retouche
        r = await demande(retouche, avant=sortie, **IMPOSE)
        dit(r["etat"] == "fini" and r["format"] == (832, 1216),
            "temoin : une analyse basculee en retouche par le code garde son "
            "format d'image — seules musique et video le perdent",
            f"etat={r['etat']}, format={r['format']}")
    finally:
        plan_du_modele[0] = None


async def les_vraies_demandes():
    print("\n  ── moteur libre, analyse coupee : ce que le repli decide ──")
    r = await demande("un forgeron nain devant sa forge avec son tablier de cuir")
    dit(r["etat"] == "fini" and r["type"] == "image" and r["format"] == (1216, 832),
        "« son tablier » n'est pas une musique : une image, en 1216x832",
        f"etat={r['etat']}, type={r['type']}, format={r['format']}")
    r = await demande("un animal fantastique a plumes bleues sur un rocher")
    dit(r["etat"] == "fini" and r["type"] == "image",
        "« un animal » n'est pas une video : une image",
        f"etat={r['etat']}, type={r['type']}")
    r = await demande("une musique instrumentale douce au piano")
    dit(r["etat"] == "fini" and r["type"] == "audio" and r["moteur"] in S.MODELES_AUDIO,
        "temoin : une vraie demande de musique reste une musique",
        f"etat={r['etat']}, type={r['type']}, moteur={r['moteur']}")
    r = await demande("une video d'un dragon qui survole une vallee")
    dit(r["etat"] == "fini" and r["type"] == "video" and r["moteur"] == "wan5b",
        "temoin : une vraie demande de video reste une video",
        f"etat={r['etat']}, type={r['type']}, moteur={r['moteur']}")


def les_mots():
    print("\n  ── secours(), mot par mot ──")
    attendus = [
        ("un forgeron avec son tablier", "image", "le possessif « son »"),
        ("un cerf devant une plus grande maison au bord du lac", "image",
         "« maison »"),
        ("un chevalier et son armure, le poisson rouge de la saison", "image",
         "« poisson », « saison »"),
        ("un animal hybride jamais vu", "image", "« animal »"),
        ("une foret animee par le vent", "image", "« animee par »"),
        ("une eclipse de lune au-dessus de la mer", "image", "« eclipse »"),
        ("un son de cloche dans le lointain", "audio", "« un son de »"),
        ("le son des vagues sur les galets", "audio", "« le son des »"),
        ("une bande-son epique pour un combat", "audio", "« bande-son »"),
        ("une chanson triste sur la pluie", "audio", "« chanson »"),
        ("anime une scene de bataille navale", "video", "« anime une scene »"),
        ("une animation de dragon en vol", "video", "« animation »"),
        ("une sequence animee d'une tempete en mer", "video", "« sequence animee »"),
        ("un clip de rock dans un hangar", "video", "« clip »"),
        # ── la relecture du 10 novembre 2026 : ce que le premier resserrage
        #    avait fait reculer, en francais et ailleurs ──
        ("son de pluie sur un toit", "audio", "« son de » en tete de demande"),
        ("une boucle animee de flammes", "video", "« une boucle animee »"),
        ("un logo anime pour ma chaine", "video", "« un logo anime »"),
        ("animate a cat running in a field", "video", "anglais, « animate »"),
        ("a short animated teaser", "video", "anglais, « animated »"),
        ("animiere eine Katze die rennt", "video", "allemand, « animiere »"),
        ("una animacion de un gato", "video", "espagnol, « animacion »"),
        ("un pequeno teaser animado", "video", "espagnol, « teaser animado »"),
        ("an animal in the forest", "image", "anglais, « animal »"),
        ("un animal en el bosque", "image", "espagnol, « animal »"),
        ("una ciudad muy animada de noche", "image",
         "espagnol, « animada » sans nom de film"),
        ("une ville animee un soir de marche", "image",
         "« une ville animee » sans nom de film"),
    ]
    for texte, attendu, quoi in attendus:
        rendu = S.secours(texte)["intention"]
        dit(rendu == attendu,
            f"{quoi} : {attendu}" + (" (temoin)" if attendu != "image" else ""),
            f"« {texte} » -> {rendu}")
    dit(S.secours("un personnage de style anime")["modele"] == "pony"
        and S.secours("une foret animee par le vent")["modele"] == "klein4b",
        "le style « anime » va a Pony, « animee par le vent » non",
        f"{S.secours('un personnage de style anime')['modele']}, "
        f"{S.secours('une foret animee par le vent')['modele']}")
    dit(S.secours("anime cette photo", "image")["intention"] == "video_image"
        and S.secours("un animal sur cette photo", "image")["intention"] == "edition",
        "avec une image jointe, « anime cette photo » l'anime toujours "
        "(temoin), et « un animal sur cette photo » est une retouche, plus "
        "une video")
    jointes = [("animate this photo of my cat pls", "anglais"),
               ("animier bitte dieses Foto von meiner Katze", "allemand"),
               ("anima esta foto de mi gato porfa", "espagnol"),
               ("quiero que esta foto se vuelva animada", "espagnol, l'adjectif"),
               ("que cette photo devienne animee", "francais, l'adjectif")]
    for texte, quoi in jointes:
        rendu = S.secours(texte, "image")["intention"]
        dit(rendu == "video_image",
            f"image jointe, {quoi} : « {texte} » l'anime", f"-> {rendu}")


def un_style_n_est_pas_une_animation():
    print("\n  ── un style n'est pas une animation (seconde relecture) ──")
    # LES PHRASES DE LA SONDE DU 10 NOVEMBRE 2026. Vingt de ces demandes
    # d'image sur vingt-deux partaient en video chez Wan quand aucun cerveau
    # ne repondait — vingt-deux sur vingt-deux sur main —, et les cinq
    # retouches en animation de la photo jointe.
    images = [
        "un chat roux en style dessin animé",
        "portrait de ma fille façon dessin animé Disney",
        "un personnage de dessin animé des années 90, fond blanc",
        "transforme-moi en personnage de dessin animé",
        "un renard, style dessin animé, couleurs vives",
        "affiche de film, style dessin animé japonais",
        "un logo animé par la passion du vin",
        "a cat, animated movie style",
        "Pixar animated style portrait of a grandmother",
        "a still from a 90s animated series, city at night",
        "poster in the style of an animated Disney film",
        "un rendu animé et joyeux d'une place de village",
        "une intro animée par un conférencier, photo de scène",
        "un loup dessiné comme dans un film d'animation",
        "personnage style animation 3D Pixar, fond uni",
        "illustration style film d'animation Ghibli",
        "a knight, animation style, flat colors",
        "Son Goku en dessin animé",
        "une rue animée de Tokyo la nuit",
        "un marché animé à Marrakech",
        "un clip-art de sapin de Noël",
        "une bannière animée de fanions sur une place de fête",
    ]
    for texte in images:
        rendu = S.secours(texte)["intention"]
        dit(rendu == "image", f"image : « {texte} »", f"-> {rendu}")
    retouches = [
        "mets-la en style dessin animé",
        "transforme cette photo en dessin animé",
        "fais-en un personnage de dessin animé",
        "turn this photo into an animated movie character",
        "version dessin anime de cette photo",
    ]
    for texte in retouches:
        rendu = S.secours(texte, "image")["intention"]
        dit(rendu == "edition", f"image jointe, retouche : « {texte} »",
            f"-> {rendu}")
    # CE QUI RESTE FAUX, et le banc le dit plutot que de le taire : la phrase
    # commence par « son de », la tournure d'une demande de bruitage.
    dit(S.secours("son de cloche visuel : une cloche en bronze")["intention"]
        == "audio",
        "defaut connu : « son de cloche visuel : une cloche en bronze » reste "
        "lu comme une musique (comme sur main)")
    # ET LES VRAIES ANIMATIONS LE RESTENT.
    for texte in ("un film d'animation court sur un renard, 5 secondes",
                  "une animation d'un logo qui tourne",
                  "un logo animé qui tourne sur lui-même",
                  "a short animated loop of falling snow"):
        rendu = S.secours(texte)["intention"]
        dit(rendu == "video", f"temoin, video : « {texte} »", f"-> {rendu}")


def les_quatre_langues():
    print("\n  ── secours() sur le banc traduit (mesures_langues), par langue ──")
    # AUCUNE LANGUE SOUS SON SCORE DE main (e192d6e). Le premier resserrage de
    # « anim » n'avait ete mesure qu'en francais : la video est tombee de 7 a
    # 5 sur 10 en anglais et en allemand, de 8 a 5 en espagnol. Les planchers
    # sont ceux de main ; la mesure d'aujourd'hui est a cote. Une piece jointe
    # pour ce qui en demande une, comme dans le studio.
    spec = importlib.util.spec_from_file_location(
        "banc_langues", os.path.join(ICI, "mesures_langues", "banc_langues.py"))
    bl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bl)
    cas = list(bl.FACILE) + list(bl.DUR)
    de_main = {"image": (15, 15, 15, 15), "video": (7, 7, 7, 8),
               "audio": (6, 1, 3, 1), "video_image": (5, 2, 2, 0),
               "edition": (9, 9, 9, 10)}
    # Ce qui est tenu : le score de main, et la ou la correction a fait mieux
    # — l'image jointe qu'on anime, la retouche prise pour une musique —, ce
    # mieux-la.
    tenus = dict(de_main, video_image=(5, 5, 5, 5), edition=(10, 10, 10, 10))
    jointe = {"video_image": "image", "edition": "image"}
    for voulu, planchers in de_main.items():
        lignes = [c for c in cas if c[0] == voulu]
        for k, langue in enumerate(("fr", "en", "de", "es"), start=1):
            bons = sum(S.secours(c[k], jointe.get(voulu, False))["intention"] == voulu
                       for c in lignes)
            dit(bons >= tenus[voulu][k - 1],
                f"{langue}, « {voulu} » : {bons} sur {len(lignes)} "
                f"(main : {planchers[k - 1]}, plancher {tenus[voulu][k - 1]})")


def les_corpus():
    print("\n  ── secours() sur les corpus etiquetes du depot, sans piece "
          "jointe ──")
    # Les planchers sont la mesure du 10 novembre 2026, APRES correction.
    # Avant : 271 images sur 286 (15 lues musique ou video), 217 musiques,
    # 231 videos. Apres : 286, 217, 231. Un mot resserre de trop se voit ici,
    # un mot relache aussi.
    comptes = {"image": [0, 0], "audio": [0, 0], "video": [0, 0]}
    egarees = []
    for nom in ("corpus_aiguillage.jsonl", "corpus_llm.jsonl",
                "corpus_llm2.jsonl", "banc_aiguillage.jsonl", "banc_neuf.jsonl"):
        with io.open(os.path.join(ICI, nom), encoding="utf-8") as f:
            for ligne in f:
                if not ligne.strip():
                    continue
                cas = json.loads(ligne)
                if cas["intention"] not in comptes:
                    continue
                rendu = S.secours(cas["texte"])["intention"]
                comptes[cas["intention"]][1] += 1
                comptes[cas["intention"]][0] += rendu == cas["intention"]
                if cas["intention"] == "image" and rendu != "image":
                    egarees.append(cas["texte"])
    dit(comptes["image"][1] >= 280 and not egarees,
        f"aucune des {comptes['image'][1]} demandes d'image n'est lue musique "
        f"ou video", str(egarees[:2]))
    dit(comptes["audio"][0] >= 217,
        f"les musiques reconnues ne baissent pas : {comptes['audio'][0]} sur "
        f"{comptes['audio'][1]} (plancher 217)")
    dit(comptes["video"][0] >= 231,
        f"les videos reconnues ne baissent pas : {comptes['video'][0]} sur "
        f"{comptes['video'][1]} (plancher 231, le score de main)")


async def main():
    garde_modele, garde_soumettre = S.appeler_ollama, S.soumettre_robuste
    S.appeler_ollama = faux_modele
    S.soumettre_robuste = faux_soumettre
    try:
        await le_cas_du_releve()
        await les_dimensions_d_une_autre_modalite()
        await les_vraies_demandes()
    finally:
        S.appeler_ollama, S.soumettre_robuste = garde_modele, garde_soumettre
    les_mots()
    un_style_n_est_pas_une_animation()
    les_quatre_langues()
    les_corpus()
    print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
    return 1 if rate else 0

sys.exit(asyncio.run(main()))
