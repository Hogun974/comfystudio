#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L'encodeur QR, mesure contre segno et contre l'algebre — jamais contre lui-meme.

    python banc_qr.py

POURQUOI CE BANC EST LE PLUS NECESSAIRE DU DEPOT. Un encodeur QR ecrit a la main
peut etre parfaitement coherent avec lui-meme et produire une image qu'aucun
telephone ne lit : un masque mal choisi, un octet de correction dans le mauvais
ordre, un motif d'alignement place a un pixel pres. Rien de tout cela ne leve, et
« ca ressemble a un QR code » est tout ce qu'on saurait. La seule mesure qui
vaille est la comparaison a une implementation qu'on n'a pas ecrite — le meme
raisonnement que les vecteurs de la RFC 6238 pour le TOTP, et la meme necessite.

QUATRE ETAGES, ET CHACUN TIENT L'ETAGE AU-DESSUS :

  1. LES SYNDROMES DE REED-SOLOMON, qui ne doivent RIEN aux etalons. Les mots de
     code d'un bloc forment un polynome divisible par le polynome generateur :
     evalue en alpha^0 .. alpha^(n-1), il vaut zero. Ce banc recalcule cela avec sa
     PROPRE arithmetique de GF(256) — le corps est reconstruit ici, en six
     lignes, a partir du polynome primitif 0x11D ecrit en toutes lettres — et
     n'emprunte a qr.py que la table des blocs. Un octet de correction inverse,
     un bloc coupe au mauvais endroit, un entrelacement decale : les syndromes
     cessent d'etre nuls. C'est ce controle qui permettra d'ajouter un cas sans
     etalon.
  2. LA RELECTURE DES ETALONS. Le banc relit les mots de code dans la matrice
     d'un etalon — il defait le masque que le format d'information y annonce,
     puis parcourt le zigzag a l'envers — et exige que leurs syndromes soient
     nuls. Ce n'est pas circulaire : si le plan des motifs fixes ou le zigzag
     etaient faux, la relecture rendrait des octets brouilles et les syndromes
     rougiraient. C'est l'etage 1 qui tient celui-ci.
  3. LA MATRICE, MODULE PAR MODULE. Notre encodeur refait chaque etalon et le
     banc compare les 6364 modules des quatre cas un par un ; un ecart, et il
     dit lequel et ou.
  4. LE MESSAGE, RELU EN ENTIER. Les trois etages precedents mesurent des
     morceaux — des blocs qui se corrigent, des modules a leur place — et aucun
     ne dit que le TEXTE ressort. Le dernier defait tout le chemin d'un lecteur
     et exige l'URI caractere pour caractere. Sans lui, un indicateur de mode ou
     un champ de longueur faux passerait les trois autres.

DEUX ECARTS AVEC SEGNO SONT CONNUS, MESURES, ET DITS ICI PLUTOT QUE CACHES.

  - LE MASQUE. Nos regles de penalite retiennent 4, 6, 2 et 2 la ou segno a
    retenu 3, 5, 4 et 0. Les huit masques sont legaux — le numero est ecrit dans
    le format d'information et le lecteur defait celui qu'on annonce —, et avec
    le masque de segno force, nos matrices sont IDENTIQUES aux siennes. La
    comparaison module par module se fait donc avec ce masque force, et le choix
    lui-meme est mesure autrement : le banc verifie, pour les HUIT masques, que
    le numero annonce dans la matrice est bien celui applique, en relisant les
    mots de code par le chemin d'un telephone. C'est ce qui rend le code
    lisible ; le classement des huit ne l'est pas.
    CE QUI A ETE ESSAYE AVANT DE S'ARRETER LA, le 3 septembre 2026 : les regles
    de la norme telles que python-qrcode les ecrit, la variante a fenetres de
    onze modules, celle de l'edition 2015 avec la bordure claire virtuelle
    (nayuki), la penalite calculee avant l'ecriture du format, la penalite
    calculee avec les zones reservees mises a une valeur sentinelle, et la
    penalite calculee sur une matrice entouree de sa zone de silence — six
    lectures, plus un balayage de 5600 combinaisons de variantes et de poids.
    AUCUNE ne rend le choix de segno sur « court » : le masque 4 y gagne dans
    les six, et l'ecart avec le 3 de segno va de 58 a 160 points selon la
    lecture. Continuer aurait voulu dire ajuster des poids sur quatre cas, ce
    qui est exactement l'ajustement creux que CONTRIBUTING.md refuse.
  - LE REMPLISSAGE. La norme (ISO/IEC 18004 §7.4.10) comble « de 0 a 7 bits »
    jusqu'a l'octet ; segno en met HUIT quand le flux tombe deja juste, soit un
    mot de code 0x00 de plus. En mode octet le flux tombe TOUJOURS juste, donc
    l'ecart est dans les trois etalons sur trois. qr.py suit l'etalon, et le
    banc le mesure a l'endroit ou cela se voit : le mot de code qui suit le
    terminateur. Ces mots-la sont du remplissage — le lecteur s'arrete au
    terminateur —, les deux flux rendent la meme chaine.

Aucun reseau, aucune carte, aucun studio : ce banc n'importe que qr.py et
etalons_qr.py, qui n'importent que la bibliotheque standard.
"""
import io
import os
import sys

# LA CONSOLE WINDOWS ECRIT EN cp1252, et ce banc n'importe pas serveur.py —
# c'est serveur.py qui reconfigure la sortie pour tout le reste du depot (voir
# sa tete de fichier). Sans ces quatre lignes, le banc MEURT sur son propre
# affichage au premier titre de section : « UnicodeEncodeError: 'charmap' codec
# can't encode characters », une pile d'appels a la place du verdict.
for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)

import qr  # noqa: E402
from etalons_qr import ETALONS  # noqa: E402

ok, rate = [], []


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


# ══ L'arithmetique du banc, ecrite ICI et pas empruntee ════════════════
# LE CORPS EST RECONSTRUIT, et c'est tout l'interet. Si le banc appelait
# qr._mul(), une table exponentielle fausse s'annulerait des deux cotes et les
# syndromes seraient nuls sur un bloc faux — la definition meme de l'assertion
# creuse. 0x11D est le polynome primitif que la norme impose, ecrit en toutes
# lettres ici comme il l'est la-bas : c'est la SEULE chose que les deux
# partagent, et c'est une constante de la norme, pas du code.
_E = [0] * 512
_L = [0] * 256
_v = 1
for _i in range(255):
    _E[_i] = _v
    _L[_v] = _i
    _v <<= 1
    if _v & 0x100:
        _v ^= 0x11D
for _i in range(255, 512):
    _E[_i] = _E[_i - 255]


def _fois(a, b):
    return 0 if a == 0 or b == 0 else _E[_L[a] + _L[b]]


def syndromes(mots, combien):
    """Les « combien » syndromes du bloc. Tous nuls = le bloc se corrige.

    On evalue le polynome des mots de code en alpha^0 .. alpha^(combien-1) par
    Horner. C'est la definition d'un code de Reed-Solomon, et elle ne suppose
    rien de la facon dont les octets de correction ont ete calcules : un ordre
    inverse, un generateur de mauvais degre, un bloc coupe au mauvais endroit y
    laissent une valeur non nulle.

    LES RACINES COMMENCENT A alpha^0, ET C'EST LE PIEGE DE CE FICHIER. Le
    generateur du QR est le produit des (x - alpha^i) pour i de 0 a combien-1 ;
    beaucoup de traites de Reed-Solomon partent de alpha^1, et ce banc l'a
    d'abord fait — les syndromes etaient alors non nuls sur des blocs
    parfaitement justes, y compris ceux de segno. Un banc qui rougit sur tout
    n'attrape rien.
    """
    sortie = []
    for k in range(combien):
        acc = 0
        for m in mots:
            acc = _fois(acc, _E[k]) ^ m
        sortie.append(acc)
    return sortie


# ══ Relire une matrice comme le ferait un telephone ════════════════════

def masque_annonce(grille):
    """Le numero de masque ecrit dans le format d'information de la matrice.

    On lit la PREMIERE copie, celle du coin haut-gauche, et l'on defait le
    brouillage 101010000010010 de la norme. Rendre aussi le niveau permet de
    verifier que la matrice annonce bien M, ce qu'aucune comparaison de modules
    ne dirait separement.
    """
    bits = [grille[i][8] for i in range(6)]
    bits += [grille[7][8], grille[8][8], grille[8][7]]
    bits += [grille[8][14 - i] for i in range(9, 15)]
    valeur = 0
    for i, b in enumerate(bits):
        valeur |= (1 if b else 0) << i
    valeur ^= 0b101010000010010
    return (valeur >> 13) & 3, (valeur >> 10) & 7


def relire(grille):
    """Les mots de code entrelaces d'une matrice, masque defait.

    LE CHEMIN D'UN TELEPHONE, et pas un raccourci : on lit le masque dans le
    format, on le defait, puis on parcourt le zigzag a l'envers. Le banc emprunte
    a qr.py la carte des modules fixes — s'il la recopiait, elle divergerait, et
    c'est le defaut que banc_mutations.py a trouve trois fois dans ce depot.
    Ce que ce partage pourrait cacher, l'etage des syndromes le rattrape : un
    plan faux rend des octets brouilles, et les syndromes rougissent.
    """
    taille = len(grille)
    version = (taille - 17) // 4
    _, fixe = qr._plan(version)
    _, masque = masque_annonce(grille)
    nu = [[grille[l][c] != (not fixe[l][c] and qr._MASQUES[masque](l, c))
           for c in range(taille)] for l in range(taille)]
    bits, droite = [], taille - 1
    while droite >= 1:
        if droite == 6:
            droite = 5
        monte = ((droite + 1) & 2) == 0
        for pas in range(taille):
            ligne = taille - 1 - pas if monte else pas
            for colonne in (droite, droite - 1):
                if not fixe[ligne][colonne]:
                    bits.append(1 if nu[ligne][colonne] else 0)
        droite -= 2
    return [int("".join(str(b) for b in bits[i:i + 8]), 2)
            for i in range(0, len(bits) - len(bits) % 8, 8)]


def desentrelacer(flux, version):
    """Le flux entrelace redecoupe en blocs (donnees + correction).

    L'entrelacement prend un octet dans chaque bloc a tour de role ; le defaire
    demande de savoir ou chaque bloc s'arrete, donc la table de qr.py. Si cette
    table etait fausse, les blocs seraient coupes de travers et leurs syndromes
    ne seraient pas nuls — c'est ainsi que ce banc la verifie sans la relire.
    """
    ec, b1, d1, b2, d2 = qr._BLOCS_M[version]
    tailles = [d1] * b1 + [d2] * b2
    donnees = [[] for _ in tailles]
    i = 0
    for rang in range(max(tailles)):
        for n, t in enumerate(tailles):
            if rang < t:
                donnees[n].append(flux[i])
                i += 1
    corrections = [[] for _ in tailles]
    for rang in range(ec):
        for n in range(len(tailles)):
            corrections[n].append(flux[i])
            i += 1
    return [(d, c) for d, c in zip(donnees, corrections)]


def texte_des_matrices(a, b):
    """Le premier module qui differe, en ligne et colonne. Vide si identiques."""
    for l in range(len(a)):
        for c in range(len(a[l])):
            if a[l][c] != b[l][c]:
                return (f"ligne {l}, colonne {c} : attendu "
                        f"{'sombre' if b[l][c] else 'clair'}, obtenu "
                        f"{'sombre' if a[l][c] else 'clair'}")
    return ""


def en_booleens(lignes):
    return [[c == "1" for c in ligne] for ligne in lignes]


# ══ Le sol : sans etalons, ce banc ne mesure rien ══════════════════════
# VERT A VIDE EST LE DEFAUT QUE CE DEPOT A DEJA PAYE TROIS FOIS. Toutes les
# boucles ci-dessous passent sur une liste vide, et le banc sortirait vert en
# n'ayant rien compare. Le sol est pris ici, avant tout le reste, et il compte
# aussi les VERSIONS distinctes : quatre etalons du meme 21x21 ne couvriraient
# ni les motifs d'alignement (a partir de la 2) ni le bloc d'information de
# version (a partir de la 7).
print("\n  ── il y a bien quelque chose a mesurer ──")
dit(len(ETALONS) >= 4, "la liste des etalons n'est pas vide",
    f"{len(ETALONS)} cas")
_versions = sorted({(len(m) - 17) // 4 for _, _, _, m in ETALONS})
dit(len(_versions) >= 4, "et ils ne sont pas tous de la meme version",
    f"versions {_versions}")
dit(any(v == 1 for v in _versions), "dont une version 1, SANS motif d'alignement",
    "le seul cas ou la table d'alignement ne peut pas cacher une faute")
dit(any(v >= 7 for v in _versions),
    "et une version 7 ou plus, AVEC le bloc d'information de version",
    "il n'existe pas en dessous, et l'oublier ne leve pas")
dit(all(d.endswith("-M") for _, _, d, _ in ETALONS),
    "et les quatre sont au niveau M, celui que le studio demande",
    ", ".join(d for _, _, d, _ in ETALONS))

# ══ Etage 1 : l'algebre, qui ne doit rien aux etalons ══════════════════
print("\n  ── les syndromes de Reed-Solomon, sans aucun etalon ──")

# LE BANC S'EPROUVE AVANT DE JUGER. Un controle de syndromes qui rendrait
# toujours zero — un corps mal construit, une boucle qui ne tourne pas — passerait
# tous les cas ci-dessous sans rien mesurer. On lui presente donc d'abord un bloc
# JUSTE, puis le meme avec deux octets de correction echanges : le premier doit
# etre nul, le second non.
_essai = list(b"ComfyStudio, un bloc d'essai de vingt-cinq")
_corr = qr.correction(_essai, 18)
dit(not any(syndromes(_essai + _corr, 18)),
    "un bloc juste a ses dix-huit syndromes nuls",
    f"{len(_essai)} octets de donnees, 18 de correction")
_abime = _corr[:]
_abime[3], _abime[9] = _abime[9], _abime[3]
dit(any(syndromes(_essai + _abime, 18)),
    "et DEUX octets de correction echanges les rendent non nuls",
    "sans quoi ce controle serait vrai de n'importe quoi")
_tordu = _essai[:]
_tordu[0] ^= 1
dit(any(syndromes(_tordu + _corr, 18)),
    "un seul bit de donnee retourne aussi",
    "un octet de donnee sur quarante et un")

# ET LE CORPS DU BANC EST BIEN CELUI DE LA NORME. Sans ces deux lignes, un corps
# construit sur un autre polynome primitif donnerait une arithmetique coherente,
# des syndromes nuls sur ses propres blocs, et ne mesurerait rien de qr.py.
dit(_E[8] == 0x1D and _E[254] == 0x8E and _L[1] == 0,
    "le corps du banc est bien GF(256) sur 0x11D",
    f"alpha^8 = {_E[8]:#x}, alpha^254 = {_E[254]:#x}")

# ══ Etage 2 : les etalons relus, et leurs syndromes ════════════════════
print("\n  ── les etalons se relisent, et leurs blocs se corrigent ──")
for nom, texte, designation, lignes in ETALONS:
    grille = en_booleens(lignes)
    version = (len(grille) - 17) // 4
    niveau, masque = masque_annonce(grille)
    dit(niveau == 0b00,
        f"« {nom} » annonce le niveau M dans son format d'information",
        f"deux bits a {niveau:02b}, et M vaut 00 — jamais 01, qui est L")
    flux = relire(grille)
    ec = qr._BLOCS_M[version][0]
    parts = desentrelacer(flux, version)
    faux = [i for i, (d, c) in enumerate(parts) if any(syndromes(d + c, ec))]
    dit(not faux,
        f"« {nom} » : ses {len(parts)} bloc(s) relus ont tous leurs syndromes nuls",
        f"blocs fautifs {faux}" if faux
        else f"{version}-M, masque {masque}, {ec} octets de correction par bloc")

# ══ Etage 3 : la matrice, module par module ════════════════════════════
print("\n  ── la matrice, module par module contre segno ──")

# LE MASQUE DE SEGNO EST FORCE ICI, et l'en-tete dit pourquoi : nos regles de
# penalite en retiennent un autre sur trois cas sur quatre, les huit sont
# legaux, et la matrice est identique des lors qu'on compare a masque egal. Le
# masque n'est pas pris dans un tableau ecrit a la main : il est LU dans
# l'etalon, donc il ne peut pas deriver de lui.
#
# « ascii » PASSE PAR SES PROPRES MOTS DE CODE et non par son texte : segno l'a
# encode en mode ALPHANUMERIQUE (son premier mot de code vaut 0x20, soit
# l'indicateur 0010 ; le mode octet ecrit 0100), et qr.py ne connait que le mode
# octet. Le refaire depuis « HELLO WORLD » donnerait une matrice legale et
# differente. Ce qui reste mesure sur lui — et c'est l'essentiel de ce fichier —
# c'est le plan des motifs fixes d'un 21x21, le zigzag, le masque et les deux
# copies du format.
compares = 0
for nom, texte, designation, lignes in ETALONS:
    attendu = en_booleens(lignes)
    version = (len(attendu) - 17) // 4
    _, masque = masque_annonce(attendu)
    _, obtenu = qr.matrice_des_mots(version, relire(attendu), masque=masque)
    ecart = texte_des_matrices(obtenu, attendu)
    compares += len(attendu) ** 2
    dit(not ecart,
        f"« {nom} » ({designation}) se refait module par module depuis ses mots "
        f"de code",
        ecart or f"{len(attendu)}x{len(attendu)} = {len(attendu) ** 2} modules")
dit(compares == sum(len(m) ** 2 for _, _, _, m in ETALONS) and compares > 6000,
    "et le compte des modules compares est bien celui de TOUS les etalons",
    f"{compares} modules")

print("\n  ── et depuis le TEXTE, pour les trois cas en mode octet ──")
# LA MOITIE QUI MANQUE A L'ETAGE PRECEDENT. Refaire la matrice depuis les mots de
# code de l'etalon ne mesure pas le chemin texte -> octets -> blocs ->
# correction -> entrelacement. C'est ici qu'il l'est, et c'est le chemin que le
# studio emprunte reellement.
octet = [(n, t, d, m) for n, t, d, m in ETALONS
         if relire(en_booleens(m))[0] >> 4 == 0b0100]
# LE COMPTE SE DEDUIT, IL NE S'ECRIT PAS. Cette ligne disait « trois etalons
# sur quatre » : le nombre etait recopie a cote de la liste qui le donne, et
# ajouter le cinquieme etalon — celui de la version que le studio emet
# vraiment — l'a fait rougir alors que RIEN n'etait casse. C'est le troisieme
# comptage a la main pris en defaut dans ce depot en deux jours, apres
# FICHIERS_SUIVIS et SEUIL_TENU.
#
# CE QU'ON EXIGE VRAIMENT est autre chose que le nombre : que tous les etalons
# soient en mode octet SAUF ceux dont on sait pourquoi. Un etalon neuf qui
# sortirait en alphanumerique sans qu'on l'ait voulu doit rougir ici ; en
# ajouter un en mode octet ne doit rien changer.
_autres = [n for n, _t, _d, m in ETALONS
           if relire(en_booleens(m))[0] >> 4 != 0b0100]
dit(_autres == ["ascii"] and len(octet) == len(ETALONS) - 1,
    "tous les etalons sont en mode octet, sauf « ascii » qui en dit la raison",
    f"{len(octet)}/{len(ETALONS)} en octet ; hors mode octet : {_autres} — "
    "« ascii » porte l'indicateur 0010, alphanumerique : segno choisit le mode "
    "le plus court, qr.py n'en connait qu'un")
for nom, texte, designation, lignes in octet:
    attendu = en_booleens(lignes)
    _, masque = masque_annonce(attendu)
    code = qr.encoder(texte, masque=masque)
    ecart = texte_des_matrices(code.modules, attendu)
    dit(not ecart,
        f"« {nom} » ({designation}) se refait module par module depuis son TEXTE",
        ecart or f"{len(attendu) ** 2} modules, {len(texte)} caracteres")

# ══ La politique de version, mesuree a PART de la matrice ══════════════
print("\n  ── la plus petite version qui tient a M, et pas plus ──")
# ELLE EST MESUREE SEPAREMENT, et ce n'est pas une redondance avec la comparaison
# des matrices : celle-ci force la version lue dans l'etalon. Si version_pour()
# se trompait d'un cran, la comparaison passerait quand meme et le studio
# produirait des codes plus gros — ou, dans l'autre sens, leverait sur une URI
# ordinaire.
for nom, texte, designation, lignes in octet:
    code = qr.encoder(texte)
    dit(f"{code.version}-{code.niveau}" == designation,
        f"« {nom} » : {designation}, ni plus ni moins",
        f"obtenu {code.version}-{code.niveau} pour {len(texte)} caracteres")

# ET LA POLITIQUE EST EXACTE AUX DEUX BORDS. Sans ces deux cas, une politique qui
# monterait systematiquement d'une version passerait les trois cas ci-dessus si
# les etalons tombaient tous loin d'un bord.
def tient_juste(version):
    """Le plus long message en octets que cette version prenne a M.

    L'en-tete du mode octet coute 4 bits d'indicateur plus 8 ou 16 bits de
    compte : le calculer ici plutot que de le recopier de qr.py le laisserait
    deriver, mais le recopier de qr.py rendrait le cas circulaire. On l'ecrit
    donc a partir de la NORME — 4 bits, puis 8 jusqu'a la version 9 et 16
    au-dela — et c'est cette frontiere-la que le cas eprouve aussi.
    """
    return (8 * qr.octets_utiles(version) - 4 - (8 if version <= 9 else 16)) // 8


for combien in range(1, 41):
    juste = tient_juste(combien)
    obtenu = qr.version_pour(b"a" * juste)
    if obtenu != combien:
        dit(False, f"la version {combien} devrait prendre {juste} octets",
            f"version_pour() rend {obtenu}")
        break
    trop = qr.version_pour(b"a" * (juste + 1)) if combien < 40 else 41
    if trop <= combien:
        dit(False, f"la version {combien} ne devrait PAS prendre "
                   f"{juste + 1} octets", f"version_pour() rend {trop}")
        break
else:
    dit(True, "et pour les quarante versions, un octet de plus fait monter d'un cran",
        f"1-M tient {tient_juste(1)} octets, 9-M {tient_juste(9)}, 10-M "
        f"{tient_juste(10)} — le compte passe de 8 a 16 bits entre les deux")

# UNE URI QUI NE TIENT NULLE PART LEVE UNE ERREUR NOMMEE, et ne rend pas une
# matrice tronquee. Un QR code tronque se dessine, s'affiche, et ne se lit pas.
_leve = False
try:
    qr.encoder("x" * (qr.octets_utiles(40) + 1))
except qr.ErreurQR:
    _leve = True
dit(_leve, "et un texte trop long leve ErreurQR au lieu de tronquer",
    f"{qr.octets_utiles(40)} octets est le maximum a M")

# ══ Le masque annonce est celui applique, pour les huit ════════════════
print("\n  ── le masque annonce est celui qui a ete applique ──")
# CE QUE LE CHOIX DU MASQUE NE MESURE PAS, CECI LE MESURE. Le classement des huit
# masques n'est pas verifiable contre une autorite exterieure (voir l'en-tete),
# mais ce qui rend un code LISIBLE l'est : que le numero ecrit dans le format
# soit celui qu'on a applique. Un decalage la — le masque 3 applique et le 4
# annonce — donne une matrice parfaitement formee que rien ne lit.
_uri = ETALONS[1][1]
_version, _parts = qr.blocs(_uri)
_attendus = qr._entrelacer(_parts, _version)
_faux = []
for _m in range(8):
    _, _grille = qr.matrice_des_mots(_version, _attendus, masque=_m)
    _niveau, _lu = masque_annonce(_grille)
    if _lu != _m or _niveau != 0 or relire(_grille)[:len(_attendus)] != _attendus:
        _faux.append(_m)
dit(not _faux,
    "les huit masques s'annoncent juste et se defont pour rendre les memes mots",
    f"masques fautifs {_faux}" if _faux else "8/8, relus par le chemin d'un "
    "telephone")

# ET LES HUIT DONNENT HUIT MATRICES DIFFERENTES. Sans ce cas, un masque qui ne
# serait jamais applique — la boucle qui ne mord pas — passerait le cas
# precedent : les mots relus seraient justes puisque rien n'aurait ete masque.
_grilles = {tuple(tuple(l) for l in qr.matrice_des_mots(_version, _attendus,
                                                       masque=_m)[1])
            for _m in range(8)}
dit(len(_grilles) == 8, "et les huit sont bien huit matrices DIFFERENTES",
    f"{len(_grilles)} distinctes sur 8")

# LE CHOIX EST-IL CELUI QUE NOS PROPRES REGLES DESIGNENT ? Il n'y a pas
# d'autorite exterieure pour le classement des huit — segno en retient un autre
# et l'en-tete dit ce qui a ete essaye —, mais il y en a une pour la POLITIQUE :
# « le plus petit total gagne ». Le banc recalcule les huit penalites et exige
# que le masque rendu soit celui de plus petit total. Un encodeur qui forcerait
# le masque 0 — la mutation que CONTRIBUTING.md cite en exemple — passerait tous
# les cas ci-dessus, puisque 0 est legal et que la comparaison aux etalons force
# le masque ; c'est ce cas-ci, et lui seul, qui l'attrape.
_hors = []
_plats = []
for nom, texte, designation, lignes in octet + [("neuf", _cas_neuf, "", "")
                                                for _cas_neuf in [
        "otpauth://totp/ComfyStudio:essai?secret=" + "A" * 32
        + "&issuer=ComfyStudio&algorithm=SHA1&digits=6&period=30"]]:
    code = qr.encoder(texte)
    version, parts = qr.blocs(texte)
    mots = qr._entrelacer(parts, version)
    notes = [qr._penalite(qr.matrice_des_mots(version, mots, masque=m)[1])
             for m in range(8)]
    if code.masque != notes.index(min(notes)):
        _hors.append(f"{nom} : rendu {code.masque}, le moindre est "
                     f"{notes.index(min(notes))}")
    if len(set(notes)) < 2:
        _plats.append(nom)
dit(not _hors and not _plats,
    "le masque rendu est celui de plus petite penalite parmi les huit",
    " / ".join(_hors) or
    (f"penalites toutes egales sur {_plats} : la regle ne mesure rien"
     if _plats else "4 cas, les huit penalites recalculees a chaque fois"))

_choisis = [qr.encoder(t).masque for _, t, _, _ in octet]
_segno = [masque_annonce(en_booleens(m))[1] for _, _, _, m in octet]
dit(all(0 <= m <= 7 for m in _choisis),
    "et il est legal pour chaque cas",
    f"nous {_choisis} — segno {_segno} : voir l'en-tete, les huit sont legaux")

# ══ Les invariants de structure ════════════════════════════════════════
print("\n  ── les invariants de structure ──")
# CE QUE LES ETALONS NE DIRAIENT PAS SI L'ON EN AJOUTAIT UN SANS EUX. Ces
# controles-la se tiennent sur la NORME et non sur segno : ils resteront vrais
# pour un cas qu'on ajouterait demain sans matrice de reference.
_cas = [(n, t) for n, t, _, _ in octet] + [("neuf", "otpauth://totp/"
        "ComfyStudio:essai?secret=" + "A" * 32 + "&issuer=ComfyStudio")]
for nom, texte in _cas:
    code = qr.encoder(texte)
    m = code.modules
    taille = len(m)
    soucis = []

    if taille != 4 * code.version + 17:
        soucis.append(f"taille {taille} au lieu de {4 * code.version + 17}")
    if any(len(ligne) != taille for ligne in m):
        soucis.append("la matrice n'est pas carree")

    # LES TROIS MOTIFS DE REPERAGE, et TROIS et pas quatre : le coin bas-droite
    # est laisse vide expres, c'est lui qui donne au lecteur l'orientation du
    # code. En poser un quatrieme rendrait le code illisible dans un sens sur
    # deux.
    coins = ((0, 0), (0, taille - 7), (taille - 7, 0))
    for (l0, c0) in coins:
        for dl in range(7):
            for dc in range(7):
                noir = (dl in (0, 6) or dc in (0, 6)
                        or (2 <= dl <= 4 and 2 <= dc <= 4))
                if m[l0 + dl][c0 + dc] != noir:
                    soucis.append(f"reperage abime en ({l0 + dl},{c0 + dc})")
    coin = [[m[taille - 7 + dl][taille - 7 + dc] for dc in range(7)]
            for dl in range(7)]
    if all(coin[dl][dc] == (dl in (0, 6) or dc in (0, 6)
                            or (2 <= dl <= 4 and 2 <= dc <= 4))
           for dl in range(7) for dc in range(7)):
        soucis.append("un QUATRIEME reperage en bas a droite")

    # LES SEPARATEURS. Un reperage colle a une donnee sombre s'agrandit, et le
    # lecteur ne retrouve plus le coin.
    for i in range(8):
        if m[7][i] or m[i][7]:
            soucis.append(f"separateur haut-gauche sombre en {i}")
        if m[7][taille - 1 - i] or m[taille - 8][i]:
            soucis.append(f"separateur oppose sombre en {i}")

    # LES MOTIFS DE SYNCHRONISATION. Ils donnent l'echelle : un module sur deux,
    # sur toute la ligne 6 et toute la colonne 6.
    for i in range(8, taille - 8):
        if m[6][i] != (i % 2 == 0) or m[i][6] != (i % 2 == 0):
            soucis.append(f"synchronisation cassee en {i}")

    # LE MODULE SOMBRE OBLIGATOIRE. Il ne porte aucune information ; il est la
    # pour qu'une matrice entierement claire ne passe pas pour valide.
    if not m[taille - 8][8]:
        soucis.append("le module sombre obligatoire est clair")

    # LES MOTIFS D'ALIGNEMENT. Aucun avant la version 2 ; a partir de la 2, un
    # a chaque croisement des centres sauf aux trois coins de reperage.
    centres = qr._ALIGNEMENTS[code.version]
    combien = 0
    for l in centres:
        for c in centres:
            if (l, c) in ((6, 6), (6, taille - 7), (taille - 7, 6)):
                continue
            combien += 1
            for dl in range(-2, 3):
                for dc in range(-2, 3):
                    if m[l + dl][c + dc] != (max(abs(dl), abs(dc)) != 1):
                        soucis.append(f"alignement abime en ({l},{c})")
    attendu_align = 0 if code.version == 1 else len(centres) ** 2 - 3
    if combien != attendu_align:
        soucis.append(f"{combien} alignements au lieu de {attendu_align}")

    dit(not soucis,
        f"« {nom} » ({code.version}-{code.niveau}) : reperage, separateurs, "
        f"synchronisation, module sombre, alignement",
        " / ".join(soucis[:2]) or
        f"{taille}x{taille} = 4x{code.version}+17, {combien} alignement(s)")

# LA TABLE DES BLOCS EST VERIFIEE SANS ETRE RELUE. Le total des mots de code
# d'une version, en bits, plus ses bits de reste, doit remplir EXACTEMENT les
# modules qui ne sont pas des motifs fixes. Cet invariant vient de la norme et
# pas de segno : il attrape un chiffre recopie de travers dans _BLOCS_M pour les
# quarante versions, alors que les etalons n'en couvrent que quatre.
_faux_table = []
for _v in range(1, 41):
    ec, b1, d1, b2, d2 = qr._BLOCS_M[_v]
    mots = b1 * d1 + b2 * d2 + (b1 + b2) * ec
    _, fixe = qr._plan(_v)
    libres = sum(1 for ligne in fixe for x in ligne if not x)
    if mots * 8 + qr._RESTE[_v] != libres:
        _faux_table.append(f"{_v} : {mots * 8 + qr._RESTE[_v]} bits pour "
                           f"{libres} modules")
dit(not _faux_table,
    "et les quarante versions de la table des blocs remplissent exactement leur "
    "matrice",
    " / ".join(_faux_table[:3]) or "40 versions, mots de code + bits de reste = "
    "modules libres")

# ══ Le remplissage, la divergence assumee ══════════════════════════════
print("\n  ── le remplissage, et l'ecart assume avec la norme ──")
# ON MESURE L'ECART PLUTOT QUE DE LE TAIRE. La norme comble « de 0 a 7 bits »
# jusqu'a l'octet, segno en met huit quand le flux tombe deja juste. qr.py suit
# segno, sans quoi les trois etalons en mode octet seraient tous faux — et ce
# n'est sans consequence que parce que ces mots-la sont du remplissage, jamais lus.
# Le jour ou l'on repasserait a la norme, ce cas-ci rougirait et dirait ou.
for nom, texte, designation, lignes in octet:
    version = (len(lignes) - 17) // 4
    mots = qr._mots_de_donnees(texte.encode(), version)
    utile = (4 + qr._longueur_du_compte(version) + 8 * len(texte)) // 8 + 1
    dit(mots[utile] == 0x00 and mots[utile + 1] == 0xEC,
        f"« {nom} » : le mot {utile} vaut 0x00 et le remplissage commence apres",
        f"0x{mots[utile]:02X} puis 0x{mots[utile + 1]:02X} — la norme mettrait "
        f"0xEC des le mot {utile}")
# ET LE COMBLEMENT EST BORNE PAR LA CAPACITE. Un message qui remplit la version
# a l'octet pres ne doit rien recevoir de plus : sans la borne, l'octet de trop
# deborderait la matrice ou ferait monter d'une version pour rien. Quatorze
# octets en 1-M, c'est exactement 128 bits avec le terminateur.
_plein = qr._mots_de_donnees(b"a" * 14, 1)
_creux = qr._mots_de_donnees(b"a" * 12, 1)
dit(len(_plein) == qr.octets_utiles(1) == 16 and 0xEC not in _plein
    and len(_creux) == 16 and _creux[-1] == 0xEC,
    "et un message qui remplit la version a l'octet pres ne recoit aucun "
    "remplissage",
    f"14 octets : {len(_plein)} mots sans 0xEC — 12 octets : le dernier vaut "
    f"0x{_creux[-1]:02X}")

# ══ Ce que la page recoit ══════════════════════════════════════════════
print("\n  ── ce que la page recoit ──")
_code = qr.encoder(ETALONS[1][1])
dit(all(isinstance(x, bool) for ligne in _code.modules for x in ligne),
    "la matrice est faite de booleens, jamais de None",
    "un None se dessinerait comme un module clair ici et autrement ailleurs")
dit(_code.modules[0][0] and _code.modules[0][6],
    "et elle commence au premier module du reperage : AUCUNE zone de silence",
    "c'est la page qui la dessine, et les etalons ne l'ont pas non plus")
dit(qr.matrice(ETALONS[1][1]) == _code.modules,
    "matrice() rend exactement les modules d'encoder()",
    "c'est le seul appel dont le serveur ait besoin")
dit(_code.niveau == qr.NIVEAU == "M",
    "et le niveau annonce est celui du module", _code.niveau)

# ══ Le studio ══════════════════════════════════════════════════════════
print("\n  ── le message se relit en entier, comme le ferait un lecteur ──")
# LE DERNIER ETAGE, ET LE SEUL QUI DISE « CE CODE REND CETTE CHAINE ». Tout ce
# qui precede mesure des morceaux : les syndromes disent que les blocs se
# corrigent, les modules qu'ils sont a leur place. Aucun ne dit que le texte
# ressort. Ici on defait tout le chemin — masque, zigzag, desentrelacement — et
# l'on relit l'en-tete comme la norme le decrit : quatre bits de mode, puis huit
# ou seize bits de longueur, puis les octets. Sans ce cas, un encodeur qui
# ecrirait un mode ou une longueur faux passerait tous les autres.


def relire_le_message(code):
    """Le texte que porte cette matrice, ou une raison de ne pas y arriver."""
    parts = desentrelacer(relire(code.modules), code.version)
    utiles = []
    for donnees, _ in parts:
        utiles += donnees
    bits = [(o >> d) & 1 for o in utiles for d in range(7, -1, -1)]

    def lire(depart, largeur):
        v = 0
        for b in bits[depart:depart + largeur]:
            v = (v << 1) | b
        return v

    mode = lire(0, 4)
    if mode != 0b0100:
        return None, f"mode {mode:04b} et non 0100"
    large = 8 if code.version <= 9 else 16
    combien = lire(4, large)
    debut = 4 + large
    octets = bytes(lire(debut + 8 * i, 8) for i in range(combien))
    # LES BLOCS SONT DESENTRELACES DANS L'ORDRE DES BLOCS, et le message
    # traverse leur frontiere : c'est justement ce que l'entrelacement melange,
    # donc le remettre a l'endroit fait partie de ce qui est mesure ici.
    return octets.decode("utf-8", "replace"), ""


_manques = []
for nom, texte, designation, lignes in octet:
    rendu, souci = relire_le_message(qr.encoder(texte))
    if rendu != texte:
        _manques.append(f"{nom} : {souci or 'texte different'}")
dit(not _manques,
    "les trois URI ressortent CARACTERE POUR CARACTERE de leur propre matrice",
    " / ".join(_manques) or
    f"mode 0100, longueurs {[len(t) for _, t, _, _ in octet]}")

print("\n  ── l'URI reelle du studio ──")
# LE CAS QUE LE STUDIO PRODUIT VRAIMENT, et pas seulement ceux des etalons : un
# secret tire au sort et un nom de compte quelconque. Sans lui, un defaut qui
# n'apparaitrait que sur une longueur non couverte par les quatre etalons
# passerait — et c'est justement la longueur qui fait changer de version.
import mfa  # noqa: E402

_soucis = []
for _nom_compte in ("a", "jordan", "un-nom-de-compte-plutot-long",
                    "prenom.nom@exemple.fr", "j" * 40):
    _uri = mfa.uri(_nom_compte, mfa.secret_neuf())
    _c = qr.encoder(_uri)
    if relire(_c.modules)[:len(qr._entrelacer(qr.blocs(_uri)[1], _c.version))] \
            != qr._entrelacer(qr.blocs(_uri)[1], _c.version):
        _soucis.append(_nom_compte)
    _ec = qr._BLOCS_M[_c.version][0]
    for _d, _corr in desentrelacer(relire(_c.modules), _c.version):
        if any(syndromes(_d + _corr, _ec)):
            _soucis.append(f"{_nom_compte} (syndromes)")
dit(not _soucis,
    "cinq URI d'enrolement se relisent et leurs blocs se corrigent",
    ", ".join(_soucis[:2]) or
    f"versions {sorted({qr.encoder(mfa.uri(n, mfa.secret_neuf())).version for n in ('a', 'jordan', 'j' * 40)})}")

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
for r in rate:
    print(f"    RATE : {r}")
sys.exit(1 if rate else 0)
