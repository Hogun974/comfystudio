# -*- coding: utf-8 -*-
"""L'agent fait-il vraiment ce que son code dit, sur la machine de quelqu'un
d'autre ?

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
au monde tient en TROIS portes, qu'on remplace ici par des faux.

TROIS, ET NON UNE. Ce banc a annonce « une seule porte sur le monde,
appeler() » le 3 septembre 2026, et le fichier de la CI a recopie la phrase.
Elle etait fausse, et c'est exactement le reproche que SECURITY.md fait a une
politique qui promet un controle inexistant : deposer_entrees() appelle
« urllib.request.urlopen » en direct — il lui faut du multipart, que appeler()
ne sait pas faire — et ecouter_progression() ouvre une socket NUE et parle
websocket a la main. Tant que ces deux-la n'etaient pas remplacees, la moitie
de ce que l'agent envoie sur le fil ne pouvait pas etre mesuree, et la phrase
faisait croire le contraire. Les trois portes sont donc :

  - appeler(), pour tout le HTTP ordinaire — ComfyUI comme le studio ;
  - urllib.request.urlopen, pour le depot multipart des fichiers d'entree ;
  - socket.create_connection, pour la websocket de progression.

C'est le seul choix honnete des trois qui se presentaient :

  - un banc STATIQUE, qui relirait le texte de l'agent par l'arbre de syntaxe :
    il aurait vu « free_memory » ecrit, jamais ENVOYE. La ligne peut etre la et
    ne rien atteindre — c'est le defaut que banc_mutations.py reproche aux
    bancs depuis le premier jour.
  - une RECETTE avec une vraie carte : elle mesure ce qu'aucun banc ne peut
    mesurer, mais elle a besoin d'une machine a GPU et ne peut pas entrer dans
    la CI. C'est le role de recette_chemin_page.py, pas celui d'un banc.
  - LE CODE REEL CONTRE UN FAUX RESEAU, ci-dessous. Les fonctions appelees sont
    celles que l'agent execute en service, et ce qui est verifie est ce qui
    SORT sur le fil.

DANS L'ORDRE DE LA CONSEQUENCE, et non de la facilite :

  1. LA MISE A JOUR. Le studio distribue le code de l'agent, l'agent le
     telecharge et l'EXECUTE sur la machine de quelqu'un d'autre, en HTTP
     simple. SECURITY.md nomme ce chemin comme la surface la plus sensible du
     depot. Trois gardes le tiennent — l'empreinte epinglee, ast.parse(), le
     marqueur anti-boucle — et aucune n'etait exercee.
  2. La liberation de la carte, deja couverte le 3 septembre.
  3. executer() : ce qui part sur /prompt, ce qui remonte comme erreur, et
     l'annulation qui regarde la file avant de tirer.
  4. Le depot des entrees et le registre des sorties : les deux seuls endroits
     ou l'agent ECRIT et EFFACE des fichiers sur une machine qui n'est pas la
     notre.
  5. La progression, ecrite a la main faute de dependance.

Statique au sens ou il ne parle a personne : aucun reseau, aucune carte, aucun
studio, aucune dependance. Il entre dans la CI. Tout ce qu'il ecrit va dans des
dossiers temporaires effaces a la sortie — JAMAIS dans le depot, et jamais a
cote de ce fichier : l'agent se reecrit lui-meme, et un banc qui se tromperait
de dossier reecrirait le sien.

CE QU'IL NE VOIT PAS, et il faut l'ecrire :

  - Que ComfyUI comprenne « /free » et rende sa memoire. Un faux ComfyUI repond
    ce qu'on lui fait repondre. Ce banc mesure la CONSIGNE — qu'elle parte,
    qu'elle porte les deux clefs, qu'elle ne parte pas quand la carte travaille
    — et le studio, lui, mesure ce qu'elle rapporte : banc_repartition.py tient
    l'autre moitie.
  - Que os.execv remplace vraiment le processus, ni qu'un ComfyUI reel accepte
    le multipart tel qu'on le lui construit. On mesure ce qui SORT, pas ce que
    l'autre bout en fait.
  - boucle(), qui ne rend jamais la main. Trois de ses regles restent
    decouvertes, et il vaut mieux les nommer que les taire :
      * sa fonction « dire » — celle qui refuse de croire un studio muet quand
        il s'agit d'annuler, « on ne jette pas un rendu sur un doute » — est
        une fermeture interieure, injoignable d'ici ;
      * la mise a jour n'y est tentee qu'UNE FOIS PAR BATTEMENT, et seulement
        entre deux travaux ;
      * une machine dont le ComfyUI ne repond pas n'incremente jamais
        « battements » dans battre_annonce(), et ne se met donc JAMAIS a jour
        toute seule. C'est peut-etre voulu — la boucle ne reclame pas de
        travail non plus — mais rien ne le dit, et aucune mesure ne le tranche.
  - insister(), servir_le_langage(), trouver_ollama() et main(). Le premier
    garde dix minutes un travail DEJA FAIT pendant qu'un studio redemarre ; les
    trois autres n'ecrivent ni n'effacent rien. Ils passent apres ce qui est
    couvert ici, et ils passent.
"""
import atexit
import hashlib
import io
import json
import os
import shutil
import socket
import sys
import tempfile
import time as _vrai_temps
import types
import urllib.error
import urllib.parse
import urllib.request
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


# ══════════════════════════ le bac a sable ═══════════════════════════
# L'AGENT SE REECRIT LUI-MEME, et ce banc tourne a cote du vrai agent_noeud.py.
# se_mettre_a_jour() ecrase « os.path.abspath(__file__) » du module : lance sans
# precaution, ce banc REMPLACERAIT l'agent du depot par ses octets d'essai. Tout
# passe donc par un dossier temporaire, et AGENT.__file__ y est deplace le temps
# de l'appel. Meme raison pour AGENT.ICI dans la section du registre : c'est la
# que l'agent va chercher l'ancien registre, et il l'EFFACE apres l'avoir repris.
BACS = []


def bac(contenu=b"", sous=""):
    """Un dossier temporaire neuf, avec un agent bidon dedans. Rend son chemin.

    « sous » y glisse un dossier intermediaire — « Program Files » et son
    espace, pour eprouver la regle des guillemets de Windows.
    """
    dossier = tempfile.mkdtemp(prefix="banc_agent_")
    BACS.append(dossier)
    if sous:
        dossier = os.path.join(dossier, sous)
        os.makedirs(dossier)
    chemin = os.path.join(dossier, "agent_noeud.py")
    with open(chemin, "wb") as f:
        f.write(contenu)
    return chemin


@atexit.register
def _ranger():
    for dossier in BACS:
        shutil.rmtree(dossier, ignore_errors=True)


def sha(octets):
    return hashlib.sha256(octets).hexdigest()


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


# ══════════════════════ 1. LA MISE A JOUR ════════════════════════════
# LE CHEMIN A LA PIRE CONSEQUENCE DU DEPOT. Le studio sert son propre
# agent_noeud.py sur /api/noeud/agent, route deliberement ouverte — c'est ce qui
# permet d'installer une machine neuve qui n'a pas encore de jeton — et l'agent
# telecharge ce fichier puis L'EXECUTE, sur une machine qui n'est pas celle du
# studio. SECURITY.md le dit sans detour : « qui peut s'intercaler sur le reseau
# choisit le code qui tournera sur chaque machine a agent, et l'obtient sur
# toutes a la fois a la prochaine mise a jour ».
#
# Contre un reseau hostile, la seule vraie reponse est le TLS d'un reverse
# proxy, et ce banc ne la remplace pas. Ce qu'il mesure, ce sont les trois
# gardes qui EXISTENT, et dont pas une n'etait exercee :
#
#   - l'empreinte epinglee (--empreinte / AGENT_EMPREINTE), qui n'a de valeur
#     que relevee AILLEURS que sur ce lien ;
#   - ast.parse(), qui refuse d'ecraser un agent qui marche par un
#     telechargement tronque — « inacceptable depuis que la mise a jour est
#     automatique, ou un telechargement tronque ferait une brique sans personne
#     pour le voir » ;
#   - le marqueur anti-boucle, qui empeche une machine de redemarrer sans fin
#     sur une empreinte qui ne correspondra jamais.
#
# LE TEMOIN DE LA TENTATIVE, PARTOUT. « la mise a jour est refusee » est vrai
# d'un agent qui ne tente jamais rien : chaque refus est donc releve avec ce qui
# prouve que la tentative a eu lieu — le nombre d'appels a /api/noeud/agent pour
# se_mettre_a_jour(), et un CONTROLE POSITIF dans les memes conditions, garde
# levee, pour se_mettre_a_jour_seul(), qui refuse AVANT de telecharger.
AVANT = b"# agent d'avant\nVERSION = 1\n"
APRES = b"# agent servi par le studio\nVERSION = 2\n"


class Redemarre(BaseException):
    """os.execv ne rend jamais la main ; ce faux-la non plus.

    Une BaseException pour la meme raison que Stop : se_mettre_a_jour_seul()
    rattrape « except OSError » autour de l'execv, et une erreur ordinaire y
    serait avalee — le banc croirait avoir mesure un redemarrage la ou il
    aurait mesure le repli.
    """


class FauxOs:
    """os, moins ce qui remplacerait ce processus ou toucherait cette machine.

    __getattr__ n'est consulte que pour ce que l'instance n'a pas : path,
    remove, makedirs passent au vrai module, « environ », « name » et execv
    non.

    « name » EST POSE A LA MAIN, et c'est ce qui rend la mesure du 31 aout
    rejouable. Les guillemets d'os.execv ne servent que sous Windows, la CI
    tourne sous Linux, et cette regle-la ne serait donc jamais exercee la ou
    elle est verifiee.
    """

    def __init__(self, nom=None, leve=None):
        self.environ = dict(os.environ)
        # Une machine reelle peut porter le marqueur d'une tentative
        # precedente ; chaque cas dit lui-meme s'il en veut un.
        self.environ.pop(AGENT.MARQUE_MAJ, None)
        self.name = nom or os.name
        self.leve = leve
        self.execs = []

    def __getattr__(self, quoi):
        return getattr(os, quoi)

    def execv(self, programme, morceaux):
        self.execs.append((programme, list(morceaux)))
        raise self.leve if self.leve is not None else Redemarre()


class FauxSys:
    """sys, avec l'interpreteur et la ligne de commande d'une autre machine."""

    def __init__(self, executable, argv):
        self.executable = executable
        self.argv = list(argv)

    def __getattr__(self, quoi):
        return getattr(sys, quoi)


class FauxSource:
    """Le studio qui sert /api/noeud/agent, et qui compte ce qu'on lui demande.

    Le compte est le temoin : sans lui, « rien n'a ete remplace » serait vrai
    d'un agent qui n'a jamais rien telecharge.
    """

    def __init__(self, octets, statut=200):
        self.octets, self.statut, self.appels = octets, statut, []

    def __call__(self, url, jeton=None, corps=None, methode=None, brut=None,
                 secondes=60):
        self.appels.append(url)
        return self.statut, self.octets


def _trace(ou, faux, sortie, **reste):
    return types.SimpleNamespace(
        appels=list(faux.appels), dit=sortie.getvalue(), chemin=ou,
        pose=open(ou, "rb").read(),
        precedent=(open(ou + ".precedent", "rb").read()
                   if os.path.exists(ou + ".precedent") else None),
        **reste)


def maj(octets, statut=200, empreinte="", contenu=AVANT):
    """Lance la VRAIE se_mettre_a_jour() sur un agent bidon, dans un bac.

    L'exception est rattrapee plutot que laissee filer : une mutation qui fait
    LEVER l'agent doit faire rougir le cas qui la nomme, pas casser le banc —
    « le banc s'est casse au lieu de rougir » est un verdict faux.
    """
    chemin = bac(contenu)
    faux, sortie = FauxSource(octets, statut), io.StringIO()
    vieux_appeler, vieux_fichier = AGENT.appeler, AGENT.__file__
    AGENT.appeler, AGENT.__file__ = faux, chemin
    code, souci = None, ""
    try:
        with redirect_stdout(sortie):
            code = AGENT.se_mettre_a_jour("http://studio", empreinte)
    except Exception as e:
        souci = f"{type(e).__name__}: {e}"
    finally:
        AGENT.appeler, AGENT.__file__ = vieux_appeler, vieux_fichier
    return _trace(chemin, faux, sortie, code=code, souci=souci)


def maj_seule(octets=APRES, attendue=None, epinglee="", marqueur=None,
              contenu=AVANT, nom_os=None, executable="/usr/bin/python3",
              argv=("agent_noeud.py", "--studio", "http://s"), execv_leve=None,
              demarrage=None):
    """Lance la VRAIE se_mettre_a_jour_seul(), execv compris. Rend sa trace.

    « demarrage » est l'empreinte du code EN COURS D'EXECUTION, celle que
    _mon_empreinte() retient au chargement. Par defaut celle du fichier pose :
    une machine qui vient de demarrer.
    """
    chemin = bac(contenu, sous="Program Files" if nom_os == "nt" else "")
    faux = FauxSource(octets)
    faux_os = FauxOs(nom_os, execv_leve)
    if marqueur is not None:
        faux_os.environ[AGENT.MARQUE_MAJ] = marqueur
    vieux = (AGENT.appeler, AGENT.__file__, AGENT.os, AGENT.sys,
             AGENT._EMPREINTE_AU_DEMARRAGE)
    AGENT.appeler, AGENT.__file__ = faux, chemin
    AGENT.os, AGENT.sys = faux_os, FauxSys(executable, argv)
    AGENT._EMPREINTE_AU_DEMARRAGE = (sha(contenu) if demarrage is None
                                     else demarrage)
    sortie, souci, redemarre = io.StringIO(), "", False
    try:
        with redirect_stdout(sortie):
            AGENT.se_mettre_a_jour_seul(
                "http://studio", sha(octets) if attendue is None else attendue,
                epinglee)
    except Redemarre:
        redemarre = True
    except Exception as e:
        souci = f"{type(e).__name__}: {e}"
    finally:
        (AGENT.appeler, AGENT.__file__, AGENT.os, AGENT.sys,
         AGENT._EMPREINTE_AU_DEMARRAGE) = vieux
    return _trace(chemin, faux, sortie, souci=souci, redemarre=redemarre,
                  execs=list(faux_os.execs),
                  marqueur=faux_os.environ.get(AGENT.MARQUE_MAJ))


print("\n  ── du code telecharge, puis EXECUTE sur la machine d'un autre ──")
_pris = maj(APRES)
dit(_pris.appels == ["http://studio/api/noeud/agent"] and _pris.pose == APRES
    and _pris.code == 0,
    "l'agent va chercher son remplacant sur /api/noeud/agent, et l'installe",
    f"{_pris.appels}, pose={_pris.pose!r}, code={_pris.code} {_pris.souci}")

# LA COPIE DE SECOURS. « si la nouvelle version est cassee, il reste la
# precedente a cote, sans avoir a la retelecharger » — et une version cassee
# est justement celle qui ne redemarrera pas pour aller en chercher une autre.
dit(_pris.precedent == AVANT,
    "et il garde l'ancienne a cote, sous .precedent",
    f"{_pris.precedent!r}")

# L'EMPREINTE AFFICHEE EST CELLE DU FICHIER POSE. C'est le seul moyen qu'ait
# celui qui heberge de comparer une machine a l'autre, et de la confronter au
# « sha256sum agent_noeud.py » releve en SSH sur l'hote du studio.
dit(sha(APRES) in _pris.dit,
    "il annonce le sha256 de ce qu'il vient de poser, pour qu'on le compare",
    _pris.dit.strip().splitlines()[-1][:90] if _pris.dit.strip() else "muet")

_faux_sha = maj(APRES, empreinte="0" * 64)
dit(_faux_sha.pose == AVANT and _faux_sha.code == 1
    and len(_faux_sha.appels) == 1,
    "une empreinte EPINGLEE qui ne correspond pas : rien n'est remplace",
    f"telecharge {len(_faux_sha.appels)} fois, pose={_faux_sha.pose!r}, "
    f"code={_faux_sha.code}")
dit(_faux_sha.precedent is None,
    "et pas meme la copie de secours — un refus ne touche a aucun fichier",
    f"{_faux_sha.precedent!r}")

# LE CONTROLE POSITIF DU CAS CI-DESSUS, et il n'est pas facultatif : « rien
# n'est remplace » est vrai d'un agent qui ne remplace jamais rien.
_bon_sha = maj(APRES, empreinte=sha(APRES))
dit(_bon_sha.pose == APRES and _bon_sha.code == 0,
    "et l'empreinte qui correspond, elle, laisse passer",
    f"pose={_bon_sha.pose!r}, code={_bon_sha.code}")

# LE SHA256 SE RELEVE A LA MAIN, donc il arrive comme on l'a copie.
# « sha256sum » rend des minuscules, « certutil -hashfile » de Windows et
# « Get-FileHash » rendent des MAJUSCULES, et un copier-coller ramene des
# espaces. Sans le .strip().lower(), l'empreinte juste serait refusee et la
# machine resterait sur sa vieille version en croyant se defendre.
_majuscule = maj(APRES, empreinte="  " + sha(APRES).upper() + "\n")
dit(_majuscule.pose == APRES,
    "l'empreinte relevee en MAJUSCULES, ou avec des espaces, reste la bonne",
    f"pose={_majuscule.pose!r}, {_majuscule.dit.strip()[:80]}")

# ══ ast.parse() ════════════════════════════════════════════════════════
# Le fichier n'etait pas relu avant d'ecraser un agent qui fonctionnait. Anodin
# tant qu'un humain lançait « --maj » et voyait l'erreur au redemarrage,
# inacceptable depuis que la mise a jour est automatique : un telechargement
# tronque ferait une brique sans personne pour le voir.
_tronque = maj(b"def executer(comfy, graphe")
dit(_tronque.pose == AVANT and _tronque.code == 1 and len(_tronque.appels) == 1,
    "un telechargement TRONQUE ne remplace pas un agent qui fonctionne",
    f"telecharge {len(_tronque.appels)} fois, pose={_tronque.pose!r}")

_html = maj(b"<html><body>portail wifi</body></html>\n")
dit(_html.pose == AVANT and _html.code == 1,
    "ni une page de portail captif servie a la place du script",
    f"pose={_html.pose!r}, {_html.dit.strip()[:80]}")

# Le meme refus sur des octets qui ne sont pas de l'UTF-8 : ast.parse() ne
# recoit pas du texte, il recoit ce que le reseau a rendu.
_binaire = maj(b"\x89PNG\r\n\x1a\n\xff\xfe")
dit(_binaire.pose == AVANT and _binaire.code == 1,
    "ni des octets qui ne sont meme pas du texte",
    f"pose={_binaire.pose!r}, {_binaire.dit.strip()[:80]}")

_muet = maj(APRES, statut=500)
dit(_muet.pose == AVANT and _muet.code == 1 and len(_muet.appels) == 1,
    "un studio en panne ne fait pas croire a une version neuve",
    f"telecharge {len(_muet.appels)} fois, code={_muet.code}")

# appeler() rend un OBJET quand la reponse est du JSON, des octets sinon. Un
# studio qui repond « {\"erreur\": ...} » avec un 200 — une route qui a change de
# nom, un proxy qui s'interpose — ne doit pas etre ecrit sur le disque.
_json = maj({"erreur": "inconnu"})
dit(_json.pose == AVANT and _json.code == 1,
    "ni une reponse JSON servie a la place du fichier",
    f"pose={_json.pose!r}, code={_json.code}")

# DEJA A JOUR : ni ecriture, ni copie de secours. Sans ce cas, un agent qui
# reecrit son propre fichier a chaque battement ecraserait son .precedent par
# lui-meme au premier passage, et la copie de secours ne vaudrait plus rien.
_meme = maj(AVANT)
dit(_meme.code == 0 and _meme.precedent is None and len(_meme.appels) == 1,
    "et quand le studio sert le meme agent, rien n'est reecrit",
    f"code={_meme.code}, precedent={_meme.precedent!r}, "
    f"telecharge {len(_meme.appels)} fois")


print("\n  ── se remplacer tout seul, sans personne pour regarder ──")
# On ne telecharge RIEN quand il n'y a rien a faire : c'est le cas courant,
# appele a chaque battement. Le temoin est le compte d'appels, a zero.
_rien = maj_seule(attendue="")
dit(not _rien.appels and not _rien.execs and _rien.pose == AVANT,
    "sans empreinte servie par le studio, l'agent ne telecharge rien",
    f"{len(_rien.appels)} appel(s), {len(_rien.execs)} redemarrage(s)")

_pareil = maj_seule(attendue=sha(AVANT))
dit(not _pareil.appels and not _pareil.execs,
    "et quand le studio sert l'empreinte qu'on execute deja, non plus",
    f"{len(_pareil.appels)} appel(s)")

# ══ L'EMPREINTE EPINGLEE ═══════════════════════════════════════════════
# Celui qui heberge a releve le sha256 ailleurs que sur ce lien HTTP et l'a
# epingle. Le studio sert autre chose : c'est exactement le cas ou l'epingle
# doit tenir, et le refus vient AVANT le telechargement.
_epingle = maj_seule(epinglee=sha(b"une autre version\n"))
dit(not _epingle.appels and not _epingle.execs and _epingle.pose == AVANT,
    "une empreinte EPINGLEE arrete la mise a jour automatique",
    f"{len(_epingle.appels)} appel(s), pose={_epingle.pose!r}")
dit("epinglee" in _epingle.dit,
    "et elle le DIT, au lieu de se taire sur une machine qu'on croit a jour",
    _epingle.dit.strip()[:100] or "muet")

# LE CONTROLE POSITIF, dans les memes conditions a l'epingle pres : sans lui,
# « l'agent n'a rien telecharge » serait vrai d'un agent qui ne se met jamais
# a jour, et les deux cas ci-dessus seraient verts de rien.
_libre = maj_seule()
dit(_libre.appels == ["http://studio/api/noeud/agent"] and _libre.pose == APRES
    and _libre.redemarre,
    "sans epingle, la meme machine telecharge, remplace et redemarre",
    f"{_libre.appels}, pose={_libre.pose!r}, redemarre={_libre.redemarre} "
    f"{_libre.souci}")

# ══ CE QUE LE STUDIO A ANNONCE EST CE QU'IL DOIT SERVIR ════════════════
# L'empreinte apprise a l'annonce est repassee a se_mettre_a_jour() comme
# empreinte ATTENDUE. Elle ne defend pas contre un reseau hostile — qui reecrit
# le fichier reecrit l'annonce, SECURITY.md le dit — mais elle attrape le cas
# banal et invisible : un telechargement tronque, un proxy qui reecrit les fins
# de ligne, un studio mis a jour entre l'annonce et la demande. Sans elle, la
# machine redemarrerait sur un fichier different de celui qu'elle croit avoir.
_menteur = maj_seule(octets=APRES, attendue=sha(b"une troisieme version\n"))
dit(_menteur.appels and _menteur.pose == AVANT and not _menteur.execs,
    "un agent servi different de l'empreinte ANNONCEE n'est pas installe",
    f"{len(_menteur.appels)} appel(s), pose={_menteur.pose!r}, "
    f"execs={_menteur.execs}")

# ══ LE MARQUEUR ANTI-BOUCLE ════════════════════════════════════════════
# Il survit a os.execv, qui remplace le processus sans rien perdre de son
# environnement : c'est ce qui distingue « je viens d'essayer et ça n'a pas
# pris » de « je decouvre qu'une version existe ». Sans lui, un studio qui sert
# un agent dont l'empreinte ne correspondra jamais — un proxy qui reecrit, un
# fichier servi avec des CRLF — fait redemarrer la machine sans fin.
_boucle = maj_seule(marqueur=sha(APRES))
dit(not _boucle.appels and not _boucle.execs,
    "une empreinte deja tentee n'est pas retentee : pas de redemarrage sans fin",
    f"{len(_boucle.appels)} appel(s), {len(_boucle.execs)} redemarrage(s)")

# ET LE MARQUEUR EST LIE A CETTE EMPREINTE-LA. Un marqueur qui arreterait TOUTE
# mise a jour clouerait la machine sur sa version des la premiere tentative
# ratee, et le studio ne pourrait plus jamais la corriger.
_autre = maj_seule(marqueur=sha(b"une tentative d'hier\n"))
dit(_autre.appels and _autre.redemarre and _autre.pose == APRES,
    "mais une AUTRE empreinte repart : le marqueur ne cloue pas la machine",
    f"{len(_autre.appels)} appel(s), redemarre={_autre.redemarre}")

# ══ LE REDEMARRAGE ═════════════════════════════════════════════════════
dit(_libre.execs and _libre.execs[0] == (
        "/usr/bin/python3",
        ["/usr/bin/python3", _libre.chemin, "--studio", "http://s"]),
    "il redemarre sur le fichier neuf, avec les memes arguments qu'au depart",
    f"{_libre.execs}")

# LE MARQUEUR EST POSE AVANT L'EXECV, jamais apres : apres, il n'y a plus de
# processus pour le poser.
dit(_libre.marqueur == sha(APRES),
    "et il laisse sa trace dans l'environnement AVANT de se remplacer",
    f"{_libre.marqueur}")

# ══ LES GUILLEMETS DE WINDOWS ══════════════════════════════════════════
# Mesure du 31 aout avec « C:/Program Files/Python314 » : os.execv y recolle
# les arguments en une seule ligne de commande SANS les proteger, l'enfant
# meurt sur « C:\Program: can't open file », et le parent sort avec le code 0 —
# donc aucune OSError, donc le repli ne s'execute jamais et l'agent est mort
# pour de bon. Aucune des deux machines n'est concernee aujourd'hui ; la CI
# tourne sous Linux et ne le serait jamais non plus.
_nt = maj_seule(nom_os="nt", executable=r"C:\Program Files\Python314\python.exe",
                argv=("agent.py", "--studio", "http://s", "--sorties",
                      r"D:\mes sorties"))
_morceaux = _nt.execs[0][1] if _nt.execs else []
dit(_morceaux[:2] == [r'"C:\Program Files\Python314\python.exe"',
                      f'"{_nt.chemin}"'],
    "sous Windows, l'interpreteur et le script a espaces partent proteges",
    f"{_morceaux[:2]}")
dit(_morceaux[2:] == ["--studio", "http://s", "--sorties", r'"D:\mes sorties"'],
    "et les arguments aussi, un par un, sans toucher a ceux qui n'en ont pas "
    "besoin",
    f"{_morceaux[2:]}")

# ══ LE REPLI ═══════════════════════════════════════════════════════════
# execv a echoue : le processus est intact, sur l'ANCIEN code, avec le nouveau
# fichier sur le disque. Le dire, et continuer de travailler.
_repli = maj_seule(execv_leve=OSError("Cannot allocate memory"))
dit(not _repli.redemarre and _repli.pose == APRES and not _repli.souci,
    "un redemarrage impossible n'emporte pas l'agent : il continue de "
    "travailler",
    f"redemarre={_repli.redemarre}, pose={_repli.pose!r}, {_repli.souci}")
dit("prochain lancement" in _repli.dit,
    "et il annonce que la nouvelle version prendra effet au lancement suivant",
    _repli.dit.strip().splitlines()[-1][:90] if _repli.dit.strip() else "muet")

# ══ CE QUI ARRIVE QUAND LE STUDIO SERT UN AGENT CASSE ══════════════════
# Le refus d'ast.parse() doit remonter jusqu'ici : ni ecriture, ni redemarrage,
# ET PAS DE MARQUEUR. Poser le marqueur sur une tentative qui n'a rien tente
# ferait renoncer la machine pour toujours a une version qu'elle n'a jamais
# essayee — le studio corrigerait son fichier, et elle ne le verrait pas.
_casse = maj_seule(octets=b"def f(:\n")
dit(_casse.appels and _casse.pose == AVANT and not _casse.execs
    and _casse.marqueur is None,
    "un agent casse servi par le studio : rien de pose, rien de redemarre, "
    "aucun marqueur",
    f"{len(_casse.appels)} appel(s), pose={_casse.pose!r}, "
    f"execs={_casse.execs}, marqueur={_casse.marqueur}")


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

# ══════════════════════ 3. LE RENDU LUI-MEME ═════════════════════════
class FauxComfy:
    """Un ComfyUI qui repond ce qu'on lui fait repondre, et retient tout.

    « hist » est la suite des reponses de /history/<pid>, une par tour de la
    boucle d'executer() : le premier tour rend un historique vide, comme un
    vrai ComfyUI qui charge encore son modele.
    """

    def __init__(self, hist=(), file=None, refus=None):
        self.appels = []
        self.hist = list(hist) or [{}]
        self.file = file if file is not None else {"queue_running": [],
                                                   "queue_pending": []}
        self.refus = refus
        self.tours = 0

    def __call__(self, url, jeton=None, corps=None, methode=None, brut=None,
                 secondes=60):
        self.appels.append((url, corps))
        if url.endswith("/prompt"):
            return self.refus if self.refus is not None else (200,
                                                              {"prompt_id": "pid-1"})
        if "/history/" in url:
            self.tours += 1
            return 200, self.hist[min(self.tours - 1, len(self.hist) - 1)]
        if url.endswith("/queue"):
            return (200, self.file) if corps is None else (200, {})
        return 200, {}

    def vus(self, fin):
        return [(u, c) for u, c in self.appels if u.endswith(fin)]


def rendre(comfy, graphe=None, dire=None):
    """Fait tourner la VRAIE executer() contre ce faux ComfyUI."""
    vieux_appeler, vieux_temps = AGENT.appeler, AGENT.time
    AGENT.appeler, AGENT.time = comfy, FauxTemps()
    sortie, souci, resultat = io.StringIO(), "", ([], 0, None)
    try:
        with redirect_stdout(sortie):
            resultat = AGENT.executer(
                "http://comfy",
                graphe if graphe is not None else {"1": {"class_type": "K",
                                                         "inputs": {}}},
                dire)
    except Exception as e:
        souci = f"{type(e).__name__}: {e}"
    finally:
        AGENT.appeler, AGENT.time = vieux_appeler, vieux_temps
    fichiers, secondes, erreur = resultat
    return types.SimpleNamespace(fichiers=fichiers, secondes=secondes,
                                 erreur=erreur, souci=souci,
                                 dit=sortie.getvalue())


FINI = {"pid-1": {"status": {"completed": True},
                  "outputs": {"9": {"images": [
                      {"filename": "sortie.png", "subfolder": "",
                       "type": "output"},
                      {"sans_filename": 1}]},
                              "10": {"nombre": 3}}}}

print("\n  ── le rendu : ce qui part, ce qui remonte, ce qu'on coupe ──")
_ok = rendre(FauxComfy([{}, FINI]))
_soumis = _ok.fichiers and _ok.erreur is None
dit(_soumis and _ok.fichiers == [{"filename": "sortie.png", "subfolder": "",
                                  "type": "output"}],
    "le rendu abouti rend les fichiers produits, et rien d'autre",
    f"{_ok.fichiers}, erreur={_ok.erreur} {_ok.souci}")

# CE QUI N'EST PAS UN FICHIER EST ECARTE. Un noeud ComfyUI peut poser dans
# « outputs » un nombre, un texte, une liste de rien : les envoyer au studio le
# ferait echouer sur un « filename » absent, apres que la carte a travaille.
_liste = _ok.fichiers
dit(all(isinstance(f, dict) and "filename" in f for f in _liste)
    and len(_liste) == 1,
    "et ce qu'un noeud pose dans « outputs » sans etre un fichier est ecarte",
    f"{_liste}")

_graphe = {"1": {"class_type": "KSampler", "inputs": {"seed": 7}}}
_c = FauxComfy([{}, FINI])
rendre(_c, _graphe)
_corps_prompt = _c.vus("/prompt")
dit(len(_corps_prompt) == 1 and _corps_prompt[0][1].get("prompt") == _graphe,
    "le graphe part sur /prompt tel qu'il est arrive, sans etre reecrit",
    f"{_corps_prompt}")

# ══ LE client_id, ECRIT DEUX FOIS DANS DEUX FONCTIONS ══════════════════
# executer() soumet sous « agent » et ecouter_progression() s'abonne a la
# websocket sous « agent ». ComfyUI adresse la progression AU CLIENT QUI A
# SOUMIS : les deux noms doivent etre le meme, et rien dans l'agent ne les tient
# ensemble — ce sont deux chaines litterales, dans deux fonctions, a trois cents
# lignes d'ecart. Qu'ils derivent et la barre de la file s'eteint sans que rien
# ne leve : le rendu marche, il n'a simplement plus de pourcentage.
CLIENT_SOUMIS = _corps_prompt[0][1].get("client_id") if _corps_prompt else None
dit(CLIENT_SOUMIS == "agent",
    "et il se presente sous un client_id — c'est a lui que la progression ira",
    f"client_id = {CLIENT_SOUMIS!r}")

_refus = rendre(FauxComfy(refus=(400, {"error": "noeud KSampler inconnu"})))
dit(not _refus.fichiers and _refus.erreur
    and "KSampler inconnu" in _refus.erreur,
    "un graphe refuse remonte CE QUE ComfyUI a dit, pas un « echec » sec",
    f"{_refus.erreur!r}")

# LE DETAIL DE L'ERREUR D'EXECUTION. C'est la seule chose que verra
# l'utilisateur du studio quand un rendu meurt sur la machine d'un autre : sans
# le message du noeud, « echec de la generation » ne distingue pas un OOM d'un
# modele absent.
_oom = rendre(FauxComfy([{"pid-1": {"status": {"completed": False, "messages": [
    ["execution_start", {}],
    ["execution_error", {"exception_message": "CUDA out of memory"}]]}}}]))
dit(_oom.erreur and "CUDA out of memory" in _oom.erreur,
    "un rendu qui echoue remonte le message du noeud qui a lache",
    f"{_oom.erreur!r}")

# ══ L'ANNULATION ═══════════════════════════════════════════════════════
# « dire » est appele a CHAQUE TOUR, meme sans pourcentage a montrer : c'est la
# REPONSE a cette annonce qui apporte l'annulation, et les premieres dizaines de
# secondes d'un rendu — le chargement du modele — n'ont aucun pourcentage. Ne
# l'appeler que sur progression laissait ce trou-la sans aucun moyen d'apprendre
# qu'on calcule pour rien.
_vus = []


def _dire_au_second_tour(fait, total):
    _vus.append((fait, total))
    return len(_vus) >= 2


AGENT.PROGRES.update(fait=0, total=0)
_c = FauxComfy([{}, {}, {}, FINI], file={"queue_running": [[0, "pid-1"]],
                                         "queue_pending": []})
_annule = rendre(_c, dire=_dire_au_second_tour)
dit(_vus[:1] == [(0, 0)],
    "« dire » est appele des le premier tour, sans attendre un pourcentage",
    f"{_vus}")
dit(_annule.erreur == AGENT.ANNULE and not _annule.fichiers,
    "une annonce qui rapporte l'annulation arrete le rendu, et le DIT a part",
    f"erreur={_annule.erreur!r}, fichiers={_annule.fichiers}")

# ON REGARDE LA FILE AVANT DE TIRER. POST /interrupt ne nomme pas le travail
# qu'il coupe : il coupe ce qui tourne. Sur une carte dont le proprietaire se
# sert aussi depuis l'interface de ComfyUI, tirer sans regarder reviendrait a
# lui voler son rendu a lui.
dit([u for u, _ in _c.appels].index("http://comfy/queue")
    < [u for u, _ in _c.appels].index("http://comfy/interrupt"),
    "et l'agent LIT la file avant d'interrompre, pour ne couper que le sien",
    " → ".join(u.rsplit("/", 1)[-1] for u, _ in _c.appels[-3:]))

# Un travail encore en attente se retire de la file sans reveiller la carte :
# mesure du 30 aout, moins de dix millisecondes contre 2,1 s d'interruption.
_vus.clear()
_c = FauxComfy([{}, {}, {}, FINI], file={"queue_running": [],
                                         "queue_pending": [[0, "pid-1"]]})
_avant_gpu = rendre(_c, dire=_dire_au_second_tour)
dit(any(c == {"delete": ["pid-1"]} for _, c in _c.vus("/queue"))
    and not _c.vus("/interrupt"),
    "un travail encore en file est RETIRE, pas interrompu — la carte dort",
    f"{[c for _, c in _c.vus('/queue')]}")

# LE RENDU D'UN AUTRE N'EST PAS COUPE. Notre travail n'est ni en file ni sur la
# carte : il est fini, ou c'est celui du proprietaire qui tourne. On ne tire pas.
_vus.clear()
_c = FauxComfy([{}, {}, {}, FINI],
               file={"queue_running": [[0, "pid-du-proprietaire"]],
                     "queue_pending": []})
rendre(_c, dire=_dire_au_second_tour)
dit(not _c.vus("/interrupt")
    and not [c for _, c in _c.vus("/queue") if c],
    "et un rendu qui n'est pas le notre n'est NI coupe NI retire de la file",
    f"interrupt={len(_c.vus('/interrupt'))}, "
    f"delete={[c for _, c in _c.vus('/queue') if c]}")

# UNE FILE ILLISIBLE NE FAIT PAS TIRER AU HASARD.
_vus.clear()
_c = FauxComfy([{}, {}, {}, FINI], file="pas un dictionnaire")
rendre(_c, dire=_dire_au_second_tour)
dit(not _c.vus("/interrupt"),
    "une file illisible non plus : on ne tire pas sur ce qu'on n'a pas vu",
    f"interrupt={len(_c.vus('/interrupt'))}")

# UN STUDIO QUI NE DIT RIEN N'ANNULE RIEN. « dire » rend faux, et le rendu doit
# aller au bout : on ne jette pas une image sur un doute.
_c = FauxComfy([{}, {}, FINI])
_calme = rendre(_c, dire=lambda f, t: False)
dit(_calme.fichiers and _calme.erreur is None and not _c.vus("/interrupt"),
    "un studio qui ne demande rien ne fait rien couper",
    f"fichiers={len(_calme.fichiers)}, erreur={_calme.erreur!r}")


# ══════════ 4. CE QUE L'AGENT ECRIT ET EFFACE CHEZ QUELQU'UN D'AUTRE ══
# LES DEUX SEULS ENDROITS OU L'AGENT TOUCHE LE DISQUE DE LA MACHINE A CARTE.
# Le depot y ecrit des fichiers d'entree, le menage y EFFACE des sorties. Une
# machine a agent est la machine de quelqu'un — souvent celle sur laquelle il
# fait aussi ses propres rendus depuis l'interface de ComfyUI.
class Televersement:
    """Le ComfyUI qui recoit le multipart. C'est la SECONDE porte de l'agent.

    deposer_entrees() n'utilise pas appeler() : il construit sa requete a la
    main et appelle urllib.request.urlopen. On remplace donc urllib dans le
    module plutot que globalement — le vrai urllib.parse et le vrai
    urllib.error restent en place pour tout le reste de l'agent.
    """

    def __init__(self, rendu=None, leve=None):
        self.demandes, self.rendu, self.leve = [], rendu, leve

    def __call__(self, req, timeout=None, context=None):
        self.demandes.append(req)
        if self.leve is not None:
            raise self.leve
        return self

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return json.dumps(self.rendu or {}).encode()


def deposer(entrees, graphe, rendu=None, leve=None):
    faux = Televersement(rendu, leve)
    vieux = AGENT.urllib
    AGENT.urllib = types.SimpleNamespace(
        request=types.SimpleNamespace(Request=urllib.request.Request,
                                      urlopen=faux),
        parse=urllib.parse, error=urllib.error)
    erreur, souci = None, ""
    try:
        erreur = AGENT.deposer_entrees("http://comfy", entrees, graphe)
    except Exception as e:
        souci = f"{type(e).__name__}: {e}"
    finally:
        AGENT.urllib = vieux
    return types.SimpleNamespace(erreur=erreur, souci=souci,
                                 demandes=faux.demandes)


print("\n  ── ce que l'agent ecrit sur le disque de la machine a carte ──")
_graphe = {"3": {"inputs": {"image": "chat.png"}},
           "4": {"inputs": {"seed": 1}}}
_depot = deposer({"chat.png": "UE5H"}, _graphe)          # base64 de « PNG »
_req = _depot.demandes[0] if _depot.demandes else None
dit(_req is not None and _req.full_url == "http://comfy/upload/image"
    and _depot.erreur is None,
    "le fichier d'entree part sur l'/upload/image de CE ComfyUI",
    f"{_req.full_url if _req else 'aucune requete'} {_depot.souci}")

# LES OCTETS DEPOSES SONT EXACTEMENT CEUX RECUS. Le studio les envoie en
# base64 ; un decodage qui laisserait passer le texte tel quel poserait une
# image illisible sur la machine, et le rendu echouerait pour une raison
# invisible depuis le studio.
_corps = _req.data if _req else b""
dit(b"\r\n\r\nPNG\r\n" in _corps,
    "et ce sont les octets decodes qui partent, pas le base64",
    f"{_corps[-260:-120]!r}")

# LA FRONTIERE DECLAREE EST CELLE DU CORPS. Un multipart dont l'en-tete annonce
# une frontiere que le corps n'emploie pas est un corps vide pour ComfyUI, qui
# repond 200 sans avoir rien retenu — et le graphe pointerait ensuite sur un
# fichier qui n'existe pas.
_type = _req.headers.get("Content-type", "") if _req else ""
_frontiere = _type.split("boundary=")[-1] if "boundary=" in _type else "?"
dit(_frontiere != "?"
    and _corps.startswith(f"--{_frontiere}\r\n".encode())
    and _corps.rstrip().endswith(f"--{_frontiere}--".encode()),
    "la frontiere annoncee dans l'en-tete est celle qui decoupe le corps",
    f"boundary={_frontiere[:24]}…")

# DEUX FICHIERS, DEUX FRONTIERES. Elle est tiree par uuid4 a chaque fichier :
# une frontiere fixe finirait un jour par figurer dans les octets d'une image,
# et couperait le corps en plein milieu.
_deux = deposer({"a.png": "UE5H", "b.png": "UE5H"}, {})
_frontieres = {d.headers.get("Content-type", "") for d in _deux.demandes}
dit(len(_deux.demandes) == 2 and len(_frontieres) == 2,
    "chaque fichier porte SA frontiere, tiree au hasard",
    f"{len(_deux.demandes)} depots, {len(_frontieres)} frontiere(s) distincte(s)")

# ══ LE GRAPHE EST CORRIGE AVEC LE NOM REELLEMENT ACCEPTE ═══════════════
# ComfyUI renomme en « x (1).png » quand le nom existe deja. Sans cette
# correction, le graphe chercherait un fichier qui n'est pas celui qu'on vient
# d'ecrire — et le rendu partirait sur l'image du voisin.
_graphe = {"3": {"inputs": {"image": "chat.png"}},
           "5": {"inputs": {"audio": "chat.png"}},
           "6": {"inputs": {"file": "chat.png"}},
           "7": {"inputs": {"video": "chat.png"}},
           "8": {"inputs": {"texte": "chat.png"}},
           "9": {}}
deposer({"chat.png": "UE5H"}, _graphe, rendu={"name": "chat (1).png"})
dit(all(_graphe[n]["inputs"][c] == "chat (1).png"
        for n, c in (("3", "image"), ("5", "audio"), ("6", "file"),
                     ("7", "video"))),
    "quand ComfyUI renomme, les quatre champs d'entree du graphe suivent",
    f"{[_graphe[n]['inputs'] for n in ('3', '5', '6', '7')]}")
dit(_graphe["8"]["inputs"]["texte"] == "chat.png",
    "et RIEN d'autre n'est reecrit : un champ qui n'est pas une entree ne "
    "bouge pas",
    f"{_graphe['8']['inputs']}")

_refuse = deposer({"chat.png": "UE5H"}, {}, leve=OSError("413 trop gros"))
dit(_refuse.erreur and "413 trop gros" in _refuse.erreur,
    "un ComfyUI qui refuse l'entree rend une erreur, et le rendu ne part pas",
    f"{_refuse.erreur!r}")


# ══ LE REGISTRE DES DEPOTS, ET LE MENAGE ═══════════════════════════════
def _greffe_registre(ici):
    """Deplace TOUT ce que l'agent connait du disque dans un bac.

    AGENT.ICI pointe sur le depot : _reprendre_ancien_registre() y cherche un
    ancien registre, le fusionne et L'EFFACE. Un banc qui oublierait cette ligne
    effacerait un fichier du depot de celui qui le lance.
    """
    AGENT.ICI = ici
    AGENT._ancien_registre_repris = False


def poser(dossier, nom, sous=""):
    chemin = os.path.join(dossier, sous, nom)
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "wb") as f:
        f.write(b"des octets")
    return chemin


def menage(garde_h, sorties, notes=(), ici=None):
    """Note des depots puis passe le menage. Rend (efface, registre restant)."""
    vieux_ici, vieux_repris = AGENT.ICI, AGENT._ancien_registre_repris
    _greffe_registre(ici or os.path.dirname(sorties))
    efface, souci, restant = 0, "", []
    try:
        with redirect_stdout(io.StringIO()):
            for fichier, quand in notes:
                AGENT.noter_depot(sorties, fichier, quand)
            efface = AGENT.faire_le_menage(garde_h, sorties)
            restant = AGENT._registre(sorties)
    except Exception as e:
        souci = f"{type(e).__name__}: {e}"
    finally:
        AGENT.ICI, AGENT._ancien_registre_repris = vieux_ici, vieux_repris
    return types.SimpleNamespace(efface=efface, restant=restant, souci=souci)


VIEUX = _vrai_temps.time() - 50 * 3600      # au-dela des 24 h de GARDE_DEFAUT
NEUF = _vrai_temps.time()

_racine = os.path.dirname(bac())
_sorties = os.path.join(_racine, "output")
os.makedirs(_sorties)
_perso = poser(_sorties, "mon_rendu_a_moi.png")
_vieux = poser(_sorties, "depose_hier.png")
_recent = poser(_sorties, "depose_a_l_instant.png")
_r = menage(24, _sorties,
            [({"filename": "depose_hier.png"}, VIEUX),
             ({"filename": "depose_a_l_instant.png"}, NEUF)])

# LE TEMOIN D'ABORD : « le fichier personnel survit » est vrai d'un menage qui
# n'efface jamais rien, et c'est justement l'etat qu'on obtient le jour ou le
# registre cesse d'etre ecrit.
dit(_r.efface == 1 and not os.path.exists(_vieux),
    "le menage efface bien la sortie deposee et assez vieille",
    f"efface={_r.efface}, {_r.souci}")
dit(os.path.exists(_perso),
    "mais JAMAIS un fichier absent du registre : le travail du proprietaire "
    "de la machine est a lui",
    "efface" if not os.path.exists(_perso) else "intact")
dit(os.path.exists(_recent),
    "ni une sortie deposee trop recemment — la garde est un delai, pas un "
    "drapeau",
    "efface" if not os.path.exists(_recent) else "intact")
dit([e.get("chemin") for e in _r.restant] == [_recent],
    "et le registre ne garde que ce qui reste a surveiller",
    f"{[os.path.basename(e.get('chemin', '?')) for e in _r.restant]}")

# LE REGISTRE VIT DANS LE DOSSIER DES SORTIES. C'est le seul endroit persistant
# dont un agent en conteneur soit sur : son script, ses reglages et son /tmp
# repartent a zero a chaque demarrage. Ecrit a cote du script, il serait perdu
# a chaque redemarrage, et le menage n'effacerait jamais rien.
_vieux_ici, _vieux_repris = AGENT.ICI, AGENT._ancien_registre_repris
_greffe_registre(_racine)
try:
    _ou = AGENT._registre_chemin(_sorties)
finally:
    AGENT.ICI, AGENT._ancien_registre_repris = _vieux_ici, _vieux_repris
dit(os.path.dirname(_ou) == _sorties,
    "le registre des depots vit DANS le dossier des sorties, pas a cote du "
    "script",
    _ou)

# UN FICHIER DEJA PARTI EST OUBLIE ; UN FICHIER QU'ON N'ARRIVE PAS A EFFACER
# RESTE. Le premier ferait retenter la suppression sans fin, le second serait
# perdu de vue en etant raye.
_racine2 = os.path.dirname(bac())
_sorties2 = os.path.join(_racine2, "output")
os.makedirs(_sorties2)
os.makedirs(os.path.join(_sorties2, "un_dossier.png"))   # os.remove leve OSError
_r2 = menage(24, _sorties2,
             [({"filename": "jamais_ecrit.png"}, VIEUX),
              ({"filename": "un_dossier.png"}, VIEUX)])
_noms = [os.path.basename(e.get("chemin", "?")) for e in _r2.restant]
dit(_r2.efface == 0 and _noms == ["un_dossier.png"],
    "ce qui a deja disparu est oublie, ce qu'on n'a pas pu effacer reste au "
    "registre",
    f"efface={_r2.efface}, restant={_noms} {_r2.souci}")

# SANS --sorties, RIEN N'EST NOTE. « un disque qui se remplit en silence est
# plus penible qu'un dossier suppose, mais effacer au hasard le serait bien
# davantage ».
_racine3 = os.path.dirname(bac())
_r3 = menage(24, "", [({"filename": "x.png"}, VIEUX)], ici=_racine3)
dit(_r3.efface == 0 and not _r3.restant,
    "sans dossier de sorties, aucun depot n'est note et rien n'est efface",
    f"efface={_r3.efface}, registre={_r3.restant} {_r3.souci}")

# LA REPRISE DE L'ANCIEN REGISTRE. Il a demenage a cote des sorties ; sans
# reprise, les depots notes avant le demenagement ne seraient plus jamais
# effaces. On FUSIONNE au lieu de deplacer : un deplacement ecraserait les
# depots recents, un refus abandonnerait les anciens.
_racine4 = os.path.dirname(bac())
_sorties4 = os.path.join(_racine4, "output")
os.makedirs(_sorties4)
_ancien_f = poser(_sorties4, "note_avant.png")
_neuf_f = poser(_sorties4, "note_apres.png")
with open(os.path.join(_racine4, AGENT.DEPOSEES), "w", encoding="utf-8") as _g:
    json.dump([{"chemin": _ancien_f, "quand": VIEUX}], _g)
with open(os.path.join(_sorties4, "." + AGENT.DEPOSEES), "w",
          encoding="utf-8") as _g:
    json.dump([{"chemin": _neuf_f, "quand": VIEUX}], _g)
_r4 = menage(24, _sorties4, ici=_racine4)
dit(_r4.efface == 2 and not os.path.exists(_ancien_f)
    and not os.path.exists(_neuf_f),
    "l'ancien registre est REPRIS, pas ecrase : les deux notes sont honorees",
    f"efface={_r4.efface} {_r4.souci}")
dit(not os.path.exists(os.path.join(_racine4, AGENT.DEPOSEES)),
    "et l'ancien fichier ne reste pas a decrire des sorties que plus personne "
    "ne surveille",
    "efface" if not os.path.exists(os.path.join(_racine4, AGENT.DEPOSEES))
    else "toujours la")

# DEUX NOTES POUR UN MEME FICHIER : LA PLUS RECENTE GAGNE. Sinon la plus
# ancienne ferait effacer avant l'heure un fichier redepose entre-temps.
_racine5 = os.path.dirname(bac())
_sorties5 = os.path.join(_racine5, "output")
os.makedirs(_sorties5)
_redepose = poser(_sorties5, "redepose.png")
with open(os.path.join(_racine5, AGENT.DEPOSEES), "w", encoding="utf-8") as _g:
    json.dump([{"chemin": _redepose, "quand": VIEUX}], _g)
with open(os.path.join(_sorties5, "." + AGENT.DEPOSEES), "w",
          encoding="utf-8") as _g:
    json.dump([{"chemin": _redepose, "quand": NEUF}], _g)
_r5 = menage(24, _sorties5, ici=_racine5)
dit(_r5.efface == 0 and os.path.exists(_redepose),
    "et d'un fichier note deux fois, c'est la note la PLUS RECENTE qui compte",
    f"efface={_r5.efface}, encore la={os.path.exists(_redepose)} {_r5.souci}")


# ══════════════════════ 5. LA PROGRESSION ════════════════════════════
# LA TROISIEME PORTE, et la plus artisanale : ecrite a la main parce que l'agent
# doit rester un fichier unique, sans dependance a installer sur une machine
# qu'on ne maitrise pas. Une websocket ecrite a la main peut etre parfaitement
# coherente avec elle-meme et parler a cote — meme raisonnement que l'encodeur
# QR mesure contre segno.
#
# « import socket » est fait DANS la fonction : c'est donc le vrai module qu'il
# faut greffer, le temps de l'appel, et non un attribut du module agent.
def _trame(opcode, charge=b""):
    return bytes([0x80 | opcode, len(charge)]) + charge


def _texte(objet):
    return _trame(0x1, json.dumps(objet).encode())


POIGNEE_OK = b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n\r\n"


class FausseSocket:
    """Un ComfyUI qui parle websocket, morceau par morceau.

    recv() ne rend jamais deux morceaux d'un coup : la poignee de main de
    l'agent lit par blocs de 1024 octets jusqu'au « \\r\\n\\r\\n », et une
    socket qui lui servirait les trames dans le meme bloc les lui ferait avaler
    avec l'en-tete — le banc ne mesurerait alors qu'un flux vide.
    """

    def __init__(self, morceaux):
        self.morceaux = list(morceaux)
        self.envois = []
        # CE QUE L'AGENT SAIT AU MOMENT OU IL PARLE. La remise a zero du
        # pourcentage se fait quand la connexion tombe : lu apres coup, PROGRES
        # est donc toujours a zero, et « le pourcentage est relaye » serait
        # inverifiable. On le releve a chaque envoi — c'est-a-dire au pong, la
        # seule fois ou l'agent parle en cours de connexion.
        self.pendant = []
        self.fermee = False

    def sendall(self, octets):
        self.envois.append(octets)
        self.pendant.append(dict(AGENT.PROGRES))

    def recv(self, taille):
        while self.morceaux and not self.morceaux[0]:
            self.morceaux.pop(0)
        if not self.morceaux:
            return b""
        bout, self.morceaux[0] = self.morceaux[0][:taille], self.morceaux[0][taille:]
        return bout

    def settimeout(self, _):
        pass

    def close(self):
        self.fermee = True


def ecouter(scenarios, poignee=POIGNEE_OK):
    """Fait tourner la VRAIE ecouter_progression(). Rend les sockets servies.

    Elle ne s'arrete jamais : on lui refuse la connexion suivante par un Stop,
    qui est une BaseException et passe donc a travers son « except Exception ».
    """
    files = [[poignee] + list(s) for s in scenarios]
    servies = []

    def creer(adresse, timeout=None):
        if not files:
            raise Stop()
        servies.append(FausseSocket(files.pop(0)))
        return servies[-1]

    vieux_creer, vieux_temps = socket.create_connection, AGENT.time
    socket.create_connection, AGENT.time = creer, FauxTemps()
    AGENT.PROGRES.update(fait=0, total=0)
    souci = ""
    try:
        with redirect_stdout(io.StringIO()):
            AGENT.ecouter_progression("http://127.0.0.1:8188")
    except Stop:
        pass
    except Exception as e:
        souci = f"{type(e).__name__}: {e}"
    finally:
        socket.create_connection, AGENT.time = vieux_creer, vieux_temps
    return types.SimpleNamespace(
        sockets=servies, souci=souci, progres=dict(AGENT.PROGRES),
        # Le dernier releve pris en cours de connexion, ou None : c'est celui
        # du pong, la seule parole de l'agent pendant qu'il ecoute.
        pendant=(servies[-1].pendant[-1] if servies and servies[-1].pendant
                 else None))


print("\n  ── la progression, une websocket ecrite a la main ──")
_p = ecouter([[_trame(0x8)]])
_poignee = _p.sockets[0].envois[0] if _p.sockets and _p.sockets[0].envois else b""
dit(b"Upgrade: websocket" in _poignee and b"Sec-WebSocket-Version: 13" in _poignee
    and b"Sec-WebSocket-Key: " in _poignee,
    "l'agent ouvre une VRAIE poignee de main websocket sur le ComfyUI local",
    f"{_poignee[:38]!r}… {_p.souci}")

# L'AUTRE MOITIE DU client_id. ComfyUI adresse la progression au client qui a
# soumis : ce nom-ci doit etre celui qu'executer() a mis dans /prompt, et les
# deux sont ecrits a la main dans deux fonctions differentes.
dit(CLIENT_SOUMIS is not None
    and f"clientId={CLIENT_SOUMIS}".encode() in _poignee,
    "et il s'abonne sous le MEME client_id que celui qui a soumis le graphe",
    f"soumis={CLIENT_SOUMIS!r}, "
    f"abonne={_poignee.split(b'clientId=')[-1].split(b' ')[0]!r}")

_p = ecouter([[_texte({"type": "progress", "data": {"value": 7, "max": 20}}),
               _trame(0x8)]])
dit(_p.progres != {"fait": 7, "total": 20},
    "une connexion fermee par ComfyUI ne laisse pas un pourcentage FIGE",
    f"{_p.progres} — c'etait 7/20 avant la fermeture")

# LE CAS QUI PRECEDE EST LE DEFAUT CORRIGE LE 3 SEPTEMBRE 2026, et il faut son
# jumeau : sans lui, « la progression est remise a zero » serait vrai d'un agent
# qui ne relaie plus rien du tout.
_vif = ecouter([[_texte({"type": "progress", "data": {"value": 7, "max": 20}}),
                 _trame(0x9, b"reste-la")]])
dit(_vif.pendant == {"fait": 7, "total": 20},
    "tant que la connexion TIENT, le pourcentage de ComfyUI est bien relaye",
    f"{_vif.pendant}")

_p = ecouter([[_texte({"type": "progress", "data": {"value": 7, "max": 20}}),
               _texte({"type": "execution_success", "data": {}}),
               _trame(0x9, b"x")]])
dit(_p.pendant == {"fait": 0, "total": 0},
    "un rendu qui se termine remet le pourcentage a zero, connexion tenue",
    f"{_p.pendant}")

_p = ecouter([[_texte({"type": "progress", "data": {"value": 7, "max": 20}}),
               _texte({"type": "execution_interrupted", "data": {}}),
               _trame(0x9, b"x")]])
dit(_p.pendant == {"fait": 0, "total": 0},
    "un rendu interrompu aussi — sinon la barre du suivant demarre a 35 %",
    f"{_p.pendant}")

# ══ LE PONG, ET SON MASQUE ═════════════════════════════════════════════
# RFC 6455 : une trame qui va du client au serveur DOIT etre masquee, avec une
# clef tiree au hasard pour chaque trame. Un serveur qui en recoit une non
# masquee ferme la connexion — et la progression s'eteindrait toutes les
# minutes sans que rien ne leve.
#
# CINQUANTE TIRAGES, ET NON UN. Un seul pong ne distingue pas une clef tiree au
# hasard d'une clef constante : les deux passeraient le test du round-trip, et
# une clef figee — ou nulle — survivrait au banc. C'est la faute qui a laisse
# passer une faille du second facteur pendant deux cas de suite.
_masques, _bons, _entetes = set(), 0, set()
for _ in range(50):
    _p = ecouter([[_trame(0x9, b"es-tu la"), _trame(0x8)]])
    _pongs = [e for e in _p.sockets[0].envois if e[:1] == b"\x8a"]
    if len(_pongs) != 1:
        break
    _clef, _charge = _pongs[0][2:6], _pongs[0][6:]
    _entetes.add(_pongs[0][1])
    _masques.add(_clef)
    if bytes(o ^ _clef[i % 4] for i, o in enumerate(_charge)) == b"es-tu la":
        _bons += 1
dit(_bons == 50,
    "un ping recoit un pong dont la charge, demasquee, est celle du ping",
    f"{_bons}/50 tirages justes")
dit(_entetes == {0x80 | 8},
    "et son second octet declare le masque et la longueur de la charge",
    f"{[hex(e) for e in sorted(_entetes)]}")
dit(len(_masques) >= 45,
    "avec une clef de masque TIREE A CHAQUE TRAME, comme l'exige la RFC 6455",
    f"{len(_masques)} clefs distinctes en 50 tirages "
    f"— une clef figee en donnerait 1")

# UNE TRAME LONGUE. Au-dela de 125 octets, la longueur passe dans deux octets
# de plus : un ComfyUI qui nomme le noeud en cours dans son message de
# progression y arrive tout de suite.
_long = json.dumps({"type": "progress",
                    "data": {"value": 11, "max": 22, "node": "K" * 200}}).encode()
_p = ecouter([[bytes([0x81, 126]) + len(_long).to_bytes(2, "big") + _long,
               _trame(0x9, b"x")]])
dit(_p.pendant == {"fait": 11, "total": 22},
    "une trame de plus de 125 octets est lue, longueur etendue comprise",
    f"{_p.pendant}")

# CE FIL NE DOIT JAMAIS MOURIR. Une poignee de main refusee, une trame
# illisible : il se rattrape au tour suivant, sinon la barre de la file
# s'eteint jusqu'au prochain redemarrage de l'agent.
_p = ecouter([[_texte({"type": "progress", "data": {"value": 3, "max": 4}})],
              [_texte({"type": "progress", "data": {"value": 9, "max": 10}}),
               _trame(0x9, b"x")]],
             poignee=b"HTTP/1.1 403 Forbidden\r\n\r\n")
dit(len(_p.sockets) == 2 and not _p.souci,
    "une poignee de main refusee ne tue pas le fil : il se reconnecte",
    f"{len(_p.sockets)} connexion(s), {_p.souci or 'sans incident'}")
dit(all(s.fermee for s in _p.sockets),
    "et chaque socket abandonnee est refermee — pas de descripteur qui fuit",
    f"{[s.fermee for s in _p.sockets]}")

_p = ecouter([[_trame(0x1, b"{ceci n'est pas du json"),
               _texte({"type": "progress", "data": {"value": 5, "max": 6}}),
               _trame(0x9, b"x")]])
dit(_p.pendant == {"fait": 5, "total": 6},
    "une trame illisible est sautee, et la suivante est lue quand meme",
    f"{_p.pendant}")

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
sys.exit(1 if rate else 0)
