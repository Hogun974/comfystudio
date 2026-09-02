#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Les comptes, et le second facteur qu'ils gardent.

banc_mfa.py mesure l'ARITHMETIQUE — les vecteurs de la RFC 6238, la derive,
le rejeu d'un code. Celui-ci mesure le STOCKAGE et la porte : ce qui est ecrit
sur le disque, ce qui en ressort, et ce qu'un appelant distrait obtient.

CE QU'IL EXISTE POUR EMPECHER, dans l'ordre de gravite :

  - QU'UN APPELANT QUI IGNORE LE SECOND FACTEUR OUVRE UNE SESSION. C'est le cas
    qui fait tout le reste. authentifier() rend un sentinelle quand il manque le
    code, et ce sentinelle est FAUX : le code d'avant, « if not c: refuser »,
    refuse. S'il avait ete vrai, chaque site d'appel oublie aurait ouvert une
    session sur le seul mot de passe — et un site oublie ne se voit pas,
    puisque tout continue de marcher pour les comptes qui n'ont rien arme.
  - QUE LE SECRET SORTE. Il ne peut pas etre garde en empreinte, puisqu'il faut
    le relire pour calculer le code attendu : il est donc en clair dans
    _comptes.json, comme partout ailleurs, et rien ne doit le laisser sortir
    par une route.
  - QU'ON S'ENFERME DEHORS. Armer le facteur au moment ou l'on tire le secret
    condamne le compte de quiconque a mal scanne son QR code — et
    l'administrateur ne peut rien, c'est justement ce qu'on vient d'empecher.
  - QU'UN CODE SERVE DEUX FOIS. Un code TOTP vaut trente secondes ; un code de
    secours rejouable est un second mot de passe note sur un papier.
  - QUE LE REJEU ROUVRE AU REDEMARRAGE. Le dernier pas accepte doit etre sur le
    DISQUE : le studio redemarre souvent, c'est ecrit en tete de comptes.py.

Aucun reseau, aucun studio : un registre dans un dossier temporaire.

    python banc_comptes.py
"""
import json
import os
import shutil
import sys
import tempfile

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)

import comptes as C  # noqa: E402
import mfa           # noqa: E402

ok, rate = [], []


def dit(vrai, quoi, releve=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok  ' if vrai else 'RATE'} {quoi}"
          + (f" — {releve}" if releve else ""))


DOSSIER = tempfile.mkdtemp(prefix="banc_comptes_")
CHEMIN = os.path.join(DOSSIER, "_comptes.json")
MDP = "un-mot-de-passe-assez-long"


def neuf():
    """Un registre vide, avec un compte « jordan » et rien d'autre."""
    try:
        os.remove(CHEMIN)
    except OSError:
        pass
    r = C.Comptes(CHEMIN, "secret-de-banc")
    r.creer("jordan", MDP, admin=True)
    return r


try:
    print("\n  ── sans second facteur, rien ne change ──")
    r = neuf()
    dit(bool(r.authentifier("jordan", MDP)),
        "le mot de passe seul ouvre un compte qui n'a rien arme")
    dit(r.authentifier("jordan", "faux") is None,
        "un mauvais mot de passe rend None")
    dit(r.authentifier("personne", MDP) is None,
        "un compte inconnu rend None, comme un mauvais mot de passe : dire "
        "« ce compte n'existe pas » publierait la liste des comptes")
    dit(not r.mfa_arme("jordan"), "et le facteur n'est pas arme")

    print("\n  ── l'enrolement se fait en DEUX temps ──")
    secret, uri = r.mfa_preparer("jordan")
    dit(len(secret) == 32 and "=" not in secret,
        "preparer() rend un secret et son URI", uri[:44] + "…")
    # LE CAS QUI EVITE DE S'ENFERMER DEHORS. Entre le tirage du secret et la
    # confirmation, le compte doit se comporter EXACTEMENT comme avant :
    # quelqu'un qui ferme l'onglet apres avoir scanne de travers doit pouvoir
    # continuer a entrer avec son seul mot de passe.
    dit(not r.mfa_arme("jordan"),
        "le facteur n'est PAS arme tant qu'un code juste n'a pas ete presente")
    dit(bool(r.authentifier("jordan", MDP)),
        "et le mot de passe seul ouvre encore : on ne s'enferme pas dehors")
    dit(r.gens["jordan"].get("mfa_attente", {}).get("secret") == secret,
        "le secret attend dans « mfa_attente », pas dans « mfa »")

    mauvais = False
    try:
        r.mfa_confirmer("jordan", "000000")
    except C.ErreurCompte:
        mauvais = True
    dit(mauvais, "un code faux ne confirme rien, et le dit par une erreur nommee")
    dit(not r.mfa_arme("jordan"), "et le facteur n'est toujours pas arme")

    # Deux preparations de suite tirent deux secrets : quelqu'un qui reprend un
    # enrolement abandonne ne doit pas avoir a deviner lequel de ses deux
    # comptes d'application est le bon.
    secret2, _ = r.mfa_preparer("jordan")
    dit(secret2 != secret, "preparer() deux fois tire un secret NEUF")

    print("\n  ── confirmer arme, et rend les codes de secours ──")
    # LE PAS EST EPINGLE, ET NON RELU A CHAQUE LIGNE. La premiere version de ce
    # banc appelait mfa.code(secret2) deux fois — une pour confirmer, une pour
    # verifier que ce code-la etait consomme — et les deux appels tombaient
    # dans des fenetres DIFFERENTES quand l'execution traversait une frontiere
    # de trente secondes. Verdicts opposes d'un lancement a l'autre, sur un
    # code juste : exactement le genre de banc capricieux qui finit par etre
    # ignore. On fige le pas ; verifie() en accepte un de part et d'autre, donc
    # le cas reste vrai meme si l'horloge tourne pendant le banc.
    PAS_CONF = mfa.pas_de()
    secours = r.mfa_confirmer("jordan", mfa.code(secret2, pas=PAS_CONF))
    dit(r.mfa_arme("jordan"), "le facteur est arme")
    dit(len(secours) == 10 and len(set(secours)) == 10,
        "dix codes de secours, tous distincts, EN CLAIR une seule fois",
        str(len(secours)))
    dit("mfa_attente" not in r.gens["jordan"], "et l'attente a disparu")

    print("\n  ── un appelant distrait echoue FERME ──")
    # LE CAS LE PLUS IMPORTANT DE CE BANC. Le code d'avant s'ecrit
    # « c = authentifier(nom, mdp) ; if not c: refuser ». Il doit refuser.
    sans_code = r.authentifier("jordan", MDP)
    dit(not sans_code,
        "authentifier() sans code rend quelque chose de FAUX : « if not c » "
        "refuse", repr(sans_code))
    dit(sans_code is C.BESOIN_MFA,
        "et ce quelque chose se distingue de None pour qui veut afficher le "
        "champ", repr(sans_code))
    dit(sans_code is not None,
        "il n'est donc PAS None : les deux cas ne se confondent pas")
    dit(r.authentifier("jordan", "faux") is None,
        "un mauvais mot de passe rend toujours None, jamais BESOIN_MFA : "
        "sinon le sentinelle dirait quels mots de passe sont bons")

    print("\n  ── le code, et le rejeu ──")
    # LE CODE QUI A CONFIRME L'ENROLEMENT EST DEJA CONSOMME, et il faut le dire
    # a l'utilisateur : il vient de le taper, il le voit encore a l'ecran, et
    # le retaper ne l'ouvrira pas. C'est voulu — sans cela le rejeu rentrerait
    # par la porte de l'enrolement — mais quelqu'un qui ne le sait pas croit
    # que son enrolement a rate. L'interface doit annoncer l'attente, au plus
    # trente secondes.
    #
    # Ce cas-la etait ecrit a l'envers dans la premiere version de ce banc : il
    # exigeait que ce code ouvre la session, et c'est le banc qui avait tort.
    confirme = mfa.code(secret2, pas=PAS_CONF)
    dit(r.authentifier("jordan", MDP, confirme) is None,
        "le code qui a CONFIRME l'enrolement n'ouvre pas de session ensuite",
        confirme)
    # Le suivant, lui, passe : verifie() accepte un pas d'avance, donc on n'a
    # pas besoin d'attendre reellement trente secondes pour le mesurer.
    suivant = mfa.code(secret2, pas=PAS_CONF + 1)
    dit(bool(r.authentifier("jordan", MDP, suivant)),
        "mot de passe plus code SUIVANT : la session s'ouvre", suivant)
    dit(r.authentifier("jordan", MDP, suivant) is None,
        "LE MEME CODE NE SERT PAS DEUX FOIS", "rejeu ferme")
    dit(r.authentifier("jordan", MDP, "000000") is None,
        "un code faux rend None, comme un mauvais mot de passe")
    code = suivant

    # SUR LE DISQUE, ET PAS SEULEMENT EN MEMOIRE. Le studio redemarre souvent :
    # un dernier pas garde en memoire seulement rouvrirait le rejeu a chaque
    # relance, ce qui est la moitie d'une protection.
    relu = C.Comptes(CHEMIN, "secret-de-banc")
    dit(relu.authentifier("jordan", MDP, code) is None,
        "et il ne sert pas davantage APRES un redemarrage : le dernier pas "
        "accepte est sur le disque")

    print("\n  ── les codes de secours ──")
    dit(relu.mfa_secours_restants("jordan") == 10, "dix au depart",
        str(relu.mfa_secours_restants("jordan")))
    dit(bool(relu.authentifier("jordan", MDP, secours[0])),
        "un code de secours ouvre la session", secours[0])
    dit(relu.mfa_secours_restants("jordan") == 9, "et il est retire",
        str(relu.mfa_secours_restants("jordan")))
    dit(relu.authentifier("jordan", MDP, secours[0]) is None,
        "LE MEME NE SERT PAS DEUX FOIS : sinon c'est un second mot de passe "
        "note sur un papier")
    # Ce qu'un humain recopie depuis un papier : la casse et les tirets.
    dit(bool(relu.authentifier("jordan", MDP,
                               secours[1].upper().replace("-", " "))),
        "la casse, les espaces et les tirets sont pardonnes en le recopiant",
        secours[1])

    print("\n  ── rien de secret ne sort ──")
    l = relu.liste()
    plat = json.dumps(l)
    dit(secret2 not in plat and "secret" not in plat,
        "liste() ne laisse sortir NI le secret NI le mot « secret »", plat[:60])
    dit(not any("mfa" in x for x in l[0]),
        "ni le moindre champ du second facteur",
        ", ".join(sorted(l[0])))
    # ET LE FICHIER, LUI, LE PORTE — sinon les deux cas ci-dessus seraient vrais
    # d'un registre ou l'on n'aurait rien arme du tout.
    brut = open(CHEMIN, encoding="utf-8").read()
    dit(secret2 in brut,
        "alors que le fichier sur disque le porte bien : les cas ci-dessus ne "
        "sont pas vrais de rien", "le secret est dans _comptes.json")

    print("\n  ── desarmer ──")
    relu.mfa_retirer("jordan")
    dit(not relu.mfa_arme("jordan"), "le facteur est desarme")
    dit(bool(relu.authentifier("jordan", MDP)),
        "et le mot de passe seul ouvre de nouveau")
    dit(secret2 not in open(CHEMIN, encoding="utf-8").read(),
        "LE SECRET EST EFFACE, et non garde « au cas ou » : le garder ferait "
        "qu'un compte desarme puis rearme reprendrait l'ancien — le telephone "
        "qu'on venait de perdre rouvrirait le studio")

    print("\n  ── ce que les autres comptes ne subissent pas ──")
    r2 = neuf()
    r2.creer("visiteur", MDP)
    s3, _ = r2.mfa_preparer("jordan")
    r2.mfa_confirmer("jordan", mfa.code(s3))
    dit(bool(r2.authentifier("visiteur", MDP)),
        "un compte sans facteur entre toujours avec son seul mot de passe")
    dit(not r2.authentifier("jordan", MDP),
        "pendant que l'autre exige son code : le facteur est PAR COMPTE")

    deja = False
    try:
        r2.mfa_preparer("jordan")
    except C.ErreurCompte:
        deja = True
    dit(deja, "on ne prepare pas un enrolement sur un compte deja arme")

    print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
    for x in rate:
        print(f"    RATE : {x}")
finally:
    shutil.rmtree(DOSSIER, ignore_errors=True)

sys.exit(1 if rate else 0)
