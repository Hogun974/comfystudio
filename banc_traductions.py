#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ce qu'une traduction peut casser sans que rien ne leve.

UNE TRADUCTION NE PLANTE PAS, ELLE MENT. C'est ce qui la rend dangereuse : un
« {n} » oublie dans la version anglaise ne leve aucune exception — la phrase
s'affiche, entiere, sans le chiffre qu'elle annonce. Une cle qui manque dans
une langue ne casse rien non plus : le repli rend le francais, et l'utilisateur
anglais voit une phrase francaise au milieu de son interface sans que personne
au studio ne l'apprenne jamais.

CE BANC MESURE DONC CE QUI NE SE VOIT PAS :

  - AUCUNE CLE NE MANQUE dans une langue servie. Une interface a moitie
    traduite est pire qu'une interface qui n'a jamais promis de l'etre.
  - LES VALEURS INTERPOLEES SONT LES MEMES d'une langue a l'autre. C'est la
    verification qui rapporte le plus : elle attrape le « {titre} » oublie, le
    « {secondes} » devenu « {seconds} » en traduisant le NOM de la valeur, et
    la valeur ajoutee d'un seul cote.
  - LA REGLE DU PLURIEL EST CELLE DE LA LANGUE. Elle etait recopiee a la main
    dans la page, en francais, a chaque endroit qui compte quelque chose :
    « ${n} echange${n > 1 ? "s" : ""} ». Cette regle-la est FAUSSE en anglais
    des zero — « 0 exchanges » — et la recopier vingt fois garantit qu'une des
    vingt sera oubliee.
  - LE CHOIX DE LA LANGUE se fait sur le cookie, et l'en-tete du navigateur ne
    sert que de premiere valeur. Un francophone sur un Windows anglais doit
    pouvoir revenir au francais et y rester.

Aucun studio, aucun reseau, aucune carte : ce banc n'importe que
traductions.py, qui n'importe rien.

    python banc_traductions.py
"""
import os
import re
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)

import traductions as TR  # noqa: E402

ok, rate = [], []


def dit(vrai, quoi, releve=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok  ' if vrai else 'RATE'} {quoi}"
          + (f" — {releve}" if releve else ""))


# Les valeurs interpolees d'un gabarit : « {titre} », « {secondes} ». On ne
# releve pas « {} » ni « {0} » — le dictionnaire ne s'en sert pas, et les
# accepter ferait passer pour une valeur nommee ce qui n'en est pas une.
_VALEUR = re.compile(r"\{([a-z_][a-z0-9_]*)\}")


def valeurs(texte):
    if isinstance(texte, (list, tuple)):
        rendu = set()
        for f in texte:
            rendu |= set(_VALEUR.findall(f))
        return rendu
    return set(_VALEUR.findall(texte))


# ── le dictionnaire mesure quelque chose ───────────────────────────────
# SANS CETTE LIGNE, TOUT LE RESTE SERAIT VRAI DE RIEN. Un dictionnaire vide
# n'a aucune cle manquante, aucune valeur qui differe et aucun pluriel faux :
# ce banc se compterait vert sur zero traduction, et c'est exactement l'etat
# qu'il existe pour interdire.
print("\n  ── le dictionnaire ──")
dit(len(TR.TEXTES) >= 40,
    "le dictionnaire porte les textes qu'on lui demande de garder",
    f"{len(TR.TEXTES)} cles, {len(TR.LANGUES)} langues")
dit(TR.LANGUES[0] == "fr",
    "le francais est la langue source : c'est lui qui fait foi",
    str(TR.LANGUES))

print("\n  ── aucune cle ne manque ──")
manquantes = {}
for lg in TR.LANGUES:
    absentes = [c for c, e in TR.TEXTES.items() if not e.get(lg)]
    if absentes:
        manquantes[lg] = absentes
dit(not manquantes,
    "chaque cle est ecrite dans CHAQUE langue servie",
    "; ".join(f"{lg} : {len(v)} manquante(s) — {', '.join(v[:3])}"
              for lg, v in manquantes.items())
    or f"{len(TR.TEXTES)} x {len(TR.LANGUES)}")

# ET AUCUNE LANGUE INCONNUE NE TRAINE DANS UNE ENTREE. Une colonne « es »
# ecrite dans trois entrees puis oubliee ne serait jamais servie et ne
# rougirait nulle part : elle donnerait l'impression que l'espagnol existe.
egarees = {c: sorted(set(e) - set(TR.LANGUES))
           for c, e in TR.TEXTES.items() if set(e) - set(TR.LANGUES)}
dit(not egarees,
    "et aucune entree ne porte une langue que LANGUES ne sert pas",
    "; ".join(f"{c} : {v}" for c, v in list(egarees.items())[:3]) or "aucune")

print("\n  ── les valeurs interpolees se retrouvent d'une langue a l'autre ──")
# LA VERIFICATION QUI RAPPORTE LE PLUS. « {titre} » oublie dans la traduction
# ne leve rien : la phrase s'affiche entiere, sans le nom du moteur qu'elle
# annonce. Traduire le NOM de la valeur — « {secondes} » devenu « {seconds} »
# — ne leve rien non plus : T() rattrape le KeyError et rend le gabarit brut,
# accolades comprises, a l'ecran.
ecarts = []
for cle, entree in TR.TEXTES.items():
    ref = valeurs(entree["fr"])
    for lg in TR.LANGUES[1:]:
        if lg not in entree:
            continue
        v = valeurs(entree[lg])
        if v != ref:
            ecarts.append(f"{cle} [{lg}] {sorted(ref)} vs {sorted(v)}")
dit(not ecarts,
    "chaque traduction pose exactement les memes valeurs que le francais",
    " / ".join(ecarts[:3]) or
    f"{sum(len(valeurs(e['fr'])) for e in TR.TEXTES.values())} valeurs verifiees")

print("\n  ── le pluriel est une regle de la langue ──")
# LES DEUX LANGUES NE COMPTENT PAS PAREIL, et c'est tout l'interet d'avoir sorti
# la regle des sites d'appel : le francais ecrit « 0 echange », l'anglais
# « 0 exchanges ». Une regle recopiee a la main dans la page etait la regle
# francaise, appliquee a l'anglais.
dit(TR.PLURIELS["fr"](0) == 0 and TR.PLURIELS["fr"](1) == 0
    and TR.PLURIELS["fr"](2) == 1,
    "le francais met zero et un au singulier",
    f"0->{TR.PLURIELS['fr'](0)} 1->{TR.PLURIELS['fr'](1)} "
    f"2->{TR.PLURIELS['fr'](2)}")
dit(TR.PLURIELS["en"](0) == 1 and TR.PLURIELS["en"](1) == 0
    and TR.PLURIELS["en"](2) == 1,
    "l'anglais met zero au PLURIEL, et lui seul separe un du reste",
    f"0->{TR.PLURIELS['en'](0)} 1->{TR.PLURIELS['en'](1)} "
    f"2->{TR.PLURIELS['en'](2)}")
dit(set(TR.PLURIELS) == set(TR.LANGUES),
    "et chaque langue servie a sa regle",
    f"{sorted(TR.PLURIELS)} pour {sorted(TR.LANGUES)}")

# Les entrees a formes multiples en ont autant dans toutes les langues, et
# assez pour la regle. Une entree a une seule forme la ou la regle en demande
# deux leverait IndexError a l'affichage — sur un pluriel, donc rarement, donc
# tard.
formes, combien = [], 0
for cle, entree in TR.TEXTES.items():
    if not isinstance(entree["fr"], (list, tuple)):
        continue
    combien += 1
    for lg in TR.LANGUES:
        f = entree.get(lg)
        if not isinstance(f, (list, tuple)) or len(f) < 2:
            formes.append(f"{cle} [{lg}]")
# « combien » EN PLUS DE « pas d'ecart » : sans lui, ce cas etait vert parce
# qu'il n'y avait AUCUNE entree a formes multiples — son propre releve le
# disait, « aucune entree a formes, ou toutes completes », et personne ne
# l'aurait lu. C'est le defaut que treize assertions de banc_refaire.py
# portaient le 2 septembre : verte parce que rien ne s'est passe.
dit(combien > 0 and not formes,
    "une entree qui compte porte toutes ses formes dans toutes les langues",
    ", ".join(formes[:3]) or f"{combien} entree(s) a formes")

# ET LES DEUX FORMES DIFFERENT VRAIMENT. Une entree dont le singulier et le
# pluriel sont identiques passerait les deux cas ci-dessus tout en ne comptant
# rien — c'est le cas de « conversation » en anglais, ou seul le « s » change,
# mais pas celui de « {n} echange » qui doit s'accorder.
sourdes = [c for c, e in TR.TEXTES.items()
           if isinstance(e["fr"], (list, tuple)) and e["fr"][0] == e["fr"][1]]
dit(not sourdes,
    "et ses deux formes francaises different : sinon elle ne compte rien",
    ", ".join(sourdes[:3]) or f"{combien} accordees")

# LE RENDU, ET PAS SEULEMENT LA TABLE. Les cas ci-dessus lisent le
# dictionnaire ; celui-ci fait passer un nombre par T() dans les deux langues,
# c'est-a-dire par le chemin que le studio empruntera.
dit(TR.T("compte.echanges", "fr", nombre=0) == "0 echange"
    and TR.T("compte.echanges", "fr", nombre=2) == "2 echanges",
    "et T() rend le francais accorde a la francaise",
    f"0 -> « {TR.T('compte.echanges', 'fr', nombre=0)} », "
    f"2 -> « {TR.T('compte.echanges', 'fr', nombre=2)} »")
dit(TR.T("compte.echanges", "en", nombre=0) == "0 exchanges"
    and TR.T("compte.echanges", "en", nombre=1) == "1 exchange",
    "et l'anglais a l'anglaise — c'est le zero qui les separe",
    f"0 -> « {TR.T('compte.echanges', 'en', nombre=0)} », "
    f"1 -> « {TR.T('compte.echanges', 'en', nombre=1)} »")

print("\n  ── ce que T() fait quand quelque chose manque ──")
# UN MOT MANQUANT NE DOIT PAS RENDRE UNE PAGE BLANCHE. Le studio qui repond en
# francais a un anglophone est genant ; le studio qui rend 500 est casse.
dit(TR.T("cle.qui.n.existe.pas", "en") == "cle.qui.n.existe.pas",
    "une cle inconnue rend sa propre cle, et ne leve pas",
    TR.T("cle.qui.n.existe.pas", "en"))
une = next(c for c, e in TR.TEXTES.items() if valeurs(e["fr"]))
dit("{" in TR.T(une, "fr"),
    "une valeur manquante rend le gabarit BRUT, accolades comprises : il se "
    "voit", TR.T(une, "fr")[:60])
dit(TR.T("erreur.corps_illisible", "kl") == TR.T("erreur.corps_illisible", "fr"),
    "une langue qu'on ne sert pas retombe sur le francais",
    TR.T("erreur.corps_illisible", "kl"))

print("\n  ── quelle langue on sert ──")
dit(TR.langue_choisie("en", "fr-FR,fr;q=0.9") == "en",
    "le choix explicite passe AVANT le navigateur",
    TR.langue_choisie("en", "fr-FR,fr;q=0.9"))
dit(TR.langue_choisie("", "en-US,en;q=0.9,fr;q=0.8") == "en",
    "sans choix, la premiere langue du navigateur qu'on sache servir",
    TR.langue_choisie("", "en-US,en;q=0.9,fr;q=0.8"))
dit(TR.langue_choisie("", "de-DE,de;q=0.9,es;q=0.8") == "fr",
    "et le francais quand on n'en sert aucune",
    TR.langue_choisie("", "de-DE,de;q=0.9,es;q=0.8"))
dit(TR.langue_choisie("kl", "en-US") == "en",
    "un cookie fabrique a la main ne fait pas servir n'importe quoi",
    TR.langue_choisie("kl", "en-US"))
dit(TR.langue_choisie("", "") == "fr",
    "et sans rien du tout, le francais", TR.langue_choisie("", ""))

print("\n  ── ce que la page recoit ──")
plat = TR.textes_de("en")
dit(set(plat) == set(TR.TEXTES),
    "la page recoit TOUTES les cles, jamais un sous-ensemble",
    f"{len(plat)} sur {len(TR.TEXTES)}")
dit(plat["erreur.corps_illisible"] == TR.TEXTES["erreur.corps_illisible"]["en"],
    "et elle les recoit dans la langue demandee",
    plat["erreur.corps_illisible"])

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
for r in rate:
    print(f"    RATE : {r}")
sys.exit(1 if rate else 0)
