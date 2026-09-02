# -*- coding: utf-8 -*-
"""La feuille de style et le script de la page se contredisent-ils ?

    python banc_page.py

web/index.html porte le HTML, le CSS et le JS dans un seul fichier. Rien ne
relit l'ensemble : une regle peut y dormir sans element, deux classes peuvent
porter le meme nom pour deux choses differentes, et une table peut nommer un
menu qui n'existe pas. Aucun de ces trois defauts ne leve d'erreur — la page
s'affiche, simplement pas comme on croit.

Les trois sont arrives :

  - « .puce.moteur » colorait une pastille du nom de « .moteur », le panneau
    des machines de la colonne de gauche. Un element portant les deux classes
    heritait de « display:flex ; flex-direction:column » et des regles
    descendantes du panneau. La regle n'etait posee sur rien, ce qui l'a rendue
    invisible pendant des mois — et l'aurait rendue redoutable le jour ou
    quelqu'un s'en serait servi.
  - MENU_REGLAGE et CLE_REGLAGE sont deux tables inverses l'une de l'autre,
    ecrites a la main a deux cents lignes d'ecart. Une seule qui derive, et un
    reglage cesse d'etre retenu sans que rien ne le dise : c'est exactement le
    defaut que l'utilisateur a signale le 31 aout.

Statique, sans reseau, sans studio : ce banc entre dans la CI. Ce qu'il ne peut
PAS voir — un rendu, une largeur, un debordement — reste le travail de
recette_chemin_page.py et de l'oeil.

Quatre de ses releves ont ete refaits apres que banc_mutations.py les a montres
troues : tous les quatre etaient des expressions regulieres qui decrivaient UNE
facon d'ecrire la panne au lieu de la panne. Un banc ecrit pour un defaut precis
qui ne voit pas ce defaut, c'est le pire des filets — il rassure. Chacun porte
desormais, a l'endroit de la decision, ce que la version d'avant laissait
passer.
"""
import io
import os
import re
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
PAGE = io.open(os.path.join(ICI, "web", "index.html"), encoding="utf-8").read()
ok, rate = [], []


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


# Le CSS s'arrete au premier </style> : au-dela, « .puce » dans une chaine de
# caracteres n'est plus une regle.
# Les commentaires sont RETIRES : ils parlent des regles, et ce banc a commence
# par se signaler lui-meme, en lisant « .puce.moteur » dans le commentaire qui
# explique justement pourquoi la regle n'existe plus.
CSS = re.sub(r'/\*.*?\*/', "", PAGE.split("</style>", 1)[0], flags=re.S)

# « .puce.devis.depasse » ne rendait que « devis » : le second modificateur
# sortait du releve, et « depasse » n'etait verifie ni en collision ni en
# dormance. On prend la SUITE des modificateurs, pas le premier.
modifs = set()
for suite in re.findall(r'\.puce((?:\.[a-z][a-z0-9-]*)+)', CSS):
    modifs |= set(suite.lstrip(".").split("."))


def classes_attrapantes(css):
    """Les classes qu'un simple <span class="puce X"> peut suffire a matcher.

    Le releve d'origine lisait « ^\\.classe » : les seules regles ancrees en
    colonne 0. Mesure : 53 classes vues sur 77 — les 24 autres ne sont definies
    qu'en descendante ou en fin de liste de selecteurs (« .moteur .ligne »,
    « .detail .ligne »). Poser « .puce.ligne » refaisait donc mot pour mot le
    degat de « .puce.moteur », sous le nez du banc ecrit pour lui, et il restait
    vert (banc_mutations.py, trou 2).

    Ce qui fait le degat n'est pas l'endroit ou la regle est ecrite, c'est
    qu'elle MORDE sur la pastille. Un <span class="puce X"> ne matche qu'un
    selecteur dont le dernier compound se reduit a la seule classe « .X » : ce
    qui precede n'est qu'un ancetre, et il finit toujours par y en avoir un.
    « .reponse.rate::before » en demande deux sur l'element lui-meme, il ne peut
    donc jamais mordre — le compter ferait rougir le depot sain sur
    « .puce.rate », qui est une pastille parfaitement legitime.
    """
    noms = set()
    # Le prefixe d'un bloc, c'est ce qui separe la derniere accolade de la
    # suivante. « @media » et « @keyframes » sont ecartes : leur prelude n'est
    # pas une liste de selecteurs.
    for prelude in re.findall(r'(?:^|[{}])([^{}]*?)\{', css, re.S):
        prelude = prelude.strip()
        if not prelude or prelude.startswith("@"):
            continue
        for sel in prelude.split(","):
            dernier = re.split(r'[\s>+~]+', sel.strip())[-1]
            # Les pseudos et leurs arguments ne changent pas de qui la regle
            # parle : « .retirer-armee:hover:not(:disabled) » vise bien
            # « .retirer-armee ».
            net = re.sub(r'::?[a-z-]+(\([^()]*\))?', "", dernier)
            seule = re.fullmatch(r'\.([a-z][a-z0-9_-]*)', net)
            if seule:
                noms.add(seule.group(1))
    return noms


collisions = sorted(modifs & classes_attrapantes(CSS))
dit(not collisions,
    "aucune pastille ne porte le nom d'une classe de mise en page",
    ", ".join(f".puce.{c} contre .{c}" for c in collisions) or "aucun doublon")

# Une pastille se pose dans une chaine du script : « class="puce cours" », mais
# aussi « class="puce devis${depasse ? " depasse" : ""}" ».
#
# Le releve d'origine prenait les LIGNES contenant « puce » et y cherchait les
# noms connus. Il cherchait un mot, pas une classe : « <span class="puce
# attente">en file — 3 devant</span> » fait passer « .puce.file » pour posee,
# alors que la regle dort. C'est du texte francais affiche a l'utilisateur, et
# rien ne l'empeche de contenir « rate », « cours » ou « devis » non plus
# (banc_mutations.py, trou 4).
#
# On lit donc l'attribut « class » lui-meme. Ce n'est toujours pas analyser du
# JavaScript : on suit les accolades de « ${…} » pour ne pas s'arreter sur les
# guillemets qu'elles contiennent, et voila tout.
CORPS = PAGE.split("</style>", 1)[1]


def listes_de_classes(texte):
    """Le contenu de chaque « class="…" », les « ${…} » traverses."""
    for depart in re.finditer(r'class=(["\'])', texte):
        guillemet, i, debut, prof = depart.group(1), depart.end(), depart.end(), 0
        while i < len(texte):
            c = texte[i]
            if not prof and c == "$" and texte[i + 1:i + 2] == "{":
                prof, i = 1, i + 2
                continue
            if prof:
                prof += (c == "{") - (c == "}")
                i += 1
                continue
            # Le saut de ligne autant que le guillemet : un attribut jamais
            # ferme avalerait sinon la moitie du script.
            if c == guillemet or c == "\n":
                break
            i += 1
        yield texte[debut:i]


def noms_poses(valeur):
    """Les classes que cette liste pose vraiment.

    Hors « ${…} », les mots sont des noms de classe. Dedans, SEULES les chaines
    litterales en sont — « ${depasse ? " depasse" : ""} » pose « depasse », et
    non « depasse » l'expression.

    Deux facons de poser une pastille echappent a ce releve, et c'est voulu : une
    classe calculee (« ${etat} ») et un « classList.add » sur un element
    construit ailleurs. Les sept pastilles de la page passent toutes par un
    attribut « class » litteral ; le jour ou l'une n'y passera plus, ce banc la
    declarera dormante, ce qui est le bon sens de l'erreur — il vaut mieux
    relire une pastille qui sert que croire posee une regle qui dort. Les
    accepter demanderait de rendre a « classList.add("file") » sur n'importe
    quel element le pouvoir de justifier « .puce.file », et l'on aurait rouvert
    le trou par l'autre bout.
    """
    noms = set(re.findall(r'[a-z][a-z0-9-]*',
                          re.sub(r'\$\{.*?\}', " ", valeur, flags=re.S)))
    for expr in re.findall(r'\$\{(.*?)\}', valeur, flags=re.S):
        for litteral in re.findall(r'"([^"]*)"|\'([^\']*)\'|`([^`]*)`', expr):
            for morceau in litteral:
                noms |= set(re.findall(r'[a-z][a-z0-9-]*', morceau))
    return noms


posees = set()
for liste in listes_de_classes(CORPS):
    noms = noms_poses(liste)
    if "puce" in noms:
        posees |= modifs & noms

dormantes = sorted(modifs - posees)
dit(not dormantes, "aucune pastille decrite sans etre jamais posee",
    ", ".join(f".puce.{d}" for d in dormantes) or "toutes servent")

# Les deux tables des reglages, inverses l'une de l'autre, ecrites a deux cents
# lignes d'ecart. C'est la derive de l'une des deux qui a tue les reglages par
# conversation le 31 aout.
#
# « [\w-] » et non « \w » : le trait d'union est la ponctuation ordinaire d'un
# identifiant HTML, et « \w » ne le franchit pas. Nommer « #forcer-moteur » dans
# les deux tables faisait DISPARAITRE l'entree des trois releves d'un coup — les
# tables restaient inverses l'une de l'autre, plus rien ne manquait, et le
# reglage du moteur cessait simplement d'etre retenu. Le defaut du 31 aout, dans
# sa forme la plus muette, sous le nez du banc ecrit pour lui
# (banc_mutations.py, trou 3).
menu = dict(re.findall(r'([\w-]+):\s*"(#[\w-]+)"',
                       PAGE.split("const MENU_REGLAGE = {", 1)[1].split("};", 1)[0]))
cle = dict(re.findall(r'"(#[\w-]+)":\s*"([\w-]+)"',
                      PAGE.split("const CLE_REGLAGE = {", 1)[1].split("};", 1)[0]))
dit(menu and cle and {v: k for k, v in menu.items()} == cle,
    "MENU_REGLAGE et CLE_REGLAGE disent la meme chose",
    f"{len(menu)} contre {len(cle)}")

# re.escape : le selecteur vient de la page, pas de ce fichier. Un identifiant
# a trait d'union passe encore, mais un point ou un plus feraient de la
# recherche un motif, et le banc mesurerait autre chose que ce qu'il croit.
manquants = sorted(sel for sel in menu.values()
                   if not re.search(r'id="' + re.escape(sel[1:]) + r'"', PAGE))
dit(not manquants, "chaque reglage nomme un menu qui existe dans la page",
    ", ".join(manquants) or f"{len(menu)} menus trouves")

# ── le nombre de variantes est un GESTE, pas un reglage ───────────────
# Ce n'est pas un avis, c'est le serveur qui l'a tranche : REGLAGES_CONV ne
# contient pas « variantes », poser_reglages ne le lit donc pas, et
# /api/conversation/{cid}/reglages le jetterait sans un mot. Le jour ou
# quelqu'un le rangera « avec les quatre autres », les deux tables resteront
# inverses l'une de l'autre — la verification ci-dessus passerait — et le menu
# cesserait simplement d'avoir un effet. Exactement le silence du 31 aout.
dit("variantes" not in menu and "#variantes" not in cle,
    "« variantes » reste hors des deux tables : le serveur ne le retient pas",
    f"{sorted(menu)} / {sorted(cle)}")

# Chaque entree de REGLAGES nomme un reglage connu, OU se declare « geste ».
# Sans ce marqueur, le gestionnaire de « change » appelle
# retenirReglages(CLE_REGLAGE[sel]) avec undefined — et retenirReglages sans
# cle renvoie LES QUATRE reglages d'un coup, c'est-a-dire le degat pour lequel
# la table a ete decoupee, declenche par un menu qui n'a rien a voir avec eux.
entrees = re.findall(
    r'\{\s*sel:\s*"(#[\w-]+)"(.*?)\}',
    PAGE.split("const REGLAGES = [", 1)[1].split("\n];", 1)[0], re.S)
orphelines = [s for s, reste in entrees
              if s not in cle and "geste: true" not in reste]
dit(entrees and not orphelines,
    "chaque entree de REGLAGES est un reglage connu ou un geste declare",
    ", ".join(orphelines) or f"{len(entrees)} entrees")

# VARIANTES_MAX = 4 (serveur.py). Au-dela, /api/generer repond 400 « de 1 a 4
# variantes » : un menu qui propose ce que le serveur refuse fabrique une panne
# visible pour un geste ordinaire. Rien en dessous de 2 non plus — « une
# seule » est la valeur vide, et un « 1 » explicite ferait un doublon muet.
choix = PAGE.split('<select id="variantes"', 1)[1].split("</select>", 1)[0]
rangs = sorted(int(v) for v in re.findall(r'<option value="(\d+)"', choix))
dit(rangs == [2, 3, 4],
    "le menu des variantes ne propose rien que le serveur refuserait",
    str(rangs))

# LE DEFAUT QU'ON FERME. Les variantes existaient entierement cote serveur —
# quatre-vingt-une verifications dans banc_variantes.py — et le mot
# n'apparaissait pas une seule fois dans la page : rien ne le postait, rien ne
# l'affichait. Un banc qui teste un contrat que personne n'emprunte ne mesure
# rien (CONTRIBUTING.md).
demande = PAGE.split("function reglagesDemandes()", 1)[1].split("\n}", 1)[0]
dit("c.variantes" in demande and '$("#variantes")' in demande,
    "le nombre de variantes part dans le corps de la demande",
    "pose par reglagesDemandes")

# « priorite » a vecu des mois dans le corps de /api/generer alors que les trois
# autres reglages avaient demenage sur la conversation. Un second onglet reste
# ouvert effaçait donc le cran du premier au simple envoi d'un message.
envois = re.findall(r'fetch\("/api/generer"[^;]*?\}\);', PAGE, re.S)
dit(len(envois) >= 2, f"{len(envois)} envois vers /api/generer reperes")

# Ce releve cherchait « priorite: $("#priorite") » — UNE facon de l'ecrire. Le
# vrai code portait l'abreviation ES6, « priorite, », le menu lu deux lignes
# plus haut : la ligne fautive d'origine restauree sous cette forme-la, ce
# banc-ci restait vert. C'est la panne qui a fait naitre banc_mutations.py, et
# elle y dormait en trou 1.
#
# Ce qui fait le degat n'est pas la FORME de la propriete mais d'ou vient sa
# VALEUR. On releve donc d'abord les noms qui portent le cran du menu, puis on
# regarde si l'un d'eux entre dans un corps de demande — quelle que soit la
# facon de l'y ecrire.
#
# Cette distinction n'est pas un raffinement : « priorite » figure DEJA pour de
# bon dans le second envoi — « ...(priorite ? { priorite } : {}) », le
# brouillon — et c'est le parametre de lancerDemande, jamais une lecture du
# menu. Se contenter de « la cle priorite est dans le corps » ferait rougir le
# depot sain.
# ET LA MEME FAUTE UNE CINQUIEME FOIS. La liste qui tenait ici etait
# litteralement trois FACONS D'ECRIRE — « $("#priorite") »,
# « valeurReglage("priorite") », « reglagesVoulus.priorite » — et la plus
# banale de toutes manquait : « document.getElementById("priorite") ». Verifie
# avant correction : « lancerDemande(document.getElementById("priorite").value) »
# pose dans la page laissait ce banc VERT. Enumerer une ecriture de plus
# n'aurait fait que reculer la sixieme.
#
# On ne nomme donc plus les lecteurs mais la FORME : un appel dont le seul
# argument est ce menu-la, quel que soit le nom de l'appel et la sorte de
# guillemets. « [\w$]+ » pour que « $( » entre aussi.
#
# Le sol reste le meme qu'avant : « mettre("#priorite", ...) » a DEUX arguments
# et n'est donc pas une lecture, tandis que les tables « "#priorite":
# "priorite" » ne sont pas des appels du tout. Sans ces deux exclusions, le
# depot sain rougirait — et un banc qui rougit sur tout n'attrape rien.
LECTURES_DU_MENU = (r'[\w$]+\(\s*["\']#?priorite["\']\s*\)'
                    r'|reglagesVoulus\.priorite')


def separer(args):
    """Decoupe une liste d'arguments sur les virgules DE PREMIER NIVEAU."""
    morceaux, prof, courant = [], 0, ""
    for c in args:
        if c in "([{":
            prof += 1
        elif c in ")]}":
            prof -= 1
        if c == "," and prof == 0:
            morceaux.append(courant)
            courant = ""
            continue
        courant += c
    return morceaux + [courant]


def noms_nourris_par(lecture):
    """Les identifiants qui finissent par porter la valeur lue sur ce menu.

    Deux facons de la recevoir, et la seconde est celle qu'avait la VRAIE panne
    (page de 21c443c^) : « $("#go").onclick = () => lancerDemande($("#priorite")
    .value) » deux mille lignes plus bas que le « priorite, » du corps. Le cran
    entrait par le point d'APPEL, pas par une declaration voisine — s'arreter
    aux « const » aurait ferme la mutation de banc_mutations.py en laissant
    passer le defaut qu'elle imite.
    """
    noms = set()
    for nom, valeur in re.findall(
            r'(?:^|[;{}\n]|\b(?:const|let|var)\s+)\s*([A-Za-z_$][\w$]*)\s*=\s*([^;\n]*)',
            PAGE, re.M):
        if re.search(lecture, valeur):
            noms.add(nom)
    # « ([^()]*(?:\([^()]*\)[^()]*)*) » : un seul etage d'imbrication suffit a
    # tenir « lancerDemande($("#priorite").value) », et evite le motif recursif.
    for fonction, args in re.findall(
            r'\b([A-Za-z_$][\w$]*)\s*\(([^()]*(?:\([^()]*\)[^()]*)*)\)', PAGE):
        rangs = [i for i, a in enumerate(separer(args)) if re.search(lecture, a)]
        if not rangs:
            continue
        f = re.escape(fonction)
        for params in re.findall(
                r'function\s+' + f + r'\s*\(([^)]*)\)'
                r'|\b(?:const|let|var)\s+' + f
                + r'\s*=\s*(?:async\s+)?(?:function\s*)?\(([^)]*)\)', PAGE):
            listes = [p.strip() for p in "".join(params).split(",")]
            for i in rangs:
                if i < len(listes) and re.fullmatch(r'[A-Za-z_$][\w$]*', listes[i]):
                    noms.add(listes[i])
    return noms


noms_du_menu = noms_nourris_par(LECTURES_DU_MENU)


def porte_le_cran(envoi):
    # « priorite: <valeur> », guillemets ou non autour de la cle.
    for valeur in re.findall(r'\bpriorite"?\s*:\s*([^,\n}]*)', envoi):
        if re.search(LECTURES_DU_MENU, valeur):
            return True
    # L'abreviation : « priorite, » ou « priorite }». La valeur est alors la
    # variable du meme nom, et c'est le releve ci-dessus qui dit d'ou elle vient.
    return bool(re.search(r'\bpriorite\s*[,}]', envoi)) and "priorite" in noms_du_menu


fautifs = [e for e in envois if porte_le_cran(e)]
dit(not fautifs, "aucun envoi ne renvoie le cran de priorite du menu",
    f"{len(fautifs)} envoi(s) fautif(s)" if fautifs else "il vit sur la conversation")

# Les DEUX chemins, pas seulement la fleche. Le formulaire de reponse a une
# precision a longtemps oublie la moitie des champs de l'autre : deux listes
# ecrites a mille lignes d'ecart divergent des la premiere correction. Le seul
# remede tenu est qu'aucune des deux n'ecrive de liste — les deux appellent
# reglagesDemandes().
porteurs = [e for e in envois if "reglagesDemandes()" in e]
dit(len(porteurs) == len(envois),
    "les deux chemins d'envoi passent par reglagesDemandes()",
    f"{len(porteurs)} sur {len(envois)}")

# ── la coche « deja refait » ne se lit plus dans le TEXTE du refus ────
# Le contrat de ce refus-la tenait sur un mot. La page affichait « ✓ déjà refait
# en soigné » — donc RETIRAIT le bouton — quand le message du serveur contenait
# « deja » : « r.status === 409 && /deja/i.test(d.erreur) ». Les trois messages
# 409 de /api/au_propre avaient bien ete verifies un par un, mais RIEN ne
# reliait ce test aux chaines du serveur — ni ce banc ni recette_chemin_page.py
# ne contenaient « 409 » ni « deja ». Un accent (« déjà »), une reformulation,
# et la coche verte revenait sur les deux refus ou rien n'a ete rendu : le
# mensonge que d24980a venait de fermer, revenu sans qu'une ligne de la page ne
# bouge.
#
# LES DEUX MOITIES DU CONTRAT SONT MESUREES A DEUX ENDROITS, et c'est voulu :
# ici la page — elle nomme le champ et ne lit plus le texte —, dans
# banc_refaire.py le serveur, qui releve ce meme nom DANS CE FICHIER-CI et
# exige que la route le pose sur ce refus et sur aucun autre. Ce banc-ci est
# statique et ne peut pas appeler la route ; celui-la ne peut pas voir ce que
# la page fait de la reponse.
#
# Zero declaration compte comme un NON, et plusieurs aussi — on ne saurait plus
# laquelle la page applique. Meme doctrine que RE_DEVIS dans banc_variantes.py :
# une verification qui ne mesure plus rien et se compte verte ment deux fois.
marques = re.findall(r'const\s+MARQUE_DEJA\s*=\s*"([^"]*)"\s*;', CORPS)
dit(len(marques) == 1 and bool(marques[0]),
    "la page NOMME le champ par lequel le serveur dit « c'est deja fait »",
    f"{len(marques)} declaration(s) de MARQUE_DEJA : ce banc NE MESURE PLUS le "
    "couplage page/serveur, et banc_refaire.py non plus"
    if len(marques) != 1 else marques[0])


def condition_du_si(texte, ancre):
    """La condition du « if » dont cette ancre-la est le corps, ou None.

    On remonte de l'ancre a la parenthese fermante qui la precede, puis on
    equilibre a rebours : nommer la condition par une expression reguliere
    reviendrait a decrire UNE facon de l'ecrire, la faute que ce banc a deja
    faite cinq fois (voir LECTURES_DU_MENU). « (d.erreur || "") » en porte
    d'ailleurs une paire, que « [^)]* » coupait en deux.
    """
    i = texte.find(ancre)
    if i < 0:
        return None
    ferme = texte.rfind(")", 0, i)
    if ferme < 0:
        return None
    prof, j = 1, ferme - 1
    while j >= 0 and prof:
        prof += (texte[j] == ")") - (texte[j] == "(")
        j -= 1
    if prof:
        return None
    ouvre = j + 1
    if not re.search(r'\bif\s*$', texte[:ouvre]):
        return None
    return texte[ouvre + 1:ferme]


# L'ancre est le LIBELLE AFFICHE, accents compris : c'est la donnee, et c'est
# le seul point du script ou la coche du « deja » se pose. S'il est reformule,
# ce cas rougit en disant qu'il ne mesure plus — ce qui est le bon sens de
# l'erreur, et non un silence de plus.
cond = condition_du_si(CORPS, 'fait("déjà refait en soigné")')
dit(cond is not None and "MARQUE_DEJA" in cond and "erreur" not in cond,
    "et la coche se decide sur ce champ, jamais sur le texte du message",
    "le libelle de la coche n'est plus sous un « if » : ce cas ne mesure plus "
    "rien" if cond is None else cond.strip())

# ── designer la variante retenue ──────────────────────────────────────
# POST /api/variante decide laquelle « la » designe : « agrandis-la », « rends-la
# fluide », « le meme personnage ». Sans ce geste dans la page, les quatre
# images sortent bien, mais c'est toujours la premiere qui est visee et rien ne
# permet d'en preferer une autre.
dit('fetch("/api/variante"' in CORPS, "la page emprunte POST /api/variante")

# api_mediatheque sert « variante » (le rang), « variantes » (le total) et
# « choisie » depuis le debut, et la legende jetait les trois : quatre variantes
# ont le meme prompt, le meme moteur, la meme taille et la meme minute, donc
# quatre lignes rigoureusement indiscernables.
grille = PAGE.split("function peindreGrille()", 1)[1].split("\nfunction ", 1)[0]
# « \b » : sans lui, « f.variantes » suffirait a faire passer « f.variante ».
oublies = [c for c in ("f.variante", "f.variantes", "f.choisie")
           if not re.search(re.escape(c) + r'\b', grille)]
dit(not oublies, "la mediatheque lit le rang et la marque que le serveur sert",
    ", ".join(oublies) or "les trois")

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
for r in rate:
    print("    a regarder :", r)
sys.exit(1 if rate else 0)
