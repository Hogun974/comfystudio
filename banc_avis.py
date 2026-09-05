# -*- coding: utf-8 -*-
"""Les quatre routes par lesquelles le studio APPREND.

    uv run --with aiohttp python banc_avis.py

CE QUI MANQUAIT. Le releve du 5 septembre 2026 a compte treize routes
qu'aucun banc n'emprunte, ni par son chemin ni par sa fonction. Ce banc-ci en
prend quatre, et ce sont celles qui referment la boucle : le pouce dit ce qui
etait rate, la correction dit ce que c'etait vraiment, et le bouton de /admin
reapprend le classifieur avec.

  POST /api/avis              api_avis
  GET  /api/intentions        api_intentions
  GET  /api/admin/avis        api_admin_avis
  GET/POST /api/admin/aiguilleur   api_admin_aiguilleur

L'aiguilleur decide de l'intention de CHAQUE demande du studio. Un aiguilleur
casse ne casse pas une fonctionnalite, il les fait toutes derailler — et ce
bouton-ci est le seul endroit du studio ou un clic le remplace.

CE QU'IL GARDE, dans l'ordre des degats :

  - UN REENTRAINEMENT RATE NE TOUCHE PAS L'AIGUILLEUR EN SERVICE, et il
    RELACHE SON VERROU. Les deux moities comptent : un aiguilleur vide
    ferait tomber les onze intentions d'un coup, et un verrou reste pris
    condamnerait le bouton jusqu'au prochain redemarrage — c'est-a-dire au
    moment precis ou l'on veut reessayer.
  - LE REENTRAINEMENT N'ECRIT QUE LE MODELE LOCAL. Le modele PUBLIE est du
    code, il voyage avec le paquet ; l'ecraser avec le corpus d'une
    installation est un degat silencieux, et c'est arrive (aiguilleur.py :
    « il ecrasait la copie EMBARQUEE du modele publie »).
  - LE STUDIO SE SERT DE CE QU'IL VIENT D'ECRIRE. Sans le rechargement, le
    bouton affiche une belle mesure et le studio continue d'aiguiller avec
    le modele d'avant, jusqu'au prochain demarrage. Rien ne le dirait.
  - UN AVIS NE SE POSE QUE SUR SON PROPRE TRAVAIL, et le refus ne distingue
    pas « pas a toi » de « n'existe pas ». Le corpus est partage par tout le
    studio : etiqueter le tour d'un autre, c'est etiqueter son classifieur.
  - UN AVIS SURVIT A SA CONVERSATION. C'est toute la raison du fichier a
    part : la conversation, son proprietaire peut l'effacer.
  - LE STUDIO N'APPREND QUE DE CE QUI EST CERTAIN — un pouce en l'air, une
    correction, un moteur impose. Un tour « fini » sans pouce ne prouve rien,
    et l'apprendre reviendrait a enseigner au classifieur ses propres erreurs.
  - /api/intentions NE PROPOSE QUE CE QUE L'AIGUILLEUR CONNAIT. Proposer une
    correction qu'il ne saurait pas apprendre, c'est demander pour rien.

CE QU'IL NE DETRUIT PAS, et il faut le dire parce que c'etait le risque :
« reentrainer » ECRIT. Trois chemins sont donc detournes vers un dossier
temporaire AVANT le premier appel — le modele publie, le modele local, et le
corpus des gabarits, que corpus() reecrivait a chaque entrainement jusqu'au
5 septembre 2026. Le troisieme detour est garde meme si la route n'ecrit plus
ce fichier : c'est un filet, et il RELEVE ce que chaque ecriture visait, pour
que la derniere section puisse exiger qu'aucune n'ait vise le depot. Elle
relit aussi les trois fichiers et exige qu'ils n'aient pas bouge d'un octet.

LE SENS INVERSE. Ce banc nait bien apres les quatre routes : il n'y a pas de
filet d'avant, donc pas de diagonale. On a pris le second chemin — le banc
NEUF sur le code d'AVANT, reconstruit depuis git, le 5 septembre 2026 :

  e1198b6^  avant la correction d'intention        40 vertes, 13 rouges
  fcf3378^  avant le verrou de reentrainement      50 vertes,  6 rouges
  ff99d10^  avant le middleware d'origine          36 vertes, 14 rouges
  605b582^  avant le modele LOCAL                  30 vertes, 19 rouges
  58f920c^  avant le tuple rendu par corpus()      31 vertes, 18 rouges

Il DISTINGUE les cinq depots au lieu de mourir sur l'un d'eux, et deux lignes
valent d'etre citees parce qu'elles nomment le vrai defaut de leur epoque, et
pas seulement l'absence d'un nom :

  - sur 605b582^, « les trois fichiers que reentrainer vise n'ont pas bouge
    d'un octet — bouges : ['aiguilleur.json'] ». Le bouton ecrasait bel et
    bien le modele PUBLIE, celui que git suit ;
  - sur 58f920c^, « le bouton reentraine et rend ce qu'il a appris — HTTP
    500 ». C'est le defaut que le commentaire de _mesurer_aiguilleur raconte :
    « ne pas lire le drapeau faisait passer un tuple a apprendre() — le bouton
    rendait une erreur 500 a chaque clic ».

CE QU'IL NE VOIT PAS :

  - Que /admin et web/index.html appellent bien ces routes-la. Les quatre
    fonctions sont appelees en direct, comme banc_console.py.
  - La JUSTESSE du classifieur : entrainer_aiguilleur.py la mesure et la CI
    la garde. Ce banc mesure que la mesure est RENDUE, pas ce qu'elle vaut.

SIX DEFAUTS RELEVES LE 5 SEPTEMBRE 2026, d'abord ecrits ici sans cas — les
figer aurait rendu le banc rouge le jour de leur reparation. Ils sont corriges
le meme jour, et chacun a desormais son cas, qui exige la PROPRIETE et non la
presence d'un mot :

  - UN ENTRAINEMENT QUI ECHOUE APRES L'ECRITURE laissait sur le disque un
    modele que personne n'avait mesure : _mesurer_aiguilleur ecrivait AVANT de
    mesurer les bancs. Mesure : le fichier local passait d'absent a ecrit, la
    reponse etait 500, et le prochain demarrage prenait ce modele-la. Le cas
    fait echouer la MESURE expres et exige que le modele local n'ait pas bouge
    d'un octet, et qu'aucun fichier provisoire ne traine.
  - POST /api/admin/aiguilleur REECRIVAIT corpus_aiguillage.jsonl, un fichier
    suivi par git, dans l'arbre des sources. Le cas releve ce que chaque
    ecriture du reentrainement VISAIT et exige que rien n'ait vise le depot.
  - UN JOURNAL INECRIVABLE RENDAIT QUAND MEME « ok ». Mesure : avis.jsonl
    rendu inecrivable, POST /api/avis rendait 200 {"ok": true} et l'avis
    n'existait nulle part. Le cas rend le journal inecrivable et exige un
    refus, la phrase du dictionnaire, et un tour rendu tel qu'il etait.
  - LE DECOMPTE DES POUCES DE /admin COMPTAIT LES CLICS, PAS LES TOURS : le
    geste complet de la page pour UN pouce en bas ecrit trois lignes, et
    pouces.bas rendait 3 ; un pouce retire restait compte. Le cas rejoue le
    geste de la page et le retrait, et exige un tour, une voix.
  - avis: "oui" DEVENAIT 0, un retrait silencieux, au lieu de 400.
  - LE COMMENTAIRE DE api_avis SUR intention ETAIT FAUX : il promettait un
    refus « si l'aiguilleur ne connait pas cette classe », le code testait un
    dictionnaire fige. C'est le code qui a suivi le commentaire — une seule
    porte pour proposer et accepter — et le cas exige qu'une classe lisible
    mais inconnue de l'aiguilleur en service soit refusee.
"""
import asyncio
import hashlib
import json
import os
import sys
import tempfile

DOSSIER = tempfile.mkdtemp(prefix="banc_avis_")
os.environ["STUDIO_DONNEES"] = DOSSIER
os.environ["STUDIO_AUTH"] = "libre"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serveur as S  # noqa: E402
import corpus_aiguillage as _corpus  # noqa: E402

# LE JETON D'ADMINISTRATION EST VIDE A L'IMPORT — charger_registre() l'etablit
# au demarrage, et ce banc ne demarre pas de studio. Sans cette ligne,
# admin_ok() compare l'en-tete a une chaine vide, refuse tout, et les deux
# routes d'administration rendent 403 : le banc mesurerait sa propre absence
# d'authentification, ce qui est vrai de n'importe quel code.
S.ADMIN_JETON = "jeton-d-administration-du-banc"

# ── LES TROIS ECRITURES DU REENTRAINEMENT, DETOURNEES ───────────────────
# « Reentrainer » n'est pas une lecture : il ecrit un modele, et corpus()
# reecrit AUSSI le corpus des gabarits a chaque appel — « on regenere
# TOUJOURS, et pas seulement quand le fichier manque ». Les trois chemins
# visent le depot :
#
#   aiguilleur.json          suivi par git, c'est le modele PUBLIE
#   aiguilleur.local.json    ignore par git, mais c'est le modele que le
#                            studio de l'utilisateur prefere : l'ecraser
#                            depuis un banc lui prend son apprentissage
#   corpus_aiguillage.jsonl  suivi par git
#
# On les detourne AVANT le premier appel. La derniere section relit les trois
# et exige qu'ils n'aient pas bouge : un banc qui abime le depot qu'il mesure
# est pire qu'un banc absent.
MODELE_PUBLIE = os.path.join(DOSSIER, "publie.json")
MODELE_LOCAL = os.path.join(DOSSIER, "local.json")
S._aiguilleur.MODELE = MODELE_PUBLIE
S._aiguilleur.MODELE_LOCAL = MODELE_LOCAL
# Une valeur reconnaissable : la section 4 exige qu'elle soit encore la, mot
# pour mot, apres un reentrainement reussi.
TEMOIN_PUBLIE = ('{"poids": {"image": {"chat": 1}}, "classes": {"image": 1}, '
                 '"total": {"image": 1}, "vocabulaire": 1}')
with open(MODELE_PUBLIE, "w", encoding="utf-8") as _f:
    _f.write(TEMOIN_PUBLIE)

# corpus_aiguillage n'est PAS recharge par _mesurer_aiguilleur (seul
# entrainer_aiguilleur l'est) : le detour tient d'un bout a l'autre.
#
# LE DETOUR RELEVE CE QU'IL DETOURNE. Sans cela, il cacherait exactement le
# defaut qu'il protege : une route qui reecrirait le corpus du depot ecrirait
# ici dans le dossier temporaire, et la section 6 verrait un depot intact. On
# note donc le chemin que l'appelant VISAIT — le sien, ou le defaut du module,
# corpus_aiguillage.FICHIER — et l'on ecrit ailleurs.
_vrai_ecrire = _corpus.ecrire
ECRITURES_VISEES = []


def _ecrire_detourne(exemples, chemin=None):
    ECRITURES_VISEES.append(os.path.abspath(chemin or _corpus.FICHIER))
    return _vrai_ecrire(exemples, os.path.join(DOSSIER, "corpus.jsonl"))


_corpus.ecrire = _ecrire_detourne

ok, rate = [], []


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


class Req(dict):
    """Une requete assez complete pour ces quatre routes et pour les deux
    garde-fous de middleware qui les couvrent.

    « chemin » et « methode » ne servent pas aux routes elles-memes — elles
    lisent le corps et les en-tetes — mais aux middlewares de la section 5,
    qui decident sur eux seuls.
    """

    def __init__(self, corps=None, pid="u" * 32, entetes=None, admin=False,
                 methode="POST", chemin="/api/avis", compte=""):
        super().__init__(pid=pid, compte=compte)
        self.headers = dict(entetes or {})
        if admin and "X-Admin" not in self.headers:
            self.headers["X-Admin"] = S.ADMIN_JETON
        self.cookies = {}
        self.match_info = {}
        self.method = methode
        self.path = chemin
        self._corps = corps

    async def json(self):
        if self._corps is None:
            raise ValueError("pas de corps")
        return self._corps


def lire(rep):
    return rep.status, json.loads(rep.text)


lancer = asyncio.run
MOI = "u" * 32
AUTRE = "v" * 32


def aig(methode="GET", admin=True):
    """Une requete pour /api/admin/aiguilleur, GET ou POST."""
    return Req(methode=methode, admin=admin, chemin="/api/admin/aiguilleur")


def texte(cle, langue):
    """Le message du dictionnaire, ou un TEMOIN IMPOSSIBLE.

    T() cherche par hasattr et non par S.T direct : sur un depot d'avant le
    dictionnaire, l'attribut n'existe pas et la section entiere mourrait sur
    un AttributeError — « le banc s'est casse au lieu de rougir » ne mesure
    rien. Le defaut n'est SURTOUT pas le message d'aujourd'hui : souffler la
    reponse rendrait le cas vert au lieu de rouge, ce qui est la faute que
    banc_boucle.py a corrigee sur ses accesseurs tolerants.
    """
    if not hasattr(S, "T"):
        return f"<aucun dictionnaire pour {cle}/{langue}>"
    return getattr(S, "T")(cle, langue)


# ENTRAINEUR CHERCHE ET NON EXIGE, pour la meme raison : la section 4 lit
# BANCS et POIDS_REEL, et un depot qui n'aurait pas ce module doit poser des
# cas nommes plutot qu'une trace de pile a l'import du banc.
try:
    import entrainer_aiguilleur as _entrainer  # noqa: E402
except Exception:
    _entrainer = None


def du_maitre(nom, temoin):
    """Une constante d'entrainer_aiguilleur.py, ou un temoin impossible."""
    return getattr(_entrainer, nom, temoin) if _entrainer else temoin


def journal():
    """Ce que avis.jsonl porte VRAIMENT, relu du disque.

    Relire le fichier et non un objet en memoire : la question posee est
    « le retour survit-il a la conversation », et seul le disque y repond.
    """
    try:
        with open(S.FICHIER_AVIS, encoding="utf-8") as f:
            return [json.loads(l) for l in f if l.strip()]
    except OSError:
        return []


def table_rase():
    """Un studio neuf : ni conversation, ni journal d'avis, ni rien du cas
    d'avant. Tout se passe dans le dossier temporaire de ce banc."""
    S.CONVERSATIONS.clear()
    S.COURANTE.clear()
    for nom in os.listdir(DOSSIER):
        if nom.endswith(".json") and nom not in ("publie.json", "local.json"):
            os.remove(os.path.join(DOSSIER, nom))
    if os.path.exists(S.FICHIER_AVIS):
        os.remove(S.FICHIER_AVIS)


def poser_tour(pid=MOI, tid="t1", **change):
    """Une conversation d'une personne, avec un tour fini qui a produit."""
    conv = S._vide(proprietaire=pid)
    tour = {"id": tid, "demande": "un renard roux dans les hautes herbes",
            "type": "image", "etat": "fini", "modele": "sdxl",
            "prompt": "a red fox in tall grass", "parametres": {"pas": 20},
            "paroles": None, "raison": "", "erreur": None,
            "fichiers": [{"filename": "renard.png"}]}
    tour.update(change)
    conv["tours"] = [tour]
    S.CONVERSATIONS[conv["id"]] = conv
    S.sauver(conv)
    return conv, tour


async def avis(corps, pid=MOI, entetes=None):
    return lire(await S.api_avis(Req(corps, pid=pid, entetes=entetes)))


def empreinte(chemin):
    try:
        with open(chemin, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except OSError:
        return "absent"


# CE QUE LE DEPOT PORTE AVANT QU'ON Y TOUCHE. Releve ici, compare a la fin.
DEPOT = {nom: empreinte(os.path.join(S.ICI, nom)) for nom in
         ("aiguilleur.json", "aiguilleur.local.json", "corpus_aiguillage.jsonl")}


# ── UNE SECTION QUI MEURT NE MESURE RIEN ────────────────────────────────
# « Un banc qui meurt sur le code d'avant ne mesure pas le sens inverse »
# (docs/eprouver-les-bancs.md). banc_comptes.py a emporte ses soixante
# verifications sur un TypeError, et banc_boucle.py s'arretait sur un
# AttributeError cinq commits sur six. Chaque section est donc lancee sous
# garde : une mort y pose UN cas nomme, et les autres sections continuent.
# C'est ce qui permet de relancer ce banc-ci, tel quel, sur un depot d'avant.
def section(titre, faire):
    print("\n  ── " + titre + " ──")
    try:
        faire()
    except Exception as e:
        dit(False, f"la section « {titre} » s'est arretee au lieu de mesurer",
            f"{type(e).__name__}: {e}")


# LES NOMS DONT CE BANC A BESOIN, CHERCHES ET NON IMPORTES. Sur un depot qui
# n'a pas encore ces routes, hasattr rend faux et le banc le DIT ; un import
# direct le tuerait a la premiere ligne, et « le banc s'est casse au lieu de
# rougir » ne mesure rien.
ATTENDUS = ("api_avis", "api_intentions", "api_admin_avis",
            "api_admin_aiguilleur", "noter_avis", "lire_avis",
            "INTENTIONS_LISIBLES", "SANS_ECRITURE", "_VERROU_AIGUILLEUR",
            "_mesurer_aiguilleur", "origine_verifiee", "exiger_compte")
absents = [n for n in ATTENDUS if not hasattr(S, n)]
dit(not absents,
    "les quatre routes et ce qui les tient existent dans serveur.py",
    f"manquants : {absents or 'aucun'}")

def _section_1():
    # ══════════════════════════════════════════════════════════════════
    #  1. POST /api/avis — ou va un avis, et a qui il appartient
    # ══════════════════════════════════════════════════════════════════
    table_rase()
    conv, tour = poser_tour()

    st, d = lancer(avis({"tid": "t1", "avis": 1}))
    dit(st == 200 and d.get("ok") and d.get("avis") == 1,
        "un pouce en l'air est accepte et rend l'avis pose",
        f"HTTP {st}, avis={d.get('avis')}")
    dit(tour.get("avis") == 1, "l'avis est ecrit sur le tour",
        f"tour.avis={tour.get('avis')}")

    lignes = journal()
    dit(len(lignes) == 1, "et une ligne part dans le journal des avis",
        f"{len(lignes)} ligne(s) dans {os.path.basename(S.FICHIER_AVIS)}")

    # « DE QUOI REFAIRE LE CAS SANS REDEMANDER A PERSONNE » — docs/avis.md. On
    # exige le JEU DE CHAMPS EN ENTIER et non la presence de l'un d'eux : une
    # ligne qui aurait perdu le prompt ou les parametres se relit encore, et
    # ne sert plus a rien. C'est la faute que CONTRIBUTING appelle « le mot
    # taskkill est la » — la valeur entiere, ou rien.
    ATTENDUS = {"quand", "avis", "note", "utilisateur", "conversation", "tour",
                "demande", "moteur", "type", "intention_voulue", "parametres",
                "prompt", "paroles", "raison", "etat", "erreur", "fichiers"}
    ligne = lignes[0] if lignes else {}
    manque = ATTENDUS - set(ligne)
    dit(not manque and set(ligne) == ATTENDUS,
        "la ligne porte de quoi refaire le cas sans la conversation : les "
        "dix-sept champs, ni un de moins",
        f"manquants : {sorted(manque) or 'aucun'}"
        + (f", en trop : {sorted(set(ligne) - ATTENDUS)}"
           if set(ligne) - ATTENDUS else ""))
    dit(ligne.get("demande") == tour["demande"]
        and ligne.get("prompt") == tour["prompt"]
        and ligne.get("moteur") == tour["modele"]
        and ligne.get("type") == tour["type"]
        and ligne.get("parametres") == tour["parametres"]
        and ligne.get("fichiers") == ["renard.png"],
        "et ce sont les valeurs DU TOUR, pas des cases vides",
        f"moteur={ligne.get('moteur')}, fichiers={ligne.get('fichiers')}")
    dit(ligne.get("utilisateur") == MOI[:12] and len(ligne.get("utilisateur", "")) == 12,
        "l'auteur y est, tronque a douze caracteres",
        str(ligne.get("utilisateur")))

    # LA RAISON D'ETRE DU FICHIER A PART. « pas dans la conversation, que son
    # proprietaire peut supprimer » — docs/avis.md. Sans ce cas, un avis range
    # dans la conversation passerait tous les autres.
    chemin_conv = os.path.join(S.DOSSIER_CONV, conv["id"] + ".json")
    S.CONVERSATIONS.pop(conv["id"], None)
    if os.path.exists(chemin_conv):
        os.remove(chemin_conv)
    survivante = journal()
    dit(len(survivante) == 1
        and survivante[0].get("demande") == "un renard roux dans les hautes herbes",
        "la conversation effacee, l'avis est toujours la, avec la demande : "
        "c'est la seule mesure qu'on ait de ce qui marche",
        f"{len(survivante)} ligne(s) apres suppression de la conversation")

    # ── un avis ne se pose pas sur le travail d'un autre ────────────────
    print("\n  ── a qui appartient un avis ──")
    table_rase()
    _, sien = poser_tour(pid=AUTRE, tid="pas-a-moi")
    st, d = lancer(avis({"tid": "pas-a-moi", "avis": 1}))
    dit(st == 404 and sien.get("avis") is None and not journal(),
        "un avis sur le travail de quelqu'un d'autre est refuse, et son tour "
        "n'est pas touche",
        f"HTTP {st}, tour.avis={sien.get('avis')}, {len(journal())} ligne(s)")

    st_inconnu, d_inconnu = lancer(avis({"tid": "jamais-vu", "avis": 1}))
    dit(st_inconnu == 404 and d_inconnu.get("erreur") == d.get("erreur"),
        "et le refus est MOT POUR MOT celui d'un tour inexistant : distinguer "
        "« pas a toi » de « n'existe pas » renseignerait un curieux",
        f"{d.get('erreur')!r} contre {d_inconnu.get('erreur')!r}")

    # UNE CONVERSATION FERMEE SORT DE mes_conversations(). Elle attend sa
    # purge ; on ne la commente plus.
    table_rase()
    fermee, _ = poser_tour(tid="t-ferme")
    fermee["ferme"] = True
    st, d = lancer(avis({"tid": "t-ferme", "avis": 1}))
    dit(st == 404 and not journal(),
        "une conversation fermee n'accepte plus d'avis", f"HTTP {st}")

    # ── retirer un pouce ────────────────────────────────────────────────
    print("\n  ── retirer un pouce, et corriger l'intention ──")
    table_rase()
    conv, tour = poser_tour()
    lancer(avis({"tid": "t1", "avis": -1}))
    avant = len(journal())
    st, d = lancer(avis({"tid": "t1", "avis": 0}))
    # UN RETRAIT S'ECRIT S'IL RETIRE QUELQUE CHOSE. Jusqu'au 5 septembre 2026
    # il n'ecrivait rien — « un retrait n'est pas un retour » — et c'etait
    # coherent avec un /admin qui comptait les LIGNES. Depuis qu'il compte par
    # tour, dernier avis retenu, la ligne de retrait est ce qui permet de ne
    # plus compter un pouce que personne ne porte. On exige UNE ligne, et
    # qu'elle porte zero : deux lignes ou un -1 recopie seraient le vieux
    # defaut sous une autre forme.
    dit(st == 200 and tour.get("avis") == 0 and len(journal()) == avant + 1
        and journal()[-1].get("avis") == 0,
        "un pouce retire (avis=0) efface l'avis du tour et ecrit UNE ligne de "
        "retrait, qui porte zero : c'est elle qui decompte le pouce",
        f"HTTP {st}, tour.avis={tour.get('avis')}, {len(journal())} ligne(s), "
        f"derniere avis={journal()[-1].get('avis') if journal() else '?'}")

    # ET UN ZERO SUR UN TOUR QUI N'AVAIT RIEN N'ECRIT RIEN. La page envoie
    # zero quand on reclique le meme pouce ; un zero venu d'ailleurs, sur un
    # tour vierge, ne retire rien et n'a pas a laisser de trace.
    table_rase()
    conv, tour = poser_tour(tid="t-vierge")
    st, d = lancer(avis({"tid": "t-vierge", "avis": 0}))
    dit(st == 200 and not journal(),
        "un retrait sur un tour qui n'avait pas d'avis n'ecrit aucune ligne : "
        "il n'y a rien a retirer", f"HTTP {st}, {len(journal())} ligne(s)")

    # ── le journal refuse ───────────────────────────────────────────────
    # LE CAS DU 5 SEPTEMBRE 2026, mesure a la main : avis.jsonl inecrivable,
    # la route rendait 200 {"ok": true, "avis": 1} et l'avis n'existait nulle
    # part. Un DOSSIER a la place du fichier : open(..., "a") echoue sur les
    # trois plateformes, sans droits a manipuler ni a restaurer.
    print("\n  ── quand le journal refuse ──")
    table_rase()
    conv, tour = poser_tour(tid="t-mur")
    os.mkdir(S.FICHIER_AVIS)
    try:
        st, d = lancer(avis({"tid": "t-mur", "avis": 1, "note": "net"}))
    finally:
        os.rmdir(S.FICHIER_AVIS)
    dit(st == 500 and not d.get("ok")
        and d.get("erreur") == texte("erreur.avis_non_consigne", "fr"),
        "un journal inecrivable ne rend pas « ok » : la route refuse et dit "
        "pourquoi, avec la phrase du dictionnaire",
        f"HTTP {st}, {d!r}"[:100])
    dit(tour.get("avis") is None and "note" not in tour,
        "et le tour est rendu tel qu'il etait : un avis consigne nulle part "
        "n'a pas ete pose",
        f"tour.avis={tour.get('avis')}, note={'presente' if 'note' in tour else 'absente'}")

    # ── la correction d'intention ───────────────────────────────────────
    table_rase()
    conv, tour = poser_tour(tid="t-corr")
    st, d = lancer(avis({"tid": "t-corr", "avis": -1, "intention": "chanson"}))
    dit(st == 400 and "intention_voulue" not in tour and not journal(),
        "une etiquette qui n'existe pas est refusee, et rien n'est ecrit — ni "
        "sur le tour, ni dans le journal",
        f"HTTP {st}, {len(journal())} ligne(s)")

    st, d = lancer(avis({"tid": "t-corr", "avis": -1, "intention": "audio",
                         "note": "c'etait une musique"}))
    dit(st == 200 and tour.get("intention_voulue") == "audio",
        "une correction connue est posee sur le tour : c'est elle que "
        "l'entrainement apprendra",
        f"HTTP {st}, intention_voulue={tour.get('intention_voulue')}")
    dit(journal() and journal()[-1].get("intention_voulue") == "audio"
        and journal()[-1].get("note") == "c'etait une musique",
        "et la ligne du journal la porte, avec le mot",
        f"intention_voulue={journal()[-1].get('intention_voulue') if journal() else '?'}")

    lancer(avis({"tid": "t-corr", "avis": 1}))
    dit("intention_voulue" not in tour,
        "un pouce repasse en l'air efface la correction : elle ne valait que "
        "pour le reproche", f"tour={sorted(k for k in tour if 'intention' in k)}")

    # ── ce que la route refuse ──────────────────────────────────────────
    print("\n  ── ce que la route refuse, et dans quelle langue ──")
    table_rase()
    conv, tour = poser_tour(tid="t-refus")
    st, d = lancer(avis({"tid": "t-refus", "avis": 2}))
    dit(st == 400 and d.get("erreur") == texte("erreur.avis_attendu", "fr")
        and not journal(),
        "un avis hors de -1, 0, 1 est refuse, et rien n'est ecrit",
        f"HTTP {st}, {d.get('erreur')!r}")

    # « oui » N'EST PAS ZERO. int("oui") echoue, le repli valait 0, et la
    # garde « not in (-1, 0, 1) » ne voyait rien : un avis illisible passait
    # pour un RETRAIT, rendait 200, et effacait le pouce du tour. On pose un
    # pouce d'abord, pour que l'effacement ait quelque chose a effacer.
    lancer(avis({"tid": "t-refus", "avis": 1}))
    st, d = lancer(avis({"tid": "t-refus", "avis": "oui"}))
    dit(st == 400 and d.get("erreur") == texte("erreur.avis_attendu", "fr")
        and tour.get("avis") == 1,
        "un avis illisible (« oui ») est refuse comme un avis hors bornes, et "
        "ne passe pas pour un retrait : le pouce pose reste pose",
        f"HTTP {st}, tour.avis={tour.get('avis')}")
    table_rase()
    conv, tour = poser_tour(tid="t-refus")

    st, d = lancer(avis({"tid": "t-refus", "avis": 2},
                        entetes={"Accept-Language": "en"}))
    # LU PAR UN HUMAIN, DONC TRADUIT — c'est ce que dit le commentaire de la
    # route. On exige la CHAINE ANGLAISE DU DICTIONNAIRE, pas « une chaine
    # differente » : un message qui changerait pour une autre raison passerait.
    dit(d.get("erreur") == texte("erreur.avis_attendu", "en")
        and texte("erreur.avis_attendu", "en") != texte("erreur.avis_attendu", "fr"),
        "et le refus est traduit : cette route-ci est lue par un humain, dans "
        "une interface", f"{d.get('erreur')!r}")

    st, d = lancer(avis(None))
    dit(st == 400 and d.get("erreur") == texte("erreur.corps_illisible", "fr"),
        "un corps illisible rend 400 et le dit", f"HTTP {st}, {d.get('erreur')!r}")

    lancer(avis({"tid": "t-refus", "avis": -1, "note": "x" * 5000}))
    dit(len(tour.get("note", "")) == 2000
        and len(journal()[-1].get("note", "")) == 2000,
        "la note est bornee a deux mille caracteres DES DEUX COTES, le tour et "
        "le journal", f"tour {len(tour.get('note', ''))}, "
        f"journal {len(journal()[-1].get('note', '')) if journal() else '?'}")


def _section_2():
    # ══════════════════════════════════════════════════════════════════
    #  2. GET /api/intentions — ce qu'on ose proposer
    # ══════════════════════════════════════════════════════════════════
    vrai_aiguilleur = S.AIGUILLEUR
    try:
        S.AIGUILLEUR = S._aiguilleur.Aiguilleur(
            classes={"image": 1, "audio": 1, "detourer": 1})
        _, liste = lire(lancer(S.api_intentions(Req())))
        cles = [x.get("cle") for x in liste]
        dit(cles == ["image", "audio", "detourer"],
            "elle ne propose QUE les classes que l'aiguilleur connait "
            "reellement : proposer une correction qu'il ne saurait pas "
            "apprendre serait demander pour rien", f"rendu {cles}")
        dit(all(x.get("titre") and x["titre"] != x["cle"] for x in liste),
            "chacune porte un titre lisible, et non sa clef",
            ", ".join(f"{x['cle']}={x['titre']!r}" for x in liste))

        # TOUTE CLEF PROPOSEE DOIT ETRE ACCEPTEE PAR L'AUTRE ROUTE. Les deux
        # cotes du meme geste : la page propose, la page repose. Une liste qui
        # proposerait une clef refusee par POST /api/avis offrirait un bouton
        # qui rend 400.
        table_rase()
        conv, tour = poser_tour(tid="t-accord")
        refuses = []
        for x in liste:
            st, _ = lancer(avis({"tid": "t-accord", "avis": -1,
                                 "intention": x["cle"]}))
            if st != 200:
                refuses.append((x["cle"], st))
        dit(not refuses,
            "et chacune est acceptee par POST /api/avis : la page ne propose "
            "pas un bouton qui rendra 400", f"refusees : {refuses or 'aucune'}")

        # L'AUTRE MOITIE DU MEME ACCORD. « video » est lisible — le
        # dictionnaire fige la connait — mais cet aiguilleur-ci ne l'a jamais
        # apprise. Jusqu'au 5 septembre 2026 la route l'acceptait : le
        # commentaire promettait « refusee si l'aiguilleur ne connait pas
        # cette classe », le code testait INTENTIONS_LISIBLES. L'etiquette
        # dormait sur le tour, et moissonner() la jetait en silence.
        conv, tour = poser_tour(tid="t-inconnue")
        st, d = lancer(avis({"tid": "t-inconnue", "avis": -1,
                             "intention": "video"}))
        dit(st == 400 and "intention_voulue" not in tour and tour.get("avis") is None
            and d.get("erreur") == texte("erreur.intention_inconnue", "fr"),
            "et une classe lisible mais que l'aiguilleur EN SERVICE ne connait "
            "pas est refusee par POST /api/avis, sans rien ecrire : ce que la "
            "page ne propose pas, la route ne l'accepte pas",
            f"HTTP {st}, intention_voulue={tour.get('intention_voulue')}")

        # SANS AIGUILLEUR, RIEN. Le commentaire de la route nomme la faute
        # exacte : « or INTENTIONS_LISIBLES » proposait les onze classes a un
        # studio qui n'a aucun classifieur pour les apprendre.
        S.AIGUILLEUR = None
        _, liste = lire(lancer(S.api_intentions(Req())))
        dit(liste == [],
            "sans aiguilleur, elle ne propose RIEN : la page n'affiche alors "
            "pas la question, et c'est la bonne reponse", f"rendu {liste}")
        conv, tour = poser_tour(tid="t-sans")
        st, d = lancer(avis({"tid": "t-sans", "avis": -1, "intention": "image"}))
        dit(st == 400 and "intention_voulue" not in tour,
            "et sans aiguilleur, aucune correction n'est acceptee non plus : "
            "il n'y a personne pour l'apprendre",
            f"HTTP {st}, intention_voulue={tour.get('intention_voulue')}")
    finally:
        S.AIGUILLEUR = vrai_aiguilleur


def _section_3():
    # ══════════════════════════════════════════════════════════════════
    #  3. GET /api/admin/avis — le recapitulatif
    # ══════════════════════════════════════════════════════════════════
    table_rase()
    for i, (pid, sens) in enumerate(((MOI, 1), (AUTRE, -1), (MOI, -1))):
        poser_tour(pid=pid, tid=f"r{i}")
        lancer(avis({"tid": f"r{i}", "avis": sens}, pid=pid))

    st, d = lire(lancer(S.api_admin_avis(Req(methode="GET",
                                             chemin="/api/admin/avis"))))
    dit(st == 403 and "avis" not in d,
        "sans le jeton d'administration, le recapitulatif est refuse — et ne "
        "laisse pas fuir une ligne au passage",
        f"HTTP {st}, cles rendues {sorted(d)}")

    st, d = lire(lancer(S.api_admin_avis(Req(methode="GET", admin=True,
                                             chemin="/api/admin/avis"))))
    tous = d.get("avis") or []
    dit(st == 200 and [x.get("tour") for x in tous] == ["r2", "r1", "r0"],
        "avec le jeton, il rend les avis LE PLUS RECENT D'ABORD",
        f"HTTP {st}, {[x.get('tour') for x in tous]}")
    dit(sorted({x.get("utilisateur") for x in tous}) == sorted({MOI[:12], AUTRE[:12]}),
        "et ceux de TOUT LE MONDE : c'est /admin, pas la page de quelqu'un",
        str(sorted({x.get("utilisateur") for x in tous})))
    dit(d.get("pouces") == {"haut": 1, "bas": 2},
        "le decompte des pouces est celui des tours rendus, un pouce par tour",
        str(d.get("pouces")))

    # UN TOUR, UNE VOIX. Le geste complet de la page pour UN pouce en bas
    # ecrit TROIS lignes — le pouce part avant le mot, puis avec le mot, puis
    # avec la correction — et /admin comptait ses lignes : pouces.bas rendait 3
    # pour un seul reproche, mesure du 5 septembre 2026. Un pouce retire
    # restait compte, et un avis change de camp comptait des deux cotes. Les
    # trois defauts dans un seul journal, et un seul decompte attendu.
    table_rase()
    poser_tour(tid="g-bas")
    reponses = [lancer(avis({"tid": "g-bas", "avis": -1}))[0],
                lancer(avis({"tid": "g-bas", "avis": -1, "note": "flou"}))[0],
                lancer(avis({"tid": "g-bas", "avis": -1, "note": "flou",
                             "intention": "audio"}))[0]]
    poser_tour(pid=AUTRE, tid="g-retire")
    reponses.append(lancer(avis({"tid": "g-retire", "avis": 1}, pid=AUTRE))[0])
    reponses.append(lancer(avis({"tid": "g-retire", "avis": 0}, pid=AUTRE))[0])
    poser_tour(tid="g-change")
    reponses.append(lancer(avis({"tid": "g-change", "avis": 1}))[0])
    reponses.append(lancer(avis({"tid": "g-change", "avis": -1}))[0])
    _, d = lire(lancer(S.api_admin_avis(Req(methode="GET", admin=True,
                                            chemin="/api/admin/avis"))))
    dit(reponses == [200] * 7 and len(journal()) == 7
        and d.get("pouces") == {"haut": 0, "bas": 2},
        "le geste complet de la page pour un pouce en bas, un pouce retire et "
        "un avis change de camp : sept lignes, et le decompte dit deux pouces "
        "en bas, zero en haut — un tour, une voix, le dernier avis retenu",
        f"reponses {reponses}, {len(journal())} ligne(s), pouces={d.get('pouces')}")
    rendus = d.get("avis") or []
    dit(len(rendus) == 6 and all(x.get("avis") in (1, -1) for x in rendus),
        "et la liste rendue ne montre que les retours, jamais la ligne de "
        "retrait : /admin ne sait peindre qu'un pouce ou l'autre",
        f"{len(rendus)} rendus, avis={[x.get('avis') for x in rendus]}")

    # LE PLAFOND. /admin doit rester ouvrable quand le journal a grossi : sans
    # borne, la page se charge le fichier entier a chaque rafraichissement.
    table_rase()
    with open(S.FICHIER_AVIS, "w", encoding="utf-8") as f:
        for i in range(405):
            f.write(json.dumps({"tour": f"x{i}", "avis": 1}) + "\n")
    _, d = lire(lancer(S.api_admin_avis(Req(methode="GET", admin=True,
                                            chemin="/api/admin/avis"))))
    tous = d.get("avis") or []
    # PAR ENSEMBLE ET NON PAR RANG : l'ordre a son propre cas, quelques lignes
    # plus haut. Deux cas qui mesurent la meme chose rougissent ensemble, et
    # l'on ne sait plus lequel des deux defauts on regarde.
    dit(len(tous) == 400
        and {x.get("tour") for x in tous} == {f"x{i}" for i in range(5, 405)},
        "il est plafonne aux quatre cents dernieres lignes, et ce sont les "
        "DERNIERES", f"{len(tous)} lignes, les cinq premieres ecrites "
        f"{'absentes' if not {'x0'} & {x.get('tour') for x in tous} else 'PRESENTES'}")
    dit(d.get("pouces", {}).get("haut") == 400,
        "et le decompte porte sur ce qui est rendu, pas sur le fichier entier",
        str(d.get("pouces")))

    # « LE FORMAT UNE LIGNE, UN OBJET SE RELIT MEME SI L'ECRITURE A ETE COUPEE
    # EN COURS » — noter_avis. Une ecriture interrompue par un arret laisse une
    # derniere ligne tronquee ; si elle emportait le fichier, /admin perdrait
    # tout l'historique des retours au premier arret brutal.
    table_rase()
    with open(S.FICHIER_AVIS, "w", encoding="utf-8") as f:
        f.write(json.dumps({"tour": "entier", "avis": 1}) + "\n")
        f.write('{"tour": "tronq')
    try:
        _, d = lire(lancer(S.api_admin_avis(Req(methode="GET", admin=True,
                                                chemin="/api/admin/avis"))))
        entiers = [x.get("tour") for x in (d.get("avis") or [])]
    except Exception as e:
        entiers = f"le recapitulatif est mort : {type(e).__name__}"
    dit(entiers == ["entier"],
        "une derniere ligne tronquee par un arret ne fait pas perdre les "
        "autres : c'est toute la raison du format « une ligne, un objet »",
        str(entiers))

    # SOUS try COMME CI-DESSUS : un journal absent qui leverait ferait MOURIR
    # le banc au lieu de le faire rougir, et « le banc s'est casse au lieu de
    # rougir » ne mesure rien.
    table_rase()
    try:
        _, d = lire(lancer(S.api_admin_avis(Req(methode="GET", admin=True,
                                                chemin="/api/admin/avis"))))
    except Exception as e:
        d = {"avis": f"le recapitulatif est mort : {type(e).__name__}"}
    dit(d.get("avis") == [] and d.get("pouces") == {"haut": 0, "bas": 0},
        "un studio qui n'a jamais recu d'avis rend une liste vide, et non une "
        "erreur", str(d))


def _section_4():
    # ══════════════════════════════════════════════════════════════════
    #  4. /api/admin/aiguilleur — l'etat, et le reentrainement
    # ══════════════════════════════════════════════════════════════════

    # DE QUOI CETTE SECTION A BESOIN, ET QU'AUCUN import NE NOMME. Le modele
    # publie est charge a l'import de serveur.py ; le vrai reentrainement lit
    # en plus trois corpus et deux bancs d'aiguillage. Ce sont des DONNEES : le
    # lanceur de mutations les copie s'il les connait, et rend un dossier
    # d'essai muet sinon — corpus tronque, bancs=[], present=False. Sans cette
    # ligne, huit cas rougiraient pour une raison qui n'a rien a voir avec la
    # mutation qu'on leur presente, et l'on chercherait ailleurs. C'est la
    # cinquieme fois que le depot se fait prendre a cela.
    NOURRITURE = ("aiguilleur.json", "corpus_aiguillage.jsonl",
                  "corpus_llm.jsonl", "corpus_llm2.jsonl",
                  "banc_aiguillage.jsonl", "banc_neuf.jsonl")
    absents = [n for n in NOURRITURE
               if not os.path.exists(os.path.join(S.ICI, n))]
    dit(not absents,
        "le modele publie, les corpus et les bancs d'aiguillage sont la : "
        "sans eux, cette section ne mesure rien",
        f"manquants : {absents or 'aucun'}")

    st, d = lire(lancer(S.api_admin_aiguilleur(aig(admin=False))))
    dit(st == 403 and "classes" not in d,
        "GET sans le jeton d'administration est refuse", f"HTTP {st}")
    st, d = lire(lancer(S.api_admin_aiguilleur(aig("POST", admin=False))))
    dit(st == 403,
        "POST — le REENTRAINEMENT — sans le jeton l'est aussi : c'est le seul "
        "clic du studio qui remplace le classifieur de tout le monde",
        f"HTTP {st}")

    st, d = lire(lancer(S.api_admin_aiguilleur(aig())))
    dit(st == 200 and d.get("present") is True and d.get("traits", 0) > 0
        and len(d.get("classes") or {}) == 11,
        "l'etat dit qu'un aiguilleur est la, combien de traits et quelles "
        "classes", f"{d.get('traits')} traits, "
        f"{len(d.get('classes') or {})} classes")
    # LA LISTE ENTIERE, ET DANS L'ORDRE. Ces trois intentions sont celles qui
    # ne demandent AUCUNE ecriture — le classifieur tranche seul, sans appeler
    # le moindre modele. Exiger « detourer est dedans » laisserait passer la
    # perte des deux autres.
    dit(d.get("sans_ecriture") == list(S.SANS_ECRITURE)
        and d.get("sans_ecriture") == ["agrandir", "detourer", "fluidifier"],
        "et il nomme les trois intentions qui se passent du modele de langage, "
        "en entier", str(d.get("sans_ecriture")))

    vrai_aiguilleur = S.AIGUILLEUR
    try:
        S.AIGUILLEUR = None
        st, d = lire(lancer(S.api_admin_aiguilleur(aig())))
        dit(st == 200 and d.get("present") is False and d.get("classes") == {}
            and d.get("traits") == 0,
            "un studio sans aiguilleur le DIT, au lieu de mourir en le lisant",
            f"HTTP {st}, present={d.get('present')}")
    finally:
        S.AIGUILLEUR = vrai_aiguilleur

def _section_4b():
    # LE VERROU CHERCHE ET NON EXIGE : sur un depot d'avant fcf3378 il n'existe
    # pas, et S._VERROU_AIGUILLEUR emporterait la section entiere sur un
    # AttributeError au lieu de poser un cas nomme.
    VERROU = getattr(S, "_VERROU_AIGUILLEUR", None)

    # LE VERROU, PRIS PAR UN PREMIER ENTRAINEMENT. Deux POST concurrents
    # partaient dans deux fils du pool : l'un regenerait le corpus pendant que
    # l'autre le relisait.
    #
    # LA BORNE N'EST PAS UN REGLAGE DE VITESSE. Le chemin mesure ici ne fait
    # AUCUN travail — il regarde un verrou et rend 409 —, il n'attend donc
    # jamais. La borne existe pour qu'un code qui ATTENDRAIT au lieu de refuser
    # pose une ligne rouge nommee plutot que de pendre : « le pendage est pire,
    # il ne se declare pas du tout » (docs/eprouver-les-bancs.md). Cinq
    # secondes contre les 0,07 s que met l'entrainement COMPLET sur cette
    # machine : soixante-dix fois la marge, et elle est pour la charge.
    BORNE_REFUS = 5.0

    async def second_pendant_le_premier():
        await VERROU.acquire()
        try:
            tache = asyncio.ensure_future(S.api_admin_aiguilleur(aig("POST")))
            try:
                return lire(await asyncio.wait_for(tache, BORNE_REFUS))
            except asyncio.TimeoutError:
                return None, {}
        finally:
            VERROU.release()

    st, d = (lancer(second_pendant_le_premier()) if VERROU is not None
             else (None, {}))
    dit(st == 409,
        "un second reentrainement pendant qu'un premier tourne est refuse TOUT "
        "DE SUITE, et ne se met pas en file",
        f"HTTP {st}" if st else
        ("aucun verrou dans ce serveur.py" if VERROU is None
         else f"aucune reponse en {BORNE_REFUS:.0f} s"))

    # UN ENTRAINEMENT QUI ECHOUE. C'est le cas qui compte : l'aiguilleur decide
    # de l'intention de CHAQUE demande, et un aiguilleur vide les ferait toutes
    # derailler d'un coup.
    vrai_mesurer = S._mesurer_aiguilleur
    try:
        def echoue():
            raise RuntimeError("corpus introuvable")

        S._mesurer_aiguilleur = echoue
        temoin = S.AIGUILLEUR
        st, d = lire(lancer(S.api_admin_aiguilleur(aig("POST"))))
        dit(st == 500 and "corpus introuvable" in str(d.get("erreur", "")),
            "un entrainement qui echoue rend 500 et dit POURQUOI",
            f"HTTP {st}, {str(d.get('erreur'))[:60]!r}")
        dit(S.AIGUILLEUR is temoin,
            "et l'aiguilleur EN SERVICE est intact : un echec de bouton ne "
            "fait pas derailler les demandes du studio",
            "meme objet qu'avant" if S.AIGUILLEUR is temoin else "remplace")

        # LE VERROU RELACHE. Un verrou reste pris rendrait 409 pour toujours :
        # le bouton serait condamne au moment precis ou l'on veut reessayer, et
        # jusqu'au prochain redemarrage.
        dit(VERROU is not None and not VERROU.locked(),
            "le verrou est relache par l'echec, et non garde",
            f"locked={VERROU.locked() if VERROU is not None else 'pas de verrou'}")

        # UN MODELE ECRIT ILLISIBLE NE LAISSE PAS LE STUDIO SANS AIGUILLEUR.
        # Le rechargement se fait DEPUIS LE DISQUE ; si le fichier local est
        # tronque, charger() retombe sur le modele publie plutot que de rendre
        # None — et onze intentions continuent d'etre reconnues.
        def ecrit_du_charabia():
            with open(MODELE_LOCAL, "w", encoding="utf-8") as f:
                f.write("ceci n'est pas du json")
            return {"exemples": 0, "traits": 0, "classes": {}, "bancs": []}

        S._mesurer_aiguilleur = ecrit_du_charabia
        st, d = lire(lancer(S.api_admin_aiguilleur(aig("POST"))))
        dit(st == 200 and S.AIGUILLEUR is not None
            and S.AIGUILLEUR.classes == {"image": 1},
            "un modele local devenu illisible ne laisse pas le studio sans "
            "aiguilleur : le rechargement retombe sur le modele publie",
            f"HTTP {st}, classes={None if S.AIGUILLEUR is None else S.AIGUILLEUR.classes}")
    finally:
        S._mesurer_aiguilleur = vrai_mesurer
        if os.path.exists(MODELE_LOCAL):
            os.remove(MODELE_LOCAL)

    # ── un entrainement qui echoue APRES l'ecriture ─────────────────────
    # LE VRAI _mesurer_aiguilleur, et c'est la MESURE qu'on casse — pas la
    # fonction entiere comme ci-dessus. Jusqu'au 5 septembre 2026 le modele
    # local etait ecrit AVANT les bancs : une exception dans la mesure rendait
    # 500, la memoire gardait l'ancien, et le disque portait un modele que
    # personne n'avait mesure. charger() le prefere au modele publie : au
    # prochain demarrage, le studio aiguillait avec.
    #
    # On casse classer() sur la CLASSE : mesurer() est la seule etape du
    # reentrainement qui l'appelle — apprendre() et connu() ne s'en servent
    # pas — donc l'entrainement reussit, l'ecriture a lieu ou non, et la
    # mesure tombe. Un temoin reconnaissable dans le fichier local, et l'on
    # exige qu'il y soit encore mot pour mot : « le fichier existe » serait
    # vrai d'un fichier reecrit.
    print("\n  ── un entrainement qui echoue APRES l'ecriture ──")
    TEMOIN_LOCAL = ('{"poids": {"audio": {"jazz": 1}}, "classes": {"audio": 1}, '
                    '"total": {"audio": 1}, "vocabulaire": 1}')
    with open(MODELE_LOCAL, "w", encoding="utf-8") as f:
        f.write(TEMOIN_LOCAL)
    vrai_classer = S._aiguilleur.Aiguilleur.classer

    def classer_casse(self, texte):
        raise RuntimeError("banc casse expres dans la mesure")

    temoin = S.AIGUILLEUR
    try:
        S._aiguilleur.Aiguilleur.classer = classer_casse
        st, d = lire(lancer(S.api_admin_aiguilleur(aig("POST"))))
    finally:
        S._aiguilleur.Aiguilleur.classer = vrai_classer
    try:
        with open(MODELE_LOCAL, encoding="utf-8") as f:
            reste = f.read()
    except OSError:
        reste = "<absent>"
    traces = sorted(n for n in os.listdir(DOSSIER)
                    if n.startswith("local.json") and n != "local.json")
    dit(st == 500 and "casse expres" in str(d.get("erreur", "")),
        "une mesure qui echoue apres l'entrainement rend 500 et dit pourquoi",
        f"HTTP {st}, {str(d.get('erreur'))[:60]!r}")
    dit(reste == TEMOIN_LOCAL,
        "et le modele LOCAL sur le disque n'a pas bouge d'un octet : un modele "
        "que personne n'a mesure ne sera pas celui du prochain demarrage",
        "intact" if reste == TEMOIN_LOCAL else
        ("ABSENT" if reste == "<absent>" else f"REECRIT ({len(reste)} octets)"))
    dit(not traces,
        "et aucun fichier provisoire ne traine a cote du modele local",
        f"traces : {traces or 'aucune'}")
    dit(S.AIGUILLEUR is temoin,
        "et l'aiguilleur en service est toujours le meme objet",
        "meme objet" if S.AIGUILLEUR is temoin else "remplace")
    os.remove(MODELE_LOCAL)

    # ── le vrai reentrainement ──────────────────────────────────────────
    table_rase()
    avant_memoire = S.AIGUILLEUR
    st, d = lire(lancer(S.api_admin_aiguilleur(aig("POST"))))
    dit(st == 200 and d.get("ok") is True and d.get("exemples", 0) > 0
        and d.get("traits", 0) > 0,
        "le bouton reentraine et rend ce qu'il a appris",
        f"HTTP {st}, {d.get('exemples')} exemples, {d.get('traits')} traits")

    # LE MODELE PUBLIE EST DU CODE : IL VOYAGE AVEC LE PAQUET. Gele par
    # PyInstaller il vit dans un dossier temporaire efface a l'arret, et
    # l'ecraser degradait le modele en memoire — « 7 890 traits tombes a
    # 7 680 » — au profit d'un fichier que personne ne relirait.
    with open(MODELE_PUBLIE, encoding="utf-8") as f:
        reste = f.read()
    dit(reste == TEMOIN_PUBLIE,
        "il n'ecrit QUE le modele local : le modele publie est intact, octet "
        "pour octet", "inchange" if reste == TEMOIN_PUBLIE else "REECRIT")
    dit(os.path.exists(MODELE_LOCAL) and os.path.getsize(MODELE_LOCAL) > 0,
        "et le modele local, lui, est bien ecrit",
        f"{os.path.getsize(MODELE_LOCAL) if os.path.exists(MODELE_LOCAL) else 0} octets")

    # « RECHARGE DEPUIS LE DISQUE : le studio doit se servir de ce qui vient
    # d'etre ecrit, pas d'un objet garde en memoire. » Sans ce cas, le bouton
    # afficherait une belle mesure et le studio continuerait d'aiguiller avec
    # le modele d'avant jusqu'au prochain demarrage.
    sur_disque = S._aiguilleur.Aiguilleur.lire(MODELE_LOCAL)
    dit(S.AIGUILLEUR is not avant_memoire
        and S.AIGUILLEUR.vocabulaire == d.get("traits")
        and S.AIGUILLEUR.vocabulaire == sur_disque.vocabulaire
        and S.AIGUILLEUR.classes == sur_disque.classes,
        "le studio se sert AUSSITOT du modele qu'il vient d'ecrire, et c'est "
        "bien celui du disque",
        f"memoire {S.AIGUILLEUR.vocabulaire} traits, disque "
        f"{sur_disque.vocabulaire}, rendu {d.get('traits')}")

    # LA MESURE A COTE DU BOUTON. « Sans elle, on ne saurait pas si le
    # reentrainement a ameliore ou abime quelque chose » — docs. On exige les
    # QUATRE nombres de chaque banc : « justes » mesure le classifieur,
    # « justes_surs / surs » mesure ce qu'on lui laisse trancher seul, et
    # CONTRIBUTING dit que les deux se lisent ensemble.
    bancs = d.get("bancs") or []
    complets = [b for b in bancs
                if {"nom", "justes", "total", "justes_surs", "surs"} <= set(b)
                and b.get("total", 0) > 0 and b.get("surs", 0) > 0]
    dit([b["nom"] for b in bancs] == list(du_maitre("BANCS", ["<aucun banc>"]))
        and len(complets) == len(bancs) and bancs,
        "la reponse porte la mesure, banc par banc, avec les quatre nombres : "
        "sans elle on ne saurait pas si le reentrainement a ameliore ou abime "
        "quelque chose",
        "; ".join(f"{b['nom']} {b['justes']}/{b['total']}, surs "
                  f"{b['justes_surs']}/{b['surs']}" for b in bancs) or "aucun banc")

def _section_4c():
    # CE QUE LE STUDIO APPREND DE L'USAGE, BOUT A BOUT : les deux routes a la
    # suite, comme l'utilisateur puis l'administrateur les empruntent.
    table_rase()
    st, base = lire(lancer(S.api_admin_aiguilleur(aig("POST"))))
    socle = base.get("classes", {}).get("image", 0)

    conv, tour = poser_tour(tid="appris")
    lancer(avis({"tid": "appris", "avis": 1}))
    st, d = lire(lancer(S.api_admin_aiguilleur(aig("POST"))))
    gagne = d.get("classes", {}).get("image", 0) - socle
    # HUIT, ECRIT EN TOUTES LETTRES, ET PAS « POIDS_REEL ». Comparer le gain a
    # la constante qui le produit ne mesure rien : la faire tomber a 1 rendrait
    # le cas vert avec un seul exemplaire. Or c'est exactement le defaut a
    # attraper — « les demandes reelles sont rares et precieuses : on les compte
    # plusieurs fois, sinon trois mille exemples fabriques les noieraient ».
    # Un exemplaire au lieu de huit, et le pouce ne sert plus a rien sans
    # qu'une ligne le dise. Le second membre garde l'accord des deux nombres :
    # si la mesure change, elle se refait, elle ne se contourne pas.
    dit(gagne == 8 and gagne == du_maitre("POIDS_REEL", 0),
        "un tour valide par un pouce en l'air entre dans le corpus, pondere "
        "huit fois",
        f"la classe « image » gagne {gagne} exemplaires, POIDS_REEL vaut "
        f"{du_maitre('POIDS_REEL', 0)}")

    lancer(avis({"tid": "appris", "avis": 0}))
    st, d = lire(lancer(S.api_admin_aiguilleur(aig("POST"))))
    dit(d.get("classes", {}).get("image", 0) == socle,
        "le pouce retire, le studio ne l'apprend plus : un tour « fini » sans "
        "pouce ne prouve rien — le studio a pu se tromper de modalite et "
        "produire quand meme quelque chose",
        f"classe « image » : {d.get('classes', {}).get('image', 0)} contre {socle} au socle")

    socle_audio = d.get("classes", {}).get("audio", 0)
    lancer(avis({"tid": "appris", "avis": -1, "intention": "audio"}))
    st, d = lire(lancer(S.api_admin_aiguilleur(aig("POST"))))
    # LE CAS LE PLUS PRECIEUX : une formulation que le classifieur a DEJA
    # ratee, avec sa bonne reponse. Les deux moities comptent — la bonne classe
    # gagne, et la mauvaise ne gagne rien.
    dit(d.get("classes", {}).get("audio", 0) - socle_audio == 8
        and d.get("classes", {}).get("image", 0) == socle,
        "une correction apprend la BONNE classe sur une demande que "
        "l'aiguilleur avait ratee — et la mauvaise n'y gagne rien",
        f"audio +{d.get('classes', {}).get('audio', 0) - socle_audio}, "
        f"image {d.get('classes', {}).get('image', 0)} contre {socle}")


def _section_5():
    # ══════════════════════════════════════════════════════════════════
    #  5. les deux garde-fous que ces quatre chemins traversent
    # ══════════════════════════════════════════════════════════════════
    passes = []

    async def bidon(req):
        passes.append(req.path)
        return S.web.json_response({"ok": True})

    PIEGE = {"Origin": "http://site-piege.example", "Host": "127.0.0.1:8199"}
    BONNE = {"Origin": "http://127.0.0.1:8199", "Host": "127.0.0.1:8199"}

    refus = []
    for chemin in ("/api/avis", "/api/admin/aiguilleur"):
        del passes[:]
        rep = lancer(S.origine_verifiee(
            Req(entetes=PIEGE, methode="POST", chemin=chemin), bidon))
        refus.append((chemin, rep.status, bool(passes)))
    dit(all(st == 403 and not vu for _, st, vu in refus),
        "un POST venu d'un site tiers n'atteint ni l'avis ni le "
        "reentrainement : le clic d'un piege ne remplace pas le classifieur de "
        "tout le monde",
        ", ".join(f"{c}={st}" for c, st, _ in refus))

    laisses = []
    for chemin in ("/api/avis", "/api/admin/aiguilleur"):
        del passes[:]
        rep = lancer(S.origine_verifiee(
            Req(entetes=BONNE, methode="POST", chemin=chemin), bidon))
        laisses.append((chemin, rep.status, bool(passes)))
    dit(all(st == 200 and vu for _, st, vu in laisses),
        "et l'interface, elle, passe : un garde-fou qui refuse tout n'en est "
        "pas un", ", ".join(f"{c}={st}" for c, st, _ in laisses))

    vrai_auth = S.AUTH
    try:
        S.AUTH = "obligatoire"
        fermes, ouverts = [], []
        for chemin, methode in (("/api/avis", "POST"), ("/api/intentions", "GET")):
            del passes[:]
            rep = lancer(S.exiger_compte(Req(methode=methode, chemin=chemin), bidon))
            fermes.append((chemin, rep.status, bool(passes)))
        for chemin, methode in (("/api/admin/avis", "GET"),
                                ("/api/admin/aiguilleur", "POST")):
            del passes[:]
            rep = lancer(S.exiger_compte(Req(methode=methode, chemin=chemin), bidon))
            ouverts.append((chemin, rep.status, bool(passes)))
        dit(all(st == 401 and not vu for _, st, vu in fermes),
            "en STUDIO_AUTH=obligatoire, ni l'avis ni la liste des intentions "
            "ne s'ouvrent a un visiteur sans compte",
            ", ".join(f"{c}={st}" for c, st, _ in fermes))
        # ET LES DEUX ROUTES D'ADMINISTRATION RESTENT OUVERTES A CE
        # MIDDLEWARE-LA, deliberement : « les fermer ici condamnerait le seul
        # moyen d'entrer quand aucun compte n'existe encore ». Ce n'est pas un
        # trou : admin_ok() les tient, et les cas de la section 4 le mesurent.
        dit(all(st == 200 and vu for _, st, vu in ouverts),
            "tandis que les deux routes d'administration le traversent : c'est "
            "admin_ok() qui les tient, sinon l'amorçage d'une installation "
            "neuve serait condamne",
            ", ".join(f"{c}={st}" for c, st, _ in ouverts))
    finally:
        S.AUTH = vrai_auth


def _section_6():
    # ══════════════════════════════════════════════════════════════════
    #  6. ce banc n'a rien ecrit dans le depot
    # ══════════════════════════════════════════════════════════════════
    apres = {nom: empreinte(os.path.join(S.ICI, nom)) for nom in DEPOT}
    bouges = [n for n in DEPOT if DEPOT[n] != apres[n]]
    dit(not bouges,
        "les trois fichiers que « reentrainer » vise n'ont pas bouge d'un "
        "octet : un banc qui abime le depot qu'il mesure est pire qu'un banc "
        "absent", f"bouges : {bouges or 'aucun'}")

    # ET RIEN N'A VISE LE DEPOT. La ligne au-dessus est vraie grace au detour ;
    # celle-ci demande ce que le detour a detourne. Jusqu'au 5 septembre 2026,
    # chaque POST /api/admin/aiguilleur reecrivait corpus_aiguillage.jsonl a
    # sa place dans l'arbre des sources — un fichier suivi par git, et /app
    # dans l'image en conteneur. Une route HTTP n'a rien a ecrire la. Quatre
    # reentrainements ont tourne dans ce banc : on exige zero ecriture visant
    # ICI, et l'on cite celles qu'il y a eu.
    depot = os.path.abspath(S.ICI) + os.sep
    vers_le_depot = sorted({c for c in ECRITURES_VISEES if c.startswith(depot)})
    dit(not vers_le_depot,
        "et aucune ecriture du reentrainement ne VISAIT l'arbre des sources : "
        "le corpus des gabarits vient du code, pas d'un fichier que la route "
        "reecrirait dans le depot",
        f"visees : {[os.path.basename(c) for c in vers_le_depot] or 'aucune'}"
        f" ({len(ECRITURES_VISEES)} ecriture(s) detournee(s) en tout)")

try:
    section("POST /api/avis — ou va un avis, et a qui il appartient", _section_1)
    section("GET /api/intentions — ce qu'on ose proposer", _section_2)
    section("GET /api/admin/avis — le recapitulatif", _section_3)
    section("/api/admin/aiguilleur — l'etat de l'aiguilleur", _section_4)
    section("reentrainer, et ce qui se passe quand ca rate", _section_4b)
    section("la boucle : un pouce, puis le bouton", _section_4c)
    section("les deux garde-fous que ces quatre chemins traversent", _section_5)
    section("ce banc n'a rien ecrit dans le depot", _section_6)
finally:
    _corpus.ecrire = _vrai_ecrire

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
for x in rate:
    print("    NON :", x)
sys.exit(1 if rate else 0)
