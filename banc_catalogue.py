# -*- coding: utf-8 -*-
"""Le catalogue promet-il ce qu'il va vraiment telecharger ?

    python banc_catalogue.py

L'installeur annonce « ~N Go a prendre » avant de lancer un telechargement de
plusieurs dizaines de minutes. Ce chiffre est la seule chose sur laquelle
quelqu'un decide, et il se fabrique par une somme : un fichier absent de la
table des tailles y compte pour ZERO, en silence.

C'est arrive. « fluidifier » annonçait « ~0 Go a prendre » — la taille de
film_net n'avait jamais ete relevee. Un plancher presente comme un total est
une promesse qu'on ne tient pas, et celle-la se lisait « c'est gratuit ».

Ce banc refuse desormais qu'un fichier requis n'ait pas de taille, sauf a etre
NOMME dans catalogue.SANS_TAILLE avec sa raison. Il verifie aussi les deux
sens : une exception qui ne correspond plus a rien se retire, sinon elle
couvrira un jour un fichier neuf portant le meme nom.

Statique, sans reseau : il entre dans la CI. Ce qu'il ne peut pas savoir, c'est
si une taille RELEVEE est juste — seul un telechargement le dirait.
"""
import io
import os
import re
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import catalogue as C  # noqa: E402

ok, rate = [], []


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


REQUIS = C.fichiers_requis(C.CATALOGUE)
dit(len(REQUIS) >= 20, f"{len(REQUIS)} fichiers a telecharger dans le catalogue",
    f"{len(C.CATALOGUE)} moteurs")

sans = sorted(f"{s}/{n}" for s, n in REQUIS - set(C.TAILLES) - set(C.SANS_TAILLE))
dit(not sans, "chaque fichier requis a une taille, ou une raison de ne pas en avoir",
    ", ".join(sans) or "aucun trou muet")

mortes = sorted(f"{s}/{n}" for s, n in set(C.SANS_TAILLE) - REQUIS)
dit(not mortes, "aucune exception perimee dans SANS_TAILLE",
    ", ".join(mortes) or "aucune")

muettes = [f"{s}/{n}" for (s, n), pourquoi in C.SANS_TAILLE.items()
           if not (pourquoi or "").strip()]
dit(not muettes, "chaque exception dit POURQUOI la taille manque",
    ", ".join(muettes) or "toutes")

# Une taille relevee a zero ne se distingue pas d'une taille absente, et c'est
# le defaut d'origine sous une autre forme.
nulles = sorted(f"{s}/{n}" for (s, n), go in C.TAILLES.items() if not go)
dit(not nulles, "aucune taille relevee a zero", ", ".join(nulles) or "aucune")

# Une taille pour un fichier que plus personne ne telecharge est du poids mort
# qui fausse les sommes le jour ou un moteur reprend ce nom.
orphelines = sorted(f"{s}/{n}" for s, n in set(C.TAILLES) - REQUIS)
dit(not orphelines, "aucune taille orpheline", ", ".join(orphelines) or "aucune")

# CE QUI EST AFFICHE, et non le drapeau qui le decide. La version d'avant
# recopiait le corps de poids_incertain et le comparait a lui-meme — « f(x) !=
# f(x) », une tautologie — en annonçant dans son commentaire qu'elle gardait ce
# que l'installeur ecrit. Elle n'importait meme pas installation.py. Pendant ce
# temps, DEUX totaux de l'installeur, dont celui qui precede l'ecriture sur le
# disque, annonçaient toujours « environ 0 Go ».
dit(C.annonce_poids(["fluidifier"]) == "taille inconnue",
    "une taille jamais relevee s'annonce comme telle",
    C.annonce_poids(["fluidifier"]))
dit(C.annonce_poids(["audio"]) == "a installer a la main",
    "un moteur sans source automatique ne s'annonce pas a zero",
    C.annonce_poids(["audio"]))
dit(C.annonce_poids(["detourer"]).endswith("Mo"),
    "sous le demi-gigaoctet on passe aux megaoctets — « ~0 Go » se lisait "
    "« c'est gratuit »", C.annonce_poids(["detourer"]))
_gros = max(C.CATALOGUE, key=lambda c: C.poids([c]))
dit(C.annonce_poids([_gros]).startswith("~") and "Go" in C.annonce_poids([_gros]),
    f"et un gros moteur garde ses gigaoctets — {_gros}", C.annonce_poids([_gros]))

# UN SEUL ENDROIT MET UN POIDS EN PHRASE. C'est la seule facon de ne pas
# recommencer : la correction precedente n'avait touche que les lignes PAR
# MOTEUR, et les deux TOTAUX etaient restes faux.
#
# ATTENDU_AILLEURS nomme ce qui n'est pas encore passe par annonce_poids, avec
# sa raison. Une entree ici est un aveu, pas une dispense.
ATTENDU_AILLEURS = {
    "serveur.py": "catalogue_texte formate encore POIDS a la main ; le fichier "
                  "est tenu par un autre chantier a l'heure ou ce banc est "
                  "ecrit, et une correction concurrente s'y perdrait",
}
_EN_PHRASE = re.compile(r'\{[^{}]*(?:POIDS|poids)[^{}]*\}\s*Go')
# LU UNE SEULE FOIS. Les deux verifications se contredisaient — « un seul
# endroit » vert et « aveu perime » rouge sur le meme fichier — parce qu'elles
# le relisaient chacune de leur cote pendant qu'un autre chantier l'ecrivait.
# Un banc qui lit deux fois un fichier qui bouge mesure deux etats differents.
_SOURCES = {}
for _nom in ("installation.py", "serveur.py"):
    _chemin = os.path.join(ICI, _nom)
    if os.path.exists(_chemin):
        _SOURCES[_nom] = io.open(_chemin, encoding="utf-8").read()

en_dur = sorted(n for n, t in _SOURCES.items()
                if _EN_PHRASE.search(t) and n not in ATTENDU_AILLEURS)
dit(not en_dur, "aucun poids mis en phrase hors de annonce_poids",
    ", ".join(en_dur) or "un seul endroit")

perimees = sorted(n for n in ATTENDU_AILLEURS
                  if n in _SOURCES and not _EN_PHRASE.search(_SOURCES[n]))
dit(not perimees, "aucun aveu perime dans ATTENDU_AILLEURS",
    ", ".join(perimees) or f"il en reste {len(ATTENDU_AILLEURS)}")

# L'union et non la somme : deux moteurs partagent des fichiers, et les
# additionner surestimerait le telechargement — c'est la raison d'etre de
# poids(), et rien ne la verifiait.
paires = [(a, b) for a in C.CATALOGUE for b in C.CATALOGUE
          if a < b and (C.fichiers_requis([a]) & C.fichiers_requis([b]))]
dit(bool(paires), f"{len(paires)} paires de moteurs partagent des fichiers",
    "l'union a donc un sens")
if paires:
    # LA PAIRE QUI PARTAGE LE PLUS, et une inegalite STRICTE. « < somme + 0,05 »
    # etait inerte : une somme naive vaut exactement la somme, donc la
    # verification passait aussi sans l'union. Et une paire au recouvrement
    # negligeable ne prouve rien non plus.
    a, b = max(paires, key=lambda p: sum(
        C.TAILLES.get(f, 0.0)
        for f in C.fichiers_requis([p[0]]) & C.fichiers_requis([p[1]])))
    ensemble, separes = C.poids([a, b]), C.poids([a]) + C.poids([b])
    dit(ensemble < separes - 0.5, f"et poids() les compte une seule fois — {a} + {b}",
        f"{ensemble} Go ensemble contre {separes:.1f} additionnes")

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
for r in rate:
    print("    a regarder :", r)
sys.exit(1 if rate else 0)
