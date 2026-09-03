# -*- coding: utf-8 -*-
"""Le second facteur : un code a six chiffres qui change toutes les trente
secondes.

POURQUOI CELUI-LA. Le studio publie un port — c'est ce que fait le conteneur —
et un mot de passe seul ne survit pas a une fuite. TOTP (RFC 6238) est ce que
toutes les applications d'authentification savent lire, il ne demande ni
reseau, ni service tiers, ni dependance : HMAC-SHA1 et base32 sont dans la
bibliotheque standard de Python. Le dépôt n'ajoute donc rien a installer, et ce
fichier se lit en entier.

CE QUI EST MESURE CONTRE UNE AUTORITE EXTERIEURE. La RFC 6238 publie ses
propres vecteurs de test — un secret connu, six instants, six codes attendus.
banc_mfa.py les rejoue tels quels. C'est la difference entre « mon code est
d'accord avec lui-meme » et « mon code est d'accord avec le reste du monde » :
un decalage d'un pas de temps, un octet lu dans le mauvais sens, un masque
oublie, et l'implementation reste coherente tout en refusant tous les codes que
Google Authenticator produit.

SHA1 ET NON SHA256, ET CE N'EST PAS UNE NEGLIGENCE. La RFC 6238 autorise les
trois ; les applications, elles, supposent SHA1 quand l'URI ne dit rien, et
plusieurs ignorent le parametre « algorithm » meme quand il est ecrit. Un
secret enrole en SHA256 y produit donc des codes qui ne marchent nulle part,
sans message d'erreur — l'utilisateur voit « code invalide » et croit s'etre
trompe. La faiblesse theorique de SHA1 ne mord pas ici : HMAC-SHA1 n'est pas
menace par les collisions, et le code ne vaut que trente secondes.
"""
import base64
import binascii
import hashlib
import hmac
import secrets
import struct
import time

# Le pas de temps de la RFC, et celui que toutes les applications supposent.
# Le changer rendrait les codes du studio illisibles par elles.
PAS = 30
CHIFFRES = 6

# COMBIEN DE PAS DE PART ET D'AUTRE. Une horloge de telephone derive, et
# quelqu'un qui tape lentement franchit une frontiere de trente secondes en
# plein milieu de sa saisie. Un seul pas de chaque cote donne une fenetre de
# 90 s au pire, ce que la RFC 6238 recommande en toutes lettres (« at most one
# time step »). Deux pas doubleraient la surface pour un confort que personne
# n'a demande.
FENETRE = 1

# Vingt octets : la taille de la sortie de SHA1, celle que la RFC emploie dans
# ses vecteurs, et celle que les applications attendent. Trente-deux
# caracteres en base32, sans remplissage.
OCTETS_SECRET = 20


class ErreurMFA(ValueError):
    pass


def secret_neuf():
    """Un secret tire au sort, en base32 sans remplissage.

    Sans remplissage parce que les « = » de fin ne survivent pas au passage
    dans une URL — otpauth:// les fait echapper en « %3D », et plusieurs
    applications les recopient tels quels dans le secret. Vingt octets tombent
    juste : 32 caracteres, aucun remplissage a produire.
    """
    return base64.b32encode(secrets.token_bytes(OCTETS_SECRET)).decode("ascii")


def _octets_du_secret(secret):
    """Le secret base32 en octets, en pardonnant ce qu'un humain recopie.

    QUELQU'UN RECOPIE UN SECRET A LA MAIN, et il le recopie comme il le voit :
    en minuscules, avec les espaces que l'affichage y met tous les quatre
    caracteres pour le rendre lisible, parfois sans le remplissage. Refuser ces
    trois-la, c'est refuser un secret juste et renvoyer « code invalide » a
    quelqu'un qui n'a rien fait de mal — la panne se cherche du mauvais cote
    pendant une heure.
    """
    propre = "".join((secret or "").split()).upper().replace("-", "")
    if not propre:
        raise ErreurMFA("secret vide")
    # base64.b32decode exige un multiple de huit caracteres. On complete, au
    # lieu d'exiger que l'appelant l'ait fait.
    reste = len(propre) % 8
    if reste:
        propre += "=" * (8 - reste)
    try:
        return base64.b32decode(propre, casefold=True)
    except (binascii.Error, ValueError) as e:
        raise ErreurMFA(f"secret illisible : {type(e).__name__}") from e


def pas_de(quand=None):
    """Le numero du pas de temps courant. Entier, donc comparable et stockable."""
    return int((time.time() if quand is None else quand) // PAS)


def code(secret, quand=None, pas=None, chiffres=CHIFFRES):
    """Le code attendu a cet instant. C'est HOTP (RFC 4226) sur un compteur
    de temps, et c'est tout ce que TOTP ajoute.

    « >B » sur le dernier octet ET « & 0x0f » : la troncature dynamique de la
    RFC 4226 prend les quatre bits de poids faible du DERNIER octet comme
    decalage. « & 0x7fffffff » ensuite efface le bit de signe — sans lui, un
    condensat sur deux donnerait un nombre negatif et un code a cinq chiffres
    precede d'un moins.
    """
    compteur = pas_de(quand) if pas is None else pas
    empreinte = hmac.new(_octets_du_secret(secret),
                         struct.pack(">Q", compteur), hashlib.sha1).digest()
    decalage = empreinte[-1] & 0x0F
    tronque = struct.unpack_from(">I", empreinte, decalage)[0] & 0x7FFFFFFF
    return str(tronque % (10 ** chiffres)).zfill(chiffres)


def verifie(secret, saisie, quand=None, fenetre=FENETRE, dernier_pas=None,
            chiffres=CHIFFRES):
    """Rend le PAS accepte, ou None. Jamais un booleen, et c'est le point.

    LA LONGUEUR ATTENDUE NE VIENT PAS DE CE QUE L'ATTAQUANT TAPE. Cette
    fonction a compare, du 2 au 3 septembre 2026, le code attendu tronque a
    « len(saisie) » — de sorte qu'une saisie a UN chiffre etait comparee au
    code modulo dix. Mesure du 3 septembre : 549 saisies a un chiffre acceptees
    sur 2 000 instants tires au hasard, soit 27,4 %, et 25 sessions ouvertes sur
    25 avec le seul mot de passe, en 4,8 essais de moyenne. Le freinage — trois
    essais gratuits, puis 1 s, 2 s, 4 s — laissait sept secondes pour 85 % de
    reussite.

    La garantie que tout le reste invoque — « six chiffres font un million » —
    etait donc fausse : le studio en acceptait un. Elle est ecrite dans
    _ouvrir_porte(), dans banc_comptes.py et dans le message du commit qui a
    branche le facteur ; aucune de ces trois phrases n'etait vraie.

    « chiffres » reste un parametre, parce que la RFC 6238 publie ses vecteurs
    sur huit et que banc_mfa.py les rejoue — mais il est POSE par l'appelant,
    jamais deduit de l'entree. C'est toute la difference.

    L'APPELANT DOIT GARDER CE PAS ET LE REPASSER. Un code TOTP reste valable
    pendant toute sa fenetre : sans memoire, le meme code rejoue trois fois de
    suite ouvre trois sessions. C'est la faute la plus courante des
    implementations maison — elles verifient le code, ce qui est le facile, et
    oublient qu'un second facteur qu'on peut rejouer ne protege plus contre
    quelqu'un qui a vu l'ecran ou relu un journal. « dernier_pas » ferme cela,
    et rendre le pas plutot qu'un booleen oblige l'appelant a s'en occuper : il
    ne peut pas l'ignorer par distraction, il n'aurait rien a stocker.

    LA COMPARAISON EST A TEMPS CONSTANT. compare_digest et non « == » : sur six
    chiffres, l'arret au premier caractere different est mesurable a distance,
    et permet de deviner le code chiffre par chiffre au lieu de le chercher
    parmi un million.
    """
    propre = "".join((saisie or "").split())
    # LA LONGUEUR D'ABORD, ET AVANT TOUT CALCUL. « isdigit() » seul laissait
    # passer « 7 » comme « 1234567 » : le premier ouvrait une chance sur dix par
    # pas, le second ne pouvait rien ouvrir mais faisait calculer trois HMAC
    # pour rien.
    if not propre.isdigit() or len(propre) != chiffres:
        return None
    maintenant = pas_de(quand)
    # On balaie du plus recent au plus ancien : le cas normal est le pas
    # courant, et l'ordre ne change rien a la securite — les six chiffres sont
    # compares en temps constant a chaque tour.
    for ecart in range(-fenetre, fenetre + 1):
        p = maintenant + ecart
        if dernier_pas is not None and p <= dernier_pas:
            # DEJA SERVI. On ne rend pas None tout de suite : un pas plus
            # recent de la fenetre peut encore convenir, et sortir ici
            # refuserait un code juste a quelqu'un qui se reconnecte trente
            # secondes apres.
            continue
        if hmac.compare_digest(code(secret, pas=p, chiffres=chiffres),
                               propre):
            return p
    return None


def uri(compte, secret, emetteur="ComfyStudio"):
    """L'URI otpauth:// que l'application lit dans un QR code.

    L'EMETTEUR EST ECRIT DEUX FOIS, dans le chemin et dans les parametres, et
    ce n'est pas une redondance : les applications anciennes lisent le chemin,
    les recentes le parametre, et celles qui lisent les deux exigent qu'ils
    concordent. En omettre un fait apparaitre le compte sans nom de service
    dans une liste ou l'utilisateur en a trente.

    Les parametres « algorithm », « digits » et « period » sont ecrits meme
    quand ils valent le defaut : plusieurs applications ne les devinent pas de
    la meme facon, et un code a huit chiffres affiche pour un studio qui en
    attend six ressemble a une panne du studio.
    """
    from urllib.parse import quote
    etiquette = quote(f"{emetteur}:{compte}", safe="")
    return (f"otpauth://totp/{etiquette}?secret={secret}"
            f"&issuer={quote(emetteur, safe='')}"
            f"&algorithm=SHA1&digits={CHIFFRES}&period={PAS}")


# ── Les codes de secours ────────────────────────────────────────────────
# UN SECOND FACTEUR SANS PORTE DE SORTIE ENFERME SON PROPRIETAIRE. Un telephone
# perdu, remplace, ou simplement reinitialise, et le compte est mort : personne
# ne peut le rouvrir, pas meme l'administrateur, puisque c'est justement ce
# qu'on vient d'empecher. Les codes de secours sont la porte, et ils sont a
# usage unique.
#
# DIX CODES, et non un seul « code maitre » : un code unique se note quelque
# part et devient un second mot de passe permanent. Dix codes rayes au fur et a
# mesure disent a leur proprietaire qu'ils s'epuisent, et le poussent a en
# regenerer un jeu plutot qu'a en recopier un.
CODES_SECOURS = 10
_ALPHABET = "23456789abcdefghjkmnpqrstuvwxyz"   # ni 0/O ni 1/l/I


def codes_de_secours(combien=CODES_SECOURS):
    """Des codes lisibles a la main, tires au sort, en clair UNE seule fois.

    L'alphabet ecarte les caracteres qu'on confond en recopiant depuis un
    papier : le zero et le O, le un, le l et le I. Quelqu'un qui se trompe de
    caractere sur son dernier code de secours n'a plus de studio.
    """
    return ["-".join("".join(secrets.choice(_ALPHABET) for _ in range(4))
                     for _ in range(2)) for _ in range(combien)]


def normalise_secours(code_):
    """La forme sous laquelle un code de secours se compare.

    On pardonne la casse, les espaces et les tirets — ce qu'un humain change
    sans y penser en recopiant. On ne pardonne rien d'autre : ces codes ne sont
    JAMAIS gardes en clair, ils sont empreintes comme un mot de passe, et cette
    fonction est ce qui doit etre appele des deux cotes pour que l'empreinte
    tombe juste.
    """
    return "".join((code_ or "").split()).replace("-", "").lower()
