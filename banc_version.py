# -*- coding: utf-8 -*-
"""Le studio sait-il dire ce qu'il est, sans jamais l'inventer ?

    python banc_version.py

Le studio n'avait aucune notion de version : rien dans la banniere, rien dans
/admin, et `.github/ISSUE_TEMPLATE` demandait pourtant « Version du studio
(commit, ou date) ». Impossible a remplir pour qui a installe par executable ou
par conteneur — DEUX chemins d'installation sur quatre.

Ce banc garde la reponse, et il en garde surtout la moitie facile a perdre :
QUAND ON NE SAIT PAS, ON LE DIT. Un identifiant invente — une date de fichier,
un « 1.0 », une chaine vide affichee comme si c'etait une valeur — est pire que
« inconnue », parce que personne ne peut savoir qu'il est faux. Il remplirait un
rapport de bogue avec quelque chose qui ne designe aucun code.

Ce que chaque chemin peut REELLEMENT offrir, mesure le 4 septembre 2026 :

    clone            git rev-parse --short HEAD -> bd9fc88 en 0,017 s
    conteneur        .git est dans .dockerignore : rien a lire dans l'image,
                     il faut graver la valeur a la construction (ARG VERSION)
    executable       ICI pointe sur le _MEIxxx temporaire de PyInstaller et
                     DONNEES ne liste pas .git : meme conclusion, la spec grave
    aucun des trois  « inconnue », ecrit en toutes lettres

Trois pieges, et chacun a son cas ici :

  - GIT REMONTE LES DOSSIERS PARENTS. Depuis
    D:\\ComfyStudio\\paquet\\build\\essai_version, qui n'est pas un depot,
    « git rev-parse --short HEAD » rend bd9fc88 — le commit du depot du dessus.
    Un studio pose dans un sous-dossier d'un AUTRE depot annoncerait donc le
    commit de cet autre depot. Le garde-fou est « .git dans CE dossier », teste
    ici en interdisant carrement l'appel a git.
  - UNE VALEUR VIDE N'EST PAS UNE VALEUR. « ARG VERSION= » sans argument grave
    un fichier qui ne porte qu'un retour a la ligne ; l'accepter ferait dire
    « Version : » suivi de rien, ce qui se lit comme une panne d'affichage et
    non comme une ignorance. C'est l'assertion creuse que ce depot traque :
    « l'identifiant est affiche » est vraie d'un studio qui affiche « ».
  - L'EXE NE DOIT PAS LIRE LE DEPOT OU IL EST POSE. construire_windows.bat
    recommande de poser l'exe dans D:\\ComfyStudio, qui EST un clone : mesure du
    meme jour, l'executable construit le 30 aout a 15 h 22 y annoncerait le
    commit du jour, 187 commits plus loin. D'ou ICI et non ICI_DATA.

CE BANC EST NE AVEC SA CORRECTION : il n'y a pas de filet d'avant. Le sens
inverse se prend donc par l'autre chemin — le banc NEUF lance sur le code
d'AVANT — et pour que cela mesure quelque chose, il faut qu'il ROUGISSE au lieu
de MOURIR la-bas. Toutes les sections sont donc gardees : la fonction est
cherchee par getattr, les fichiers sont ouverts sous try, et chaque absence pose
un cas nomme au lieu d'une trace de pile. Un banc qui meurt sur le code d'avant
ne mesure pas le sens inverse.

MESURE DU SENS INVERSE, 4 septembre 2026 : serveur.py, web/admin.html, le
Dockerfile, la spec, construire_windows.bat et le modele d'issue repris au
commit d'avant, ce banc y rend « 0 verifications passees, 19 echouees ». Les
dix-neuf lignes rouges sont exactement les dix-neuf que les mutations nomment,
et il ne meurt sur aucune. Le detail est dans docs/eprouver-les-bancs.md.
"""
import ast
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

ICI = os.path.dirname(os.path.abspath(__file__))
ok, rate = [], []


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


def lire(nom):
    return io.open(os.path.join(ICI, *nom.split("/")), encoding="utf-8").read()


def peut_lire(nom):
    """Le texte du fichier, ou None. Ouvrir sous try est ce qui rend le sens
    inverse mesurable : un fichier absent pose un cas ROUGE et n'emporte pas
    les autres avec lui."""
    try:
        return lire(nom)
    except OSError:
        return None


import serveur  # noqa: E402 — apres les utilitaires, comme les autres bancs

# ── Ce qu'on va eprouver, cherche et non suppose ──────────────────────
# getattr et non un import direct : sur le code d'AVANT la fonction n'existe
# pas, et l'on veut une ligne rouge par regle, pas une ImportError qui emporte
# le banc entier.
version_du_studio = getattr(serveur, "version_du_studio", None)
version_annoncee = getattr(serveur, "version_annoncee", None)
NOM_GRAVE = getattr(serveur, "FICHIER_VERSION", "")
INCONNUE = getattr(serveur, "VERSION_INCONNUE", "")
LONGUEUR_MAX = getattr(serveur, "VERSION_MAX", 0)

# LE PLANCHER. Sans lui, tout ce qui suit serait vrai de rien : un serveur sans
# aucune de ces quatre pieces rendrait chaque comparaison vide, donc vraie.
dit(bool(version_du_studio and version_annoncee and NOM_GRAVE and INCONNUE
         and LONGUEUR_MAX),
    "le studio a de quoi dire ce qu'il est",
    f"{NOM_GRAVE or 'pas de fichier grave'}, "
    f"« {INCONNUE or 'pas de mot pour l ignorance'} », "
    f"{LONGUEUR_MAX} caracteres au plus")


class Espion:
    """Un faux subprocess.run qui NOTE ce qu'on lui demande.

    Il sert deux fois, et dans les deux sens : pour verifier que git EST
    interroge sur le bon dossier, et pour verifier qu'il ne l'est PAS du tout
    quand le dossier n'est pas un clone. Le second est le vrai sujet — c'est le
    piege du depot parent, et on ne peut pas le mesurer en regardant seulement
    la valeur rendue, puisqu'un depot parent rendrait un sha parfaitement
    credible.
    """

    def __init__(self, sortie=b"", code=0, refuse=False):
        self.sortie, self.code, self.refuse = sortie, code, refuse
        self.appels = []

    def __call__(self, argv, **_):
        self.appels.append(list(argv))
        if self.refuse:
            raise FileNotFoundError("git")

        class _Fini:
            pass
        f = _Fini()
        f.returncode, f.stdout = self.code, self.sortie
        return f


def demander(dossier, sortie=b"", code=0, refuse=False):
    """version_du_studio(dossier) avec git remplace par un espion.

    Rend (identifiant, source, espion). subprocess.run est remis en place quoi
    qu'il arrive : le banc en a besoin pour lui-meme.
    """
    espion = Espion(sortie, code, refuse)
    vrai = subprocess.run
    subprocess.run = espion
    try:
        valeur, source = version_du_studio(dossier)
    finally:
        subprocess.run = vrai
    return valeur, source, espion


# ──────────────────────────────────────────────────────────────────────
#  1. Ce que la fonction rend, source par source
# ──────────────────────────────────────────────────────────────────────
bac = tempfile.mkdtemp(prefix="banc_version_")
try:
    if not version_du_studio:
        for quoi in ("aucune source ne repond : le studio dit « inconnue »",
                     "et il ne rend JAMAIS une chaine vide",
                     "un identifiant vide est refuse, d'ou qu'il vienne",
                     "un identifiant demesure est refuse, et la limite tient",
                     "un identifiant grave normal repond, et se nomme",
                     "git n'est pas interroge hors d'un clone",
                     "dans un clone, git est interroge sur CE dossier",
                     "et le depot passe AVANT le fichier grave"):
            dit(False, quoi, "version_du_studio() n'existe pas")
    else:
        # ── Rien du tout ────────────────────────────────────────────
        vide = os.path.join(bac, "rien")
        os.makedirs(vide)
        v, s, esp = demander(vide)
        dit(v == INCONNUE and s == "aucune source",
            "aucune source ne repond : le studio dit « inconnue »",
            f"rend « {v} » ({s})")
        # LE TEMOIN CONTRE L'ASSERTION CREUSE. « l'identifiant est affiche »
        # est vraie d'un studio qui affiche « » : on exige donc, ici et une
        # fois pour toutes, que la valeur rendue ne soit jamais vide. Les
        # couplages de la banniere et de /admin s'appuient sur celle-ci.
        dit(bool(v) and bool(v.strip()),
            "et il ne rend JAMAIS une chaine vide",
            f"{len(v)} caractere(s)")

        # ── Le fichier grave, dans ses trois etats ──────────────────
        def grave(contenu):
            d = tempfile.mkdtemp(dir=bac)
            with io.open(os.path.join(d, NOM_GRAVE or "version.txt"), "w",
                         encoding="utf-8", newline="\n") as f:
                f.write(contenu)
            return d

        # « ARG VERSION= » sans argument : printf grave un retour a la ligne
        # seul. C'est le cas REEL du conteneur construit sans passer
        # l'argument, pas une curiosite.
        #
        # ET LES DEUX SOURCES SONT JUGEES PAR LA MEME PORTE. On eprouve donc
        # aussi un git qui rend une ligne vide : deux refus ecrits a deux
        # endroits se couvriraient l'un l'autre, et l'on ne pourrait plus voir
        # rougir ni l'un ni l'autre.
        v, s, _ = demander(grave("\n"))
        blancs, _, _ = demander(grave("   \t \n"))
        depot_vide = tempfile.mkdtemp(dir=bac)
        os.makedirs(os.path.join(depot_vide, ".git"))
        v_git, s_git, _ = demander(depot_vide, sortie=b"\n")
        dit(v == INCONNUE and blancs == INCONNUE and v_git == INCONNUE,
            "un identifiant vide est refuse, d'ou qu'il vienne",
            f"grave -> « {v} » ({s}), blancs -> « {blancs} », "
            f"git muet -> « {v_git} » ({s_git})")

        # Un fichier tombe la par accident n'est pas un identifiant. On refuse
        # plutot que de tronquer : un identifiant tronque se recopierait dans
        # une issue et ne designerait rien.
        v3, _, _ = demander(grave("z" * (LONGUEUR_MAX + 1) + "\n"))
        limite, _, _ = demander(grave("z" * LONGUEUR_MAX + "\n"))
        dit(v3 == INCONNUE and limite == "z" * LONGUEUR_MAX,
            "un identifiant demesure est refuse, et la limite tient",
            f"{LONGUEUR_MAX + 1} caracteres -> « {v3} », "
            f"{LONGUEUR_MAX} -> {'accepte' if limite != INCONNUE else 'REFUSE'}")

        # LE PLANCHER DES TROIS CAS DU DESSUS. Sans lui, une fonction qui dirait
        # « inconnue » a tout coup les passerait tous les trois.
        v4, s4, esp4 = demander(grave("a1b2c3d\n"))
        dit(v4 == "a1b2c3d" and s4 == "gravee a la construction",
            "un identifiant grave normal repond, et se nomme",
            f"« {v4} » ({s4})")

        # ── Le piege du depot parent ────────────────────────────────
        # On n'interroge pas la VALEUR : un depot parent rendrait un sha
        # parfaitement credible, et le cas passerait. On interroge l'APPEL.
        sans_git = grave("a1b2c3d\n")
        v5, s5, esp5 = demander(sans_git, sortie=b"parent1\n", refuse=False)
        dit(not esp5.appels and v5 == "a1b2c3d",
            "git n'est pas interroge hors d'un clone",
            f"{len(esp5.appels)} appel(s) a git — rend « {v5} » ({s5})")

        # ── Et dans un vrai clone ───────────────────────────────────
        clone = grave("zzzzzzz\n")
        os.makedirs(os.path.join(clone, ".git"))
        v6, s6, esp6 = demander(clone, sortie=b"a1b2c3d\n")
        vise_ce_dossier = bool(esp6.appels) and "-C" in esp6.appels[0] and \
            clone in esp6.appels[0]
        dit(vise_ce_dossier,
            "dans un clone, git est interroge sur CE dossier",
            " ".join(esp6.appels[0][:4]) if esp6.appels else "aucun appel")
        # L'ORDRE, et c'est une regle a part : un fichier grave par une
        # construction passee ne doit pas primer sur le depot, qui lui ne se
        # perime pas. Le dossier porte les DEUX, et le git doit gagner.
        dit(v6 == "a1b2c3d" and s6 == "depot git",
            "et le depot passe AVANT le fichier grave",
            f"« {v6} » ({s6}) alors que le fichier dit « zzzzzzz »")
finally:
    shutil.rmtree(bac, ignore_errors=True)

# ── La valeur annoncee ne bouge pas en cours de route ─────────────────
# Un « git pull » pendant que le studio tourne change .git sans changer une
# ligne du code DEJA CHARGE. Relire a chaque appel ferait annoncer un commit
# que ce studio-ci ne fait pas tourner : la mise en cache n'est pas une
# optimisation, c'est la seule reponse juste.
if not version_annoncee:
    dit(False, "l'identifiant annonce est fige pour la duree du processus",
        "version_annoncee() n'existe pas")
else:
    tours = []
    vraie = serveur.version_du_studio
    memoire = getattr(serveur, "_VERSION_ANNONCEE", None)
    try:
        serveur.version_du_studio = lambda *a, **k: (tours.append(1)
                                                     or ("t%d" % len(tours), "essai"))
        if memoire is not None:
            del memoire[:]
        premier = serveur.version_annoncee()
        second = serveur.version_annoncee()
    finally:
        serveur.version_du_studio = vraie
        if memoire is not None:
            del memoire[:]
    dit(len(tours) == 1 and premier == second,
        "l'identifiant annonce est fige pour la duree du processus",
        f"{len(tours)} calcul(s), {premier} puis {second}")

# ──────────────────────────────────────────────────────────────────────
#  2. La banniere le dit
# ──────────────────────────────────────────────────────────────────────
# Par l'arbre de syntaxe et non par un motif de texte : ce qui compte n'est pas
# qu'un « Version » traine dans le fichier, c'est que le bloc de demarrage
# imprime les DEUX moities de ce que version_annoncee() rend. Un banc qui
# cherche un mot mesure le mot.
SRV = peut_lire("serveur.py")
if SRV is None:
    dit(False, "la banniere de demarrage annonce l'identifiant ET sa source",
        "serveur.py illisible")
else:
    arbre = ast.parse(SRV)
    bloc_demarrage = []
    for n in arbre.body:
        if (isinstance(n, ast.If) and isinstance(n.test, ast.Compare)
                and isinstance(n.test.left, ast.Name)
                and n.test.left.id == "__name__"):
            bloc_demarrage = n.body
    noms_version = []
    for n in bloc_demarrage:
        if (isinstance(n, ast.Assign) and isinstance(n.value, ast.Call)
                and isinstance(n.value.func, ast.Name)
                and n.value.func.id == "version_annoncee"
                and isinstance(n.targets[0], ast.Tuple)):
            noms_version = [c.id for c in n.targets[0].elts
                            if isinstance(c, ast.Name)]
    imprimes = set()
    for n in bloc_demarrage:
        for f in ast.walk(n):
            if (isinstance(f, ast.Call) and isinstance(f.func, ast.Name)
                    and f.func.id == "print"):
                for morceau in ast.walk(f):
                    if isinstance(morceau, ast.Name):
                        imprimes.add(morceau.id)
    dit(len(noms_version) == 2 and set(noms_version) <= imprimes,
        "la banniere de demarrage annonce l'identifiant ET sa source",
        (", ".join(noms_version) + " imprimes") if noms_version
        else "aucun appel a version_annoncee() dans le bloc de demarrage")

    # ── /admin, cote serveur ────────────────────────────────────────
    # Les DEUX clefs, et leur valeur doit venir de version_annoncee() : une
    # chaine ecrite en dur passerait un releve de noms, et annoncerait une
    # version qui ne bouge plus jamais.
    clefs_route = {}
    for n in ast.walk(arbre):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and \
                n.name == "api_admin_noeuds":
            for d in ast.walk(n):
                if isinstance(d, ast.Dict):
                    for cle, val in zip(d.keys, d.values):
                        if isinstance(cle, ast.Constant) and \
                                isinstance(cle.value, str):
                            clefs_route[cle.value] = any(
                                isinstance(x, ast.Name)
                                and x.id == "version_annoncee"
                                for x in ast.walk(val))
    attendues = {"version", "version_source"}
    servies = {c for c in attendues if clefs_route.get(c)}
    dit(servies == attendues,
        "/api/admin/noeuds rend l'identifiant et sa source, calcules",
        ", ".join(sorted(attendues - servies)) + " manquante(s) ou ecrite(s) "
        "en dur" if servies != attendues else "les deux, par version_annoncee()")

# ──────────────────────────────────────────────────────────────────────
#  3. /admin le montre — l'autre moitie du contrat
# ──────────────────────────────────────────────────────────────────────
# La moitie que ce depot a deja perdue trois fois : le serveur rend une clef,
# la page en lit une autre, les deux cotes sont verts et l'ecran est vide.
PAGE = peut_lire("web/admin.html")
if PAGE is None:
    dit(False, "la page /admin lit ces memes clefs, et a ou les poser",
        "web/admin.html illisible")
else:
    lues_par_la_page = set(re.findall(r'\bd\.(version(?:_source)?)\b', PAGE))
    a_le_cadre = bool(re.search(r'id="version"', PAGE))
    dit(lues_par_la_page == {"version", "version_source"} and a_le_cadre,
        "la page /admin lit ces memes clefs, et a ou les poser",
        f"{', '.join(sorted(lues_par_la_page)) or 'aucune clef'}"
        f"{'' if a_le_cadre else ' — et aucun element id=version'}")
    # ET ELLE N'AFFICHE PAS UNE CHAINE VIDE. Le serveur ecrit « inconnue » de
    # lui-meme, mais un studio plus ancien ne rendrait pas la clef du tout :
    # sans repli, la page poserait « version  () » et cela se lirait comme une
    # panne. C'est la meme assertion creuse, un fichier plus loin.
    dit(bool(re.search(r'd\.version\s*\|\|', PAGE))
        and bool(re.search(r'd\.version_source\s*\|\|', PAGE)),
        "et elle ne pose jamais un identifiant vide",
        "les deux clefs ont un repli ecrit"
        if re.search(r'd\.version\s*\|\|', PAGE) else "aucun repli")

# ──────────────────────────────────────────────────────────────────────
#  4. Les deux empaquetages gravent le MEME fichier
# ──────────────────────────────────────────────────────────────────────
# On ne compare a aucune liste ecrite ici : le nom vient de serveur.py, qui est
# le seul a le LIRE. Une seconde ecriture du meme fait diverge — c'est la faute
# que ce depot a payee quatre fois en deux jours.
DOCKER = peut_lire("Dockerfile")
if DOCKER is None or not NOM_GRAVE:
    dit(False, "le conteneur grave l'identifiant dans le fichier que le studio lit",
        "Dockerfile illisible" if DOCKER is None else "serveur.py ne nomme aucun fichier")
else:
    a_argument = bool(re.search(r'^ARG\s+VERSION', DOCKER, re.M))
    ecrit_dedans = bool(re.search(r'>\s*\S*' + re.escape(NOM_GRAVE), DOCKER))
    dit(a_argument and ecrit_dedans,
        "le conteneur grave l'identifiant dans le fichier que le studio lit",
        f"ARG VERSION {'present' if a_argument else 'ABSENT'}, "
        f"{NOM_GRAVE} {'ecrit' if ecrit_dedans else 'JAMAIS ecrit'}")

SPEC = peut_lire("paquet/comfystudio.spec")
if SPEC is None or not NOM_GRAVE:
    dit(False, "et l'executable embarque le meme, calcule a la construction",
        "spec illisible" if SPEC is None else "serveur.py ne nomme aucun fichier")
else:
    # « DONNEES.append(( » et non « DONNEES.append » : la spec appelle deja
    # DONNEES.append(_f(...)) dans deux boucles, et le releve du nom seul
    # serait vrai d'une spec qui n'embarque plus rien de neuf. C'est la forme a
    # DEUX parentheses — un couple (chemin, destination) ecrit a la main —
    # qui est propre au fichier grave, puisqu'il ne peut pas passer par _f() :
    # il n'existe pas encore quand la spec commence.
    embarque = NOM_GRAVE in SPEC and bool(re.search(r'DONNEES\.append\(\(', SPEC))
    calcule = "rev-parse" in SPEC
    dit(embarque and calcule,
        "et l'executable embarque le meme, calcule a la construction",
        f"{NOM_GRAVE} {'embarque' if embarque else 'ABSENT de DONNEES'}, "
        f"git {'interroge' if calcule else 'JAMAIS interroge'}")

BAT = peut_lire("paquet/construire_windows.bat")
if BAT is None or not NOM_GRAVE:
    dit(False, "et la construction Windows dit ce qu'elle a grave",
        "construire_windows.bat illisible" if BAT is None
        else "serveur.py ne nomme aucun fichier")
else:
    # Le .bat RELIT le fichier grave plutot que de relancer git : ce qui est
    # dans l'exe, et non ce que le depot vaut a la seconde ou l'on regarde.
    relit = NOM_GRAVE in BAT
    annonce = bool(re.search(r'(?im)^\s*echo\s+version\s+gravee', BAT))
    dit(relit and annonce,
        "et la construction Windows dit ce qu'elle a grave",
        f"{NOM_GRAVE} {'relu' if relit else 'jamais relu'}, "
        f"annonce {'faite' if annonce else 'ABSENTE'}")

# ──────────────────────────────────────────────────────────────────────
#  5. Le modele d'issue, qui est la raison de tout ceci
# ──────────────────────────────────────────────────────────────────────
BOGUE = peut_lire(".github/ISSUE_TEMPLATE/bogue.md")
if BOGUE is None:
    for quoi in ("le modele d'issue ne demande plus une valeur introuvable",
                 "et il dit ou la lire, pour les quatre installations"):
        dit(False, quoi, "bogue.md illisible")
else:
    # « commit, ou date » : un clone peut donner le premier, personne ne peut
    # donner le second de facon utile, et deux chemins sur quatre ne pouvaient
    # donner ni l'un ni l'autre. C'est la question qu'on a supprimee.
    dit("commit, ou date" not in BOGUE,
        "le modele d'issue ne demande plus une valeur introuvable",
        "la question est repondable" if "commit, ou date" not in BOGUE
        else "il demande encore « (commit, ou date) »")
    # LES DEUX ENDROITS, et le mot exact de la banniere. Nommer /admin sans
    # nommer la banniere laisserait sans reponse celui qui n'a pas le jeton
    # d'administration ; nommer la banniere seule laisserait sans reponse celui
    # qui a referme sa console.
    dit("/admin" in BOGUE and re.search(r'(?i)banni[eè]re', BOGUE)
        and "Version" in BOGUE,
        "et il dit ou la lire, pour les quatre installations",
        ("la banniere et /admin" if "/admin" in BOGUE
         else "il ne nomme pas /admin"))

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
for r in rate:
    print("    a regarder :", r)
sys.exit(1 if rate else 0)
