# -*- coding: utf-8 -*-
"""Les cles d'acces : ce qu'un programme presente au studio pour agir au nom
d'un compte.

POURQUOI CE MODULE EXISTE. Un workflow n8n, un agent IA branche par MCP, un
script curl ne remplissent pas un formulaire de connexion et ne gardent pas de
cookie. Leur donner le mot de passe du compte serait leur donner le compte
entier — changer ce mot de passe, armer le second facteur, supprimer
l'historique — pour un besoin qui tient en deux gestes : demander un rendu, le
relire. Une cle d'acces est ce perimetre etroit, nomme, revocable une par une,
sans toucher au mot de passe ni aux autres programmes.

  Forme : « cs_ » + 8 hex (l'identifiant PUBLIC) + « _ » + 43 caracteres
  urlsafe (le SECRET, secrets.token_urlsafe(32), soit 256 bits).

L'identifiant sert a TROUVER la fiche, l'empreinte a la PROUVER. Le prefixe
« cs_ » n'est pas une coquetterie : c'est ce qui permet a un scanner de secrets
(celui de GitHub, gitleaks) de reconnaitre une cle collee par megarde dans un
depot ou un journal, et a un humain de savoir d'un coup d'oeil a quel service
elle appartient.

POURQUOI A LA MAIN. Il n'y a rien a importer : sha256, hmac, secrets et json
sont dans la bibliotheque standard, et le studio doit demarrer sur un NAS sans
pip. Le fichier se lit en entier, ce qui est la seule facon de savoir ce qu'une
cle permet.

CE QUE CE MODULE NE FAIT PAS.

  - Il ne DECIDE RIEN de ce qu'une cle a le droit de faire. Il rend la fiche ;
    serveur.py applique le perimetre (rendus seulement, jamais
    l'administration), les plafonds « en_file », « par_jour » et
    « par_jour_familles », et la permission du nuage. Une cle ne vaut JAMAIS administration, et ce n'est pas
    ici que cela se garantit : c'est dans la route qui la lit.
  - Il n'envoie aucun rappel : rappels.py le fait, en signant avec le secret
    que secret_rappel() lui rend, vers un hote que la fiche declare.
  - Il ne sait pas si un lien signe designe un fichier qui existe encore, ni si
    la cle qui l'a signe vit toujours : lien_valide() ne controle que la
    signature et la date, le studio verifie le reste.
  - Il ne prend aucun verrou. Le studio tourne sur UNE boucle aiohttp, et
    aucune methode ici n'attend : rien ne s'intercale entre une lecture et une
    ecriture du magasin.
"""
import hashlib
import hmac
import ipaddress
import json
import os
import re
import secrets
import time

PREFIXE = "cs_"

# LA FORME EXACTE, ET RIEN D'AUTRE. Huit hex minuscules : secrets.token_hex(4),
# assez pour ne jamais trouver deux identifiants egaux parmi les quelques
# dizaines de cles d'un studio familial (et creer() retire au sort si cela
# arrive). Quarante-trois caracteres : ce que token_urlsafe(32) produit, 32
# octets en base64 urlsafe sans remplissage. Une cle tronquee d'un caractere
# n'a plus 256 bits, elle n'a plus la forme, et on ne la cherche meme pas.
_FORME = re.compile(r"cs_([0-9a-f]{8})_([A-Za-z0-9_-]{43})")

# L'empreinte qu'on compare quand l'identifiant ne designe aucune fiche. Elle
# ne correspond a aucune cle (une empreinte sha256 de 64 zeros demanderait une
# preimage), et elle existe pour que le chronometre ne separe pas « identifiant
# inconnu » de « secret faux » — voir reconnaitre().
_EMPREINTE_FACTICE = "0" * 64

# UNE ETIQUETTE, PAS UNE DESCRIPTION : « n8n maison », « agent du salon ».
# Quarante caracteres tiennent dans une ligne de la page des reglages sans la
# casser, et un nom plus long se lit comme un champ ou l'on aurait colle autre
# chose — la cle elle-meme, souvent.
NOM_MAX = 40

# VINGT CLES PAR COMPTE. Un compte a besoin d'une cle par programme qu'il
# branche, et personne n'en branche vingt. La borne existe pour qu'un script
# qui cree une cle a chaque lancement — l'erreur classique d'un workflow mal
# ecrit — bute sur un refus nomme au lieu de faire grossir le fichier sans fin.
CLES_PAR_COMPTE = 20

# DIX HOTES DE RAPPEL. Un programme rappelle d'un endroit, deux s'il a une
# instance de secours ; dix couvre tout usage honnete. Au-dela, la liste
# ressemble a un balayage du reseau local par rappels interposes, ce que la
# liste est justement la pour empecher.
HOTES_MAX = 10

# RENDUS EN FILE EN MEME TEMPS POUR UNE CLE. Quatre : un workflow n8n qui lance
# un lot en parallele n'en lance pas plus utilement, puisque la carte les
# traite un par un. Vingt au plus : au-dela, une seule cle occuperait la file
# de tout le studio pendant des heures, et les humains derriere attendraient
# un programme.
EN_FILE_DEFAUT = 4
EN_FILE_MAX = 20

# RENDUS PAR JOUR. Zero veut dire « sans plafond » — c'est le defaut, parce que
# le proprietaire du studio est souvent le proprietaire du programme. Dix mille
# au plus : un rendu toutes les neuf secondes, jour et nuit, ce qui depasse
# deja ce qu'une carte produit ; un chiffre plus grand n'est pas un plafond.
PAR_JOUR_MAX = 10000

# UNE DATE DE FIN, SI L'ON VEUT. Zero jour veut dire « sans fin » — le defaut,
# parce qu'une cle qui meurt en silence au bout de trois mois casse le
# workflow qu'elle servait sans que personne ne regarde. Mais une cle donnee a
# un essai, a une demonstration, a l'assistant d'un invite n'a pas a rester
# ouverte apres : elle se ferme seule, avec ses liens signes et ses rappels.
# Un an au plus : au-dela, ce n'est plus une date de fin, c'est un oubli.
# Les durees proposees par la page ; le serveur accepte tout entier borne.
EXPIRE_JOURS_MAX = 365
EXPIRATIONS = (0, 7, 30, 90, 365)


# RENOUVELER, SANS COUPURE. Un secret qu'on croit vu — colle dans un ticket,
# affiche sur un ecran partage — se change ; mais le changer d'un coup casse le
# workflow tant qu'on n'a pas recopie le neuf. L'ancien secret vaut donc encore
# un jour : le temps d'ouvrir n8n, pas celui d'oublier. Le MEME identifiant :
# les rendus, les conversations, les liens signes, les plafonds et le secret de
# rappel suivent la cle — seul le secret d'acces change.
GRACE_RENOUVELLEMENT = 24 * 3600

# CE QU'UNE CLE PEUT FAIRE. Une cle branchee sur un workflow de detourage n'a
# aucune raison de pouvoir lancer une video de huit minutes : volee, elle ne
# doit ouvrir que ce qu'elle servait. Huit familles et non les treize types du
# catalogue : c'est le mot que lit le proprietaire en cochant, et « retoucher
# le fond » sans « retoucher le sujet » n'est une frontiere pour personne.
# Une liste vide veut dire « tout », le defaut, et les familles qu'on ajoutera
# un jour avec — une cle d'avant n'a pas a se fermer a ce qu'elle ignorait.
OPERATIONS = ("image", "retouche", "video", "audio", "agrandir", "detourer",
              "objet3d", "lecture")

# Le type d'un moteur (CATALOGUE[...]["type"]) ou l'intention d'un plan, vers
# sa famille. Un type ABSENT d'ici n'a pas de famille : operation_permise() le
# refuse a une cle restreinte. Un moteur ajoute au catalogue sans passer par
# cette table reste ferme aux cles qui ont choisi — la faute se voit, elle ne
# s'ouvre pas.
FAMILLES = {
    "image": "image", "planche": "image",
    "edition": "retouche", "retoucher_fond": "retouche",
    "retoucher_sujet": "retouche", "retoucher_zone": "retouche",
    "video": "video", "video_image": "video", "fluidifier": "video",
    "audio": "audio", "agrandir": "agrandir", "detourer": "detourer",
    "objet3d": "objet3d", "lecture": "lecture",
}

# Ni l'une ni l'autre ne produit rien : une question demande une precision, un
# refus n'a rien rendu. Les fermer a une cle restreinte la ferait echouer la
# ou le studio voulait seulement lui parler.
SANS_RENDU = ("question", "refus")


def operations_valides(operations):
    """La liste des familles d'une cle, dans l'ordre d'OPERATIONS. Leve
    ErreurAcces sur autre chose qu'une liste de familles connues.

    None ou [] : toutes. L'ordre est celui d'OPERATIONS et non celui de la
    requete, pour que deux cles qui permettent la meme chose se lisent pareil
    dans la liste.
    """
    if operations is None:
        return []
    if isinstance(operations, (str, bytes)) or not isinstance(operations, (list, tuple)):
        # Une chaine seule serait parcourue lettre par lettre.
        raise ErreurAcces("operations : une liste parmi " + ", ".join(OPERATIONS),
                          cle="erreur.acces_operations",
                          familles=", ".join(OPERATIONS))
    for o in operations:
        if not isinstance(o, str) or o not in OPERATIONS:
            raise ErreurAcces("operations : une liste parmi " + ", ".join(OPERATIONS),
                              cle="erreur.acces_operations",
                              familles=", ".join(OPERATIONS))
    return [o for o in OPERATIONS if o in operations]


def par_jour_familles_valides(plafonds):
    """Les plafonds du jour par famille d'une cle, {famille: rendus}, dans
    l'ordre d'OPERATIONS. Leve ErreurAcces sur autre chose qu'un objet de
    familles connues vers des entiers de 0 a PAR_JOUR_MAX.

    POURQUOI PAR FAMILLE. Un detourage prend deux secondes de carte, une video
    huit minutes : un seul « par_jour » assez large pour cinquante detourages
    laisse passer cinquante videos — une nuit de carte prise par un workflow
    emballe. « 50 detourages et 5 videos par jour » ne s'ecrivait pas. Les
    deux plafonds s'appliquent : celui du jour compte tout, celui-ci une
    famille.

    None ou {} : aucun plafond de plus que « par_jour ». Un zero veut dire
    « sans plafond » pour cette famille, comme pour « par_jour » — la page
    envoie une case par famille, et une case laissee a 0 n'est pas un plafond
    de zero rendu. Il ne reste donc pas dans la fiche : « video: 0 » et
    l'absence de « video » se lisent pareil, ils s'ecrivent pareil.
    """
    if plafonds is None:
        return {}
    refus = ErreurAcces("par_jour_familles : un objet {famille: rendus par "
                        "jour}, familles parmi " + ", ".join(OPERATIONS),
                        cle="erreur.acces_par_jour_familles",
                        familles=", ".join(OPERATIONS), bas=0,
                        haut=PAR_JOUR_MAX)
    # Un dict et rien d'autre : une liste de paires ou une chaine JSON collee
    # telle quelle seraient lues de travers plutot que refusees.
    if not isinstance(plafonds, dict):
        raise refus
    for f, n in plafonds.items():
        if (not isinstance(f, str) or f not in OPERATIONS
                or isinstance(n, bool) or not isinstance(n, int)
                or not 0 <= n <= PAR_JOUR_MAX):
            raise refus
    return {f: plafonds[f] for f in OPERATIONS if plafonds.get(f)}


def _plafonds_lisibles(p):
    """Les plafonds par famille relus du disque ont la forme d'un droit."""
    return p is None or (isinstance(p, dict) and all(
        isinstance(f, str) and f in OPERATIONS and isinstance(n, int)
        and not isinstance(n, bool) and 0 <= n <= PAR_JOUR_MAX
        for f, n in p.items()))


def famille(type_):
    """La famille d'un type de moteur ou d'une intention, ou None."""
    return FAMILLES.get(type_) if isinstance(type_, str) else None


def operation_permise(operations, type_):
    """Une cle qui permet « operations » peut-elle faire « type_ » ?

    « operations » est la liste de la fiche (vide : tout). Prend la liste et
    non la fiche : la tache en garde une copie sur sa marque, qui survit au
    redemarrage comme le droit au nuage.
    """
    if not operations:
        return True
    if type_ in SANS_RENDU:
        return True
    f = famille(type_)
    return f is not None and f in operations


def expiree(fiche, maintenant=None):
    """Vrai si la fiche porte une date de fin, et qu'elle est passee."""
    fin = (fiche or {}).get("expire")
    if fin is None:
        return False
    return (time.time() if maintenant is None else maintenant) >= fin


# « vu » N'EST ECRIT SUR DISQUE QU'UNE FOIS PAR DIX MINUTES ET PAR CLE. Un n8n
# qui interroge l'etat d'un rendu chaque seconde reecrirait sinon le fichier
# chaque seconde — sur la carte SD ou le disque d'un NAS, et pour une
# information dont personne n'a besoin a la seconde pres : « utilisee il y a
# cinq minutes » suffit a reconnaitre une cle morte d'une cle vivante.
VU_ECRIT_TOUTES = 600

# LE SUIVI D'UNE CLE : ses refus du jour, par code, et les secrets faux
# presentes sous son identifiant. C'est ce que le proprietaire regarde quand un
# workflow « ne marche plus » — refuse pour plafond, pour une operation qu'on
# lui a fermee — ou quand quelqu'un essaie une cle qui n'est pas la sienne.
#
# SUR LE DISQUE, MAIS PAS A CHAQUE REQUETE. Un compteur qui repartirait a zero
# a chaque redemarrage mentirait au moment exact ou l'on s'en sert : on
# redemarre le studio APRES l'ennui, et « 0 refus aujourd'hui » effacerait les
# deux cents du matin. Mais ce n'est pas un plafond : rien n'est refuse sur sa
# foi, et en perdre quelques minutes ne rouvre rien. Il s'ecrit donc avec la
# meme retenue que « vu » — au plus une fois par dix minutes pour tout le
# magasin, et a l'arret propre du studio (vider_suivi) : un n8n refuse en
# boucle dix fois par seconde ne reecrit pas le fichier dix fois par seconde,
# et une coupure de courant perd au plus dix minutes de comptes.
SUIVI_ECRIT_TOUTES = VU_ECRIT_TOUTES

# Un code est un mot du dictionnaire sans sa famille (« cle_file_pleine ») ;
# autre chose devient « autre ». Vingt-quatre codes distincts par jour au plus :
# le dictionnaire en a une quarantaine de possibles pour un lancement, et une
# cle n'en rencontre jamais plus d'une poignee. La borne est la pour qu'un
# code fabrique ne fasse pas grossir la fiche sans fin.
SUIVI_CODES_MAX = 24
_CODE_SUIVI = re.compile(r"[a-z0-9_]{1,48}")

# Un nom DNS complet ne depasse pas 253 caracteres (RFC 1035, 2.3.4) ; une
# etiquette, 63. Au-dela, ce n'est pas un hote, c'est un texte colle.
_HOTE_MAX = 253
_NOM_HOTE = re.compile(
    r"([a-z0-9_-]{1,63}(?:\.[a-z0-9_-]{1,63})*)(?::([0-9]{1,5}))?")
_HOTE_V6 = re.compile(r"\[([0-9a-f:.]+)\](?::([0-9]{1,5}))?")

# Les champs d'un lien signe. Le rang est le numero du fichier dans le rendu :
# cent au plus, un rendu n'en produit jamais autant. Les formes sont
# CANONIQUES — pas de zero de tete — pour qu'un meme lien n'ait qu'une seule
# ecriture : « rang=07 » et « rang=7 » seraient sinon deux jetons pour une
# seule signature a deviner.
_LIEN = re.compile(r"([0-9a-f]{8})\.([0-9a-f]{32})\.(0|[1-9][0-9]?)"
                   r"\.(0|[1-9][0-9]{0,11})\.([0-9a-f]{32})")


class ErreurAcces(ValueError):
    """Refus explicable : nom vide, hote invalide, borne depassee…

    « cle » nomme la phrase au dictionnaire (traductions.py), « valeurs » ce
    qu'elle interpole : le serveur la rend dans la langue du lecteur. str(e)
    reste la phrase francaise, pour le journal et pour les refus que personne
    ne lit hors du code (compte manquant, lien hors forme) — ceux-la n'ont
    pas de cle. Meme mecanisme que les marques de panne du serveur.
    """

    def __init__(self, message, cle="", **valeurs):
        super().__init__(message)
        self.cle = cle
        self.valeurs = valeurs


def empreinte_de(cle):
    """sha256 de la cle entiere, en hex.

    SHA256 ET NON SCRYPT, et ce n'est pas l'oubli qu'on croit. scrypt protege
    un MOT DE PASSE, qu'un humain choisit et qu'un dictionnaire devine : sa
    lenteur est ce qui rend le parcours couteux. Une cle d'acces a 256 bits
    tires par secrets ; il n'y a pas de dictionnaire, et parcourir 2**256
    possibilites est hors de portee quelle que soit la vitesse du condensat.
    Et un scrypt PAR REQUETE (~50 ms, 64 Mio dans comptes.py) donnerait a
    n'importe qui un moyen de geler la boucle d'evenements du studio en
    envoyant des cles fausses a la chaine.
    """
    return hashlib.sha256(cle.encode("utf-8")).hexdigest()


def identifiant_de(cle):
    """Les 8 hex de la cle si sa FORME est exacte, sinon None. Ne leve jamais."""
    if not isinstance(cle, str):
        return None
    # fullmatch et non match : une cle suivie d'un saut de ligne ou d'un
    # morceau d'en-tete colle avec n'est pas la cle.
    m = _FORME.fullmatch(cle)
    return m.group(1) if m else None


def hote_valide(texte):
    """Un hote de rappel declare, normalise en minuscules, ou None.

    UN HOTE, PAS UNE URL. « n8n.maison », « 172.20.1.50:5678 »,
    « [::1]:5678 ». Ce qu'on refuse, on le refuse parce que rappels.py
    compare l'hote de l'URL de rappel a cette liste : un schema, un chemin ou
    des identifiants (« user@hote ») glisses ici feraient une liste qui ne se
    compare plus a rien — ou, pire, a autre chose que ce que l'humain a cru
    declarer.
    """
    if not isinstance(texte, str) or not texte or len(texte) > _HOTE_MAX:
        return None
    # ASCII AVANT LES MINUSCULES. « K » (le signe kelvin) devient un « k »
    # ASCII une fois passe par lower() : l'hote declare ne serait plus celui
    # qu'on a lu. Un nom internationalise s'ecrit en punycode (« xn--… »).
    if not texte.isascii():
        return None
    # UNE GRAMMAIRE QUI DIT CE QUI PASSE, pas une liste de ce qui ne passe pas.
    # « / », « @ », « ? », les espaces, « http: » n'ont pas besoin d'etre
    # nommes : aucun n'est dans l'alphabet d'un nom d'hote, et le prochain
    # caractere dangereux auquel personne n'aura pense n'y sera pas non plus.
    propre = texte.lower()
    m = _HOTE_V6.fullmatch(propre)
    if m:
        try:
            # La forme comprimee : « [0:0::1] » et « [::1] » sont le meme hote,
            # et la liste ne doit en garder qu'une ecriture.
            nom = "[" + ipaddress.IPv6Address(m.group(1)).compressed + "]"
        except ValueError:
            return None
    else:
        m = _NOM_HOTE.fullmatch(propre)
        if not m:
            return None
        nom = m.group(1)
    port = m.group(2)
    if port is None:
        return nom
    if not 1 <= int(port) <= 65535:
        return None
    return f"{nom}:{int(port)}"


def _entier(valeur, bas, haut, quoi, cle=""):
    """Un entier dans [bas, haut], ou ErreurAcces. bool n'est pas un entier ici :
    « en_file=True » est une faute de frappe, pas une file d'un rendu.

    Une cle PAR CHAMP, et non un gabarit « {champ} : … » : le nom du champ est
    une demi-phrase francaise, et la glisser dans une phrase anglaise ferait du
    franglais (docs/qui-prend-le-travail.md, « pas de sous-phrase »)."""
    if isinstance(valeur, bool) or not isinstance(valeur, int):
        raise ErreurAcces(f"{quoi} : un nombre entier", cle=cle, bas=bas, haut=haut)
    if not bas <= valeur <= haut:
        raise ErreurAcces(f"{quoi} : entre {bas} et {haut}", cle=cle, bas=bas, haut=haut)
    return valeur


def _jour(quand):
    """La date du studio, heure locale : le meme minuit que le plafond par_jour."""
    return time.strftime("%Y-%m-%d", time.localtime(quand))


def _instant(v):
    return v is None or (isinstance(v, (int, float)) and not isinstance(v, bool))


def _suivi_valide(s):
    """Le suivi relu du disque a la forme attendue."""
    return (isinstance(s, dict) and isinstance(s.get("jour"), str)
            and isinstance(s.get("refus"), dict)
            and len(s["refus"]) <= SUIVI_CODES_MAX
            and all(isinstance(k, str) and isinstance(n, int)
                    and not isinstance(n, bool) and n >= 0
                    for k, n in s["refus"].items())
            and isinstance(s.get("echecs"), int) and not isinstance(s["echecs"], bool)
            and s["echecs"] >= 0
            and _instant(s.get("dernier_refus")) and _instant(s.get("dernier_echec"))
            and (s.get("dernier_code") is None or isinstance(s["dernier_code"], str)))


def _ancienne_valable(fiche, empreinte, quand):
    """L'empreinte presentee est celle d'avant un renouvellement, encore dans
    sa grace. Compare toujours, meme sans fiche ni ancien secret."""
    ancienne = (fiche or {}).get("empreinte_ancienne") or _EMPREINTE_FACTICE
    egale = hmac.compare_digest(empreinte, ancienne)
    return bool(fiche and fiche.get("empreinte_ancienne") and egale
                and quand < (fiche.get("ancienne_jusqu") or 0))


class Acces:
    """Le magasin des cles d'acces, sur disque (_acces.json)."""

    def __init__(self, chemin):
        self.chemin = chemin
        self.fiches = {}
        self.illisible = False
        # Ce qui est SUR LE DISQUE pour « vu », cle par cle : c'est a lui que se
        # mesure l'intervalle de VU_ECRIT_TOUTES, pas a la valeur en memoire
        # qui avance a chaque requete.
        self._vu_ecrit = {}
        # Le suivi a change depuis la derniere ecriture, et quand elle a eu
        # lieu : voir SUIVI_ECRIT_TOUTES.
        self._suivi_sale = False
        self._suivi_ecrit = float("-inf")
        self.charger()

    # ── disque ───────────────────────────────────────────────────────────
    def charger(self):
        """Relit le fichier. Absent : magasin vide. Illisible : magasin vide ET
        verrouille en ecriture — voir sauver()."""
        self.fiches, self._vu_ecrit, self.illisible = {}, {}, False
        self._suivi_sale = False
        try:
            with open(self.chemin, encoding="utf-8") as f:
                brut = json.load(f)
            fiches = {}
            for x in brut:
                # Une fiche a laquelle il manque un champ attendu vaut fichier
                # illisible : la garder a moitie ferait reconnaitre une cle dont
                # on ne sait plus la generation, ou en perdre une en silence.
                if not (isinstance(x["id"], str) and isinstance(x["compte"], str)
                        and isinstance(x["empreinte"], str)
                        and isinstance(x["secret_rappel"], str)
                        and isinstance(x["generation"], int)
                        and isinstance(x["hotes"], list)
                        # Absente des fiches d'avant : « sans fin ».
                        and (x.get("expire") is None
                             or (isinstance(x["expire"], (int, float))
                                 and not isinstance(x["expire"], bool)))
                        # Le secret d'avant un renouvellement, et sa fin.
                        and (x.get("empreinte_ancienne") is None
                             or (isinstance(x["empreinte_ancienne"], str)
                                 and isinstance(x.get("ancienne_jusqu"), (int, float))
                                 and not isinstance(x["ancienne_jusqu"], bool)))
                        # Ce que la cle peut faire. Absente : tout. Une liste
                        # abimee vaut fichier illisible, et non « tout » : lire
                        # une restriction cassee comme une absence de
                        # restriction ouvrirait la cle qu'on avait fermee.
                        and (x.get("operations") is None
                             or (isinstance(x["operations"], list)
                                 and all(isinstance(o, str) and o in OPERATIONS
                                         for o in x["operations"])))
                        # Les plafonds par famille : meme regle. Un plafond
                        # abime lu comme « aucun » rouvrirait les cinquante
                        # videos qu'on avait bornees a cinq.
                        and _plafonds_lisibles(x.get("par_jour_familles"))):
                    raise ValueError(f"fiche mal formee : {x.get('id')!r}")
                fiches[x["id"]] = x
        except FileNotFoundError:
            return
        except Exception as e:
            # UN FICHIER ILLISIBLE NE S'ECRASE PAS. Le garder vide en memoire et
            # le reecrire au premier creer() effacerait les cles de TOUS les
            # comptes — chaque n8n branche se mettrait a recevoir des 401 sans
            # que rien ne dise pourquoi, et le fichier qui l'aurait explique
            # n'existerait plus. On le dit, on n'y touche pas, et aucune cle
            # n'est reconnue tant qu'un humain ne l'a pas repare.
            print(f"cles d'acces illisibles ({type(e).__name__}: {e}) — le "
                  f"fichier est garde tel quel, aucune cle n'est reconnue et "
                  f"aucune ne peut etre creee", flush=True)
            self.illisible = True
            return
        # Les secrets d'avant un renouvellement dont la grace est passee : rien
        # ne les accepte plus, leur empreinte n'a pas a rester au fichier. Le
        # menage se fait ici, au chargement ; la prochaine ecriture l'enregistre.
        maintenant = time.time()
        for f in fiches.values():
            if f.get("empreinte_ancienne") and (f.get("ancienne_jusqu") or 0) <= maintenant:
                f.pop("empreinte_ancienne", None)
                f.pop("ancienne_jusqu", None)
            # UN SUIVI ABIME SE PERD, IL NE REND PAS LE FICHIER ILLISIBLE. A
            # l'inverse d'« operations », ce n'est pas un droit : c'est une
            # observation. Lui sacrifier toutes les cles du studio pour un
            # compteur casse serait payer tres cher un chiffre qu'on refait
            # demain matin.
            if "suivi" in f and not _suivi_valide(f["suivi"]):
                f.pop("suivi", None)
        self.fiches = fiches
        for ident, f in fiches.items():
            if f.get("vu") is not None:
                self._vu_ecrit[ident] = f["vu"]

    def sauver(self):
        """Ecriture atomique, et REFUS si le fichier lu etait illisible.

        LE REFUS EST ICI ET NULLE PART AILLEURS. Toute ecriture du magasin passe
        par cette methode — creer(), revoquer(), la date de dernier usage — et
        une garde posee dans chacune aurait fini par manquer a la prochaine.
        """
        if self.illisible:
            raise ErreurAcces("le fichier des cles d'acces est illisible : le "
                              "studio refuse de l'ecraser, reparez-le d'abord",
                              cle="erreur.acces_illisible")
        tmp = self.chemin + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(list(self.fiches.values()), f, ensure_ascii=False,
                          indent=1)
            try:
                os.chmod(tmp, 0o600)      # sans effet sur Windows, utile ailleurs
            except OSError:
                pass
            # os.replace et non une ecriture en place : un studio coupe au
            # milieu laisserait sinon un fichier a moitie ecrit, c'est-a-dire
            # illisible, c'est-a-dire toutes les cles mortes au redemarrage.
            os.replace(tmp, self.chemin)
            # Toute ecriture emporte le suivi avec le reste : celle de « vu »
            # comme celle d'une cle neuve.
            self._suivi_sale = False
        except BaseException:
            try:
                os.remove(tmp)
            except OSError:
                pass
            raise

    # ── cles ─────────────────────────────────────────────────────────────
    def creer(self, compte, nom, generation, *, nuage=False, hotes=(),
              en_file=EN_FILE_DEFAUT, par_jour=0, expire_jours=0,
              operations=None, par_jour_familles=None, maintenant=None):
        """Une cle neuve. Rend {"cle", "secret_rappel", "fiche"}.

        LA CLE ET LE SECRET DE RAPPEL SONT MONTRES UNE FOIS, ICI. Le studio ne
        garde de la cle que son empreinte : perdue, elle se revoque et se
        refait, elle ne se relit pas. L'interface doit le dire, comme pour les
        codes de secours du second facteur.

        « generation » est celle du compte A CET INSTANT (comptes.py,
        _generation) ; voir reconnaitre() pour ce qu'elle ferme.
        """
        # EN MINUSCULES, parce que comptes.py indexe ses comptes ainsi : « Jordan »
        # et « jordan » sont un seul compte, et doivent avoir une seule liste de
        # cles — sinon revoquer_compte("jordan") laisserait vivre celles creees
        # sous « Jordan ».
        compte = (compte if isinstance(compte, str) else "").strip().lower()
        if not compte:
            raise ErreurAcces("compte manquant")
        nom = (nom if isinstance(nom, str) else "").strip()
        if not nom:
            raise ErreurAcces("nom de la cle : il en faut un, pour la "
                              "reconnaitre dans la liste",
                              cle="erreur.acces_nom_vide")
        if len(nom) > NOM_MAX:
            raise ErreurAcces(f"nom de la cle : {NOM_MAX} caracteres au plus",
                              cle="erreur.acces_nom_long", maxi=NOM_MAX)
        # Un saut de ligne ou un caractere de controle dans une etiquette casse
        # la ligne de journal qui la cite, et peut y fabriquer une fausse ligne.
        if not nom.isprintable():
            raise ErreurAcces("nom de la cle : des caracteres imprimables "
                              "seulement", cle="erreur.acces_nom_imprimable")
        if isinstance(generation, bool) or not isinstance(generation, int):
            raise ErreurAcces("generation du compte : un nombre entier")
        if isinstance(hotes, (str, bytes)):
            # Une chaine seule serait parcourue caractere par caractere : « n8n »
            # deviendrait trois hotes d'une lettre.
            raise ErreurAcces("hotes de rappel : une liste, pas une chaine",
                              cle="erreur.acces_hotes_liste")
        try:
            hotes = list(hotes)
        except TypeError:
            raise ErreurAcces("hotes de rappel : une liste",
                              cle="erreur.acces_hotes_liste") from None
        if len(hotes) > HOTES_MAX:
            raise ErreurAcces(f"hotes de rappel : {HOTES_MAX} au plus",
                              cle="erreur.acces_hotes_trop", maxi=HOTES_MAX)
        propres = []
        for h in hotes:
            p = hote_valide(h)
            if p is None:
                raise ErreurAcces(f"hote de rappel invalide : {h!r} — un nom ou "
                                  f"une adresse, avec un port si besoin, sans "
                                  f"http:// ni chemin",
                                  cle="erreur.acces_hote_invalide", hote=str(h)[:80])
            if p not in propres:
                propres.append(p)
        en_file = _entier(en_file, 1, EN_FILE_MAX, "rendus en file",
                          cle="erreur.acces_en_file")
        par_jour = _entier(par_jour, 0, PAR_JOUR_MAX,
                           "rendus par jour (0 = sans plafond)",
                           cle="erreur.acces_par_jour")
        expire_jours = _entier(expire_jours, 0, EXPIRE_JOURS_MAX,
                               "duree de vie en jours (0 = sans fin)",
                               cle="erreur.acces_expire")
        operations = operations_valides(operations)
        par_jour_familles = par_jour_familles_valides(par_jour_familles)
        if sum(1 for f in self.fiches.values()
               if f["compte"] == compte) >= CLES_PAR_COMPTE:
            raise ErreurAcces(f"{CLES_PAR_COMPTE} cles au plus par compte : "
                              f"revoquez celles qui ne servent plus",
                              cle="erreur.acces_trop_de_cles", maxi=CLES_PAR_COMPTE)
        ident = secrets.token_hex(4)
        while ident in self.fiches:
            ident = secrets.token_hex(4)
        cle = f"{PREFIXE}{ident}_{secrets.token_urlsafe(32)}"
        # LE SECRET DE RAPPEL EST GARDE EN CLAIR, et c'est un compromis assume.
        # Il sert a SIGNER : il faut le relire pour calculer le HMAC de chaque
        # rappel, une empreinte ne signe rien. C'est la meme situation que les
        # cles de jeton des machines et que le secret TOTP de comptes.py — d'ou
        # le fichier en 0600, et l'absence de ce champ dans toute fiche
        # publique. Celui qui lit le fichier peut forger un rappel ; il ne peut
        # pas, avec, se presenter au studio.
        secret = secrets.token_urlsafe(32)
        quand = time.time() if maintenant is None else maintenant
        self.fiches[ident] = {
            "id": ident, "compte": compte, "nom": nom,
            "empreinte": empreinte_de(cle), "secret_rappel": secret,
            "generation": generation, "cree": quand, "vu": None,
            "nuage": bool(nuage), "hotes": propres, "en_file": en_file,
            "par_jour": par_jour,
            "expire": quand + expire_jours * 86400 if expire_jours else None,
            "operations": operations,
            "par_jour_familles": par_jour_familles,
        }
        try:
            self.sauver()
        except BaseException:
            # Une cle montree mais pas ecrite mourrait au redemarrage, et le
            # programme qui l'a recue recevrait des 401 sans savoir pourquoi.
            # Mieux vaut ne pas la montrer du tout.
            self.fiches.pop(ident, None)
            raise
        return {"cle": cle, "secret_rappel": secret,
                "fiche": self.publique(self.fiches[ident])}

    def reconnaitre(self, cle, generation_de, maintenant=None):
        """La fiche PUBLIQUE de cette cle si elle vaut encore, sinon None.

        « generation_de(compte) » rend la generation actuelle du compte, ou
        None s'il n'existe plus. Ne leve jamais : un appelant qui n'attend que
        « fiche ou None » ne doit pas recevoir une pile d'appels sur une cle
        mal formee envoyee par n'importe qui.

        Un magasin illisible n'a aucune fiche : rien n'y est reconnu, sans
        garde de plus.
        """
        ident = identifiant_de(cle)
        if ident is None:
            return None
        fiche = self.fiches.get(ident)
        # L'EMPREINTE EST CALCULEE MEME QUAND L'IDENTIFIANT NE DESIGNE RIEN.
        # Rendre None tout de suite repondrait plus vite pour un identifiant
        # inconnu que pour un secret faux : au chronometre, on saurait quels
        # identifiants existent, et l'on n'aurait plus a deviner que la moitie
        # de la cle. Un sha256 et une comparaison dans les deux cas.
        attendu = fiche["empreinte"] if fiche else _EMPREINTE_FACTICE
        empreinte = empreinte_de(cle)
        juste = hmac.compare_digest(empreinte, attendu)
        quand = time.time() if maintenant is None else maintenant
        # LES DEUX COMPARAISONS, TOUJOURS : savoir au chronometre qu'une cle
        # vient d'etre renouvelee n'apprendrait pas grand-chose, mais une
        # comparaison de plus ne coute rien.
        if _ancienne_valable(fiche, empreinte, quand):
            juste = True
        if fiche is not None and not juste:
            # L'IDENTIFIANT D'UNE CLE QUI EXISTE, ET UN SECRET FAUX : une cle
            # mal recopiee, un ancien secret apres sa grace, ou une cle volee
            # a moitie — l'identifiant est public, il est dans chaque lien
            # signe. On compte, on ne garde RIEN de ce qui a ete essaye : ni le
            # secret, ni son empreinte. Une cle juste mais eteinte ou expiree
            # n'arrive pas ici : son secret est bon, c'est la date ou la
            # generation qui la ferment, et l'appeler « secret faux » enverrait
            # chercher un voleur qui n'existe pas.
            self._noter_echec(fiche, quand)
        if fiche is None or not juste:
            return None
        # LA GENERATION DU COMPTE. Changer son mot de passe, armer ou desarmer
        # le second facteur ferme DEJA toutes les sessions du compte
        # (comptes.py incremente « gen »). Sans ce lien, quelqu'un qui a vole
        # le mot de passe pouvait se fabriquer une cle d'acces dans la minute,
        # et elle aurait survecu au changement de mot de passe que le
        # proprietaire fait justement pour le chasser. None : le compte n'existe
        # plus, ses cles non plus.
        try:
            gen = generation_de(fiche["compte"])
        except Exception:
            return None
        if not isinstance(gen, int) or gen != fiche["generation"]:
            return None
        if expiree(fiche, quand):
            return None
        fiche["vu"] = quand
        if quand - self._vu_ecrit.get(ident, float("-inf")) >= VU_ECRIT_TOUTES:
            self._vu_ecrit[ident] = quand
            try:
                self.sauver()
            except (OSError, ErreurAcces) as e:
                # La date de dernier usage est une commodite : ne pas savoir
                # l'ecrire ne doit pas refuser une cle juste.
                print(f"cles d'acces : date d'usage non ecrite ({e})",
                      flush=True)
        return self.publique(fiche)

    def expiree_pour(self, cle, maintenant=None):
        """Vrai si CETTE cle, secret juste, est connue et a passe sa date de fin.

        Pour dire au programme « cle expiree » plutot que « cle refusee » : le
        geste a faire n'est pas le meme (en creer une autre, et non chercher la
        faute de frappe). Le secret est verifie d'abord, comme dans
        reconnaitre() : sans lui, la reponse dirait a n'importe qui quels
        identifiants designent une cle expiree.
        """
        ident = identifiant_de(cle)
        if ident is None:
            # Hors forme : rien a comparer, et rien a cacher — la forme d'une
            # cle est publique, reconnaitre() repond aussi vite dans ce cas.
            return False
        fiche = self.fiches.get(ident)
        attendu = fiche["empreinte"] if fiche else _EMPREINTE_FACTICE
        empreinte = empreinte_de(cle)
        juste = hmac.compare_digest(empreinte, attendu)
        quand = time.time() if maintenant is None else maintenant
        if _ancienne_valable(fiche, empreinte, quand):
            juste = True
        return bool(fiche and juste and expiree(fiche, quand))

    def renouveler(self, ident, compte=None, grace=GRACE_RENOUVELLEMENT,
                   maintenant=None):
        """Un secret neuf pour la cle « ident ». Rend {"cle", "fiche"}.

        L'ancien secret vaut encore GRACE_RENOUVELLEMENT secondes, puis plus
        rien ; un second renouvellement pendant la grace ferme aussitot le
        premier secret — on ne garde qu'un secret d'avance.

        Avec « compte », seulement une cle A LUI (comme revoquer). Une cle
        expiree ne se renouvelle pas : sa date de fin etait voulue, et un
        secret neuf la rouvrirait. Le secret de rappel, lui, ne change pas :
        le recepteur n8n qui verifie les signatures continue de marcher.
        """
        f = self.fiches.get(ident) if isinstance(ident, str) else None
        if f is None or (compte is not None
                         and f["compte"] != str(compte).strip().lower()):
            raise ErreurAcces("cle inconnue", cle="erreur.cle_inconnue")
        quand = time.time() if maintenant is None else maintenant
        if expiree(f, quand):
            raise ErreurAcces("une cle expiree ne se renouvelle pas : creez-en "
                              "une autre", cle="erreur.acces_renouveler_expiree")
        cle = f"{PREFIXE}{ident}_{secrets.token_urlsafe(32)}"
        avant = {k: f.get(k) for k in ("empreinte", "empreinte_ancienne",
                                       "ancienne_jusqu")}
        if grace > 0:
            f["empreinte_ancienne"] = f["empreinte"]
            f["ancienne_jusqu"] = quand + grace
        else:
            # SANS GRACE : le secret est vole, il meurt a la reponse. Aucune
            # trace de lui ne reste, pas meme son empreinte.
            f.pop("empreinte_ancienne", None)
            f.pop("ancienne_jusqu", None)
        f["empreinte"] = empreinte_de(cle)
        try:
            self.sauver()
        except BaseException:
            # Une cle montree mais pas ecrite : au redemarrage, l'ancienne
            # reviendrait seule, et le programme recevrait des 401 avec la
            # neuve. Mieux vaut ne rien changer.
            f.update(avant)
            for k, v in avant.items():
                if v is None:
                    f.pop(k, None)
            raise
        return {"cle": cle, "fiche": self.publique(f)}

    def publique(self, fiche):
        """Ce qui peut sortir d'ici : ni l'empreinte, ni le secret de rappel.

        UNE LISTE BLANCHE, PAS UNE LISTE NOIRE. Recopier la fiche en retirant
        les deux champs secrets laisserait sortir le troisieme qu'on ajoutera
        un jour sans penser a cette methode.
        """
        return {
            "id": fiche["id"], "compte": fiche["compte"], "nom": fiche["nom"],
            # « … » et non la cle tronquee : meme quatre caracteres du secret
            # sont quatre caracteres de moins a deviner. (… : l'ellipse,
            # ecrite echappee pour que ce source reste en ASCII.)
            "apercu": f"{PREFIXE}{fiche['id']}_…",
            "cree": fiche["cree"], "vu": fiche.get("vu"),
            "nuage": bool(fiche.get("nuage")),
            "hotes": list(fiche.get("hotes") or []),
            "en_file": fiche["en_file"], "par_jour": fiche["par_jour"],
            # Un entier, pas un secret. C'est la seule facon pour la page de
            # dire « cette cle s'est eteinte quand tu as change ton mot de
            # passe » au lieu de la montrer vivante : reconnaitre() la refuse
            # deja, mais une liste qui l'affiche comme valide ment.
            "generation": fiche["generation"],
            # La date de fin, ou null : sans fin.
            "expire": fiche.get("expire"),
            # Jusqu'a quand le secret d'avant un renouvellement vaut encore,
            # ou null. L'empreinte, elle, ne sort jamais.
            # Passee, la date redevient null : un client qui teste
            # « if ancienne_jusqu » croirait sinon l'ancien secret vivant.
            "ancienne_jusqu": (fiche.get("ancienne_jusqu")
                               if fiche.get("empreinte_ancienne")
                               and (fiche.get("ancienne_jusqu") or 0) > time.time()
                               else None),
            # Ce que la cle peut faire ; vide : tout. Une copie, pour qu'un
            # appelant qui la modifie ne touche pas la fiche.
            "operations": list(fiche.get("operations") or []),
            # Les plafonds du jour par famille ; vide : rien de plus que
            # « par_jour ». Une copie aussi.
            "par_jour_familles": dict(fiche.get("par_jour_familles") or {}),
        }

    # ── le suivi ─────────────────────────────────────────────────────────
    def _suivi_du_jour(self, fiche, quand):
        """Le suivi de la fiche pour le jour de « quand », remis a zero s'il
        datait d'un autre jour. Les instants du dernier refus et du dernier
        echec, eux, passent minuit : « dernier secret faux : mardi » reste
        vrai mercredi."""
        s = fiche.get("suivi")
        jour = _jour(quand)
        if not isinstance(s, dict) or s.get("jour") != jour:
            s = s if isinstance(s, dict) else {}
            s = {"jour": jour, "refus": {}, "echecs": 0,
                 "dernier_refus": s.get("dernier_refus"),
                 "dernier_code": s.get("dernier_code"),
                 "dernier_echec": s.get("dernier_echec")}
            fiche["suivi"] = s
        return s

    def _ecrire_suivi(self, quand):
        if quand - self._suivi_ecrit >= SUIVI_ECRIT_TOUTES:
            self.vider_suivi(quand)

    def vider_suivi(self, maintenant=None):
        """Ecrit le suivi s'il a change. Rend True si une ecriture a eu lieu.
        Ne leve jamais : un compteur non ecrit ne doit casser ni une requete,
        ni l'arret du studio."""
        if not self._suivi_sale or self.illisible:
            return False
        self._suivi_ecrit = time.time() if maintenant is None else maintenant
        try:
            self.sauver()
        except (OSError, ErreurAcces) as e:
            print(f"cles d'acces : suivi non ecrit ({e})", flush=True)
            return False
        return True

    def noter_refus(self, ident, code, maintenant=None):
        """Un refus de plus pour la cle « ident », sous ce code. Ne leve jamais.

        Le serveur appelle ici pour les refus d'entree comme pour les refus
        tardifs (un rendu qui finit en « erreur » parce que l'analyse a lu une
        operation que la cle ne permet pas) : le proprietaire n'a pas a savoir
        a quel moment le studio a dit non pour savoir qu'il l'a dit."""
        f = self.fiches.get(ident) if isinstance(ident, str) else None
        if f is None:
            return
        quand = time.time() if maintenant is None else maintenant
        code = code if isinstance(code, str) and _CODE_SUIVI.fullmatch(code) else "autre"
        s = self._suivi_du_jour(f, quand)
        if code not in s["refus"] and len(s["refus"]) >= SUIVI_CODES_MAX - 1:
            # La derniere place est pour « autre » : un code neuf au-dela ne
            # chasse pas ceux qu'on a deja comptes.
            code = "autre"
        s["refus"][code] = s["refus"].get(code, 0) + 1
        s["dernier_refus"], s["dernier_code"] = quand, code
        self._suivi_sale = True
        self._ecrire_suivi(quand)

    def _noter_echec(self, fiche, quand):
        s = self._suivi_du_jour(fiche, quand)
        s["echecs"] += 1
        s["dernier_echec"] = quand
        self._suivi_sale = True
        self._ecrire_suivi(quand)

    def suivi(self, ident, maintenant=None):
        """Le suivi du jour de cette cle, ou None si elle n'existe pas.

        A part de publique() : ce n'est pas ce que la cle PERMET, c'est ce qui
        lui est arrive. La fiche publique reste ce que le contrat promet a un
        programme ; le suivi ne sort que vers son proprietaire et vers
        l'administration. Une copie : l'appelant peut la modifier."""
        f = self.fiches.get(ident) if isinstance(ident, str) else None
        if f is None:
            return None
        quand = time.time() if maintenant is None else maintenant
        s = f.get("suivi") if isinstance(f.get("suivi"), dict) else {}
        du_jour = s.get("jour") == _jour(quand)
        refus = dict(s.get("refus") or {}) if du_jour else {}
        return {"refus": refus, "refus_total": sum(refus.values()),
                "dernier_refus": s.get("dernier_refus"),
                "dernier_code": s.get("dernier_code"),
                "echecs": (s.get("echecs") or 0) if du_jour else 0,
                "dernier_echec": s.get("dernier_echec")}

    def liste(self, compte=None):
        """Fiches publiques, de la plus ancienne a la plus recente."""
        # « compte is None » et non « not compte » : un compte vide ou mal type
        # passe par la route d'un proprietaire, et lui rendre TOUTES les cles
        # serait lui montrer celles des autres.
        c = None if compte is None else str(compte).strip().lower()
        return [self.publique(f)
                for f in sorted(self.fiches.values(), key=lambda f: f["cree"])
                if c is None or f["compte"] == c]

    def fiche(self, ident):
        f = self.fiches.get(ident) if isinstance(ident, str) else None
        return self.publique(f) if f else None

    def secret_rappel(self, ident):
        """Pour signer un rappel ou un lien. Jamais dans une fiche publique."""
        f = self.fiches.get(ident) if isinstance(ident, str) else None
        return f["secret_rappel"] if f else None

    def revoquer(self, ident, compte=None):
        """Revoque une cle. Avec « compte », seulement si elle est A LUI.

        La route du proprietaire passe son propre compte : sans ce filtre,
        connaitre l'identifiant PUBLIC d'une cle — il s'affiche dans l'apercu,
        il passe dans les journaux — suffirait a couper le programme d'un
        autre. L'administration, elle, appelle sans compte.
        """
        f = self.fiches.get(ident) if isinstance(ident, str) else None
        if f is None:
            return False
        if compte is not None and f["compte"] != str(compte).strip().lower():
            return False
        del self.fiches[ident]
        self._vu_ecrit.pop(ident, None)
        self.sauver()
        return True

    def revoquer_compte(self, compte):
        """Le compte est supprime : toutes ses cles meurent avec. Rend le nombre.

        La generation suffirait a les refuser (generation_de rend None), mais
        un compte recree sous le meme nom repartirait a la generation zero — et
        les cles de l'ancien proprietaire, nees a zero, redeviendraient bonnes.
        """
        c = (compte if isinstance(compte, str) else "").strip().lower()
        mortes = [i for i, f in self.fiches.items() if f["compte"] == c]
        for i in mortes:
            del self.fiches[i]
            self._vu_ecrit.pop(i, None)
        if mortes:
            self.sauver()
        return len(mortes)


# ── Les liens signes ────────────────────────────────────────────────────
# UN PROGRAMME OU UN ASSISTANT IA NE POSE PAS TOUJOURS D'EN-TETE. Un agent qui
# rend un lien a un humain dans une conversation, un noeud n8n « telecharger un
# fichier », une balise <img> : aucun ne sait ajouter « Authorization ». Le lien
# porte donc sa propre preuve — quelle cle l'a demande, quel rendu, quel
# fichier, jusqu'a quand — scellee par le secret de cette cle.

def _signature(secret, ident, tid, rang, fin):
    """Le HMAC d'un lien, sur TOUS ses champs. Une seule ecriture pour signer et
    pour controler : deux ecritures du meme enchainement finissent par
    diverger, et ici la divergence serait un champ qu'on change sans casser la
    signature. Le « lien| » de tete separe ces signatures de celles des
    rappels, faites avec le meme secret."""
    charge = f"lien|{ident}|{tid}|{rang}|{fin}"
    return hmac.new(secret.encode("utf-8"), charge.encode("utf-8"),
                    hashlib.sha256).hexdigest()[:32]


def signer_lien(secret, ident, tid, rang, fin):
    """« ident.tid.rang.fin.sig ». Refuse ce que lien_valide() refuserait :
    signer un lien qui ne se relira jamais ne servirait qu'a le decouvrir chez
    l'utilisateur."""
    if not isinstance(secret, str) or not secret:
        raise ErreurAcces("lien : secret manquant")
    if isinstance(rang, bool) or isinstance(fin, bool):
        raise ErreurAcces("lien : rang et fin sont des entiers")
    try:
        jeton = f"{ident}.{tid}.{int(rang)}.{int(fin)}"
    except (TypeError, ValueError):
        raise ErreurAcces("lien : rang et fin sont des entiers") from None
    jeton += "." + _signature(secret, ident, tid, int(rang), int(fin))
    if not _LIEN.fullmatch(jeton):
        raise ErreurAcces("lien : identifiant, rendu, rang ou fin hors forme")
    return jeton


def lien_valide(secret, jeton, maintenant=None):
    """(ident, tid, rang) si le lien est intact et pas expire, sinon None.

    Ne leve jamais. NE DIT PAS que la cle « ident » existe encore : le studio
    doit le verifier de son cote, avec Acces.fiche() — un lien MEURT AVEC SA
    CLE, et le secret qu'on passe ici a pu etre relu juste avant une
    revocation.
    """
    if not isinstance(secret, str) or not secret or not isinstance(jeton, str):
        return None
    m = _LIEN.fullmatch(jeton)
    if not m:
        return None
    ident, tid, rang, fin, sig = m.groups()
    if not hmac.compare_digest(_signature(secret, ident, tid, int(rang),
                                          int(fin)), sig):
        return None
    quand = time.time() if maintenant is None else maintenant
    if quand > int(fin):
        return None
    return ident, tid, int(rang)
