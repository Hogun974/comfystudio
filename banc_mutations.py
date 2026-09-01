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
y applique la mutation, lance CE banc-la — pas les neuf — et exige une ligne
« NON » nommee. Le depot n'est jamais touche.

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
banc_page.py laisse ENCORE passer. Elles sont ecrites, nommees et signalees,
mais ne font pas echouer : les compter en echec rendrait la CI rouge en
permanence, et une CI qui rougit pour rien finit ignoree. Les basculer dans
MUTATIONS est le geste qui clot la reparation du filet.
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
# fichiers dont banc_conteneur.py a besoin en font 0,007 s. Sur les dix-huit
# mutations, deux secondes de CI contre un huitieme de seconde.
def fichiers_du_conteneur():
    """La meme piste que celle que banc_conteneur.py suit lui-meme.

    Il ne releve pas le repertoire mais les IMPORTS de serveur.py — agent_noeud
    est dans l'image et ne tourne pas dans ce conteneur. Copier une liste ecrite
    a la main ici la ferait deriver de la sienne : le jour ou serveur.py
    importerait un module de plus, la mutation posee dedans tomberait dans un
    dossier ou le module n'est pas, et le banc rougirait sur un import manquant
    au lieu de la variable oubliee.
    """
    fichiers = ["banc_conteneur.py", "serveur.py",
                "docker-compose.yml", "Dockerfile", ".env.exemple"]
    for mod in re.findall(r'(?m)^(?:import|from)\s+([a-z_][a-z0-9_]*)',
                          lire("serveur.py")):
        nom = mod + ".py"
        if nom not in fichiers and os.path.exists(os.path.join(ICI, nom)):
            fichiers.append(nom)
    return fichiers


BESOINS = {
    "banc_conteneur.py": fichiers_du_conteneur(),
    "banc_page.py": ["banc_page.py", "web/index.html"],
}


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
#  banc_conteneur.py — treize mutations, toutes verifiees rouges
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
]

# ──────────────────────────────────────────────────────────────────────
#  banc_page.py — cinq mutations verifiees rouges (commit 21c443c)
# ──────────────────────────────────────────────────────────────────────
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
]

# ──────────────────────────────────────────────────────────────────────
#  Les trous connus : ecrits, nommes, et PAS ENCORE fermes
# ──────────────────────────────────────────────────────────────────────
# Ces quatre-la DOIVENT rougir et passent au vert aujourd'hui. Ce ne sont pas
# des hypotheses : une relecture adverse les a jouees, et banc_page.py est reste
# vert sur chacune. Les ecrire ici plutot que dans un rapport est le seul moyen
# qu'elles restent mesurees — le premier trou de ce genre a ete decouvert des
# mois trop tard, dans un rapport que personne n'a relu.
#
# Quand banc_page.py saura les voir, elles rougiront : le banc le dira, et il
# suffira de les deplacer dans PAGE ci-dessus.
TROUS_CONNUS = [
    dict(
        nom="le cran de priorite en abreviation ES6",
        banc="banc_page.py",
        imite="exactement la panne qui a lance ce fichier : la ligne fautive "
              "restauree sous sa vraie forme, « priorite, », et le banc ecrit "
              "pour elle est reste vert",
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
        nom="une classe de mise en page definie ailleurs qu'en debut de ligne",
        banc="banc_page.py",
        imite="« .puce.ligne » contre « .moteur .ligne » : le meme degat que "
              "« .puce.moteur », mais la classe heritee est definie en "
              "descendante et le releve ne lit que les debuts de ligne",
        rougit="aucune pastille ne porte le nom d'une classe de mise en page",
        editions=[
            ("web/index.html", brut(
                ".puce.rate{color:var(--rouge);border-color:var(--rouge)}",
                ".puce.ligne{color:var(--braise)}\n"
                ".puce.rate{color:var(--rouge);border-color:var(--rouge)}")),
            # Posee pour de bon, sans quoi c'est « regle jamais posee » qui
            # rougirait — la mutation passerait pour attrapee alors que la
            # collision, elle, reste invisible.
            ("web/index.html", brut(
                '(esquisse ? \'<span class="puce esquisse">brouillon</span>\'',
                '(esquisse ? \'<span class="puce esquisse ligne">brouillon</span>\'')),
        ]),
    dict(
        nom="un identifiant de menu a trait d'union",
        banc="banc_page.py",
        imite="« #forcer-moteur » : le reglage du moteur nomme un menu qui "
              "n'existe pas et cesse d'etre retenu — et les trois releves "
              "s'arretent sur « #\\w+ », donc l'entree disparait au lieu de "
              "rougir",
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
              "deux lignes de la, suffit a la faire passer pour posee : le "
              "releve cherche un mot, pas une classe",
        rougit="aucune pastille decrite sans etre jamais posee",
        editions=[
            ("web/index.html", brut(
                ".puce.rate{color:var(--rouge);border-color:var(--rouge)}",
                ".puce.file{color:var(--encre-pale)}\n"
                ".puce.rate{color:var(--rouge);border-color:var(--rouge)}")),
        ]),
]

MUTATIONS = CONTENEUR + PAGE


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
    lignes_non = [l for l in sortie.splitlines() if l.startswith("  NON")]
    if any(mut["rougit"] in l for l in lignes_non):
        return "rouge", ""
    if code == 0:
        return "vert", "le banc n'a rien vu"
    if not lignes_non:
        return "casse", sortie.strip().splitlines()[-1][:120] if sortie.strip() else "sans sortie"
    return "casse", "rouge ailleurs : " + " / ".join(l[7:] for l in lignes_non)[:120]


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
