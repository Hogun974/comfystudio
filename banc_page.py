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
import ast
import io
import os
import re
import sys
from html.parser import HTMLParser

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

# LE DICTIONNAIRE, ET C'EST LA SEULE CHOSE QUE CE BANC IMPORTE. traductions.py
# n'importe rien lui-meme : le banc reste statique, sans reseau, sans studio,
# sans aiohttp. Il en a besoin pour la moitie de contrat la plus importante
# qu'il tienne — que le francais ecrit dans le HTML soit EXACTEMENT celui du
# dictionnaire, faute de quoi une reformulation d'un seul cote laisse un
# lecteur anglais devant une traduction devenue fausse.
import traductions as TR  # noqa: E402

PAGE = io.open(os.path.join(ICI, "web", "index.html"), encoding="utf-8").read()

# SERVEUR.PY EST LU, PAS IMPORTE — il tirerait aiohttp derriere lui, que la
# machine du releve n'a pas. Une seule chose y est cherchee : le NOM du champ
# par lequel il dit « il manque le second facteur ». C'est la moitie de contrat
# qui manquait a MARQUE_DEJA et a MARQUE_DEVIS, et qu'il fallait aller chercher
# dans un banc a studio ; ici le champ est une constante, donc les deux moities
# se relevent au meme endroit.
SERVEUR = io.open(os.path.join(ICI, "serveur.py"), encoding="utf-8",
                  newline=None).read()
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

# ── la pastille des reglages ne DECOUPE plus un libelle visible ───────
# Trois entrees de REGLAGES portaient leur propre lecteur, et il decoupait le
# texte affiche d'une <option> sur le tiret cadratin :
# « o.textContent.split(" — ")[0] ». Le separateur d'un texte d'INTERFACE
# devenait le contrat d'un bout de code, et rien nulle part ne le disait :
# reformuler « rapide — moins d'étapes », ou l'ecrire avec un tiret ordinaire,
# et la pastille affichait la phrase entiere sans une plainte. Meme famille que
# « /deja/i.test(d.erreur) » et que RE_DEVIS — du texte ecrit pour l'oeil qui
# sert de contrat.
#
# Le libelle court est un ATTRIBUT desormais, « data-court », et les deux
# moities se mesurent ici : que chaque option qui porte une valeur le porte
# aussi, et qu'aucune lecture ne recoupe plus le libelle visible.
#
# UN SEUL LECTEUR, ET PAS UN PAR ENTREE. C'est la garde structurelle : tant que
# la table peut porter « lire: », la coupure peut revenir par n'importe quelle
# ecriture, et enumerer les ecritures est la faute que ce banc a deja faite
# cinq fois (voir LECTURES_DU_MENU). On exige donc que les entrees ne portent
# rien d'autre que « nom » et « geste ».
lecteurs = sorted({m for _s, reste in entrees
                   for m in re.findall(r'\b(\w+)\s*:', reste)} - {"nom", "geste"})
dit(entrees and not lecteurs,
    "aucune entree de REGLAGES ne porte son propre lecteur",
    ", ".join(lecteurs) or f"{len(entrees)} entrees, un seul lecteur")


def options_du_menu(sel):
    """Les <option> ecrites dans la page pour ce menu-la, telles quelles."""
    depart = re.search(r'<select id="' + re.escape(sel[1:]) + r'"', PAGE)
    if not depart:
        return []
    bloc = PAGE[depart.start():].split("</select>", 1)[0]
    return re.findall(r'<option\b[^>]*>', bloc)


# Une option sans valeur est le « automatique » de tete : il ne pose pas de
# pastille du tout, et lui reclamer un libelle court ferait rougir le depot
# sain. Les deux menus construits en JavaScript n'ont ici que celle-la ; leur
# moitie a eux est le releve suivant.
nus = [f"{sel} {o}" for sel, _reste in entrees
       for o in options_du_menu(sel)
       if re.search(r'value="[^"]+"', o) and not re.search(r'data-court="[^"]+"', o)]

# ENTRE SA CREATION ET SON AJOUT AU MENU : c'est la borne du bloc, et non un
# nombre de lignes choisi au hasard. Les deux blocs de la page — /api/modeles
# et /api/machines — posent la valeur, le libelle et l'attribut, puis
# « sel.appendChild(o) ».
faits = PAGE.split('document.createElement("option")')[1:]
sans = [i + 1 for i, bloc in enumerate(faits)
        if "dataset.court" not in bloc.split("appendChild", 1)[0]
        and 'setAttribute("data-court"' not in bloc.split("appendChild", 1)[0]]
dit(not nus and faits and not sans,
    "chaque option d'un menu de reglage porte son libelle court",
    ", ".join(nus + [f"option construite n°{i}" for i in sans])
    or f"{sum(len(options_du_menu(s)) for s, _r in entrees)} ecrites, "
       f"{len(faits)} construites")

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


# L'ancre est la CLE du libelle affiche, et non plus le libelle : depuis que
# la page passe par T(), le texte francais vit au dictionnaire et la page ne
# porte que son identifiant. C'est le seul point du script ou la coche du
# « deja » se pose ; si l'appel est reecrit, ce cas rougit en disant qu'il ne
# mesure plus — ce qui est le bon sens de l'erreur, et non un silence de plus.
# Que la cle designe bien le bon texte francais est mesure a part, plus bas :
# « la page et le dictionnaire disent le meme francais ».
cond = condition_du_si(CORPS, 'fait(T("page.au_propre.deja"))')
dit(cond is not None and "MARQUE_DEJA" in cond and "erreur" not in cond,
    "et la coche se decide sur ce champ, jamais sur le texte du message",
    "le libelle de la coche n'est plus sous un « if » : ce cas ne mesure plus "
    "rien" if cond is None else cond.strip())


# ── LE DEVIS ET L'ARRET DIFFERE : DEUX CHAMPS, PLUS DEUX PHRASES ──────
# Deux contrats de la meme famille que le « deja refait », et le second etait
# pire que lui.
#
#   - LE DEVIS de la pastille etait tire d'une PHRASE DE JOURNAL par expression
#     reguliere — « rendus precedents, compte 4 min » —, virgule decimale
#     française comprise (« parseFloat(m[1].replace(",", ".")) »). Muet a la
#     premiere reformulation, et FAUX de naissance : la phrase arrondit, et
#     « 2 min » pour une mediane de 90 s faisait afficher 120 s. /api/etat sert
#     le chiffre depuis le debut.
#   - LA RELECTURE DIFFEREE apres une interruption se decidait sur
#     « /^arret demande a /.test(t.erreur) ». Le texte teste venait d'etre
#     ECRASE six lignes plus haut par la derniere ligne du journal : le contrat
#     traversait deux fichiers ET une substitution. Journaliser une ligne de
#     plus apres celle-la coupait la relecture en silence, et la bulle restait
#     sur « arret demande » — une promesse — pendant que la carte s'arretait.
#
# Comme pour MARQUE_DEJA, chaque moitie est mesuree la ou elle se voit : ici la
# page nomme le champ et ne lit plus le texte, dans banc_variantes.py les deux
# routes le posent — et ce banc-la releve les noms DANS CE FICHIER-CI. Zero
# declaration compte comme un NON, plusieurs aussi : on ne saurait plus laquelle
# la page applique.
for nom_marque, quoi in (("MARQUE_DEVIS",
                          "la page NOMME le champ par lequel le studio chiffre "
                          "le devis"),
                         ("MARQUE_ARRET_DIFFERE",
                          "et celui par lequel il dit qu'un arret n'est encore "
                          "qu'une promesse")):
    vues = re.findall(r'const\s+' + nom_marque + r'\s*=\s*"([^"]*)"\s*;', CORPS)
    dit(len(vues) == 1 and bool(vues[0]), quoi,
        f"{len(vues)} declaration(s) de {nom_marque} : ce banc NE MESURE PLUS "
        "le couplage page/serveur, et banc_variantes.py non plus"
        if len(vues) != 1 else vues[0])

# L'ancre est la FONCTION qui rend le devis, et le releve porte sur ce qu'elle
# lit : le champ, et plus les etapes. Les appels avec, car reverser le seul
# point d'appel — « lireDevis(t.etapes) » — rendrait undefined a chaque tour et
# ferait disparaitre la pastille sans qu'une ligne de la fonction ne bouge.
corps_devis = CORPS.split("function lireDevis(", 1)
appels = re.findall(r'lireDevis\(([^)]*)\)', CORPS)
dit(len(corps_devis) == 2 and "MARQUE_DEVIS" in corps_devis[1].split("\n}", 1)[0]
    and not any("etapes" in a for a in appels),
    "et le devis affiche vient de ce champ, jamais du journal",
    ", ".join(appels) or "lireDevis introuvable")

# « condition_du_si » plutot qu'un motif : nommer la condition par une
# expression reguliere reviendrait a decrire UNE facon de l'ecrire. L'ancre est
# le corps du « if », c'est-a-dire le seul setTimeout du script.
cond_arret = condition_du_si(CORPS, "setTimeout(async () => {")
# « ETAT.erreur » EST RETIRE AVANT LE RELEVE, et c'est la separation que ce
# banc mesure trois cas plus bas : « erreur » est A LA FOIS la valeur de
# protocole que le serveur ecrit sur la tache et le nom du champ qui porte le
# message. Le releve d'origine ne savait pas les distinguer — il aurait fait
# rougir le depot sain sur « t.etat === ETAT.erreur », qui est justement la
# lecture correcte. Ce qui est interdit ici, c'est de decider sur le MESSAGE.
_sans_etat = re.sub(r'\bETAT\.[a-z_]+', " ", cond_arret or "")
dit(cond_arret is not None and "MARQUE_ARRET_DIFFERE" in cond_arret
    and not re.search(r'\.erreur\b|\[\s*["\']erreur["\']\s*\]', _sans_etat),
    "et la relecture differee se decide sur ce champ, jamais sur le message",
    "la relecture differee n'est plus sous un « if » : ce cas ne mesure plus "
    "rien" if cond_arret is None else cond_arret.strip())

# ── LE SECOND FACTEUR : LE CHAMP SE NOMME DES DEUX COTES ──────────────
# Troisieme contrat de la meme famille, et le premier dont les DEUX moities se
# mesurent ici. MARQUE_DEJA et MARQUE_DEVIS demandent un studio qui tourne pour
# dire quel refus pose le champ, et ce sont banc_refaire.py et banc_variantes.py
# qui s'en chargent. Celui-ci n'en demande pas : le champ est une CONSTANTE
# nommee dans serveur.py, et il suffit de relever les deux declarations pour
# exiger qu'elles disent le meme mot.
#
# CE QUE LA DERIVE COUTERAIT, si l'une bougeait seule : le champ du code ne
# s'afficherait plus jamais. L'utilisateur d'un compte arme taperait son mot de
# passe juste et lirait « nom, mot de passe ou code incorrect » sans qu'aucune
# case ne lui soit offerte — un studio qui refuse un mot de passe juste, sans
# qu'une ligne de la page ni du serveur n'ait l'air fautive.
#
# Zero declaration compte comme un NON, et plusieurs aussi : on ne saurait plus
# laquelle s'applique. Meme doctrine que MARQUE_DEJA.
_mfa_page = re.findall(r'const\s+MARQUE_MFA\s*=\s*"([^"]*)"\s*;', CORPS)
_mfa_serveur = re.findall(r'(?m)^MARQUE_MFA\s*=\s*"([^"]*)"\s*$', SERVEUR)
dit(len(_mfa_page) == 1 and len(_mfa_serveur) == 1 and bool(_mfa_page[0])
    and _mfa_page == _mfa_serveur,
    "le champ « il manque le second facteur » porte le MEME nom dans la page "
    "et dans le serveur",
    f"page {_mfa_page} / serveur {_mfa_serveur}")

# ET LA CASE S'OUVRE SUR CE CHAMP, JAMAIS SUR LE MESSAGE NI SUR LE CODE DE
# RETOUR. Les deux ecrans qui la demandent sont releves : la porte d'entree et
# le panneau du second facteur. « condition_du_si » plutot qu'un motif — nommer
# la condition par une expression reguliere reviendrait a decrire UNE facon de
# l'ecrire, la faute que ce banc a deja faite cinq fois.
for _ancre, _quoi in (
        ("demanderCode(f, mal); return; }",
         "et l'ecran de connexion ouvre la case du code sur ce champ, jamais "
         "sur le texte du refus"),
        ("demanderCode(f, mal); return null; }",
         "le panneau du second facteur l'ouvre de la meme facon")):
    _cond = condition_du_si(CORPS, _ancre)
    dit(_cond is not None and "MARQUE_MFA" in _cond and "erreur" not in _cond,
        _quoi,
        "la case du code n'est plus sous un « if » : ce cas ne mesure plus rien"
        if _cond is None else _cond.strip())

# ── LES DEUX PHRASES QUE L'ENROLEMENT NE PEUT PAS TAIRE ───────────────
# Aucune des deux ne se devine, et les deux coutent un compte a qui l'ignore :
#
#   - LES CODES DE SECOURS NE S'AFFICHENT QU'UNE FOIS. Ce qui est garde est
#     leur empreinte scrypt ; qui ferme l'onglet en pensant les retrouver dans
#     ses reglages ne les retrouvera pas, et personne ne peut les redonner —
#     pas meme l'administrateur, puisque c'est exactement ce qu'on vient
#     d'empecher.
#   - LE CODE QUI A CONFIRME L'ENROLEMENT EST DEJA CONSOMME
#     (comptes.mfa_confirmer garde son pas, et banc_comptes.py le mesure).
#     Celui qui vient de le taper le lit encore sur son telephone, le retape
#     aussitot, se voit refuse, et croit que son enrolement a rate. Trente
#     secondes au plus, le pas de la RFC 6238.
#
# L'ancre est la FONCTION qui peint cet ecran-la : les chercher dans la page
# entiere les trouverait dans un commentaire, ou sur un ecran ou personne ne
# les lit. Fonction introuvable vaut NON — le cas dit alors qu'il ne mesure
# plus rien, ce qui est le bon sens de l'erreur.
_bloc_secours = CORPS.split("const peindreSecours =", 1)
_dedans = _bloc_secours[1].split("\n  };", 1)[0] if len(_bloc_secours) == 2 else ""
# LE RELEVE NOMME CELLE QUI MANQUE, et ce n'est pas un ornement : la premiere
# version de ce cas imprimait « les deux phrases y sont » a cote de sa propre
# ligne ROUGE, parce que le detail ne distinguait que « fonction introuvable »
# du reste. Un banc qui rougit en disant le contraire de ce qu'il a vu envoie
# chercher la panne ailleurs.
_sans_phrase = [c for c in ("page.mfa.secours.unique", "page.mfa.attente")
                if c not in _dedans]
dit(len(_bloc_secours) == 2 and not _sans_phrase,
    "l'ecran des codes de secours dit qu'ils ne s'affichent QU'UNE fois, et "
    "annonce l'attente d'au plus trente secondes",
    "peindreSecours introuvable : ce cas ne mesure plus rien"
    if len(_bloc_secours) != 2
    else (", ".join(_sans_phrase) + " : absente de cet ecran") if _sans_phrase
    else "les deux phrases y sont")

# ── ET LE MEME PIEGE NULLE PART AILLEURS ──────────────────────────────
# Les trois defauts fermes se ressemblaient trop pour n'etre nommes qu'un par
# un : chaque fois, une expression reguliere s'appliquait a un texte ecrit pour
# etre LU — un message d'erreur, une ligne de journal. On releve donc TOUTES
# les applications du script et l'on exige que leur operande soit un NOM DE
# FICHIER, seul texte de la page dont la forme soit un vrai contrat technique
# (EXT_IMG, EXT_VID, EXT_SON sur f.filename).
#
# Le sol est pris par le haut et non par une liste de mauvais operandes : une
# liste aurait dit UNE facon d'ecrire la panne, la faute que ce banc a deja
# faite cinq fois (voir LECTURES_DU_MENU). Le jour ou une application
# legitime portera sur autre chose, ce cas rougira et demandera qu'on
# l'inscrive ici — c'est le bon sens de l'erreur.
#
# LES COMMENTAIRES SONT RETIRES D'ABORD, comme pour le CSS plus haut : la page
# explique « /deja/i.test(d.erreur) », « /^arret demande a /.test( » et
# « split(" — ") » dans les commentaires qui disent justement pourquoi ces
# lignes n'existent plus, et ce banc se signalerait lui-meme. Les trois
# ecritures, HTML comprise : le libelle court est explique a cote des <option>
# qui le portent, c'est-a-dire dans un commentaire HTML.
CODE = re.sub(r'<!--.*?-->', " ", CORPS, flags=re.S)
CODE = re.sub(r'/\*.*?\*/', " ", CODE, flags=re.S)
CODE = re.sub(r'(?m)^\s*//.*$', "", CODE)


def operandes(texte, verbe):
    """Ce a quoi chaque « .test( » / « .exec( » / « .match( » s'applique."""
    for depart in re.finditer(r'\.\s*' + verbe + r'\s*\(', texte):
        i, prof = depart.end(), 1
        while i < len(texte) and prof:
            prof += (texte[i] in "([{") - (texte[i] in ")]}")
            i += 1
        # « || "" » n'est pas l'operande, c'est son garde-fou.
        yield re.sub(r'\|\|.*$', "", texte[depart.end():i - 1]).strip()


sur_du_texte = [o for verbe in ("test", "exec", "match")
                for o in operandes(CODE, verbe)
                if not re.fullmatch(r'[\w.$\[\]]*\.(?:filename|name)', o)]
dit(not sur_du_texte,
    "aucune expression reguliere ne s'applique a un texte ecrit pour etre lu",
    ", ".join(sur_du_texte) or "toutes sur un nom de fichier")

# Et le tiret cadratin ne recoupe plus rien nulle part : c'etait LE separateur
# qui servait de contrat entre le libelle d'une <option> et la pastille, et il
# n'y a pas deux facons de l'ecrire.
coupes = [c for _g, c in re.findall(r'\.\s*split\s*\(\s*(["\'`])([^"\'`]*\u2014[^"\'`]*)\1',
                                    CODE)]
dit(not coupes, "et aucun libelle visible n'est recoupe sur le tiret cadratin",
    ", ".join(f"« {c} »" for c in coupes) or "aucune coupure")

# ── LE QR CODE DE L'ENROLEMENT ────────────────────────────────────────
# QUATRE REGLES, ET CHACUNE GARDE UNE PANNE QUI NE LEVE PAS. Un QR mal dessine
# ne casse rien, ne se signale pas, et ne se lit pas : l'appareil photo reste
# ouvert sur l'ecran et rien ne se passe. C'est la famille de defauts la plus
# silencieuse de cette page, et aucune ne se voit en relisant.
_bloc_qr = CODE.split("function dessinerQR(", 1)
_dessin = _bloc_qr[1].split("\n}", 1)[0] if len(_bloc_qr) == 2 else ""

# 1. LE PIEGE DU THEME SOMBRE. Un QR se lit sur fond CLAIR avec des modules
#    SOMBRES. Cette page est sombre par defaut (« color-scheme:dark », le clair
#    n'arrive que par « prefers-color-scheme: light ») : dessiner les modules
#    avec la couleur de texte sur le fond de la page INVERSE le code, et
#    beaucoup de lecteurs refusent un code inverse — sans message, en n'affichant
#    rien. Les couleurs du QR ne suivent donc AUCUNE variable de theme, ni dans
#    le SVG ni dans la regle qui le porte.
_regle_qr = re.search(r'\.entree\s+\.qr\s*\{([^}]*)\}', CSS)
_couleurs = re.findall(r'fill\s*=\s*"([^"]*)"', _dessin)
dit(len(_bloc_qr) == 2 and _regle_qr is not None
    and "var(--" not in _dessin and "var(--" not in _regle_qr.group(1)
    and sorted(_couleurs) == ["#000000", "#ffffff"],
    "le QR code ne suit PAS le theme : ses couleurs sont ecrites en clair, des "
    "deux cotes",
    "dessinerQR introuvable : ce cas ne mesure plus rien" if len(_bloc_qr) != 2
    else "« .entree .qr » n'existe plus dans la feuille" if _regle_qr is None
    else f"fill={_couleurs}, et « var(--…) » nulle part")

# 2. LA ZONE DE SILENCE EST DANS LE DESSIN. Quatre modules clairs tout autour,
#    ce que la norme exige : sans eux, un lecteur pose contre le fond sombre de
#    la page ne trouve pas les trois coins de reperage. Elle est dans le
#    viewBox et non en marge CSS — une marge se recouvre, se supprime au
#    retrecissement, et ne suit pas l'image quand on la copie.
_marge = re.findall(r'(?m)^const\s+MARGE_QR\s*=\s*(\d+)\s*;', CORPS)
_boite = re.search(r'const\s+cote\s*=\s*n\s*\+\s*2\s*\*\s*MARGE_QR', _dessin)
dit(_marge == ["4"] and _boite is not None
    and "MARGE_QR}" in _dessin and 'viewBox="0 0 ${cote} ${cote}"' in _dessin,
    "et sa zone de silence fait quatre modules, posee dans le viewBox du SVG",
    f"MARGE_QR={_marge}, cote {'calcule' if _boite else 'NON calcule'} depuis "
    f"elle")

# 3. LE SECRET RESTE ECRIT A COTE. Un QR ne se recopie pas a la main quand
#    l'appareil photo ne marche pas, et c'est le SEUL chemin pour quelqu'un qui
#    enrole depuis la machine qui affiche l'ecran — un telephone ne se
#    photographie pas lui-meme. Le remplacer par le seul code enfermerait
#    celui-la dehors, et rien a l'ecran ne le lui dirait.
_bloc_enrol = CORPS.split("const peindreEnrolement =", 1)
_enrol = _bloc_enrol[1].split("\n  };", 1)[0] if len(_bloc_enrol) == 2 else ""
_manque = [c for c in ("page.mfa.scanne", "page.mfa.recopie", "page.mfa.lien")
           if c not in _enrol]
dit(len(_bloc_enrol) == 2 and not _manque and "dessinerQR(" in _enrol
    and "groupeQuatre(" in _enrol,
    "l'ecran d'enrolement offre les TROIS chemins : le code, le secret ecrit, "
    "le lien",
    "peindreEnrolement introuvable : ce cas ne mesure plus rien"
    if len(_bloc_enrol) != 2
    else ", ".join(_manque) + " : absent de cet ecran" if _manque
    else "scanner, recopier, ouvrir")

# 4. LE CHAMP QUE LE SERVEUR SERT EST CELUI QUE LA PAGE LIT. Meme famille que
#    MARQUE_MFA, et la meme panne si les deux moities derivent : le QR
#    disparaitrait de l'ecran sans qu'une ligne ait l'air fautive, et personne
#    ne verrait que dessinerQR() rend null sur un « undefined ». Les deux
#    ecritures sont relevees, pas une seule.
_sert = re.search(r'return web\.json_response\(dict\(_etat_mfa\(nom\), '
                  r'secret=secret, uri=uri,\s*\n\s*qr=matrice\)\)', SERVEUR)
dit(_sert is not None and "dessinerQR(d.qr)" in CORPS,
    "et la page dessine le champ « qr » que la route d'enrolement sert",
    "la route ne sert plus « qr » : ce cas ne mesure plus rien"
    if _sert is None else "serveur qr=matrice / page dessinerQR(d.qr)")

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


# ══ LA PAGE ET LE DICTIONNAIRE DISENT-ILS LE MEME FRANCAIS ? ═══════════
# C'EST LA MOITIE DE CONTRAT LA PLUS IMPORTANTE DE CE BANC, et elle a la meme
# forme que MARQUE_DEJA et MARQUE_DEVIS : deux fichiers portent la meme chose,
# et un banc releve les deux pour que le jour ou l'un bouge, il rougisse au
# lieu de laisser le contrat mentir.
#
# traductions.py porte le francais AUSSI, alors que la page l'a deja en dur
# dans son HTML. Ce n'est pas une redondance : le HTML est ce qu'un
# francophone voit tout de suite, sans attendre /api/textes ; le dictionnaire
# est ce qu'un anglophone recoit. Reformuler l'un sans l'autre ne casse RIEN —
# la page francaise reste juste, le studio ne leve pas, et un lecteur anglais
# se retrouve devant une traduction devenue fausse sans que personne au studio
# ne l'apprenne jamais. Une traduction ne plante pas, elle ment
# (banc_traductions.py).
#
# ZERO CLE RELEVEE VAUT NON. Le compte est le temoin : sans lui, ce cas serait
# vert le jour ou plus aucun « data-t » ne serait pose — parce qu'on les aurait
# retires, ou parce que le releve aurait cesse de mordre. C'est le defaut que
# banc_refaire.py portait treize fois le 2 septembre, et banc_traductions.py
# une : verte parce que rien ne s'est passe.
print("\n  ── le francais de la page est celui du dictionnaire ──")


class _Marques(HTMLParser):
    """Les « data-t » et « data-t-X » du corps, avec ce qu'ils portent.

    On lit le HTML par un ANALYSEUR et non par expression reguliere : un
    attribut sur trois lignes, un ordre d'attributs different, une entite
    (« &nbsp; ») — un motif de texte en voit un, l'analyseur les voit tous.
    C'est la meme raison qui fait lire serveur.py par l'arbre de syntaxe dans
    banc_traductions.py.

    Les noeuds porteurs de « data-t » sont des feuilles : leur texte est celui
    qui suit la balise ouvrante. Le jour ou l'un en portera un autre dedans,
    ce releve rendra le texte des deux et le cas rougira — ce qui est le bon
    sens de l'erreur : un texte a trous ne se traduit pas d'un bloc.
    """

    # Les attributs qui portent du TEXTE. Ce n'est pas une liste des attributs
    # qu'on a pense a traduire, c'est celle des attributs qui se LISENT : si
    # l'un d'eux est ecrit en clair sans cle, il restera francais.
    PORTEURS = ("title", "placeholder", "aria-label")

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.textes, self.attributs, self.nus, self._pile = [], [], [], []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        for nom, valeur in d.items():
            if nom == "data-t":
                self._pile.append([valeur, ""])
            elif nom.startswith("data-t-"):
                self.attributs.append((valeur, nom[7:], d.get(nom[7:])))
        for nom in self.PORTEURS:
            if nom in d and "data-t-" + nom not in d:
                self.nus.append(f"<{tag} {nom}=\"{(d[nom] or '')[:40]}\">")

    def handle_data(self, data):
        if self._pile:
            self._pile[-1][1] += data

    def handle_endtag(self, tag):
        if self._pile:
            cle, texte = self._pile.pop()
            self.textes.append((cle, texte))


# Le corps SEUL : le script porte « <span class="…"> » dans des chaines, et
# l'analyseur y verrait des balises. La borne est la meme que celle du CSS
# plus haut, prise par l'autre bout.
_CORPS_HTML = PAGE.split("<body>", 1)[1].split("<script>", 1)[0]
_marques = _Marques()
_marques.feed(_CORPS_HTML)

# « _c » et non « cle » : « cle » est la table CLE_REGLAGE, relevee plus haut
# et relue plus bas. Une boucle qui l'ecrase transformait la table en chaine,
# et les deux cas qui la lisent se comptaient verts sur des lettres.
ecarts_t = []
for _c, _texte in _marques.textes:
    attendu = (TR.TEXTES.get(_c) or {}).get("fr")
    if _texte != attendu:
        ecarts_t.append(f"{_c} : page « {_texte} » vs dictionnaire « {attendu} »")
for _c, _attribut, _valeur in _marques.attributs:
    attendu = (TR.TEXTES.get(_c) or {}).get("fr")
    if _valeur != attendu:
        ecarts_t.append(f"{_c} [{_attribut}] : page « {_valeur} » vs "
                        f"dictionnaire « {attendu} »")
_releves = len(_marques.textes) + len(_marques.attributs)
dit(_releves > 0 and not ecarts_t,
    "chaque texte francais du HTML est EXACTEMENT celui du dictionnaire",
    " / ".join(ecarts_t[:2])
    or f"{len(_marques.textes)} textes, {len(_marques.attributs)} attributs")

# ET AUCUN ATTRIBUT QUI SE LIT N'EST OUBLIE. Le sol est pris par le haut :
# non pas la liste de ce qu'on a pense a traduire — enumerer est la faute que
# ce banc a deja faite cinq fois (voir LECTURES_DU_MENU) —, mais celle des
# attributs qui portent du texte. Tout « title », « placeholder » ou
# « aria-label » ecrit sans cle restera francais.
#
# LES aria-label COMPTENT DOUBLE : un lecteur d'ecran anglophone a qui l'on
# annonce « Afficher les conversations » n'est pas servi, et rien a l'ecran ne
# le montrerait. C'est le defaut le plus silencieux de tous, puisqu'il ne se
# voit pas — il s'entend.
_aria = [a for _c, a, _v in _marques.attributs if a == "aria-label"]
dit(_aria and not _marques.nus,
    "chaque titre, invite et aria-label du HTML passe par une cle",
    ", ".join(_marques.nus[:3])
    or f"{len(_marques.attributs)} attributs, dont {len(_aria)} aria-label")

# LES CLES CITEES EXISTENT. Une faute de frappe ne leve pas : T() rend la cle
# elle-meme, et « page.telecharge » s'affiche sur le bouton. Laid, mais
# seulement pour qui regarde — et seulement en anglais, puisque le HTML garde
# son francais.
#
# « page.langue. » et « page.media.famille. » sont COMPOSEES a l'execution
# (« "page.langue." + lg ») : un litteral qui finit par un point est donc lu
# comme un prefixe, et couvre les cles qui commencent par lui.
citees = set(re.findall(r'["\'](page\.[a-z0-9_.]*)["\']', PAGE))
prefixes = {c for c in citees if c.endswith(".")}
citees -= prefixes


def couvre(c):
    return c in citees or any(c.startswith(p) for p in prefixes)


inventees = sorted(c for c in citees if c not in TR.TEXTES)
dit(citees and not inventees,
    "et toute cle citee par la page existe au dictionnaire",
    ", ".join(inventees[:3]) or f"{len(citees)} cles citees")

# ET AUCUNE CLE « page. » NE DORT. Le sens inverse, celui que
# banc_traductions.py tient deja pour les pannes du serveur : une entree
# qu'aucun site ne pose ne sera jamais lue, sa traduction se perimerait sans
# bruit, et le dictionnaire donnerait l'impression de couvrir un ecran qui
# n'existe plus.
dormantes_t = sorted(c for c in TR.TEXTES
                     if c.startswith("page.") and not couvre(c))
dit(not dormantes_t, "et aucune cle « page. » ne dort au dictionnaire",
    ", ".join(dormantes_t[:3]) or
    f"{sum(1 for c in TR.TEXTES if c.startswith('page.'))} cles de page")


# ══ L'ECRAN DE PREMIERE MISE EN ROUTE ══════════════════════════════════
# web/demarrage.html est la SECONDE page traduite du depot — /admin, lui, reste
# en francais parce qu'il parle a celui qui heberge, apres coup. Celle-ci parle
# a quelqu'un qui vient de lancer le studio, c'est-a-dire au seul moment ou
# personne n'a encore choisi sa langue : elle est donc tenue au meme contrat que
# web/index.html, et les cinq releves ci-dessous sont les siens, refaits sur
# elle.
#
# S'Y AJOUTENT DEUX COUPLAGES QUI N'EXISTENT QUE POUR CET ECRAN :
#   - la table des VERDICTS, ecrite des deux cotes (serveur.py la nomme, la page
#     la peint) — meme patron que MENU_REGLAGE et CLE_REGLAGE, dont la derive a
#     fait perdre un reglage pendant des jours ;
#   - la regle qui fait tenir l'ecran a cote de /admin sans deriver : il MESURE
#     et il RENVOIE, il ne repose aucun reglage. Elle se verifie, et c'est ce
#     qui l'empeche d'etre une intention.
print("\n  ── l'ecran de premiere mise en route ──")

# ZERO FICHIER VAUT NON, ET EXPLICITEMENT. Ouvrir sans filet ferait MOURIR ce
# banc la ou il doit rougir — sur un depot ou l'ecran n'existe pas encore, ou
# sur celui d'ou on l'aurait retire. Un banc qui se casse ne dit rien : c'est
# la distinction que banc_mutations.py fait entre « casse » et « rouge », et
# elle vaut aussi pour un fichier absent.
try:
    DEMARRAGE = io.open(os.path.join(ICI, "web", "demarrage.html"),
                        encoding="utf-8", newline=None).read()
except OSError as _e:
    DEMARRAGE = ""
dit(bool(DEMARRAGE),
    "l'ecran de premiere mise en route existe : web/demarrage.html",
    f"{len(DEMARRAGE)} octets" if DEMARRAGE else "fichier absent")

# DEPUIS LE DEBUT DU FICHIER, ET NON DEPUIS <body> comme pour index.html : le
# <title> de cette page-ci porte une cle, et il vit dans l'en-tete. Le laisser
# hors du releve laissait un texte francais dans une interface anglaise, sans
# qu'aucun cas ne puisse le voir. La borne haute reste la meme — le script
# porte « <span class="…"> » dans des chaines, que l'analyseur lirait comme des
# balises — et le <style> traverse sans dommage : son contenu est une donnee,
# et _Marques n'en retient que ce qui tombe DANS un element porteur de
# « data-t ».
_CORPS_DEM = DEMARRAGE.split("<script>", 1)[0]
_md = _Marques()
_md.feed(_CORPS_DEM)

ecarts_d = []
for _c, _texte in _md.textes:
    attendu = (TR.TEXTES.get(_c) or {}).get("fr")
    if _texte != attendu:
        ecarts_d.append(f"{_c} : page « {_texte} » vs dictionnaire « {attendu} »")
for _c, _attribut, _valeur in _md.attributs:
    attendu = (TR.TEXTES.get(_c) or {}).get("fr")
    if _valeur != attendu:
        ecarts_d.append(f"{_c} [{_attribut}] : page « {_valeur} » vs "
                        f"dictionnaire « {attendu} »")
dit(len(_md.textes) + len(_md.attributs) > 0 and not ecarts_d,
    "chaque texte francais de l'ecran est EXACTEMENT celui du dictionnaire",
    " / ".join(ecarts_d[:2])
    or f"{len(_md.textes)} textes, {len(_md.attributs)} attributs")

dit(bool(_md.attributs) and not _md.nus,
    "et chaque titre, invite et aria-label de l'ecran passe par une cle",
    ", ".join(_md.nus[:3]) or f"{len(_md.attributs)} attributs")

# LES TITRES DES LIGNES SONT COMPOSES — « demarrage.<nom> », serveur._ligne —
# et on les releve dans les SITES D'APPEL, par l'arbre de syntaxe. Un motif de
# texte decrirait une facon d'ecrire l'appel, jamais l'appel : la meme lecon que
# les quatre trous de ce banc et que banc_traductions.py.
_arbre_srv = ast.parse(SERVEUR)
_appels_ligne = [n for n in ast.walk(_arbre_srv)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                 and n.func.id == "_ligne"]
_noms_lignes = {a.args[0].value for a in _appels_ligne
                if a.args and isinstance(a.args[0], ast.Constant)}
_titres_dem = {"demarrage." + n for n in _noms_lignes}

# COTE SERVEUR, ON NE LIT QUE CE QUI ENTRE DANS _marque() — et non toute chaine
# du fichier qui ressemble a une cle. « web/demarrage.html », le chemin que sert
# page_demarrage(), passait sinon pour une entree de dictionnaire manquante :
# le releve rougissait sur un nom de fichier. La meme lecon que le CSS plus
# haut, ou ce banc s'etait signale lui-meme en lisant une classe dans un
# commentaire — on releve ce qui AGIT, pas ce qui s'ecrit.
_marques_srv = [n for n in ast.walk(_arbre_srv)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "_marque"]
_cites_srv = {c.value for a in _marques_srv for c in ast.walk(a)
              if isinstance(c, ast.Constant) and isinstance(c.value, str)
              and re.fullmatch(r"demarrage\.[a-z0-9_.]+", c.value)}

_cites_dem = set(re.findall(r'["\'](demarrage\.[a-z0-9_.]*)["\']', DEMARRAGE))
_prefixes_dem = {c for c in _cites_dem if c.endswith(".")}
_cites_dem = (_cites_dem - _prefixes_dem) | _cites_srv

# « demarrage. » TOUT COURT NE DOIT PAS EXISTER DANS LA PAGE, et c'est un
# garde-fou sur le releve lui-meme : un tel litteral serait lu comme un
# prefixe, couvrirait la famille entiere, et rendrait muette la verification de
# dormance juste en dessous — verte parce que plus rien ne peut y dormir. C'est
# la faute que ce depot a corrigee treize fois d'un coup ailleurs : une
# assertion vraie parce qu'elle ne mesure plus rien.
dit("demarrage." not in _prefixes_dem,
    "aucun releve ne cite « demarrage. » nu, qui couvrirait toute la famille",
    ", ".join(sorted(_prefixes_dem)) or "aucun prefixe nu")


def couvre_dem(c):
    return (c in _cites_dem or c in _titres_dem
            or any(c.startswith(p) for p in _prefixes_dem))


inventees_d = sorted(c for c in (_cites_dem | _titres_dem) if c not in TR.TEXTES)
dit(len(_noms_lignes) > 0 and _cites_dem and not inventees_d,
    "toute cle « demarrage. » citee par l'ecran ou par le serveur existe",
    ", ".join(inventees_d[:3]) or
    f"{len(_cites_dem)} citees, {len(_noms_lignes)} titres de lignes composes")

dormantes_d = sorted(c for c in TR.TEXTES
                     if c.startswith("demarrage.") and not couvre_dem(c))
dit(not dormantes_d, "et aucune cle « demarrage. » ne dort au dictionnaire",
    ", ".join(dormantes_d[:3]) or
    f"{sum(1 for c in TR.TEXTES if c.startswith('demarrage.'))} cles")

# ── LES QUATRE VERDICTS, DES DEUX COTES ──────────────────────────────
# serveur.VERDICTS les nomme, la page les peint. Un verdict connu du serveur et
# inconnu de la page donne une ligne sans couleur et sans etiquette — donc une
# ligne qu'on lit « tout va bien », ce qui est exactement l'inverse du service
# rendu par cet ecran.
_v_srv = re.search(r'^VERDICTS = \(([^)]*)\)', SERVEUR, re.M)
_v_page = re.search(r'const VERDICTS = \{(.*?)\};', DEMARRAGE, re.S)
_verdicts_srv = set(re.findall(r'"([a-z]+)"', _v_srv.group(1))) if _v_srv else set()
_verdicts_page = set(re.findall(r'([a-z]+)\s*:', _v_page.group(1))) if _v_page else set()
dit(len(_verdicts_srv) >= 3 and _verdicts_srv == _verdicts_page,
    "la page peint exactement les verdicts que le serveur nomme",
    f"{sorted(_verdicts_srv)} contre {sorted(_verdicts_page)}")

# ET CHAQUE VERDICT REELLEMENT POSE EST DANS LA TABLE. La table peut etre juste
# des deux cotes pendant qu'un site d'appel en ecrit un cinquieme a la main :
# le second argument de _ligne() est donc relu, ternaires compris.
_poses = set()
for _a in _appels_ligne:
    if len(_a.args) >= 2:
        _poses |= {c.value for c in ast.walk(_a.args[1])
                   if isinstance(c, ast.Constant) and isinstance(c.value, str)}
dit(_poses and _poses <= _verdicts_srv,
    "et chaque verdict pose par une ligne figure dans cette table",
    f"{sorted(_poses - _verdicts_srv)} hors table" if _poses - _verdicts_srv
    else f"{len(_poses)} verdicts poses sur {len(_appels_ligne)} lignes")

# ── L'ECRAN MESURE, IL NE REGLE PAS ──────────────────────────────────
# C'EST LA REGLE QUI LE FAIT TENIR A COTE DE /admin. Six onglets y posent deja
# les machines, les jetons d'agent, les cles d'API, le choix local/distant par
# modalite, les comptes, le plafond du nuage et le reentrainement de
# l'aiguilleur. Un ecran d'accueil qui redemanderait l'un d'eux serait une
# SECONDE table du meme reglage — et ce depot a mesure trois fois que deux
# tables du meme reglage divergent. Il ne pose donc que ce que personne d'autre
# ne pose (la langue) et ce qui n'appartient qu'a lui (se refermer), et il
# emprunte la porte d'administration au lieu d'en ouvrir une seconde.
_APPELS_PERMIS = {"/api/textes", "/api/demarrage", "/api/admin/entrer"}
_appels_dem = set(re.findall(r'fetch\("([^"]+)"', DEMARRAGE))
dit(_appels_dem == _APPELS_PERMIS,
    "l'ecran n'appelle que la langue, sa propre mesure et la porte d'admin",
    ", ".join(sorted(_appels_dem - _APPELS_PERMIS)) or
    ", ".join(sorted(_appels_dem)))

# ── ET SA MESURE EST GARDEE ──────────────────────────────────────────
# Cette reponse dit qu'un compte porte encore son mot de passe d'origine,
# qu'aucune carte ne repond et que STUDIO_AUTH vaut « libre ». Servie sans
# garde, elle serait la meilleure page de reconnaissance qu'un studio puisse
# offrir — et elle est ATTEIGNABLE SANS SESSION, puisque exiger_compte la laisse
# passer pour que l'amorçage d'une installation neuve reste possible. Les deux
# moities se relevent donc ensemble : la porte ouverte, et le verrou derriere.
_corps_api_dem = (SERVEUR.split("async def api_demarrage(req):", 1)[-1]
                  .split("\ndef ", 1)[0].split("\nasync def ", 1)[0])
dit("admin_ok(req)" in _corps_api_dem
    and 'chemin == "/api/demarrage"' in SERVEUR,
    "la mesure est libre de session mais gardee par le jeton d'administration",
    "admin_ok present" if "admin_ok(req)" in _corps_api_dem
    else "AUCUNE garde dans api_demarrage")


# ══ LA REGLE DU PLURIEL EST CELLE DE LA LANGUE ═════════════════════════
# La page ecrivait « ${n} échange${n > 1 ? "s" : ""} » a chaque endroit qui
# compte quelque chose : la regle FRANCAISE, recopiee a la main, dans du code
# d'interface. Elle est fausse en anglais des zero — le francais ecrit
# « 0 echange », l'anglais « 0 exchanges » — et la recopier vingt fois
# garantit qu'une des vingt sera oubliee.
#
# La page a sa PROPRE copie de la table, et il le faut : elle compte des
# choses que le serveur ne voit jamais. Ce banc-ci exige donc que cette copie
# soit la meme regle, ecrite ici avec sa raison — comme banc_traductions.py
# l'exige de la table Python.
print("\n  ── la page compte comme la langue, pas comme le francais ──")
_bloc_pl = CORPS.split("const PLURIELS = {", 1)
_regles = dict(re.findall(r'([a-z]{2})\s*:\s*n\s*=>\s*([^,\n]+)',
                          _bloc_pl[1].split("};", 1)[0])) if len(_bloc_pl) == 2 else {}
dit(set(_regles) == set(TR.LANGUES),
    "la page porte une regle de pluriel par langue servie",
    f"{sorted(_regles)} pour {sorted(TR.LANGUES)}")
# LES DEUX REGLES DIFFERENT. Recopier la ligne francaise dans la colonne
# anglaise est la faute exacte que cette table existe pour empecher, et elle
# passerait le cas ci-dessus sans bruit. On nomme donc ce qui les separe :
# le francais met 0 ET 1 au singulier (« n > 1 »), l'anglais 1 seul
# (« n !== 1 »).
dit(bool(_regles) and ">" in _regles.get("fr", "")
    and "!==" in _regles.get("en", ""),
    "et le francais met zero au singulier la ou l'anglais le met au pluriel",
    f"fr : {_regles.get('fr', '—').strip()} / en : {_regles.get('en', '—').strip()}")
# ET PLUS AUCUN « s » RECOLLE A LA MAIN. Le sol est pris par le haut : ce
# n'est pas une liste des endroits ou la regle etait recopiee — les enumerer
# est la faute que ce banc a deja faite cinq fois (voir LECTURES_DU_MENU) —
# mais la FORME meme du contournement.
#
# DEUX SOLS SUCCESSIFS ONT RATE, ET ILS SONT ECRITS ICI. « \(s\) » tout court
# attrapait « catch (e) » ; y coller une lettre devant attrapait
# « querySelector(s) » et « appendChild(s) » — du JavaScript parfaitement
# ordinaire, sur lequel le depot sain rougissait. Ce qui separe le
# contournement de l'appel, c'est ce qui SUIT la parenthese : « demande(s)
# attendent » continue une phrase, « appendChild(s); » ferme une instruction.
# Le jour ou un appel legitime s'ecrira « f(s) + 1 », ce cas rougira et
# demandera qu'on l'inscrive ici — c'est le bon sens de l'erreur.
recolles = re.findall(r'\?\s*"s"\s*:|[A-Za-zÀ-ÿ]\((?:e?s|e)\)(?![);.,\]}])', CODE)
compte_n = len(re.findall(r'\bT\(\s*["\'][a-z0-9_.]+["\']\s*,\s*\{[^}]*\bn\s*:', CODE))
dit(compte_n > 0 and not recolles,
    "et rien ne recolle plus un « s » ni n'ecrit « demande(s) »",
    ", ".join(recolles[:3]) or f"{compte_n} appels qui comptent")


# ══ LES VALEURS DE PROTOCOLE NE SONT PLUS DES LIBELLES ═════════════════
# Le quatrieme des quatre chantiers de docs/plusieurs-langues.md, et le seul
# qui restait : « t.etat » vaut « en cours », « fini », « erreur » — teste a
# cinq endroits ET servant de CLES a la table des etiquettes, dont les VALEURS
# sont de l'IHM. Une passe de traduction naive touchait les deux moities du
# meme litteral, et « t.etat === "fini" » devenait muet sans lever la moindre
# erreur.
#
# ON NE CHANGE PAS LE PROTOCOLE, ON LE SEPARE : ces valeurs voyagent jusqu'au
# serveur et sont ECRITES dans les conversations deja enregistrees. Les six
# sont donc nommees ICI, dans le banc, avec ce qu'elles sont — le jour ou la
# page en traduira une, ce cas rougira au lieu de laisser tout l'historique se
# relire de travers.
print("\n  ── le protocole n'est plus un libelle ──")
ETATS_DU_SERVEUR = {"en cours", "fini", "erreur", "question",
                    "attente carte", "attente machine"}
_bloc_etat = CORPS.split("const ETAT = {", 1)
_valeurs_etat = set(re.findall(r':\s*"([^"]+)"',
                               _bloc_etat[1].split("};", 1)[0])) \
    if len(_bloc_etat) == 2 else set()
dit(_valeurs_etat == ETATS_DU_SERVEUR,
    "la page declare les six etats que le serveur ECRIT, et pas d'autres",
    f"{sorted(_valeurs_etat)}")

# ET PLUS AUCUNE COMPARAISON NE PORTE LE LITTERAL. Ce qui fait le degat n'est
# pas l'endroit ou l'etat est ecrit, c'est qu'il soit ecrit DEUX fois : une
# comparaison restee en clair survit a la table, et se tait le jour ou la
# table bouge.
literaux = re.findall(r'\.(etat|famille)\s*(?:===|!==|==|!=)\s*["\']([^"\']*)["\']',
                      CODE)
literaux += [("etat", v) for v in
             re.findall(r'\betat\s*:\s*["\']([^"\']*)["\']', CODE)]
usages = len(re.findall(r'\b(?:ETAT|FAMILLE)\.[a-z0-9_]+', CODE))
dit(usages > 0 and not literaux,
    "et aucune comparaison d'etat ni de famille ne porte encore un litteral",
    ", ".join(f".{q} === « {v} »" for q, v in literaux[:3])
    or f"{usages} lectures nommees")

# LA VALEUR DE L'<option> EST CELLE QUE LE SCRIPT RELIT. « brouillons » est
# ecrit dans le HTML et compare dans le JS a deux cents lignes d'ecart : c'est
# exactement la forme du defaut du 31 aout (MENU_REGLAGE / CLE_REGLAGE), et la
# traduction du libelle passait a un caractere de toucher la valeur.
_soins = re.findall(r'const\s+SOIN_BROUILLONS\s*=\s*"([^"]*)"\s*;', CORPS)
_options_soin = re.findall(r'<option value="([^"]*)"', PAGE.split(
    '<select id="soinMedia"', 1)[1].split("</select>", 1)[0])
dit(len(_soins) == 1 and _soins[0] and _soins[0] in _options_soin,
    "le filtre « brouillons » compare la valeur que le HTML porte vraiment",
    f"{_soins} contre {_options_soin}")


# ══ CE QUE L'UTILISATEUR LIT QUAND UN RENDU ECHOUE ═════════════════════
# La bulle affichait la DERNIERE LIGNE DE JOURNAL — « t.erreur = derniere.msg »
# —, c'est-a-dire que le message le plus lu de tout le studio n'etait pas un
# message d'API mais du journal. Et le journal ne se traduit pas : il est
# ECRIT, garde sur la tache, relu plus tard par quelqu'un d'autre.
#
# Le serveur pose donc a cote une MARQUE, { cle, valeurs }, que la page met en
# phrase. Meme patron que MARQUE_DEJA : la page NOMME le champ, et zero
# declaration compte comme un NON — plusieurs aussi, on ne saurait plus
# laquelle elle applique.
print("\n  ── la panne se lit sur la marque, et le journal reste le repli ──")
pannes = re.findall(r'const\s+MARQUE_PANNE\s*=\s*"([^"]*)"\s*;', CORPS)
dit(len(pannes) == 1 and bool(pannes[0]),
    "la page NOMME le champ par lequel le serveur dit CE QUI a echoue",
    f"{len(pannes)} declaration(s) de MARQUE_PANNE : ce banc NE MESURE PLUS le "
    "couplage page/serveur" if len(pannes) != 1 else pannes[0])

# LA MARQUE EST LUE, ET LE REPLI EST OBLIGATOIRE. Une tache relue apres
# redemarrage n'a pas de marque, et trois arguments de echouer() sur cinq n'en
# avaient pas le 2 septembre : une page qui n'aurait su lire que la marque
# aurait affiche du VIDE la ou il y avait une phrase. On exige donc les deux
# dans la MEME expression — separes, l'un des deux pourrait disparaitre sans
# que l'autre s'en apercoive.
#
# LA DEFINITION N'EST PAS UN APPEL. « function rendrePanne(marque) » entre
# sinon dans le releve, et son corps contient un « ; » bien avant la fin : le
# cas rougissait sur le depot sain. On ecarte donc la declaration, et l'on
# lit chaque APPEL jusqu'a son point-virgule.
_sites = [m.start() for m in re.finditer(r'\brendrePanne\(', CODE)
          if not CODE[:m.start()].rstrip().endswith("function")]
_chaines = [CODE[i:CODE.find(";", i) + 1] for i in _sites]
_lectures = [re.findall(r'rendrePanne\(([^)]*)\)', c + ")")[0] for c in _chaines]
# LES DEUX SITES, et non un seul : la bulle du premier passage ET la relecture
# differee huit secondes plus tard. Celle-la comparait la derniere ligne de
# journal a « t.erreur » — qui porte desormais la panne MISE EN PHRASE : sans
# la meme lecture des deux cotes, elle repeignait du francais par-dessus
# l'anglais a chaque arret de carte.
dit(len(_sites) >= 2 and all("MARQUE_PANNE" in a for a in _lectures)
    and all(".msg" in c for c in _chaines),
    "elle rend la marque en phrase, et retombe sur la ligne de journal",
    f"{len(_sites)} appels : {' / '.join(_lectures[:2])}"
    if _sites else "rendrePanne n'est appele nulle part")

# UNE VALEUR PEUT ETRE UNE MARQUE, sur un seul niveau : c'est le gabarit
# « ERREUR : {quoi} » de echouer(), dont le {quoi} est une phrase du
# dictionnaire et non une valeur calculee. Sans ce tour, l'anglophone lisait
# « ERROR: la machine n'est pas revenue a temps » — une demi-phrase traduite,
# qui se remarque moins qu'une phrase entierement francaise et trompe donc
# plus longtemps. traductions.rendre() est la specification ; on verifie ici
# que la page l'a bien suivie jusque-la.
_corps_rendre = CODE.split("function rendrePanne(", 1)
_corps_rendre = _corps_rendre[1].split("\n}", 1)[0] if len(_corps_rendre) == 2 else ""
dit(bool(_corps_rendre) and "v.cle" in _corps_rendre
    and "valeurs" in _corps_rendre,
    "et une valeur qui est elle-meme une marque est rendue d'abord",
    "rendrePanne introuvable" if not _corps_rendre else "un seul niveau")


# ══ LE MENU DE LANGUE ══════════════════════════════════════════════════
# Il n'est PAS un reglage de conversation, et c'est mesure ailleurs :
# REGLAGES_CONV est par conversation alors que l'en-tete, la mediatheque et le
# panneau de file ne le sont pas — la langue de l'ombrelle serait celle de la
# derniere conversation ouverte. Le choix vit dans le cookie, pose par POST
# /api/textes, et le menu doit rester hors des trois tables de reglages : y
# entrer le ferait poster sur une route qui ne le lit pas.
print("\n  ── le menu de langue ──")
dit('<select id="langue"' in PAGE and '/api/textes' in CORPS,
    "la page offre le choix de la langue, et le poste au serveur")
dit("langue" not in menu and "#langue" not in cle
    and not any(s == "#langue" for s, _r in entrees),
    "et il reste hors des reglages : le serveur ne le retient pas la",
    f"{sorted(menu)} / {sorted(cle)}")

# ET IL EST DANS L'EN-TETE, PAS SOUS LE BOUTON « REGLAGES ». Il y a vecu une
# heure, dans le pied de page, et deux choses le rendaient inutilisable la :
# ce panneau ne s'ouvre que pour changer de moteur ou de taille — donc la
# langue etait cachee derriere un geste sans rapport — et il ne s'ouvre PAS DU
# TOUT tant qu'on n'est pas connecte, alors que l'ecran de connexion est
# justement la premiere chose qu'un lecteur etranger doit pouvoir traduire.
#
# On releve la POSITION et non la presence : « <select id="langue"> existe »
# resterait vrai partout dans la page, y compris a l'endroit d'ou on vient de
# le sortir.
_avant_entete, _, _apres = PAGE.partition("</header>")
dit('id="langue"' in _avant_entete and "<header" in _avant_entete,
    "et il est dans l'EN-TETE, visible sans ouvrir quoi que ce soit",
    "dans l'en-tete" if 'id="langue"' in _avant_entete
    else "il est retombe plus bas dans la page")
# Le globe est son etiquette, et « for » est ce qui les relie : sans lui, le
# clic sur l'icone n'ouvre rien et un lecteur d'ecran annonce un caractere
# decoratif au lieu du menu. C'est un mot dans le HTML, et il se perd en
# reindentant.
dit('for="langue"' in _avant_entete,
    "et le globe lui est attache par « for » : cliquer l'icone ouvre le menu")

# ══ CE QUE LE NAVIGATEUR A LE DROIT DE GARDER ══════════════════════════
# LES CONTRATS ENTRE LA PAGE ET LE SERVEUR NE SURVIVENT PAS A UNE PAGE PERIMEE.
# Ce banc en mesure cinq — MARQUE_DEJA, MARQUE_DEVIS, MARQUE_PANNE, MARQUE_MFA,
# MARQUE_ARRET_DIFFERE — plus le dictionnaire de /api/textes, et il les mesure
# tous DANS LE DEPOT, ou les deux moities sont forcement du meme jour. A
# l'execution, elles ne le sont pas : sans « Cache-Control », un navigateur
# s'autorise a reutiliser une reponse pendant environ un dixieme de son age,
# soit une JOURNEE pour un fichier vieux de dix jours. Une page d'hier contre un
# serveur d'aujourd'hui, c'est la divergence silencieuse que tout ce banc existe
# pour empecher, reintroduite la ou il ne regarde pas.
#
# Constate le 3 septembre 2026 : apres un deploiement, le navigateur servait
# encore la page d'avant, sans son menu de langue.
#
# ON LIT L'ARBRE ET NON UN MOTIF : une FileResponse s'ecrit sur une ou trois
# lignes, avec ou sans os.path.join, et « une expression reguliere decrit UNE
# facon d'ecrire la panne, jamais la panne ».
print("\n  ── la page ne se sert pas de memoire ──")
_pages_html, _sans_entete = 0, []
for _n in ast.walk(ast.parse(SERVEUR)):
    if not (isinstance(_n, ast.Call)
            and isinstance(_n.func, ast.Attribute)
            and _n.func.attr == "FileResponse"):
        continue
    _arg = ast.unparse(_n.args[0]) if _n.args else ""
    if ".html" not in _arg:
        continue
    _pages_html += 1
    if not any(k.arg == "headers" for k in _n.keywords):
        _sans_entete.append(_arg)
# LE COMPTE D'ABORD : zero page servie rendrait « aucune n'oublie l'en-tete »
# vrai de rien, et c'est l'etat qu'on obtient le jour ou quelqu'un renomme
# FileResponse ou sert les pages autrement.
dit(_pages_html >= 3,
    "le studio sert bien ses pages en fichier",
    f"{_pages_html} pages html")
dit(not _sans_entete,
    "et chacune dit au navigateur de REDEMANDER avant de servir",
    ", ".join(_sans_entete) + " — sans en-tete" if _sans_entete
    else "toutes portent leurs en-tetes")
dit("no-cache" in SERVEUR,
    "et cet en-tete est bien « no-cache » : garder, mais revalider",
    "l'ETag rend alors un 304 sans corps")

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
for r in rate:
    print("    a regarder :", r)
sys.exit(1 if rate else 0)
