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
  - QU'UNE PORTE DU SERVEUR ECHAPPE AU FREINAGE. Six chiffres font un million,
    mais la fenetre vaut 90 s et un code de secours pese une quarantaine de
    bits : sans limite, on les essaie. La derniere section lit serveur.py par
    l'arbre de syntaxe et exige qu'il n'y ait qu'UN site d'appel a
    authentifier(), dans une porte qui freine avant de verifier, et qu'aucune
    route ne verifie un secret a cote d'elle.

Aucun reseau, aucun studio : un registre dans un dossier temporaire, et
serveur.py LU sans etre importe — il tirerait aiohttp derriere lui.

    python banc_comptes.py
"""
import ast
import inspect
import io
import json
import os
import shutil
import sys
import tempfile

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
    # LE SYMETRIQUE DE mfa_arme(), ET IL SE LIT AUTANT. Sans lui, un appelant
    # qui veut distinguer « ce code ne correspond pas » d'« aucun enrolement en
    # cours » n'a que la PHRASE FRANCAISE de l'exception a comparer — le
    # contrat sur un texte que ce depot a deja defait deux fois. Les deux
    # remedes different : l'un se retape, l'autre se recommence.
    dit(r.mfa_en_attente("jordan") and not r.mfa_arme("jordan"),
        "« en attente » et « arme » sont deux etats distincts, et on est dans "
        "le premier")

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
    dit(not r.mfa_en_attente("jordan"),
        "donc plus rien n'est « en attente » : confirmer une seconde fois "
        "n'est plus un code faux, c'est un enrolement qui n'existe plus")

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

    print("\n  ── un jeu NEUF de codes de secours ──")
    # POURQUOI CETTE PORTE EXISTE : les dix codes s'epuisent — c'est le but,
    # ils sont a usage unique — et arriver au dernier ne doit pas obliger a
    # desarmer puis reenroler, ce qui change le SECRET et fait ressortir le
    # telephone.
    #
    # LE TEMOIN D'ABORD. Sans cette premiere ligne, « aucun ancien code ne vaut
    # plus » serait vraie d'un jeu qui n'a JAMAIS rien valu : verte parce que
    # rien ne s'est passe, le defaut que ce depot a corrige treize fois d'un
    # coup.
    dit(bool(relu.authentifier("jordan", MDP, secours[2])),
        "un code de l'ancien jeu ouvre encore — c'est le temoin de la suite",
        secours[2])
    avant = relu.mfa_secours_restants("jordan")
    neufs = relu.mfa_regenerer("jordan")
    dit(len(neufs) == 10 and not (set(neufs) & set(secours)),
        "regenerer rend dix codes NEUFS, aucun en commun avec les anciens",
        f"{len(neufs)} codes")
    dit(relu.mfa_secours_restants("jordan") == 10,
        "et le compte repart de dix", f"{avant} avant, "
        f"{relu.mfa_secours_restants('jordan')} apres")
    dit(relu.authentifier("jordan", MDP, secours[3]) is None,
        "AUCUN ancien code ne vaut plus : le jeu est REMPLACE, jamais complete "
        "— on le regenere justement parce qu'on a perdu de vue le papier "
        "d'avant", secours[3])
    dit(bool(relu.authentifier("jordan", MDP, neufs[0])),
        "un code neuf, lui, ouvre", neufs[0])
    # LE SECRET NE BOUGE PAS, et c'est tout ce qui separe cette methode de
    # « retirer puis reenroler » : le telephone deja enrole continue de servir,
    # seuls les codes de papier changent.
    dit(secret2 in open(CHEMIN, encoding="utf-8").read(),
        "et le SECRET n'a pas change : le telephone deja enrole sert encore")

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
    absent = False
    try:
        relu.mfa_regenerer("jordan")
    except C.ErreurCompte:
        absent = True
    dit(absent,
        "et l'on ne regenere pas des codes de secours sur un compte desarme : "
        "ils ne garderaient rien")

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

    # ══ LE MOT DE PASSE D'ORIGINE ══════════════════════════════════════
    # LE STUDIO TIRE UN MOT DE PASSE AU PREMIER DEMARRAGE ET L'AFFICHE UNE
    # FOIS. Il defile dans une console, il se recolle dans un fil de
    # discussion, et il reste le seul secret du studio tant que personne ne l'a
    # change — mais RIEN ne savait dire s'il l'avait ete. « Change-le » etait
    # une phrase de documentation, pas une mesure : l'ecran de premiere mise en
    # route en a fait une ligne qui rougit, et cette ligne tient a un drapeau.
    #
    # UN DRAPEAU ET NON UNE COMPARAISON. Garder le mot de passe pour pouvoir
    # dire « c'est encore lui » reviendrait a le conserver en clair, ce que
    # comptes.py refuse en tete de fichier. Le drapeau ne dit rien du secret :
    # il dit que personne n'y a touche.
    print("\n  ── le mot de passe tire au demarrage ──")
    # LE BANC ROUGIT, IL NE MEURT PAS, et cette ligne-ci est ce qui l'y oblige.
    # Sur un comptes.py qui ne connait pas « origine », l'appel a creer()
    # levait un TypeError et emportait avec lui les soixante verifications
    # suivantes — banc_mutations.py rend alors « le banc s'est casse au lieu de
    # rougir », et le SENS INVERSE, le banc NEUF lance sur le code d'AVANT, ne
    # mesurait plus rien du tout. C'est le meme geste que l'ouverture sous try
    # de web/demarrage.html dans banc_page.py.
    #
    # LA SIGNATURE ET NON UN try/except : « except TypeError » attraperait
    # aussi un appel mal ecrit ici, et se declarerait alors satisfait d'un
    # comptes.py parfaitement sain.
    sait_marquer = "origine" in inspect.signature(C.Comptes.creer).parameters
    dit(sait_marquer,
        "creer() sait marquer le mot de passe que le studio vient de tirer",
        ", ".join(inspect.signature(C.Comptes.creer).parameters))
    if sait_marquer:
        r3 = neuf()
        r3.creer("origine", MDP, admin=True, origine=True)
        # LES DEUX SENS, ET LE SECOND EST LE TEMOIN. Sans lui, « le compte
        # marque est nomme » serait vrai d'une methode qui nommerait TOUS les
        # comptes.
        dit(r3.mdp_d_origine("origine") and not r3.mdp_d_origine("jordan"),
            "seul le compte cree avec « origine » porte la marque",
            f"marques : {r3.comptes_d_origine()}")
        dit(r3.comptes_d_origine() == ["origine"],
            "et comptes_d_origine() le NOMME : « il reste un mot de passe "
            "d'origine » enverrait chercher lequel dans une page de vingt lignes",
            str(r3.comptes_d_origine()))
        r3.changer_mdp("origine", "un-autre-mot-de-passe")
        dit(not r3.mdp_d_origine("origine") and r3.comptes_d_origine() == [],
            "changer le mot de passe efface la marque, des deux cotes")
        # LE DISQUE SE RELIT ICI ET PAS PLUS BAS, et l'ordre est la mesure : la
        # premiere version de ce cas relisait apres authentifier(), qui ecrit
        # « vu » et RESAUVE tout le registre. Elle se comptait donc verte contre
        # un changer_mdp() qui aurait sauve AVANT d'effacer la marque — le
        # defaut exact qu'elle nomme, repare par la ligne suivante. Trou releve
        # par banc_mutations.py le 3 septembre 2026.
        relu3 = C.Comptes(CHEMIN, "secret-de-banc")
        dit(not relu3.mdp_d_origine("origine"),
            "l'effacement est sur le DISQUE, pas seulement en memoire : sinon "
            "l'ecran rougirait de nouveau au prochain demarrage")
        dit(bool(r3.authentifier("origine", "un-autre-mot-de-passe")),
            "et le compte s'ouvre avec le nouveau : la marque n'est qu'une note")

    # UNE SEULE ECRITURE DE L'EFFACEMENT, et c'est la lecon que ce depot a
    # payee trois fois : tant qu'il y a deux ecritures du meme enchainement,
    # elles divergent. Les DEUX portes qui changent un mot de passe —
    # /api/compte/mdp et /api/admin/comptes — passent par changer_mdp(). Poser
    # l'effacement dans les routes l'aurait recopie, et la seconde copie aurait
    # fini par manquer : l'ecran aurait alors reclame indefiniment un
    # changement deja fait, ce qui est la facon la plus sure de le faire
    # ignorer.
    COMPTES_PY = io.open(os.path.join(ICI, "comptes.py"), encoding="utf-8",
                         newline=None).read()
    arbre_c = ast.parse(COMPTES_PY)
    efface = [n for n in ast.walk(arbre_c)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
              and n.func.attr == "pop" and n.args
              and isinstance(n.args[0], ast.Constant)
              and n.args[0].value == "origine"]
    dans_changer = [f for f in ast.walk(arbre_c)
                    if isinstance(f, ast.FunctionDef) and f.name == "changer_mdp"
                    and any(e is x for e in efface for x in ast.walk(f))]
    dit(len(efface) == 1 and len(dans_changer) == 1,
        "la marque n'est effacee qu'a UN endroit, et c'est changer_mdp()",
        f"{len(efface)} effacement(s)")

    # ── ET LE SERVEUR NE MARQUE QUE CE QU'IL A TIRE ──────────────────
    # STUDIO_ADMIN_MDP laisse l'hebergeur poser le mot de passe d'avance, dans
    # un docker-compose par exemple. Celui-la est une DECISION, et il n'y a
    # rien a en mesurer : le marquer ferait rougir pour toujours une ligne que
    # personne ne peut eteindre autrement qu'en changeant un secret qu'il a
    # choisi. Le drapeau ne vaut donc que pour le mot de passe tire au sort.
    SERVEUR_TXT = io.open(os.path.join(ICI, "serveur.py"), encoding="utf-8",
                          newline=None).read()
    arbre_s = ast.parse(SERVEUR_TXT)
    creations = [n for n in ast.walk(arbre_s)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and n.func.attr == "creer"
                 and any(k.arg == "origine" for k in n.keywords)]
    dit(len(creations) == 1
        and "ADMIN_MDP" in ast.unparse(
            next(k.value for k in creations[0].keywords if k.arg == "origine")),
        "le serveur ne marque « origine » que le mot de passe qu'il a TIRE, "
        "jamais celui de STUDIO_ADMIN_MDP",
        "; ".join(ast.unparse(c)[:60] for c in creations) or "aucune creation")

    # ══ LA PORTE DU SERVEUR ════════════════════════════════════════════
    # SIX CHIFFRES FONT UN MILLION, ET CE N'EST PAS BEAUCOUP. La fenetre de
    # verification vaut 90 s (mfa.FENETRE), donc trois codes sont valables a
    # chaque instant ; un code de secours ne pese que huit caracteres d'un
    # alphabet de trente et un, soit une quarantaine de bits. Sans freinage,
    # ces deux-la s'essaient — et le freinage ne vaut que s'il n'existe AUCUNE
    # route qui verifie un mot de passe ou un code a cote de lui. C'est la
    # meme forme que le middleware « origine_verifiee » : ecrite route par
    # route, la garde s'oublie a la prochaine route ajoutee.
    #
    # SERVEUR.PY EST LU, PAS IMPORTE : il tirerait aiohttp derriere lui, que la
    # machine du releve n'a pas. Et il est lu par l'ARBRE DE SYNTAXE et non par
    # expression reguliere — « une expression reguliere decrit UNE facon
    # d'ecrire la panne, jamais la panne » (banc_mutations.py, les quatre trous
    # de banc_page.py). Un appel etale sur trois lignes, un argument reordonne,
    # un commentaire au milieu : ast les voit tous.
    print("\n  ── la porte du serveur : un seul site, un seul compteur ──")
    SERVEUR = io.open(os.path.join(ICI, "serveur.py"), encoding="utf-8",
                      newline=None).read()
    arbre = ast.parse(SERVEUR)

    appels = [n for n in ast.walk(arbre)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
              and n.func.attr == "authentifier"]
    # TROIS ARGUMENTS, ET C'EST LE CAS QUI COMPTE. Un site d'appel qui oublie
    # le code ne LEVE PAS : authentifier() rend BESOIN_MFA, qui est faux, donc
    # la route refuse — elle echoue ferme, ce qui est le bon sens de l'erreur,
    # mais plus PERSONNE n'entre sur un compte arme et le studio a l'air de
    # refuser un mot de passe juste. C'est exactement ce que faisait le
    # changement de mot de passe avant ce travail.
    dit(len(appels) == 1 and len(appels[0].args) == 3,
        "UN SEUL site d'appel a authentifier() dans serveur.py, et il passe le "
        "code",
        f"{len(appels)} site(s) : "
        + "; ".join(ast.unparse(a)[:50] for a in appels[:3]))

    portes = [n for n in ast.walk(arbre)
              if isinstance(n, ast.FunctionDef) and n.name == "_ouvrir_porte"]
    dedans = (len(portes) == 1 and appels
              and any(a is appels[0] for a in ast.walk(portes[0])))
    dit(bool(dedans), "et ce site est dans _ouvrir_porte(), la porte commune",
        f"{len(portes)} definition(s) de _ouvrir_porte")

    porte = portes[0] if portes else None
    noms_porte = {n.id for n in ast.walk(porte or ast.Module(body=[], type_ignores=[]))
                  if isinstance(n, ast.Name)}
    dit(porte is not None and {"_freinage", "_ECHECS"} <= noms_porte,
        "cette porte-la consulte le freinage ET compte l'echec : la saisie du "
        "code passe par le MEME compteur que le mot de passe",
        ", ".join(sorted(noms_porte & {"_freinage", "_ECHECS"})) or "ni l'un ni l'autre")

    # L'ORDRE, ET PAS SEULEMENT LA PRESENCE. Freiner APRES avoir verifie le
    # code laisserait chaque essai s'executer avant d'etre compte : le scrypt
    # des dix codes de secours serait paye a chaque fois, et le studio se
    # laisserait occuper par qui tape n'importe quoi.
    lignes_frein = [n.lineno for n in ast.walk(porte) if porte is not None
                    and isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                    and n.func.id == "_freinage"]
    dit(bool(lignes_frein) and appels and min(lignes_frein) < appels[0].lineno,
        "et elle freine AVANT de verifier, jamais apres",
        f"freinage ligne {min(lignes_frein) if lignes_frein else '?'}, "
        f"verification ligne {appels[0].lineno if appels else '?'}")

    # LE SENTINELLE NE TOUCHE PAS AU COMPTEUR, NI DANS UN SENS NI DANS L'AUTRE.
    #   - le compter en echec freinerait la connexion NORMALE d'un compte arme,
    #     qui fait deux appels a chaque fois : au troisieme il faudrait
    #     attendre, sans s'etre trompe une seule fois ;
    #   - le laisser remettre le compteur a zero rouvrirait le forçage en
    #     grand — il suffirait d'intercaler un appel SANS code entre deux
    #     essais de code pour effacer l'ardoise, et l'attente exponentielle ne
    #     mordrait jamais.
    branches = [n for n in ast.walk(porte) if porte is not None
                and isinstance(n, ast.If) and "BESOIN_MFA" in ast.unparse(n.test)]
    dit(len(branches) == 1,
        "la demande de code est une branche a elle seule dans cette porte",
        f"{len(branches)} branche(s) qui nomment BESOIN_MFA")
    touche = set()
    for b in branches:
        for corps in b.body:
            touche |= {n.id for n in ast.walk(corps) if isinstance(n, ast.Name)}
    dit(bool(branches) and "_ECHECS" not in touche,
        "et elle ne touche PAS au compteur : ni comptee en echec (la connexion "
        "normale se freinerait elle-meme), ni remise a zero (un appel sans "
        "code entre deux essais effacerait l'ardoise)",
        ", ".join(sorted(touche))[:70] or "aucun nom")

    # PAR COMPTE **ET** PAR ADRESSE. Par adresse seule, un studio derriere un
    # reverse proxy qui n'ajoute pas « X-Forwarded-For » voit tout le monde
    # arriver de la meme IP, et le premier qui se trompe trois fois freine la
    # maison. Par compte seul, un tiers bloque a distance le compte de
    # quelqu'un d'autre en tapant faux.
    cles = [n for n in ast.walk(arbre)
            if isinstance(n, ast.FunctionDef) and n.name == "_cle_freinage"]
    rendus = [n for c in cles for n in ast.walk(c) if isinstance(n, ast.Return)]
    forme = ast.unparse(rendus[0].value) if rendus else ""
    dit(len(rendus) == 1 and isinstance(rendus[0].value, ast.Tuple)
        and len(rendus[0].value.elts) == 2 and "nom" in forme and "hote" in forme,
        "le compteur est indexe par le COUPLE (compte, adresse), pas par l'un "
        "des deux", forme or "aucun _cle_freinage")

    # ET AUCUNE ROUTE NE VERIFIE UN MOT DE PASSE A COTE. Le sol est pris par le
    # haut : non pas la liste des routes auxquelles on a pense, mais celle des
    # methodes qui savent dire « ce secret est le bon ». Le jour ou une route
    # en appellera une directement, ce cas rougira et demandera qu'elle passe
    # par la porte — c'est le bon sens de l'erreur.
    a_cote = sorted({n.func.attr for n in ast.walk(arbre)
                     if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                     and n.func.attr in ("verifier", "mfa_verifier")})
    passages = [n for n in ast.walk(arbre)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "_ouvrir_porte"]
    # « >= 5 » EST LE TEMOIN : sans lui, « aucune verification a cote » serait
    # vrai d'un serveur qui ne verifierait plus rien du tout.
    dit(len(passages) >= 5 and not a_cote,
        "cinq portes empruntent _ouvrir_porte(), et aucune ne verifie un mot "
        "de passe ni un code a cote",
        ", ".join(a_cote) or f"{len(passages)} passages")

    # LES CINQ ROUTES SONT ENREGISTREES. Une route ecrite et jamais branchee
    # est une fonctionnalite morte que rien ne signale : c'est le defaut qui a
    # fait naitre banc_mutations.py, et recette_chemin_page.py existe pour la
    # meme raison.
    attendues = ["/api/compte/mfa", "/api/compte/mfa/preparer",
                 "/api/compte/mfa/confirmer", "/api/compte/mfa/retirer",
                 "/api/compte/mfa/secours"]
    poses = {n.args[0].value for n in ast.walk(arbre)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr.startswith("add_") and n.args
             and isinstance(n.args[0], ast.Constant)
             and isinstance(n.args[0].value, str)}
    manquantes = [r for r in attendues if r not in poses]
    dit(not manquantes, "et les cinq routes du second facteur sont branchees",
        ", ".join(manquantes) or f"{len(attendues)} sur {len(poses)} routes")

    print("\n  ── desarmer le facteur d'un AUTRE : le jeton, pas un role ──")
    # CE QUE CETTE SECTION GARDE. Jusqu'au 4 septembre 2026, rouvrir un compte
    # dont le telephone ET les codes de secours etaient perdus demandait
    # d'arreter le studio et d'editer conversations/_comptes.json a la main.
    # /admin sait le faire maintenant — et c'est precisement le genre de
    # commodite qui rogne une promesse sans qu'une ligne de documentation ne
    # bouge, si on ne la tient pas.
    #
    # LA PROMESSE : un compte administrateur peut deja imposer un mot de passe
    # a n'importe qui. S'il pouvait AUSSI desarmer, il prendrait n'importe quel
    # compte en deux gestes, et le second facteur ne protegerait plus de rien
    # d'autre que d'un mot de passe qui fuit. Le jeton, lui, ne se lit que sur
    # la machine : l'exiger coute ce que coutait le remede d'avant.
    # LES DEUX SORTES DE DEFINITION. Les routes sont « async def », donc des
    # AsyncFunctionDef : ne ramasser que FunctionDef rendait un dictionnaire ou
    # api_admin_mfa_retirer n'existait pas, et trois cas rougissaient sur un
    # « None » plutot que sur le code. Un banc qui se trompe de noeud mesure sa
    # propre erreur.
    defs = {n.name: n for n in ast.walk(arbre)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    porte_jeton = defs.get("admin_par_jeton")
    retirer = defs.get("api_admin_mfa_retirer")
    VIDE = ast.Module(body=[], type_ignores=[])

    def code_de(fn):
        """Le corps SANS la docstring — ce qui s'execute, pas ce qui s'explique.

        Les deux cas « ce mot n'apparait nulle part » portaient sur le texte
        entier : ils rougissaient parce que la docstring de _facteur_du_compte
        dit « le secret ne passe pas par la », et celle d'admin_par_jeton
        « compte administrateur ». Une garde qu'une explication peut casser
        peut aussi bien etre satisfaite par une explication.
        """
        if fn is None:
            return ""
        corps = list(fn.body)
        if (corps and isinstance(corps[0], ast.Expr)
                and isinstance(corps[0].value, ast.Constant)
                and isinstance(corps[0].value.value, str)):
            corps = corps[1:]
        return "\n".join(ast.unparse(x) for x in corps)

    dit("/api/admin/comptes/{nom}/mfa" in poses,
        "la route qui desarme pour autrui est branchee",
        "sinon /admin propose un bouton qui n'existe pas")

    appels_jeton = [n for n in ast.walk(retirer or VIDE)
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                    and n.func.id == "admin_par_jeton"]
    coupe = [n for n in ast.walk(retirer or VIDE)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr == "mfa_retirer"]
    dit(retirer is not None and len(appels_jeton) == 1 and len(coupe) == 1
        and appels_jeton[0].lineno < coupe[0].lineno,
        "elle exige le JETON, et le verifie AVANT de desarmer",
        f"jeton ligne {appels_jeton[0].lineno if appels_jeton else '?'}, "
        f"retrait ligne {coupe[0].lineno if coupe else '?'}")

    # LE REFUS EST UN RETOUR, PAS UN AVERTISSEMENT. Verifier le jeton puis
    # continuer quand meme est le defaut le plus facile a ecrire de tous : le
    # code se lit comme s'il gardait quelque chose.
    gardes = [n for n in ast.walk(retirer or VIDE)
              if isinstance(n, ast.If) and "admin_par_jeton" in ast.unparse(n.test)
              and any(isinstance(x, ast.Return) for x in ast.walk(n))]
    dit(len(gardes) == 1,
        "et ce controle SORT de la fonction quand il echoue",
        f"{len(gardes)} branche(s) qui refusent")

    # LE JETON SEUL, ET RIEN QUI RESSEMBLE A UN ROLE. On cherche le contraire
    # de ce qu'on veut : si un jour quelqu'un « repare » admin_par_jeton en y
    # remettant le compte connecte, pour que le bouton marche sans coller le
    # jeton, ce cas rougit.
    dans_jeton = code_de(porte_jeton)
    dit(porte_jeton is not None and "est_admin" not in dans_jeton
        and "compte" not in dans_jeton and "compare_digest" in dans_jeton,
        "admin_par_jeton() ne connait QUE le jeton : ni role, ni compte "
        "connecte, et la comparaison est a temps constant",
        "est_admin" if "est_admin" in dans_jeton else
        ("compte" if "compte" in dans_jeton else "jeton seul"))

    # LE TEMOIN, sans lequel le cas du dessus serait vrai d'un serveur qui
    # aurait perdu la notion de compte administrateur.
    dans_ok = code_de(defs.get("admin_ok"))
    dit("est_admin" in dans_ok,
        "alors que admin_ok(), lui, ouvre bien aux comptes administrateurs : "
        "le cas ci-dessus n'est pas vrai de rien",
        "admin_ok consulte est_admin")

    # CETTE PORTE-LA NE SERT QU'A CA. Posee sur d'autres routes, elle
    # deviendrait une gene ordinaire qu'on finirait par retirer partout.
    tous_appels = [n for n in ast.walk(arbre)
                   if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                   and n.func.id == "admin_par_jeton"]
    dit(len(tous_appels) == 2,
        "elle garde le retrait, et sert a dire d'avance a la console si le "
        "bouton sera cliquable — deux endroits, pas un de plus",
        f"{len(tous_appels)} appel(s)")

    # CE QUE LA CONSOLE APPREND DU FACTEUR : un mot et un nombre.
    facteur = defs.get("_facteur_du_compte")
    clefs = {c.value for n in ast.walk(facteur or VIDE)
             if isinstance(n, ast.Dict) for c in n.keys
             if isinstance(c, ast.Constant)}
    dit(facteur is not None and clefs == {"mfa", "secours"},
        "l'etat servi a /admin ne porte qu'un mot et un nombre",
        ", ".join(sorted(clefs)) or "aucune clef")
    dit(facteur is not None and "secret" not in code_de(facteur)
        and "mfa_preparer" not in code_de(facteur),
        "et il ne va chercher ni le secret ni de quoi le retirer",
        "rien de secret n'y est nomme")

    # LA TRACE, PARCE QUE LA DOCUMENTATION LA PROMET. docs/comptes.md dit que
    # le studio ecrit une ligne dans sa console a chaque retrait : c'est le
    # seul endroit ou le proprietaire verra qu'une protection posee par
    # quelqu'un d'autre a ete levee. Une promesse qui n'est gardee par rien se
    # perd au premier remaniement, et personne ne s'apercoit de sa disparition
    # — c'est le propre d'une trace.
    traces = [n for n in ast.walk(retirer or VIDE)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
              and n.func.id == "print" and "DESARME" in ast.unparse(n)]
    dit(len(traces) == 1 and coupe and traces[0].lineno > coupe[0].lineno,
        "le retrait laisse une trace dans la console, ecrite APRES coup : "
        "annoncer avant, c'est annoncer ce qui peut encore echouer",
        f"{len(traces)} trace(s)")

    print("\n  ── un enrolement commence et jamais confirme se debloque aussi ──")
    # LE CAS QU'ON OUBLIE. mfa_en_attente() empeche d'en recommencer un — c'est
    # voulu, sinon chaque rechargement de page tirerait un secret neuf. Mais
    # celui qui a mal scanne son QR code reste bloque la, sans etre arme : si
    # le retrait ne nettoyait que « mfa », son compte serait coince pour
    # toujours dans un etat que personne ne peut ni confirmer ni annuler.
    r3 = neuf()
    r3.creer("coince", MDP)
    r3.mfa_preparer("coince")
    dit(r3.mfa_en_attente("coince") and not r3.mfa_arme("coince"),
        "l'enrolement est en attente, et rien n'est arme")
    r3.mfa_retirer("coince")
    dit(not r3.mfa_en_attente("coince"),
        "le retrait efface AUSSI l'attente, et non le seul facteur arme")
    s4, _ = r3.mfa_preparer("coince")
    dit(bool(r3.mfa_confirmer("coince", mfa.code(s4))),
        "un enrolement neuf redevient possible derriere")

    print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
    for x in rate:
        print(f"    RATE : {x}")
finally:
    shutil.rmtree(DOSSIER, ignore_errors=True)

sys.exit(1 if rate else 0)
