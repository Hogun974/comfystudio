# -*- coding: utf-8 -*-
"""Fabrique etalons_qr.py depuis segno, une implementation INDEPENDANTE.

    uv run --with segno python outils_etalons_qr.py

CE SCRIPT N'EST PAS UN BANC ET N'ENTRE PAS DANS LA CI. Il a servi une fois, le
3 septembre 2026, et les matrices qu'il a produites suffisent ensuite : c'est
elles que banc_qr.py compare a notre encodeur, pas segno, qui n'est pas au
depot et n'y entrera pas.

POURQUOI PASSER PAR UN TIERS. Un encodeur QR ecrit a la main peut etre
parfaitement coherent avec lui-meme et produire une image qu'aucun telephone ne
lit : un masque mal choisi, un octet de correction d'erreur dans le mauvais
ordre, un motif d'alignement place a un pixel pres. Rien de tout cela ne leve,
et « ca ressemble a un QR code » est tout ce qu'on saurait. La seule mesure qui
vaut est la comparaison a une implementation qu'on n'a pas ecrite — le meme
raisonnement que les vecteurs de la RFC 6238 pour le TOTP.

Le relancer n'a de sens que pour AJOUTER un cas. S'il change une matrice
existante, c'est que segno a change d'avis ou que le cas a ete reecrit : il faut
alors comprendre pourquoi avant de recopier, jamais l'inverse.
"""
import io
import os

import segno

# Les quatre cas, et chacun a sa raison d'etre :
#   court  — une URI minimale, la plus petite version qu'on rencontrera
#   reel   — exactement ce que mfa.uri() produit pour un compte ordinaire
#   long   — un nom de compte long et un secret de 40 caracteres : c'est la
#            que la version grimpe, donc que les motifs d'alignement arrivent
#   ascii  — sans rapport avec le studio, et c'est voulu : si les trois
#            premiers se ressemblent trop, un defaut commun leur echapperait
CAS = [
    ("court", "otpauth://totp/A:b?secret=JBSWY3DPEHPK3PXP&issuer=A"),
    # ══ LE SEUL CAS QUE LE STUDIO EMETTE VRAIMENT ═══════════════════════
    # AJOUTE LE 3 SEPTEMBRE 2026, ET IL MANQUAIT. Le cas « reel » ci-dessous
    # s'annonce comme « exactement ce que mfa.uri() produit » et emploie le
    # secret de la RFC, long de SEIZE caracteres — quand mfa.secret_neuf() en
    # rend TRENTE-DEUX. Toute URI d'enrolement reelle fait donc 123 a 150
    # caracteres et sort en 8-M, 49x49, pour n'importe quel nom de compte
    # (mesure : « a », « jordan » et un nom de vingt-huit lettres donnent les
    # trois 49x49).
    #
    # Les quatre etalons couvraient les versions 1, 4, 7 et 9. LA HUITIEME —
    # la seule qui part chez l'utilisateur — n'etait comparee a segno nulle
    # part, et les « 6 364 modules, zero ecart » du commit mesuraient quatre
    # versions dont aucune n'etait celle-la. Demonstration de l'audit : un
    # chiffre change dans la table des alignements de la version 8 laisse
    # banc_qr.py a 50/50 vert pendant qu'aucun telephone ne lit plus une URI
    # d'enrolement — exactement « un motif d'alignement a un pixel pres », la
    # panne que le commit nomme en premier.
    ("emis", "otpauth://totp/ComfyStudio:jordan"
             "?secret=MFRGGZDFMZTWQ2LKNNWG23TPOBYXE43U"
             "&issuer=ComfyStudio&algorithm=SHA1&digits=6&period=30"),
    ("reel", "otpauth://totp/ComfyStudio:jordan?secret=JBSWY3DPEHPK3PXP"
             "&issuer=ComfyStudio&algorithm=SHA1&digits=6&period=30"),
    ("long", "otpauth://totp/ComfyStudio:un-nom-de-compte-plutot-long"
             "?secret=MFRGGZDFMZTWQ2LKNNWG23TPOBYXE43UOJUW4ZY"
             "&issuer=ComfyStudio&algorithm=SHA1&digits=6&period=30"),
    ("ascii", "HELLO WORLD"),
]

ENTETE = '''# -*- coding: utf-8 -*-
"""Les matrices de reference, produites par segno 1.6 le 3 septembre 2026.

Une implementation INDEPENDANTE de la notre, capturee a une date : c'est ce qui
separe « mon encodeur est d'accord avec lui-meme » de « mon encodeur produit un
QR que les telephones lisent ». Un masque mal choisi, un octet de correction
dans le mauvais ordre, un motif d'alignement a un pixel pres — rien de tout cela
ne leve, et l'image ressemble a un QR code dans tous les cas.

Segno n'est pas au depot et n'y entrera pas : il a servi UNE fois, et ces
matrices suffisent. Pour en ajouter un cas, sans rien installer :

    uv run --with segno python outils_etalons_qr.py

« 1 » est un module noir, « 0 » un module clair. La zone de silence n'y est
pas — c'est la page qui la dessine, et segno ne la met pas non plus dans
« matrix ».
"""
'''


def ecrire(chemin):
    sortie = [ENTETE, "ETALONS = ["]
    for nom, texte in CAS:
        # « micro=False » N'EST PAS UN DETAIL. Sans lui, segno choisit tout seul
        # un MICRO QR pour les chaines courtes — le cas « ascii » sortait en
        # « M3-M », un format DIFFERENT : quatre versions au lieu de quarante,
        # un seul motif de reperage au lieu de trois, un format d'information
        # qui n'a pas la meme longueur. L'etalon aurait demande d'implementer
        # une seconde norme pour un cas qui ne sert qu'a varier, et rien dans
        # la matrice ne l'aurait annonce.
        #
        # « boost_error=False » NON PLUS. Chez segno, « error="m" » veut dire
        # AU MOINS M : quand la version choisie laisse de la place, il monte le
        # niveau tout seul. Le cas « ascii » sortait ainsi en « 1-Q » alors
        # qu'on demandait M, et l'etalon aurait decrit une politique que notre
        # encodeur n'a pas. On veut ici une regle qui se tient en une phrase —
        # la plus petite version qui tient a M, et pas plus — parce que c'est
        # celle-la que banc_qr.py va exiger.
        q = segno.make(texte, error="m", micro=False, boost_error=False)
        lignes = ["".join("1" if c else "0" for c in r) for r in q.matrix]
        sortie.append(f"    # {q.designator} — {len(lignes)}x{len(lignes)}")
        sortie.append(f"    ({nom!r}, {texte!r}, {q.designator!r}, [")
        sortie += [f"        {l!r}," for l in lignes]
        sortie.append("    ]),")
    sortie.append("]")
    with io.open(chemin, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(sortie) + "\n")
    return len(CAS)


if __name__ == "__main__":
    ici = os.path.dirname(os.path.abspath(__file__))
    combien = ecrire(os.path.join(ici, "etalons_qr.py"))
    print(f"  {combien} etalons ecrits dans etalons_qr.py")
