#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Un plan lisible ne fait plus echouer la demande parce qu'un champ a la
mauvaise forme.

L'INCIDENT DU 8 AU 9 NOVEMBRE 2026 : sept demandes mortes sur « ERREUR :
sequence item 1: expected str instance, list found ». Toutes analysees par
mistral:7b sur le NAS, et toutes avec un plan parfaitement lisible : mistral
rendait « prompt » en LISTE de morceaux. Le plan n'est pas demande avec son
schema (voir aiguiller : le decodage contraint coutait dix a vingt fois
l'appel), donc rien n'en garantissait les types, et le studio joignait ce
« prompt » a une phrase.

Le banc passe par le VRAI chemin — aiguiller(), normaliser(), executer() —
avec un modele qui rend le plan qu'on lui dicte, et une soumission qui rend
une image sans carte. Aucun reseau.

    python banc_formes_plan.py
"""
import asyncio
import json
import os
import sys
import tempfile

os.environ["STUDIO_DONNEES"] = tempfile.mkdtemp(prefix="banc_formes_")
os.environ["STUDIO_AUTH"] = "libre"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serveur as S  # noqa: E402

ok, rate = [], []


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


BASE = {"intention": "image", "modele": "klein9b",
        "prompt": "un jeton rond en bronze", "negatif": "flou",
        "raison": "image demandee", "classement": "safe"}
TEXTE = "un jeton rond en bronze pour une table de jeu, vu de face"


def unites():
    print("\n  ── formes_du_plan, champ par champ ──")
    p, r = S.formes_du_plan(dict(BASE, prompt=["un jeton rond", "en bronze patine"]))
    dit(p["prompt"] == "un jeton rond, en bronze patine" and r == ["prompt"],
        "un prompt rendu en liste devient UN texte, ses morceaux dans l'ordre",
        f"{p['prompt']!r}, {r}")
    p, r = S.formes_du_plan(dict(BASE, prompt=["un jeton", ["rond", ""], 3]))
    dit(p["prompt"] == "un jeton, rond, 3",
        "une liste imbriquee est aplatie, les vides retires", repr(p["prompt"]))
    p, r = S.formes_du_plan(dict(BASE, modele=["klein9b", "flux1"],
                                 intention=["image"]))
    dit(p["modele"] == "klein9b" and p["intention"] == "image",
        "un champ d'un seul mot (moteur, intention) garde le premier, sans "
        "joindre : « klein9b, flux1 » n'est le nom d'aucun moteur",
        f"{p['modele']!r} / {p['intention']!r}")
    p, r = S.formes_du_plan(dict(BASE, negatif={"x": "y"}, raison=None))
    dit("negatif" not in p and "raison" not in p and sorted(r) == ["negatif", "raison"],
        "un objet ou un vide a la place d'un texte est retire, pas ecrit « {'x': 'y'} »",
        f"{p}, {r}")
    p, r = S.formes_du_plan(dict(BASE, largeur="1024", hauteur=768.0))
    dit(p["largeur"] == 1024 and p["hauteur"] == 768,
        "une taille ecrite en texte ou en decimal redevient un entier",
        f"{p['largeur']!r} / {p['hauteur']!r}")
    p, r = S.formes_du_plan(dict(BASE, largeur=True, hauteur="grande"))
    dit("largeur" not in p and "hauteur" not in p,
        "un booleen ou un mot n'est pas une taille : retire", str(p))
    p, r = S.formes_du_plan(dict(BASE, cases="une case", questions=["a", 2, ["b"]]))
    dit(p["cases"] == ["une case"] and p["questions"] == ["a", "2", "b"],
        "une liste de textes reste une liste de textes", f"{p['cases']} / {p['questions']}")
    p, r = S.formes_du_plan(dict(BASE, parametres=["etapes", 20]))
    dit("parametres" not in p, "des parametres qui ne sont pas un objet sont retires",
        str(p))
    plan_ = dict(BASE, largeur=1024, cases=["a"], parametres={"etapes": 20},
                 inconnu=[1, 2])
    p, r = S.formes_du_plan(dict(plan_))
    dit(p == plan_ and r == [],
        "temoin : un plan deja dans ses formes ressort a l'identique — un champ "
        "hors schema n'est pas touche", f"{r}")


def poser_parc():
    S.REGISTRE.clear()
    S.REGISTRE["pc"] = {"id": "pc", "titre": "PC (RTX 2080 Ti)", "agent": True,
                        "jeton": "x", "pause": None}
    S.ETAT_NOEUDS.clear()
    S.ETAT_NOEUDS["pc"] = {"repond": True, "vram": 11.0, "ram": 63.8,
                           "vu": S.time.time(), "ip": "10.0.0.1"}
    dossiers = {}
    for sous, nom, _r, _d in S.CATALOGUE["klein9b"]["fichiers"]:
        dossiers.setdefault(sous, set()).add(nom)
    S.MODELES_NOEUD["pc"] = {"quand": S.time.time(), "dossiers": dossiers}


async def de_bout_en_bout():
    print("\n  ── de bout en bout : executer() ──")
    poser_parc()
    graphes = []

    async def faux_soumettre(g, tid, ident, cle, patience=1800, viser="petite",
                             taille=None):
        graphes.append(json.dumps(g, ensure_ascii=False))
        return ([{"filename": f"{tid[:8]}_00001_.png", "subfolder": "u/image",
                  "type": "output", "noeud": ident}], 1.0)

    gardes = (S.soumettre_robuste, S.appeler_ollama)
    S.soumettre_robuste = faux_soumettre

    async def demande(plan, n):
        async def faux_modele(texte, image_b64=None, systeme=None, json_mode=True,
                              modele=None, temperature=0.4, tid=None, garder=0):
            # Le plan dicte ; tout autre appel (enrichissement, traduction)
            # rend le texte qu'on lui donne, pour que le prompt se lise au bout.
            # Un enrichissement qui n'apporte pas cinq mots nouveaux demande
            # l'accord de l'utilisateur : on en ajoute, en gardant le texte.
            return (json.dumps(plan, ensure_ascii=False) if json_mode
                    else texte + ", detailed engraving, soft studio lighting, "
                            "centered composition, clean neutral background")
        S.appeler_ollama = faux_modele
        tid = f"formes{n:02d}" + "0" * 24
        poser_parc()
        conv = S._vide(proprietaire="u" * 32)
        conv["id"] = "c-" + tid
        S.CONVERSATIONS[conv["id"]] = conv
        S.TACHES[tid] = {"etapes": [], "etat": "en cours", "debut": S.time.time(),
                         "demande": TEXTE, "conv": conv["id"]}
        del graphes[:]
        await S.executer(tid, TEXTE, conv)
        t_ = S.TACHES[tid]
        return t_.get("etat"), [e["msg"] for e in t_.get("etapes", [])], list(graphes)

    try:
        etat, fil, g_ = await demande(
            dict(BASE, prompt=["un jeton rond", "anneau de bronze grave"]), 1)
        dit(etat == "fini" and not any(l.startswith("ERREUR") for l in fil),
            "LE CAS DU 9 NOVEMBRE : « prompt » rendu en liste par le modele — la "
            "demande aboutit au lieu de mourir sur « sequence item 1 »",
            f"etat={etat}, {[l for l in fil if 'ERREUR' in l][:1]}")
        dit(len(g_) == 1 and "un jeton rond" in g_[0]
            and "anneau de bronze grave" in g_[0],
            "et les deux morceaux du prompt arrivent au moteur", f"{len(g_)} graphe(s)")
        dit(any("plan remis en forme (prompt)" in l for l in fil),
            "le fil dit quel champ a ete remis en forme",
            str([l for l in fil if "forme" in l]))
        for champ, v in (("tags_audio", ["a", "b"]), ("paroles", {"x": 1}),
                         ("modele", ["klein9b", "flux1"]), ("negatif", 3)):
            etat, fil, g_ = await demande(dict(BASE, **{champ: v}), 2)
            dit(etat == "fini" and len(g_) == 1,
                f"« {champ} » rendu comme {json.dumps(v)} : la demande aboutit",
                f"etat={etat}, {[l for l in fil if 'ERREUR' in l][:1]}")
        etat, fil, g_ = await demande(dict(BASE), 3)
        dit(etat == "fini" and not any("remis en forme" in l for l in fil),
            "temoin : un plan dans ses formes aboutit sans ligne de plus", f"etat={etat}")
    finally:
        S.soumettre_robuste, S.appeler_ollama = gardes


async def main():
    unites()
    await de_bout_en_bout()
    print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
    return 1 if rate else 0

sys.exit(asyncio.run(main()))
