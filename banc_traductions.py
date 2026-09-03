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
  - AUCUNE VALEUR NE PORTE LE NOM D'UN PARAMETRE DE T(). Celle-la LEVE, et
    c'est la seule : rendre() ecrit « T(cle, langue, **valeurs) », donc une
    valeur nommee « langue » arrive deux fois sur le meme parametre et Python
    rend un TypeError au moment ou l'on essayait de dire quelque chose a
    quelqu'un. Deux entrees le faisaient le 3 septembre 2026.
  - ET UNE MARQUE QUI COMPTE S'ACCORDE. rendre() oubliait « nombre » : toute
    marque plurielle prenait la forme d'indice zero en francais et celle
    d'indice un en anglais — « 1 accounts registered » — pendant que la page,
    qui lit « v.n », accordait juste. Les deux moities du contrat divergeaient
    la ou rendre() se declare leur specification, et rien ne pouvait le montrer
    tant qu'aucune marque ne comptait quelque chose.
  - LE CHOIX DE LA LANGUE se fait sur le cookie, et l'en-tete du navigateur ne
    sert que de premiere valeur. Un francophone sur un Windows anglais doit
    pouvoir revenir au francais et y rester.
  - AUCUN SITE DE PANNE N'EST SANS CLE. C'est la verification ajoutee le
    2 septembre 2026 au soir avec le branchement du serveur, et la seule qui
    regarde ailleurs que dans le dictionnaire : le dictionnaire portait NEUF
    cles de panne pour treize sites, et les quatre manquantes n'auraient
    rougi nulle part — la ligne de journal francaise serait simplement partie
    a l'ecran d'un lecteur anglais. Un dictionnaire complet ne dit rien de sa
    COUVERTURE.

Aucun studio, aucun reseau, aucune carte : ce banc n'importe que
traductions.py, qui n'importe rien. serveur.py, lui, n'est pas IMPORTE mais
LU — il tirerait aiohttp derriere lui, que la machine du releve n'a pas — et
il est lu par l'arbre de syntaxe et non par expression reguliere : « une
expression reguliere decrit UNE facon d'ecrire la panne, jamais la panne »
(banc_mutations.py, les quatre trous de banc_page.py). Un appel a journal()
etale sur quatre lignes, un argument reordonne, un commentaire au milieu : ast
les voit tous, un motif de texte en voit un.

    python banc_traductions.py
"""
import ast
import inspect
import io
import os
import re
import sys

# LA CONSOLE WINDOWS ECRIT EN cp1252, et ce banc n'importe pas serveur.py —
# c'est serveur.py qui reconfigure la sortie pour tout le reste du depot
# (voir sa tete de fichier). Sans ces quatre lignes, le banc MEURT sur son
# propre affichage au premier titre de section : « UnicodeEncodeError:
# 'charmap' codec can't encode characters », une pile d'appels a la place du
# verdict. Mesure du 2 septembre 2026 : banc_page.py s'arretait ainsi a la
# verification 30 sur 38, et le lanceur de banc_mutations.py ne le voyait pas
# — il pose PYTHONIOENCODING pour ses fils, donc le defaut n'apparaissait
# QUE lorsqu'on lancait le banc a la main, ce que fait tout contributeur.
for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)

import traductions as TR  # noqa: E402

SERVEUR = io.open(os.path.join(ICI, "serveur.py"), encoding="utf-8",
                  newline=None).read()

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

# ── ET AUCUNE NE PORTE LE NOM D'UN PARAMETRE DE T() ──────────────────
# CELLE-CI LEVE, ET C'EST LA SEULE DU FICHIER QUI LEVE. rendre() ecrit
# « T(marque["cle"], langue, **valeurs) » : une valeur nommee « langue » —
# ou « nombre », ou « cle » — arrive alors deux fois sur le meme parametre, et
# Python rend un TypeError, « got multiple values for argument 'langue' ». Pas
# une phrase fausse, pas un trou dans le texte : une exception, au moment
# precis ou l'on essayait de dire quelque chose a quelqu'un.
#
# Mesure du 3 septembre 2026 : deux entrees de « demarrage. » posaient
# « {langue} » — le nom de la langue servie — et faisaient lever le rendu de la
# premiere ligne de l'ecran de premiere mise en route. Rien ne l'aurait dit
# avant qu'un lecteur ne l'atteigne.
#
# LES NOMS INTERDITS SE LISENT DANS LA SIGNATURE, jamais dans une liste ecrite
# a la main : le jour ou T() prend un parametre de plus, ce cas le sait tout
# seul. Enumerer est la faute que ce depot a deja faite cinq fois.
_INTERDITS = {p for p in inspect.signature(TR.T).parameters
              if inspect.signature(TR.T).parameters[p].kind
              is not inspect.Parameter.VAR_KEYWORD}
heurtees = sorted(f"{cle} : {sorted(valeurs(entree['fr']) & _INTERDITS)}"
                  for cle, entree in TR.TEXTES.items()
                  if valeurs(entree["fr"]) & _INTERDITS)
dit(len(_INTERDITS) >= 3 and not heurtees,
    "et aucune valeur ne porte le nom d'un parametre de T(), qui ferait lever "
    "rendre()",
    " / ".join(heurtees[:3]) or f"noms reserves : {sorted(_INTERDITS)}")

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

print("\n  ── une marque de panne mise en phrase ──")
# CE QUE LA PAGE DEVRA FAIRE, exerce ici sans navigateur. Le serveur pose sur
# la tache { "cle", "valeurs" } ; traductions.rendre() est la specification de
# la lecture, et web/index.html devra la refaire a l'identique.
dit(TR.rendre({"cle": "panne.retiree_de_la_file", "valeurs": {}}, "en")
    == "removed from the queue",
    "une marque simple rend la phrase de sa langue",
    TR.rendre({"cle": "panne.retiree_de_la_file", "valeurs": {}}, "en"))
# L'IMBRICATION, ET C'EST ELLE QUI COMPTE. « ERREUR : {quoi} » recoit au site
# d'appel de echouer() une PHRASE du dictionnaire, pas une valeur calculee :
# sans ce tour, l'anglophone lisait « ERROR: la machine n'est pas revenue a
# temps » — une demi-phrase traduite, qui se remarque moins qu'une phrase
# entierement francaise et trompe donc plus longtemps.
_gigogne = {"cle": "panne.echec",
            "valeurs": {"quoi": {"cle": "panne.machine_pas_revenue",
                                 "valeurs": {}}}}
dit(TR.rendre(_gigogne, "en") == "ERROR: the machine did not come back in time",
    "et une valeur qui est elle-meme une marque est rendue d'abord",
    TR.rendre(_gigogne, "en"))
dit(TR.rendre(_gigogne, "fr") == "ERREUR : la machine n'est pas revenue a temps",
    "des deux cotes : le francais du dictionnaire est celui du journal",
    TR.rendre(_gigogne, "fr"))
# UNE VALEUR TECHNIQUE RESTE TECHNIQUE. C'est le second usage du meme gabarit :
# executer() y verse « str(e) », qu'aucune langue ne traduit.
dit(TR.rendre({"cle": "panne.echec", "valeurs": {"quoi": "KeyError('sdxl')"}},
              "en") == "ERROR: KeyError('sdxl')",
    "et une valeur qui n'est PAS une marque traverse telle quelle",
    TR.rendre({"cle": "panne.echec",
               "valeurs": {"quoi": "KeyError('sdxl')"}}, "en"))
dit(TR.rendre(None, "en") == "" and TR.rendre({"valeurs": {}}, "en") == "",
    "et rien du tout ne rend rien du tout, sans lever",
    f"« {TR.rendre(None, 'en')} »")
# ── ET UNE MARQUE QUI COMPTE S'ACCORDE ───────────────────────────────
# rendre() OUBLIAIT « nombre », et T() lisait alors « nombre or 0 » : toute
# marque plurielle prenait la forme d'indice zero en francais et celle
# d'indice un en anglais, quel que soit le compte. « 1 accounts registered ».
# La page, elle, lit « v.n » et accordait juste — les deux moities du contrat
# divergeaient donc exactement la ou cette fonction se declare leur
# specification, et personne ne pouvait le voir tant qu'aucune marque ne
# comptait quelque chose. La premiere est arrivee avec l'ecran de premiere
# mise en route, le 3 septembre 2026.
#
# LES DEUX LANGUES ET LES DEUX COMPTES, sinon le cas serait vrai d'une
# fonction qui rendrait toujours le singulier. L'anglais a 1, c'est ce qui
# distingue les deux regles.
_compte1 = {"cle": "compte.echanges", "valeurs": {"n": 1}}
_compte2 = {"cle": "compte.echanges", "valeurs": {"n": 2}}
dit(TR.rendre(_compte1, "en") == "1 exchange"
    and TR.rendre(_compte2, "en") == "2 exchanges"
    and TR.rendre(_compte1, "fr") == "1 echange"
    and TR.rendre(_compte2, "fr") == "2 echanges",
    "une marque qui compte accorde sa forme, comme la page le fait",
    " / ".join(TR.rendre(m, lg) for lg in ("fr", "en")
               for m in (_compte1, _compte2)))


# ── ce que le SERVEUR nomme, et ce qu'il oublie de nommer ───────────────
# LE DICTIONNAIRE COMPLET NE DIT RIEN DE SA COUVERTURE. Toutes les
# verifications ci-dessus sont vraies d'un dictionnaire qui traduit neuf
# pannes sur treize : elles regardent les entrees, jamais les sites. C'est
# exactement ce qui s'est passe — le dictionnaire du 2 septembre au matin
# portait neuf cles de panne, echouer() avait cinq sites d'appel dont trois
# sans cle, et rien nulle part n'aurait rougi.
print("\n  ── chaque site de panne du serveur porte sa cle ──")
_arbre = ast.parse(SERVEUR)


def _appels(nom):
    """Les appels a cette fonction dans serveur.py, sa definition exclue."""
    return [n for n in ast.walk(_arbre)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            and n.func.id == nom]


def _mots_clefs(appel):
    return {k.arg for k in appel.keywords if k.arg}


def _double_etoile(appel, nom):
    """Vrai si l'appel porte « **nom(...) » — le « ** » a un arg a None."""
    return any(k.arg is None and isinstance(k.value, ast.Call)
               and isinstance(k.value.func, ast.Name) and k.value.func.id == nom
               for k in appel.keywords)


def _etat_erreur(appel):
    return any(k.arg == "etat" and isinstance(k.value, ast.Constant)
               and k.value.value == "erreur" for k in appel.keywords)


# LES LIGNES DE JOURNAL QUI TERMINENT UNE DEMANDE. La page prend la derniere
# du fil et la met dans la bulle : ce sont elles que l'utilisateur lit apres
# une panne, et pas les refus de routes.
pannes = [a for a in _appels("journal") if _etat_erreur(a)]
sans = [ast.unparse(a).splitlines()[0][:60] for a in pannes
        if not _double_etoile(a, "marque_panne")]
# « pannes » EN PLUS DE « pas de site sans cle » : sans ce compte, le cas
# serait vert le jour ou plus aucun appel ne porte « etat="erreur" » — parce
# qu'on l'a ecrit autrement, ou parce que le releve a cesse de mordre. Vrai de
# rien : le defaut que ce banc porte deja sur les pluriels.
dit(len(pannes) >= 8 and not sans,
    "chaque journal(..., etat=erreur) pose une cle a cote de sa phrase",
    "; ".join(sans[:3]) or f"{len(pannes)} sites")

# echouer() ECRIT LA DERNIERE LIGNE de cinq chemins, et sa cle ne dit pas la
# phrase entiere mais son morceau variable : « ERREUR : {quoi} », dont le
# {quoi} est ce que le site d'appel a ecrit. Trois des cinq sites n'en avaient
# pas le 2 septembre au matin.
echecs = _appels("echouer")
muets = [ast.unparse(a).splitlines()[0][:60] for a in echecs
         if len(a.args) < 3 and "panne" not in _mots_clefs(a)]
dit(len(echecs) >= 4 and not muets,
    "et chaque appel a echouer() nomme la phrase qu'il lui passe",
    "; ".join(muets[:3]) or f"{len(echecs)} sites")

# LES CLES CITEES EXISTENT. Une faute de frappe ne leve pas : T() rend la cle
# elle-meme, et « panne.retire_de_la_file » s'affiche dans la bulle. Laid,
# mais seulement pour qui regarde.
citees = {n.value for n in ast.walk(_arbre)
          if isinstance(n, ast.Constant) and isinstance(n.value, str)
          and re.fullmatch(r"(erreur|panne)\.[a-z0-9_]+", n.value)}
inventees = sorted(citees - set(TR.TEXTES))
dit(citees and not inventees,
    "et toute cle citee par le serveur existe au dictionnaire",
    ", ".join(inventees[:3]) or f"{len(citees)} cles citees")

# ET AUCUNE CLE DE PANNE NE DORT. Le sens inverse : une entree qu'aucun site
# ne pose ne sera jamais lue, et sa traduction se perimerait sans bruit — le
# dictionnaire donnerait l'impression de couvrir un chemin qui n'existe plus.
# « panne. » SEULEMENT : ce sont les seules cles dont le serveur soit le seul
# lecteur. Les « famille. » sont composees a l'execution (« famille. » + le
# nom de la famille) et les « compte. » ne servent qu'a la page ; les chercher
# ici les declarerait mortes a tort.
dormantes = sorted(c for c in TR.TEXTES
                   if c.startswith("panne.") and c not in citees)
dit(not dormantes,
    "et aucune cle de panne ne dort : le serveur les pose toutes",
    ", ".join(dormantes[:3]) or
    f"{sum(1 for c in TR.TEXTES if c.startswith('panne.'))} cles de panne")

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
for r in rate:
    print(f"    RATE : {r}")
sys.exit(1 if rate else 0)
