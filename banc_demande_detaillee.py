#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Une demande deja detaillee part telle quelle : ni appel pour l'etoffer, ni
question « je n'ai pas reussi a etoffer ta demande ».

LE RELEVE DU 9 NOVEMBRE 2026 : 314 demandes de programme, 130 mots en
mediane, arretees sur cette question — le modele ne peut pas allonger de cinq
mots nouveaux une description qui en compte deja cent trente, il la resume.
Le programme devait repondre a chaque fois ; une demande sur deux faisait un
aller-retour de plus.

Le banc passe par enrichir() lui-meme, puis par executer() de bout en bout,
avec un modele qui RESUME (l'echec du releve) et une soumission sans carte.

    python banc_demande_detaillee.py
"""
import asyncio
import json
import os
import sys
import tempfile

os.environ["STUDIO_DONNEES"] = tempfile.mkdtemp(prefix="banc_detaillee_")
os.environ["STUDIO_AUTH"] = "libre"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serveur as S  # noqa: E402

ok, rate = [], []


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


def demande_de(n):
    """Une demande de n mots, faite de vrais mots (le compte est celui de split)."""
    base = ("jeton rond pour table de jeu virtuelle vu exactement de face un "
            "disque centre qui remplit toute l'image entoure d'un anneau fin "
            "en bronze patine grave de petites feuilles").split()
    return " ".join((base * (n // len(base) + 1))[:n])


appels = []
reponse_ecriture = ["un jeton rond"]       # ce que rend le modele qui ecrit
resume_du_plan = [None]                    # le prompt du plan, s'il resume

# LE CAS DE LA SECONDE RELECTURE (10 novembre 2026) : 79 mots de neerlandais,
# que les motifs de garde_fou() ne lisent pas, et le resume francais qu'en
# fait l'analyse — trois phrases, comme son gabarit le lui demande, sans le
# detail.
NEERLANDAIS = (
    "Een oude vuurtoren op een rotsachtige kust bij zonsondergang, met hoge "
    "golven die tegen de rotsen slaan en een kleine vissersboot in de verte. "
    "De lucht is oranje en paars, er vliegen meeuwen boven het water en het "
    "licht van de toren schijnt over de zee naar de horizon. Op het strand "
    "staat een naakt kind van acht jaar. In de verte zijn donkere wolken te "
    "zien en de wind waait hard over de duinen waar het gras buigt.")
RESUME = ("Un vieux phare sur une cote rocheuse au coucher du soleil, avec de "
          "hautes vagues et un petit bateau de peche au loin. Ciel orange et "
          "violet, mouettes, nuages sombres et vent sur les dunes.")


async def faux_modele(texte, image_b64=None, systeme=None, json_mode=True,
                      modele=None, temperature=0.4, tid=None, garder=0):
    appels.append("json" if json_mode else "texte")
    if json_mode:
        return json.dumps({"intention": "image", "modele": "klein9b",
                           "prompt": resume_du_plan[0] or texte,
                           "raison": "image", "classement": "safe"},
                          ensure_ascii=False)
    return reponse_ecriture[0]


def tache(tid):
    S.TACHES[tid] = {"etapes": [], "etat": "en cours", "debut": S.time.time()}
    return tid


def fil(tid):
    return [e["msg"] for e in S.TACHES[tid]["etapes"]]


async def directement():
    print("\n  ── enrichir(), selon la longueur de la demande ──")
    S.appeler_ollama = faux_modele
    plan_ = lambda t: {"intention": "image", "modele": "klein9b", "prompt": t}

    del appels[:]
    t = demande_de(130)
    tid = tache("detaillee-130")
    p = await S.enrichir(plan_(t), t, tid)
    dit(not appels and not p.get("enrichissement_rate") and p["prompt"] == t,
        "LE CAS DU RELEVE : 130 mots — aucun appel au modele, aucune marque, le "
        "prompt part tel quel", f"appels={appels}, marque={p.get('enrichissement_rate')}")
    dit(any("demande deja detaillee (130 mots)" in l for l in fil(tid)),
        "et le fil dit pourquoi", str(fil(tid)[-1:]))

    del appels[:]
    t = demande_de(S.DEMANDE_DETAILLEE)
    p = await S.enrichir(plan_(t), t, tache("detaillee-seuil"))
    dit(not appels and not p.get("enrichissement_rate"),
        f"au seuil ({S.DEMANDE_DETAILLEE} mots) : envoyee sans etoffer",
        f"appels={appels}")

    del appels[:]
    t = demande_de(S.DEMANDE_DETAILLEE - 1)
    p = await S.enrichir(plan_(t), t, tache("detaillee-sous"))
    dit(appels and p.get("enrichissement_rate"),
        f"temoin : un mot sous le seuil, la regle d'avant — on essaie, et un "
        f"modele qui resume laisse la marque qui fait poser la question",
        f"appels={appels}, marque={p.get('enrichissement_rate')}")

    del appels[:]
    reponse_ecriture[0] = ("un chat roux endormi en boule sur un vieux fauteuil "
                           "de velours vert, lumiere douce d'une fin d'apres-midi")
    p = await S.enrichir(plan_("un chat roux"), "un chat roux", tache("detaillee-court"))
    dit(appels and not p.get("enrichissement_rate") and "velours" in p["prompt"],
        "temoin : une demande courte est toujours etoffee", p["prompt"][:60])
    reponse_ecriture[0] = "un jeton rond"

    del appels[:]
    t = demande_de(130)
    plan_long = plan_("jeton rond")       # l'analyse a resume la demande
    tid = tache("detaillee-resumee")
    p = await S.enrichir(plan_long, t, tid)
    dit(not appels and p["prompt"] == t,
        "c'est la demande de l'UTILISATEUR qui compte, pas le plan : 130 mots "
        "resumes en deux par l'analyse partent tels que l'auteur les a ecrits",
        f"appels={appels}, prompt={p['prompt'][:40]!r}")
    dit(any("telle que tu l'as ecrite" in l for l in fil(tid)),
        "et le fil dit que c'est son texte qui part", str(fil(tid)[-1:]))

    del appels[:]
    garde_ = " ".join(t.split()[:80])     # l'analyse a garde l'essentiel
    p = await S.enrichir(plan_(garde_), t, tache("detaillee-gardee"))
    dit(not appels and p["prompt"] == garde_,
        "temoin : un plan qui garde plus de la moitie de la demande part tel "
        "quel — le texte de l'auteur ne le remplace pas", f"{len(p['prompt'].split())} mots")

    print("\n  ── le texte de l'auteur ne revient que s'il peut etre relu ──")
    del appels[:]
    tid = tache("detaillee-neerlandais")
    p = await S.enrichir(plan_(RESUME), NEERLANDAIS, tid)
    dit(not appels and p["prompt"] == RESUME,
        "LE CAS DE LA RELECTURE : 79 mots de neerlandais resumes par l'analyse "
        "— c'est le resume, que garde_fou() a lu, qui part, et pas le texte "
        "que rien ne sait relire", f"prompt={p['prompt'][:40]!r}")
    dit(any("resume de l'analyse qui part" in l for l in fil(tid))
        and not any("telle que tu l'as ecrite" in l for l in fil(tid)),
        "et le fil le dit simplement", str(fil(tid)[-1:]))

    t = demande_de(130) + " avec le signe π grave au centre"
    p = await S.enrichir(plan_("jeton rond"), t, tache("detaillee-grec"))
    dit(p["prompt"] == "jeton rond",
        "une seule lettre non latine dans une demande francaise : le resume "
        "reste aussi", f"prompt={p['prompt'][:40]!r}")

    etiquettes = ("portrait d'une guerriere naine, armure de plates cabossee, "
                  "tresses rousses, cicatrice sur la joue, marteau de guerre, "
                  "fond de forge rougeoyante, lumiere chaude, peinture "
                  "numerique, tres detaille, cadrage buste, regard determine, "
                  "braises, fumee, style fantasy, palette sombre, contraste "
                  "fort, textures de metal, cuir use, fourrure, runes gravees")
    p = await S.enrichir(plan_("guerriere naine"), etiquettes,
                         tache("detaillee-etiquettes"))
    dit(p["prompt"] == "guerriere naine",
        "des etiquettes dont rien ne prouve la langue : le resume reste, "
        "comme avant la ronde 11", f"prompt={p['prompt'][:40]!r}")


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
    graphes = []

    async def faux_soumettre(g, tid, ident, cle, patience=1800, viser="petite",
                             taille=None):
        graphes.append(json.dumps(g, ensure_ascii=False))
        return ([{"filename": f"{tid[:8]}_00001_.png", "subfolder": "u/image",
                  "type": "output", "noeud": ident}], 1.0)

    garde = S.soumettre_robuste
    S.soumettre_robuste = faux_soumettre
    S.appeler_ollama = faux_modele

    async def demande(texte, n):
        tid = f"detail{n:02d}" + "0" * 24
        poser_parc()
        conv = S._vide(proprietaire="u" * 32)
        conv["id"] = "c-" + tid
        S.CONVERSATIONS[conv["id"]] = conv
        S.TACHES[tid] = {"etapes": [], "etat": "en cours", "debut": S.time.time(),
                         "demande": texte, "conv": conv["id"]}
        del graphes[:]
        await S.executer(tid, texte, conv)
        return S.TACHES[tid].get("etat"), list(graphes)

    try:
        etat, g_ = await demande(demande_de(130), 1)
        dit(etat == "fini" and len(g_) == 1,
            "une demande de 130 mots aboutit sans question", f"etat={etat}")
        etat, g_ = await demande(demande_de(20), 2)
        dit(etat == "question" and not g_,
            "temoin : 20 mots et un enrichissement rate posent toujours la "
            "question", f"etat={etat}")

        def prompt_parti(g_):
            noeuds = json.loads(g_[0]) if g_ else {}
            return next((n["inputs"]["text"] for _k, n in sorted(noeuds.items())
                         if n.get("class_type") == "CLIPTextEncode"), None)

        resume_du_plan[0] = RESUME
        try:
            etat, g_ = await demande(NEERLANDAIS, 3)
            dit(etat == "fini" and prompt_parti(g_) == RESUME,
                "de bout en bout : la demande neerlandaise resumee par "
                "l'analyse est rendue avec ce resume — le texte de l'auteur, "
                "que les motifs ne lisent pas, ne part pas au moteur",
                f"etat={etat}, prompt={(prompt_parti(g_) or '')[:40]!r}")
            t = demande_de(130)
            etat, g_ = await demande(t, 4)
            dit(etat == "fini" and prompt_parti(g_) == t,
                "temoin : la meme analyse qui resume une demande FRANCAISE — "
                "c'est le texte de l'auteur qui part, la regle de la ronde 11",
                f"etat={etat}, prompt={(prompt_parti(g_) or '')[:40]!r}")
        finally:
            resume_du_plan[0] = None
    finally:
        S.soumettre_robuste = garde


async def main():
    garde = S.appeler_ollama
    try:
        await directement()
        await de_bout_en_bout()
    finally:
        S.appeler_ollama = garde
    print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
    return 1 if rate else 0

sys.exit(asyncio.run(main()))
