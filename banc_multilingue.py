#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""La garde de couverture : ce qu'elle ferme, et ce qu'elle ne coute pas.

LE COURT-CIRCUIT DU CLASSIFIEUR TIRAIT PLUS SOUVENT SUR DE L'ETRANGER QUE SUR
DU FRANCAIS, ET SE TROMPAIT LA MOITIE DU TEMPS. Bayes naif ne sait pas dire
« je ne connais pas ces mots » : quand presque aucun trait de la phrase n'est
au corpus, le lissage de Laplace et les probabilites a priori departagent les
classes tout seuls, et la marge — le seul chiffre que le studio consultait —
peut etre grande pour de mauvais motifs. « brauche ein Video von null mit einem
fliegenden Drachen », une video a creer de zero, partait en « fluidifier » avec
une marge de 3,9 : le studio interpolait la sortie precedente, et personne
n'etait prevenu.

Mesure du 2 septembre 2026 : sur 345 demandes etrangeres, 26 pannes
SILENCIEUSES — tranchees d'office et fausses. Une sur quatre sur le banc dur.
En francais, une sur douze.

CE BANC EMPRUNTE LE CHEMIN, IL NE LE RECOPIE PAS. Il appelle aiguiller() et
compte les appels au modele de langage en remplaçant appeler_ollama : c'est la
seule maniere de mesurer un court-circuit, qui est par definition ce qui n'est
PAS appele. Les scripts de mesures_langues/, eux, rejouaient la sequence a la
main — ils ont servi a choisir le seuil, ils ne gardent rien.

CE QU'IL MESURE, dans l'ordre de gravite :

  - LE FRANCAIS NE PERD RIEN, et c'est la moitie qui pourrait faire retirer la
    garde « pour simplifier » : les memes 115 demandes francaises sont
    tranchees sans appel, exactement les memes, avec la garde et sans elle.
    C'est une egalite d'ENSEMBLES, pas de comptes : deux demandes qui
    s'echangent donneraient le meme total.
  - LES PANNES SILENCIEUSES ETRANGERES tombent d'un facteur cinq au moins, et
    il n'en reste pas plus de trois sur 345.
  - LE SEUIL SEPARE VRAIMENT : au-dessus de 0,58, le francais ; en dessous, le
    reste. Sans cela, la garde rendrait le bon service pour la mauvaise raison.
  - LA GARDE LE DIT. Une demande qui part au modele parce qu'on ne la comprend
    pas est le seul cas du studio ou cela arrive : le journal doit le nommer,
    sans quoi personne ne saura jamais expliquer l'appel supplementaire.

LES 460 CAS sont les deux bancs du depot — banc_aiguillage.jsonl, familier et
fautif, banc_neuf.jsonl, indirect et poli — traduits A LA MAIN en anglais,
allemand et espagnol, meme registre. Ils vivent dans mesures_langues/.

    LEUR LIMITE EST ECRITE ICI parce qu'elle vaut pour ce banc aussi : ils ont
    ete traduits par UNE SEULE personne, ce que CONTRIBUTING.md denonce
    precisement (100 % de justesse sur ses propres phrases, 74 % sur celles
    d'un tiers). Les valeurs absolues sont donc a prendre avec reserve. Les
    ECARTS — entre les deux politiques, sur le meme jeu — le sont beaucoup
    moins, et ce banc ne mesure que des ecarts.

    python banc_multilingue.py
"""
import asyncio
import contextlib
import io
import os
import sys
import tempfile

ICI = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("STUDIO_DONNEES", tempfile.mkdtemp(prefix="banc_multi_"))
os.environ.setdefault("STUDIO_AUTH", "libre")
sys.path.insert(0, ICI)
sys.path.insert(0, os.path.join(ICI, "mesures_langues"))

import aiguilleur as _aiguilleur      # noqa: E402
import banc_langues                   # noqa: E402
import serveur as S                   # noqa: E402

# LE MODELE PUBLIE, ET PAS CELUI DE CETTE INSTALLATION. charger() prend
# aiguilleur.local.json S'IL EXISTE, et aiguilleur.json seulement sinon — l'un
# OU l'autre, pas les deux. Le premier est une DONNEE : le modele reentraine
# sur les demandes reelles de cette machine-ci, que .gitignore ecarte. Il a
# donc vu des tournures que le modele versionne n'a pas, et leur couverture y
# est plus haute : mesure du 2 septembre 2026, « de quoi ca parle » vaut 0,56
# avec le modele publie et 0,67 avec le modele local de la machine de
# developpement. Le meme commit rendrait donc des verdicts differents sur deux
# machines, et le vert de la CI ne dirait rien du vert d'ici. On epingle le
# modele versionne : c'est le seul que tout le monde ait.
S.AIGUILLEUR = _aiguilleur.Aiguilleur.lire(_aiguilleur.MODELE)

CAS = banc_langues.FACILE + banc_langues.DUR
LANGUES = ("fr", "en", "de", "es")

ok, rate = [], []


def dit(vrai, quoi, releve=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok  ' if vrai else 'RATE'} {quoi}"
          + (f" — {releve}" if releve else ""))


# ── ce que le studio decide, par le VRAI chemin ────────────────────────
APPELS = {"modele": 0}


async def _faux_ollama(*a, **k):
    """Le modele de langage, remplace par un compteur.

    Il leve : aiguiller() attrape et se replie sur secours(), un chemin
    deterministe et hors ligne. Ce que le repli decide ne nous interesse pas —
    ce banc compte les demandes qui N'Y ARRIVENT PAS.
    """
    APPELS["modele"] += 1
    raise RuntimeError("pas de modele de langage sur ce banc")


S.appeler_ollama = _faux_ollama


async def decide(texte):
    """Rend (intention, appel_au_modele, lignes de journal) pour une demande.

    Aucune image jointe, mais une sortie precedente dans la conversation :
    c'est la condition exacte du court-circuit — agrandir, detourer et
    fluidifier portent sur une image qui EXISTE.
    """
    APPELS["modele"] = 0
    tid = "banc"
    S.TACHES.clear()
    S.TACHES[tid] = {"etapes": [], "etat": "en cours", "proprietaire": None}
    conv = {"derniere_sortie": "deja_la.png", "tours": []}
    muet = io.StringIO()
    with contextlib.redirect_stdout(muet):
        plan = await S.aiguiller(texte, tid, conv)
    lignes = [e["msg"] for e in S.TACHES[tid]["etapes"]]
    return plan.get("intention"), APPELS["modele"] > 0, lignes


async def politique(seuil):
    """Les 460 demandes, sous un seuil donne. 0 rejoue l'etat d'avant.

    « tranche » est l'ensemble des demandes decidees SANS appel au modele, et
    « faux » celles qui l'ont ete de travers : une panne silencieuse, la seule
    espece que ce depot ne sache pas voir autrement.
    """
    _aiguilleur.SEUIL_LANGUE = seuil
    rendu = {lg: {"tranche": set(), "faux": set(), "appels": 0, "dits": 0}
             for lg in LANGUES}
    for n, cas in enumerate(CAS):
        attendu = cas[0]
        for i, lg in enumerate(LANGUES):
            quoi, appele, lignes = await decide(cas[1 + i])
            r = rendu[lg]
            if appele:
                r["appels"] += 1
                if any("ne connait que" in l for l in lignes):
                    r["dits"] += 1
            else:
                r["tranche"].add(n)
                if quoi != attendu:
                    r["faux"].add(n)
    return rendu


def moisson():
    """Ce que le corpus retient des demandes reelles, langue par langue.

    LA MOISSON INVERSE LE REMEDE. Mesure du 2 septembre 2026 : onze demandes
    allemandes confirmees d'un pouce en l'air font passer les pannes
    silencieuses allemandes de 17 % a 44 %. La justesse, elle, ne bouge presque
    pas — 45 % a 51 %. Ce n'est pas la justesse qui monte, c'est la CONFIANCE :
    huit exemplaires ponderes d'une phrase allemande creent des traits que
    toutes les autres phrases allemandes partagent, et le court-circuit tire
    plus souvent. Sur le banc francais, l'ajout ne change rien (91, 90, 96 %
    pour K=0, 3, 5) : AUCUN BANC DU DEPOT NE VERRAIT CETTE DEGRADATION.

    On pose donc quatre demandes confirmees dans le dossier des conversations —
    deux francaises, deux allemandes, meme sujet et meme classe deux a deux —
    et on regarde ce que corpus() en garde. C'est le vrai chemin, celui
    qu'emprunte « python entrainer_aiguilleur.py ».
    """
    import json
    import entrainer_aiguilleur as E
    dossier = os.environ["STUDIO_DONNEES"]
    # « avis: 1 » et « etat: fini » : la moisson ne prend que ce que
    # l'utilisateur a lui-meme valide. Sans ces deux champs, rien n'est recolte
    # et tout ce qui suit serait vrai de rien — d'ou la premiere verification.
    fr = ["une illustration de renard dans les hautes herbes",
          "une musique douce au piano pour dormir"]
    de = ["eine Illustration von einem Fuchs im hohen Gras",
          "eine sanfte Klaviermusik zum Einschlafen"]
    tours = [{"demande": t, "type": i, "etat": "fini", "avis": 1}
             for t, i in zip(fr + de, ["image", "audio", "image", "audio"])]
    with open(os.path.join(dossier, "conv_banc.json"), "w",
              encoding="utf-8") as f:
        json.dump({"proprietaire": "banc", "tours": tours}, f)

    recoltees = [x["texte"] for x in E.moissonner()]
    dit(all(t in recoltees for t in fr + de),
        "la moisson les voit toutes les quatre — le filtre n'est pas en amont",
        f"{len(recoltees)} recoltee(s)")
    tout, _ = E.corpus()
    gardes = {x["texte"] for x in tout}
    dit(all(t in gardes for t in fr),
        "les deux demandes francaises entrent au corpus",
        f"{sum(t in gardes for t in fr)}/2")
    dit(not any(t in gardes for t in de),
        "et aucune des deux allemandes : elles rendraient le studio plus SUR "
        "de ses erreurs, pas meilleur",
        ", ".join(t for t in de if t in gardes) or "aucune")


async def main():
    seuil_reel = _aiguilleur.SEUIL_LANGUE
    print(f"\n  {len(CAS)} demandes x 4 langues, seuil de couverture "
          f"{seuil_reel}\n")

    print("  ── sans la garde (l'etat d'avant le 2 septembre 2026) ──")
    avant = await politique(0.0)
    print("  ── avec la garde ──")
    apres = await politique(seuil_reel)
    _aiguilleur.SEUIL_LANGUE = seuil_reel

    print(f"\n  {'langue':>7} {'tranche sans appel':>22} {'dont FAUX':>22}")
    for lg in LANGUES:
        a, b = avant[lg], apres[lg]
        print(f"  {lg:>7} {len(a['tranche']):>12} -> {len(b['tranche']):<8}"
              f"{len(a['faux']):>12} -> {len(b['faux']):<8}")

    print("\n  ── le francais ne perd rien ──")
    # EGALITE D'ENSEMBLES, PAS DE COMPTES. Deux demandes qui s'echangent
    # laisseraient le total intact, et la garde aurait pourtant change ce que
    # le studio repond a quelqu'un qui ecrit en francais.
    perdues = avant["fr"]["tranche"] - apres["fr"]["tranche"]
    gagnees = apres["fr"]["tranche"] - avant["fr"]["tranche"]
    dit(not perdues and not gagnees,
        "les MEMES demandes francaises sont tranchees sans appel, garde ou non",
        (f"{len(perdues)} perdue(s), {len(gagnees)} gagnee(s) : "
         + ", ".join(CAS[n][1] for n in sorted(perdues | gagnees)))
        if (perdues or gagnees) else f"{len(apres['fr']['tranche'])} demandes")
    dit(avant["fr"]["faux"] == apres["fr"]["faux"],
        "et elles se trompent aux memes endroits, ni plus ni moins",
        f"{len(avant['fr']['faux'])} -> {len(apres['fr']['faux'])}")

    print("\n  ── ce que la garde ferme sur l'etranger ──")
    etr_avant = sum(len(avant[lg]["faux"]) for lg in LANGUES[1:])
    etr_apres = sum(len(apres[lg]["faux"]) for lg in LANGUES[1:])
    etr_total = len(CAS) * 3
    # SANS CETTE PREMIERE LIGNE, TOUT LE RESTE SERAIT VRAI DE RIEN. Le jour ou
    # le corpus change au point que le court-circuit ne tire plus du tout,
    # « les pannes sont divisees par cinq » se lirait vert sur 0 -> 0, et ce
    # banc certifierait une garde qui ne garde plus personne.
    dit(etr_avant >= 10,
        "sans la garde, le court-circuit se trompait en silence sur "
        "l'etranger", f"{etr_avant} pannes sur {etr_total} demandes")
    dit(etr_apres * 5 <= etr_avant,
        "avec elle, les pannes silencieuses sont divisees par cinq au moins",
        f"{etr_avant} -> {etr_apres}")
    dit(etr_apres <= 3,
        "et il n'en reste pas plus de trois sur les 345 demandes etrangeres",
        str(etr_apres))

    print("\n  ── le seuil separe, il ne marche pas par accident ──")
    # La garde repose sur UN chiffre. S'il ne separait pas, elle rendrait le
    # bon service pour la mauvaise raison — et le premier reglage du corpus
    # l'emporterait sans que rien ne rougisse.
    A = S.AIGUILLEUR
    haut_fr = sum(1 for c in CAS if A.couverture(c[1]) >= seuil_reel)
    bas_etr = sum(1 for c in CAS for i in (2, 3, 4)
                  if A.couverture(c[i]) < seuil_reel)
    dit(haut_fr >= 0.95 * len(CAS),
        "au-dessus du seuil, le francais : 95 % au moins",
        f"{haut_fr}/{len(CAS)}")
    dit(bas_etr >= 0.90 * etr_total,
        "en dessous, l'etranger : 90 % au moins",
        f"{bas_etr}/{etr_total}")

    print("\n  ── la garde le DIT ──")
    # Une demande qui part au modele PARCE QU'ON NE LA COMPREND PAS est le seul
    # cas du studio ou cela arrive. Sans la ligne de journal, l'utilisateur voit
    # un appel qu'il n'attendait pas et personne ne saura jamais dire pourquoi.
    #
    # « dits > 0 » EN PLUS DE LA COMPARAISON, et ce n'est pas une ceinture de
    # plus : sans lui, cette ligne etait VERTE sur le code d'avant la garde —
    # « 0 lignes de journal pour au moins 0 pannes evitees ». Zero est bien
    # superieur ou egal a zero. L'assertion ne distinguait pas « la garde le
    # dit » de « il n'y a pas de garde », le defaut exact que treize assertions
    # de banc_refaire.py portaient le meme jour.
    dits = sum(apres[lg]["dits"] for lg in LANGUES[1:])
    dit(dits > 0 and dits >= (etr_avant - etr_apres),
        "chaque demande etrangere retenue par la garde le dit dans le journal",
        f"{dits} lignes de journal pour au moins "
        f"{etr_avant - etr_apres} pannes evitees")
    dit(apres["fr"]["dits"] == 0,
        "et aucune demande francaise n'a ete retenue par elle",
        str(apres["fr"]["dits"]))

    print("\n  ── et la moisson n'apprend pas l'etranger ──")
    moisson()

    print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
    for r in rate:
        print(f"    RATE : {r}")
    return 1 if rate else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
