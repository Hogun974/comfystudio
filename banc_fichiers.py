# -*- coding: utf-8 -*-
"""Les trois routes par lesquelles des OCTETS entrent et sortent du studio.

    uv run --with aiohttp python banc_fichiers.py

CE QUI MANQUAIT. Le releve du 5 septembre 2026 compte treize routes qu'aucun
banc n'emprunte, ni par son chemin ni par sa fonction. Ce banc-ci en prend
TROIS, et ce sont celles qui portent des fichiers :

  - GET  /api/noeud/{quoi}  (api_agent_source) sert agent_noeud.py aux machines
    du parc. C'est le CODE QU'ELLES VONT EXECUTER. Rien d'autre du studio n'a
    cette portee : une machine qui recoit le mauvais fichier ici execute le
    mauvais fichier, et toutes le recoivent a la prochaine mise a jour.
  - POST /api/televerser    (api_televerser) accepte ce qu'on lui donne et
    l'ecrit sur le disque du studio.
  - GET  /api/fichier       (api_fichier) ressert ce qui a ete produit, et
    c'est la seule chose qui separe la production d'un utilisateur de celle de
    tous les autres.

CE QU'IL GARDE, dans l'ordre des degats :

  - ON NE SORT PAS DU DOSSIER PREVU, ET PAS PAR LE CHEMIN QU'ON CROIT. Les
    trois routes s'en protegent de TROIS facons differentes, et aucune n'est
    un nettoyage de chaine : api_agent_source ne lit qu'une LISTE BLANCHE
    (SCRIPTS_NOEUD), api_televerser JETTE le nom du client et en tire un
    (studio_<10 hexa><ext>), api_fichier exige que le triplet demande figure
    dans ce que cet utilisateur-la a produit. Le banc mesure les trois, avec
    « .. », un chemin absolu, des separateurs Windows et « %2e%2e ».
  - LE REFUS PRECEDE LE RELAIS. Sur /api/fichier, un fichier qui n'est pas a
    moi doit rendre 404 SANS qu'un seul appel parte vers ComfyUI. Le banc
    compte les appels : « 404 » apres etre alle chercher les octets serait un
    trou de journal, de temps, et un oracle sur ce qui existe chez le voisin.
  - LE PLAFOND EST PAR FAMILLE, ET IL COUPE PENDANT L'ECRITURE. 32 Mio pile
    passent, 32 Mio et un octet sont refuses, et le fichier partiel est
    efface — sinon un envoi de plusieurs gigaoctets remplit le disque avant
    d'etre refuse.
  - LES DEUX LISTES D'EMPAQUETAGE SUIVENT LA TABLE. Un fichier que
    SCRIPTS_NOEUD nomme et que le Dockerfile ou paquet/comfystudio.spec
    n'emporte pas rend « absent du studio » chez l'utilisateur et nulle part
    ailleurs. Ce n'est pas une hypothese : le commentaire de la table raconte
    que /api/noeud/maj_noeud.sh a rendu 404 pendant que la mise a jour des
    agents echouait sans un mot.

CE QU'IL NE VOIT PAS, et il faut l'ecrire :

  - Un vrai ComfyUI. aiohttp.ClientSession est remplace par un temoin : on
    mesure CE QUI PART et CE QUI REVIENT, pas ce que ComfyUI en fait. Ce que
    ComfyUI accepte comme « filename » lui appartient, et le studio le lui
    passe tel quel (voir plus bas).
  - Les plafonds de la video (512 Mio) et du son (64 Mio). Seul celui de
    l'image est mesure par un envoi reel ; les deux autres demanderaient un
    demi-gigaoctet en memoire. Ce que le banc mesure a leur place est plus
    faible et le reste : que le plafond DEPEND de la famille — les memes
    32 Mio et un octet passent en .mp4 et sont refuses en .png.
  - Le vrai routeur. Les fonctions sont appelees en direct, comme dans
    banc_console.py : « %2e%2e » est donc mesure sous ses deux formes, brute
    et decodee, parce que la protection de cette route ne depend d'aucune des
    deux. Ce que le routeur decode avant elle n'est pas mesure ici.
  - Que la page appelle bien ces routes-la. Un seul couplage est tenu : la
    liste « accept » du champ de fichier de web/index.html. Le reste de
    index.html n'est relu par personne pour ces trois routes.

CE QU'IL A TROUVE, ET QUI N'EST PAS CORRIGE (rapporte, pas repare) :

  - api_fichier RELAIE « filename » et « subfolder » A ComfyUI TELS QUELS. Il
    ne cherche ni « .. » ni chemin absolu : sa seule barriere est la liste
    d'autorisation, dont le contenu vient des comptes rendus des machines a
    agent (api_noeud_resultat ne valide pas les noms qu'on lui rend). Le cas
    « le relais porte exactement le triplet autorise » le mesure et le nomme.
  - « X-Content-Type-Options: nosniff » n'est pose que sur la branche du
    DEPOT. La branche du relais sert pourtant, elle aussi, sur l'origine du
    studio — y compris les fichiers televerses (type=input). Le banc ne
    l'exige pas : il ne faut pas qu'ajouter la protection le fasse rougir.

CE QU'IL MESURE, EN CHIFFRES, le 5 septembre 2026 :

  - 50 verifications, 0 rouge sur le depot du jour, 1,3 s.
  - 47 mutations, toutes ROUGES sur la ligne qu'elles nomment ; aucune verte,
    aucune qui casse le banc. 31 rougissent leur ligne et elle SEULE ; les 16
    autres en entrainent une a quatre de plus, et toujours des lignes qui
    gardent la MEME porte — la liste blanche des scripts, la porte de famille
    du televersement, la liste d'autorisation de la relecture. Ces portes sont
    uniques expres : deux refus ecrits a deux endroits se couvriraient l'un
    l'autre.
  - LE SENS INVERSE, par le second chemin : ce banc est ne bien apres les
    trois routes, il n'existe aucun filet d'avant. On lance donc le banc NEUF
    sur le code d'AVANT. Trois depots, et il DISTINGUE les trois au lieu de
    mourir sur l'un d'eux : 811677b 38/12, ff99d10^ 40/10, 1511c35^ 44/6. Les
    douze lignes rouges sont exactement les gardes absentes a ces
    commits-la — origine_verifiee, « nosniff », tous_les_fichiers, le filtre
    des conversations fermees, et les messages qui n'etaient pas encore dans
    le dictionnaire. TREIZE des quarante-sept mutations nomment une de ces
    lignes.
  - CE QUE LE SENS INVERSE NE PEUT PAS MONTRER, et il faut l'ecrire : les
    trente-quatre autres gardent des regles aussi vieilles que le depot. La
    liste blanche SCRIPTS_NOEUD, le nom regenere du televersement et la liste
    d'autorisation de api_fichier sont toutes trois dans le commit initial
    (811677b) : il n'y a pas de « code d'avant » ou les montrer rouges. Ce qui
    porte la preuve pour elles, c'est le sens ALLER et l'exigence de la ligne
    nommee.

CE QU'IL LUI FAUT DANS LE DOSSIER D'ESSAI (BESOINS, banc_mutations.py) :

    "banc_fichiers.py": ["banc_fichiers.py"] + fichiers_du_conteneur() + [
        "paquet/comfystudio.spec", "web/index.html", "agent_noeud.py",
        "noeud.sh", "noeud.bat", "maj_noeud.sh", "maj_noeud.bat",
        "modeles.sh", "zimaos-comfyui.yml", "zimaos-registry.yml",
        "installer.py", "installation.py"]

Il OUVRE ces fichiers : les onze que SCRIPTS_NOEUD nomme (la route les sert
depuis ICI), le Dockerfile et le .spec (les deux empaquetages), web/index.html
(le couplage de « accept »). catalogue.py et le Dockerfile viennent deja de
fichiers_du_conteneur(). Un banc qui ouvre un fichier de plus doit le declarer
la-bas, sinon il ne mesure plus rien dans le dossier d'essai.
"""
import asyncio
import fnmatch
import ast
import io
import json
import os
import re
import sys
import tempfile

import aiohttp
from aiohttp import streams
from aiohttp.base_protocol import BaseProtocol

# TOUT CE QUE LE BANC ECRIT VA DANS UN BAC TEMPORAIRE, et les trois variables
# comptent autant l'une que l'autre. Sans COMFY_ENTREE, api_televerser ecrit
# dans l'input du ComfyUI de la machine qui lance le banc ; sans COMFY_DIR,
# serveur.py va deviner une arborescence a cote du depot.
_BAC = tempfile.mkdtemp(prefix="banc_fichiers_")
for _nom, _var in (("donnees", "STUDIO_DONNEES"), ("comfy", "COMFY_DIR"),
                   ("entree", "COMFY_ENTREE")):
    os.environ[_var] = os.path.join(_BAC, _nom)
    os.makedirs(os.environ[_var], exist_ok=True)
os.environ["STUDIO_AUTH"] = "libre"
ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import serveur as S  # noqa: E402

ok, rate = [], []


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


# ══════════════════════════════════════════════════════════════════════
#  lire le studio SANS mourir s'il lui manque un nom
# ══════════════════════════════════════════════════════════════════════
# UN BANC QUI MEURT SUR LE CODE D'AVANT NE MESURE PAS LE SENS INVERSE. C'est
# la lecon que banc_comptes.py a payee — « TypeError: Comptes.creer() got an
# unexpected keyword argument 'origine' », soixante verifications emportees
# avec lui — et celle de banc_boucle.py, arrete cinq commits sur six sur un
# AttributeError. Mesure du 5 septembre 2026 : ce banc-ci, ecrit en direct,
# mourait sur « module 'serveur' has no attribute 'T' » des qu'on le rejouait
# contre un serveur.py d'avant les traductions (30 aout).
#
# LE DEFAUT EST UN TEMOIN IMPOSSIBLE, JAMAIS LA VALEUR DU JOUR : souffler la
# reponse rendrait le cas VERT au lieu de rouge, et l'on aurait mesure le banc
# au lieu du studio.
_ABSENT = "\x00 ce nom n'existe pas dans ce serveur.py \x00"


def du_studio(nom, defaut):
    return getattr(S, nom, defaut)


def traduire(cle, **valeurs):
    """Le texte francais d'une cle, ou un temoin qu'aucun message n'egale."""
    fonction = du_studio("T", None)
    if fonction is None:
        return _ABSENT + cle
    return fonction(cle, "fr", **valeurs)


FAMILLES = du_studio("FAMILLES", {})
TABLE = du_studio("SCRIPTS_NOEUD", {})
EXT_IMAGE = du_studio("EXT_IMAGE", set())
EXT_DEPOT = du_studio("EXT_DEPOT", set())
ENTREES = du_studio("ENTREES", {})
CONVERSATIONS = du_studio("CONVERSATIONS", {})
REGISTRE = du_studio("REGISTRE", {})
FICHIER_ENTREES = du_studio("FICHIER_ENTREES", os.path.join(_BAC, "sans-registre"))
# Ces deux-la doivent EXISTER, sinon os.listdir et os.makedirs levent avant
# qu'un cas ait pu nommer l'absence. On pose donc un dossier vide du bac.
DOSSIER_ENTREE = du_studio("DOSSIER_ENTREE", os.path.join(_BAC, "sans-entree"))
SORTIES_AGENT = du_studio("SORTIES_AGENT", os.path.join(_BAC, "sans-sorties"))
for _d in (DOSSIER_ENTREE, SORTIES_AGENT):
    os.makedirs(_d, exist_ok=True)


def lire_texte(rel):
    """Un fichier du depot, ou None. Sous try, et le defaut pose un cas nomme.

    Un banc qui meurt sur un fichier absent ne mesure pas le sens inverse :
    c'est la lecon de banc_comptes.py sur le code d'avant, et de
    web/demarrage.html sous try avant lui.
    """
    try:
        with io.open(os.path.join(S.ICI, rel), encoding="utf-8",
                     errors="replace") as f:
            return f.read()
    except OSError:
        return None


# ══════════════════════════════════════════════════════════════════════
#  de quoi appeler les trois routes sans routeur ni reseau
# ══════════════════════════════════════════════════════════════════════
MOI, TOI = "a" * 32, "b" * 32


class Req(dict):
    """Une requete assez complete pour ces trois routes et deux intergiciels.

    « query » pour api_fichier, « match_info » pour api_agent_source,
    « headers » pour le Range et l'origine, « compte » pour la visibilite de
    l'administrateur. La classe est un dict parce que le code lit req["pid"]
    et req.get("compte").
    """

    def __init__(self, query=None, match=None, entetes=None, pid=MOI,
                 compte="", methode="GET", chemin="/"):
        super().__init__(pid=pid, compte=compte)
        self.query = dict(query or {})
        self.match_info = dict(match or {})
        self.headers = dict(entetes or {})
        self.cookies = {}
        self.transport = None
        self.method = methode
        self.path = chemin
        self._lecteur = None

    async def multipart(self):
        return self._lecteur


def corps_multipart(nom_fichier, octets, avec_fichier=True):
    """Un vrai corps multipart, celui qu'un navigateur poste.

    Un faux lecteur qui rendrait tout d'un coup ne traverserait pas la boucle
    de read_chunk(), c'est-a-dire precisement l'endroit ou le plafond coupe.
    On assemble donc de vrais octets et on les fait lire par le
    aiohttp.MultipartReader du studio.
    """
    limite = "----bancfichiers7f3a"
    disp = f'form-data; name="f"; filename="{nom_fichier}"' if avec_fichier \
        else 'form-data; name="f"'
    tete = f"--{limite}\r\nContent-Disposition: {disp}\r\n\r\n".encode()
    return limite, tete + octets + f"\r\n--{limite}--\r\n".encode()


async def lecteur_multipart(nom_fichier, octets, avec_fichier=True):
    limite, corps = corps_multipart(nom_fichier, octets, avec_fichier)
    # « limit » au-dela du corps : en deca, StreamReader met le protocole en
    # pause au lieu d'avaler, et un faux protocole n'a personne pour le
    # reveiller. Ce n'est pas une propriete du studio, c'est la plomberie du
    # banc.
    flux = streams.StreamReader(BaseProtocol(asyncio.get_running_loop()),
                                limit=max(2 ** 16, len(corps) + 4096),
                                loop=asyncio.get_running_loop())
    flux.feed_data(corps)
    flux.feed_eof()
    return aiohttp.MultipartReader(
        {"Content-Type": f"multipart/form-data; boundary={limite}"}, flux)


class Panne:
    """Ce que rend une route qui a leve au lieu de repondre.

    UN BANC QUI MEURT NE MESURE RIEN. C'est la lecon de banc_comptes.py sur le
    code d'avant — « le banc s'est casse au lieu de rougir », et le sens
    inverse ne mesure plus rien. Plusieurs des defauts qu'on imite ici (le
    relais tente vers une machine a agent, un champ sans nom de fichier) font
    lever la route : sans ce filet, ils emporteraient les cinquante
    verifications au lieu d'en rougir une.
    """

    def __init__(self, souci):
        self.status = 500
        self.headers = {}
        self.body = f"la route a leve : {souci}".encode()
        self.text = json.dumps({"erreur": f"la route a leve : {souci}"})


async def televerser(nom_fichier, octets, avec_fichier=True, pid=MOI):
    route = du_studio("api_televerser", None)
    if route is None:
        return 500, {"erreur": "api_televerser n'existe pas dans ce serveur.py"}
    req = Req(pid=pid, methode="POST", chemin="/api/televerser")
    req._lecteur = await lecteur_multipart(nom_fichier, octets, avec_fichier)
    try:
        rep = await route(req)
        return rep.status, json.loads(rep.text)
    except Exception as souci:      # noqa: BLE001 — voir Panne
        return 500, {"erreur": f"la route a leve : {souci}"}


# ── le faux ComfyUI : on mesure ce qui part et ce qui revient ──────────
# api_fichier ouvre une aiohttp.ClientSession vers /view. Sans ce temoin, le
# banc parlerait au ComfyUI de la machine qui le lance — ou a personne, et
# rougirait sur une connexion refusee, ce qui ne dit rien du studio.
RELAIS = []
REPONSE = [None]


class FausseReponse:
    def __init__(self, statut=200, corps=b"", entetes=None):
        self.status = statut
        self._corps = corps
        self.headers = dict(entetes or {})

    async def read(self):
        return self._corps

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False


class FausseSession:
    def __init__(self, *_, **__):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    def get(self, url, params=None, headers=None):
        RELAIS.append({"url": url, "params": dict(params or {}),
                       "entetes": dict(headers or {})})
        return REPONSE[0]


def poser_comfy(statut=200, corps=b"les octets de comfy", entetes=None):
    del RELAIS[:]
    REPONSE[0] = FausseReponse(statut, corps, entetes)


async def demander(pid=MOI, compte="", entetes=None, **query):
    route = du_studio("api_fichier", None)
    if route is None:
        return Panne("api_fichier n'existe pas dans ce serveur.py")
    try:
        return await route(Req(query=query, pid=pid, compte=compte,
                               entetes=entetes, chemin="/api/fichier"))
    except Exception as souci:      # noqa: BLE001 — voir Panne
        return Panne(souci)


def corps_de(rep):
    """Les octets qu'une reponse porte — b"" pour une FileResponse."""
    return rep.body if isinstance(getattr(rep, "body", None), bytes) else b""


def chemin_servi(rep):
    """Le fichier qu'une FileResponse s'apprete a servir, ou None.

    « _path » n'est pas une interface publique d'aiohttp : son absence pose un
    cas nomme (le chemin attendu ne sera pas trouve) plutot qu'une trace de
    pile, parce qu'un banc qui meurt sur une version de bibliotheque ne mesure
    plus rien.
    """
    chemin = getattr(rep, "_path", None)
    return os.path.realpath(str(chemin)) if chemin is not None else None


def dans_le_depot(rel):
    return os.path.realpath(os.path.join(S.ICI, rel))


def conversation(cid, proprio, fichiers, ferme=False):
    CONVERSATIONS[cid] = {"id": cid, "proprietaire": proprio, "ferme": ferme,
                          "tours": [{"id": "t-" + cid, "fichiers": fichiers}]}


def entrees_sur_disque():
    try:
        return sorted(os.listdir(DOSSIER_ENTREE))
    except OSError:
        return []


NOM_ENTREE = re.compile(r"^studio_[0-9a-f]{10}(\.[a-z0-9]+)$")

lancer = asyncio.run
_vraie_session = S.aiohttp.ClientSession
S.aiohttp.ClientSession = FausseSession

try:
    # ══════════════════════════════════════════════════════════════════
    #  1. /api/noeud/{quoi} — le code que les machines vont executer
    # ══════════════════════════════════════════════════════════════════
    print("\n  ── ce que le studio sert aux machines du parc ──")

    async def source(quoi=None):
        route = du_studio("api_agent_source", None)
        if route is None:
            return Panne("api_agent_source n'existe pas dans ce serveur.py")
        try:
            return await route(
                Req(match={} if quoi is None else {"quoi": quoi},
                    chemin="/api/noeud/" + (quoi or "agent")))
        except Exception as souci:      # noqa: BLE001 — voir Panne
            return Panne(souci)

    rep = lancer(source())
    dit(rep.status == 200 and chemin_servi(rep) == dans_le_depot("agent_noeud.py"),
        "l'adresse sans nom sert agent_noeud.py, le code que la machine va "
        "executer", f"HTTP {rep.status}, {chemin_servi(rep)}")
    # « text/plain » ET RIEN D'AUTRE : la route est ouverte a tout le monde et
    # sert sur l'origine du studio. Servi en text/html, un .yml ou un .bat
    # deviendrait une page executee dans la session de qui l'ouvre.
    dit(rep.headers.get("Content-Type") == "text/plain; charset=utf-8",
        "et en texte brut : un navigateur l'affiche, curl l'enregistre",
        str(rep.headers.get("Content-Type")))

    rep_nomme = lancer(source("agent"))
    dit(rep_nomme.status == 200
        and chemin_servi(rep_nomme) == dans_le_depot("agent_noeud.py"),
        "« /api/noeud/agent », nomme, sert le meme fichier que l'adresse nue",
        f"HTTP {rep_nomme.status}")

    # CHAQUE ENTREE DE LA TABLE, ET LE FICHIER QU'ELLE NOMME. Une entree qui
    # designe un fichier disparu ne se voit nulle part ailleurs : la machine
    # recoit « absent du studio » et le studio, lui, ne dit rien.
    manques = []
    for quoi, fichier in sorted(TABLE.items()):
        r = lancer(source(quoi))
        if r.status != 200 or chemin_servi(r) != dans_le_depot(fichier):
            manques.append(f"{quoi}->{fichier} ({r.status})")
    # « >= 8 » ET NON « == 11 » : le nombre est la contre le vide — une table
    # videe rendrait ce cas vrai a vide, exactement le defaut que
    # banc_multilingue a paye. Il n'est pas la pour figer le compte, sinon la
    # mutation qui retire UNE entree rougirait ici au lieu de rougir sur le
    # couplage qu'elle vise.
    dit(not manques and len(TABLE) >= 8,
        "chacun des noms de la table sert EXACTEMENT le fichier qu'elle nomme, "
        "et ce fichier est la", f"{len(TABLE)} noms, "
        + (", ".join(manques) or "aucun manque"))

    # RIEN D'AUTRE QUE LA TABLE. Ces quatre-la sont dans le meme dossier et
    # aucun n'a a sortir : serveur.py est le studio, comptes.py porte la
    # verification des mots de passe, aiguilleur.json et agent_noeud.json sont
    # de la donnee locale.
    hors = []
    for quoi in ("serveur.py", "comptes.py", "aiguilleur.json",
                 "agent_noeud.json", "requirements.txt", ".env", "conversations",
                 "banc_fichiers.py"):
        r = lancer(source(quoi))
        if r.status != 404 or chemin_servi(r) is not None:
            hors.append(f"{quoi}={r.status}")
    dit(not hors,
        "aucun fichier voisin de la table n'est servi, meme present a cote : "
        "la table est une liste blanche, pas un filtre",
        ", ".join(hors) or "8 noms refuses")

    # SORTIR DU DOSSIER. Les six formes, dont les deux separateurs et
    # « %2e%2e » sous sa forme brute ET decodee : la protection de cette route
    # ne depend d'aucune des deux, et c'est ce qu'on mesure.
    fuites = []
    for quoi in ("..", "../serveur.py", "..\\serveur.py", "/etc/passwd",
                 "C:\\Windows\\win.ini", "agent/../serveur.py",
                 "%2e%2e/serveur.py", "..%2fserveur.py", "", "."):
        r = lancer(source(quoi))
        if r.status != 404 or chemin_servi(r) is not None:
            fuites.append(f"{quoi!r}={r.status}")
    dit(not fuites,
        "on ne sort pas du dossier : « .. », un chemin absolu, les deux "
        "separateurs et « %2e%2e » rendent tous 404 sans servir un octet",
        ", ".join(fuites) or "10 formes refusees")

    # LA CASSE COMPTE, et c'est la consequence d'une table plutot que d'un
    # nettoyage : un dict ne connait pas « AGENT ». Le dire, parce que la
    # difference se voit depuis un Windows ou les noms de fichiers, eux, ne la
    # font pas.
    casses = [q for q in ("Agent", "AGENT", "Noeud.sh", "MAJ_NOEUD.SH")
              if lancer(source(q)).status != 404]
    dit(not casses, "la table distingue la casse : « AGENT » n'est pas « agent »",
        ", ".join(casses) or "4 variantes refusees")

    # LES DEUX 404 NE DISENT PAS LA MEME CHOSE, et la difference est tout ce
    # qu'on a pour diagnostiquer : « inconnu » veut dire « ce nom n'existe pas
    # dans la table », « absent du studio » veut dire « la table le nomme mais
    # l'empaquetage ne l'a pas emporte ». Confondus, on cherche du cote du
    # client ce qui manque dans l'image.
    vrai_ici = S.ICI
    S.ICI = os.path.join(_BAC, "studio-vide")
    os.makedirs(S.ICI, exist_ok=True)
    try:
        rep_vide = lancer(source("agent"))
        d_vide = json.loads(rep_vide.text)
    finally:
        S.ICI = vrai_ici
    dit(rep_vide.status == 404 and d_vide.get("erreur") == "absent du studio",
        "un fichier que la table nomme mais que l'empaquetage n'a pas emporte "
        "rend « absent du studio », et non « inconnu »",
        f"HTTP {rep_vide.status}, {d_vide}")
    dit(json.loads(lancer(source("nom-qui-n-existe-pas")).text).get("erreur")
        == "inconnu",
        "tandis qu'un nom que la table ne connait pas rend « inconnu »")

    # ── couplage : ce que les scripts du depot vont VRAIMENT chercher ──
    # C'EST LE DEFAUT QUE LA TABLE RACONTE ELLE-MEME. maj_noeud.sh et
    # maj_noeud.bat etaient copies dans l'image « depuis toujours, avec un
    # commentaire disant que le studio les sert » et n'etaient pas dans la
    # table : /api/noeud/maj_noeud.sh rendait 404 et la mise a jour d'un agent
    # echouait sans que rien ne dise pourquoi. On releve donc les adresses
    # dans les scripts, pas dans une liste ecrite a la main ici.
    servables = set(TABLE)
    source_serveur = lire_texte("serveur.py") or ""
    servables |= set(re.findall(
        r'add_(?:get|post|delete|put)\(\s*"/api/noeud/([^{"/]+)"', source_serveur))
    reclames = {}
    for motif in ("*.sh", "*.bat", "*.py", "*.yml", "web/*.html"):
        for chemin_f in sorted(__import__("glob").glob(
                os.path.join(S.ICI, motif.replace("/", os.sep)))):
            base = os.path.basename(chemin_f)
            if base.startswith(("banc_", "recette_")) or base == "serveur.py":
                continue
            texte = lire_texte(os.path.relpath(chemin_f, S.ICI)) or ""
            for nom in re.findall(r"/api/noeud/([A-Za-z0-9_.-]+)", texte):
                reclames.setdefault(nom, set()).add(base)
    orphelins = {n: sorted(o) for n, o in reclames.items() if n not in servables}
    dit(len(reclames) >= 6 and not orphelins,
        "chaque adresse /api/noeud/<nom> que les scripts du depot vont "
        "chercher est servable — une route nommee ou une entree de la table",
        f"{len(reclames)} adresses relevees, " + (str(orphelins) or "aucun orphelin"))

    # ── couplage : les DEUX empaquetages emportent ce que la table nomme ──
    # Deux listes recopiees a la main, comme les quatre paires min/max de
    # /admin que banc_page.py a laissees deriver. La table est la source ; ces
    # deux-la doivent la couvrir, sinon la route rend « absent du studio » chez
    # l'utilisateur et nulle part ailleurs.
    docker = lire_texte("Dockerfile")
    motifs = []
    for ligne in (docker or "").splitlines():
        nu = ligne.strip()
        if nu.upper().startswith("COPY "):
            morceaux = [m for m in nu.split()[1:] if not m.startswith("--")]
            motifs += morceaux[:-1]
    oublies = sorted(f for f in set(TABLE.values())
                     if not any(fnmatch.fnmatch(f, m) for m in motifs))
    dit(docker is not None and motifs and not oublies,
        "le Dockerfile emporte les onze fichiers que la table nomme",
        "Dockerfile illisible" if docker is None
        else (", ".join(oublies) or f"{len(motifs)} motifs de COPY"))

    spec = lire_texte(os.path.join("paquet", "comfystudio.spec"))
    # LES LIGNES DE COMMENTAIRE SONT ECARTEES D'ABORD, et ce n'est pas un
    # raffinement : le .spec est commente en francais, et chaque apostrophe de
    # « l'executable » ou « d'un » se fait prendre pour une quote ouvrante par
    # un releve naif. Mesure : sans ce filtre, maj_noeud.sh et maj_noeud.bat —
    # qui SONT dans le fichier — n'etaient pas trouves, et ce cas rougissait
    # sur un defaut du banc.
    lignes_utiles = [l for l in (spec or "").splitlines()
                     if not l.lstrip().startswith("#")]
    cites = set(re.findall(r"[\"']([^\"'\n]{1,200})[\"']",
                           "\n".join(lignes_utiles)))
    absents = sorted(f for f in set(TABLE.values()) if f not in cites)
    dit(spec is not None and not absents,
        "et paquet/comfystudio.spec aussi : l'executable Windows sert les "
        "memes fichiers que l'image",
        "spec illisible" if spec is None
        else (", ".join(absents) or f"{len(set(TABLE.values()))} fichiers"))

    # ══════════════════════════════════════════════════════════════════
    #  2. POST /api/televerser — ce que le studio accepte
    # ══════════════════════════════════════════════════════════════════
    print("\n  ── ce que le televersement accepte, et ce qu'il refuse ──")

    st, d = lancer(televerser("", b"du texte", avec_fichier=False))
    dit(st == 400 and d.get("erreur") == traduire("erreur.aucun_fichier"),
        "un champ de formulaire sans fichier est refuse, et le dit dans la "
        "langue de la requete", f"HTTP {st}, {d.get('erreur')}")

    ACCEPTEES = sorted(e for x, _ in FAMILLES.values() for e in x)
    refus, mauvais = [], []
    for ext in ACCEPTEES:
        octets = ("les octets de " + ext).encode()
        st, d = lancer(televerser("photo-de-vacances" + ext, octets))
        nom = d.get("image", "")
        chemin = os.path.join(DOSSIER_ENTREE, nom)
        if st != 200 or d.get("octets") != len(octets):
            refus.append(f"{ext}={st}")
            continue
        marque = NOM_ENTREE.match(nom)
        if not marque or marque.group(1) != ext or not os.path.exists(chemin) \
                or io.open(chemin, "rb").read() != octets:
            mauvais.append(f"{ext}->{nom}")
    dit(not refus and not mauvais and len(ACCEPTEES) == 15,
        "les quinze extensions des trois familles sont acceptees, et les "
        "octets recus sont EXACTEMENT ceux ecrits sur le disque",
        ", ".join(refus + mauvais) or f"{len(ACCEPTEES)} extensions")

    st, d = lancer(televerser("PHOTO.PNG", b"majuscules"))
    dit(st == 200 and d.get("image", "").endswith(".png"),
        "une extension en majuscules est reconnue, et rangee en minuscules",
        str(d.get("image")))

    # LE NOM DU CLIENT EST JETE, ET C'EST TOUTE LA PROTECTION. Il n'y a aucun
    # nettoyage de « .. » dans cette route : le nom est REGENERE, seule
    # l'extension survit. On mesure donc l'endroit ou le fichier atterrit,
    # chemin resolu, et non la forme du nom rendu.
    dedans = os.path.realpath(DOSSIER_ENTREE)
    sorties, gardes = [], []
    for nom_client in ("../../evil.png", "..\\..\\evil.png", "/etc/passwd.png",
                       "C:\\Windows\\System32\\evil.png", "%2e%2e/evil.png",
                       "dossier/sous/evil.png", "....//evil.png"):
        st, d = lancer(televerser(nom_client, b"charge utile"))
        nom = d.get("image", "")
        pose = os.path.realpath(os.path.join(DOSSIER_ENTREE, nom))
        if st != 200 or not NOM_ENTREE.match(nom):
            gardes.append(f"{nom_client!r}={st}/{nom}")
        if os.path.dirname(pose) != dedans or not os.path.exists(pose):
            sorties.append(f"{nom_client!r}->{pose}")
        if "evil" in nom or "passwd" in nom:
            gardes.append(f"{nom_client!r} a garde son nom : {nom}")
    dit(not sorties and not gardes,
        "un nom de fichier qui remonte, absolu, ou avec des separateurs des "
        "deux mondes n'ecrit rien hors du dossier d'entree : le nom du client "
        "est JETE, seule l'extension survit",
        ", ".join(sorties + gardes) or "7 formes rangees dans le dossier")

    avant = len(entrees_sur_disque())
    formats, textes = [], []
    for nom_client, ext_attendue in (("note.txt", ".txt"), ("outil.exe", ".exe"),
                                     ("livre.pdf", ".pdf"), ("maillage.glb", ".glb"),
                                     ("archive.tar.gz", ".gz"),
                                     ("photo.png.exe", ".exe")):
        st, d = lancer(televerser(nom_client, b"charge utile"))
        attendu = traduire("erreur.format_refuse", extension=ext_attendue,
                      acceptes=", ".join(ACCEPTEES))
        if st != 400:
            formats.append(f"{nom_client}={st}")
        if d.get("erreur") != attendu:
            textes.append(f"{nom_client}: {d.get('erreur')}")
    dit(not formats and not textes,
        "un format hors des trois familles est refuse en 400, et le refus "
        "nomme l'extension vue ET la liste entiere des acceptees",
        ", ".join(formats + textes) or "6 formats refuses")
    dit(len(entrees_sur_disque()) == avant,
        "et rien n'a ete ecrit : le refus tombe avant l'ouverture du fichier",
        f"{avant} entrees avant, {len(entrees_sur_disque())} apres")

    st, d = lancer(televerser("pieuvre", b"charge utile"))
    dit(st == 400 and d.get("erreur") == traduire(
        "erreur.format_refuse", extension=traduire("erreur.sans_extension"),
        acceptes=", ".join(ACCEPTEES)),
        "un fichier sans extension le dit en toutes lettres, traduit, et non "
        "par un blanc au milieu de la phrase", str(d.get("erreur"))[:70])

    # « .gif » EST REFUSE ICI ET ACCEPTE AU DEPOT, et c'est delibere : le
    # commentaire de EXT_DEPOT dit qu'un gif joint en ENTREE serait lu par
    # LoadImage qui n'en prendrait que la premiere image, alors qu'une machine
    # qui fait de l'animation en PRODUIT. Sans ce cas, unifier les deux listes
    # « pour simplifier » ne se verrait pas.
    st, d = lancer(televerser("anime.gif", b"GIF89a"))
    dit(st == 400 and ".gif" in EXT_DEPOT and ".gif" not in EXT_IMAGE,
        "« .gif » est refuse a l'entree alors qu'une machine a agent a le "
        "droit d'en DEPOSER : les deux listes ne sont pas la meme",
        f"HTTP {st}")

    print("\n  ── le plafond, et l'endroit ou il coupe ──")
    PILE = 32 * 1024 ** 2
    avant = len(entrees_sur_disque())
    st, d = lancer(televerser("juste-a-la-limite.png", b"x" * PILE))
    dit(st == 200 and d.get("octets") == PILE,
        "32 Mio pile passent : le plafond de l'image vaut exactement "
        "33 554 432 octets", f"HTTP {st}, {d.get('octets')} octets")
    st, d = lancer(televerser("un-octet-de-trop.png", b"x" * (PILE + 1)))
    dit(st == 413 and d.get("erreur") == traduire(
        "erreur.fichier_trop_lourd", famille=traduire("famille.image"),
        mega=32),
        "un octet de plus est refuse en 413, et le refus nomme la famille "
        "traduite et le plafond en Mo", f"HTTP {st}, {d.get('erreur')}")
    dit(len(entrees_sur_disque()) == avant + 1,
        "et le fichier partiel est EFFACE : on coupe pendant l'ecriture, "
        "sinon plusieurs gigaoctets remplissent le disque avant le refus",
        f"{avant} entrees avant, {len(entrees_sur_disque())} apres (une seule "
        f"de plus, celle qui est passee)")

    # LE PLAFOND DEPEND DE LA FAMILLE. Mesure faible mais reelle : les memes
    # 32 Mio et un octet passent en .mp4. Les plafonds de la video et du son
    # ne sont pas mesures a leur valeur — un demi-gigaoctet en memoire.
    st, d = lancer(televerser("meme-taille.mp4", b"x" * (PILE + 1)))
    dit(st == 200 and d.get("octets") == PILE + 1,
        "les memes 32 Mio et un octet passent en .mp4 : le plafond est par "
        "FAMILLE, pas un plafond unique", f"HTTP {st}")

    avant = len(entrees_sur_disque())
    st, d = lancer(televerser("rien.png", b""))
    dit(st == 400 and d.get("erreur") == traduire("erreur.fichier_vide")
        and len(entrees_sur_disque()) == avant,
        "un fichier vide est refuse, et ne laisse pas un fichier vide derriere "
        "lui", f"HTTP {st}, {d.get('erreur')}")

    print("\n  ── a qui appartient ce qui vient d'entrer ──")
    st, d = lancer(televerser("a-moi.png", b"les octets de MOI", pid=MOI))
    mien = d.get("image")
    dit(ENTREES.get(mien) == MOI,
        "le studio retient QUI a televerse : sans cela, l'auteur ne peut plus "
        "relire sa propre piece jointe", f"{mien} -> {ENTREES.get(mien)}")
    try:
        with io.open(FICHIER_ENTREES, encoding="utf-8") as f:
            sur_disque = json.load(f)
    except (OSError, ValueError):
        sur_disque = {}
    dit(sur_disque.get(mien) == MOI,
        "et il l'ECRIT dans _entrees.json : en memoire seule, un studio "
        "relance ne reconnait plus ces fichiers, ne les purge plus jamais, et "
        "l'input de ComfyUI gonfle a chaque redemarrage",
        os.path.basename(FICHIER_ENTREES))

    # LA PURGE EST PAR UTILISATEUR, et le commentaire de purger_entrees dit
    # pourquoi : globale, un visiteur qui televerse en rafale effacait le
    # fichier d'entree d'un autre dont la tache attendait encore son tour. On
    # ne compte que des nombres : l'ordre depend des dates de fichiers, donc de
    # la resolution de l'horloge de la machine.
    for f in entrees_sur_disque():
        os.remove(os.path.join(DOSSIER_ENTREE, f))
    ENTREES.clear()
    for i in range(6):
        lancer(televerser(f"toi-{i}.png", b"a toi", pid=TOI))
    for i in range(41):
        lancer(televerser(f"moi-{i}.png", b"a moi", pid=MOI))
    restants = entrees_sur_disque()
    a_moi = [f for f in restants if ENTREES.get(f) == MOI]
    a_toi = [f for f in restants if ENTREES.get(f) == TOI]
    dit(len(a_moi) == 40 and len(a_toi) == 6,
        "la purge est PAR UTILISATEUR : quarante-et-un envois n'en laissent "
        "que quarante a leur auteur, et n'entament pas les six du voisin",
        f"{len(a_moi)} a moi, {len(a_toi)} au voisin")

    # ── couplage : ce que la page propose et ce que le studio accepte ──
    page = lire_texte(os.path.join("web", "index.html"))
    trouve = re.search(r'<input type="file" id="img"\s*\n?\s*accept="([^"]+)"',
                       page or "")
    propose = sorted(x.strip().lower() for x in trouve.group(1).split(",")) \
        if trouve else []
    dit(propose == ACCEPTEES,
        "le champ « joindre un fichier » de la page propose EXACTEMENT les "
        "quinze extensions que le studio accepte — ni une de plus, qui serait "
        "refusee apres le temps de l'envoi, ni une de moins, qui serait "
        "indisponible sans raison",
        "web/index.html illisible" if page is None
        else f"page {len(propose)}, studio {len(ACCEPTEES)}, "
             f"ecart {sorted(set(propose) ^ set(ACCEPTEES))}")

    # ══════════════════════════════════════════════════════════════════
    #  3. GET /api/fichier — ce que le studio ressert, et a qui
    # ══════════════════════════════════════════════════════════════════
    print("\n  ── ce que le studio ressert, et a qui ──")
    # « local » EST UN TEMOIN IMPOSSIBLE ICI AUSSI : sur un serveur.py qui
    # n'aurait pas noeud_local(), tous les triplets porteraient un identifiant
    # que noeud() ne connait pas, et les cas rougiraient — ce qui est la
    # verite, et non un vert souffle.
    _local = du_studio("noeud_local", None)
    LOCAL = _local()["id"] if _local else "pas-de-noeud-local"
    conversation("c-moi", MOI, [{"filename": "moi_00001_.png", "subfolder": "",
                                 "noeud": LOCAL}])
    conversation("c-toi", TOI, [{"filename": "toi_00002_.png", "subfolder": "",
                                 "noeud": LOCAL}])
    conversation("c-ferme", MOI, [{"filename": "ferme_00003_.png",
                                   "subfolder": "", "noeud": LOCAL}], ferme=True)

    poser_comfy(200, b"les octets de comfy",
                {"Content-Type": "image/png", "Content-Length": "19"})
    rep = lancer(demander(filename="moi_00001_.png"))
    dit(rep.status == 200 and corps_de(rep) == b"les octets de comfy"
        and len(RELAIS) == 1
        and RELAIS[0]["url"].endswith("/view")
        and RELAIS[0]["params"] == {"filename": "moi_00001_.png",
                                    "subfolder": "", "type": "output"},
        "ce que J'AI produit m'est resservi, relaye vers /view de ma machine, "
        "et le relais ne porte que le triplet autorise",
        f"HTTP {rep.status}, {RELAIS}")

    # LE CAS QUI FAIT TOUT LE RESTE, ET LA DOCSTRING LE RACONTE : « ComfyUI
    # numerote ses sorties en sequence (_00011_, _00012_), il suffisait
    # d'incrementer le compteur pour lire la production de tout le monde ».
    # ZERO APPEL, et non pas seulement 404 : un refus rendu APRES etre alle
    # chercher les octets serait un oracle sur ce qui existe chez le voisin, et
    # ferait porter le cout du vol a la machine qui calcule.
    refuses = []
    for quoi, query in (("celui d'un autre", {"filename": "toi_00002_.png"}),
                        ("une conversation fermee",
                         {"filename": "ferme_00003_.png"}),
                        ("un compteur incremente",
                         {"filename": "moi_00002_.png"}),
                        ("un nom vide", {}),
                        ("un sous-dossier invente",
                         {"filename": "moi_00001_.png", "subfolder": "prive"}),
                        ("une machine inconnue",
                         {"filename": "moi_00001_.png", "noeud": "pas-la"}),
                        ("un type que ComfyUI connait pourtant",
                         {"filename": "moi_00001_.png", "type": "temp"})):
        poser_comfy()
        rep = lancer(demander(**query))
        if rep.status != 404 or RELAIS or corps_de(rep) != b'{"erreur": "inconnu"}':
            refuses.append(f"{quoi}={rep.status}/{len(RELAIS)} appel(s)")
    dit(not refuses,
        "sept demandes qui ne sont pas a moi rendent 404 SANS qu'un seul appel "
        "parte vers ComfyUI : le refus precede le relais",
        ", ".join(refuses) or "7 refus, 0 appel")

    # LE DEPOT D'UNE MACHINE A AGENT, SERVI DU DISQUE. Le studio n'a pas
    # l'adresse d'un agent : s'il tentait le relais, url_de() leverait et la
    # route rendrait 500 au lieu de 404.
    REGISTRE["zima"] = {"id": "zima", "titre": "zima", "jeton": "jeton-zima"}
    depot = os.path.join(SORTIES_AGENT, "zima")
    os.makedirs(depot, exist_ok=True)
    with io.open(os.path.join(depot, "rendu.png"), "wb") as f:
        f.write(b"les octets du depot")
    with io.open(os.path.join(depot, "pas-a-moi.png"), "wb") as f:
        f.write(b"SECRET DU VOISIN")
    conversation("c-zima", MOI, [{"filename": "rendu.png", "subfolder": "",
                                  "noeud": "zima"}])
    poser_comfy()
    rep = lancer(demander(filename="rendu.png", noeud="zima"))
    dit(rep.status == 200 and not RELAIS
        and chemin_servi(rep) == os.path.realpath(
            os.path.join(depot, "rendu.png")),
        "un depot de machine a agent est servi DU DISQUE, sans relais : le "
        "studio n'a pas l'adresse d'un agent, un relais rendrait 500",
        f"HTTP {rep.status}, {len(RELAIS)} appel(s)")
    dit(rep.headers.get("X-Content-Type-Options") == "nosniff",
        "et avec « nosniff » : ces octets viennent d'ailleurs et sont servis "
        "sur l'origine du studio, donc dans la session de l'utilisateur",
        str(rep.headers.get("X-Content-Type-Options")))

    poser_comfy()
    rep = lancer(demander(filename="pas-a-moi.png", noeud="zima"))
    dit(rep.status == 404 and not RELAIS
        and b"SECRET" not in corps_de(rep) and chemin_servi(rep) is None,
        "un fichier POSE SUR LE DISQUE mais absent de mes conversations n'est "
        "pas servi : c'est la liste d'autorisation qui decide, pas la presence",
        f"HTTP {rep.status}")

    conversation("c-perdu", MOI, [{"filename": "envole.png", "subfolder": "",
                                   "noeud": "zima"}])
    poser_comfy()
    rep = lancer(demander(filename="envole.png", noeud="zima"))
    dit(rep.status == 404 and not RELAIS,
        "un depot d'agent qui n'est plus la rend 404, et surtout n'essaie "
        "aucun relais", f"HTTP {rep.status}, {len(RELAIS)} appel(s)")

    print("\n  ── ce que le relais propage, et ce qu'il retient ──")
    # LE RANGE EST TOUTE LA DIFFERENCE ENTRE UNE VIDEO QU'ON PARCOURT ET UNE
    # VIDEO QU'ON SUBIT. Sans lui, le navigateur ne peut pas sauter, et la
    # docstring de la route le dit.
    poser_comfy(206, b"morceau", {"Content-Type": "video/mp4",
                                  "Content-Range": "bytes 0-6/100",
                                  "Content-Length": "7",
                                  "Accept-Ranges": "bytes",
                                  "Set-Cookie": "session=celle-de-comfy",
                                  "X-Bavard": "ne doit pas traverser"})
    rep = lancer(demander(filename="moi_00001_.png",
                          entetes={"Range": "bytes=0-6"}))
    dit(RELAIS and RELAIS[0]["entetes"] == {"Range": "bytes=0-6"},
        "le Range demande par le navigateur part tel quel vers ComfyUI, et lui "
        "seul", str(RELAIS[0]["entetes"]) if RELAIS else "aucun appel")
    dit(rep.status == 206 and rep.headers.get("Content-Range") == "bytes 0-6/100",
        "le 206 revient 206, avec son Content-Range : un 200 a la place, et le "
        "navigateur croit tenir la video entiere", f"HTTP {rep.status}")
    # LES QUATRE, ET RIEN D'AUTRE. « Set-Cookie » est l'exemple qui compte :
    # un ComfyUI qui en pose un le poserait sur l'origine DU STUDIO.
    passes = {h for h in ("Content-Type", "Content-Length", "Accept-Ranges",
                          "Content-Range", "Set-Cookie", "X-Bavard")
              if h in rep.headers}
    dit(passes == {"Content-Type", "Content-Length", "Accept-Ranges",
                   "Content-Range"},
        "seuls les quatre en-tetes nommes traversent : un Set-Cookie de "
        "ComfyUI se poserait sur l'origine du studio", str(sorted(passes)))

    poser_comfy(200, b"une image sans en-tetes", {})
    rep = lancer(demander(filename="moi_00001_.png"))
    dit(rep.headers.get("Accept-Ranges") == "bytes",
        "« Accept-Ranges: bytes » est pose meme quand ComfyUI se tait : sans "
        "lui le navigateur ne demandera jamais de morceau",
        str(rep.headers.get("Accept-Ranges")))

    poser_comfy(404, b"introuvable chez comfy", {})
    rep = lancer(demander(filename="moi_00001_.png"))
    dit(rep.status == 404 and corps_de(rep) == b"introuvable chez comfy",
        "le statut de ComfyUI est propage tel quel : un 404 de sa part reste "
        "un 404, et non un 200 vide", f"HTTP {rep.status}")

    # CE QUE LE STUDIO NE NETTOIE PAS, ET IL FAUT LE MESURER POUR LE SAVOIR.
    # api_fichier ne cherche ni « .. » ni chemin absolu dans « filename » : sa
    # SEULE barriere est la liste d'autorisation. Un nom qui y figure part vers
    # ComfyUI tel quel, et ce cas est ce qui empeche ce fait de changer sans
    # qu'on le voie.
    #
    # LA MOITIE QUI MANQUAIT EST FERMEE DEPUIS LE 5 SEPTEMBRE 2026, et c'est
    # l'autre bout de la chaine : le contenu de cette liste vient des comptes
    # rendus des machines a agent, et api_noeud_resultat ne les validait pas.
    # Un noeud pouvait donc FABRIQUER l'entree que cette route relaie ensuite.
    # fichiers_rendus() ferme cette porte-la — voir la section suivante — et
    # celle-ci reste ouverte a dessein : deux barrieres qui se recouvrent se
    # couvrent l'une l'autre, et l'on ne peut plus faire rougir ni l'une ni
    # l'autre.
    conversation("c-torve", MOI, [{"filename": "../../serveur.py",
                                   "subfolder": "..", "noeud": LOCAL}])
    poser_comfy(200, b"peu importe", {})
    rep = lancer(demander(filename="../../serveur.py", subfolder=".."))
    dit(len(RELAIS) == 1
        and RELAIS[0]["params"] == {"filename": "../../serveur.py",
                                    "subfolder": "..", "type": "output"},
        "un « .. » ADMIS DANS LA LISTE part vers ComfyUI tel quel : le studio "
        "ne nettoie pas les chemins qu'il relaie, la liste est sa seule "
        "barriere — mesure, et rapporte", str(RELAIS[0]["params"] if RELAIS else None))

    print("\n  ── ce qu'une machine a le droit de RAPPORTER ──")
    # LA SOURCE DE LA LISTE D'AUTORISATION. Les noms qu'un agent rend entrent
    # dans le tour, donc dans la liste que la route ci-dessus relaie a ComfyUI.
    # Tant que rien ne les validait, une machine du parc — ou quelqu'un ayant
    # pris son jeton — pouvait fabriquer le chemin qu'elle voulait voir servi.
    #
    # Une machine a carte est precisement ce qu'on installe chez soi et qu'on
    # oublie. Le studio n'a aucune raison de lui accorder plus que ce qu'elle
    # doit rendre : un nom de fichier et un sous-dossier.
    TORDUS = [
        ("../../serveur.py", "", "un chemin qui remonte"),
        ("sortie.png", "..", "un sous-dossier qui remonte"),
        ("a/b.png", "", "un separateur POSIX dans le nom"),
        ("a" + chr(92) + "b.png", "", "un separateur Windows dans le nom"),
        ("/etc/passwd", "", "un chemin absolu POSIX"),
        ("C:" + chr(92) + "Windows" + chr(92) + "win.ini", "", "un chemin absolu Windows"),
        ("sortie.png", "a/../..", "un « .. » cache au milieu du sous-dossier"),
        ("", "", "un nom vide"),
        (".", "", "un point tout seul"),
    ]
    refuses = []
    for nom, sous, quoi in TORDUS:
        garde = S.fichiers_rendus([{"filename": nom, "subfolder": sous}], "pc")
        if garde:
            refuses.append(quoi)
    dit(not refuses,
        f"les {len(TORDUS)} formes tordues sont TOUTES jetees : un rendu est un "
        f"nom, pas un chemin",
        ", ".join(refuses) or "aucune ne passe")

    # LE TEMOIN, sans lequel le cas du dessus serait vrai d'un filtre qui jette
    # tout — et un studio qui ne sert plus aucune image passerait pour sur.
    droits = S.fichiers_rendus(
        [{"filename": "sortie_00001_.png", "subfolder": ""},
         {"filename": "clip.mp4", "subfolder": "u/video"}], "pc")
    dit(len(droits) == 2,
        "alors qu'un nom normal, avec ou sans sous-dossier, passe : le filtre "
        "ne jette pas tout", f"{len(droits)} sur 2")

    # ON JETTE, ON NE CORRIGE PAS. Retirer les « .. » et garder le reste
    # laisserait passer un nom qu'on aurait fabrique soi-meme, et le journal ne
    # montrerait rien d'anormal. Un rendu refuse se voit.
    melange = S.fichiers_rendus(
        [{"filename": "bon.png", "subfolder": ""},
         {"filename": "../mauvais.png", "subfolder": ""}], "pc")
    dit([f["filename"] for f in melange] == ["bon.png"],
        "le mauvais est JETE et le bon garde : on ne corrige pas un nom, on le "
        "refuse", str([f.get("filename") for f in melange]))

    # ET LA ROUTE S'EN SERT VRAIMENT. Le filtre pourrait exister sans etre
    # appele : c'est le defaut le plus facile a ecrire, et le seul que le banc
    # ne verrait pas s'il ne mesurait que la fonction.
    _arbre = ast.parse(io.open(os.path.join(ICI, "serveur.py"),
                               encoding="utf-8").read())
    # LE SOL EST PRIS PAR LE HAUT, et non route par route. La premiere ecriture
    # de ce cas ne regardait que api_noeud_resultat et manquait la seconde
    # entree : rattacher_tardif() est une fonction VOISINE, pas une imbriquee.
    # La deuxieme ratissait tout le fichier et accusait soumettre_a_agent(),
    # qui lit le resultat DEJA filtre rendu par le futur.
    #
    # La bonne frontiere est celle-ci : les fonctions qui authentifient une
    # MACHINE — celles qui appellent noeud_du_jeton() — plus rattacher_tardif,
    # qui recoit leur corps. Ce sont les seules ou « d » est ce qu'un agent a
    # envoye. Le jour ou une troisieme route de noeud lira « fichiers » sans
    # filtrer, ce cas la reclamera.
    def _lit_le_corps(fn):
        return [n for n in ast.walk(fn)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "get" and n.args
                and isinstance(n.args[0], ast.Constant)
                and n.args[0].value == "fichiers"
                and isinstance(n.func.value, ast.Name)
                and n.func.value.id == "d"]

    _nus, _gardees = [], 0
    for _fn in ast.walk(_arbre):
        if not isinstance(_fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if ("noeud_du_jeton" not in ast.unparse(_fn)
                and _fn.name != "rattacher_tardif"):
            continue
        _filtres = [n for n in ast.walk(_fn)
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                    and n.func.id == "fichiers_rendus"]
        _sous = {id(a) for f in _filtres for a in ast.walk(f) if a is not f}
        for _lu in _lit_le_corps(_fn):
            if id(_lu) in _sous:
                _gardees += 1
            else:
                _nus.append((_fn.name, _lu.lineno))
    dit(_gardees >= 2 and not _nus,
        "dans les routes qui authentifient une MACHINE, aucune liste de "
        "fichiers rendue n'atteint un tour sans passer par le filtre",
        f"{_gardees} lecture(s) gardee(s), {len(_nus)} nue(s)"
        + (" : " + ", ".join(f"{n} l.{l}" for n, l in _nus) if _nus else ""))

    print("\n  ── qui a le droit ──")
    import comptes as _comptes  # noqa: E402
    S.COMPTES = _comptes.Comptes(os.path.join(_BAC, "_comptes.json"),
                                 b"secret-de-session-du-banc")
    S.COMPTES.creer("chef", "un-mot-de-passe-assez-long", admin=True)
    S.COMPTES.creer("simple", "un-mot-de-passe-assez-long")
    poser_comfy(200, b"vu par l'administrateur", {})
    rep = lancer(demander(filename="toi_00002_.png", compte="chef"))
    dit(rep.status == 200 and corps_de(rep) == b"vu par l'administrateur",
        "un administrateur relit la production de tout le monde : il voit deja "
        "les conversations depuis sa console", f"HTTP {rep.status}")
    poser_comfy()
    rep = lancer(demander(filename="toi_00002_.png", compte="simple"))
    dit(rep.status == 404 and not RELAIS,
        "un compte ORDINAIRE, lui, ne voit rien de plus qu'un visiteur : ce "
        "n'est pas « etre connecte » qui ouvre, c'est « etre administrateur »",
        f"HTTP {rep.status}")
    poser_comfy()
    rep = lancer(demander(filename="ferme_00003_.png", compte="chef"))
    dit(rep.status == 404 and not RELAIS,
        "et meme lui ne rouvre pas une conversation FERMEE : elle attend son "
        "effacement, elle n'est plus a personne", f"HTTP {rep.status}")

    # BOUT A BOUT, ET C'EST LE SEUL CAS QUI RELIE LES DEUX ROUTES. Ce que A a
    # televerse, A doit pouvoir le relire — c'est ce que promet la derniere
    # ligne de mes_fichiers() — et B ne le doit pas.
    st, d = lancer(televerser("ma-piece-jointe.png", b"ma piece jointe", pid=MOI))
    jointe = d.get("image")
    poser_comfy(200, b"ma piece jointe", {"Content-Type": "image/png"})
    rep = lancer(demander(filename=jointe, type="input", pid=MOI))
    dit(st == 200 and rep.status == 200 and len(RELAIS) == 1
        and RELAIS[0]["params"]["type"] == "input",
        "ce que J'AI televerse, je le relis par /api/fichier?type=input : les "
        "deux routes se tiennent, l'une depose et l'autre ressert",
        f"HTTP {rep.status}")
    poser_comfy()
    rep = lancer(demander(filename=jointe, type="input", pid=TOI))
    dit(rep.status == 404 and not RELAIS,
        "et le voisin ne le relit pas, alors que le fichier est bien la : "
        "ENTREES retient un PROPRIETAIRE, pas seulement un nom",
        f"HTTP {rep.status}")

    # LES INTERGICIELS, PARCE QUE C'EST LA QUE VIT LA GARDE. Les trois routes
    # ne verifient rien elles-memes : origine_verifiee et exiger_compte le font
    # pour elles, et c'est la forme « qui ne s'oublie pas a la prochaine route
    # ajoutee ». Un banc qui appelle les fonctions en direct ne les traverse
    # pas — on les appelle donc, elles aussi.
    async def suite(_):
        return S.web.json_response({"passe": True})

    async def par(nom, req):
        """L'intergiciel nomme, ou une Panne : son absence est un cas rouge."""
        milieu = du_studio(nom, None)
        if milieu is None:
            return Panne(f"{nom} n'existe pas dans ce serveur.py")
        try:
            return await milieu(req, suite)
        except Exception as souci:      # noqa: BLE001
            return Panne(souci)

    vrai_auth = du_studio("AUTH", "libre")
    S.AUTH = "obligatoire"
    try:
        fermees = []
        for chemin, methode in (("/api/televerser", "POST"),
                                ("/api/fichier", "GET")):
            rep = lancer(par("exiger_compte",
                              Req(methode=methode, chemin=chemin)))
            corps = json.loads(rep.text) if isinstance(
                getattr(rep, "text", None), str) else {}
            if rep.status != 401 or not corps.get("connexion"):
                fermees.append(f"{methode} {chemin}={rep.status}")
        dit(not fermees,
            "connexion obligatoire : le televersement et la relecture sont "
            "fermes a un visiteur sans compte, et le refus porte le champ "
            "« connexion » que la page attend", ", ".join(fermees) or "2 refus 401")

        # ET LA TROISIEME EST OUVERTE EXPRES. SECURITY.md le dit en toutes
        # lettres : c'est ce qui permet d'installer une machine neuve qui n'a
        # encore aucun jeton. La consequence y est ecrite aussi — qui s'intercale
        # sur le reseau choisit le code qui tournera sur chaque machine. Le cas
        # est ici pour que la fermer un jour soit une DECISION et non un effet
        # de bord.
        ouvertes = []
        for chemin in ("/api/noeud/agent", "/api/noeud/noeud.sh",
                       "/api/noeud/maj_noeud.sh"):
            rep = lancer(par("exiger_compte", Req(chemin=chemin)))
            if rep.status != 200:
                ouvertes.append(f"{chemin}={rep.status}")
        dit(not ouvertes,
            "tandis que le service des scripts reste OUVERT sans compte, "
            "delibere : une machine neuve n'a encore aucun jeton",
            ", ".join(ouvertes) or "3 adresses ouvertes")
    finally:
        S.AUTH = vrai_auth

    piege = {"Origin": "http://site-piege.example", "Host": "127.0.0.1:8199"}
    rep = lancer(par("origine_verifiee",
                     Req(methode="POST", chemin="/api/televerser",
                         entetes=piege)))
    dit(rep.status == 403,
        "un televersement poste depuis un site tiers est refuse : le "
        "formulaire partirait du navigateur de l'utilisateur, donc avec ses "
        "cookies", f"HTTP {rep.status}")
    rep = lancer(par("origine_verifiee",
                     Req(methode="POST", chemin="/api/televerser",
                         entetes={"Origin": "http://127.0.0.1:8199",
                                  "Host": "127.0.0.1:8199"})))
    dit(rep.status == 200,
        "et le meme envoi depuis l'interface passe : c'est l'origine qui est "
        "jugee, pas la methode", f"HTTP {rep.status}")
finally:
    S.aiohttp.ClientSession = _vraie_session

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
for x in rate:
    print("    NON :", x)
sys.exit(1 if rate else 0)
