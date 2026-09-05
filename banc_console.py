# -*- coding: utf-8 -*-
"""Les BOUTONS de /admin font-ils ce qu'ils disent ?

    python banc_console.py

CE QUI MANQUAIT, ET LA FORME EXACTE DU MANQUE. Le 5 septembre 2026, un releve
des routes du studio contre tous les bancs et toutes les recettes : soixante-
quatre routes, VINGT-DEUX qu'aucun banc ne nomme. Ce banc-ci en prend sept, et
ce sont celles qui AGISSENT sur le parc.

La pause en est l'exemple parfait, et il vaut la peine d'etre ecrit. Son EFFET
est mesure depuis longtemps — banc_attente.py la nomme quarante-cinq fois,
banc_repartition.py huit : une machine en pause ne recoit pas de travail, la
demande qui la reclame patiente, puis attend son retour. Ce que personne ne
mesurait, c'est le GESTE : que le clic pose vraiment la marque, qu'il l'ECRIVE
sur le disque, et que le retour de pause relance ce qui attendait. Les deux
bancs partaient d'un registre ou l'on avait pose « pause » a la main.

C'est mot pour mot la lecon de recette_chemin_page.py — sept bancs verts
pendant que les reglages par conversation etaient morts, parce qu'aucun
n'empruntait le chemin de la page. Un etat qu'on pose soi-meme n'est pas un
bouton qu'on clique.

CE QU'IL GARDE, dans l'ordre des degats :

  - LE JETON REGENERE FERME L'ANCIEN. C'est tout l'objet du bouton : une
    machine dont le jeton a fuite. S'il posait le neuf sans fermer l'ancien, le
    bouton donnerait le sentiment d'avoir agi sans rien fermer du tout — la
    pire des deux issues, puisqu'on ne chercherait plus.
  - RETIRER UNE MACHINE LA RETIRE DE QUATRE ENDROITS. Le registre, l'etat, les
    modeles, les travaux. Un reste dans n'importe lequel est une machine
    fantome : elle ne s'annonce plus, mais le studio compte encore sur elle.
  - LA PAUSE SURVIT AU REDEMARRAGE. Elle est ecrite dans _noeuds.json, et c'est
    la seule chose qui empeche qu'un studio relance prenne la carte de
    quelqu'un qui joue.
  - LE PILOTAGE DE ComfyUI EST RESERVE A LA MACHINE HOTE, et par DEUX gardes,
    pas une : local() dit que l'appel vient de la machine, origine_sure() dit
    qu'il vient de l'interface et non d'un site piege. La seconde existe parce
    que la premiere ne suffit pas — un formulaire poste depuis n'importe quel
    site part du navigateur de l'utilisateur, donc de 127.0.0.1.
  - L'ARRET REFUSE QUAND LA FILE N'EST PAS VIDE. Tuer ComfyUI pendant un rendu
    perd le travail de quelqu'un.
  - LA CONSOLE APPELLE CE QUE LE SERVEUR SERT, ET LE SERVEUR NE SERT RIEN QUE
    LA CONSOLE N'APPELLE. C'est l'autre moitie du contrat, et elle n'etait
    tenue par personne : les six sections ci-dessus appellent les
    gestionnaires EN PYTHON, et banc_page.py ne relit web/admin.html que pour
    les noms de reglage. La septieme section reconstruit chaque appel api()
    de la page — chemin, methode, y compris ceux qui passent par une
    enveloppe — et le confronte au VRAI routeur, dans les deux sens : un
    appel vers une route absente est un bouton qui rend 404 au clic, vers la
    bonne route avec la mauvaise methode 405 ; une route qu'aucun bouton
    n'atteint est une fonctionnalite morte que rien ne signale, et elle est
    nommee avec sa raison ou le banc rougit. Releve du 5 septembre 2026 :
    23 appels, 20 couples methode/chemin, 23 routes dans la famille, trois
    exceptions nommees.

CE QU'IL NE VOIT PAS, et il faut l'ecrire :

  - Qu'un vrai ComfyUI demarre. subprocess.Popen est remplace par un temoin :
    on mesure la DECISION de lancer et ce qu'on lui passe, pas ce que le
    systeme en fait. os.startfile et taskkill non plus.
  - Que le bouton soit BRANCHE sur son appel. Le releve de la section 7 est
    statique : un api() dans un gestionnaire que rien n'attache compte comme
    un appel. Emprunter le chemin du navigateur est le travail de
    recette_chemin_page.py, qui a besoin d'un studio.
  - Les deux routes de pilotage de la section 4 n'ont AUCUN bouton : au
    5 septembre 2026, rien dans web/ n'appelle /api/comfy/demarrer ni
    /api/comfy/arreter, et ce depuis le premier commit. La section 7 les
    nomme en exception, elle ne les couvre pas — un banc qui eprouve une
    route « depuis l'interface » que l'interface n'appelle pas mesure le
    gestionnaire, pas le bouton.
  - L'effet de la pause sur la repartition : banc_attente.py et
    banc_repartition.py le tiennent, et ce banc-ci ne le redit pas.
"""
import asyncio
import io
import json
import os
import re
import sys
import tempfile
import time

os.environ["STUDIO_DONNEES"] = tempfile.mkdtemp(prefix="banc_console_")
os.environ["STUDIO_AUTH"] = "libre"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serveur as S  # noqa: E402

# LE JETON D'ADMINISTRATION EST VIDE A L'IMPORT — charger_registre() l'etablit
# au demarrage, et ce banc ne demarre pas de studio. Sans cette ligne,
# admin_ok() compare l'en-tete a une chaine vide, refuse tout, et les sept
# routes rendent 403 : le banc mesurerait sa propre absence d'authentification,
# ce qui est vrai de n'importe quel code.
S.ADMIN_JETON = "jeton-d-administration-du-banc"

ok, rate = [], []


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


class Transport:
    """Le peername que local() interroge, et rien d'autre."""

    def __init__(self, hote):
        self.hote = hote

    def get_extra_info(self, quoi):
        return (self.hote, 0) if quoi == "peername" else None


class Req(dict):
    """Une requete assez complete pour ces sept routes.

    « transport » compte autant que le corps : c'est par lui que local() decide
    si l'appel vient de la machine hote, et deux des routes n'existent que pour
    cette question-la.
    """

    def __init__(self, match=None, corps=None, hote=None, entetes=None,
                 admin=True):
        super().__init__(pid="u" * 32, compte="")
        self.match_info = match or {}
        # LE JETON, COMME LA CONSOLE LE PORTE. Sans lui, admin_ok() refuse et
        # les sept routes rendent 403 : le banc mesurerait sa propre absence
        # d'authentification, ce qui est vrai de n'importe quel code.
        self.headers = dict(entetes or {})
        if admin and "X-Admin" not in self.headers:
            self.headers["X-Admin"] = S.ADMIN_JETON
        self.cookies = {}
        self.transport = Transport(hote) if hote is not None else None
        self._corps = corps

    async def json(self):
        if self._corps is None:
            raise ValueError("pas de corps")
        return self._corps


def lire(rep):
    return rep.status, json.loads(rep.text)


def registre_sur_disque():
    """Ce que _noeuds.json porte VRAIMENT, relu du disque.

    Relire le fichier et non l'objet en memoire : la question posee est « un
    studio qui redemarre retrouve-t-il ce geste », et seul le disque y repond.
    """
    try:
        with io.open(S.FICHIER_REGISTRE, encoding="utf-8") as f:
            return {x["id"]: x for x in json.load(f)}
    except (OSError, ValueError):
        return {}


def poser(*idents):
    """Un parc neuf, et rien qui traine d'un cas a l'autre."""
    S.REGISTRE.clear()
    S.ETAT_NOEUDS.clear()
    S.MODELES_NOEUD.clear()
    S.TRAVAUX.clear()
    S.EN_FILE.clear()
    S.EN_VOL.clear()
    del S.ATTENTE[:]
    S.ARMEES.clear()
    for i, ident in enumerate(idents):
        S.REGISTRE[ident] = {"id": ident, "titre": f"machine {ident}",
                             "jeton": f"jeton-{ident}", "cree": "2026-09-05"}
        S.ETAT_NOEUDS[ident] = {"repond": True, "vram": 11.0 - i, "vu": time.time()}
        S.MODELES_NOEUD[ident] = {"quand": time.time(), "dossiers": {}}
        S.TRAVAUX[ident] = []
    S.sauver_registre()


# ── Relire les appels de la console ───────────────────────────────────
# Ce qui suit reconstruit chaque appel api() de web/admin.html : le chemin tel
# que le serveur le verra, morceaux dynamiques remplaces par « {x} », et la
# methode HTTP. Pas une expression reguliere sur « api("/api/... » : les
# chemins sont des CONCATENATIONS — « "/api/admin/noeuds/" +
# encodeURIComponent(n.id) + "/pause" » — dont les parentheses interieures
# arreteraient un motif au mauvais endroit, la pause s'etale sur deux lignes,
# et les comptes passent par une enveloppe « envoyer(charge, methode, ou) »
# dont le chemin est un PARAMETRE. Un releve qui manquerait ces cinq appels-la
# declarerait mortes trois routes bien vivantes.

def sans_commentaires(html):
    """Le JavaScript sans ses commentaires de bloc, MEMES numeros de ligne.

    Un « api() » cite dans un commentaire n'est pas un appel ; le retirer
    avant le releve evite de le compter. Les sauts de ligne sont gardes pour
    que les numeros de ligne des cas restent ceux du fichier.
    """
    return re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"),
                  html, flags=re.S)


def arguments_js(texte, i):
    """Les arguments de premier niveau de l'appel dont « ( » est a texte[i].

    Par comptage de parentheses, en sautant les chaines : rend (arguments,
    indice apres la parenthese fermante), ou (None, fin) si l'appel n'est
    jamais ferme.
    """
    creux, corde, args, debut, j = 0, None, [], i + 1, i
    while j < len(texte):
        c = texte[j]
        if corde:
            if c == "\\":
                j += 2
                continue
            if c == corde:
                corde = None
        elif c in "\"'`":
            corde = c
        elif c in "([{":
            creux += 1
        elif c in ")]}":
            creux -= 1
            if creux == 0:
                args.append(texte[debut:j].strip())
                return [a for a in args if a], j + 1
        elif c == "," and creux == 1:
            args.append(texte[debut:j].strip())
            debut = j + 1
        j += 1
    return None, len(texte)


def gabarit_js(expr):
    """Le chemin que sert le serveur, ou None si l'expression ne se lit pas.

    « "/a/" + encodeURIComponent(x) + "/b" » et `/a/${x}/b` rendent tous deux
    « /a/{x}/b » ; la requete « ?fournisseur=... » est otee, le routeur ne la
    voit pas. Un identifiant nu rend None : c'est un chemin passe par une
    variable, que l'appelant resout par son enveloppe ou declare obscur.
    """
    if not expr or expr[0] not in "\"'`":
        return None
    if expr[0] == "`":
        if not expr.endswith("`"):
            return None
        chemin = re.sub(r"\$\{[^}]*\}", "{x}", expr[1:-1])
    else:
        chemin, creux, corde, debut, morceaux = "", 0, None, 0, []
        for j, c in enumerate(expr):
            if corde:
                if c == corde and expr[j - 1] != "\\":
                    corde = None
            elif c in "\"'`":
                corde = c
            elif c in "([{":
                creux += 1
            elif c in ")]}":
                creux -= 1
            elif c == "+" and creux == 0:
                morceaux.append(expr[debut:j].strip())
                debut = j + 1
        morceaux.append(expr[debut:].strip())
        for m in morceaux:
            chemin += m[1:-1] if m[:1] in "\"'" and m.endswith(m[0]) else "{x}"
    return chemin.split("?", 1)[0]


def litteral_js(expr):
    """Le contenu d'une chaine litterale simple, ou None."""
    if expr and len(expr) >= 2 and expr[0] in "\"'" and expr.endswith(expr[0]):
        return expr[1:-1]
    return None


def corps_de_fonction(texte, nom):
    """Le corps de « function nom(...) { ... } », par comptage d'accolades ; "" sinon."""
    depart = texte.find("function " + nom + "(")
    ouvre = texte.find("{", depart) if depart >= 0 else -1
    if ouvre < 0:
        return ""
    creux = 0
    for i in range(ouvre, len(texte)):
        if texte[i] == "{":
            creux += 1
        elif texte[i] == "}":
            creux -= 1
            if creux == 0:
                return texte[ouvre:i + 1]
    return ""


def appels_de_la_console(html):
    """Rend (porte, appels, obscurs).

    porte : (nom de la fonction d'appel, methode par defaut) lus dans SA
    DEFINITION — « async function api(chemin, methode = "GET", corps) » —
    et non supposes : si la page change son defaut, le releve suit. None si
    la page n'en a pas.
    appels : liste de (METHODE, gabarit, ligne, enveloppe ou None).
    obscurs : les appels dont le chemin ou la methode ne se reconstruit pas.
    """
    porte = re.search(r'async function (\w+)\(\s*chemin\s*,\s*methode\s*=\s*'
                      r'"(\w+)"', html)
    if not porte:
        return None, [], []
    nom, defaut = porte.group(1), porte.group(2)
    code = sans_commentaires(html)
    appels, obscurs = [], []

    def ligne(pos):
        return code.count("\n", 0, pos) + 1

    def resoudre(chemin_expr, methode_expr, pos):
        chemin, methode = gabarit_js(chemin_expr), litteral_js(methode_expr)
        if chemin is not None and methode is not None:
            appels.append((methode.upper(), chemin, ligne(pos), None))
            return
        # UNE ENVELOPPE : le chemin ou la methode est un parametre d'une
        # fonction flechee definie plus haut, et chaque appel de CETTE
        # fonction est un appel au serveur. On prend la definition la plus
        # proche qui nomme tous les identifiants en jeu, et ses appels jusqu'a
        # la prochaine definition du meme nom — la page en a deux, « envoyer »
        # des cles et « envoyer » des comptes, et seule la seconde passe le
        # chemin en parametre.
        idents = [e for e in (chemin_expr, methode_expr)
                  if re.fullmatch(r"\w+", e or "")]
        defs = [d for d in re.finditer(
            r"(\w+)\s*=\s*(?:async\s*)?\(([^()]*)\)\s*=>", code[:pos])
            if all(re.search(r"\b" + i + r"\b", d.group(2)) for i in idents)]
        if not defs:
            obscurs.append((chemin_expr, methode_expr, ligne(pos)))
            return
        d = defs[-1]
        params = []
        for p in d.group(2).split(","):
            n, _, v = p.partition("=")
            params.append((n.strip(), v.strip() or None))
        noms = [n for n, _ in params]
        suivant = re.search(r"\b" + d.group(1) + r"\s*=\s*(?:async\s*)?\(",
                            code[d.end():])
        fin = d.end() + suivant.start() if suivant else len(code)
        vus = 0
        for site in re.finditer(r"(?<![\w.])" + d.group(1) + r"\(",
                                code[d.end():fin]):
            args, _ = arguments_js(code, d.end() + site.end() - 1)
            if args is None:
                continue
            vus += 1

            def valeur(expr):
                if expr in noms:
                    k = noms.index(expr)
                    return args[k] if k < len(args) else params[k][1]
                return expr

            c, m = gabarit_js(valeur(chemin_expr)), litteral_js(valeur(methode_expr))
            p = d.end() + site.start()
            if c is None or m is None:
                obscurs.append((valeur(chemin_expr), valeur(methode_expr), ligne(p)))
            else:
                appels.append((m.upper(), c, ligne(p), d.group(1)))
        if not vus:
            obscurs.append((chemin_expr, methode_expr, ligne(pos)))

    for site in re.finditer(r"(?<![\w.])" + nom + r"\(", code):
        if code[max(0, site.start() - 9):site.start()] == "function ":
            continue
        args, _ = arguments_js(code, site.end() - 1)
        if not args:
            continue
        resoudre(args[0], args[1] if len(args) > 1 else '"' + defaut + '"',
                 site.start())
    return (nom, defaut), appels, obscurs


lancer = asyncio.get_event_loop().run_until_complete if False else asyncio.run

try:
    # ══════════════════════════════════════════════════════════════════
    #  1. la pause — un geste, et non un etat qu'on pose soi-meme
    # ══════════════════════════════════════════════════════════════════
    print("\n  ── la pause, prise par son bouton ──")
    poser("pc", "zima")

    async def pause(ident, valeur):
        return lire(await S.api_admin_pause(
            Req(match={"ident": ident}, corps={"pause": valeur})))

    st, d = lancer(pause("pc", True))
    dit(st == 200 and d.get("ok") and d.get("pause"),
        "le bouton met la machine en pause, et rend l'instant ou elle l'a ete",
        f"HTTP {st}, pause={bool(d.get('pause'))}")
    dit(bool(S.REGISTRE["pc"].get("pause")), "la marque est dans le registre")

    # LA MOITIE QUI COMPTE, ET QUE NUL NE MESURAIT. Une pause perdue au
    # redemarrage rend la carte a un studio qui la redistribue aussitot —
    # c'est-a-dire exactement pendant que son proprietaire joue.
    dit(bool(registre_sur_disque().get("pc", {}).get("pause")),
        "et elle est ECRITE dans _noeuds.json : un studio qui redemarre la "
        "retrouve", os.path.basename(S.FICHIER_REGISTRE))

    # UNE PAUSE N'EST PAS UN RETRAIT. La docstring de la route le dit en toutes
    # lettres ; sans ce cas, une pause qui effacerait le jeton passerait pour
    # une pause reussie jusqu'au retour de la machine.
    dit(S.REGISTRE["pc"].get("jeton") == "jeton-pc"
        and "pc" in S.ETAT_NOEUDS and "pc" in S.MODELES_NOEUD,
        "le jeton reste valable, la machine reste visible et son inventaire "
        "avec : une pause n'est pas un retrait")
    dit(d.get("reveillees") == 0,
        "mettre en pause ne reveille rien — il n'y a rien a relancer",
        f"reveillees={d.get('reveillees')}")

    st, d = lancer(pause("pc", False))
    dit(st == 200 and not d.get("pause"), "le meme bouton l'en sort",
        f"HTTP {st}, pause={d.get('pause')}")
    dit("pause" not in S.REGISTRE["pc"]
        and "pause" not in registre_sur_disque().get("pc", {}),
        "et la marque disparait des DEUX cotes, memoire et disque : une pause "
        "qui survit a sa sortie est une machine qu'on croit rendue")

    # LE RETOUR DE PAUSE RELANCE CE QUI ATTENDAIT, et tout de suite. Le veilleur
    # le ferait trente secondes plus tard ; l'interet du bouton est que la file
    # reparte dans le meme rafraichissement que le clic.
    reveils = []

    async def faux_reveil(ident=None, plancher=True):
        reveils.append((ident, plancher))
        return 3

    vrai_reveil, S.reveiller_armees = S.reveiller_armees, faux_reveil
    try:
        st, d = lancer(pause("zima", False))
    finally:
        S.reveiller_armees = vrai_reveil
    dit(st == 200 and d.get("reveillees") == 3 and reveils == [("zima", False)],
        "sortir une machine de pause relance ce qui l'attendait, sur ELLE, et "
        "dit combien", f"{d.get('reveillees')} relancee(s), appels {reveils}")
    # « plancher=False » EST LE DETAIL QUI DECIDE. Avec le plancher, une demande
    # armee depuis moins de quinze secondes etait ecartee : la reponse
    # annoncait « 0 relancee » alors qu'elle repartait au battement suivant.
    dit(reveils and reveils[0][1] is False,
        "sans le plancher de quinze secondes : le clic est deliberatif, pas un "
        "va-et-vient de machine", f"plancher={reveils[0][1] if reveils else '?'}")

    st, d = lancer(pause("machine-qui-n-existe-pas", True))
    dit(st == 404, "une machine inconnue rend 404, et non un succes vide",
        f"HTTP {st}")

    # LA GARDE D'ACCES, SUR LES TROIS ROUTES QUI AGISSENT SUR LE PARC. Elles
    # mettent une carte au repos, ferment un jeton et retirent une machine :
    # ce sont les gestes qu'un visiteur ne doit pas pouvoir faire. On les
    # demande SANS le jeton, ce qui est exactement ce qu'un navigateur qui
    # n'est jamais passe par /admin envoie.
    poser("pc")
    refus = []
    for nom, appel in (
            ("pause", S.api_admin_pause(Req(match={"ident": "pc"},
                                            corps={"pause": True}, admin=False))),
            ("jeton", S.api_admin_rejeton(Req(match={"ident": "pc"}, admin=False))),
            ("retrait", S.api_admin_supprimer(Req(match={"ident": "pc"},
                                                  admin=False)))):
        st, _ = lire(lancer(appel))
        refus.append((nom, st))
    dit(all(st == 403 for _, st in refus),
        "sans le jeton d'administration, les trois gestes sont refuses",
        ", ".join(f"{n}={s}" for n, s in refus))
    dit("pc" in S.REGISTRE and not S.REGISTRE["pc"].get("pause")
        and S.REGISTRE["pc"]["jeton"] == "jeton-pc",
        "et le parc est intact apres ces trois refus : rien n'a ete a moitie "
        "fait")

    # ══════════════════════════════════════════════════════════════════
    #  2. le jeton d'une machine — le regenerer FERME l'ancien
    # ══════════════════════════════════════════════════════════════════
    print("\n  ── regenerer le jeton d'une machine ──")
    poser("pc")
    ancien = S.REGISTRE["pc"]["jeton"]
    dit(S.noeud_du_jeton(ancien) is not None,
        "avant le clic, l'ancien jeton ouvre bien", "il designe une machine")

    st, d = lire(lancer(S.api_admin_rejeton(Req(match={"ident": "pc"}))))
    neuf = d.get("jeton", "")
    dit(st == 200 and neuf and neuf != ancien,
        "le bouton rend un jeton NEUF, different de l'ancien",
        f"HTTP {st}, {len(neuf)} caracteres")
    dit(len(neuf) >= 24,
        "assez long pour ne pas se deviner", f"{len(neuf)} caracteres")

    # LE CAS QUI FAIT TOUT LE RESTE. Poser le neuf sans fermer l'ancien donne le
    # sentiment d'avoir agi sans rien fermer : on ne chercherait plus.
    dit(S.noeud_du_jeton(ancien) is None,
        "ET L'ANCIEN NE VAUT PLUS RIEN : c'est tout l'objet du bouton, une "
        "machine dont le jeton a fuite")
    dit(S.noeud_du_jeton(neuf) is not None, "tandis que le neuf ouvre")
    dit(registre_sur_disque().get("pc", {}).get("jeton") == neuf,
        "le neuf est ecrit sur le disque : un studio relance ne rouvre pas "
        "l'ancien")
    # L'agent presentera l'ancien jeton et sera refuse ; il doit se reannoncer
    # avec le neuf, et l'etat d'avant ne vaut plus rien.
    dit("pc" not in S.ETAT_NOEUDS,
        "l'etat de la machine est oublie : elle devra se reannoncer")

    st, d = lire(lancer(S.api_admin_rejeton(Req(match={"ident": "fantome"}))))
    dit(st == 404, "une machine inconnue rend 404", f"HTTP {st}")

    # ══════════════════════════════════════════════════════════════════
    #  3. retirer une machine — quatre traces, pas une
    # ══════════════════════════════════════════════════════════════════
    print("\n  ── retirer une machine du parc ──")
    poser("pc", "zima")
    S.TRAVAUX["pc"] = [{"tid": "t1"}]
    st, d = lire(lancer(S.api_admin_supprimer(Req(match={"ident": "pc"}))))
    restes = [nom for nom, table in (("registre", S.REGISTRE),
                                     ("etat", S.ETAT_NOEUDS),
                                     ("modeles", S.MODELES_NOEUD),
                                     ("travaux", S.TRAVAUX)) if "pc" in table]
    dit(st == 200 and not restes,
        "elle disparait des QUATRE tables : un reste dans l'une d'elles est "
        "une machine fantome, qui ne s'annonce plus et sur qui le studio "
        "compte encore", ", ".join(restes) or "aucune trace")
    dit("pc" not in registre_sur_disque(),
        "et du disque : sinon elle revient au prochain demarrage")
    dit("zima" in S.REGISTRE and "zima" in S.ETAT_NOEUDS,
        "la voisine n'est pas emportee au passage")

    st, d = lire(lancer(S.api_admin_supprimer(Req(match={"ident": "pc"}))))
    dit(st == 404, "la retirer deux fois rend 404 la seconde", f"HTTP {st}")

    # ══════════════════════════════════════════════════════════════════
    #  4. piloter ComfyUI — deux gardes, et il en faut deux
    # ══════════════════════════════════════════════════════════════════
    print("\n  ── demarrer et arreter ComfyUI depuis l'interface ──")
    LOCALE = sorted(S.ADRESSES_MACHINE)[0] if S.ADRESSES_MACHINE else "127.0.0.1"
    lances = []

    class FauxPopen:
        def __init__(self, *a, **kw):
            lances.append((a, kw))

    async def repond_non():
        return False

    async def repond_oui():
        return True

    # LES DEUX BRANCHES DE L'ARRET SONT REMPLACEES, ET CE N'EST PAS UN DETAIL.
    # Le code tue par « taskkill /PID <pid> /T /F » sous Windows et par
    # os.kill(pid, 15) ailleurs. Ne remplacer que la premiere donne un banc qui
    # TUE POUR DE VRAI sur l'autre systeme — et le numero vient de pid_du_port,
    # que ce banc-ci fabrique.
    #
    # DEUX FOIS LA MEME FAUTE LE MEME JOUR, 5 septembre 2026. D'abord ici :
    # subprocess.run n'etait pas remplace, et le faux pid 4242 est parti a un
    # vrai taskkill sur la machine de developpement. Corrige — et la correction
    # ne visait QUE Windows, si bien que la CI Ubuntu a appele os.kill(4242, 15)
    # sur son runner au tour suivant. Une garde ecrite pour la plateforme qu'on
    # a sous les yeux n'est pas une garde.
    tues = []

    def faux_run(cmd, **kw):
        tues.append(list(cmd))
        return type("Fini", (), {"returncode": 0, "stdout": b"", "stderr": b""})()

    def faux_kill(pid, signal):
        tues.append(["kill", str(pid), str(signal)])

    vrais = (S.subprocess.Popen, S.subprocess.run, S.os.kill, S.comfy_repond,
             S.lanceur_comfy, S.pid_du_port, S.commande_comfy)
    S.subprocess.Popen = FauxPopen
    S.subprocess.run = faux_run
    S.os.kill = faux_kill
    S.comfy_repond = repond_non
    S.lanceur_comfy = lambda: os.path.join(tempfile.gettempdir(), "faux_lanceur.sh")
    S.pid_du_port = lambda port=None: 4242
    # SANS CELLE-CI, le code retombe sur os.startfile pour un fichier qui
    # n'existe pas et rend 500 : on mesurerait le lanceur absent, pas la
    # decision de lancer.
    S.commande_comfy = lambda: ["python", "main.py"]
    try:
        # LA GARDE DE L'ADRESSE. Le pilotage tue et relance un processus sur la
        # machine hote : il n'a rien a faire au bout du reseau.
        st, d = lire(lancer(S.api_comfy_demarrer(Req(hote="203.0.113.9"))))
        dit(st == 403 and not lances,
            "un appel venu d'une AUTRE machine est refuse, et rien n'est lance",
            f"HTTP {st}, {len(lances)} lancement(s)")

        # LA SECONDE GARDE, et elle n'est pas redondante : un formulaire poste
        # depuis un site piege part du navigateur de l'utilisateur, donc de
        # 127.0.0.1. local() seul le laisserait passer.
        st, d = lire(lancer(S.api_comfy_demarrer(
            Req(hote=LOCALE, entetes={"Origin": "http://site-piege.example",
                                      "Host": "127.0.0.1:8199"}))))
        dit(st == 403 and not lances,
            "et un clic sur un site tiers l'est aussi, alors qu'il vient bien "
            "de la machine : local() seul ne distingue pas les deux",
            f"HTTP {st}")

        st, d = lire(lancer(S.api_comfy_demarrer(
            Req(hote=LOCALE, entetes={"Origin": "http://127.0.0.1:8199",
                                      "Host": "127.0.0.1:8199"}))))
        dit(st == 200 and len(lances) == 1,
            "l'interface, elle, lance bien le moteur", f"HTTP {st}")

        S.comfy_repond = repond_oui
        avant = len(lances)
        st, d = lire(lancer(S.api_comfy_demarrer(Req(hote=LOCALE))))
        dit(st == 200 and d.get("deja") and len(lances) == avant,
            "un ComfyUI qui repond deja n'est pas relance une seconde fois",
            f"deja={d.get('deja')}, {len(lances) - avant} lancement(s) de plus")

        S.comfy_repond = repond_non
        S.lanceur_comfy = lambda: ""
        st, d = lire(lancer(S.api_comfy_demarrer(Req(hote=LOCALE))))
        dit(st == 404 and "COMFY_LANCEUR" in str(d.get("erreur", "")),
            "sans script de lancement, il le DIT et nomme le reglage qui repare",
            str(d.get("erreur"))[:60])

        # L'ARRET, ET LA SEULE CHOSE QU'IL DOIT REFUSER.
        # ATTENTE, ET NON EN_FILE. La premiere ecriture de ce cas posait
        # EN_FILE — « de quoi refaire la demande apres un arret » — et
        # s'attendait a un refus. Le code n'a pas tort : EN_FILE est une
        # comptabilite de reprise, pas du travail qui attend. Le banc l'etait.
        S.ATTENTE.append({"tid": "t1"})
        st, d = lire(lancer(S.api_comfy_arreter(Req(hote=LOCALE))))
        dit(st == 409 and not tues,
            "l'arret est REFUSE tant qu'une demande ATTEND, et rien n'est tue : "
            "tuer ComfyUI perdrait le travail de quelqu'un",
            f"HTTP {st}, {len(tues)} arret(s)")
        del S.ATTENTE[:]
        S.EN_VOL["t2"] = "une tache en cours"
        st, d = lire(lancer(S.api_comfy_arreter(Req(hote=LOCALE))))
        dit(st == 409 and not tues,
            "et tant qu'une generation est EN VOL : l'attente se vide entre "
            "deux taches, la tester seule laisserait passer l'arret dans cet "
            "intervalle", f"HTTP {st}")
        S.EN_VOL.clear()

        # LE CHEMIN QUI TUE, une fois qu'il n'y a plus rien a perdre.
        st, d = lire(lancer(S.api_comfy_arreter(Req(hote=LOCALE))))
        # « 4242 dans l'ordre », et non « taskkill » : la premiere ecriture de
        # ce cas nommait la commande Windows, et rougissait sur la CI Ubuntu
        # pour une raison qui n'avait rien a voir avec le studio. Ce qu'on
        # mesure est qu'UN ordre part, et qu'il porte le pid du PORT de
        # ComfyUI — pas la facon dont le systeme tue.
        dit(st == 200 and d.get("pid") == 4242 and len(tues) == 1
            and "4242" in " ".join(tues[0]),
            "file vide, il arrete le moteur, et sur le pid du PORT de ComfyUI",
            f"HTTP {st}, {tues}")

        # LES DEUX SYSTEMES, DEPUIS N'IMPORTE LEQUEL DES DEUX. Le cas
        # ci-dessus ne traverse qu'UNE branche : celle de la machine qui
        # lance le banc. C'est ainsi qu'une assertion ecrite pour Windows a
        # rougi sur la CI Ubuntu — et, plus grave, que l'autre branche a
        # appele os.kill POUR DE VRAI, parce que rien ne l'avait exercee ici.
        # On force donc os.name, qui est le seul aiguillage.
        vrai_nom = S.os.name
        try:
            # L'ORDRE EN ENTIER, ET NON SON PREMIER MOT. La premiere ecriture
            # exigeait « taskkill » et « 4242 quelque part » : la mutation qui
            # retire « /T » gardait les deux, et revenait VERTE. Sans « /T »,
            # taskkill ne tue que le parent — or un exe onefile a un enfant, et
            # c'est LUI qui tient le port. L'arret rendrait 200, le port
            # resterait pris, la relance echouerait sur « adresse deja
            # utilisee ». C'est le piege mesure sur l'executable le meme jour.
            for systeme, attendu in (
                    ("nt", ["taskkill", "/PID", "4242", "/T", "/F"]),
                    ("posix", ["kill", "4242", "15"])):
                S.os.name = systeme
                del tues[:]
                S.pid_du_port = lambda port=None: 4242
                st, d = lire(lancer(S.api_comfy_arreter(Req(hote=LOCALE))))
                dit(st == 200 and tues == [attendu],
                    f"sur « {systeme} », l'arret est exactement "
                    f"« {' '.join(attendu)} »",
                    f"HTTP {st}, {tues}")
        finally:
            S.os.name = vrai_nom
        S.pid_du_port = lambda port=None: 0
        avant = len(tues)
        st, d = lire(lancer(S.api_comfy_arreter(Req(hote=LOCALE))))
        dit(st == 200 and d.get("deja") and len(tues) == avant,
            "et quand plus rien n'ecoute, il ne tue personne",
            f"deja={d.get('deja')}, {len(tues) - avant} arret(s) de plus")
        st, d = lire(lancer(S.api_comfy_arreter(Req(hote="203.0.113.9"))))
        dit(st == 403, "l'arret est reserve a la machine hote lui aussi",
            f"HTTP {st}")
    finally:
        (S.subprocess.Popen, S.subprocess.run, S.os.kill, S.comfy_repond,
         S.lanceur_comfy, S.pid_du_port, S.commande_comfy) = vrais
    # ══════════════════════════════════════════════════════════════════
    #  5. ce qu'une machine porte, et ce qu'on lui demande
    # ══════════════════════════════════════════════════════════════════
    print("\n  ── le detail d'une machine, et l'essai de son modele ──")
    poser("pc")
    S.ETAT_NOEUDS["pc"].update(carte="RTX 2080 Ti", libre=9.4, ram=63.8,
                               llm=True, llm_modeles=["qwen2.5vl:7b"])
    st, d = lire(lancer(S.api_admin_noeud_detail(Req(match={"ident": "pc"}))))
    dit(st == 200 and d.get("id") == "pc" and d.get("carte") == "RTX 2080 Ti",
        "le detail rend ce que la machine porte", f"HTTP {st}")

    # LE CAS QUI COMPTE ICI, ET IL NE SE VOIT QU'EN LE CHERCHANT. Cette route
    # sert le contenu du registre a la console. Le registre porte le JETON de
    # chaque machine — celui qui donne droit de faire travailler sa carte — et
    # il suffirait d'un « dict(x) » pour le faire sortir avec le reste.
    plat = json.dumps(d)
    dit("jeton" not in plat and "jeton-pc" not in plat,
        "et il ne porte NI le jeton de la machine NI le mot : le registre en "
        "contient un, servir le registre entier le publierait",
        ", ".join(sorted(d))[:70])

    # ET LA PROTECTION N'EST PAS DANS CETTE ROUTE, ce qu'on n'apprend qu'en
    # cherchant : tous_les_noeuds() REBATIT un dictionnaire propre a partir du
    # registre — six champs nommes, jamais le jeton. Toutes les routes qui
    # parlent d'une machine passent par elle, et c'est donc la que le secret
    # est retenu. Un banc qui ne garderait que la sortie de /detail laisserait
    # cette fonction-la sans filet, alors qu'elle sert tout le monde.
    vus = S.tous_les_noeuds()
    dit(vus and all("jeton" not in x for x in vus),
        "tous_les_noeuds() rebatit des fiches PROPRES : c'est la, et non dans "
        "chaque route, que le jeton d'une machine est retenu",
        ", ".join(sorted(vus[-1])) if vus else "aucune machine")

    # LES TROIS LISTES SE DISTINGUENT, et la docstring dit pourquoi : « la
    # carte est trop petite » ne se resout pas en telechargeant, « le modele
    # n'est pas la » si. Les confondre envoie chercher au mauvais endroit.
    dit(all(k in d for k in ("prets", "absents", "trop_gros")),
        "il separe ce qui est pret, ce qui manque et ce qui ne tiendra jamais",
        f"{len(d.get('prets', []))} prets, {len(d.get('absents', []))} absents, "
        f"{len(d.get('trop_gros', []))} trop gros")

    st, d = lire(lancer(S.api_admin_noeud_detail(Req(match={"ident": "nulle"}))))
    dit(st == 404, "une machine inconnue rend 404", f"HTTP {st}")

    # L'ESSAI DU MODELE DE LANGAGE. Sa docstring porte une regle de conception
    # qu'on peut mesurer : « par le MEME chemin que la bascule automatique, et
    # non par une variante de test — une voie de secours qu'on verifie
    # autrement que par son usage reel peut passer l'essai et echouer le jour
    # venu ».
    demandes = []

    async def faux_poser(ident, corps, tid=None, secondes=900, patience=None):
        demandes.append((ident, corps, secondes))
        return "bleu", ""

    vrai_poser, S.poser_a = S.poser_a, faux_poser
    try:
        st, d = lire(lancer(S.api_admin_essai_llm(Req(match={"ident": "pc"}))))
        dit(st == 200 and d.get("reponse") == "bleu" and not d.get("erreur"),
            "l'essai pose une vraie question et rend ce que la machine repond",
            f"HTTP {st}, « {d.get('reponse')} » en {d.get('secondes')} s")
        dit(len(demandes) == 1 and demandes[0][0] == "pc",
            "par poser_a(), le MEME chemin que la bascule automatique : une "
            "voie de secours verifiee autrement que par son usage reel peut "
            "passer l'essai et echouer le jour venu",
            f"{len(demandes)} appel(s), vers {demandes[0][0] if demandes else '?'}")
        # « keep_alive: 0 » N'EST PAS UN DETAIL : un essai qui laisse le modele
        # resident occupe la carte de quelqu'un qui n'a rien demande, et le
        # studio passe son temps a rendre cette carte ailleurs.
        corps = demandes[0][1] if demandes else {}
        dit(corps.get("keep_alive") == 0,
            "et il ne laisse pas le modele charge derriere lui",
            f"keep_alive={corps.get('keep_alive')}")
        dit(corps.get("stream") is False
            and (corps.get("options") or {}).get("temperature") == 0,
            "la question est posee sans flux et sans hasard : deux essais de "
            "suite doivent se comparer", str(corps.get("options")))

        S.ETAT_NOEUDS["pc"]["repond"] = False
        st, d = lire(lancer(S.api_admin_essai_llm(Req(match={"ident": "pc"}))))
        dit(st == 409 and len(demandes) == 1,
            "une machine qui ne repond pas rend 409, et rien n'est demande : "
            "l'essai attendrait trois minutes pour rien",
            f"HTTP {st}, {len(demandes)} appel(s) en tout")
    finally:
        S.poser_a = vrai_poser

    # ══════════════════════════════════════════════════════════════════
    #  6. les modeles d'un fournisseur, lus chez lui
    # ══════════════════════════════════════════════════════════════════
    print("\n  ── les modeles que declare un fournisseur ──")
    st, d = lire(lancer(S.api_admin_modeles(Req(admin=False))))
    dit(st == 403, "sans le jeton, la liste est refusee", f"HTTP {st}")

    class Requete(Req):
        def __init__(self, requete=None, **kw):
            super().__init__(**kw)
            self.query = requete or {}

    st, d = lire(lancer(S.api_admin_modeles(
        Requete(requete={"fournisseur": "pas-un-fournisseur"}))))
    dit(st == 400 and "inconnu" in str(d.get("erreur", "")),
        "un fournisseur inconnu est refuse AVANT qu'on aille chercher quoi que "
        "ce soit", f"HTTP {st}")

    # SANS CLE, ON LE DIT — et l'on n'appelle personne. Rendre une liste vide
    # sans raison ferait chercher une panne de reseau la ou il manque une cle.
    appels = []

    async def faux_lister(nom, cle):
        appels.append((nom, cle))
        return ["un-modele"]

    vrai_lister = S.fournisseurs.lister_modeles
    vraie_cle, S.cle_de = S.cle_de, lambda n: ""
    S.fournisseurs.lister_modeles = faux_lister
    try:
        st, d = lire(lancer(S.api_admin_modeles(
            Requete(requete={"fournisseur": "anthropic"}))))
        dit(st == 200 and d.get("modeles") == [] and d.get("raison") == "aucune cle"
            and not appels,
            "sans cle, il le DIT et n'appelle personne : une liste vide sans "
            "raison ferait chercher une panne de reseau",
            f"raison={d.get('raison')!r}, {len(appels)} appel(s)")
        S.cle_de = lambda n: "une-cle-qui-ne-doit-pas-sortir"
        st, d = lire(lancer(S.api_admin_modeles(
            Requete(requete={"fournisseur": "anthropic"}))))
        dit(st == 200 and d.get("modeles") == ["un-modele"] and len(appels) == 1,
            "avec une cle, il va la chercher chez le fournisseur",
            f"{d.get('modeles')}")
        dit("une-cle-qui-ne-doit-pas-sortir" not in json.dumps(d),
            "et la cle ne repart PAS dans la reponse")
    finally:
        S.fournisseurs.lister_modeles = vrai_lister
        S.cle_de = vraie_cle

    # ══════════════════════════════════════════════════════════════════
    #  7. la console appelle bien ce que le serveur sert
    # ══════════════════════════════════════════════════════════════════
    # L'AUTRE MOITIE DU CONTRAT. Les six sections ci-dessus appellent les
    # gestionnaires en Python ; que la page de /admin les appelle, eux et avec
    # cette methode-la, personne ne le relisait. LE VRAI ROUTEUR, et non un
    # motif sur « a.router.add_post(...) » : S.app().router porte exactement ce
    # que le studio servira, methodes comprises — un releve textuel decrirait
    # une facon d'ecrire la route, jamais la route.
    print("\n  ── la console appelle bien ce que le serveur sert ──")
    ICI = os.path.dirname(os.path.abspath(__file__))
    try:
        ADMIN = io.open(os.path.join(ICI, "web", "admin.html"),
                        encoding="utf-8", newline=None).read()
    except OSError:
        ADMIN = ""
    porte, appels, obscurs = appels_de_la_console(ADMIN)
    CODE = sans_commentaires(ADMIN)

    # UNE SEULE PORTE, SINON LE RELEVE EST AVEUGLE. Un bouton qui appellerait
    # fetch() en direct sortirait du releve, et « chaque appel vise une route »
    # resterait vrai de lui. C'est le raisonnement de « un seul ecrivain » dans
    # banc_page.py, applique a la porte au lieu du reglage.
    corps_porte = corps_de_fonction(CODE, porte[0]) if porte else ""
    dit(bool(ADMIN) and porte is not None and CODE.count("fetch(") == 1
        and "fetch(" in corps_porte,
        "la console n'a qu'UNE porte vers le serveur : fetch() n'apparait que "
        "dans le corps de sa fonction d'appel",
        f"{CODE.count('fetch(')} fetch(), porte "
        f"{porte[0] + '()' if porte else 'introuvable'}"
        if ADMIN else "web/admin.html absent")

    # LE TEMOIN. « Chaque appel vise une route » est vrai d'un releve qui ne
    # trouve rien — une porte renommee, un motif qui ne mord plus. Quinze,
    # parce que la page en porte vingt-trois au 5 septembre 2026 et que le
    # chiffre doit survivre au retrait d'un onglet sans survivre au releve vide.
    couples = sorted(set((m, c) for m, c, _, _ in appels))
    enveloppes = sum(1 for a in appels if a[3])
    dit(len(appels) >= 15,
        "le releve trouve au moins quinze appels : sans ce temoin, « chaque "
        "appel vise une route » serait vrai d'un releve qui ne trouve rien",
        f"{len(appels)} appels, {len(couples)} couples methode/chemin, "
        f"{enveloppes} passes par une enveloppe")
    dit(not obscurs,
        "aucun appel n'est obscur : chaque chemin et chaque methode se "
        "reconstruisent depuis la page, enveloppes comprises",
        " ; ".join(f"l. {l} : {c} {m}" for c, m, l in obscurs)
        or f"{len(appels)} reconstruits")

    # LES ROUTES, LUES SUR LE ROUTEUR QUE LE STUDIO SERVIRA. getattr et non
    # un appel direct : sur un serveur.py d'avant, le cas rougit au lieu de
    # mourir, et le sens inverse reste mesurable. HEAD est ecarte — aiohttp
    # l'ajoute de lui-meme a chaque GET, personne ne l'ecrit ni ne l'appelle.
    #
    # LA FAMILLE : /api/admin/*, et les deux routes de pilotage de ComfyUI que
    # la section 4 eprouve. « /api/comfy » sans barre est l'etat que lit la
    # page d'accueil, pas la console.
    FAMILLE = ("/api/admin/", "/api/comfy/")
    toutes, famille, souci = {}, {}, ""
    fabrique = getattr(S, "app", None)
    try:
        for r in (fabrique().router.routes() if fabrique else ()):
            if r.method == "HEAD":
                continue
            canon = r.resource.canonical
            clef = (r.method, re.sub(r"\{[^}]*\}", "{x}", canon))
            toutes[clef] = r.handler.__name__
            if canon.startswith(FAMILLE):
                famille[clef] = r.handler.__name__
    except Exception as e:  # noqa: BLE001 — un cas nomme, pas une trace
        souci = repr(e)[:80]
    dit(len(famille) >= 15,
        "le routeur du studio sert au moins quinze routes de la famille de la "
        "console : sans ce temoin, « aucune route morte » serait vrai d'un "
        "routeur vide",
        f"{len(famille)} routes sous {' et '.join(FAMILLE)}, {len(toutes)} en tout"
        + (f" — {souci}" if souci else "")
        + ("" if fabrique else " — serveur.app() n'existe pas"))

    # LE SENS ALLER : chaque bouton vise une route servie, avec SA methode.
    # Contre TOUTES les routes et non la seule famille : un appel de la console
    # vers /api/textes serait legitime, et ne doit pas passer pour un manque.
    manques = [(m, c, l) for m, c, l, _ in appels if (m, c) not in toutes]
    dit(not manques,
        "chaque appel de la console vise une route que le serveur sert, avec "
        "la MEME methode : sinon le bouton rend 404 ou 405 au clic, et "
        "personne ne le voit avant l'utilisateur",
        " ; ".join(f"l. {l} : {m} {c}" for m, c, l in manques)
        or f"{len(couples)} couples, tous servis")

    # LE SENS RETOUR, ET SES EXCEPTIONS NOMMEES UNE PAR UNE. Une route que rien
    # n'appelle est une fonctionnalite morte que rien ne signale — le defaut
    # fondateur de banc_mutations.py. Ici elle est au moins ECRITE, avec la
    # raison, et deux cas plus bas tiennent la liste : une exception dont la
    # route a disparu, ou que la console appelle de nouveau, est un mensonge.
    EXCEPTIONS = {
        ("GET", "/api/admin/reglages"):
            "aucun appelant dans le depot au 5 septembre 2026 — la console lit "
            "pause_propose, armee_heures et vram_repos_min dans la reponse de "
            "GET /api/admin/noeuds, et le POST rend deja l'etat complet ; "
            "reste servie a un script",
        ("POST", "/api/comfy/demarrer"):
            "aucun bouton dans web/ au 5 septembre 2026, et ce depuis le "
            "premier commit : la section 4 l'eprouve « depuis l'interface », "
            "et l'interface ne l'appelle pas",
        ("POST", "/api/comfy/arreter"):
            "meme releve que /api/comfy/demarrer — aucun bouton, aucune page",
    }
    atteintes = set(couples)
    mortes = sorted(k for k in famille
                    if k not in atteintes and k not in EXCEPTIONS)
    dit(not mortes,
        "chaque route de la famille est atteinte par la console, ou nommee ici "
        "en exception avec sa raison : une route que rien n'appelle est une "
        "fonctionnalite morte que rien ne signale",
        " ; ".join(f"{m} {c} ({famille[(m, c)]})" for m, c in mortes)
        or f"{len(famille)} routes, {len(atteintes & set(famille))} atteintes, "
           f"{len(EXCEPTIONS)} exceptions nommees")
    perimees = sorted(k for k in EXCEPTIONS if k not in famille)
    dit(not perimees,
        "chaque exception nomme une route que le serveur sert encore : une "
        "exception perimee couvrirait la route suivante du meme nom",
        " ; ".join(f"{m} {c}" for m, c in perimees) or "aucune perimee")
    mensonges = sorted(set(EXCEPTIONS) & atteintes)
    dit(not mensonges,
        "aucune exception n'est appelee par la console : la liste ne ment pas, "
        "et une route revenue au service en sort",
        " ; ".join(f"{m} {c}" for m, c in mensonges) or "aucune")
    for (m, c), pourquoi in sorted(EXCEPTIONS.items()):
        print(f"       exception : {m} {c} — {pourquoi}")
finally:
    pass

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
for x in rate:
    print("    NON :", x)
sys.exit(1 if rate else 0)
