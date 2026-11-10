#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Une image jointe : lire reste lire, et poser quelque chose n'est pas detourer.

LA MESURE DU 9 NOVEMBRE 2026, par un studio d'essai, une image jointe a la
demande (POST /api/v1/rendus, image_base64), avec les deux modeles d'analyse :

    « mets-lui un ciel etoile »                  detourer  (qwen2.5vl:7b)
    « lis cette image et dis-moi ses couleurs »  retoucher_sujet (qwen2.5vl:7b),
                                                 edition   (qwen2.5:7b)
    « qu'est-ce qu'on voit sur cette image ? »   lecture avec le moteur flux1,
                                                 une question en anglais (qwen2.5:7b)

Les deux modeles se trompaient sur les deux premieres : ce n'etait pas le
modele du jour, c'etait le studio. Trois regles, et ce banc les tient toutes
les trois par le VRAI chemin — raccourci_ecrit(), aiguiller(), normaliser(),
et executer() pour la lecture — avec un modele qui rend le plan qu'on lui
dicte, c'est-a-dire la MAUVAISE reponse relevee ce jour-la :

  1. lire, dire, ce qu'on voit, les couleurs : reconnus a l'ecrit, donc
     tranches avant tout appel (veut_lire) ;
  2. une lecture que le modele annonce n'est recouverte par aucune cle de
     moteur (normaliser) : elle ne tenait que si la cle, mise au hasard, etait
     celle d'un moteur d'image ;
  3. un detourage ne pose rien : « mets-lui », « ajoute », « change » sans un
     mot de detourage font une retouche, quoi que rende le modele.

LA RELECTURE DU 10 NOVEMBRE 2026 a trouve trois defauts dans ces regles, et
leurs phrases sont ici une par une : des retouches sorties « lecture » sans
appel (« peins le mur, n'importe quelle couleur », « une fleur de lis le long
du bord »), le detourage dementi qui manquait « mets lui » sans trait d'union
et renversait « turn this into a sticker », et un mot pris pour un ordre ou
qu'il soit (« que fait le personnage ? »). Le raccourci de lecture ne tire que
sur une demande qui ne fait que lire ; un ordre est un imperatif a sa place,
dans les quatre langues.

Aucun reseau, aucune carte.

    python banc_image_jointe.py
"""
import asyncio
import contextlib
import io
import json
import os
import sys
import tempfile

DOSSIER = tempfile.mkdtemp(prefix="banc_jointe_")
os.environ["STUDIO_DONNEES"] = DOSSIER
os.environ["STUDIO_AUTH"] = "libre"
os.environ["COMFY_DIR"] = os.path.join(DOSSIER, "comfy")
os.environ["COMFY_ENTREE"] = os.path.join(DOSSIER, "entrees")
os.makedirs(os.environ["COMFY_ENTREE"], exist_ok=True)
# NI CARTE NI MODELE, MEME QUAND LE BANC ROUGIT. Sur un studio fautif — celui
# d'avant, ou celui d'une mutation —, la lecture de la derniere section repart
# vers un rendu : rien ne doit alors pouvoir joindre le ComfyUI ou l'Ollama de
# la machine qui lance le banc. Le port 9 ne repond a personne.
os.environ["COMFY_URL"] = "http://127.0.0.1:9"
os.environ["OLLAMA_URL"] = "http://127.0.0.1:9"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serveur as S  # noqa: E402

for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# LE CLASSIFIEUR HORS JEU, et ce n'est pas un oubli : il n'est consulte que
# SANS image jointe, et il depend du fichier de la machine (aiguilleur.json,
# ou aiguilleur.local.json s'il existe). Ce banc mesure ce qui suit — les
# raccourcis ecrits et ce que normaliser() fait de la reponse du modele.
S.AIGUILLEUR = None

ok, rate = [], []


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


APPELS = {"plan": 0, "vision": 0}
DICTE = {}
VU = "Un disque bleu uni, centre sur un fond blanc."


async def faux_modele(texte, image_b64=None, systeme=None, json_mode=True,
                      modele=None, temperature=0.4, tid=None, garder=0):
    """Le modele de langage : il rend le plan qu'on lui dicte quand on lui
    demande un plan, et une description quand on lui montre l'image."""
    if image_b64:
        APPELS["vision"] += 1
        return VU
    if json_mode:
        APPELS["plan"] += 1
        return json.dumps(DICTE["plan"], ensure_ascii=False)
    return texte


async def aiguille(texte, plan, jointe="image", sortie=None):
    """Le plan que rend aiguiller() quand le modele repond « plan », et le
    nombre d'appels qu'il a fallu. « jointe » porte la FAMILLE de la piece
    jointe, comme dans le studio."""
    DICTE["plan"] = dict(plan, prompt=plan.get("prompt", "x"), raison="banc")
    APPELS["plan"] = APPELS["vision"] = 0
    tid = "jointe" + "0" * 26
    S.TACHES.clear()
    S.TACHES[tid] = {"etapes": [], "etat": "en cours", "proprietaire": None}
    conv = S._vide()
    conv["derniere_sortie"] = sortie
    with contextlib.redirect_stdout(io.StringIO()):
        rendu = await S.aiguiller(texte, tid, conv,
                                  image_b64="x" if jointe == "image" else None,
                                  a_une_image=jointe)
    return rendu, APPELS["plan"]


def court(p):
    return f"{p.get('intention')} / {p.get('modele')}"


DETOURER = {"intention": "detourer", "modele": "detourer"}
SUJET = {"intention": "retoucher_sujet", "modele": "retoucher_sujet"}
EDITION = {"intention": "edition", "modele": "edition",
           "prompt": "turn the image into a watercolor painting"}


async def le_tableau():
    print("\n  ── les six demandes du 9 novembre, le modele rendant ce qu'il a rendu ──")
    p, n = await aiguille("mets-lui un ciel etoile", DETOURER)
    dit(p["intention"] == "edition" and p["modele"] == "edition",
        "LE CAS DU 9 NOVEMBRE : « mets-lui un ciel etoile », le modele rend "
        "« detourer » — c'est une retouche", court(p))
    dit(p.get("prompt") == "mets-lui un ciel etoile",
        "et la retouche part avec la phrase de l'utilisateur, pas le prompt "
        "ecrit pour une decoupe", repr(p.get("prompt")))
    p, n = await aiguille("mets-lui un ciel etoile",
                          {"intention": "image", "modele": "detourer"})
    dit(p["intention"] == "edition",
        "la meme, le modele disant « image » avec la cle « detourer » : la "
        "cle ne fait pas un detourage", court(p))
    p, n = await aiguille("lis cette image et dis-moi ses couleurs", SUJET)
    dit(p["intention"] == "lecture" and n == 0,
        "LE CAS DU 9 NOVEMBRE : « lis cette image et dis-moi ses couleurs » "
        "est une lecture, tranchee sans demander au modele qui rendait "
        "« retoucher_sujet »", f"{court(p)}, {n} appel(s)")
    p, n = await aiguille("qu'est-ce qu'on voit sur cette image ?",
                          {"intention": "lecture", "modele": "flux1"})
    dit(p["intention"] == "lecture" and n == 0 and p.get("modele") is None,
        "« qu'est-ce qu'on voit sur cette image ? » : lecture sans appel, et "
        "sans le moteur flux1 que le modele y collait", f"{court(p)}, {n} appel(s)")
    p, n = await aiguille("decris cette image", SUJET)
    dit(p["intention"] == "lecture" and n == 0,
        "temoin : « decris cette image » reste une lecture sans appel", court(p))
    p, n = await aiguille("fais une image dans le meme style que celle-ci, "
                          "mais avec un chat", EDITION)
    dit(p["intention"] == "edition" and n == 1,
        "temoin : « dans le meme style que celle-ci, mais avec un chat » "
        "reste ce que le modele en dit", f"{court(p)}, {n} appel(s)")
    p, n = await aiguille("transforme cette image en aquarelle", EDITION)
    dit(p["intention"] == "edition" and n == 1
        and p.get("prompt") == EDITION["prompt"],
        "temoin : « transforme cette image en aquarelle » reste une retouche, "
        "avec la consigne du modele", f"{court(p)}, {p.get('prompt')!r}")


async def la_lecture():
    print("\n  ── une lecture que le modele annonce n'est recouverte par aucune cle ──")
    # Des demandes que le raccourci ecrit ne connait pas : elles arrivent au
    # modele, qui dit « lecture » et met la cle qu'il peut.
    p, n = await aiguille("beschreib mir bitte dieses Bild",
                          {"intention": "lecture", "modele": "retoucher_sujet"})
    dit(p["intention"] == "lecture" and n == 1,
        "le modele dit lecture avec la cle « retoucher_sujet » : c'est une "
        "lecture, la cle ne la recouvre pas", court(p))
    dit(p.get("modele") is None,
        "et la lecture gardee part sans moteur : la cle qui la recouvrait "
        "est retiree", court(p))
    p, n = await aiguille("tell me what's in this photo", {"intention": "lecture"})
    dit(p["intention"] == "lecture" and "modele" in p and p["modele"] is None,
        "une lecture rendue SANS cle ne part plus au secours, donc en "
        "retouche", court(p))
    p, n = await aiguille("dime que hay en esta foto",
                          {"intention": "lecture", "modele": "detourer"})
    dit(p["intention"] == "lecture",
        "ni en detourage avec la cle « detourer »", court(p))
    p, n = await aiguille("what is on this pic exactly",
                          {"intention": "lecture", "modele": "flux1"})
    dit(p["intention"] == "lecture" and p.get("modele") == "flux1",
        "temoin : une lecture rendue avec un moteur d'image passe comme "
        "avant, cle comprise — le champ est sans effet, il n'est pas touche",
        court(p))
    p, n = await aiguille("regarde cette photo et corrige les couleurs",
                          {"intention": "lecture", "modele": "edition"})
    dit(p["intention"] == "edition",
        "les mots ordonnent une transformation (« corrige ») : la cle de "
        "retouche garde la main sur la lecture annoncee", court(p))
    p, n = await aiguille("look at it and remove the hat",
                          {"intention": "lecture", "modele": "edition"})
    dit(p["intention"] == "edition",
        "en anglais aussi (« remove »)", court(p))
    p, n = await aiguille("beschreib mir bitte dieses Video",
                          {"intention": "lecture", "modele": "fluidifier"},
                          jointe="video")
    dit(p["intention"] == "fluidifier",
        "une video jointe n'est pas une image a lire : la cle « fluidifier » "
        "du modele garde la main", court(p))
    p, n = await aiguille("erase the person on the left",
                          {"intention": "image", "modele": "retoucher_sujet"})
    dit(p["intention"] == "retoucher_sujet",
        "temoin : la cle d'un moteur de retouche fait toujours l'intention "
        "quand le modele ne dit pas lecture", court(p))


async def le_detourage():
    print("\n  ── un detourage ne pose rien ──")
    p, n = await aiguille("ajoute un chapeau de paille", DETOURER)
    dit(p["intention"] == "edition",
        "« ajoute un chapeau de paille » rendu « detourer » : retouche", court(p))
    p, n = await aiguille("add a starry sky", DETOURER)
    dit(p["intention"] == "edition", "en anglais aussi (« add »)", court(p))
    p, n = await aiguille("peux-tu changer le ciel en ciel d'orage", DETOURER)
    dit(p["intention"] == "edition", "et a l'infinitif (« changer »)", court(p))
    p, n = await aiguille("detoure-la", {"intention": "image", "modele": "klein4b"})
    dit(p["intention"] == "detourer" and n == 0,
        "temoin : « detoure-la » est un detourage, tranche sans appel", court(p))
    p, n = await aiguille("enleve le fond", {"intention": "image", "modele": "klein4b"})
    dit(p["intention"] == "detourer" and n == 0,
        "temoin : « enleve le fond » aussi", court(p))
    for phrase in ("entferne bitte den Hintergrund von diesem Foto",
                   "quita el fondo de esta foto porfa",
                   "remove the background of this photo pls"):
        p, n = await aiguille(phrase, DETOURER)
        dit(p["intention"] == "detourer",
            f"temoin : « {phrase} », que le modele dit detourage, le reste",
            court(p))
    p, n = await aiguille("delete everything except the character pls", DETOURER)
    dit(p["intention"] == "detourer",
        "un verbe qui RETIRE ne dement pas un detourage : « delete everything "
        "except the character » le reste", court(p))
    p, n = await aiguille("give me just the dog", DETOURER)
    dit(p["intention"] == "detourer",
        "« give » sans son pronom ne pose rien : « give me just the dog » "
        "reste un detourage", court(p))
    p, n = await aiguille("give him a red scarf", DETOURER)
    dit(p["intention"] == "edition",
        "et avec son pronom, « give him a red scarf » est une retouche", court(p))
    p, n = await aiguille("put it on a transparent background", DETOURER)
    dit(p["intention"] == "detourer",
        "un verbe qui pose AVEC un mot de detourage : « put it on a "
        "transparent background » reste un detourage", court(p))
    p, n = await aiguille("give it a plain white background", DETOURER)
    dit(p["intention"] == "detourer",
        "les mots du detourage se lisent en anglais : « give it a plain "
        "white background » reste un detourage", court(p))
    p, n = await aiguille("mets-le en png", DETOURER)
    dit(p["intention"] == "detourer",
        "et en francais hors des raccourcis : « mets-le en png » reste un "
        "detourage", court(p))
    p, n = await aiguille("mets-lui un ciel etoile", DETOURER, jointe="video")
    dit(p["intention"] != "edition",
        "une video jointe n'est pas une image a retoucher : la regle du "
        "detourage ne l'envoie pas au moteur d'edition", court(p))


async def ne_faire_que_lire():
    print("\n  ── le raccourci de lecture ne tire que sur une demande qui ne fait QUE lire ──")
    # Relecture du 10 novembre 2026 : ces retouches sortaient « lecture » sans
    # appel. Elles vont au modele, qui dit ici ce qu'il en dirait : une retouche.
    for phrase in ("peins le mur d'une autre couleur, n'importe quelle couleur",
                   "repeins la voiture, peu importe quelle couleur",
                   "habille-la autrement, quelle couleur tu veux",
                   "une fleur de lis le long du bord gauche",
                   "pose une fleur de lis la ou se trouve le logo",
                   "dis-moi les couleurs puis inverse-les",
                   "lis le texte et reecris-le en rouge",
                   "dis-moi ce que ca donne avec un ciel rouge",
                   "teins ses cheveux, n'importe quelle couleur vive",
                   "passe la robe en rouge ou quelle couleur tu preferes",
                   "dis-moi le resultat avec des lunettes de soleil",
                   "lis le panneau et traduis-le en anglais sur l'image",
                   "quelles couleurs ? essaie plus chaud",
                   "montre-moi la meme, quelle couleur que soit la robe"):
        p, n = await aiguille(phrase, EDITION)
        dit(p["intention"] == "edition" and n == 1,
            f"« {phrase} » part au modele, et reste la retouche qu'il en dit",
            f"{court(p)}, {n} appel(s)")
    for phrase in ("lis cette image et dis-moi ses couleurs",
                   "qu'est-ce qu'on voit sur cette image ?",
                   "Qu’est-ce que c’est ?",
                   "tu peux lire le texte ?",
                   "QUELLES SONT LES COULEURS ?",
                   "de quelle couleur est la voiture ?",
                   "dis moi ce que tu vois"):
        p, n = await aiguille(phrase, EDITION)
        dit(p["intention"] == "lecture" and n == 0,
            f"temoin : « {phrase} » ne fait que lire — lecture sans appel",
            f"{court(p)}, {n} appel(s)")


async def un_ordre_et_non_un_mot():
    print("\n  ── un ordre se lit a sa place d'imperatif, dans les quatre langues ──")
    LUE = {"intention": "lecture", "modele": "retoucher_sujet"}
    for phrase in ("que fait le personnage sur cette photo ?",
                   "dans quel style est peinte cette image ?",
                   "can you give me a description of this picture?",
                   "tell me what would make it better",
                   "read the sign and give me the text",
                   "fais-moi une description de cette image",
                   "was siehst du auf diesem Bild?"):
        p, n = await aiguille(phrase, LUE)
        dit(p["intention"] == "lecture" and n == 1,
            f"« {phrase} », que le modele dit lecture avec une cle de "
            f"retouche, reste une lecture", court(p))
    RETOUCHE_DITE_LUE = {"intention": "lecture", "modele": "edition"}
    for phrase in ("rajoute un chapeau au chat",
                   "passe-la en noir et blanc",
                   "rends le ciel plus sombre",
                   "bonjour, tu peux lui mettre un chapeau ?",
                   "could you make the sky darker",
                   "Mach den Himmel dunkler",
                   "fuege der Figur eine Brille hinzu",
                   "aendere die Farbe des Himmels",
                   "pon un sombrero al gato",
                   "haz el cielo mas oscuro",
                   "a" + chr(0xf1) + "ade un sombrero al gato",
                   "cambia el color del coche"):
        p, n = await aiguille(phrase, RETOUCHE_DITE_LUE)
        dit(p["intention"] == "edition",
            f"« {phrase} » ordonne : la cle de retouche garde la main sur la "
            f"lecture annoncee", court(p))
    p, n = await aiguille("lis le texte puis copie-le a droite", RETOUCHE_DITE_LUE)
    dit(p["intention"] == "edition" and n == 1,
        "un verbe inconnu et son pronom accroche (« copie-le ») sont un "
        "ordre : pas de lecture sans appel, et la cle de retouche garde la "
        "main", f"{court(p)}, {n} appel(s)")
    p, n = await aiguille("garde cette image-la et dis ce que c'est", LUE)
    dit(p["intention"] == "lecture",
        "« cette image-la » n'ordonne rien", court(p))


async def le_detourage_relu():
    print("\n  ── le detourage dementi, relu le 10 novembre ──")
    for phrase in ("mets lui un ciel etoile",
                   "donne lui des lunettes",
                   "mets un ciel etoile derriere",
                   "fais lui un sourire",
                   "PUT A HAT ON IT",
                   "pon un sombrero al gato",
                   "mach den Himmel dunkler"):
        p, n = await aiguille(phrase, DETOURER)
        dit(p["intention"] == "edition" and p.get("prompt") == phrase,
            f"« {phrase} » rendu « detourer » : retouche", court(p))
    for phrase in ("ajoute un canal alpha autour du sujet",
                   "turn this into a sticker",
                   "transforme cette photo en sticker",
                   "don't change anything, just isolate the subject",
                   "extract the person and add an alpha channel",
                   "isolate the subject and put it on white",
                   "pon un fondo blanco",
                   "mach den Hintergrund weiss"):
        p, n = await aiguille(phrase, DETOURER)
        dit(p["intention"] == "detourer",
            f"« {phrase} » porte un mot de detourage : il le reste", court(p))
    p, n = await aiguille("change rien, garde juste le chat", DETOURER)
    dit(p["intention"] == "detourer",
        "une negation n'ordonne pas : « change rien, garde juste le chat » "
        "reste un detourage", court(p))
    for phrase in ("keep the cat only, don't change anything else",
                   "garde seulement le chien, sans rien ajouter",
                   "aendere nichts, behalte nur die Katze"):
        p, n = await aiguille(phrase, DETOURER)
        dit(p["intention"] == "detourer",
            f"ni « {phrase} »", court(p))
    p, n = await aiguille("what should i add to this picture", DETOURER)
    dit(p["intention"] == "detourer",
        "un verbe hors de sa place d'imperatif ne dement rien : « what "
        "should i add to this picture » garde ce que le modele en dit", court(p))


# LA SECONDE RELECTURE DU 10 NOVEMBRE 2026 : 22 de ces 44 demandes composees
# sortaient encore « lecture sans appel » (23 sur main). Le sort de chacune,
# image jointe : None, elle part au modele ; sinon le raccourci qui la prend.
# « retoucher_ » sans suite : la zone nommee ou le sujet, selon que la machine
# qui lance le banc a telecharge SAM 3.1 — un etat de machine, pas une regle.
COMPOSEES = (
    ("decris cette image puis rends-la plus nette", None),
    ("qu'est-ce que c'est ? fais-en un poster", None),
    ("decris l'image, je la veux plus lumineuse", None),
    ("dis-moi ce que tu vois et vieillis le personnage", None),
    ("analyse la photo, rajeunis-le de dix ans", None),
    ("c'est quoi ce truc ? vire-le", "retoucher_"),
    ("decris-la, sauf que le ciel doit etre rouge", None),
    ("que vois-tu ? le chat doit devenir un chien", None),
    ("raconte ce que tu vois, avec un chapeau sur la tete du monsieur", None),
    ("explique l'image et zoome sur le visage", None),
    ("decris la scene, plus sombre", None),
    ("decris cette image, mais de nuit", None),
    ("c'est quoi ? en plus grand", "agrandir"),
    ("analyse l'image et lisse la peau", None),
    ("decris-moi ca et vectorise le logo", None),
    ("lis le texte et corrigez les fautes", None),
    ("lis-moi ca puis grossis le titre", None),
    ("quelle couleur est la voiture ? je la prefere en bleu", None),
    ("dis-moi les couleurs, puis desature", None),
    ("decris, puis ensoleille le paysage", None),
    ("raconte la scene facon Pixar", None),
    ("explique cette image a la maniere de Van Gogh", None),
    ("decris l'image ; ensuite un detourage", "detourer"),
    ("analyse et upscale", "agrandir"),
    ("describe this image then make it sharper", None),
    ("what is this? turn it into a poster", None),
    ("decris l'image et il faudrait la recadrer en carre", None),
    ("qu'est-ce qu'on voit ? et tu pourrais gommer le poteau", None),
    ("dis-moi ce qu'il y a dessus et tu la mets en fond d'ecran 16:9",
     "retoucher_fond"),
    ("decris cette photo, je veux la meme en hiver", None),
    ("qu'y a-t-il sur l'image ? la meme avec de la neige", None),
    ("c'est quoi ? et maintenant en dessin anime", None),
    ("raconte l'image, puis une suite", None),
    ("decris ce logo et propose une variante", None),
    ("analyse cette image et genere la suite", None),
    ("que vois-tu ? dessine la suite", None),
    ("decris la photo et cree une version cartoon", None),
    ("decris-la et anime-la", None),
    ("qu'est-ce que c'est ? et fais-la bouger", None),
    ("explique ce schema et refais-le au propre", None),
    ("commente cette photo et retouche la peau", None),
    ("decris l'image et enleve les rides", "retoucher_"),
    ("analyse ce portrait puis blanchis les dents", None),
    ("decris, et pivote de 90 degres", None),
)
# Les 24 lectures simples de la meme sonde. Une seule part au modele, et elle
# y partait deja sur main : « fait » est dans _PAS_LIRE.
SIMPLES = (
    ("decris cette image", True),
    ("qu'est-ce que c'est ?", True),
    ("qu" + chr(0x2019) + "est-ce que c" + chr(0x2019) + "est ?", True),
    ("c'est quoi ?", True),
    ("que vois-tu sur cette photo ?", True),
    ("lis-moi le texte de l'image", True),
    ("dis-moi ce que tu vois", True),
    ("quelles sont les couleurs dominantes ?", True),
    ("de quoi s'agit-il ?", True),
    ("qu'y a-t-il sur cette image ?", True),
    ("analyse cette photo", True),
    ("raconte-moi ce qu'il se passe", True),
    ("explique ce schema", True),
    ("decris-moi le personnage", True),
    ("dis-moi combien il y a de personnes", True),
    ("qu'est-ce qu'on voit la-dessus ?", True),
    ("commente cette photo", True),
    ("peux-tu me lire ce panneau ?", True),
    ("decris l'image, s'il te plait", True),
    ("bonjour, decris cette image", True),
    ("decris precisement ce que fait le personnage", False),
    ("decris les vetements qu'il porte", True),
    ("dis-moi ce que mange le chat", True),
    ("que voit-on a l'arriere-plan ?", True),
)


async def une_seule_proposition():
    print("\n  ── la lecture sans appel tient en UNE proposition de lecture ──")
    a_tort = 0
    for phrase, raccourci in COMPOSEES:
        p, n = await aiguille(phrase, EDITION)
        a_tort += p["intention"] == "lecture"
        if raccourci:
            dit(p["intention"].startswith(raccourci) and n == 0,
                f"« {phrase} » est composee : pas une lecture, le raccourci "
                f"« {raccourci} » la prend", f"{court(p)}, {n} appel(s)")
        else:
            dit(p["intention"] == "edition" and n == 1,
                f"« {phrase} » est composee : elle part au modele, et reste "
                f"la retouche qu'il en dit", f"{court(p)}, {n} appel(s)")
    dit(a_tort == 0,
        "aucune des 44 demandes composees n'est lue sans appel",
        f"{a_tort} sur {len(COMPOSEES)}")
    gardees = 0
    for phrase, sans_appel in SIMPLES:
        p, n = await aiguille(phrase, EDITION)
        gardees += p["intention"] == "lecture" and n == 0
        if sans_appel:
            dit(p["intention"] == "lecture" and n == 0,
                f"temoin : « {phrase} » tient en une proposition — lecture "
                f"sans appel", f"{court(p)}, {n} appel(s)")
        else:
            dit(n == 1,
                f"temoin : « {phrase} » part au modele, comme sur main",
                f"{court(p)}, {n} appel(s)")
    dit(gardees == 23,
        "23 des 24 lectures simples gardent le raccourci",
        f"{gardees} sur {len(SIMPLES)}")
    for phrase in ("dis-moi ce qu'on voit sur cette image et ses couleurs",
                   "decris cette image en detail",
                   "decris cette image en francais",
                   "decris cette image avec precision",
                   "bonjour, decris cette image, merci",
                   "decris les couleurs, les formes et les textures",
                   "regarde cette photo et dis-moi ce qui s'y passe",
                   "analyse cette image et donne moi les details",
                   "qu'est-ce qu'on voit ? et ses couleurs ?"):
        p, n = await aiguille(phrase, EDITION)
        dit(p["intention"] == "lecture" and n == 0,
            f"temoin : « {phrase} » — politesse, complement ou second objet "
            f"de la MEME lecture, le raccourci tient", f"{court(p)}, {n} appel(s)")
    for phrase in ("decris cette photo je veux la meme en hiver",
                   "decris-la i want it brighter",
                   "decris cette photo et la meme scene de nuit",
                   "decris l'image et le texte doit disparaitre",
                   "decris la photo et ses cheveux en bleu",
                   "decris l'image, le fond flou",
                   "decris la scene plus sombre",
                   "raconte ce que tu vois avec un chapeau sur la tete du monsieur"):
        p, n = await aiguille(phrase, EDITION)
        dit(p["intention"] == "edition" and n == 1,
            f"« {phrase} » : une suite sans ponctuation, ou un faux objet — "
            f"au modele", f"{court(p)}, {n} appel(s)")


async def les_temoins():
    print("\n  ── ce qui ne devait pas bouger ──")
    p, n = await aiguille("enleve le sujet", {"intention": "image", "modele": "klein4b"})
    dit(p["intention"] == "retoucher_sujet" and n == 0,
        "temoin : « enleve le sujet » est une retouche du sujet, sans appel",
        court(p))
    p, n = await aiguille("un renard roux dans la neige, au petit matin",
                          {"intention": "image", "modele": "klein9b"}, jointe=False)
    dit(p["intention"] == "image" and p["modele"] == "klein9b" and n == 1,
        "temoin : sans image, une demande de creation reste une image, par "
        "le modele", f"{court(p)}, {n} appel(s)")
    p, n = await aiguille("lis cette image et dis-moi ses couleurs",
                          {"intention": "lecture", "modele": "flux1"}, jointe=False)
    dit(p["intention"] != "lecture" and n == 1,
        "temoin : sans image jointe, rien n'est lu — la demande va au modele "
        "et une lecture sans image n'en reste pas une", f"{court(p)}, {n} appel(s)")
    p, n = await aiguille("detoure-la", {"intention": "image", "modele": "klein4b"},
                          jointe=False, sortie={"filename": "x.png"})
    dit(p["intention"] == "detourer" and n == 0,
        "temoin : « detoure-la » apres une sortie precedente reste un "
        "detourage", court(p))


async def de_bout_en_bout():
    print("\n  ── de bout en bout : executer() ──")
    nom = "jointe_banc.png"
    with open(os.path.join(S.DOSSIER_ENTREE, nom), "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
    soumis = []

    async def faux_soumettre(*a, **k):
        soumis.append(a)
        raise RuntimeError("ce banc ne rend aucune image")

    garde = S.soumettre_robuste
    S.soumettre_robuste = faux_soumettre
    try:
        DICTE["plan"] = dict(SUJET, prompt="x", raison="banc")
        APPELS["plan"] = APPELS["vision"] = 0
        texte = "lis cette image et dis-moi ses couleurs"
        tid = "lecture" + "0" * 25
        conv = S._vide(proprietaire="u" * 32)
        S.CONVERSATIONS[conv["id"]] = conv
        S.TACHES.clear()
        S.TACHES[tid] = {"etapes": [], "etat": "en cours", "debut": S.time.time(),
                         "demande": texte, "conv": conv["id"], "image": nom}
        with contextlib.redirect_stdout(io.StringIO()):
            await S.executer(tid, texte, conv, image=nom)
        t_ = S.TACHES[tid]
        fil = [e["msg"] for e in t_.get("etapes", [])]
        dit(t_.get("etat") == "fini" and t_.get("description") == VU,
            "« lis cette image et dis-moi ses couleurs » rend la description "
            "de l'image jointe", f"etat={t_.get('etat')}, {fil[-1:]}")
        dit(not soumis and APPELS["plan"] == 0 and APPELS["vision"] == 1,
            "sans rien soumettre a un moteur ni demander de plan : un seul "
            "appel, celui qui regarde l'image",
            f"{len(soumis)} graphe(s), {APPELS}")
    finally:
        S.soumettre_robuste = garde
        try:
            os.remove(os.path.join(S.DOSSIER_ENTREE, nom))
        except OSError:
            pass


async def main():
    garde = S.appeler_ollama
    S.appeler_ollama = faux_modele
    try:
        await le_tableau()
        await la_lecture()
        await le_detourage()
        await ne_faire_que_lire()
        await un_ordre_et_non_un_mot()
        await le_detourage_relu()
        await une_seule_proposition()
        await les_temoins()
        await de_bout_en_bout()
    finally:
        S.appeler_ollama = garde
    print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
    return 1 if rate else 0

sys.exit(asyncio.run(main()))
