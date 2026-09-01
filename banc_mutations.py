# -*- coding: utf-8 -*-
"""Les bancs rougissent-ils encore sur les pannes qu'ils disent attraper ?

    python banc_mutations.py

Trois fois cette semaine, un banc vert a couvert une fonctionnalite morte. La
derniere est la pire : banc_page.py, ecrit expres pour empecher un defaut de
revenir, ne voyait pas ce defaut. Il cherchait « priorite: $("#priorite").value »
alors que le vrai code portait l'abreviation ES6, « priorite, ». La ligne fautive
restauree, le banc est reste vert.

Un banc ne se relit pas, il s'eprouve. Le seul geste qui l'a montre, c'est de
MUTER le code et d'exiger que le banc rougisse. Il a ete fait trois fois a la
main, dans des scripts jetables, et jete a chaque fois. Il est ici.

Chaque mutation copie dans un dossier temporaire ce dont le banc vise a besoin,
y applique la mutation, lance CE banc-la — pas les autres — et exige une ligne
rouge NOMMEE. Le depot n'est jamais touche.

Dix bancs y sont depuis le 1er septembre ; ils etaient quatre. Les six qui
manquaient portaient 355 verifications a eux tous, et pas une n'avait jamais
ete vue rougir : la regle de CONTRIBUTING.md, « si tu ajoutes un banc,
ajoute-lui sa mutation », avait ete ecrite et pas tenue.

Il reste verifier_formulations.py, et c'est le dernier : il nomme ses fautes
par le NUMERO DE LIGNE de banc_formulations.jsonl, si bien qu'une ancre posee
dessus se perimerait au premier cas insere au milieu du fichier. L'ancrer sur
la formulation elle-meme est possible ; ce n'est simplement pas fait.

Trois facons d'echouer, et la premiere est la plus precieuse :

  - une mutation qui passe au VERT : le filet a un trou, exactement celui qui a
    laisse passer « priorite, ».
  - une mutation dont l'ANCRE n'existe plus : elle ne mesure plus rien, et
    personne ne s'en apercevrait. C'est un echec, pas un succes silencieux —
    d'ou l'ancrage sur un motif de texte et jamais sur un numero de ligne
    (serveur.py change plusieurs fois par jour).
  - le depot SAIN qui rougit : un banc qui rougit sur tout n'attrape rien non
    plus, et le sens inverse se verifie donc aussi.

Exiger la LIGNE attendue et pas seulement un code de retour non nul n'est pas
un raffinement : une mutation qui casse le banc par une exception rend elle
aussi un code non nul, et se ferait passer pour une reussite.

TROUS_CONNUS rassemble les mutations que la relecture adverse a trouvees et que
le banc vise laisse ENCORE passer. Elles sont ecrites, nommees et signalees,
mais ne font pas echouer : les compter en echec rendrait la CI rouge en
permanence, et une CI qui rougit pour rien finit ignoree. Les basculer dans
MUTATIONS est le geste qui clot la reparation du filet.

Ils etaient cinq ; les quatre qui visaient banc_page.py sont fermes et ont
rejoint PAGE. Ils disaient tous la meme chose : un releve par expression
reguliere decrit UNE facon d'ecrire la panne, jamais la panne. Fermer le
premier a d'ailleurs revele qu'il n'imitait pas encore le vrai defaut — la
mutation posait un « const », la page de 21c443c^ recevait le cran en argument
d'appel — et la mutation qui manquait est desormais dans PAGE elle aussi. C'est
le meme service que ce fichier rend aux bancs : une mutation aussi s'eprouve.
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

ICI = os.path.dirname(os.path.abspath(__file__))
ok, rate, signales = [], [], []


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


def lire(rel):
    # newline=None : un depot clone sous Windows rend des CRLF, et les ancres
    # ci-dessous sont ecrites en "\n". Sans cette normalisation, TOUTES les
    # mutations seraient declarees perimees sur une machine et sur une seule.
    with io.open(os.path.join(ICI, *rel.split("/")), encoding="utf-8",
                 newline=None) as f:
        return f.read()


# ── Ce qu'il faut copier, et rien de plus ─────────────────────────────
# Mesure : le depot entier fait 138 fichiers et 0,12 s de copie, les neuf
# fichiers dont banc_conteneur.py a besoin en font 0,007 s. Sur les vingt-deux
# mutations, deux secondes de CI contre un huitieme de seconde.
def fichiers_du_conteneur():
    """La meme piste que celle que banc_conteneur.py suit lui-meme.

    Il ne releve pas le repertoire mais les IMPORTS de serveur.py — agent_noeud
    est dans l'image et ne tourne pas dans ce conteneur. Copier une liste ecrite
    a la main ici la ferait deriver de la sienne : le jour ou serveur.py
    importerait un module de plus, la mutation posee dedans tomberait dans un
    dossier ou le module n'est pas, et le banc rougirait sur un import manquant
    au lieu de la variable oubliee.

    « ^\\s* » comme lui, donc : les mutations qui deplacent un import en cours
    de fonction copieraient sinon un jeu de fichiers different du sien.
    """
    fichiers = ["banc_conteneur.py", "serveur.py",
                "docker-compose.yml", "Dockerfile", ".env.exemple"]
    for mod in re.findall(r'(?m)^\s*(?:import|from)\s+([a-z_][a-z0-9_]*)',
                          lire("serveur.py")):
        nom = mod + ".py"
        if nom not in fichiers and os.path.exists(os.path.join(ICI, nom)):
            fichiers.append(nom)
    return fichiers


BESOINS = {
    "banc_conteneur.py": fichiers_du_conteneur(),
    "banc_page.py": ["banc_page.py", "web/index.html"],
    # Le banc importe serveur.py, donc tout ce que serveur.py importe.
    "banc_repartition.py": ["banc_repartition.py"] + fichiers_du_conteneur()[1:],
    "banc_cerveaux.py": ["banc_cerveaux.py"] + fichiers_du_conteneur()[1:],
    # banc_variantes.py relit web/index.html pour UNE chose : RE_DEVIS, le
    # releve par lequel la page tire un chiffre de la phrase du journal. Sans
    # cette page, le banc annonce lui-meme que l'ecart « N'EST PLUS MESURE » —
    # et la mutation du seuil du devis rougirait pour la mauvaise raison.
    "banc_variantes.py": (["banc_variantes.py", "web/index.html"]
                          + fichiers_du_conteneur()[1:]),
    # banc_cout.py et banc_attente.py importent serveur.py comme les autres.
    # aiohttp leur est en plus indispensable : fournisseurs.py l'importe en
    # tete de fichier, et sans lui le banc meurt a l'import — un plantage qui
    # ressemblerait a une mutation attrapee.
    "banc_cout.py": ["banc_cout.py"] + fichiers_du_conteneur()[1:],
    "banc_attente.py": ["banc_attente.py"] + fichiers_du_conteneur()[1:],
    "banc_durees.py": ["banc_durees.py"] + fichiers_du_conteneur()[1:],
    # Celui-la n'importe pas le studio : il preleve deux expressions
    # regulieres dans le TEXTE de serveur.py. Il lui faut donc serveur.py, et
    # rien d'autre — pas meme les modules qu'il importe.
    "banc_adulte.py": ["banc_adulte.py", "serveur.py"],
    # catalogue.py pour les tailles, installation.py et serveur.py parce que
    # le banc y cherche les poids encore mis en phrase a la main. Sans
    # serveur.py, son aveu d'ATTENDU_AILLEURS se declarerait perime.
    "banc_catalogue.py": ["banc_catalogue.py", "catalogue.py",
                          "installation.py", "serveur.py"],
}


# ── Ou se lit la ligne rouge ──────────────────────────────────────────
# Huit bancs sur dix impriment « NON » ; banc_cout.py imprime « RATE » et
# banc_adulte.py n'a pas de dit() du tout — il liste ses fautes indentees sous
# leur compte. Sans cette table, TOUTE mutation qui les vise serait rendue
# « le banc s'est casse au lieu de rougir » alors qu'il l'a parfaitement
# attrapee : le faux positif que ce fichier existe pour interdire, retourne.
#
# L'exigence, elle, ne bouge pas — la ligne NOMMEE et pas un code de retour.
MARQUE_ROUGE = {"banc_cout.py": "  RATE ", "banc_adulte.py": "    "}


# ── Les deux formes d'ancre ───────────────────────────────────────────
# « brut » pour un morceau de ligne recopie tel quel, qui est le cas courant et
# se relit sans decoder d'echappement. « motif » pour ce qui s'etale sur des
# lignes dont on ne veut pas recopier le contenu — le bandeau de commentaire
# entre deux services, par exemple.
def brut(cherche, pose):
    return ("brut", cherche, pose)


def motif(cherche, pose):
    return ("motif", cherche, pose)


def appliquer(texte, edition):
    """Rend (texte mute, "") ou (None, raison). UNE occurrence, jamais zero.

    Zero occurrence est le cas qui compte : l'ancre a bouge, la mutation
    n'imite plus rien, et sans ce refus elle passerait pour appliquee. Plusieurs
    occurrences valent refus aussi : on ne sait plus laquelle on mute.
    """
    genre, cherche, pose = edition
    if genre == "brut":
        trouve = texte.count(cherche)
        neuf = texte.replace(cherche, pose)
    else:
        # lambda et non la chaine : un « \1 » ou un « \g » dans le remplacement
        # serait interprete, et une mutation se transformerait en silence.
        neuf, trouve = re.subn(cherche, lambda m: pose, texte, flags=re.M | re.S)
    if trouve != 1:
        return None, f"{trouve} occurrence(s) pour « {cherche.splitlines()[0][:60]} »"
    return neuf, ""


# ──────────────────────────────────────────────────────────────────────
#  banc_conteneur.py — dix-sept mutations, toutes verifiees rouges
# ──────────────────────────────────────────────────────────────────────
# Elles viennent de l'en-tete de banc_conteneur.py et des commits 537a205 et
# 77fb1ef, ou elles ont ete jouees a la main. Chacune dit la PANNE qu'elle
# imite, pas la manipulation : « OLLAMA_URL disparait du compose » se relit dans
# les deux lignes en dessous, « le studio ne trouve plus aucun Ollama » non.
CONTENEUR = [
    dict(
        nom="OLLAMA_URL retiree du compose et du Dockerfile",
        banc="banc_conteneur.py",
        imite="le studio en conteneur ne trouve plus aucun Ollama, et rien ne "
              "le dit : c'est la variable la plus importante du montage",
        rougit="tout ce qui est lu arrive au conteneur par le compose",
        editions=[
            ("docker-compose.yml", brut(
                '      OLLAMA_URL: "${OLLAMA_URL:-http://host.docker.internal:11434}"\n',
                "")),
            ("Dockerfile", brut("    OLLAMA_URL=http://ollama:11434 \\\n", "")),
        ]),
    dict(
        nom="un reglage deplace du compose vers le Dockerfile",
        banc="banc_conteneur.py",
        imite="la variable arrive bien au conteneur — avec la valeur de "
              "l'IMAGE, figee : ce qu'on pose dans .env reste lettre morte",
        rougit="tout ce qui est lu arrive au conteneur par le compose",
        editions=[
            ("docker-compose.yml", brut(
                '      STUDIO_TRAVAILLEURS: "${STUDIO_TRAVAILLEURS:-}"\n', "")),
            ("Dockerfile", brut("ENV COMFY_DIR=/comfy\n",
                                "ENV COMFY_DIR=/comfy\nENV STUDIO_TRAVAILLEURS=3\n")),
        ]),
    dict(
        nom="faute de frappe dans le nom substitue",
        banc="banc_conteneur.py",
        imite="la clef est relayee et sa valeur est vide POUR TOUJOURS : le "
              "reglage semble present et n'a jamais aucun effet",
        rougit="chaque ligne renvoie a SA variable",
        editions=[
            ("docker-compose.yml", brut(
                '      STUDIO_ANALYSE_MAX: "${STUDIO_ANALYSE_MAX:-}"',
                '      STUDIO_ANALYSE_MAX: "${STUDIO_ANALYSE_MAXX:-}"')),
        ]),
    dict(
        nom="faute de frappe sur une variable derivee",
        banc="banc_conteneur.py",
        imite="la banniere de demarrage annonce un port ou le studio ne repond "
              "pas, et sur une machine qui en heberge deux, cette adresse "
              "repond : c'est le studio d'a cote",
        rougit="chaque ligne renvoie a SA variable",
        editions=[
            ("docker-compose.yml", brut(
                '      STUDIO_PORT_HOTE: "${STUDIO_PORT:-8199}"',
                '      STUDIO_PORT_HOTE: "${STUDIO_PORTT:-8199}"')),
        ]),
    dict(
        nom="valeur figee non quotee dans le compose",
        banc="banc_conteneur.py",
        imite="le reglage est fige dans le YAML sans raison ecrite : .env ne "
              "peut plus rien pour lui, et personne ne sait pourquoi",
        rougit="aucune valeur figee sans raison ecrite",
        editions=[
            ("docker-compose.yml", brut(
                '      STUDIO_TRAVAILLEURS: "${STUDIO_TRAVAILLEURS:-}"',
                "      STUDIO_TRAVAILLEURS: 3")),
        ]),
    dict(
        nom="un reglage neuf lu par os.getenv",
        banc="banc_conteneur.py",
        imite="le scenario d'origine, rejoue sous le nez du filet ecrit pour "
              "lui : un reglage neuf lu hors conteneur, ignore dedans",
        rougit="tout ce qui est lu arrive au conteneur par le compose",
        editions=[
            ("serveur.py", brut(
                'TRAVAILLEURS = max(1, int(os.environ.get("STUDIO_TRAVAILLEURS") or 3))',
                'TRAVAILLEURS = max(1, int(os.environ.get("STUDIO_TRAVAILLEURS") or 3))\n'
                'REGLAGE_NEUF = os.getenv("STUDIO_NEUF", "")')),
        ]),
    dict(
        nom="le meme reglage neuf en apostrophes simples",
        banc="banc_conteneur.py",
        imite="la meme panne, ecrite dans l'autre sorte de guillemets — celle "
              "que le releve ne regardait pas",
        rougit="tout ce qui est lu arrive au conteneur par le compose",
        editions=[
            ("serveur.py", brut(
                'TRAVAILLEURS = max(1, int(os.environ.get("STUDIO_TRAVAILLEURS") or 3))',
                'TRAVAILLEURS = max(1, int(os.environ.get("STUDIO_TRAVAILLEURS") or 3))\n'
                "REGLAGE_NEUF = os.getenv('STUDIO_NEUF', '')")),
        ]),
    dict(
        nom="un reglage lu dans un module importe",
        banc="banc_conteneur.py",
        imite="la meme panne posee ailleurs que dans serveur.py : le module "
              "tourne dans le conteneur, sa variable n'y arrive pas",
        rougit="tout ce qui est lu arrive au conteneur par le compose",
        editions=[
            ("comptes.py", brut(
                "import secrets\nimport time\n",
                "import secrets\nimport time\n\n"
                'REGLAGE_NEUF = os.environ.get("STUDIO_NEUF", "")\n')),
        ]),
    dict(
        nom="les bandeaux retires, un reglage pose sur le conteneur voisin",
        banc="banc_conteneur.py",
        imite="COMFY_LANCEUR se retrouve dans la MAUVAISE machine apres un "
              "nettoyage anodin des commentaires : le studio ne le lit plus",
        rougit="tout ce qui est lu arrive au conteneur par le compose",
        editions=[
            ("docker-compose.yml", brut(
                '      COMFY_LANCEUR: "${COMFY_LANCEUR:-}"\n', "")),
            ("docker-compose.yml", brut(
                '      COMFY_ARGS: "${COMFY_ARGS:-}"\n',
                '      COMFY_ARGS: "${COMFY_ARGS:-}"\n'
                '      COMFY_LANCEUR: "${COMFY_LANCEUR:-}"\n')),
            ("docker-compose.yml", motif(r'^  #.*?(?=^  comfyui:)', "")),
        ]),
    dict(
        nom="une exception devenue inutile, sans guillemets",
        banc="banc_conteneur.py",
        imite="IMPOSEES affirme que l'image impose ce reglage alors que .env le "
              "gouverne : la liste des dispenses ment sur son propre contenu",
        rougit="aucune exception inutile",
        editions=[
            ("docker-compose.yml", brut(
                '      STUDIO_HOTE: "0.0.0.0"',
                "      STUDIO_HOTE: ${STUDIO_HOTE:-0.0.0.0}")),
        ]),
    dict(
        nom="un defaut du compose recopie en dur dans .env.exemple",
        banc="banc_conteneur.py",
        imite="deux maitres pour un reglage : le jour ou le defaut change, "
              "toute installation nee d'un « cp .env.exemple .env » garde "
              "l'ancien sans un mot",
        rougit="aucun defaut recopie en dur dans .env.exemple",
        editions=[(".env.exemple", brut("#ROUE=cu128", "ROUE=cu128"))],
    ),
    dict(
        nom="le meme defaut recopie, avec guillemets",
        banc="banc_conteneur.py",
        imite="la meme panne sous la forme que Compose nettoie a la lecture : "
              "les guillemets tombent, la valeur reste",
        rougit="aucun defaut recopie en dur dans .env.exemple",
        editions=[(".env.exemple", brut("#STUDIO_LLM=qwen2.5vl:7b",
                                        'STUDIO_LLM="qwen2.5vl:7b"'))],
    ),
    dict(
        nom="le meme defaut recopie, avec un commentaire en bout de ligne",
        banc="banc_conteneur.py",
        imite="l'autre forme que Compose nettoie : le commentaire tombe, la "
              "valeur reste",
        rougit="aucun defaut recopie en dur dans .env.exemple",
        editions=[(".env.exemple", brut("#COMFY_PORT=8188",
                                        "COMFY_PORT=8188  # le port de ComfyUI"))],
    ),
    # ── La troisieme relecture adverse ────────────────────────────────
    dict(
        nom="un module suivi importe a cote d'un import paresseux",
        banc="banc_conteneur.py",
        imite="serveur.py importe douze fois en cours de fonction ; un module "
              "importe la sortait du suivi, et le reglage qu'il lit n'arrivait "
              "jamais au conteneur — le commit f6a30ba rejoue entier",
        rougit="tout ce qui est lu arrive au conteneur par le compose",
        editions=[
            ("serveur.py", brut("import comptes as _comptes\n", "")),
            ("serveur.py", brut("        import av\n",
                                "        import av\n"
                                "        import comptes as _comptes\n")),
            ("comptes.py", brut(
                "import secrets\nimport time\n",
                "import secrets\nimport time\n\n"
                'CADENCE = os.getenv("STUDIO_CADENCE", "24")\n')),
        ]),
    dict(
        nom="un module suivi dont l'import passe en try / except ImportError",
        banc="banc_conteneur.py",
        imite="la meme sortie de suivi par un nettoyage encore plus banal : "
              "rendre un import facultatif indente sa ligne, et le releve ne "
              "lisait que la colonne 0",
        rougit="tout ce qui est lu arrive au conteneur par le compose",
        editions=[
            ("serveur.py", brut(
                "import comptes as _comptes\n",
                "try:\n    import comptes as _comptes\n"
                "except ImportError:\n    _comptes = None\n")),
            ("comptes.py", brut(
                "import secrets\nimport time\n",
                "import secrets\nimport time\n\n"
                'SEL_TOUR = os.environ.get("STUDIO_SEL_TOUR", "")\n')),
        ]),
    dict(
        nom="un module suivi charge par importlib",
        banc="banc_conteneur.py",
        imite="aucun import a relever, le module disparait du suivi sans qu'un "
              "seul chiffre bouge : les 25 variables sont toutes dans "
              "serveur.py, donc le releve ne peut pas s'en apercevoir",
        rougit="fichiers du conteneur sont suivis",
        editions=[
            ("serveur.py", brut(
                "import comptes as _comptes\n",
                '_comptes = importlib.import_module("comptes")\n')),
        ]),
    dict(
        nom="COMFY_MODELES en double, dans le compose ET dans .env.exemple",
        banc="banc_conteneur.py",
        imite="deux maitres pour un chemin dont le defaut est CALCULE par le "
              "code : defaut_du_code rendait « os.path.join(BASE_COMFY, », un "
              "fragment truthy qui court-circuitait le repli sur le compose et "
              "ne s'egalait jamais lui-meme",
        rougit="aucun defaut recopie en dur dans .env.exemple",
        editions=[
            ("docker-compose.yml", brut(
                '      COMFY_MODELES: "${COMFY_MODELES:-}"',
                '      COMFY_MODELES: "${COMFY_MODELES:-/comfy/models}"')),
            (".env.exemple", brut("#OLLAMA_PORT=11434\n",
                                  "#OLLAMA_PORT=11434\n"
                                  "COMFY_MODELES=/comfy/models\n")),
        ]),
]

# ──────────────────────────────────────────────────────────────────────
#  banc_page.py — dix mutations verifiees rouges (commit 21c443c)
# ──────────────────────────────────────────────────────────────────────
# Les cinq premieres viennent de 21c443c. Les cinq suivantes etaient des TROUS
# CONNUS : quatre trouvees par la relecture adverse, plus celle du point
# d'appel, trouvee en fermant la premiere. Les quatre trous ne faisaient qu'un
# seul et meme defaut de banc — quatre releves par expression reguliere qui
# decrivaient UNE facon d'ecrire la panne au lieu de la panne : le debut de
# ligne, le trait d'union, le mot au lieu de la classe, la forme de la
# propriete. Chacune a ete eprouvee dans les deux sens : rouge sur le banc
# repare, verte sur le banc d'avant sa correction, et verte sur le banc repare
# des trois AUTRES corrections seulement.
PAGE = [
    dict(
        nom="une pastille reprend le nom d'une classe de mise en page",
        banc="banc_page.py",
        imite="« .puce.moteur » : une pastille qui herite de display:flex, de "
              "flex-direction:column et des regles descendantes du panneau des "
              "machines — invisible tant que personne ne s'en sert",
        rougit="aucune pastille ne porte le nom d'une classe de mise en page",
        editions=[
            ("web/index.html", brut(
                ".puce.rate{color:var(--rouge);border-color:var(--rouge)}",
                ".puce.moteur{color:var(--braise)}\n"
                ".puce.rate{color:var(--rouge);border-color:var(--rouge)}")),
        ]),
    dict(
        nom="une regle de pastille qui n'est jamais posee",
        banc="banc_page.py",
        imite="une regle qui dort sans element : elle ne fait rien, elle ne "
              "leve rien, et le prochain qui la lit croit qu'elle sert",
        rougit="aucune pastille decrite sans etre jamais posee",
        editions=[
            ("web/index.html", brut(
                ".puce.rate{color:var(--rouge);border-color:var(--rouge)}",
                ".puce.fini{color:var(--vert)}\n"
                ".puce.rate{color:var(--rouge);border-color:var(--rouge)}")),
        ]),
    dict(
        nom="CLE_REGLAGE derive de MENU_REGLAGE",
        banc="banc_page.py",
        imite="le silence du 31 aout : deux tables inverses ecrites a deux "
              "cents lignes d'ecart, une seule qui derive, et un reglage cesse "
              "d'etre retenu sans que rien ne le dise",
        rougit="MENU_REGLAGE et CLE_REGLAGE disent la meme chose",
        editions=[
            ("web/index.html", brut('"#priorite": "priorite"', '"#priorite": "prio"')),
        ]),
    dict(
        nom="un reglage qui nomme un menu inexistant",
        banc="banc_page.py",
        imite="valeurReglage rend null pour toujours : le menu tourne dans le "
              "vide et la conversation ne retient plus rien",
        rougit="chaque reglage nomme un menu qui existe dans la page",
        editions=[
            ("web/index.html", brut('taille: "#taille" };', 'taille: "#tailles" };')),
        ]),
    dict(
        nom="le cran de priorite repart dans le corps de la demande",
        banc="banc_page.py",
        imite="un second onglet reste ouvert efface le cran du premier au "
              "simple envoi d'un message : le serveur raisonne sur la PRESENCE",
        rougit="aucun envoi ne renvoie le cran de priorite du menu",
        editions=[
            ("web/index.html", brut(
                "body: JSON.stringify({ texte: complet, conversation: cid,",
                "body: JSON.stringify({ texte: complet, conversation: cid,"
                ' priorite: $("#priorite").value,')),
        ]),
    # ── Les quatre trous fermes, et leur descendante ──────────────────
    dict(
        nom="le cran de priorite en abreviation ES6",
        banc="banc_page.py",
        imite="exactement la panne qui a lance ce fichier : la ligne fautive "
              "restauree sous sa vraie forme, « priorite, », que le releve ne "
              "voyait pas parce qu'il cherchait « priorite: $(\"#priorite\") »",
        rougit="aucun envoi ne renvoie le cran de priorite du menu",
        editions=[
            ("web/index.html", brut(
                "      if (reglageEnVol) { try { await reglageEnVol; } catch (e) {} }\n"
                '      const r = await fetch("/api/generer", {',
                "      if (reglageEnVol) { try { await reglageEnVol; } catch (e) {} }\n"
                '      const priorite = $("#priorite").value;\n'
                '      const r = await fetch("/api/generer", {')),
            ("web/index.html", brut(
                "body: JSON.stringify({ texte: complet, conversation: cid,",
                "body: JSON.stringify({ texte: complet, conversation: cid, priorite,")),
        ]),
    dict(
        nom="le cran de priorite entre par le point d'appel",
        banc="banc_page.py",
        imite="la panne d'origine dans sa VRAIE forme, relevee sur "
              "21c443c^ : le corps portait « priorite, » et le cran entrait "
              "deux mille lignes plus bas, en argument de lancerDemande. Ni "
              "« priorite: » ni « const » nulle part — la mutation ci-dessus, "
              "seule, se fermait sans fermer le defaut qu'elle imite",
        rougit="aucun envoi ne renvoie le cran de priorite du menu",
        editions=[
            ("web/index.html", brut(
                '$("#go").onclick = () => lancerDemande(null);',
                '$("#go").onclick = () => lancerDemande($("#priorite").value);')),
        ]),
    dict(
        nom="une classe de mise en page definie ailleurs qu'en debut de ligne",
        banc="banc_page.py",
        imite="« .puce.ligne » contre « .moteur .ligne » : le meme degat que "
              "« .puce.moteur », mais la classe heritee est definie en "
              "descendante — 24 classes sur 77 echappaient au releve",
        rougit="aucune pastille ne porte le nom d'une classe de mise en page",
        editions=[
            ("web/index.html", brut(
                ".puce.rate{color:var(--rouge);border-color:var(--rouge)}",
                ".puce.ligne{color:var(--braise)}\n"
                ".puce.rate{color:var(--rouge);border-color:var(--rouge)}")),
            # Posee pour de bon, sans quoi c'est « regle jamais posee » qui
            # rougirait — la mutation passerait pour attrapee alors que la
            # collision, elle, resterait invisible.
            ("web/index.html", brut(
                '(esquisse ? \'<span class="puce esquisse">brouillon</span>\'',
                '(esquisse ? \'<span class="puce esquisse ligne">brouillon</span>\'')),
        ]),
    dict(
        nom="un identifiant de menu a trait d'union",
        banc="banc_page.py",
        imite="« #forcer-moteur » : le reglage du moteur nomme un menu qui "
              "n'existe pas et cesse d'etre retenu. « \\w » ne franchit pas le "
              "trait d'union, donc l'entree DISPARAISSAIT des trois releves au "
              "lieu de rougir — le defaut du 31 aout dans sa forme la plus muette",
        rougit="chaque reglage nomme un menu qui existe dans la page",
        editions=[
            ("web/index.html", brut('modele: "#forcer"', 'modele: "#forcer-moteur"')),
            ("web/index.html", brut('"#forcer": "modele"', '"#forcer-moteur": "modele"')),
            ("web/index.html", brut('{ sel: "#forcer", nom: "moteur"',
                                    '{ sel: "#forcer-moteur", nom: "moteur"')),
        ]),
    dict(
        nom="une regle de pastille dont le nom traine dans du texte francais",
        banc="banc_page.py",
        imite="« .puce.file » dort sans element, et « en file — 3 devant », a "
              "deux lignes de la, suffisait a la faire passer pour posee : le "
              "releve cherchait un mot dans la ligne, pas une classe dans un "
              "attribut",
        rougit="aucune pastille decrite sans etre jamais posee",
        editions=[
            ("web/index.html", brut(
                ".puce.rate{color:var(--rouge);border-color:var(--rouge)}",
                ".puce.file{color:var(--encre-pale)}\n"
                ".puce.rate{color:var(--rouge);border-color:var(--rouge)}")),
        ]),
]

# ──────────────────────────────────────────────────────────────────────
#  Les trous connus : ecrits, nommes, et PAS ENCORE fermes
# ──────────────────────────────────────────────────────────────────────
# Celle-ci DOIT rougir et passe au vert aujourd'hui. Ce n'est pas une
# hypothese : elle a ete jouee, et le banc vise est reste vert. L'ecrire ici
# plutot que dans un rapport est le seul moyen qu'elle reste mesuree — le
# premier trou de ce genre a ete decouvert des mois trop tard, dans un rapport
# que personne n'a relu.
#
# Quand le banc saura la voir, elle rougira : il le dira, et il suffira de la
# deplacer dans PAGE ou CONTENEUR ci-dessus. Les quatre qui visaient
# banc_page.py y sont passees ; il ne reste que celle de banc_conteneur.py,
# qui demande d'EVALUER un defaut calcule et non de generaliser un releve.
TROUS_CONNUS = [
    dict(
        nom="un defaut du compose qui repete un defaut CALCULE par le code",
        banc="banc_conteneur.py",
        imite="deux maitres pour COMFY_MODELES, et la verification ecrite pour "
              "ce piege ne peut pas le voir : le defaut du code est "
              "« os.path.join(BASE_COMFY, \"models\") », que le banc lit sans "
              "l'evaluer. Rendre None est honnete, mais quatre chemins et un "
              "port restent hors de portee de « pas deux defauts »",
        rougit="pas deux defauts pour un meme reglage dans le compose",
        editions=[
            ("docker-compose.yml", brut(
                '      COMFY_MODELES: "${COMFY_MODELES:-}"',
                '      COMFY_MODELES: "${COMFY_MODELES:-/comfy/models}"')),
        ]),
]

# ──────────────────────────────────────────────────────────────────────
#  banc_repartition.py — le studio sans carte se choisissait lui-meme
# ──────────────────────────────────────────────────────────────────────
# Signale par l'utilisateur : « il m'affiche souvent moteur local, le studio
# n'en a pas, uniquement les noeuds, et du coup attend dans le vide ». Trois
# endroits supposaient que le studio pouvait calculer ; les trois sont ici.
_AVEC_TOLERANCE = '    return vram + tolerance_ram(e.get("ram") or 0)'
_SANS_CARTE = ('    if not vram:' + chr(10)
               + '        return 0.0' + chr(10))

REPARTITION = [
    dict(
        nom="la tolerance RAM accordee a une machine SANS carte",
        banc="banc_repartition.py",
        imite="un studio sans GPU se presente comme une carte de 2 a 5 Go "
              "selon sa RAM, et se fait retenir pour les petits moteurs",
        rougit="et la tolerance RAM ne lui invente pas une carte de 5 Go",
        editions=[("serveur.py", brut(
            _SANS_CARTE + _AVEC_TOLERANCE, _AVEC_TOLERANCE))]),
    dict(
        nom="une machine SANS carte redevient candidate au rendu",
        banc="banc_repartition.py",
        imite="depuis que le rendu prend la PLUS PETITE, une machine a zero "
              "gigaoctet serait choisie la premiere : elle est la plus petite "
              "de toutes, et elle ne rend rien",
        rougit="mais « pas de carte, pas de rendu » l'ecarte quand meme",
        editions=[("serveur.py", brut(
            '        if not (e.get("vram") or 0):' + chr(10)
            + "            continue" + chr(10), ""))]),
    dict(
        nom="le rendu reprend la PLUS GROSSE carte",
        banc="banc_repartition.py",
        imite="la regle d'avant, que l'utilisateur a inversee : la grosse carte "
              "part en rendu et n'est plus la pour le suivant",
        rougit="a cartes libres, le rendu prend la PLUS PETITE qui tient",
        editions=[("serveur.py", brut(
            'petite = min(dans, key=lambda x: vram_de(x["id"]))',
            'petite = max(dans, key=lambda x: vram_de(x["id"]))'))]),
    dict(
        nom="l'analyse reprend la plus PETITE carte",
        banc="banc_cerveaux.py",
        imite="l'autre moitie de la regle inversee : l'analyse traine sur la "
              "petite carte pendant que la grosse attend le rendu qu'elle "
              "n'a pas encore lu",
        rougit="a cartes libres, la PLUS GROSSE d'abord",
        editions=[("serveur.py", brut(
            "bons.append((0 if libre else 1, -taille, url, ident))",
            "bons.append((0 if libre else 1, taille, url, ident))"))]),
    dict(
        nom="le verrou de carte oublie la priorite",
        banc="banc_repartition.py",
        imite="une analyse de trois secondes patiente derriere deux rendus de "
              "quatre minutes — huit minutes sans que rien ne parte, pour une "
              "demande que le studio n'a meme pas encore lue",
        rougit="puis l'analyse passe devant, et les rendus gardent leur ordre",
        editions=[("serveur.py", brut(
            "        file = self._attente[0 if prioritaire else 1]",
            "        file = self._attente[1]"))]),
]

# ──────────────────────────────────────────────────────────────────────
#  banc_variantes.py — six mutations, une par panne de 3cecca2
# ──────────────────────────────────────────────────────────────────────
# Ce banc porte 115 verifications et n'en avait aucune d'eprouvee : le commit
# qui l'a porte de 101 a 115 le dit lui-meme — « aucune mutation ajoutee pour
# ces vingt-deux cas ». Les six ci-dessous ne prennent pas les cas un par un,
# elles reprennent les QUATRE pannes que 3cecca2 nomme, plus les deux ecritures
# de la regle du rang qu'il a fusionnees.
#
# Chacune restaure le code d'AVANT le correctif, mot pour mot quand c'est
# possible : une mutation qui invente une manipulation prouve que le banc voit
# quelque chose, pas qu'il voit la panne.
VARIANTES = [
    dict(
        nom="la mediatheque ne sert ni le tour ni le groupe",
        banc="banc_variantes.py",
        imite="« tour=None, groupe=None » et un 404 — releve sur le studio en "
              "service : POST /api/variante reclame la conversation ET le "
              "tour, le geste n'etait donc pas appelable depuis la grille, "
              "c'est-a-dire partout sauf la ou l'on compare quatre images "
              "indiscernables",
        rougit="chaque piece dit de quel tour elle sort",
        editions=[("serveur.py", brut(
            '                    "tour": tour.get("id"),' + chr(10)
            + '                    "groupe": groupe,' + chr(10),
            '                    "tour": None,' + chr(10)
            + '                    "groupe": None,' + chr(10)))]),
    dict(
        nom="la mediatheque sert la marque BRUTE au lieu de la reponse calculee",
        banc="banc_variantes.py",
        imite="trois vues, trois reponses : le fil encadrait la premiere, la "
              "mediatheque n'en marquait AUCUNE, et « agrandis-la » suivait "
              "encore une troisieme regle. Le tour ne porte « choisie » "
              "qu'apres un geste humain ; le studio, lui, vise le plus petit "
              "rang abouti des la fin du rendu",
        rougit="sans aucun choix humain, la mediatheque marque la premiere",
        editions=[("serveur.py", brut(
            '"choisie": (retenues.get(groupe) == tour.get("id") if groupe'
            + chr(10)
            + '                                else bool(tour.get("choisie"))),',
            '"choisie": bool(tour.get("choisie")),'))]),
    dict(
        nom="le choix fait a la main ne prime plus sur le rang",
        banc="banc_variantes.py",
        imite="la troisieme est designee pendant que la premiere calcule "
              "encore ; celle-ci, en finissant, reprend la place que "
              "l'utilisateur venait de donner a une autre — l'inverse exact de "
              "ce que la garde protege, et un clic qu'on ne peut pas refaire",
        rougit="et elle ne reprend pas la place donnee a la troisieme",
        editions=[("serveur.py", brut(
            "    if designee:" + chr(10) + "        return designee" + chr(10),
            ""))]),
    dict(
        nom="le rang 1 tout court, et non le plus petit rang ABOUTI",
        banc="banc_variantes.py",
        imite="quand le premier tirage echoue ou qu'on le retire de la file, "
              "plus AUCUNE variante ne devient l'image courante et "
              "« agrandis-la » vise en silence l'image d'avant le groupe",
        rougit="le groupe designe quand meme une image",
        editions=[("serveur.py", brut(
            "    return min(aboutis)[1] if aboutis else None",
            "    return next((i for r, i in aboutis if r == 1), None)"))]),
    dict(
        nom="la phrase du devis repasse aux minutes des 90 s",
        banc="banc_variantes.py",
        imite="la page ne lit pas le champ, elle relit la phrase : a 90 s de "
              "mediane le serveur ecrivait « 2 min » et la page affichait "
              "120 s — 33,3 % d'ecart sur le seul chiffre que l'utilisateur "
              "voie avant de lancer",
        rougit="la phrase ne s'ecarte jamais du champ de plus de 10 %",
        editions=[("serveur.py", brut("DEVIS_EN_SECONDES_JUSQUA = 300",
                                      "DEVIS_EN_SECONDES_JUSQUA = 90"))]),
    dict(
        nom="le devis d'un essai precedent survit a la relance",
        banc="banc_variantes.py",
        imite="la tache garde son identifiant d'une relance a l'autre : une "
              "demande repartie en brouillon, ou relancee apres l'effacement "
              "de ses rendus comparables, promettait encore le chiffre que "
              "plus aucune mediane n'etayait. La phrase du journal, elle, ne "
              "ment jamais ainsi — elle n'est simplement pas reecrite",
        rougit="sans mediane, le devis d'avant est retire et non laisse la",
        editions=[("serveur.py", brut(
            '            TACHES.get(tid, {}).pop("devis", None)',
            "            pass"))]),
]


# ──────────────────────────────────────────────────────────────────────
#  banc_cerveaux.py — le plafond de la REFLEXION, qui n'est pas celui du RENDU
# ──────────────────────────────────────────────────────────────────────
# Les sept cas que 3cecca2 a ajoutes sur plafond_cerveau n'etaient couverts par
# rien. La panne qu'ils gardent est un piege a deux etages : « cette machine
# n'a pas de carte » s'y lisait « on ne sait pas ce qu'elle tient », et un zero
# qui veut dire « elle ne rend rien » devenait « elle peut tout charger ».
# Mesure du 31 aout, rejouee sur un noeud a agent annoncant vram=0 et ram=63,8 :
# gemma4:26b, 18,6 Go, choisi sur une carte de 11 — cent soixante-cinq secondes
# par traduction.
#
# La troisieme mutation garde la porte d'en face, et c'est pour cela qu'elle
# est la : le correctif pouvait tres bien fermer le cas « machine inconnue » en
# fermant le cas « machine sans carte », et personne ne l'aurait vu.
#
# CES DEUX-LA SE RECOUVRENT DANS UN SEUL SENS, et c'est verifie : retirer le
# plafond RAM allume AUSSI la ligne du repli, parce qu'un plafond infini fait
# que plus rien n'est jamais ecarte et que le repli ne s'emprunte plus. Le
# contraire est faux — inverser le repli n'allume que sa ligne. Les deux
# mesurent donc bien deux gardes, et non deux fois la meme.
CERVEAUX = [
    dict(
        nom="la machine SANS carte reperd son plafond",
        banc="banc_cerveaux.py",
        imite="la branche morte reveillee par 38cb9d0 : sans carte, "
              "_vram_utile rend 0, zero est faux, et « sinon aucun plafond » "
              "l'emporte. Le plafond disparait la ou il devait etre le plus "
              "bas — 165 s par traduction, le chiffre ecrit juste au-dessus "
              "dans le code",
        rougit="et pour ecrire, elle reste plafonnee",
        editions=[("serveur.py", brut(
            '    if e.get("ram"):' + chr(10)
            + '        return tolerance_ram(e["ram"])' + chr(10), ""))]),
    dict(
        nom="quand aucun voyant ne tient, le repli reprend le PLUS GROS",
        banc="banc_cerveaux.py",
        imite="la seconde porte : « tenables or voyants » puis max() rendait "
              "precisement le modele que le plafond venait d'ecarter, et le "
              "plafond ne servait plus a rien des qu'il mordait sur tout le "
              "monde. Une image mal lue par un petit modele se corrige ; neuf "
              "cents secondes a ne pas rendre, non (GTX 1060, 31 aout)",
        rougit="meme quand aucun voyant ne tient, c'est le plus petit qui repond",
        editions=[("serveur.py", brut(
            '    return min(voyants, key=lambda m: m.get("size", 0))["name"]',
            '    return max(voyants, key=lambda m: m.get("size", 0))["name"]'))]),
    dict(
        nom="la machine INCONNUE herite du plafond des machines sans carte",
        banc="banc_cerveaux.py",
        imite="la porte d'en face, celle qu'on ferme par erreur en fermant "
              "l'autre : on ne devine pas ce qu'une machine dont on ignore "
              "tout peut charger, et lui refuser ses gros modeles la rendrait "
              "muette pour rien",
        rougit="d'une machine inconnue, on prend le plus gros",
        editions=[("serveur.py", brut(
            "    if not ident:" + chr(10) + '        return float("inf")'
            + chr(10),
            "    if not ident:" + chr(10) + "        return 0.0" + chr(10)))]),
]


# ──────────────────────────────────────────────────────────────────────
#  banc_cout.py — l'argent qui sort, et la comptabilite qui le dit
# ──────────────────────────────────────────────────────────────────────
# Soixante-dix-neuf verifications, aucune eprouvee. Les trois ci-dessous visent
# les trois endroits ou une erreur ne se voit PAS : un depassement de plafond
# paye pour de bon, une ligne perdue en silence a l'arret, et une depense
# rangee sous un compte qui n'existe pas.
#
# Ce banc imprime « RATE » et non « NON » — voir MARQUE_ROUGE plus haut.
COUT = [
    dict(
        nom="le plafond ne regarde plus que les appels DEJA consignes",
        banc="banc_cout.py",
        imite="la course d'origine : le compteur n'est ecrit qu'au RETOUR du "
              "fournisseur, donc pendant l'aller-retour il reste immobile et "
              "les trois travailleurs partent tous. Un appel parti est un "
              "appel paye, meme sans reponse — c'est de l'argent, pas un "
              "compteur",
        rougit="appels lances ensemble : un seul part",
        editions=[("serveur.py", brut(
            "    return appels_du_mois(compte) + _EN_VOL_NUAGE.get(compte, 0)",
            "    return appels_du_mois(compte)"))]),
    dict(
        nom="la vidange recompte la file avec qsize()",
        banc="banc_cout.py",
        imite="qsize() ne compte pas la ligne deja SORTIE de la file, celle "
              "que le fil tient pendant que le disque ne repond plus : un "
              "appel distant consigne a l'instant de l'arret disparait sans "
              "un mot, et le compte plafonne se rembourse en redemarrant. "
              "Mesure : 39 annonces pour 40 lignes reellement perdues",
        rougit="mais la vidange la compte quand meme",
        editions=[("serveur.py", brut("    return _A_ECRIRE.unfinished_tasks",
                                      "    return _A_ECRIRE.qsize()"))]),
    dict(
        nom="le journal se relit avec errors=replace",
        banc="banc_cout.py",
        imite="le remede evident, et il etait PIRE que le mal : un octet "
              "abime au milieu d'une ligne complete donne un JSON valide au "
              "nom de compte corrompu. Le studio demarre, la depense quitte le "
              "compte plafonne pour un compte fantome, et rien ne le dit — "
              "c'est le remboursement par redemarrage sous une autre forme",
        rougit="une ligne abimee est JETEE, pas rangee sous un compte fantome",
        editions=[("serveur.py", brut(
            '                    l = brut.decode("utf-8").strip()',
            '                    l = brut.decode("utf-8", "replace").strip()'))]),
]


# ──────────────────────────────────────────────────────────────────────
#  banc_catalogue.py — « ~0 Go a prendre », une ligne avant le telechargement
# ──────────────────────────────────────────────────────────────────────
# Le chiffre sur lequel quelqu'un decide d'attendre quarante minutes. Les deux
# mutations reprennent les deux facons de le fausser que le banc raconte : un
# affichage arrondi a zero, et une somme qui compte deux fois les fichiers que
# deux moteurs partagent.
CATALOGUE = [
    dict(
        nom="l'affichage sous le demi-gigaoctet repasse aux gigaoctets",
        banc="banc_catalogue.py",
        imite="« fluidifier : ~0 Go a prendre » — le defaut d'origine, mais "
              "par l'AFFICHAGE et non par la table : detourer pese 0,44 Go "
              "releve et agrandir 0,07, et « ~0 Go » se lit « c'est gratuit »",
        rougit="sous le demi-gigaoctet on passe aux megaoctets",
        editions=[("catalogue.py", brut(
            '        quantite = f"{exact * 1000:.0f} Mo"',
            '        quantite = f"{exact:.0f} Go"'))]),
    dict(
        nom="poids() additionne les moteurs au lieu de les unir",
        banc="banc_catalogue.py",
        imite="deux moteurs partagent des fichiers, et les additionner "
              "surestime le telechargement : la raison d'etre de poids(), que "
              "rien ne verifiait avant ce banc",
        rougit="et poids() les compte une seule fois",
        editions=[("catalogue.py", brut(
            "    return round(sum(TAILLES.get(f, 0.0) "
            "for f in fichiers_requis(cles)), 1)",
            "    return round(sum(TAILLES.get(f, 0.0) "
            "for c in cles for f in fichiers_requis([c])), 1)"))]),
    dict(
        nom="une taille jamais relevee s'annonce « au moins 0 Mo »",
        banc="banc_catalogue.py",
        imite="un plancher annonce comme un total : quand TOUT ce qui manque "
              "est justement ce qu'on ne sait pas mesurer, « au moins 0 » "
              "n'annonce rien du tout — et c'est le cas de fluidifier, celui "
              "par lequel le defaut a ete trouve",
        rougit="une taille jamais relevee s'annonce comme telle",
        editions=[("catalogue.py", brut(
            '        return "taille inconnue" if exact < 0.05 '
            'else f"au moins {quantite}"',
            '        return f"au moins {quantite}"'))]),
]


# ──────────────────────────────────────────────────────────────────────
#  banc_attente.py — une demande gardee, et un chiffre qui ne ment pas
# ──────────────────────────────────────────────────────────────────────
# Soixante-quatre verifications, aucune eprouvee. Les deux mutations visent les
# deux reglages qui mentaient sur ce qu'ils faisaient — c'est la meme faute
# deux fois, et c'est celle que ce projet traite comme pire qu'un reglage
# absent : l'administrateur croit avoir agi et s'en va.
ATTENTE = [
    dict(
        nom="le plancher de quinze secondes s'applique aussi au clic",
        banc="banc_attente.py",
        imite="api_admin_pause annoncait « reveillees: 0 » pendant que les "
              "demandes repartaient trente secondes plus tard par le veilleur. "
              "Mesure du 1er septembre : trois demandes armees, reponse "
              "« 0 relancee », trois departs une fois le plancher passe. Un "
              "chiffre faux est pire que pas de chiffre",
        rougit="le clic, lui, la reveille tout de suite",
        editions=[("serveur.py", brut(
            '        if plancher and time.time() - a.get("quand", 0) < 15:',
            '        if time.time() - a.get("quand", 0) < 15:'))]),
    dict(
        nom="la revision d'echeance repart de maintenant et non de « depuis »",
        banc="banc_attente.py",
        imite="un simple passage dans /admin repousse alors l'attente de "
              "toutes les demandes en cours — le rearmement que « depuis » "
              "avait justement ete introduit pour empecher, et l'expiration "
              "n'arrive jamais",
        rougit="elle est deja passee, et l'on sait POURQUOI",
        editions=[("serveur.py", brut(
            '        neuve = a.get("depuis", 0) + heures * 3600',
            "        neuve = time.time() + heures * 3600"))]),
]


# ──────────────────────────────────────────────────────────────────────
#  banc_durees.py — la mediane, et pourquoi ce n'est pas la moyenne
# ──────────────────────────────────────────────────────────────────────
# Dix verifications, aucune eprouvee. Une seule mutation suffit ici : le banc
# tient en une phrase, et cette phrase est un choix qu'un lecteur presse
# defera. « Simplifier » sum()/len() ne change rien sur les jeux reguliers du
# banc — 100/110/120 ont la meme moyenne que leur mediane — et ne se voit QUE
# sur le rendu qui a attendu une carte occupee.
DUREES = [
    dict(
        nom="la moyenne au lieu de la mediane",
        banc="banc_durees.py",
        imite="un rendu qui a attendu une demi-heure derriere une carte "
              "occupee tire la moyenne a 682 s pour un travail qui en prend "
              "110, et le devis annonce onze minutes au lieu de deux : il ne "
              "dit plus rien de ce qui va se passer maintenant",
        rougit="un rendu qui a attendu ne fausse pas le devis",
        editions=[("serveur.py", brut("            return v[len(v) // 2], len(v)",
                                      "            return sum(v) / len(v), len(v)"))]),
]


# ──────────────────────────────────────────────────────────────────────
#  banc_adulte.py — le seul garde-fou code en dur du projet
# ──────────────────────────────────────────────────────────────────────
# Ce banc n'a pas de dit() : il liste ses fautes indentees sous leur compte,
# d'ou son entree dans MARQUE_ROUGE. La ligne nommee existe bel et bien — elle
# cite la demande qui est passee au travers — et c'est elle qu'on exige.
#
# Une seule mutation, et c'est la deuxieme des deux erreurs du 31 aout, celle
# qui a fait passer « a child in a sexual pose » : le souligne est un caractere
# de mot, donc « \\b » ne separe pas « nude » de « _body », et les moteurs a
# etiquettes recoivent justement du danbooru colle par des soulignes.
ADULTE = [
    dict(
        nom="les frontieres du motif redeviennent des « \\b » ordinaires",
        banc="banc_adulte.py",
        imite="tout le pan des etiquettes collees repasse : « nude_body », "
              "« sex_scene », « explicit_content », « rating_explicit » ne "
              "sont plus reconnus adultes — et le prompt envoye a la carte est "
              "TOUJOURS traduit en anglais, donc c'est par la que tout sort de "
              "la maison",
        rougit="adulte NON reconnu : « 1girl, nude_body »",
        editions=[("serveur.py", brut(
            '_BORD = r"(?<![^\\W_])"' + chr(10) + '_FIN = r"(?![^\\W_])"',
            '_BORD = r"\\b"' + chr(10) + '_FIN = r"\\b"'))]),
]


# ── Ce que la couverture coute, et ou part le temps ───────────────────
# Mesure du 1er septembre, sur cette machine : 8,4 s pour 32 mutations sur
# quatre bancs, 52,8 s pour 51 sur dix. Le sextuplement ne vient pas du nombre
# mais des DEUX bancs qui montent un studio complet — banc_variantes.py met
# 3,5 s par lancement et banc_cout.py 2,9, la ou banc_catalogue.py en met 0,07.
# Les six mutations de banc_variantes pesent a elles seules 22 s.
#
# C'est le prix qu'on accepte, et il vaut la peine d'etre relu avant d'ajouter
# une mutation de plus sur ces deux bancs-la : une couverture qui vaut vingt
# secondes de CI par panne finirait par se faire couper, et un filet coupe ne
# mesure plus rien. Sur les huit autres bancs, une mutation neuve coute moins
# d'une demi-seconde — c'est la qu'il reste de la place.
#
# On ne les lance pas en parallele, et ce n'est pas un oubli : banc_variantes
# ordonne ses tirages par des sommeils de 0,02 a 0,6 s pour eprouver « le
# premier fini n'est pas celui qui tient le rang ». Huit processus qui se
# disputent les coeurs reordonnent ces tirages, et le banc deviendrait
# capricieux — un banc qui rougit au hasard vaut moins qu'un banc lent.
MUTATIONS = (CONTENEUR + PAGE + REPARTITION + VARIANTES + CERVEAUX + COUT
             + CATALOGUE + ATTENTE + DUREES + ADULTE)


# ── Jouer une mutation ────────────────────────────────────────────────
_CACHE = {}


def source(banc):
    if banc not in _CACHE:
        _CACHE[banc] = {rel: lire(rel) for rel in BESOINS[banc]}
    return dict(_CACHE[banc])


def lancer(banc, fichiers, racine):
    """Ecrit les fichiers dans un dossier neuf, lance le banc, rend (code, sortie)."""
    dossier = tempfile.mkdtemp(dir=racine)
    for rel, texte in fichiers.items():
        chemin = os.path.join(dossier, *rel.split("/"))
        os.makedirs(os.path.dirname(chemin), exist_ok=True)
        with io.open(chemin, "w", encoding="utf-8", newline="\n") as f:
            f.write(texte)
    # PYTHONIOENCODING : les bancs impriment des guillemets francais, et une
    # console Windows en cp1252 faisait mourir le fils sur son propre affichage
    # — un plantage qui ressemblait a une mutation attrapee.
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    fini = subprocess.run([sys.executable, os.path.join(dossier, banc)],
                          cwd=dossier, env=env, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT)
    return fini.returncode, fini.stdout.decode("utf-8", "replace")


def verdict(mut, racine):
    """Rend (etat, detail). etat : "rouge", "vert", "perimee" ou "casse"."""
    fichiers = source(mut["banc"])
    for rel, edition in mut["editions"]:
        if rel not in fichiers:
            return "perimee", f"{rel} n'est pas copie pour {mut['banc']}"
        neuf, souci = appliquer(fichiers[rel], edition)
        if neuf is None:
            return "perimee", f"{rel} : {souci}"
        fichiers[rel] = neuf
    code, sortie = lancer(mut["banc"], fichiers, racine)
    marque = MARQUE_ROUGE.get(mut["banc"], "  NON")
    lignes_non = [l for l in sortie.splitlines() if l.startswith(marque)]
    if any(mut["rougit"] in l for l in lignes_non):
        return "rouge", ""
    if code == 0:
        return "vert", "le banc n'a rien vu"
    if not lignes_non:
        return "casse", sortie.strip().splitlines()[-1][:120] if sortie.strip() else "sans sortie"
    return "casse", "rouge ailleurs : " + " / ".join(l.strip() for l in lignes_non)[:120]


depart = time.time()
racine = tempfile.mkdtemp(prefix="banc_mutations_")
try:
    # ── LE SENS INVERSE. Un banc qui rougit sur tout n'attrape rien : sans
    # cette verification, une mutation « rouge » ne prouverait pas que c'est
    # ELLE qui a fait rougir.
    for banc in sorted(BESOINS):
        code, sortie = lancer(banc, source(banc), racine)
        derniere = [l for l in sortie.splitlines() if l.strip()]
        dit(code == 0, f"{banc} est vert sur le depot sain",
            derniere[-1].strip() if derniere else "sans sortie")

    for mut in MUTATIONS:
        etat, detail = verdict(mut, racine)
        dit(etat == "rouge", f"{mut['banc']} rougit : {mut['nom']}",
            {"rouge": mut["rougit"],
             "vert": "LE FILET A UN TROU — " + mut["imite"],
             "perimee": "MUTATION PERIMEE, elle ne mesure plus rien — " + detail,
             "casse": "le banc s'est casse au lieu de rougir — " + detail}[etat])

    # Signales, jamais comptes en echec : voir TROUS_CONNUS plus haut.
    for mut in TROUS_CONNUS:
        etat, detail = verdict(mut, racine)
        if etat == "rouge":
            signales.append(f"FERME : {mut['nom']} — a deplacer dans PAGE")
        elif etat == "vert":
            signales.append(f"trou ouvert : {mut['nom']} — {mut['imite']}")
        else:
            # Une ancre perimee reste un echec, meme pour un trou connu : sans
            # elle, le trou cesse d'etre mesure et l'on croira l'avoir ferme.
            rate.append(mut["nom"])
            signales.append(f"A REGARDER : {mut['nom']} — {detail}")
finally:
    shutil.rmtree(racine, ignore_errors=True)

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees — "
      f"{len(MUTATIONS)} mutations, {len(TROUS_CONNUS)} trous connus, "
      f"{time.time() - depart:.1f} s")
for s in signales:
    print("    " + s)
for r in rate:
    print("    a regarder :", r)
sys.exit(1 if rate else 0)
