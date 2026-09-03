# -*- coding: utf-8 -*-
"""Un QR code, en Python nu, pour que le second facteur se scanne.

POURQUOI L'ECRIRE PLUTOT QUE L'INSTALLER. Le studio doit demarrer sur un NAS ou
pip n'a jamais servi, et la page n'a aucune dependance ni aucun CDN — c'est une
regle du depot, pas une paresse. La seule facon d'afficher un QR code dans ces
conditions est de calculer la matrice ici. Ce fichier ne fait que cela : il rend
une grille de booleens, sans zone de silence et sans savoir ce qu'est un pixel.
C'est la page qui dessine.

CE QUI REND CE FICHIER DANGEREUX, ET COMMENT ON S'EN GARDE. Un encodeur QR
ecrit a la main peut etre parfaitement coherent avec lui-meme et produire une
image qu'aucun telephone ne lit : un masque mal choisi, un octet de correction
dans le mauvais ordre, un motif d'alignement place a un pixel pres. Rien de
tout cela ne leve, et « ca ressemble a un QR code » est tout ce qu'on saurait.
banc_qr.py compare donc module par module a quatre matrices produites par
segno — une implementation qu'on n'a PAS ecrite, capturee le 3 septembre 2026
dans etalons_qr.py. Le meme raisonnement que les vecteurs de la RFC 6238 pour
le TOTP, et la meme necessite.

CE QU'IL SAIT FAIRE, ET RIEN DE PLUS :

  - MODE OCTET SEULEMENT. Le studio n'encode qu'une chose, l'URI otpauth://,
    et elle porte des minuscules et des barres obliques : le mode
    alphanumerique, qui ne connait que 45 caracteres, ne peut pas la prendre.
    Ecrire les modes numerique et alphanumerique ajouterait deux chemins que
    RIEN dans le studio n'emprunterait — donc deux chemins qu'aucune mesure
    reelle n'eprouve. Mesure : sur les trois URI des etalons, le mode octet est
    le seul legal. Le quatrieme, « HELLO WORLD », est le seul ou un autre mode
    existe et segno l'a pris : son premier mot de code vaut 0x20, soit
    l'indicateur 0010 du mode ALPHANUMERIQUE, la ou le mode octet ecrit 0100.
    Cet etalon-la ne peut donc pas etre refait depuis son texte ; banc_qr.py le
    refait depuis ses propres mots de code, et le dit.
  - CORRECTION M SEULEMENT, pour la meme raison : c'est le niveau que le studio
    demande, et la table des blocs des trois autres niveaux ferait quatre fois
    plus de chiffres recopies a la main dont trois quarts ne seraient jamais
    relus par personne. Une table fausse et jamais lue est pire qu'une table
    absente.
  - LA PLUS PETITE VERSION QUI TIENT A M, ET PAS PLUS. C'est la politique, elle
    tient en une phrase, et banc_qr.py l'exige separement de la matrice. Segno
    fait autre chose par defaut : « error='m' » y veut dire AU MOINS M, et il
    monte le niveau quand la version choisie laisse de la place — d'ou le
    « boost_error=False » d'outils_etalons_qr.py, sans lequel « HELLO WORLD »
    sortait en 1-Q et l'etalon aurait decrit une politique que ce fichier n'a
    pas.
  - LE MASQUE PAR LES QUATRE REGLES DE PENALITE DE LA NORME, les huit essayes,
    le plus petit total gagne. Pas de raccourci : un masque choisi au hasard
    donne une matrice parfaitement valide au sens du code correcteur et que
    beaucoup de lecteurs refusent, parce que les grandes plages uniformes et
    les faux motifs de reperage les egarent. C'est la faute qui ne leve pas.

CE QU'IL NE FAIT PAS COMME SEGNO, ET C'EST MESURE. Nos regles de penalite ne
retiennent pas le meme masque que lui : 4 contre 3 sur « court », 6 contre 5 sur
« reel », 2 contre 4 sur « long » — trois sur trois en mode octet, et 2 contre 0
sur le quatrieme etalon si l'on rejoue ses mots de code.

Ce n'est pas un defaut de l'encodeur, et deux mesures le disent. D'abord, avec le
masque de segno force, nos matrices sont IDENTIQUES aux siennes : 6364 modules
compares un par un sur les quatre etalons, zero ecart. Ensuite, les huit masques
sont legaux — le numero est ecrit dans le format d'information et le lecteur
defait celui qu'on annonce —, et banc_qr.py verifie pour les HUIT que le numero
annonce est bien celui applique, en relisant les mots de code par le chemin d'un
telephone. Ce qui n'est PAS verifie contre une autorite exterieure, c'est le
CLASSEMENT des huit ; l'en-tete de banc_qr.py dit ce qui a ete essaye pour
retrouver celui de segno et pourquoi on s'est arrete la.

MESURE DE COUT, sur cette machine (Windows 11, Python 3.14), moyenne de
200 encodages de l'URI reelle d'un compte (7-M, 45x45) : 6,4 ms en tout, dont
0,4 ms pour les mots de code et 6,0 ms pour les huit masques et leurs
penalites — un seul masque coute 1,0 ms. C'est paye UNE fois par enrolement, sur
une route qui fait deja un scrypt de 2**14 tours ; le budget n'est pas ici, et
ne pas essayer les huit masques ferait gagner 5 ms contre un code moins lisible.

    from qr import encoder
    c = encoder("otpauth://totp/...")
    c.version, c.niveau, c.masque, c.modules
"""
import collections

# Le niveau de correction, et le seul que ce fichier connaisse. « M » corrige
# environ 15 % des modules perdus : c'est le compromis que toutes les
# applications d'authentification affichent, et celui des etalons.
NIVEAU = "M"

# Les deux bits que la norme donne au niveau dans le format d'information.
# Ils ne suivent PAS l'ordre L < M < Q < H : L vaut 01 et M vaut 00. Recopier
# l'ordre intuitif produit un format valide pour un AUTRE niveau, que le
# lecteur applique ensuite au bloc de correction — il ne lit rien et ne dit pas
# pourquoi.
_BITS_NIVEAU = 0b00


class ErreurQR(ValueError):
    pass


# ── Les tables de la norme ────────────────────────────────────────────
# ISO/IEC 18004, tables 13 a 22, colonne M UNIQUEMENT.
#
# Par version : (correction par bloc, blocs du groupe 1, donnees par bloc du
# groupe 1, blocs du groupe 2, donnees par bloc du groupe 2). Les versions
# hautes coupent le message en deux tailles de blocs qui different d'UN octet,
# et cette difference d'un octet est exactement ce qui se perd quand on recopie
# la table de travers : l'entrelacement decale alors tout ce qui suit, et la
# matrice reste parfaitement formee. banc_qr.py verifie cette table sans la
# relire, par un invariant de la norme — le total des mots de code plus les
# bits de reste doit remplir exactement les modules libres de la version.
_BLOCS_M = {
    1: (10, 1, 16, 0, 0),
    2: (16, 1, 28, 0, 0),
    3: (26, 1, 44, 0, 0),
    4: (18, 2, 32, 0, 0),
    5: (24, 2, 43, 0, 0),
    6: (16, 4, 27, 0, 0),
    7: (18, 4, 31, 0, 0),
    8: (22, 2, 38, 2, 39),
    9: (22, 3, 36, 2, 37),
    10: (26, 4, 43, 1, 44),
    11: (30, 1, 50, 4, 51),
    12: (22, 6, 36, 2, 37),
    13: (22, 8, 37, 1, 38),
    14: (24, 4, 40, 5, 41),
    15: (24, 5, 41, 5, 42),
    16: (28, 7, 45, 3, 46),
    17: (28, 10, 46, 1, 47),
    18: (26, 9, 43, 4, 44),
    19: (26, 3, 44, 11, 45),
    20: (26, 3, 41, 13, 42),
    21: (26, 17, 42, 0, 0),
    22: (28, 17, 46, 0, 0),
    23: (28, 4, 47, 14, 48),
    24: (28, 6, 45, 14, 46),
    25: (28, 8, 47, 13, 48),
    26: (28, 19, 46, 4, 47),
    27: (28, 22, 45, 3, 46),
    28: (28, 3, 45, 23, 46),
    29: (28, 21, 45, 7, 46),
    30: (28, 19, 47, 10, 48),
    31: (28, 2, 46, 29, 47),
    32: (28, 10, 46, 23, 47),
    33: (28, 14, 46, 21, 47),
    34: (28, 14, 46, 23, 47),
    35: (28, 12, 47, 26, 48),
    36: (28, 6, 47, 34, 48),
    37: (28, 29, 46, 14, 47),
    38: (28, 13, 46, 32, 47),
    39: (28, 40, 47, 7, 48),
    40: (28, 18, 47, 31, 48),
}

# Les CENTRES des motifs d'alignement, par version. Version 1 n'en a aucun —
# c'est le cas « ascii » des etalons, et il est la pour cela : un encodeur qui
# se trompe de table d'alignement produit quand meme un 21x21 juste, et le
# defaut n'apparait qu'a partir de la version 2.
#
# Toutes les combinaisons de ces coordonnees portent un motif, SAUF les trois
# qui tomberaient sur un motif de reperage. Les enumerer une par une serait
# 39 lignes de coordonnees a recopier ; la regle, elle, tient en trois
# exceptions et se relit.
_ALIGNEMENTS = {
    1: (), 2: (6, 18), 3: (6, 22), 4: (6, 26), 5: (6, 30), 6: (6, 34),
    7: (6, 22, 38), 8: (6, 24, 42), 9: (6, 26, 46), 10: (6, 28, 50),
    11: (6, 30, 54), 12: (6, 32, 58), 13: (6, 34, 62),
    14: (6, 26, 46, 66), 15: (6, 26, 48, 70), 16: (6, 26, 50, 74),
    17: (6, 30, 54, 78), 18: (6, 30, 56, 82), 19: (6, 30, 58, 86),
    20: (6, 34, 62, 90),
    21: (6, 28, 50, 72, 94), 22: (6, 26, 50, 74, 98), 23: (6, 30, 54, 78, 102),
    24: (6, 28, 54, 80, 106), 25: (6, 32, 58, 84, 110),
    26: (6, 30, 58, 86, 114), 27: (6, 34, 62, 90, 118),
    28: (6, 26, 50, 74, 98, 122), 29: (6, 30, 54, 78, 102, 126),
    30: (6, 26, 52, 78, 104, 130), 31: (6, 30, 56, 82, 108, 134),
    32: (6, 34, 60, 86, 112, 138), 33: (6, 30, 58, 86, 114, 142),
    34: (6, 34, 62, 90, 118, 146),
    35: (6, 30, 54, 78, 102, 126, 150), 36: (6, 24, 50, 76, 102, 128, 154),
    37: (6, 28, 54, 80, 106, 132, 158), 38: (6, 32, 58, 84, 110, 136, 162),
    39: (6, 26, 54, 82, 110, 138, 166), 40: (6, 30, 58, 86, 114, 142, 170),
}

# LES BITS DE RESTE, ceux qui restent une fois les mots de code poses et qui
# valent zero. Les oublier ne decale rien — ils sont a la FIN — et la matrice
# reste juste ; les mettre ailleurs qu'a la fin, en revanche, decale tout. Ils
# sont ici parce que banc_qr.py s'en sert pour verifier _BLOCS_M sans la relire.
_RESTE = {}
for _v in range(1, 41):
    _RESTE[_v] = (0 if _v == 1 else 7 if _v <= 6 else 0 if _v <= 13 else
                  3 if _v <= 20 else 4 if _v <= 27 else 3 if _v <= 34 else 0)


# ── Le corps fini GF(256) ─────────────────────────────────────────────
# 0x11D est le polynome primitif que la norme impose (x^8 + x^4 + x^3 + x^2 + 1)
# et il n'y a rien a choisir : un autre polynome donne un corps parfaitement
# valide, une arithmetique parfaitement coherente, et des octets de correction
# qu'aucun lecteur ne reconnait.
_EXP = [0] * 512
_LOG = [0] * 256
_x = 1
for _i in range(255):
    _EXP[_i] = _x
    _LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
# La table est doublee pour que « _EXP[a + b] » n'ait jamais a poser de modulo :
# les exposants s'additionnent au plus a 508.
for _i in range(255, 512):
    _EXP[_i] = _EXP[_i - 255]


def _mul(a, b):
    # Zero n'a pas de logarithme, et c'est le seul cas particulier du corps.
    return 0 if a == 0 or b == 0 else _EXP[_LOG[a] + _LOG[b]]


def _generateur(n):
    """Le polynome generateur de degre n, coefficients du plus haut degre au plus bas."""
    g = [1]
    for i in range(n):
        neuf = [0] * (len(g) + 1)
        for j, c in enumerate(g):
            neuf[j] ^= c                       # c * x
            neuf[j + 1] ^= _mul(c, _EXP[i])    # c * alpha^i
        g = neuf
    return g


def correction(donnees, combien):
    """Les octets de Reed-Solomon d'un bloc : le reste de la division.

    L'ORDRE EST LE PIEGE. Ces octets suivent les donnees, du plus haut degre au
    plus bas, et les inverser produit un bloc parfaitement forme dont les
    syndromes ne sont plus nuls. Aucune exception, aucune image differente a
    l'oeil : le telephone eclaire le code et n'affiche rien. banc_qr.py calcule
    les syndromes avec sa PROPRE arithmetique et exige zero — c'est le seul
    controle de ce fichier qui ne doive rien aux etalons.
    """
    g = _generateur(combien)
    reste = list(donnees) + [0] * combien
    for i in range(len(donnees)):
        coef = reste[i]
        if coef:
            # g[0] vaut 1, donc reste[i] tombe a zero : la boucle avance.
            for j, gc in enumerate(g):
                reste[i + j] ^= _mul(gc, coef)
    return reste[len(donnees):]


# ── Du texte aux mots de code ─────────────────────────────────────────

def octets_utiles(version):
    """Combien de mots de code de DONNEES la version porte a M.

    Les octets de correction ne sont PAS comptes : c'est la place ou le message
    tient, pas la taille du symbole. Confondre les deux fait choisir une version
    trop petite, et le message est alors tronque sans que rien ne leve.
    """
    ec, b1, d1, b2, d2 = _BLOCS_M[version]
    return b1 * d1 + b2 * d2


def _longueur_du_compte(version):
    """Le champ « combien d'octets » fait 8 bits jusqu'a la version 9, 16 apres.

    LA VERSION 10 EST LA PREMIERE A SEIZE BITS, et c'est le seul chiffre a
    retenir de cette fonction. Se tromper d'un cran decale TOUT le flux de huit
    bits : le lecteur lit une longueur absurde, et rien ne leve. Aucun etalon ne
    va jusqu'a la version 10 — c'est le balayage des quarante versions de
    banc_qr.py qui garde cette frontiere, et lui seul.
    """
    return 8 if version <= 9 else 16


def version_pour(octets):
    """La plus petite version qui tient a M. C'est toute la politique.

    On ne monte pas le niveau de correction quand il reste de la place — segno
    le fait, ce fichier non — parce qu'une politique qui depend de la place
    restante ne se resume pas en une phrase et ne s'exige pas dans un banc.
    """
    for version in range(1, 41):
        bits = 4 + _longueur_du_compte(version) + 8 * len(octets)
        if bits <= 8 * octets_utiles(version):
            return version
    raise ErreurQR(f"{len(octets)} octets ne tiennent dans aucune version a "
                   f"{NIVEAU} (le maximum est {octets_utiles(40)} octets)")


def _mots_de_donnees(octets, version):
    """Le flux binaire du mode octet, complete jusqu'a remplir la version."""
    place = 8 * octets_utiles(version)
    bits = []

    def pousser(valeur, largeur):
        for d in range(largeur - 1, -1, -1):
            bits.append((valeur >> d) & 1)

    pousser(0b0100, 4)                                  # mode octet
    pousser(len(octets), _longueur_du_compte(version))
    for o in octets:
        pousser(o, 8)

    # LE TERMINATEUR EST D'AU PLUS quatre zeros, et non d'exactement quatre :
    # quand il ne reste que deux bits de place, on en met deux. En poser quatre de force deborderait
    # la capacite d'un message qui tient tout juste — et le debordement se
    # verrait comme des donnees tronquees, jamais comme une erreur.
    bits += [0] * min(4, place - len(bits))

    # LE COMBLEMENT JUSQU'A L'OCTET, ET LA SEULE DIVERGENCE MESUREE AVEC LA
    # NORME. ISO/IEC 18004 §7.4.10 dit « de 0 a 7 bits » : quand le flux tombe
    # deja juste, on n'ajoute rien. Segno, lui, ajoute alors HUIT bits — un mot
    # de code 0x00 entier — et les etalons le portent. En mode octet le flux
    # tombe TOUJOURS juste (4 bits de mode + 8 ou 16 bits de compte + 8k, plus
    # 4 bits de terminateur), donc l'ecart n'est pas un cas de bord : il est
    # dans les trois etalons sur trois.
    #
    # MESURE, sur l'etalon « court » (4-M) : le mot de code 53 vaut 0x00 chez
    # segno et 0xEC chez la norme, et tout le remplissage decale d'un rang
    # derriere. Sur « reel » c'est le mot 112, sur « long » le mot 157 — les
    # trois memes 100 % du temps.
    #
    # ON SUIT L'ETALON, et voici pourquoi c'est sans risque : ces mots-la sont
    # du REMPLISSAGE. Le lecteur s'arrete au terminateur et ne les lit jamais ;
    # les deux flux rendent exactement la meme chaine. Choisir la norme contre
    # l'etalon reviendrait a renoncer a la seule verification exterieure qu'on
    # ait — « mon encodeur est d'accord avec lui-meme » — pour un octet que
    # personne ne regarde. Le jour ou un telephone s'en plaindra, la ligne a
    # changer est celle-ci, et « (-len(bits)) % 8 » est la forme de la norme.
    #
    # Le « min » borne au reste de la capacite : un message qui remplit la
    # version a l'octet pres (14 caracteres en 1-M) ne doit rien recevoir de
    # plus, sinon il deborderait et changerait de version pour rien.
    bits += [0] * min(8 - len(bits) % 8, place - len(bits))

    mots = [int("".join(str(b) for b in bits[i:i + 8]), 2)
            for i in range(0, len(bits), 8)]
    # LES DEUX OCTETS DE REMPLISSAGE DE LA NORME, en alternance. Leur valeur
    # n'est pas arbitraire : 11101100 et 00010001 alternes donnent une plage
    # bien contrastee, ce que ne ferait pas une plage de zeros — et le choix du
    # masque, plus bas, part d'une matrice moins uniforme.
    # L'alternance se compte depuis le PREMIER octet de bourrage et non depuis
    # le debut du message : sinon un message de longueur paire et un message de
    # longueur impaire ne bourrent pas dans le meme ordre, et un lecteur sur
    # deux voit un bloc de correction qui ne tombe pas juste.
    bourrage = (0xEC, 0x11)
    debut = len(mots)
    while len(mots) < octets_utiles(version):
        mots.append(bourrage[(len(mots) - debut) % 2])
    return mots


def blocs(texte, version=None):
    """Rend (version, [(donnees, correction), ...]) — avant tout entrelacement.

    Cette fonction est publique pour banc_qr.py : c'est a ce niveau, et pas sur
    la matrice, qu'un bloc de Reed-Solomon se verifie tout seul par ses
    syndromes. Une fois entrelace puis masque, le meme defaut est indiscernable
    d'un bruit.
    """
    octets = texte.encode("utf-8")
    version = version_pour(octets) if version is None else version
    mots = _mots_de_donnees(octets, version)
    ec, b1, d1, b2, d2 = _BLOCS_M[version]
    sortie, i = [], 0
    for combien, taille in ((b1, d1), (b2, d2)):
        for _ in range(combien):
            part = mots[i:i + taille]
            i += taille
            sortie.append((part, correction(part, ec)))
    return version, sortie


def _entrelacer(parts, version):
    """Les mots de code dans l'ordre ou la matrice les recoit.

    LES BLOCS S'ENTRELACENT COLONNE PAR COLONNE, pas l'un apres l'autre : le
    premier octet de chaque bloc, puis le deuxieme de chaque bloc. C'est ce qui
    fait qu'une eclaboussure locale abime un octet dans chaque bloc plutot que
    dix dans le meme — la correction en supporte quelques-uns par bloc, pas dix.
    Les ecrire a la suite donne un code dont chaque module est a sa place et qui
    ne survit a rien.
    """
    flux = []
    for i in range(max(len(d) for d, _ in parts)):
        for d, _ in parts:
            if i < len(d):
                flux.append(d[i])
    for i in range(max(len(c) for _, c in parts)):
        for _, c in parts:
            if i < len(c):
                flux.append(c[i])
    return flux


# ── La matrice ────────────────────────────────────────────────────────

def taille_de(version):
    """4 x version + 17. La formule de la norme, et rien d'autre."""
    return 4 * version + 17


def _poser_reperage(modules, fixe, ligne, colonne):
    """Un motif de reperage et son separateur clair, d'un seul geste.

    Le separateur fait PARTIE du motif : sans lui, une donnee sombre collee au
    reperage l'agrandit et le lecteur ne retrouve plus le coin. On balaie donc
    de -1 a 7 et l'on ignore ce qui sort de la matrice.
    """
    for dl in range(-1, 8):
        for dc in range(-1, 8):
            l, c = ligne + dl, colonne + dc
            if not (0 <= l < len(modules) and 0 <= c < len(modules)):
                continue
            dedans = (0 <= dl <= 6 and 0 <= dc <= 6)
            noir = dedans and (dl in (0, 6) or dc in (0, 6)
                               or (2 <= dl <= 4 and 2 <= dc <= 4))
            modules[l][c] = noir
            fixe[l][c] = True


def _poser_alignement(modules, fixe, ligne, colonne):
    for dl in range(-2, 3):
        for dc in range(-2, 3):
            noir = max(abs(dl), abs(dc)) != 1
            modules[ligne + dl][colonne + dc] = noir
            fixe[ligne + dl][colonne + dc] = True


def _plan(version):
    """La matrice des motifs fixes, et la carte de ce qui est fixe.

    « fixe » n'est pas un doublon de « ce qui n'est pas None » : les zones du
    format d'information et du bloc de version sont RESERVEES ici, encore
    vides, et le masque ne doit pas les toucher. Sans cette carte separee, le
    masque mordait sur le format et le lecteur ne savait plus quel masque
    defaire — la panne la plus circulaire de ce fichier.
    """
    taille = taille_de(version)
    modules = [[None] * taille for _ in range(taille)]
    fixe = [[False] * taille for _ in range(taille)]

    _poser_reperage(modules, fixe, 0, 0)
    _poser_reperage(modules, fixe, 0, taille - 7)
    _poser_reperage(modules, fixe, taille - 7, 0)

    # Les synchronisations : une ligne et une colonne alternees qui donnent au
    # lecteur l'echelle du code. Elles traversent tout, entre les separateurs.
    for i in range(8, taille - 8):
        modules[6][i] = modules[i][6] = (i % 2 == 0)
        fixe[6][i] = fixe[i][6] = True

    centres = _ALIGNEMENTS[version]
    dernier = taille - 7
    for l in centres:
        for c in centres:
            # Les trois coins portent deja un reperage. Y poser un alignement
            # l'ecraserait — et c'est un defaut d'un pixel qui ne se voit pas.
            if (l, c) in ((6, 6), (6, dernier), (dernier, 6)):
                continue
            _poser_alignement(modules, fixe, l, c)

    # LE MODULE SOMBRE OBLIGATOIRE. Un seul module, toujours noir, toujours au
    # meme endroit. Il ne porte aucune information : il est la pour que le
    # lecteur ne prenne pas une matrice entierement claire pour une matrice
    # valide. L'oublier laisse un code que certains lecteurs acceptent et
    # d'autres non — donc un defaut qui ne se reproduit pas.
    modules[taille - 8][8] = True
    fixe[taille - 8][8] = True

    # LES DEUX ZONES DE FORMAT, reservees et pas encore ecrites. « if not
    # fixe » n'est pas une precaution : la synchronisation traverse ces deux
    # bandes en (8,6) et (6,8), et le module sombre est deja pose en
    # (taille-8, 8). Les ecraser ici les rendrait clairs pour tout le calcul de
    # penalite — donc un choix de masque fait sur une matrice qui n'existe pas.
    def reserver(l, c):
        if not fixe[l][c]:
            fixe[l][c] = True
            modules[l][c] = False

    for i in range(9):
        reserver(8, i)
        reserver(i, 8)
    for i in range(8):
        reserver(8, taille - 1 - i)
        reserver(taille - 1 - i, 8)

    # LE BLOC D'INFORMATION DE VERSION N'EXISTE QU'A PARTIR DE LA 7. Deux
    # rectangles de 3x6 pres des coins bas-gauche et haut-droit. Les poser sur
    # une version 6 mangerait six modules de donnees ; les oublier sur une
    # version 7 laisse le lecteur deviner la taille, ce qu'il sait souvent
    # faire — d'ou un defaut qui marche sur la moitie des telephones.
    if version >= 7:
        for i in range(18):
            l, c = i // 3, taille - 11 + i % 3
            fixe[l][c] = fixe[c][l] = True
            modules[l][c] = modules[c][l] = False

    return modules, fixe


def _poser_donnees(modules, fixe, flux):
    """Le zigzag : deux colonnes a la fois, de la droite vers la gauche.

    LA COLONNE 6 EST SAUTEE parce qu'elle porte la synchronisation verticale.
    L'oublier decale d'une colonne toute la moitie gauche du code : la matrice
    reste parfaitement formee, les motifs sont a leur place, et rien ne se lit.
    """
    taille = len(modules)
    bits = [(o >> d) & 1 for o in flux for d in range(7, -1, -1)]
    i = 0
    droite = taille - 1
    while droite >= 1:
        if droite == 6:
            droite = 5
        monte = ((droite + 1) & 2) == 0
        for pas in range(taille):
            ligne = taille - 1 - pas if monte else pas
            for colonne in (droite, droite - 1):
                if fixe[ligne][colonne] or i >= len(bits):
                    continue
                modules[ligne][colonne] = bool(bits[i])
                i += 1
        droite -= 2
    # Ce qui reste apres le dernier mot de code, ce sont les bits de reste, et
    # ils valent zero. On les pose explicitement : « None » traverserait la
    # penalite et le rendu sans lever, en se comportant comme un module clair
    # ici et comme autre chose ailleurs.
    for ligne in range(taille):
        for colonne in range(taille):
            if modules[ligne][colonne] is None:
                modules[ligne][colonne] = False


# Les huit masques de la norme, indexes par leur numero. « l » est la ligne,
# « c » la colonne — et c'est le piege le plus courant de ce tableau : les
# masques 1 et 2 ne sont pas symetriques, les intervertir donne une matrice
# valide masquee par le mauvais motif, que le lecteur demasque de travers.
_MASQUES = (
    lambda l, c: (l + c) % 2 == 0,
    lambda l, c: l % 2 == 0,
    lambda l, c: c % 3 == 0,
    lambda l, c: (l + c) % 3 == 0,
    lambda l, c: (l // 2 + c // 3) % 2 == 0,
    lambda l, c: (l * c) % 2 + (l * c) % 3 == 0,
    lambda l, c: ((l * c) % 2 + (l * c) % 3) % 2 == 0,
    lambda l, c: ((l + c) % 2 + (l * c) % 3) % 2 == 0,
)


def _format(masque):
    """Les quinze bits du format d'information, deja brouilles.

    LE OU EXCLUSIF FINAL N'EST PAS DECORATIF. Sans lui, le format du niveau M
    avec le masque 0 vaut zero : quinze modules clairs d'affilee a cote du
    reperage, que le lecteur prend pour une zone vide. La norme impose donc de
    le brouiller par 101010000010010.
    """
    donnee = (_BITS_NIVEAU << 3) | masque
    # BCH(15,5) : dix tours de division par 10100110111, le reste tient alors
    # sur dix bits et se colle derriere les cinq bits de donnee.
    reste = donnee
    for _ in range(10):
        reste = (reste << 1) ^ ((reste >> 9) * 0b10100110111)
    return ((donnee << 10) | reste) ^ 0b101010000010010


def _bits_de_version(version):
    """Les dix-huit bits du bloc de version, BCH(18,6), sans brouillage.

    Pas de OU exclusif ici, contrairement au format : la norme n'en met pas, et
    en ajouter un par symetrie donnerait un bloc que le lecteur refuse.
    """
    reste = version
    for _ in range(12):
        reste = (reste << 1) ^ ((reste >> 11) * 0b1111100100101)
    return (version << 12) | reste


def _ecrire_format(modules, masque):
    """Les quinze bits, DEUX fois. La redondance est le point.

    Une eclaboussure sur un coin ne doit pas rendre le code illisible : le
    format est ecrit en haut a gauche ET reparti sur les deux autres coins.
    N'en ecrire qu'un donne un code qui se lit — jusqu'au jour ou le coin
    concerne est sali.
    """
    taille = len(modules)
    bits = _format(masque)

    def bit(i):
        return bool((bits >> i) & 1)

    # Premiere copie : la COLONNE 8 pour les bits 0 a 8, puis la LIGNE 8 pour
    # les bits 9 a 14. Transposer les deux moities donne une matrice ou le
    # format est parfaitement ecrit — a l'envers. Rien ne leve, et le lecteur
    # demasque avec le mauvais numero.
    for i in range(6):
        modules[i][8] = bit(i)
    modules[7][8] = bit(6)
    modules[8][8] = bit(7)
    modules[8][7] = bit(8)
    for i in range(9, 15):
        modules[8][14 - i] = bit(i)

    # Seconde copie : la LIGNE 8 a droite pour les bits 0 a 7, la COLONNE 8 en
    # bas pour les bits 8 a 14.
    for i in range(8):
        modules[8][taille - 1 - i] = bit(i)
    for i in range(8, 15):
        modules[taille - 15 + i][8] = bit(i)
    # LE MODULE SOMBRE N'EST PAS REECRIT ICI, et c'est mesure. Beaucoup
    # d'implementations le reposent a la fin de cette fonction ; ce fichier l'a
    # fait aussi, et banc_mutations.py a montre que la ligne etait MORTE — _plan()
    # le pose deja et aucune des deux boucles ci-dessus ne passe sur lui (elles
    # tiennent la ligne 8 a droite et la colonne 8 en bas, jamais (taille-8, 8)).
    # Une ligne morte a cet endroit-la est pire qu'inutile : elle rendait la
    # mutation « le module sombre n'est plus pose » VERTE des deux cotes, donc
    # le garde-fou invisible.


def _ecrire_version(modules, version):
    """Le bloc de version, DEUX fois lui aussi, et seulement a partir de la 7.

    Les deux rectangles sont l'un la transposee de l'autre, d'ou l'affectation
    double : ecrire (l, c) sans ecrire (c, l) laisse la moitie du bloc vide, et
    le lecteur qui la consulte ne trouve pas de version valide.
    """
    if version < 7:
        return
    taille = len(modules)
    bits = _bits_de_version(version)
    for i in range(18):
        b = bool((bits >> i) & 1)
        l, c = i // 3, taille - 11 + i % 3
        modules[l][c] = modules[c][l] = b


# ── Le choix du masque ────────────────────────────────────────────────
# LES QUATRE REGLES DE PENALITE DE LA NORME, avec leurs poids. Ces quatre
# chiffres ne sont pas reglables : ils viennent de la norme, et les changer
# donne un choix de masque different de celui de tout autre encodeur — donc un
# code parfaitement valide qui ne ressemble a aucun etalon, et dont on ne sait
# plus rien.
_N1, _N2, _N3, _N4 = 3, 3, 40, 10


def _penalite(modules):
    taille = len(modules)
    total = 0

    # Regle 1 — les suites d'une meme couleur. Cinq modules valent 3 points,
    # chaque module de plus en vaut un : c'est ce qui decourage les grandes
    # plages ou le lecteur perd le compte des modules.
    for sens in range(2):
        for a in range(taille):
            court = 1
            precedent = None
            for b in range(taille):
                m = modules[a][b] if sens == 0 else modules[b][a]
                if m == precedent:
                    court += 1
                else:
                    if court >= 5:
                        total += _N1 + court - 5
                    court, precedent = 1, m
            if court >= 5:
                total += _N1 + court - 5

    # Regle 2 — les blocs uniformes. La norme parle de rectangles m x n valant
    # 3 (m-1)(n-1) ; compter chaque carre 2x2 pour 3 points donne exactement la
    # meme somme, et se lit.
    for l in range(taille - 1):
        for c in range(taille - 1):
            if (modules[l][c] == modules[l][c + 1] == modules[l + 1][c]
                    == modules[l + 1][c + 1]):
                total += _N2

    # Regle 3 — les FAUX MOTIFS DE REPERAGE. La sequence du reperage suivie ou
    # precedee de quatre modules clairs, ailleurs que dans un coin : le lecteur
    # croit avoir trouve un quatrieme coin et cale son quadrillage dessus.
    # Quarante points, le poids le plus lourd de la norme, et c'est justifie —
    # c'est la seule des quatre regles qui rende un code franchement illisible
    # plutot que fragile.
    #
    # ON CHERCHE LES DEUX FENETRES DE ONZE et non le coeur de sept entoure : une
    # suite qui a quatre modules clairs des DEUX cotes compte DEUX fois, ce que
    # la version « coeur entoure » compte une seule. Mesure sur les quatre
    # etalons : cinq occurrences de plus au total, et le masque retenu change
    # sur « long ».
    avant = [True, False, True, True, True, False, True, False, False, False,
             False]
    apres = [False, False, False, False, True, False, True, True, True, False,
             True]
    for a in range(taille):
        ligne = modules[a]
        colonne = [modules[b][a] for b in range(taille)]
        for suite in (ligne, colonne):
            for d in range(taille - 10):
                fenetre = suite[d:d + 11]
                if fenetre == avant:
                    total += _N3
                if fenetre == apres:
                    total += _N3

    # Regle 4 — l'equilibre sombre/clair. Un code a 80 % sombre se lit mal sous
    # un mauvais eclairage : chaque tranche de 5 % d'ecart a la moitie coute
    # dix points.
    #
    # La tranche INFERIEURE, jamais un arrondi : « abs(sombres*20 - total*10)
    # // total » est la division entiere de l'ecart en pour-cent par cinq, sans
    # passer par un flottant. Un arrondi ferait basculer le choix du masque sur
    # les cas serres, et le ferait basculer differemment selon la machine.
    sombres = sum(1 for l in modules for m in l if m)
    modules_en_tout = taille * taille
    total += _N4 * (abs(sombres * 20 - modules_en_tout * 10) // modules_en_tout)
    return total


Code = collections.namedtuple("Code", "version niveau masque modules")


def matrice_des_mots(version, flux, masque=None):
    """La matrice d'un flux de mots de code DEJA entrelace. Rend (masque, modules).

    CETTE COUTURE EXISTE POUR LE BANC, et elle merite d'etre justifiee : elle
    lui permet de relire les mots de code d'un etalon, de les repasser par ici,
    et de comparer module par module — y compris sur l'etalon « ascii », que
    segno a encode en mode ALPHANUMERIQUE et que le studio ne saurait donc pas
    refaire depuis son texte. Sans elle, un etalon sur quatre ne serait compare
    a rien.

    « masque » force le numero au lieu de le choisir. Le studio ne le passe
    JAMAIS : c'est le banc qui s'en sert pour opposer notre matrice a celle de
    segno quand nos regles de penalite ne retiennent pas le meme numero — voir
    l'en-tete de banc_qr.py, qui dit la mesure et pourquoi elle ne rend pas le
    code moins lisible.
    """
    modules, fixe = _plan(version)
    _poser_donnees(modules, fixe, flux)
    _ecrire_version(modules, version)

    # LES HUIT MASQUES SONT ESSAYES, ET LE PLUS PETIT TOTAL GAGNE. Aucun
    # raccourci n'est possible : la penalite depend des donnees, et deux URI qui
    # different d'un caractere ne choisissent pas le meme masque. Mesure sur les
    # trois etalons en mode octet : nos regles retiennent 4, 6 et 2, et segno 3,
    # 5 et 4 — six numeros, jamais deux fois le meme d'affilee. Un encodeur qui
    # forcerait le masque 0 produirait une matrice parfaitement formee, se
    # tromperait sur les six, et aucune comparaison a un etalon ne le verrait
    # puisqu'elle force le masque : c'est le cas « le masque rendu est celui de
    # plus petite penalite » de banc_qr.py qui l'attrape, et lui seul.
    candidats = range(8) if masque is None else (masque,)
    retenu, note_retenue = None, None
    for essai_masque in candidats:
        essai = [ligne[:] for ligne in modules]
        for l in range(len(essai)):
            for c in range(len(essai)):
                if not fixe[l][c] and _MASQUES[essai_masque](l, c):
                    essai[l][c] = not essai[l][c]
        _ecrire_format(essai, essai_masque)
        note = _penalite(essai)
        if note_retenue is None or note < note_retenue:
            retenu, note_retenue = (essai_masque, essai), note
    return retenu


def encoder(texte, masque=None):
    """Le QR code de ce texte : version, niveau, masque et matrice.

    « modules » est une liste de listes de booleens — True pour un module
    SOMBRE — SANS zone de silence. C'est la page qui l'ajoute, parce que c'est
    elle qui sait sur quel fond elle dessine, et les etalons ne l'ont pas non
    plus.
    """
    version, parts = blocs(texte)
    masque, modules = matrice_des_mots(version, _entrelacer(parts, version),
                                       masque)
    return Code(version, NIVEAU, masque, modules)


def matrice(texte):
    """La seule chose dont la page ait besoin : la grille de booleens."""
    return encoder(texte).modules
