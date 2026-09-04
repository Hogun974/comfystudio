# -*- coding: utf-8 -*-
"""La boucle de l'agent prend-elle, rend-elle et perd-elle ce qu'elle dit ?

    python banc_boucle.py

banc_agent.py a ferme le trou du fichier agent_noeud.py, mais il a nomme lui-
meme ce qu'il laissait dehors, en toutes lettres dans son en-tete :

    « boucle(), qui ne rend jamais la main. Trois de ses regles restent
      decouvertes […] sa fonction « dire » […] est une fermeture interieure,
      injoignable d'ici […] insister(), servir_le_langage(), trouver_ollama()
      et main(). »

SIX FONCTIONS, ET CE SONT CELLES QUI DECIDENT. boucle() est l'ordonnanceur de
la machine a carte : c'est elle qui prend un travail, qui declare la machine
occupee, qui livre les fichiers, qui dit au studio si le rendu a abouti et qui
choisit l'instant ou l'agent se remplace lui-meme. insister() est la seule
chose qui separe un rendu de trois minutes deja fait d'un « echec » affiche a
l'utilisateur parce que le studio redemarrait a la seconde ou l'on rendait.
main() est la porte : un argument lu de travers, et la machine ne s'enrole pas.

« INJOIGNABLE D'ICI » ETAIT UNE CONCLUSION TROP RAPIDE. dire() est une
fermeture, mais boucle() la PASSE a executer() — et executer() est un global du
module. Un faux executer(), et la fermeture arrive dans la main du banc, avec
son frein de 1,5 s et sa regle « on ne jette pas un rendu sur un doute ». Ce
banc l'exerce. C'est la meme lecon que « une seule porte sur le monde » : ce
qu'un banc declare hors de portee merite d'etre reessaye une fois.

CE QU'ON REMPLACE, ET RIEN DE PLUS. Comme banc_agent.py, le code qui tourne est
celui du depot ; ce qui est faux, c'est le monde autour :

  - appeler(), l'unique porte HTTP de ces six fonctions — aucune n'ouvre de
    socket ni ne construit de multipart, contrairement a deposer_entrees() et
    ecouter_progression() ;
  - time, remplace par une HORLOGE QU'ON AVANCE. Ce n'est pas un confort :
    insister() attend dix minutes pour de vrai, et le frein de dire() se mesure
    a la demi-seconde. Une horloge simulee rend ces deux regles mesurables en
    un millieme du temps qu'elles decrivent, et sans une seconde d'attente
    reelle dans la CI ;
  - threading, pour NOTER les trois fils de fond au lieu de les lancer. Un fil
    reellement demarre irait battre contre le faux studio pendant que la boucle
    est mesuree, et l'on ne saurait plus qui a fait quel appel ;
  - PREMIERE_ANNONCE, remplace par un temoin qui compte les appels DEJA faits
    au moment ou la boucle l'attend. Sans ce temoin, « elle attend le premier
    battement » serait vrai d'une boucle qui attend apres avoir pris un rendu ;
  - les collaborateurs de boucle() — executer(), deposer_entrees(),
    lire_sortie(), noter_depot(), faire_le_menage(), se_mettre_a_jour_seul().
    Ils ont deja leur filet dans banc_agent.py ; ce qui est mesure ICI est
    l'ORCHESTRATION : l'ordre, ce qui part sur le fil, et ce qu'on garde.

CE QU'IL NE VOIT PAS, et il faut l'ecrire :

  - Qu'un vrai studio reponde comme le faux. C'est l'autre moitie, et elle est
    tenue ailleurs : banc_repartition.py pour ce que le studio fait d'un
    resultat, recette_chemin_page.py pour le chemin complet.
  - Que executer() rende vraiment ce qu'on lui fait rendre, ni que
    deposer_entrees() ecrive un multipart qu'un ComfyUI accepte. banc_agent.py
    tient cette moitie-la, et ce banc ne la redit pas.
  - Le VRAI parallelisme. Les fils sont notes, pas lances : ce banc mesure que
    la boucle les demande, avec les bons arguments et en daemon, pas ce que
    deux fils font l'un a l'autre. Une course entre EN_COURS_ICI et l'annonce
    ne se mesure pas ici — le commentaire de battre_annonce() dit pourquoi la
    copie est prise au plus tard, et banc_agent.py l'exerce de son cote.
  - os.execv, ni un vrai enrolement. main() est mesuree jusqu'a l'appel de
    boucle(), qu'on remplace par un temoin : ce qui compte est ce qu'elle lui
    passe. La mise en service complete, elle, est le role de banc_noeud.py.

TROIS DEFAUTS TROUVES EN COUVRANT. DEUX SONT CORRIGES, le 4 septembre 2026 et
le jour meme ou ce banc les a montres ; le troisieme est RELEVE, c'est-a-dire
decrit tel qu'il est plutot que tu, et son cas rougira le jour d'une
correction. Les deux corriges tenaient dans l'ecart entre une docstring et sa
condition — ce n'est pas un hasard : la promesse est ce qu'on relit, la
condition est ce qui s'execute.

  - CORRIGE. insister() promettait « on ne recommence que sur un studio MUET ou
    en panne (0, ou 5xx) » et ecrivait « st == 200 or (400 <= st < 500) » :
    tout ce qui n'etait ni 200 ni 4xx passait pour un studio muet. Mesure du
    4 septembre — un 204 et un 202 partent chacun VINGT-QUATRE fois sur six
    cents secondes, puis le travail est declare perdu, en annoncant « studio
    muet (204) » d'une reponse qui disait oui. 204 n'a rien d'hypothetique : le
    studio le sert deja sur /api/noeud/question. La condition dit desormais ce
    que la phrase promettait, et une reponse qui n'est ni 200 ni reessayee se
    DIT au lieu d'etre rendue en silence.

    LA REDIRECTION N'ETAIT PAS LE DECLENCHEUR, contrairement a ce que la
    premiere version de ce paragraphe affirmait, et la correction de cette
    phrase-la vaut le defaut lui-meme : urllib SUIT les redirections. Mesure du
    meme jour contre un serveur d'essai — un 301 avec Location rend 200 a
    appeler(), et seule une BOUCLE de redirections ressort en 301. Un reverse
    proxy qui redirige http vers https n'aurait donc jamais declenche ce
    defaut. Le declencheur reel etait 204, plus banal et moins spectaculaire.

  - CORRIGE. trouver_ollama() promettait « l'adresse ou un modele repond
    VRAIMENT » et testait la veracite du dictionnaire rendu par etat_ollama(),
    qui vaut {"ok": False, "modeles": []} pour un Ollama installe et VIDE —
    non vide, donc vrai. La recherche s'arretait dessus. En conteneur,
    OLLAMA_URL pointe souvent sur un Ollama qu'on vient d'installer et ou l'on
    n'a rien tire : host.docker.internal, ou vivent les modeles de l'hote,
    n'etait alors JAMAIS essaye, et la machine s'annoncait avec « 0 modele(s) »
    sans que rien ne dise pourquoi. On exige « ok » depuis.

  - RELEVE, non corrige. L'annulation est le SEUL rapport au studio qui ne
    passe pas par insister(). Un studio qui redemarre a cet instant n'apprend
    jamais qu'elle a abouti. Ce n'est pas une ligne a changer mais une decision
    a prendre — insister dix minutes sur une annulation tient la boucle
    occupee, et le travail annule, lui, n'existe plus.

ET TROIS TROUS DANS CE BANC-CI, tous les trois trouves par ses propres
mutations, tous les trois du motif de « priorite, » : deux cas ou le faux
reseau retirait de sa trace la demande qui l'arrete — « aucun travail
reclame » restait donc vrai d'une boucle qui en reclamait un — et un cas ou le
fichier illisible etait ecrit EN SECOND, si bien que remplacer le « continue »
par un « break » ne changeait plus rien. Deux autres ont ete trouves a la
relecture et sont ecrits a l'endroit du cas : une assertion sur l'espacement
qui mesurait un sleep ecrit en dur, et des corps de reponse trop anodins pour
que « on ne jette pas un rendu sur un doute » ait quoi que ce soit a refuser.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import types
from contextlib import redirect_stdout

# Meme raison que dans banc_agent.py : ce banc n'importe pas serveur.py, qui
# est ce qui reconfigure la sortie pour le reste du depot, et la console
# Windows ecrit en cp1252. Sans ces lignes il MEURT sur son propre affichage au
# premier « « », et une pile d'appels remplace le verdict.
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
    # str(detail) et non detail : un cas dont le detail est une liste faisait
    # MOURIR ce banc sur son propre affichage, TypeError a la place du verdict.
    # C'est le defaut releve sur banc_page.py le 2 septembre, en plus bete :
    # un banc qui casse en imprimant ne mesure plus rien, et banc_mutations.py
    # rend alors « le banc s'est casse au lieu de rougir ».
    (ok if vrai else rate).append(quoi)
    detail = str(detail) if detail else ""
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


# ══════════════════════════ le faux monde ═════════════════════════════
class Stop(BaseException):
    """De quoi sortir de boucle() et de servir_le_langage(), qui ne s'arretent
    jamais.

    Une BaseException et non une Exception : les deux rattrapent
    « except Exception » a dessein — la boucle pour ne pas mourir sur un
    incident, le fil des questions pour ne jamais emporter l'agent — et une
    Exception ordinaire serait donc avalee, imprimee comme un incident, puis
    la boucle repartirait pour toujours. C'est le meme raisonnement que
    KeyboardInterrupt, et que le Stop de banc_agent.py.
    """


class Horloge:
    """time, mais l'attente est SIMULEE : sleep() avance l'horloge.

    Pas seulement pour aller vite. Deux regles de ce fichier sont des DUREES,
    et sans horloge maitrisee elles ne se mesurent pas :

      - insister() garde un travail dix minutes. Le mesurer pour de vrai
        couterait dix minutes de CI par cas ;
      - le frein de dire() vaut 1,5 s, et il faut pouvoir se placer JUSTE
        au-dessus et JUSTE au-dessous.

    Le budget est le second garde-fou, et il n'est pas decoratif : boucle() ne
    rend jamais la main, et une mutation qui la ferait tourner sans jamais
    appeler le reseau — la porte par laquelle Stop est lance — ferait PENDRE ce
    banc au lieu de le faire rougir. banc_mutations.py appelle cela « pendre
    n'est pas rougir » et compte trente secondes ; ici, un budget de tours
    d'attente arrete la boucle avant, quoi qu'elle fasse.
    """

    def __init__(self, budget=60):
        self.t = 100000.0
        self.budget = budget
        self.dormi = []
        # Un observateur appele a CHAQUE attente. C'est le seul endroit d'ou
        # l'on voit certains etats du module : le drapeau « remesurer » est
        # pose en fin de battement et efface au debut du suivant, donc jamais
        # visible depuis un appel reseau.
        self.observer = None
        self.observe = []

    def time(self):
        return self.t

    def sleep(self, secondes):
        self.dormi.append(secondes)
        if self.observer:
            self.observe.append(self.observer())
        self.t += secondes
        self.budget -= 1
        if self.budget < 0:
            raise Stop()

    def avancer(self, secondes):
        self.t += secondes


class FauxFils:
    """threading, moins les fils : on NOTE ce que la boucle voulait lancer.

    Lancer pour de vrai les trois fils de fond ferait battre l'annonce contre
    le meme faux studio pendant qu'on mesure la boucle, et l'on ne saurait plus
    qui a passe quel appel. Ce qui est mesurable ici, c'est la DEMANDE : quelle
    cible, quels arguments, et daemon ou non — car un fil qui ne serait pas
    daemon empecherait l'agent de s'arreter.
    """

    def __init__(self):
        self.lances = []

    def Thread(self, target=None, args=(), daemon=None):
        self.lances.append(types.SimpleNamespace(
            cible=getattr(target, "__name__", str(target)),
            args=tuple(args), daemon=daemon))
        return self

    def start(self):
        pass

    def __getattr__(self, quoi):
        import threading
        return getattr(threading, quoi)


class FauxSignal:
    """PREMIERE_ANNONCE, avec un temoin de CE QUI S'EST DEJA PASSE.

    « La boucle attend le premier battement avant de reclamer du travail » est
    vrai d'une boucle qui attend APRES avoir reclame. Le temoin releve le
    nombre d'appels reseau deja passes a l'instant de l'attente : zero, ou la
    phrase ne veut rien dire.
    """

    def __init__(self, temoin=None):
        self.attentes = []
        self.temoin = temoin

    def wait(self, delai=None):
        self.attentes.append((delai, self.temoin() if self.temoin else None))
        return True

    def set(self):
        pass


class FauxOs:
    """os, avec l'environnement d'une autre machine.

    __getattr__ n'est consulte que pour ce que l'instance n'a pas : path,
    isdir, remove passent au vrai module, « environ » non. Meme tour que dans
    banc_agent.py.
    """

    def __init__(self, environ=None):
        self.environ = dict(environ or {})

    def __getattr__(self, quoi):
        return getattr(os, quoi)


BACS = []


def bac():
    dossier = tempfile.mkdtemp(prefix="banc_boucle_")
    BACS.append(dossier)
    return dossier


import atexit  # noqa: E402


@atexit.register
def _ranger():
    for dossier in BACS:
        shutil.rmtree(dossier, ignore_errors=True)


def a(nom, defaut=None):
    """Ce que l'agent porte sous ce nom, ou « defaut » s'il ne le porte pas.

    CE N'EST PAS UNE PRECAUTION, C'EST CE QUI REND LE SENS INVERSE MESURABLE.
    Ce banc est ne bien apres les six fonctions qu'il garde : la seule preuve
    inverse possible est de le lancer sur l'agent d'AVANT. Ecrit avec des
    « AGENT.PAUSE_LONGUE » nus, il MOURAIT la — « AttributeError: module
    'agent_noeud' has no attribute 'PREMIERE_ANNONCE' » sur cinq commits
    anterieurs sur six, et banc_mutations.py aurait rendu « le banc s'est casse
    au lieu de rougir ». Un banc qui meurt sur le code d'avant ne mesure pas le
    sens inverse : c'est le meme tour que le « try » de banc_page.py sur
    web/demarrage.html et le « getattr » de banc_version.py.

    Le defaut est un TEMOIN IMPOSSIBLE et jamais la valeur d'aujourd'hui : une
    constante absente doit faire ROUGIR le cas qui la nomme, pas le rendre vert
    en lui soufflant la reponse.
    """
    return getattr(AGENT, nom, defaut)


IMPOSSIBLE = object()


def _absente(nom):
    """Un bouchon pour une fonction que cet agent ne porte pas.

    Il ne LEVE pas : une AttributeError tuerait le banc, et « le banc s'est
    casse » ne mesure rien. Il ne fait rien, et chaque cas de la section
    rougit alors sur sa propre ligne — ce qui est le verdict juste.
    """
    def bouchon(*args, **k):
        return None
    bouchon.__name__ = f"<{nom} absente de cet agent>"
    return bouchon


def pose(nom, valeur):
    """Pose « valeur » sur l'agent et rend de quoi la reprendre. Tolere
    l'absence : un nom que cet agent ne porte pas est retire a la fin."""
    ancien = getattr(AGENT, nom, IMPOSSIBLE)
    setattr(AGENT, nom, valeur)
    return (nom, ancien)


def reprendre(sauves):
    for nom, ancien in sauves:
        if ancien is IMPOSSIBLE:
            try:
                delattr(AGENT, nom)
            except AttributeError:
                pass
        else:
            setattr(AGENT, nom, ancien)


# Les etats de module sont partages par tout l'agent. Un cas qui heriterait de
# l'etat du precedent mesurerait autre chose que ce qu'il nomme — c'est la
# raison pour laquelle battre() remet tout a neuf dans banc_agent.py, et c'est
# la meme ici.
def _neuf():
    if hasattr(AGENT, "EN_COURS_ICI"):
        AGENT.EN_COURS_ICI.clear()
    if hasattr(AGENT, "DEPUIS_L_ANNONCE"):
        AGENT.DEPUIS_L_ANNONCE.update(comfy=None, studio=False,
                                      empreinte_agent="", battements=0,
                                      remesurer=False)


# ══════════════════════════════════════════════════════════════════════
#  1. boucle() — l'ordonnanceur de la machine a carte
# ══════════════════════════════════════════════════════════════════════
# DANS L'ORDRE DE LA CONSEQUENCE. Ce qu'une erreur ici coute a l'utilisateur :
# un rendu pris par une machine qui ne peut pas le faire, une machine qui
# declare libre pendant qu'elle calcule (donc deux cartes sur la meme image),
# un travail fini dont le fichier n'arrive jamais, une annulation prise pour
# une panne — et la machine ecartee du repartiteur pour un incident qui n'est
# pas le sien.
TID = "abcdef1234567890"
TRAVAIL = {"tid": TID, "graphe": {"3": {"class_type": "KSampler"}},
           "entrees": {"image": "chat.png"}}


def tourner(travaux=(), executer=None, deposer=None, lire=None, ollama="",
            sorties="", maj_auto=True, epinglee="", garder=24.0,
            comfy_connu=True, studio_ok=True, arret_apres=1, budget=60,
            reponses=None, battements=1, bouger_battements=False):
    """Lance la VRAIE boucle() contre un faux monde. Rend sa trace.

    « arret_apres » : le nombre de demandes de travail avant que le faux
    reseau ne lance Stop. C'est la porte de sortie ordinaire ; le budget de
    l'horloge est le filet de secours quand la boucle ne reclame rien.
    """
    horloge = Horloge(budget)
    appels = []
    vus = {"menage": [], "notes": [], "maj": [], "dire": [], "entrees": [],
           "sorties_lues": []}
    file = list(travaux)
    reponses = dict(reponses or {})

    def appeler(url, jeton=None, corps=None, methode=None, brut=None,
                secondes=60):
        appels.append(types.SimpleNamespace(
            url=url, corps=corps, brut=brut, jeton=jeton, secondes=secondes,
            t=horloge.t, en_cours=list(a("EN_COURS_ICI", []))))
        if url.endswith("/api/noeud/travail"):
            # Le compte AVANT d'inscrire l'appel : sans cela le dernier tour,
            # celui qui lance Stop, figurerait dans la trace et chaque cas
            # compterait une demande de plus qu'il n'y en a eu.
            pris = len([a for a in appels if a.url.endswith("/travail")])
            if pris > arret_apres:
                appels.pop()
                raise Stop()
            if bouger_battements and hasattr(AGENT, "DEPUIS_L_ANNONCE"):
                AGENT.DEPUIS_L_ANNONCE["battements"] += 1
            return file.pop(0) if file else (204, None)
        for morceau, rep in reponses.items():
            if morceau in url:
                return rep
        return 200, {"ok": True}

    signal = FauxSignal(temoin=lambda: len(appels))
    fils = FauxFils()

    def faux_executer(comfy, graphe, dire=None):
        vus["dire"].append(dire)
        vus.setdefault("executer", []).append(
            (comfy, graphe, list(a("EN_COURS_ICI", []))))
        return executer(comfy, graphe, dire) if executer else ([], 12.0, None)

    def faux_deposer(comfy, entrees, graphe):
        vus["entrees"].append((comfy, entrees, list(a("EN_COURS_ICI", []))))
        return deposer(comfy, entrees, graphe) if deposer else None

    def faux_lire(comfy, f):
        vus["sorties_lues"].append(f.get("filename"))
        return lire(comfy, f) if lire else b"OCTETS"

    sauves = [pose("appeler", appeler), pose("time", horloge),
              pose("threading", fils), pose("PREMIERE_ANNONCE", signal)]
    for _nom_faux in ("faire_le_menage", "noter_depot",
                      "se_mettre_a_jour_seul", "executer", "deposer_entrees",
                      "lire_sortie"):
        sauves.append(pose(_nom_faux, getattr(AGENT, _nom_faux, None)))
    AGENT.faire_le_menage = lambda g, s="": (
        vus["menage"].append((g, s, horloge.t)), 2)[1]
    AGENT.noter_depot = lambda s, f, quand: vus["notes"].append(
        (s, f.get("filename"), quand))
    # Le battement AU MOMENT de la tentative : c'est lui qui dit « une fois par
    # battement », et le compter apres coup ne le dirait pas.
    AGENT.se_mettre_a_jour_seul = lambda studio, attendue, epingle: vus[
        "maj"].append((studio, attendue, epingle, len(appels),
                       list(a("EN_COURS_ICI", [])),
                       a("DEPUIS_L_ANNONCE", {}).get("battements")))
    AGENT.executer, AGENT.deposer_entrees = faux_executer, faux_deposer
    AGENT.lire_sortie = faux_lire
    _neuf()
    if hasattr(AGENT, "DEPUIS_L_ANNONCE"):
        AGENT.DEPUIS_L_ANNONCE.update(
            comfy={"carte": "RTX 2080 Ti"} if comfy_connu else None,
            studio=studio_ok, battements=battements,
            empreinte_agent="EMPREINTE")
    sortie, souci, interrompu = io.StringIO(), "", False
    try:
        with redirect_stdout(sortie):
            a("boucle", _absente("boucle"))(
                "http://studio", "JETON", "http://comfy", sorties,
                garder, ollama, epinglee, maj_auto)
    except Stop:
        pass
    except KeyboardInterrupt:
        interrompu = True
    except Exception as e:
        souci = f"{type(e).__name__}: {e}"
    finally:
        reprendre(sauves)
        en_cours = list(a("EN_COURS_ICI", []))
        remesurer = a("DEPUIS_L_ANNONCE", {}).get("remesurer")
        _neuf()
    return types.SimpleNamespace(
        appels=appels, fils=fils.lances, attentes=signal.attentes,
        dit=sortie.getvalue(), souci=souci, interrompu=interrompu,
        horloge=horloge, en_cours=en_cours, remesurer=remesurer, **vus)


def urls(trace, morceau=""):
    return [a.url for a in trace.appels if morceau in a.url]


def premier(trace, morceau):
    return next((a for a in trace.appels if morceau in a.url), None)


# ══ CE QUE CET AGENT PORTE ═════════════════════════════════════════════
# LE PLANCHER DE TOUT LE RESTE, et il n'est pas decoratif. Les six fonctions
# sont plus vieilles que ce banc : la seule preuve inverse possible est de le
# lancer sur l'agent d'AVANT, et il faut alors qu'une fonction absente pose un
# cas NOMME au lieu d'une trace de pile. Sans ces lignes, une section entiere
# pourrait devenir verte a vide — les bouchons de _absente() ne levent pas, et
# « aucun appel a Ollama » serait vrai d'un agent qui n'a pas de fil de langage
# du tout. C'est le meme plancher que « SEUL n banc(s) trouve(s) » dans la
# verification de la CI.
print("\n  ── ce que cet agent porte, avant de mesurer ce qu'il en fait ──")
for _nom, _quoi in [
        ("boucle", "l'ordonnanceur qui prend, fait et rend le travail"),
        ("insister", "la livraison qui garde un travail deja fait"),
        ("servir_le_langage", "le fil qui prete le modele local au studio"),
        ("trouver_ollama", "le choix de l'Ollama, reglage puis voisins"),
        ("modeles_comfy", "l'inventaire des modeles de cette machine"),
        ("main", "la porte d'entree et ses arguments"),
        ("battre_annonce", "le fil qui rend la machine visible"),
        ("PREMIERE_ANNONCE", "le signal que la boucle attend avant de prendre"),
        ("DEPUIS_L_ANNONCE", "ce que le fil d'annonce apprend a la boucle"),
        ("EN_COURS_ICI", "ce que CETTE machine calcule en ce moment")]:
    dit(hasattr(AGENT, _nom), f"l'agent porte {_nom} — {_quoi}",
        "" if hasattr(AGENT, _nom) else "absent de cet agent")

print("\n  ── ce que la boucle demarre, et ce qu'elle attend avant de prendre ──")

_t = tourner([(200, TRAVAIL)], ollama="http://ollama:11434")
dit(_t.attentes == [(60, 0)],
    "la boucle attend le premier battement AVANT de reclamer le moindre travail",
    f"attentes={_t.attentes} (delai, appels deja passes)")

dit([f.cible for f in _t.fils] == ["ecouter_progression", "battre_annonce",
                                   "servir_le_langage"],
    "trois fils de fond partent avec elle, dans cet ordre",
    f"{[f.cible for f in _t.fils]}")

# TOUS DAEMON. Un seul qui ne le serait pas, et l'agent ne s'arreterait plus :
# ctrl+C rendrait la main a la boucle, le processus attendrait un fil qui ne
# finit jamais, et l'utilisateur tuerait la machine au lieu de l'arreter.
dit(all(f.daemon for f in _t.fils),
    "et tous en daemon — sinon l'agent ne s'arreterait jamais",
    f"{[(f.cible, f.daemon) for f in _t.fils]}")

dit([f.args for f in _t.fils] == [("http://comfy",),
                                  ("http://studio", "JETON", "http://comfy",
                                   "http://ollama:11434"),
                                  ("http://studio", "JETON",
                                   "http://ollama:11434")],
    "chaque fil recoit ce qu'il lui faut, et rien de plus",
    f"{[f.args for f in _t.fils]}")

_sans = tourner([(200, TRAVAIL)], ollama="")
dit([f.cible for f in _sans.fils] == ["ecouter_progression", "battre_annonce"],
    "sans modele de langage local, le fil des questions ne part pas",
    f"{[f.cible for f in _sans.fils]}")

print("\n  ── pas de carte, pas de studio : on ne prend rien ──")

# PRENDRE UN TRAVAIL QU'ON NE PEUT PAS FAIRE le fait echouer chez
# l'utilisateur, alors qu'une autre machine l'aurait pris. Le fil d'annonce,
# lui, continue de battre : la machine reste VISIBLE sans sa carte, et c'est
# justement celle dont le studio a besoin quand son propre Ollama tombe.
# « arret_apres » TRES GRAND, ET C'EST LA MUTATION QUI L'A EXIGE. Ecrits avec
# arret_apres=0, ces deux cas etaient VERTS sous la mutation qui retire la
# garde : le faux reseau lance Stop a la premiere demande de travail et la
# retire de sa trace, si bien que « aucun travail reclame » restait vrai d'une
# boucle qui en reclamait un. Le filet ne pouvait pas voir le trou qu'il
# nomme — le motif de « priorite, », dans le banc qui vient le fermer. Ici,
# rien ne peut supprimer la demande : c'est le budget de l'horloge qui arrete.
_t = tourner(comfy_connu=False, arret_apres=10 ** 6, budget=8)
dit(urls(_t, "/travail") == [],
    "une machine dont ComfyUI ne repond pas ne reclame aucun travail",
    f"{len(_t.appels)} appel(s), {urls(_t)}")
dit(_t.horloge.dormi and set(_t.horloge.dormi) == {a("PAUSE_LONGUE", -1)},
    "et elle repasse toutes les vingt secondes, pas trois",
    f"attentes={sorted(set(_t.horloge.dormi))}")

_t = tourner(studio_ok=False, arret_apres=10 ** 6, budget=8)
dit(urls(_t, "/travail") == [],
    "un studio qui n'a pas repondu 200 au dernier battement non plus",
    f"{len(_t.appels)} appel(s)")

_t = tourner([(200, TRAVAIL)], arret_apres=1, budget=8)
dit(urls(_t, "/travail") == ["http://studio/api/noeud/travail"],
    "carte connue ET studio joignable : elle reclame, et par la meme route",
    f"{urls(_t, '/travail')}")

print("\n  ── un travail pris, fait, et rendu ──")

_t = tourner([(200, TRAVAIL)],
             executer=lambda c, g, d: ([{"filename": "resultat 1&2.png",
                                         "subfolder": "sous", "type": "output"}],
                                       7.42, None))

# LA MACHINE SE DECLARE OCCUPEE AVANT DE TOUCHER A LA CARTE. EN_COURS_ICI est
# ce que le fil d'annonce recopie a chaque battement : pose trop tard, le
# studio croit la machine libre pendant tout le depot des entrees, et un studio
# qui redemarre dans cette fenetre relance une demande que la carte rend deja.
dit(_t.entrees and _t.entrees[0][2] == [TID],
    "le travail est annonce EN COURS avant meme le depot des entrees",
    f"EN_COURS_ICI au depot = {_t.entrees[0][2] if _t.entrees else 'jamais depose'}")
dit(_t.entrees and _t.entrees[0][:2] == ("http://comfy", {"image": "chat.png"}),
    "et les entrees venues avec lui vont a la carte de CETTE machine",
    f"{_t.entrees[0][:2] if _t.entrees else None}")

_fichier = premier(_t, "/api/noeud/fichier")
dit(_fichier is not None and _fichier.brut == b"OCTETS",
    "le fichier produit part au studio en octets bruts",
    f"brut={_fichier.brut!r}" if _fichier else "aucun depot")

# LE NOM PASSE PAR L'ADRESSE, donc il doit etre ENCODE. Un « & » non encode
# coupe le nom en deux parametres, et le studio enregistre un fichier qui n'a
# plus le nom que ComfyUI lui a donne — celui que le graphe rappelle.
dit(_fichier is not None
    and _fichier.url == f"http://studio/api/noeud/fichier?tid={TID}"
                        "&nom=resultat+1%262.png",
    "le tid et le NOM ENCODE voyagent dans l'adresse du depot",
    _fichier.url if _fichier else "aucun depot")

_res = premier(_t, "/api/noeud/resultat")
dit(_res is not None and _res.corps == {
        "tid": TID, "etat": "fini", "erreur": None, "secondes": 7.4,
        "fichiers": [{"filename": "resultat 1&2.png", "subfolder": "sous",
                      "type": "output"}]},
    "le resultat rend l'etat, la duree arrondie et ce qui est REELLEMENT arrive",
    f"{_res.corps}" if _res else "aucun resultat")

dit(_t.notes == [("", "resultat 1&2.png", _t.horloge.t)],
    "et le registre des depots ne retient QUE ce qui est bien arrive",
    f"{_t.notes}")

dit(_t.en_cours == [] and _res is not None and _res.en_cours == [TID],
    "la machine reste occupee jusqu'au resultat, et se libere apres",
    f"pendant={_res.en_cours if _res else '?'}, apres={_t.en_cours}")

# REMESURER TOUT DE SUITE. Sans cela le travail suivant est reclame sur un etat
# vieux de dix a trente secondes — et un ComfyUI mort en fin de rendu, le cas
# classique de l'OOM sur le dernier noeud, fait prendre puis rater le travail
# suivant au lieu de le laisser partir sur l'autre carte.
dit(_t.remesurer,
    "la carte est remesuree tout de suite, pas au prochain cache",
    f"remesurer={_t.remesurer}")

print("\n  ── ce qui rate, et a qui on l'impute ──")

# LE FICHIER ILLISIBLE EST LE PREMIER, ET LA MUTATION L'A EXIGE. Ecrit avec
# l'illisible en second, ce cas etait VERT sous la mutation qui remplace le
# « continue » par un « break » : le premier fichier etait deja parti, et la
# trace ne distinguait plus « on saute celui-la » de « on s'arrete la ». Une
# video rend dix images et c'est la TROISIEME qui manque : ce qu'il faut
# mesurer, c'est que les suivantes partent quand meme.
_t = tourner([(200, TRAVAIL)],
             executer=lambda c, g, d: ([{"filename": "perdu.png"},
                                        {"filename": "bon.png"}], 5.0, None),
             lire=lambda c, f: None if f["filename"] == "perdu.png" else b"A",
             )
_res = premier(_t, "/api/noeud/resultat")
dit(urls(_t, "/api/noeud/fichier") == [
        f"http://studio/api/noeud/fichier?tid={TID}&nom=bon.png"],
    "un fichier illisible sur le disque n'emporte pas les SUIVANTS",
    f"{urls(_t, '/api/noeud/fichier')}")
dit(_res is not None and _res.corps["erreur"] == "fichier illisible : perdu.png"
    and [f["filename"] for f in _res.corps["fichiers"]] == ["bon.png"],
    "et le resultat dit lequel manque, sans effacer celui qui est passe",
    f"{_res.corps if _res else None}")
dit([n[1] for n in _t.notes] == ["bon.png"],
    "seul le fichier arrive entre au registre — l'autre pourra etre repris",
    f"{[n[1] for n in _t.notes]}")

_t = tourner([(200, TRAVAIL)],
             executer=lambda c, g, d: ([{"filename": "a.png"}], 5.0, None),
             reponses={"/api/noeud/fichier": (413, {"erreur": "trop gros"})})
_res = premier(_t, "/api/noeud/resultat")
dit(_res is not None and _res.corps["erreur"] == "envoi refuse par le studio (413)"
    and _res.corps["fichiers"] == [],
    "un depot refuse par le studio est dit tel quel, avec son code",
    f"{_res.corps['erreur'] if _res else None}")
dit(_t.notes == [],
    "et rien n'entre au registre : on n'effacera pas ici ce qui n'est pas la-bas",
    f"{_t.notes}")

# LA PREMIERE ERREUR EST CELLE QUI REMONTE — « erreur = erreur or ... ». La
# derniere ecraserait la cause par sa consequence : un disque plein donne
# d'abord un fichier illisible, puis dix depots refuses, et c'est le premier
# qui dit ou regarder.
_t = tourner([(200, TRAVAIL)],
             executer=lambda c, g, d: ([{"filename": "a.png"},
                                        {"filename": "b.png"}], 5.0, None),
             lire=lambda c, f: None)
_res = premier(_t, "/api/noeud/resultat")
dit(_res is not None and _res.corps["erreur"] == "fichier illisible : a.png",
    "deux echecs de suite : c'est le PREMIER qui remonte, pas le dernier",
    f"{_res.corps['erreur'] if _res else None}")


def _executer_interdit(c, g, d):
    raise AssertionError("executer() a ete appele malgre une entree refusee")


_t = tourner([(200, TRAVAIL)], deposer=lambda c, e, g: "entree refusee (extension)",
             executer=_executer_interdit)
_res = premier(_t, "/api/noeud/resultat")
dit(not _t.souci and _res is not None
    and _res.corps["erreur"] == "entree refusee (extension)"
    and _res.corps["secondes"] == 0,
    "une entree qui n'a pas pu etre deposee n'envoie RIEN a la carte",
    f"{_t.souci or (_res.corps if _res else None)}")

print("\n  ── l'annulation, qui n'est pas une panne de la machine ──")

# L'IMPUTER A LA MACHINE LA FERAIT ECARTER DU REPARTITEUR pour un incident qui
# n'est pas le sien : le studio compte les pannes par machine, et une salle ou
# l'on annule beaucoup viderait son parc.
_ANNULE = a("ANNULE", "cet agent ne connait pas l'annulation")
_t = tourner([(200, TRAVAIL)], executer=lambda c, g, d: ([], 3.25, _ANNULE))
_res = premier(_t, "/api/noeud/resultat")
dit(_res is not None and _res.corps == {"tid": TID, "etat": "annule",
                                        "erreur": None, "secondes": 3.2,
                                        "fichiers": []},
    "un travail annule est rendu « annule », sans erreur a imputer a la machine",
    f"{_res.corps if _res else None}")
dit(_t.en_cours == [] and _t.remesurer,
    "la machine se libere et fait remesurer sa carte, comme apres un rendu",
    f"en_cours={_t.en_cours}, remesurer={_t.remesurer}")
dit("annule par le studio" in _t.dit,
    "et la console le dit, avec le temps que la carte a tout de meme passe",
    _t.dit.strip().splitlines()[-1][:80] if _t.dit.strip() else "muette")

# LE DEFAUT. Toutes les autres reponses au studio passent par insister(), qui
# garde dix minutes ; CELLE-CI passe par appeler() en direct. Un studio qui
# redemarre a cet instant n'apprend jamais que l'annulation a abouti — la
# demande reste « en cours d'annulation » chez lui, et la derniere ligne du
# journal, « la seule qui parle de l'arret au passe », n'est jamais ecrite.
# Ce cas RELEVE le comportement d'aujourd'hui plutot que de le taire : le jour
# ou l'on branchera insister() ici, il rougira et il faudra le reecrire.
_t = tourner([(200, TRAVAIL)], executer=lambda c, g, d: ([], 1.0, _ANNULE),
             reponses={"/api/noeud/resultat": (0, "studio muet")})
dit(len(urls(_t, "/api/noeud/resultat")) == 1,
    "RELEVE : l'annulation est le SEUL rapport qui ne soit pas reessaye",
    f"{len(urls(_t, '/api/noeud/resultat'))} envoi(s) pour un studio muet — "
    f"un resultat ordinaire en ferait vingt-quatre")

print("\n  ── un studio qui n'a rien, ou qui repond de travers ──")

_t = tourner([], arret_apres=3, budget=30)
dit(_t.horloge.dormi[:3] == [a("PAUSE_COURTE", -1)] * 3,
    "un studio sans travail (204) ne coute que trois secondes",
    f"{_t.horloge.dormi[:3]}")

_t = tourner([(200, {"tid": TID})], arret_apres=1, budget=30)
dit(a("PAUSE_LONGUE", -1) in _t.horloge.dormi and _t.entrees == [],
    "une reponse 200 SANS graphe est ignoree, et l'on attend vingt secondes",
    f"attentes={_t.horloge.dormi[:2]}, entrees deposees={len(_t.entrees)}")

_t = tourner([(500, {"graphe": {}})], arret_apres=1, budget=30)
dit(_t.entrees == [] and a("PAUSE_LONGUE", -1) in _t.horloge.dormi,
    "un studio en panne (500) ne fait pas prendre un travail fantome",
    f"entrees deposees={len(_t.entrees)}")

print("\n  ── un incident ne tue pas la boucle, et ne bloque pas la machine ──")


def _boum(c, g, d):
    raise RuntimeError("la carte a disparu")


_t = tourner([(200, TRAVAIL), (200, TRAVAIL)], executer=_boum, arret_apres=2,
             budget=30)
dit(len(urls(_t, "/travail")) >= 2 and not _t.souci and len(_t.entrees) == 2,
    "apres un incident, elle repart chercher du travail",
    f"{len(urls(_t, '/travail'))} demande(s), {len(_t.entrees)} travaux "
    f"entames, {_t.souci or 'sans mourir'}")
dit(_t.en_cours == [],
    "et la liste des travaux est VIDEE — sinon le studio attend un resultat "
    "qui ne viendra jamais",
    f"en_cours={_t.en_cours}")
dit(_t.remesurer,
    "la carte est remesuree la aussi : c'est souvent elle qui vient de tomber",
    f"remesurer={_t.remesurer}")
dit("incident : RuntimeError la carte a disparu" in _t.dit,
    "l'incident est nomme dans la console, avec son type",
    [l.strip() for l in _t.dit.splitlines() if "incident" in l][:1])


def _ctrlc(c, g, d):
    raise KeyboardInterrupt()


_t = tourner([(200, TRAVAIL)], executer=_ctrlc, budget=30)
dit(_t.interrompu,
    "ctrl+C n'est PAS avale par le filet a incidents : l'agent s'arrete",
    f"interrompu={_t.interrompu}, souci={_t.souci or 'aucun'}")

print("\n  ── le menage des sorties deja au studio ──")

# Un studio qui n'a jamais de travail : chaque tour coute PAUSE_COURTE, et le
# budget de l'horloge decide de la duree simulee. Il en faut plus de vingt
# minutes pour voir DEUX ecarts, sans quoi « une fois par dix minutes » serait
# vrai d'un menage qui ne passe qu'une fois.
_t = tourner([], sorties="/sorties/comfy", garder=12.0, arret_apres=10 ** 6,
             budget=700)
_ecarts = [round(_t.menage[i + 1][2] - _t.menage[i][2])
           for i in range(len(_t.menage) - 1)]
# L'ecart n'est pas exactement PURGE_TOUS_LES mais le PREMIER tour qui le
# depasse — trois secondes de plus ici, la duree d'un tour a vide. C'est ce
# qu'il faut mesurer : « au plus une fois par dix minutes », pas une horloge.
dit(len(_t.menage) >= 3
    and all(a("PURGE_TOUS_LES", -1) < e <= a("PURGE_TOUS_LES", -1) + a("PAUSE_COURTE", -1)
            for e in _ecarts),
    "le menage passe entre deux travaux, au plus une fois par dix minutes",
    f"{len(_t.menage)} passages, ecarts={_ecarts} pour un delai de "
    f"{a("PURGE_TOUS_LES", -1)} s")
dit(_t.menage and _t.menage[0][:2] == (12.0, "/sorties/comfy"),
    "et il recoit le delai de garde et le dossier donnes a l'agent",
    f"{_t.menage[0][:2] if _t.menage else None}")
dit("2 sortie(s) effacee(s) ici" in _t.dit,
    "ce qui a ete efface est dit, et seulement quand il y en a",
    [l.strip() for l in _t.dit.splitlines() if "effacee" in l][:1])

_t = tourner([], sorties="", arret_apres=10 ** 6, budget=700)
dit(_t.menage == [],
    "sans dossier de sorties, RIEN n'est efface sur la machine de l'utilisateur",
    f"{len(_t.menage)} passage(s)")

print("\n  ── se remplacer soi-meme, et seulement au bon moment ──")

# ICI ET NULLE PART AILLEURS : le travail precedent est rendu, le suivant pas
# encore reclame. C'est le seul instant ou se remplacer ne trahit personne, et
# c'est pourquoi le fil d'annonce se contente de POSER l'empreinte au lieu de
# l'appliquer — son os.execv, tire pendant un rendu, emporterait l'image avec
# le processus.
_t = tourner([(200, TRAVAIL)], epinglee="SHA-EPINGLE", arret_apres=3, budget=30)
dit(len(_t.maj) == 1 and len(urls(_t, "/travail")) == 3,
    "la mise a jour n'est tentee qu'UNE FOIS PAR BATTEMENT, pas a chaque tour",
    f"{len(_t.maj)} tentative(s) pour {len(urls(_t, '/travail'))} demandes de "
    f"travail, a battement constant")
dit(_t.maj and _t.maj[0][:3] == ("http://studio", "EMPREINTE", "SHA-EPINGLE"),
    "avec l'empreinte servie par le studio ET celle qu'on a epinglee",
    f"{_t.maj[0][:3] if _t.maj else None}")
dit(_t.maj and _t.maj[0][4] == [] and _t.maj[0][3] == 0,
    "et jamais pendant un travail : aucun rendu en cours, rien encore reclame",
    f"en_cours={_t.maj[0][4] if _t.maj else '?'}, "
    f"appels deja passes={_t.maj[0][3] if _t.maj else '?'}")

_t = tourner([(200, TRAVAIL)], arret_apres=3, budget=30, bouger_battements=True)
_vus_battements = [m[5] for m in _t.maj]
dit(len(_vus_battements) > 1
    and _vus_battements == sorted(set(_vus_battements)),
    "un battement de plus, une tentative de plus — et jamais deux fois le meme",
    f"battements vus a la tentative : {_vus_battements}")

_t = tourner([(200, TRAVAIL)], maj_auto=False, arret_apres=3, budget=30,
             bouger_battements=True)
dit(_t.maj == [],
    "--sans-maj-auto : la machine ne se remplace jamais toute seule",
    f"{len(_t.maj)} tentative(s)")

# LA QUESTION QUE banc_agent.py A LAISSEE OUVERTE, en toutes lettres : « une
# machine dont le ComfyUI ne repond pas n'incremente jamais battements dans
# battre_annonce(), et ne se met donc JAMAIS a jour toute seule. C'est peut-etre
# voulu, mais rien ne le dit, et aucune mesure ne le tranche. » Elle se tranche
# en deux moities, et les voici : la boucle, elle, ne retient rien.
_t = tourner([], comfy_connu=False, arret_apres=0, budget=6)
dit(bool(_t.maj) and _t.maj[0][0] == "http://studio",
    "sans carte, la BOUCLE tente quand meme la mise a jour — elle ne retient rien",
    f"{len(_t.maj)} tentative(s) sans ComfyUI")

print("\n  ── dire(), la fermeture que banc_agent.py disait injoignable ──")


def eprouver_dire(reponse, avances):
    """Lance boucle() et appelle SA fermeture dire(), en avancant l'horloge.

    C'est le detour qui rend mesurable ce que banc_agent.py declarait
    « injoignable d'ici » : boucle() PASSE dire a executer(), et executer() est
    un global du module. Le faux executer() recoit donc la fermeture reelle, et
    l'horloge qu'il avance est celle que tourner() vient de poser dans
    AGENT.time — un frein de 1,5 s ne se mesure pas autrement.
    """
    retours = []

    def executer(comfy, graphe, dire):
        for i, pas in enumerate(avances):
            AGENT.time.avancer(pas)
            retours.append(dire(i, len(avances)))
        return [], 1.0, None

    trace = tourner([(200, TRAVAIL)], executer=executer,
                    reponses={"/api/noeud/progres": reponse}, budget=30)
    postes = [(a.corps, a.secondes) for a in trace.appels
              if "/api/noeud/progres" in a.url]
    return retours, postes, trace


_r, _p, _tr = eprouver_dire((200, {"annule": False}), [0.0])
dit(_p == [({"tid": TID, "fait": 0, "total": 1}, 10)],
    "dire() rapporte au studio le tid, le fait et le total, sans attendre",
    f"{_p}")

# LE FREIN A 1,5 s ET NON 2 : la boucle d'executer() tourne toutes les deux
# secondes, et un frein regle sur la meme duree laissait passer un tour sur
# deux — un tour saute, ce sont deux secondes de GPU de plus a chaque
# annulation.
# Les avances sont choisies pour encadrer le seuil : 1,40 s depuis la derniere
# annonce (juste au-dessous, saute), puis 1,51 s (juste au-dessus, passe).
_r, _p, _tr = eprouver_dire((200, {"annule": False}), [0.0, 1.4, 0.11, 5.0])
dit([c["fait"] for c, _ in _p] == [0, 2, 3],
    "un frein de 1,5 s : une carte bavarde ne noie pas le studio de pourcentages",
    f"{len(_p)} annonces pour 4 appels — a 0,00 s (passe), 1,40 s (saute), "
    f"1,51 s (passe), 6,51 s (passe)")

print("\n  ── on ne jette pas un rendu sur un doute ──")

# LE RETOUR DE CETTE ANNONCE EST LE SEUL CHEMIN par lequel une annulation nous
# parvienne : le studio n'a pas notre adresse. Un studio muet ou en erreur ne
# vaut donc JAMAIS « annule » — sinon la premiere coupure reseau jette un rendu
# de trois minutes deja a moitie fait.
# LES CORPS SONT CHOISIS POUR QUE LA GARDE AIT QUELQUE CHOSE A GARDER. Ecrits
# d'abord avec des corps anodins — (500, b"boum"), (401, {"erreur": ...}) — ces
# cas etaient verts d'un agent SANS aucune garde : rien la-dedans ne dit
# « annule », et « ne vaut jamais annule » n'y avait rien a refuser. On donne
# donc a chaque reponse douteuse le mot exact qu'elle ne doit pas faire croire.
for _nom, _rep in [("un studio MUET, dont appeler() rend une trace",
                    (0, "URLError: [Errno 111] Connection refused")),
                   ("un studio en panne dont le corps dirait « annule »",
                    (500, {"annule": True})),
                   ("un studio qui refuse le jeton, meme s'il dit « annule »",
                    (401, {"annule": True})),
                   ("une reponse qui n'est pas un objet", (200, b"annule")),
                   ("un 200 sans le mot", (200, {}))]:
    _r, _p, _tr = eprouver_dire(_rep, [0.0])
    dit(_r == [False], f"{_nom} ne vaut jamais « annule »", f"dire rend {_r}")

_r, _p, _tr = eprouver_dire((200, {"annule": True}), [0.0])
dit(_r == [True],
    "mais un « annule » franc du studio arrete bien le rendu",
    f"dire rend {_r}")


# ══════════════════════════════════════════════════════════════════════
#  2. insister() — dix minutes pour ne pas perdre un travail DEJA FAIT
# ══════════════════════════════════════════════════════════════════════
# LA CARTE A DEJA TOURNE. C'est ce qui distingue cette fonction de toutes les
# autres : ce qu'elle transporte a coute trois minutes de GPU, et un studio qui
# redemarrait a la seconde ou l'on rendait faisait lire « echec » a
# l'utilisateur pour un travail que sa machine avait bel et bien mene a terme.
print("\n  ── un travail deja fait ne se perd pas parce que le studio redemarre ──")


def insiste(statuts, corps=None, brut=None, budget=60):
    """Lance la VRAIE insister() contre un studio qui repond ce qu'on veut."""
    horloge = Horloge(budget)
    essais = []
    file = list(statuts)

    def appeler(url, jeton=None, corps=None, methode=None, brut=None,
                secondes=60):
        essais.append(types.SimpleNamespace(url=url, jeton=jeton, corps=corps,
                                            brut=brut, secondes=secondes,
                                            t=horloge.t))
        return file.pop(0) if len(file) > 1 else file[0]

    sauves = [pose("appeler", appeler), pose("time", horloge)]
    sortie, rendu, souci = io.StringIO(), None, ""
    try:
        with redirect_stdout(sortie):
            rendu = a("insister", _absente("insister"))(
                "http://studio/api/noeud/resultat?x=1",
                "JETON", corps, brut=brut, secondes=77)
    except Stop:
        souci = "budget epuise"
    finally:
        reprendre(sauves)
    return types.SimpleNamespace(rendu=rendu, essais=essais, souci=souci,
                                 dit=sortie.getvalue(),
                                 duree=horloge.t - 100000.0,
                                 attentes=list(horloge.dormi))


_i = insiste([(200, b"ok")], corps={"tid": TID})
dit(_i.rendu == 200 and len(_i.essais) == 1 and _i.dit == "",
    "un studio qui repond du premier coup n'est ni rappele ni commente",
    f"rend {_i.rendu}, {len(_i.essais)} essai(s), dit={_i.dit!r}")

# UN REFUS FRANC NE SE REPARE PAS EN LE REPETANT : jeton invalide, extension
# refusee, fichier trop gros. Recommencer pendant dix minutes retarderait
# seulement le message d'erreur, et occuperait la machine pour rien.
for _st in (400, 401, 403, 413, 499):
    _i = insiste([(_st, b"non")], corps={"tid": TID})
    dit(_i.rendu == _st and len(_i.essais) == 1,
        f"un refus franc ({_st}) rend la main tout de suite",
        f"{len(_i.essais)} essai(s)")

_i = insiste([(0, "Timeout"), (0, "Timeout"), (0, "Timeout"), (200, b"ok")],
             brut=b"IMAGE")
dit(_i.rendu == 200 and len(_i.essais) == 4,
    "un studio MUET est rappele jusqu'a ce qu'il revienne — le travail est garde",
    f"rend {_i.rendu} apres {len(_i.essais)} essais")
dit([e.brut for e in _i.essais] == [b"IMAGE"] * 4
    and [e.jeton for e in _i.essais] == ["JETON"] * 4
    and [e.secondes for e in _i.essais] == [77] * 4,
    "et l'on renvoie EXACTEMENT les memes octets, le meme jeton, le meme delai",
    f"octets={[e.brut for e in _i.essais]}, delais={[e.secondes for e in _i.essais]}")

_i = insiste([(500, b"boum"), (200, b"ok")], corps={"tid": TID})
dit(_i.rendu == 200 and len(_i.essais) == 2,
    "un studio en panne (5xx) est rappele lui aussi",
    f"{len(_i.essais)} essais")

# L'ATTENTE DOUBLE, PLAFONNEE A TRENTE SECONDES. Sans plafond, la neuvieme
# attente ferait huit minutes et l'on depasserait le delai de livraison sans
# avoir reessaye ; sans doublement, un studio qui redemarre en deux minutes
# serait rappele soixante fois pour rien.
_i = insiste([(0, "")] * 8 + [(200, b"ok")], corps={"tid": TID})
dit(_i.attentes == [2, 4, 8, 16, 30, 30, 30, 30],
    "l'attente double a chaque essai, et plafonne a trente secondes",
    f"{_i.attentes}")

dit(_i.dit.count("on garde le travail et l'on insiste") == 1,
    "le studio muet n'est annonce QU'UNE FOIS, pas a chaque essai",
    f"{_i.dit.count('on garde le travail et l')} ligne(s) pour "
    f"{len(_i.essais)} essais")
dit("studio revenu — resultat livre (200)" in _i.dit,
    "et son retour est annonce, avec ce qui vient d'etre livre",
    [l.strip() for l in _i.dit.splitlines() if "revenu" in l][:1])

_i = insiste([(200, b"ok")], corps={"tid": TID})
dit("revenu" not in _i.dit,
    "un studio qui n'est jamais parti n'est pas annonce « revenu »",
    f"dit={_i.dit!r}")

# DIX MINUTES, PUIS ON LACHE — et on le DIT. Insister sans fin bloquerait la
# boucle : la machine ne reprendrait plus jamais de travail, et le studio la
# verrait vivante (le fil d'annonce bat) et occupee pour toujours.
_i = insiste([(0, "Timeout")], corps={"tid": TID}, budget=80)
_limite = a("LIVRAISON_MINUTES", -1) * 60
dit(_i.souci == "" and _i.duree >= _limite and _i.duree < _limite + 30,
    "au-dela du delai de livraison, le travail est declare perdu — et l'on rend",
    f"{_i.duree:.0f} s pour un delai de {_limite} s, {len(_i.essais)} essais")
dit(f"studio injoignable depuis {a("LIVRAISON_MINUTES", -1)} min" in _i.dit
    and "travail perdu" in _i.dit,
    "la perte est ecrite en clair, avec la duree — sinon personne ne la voit",
    [l.strip() for l in _i.dit.splitlines() if "perdu" in l][:1])

if not os.environ.get("AGENT_LIVRAISON_MINUTES"):
    dit(a("LIVRAISON_MINUTES", -1) == 10,
        "et ce delai vaut dix minutes quand l'environnement ne dit rien",
        f"LIVRAISON_MINUTES={a("LIVRAISON_MINUTES", -1)}")

# LE DEFAUT ETAIT LA JUSQU'AU 4 SEPTEMBRE 2026, et ces cas le gardent ferme.
# La docstring promettait « on ne recommence que sur un studio MUET ou en panne
# (0, ou 5xx) » ; le code ecrivait « st == 200 or (400 <= st < 500) ». Tout ce
# qui n'etait ni 200 ni 4xx passait pour un studio muet — mesure du meme jour :
# un 204 et un 202 partaient chacun VINGT-QUATRE fois sur dix minutes, avant que
# le travail ne soit declare perdu.
#
# 204 N'A RIEN D'HYPOTHETIQUE : le studio le sert deja sur /api/noeud/question,
# et c'est la reponse naturelle pour « recu, rien a dire ». Le jour ou une route
# de livraison l'adopterait, chaque fichier rendu aurait ete perdu.
#
# LA REDIRECTION, ELLE, N'EST PAS LE DECLENCHEUR, contrairement a ce que la
# premiere version de ce commentaire affirmait. urllib SUIT les redirections :
# mesure du 4 septembre 2026 contre un serveur d'essai — un 301 avec Location
# rend 200 a appeler(). Seule une BOUCLE de redirections ressort en 301, et
# c'est ce cas-la qu'on garde ci-dessous, en sachant ce qu'il vaut.
_i = insiste([(204, None)], corps={"tid": TID}, budget=80)
dit(len(_i.essais) == 1 and _i.essais and "204" in _i.dit,
    "un 204 — « recu, rien a dire » — est une reponse : on ne recommence pas, "
    "et on le dit",
    f"{len(_i.essais)} essai(s) — "
    f"« {([l.strip() for l in _i.dit.splitlines() if '204' in l] or [''])[0]} »")
_i = insiste([(202, None)], corps={"tid": TID}, budget=80)
dit(len(_i.essais) == 1, "un 202 non plus", f"{len(_i.essais)} essai(s)")
_i = insiste([(301, b"")], corps={"tid": TID}, budget=80)
dit(len(_i.essais) == 1,
    "et une boucle de redirections — le seul 3xx qui ressorte, urllib suivant "
    "les autres — n'est pas prise pour un studio muet",
    f"{len(_i.essais)} essai(s)")
# LE TEMOIN : sans lui, les trois cas ci-dessus seraient vrais d'une fonction
# qui n'insisterait JAMAIS, c'est-a-dire du defaut que insister() repare.
_i = insiste([(503, b"")], corps={"tid": TID}, budget=80)
dit(len(_i.essais) > 20 and "studio muet (503)" in _i.dit,
    "alors qu'une panne franche, elle, est bien reessayee dix minutes durant",
    f"{len(_i.essais)} essais, {_i.duree:.0f} s")


# ══════════════════════════════════════════════════════════════════════
#  3. servir_le_langage() — le fil qui prete le modele local au studio
# ══════════════════════════════════════════════════════════════════════
# UN FIL A PART, et le commentaire dit pourquoi : la boucle de travail est
# bloquee pendant un rendu, et une question posee au milieu d'une video de
# quatre minutes attendrait sa fin. C'est ce fil qui rend une machine a carte
# utile au studio quand l'Ollama du studio est tombe.
print("\n  ── le modele local, prete au studio quand le sien tombe ──")


def servir(questions, generation=(200, {"response": "bonjour"}),
           reponse=(200, {"ok": True}), tours=1, budget=60):
    """Lance le VRAI servir_le_langage() contre un faux studio et un faux
    Ollama."""
    horloge = Horloge(budget)
    appels = []
    file = list(questions)

    def appeler(url, jeton=None, corps=None, methode=None, brut=None,
                secondes=60):
        appels.append(types.SimpleNamespace(url=url, jeton=jeton, corps=corps,
                                            secondes=secondes, t=horloge.t))
        if url.endswith("/api/noeud/question"):
            # Le tour de trop est retire de la trace : sans cela chaque cas
            # compterait une demande de plus qu'il n'y en a eu.
            if len([a for a in appels
                    if a.url.endswith("/question")]) > tours:
                appels.pop()
                raise Stop()
            return file.pop(0) if len(file) > 1 else file[0]
        if url.endswith("/api/generate"):
            if isinstance(generation, BaseException):
                raise generation
            return generation
        return reponse

    sauves = [pose("appeler", appeler), pose("time", horloge)]
    sortie, souci = io.StringIO(), ""
    try:
        with redirect_stdout(sortie):
            a("servir_le_langage", _absente("servir_le_langage"))(
                "http://studio", "JETON", "http://ollama:11434")
    except Stop:
        pass
    except Exception as e:
        souci = f"{type(e).__name__}: {e}"
    finally:
        reprendre(sauves)
    return types.SimpleNamespace(appels=appels, souci=souci,
                                 attentes=list(horloge.dormi),
                                 dit=sortie.getvalue())


_QUESTION = (200, {"qid": "q-42", "corps": {"model": "qwen2.5:7b",
                                            "prompt": "un chat en pixel art",
                                            "stream": False}})

_s = servir([_QUESTION])
_gen = next((a for a in _s.appels if a.url.endswith("/api/generate")), None)
dit(_gen is not None and _gen.corps == {"model": "qwen2.5:7b",
                                        "prompt": "un chat en pixel art",
                                        "stream": False},
    "la question du studio part TELLE QUELLE au modele local",
    f"{_gen.corps if _gen else 'jamais posee'}")

_rep = next((a for a in _s.appels if a.url.endswith("/api/noeud/reponse")), None)
dit(_rep is not None and _rep.corps == {"qid": "q-42", "reponse": "bonjour"},
    "et la reponse revient au studio sous le MEME qid — sinon elle est perdue",
    f"{_rep.corps if _rep else 'jamais rendue'}")

# LE JETON DU NOEUD NE SORT PAS DE LA CONVERSATION AVEC LE STUDIO. C'est la
# clef qui autorise cette machine a prendre du travail : la poster a un Ollama
# — qui peut etre un conteneur voisin, ou une machine du LAN — la donnerait a
# qui n'en a pas besoin. Le code passe « corps » par mot-clef, ce qui laisse
# jeton a None ; un appel positionnel de plus, et le jeton partirait.
dit(_gen is not None and _gen.jeton is None
    and all(a.jeton == "JETON" for a in _s.appels
            if a.url.startswith("http://studio")),
    "le jeton du noeud va au studio et JAMAIS a Ollama",
    f"ollama={_gen.jeton if _gen else '?'}, "
    f"studio={[a.jeton for a in _s.appels if a.url.startswith('http://studio')]}")

dit(_gen is not None and _gen.secondes == 900
    and bool(_s.appels) and _s.appels[0].secondes == 30 and _rep is not None
    and _rep.secondes == 60,
    "quinze minutes pour generer, trente secondes pour demander, une pour rendre",
    f"generer={_gen.secondes if _gen else '?'}, "
    f"demander={_s.appels[0].secondes if _s.appels else '?'}, "
    f"rendre={_rep.secondes if _rep else '?'}")

# UN OLLAMA EN PANNE DOIT ETRE DIT. Sans ce rapport, le studio attend son
# delai entier sur une question a laquelle personne ne repondra jamais — et
# l'utilisateur regarde une conversation qui ne repond pas.
_s = servir([_QUESTION], generation=(500, b"model not found"))
_rep = next((a for a in _s.appels if a.url.endswith("/api/noeud/reponse")), None)
dit(_rep is not None and _rep.corps == {"qid": "q-42",
                                        "erreur": "ollama a repondu 500"},
    "un Ollama en panne est RAPPORTE au studio, qui n'attend pas pour rien",
    f"{_rep.corps if _rep else 'silence'}")

_s = servir([_QUESTION], generation=(200, {"model": "qwen", "done": True}))
_rep = next((a for a in _s.appels if a.url.endswith("/api/noeud/reponse")), None)
dit(_rep is not None and _rep.corps == {"qid": "q-42", "reponse": ""},
    "un Ollama qui repond sans texte rend une reponse vide, pas un silence",
    f"{_rep.corps if _rep else 'silence'}")

_s = servir([(200, {"pas_de_qid": True})], tours=2)
dit([a.url for a in _s.appels] == ["http://studio/api/noeud/question"] * 2
    and _s.attentes == [a("PAUSE_COURTE", -1)] * 2,
    "une reponse sans qid ne declenche aucune generation",
    f"{[a.url.rsplit('/', 1)[-1] for a in _s.appels]}, attentes={_s.attentes}")

# 204 N'EST PAS UNE ERREUR : c'est ce que le studio repond quand sa file de
# questions est vide, c'est-a-dire presque toujours. L'espacer comme une panne
# ferait attendre vingt secondes la premiere question posee apres un calme.
_s = servir([(204, None)], tours=5)
dit(_s.attentes == [a("PAUSE_COURTE", -1)] * 5,
    "pas de question (204) : on repasse dans trois secondes, sans s'espacer",
    f"{_s.attentes}")

# UN JETON REFUSE NE GUERIT PAS EN TROIS SECONDES. Sans cet espacement, le fil
# interroge un studio mort mille fois par heure, sans que rien ne le dise.
_s = servir([(401, {"erreur": "jeton inconnu"})], tours=6)
dit(_s.attentes == [3, 6, 12, 20, 20, 20],
    "un jeton refuse espace les demandes, en doublant, jusqu'a vingt secondes",
    f"{_s.attentes}")

# IL FAUT UNE PANNE APRES LA REPRISE, sinon ce cas ne mesure rien. Ecrit
# d'abord « 401, 401, question, 204 », il relevait [3, 6, 3] — et ce troisieme
# trois n'etait PAS la remise a zero : c'est le « time.sleep(PAUSE_COURTE) »
# ecrit en dur de la branche « pas de question ». Le cas etait vert d'un agent
# qui ne remet jamais rien a zero. C'est le defaut de banc_multilingue releve
# dans docs/eprouver-les-bancs.md, sous une autre forme : une assertion qui ne
# distingue pas la garde de son absence.
_s = servir([(401, None), (401, None), (204, None), (401, None), (401, None)],
            tours=5)
dit(_s.attentes == [3, 6, a("PAUSE_COURTE", -1), 3, 6],
    "et l'espacement est remis a zero des que le studio repond",
    f"{_s.attentes} — sans la remise a zero, la reprise repartirait a 12 s")

# CE FIL NE DOIT JAMAIS EMPORTER L'AGENT : au pire le studio se passe de cette
# machine pour ses questions. Une exception non rattrapee ici tuerait le fil,
# et la machine cesserait silencieusement de servir le langage — en continuant
# de s'annoncer comme capable de le faire.
_s = servir([_QUESTION], generation=ValueError("le reseau a hoquete"), tours=3)
_tours = len([a for a in _s.appels if a.url.endswith("/question")])
dit(_s.souci == "" and _tours == 3,
    "une exception au milieu ne tue pas le fil : il revient au tour suivant",
    f"{_s.souci or 'sans mourir'}, {_tours} tours")
dit(_s.attentes and _s.attentes[0] == a("PAUSE_LONGUE", -1),
    "et l'incident coute vingt secondes, pas la machine",
    f"{_s.attentes[:2]}")


# ══════════════════════════════════════════════════════════════════════
#  4. trouver_ollama() et modeles_comfy() — ce que la machine sait faire
# ══════════════════════════════════════════════════════════════════════
# CES DEUX FONCTIONS ECRIVENT LE MENU QUE LE STUDIO LIT. Un dossier oublie, et
# une machine distante ne peut jamais servir l'agrandissement, le detourage ni
# la fluidite video, meme avec les fichiers sur son disque — le studio ne le
# saura pas. Un Ollama mal choisi, et c'est le repli du studio qui tombe.
print("\n  ── quel Ollama, et quels modeles ──")


def chercher(prefere, repondent):
    """Lance la VRAIE trouver_ollama(). « repondent » : adresse -> modeles."""
    vus = []

    def appeler(url, jeton=None, corps=None, methode=None, brut=None,
                secondes=60):
        vus.append(url)
        for adresse, modeles in repondent.items():
            if url == adresse + "/api/tags":
                return 200, {"models": [{"name": m} for m in modeles]}
        return 0, "ConnectionRefusedError"

    sauves = [pose("appeler", appeler)]
    try:
        return a("trouver_ollama", _absente("trouver_ollama"))(prefere), vus
    finally:
        reprendre(sauves)


_VOISIN1, _VOISIN2 = a("VOISINS_OLLAMA", ("", ""))[:2] or ("", "")

# LE REGLAGE D'ABORD — s'il a ete pose, c'est qu'on sait ou l'on va. Essayer
# les voisins d'emblee masquerait une faute de frappe dans le reglage : la
# machine marcherait, et personne ne saurait que le reglage est mort.
_r, _vus = chercher("http://regle:11434", {"http://regle:11434": ["qwen"],
                                           _VOISIN1: ["llama"]})
dit(_r == "http://regle:11434" and _vus == ["http://regle:11434/api/tags"],
    "le reglage est essaye AVANT les voisins de conteneur, et seul s'il repond",
    f"rend {_r!r} apres {_vus}")

_r, _vus = chercher("http://regle:11434", {_VOISIN2: ["llama"]})
dit(_r == _VOISIN2
    and _vus == ["http://regle:11434/api/tags", _VOISIN1 + "/api/tags",
                 _VOISIN2 + "/api/tags"],
    "puis les deux voisins de conteneur, dans l'ordre, en dernier recours",
    f"rend {_r!r} apres {len(_vus)} essais")

_r, _vus = chercher("", {_VOISIN1: ["llama"]})
dit(_r == _VOISIN1 and _vus == [_VOISIN1 + "/api/tags"],
    "un reglage vide n'est pas interroge — on ne demande pas a « /api/tags »",
    f"rend {_r!r} apres {_vus}")

# LA BARRE FINALE, DES DEUX COTES. Retiree a l'essai seulement, l'adresse
# rendue porterait le slash et toutes les URL suivantes en auraient deux :
# « http://x//api/generate ». Certains serveurs l'acceptent, d'autres non.
_r, _vus = chercher("http://regle:11434/", {"http://regle:11434": ["qwen"]})
dit(_r == "http://regle:11434" and _vus == ["http://regle:11434/api/tags"],
    "la barre finale du reglage est retiree, a l'essai comme au retour",
    f"rend {_r!r} apres {_vus}")

_r, _vus = chercher("http://regle:11434", {})
dit(_r == "" and len(_vus) == 3,
    "aucun Ollama joignable : on rend une chaine vide, apres trois essais",
    f"rend {_r!r} apres {len(_vus)} essais")

# LE DEFAUT ETAIT LA JUSQU'AU 4 SEPTEMBRE 2026, et ce cas le garde ferme.
# La docstring promet « l'adresse ou un modele repond VRAIMENT » ; le code
# testait la veracite du dictionnaire rendu par etat_ollama(), qui vaut
# {"ok": False, "modeles": []} pour un Ollama installe et VIDE — non vide, donc
# vrai. La recherche s'arretait sur lui.
#
# LE CAS N'EST PAS DE BORD : en conteneur, OLLAMA_URL pointe souvent sur un
# Ollama voisin qu'on vient d'installer et ou l'on n'a encore rien tire.
# host.docker.internal, ou vivent les modeles de l'hote, n'etait alors jamais
# essaye, et la machine s'annoncait avec « 0 modele(s) ».
_r, _vus = chercher("http://regle:11434", {"http://regle:11434": [],
                                           _VOISIN1: ["llama3", "qwen"]})
dit(_r == _VOISIN1 and len(_vus) == 2,
    "un Ollama joignable mais VIDE ne masque plus le voisin qui porte des "
    "modeles",
    f"rend {_r!r} apres {_vus}")
# ET IL RESTE PREFERE QUAND IL A DE QUOI REPONDRE : la correction ne doit pas
# retourner la regle « le reglage d'abord ».
_r, _vus = chercher("http://regle:11434", {"http://regle:11434": ["mistral"],
                                           _VOISIN1: ["llama3", "qwen"]})
dit(_r == "http://regle:11434" and len(_vus) == 1,
    "et le reglage garde la priorite des qu'il porte un seul modele",
    f"rend {_r!r} apres {_vus}")
# UN VIDE PARTOUT REND LA CHAINE VIDE, et non la premiere adresse joignable :
# un Ollama sans modele ne repond a rien, et le studio doit le savoir.
_r, _vus = chercher("http://regle:11434", {"http://regle:11434": [],
                                           _VOISIN1: []})
dit(_r == "" and len(_vus) == 3,
    "et quand aucun ne porte de modele, on rend \"\" plutot qu'une adresse "
    "qui ne repondra a rien",
    f"rend {_r!r} apres {len(_vus)} essais")


def inventaire(par_dossier):
    """Lance la VRAIE modeles_comfy(). Rend (inventaire, appels)."""
    vus = []

    def appeler(url, jeton=None, corps=None, methode=None, brut=None,
                secondes=60):
        vus.append((url, secondes))
        return par_dossier.get(url.rsplit("/", 1)[-1], (404, b"not found"))

    sauves = [pose("appeler", appeler)]
    try:
        return (a("modeles_comfy", _absente("modeles_comfy"))("http://comfy")
                or {}), vus
    finally:
        reprendre(sauves)


_DOSSIERS = a("DOSSIERS", [])
_inv, _vus = inventaire({d: (200, [f"{d}.safetensors"]) for d in _DOSSIERS})
# LE PLANCHER D'ABORD : « tous les dossiers de DOSSIERS » est vrai DE RIEN si
# la liste est vide, et c'est justement l'etat qu'on obtient sur un agent qui
# ne la porte pas. Sans ce compte, ce cas serait vert a vide.
dit(len(_DOSSIERS) >= 10
    and [u for u, _ in _vus] == [f"http://comfy/models/{d}" for d in _DOSSIERS],
    "l'inventaire interroge tous les dossiers de DOSSIERS, un par un",
    f"{len(_vus)} dossiers demandes pour {len(_DOSSIERS)} nommes")

# LES TROIS MOTEURS AJOUTES APRES COUP. Sans eux, une machine distante ne
# pouvait jamais servir l'agrandissement, le detourage ni la fluidite video,
# meme avec les fichiers sur son disque : le studio ne les voyait pas.
dit({"upscale_models", "background_removal", "frame_interpolation"}
    <= set(_inv),
    "y compris les trois moteurs ajoutes apres coup — sans eux, pas "
    "d'agrandissement a distance",
    f"{sorted(set(_inv) & {'upscale_models', 'background_removal', 'frame_interpolation'})}")

# LES DEUX DOSSIERS VIRTUELS DE ComfyUI-GGUF : les .gguf n'apparaissent que la,
# et une machine qui ne sert que du GGUF serait declaree sans aucun modele.
dit({"unet_gguf", "clip_gguf"} <= set(_inv),
    "et les deux dossiers virtuels du noeud GGUF, ou les .gguf sont seuls a "
    "apparaitre",
    f"{sorted(set(_inv) & {'unet_gguf', 'clip_gguf'})}")

dit(all(s == 10 for _, s in _vus),
    "chaque dossier est demande avec un delai de dix secondes",
    f"{sorted(set(s for _, s in _vus))}")

_inv, _vus = inventaire({"checkpoints": (200, ["a.safetensors"]),
                         "loras": (200, ["b.safetensors"])})
dit(_inv == {"checkpoints": ["a.safetensors"], "loras": ["b.safetensors"]}
    and len(_vus) == len(_DOSSIERS),
    "un dossier que ce ComfyUI ne connait pas est absent, sans emporter les autres",
    f"{sorted(_inv)} sur {len(_vus)} demandes")

# UN DOSSIER VIDE N'EST PAS UN DOSSIER INCONNU. Le studio se sert de cette
# difference : une clef presente avec une liste vide dit « cette machine a le
# dossier et il est vide », une clef absente dit « je ne sais pas ».
_inv, _ = inventaire({"loras": (200, [])})
dit(_inv == {"loras": []},
    "un dossier VIDE reste dans l'inventaire — ce n'est pas la meme chose "
    "qu'inconnu",
    f"{_inv}")

# UNE REPONSE 200 QUI N'EST PAS UNE LISTE. ComfyUI repond parfois un objet
# d'erreur avec un 200, et un portail captif repond du HTML : sans le
# isinstance, l'inventaire annoncerait au studio un dossier dont le contenu est
# une page web, et manquants() en tirerait n'importe quoi.
_inv, _ = inventaire({"vae": (200, {"error": "no such folder"}),
                      "loras": (200, b"<html>portail</html>"),
                      "checkpoints": (200, ["bon.safetensors"])})
dit(_inv == {"checkpoints": ["bon.safetensors"]},
    "une reponse 200 qui n'est pas une liste n'entre pas dans l'inventaire",
    f"{_inv}")


# ══════════════════════════════════════════════════════════════════════
#  5. main() — la porte d'entree, et ce qu'elle passe a la boucle
# ══════════════════════════════════════════════════════════════════════
# C'EST ICI QUE LES REGLAGES SE FIGENT. Un argument lu de travers, et la
# machine ne s'enrole pas — ou pire, s'enrole avec l'adresse d'un autre studio.
# banc_noeud.py mesure le SCRIPT qui appelle cet agent ; ce banc mesure ce que
# l'agent fait des arguments qu'il en recoit.
print("\n  ── la porte d'entree : arguments, environnement, reglages ──")


def lancer_main(argv, environ=None, config=None, ollama_repond=True,
                modeles=("qwen",)):
    """Lance le VRAI main(), boucle() remplacee par un temoin.

    AGENT.CONFIG est deplace dans un bac : sans cela, ce banc ECRIRAIT
    agent_noeud.json a cote du vrai agent du depot — la meme precaution que
    banc_agent.py prend pour AGENT.__file__, et pour la meme raison.
    """
    dossier = bac()
    chemin = os.path.join(dossier, "agent_noeud.json")
    if config is not None:
        with io.open(chemin, "w", encoding="utf-8") as f:
            json.dump(config, f)
    recu = {}

    def faux_boucle(*a, **k):
        recu["args"] = a
        return None

    def appeler(url, jeton=None, corps=None, methode=None, brut=None,
                secondes=60):
        recu.setdefault("appels", []).append(url)
        if url.endswith("/api/tags") and ollama_repond:
            return 200, {"models": [{"name": m} for m in modeles]}
        return 0, "ConnectionRefusedError"

    def faux_maj(studio, empreinte=""):
        recu["maj"] = (studio, empreinte)
        return 7

    sauves = [pose("CONFIG", chemin), pose("appeler", appeler),
              pose("boucle", faux_boucle), pose("os", FauxOs(environ)),
              pose("se_mettre_a_jour", faux_maj)]
    vieux_argv = sys.argv
    sys.argv = ["agent_noeud.py"] + list(argv)
    sortie, code, souci = io.StringIO(), None, ""
    try:
        with redirect_stdout(sortie):
            code = a("main", _absente("main"))()
    except SystemExit as e:
        souci = f"SystemExit {e.code}"
    except Exception as e:
        souci = f"{type(e).__name__}: {e}"
    finally:
        reprendre(sauves)
        sys.argv = vieux_argv
    ecrit = None
    if os.path.exists(chemin):
        with io.open(chemin, encoding="utf-8") as f:
            ecrit = json.load(f)
    return types.SimpleNamespace(code=code, boucle=recu.get("args"),
                                 maj=recu.get("maj"), ecrit=ecrit,
                                 dit=sortie.getvalue(), souci=souci,
                                 dossier=dossier)


def arg(m, i):
    """Le i-eme argument que main() a passe a boucle(), ou un temoin absent.

    Un agent plus ancien en passe MOINS : « arg(_m, 7) » y levait une
    IndexError et tuait le banc au milieu de sa derniere section — le sens
    inverse cessait de mesurer a partir de la. Le temoin ne vaut ni True ni
    False ni aucune adresse : le cas rougit, ce qui est le verdict juste.
    """
    if m.boucle is None or len(m.boucle) <= i:
        return "<cet agent ne passe pas cet argument>"
    return m.boucle[i]


_m = lancer_main([])
dit(_m.code == 1 and "Il manque l'adresse du studio" in _m.dit
    and _m.boucle is None,
    "sans adresse de studio, rien ne demarre — et l'on dit quoi taper",
    f"code={_m.code}, {_m.dit.strip()[:60]}")

_m = lancer_main(["--studio", "http://s:8199"])
dit(_m.code == 1 and "Il manque le jeton" in _m.dit and _m.ecrit is None,
    "sans jeton non plus, et AUCUN reglage n'est ecrit sur cette machine",
    f"code={_m.code}, reglages={_m.ecrit}")

# --maj SE PASSE DE JETON : la route /api/noeud/agent est deliberement ouverte,
# c'est ce qui permet d'installer une machine neuve qui n'en a pas encore.
_m = lancer_main(["--studio", "http://s:8199/", "--maj", "--empreinte", "abc123"])
dit(_m.code == 7 and _m.maj == ("http://s:8199", "abc123")
    and _m.boucle is None and _m.ecrit is None,
    "--maj se passe de jeton, rend le code de la mise a jour, et ne lance rien",
    f"code={_m.code}, maj={_m.maj}")

_m = lancer_main(["--studio", "http://s:8199/", "--jeton", "ABC",
                  "--comfy", "http://c:8188/"])
dit(_m.boucle is not None
    and tuple(_m.boucle)[:3] == ("http://s:8199", "ABC", "http://c:8188"),
    "la barre finale du studio ET celle de ComfyUI sont retirees avant la boucle",
    f"{tuple(_m.boucle or ())[:3] if _m.boucle else None}")

dit(_m.ecrit == {"studio": "http://s:8199", "jeton": "ABC",
                 "comfy": "http://c:8188/", "sorties": "",
                 "garder_heures": 24.0, "ollama": "http://127.0.0.1:11434"},
    "les reglages sont ecrits pour le prochain lancement, sans arguments",
    f"{_m.ecrit}")

# L'ENVIRONNEMENT AVANT LE FICHIER : en conteneur il n'y a pas de fichier, et
# transmettre des arguments par un compose est fragile — un « $VAR » y est
# resolu au mauvais moment et arrive vide.
_m = lancer_main(["--jeton", "ABC"],
                 environ={"STUDIO_URL": "http://env:8199",
                          "COMFY_URL": "http://comfyenv:8188",
                          "OLLAMA_URL": "http://ollamaenv:11434",
                          "COMFY_GARDER_HEURES": "6"},
                 config={"studio": "http://fichier", "comfy": "http://cfichier",
                         "ollama": "http://ofichier", "garder_heures": 99})
dit(_m.boucle is not None and arg(_m, 0) == "http://env:8199"
    and arg(_m, 2) == "http://comfyenv:8188" and arg(_m, 4) == 6.0,
    "l'environnement passe AVANT le fichier de reglages, pour le conteneur",
    f"studio={arg(_m, 0) if _m.boucle else None}, "
    f"comfy={arg(_m, 2) if _m.boucle else None}, "
    f"garder={arg(_m, 4) if _m.boucle else None}")

_m = lancer_main(["--jeton", "ABC"],
                 config={"studio": "http://fichier:8199",
                         "comfy": "http://cfichier:8188"})
dit(_m.boucle is not None and arg(_m, 0) == "http://fichier:8199"
    and arg(_m, 2) == "http://cfichier:8188",
    "et sans environnement, c'est le fichier qui parle : plus aucun argument "
    "au second lancement",
    f"{tuple(_m.boucle or ())[:3] if _m.boucle else None}")

# UN CHEMIN FAUX FERAIT CROIRE AU MENAGE sans que rien ne soit jamais efface :
# le disque de l'utilisateur se remplit, et l'agent affiche qu'il fait le
# menage.
_absent = os.path.join(bac(), "dossier-qui-n-existe-pas")
_m = lancer_main(["--studio", "http://s", "--jeton", "A", "--sorties", _absent])
dit(_m.code == 1 and "dossier de sorties introuvable" in _m.dit
    and _m.boucle is None,
    "un dossier de sorties introuvable est refuse TOUT DE SUITE",
    f"code={_m.code}, {_m.dit.strip()[-50:]}")

_present = bac()
_m = lancer_main(["--studio", "http://s", "--jeton", "A", "--sorties", _present,
                  "--garder-heures", "3"])
dit(_m.boucle is not None and arg(_m, 3) == os.path.abspath(_present)
    and arg(_m, 4) == 3.0,
    "un dossier qui existe part en chemin ABSOLU, avec son delai de garde",
    f"sorties={arg(_m, 3) if _m.boucle else None}, "
    f"garder={arg(_m, 4) if _m.boucle else None}")
dit("effacees 3 h apres depot" in _m.dit,
    "et l'agent annonce au demarrage ce qu'il effacera, et quand",
    [l.strip() for l in _m.dit.splitlines() if "Sorties" in l][:1])

_m = lancer_main(["--studio", "http://s", "--jeton", "A"])
dit("rien ne sera efface ici" in _m.dit,
    "sans dossier, il dit une fois qu'il n'effacera rien — un disque qui se "
    "remplit en silence est pire",
    [l.strip() for l in _m.dit.splitlines() if "Sorties" in l][:1])

# C'EST L'OLLAMA TROUVE QUI PART A LA BOUCLE, pas celui qu'on a demande : la
# boucle s'en sert pour decider de lancer le fil des questions, et un voisin
# de conteneur decouvert au demarrage doit y arriver.
_m = lancer_main(["--studio", "http://s", "--jeton", "A",
                  "--ollama", "http://absent:11434"], ollama_repond=False)
dit(_m.boucle is not None and arg(_m, 5) == "",
    "aucun Ollama joignable : la boucle demarre quand meme, sans fil de langage",
    f"ollama={arg(_m, 5)!r}" if _m.boucle else "pas de boucle")
dit("aucun modele joignable" in _m.dit and "http://absent:11434" in _m.dit,
    "et l'agent dit ce qu'il a essaye — sinon on cherche du cote du studio",
    [l.strip() for l in _m.dit.splitlines() if "Langage" in l][:1])

_m = lancer_main(["--studio", "http://s", "--jeton", "A",
                  "--ollama", "http://o:11434"], modeles=("qwen", "llama3"))
dit(_m.boucle is not None and arg(_m, 5) == "http://o:11434",
    "un Ollama trouve descend jusqu'a la boucle, qui en fera un fil",
    f"ollama={arg(_m, 5)!r}" if _m.boucle else "pas de boucle")
dit("2 modele(s)" in _m.dit,
    "et le nombre de modeles pretes est annonce au demarrage",
    [l.strip() for l in _m.dit.splitlines() if "Langage" in l][:1])

dit(_m.ecrit is not None and _m.ecrit["ollama"] == "http://o:11434",
    "c'est le reglage DEMANDE qui est enregistre, pas un voisin decouvert",
    f"{_m.ecrit['ollama'] if _m.ecrit else None}")

_m = lancer_main(["--studio", "http://s", "--jeton", "A", "--sans-maj-auto"])
dit(_m.boucle is not None and arg(_m, 7) is False,
    "--sans-maj-auto arrive jusqu'a la boucle, qui ne se remplacera pas",
    f"maj_auto={arg(_m, 7) if _m.boucle else None}")

_m = lancer_main(["--studio", "http://s", "--jeton", "A"],
                 environ={"AGENT_SANS_MAJ_AUTO": "1"})
dit(_m.boucle is not None and arg(_m, 7) is False,
    "AGENT_SANS_MAJ_AUTO fait la meme chose, pour un conteneur sans arguments",
    f"maj_auto={arg(_m, 7) if _m.boucle else None}")

_m = lancer_main(["--studio", "http://s", "--jeton", "A"])
dit(_m.boucle is not None and arg(_m, 7) is True,
    "et par defaut, la machine se met a jour toute seule",
    f"maj_auto={arg(_m, 7) if _m.boucle else None}")

_m = lancer_main(["--studio", "http://s", "--jeton", "A",
                  "--empreinte", "SHA-EPINGLE"])
dit(_m.boucle is not None and arg(_m, 6) == "SHA-EPINGLE",
    "l'empreinte epinglee descend jusqu'a la boucle, qui la passera a la maj",
    f"epinglee={arg(_m, 6) if _m.boucle else None}")

_m = lancer_main(["--studio", "http://s", "--jeton", "A"],
                 environ={"AGENT_EMPREINTE": "SHA-ENV"})
dit(_m.boucle is not None and arg(_m, 6) == "SHA-ENV",
    "AGENT_EMPREINTE aussi — l'epinglage doit tenir en conteneur",
    f"epinglee={arg(_m, 6) if _m.boucle else None}")


# ══════════════════════════════════════════════════════════════════════
#  6. LA CONSIGNE DE LIBERATION — ce que banc_agent.py laisse dehors
# ══════════════════════════════════════════════════════════════════════
# CE CHEMIN N'A JAMAIS ETE EMPRUNTE SUR LE PARC REEL, et c'est mesure : le
# 4 septembre 2026, apres un rendu de 112 s sur « pc » (RTX 2080 Ti), la carte
# retombe de 9,4 Go a 1,4 Go en moins de dix secondes et y reste quatre minutes
# (24 releves, aucune remontee). SEUIL_TENU vaut 2,0 Go, donc le studio ne
# reclame jamais rien sur ce parc. Le code de l'agent est la, complet, et
# personne ne l'a vu tourner — c'est exactement le motif du « banc vert sur une
# fonctionnalite morte » pris a l'envers : du code vivant que rien n'exerce.
#
# CE QUE banc_agent.py TIENT DEJA, et qui n'est PAS redit ici — le redire
# ferait deux filets qui se recouvrent, et l'on ne pourrait plus faire rougir
# ni l'un ni l'autre (c'est la lecon de _identifiant_acceptable(), dans
# docs/eprouver-les-bancs.md) :
#
#   - « liberer_carte() envoie UNE demande, et par appeler() » ;
#   - les deux clefs, « unload_models » ET « free_memory » ;
#   - l'adresse : le /free de CE ComfyUI ;
#   - un ComfyUI qui accepte rend (True, 200), un qui refuse rend (False, 404) ;
#   - une machine au repos qui recoit la consigne LIBERE ;
#   - une machine qui CALCULE ne libere pas, meme si le studio le reclame ;
#   - sans consigne, l'agent ne libere rien de lui-meme ;
#   - le rapport { ok, statut } remonte au studio, UNE fois, sur un succes.
#
# CE QUI RESTAIT DEHORS, et que voici : le ComfyUI qui NE REPOND PAS DU TOUT
# (statut 0, et non un refus franc), le rapport d'un ECHEC — banc_agent.py ne
# mesure que celui d'un succes, alors que c'est le rapport d'echec qui remplit
# « liberation_refusee » cote studio —, la CONSERVATION du diagnostic tant que
# le studio n'a pas repondu 200, et la remesure immediate de la carte.
print("\n  ── la consigne de liberation, et ce que l'agent en rapporte ──")


def battre(annonces, statut_free=200, travaux=(), comfy_repond=True,
           budget=40):
    """Lance le VRAI battre_annonce() contre un faux studio et un faux ComfyUI.

    « annonces » : la suite des (statut, corps) que le studio rend a chaque
    POST /api/noeud/annonce. Le statut compte autant que le corps — c'est lui
    qui decide si le diagnostic de liberation est garde ou jete.

    Un faux a part de celui de banc_agent.py, et pour une raison precise : le
    sien repond TOUJOURS 200 a l'annonce et ne sait pas ne pas repondre du tout
    au /free. Ces deux-la sont justement ce qui manque.
    """
    horloge = Horloge(budget)
    appels = []
    suite = list(annonces)

    def appeler(url, jeton=None, corps=None, methode=None, brut=None,
                secondes=60):
        appels.append(types.SimpleNamespace(url=url, corps=corps,
                                            secondes=secondes, t=horloge.t))
        if url.endswith("/system_stats"):
            if not comfy_repond:
                return 0, "URLError: [Errno 111] Connection refused"
            return 200, {"devices": [{"name": "RTX 2080 Ti",
                                      "vram_total": 11 * 1024 ** 3,
                                      "vram_free": 2 * 1024 ** 3}],
                         "system": {"ram_total": 32 * 1024 ** 3}}
        if url.endswith("/free"):
            # statut 0 : ce que appeler() rend quand la connexion echoue. Ce
            # n'est PAS un refus franc, et le studio doit pouvoir les
            # distinguer — « ComfyUI trop ancien » de « ComfyUI mort ».
            if statut_free == 0:
                return 0, "URLError: [Errno 111] Connection refused"
            return statut_free, b""
        if url.endswith("/api/noeud/annonce"):
            vues = len([a for a in appels if a.url.endswith("/annonce")])
            if vues > len(suite):
                appels.pop()
                raise Stop()
            return suite[vues - 1]
        return 200, []

    horloge.observer = lambda: a("DEPUIS_L_ANNONCE", {}).get("remesurer")
    sauves = [pose("appeler", appeler), pose("time", horloge)]
    if hasattr(AGENT, "EN_COURS_ICI"):
        AGENT.EN_COURS_ICI[:] = list(travaux)
    if hasattr(AGENT, "DEPUIS_L_ANNONCE"):
        AGENT.DEPUIS_L_ANNONCE.update(remesurer=False, battements=0)
    sortie, souci = io.StringIO(), ""
    try:
        with redirect_stdout(sortie):
            a("battre_annonce", _absente("battre_annonce"))(
                "http://studio", "JETON", "http://comfy", "")
    except Stop:
        pass
    except Exception as e:
        souci = f"{type(e).__name__}: {e}"
    finally:
        reprendre(sauves)
        remesurer = a("DEPUIS_L_ANNONCE", {}).get("remesurer")
        if hasattr(AGENT, "PREMIERE_ANNONCE"):
            AGENT.PREMIERE_ANNONCE.clear()
        _neuf()
    return types.SimpleNamespace(
        appels=appels, dit=sortie.getvalue(), souci=souci,
        remesurer=remesurer, remesurer_par_battement=list(horloge.observe),
        free=[a for a in appels if a.url.endswith("/free")],
        rapports=[a.corps.get("libere") for a in appels
                  if a.url.endswith("/annonce") and isinstance(a.corps, dict)])


# L'ORDRE DESCEND PAR LA REPONSE A L'ANNONCE, et il ne peut pas venir
# autrement : le studio n'a pas notre adresse — c'est toute la raison d'etre de
# cet agent, « une machine derriere une box ne peut pas etre jointe de
# l'exterieur ; elle peut toujours sortir ».
_b = battre([(200, {"liberer": True}), (200, {}), (200, {})])
dit(len(_b.free) == 1
    and _b.free[0].t == _b.appels[[a.url for a in _b.appels].index(
        "http://studio/api/noeud/annonce")].t,
    "l'ordre arrive par la REPONSE a l'annonce, et le /free part dans la foulee",
    f"{len(_b.free)} liberation(s) pour 3 battements, une seule consigne")

# UNE FOIS PAR CONSIGNE, PAS UNE PAR BATTEMENT. Un agent qui dechargerait a
# chaque battement paierait un rechargement de modele a chaque rendu — dix a
# trente secondes de carte, pour rien.
dit(len(_b.free) == 1,
    "et une seule fois : un ordre unique ne vaut pas une liberation par battement",
    f"{len(_b.free)} liberation(s) pour 3 battements")

# LE DRAPEAU EST POSE EN FIN DE BATTEMENT ET EFFACE AU DEBUT DU SUIVANT : il
# n'est donc visible d'aucun appel reseau, et c'est l'observateur de l'horloge
# qui le releve, une fois par attente. Ce qu'il garde est etroit et reel : la
# liberation n'a lieu que machine au repos, ou la carte est deja remesuree a
# chaque battement — mais si la BOUCLE prend un travail entre la liberation et
# le battement suivant, sans ce drapeau la VRAM annoncee serait celle d'AVANT,
# prise dans le cache d'une minute, et le studio croirait le /free sans effet.
dit(_b.remesurer_par_battement[:3] == [True, False, False],
    "la carte est remesuree au battement SUIVANT, et une seule fois",
    f"drapeau en fin de battement : {_b.remesurer_par_battement[:3]}")

# LE RAPPORT D'ECHEC, celui qui remplit « liberation_refusee » cote studio.
# banc_agent.py ne mesure que le rapport d'un SUCCES — et « le resultat remonte »
# serait vrai d'un agent qui ne rapporte que ce qui a marche, c'est-a-dire d'un
# agent dont le diagnostic ne sert a rien : c'est l'echec qui a besoin d'etre
# explique.
_b = battre([(200, {"liberer": True}), (200, {}), (200, {})], statut_free=404)
_rap = [r for r in _b.rapports if r is not None]
dit(_rap == [{"ok": False, "statut": 404}],
    "un ComfyUI qui REFUSE le /free est rapporte au studio, avec son statut",
    f"{_rap}")
dit("ComfyUI a refuse /free (404)" in _b.dit,
    "et la console nomme le refus, avec le chiffre qui dit ou regarder",
    [l.strip() for l in _b.dit.splitlines() if "free" in l][:1])

# UN ComfyUI QUI NE REPOND PAS DU TOUT n'est pas un ComfyUI qui refuse. Le
# premier est mort — le studio doit cesser de compter sur cette carte ; le
# second est trop ancien — la machine travaille, elle ne sait juste pas rendre
# sa memoire. Un agent qui AVALERAIT ce cas rendrait les deux indiscernables.
_b = battre([(200, {"liberer": True}), (200, {}), (200, {})], statut_free=0)
_rap = [r for r in _b.rapports if r is not None]
dit(_rap == [{"ok": False, "statut": 0}],
    "un ComfyUI qui NE REPOND PAS est rapporte lui aussi, sous le statut zero",
    f"{_rap}")
dit(_b.souci == "",
    "et il n'emporte pas le fil d'annonce, qui rend la machine visible",
    _b.souci or "le fil a tenu")

_b = battre([(200, {"liberer": True}), (200, {}), (200, {})])
_rap = [r for r in _b.rapports if r is not None]
dit(_rap == [{"ok": True, "statut": 200}]
    and "carte rendue au systeme" in _b.dit,
    "un ComfyUI qui accepte le dit une fois, et pas a chaque battement",
    f"{_rap}")

# LE DIAGNOSTIC EST GARDE TANT QUE LE STUDIO N'A PAS REPONDU 200. Le
# commentaire de battre_annonce() le dit en toutes lettres — « un studio qui
# redemarre a la seconde ou l'on rapporte ne doit pas faire perdre le
# diagnostic, qui est justement ce qui distingue ComfyUI trop ancien de la
# carte etait deja vide » — et rien ne le mesurait. Le studio tombe juste apres
# avoir donne l'ordre : le rapport doit repartir au battement d'apres.
_b = battre([(200, {"liberer": True}), (0, None), (500, b"boum"),
             (200, {}), (200, {})], statut_free=404)
_rap = [r for r in _b.rapports if r is not None]
dit(len(_rap) == 3 and all(r == {"ok": False, "statut": 404} for r in _rap),
    "un studio muet ne fait pas perdre le diagnostic : il est GARDE et repropose",
    f"{len(_rap)} envois du rapport, pour deux battements perdus")
dit(_b.rapports[-1:] == [None],
    "et il n'est jete qu'une fois le studio revenu — pas une annonce de plus",
    f"rapports par battement : {_b.rapports}")

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
sys.exit(1 if rate else 0)
