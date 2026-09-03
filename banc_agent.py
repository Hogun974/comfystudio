# -*- coding: utf-8 -*-
"""L'agent rend-il vraiment la carte, et refuse-t-il de la rendre au mauvais
moment ?

    python banc_agent.py

agent_noeud.py N'ETAIT COUVERT PAR AUCUN BANC. Dix-sept bancs, deux cent une
mutations, et pas une ligne de ce fichier sous filet : les deux mutations qui
le visaient revenaient « MUTATION PERIMEE — agent_noeud.py n'est pas copie ».
On pouvait couper « free_memory » du corps de /free et les dix-sept bancs
restaient verts, alors que le commentaire de liberer_carte() dit en toutes
lettres que l'un sans l'autre laisse plusieurs gigaoctets sur la carte, « ce
qui donne exactement l'apparence d'un /free qui ne marche pas ».

POURQUOI CE TROU EXISTAIT, et pourquoi il se referme ici. L'agent ne tourne pas
dans le studio : il vit sur la machine a carte, n'importe pas serveur.py, et
banc_conteneur.py le nomme deja comme tel — « tourne sur la machine a carte,
pas ici ». Les bancs du studio ne peuvent donc pas l'exercer comme ils
exercent une route. Mais ce n'est pas une raison de le LIRE au lieu de le
FAIRE TOURNER : ce fichier n'a AUCUNE dependance — la bibliotheque standard, et
rien d'autre, c'est la promesse de sa premiere page — et tout ce qui le relie
au monde passe par UNE fonction, appeler(). Remplacer appeler() par un faux
suffit a faire tourner le vrai code contre un faux ComfyUI et un faux studio.

C'est ce que fait ce banc, et c'est le seul choix honnete des trois qui se
presentaient :

  - un banc STATIQUE, qui relirait le texte de l'agent par l'arbre de syntaxe :
    il aurait vu « free_memory » ecrit, jamais ENVOYE. La ligne peut etre la et
    ne rien atteindre — c'est le defaut que banc_mutations.py reproche aux
    bancs depuis le premier jour.
  - une RECETTE avec une vraie carte : elle mesure ce qu'aucun banc ne peut
    mesurer, mais elle a besoin d'une machine a GPU et ne peut pas entrer dans
    la CI. C'est le role de recette_chemin_page.py, pas celui d'un banc.
  - LE CODE REEL CONTRE UN FAUX RESEAU, ci-dessous. Les fonctions appelees sont
    celles que l'agent execute en service — liberer_carte() et battre_annonce()
    — et ce qui est verifie est ce qui SORT sur le fil.

Statique au sens ou il ne parle a personne : aucun reseau, aucune carte, aucun
studio, aucune dependance. Il entre dans la CI.

CE QU'IL NE VOIT PAS, et il faut l'ecrire : que ComfyUI comprenne « /free » et
rende sa memoire. Un faux ComfyUI repond ce qu'on lui fait repondre. Ce banc
mesure la CONSIGNE — qu'elle parte, qu'elle porte les deux clefs, qu'elle ne
parte pas quand la carte travaille — et le studio, lui, mesure ce qu'elle
rapporte : banc_repartition.py tient l'autre moitie.
"""
import io
import os
import sys
import time as _vrai_temps
from contextlib import redirect_stdout

# La console Windows ecrit en cp1252 et ce banc n'importe pas serveur.py, qui
# est ce qui reconfigure la sortie pour le reste du depot. Sans ces lignes, il
# MEURT sur son propre affichage au premier « « » — une pile d'appels a la
# place du verdict, exactement le defaut releve sur banc_page.py le
# 2 septembre 2026.
for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)

import agent_noeud as AGENT  # noqa: E402

ok, rate = [], []


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


class Stop(BaseException):
    """De quoi sortir de battre_annonce(), qui ne s'arrete jamais.

    Une BaseException et non une Exception : la boucle d'annonce rattrape
    « except Exception » a dessein — ce fil ne doit jamais mourir, c'est lui
    qui rend la machine visible — et une Exception ordinaire serait donc
    avalee, imprimee comme un incident, et la boucle repartirait pour
    toujours. C'est le meme raisonnement que KeyboardInterrupt.
    """


class FauxTemps:
    """time, moins l'attente. La boucle finit par « time.sleep(max(1.0, …)) ».

    Une seconde par battement, trois battements par cas, une dizaine de cas :
    une demi-minute d'attente pure pour un banc qui ne calcule rien. Le module
    est remplace en entier plutot que sa seule fonction sleep, parce que
    l'agent lit « time.time() » dans la meme portee.
    """

    def time(self):
        return _vrai_temps.time()

    def sleep(self, _):
        pass


class FauxReseau:
    """Le seul point par lequel l'agent touche le monde, et on le remplace.

    Tout ce que agent_noeud.py envoie ou recoit passe par appeler() : ComfyUI
    comme le studio. Un faux ici, et le VRAI code tourne — pas une copie de sa
    logique, ce qui ne mesurerait rien de lui (« un banc qui RECOPIE la
    sequence qu'il verifie ne verifie rien de cette sequence »).
    """

    def __init__(self, annonces, statut_free=200, libre_go=2.0):
        self.appels = []            # (url, corps) dans l'ordre du fil
        self.annonces = list(annonces)   # ce que le studio repond, battement
        self.statut_free = statut_free   # par battement
        self.libre_go = libre_go
        self.vues = 0

    def __call__(self, url, jeton=None, corps=None, methode=None, brut=None,
                 secondes=60):
        self.appels.append((url, corps))
        if url.endswith("/system_stats"):
            return 200, {"devices": [{"name": "RTX 2080 Ti",
                                      "vram_total": 11 * 1024 ** 3,
                                      "vram_free": int(self.libre_go * 1024 ** 3)}],
                         "system": {"ram_total": 32 * 1024 ** 3}}
        if url.endswith("/free"):
            return self.statut_free, b""
        if url.endswith("/api/noeud/annonce"):
            self.vues += 1
            if self.vues > len(self.annonces):
                raise Stop()
            return 200, dict(self.annonces[self.vues - 1])
        return 200, {}

    def corps_free(self):
        return [c for u, c in self.appels if u.endswith("/free")]

    def corps_annonces(self):
        return [c for u, c in self.appels if u.endswith("/api/noeud/annonce")]


def battre(travaux, annonces, statut_free=200):
    """Fait tourner le VRAI fil d'annonce contre un faux monde. Rend le faux.

    Les etats de module sont remis a neuf a chaque appel : EN_COURS_ICI et
    DEPUIS_L_ANNONCE sont partages par tout l'agent, et un cas qui heriterait
    de l'etat du precedent mesurerait autre chose que ce qu'il nomme.
    """
    faux = FauxReseau(annonces, statut_free=statut_free)
    vieux_appeler, vieux_temps = AGENT.appeler, AGENT.time
    AGENT.appeler, AGENT.time = faux, FauxTemps()
    AGENT.EN_COURS_ICI[:] = list(travaux)
    AGENT.DEPUIS_L_ANNONCE["remesurer"] = False
    AGENT.DEPUIS_L_ANNONCE["battements"] = 0
    try:
        # L'agent parle a sa console a chaque liberation ; ce banc n'a pas a
        # relayer sa prose au milieu de ses verdicts.
        with redirect_stdout(io.StringIO()):
            AGENT.battre_annonce("http://studio", "jeton", "http://comfy", "")
    except Stop:
        pass
    finally:
        AGENT.appeler, AGENT.time = vieux_appeler, vieux_temps
        AGENT.EN_COURS_ICI.clear()
    return faux


print("\n  ── la consigne qui part sur le fil ──")
# ══ LES DEUX CLEFS DE /free ════════════════════════════════════════════
# « unload_models » decharge les modeles, « free_memory » rend le cache. Le
# commentaire de liberer_carte() porte la mesure : « l'un sans l'autre laisse
# plusieurs gigaoctets, ce qui donne exactement l'apparence d'un /free qui ne
# marche pas ». Cette phrase etait vraie et INVERIFIABLE — on pouvait couper
# l'une des deux clefs et les dix-sept bancs du depot restaient verts.
#
# On appelle la VRAIE fonction et l'on regarde ce qui SORT, plutot que de
# relire son texte : une clef ecrite dans le fichier peut tres bien ne jamais
# atteindre le corps envoye.
#
# LE HASATTR N'EST PAS UNE PRECAUTION, C'EST CE QUI REND LE SENS INVERSE
# MESURABLE. Ce banc est NE avec la liberation de la VRAM : sur l'agent
# d'avant, liberer_carte() n'existe pas du tout. Sans cette garde, le banc
# neuf lance sur le code d'avant mourrait d'un AttributeError — « le banc
# s'est casse », ce qui ne mesure rien — au lieu de ROUGIR sur un cas nomme.
# C'est le meme garde-fou que banc_page.py pose sur web/demarrage.html.
dit(hasattr(AGENT, "liberer_carte"),
    "l'agent sait demander a son ComfyUI de rendre la carte",
    "liberer_carte()" if hasattr(AGENT, "liberer_carte")
    else "aucune fonction de liberation dans cet agent")


def _liberer(statut=200):
    """Appelle la vraie liberer_carte() contre un faux reseau. Rend (faux, res)."""
    faux = FauxReseau([], statut_free=statut)
    vieux = AGENT.appeler
    AGENT.appeler = faux
    try:
        return faux, AGENT.liberer_carte("http://comfy")
    finally:
        AGENT.appeler = vieux


if not hasattr(AGENT, "liberer_carte"):
    _faux, (_abouti, _statut), _refus = FauxReseau([]), (None, None), None
else:
    _faux, (_abouti, _statut) = _liberer()
    _refus = _liberer(404)[1]
_corps = _faux.corps_free()
# LE COMPTE D'ABORD : « les deux clefs sont la » est vrai de zero corps, et
# c'est l'etat qu'on obtient le jour ou la fonction cesse de passer par
# appeler(). Sans cette ligne, tout ce qui suit serait vert de rien.
dit(len(_corps) == 1,
    "liberer_carte() envoie UNE demande, et par appeler()",
    f"{len(_corps)} corps vus")
_c = _corps[0] if _corps else {}
dit(_c.get("unload_models") is True,
    "elle demande le dechargement des modeles",
    f"unload_models = {_c.get('unload_models')!r}")
dit(_c.get("free_memory") is True,
    "ET la liberation du cache : l'une sans l'autre laisse des gigaoctets",
    f"free_memory = {_c.get('free_memory')!r}")
dit(any(u == "http://comfy/free" for u, _ in _faux.appels),
    "et elle s'adresse au /free de CE ComfyUI",
    ", ".join(u for u, _ in _faux.appels) or "aucun appel")
dit((_abouti, _statut) == (True, 200),
    "un ComfyUI qui accepte rend « abouti », avec son statut",
    f"{(_abouti, _statut)}")

# LE STATUT REMONTE, ET IL EST LE DIAGNOSTIC. Un ComfyUI trop ancien repond 404
# et le studio l'affiche tel quel : sans le chiffre, « la carte n'a rien rendu »
# ne distingue pas une version perimee d'une carte deja vide.
dit(_refus == (False, 404),
    "un ComfyUI qui refuse rend le refus AVEC son statut, pas un simple faux",
    f"{_refus}")


print("\n  ── l'autre moitie du garde-fou, celle que le studio ne peut PAS tenir ──")
# ══ « not EN_COURS_ICI » ═══════════════════════════════════════════════
# Le studio decide de reclamer la carte sur ce qu'il savait au DEBUT du
# battement. Entre sa decision et l'arrivee de sa reponse, la boucle de l'agent
# a pu prendre un travail : lui seul le sait a temps, et c'est pourquoi cette
# moitie-la du garde-fou vit ici et pas la-bas. Le commit en fait un argument ;
# rien ne le mesurait.
#
# Les trois cas se lisent ensemble. Le premier seul serait vert d'un agent qui
# libere TOUJOURS, le second seul vert d'un agent qui ne libere JAMAIS.
_libre = battre([], [{"liberer": True}, {}])
dit(len(_libre.corps_free()) == 1,
    "une machine au repos a qui le studio reclame la carte la REND",
    f"{len(_libre.corps_free())} demande(s) de liberation")

_occupe = battre(["tache-1"], [{"liberer": True}, {}])
dit(not _occupe.corps_free(),
    "une machine qui CALCULE ne la rend pas, meme si le studio la reclame",
    f"{len(_occupe.corps_free())} demande(s) — le studio ne peut pas savoir "
    "qu'un travail vient d'etre pris" if _occupe.corps_free()
    else "le travail pris entre-temps est protege")

_muet = battre([], [{}, {}])
dit(not _muet.corps_free(),
    "et sans consigne, l'agent ne libere rien de lui-meme",
    f"{len(_muet.corps_free())} demande(s) non reclamee(s)")

# LE COMPTE, une seconde fois et pour la meme raison : les trois cas ci-dessus
# seraient tous les trois verts si battre_annonce() s'arretait avant d'avoir
# rien fait — une exception avalee par son « except Exception », et le banc ne
# verrait qu'un fil qui n'a jamais tourne.
dit(len(_occupe.corps_annonces()) >= 2 and len(_muet.corps_annonces()) >= 2,
    "et le fil d'annonce a bien tourne dans les trois cas",
    f"{len(_libre.corps_annonces())}, {len(_occupe.corps_annonces())}, "
    f"{len(_muet.corps_annonces())} annonces")


print("\n  ── ce que l'agent rapporte au studio ──")
# CE QUE LA LIBERATION A DONNE REMONTE. Sans ce rapport, le studio ne distingue
# pas « ComfyUI trop ancien » de « la carte etait deja vide » — c'est ce que
# banc_repartition.py lit de son cote, sous le nom « libere ».
_rapports = [c.get("libere") for c in _libre.corps_annonces()
             if isinstance(c, dict) and c.get("libere") is not None]
dit(len(_rapports) == 1 and _rapports[0] == {"ok": True, "statut": 200},
    "le resultat du /free remonte au studio, une fois",
    f"{_rapports}")

# ET « travaux » A CHAQUE ANNONCE. C'est la moitie que le studio LIT pour
# savoir, apres un redemarrage, qu'un rendu tourne deja ici — sinon il remet la
# demande en file et la carte fait deux fois le meme travail.
_annonces_occupe = [c for c in _occupe.corps_annonces() if isinstance(c, dict)]
dit(bool(_annonces_occupe)
    and all(c.get("travaux") == ["tache-1"] for c in _annonces_occupe),
    "et chaque annonce dit ce que CETTE machine calcule",
    f"{[c.get('travaux') for c in _annonces_occupe]}")

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
sys.exit(1 if rate else 0)
