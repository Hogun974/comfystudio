#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Le second facteur, mesure contre la RFC et contre le rejeu.

CE BANC MESURE CONTRE UNE AUTORITE EXTERIEURE, et c'est sa raison d'etre. La
RFC 6238 publie ses propres vecteurs de test : un secret connu, six instants,
six codes attendus. Un TOTP maison peut etre parfaitement coherent avec
lui-meme et refuser tous les codes que Google Authenticator produit — un pas de
temps decale, un octet lu dans le mauvais sens, le bit de signe oublie. Le seul
moyen de le savoir est de comparer a ce que le reste du monde calcule.

    Vecteurs : RFC 6238, appendice B. Secret ASCII « 12345678901234567890 »
    (20 octets), T0 = 0, pas de 30 s, HMAC-SHA1. La RFC les donne sur HUIT
    chiffres ; le studio en affiche six, et six est le suffixe de huit — c'est
    la meme troncature, un modulo plus loin. On verifie les deux : si seuls les
    six passaient, un modulo faux resterait invisible.

CE QU'IL MESURE ENSUITE, et qui n'est pas dans la RFC :

  - LE REJEU. Un code TOTP reste valable toute sa fenetre. Sans memoire du
    dernier pas accepte, le meme code rejoue trois fois ouvre trois sessions —
    la faute la plus courante des implementations maison, parce qu'elles
    verifient le code, qui est le facile, et oublient qu'un second facteur
    rejouable ne protege plus contre quelqu'un qui a vu l'ecran.
  - LA DERIVE. Une horloge de telephone derive, et quelqu'un qui tape lentement
    franchit une frontiere de trente secondes au milieu de sa saisie. Un pas de
    chaque cote, pas deux : la RFC dit « at most one time step ».
  - CE QU'UN HUMAIN RECOPIE. Un secret en minuscules, avec les espaces de
    l'affichage, sans remplissage. Refuser ces trois-la renvoie « code
    invalide » a quelqu'un qui n'a rien fait de mal.
  - L'URI, parce qu'une application qui la lit de travers ne le dit pas : elle
    enrole, affiche des codes, et aucun ne marche.

Aucun reseau, aucune carte, aucun studio : ce banc n'importe que mfa.py, qui
n'importe que la bibliotheque standard.

    python banc_mfa.py
"""
import base64
import os
import random
import sys
import time

# LA CONSOLE WINDOWS ECRIT EN cp1252, et ce banc n'importe pas serveur.py —
# c'est serveur.py qui reconfigure la sortie pour tout le reste du depot
# (voir sa tete de fichier). Sans ces quatre lignes, le banc MEURT sur son
# propre affichage au premier titre de section : « UnicodeEncodeError:
# 'charmap' codec can't encode characters », une pile d'appels a la place du
# verdict. Mesure du 2 septembre 2026 : banc_page.py s'arretait ainsi a la
# verification 30 sur 38, et le lanceur de banc_mutations.py ne le voyait pas
# — il pose PYTHONIOENCODING pour ses fils, donc le defaut n'apparaissait
# QUE lorsqu'on lancait le banc a la main, ce que fait tout contributeur.
for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)

import mfa  # noqa: E402

ok, rate = [], []


def dit(vrai, quoi, releve=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok  ' if vrai else 'RATE'} {quoi}"
          + (f" — {releve}" if releve else ""))


# Le secret des vecteurs de la RFC, tel qu'elle l'ecrit : vingt octets ASCII.
SECRET_RFC = base64.b32encode(b"12345678901234567890").decode("ascii")

# RFC 6238, appendice B — la colonne SHA1 uniquement. (instant, code a 8)
VECTEURS = [
    (59,          "94287082"),
    (1111111109,  "07081804"),
    (1111111111,  "14050471"),
    (1234567890,  "89005924"),
    (2000000000,  "69279037"),
    (20000000000, "65353130"),
]

print("\n  ── les vecteurs de la RFC 6238 ──")
faux = [(t, a, mfa.code(SECRET_RFC, quand=t, chiffres=8))
        for t, a in VECTEURS if mfa.code(SECRET_RFC, quand=t, chiffres=8) != a]
dit(not faux,
    "les six codes a huit chiffres de la RFC tombent juste",
    "; ".join(f"t={t} attendu {a} obtenu {o}" for t, a, o in faux)
    or f"{len(VECTEURS)} vecteurs")

# LES SIX CHIFFRES SONT LE SUFFIXE DES HUIT, et le verifier separement n'est pas
# une redondance : c'est le modulo qui differe, et un modulo faux passerait
# inaperçu si l'on ne mesurait que les huit.
faux6 = [(t, a[-6:], mfa.code(SECRET_RFC, quand=t))
         for t, a in VECTEURS if mfa.code(SECRET_RFC, quand=t) != a[-6:]]
dit(not faux6,
    "et les six chiffres du studio en sont le suffixe exact",
    "; ".join(f"t={t} attendu {a} obtenu {o}" for t, a, o in faux6)
    or ", ".join(mfa.code(SECRET_RFC, quand=t) for t, _ in VECTEURS[:3]))

# SANS CETTE LIGNE, LES DEUX PRECEDENTES POURRAIENT ETRE VRAIES DE RIEN. Une
# fonction qui rend toujours la meme chose passerait le cas des six chiffres
# si, par malchance, le vecteur unique tombait juste — et une liste vide de
# vecteurs les passerait tous les deux.
dit(len(VECTEURS) == 6 and len({c for _, c in VECTEURS}) == 6,
    "les six vecteurs sont bien six codes DIFFERENTS",
    f"{len({c for _, c in VECTEURS})} distincts")

print("\n  ── la derive d'horloge ──")
# Une horloge de telephone derive, et l'on tape lentement. Un pas de chaque
# cote, et pas deux.
T = 1_700_000_000
dit(mfa.verifie(SECRET_RFC, mfa.code(SECRET_RFC, quand=T), quand=T) is not None,
    "le code de l'instant present passe", mfa.code(SECRET_RFC, quand=T))
dit(mfa.verifie(SECRET_RFC, mfa.code(SECRET_RFC, quand=T - mfa.PAS),
                quand=T) is not None,
    "celui du pas precedent aussi : trente secondes de retard se pardonnent")
dit(mfa.verifie(SECRET_RFC, mfa.code(SECRET_RFC, quand=T + mfa.PAS),
                quand=T) is not None,
    "celui du pas suivant aussi : une horloge qui avance se pardonne")
dit(mfa.verifie(SECRET_RFC, mfa.code(SECRET_RFC, quand=T - 2 * mfa.PAS),
                quand=T) is None,
    "DEUX pas en arriere, non — la RFC dit « at most one time step »")
dit(mfa.verifie(SECRET_RFC, mfa.code(SECRET_RFC, quand=T + 2 * mfa.PAS),
                quand=T) is None,
    "et deux pas en avant non plus")

print("\n  ── le rejeu ──")
# LE CAS QUI FAIT LA DIFFERENCE ENTRE UN SECOND FACTEUR ET UN THEATRE. Un code
# reste valable toute sa fenetre : sans memoire, le meme code ouvre autant de
# sessions qu'on veut.
c = mfa.code(SECRET_RFC, quand=T)
p = mfa.verifie(SECRET_RFC, c, quand=T)
dit(p is not None and p == mfa.pas_de(T),
    "verifie() rend le PAS accepte, pas un booleen : l'appelant DOIT le garder",
    str(p))
dit(mfa.verifie(SECRET_RFC, c, quand=T, dernier_pas=p) is None,
    "et le meme code repasse avec ce pas en memoire est REFUSE",
    "rejeu ferme")
# ET IL NE FERME PAS TROP. Refuser tout ce qui precede le dernier pas
# empecherait quelqu'un de se reconnecter trente secondes plus tard — le
# remede serait pire que le mal, et il ne se verrait qu'a l'usage.
suivant = mfa.code(SECRET_RFC, quand=T + mfa.PAS)
dit(mfa.verifie(SECRET_RFC, suivant, quand=T + mfa.PAS, dernier_pas=p)
    is not None,
    "mais le code SUIVANT passe : on ferme le rejeu, pas la reconnexion")

print("\n  ── ce qu'un humain recopie ──")
octets = mfa._octets_du_secret(SECRET_RFC)
for nom, variante in (
        ("en minuscules", SECRET_RFC.lower()),
        ("avec les espaces de l'affichage",
         " ".join(SECRET_RFC[i:i + 4] for i in range(0, len(SECRET_RFC), 4))),
        ("sans le remplissage", SECRET_RFC.rstrip("=")),
        ("avec des tirets", "-".join(SECRET_RFC[i:i + 4]
                                     for i in range(0, len(SECRET_RFC), 4)))):
    dit(mfa._octets_du_secret(variante) == octets,
        f"un secret {nom} donne les memes octets")
for mauvais in ("", "   ", "1", "!!!!"):
    leve = False
    try:
        mfa._octets_du_secret(mauvais)
    except mfa.ErreurMFA:
        leve = True
    dit(leve, f"et « {mauvais or '(vide)'} » est refuse par une erreur nommee")

print("\n  ── ce qui n'est pas un code ──")
for saisie in ("", "   ", "abcdef", "12345", "1234567", None):
    dit(mfa.verifie(SECRET_RFC, saisie, quand=T) is None,
        f"« {saisie if saisie is not None else 'None'} » ne passe pas")

# ══ UNE SAISIE PLUS COURTE N'EST PAS UN CODE PLUS FACILE ═══════════════
# LES DEUX CAS CI-DESSUS PASSAIENT DEJA PENDANT QUE LA PORTE ETAIT OUVERTE, et
# c'est la lecon. verifie() a compare, du 2 au 3 septembre 2026, le code attendu
# TRONQUE A LA LONGUEUR DE LA SAISIE : « 7 » etait donc confronte au code modulo
# dix, une chance sur dix par pas de temps, trois pas dans la fenetre. Mesure :
# 549 acceptations sur 2 000 instants tires au hasard — 27,4 % — et 25 sessions
# ouvertes sur 25 avec le seul mot de passe, en 4,8 essais de moyenne.
#
# « 12345 » ne l'a pas vu parce qu'une saisie a cinq chiffres n'avait qu'une
# chance sur cent mille de tomber juste : le cas etait vrai PAR CHANCE, et il
# aurait fallu le relancer cent mille fois pour qu'il mente une fois. Un cas
# qui eprouve une porte probabiliste avec UN tirage ne l'eprouve pas.
#
# ON PROBE DONC LA PORTE EXACTE. Pour chaque longueur fautive, on calcule ce que
# le code d'avant aurait ACCEPTE — le vrai code tronque a cette longueur-la —
# et on exige qu'il soit refuse. Deterministe, et ca rougit a coup sur.
print("\n  ── une saisie plus courte n'est pas un code plus facile ──")
_ouvertes = []
for n in (1, 2, 3, 4, 5, 7, 8):
    # mfa.code(..., chiffres=n) est litteralement la valeur que verifie()
    # calculait quand elle deduisait la longueur de la saisie.
    ce_qui_ouvrait = mfa.code(SECRET_RFC, quand=T, chiffres=n)
    if mfa.verifie(SECRET_RFC, ce_qui_ouvrait, quand=T) is not None:
        _ouvertes.append(f"{n} chiffres : « {ce_qui_ouvrait} »")
dit(not _ouvertes,
    "aucune longueur autre que six n'ouvre, meme avec le bon prefixe",
    ", ".join(_ouvertes) or "sept longueurs fautives, toutes refusees")

# ET LA MESURE EN GRAND, parce qu'un seul instant ne dit rien d'une porte qui
# s'ouvre une fois sur quatre. Deux cents instants, un chiffre au hasard : la
# porte d'avant en laissait passer une cinquantaine.
_hasard = random.Random(20260903)
_passees = sum(
    1 for _ in range(200)
    if mfa.verifie(SECRET_RFC, _hasard.choice("0123456789"),
                   quand=_hasard.randint(1_600_000_000, 1_800_000_000))
    is not None)
dit(_passees == 0,
    "et deux cents saisies a un chiffre, a deux cents instants, n'ouvrent rien",
    f"{_passees}/200 — la version du 2 septembre en laissait passer ~55")

# LA LONGUEUR EST POSEE PAR L'APPELANT, JAMAIS DEDUITE. C'est ce qui permet a
# la RFC de rester verifiable sur huit chiffres sans rouvrir la porte : le banc
# le demande explicitement, une saisie ne peut pas le demander.
dit(mfa.verifie(SECRET_RFC, mfa.code(SECRET_RFC, quand=T, chiffres=8),
                quand=T, chiffres=8) is not None,
    "mais huit chiffres passent quand l'APPELANT les demande",
    "c'est ainsi que les vecteurs de la RFC restent verifiables")
# UN CODE JUSTE MAIS D'UN AUTRE SECRET. Sans ce cas, une fonction qui accepte
# tout ce qui a six chiffres passerait tous les cas ci-dessus.
autre = mfa.secret_neuf()
dit(mfa.verifie(SECRET_RFC, mfa.code(autre, quand=T), quand=T) is None,
    "et le code d'un AUTRE secret non plus",
    mfa.code(autre, quand=T))

print("\n  ── les secrets tires au sort ──")
lot = [mfa.secret_neuf() for _ in range(200)]
dit(len(set(lot)) == 200, "deux cents secrets, deux cents valeurs distinctes",
    f"{len(set(lot))}/200")
dit(all(len(s) == 32 and "=" not in s for s in lot),
    "32 caracteres et AUCUN remplissage : les « = » ne survivent pas a une URL",
    f"{len(lot[0])} caracteres")
dit(all(len(mfa._octets_du_secret(s)) == mfa.OCTETS_SECRET for s in lot),
    "et chacun se relit en vingt octets", str(mfa.OCTETS_SECRET))

print("\n  ── l'URI que l'application lit ──")
u = mfa.uri("jordan", SECRET_RFC)
dit(u.startswith("otpauth://totp/"), "elle est bien une URI otpauth de type totp",
    u[:40])
dit(f"secret={SECRET_RFC}" in u, "elle porte le secret tel quel")
dit("issuer=ComfyStudio" in u and "ComfyStudio%3Ajordan" in u,
    "l'emetteur est ecrit DEUX fois : dans le chemin et en parametre",
    "les applications anciennes lisent l'un, les recentes l'autre")
dit("algorithm=SHA1" in u and "digits=6" in u and "period=30" in u,
    "et les trois parametres sont ecrits meme quand ils valent le defaut",
    "plusieurs applications ne les devinent pas de la meme facon")
# UN NOM DE COMPTE QUI CASSERAIT L'URI. « a:b » et « c/d » sont des separateurs
# dans otpauth:// ; non echappes, l'application lit un autre compte.
sale = mfa.uri("jean:paul/durand", SECRET_RFC)
dit("jean%3Apaul%2Fdurand" in sale,
    "un nom de compte a deux-points ou a barre oblique est echappe",
    sale.split("?")[0])

print("\n  ── les codes de secours ──")
codes = mfa.codes_de_secours()
dit(len(codes) == mfa.CODES_SECOURS == 10,
    "dix codes, et non un « code maitre » qui deviendrait un second mot de passe",
    str(len(codes)))
dit(len(set(codes)) == len(codes), "tous distincts", f"{len(set(codes))}")
interdits = set("01lIoO")
dit(not (set("".join(codes)) & interdits),
    "aucun caractere qu'on confond en recopiant depuis un papier",
    "".join(sorted(set("".join(codes)) & interdits)) or "ni 0/O ni 1/l/I")
dit(mfa.normalise_secours("AB-CD ef GH") == "abcdefgh",
    "la normalisation pardonne la casse, les espaces et les tirets",
    mfa.normalise_secours("AB-CD ef GH"))
dit(mfa.normalise_secours("abcd-efgh") == mfa.normalise_secours("ABCDEFGH"),
    "et les deux cotes de la comparaison passent par elle")

print("\n  ── le pas de temps ──")
dit(mfa.pas_de(0) == 0 and mfa.pas_de(29) == 0 and mfa.pas_de(30) == 1,
    "le pas change toutes les trente secondes, et pas ailleurs",
    f"0->{mfa.pas_de(0)} 29->{mfa.pas_de(29)} 30->{mfa.pas_de(30)}")
dit(abs(mfa.pas_de() - int(time.time() // 30)) <= 1,
    "et sans instant donne, c'est l'heure du studio")

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
for r in rate:
    print(f"    RATE : {r}")
sys.exit(1 if rate else 0)
