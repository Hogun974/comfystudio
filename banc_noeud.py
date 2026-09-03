# -*- coding: utf-8 -*-
"""La commande d'enrolement que le studio distribue met-elle vraiment une
machine en service ?

    python banc_noeud.py

RIEN N'EXERCAIT noeud.sh. La CI l'analysait par « sh -n » — de la syntaxe pure,
qui ne voit pas une fonction DEFINIE dans une branche NON PRISE — et aucun banc
ne le lancait. Le defaut que ce banc ouvre a survecu a cela :

    ecrire_reglages() etait definie a l'interieur du « if [ -z "$JETON" ] ».
    Avec --jeton, c'est-a-dire la commande exacte que /admin affiche et que
    docs/machines-a-agent.md recopie, la branche n'est pas prise, la fonction
    n'existe pas, « command not found » ne tue rien (ce script n'a pas de
    set -e), puis « exec "$PY" "$AGENT" » SANS configuration. L'agent sortait
    sur « Il manque l'adresse du studio ». Toute PREMIERE mise en service
    echouait ; une machine deja enrolee survivait parce que agent_noeud.json
    etait deja la, et c'est ce qui a cache le defaut.

Et un second, du meme lot : le script comptait ses « souci » et sortait en 1
des qu'il y en avait un, alors que trois d'entre eux sont declares benins DEUX
LIGNES PLUS BAS par le script lui-meme — « aucun Ollama : le studio le fera
ailleurs », « ComfyUI arrete : l'agent attendra qu'il reponde », « Ollama sans
modele ». Une machine a carte sans Ollama ne pouvait donc pas s'enroler, ce qui
est precisement le montage que le README recommande.

ON LE LANCE, ON NE LE LIT PAS. C'est le seul des trois choix qui aurait vu ces
deux defauts :

  - « sh -n » les rend verts tous les deux, c'est mesure : la CI les a laisses
    passer pendant toute leur vie ;
  - un banc STATIQUE qui relirait le texte du script y trouverait
    « ecrire_reglages » ecrite ET appelee, sans jamais voir qu'elle n'existe pas
    au moment de l'appel. C'est le reproche que banc_mutations.py fait aux bancs
    depuis le premier jour : la ligne peut etre la et ne rien atteindre ;
  - LE VRAI SCRIPT CONTRE UN FAUX MONDE, ci-dessous. Ce qui tourne est le
    fichier du depot, sans une ligne recopiee.

LES QUATRE PORTES DE noeud.sh SUR LE MONDE, et ce qu'on met a leur place :

  - « curl », pour tout : ComfyUI, Ollama, le studio, le telechargement de
    l'agent. Un faux curl, pose en tete de PATH, repond ce que le scenario dit
    et JOURNALISE chaque adresse appelee ;
  - « nvidia-smi », pour la carte. Un faux, sinon la machine qui lance le banc
    deciderait du verdict ;
  - le clavier, pour le jeton et pour « demarrer ComfyUI ? ». C'est l'entree
    standard du processus ;
  - « exec "$PY" "$AGENT" », la mise en service elle-meme. L'agent est remplace
    par un TEMOIN : un vrai fichier Python, servi par le faux studio, qui ecrit
    ce qu'il a trouve dans agent_noeud.json et ce qu'on lui a passe sur la ligne
    de commande.

CE TEMOIN EST LA PIECE MAITRESSE, et il n'est pas decoratif. Un cas qui
verifierait seulement « agent_noeud.json existe » serait vrai d'un script qui
ecrit sa configuration puis meurt avant de servir ; un cas qui verifierait
seulement le code de sortie serait vrai d'un script qui ne fait rien. Le temoin
n'existe que si le script est alle jusqu'au bout, et il porte ce que l'agent a
REELLEMENT lu au demarrage.

CE QU'IL NE VOIT PAS, et il faut l'ecrire :

  - noeud.bat et « LANCER ComfyStudio.bat ». cmd.exe n'existe pas sur les
    runners Ubuntu de la CI, et un cas qui ne tournerait que sur la machine de
    celui qui ecrit ne garde rien : il serait vert chez tout le monde sans avoir
    rien mesure. La derniere section releve donc, dans leur TEXTE, le seul
    couplage qui se mesure sans les lancer, et elle le dit. Le comportement
    qu'ils empruntent, lui, est exerce pour de vrai : installation.py
    python_du_studio() est appele en sous-processus, deux fois.
  - qu'un vrai ComfyUI demarre, qu'un vrai Ollama reponde, qu'une vraie carte
    soit la. On mesure ce que le script FAIT de ce qu'on lui repond.
  - noeud.sh sur un dash minimal. La CI garde cette moitie-la (« sh -n »), et ce
    banc lance bash, comme la documentation le dit.
  - le mode --fond au-dela de trois secondes : on regarde le temoin apres le
    « sleep 3 » du script, pas la vie du processus detache.
  - le second lancement d'une machine deja en service, celui que la boucle de
    l'agent fait toute seule : c'est banc_agent.py qui tient cette moitie.

SANS BASH, CE BANC NE MESURE RIEN, ET IL ROUGIT. C'est voulu : un banc vert qui
n'a rien lance est exactement ce que ce depot refuse. bash est present sur les
runners Ubuntu de la CI, et dans le Git for Windows de la machine de travail.

LES SCENARIOS D'UNE SECTION SONT LANCES ENSEMBLE, puis juges dans l'ordre.
Mesure : un lancement de noeud.sh coute 1,28 s sur cette machine (bash, six faux
curl, sept demarrages de Python) ; en file, les seize cas de la premiere version
ont mis 23 s, dont trois pour le seul « sleep 3 » de --fond. Les quinze
d'aujourd'hui, lances par section, en mettent 8,4. Or banc_mutations.py coupe un
banc a 90 s, et ce depot mesure un facteur QUATRE par la seule charge : 23 s en
file, c'etait une CI rouge sans defaut a la premiere machine occupee. Chaque bac
a sable est un dossier neuf, sans port ni fichier partage, et aucun cas ne
mesure une duree : les lancer de front ne les reordonne pas.
"""
import atexit
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

# La console Windows ecrit en cp1252 et ce banc n'importe pas serveur.py, qui
# est ce qui reconfigure la sortie pour le reste du depot. Sans ces lignes, il
# MEURT sur son propre affichage au premier « « ».
for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ICI = os.path.dirname(os.path.abspath(__file__))
ok, rate = [], []


def dit(vrai, quoi, detail=""):
    (ok if vrai else rate).append(quoi)
    print(f"  {'ok ' if vrai else 'NON'}  {quoi}{' — ' + detail if detail else ''}")


BASH = shutil.which("bash")
if not BASH:
    dit(False, "bash est disponible pour lancer noeud.sh",
        "introuvable : ce banc ne mesure RIEN, et il ne se declarera pas vert")
    print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees")
    sys.exit(1)


# ══════════════════════════ le faux monde ════════════════════════════
# UN FAUX curl, ET NON UN VRAI SERVEUR SUR 127.0.0.1. Le banc n'ouvre aucune
# socket : rien a liberer, aucun port a se disputer avec une autre instance ou
# avec le studio de la machine, et le scenario se lit dans l'environnement
# plutot que dans un fil de discussion. Le journal des adresses appelees sert de
# second temoin : il dit ce que le script est REELLEMENT alle chercher.
FAUX_CURL = r"""#!/bin/sh
# Le faux curl du banc. Il imite les seules options que noeud.sh et maj_noeud.sh
# emploient, et il sort en 22 comme le vrai « curl -f » devant une reponse
# d'erreur, sans ecrire le fichier de sortie.
url=""; sortie=""
while [ $# -gt 0 ]; do
  case "$1" in
    -o) sortie="$2"; shift 2 ;;
    --max-time) shift 2 ;;
    -*) shift ;;
    *) url="$1"; shift ;;
  esac
done
echo "$url" >> "$JOURNAL"
rendre() {
  if [ -n "$sortie" ]; then printf '%s' "$1" > "$sortie"; else printf '%s' "$1"; fi
}
case "$url" in
  */system_stats)
      [ "$FAUX_COMFY" = 1 ] || exit 22
      rendre '{"devices":[]}' ;;
  */models/diffusion_models)
      [ "$FAUX_COMFY" = 1 ] || exit 22
      rendre '["a.safetensors","b.safetensors"]' ;;
  */api/tags)
      case "$FAUX_OLLAMA" in
        modeles) rendre '{"models":[{"name":"qwen3:8b"}]}' ;;
        vide)    rendre '{"models":[]}' ;;
        *)       exit 22 ;;
      esac ;;
  */api/compte)
      [ "$FAUX_STUDIO" = 1 ] || exit 22
      rendre '{}' ;;
  */api/noeud/agent)
      [ "$FAUX_STUDIO" = 1 ] || exit 22
      [ -n "$FAUX_AGENT" ] || exit 22
      if [ -n "$sortie" ]; then cp "$FAUX_AGENT" "$sortie"; else cat "$FAUX_AGENT"; fi ;;
  *) exit 22 ;;
esac
exit 0
"""

FAUX_NVIDIA = r"""#!/bin/sh
# Une carte de 12 Go, toujours la meme : sans ce faux, le verdict du banc
# dependrait de la machine qui le lance.
case "$*" in
  *nounits*) echo "12288" ;;
  *) echo "NVIDIA GeForce RTX 3060, 12288 MiB" ;;
esac
"""

# LE PYTHON DU SCRIPT, ET POURQUOI IL PASSE PAR UN RELAIS SOUS WINDOWS.
# noeud.sh ecrit la reponse d'Ollama dans « /tmp/.ollama.$$ » puis la fait lire
# par Python. Sous Git for Windows, « /tmp » est un chemin que seul le shell
# sait traduire : le Python natif l'ouvrirait sous « C:\tmp », ne trouverait
# rien, et le banc mesurerait un defaut de la machine d'essai au lieu d'un
# defaut du script. Le relais retablit ce qu'un Linux fait naturellement, et ne
# s'interpose QUE la — partout ailleurs il transmet mot pour mot. Il fixe aussi
# QUEL interpreteur le script emploie : celui qui fait tourner ce banc.
RELAIS_PY = r"""#!/bin/sh
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*)
    natif=$(cygpath -m /tmp)
    for a in "$@"; do
      shift
      set -- "$@" "$(printf '%s' "$a" | sed "s#/tmp/#$natif/#g")"
    done ;;
esac
exec "$VRAI_PYTHON" "$@"
"""

# L'AGENT QUE LE FAUX STUDIO DISTRIBUE, et le temoin de tout ce banc : il
# n'existe de trace de lui QUE si le script est alle jusqu'a la mise en service.
AGENT_TEMOIN = '''# -*- coding: utf-8 -*-
"""Faux agent : il note ce qu'il a trouve, et rend la main."""
import io, json, os, sys

ici = os.path.dirname(os.path.abspath(__file__))
reglages = {}
chemin = os.path.join(ici, "agent_noeud.json")
if os.path.exists(chemin):
    with io.open(chemin, encoding="utf-8") as f:
        reglages = json.load(f)
with io.open(os.path.join(ici, "temoin.json"), "w", encoding="utf-8") as f:
    json.dump({"argv": sys.argv[1:], "reglages": reglages}, f)
'''

# Une page d'erreur de serveur mandataire : du HTML, pas du Python. ast.parse()
# doit la refuser — c'est la garde que SECURITY.md nomme sur ce chemin-la.
AGENT_ILLISIBLE = "<html><body><h1>502 Bad Gateway</h1></body></html>\n"

BACS = []
ANSI = re.compile("\x1b\\[[0-9;]*m")


class Essai:
    """Un lancement, DEMARRE des sa construction et attendu a la premiere
    lecture. C'est ce qui permet de lancer une section entiere de front sans
    deranger l'ordre dans lequel on la juge."""

    def __init__(self, processus, dossier, journal):
        self.processus = processus
        self.dossier = dossier
        self.chemin_journal = journal
        self._code = None
        self._sortie = ""

    def _attendre(self):
        if self._code is None:
            sortie, _ = self.processus.communicate(timeout=120)
            self._code = self.processus.returncode
            self._sortie = ANSI.sub("", sortie.decode("utf-8", "replace"))
        return self

    # EN PROPRIETE, ET NON EN ATTRIBUT. Ecrit en attribut, il valait None tant
    # que rien d'autre n'avait ete lu de cet essai — et « code != 0 » etait alors
    # vrai d'un scenario JAMAIS ATTENDU. Le cas « --verifier sort non nul » s'est
    # declare vert de cette facon-la, sans avoir rien mesure : l'assertion creuse
    # que ce banc reproche aux autres, commise dedans.
    @property
    def code(self):
        return self._attendre()._code

    @property
    def sortie(self):
        return self._attendre()._sortie

    def _lire(self, nom):
        self._attendre()
        chemin = os.path.join(self.dossier, nom)
        if not os.path.exists(chemin):
            return None
        try:
            with io.open(chemin, encoding="utf-8") as f:
                return json.load(f)
        except ValueError:
            return "illisible"

    @property
    def temoin(self):
        """Ce que l'agent a lu — None s'il n'a jamais ete lance."""
        return self._lire("temoin.json")

    def regle(self, nom):
        t = self.temoin
        return t.get("reglages", {}).get(nom) if isinstance(t, dict) else None

    @property
    def agent(self):
        self._attendre()
        chemin = os.path.join(self.dossier, "agent_noeud.py")
        if not os.path.exists(chemin):
            return None
        with io.open(chemin, encoding="utf-8") as f:
            return f.read()

    @property
    def journal(self):
        self._attendre()
        if not os.path.exists(self.chemin_journal):
            return []
        with io.open(self.chemin_journal, encoding="utf-8") as f:
            return [l.strip() for l in f if l.strip()]

    def remarque(self, bout):
        """Vrai si « bout » est dit en REMARQUE et non en point bloquant. Les
        deux se distinguent au marqueur qui ouvre la ligne."""
        return any(l.lstrip().startswith("!") and bout in l
                   for l in self.sortie.splitlines())

    def ligne(self, bout):
        return " / ".join(l.strip() for l in self.sortie.splitlines()
                          if bout in l)[:70]


def lancer(script="noeud.sh", args=(), entree="", comfy=True, ollama="modeles",
           studio=True, agent=AGENT_TEMOIN, reglages=None, deja=None):
    """Monte un bac a sable neuf, y DEMARRE le vrai script, rend l'Essai.

    « deja » pose des fichiers avant le lancement — un agent deja installe, par
    exemple, pour mesurer qu'on ne l'ecrase pas.
    """
    dossier = tempfile.mkdtemp(prefix="banc_noeud_")
    BACS.append(dossier)
    binaires = os.path.join(dossier, "bin")
    os.makedirs(binaires)
    for nom, contenu in (("curl", FAUX_CURL), ("nvidia-smi", FAUX_NVIDIA),
                         ("python3", RELAIS_PY)):
        chemin = os.path.join(binaires, nom)
        with io.open(chemin, "w", encoding="utf-8", newline="\n") as f:
            f.write(contenu)
        os.chmod(chemin, 0o755)
    for nom in ("noeud.sh", "maj_noeud.sh"):
        shutil.copyfile(os.path.join(ICI, nom), os.path.join(dossier, nom))
    if agent:
        with io.open(os.path.join(dossier, "agent.servi"), "w",
                     encoding="utf-8", newline="\n") as f:
            f.write(agent)
    if reglages is not None:
        with io.open(os.path.join(dossier, "agent_noeud.json"), "w",
                     encoding="utf-8") as f:
            json.dump(reglages, f)
    for nom, contenu in (deja or {}).items():
        with io.open(os.path.join(dossier, nom), "w", encoding="utf-8",
                     newline="\n") as f:
            f.write(contenu)

    # L'entree standard vient d'un FICHIER et non d'un tube : le script lit le
    # jeton au clavier, et un tube qu'on n'alimente qu'a la lecture du resultat
    # ferait attendre un scenario deja lance derriere un autre.
    chemin_entree = os.path.join(dossier, "au.clavier")
    with io.open(chemin_entree, "w", encoding="utf-8", newline="\n") as f:
        f.write(entree)

    journal = os.path.join(dossier, "journal")
    env = dict(os.environ)
    env.update(
        PATH=binaires + os.pathsep + env.get("PATH", ""),
        JOURNAL=journal,
        VRAI_PYTHON=sys.executable,
        FAUX_COMFY="1" if comfy else "0",
        FAUX_OLLAMA=ollama,
        FAUX_STUDIO="1" if studio else "0",
        FAUX_AGENT=os.path.join(dossier, "agent.servi") if agent else "",
        PYTHONIOENCODING="utf-8",
    )
    # Rien de la machine qui lance le banc ne doit entrer dans le scenario : il
    # est ici, et nulle part ailleurs.
    for parasite in ("COMFY_DIR", "COMFY_URL", "OLLAMA_URL", "AGENT_EMPREINTE",
                     "STUDIO_PYTHON"):
        env.pop(parasite, None)
    processus = subprocess.Popen(
        [BASH, script] + list(args), cwd=dossier, env=env,
        stdin=io.open(chemin_entree, "rb"), stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)
    return Essai(processus, dossier, journal)


@atexit.register
def _ranger():
    for dossier in BACS:
        shutil.rmtree(dossier, ignore_errors=True)


_depart = time.time()

# ══════════════════ 1. l'enrolement que /admin distribue ═════════════
# web/admin.html affiche, pour chaque machine creee :
#     bash noeud.sh --studio ${adresse} --jeton ${jeton}
# C'est cette ligne-la, et pas une autre, qu'on joue ici.
print("\nL'enrolement, tel que le studio le distribue")
print("-" * 44)

# « sorties_partagees » et non « /mnt/sorties » : Git for Windows reecrit les
# arguments qui ressemblent a un chemin absolu POSIX, et le banc aurait mesure
# cette traduction-la plutot que le script.
_e = lancer(args=["--studio", "http://192.0.2.10:8199", "--jeton", "JETON-SECRET",
                  "--comfy", "http://127.0.0.1:8188",
                  "--ollama", "http://192.0.2.11:11434",
                  "--sorties", "sorties_partagees"])
# LE JUMEAU, ET IL EST INDISPENSABLE : le jeton tape au clavier est le chemin
# qui MARCHAIT — ecrire_reglages() etait definie dans cette branche-la — et
# c'est pour cela que le defaut a tenu si longtemps.
_clavier = lancer(args=["--studio", "http://192.0.2.10:8199"],
                  entree="JETON-TAPE\n")
# --fond : l'autre site d'appel de ecrire_reglages(), celui qu'un correctif
# distrait laisserait derriere lui.
_fond = lancer(args=["--studio", "http://192.0.2.10:8199", "--jeton", "J2",
                     "--fond"])
# Le second lancement, celui ou l'on ne repasse plus rien : tout se relit dans
# le fichier. C'est ce qui faisait survivre les machines deja enrolees.
_repris = lancer(reglages={"studio": "http://192.0.2.10:8199", "jeton": "J3",
                           "comfy": "http://127.0.0.1:8188"}, ollama="vide")

dit(_e.temoin is not None,
    "l'enrolement avec --jeton va jusqu'a lancer l'agent",
    f"code {_e.code}, temoin {'ecrit' if _e.temoin else 'ABSENT'}")
dit(_e.regle("jeton") == "JETON-SECRET",
    "et l'agent trouve le jeton dans agent_noeud.json quand il demarre",
    f"{(_e.temoin or {}).get('reglages')}")
dit(_e.regle("studio") == "http://192.0.2.10:8199",
    "l'adresse du studio y est aussi : sans elle l'agent sort aussitot",
    f"{_e.regle('studio')!r}")
dit(_e.regle("ollama") == "http://192.0.2.11:11434",
    "--ollama est retenu, sinon la machine ne prete son cerveau qu'une fois",
    f"{_e.regle('ollama')!r}")
dit(_e.regle("sorties") == "sorties_partagees",
    "--sorties aussi, pour le menage des rendus",
    f"{_e.regle('sorties')!r}")
# LE JETON N'EST PAS UN ARGUMENT. Le commentaire de noeud.sh le dit en toutes
# lettres : « la ligne de commande d'un processus est lisible par tout le monde
# sur la machine, ce qui annulait le masquage de la saisie ». Le temoin
# rapporte ce qu'il a recu : la liste doit etre vide.
dit(isinstance(_e.temoin, dict) and _e.temoin["argv"] == [],
    "le jeton ne passe jamais par la ligne de commande de l'agent",
    f"{(_e.temoin or {}).get('argv')}")
dit(_e.code == 0, "et la mise en service se termine sans erreur", f"code {_e.code}")

dit(_clavier.regle("jeton") == "JETON-TAPE",
    "le jeton tape au clavier mene lui aussi a une machine en service",
    f"{_clavier.regle('jeton')!r}")
dit(_fond.regle("jeton") == "J2",
    "--fond enregistre les memes reglages avant de detacher l'agent",
    f"{(_fond.temoin or {}).get('reglages')}")
dit(_repris.regle("jeton") == "J3",
    "un second lancement sans argument reprend studio et jeton du fichier",
    f"code {_repris.code}")


# ══════════════════ 2. consultatif contre bloquant ═══════════════════
# Le script comptait tous ses « souci » et sortait en 1 des qu'il y en avait un,
# y compris pour des cas qu'il declare benins deux lignes plus bas. Une machine
# a carte sans Ollama — le montage que le README recommande, studio sur le NAS,
# cartes ailleurs — ne pouvait donc pas s'enroler.
print("\nCe qui empeche de se mettre en service, et ce qui ne l'empeche pas")
print("-" * 66)

_sans_ollama = lancer(args=["--studio", "http://192.0.2.10:8199", "--jeton", "J"],
                      ollama="absent")
_sans_comfy = lancer(args=["--studio", "http://192.0.2.10:8199", "--jeton", "J"],
                     comfy=False)
# L'INVERSE, ET IL COMPTE AUTANT : un script qui ne refuserait plus rien
# passerait les cas ci-dessus sans rien mesurer.
_muet = lancer(args=["--studio", "http://192.0.2.10:8199", "--jeton", "J"],
               studio=False)
_sans_agent = lancer(args=["--studio", "http://192.0.2.10:8199", "--jeton", "J"],
                     agent=None)
# L'EMPREINTE EPINGLEE. SECURITY.md nomme ce chemin — du code Python telecharge
# en HTTP simple puis execute — comme la surface la plus sensible du depot. Une
# empreinte qui ne repond pas de l'agent ne doit RIEN remplacer, et ne doit pas
# mettre la machine en service.
_ancien = "# l'agent d'hier\n"
_faux_sceau = lancer(args=["--studio", "http://192.0.2.10:8199", "--jeton", "J",
                           "--empreinte", "0" * 64],
                     deja={"agent_noeud.py": _ancien})
_vraie = hashlib.sha256(AGENT_TEMOIN.encode("utf-8")).hexdigest()
_bon_sceau = lancer(args=["--studio", "http://192.0.2.10:8199", "--jeton", "J",
                          "--empreinte", _vraie.upper()])
_html = lancer(args=["--studio", "http://192.0.2.10:8199", "--jeton", "J"],
               agent=AGENT_ILLISIBLE, deja={"agent_noeud.py": _ancien})

dit(_sans_ollama.temoin is not None,
    "une machine a carte SANS Ollama s'enrole quand meme",
    f"code {_sans_ollama.code}, temoin "
    f"{'ecrit' if _sans_ollama.temoin else 'ABSENT'}")
dit(_sans_ollama.remarque("aucun Ollama"),
    "et l'absence d'Ollama est dite en remarque, pas en point a regler",
    _sans_ollama.ligne("Ollama"))
dit(_repris.temoin is not None and _repris.remarque("aucun modele"),
    "un Ollama sans modele ne bloque pas l'enrolement non plus",
    f"code {_repris.code}")
dit(_sans_comfy.temoin is not None and _sans_comfy.remarque("ComfyUI introuvable"),
    "un ComfyUI absent non plus : l'agent attendra qu'il reponde",
    f"code {_sans_comfy.code}")

dit(_muet.temoin is None and _muet.code != 0,
    "un studio injoignable, lui, arrete tout avant de lancer l'agent",
    f"code {_muet.code}, temoin {'ECRIT' if _muet.temoin else 'absent'}")
dit(not _muet.remarque("studio injoignable"),
    "et il est compte comme un point a regler, jamais comme une remarque",
    _muet.ligne("studio injoignable"))
dit(_sans_agent.temoin is None and _sans_agent.code != 0,
    "un agent ni present ni telechargeable arrete tout",
    f"code {_sans_agent.code}")
dit(_faux_sceau.temoin is None and _faux_sceau.code != 0,
    "une empreinte inattendue arrete tout",
    f"code {_faux_sceau.code}")
dit(_faux_sceau.agent == _ancien,
    "et l'agent deja installe n'est pas remplace",
    f"{(_faux_sceau.agent or '')[:30]!r}")
dit(_bon_sceau.temoin is not None,
    "l'empreinte attendue, elle, laisse passer — meme ecrite en majuscules",
    f"code {_bon_sceau.code}")
dit(_html.agent == _ancien and _html.temoin is None,
    "une page d'erreur du studio n'ecrase pas l'agent qui fonctionnait",
    f"code {_html.code}")


# ══════════════════ 3. le diagnostic --verifier ══════════════════════
print("\nLe diagnostic")
print("-" * 13)

_v = lancer(args=["--verifier", "--studio", "http://192.0.2.10:8199"],
            ollama="absent", comfy=False)
_vm = lancer(args=["--verifier", "--studio", "http://192.0.2.10:8199"],
             studio=False)

dit(_v.temoin is None, "--verifier ne lance jamais l'agent",
    f"temoin {'ECRIT' if _v.temoin else 'absent'}")
dit(_v.code == 0, "--verifier sort en 0 quand il ne reste que des remarques",
    f"code {_v.code}")
dit(_v.remarque("aucun Ollama") and _v.remarque("ComfyUI introuvable"),
    "et il les dit toutes, sans en faire des points a regler")
dit(_vm.code != 0, "--verifier sort non nul des qu'un point bloquant reste",
    f"code {_vm.code}")


# ══════════════════ 4. maj_noeud.sh ══════════════════════════════════
# Le meme jeton, le meme reproche : maj_noeud.sh le passait sur la ligne de
# commande de l'agent, ce que noeud.sh interdit explicitement.
print("\nLa mise a jour d'un parc")
print("-" * 23)

_m = lancer(script="maj_noeud.sh",
            args=["http://192.0.2.10:8199", "JETON-DU-PARC"])
_m2 = lancer(script="maj_noeud.sh", args=["http://192.0.2.10:8199"])

dit(isinstance(_m.temoin, dict), "maj_noeud.sh installe l'agent et le lance",
    f"code {_m.code}, temoin {'ecrit' if _m.temoin else 'ABSENT'}")
dit(isinstance(_m.temoin, dict) and _m.temoin["argv"] == [],
    "sans passer le jeton sur la ligne de commande, comme noeud.sh l'exige",
    f"{(_m.temoin or {}).get('argv')}")
dit(_m.regle("jeton") == "JETON-DU-PARC"
    and _m.regle("studio") == "http://192.0.2.10:8199",
    "le jeton et le studio passent par agent_noeud.json",
    f"{(_m.temoin or {}).get('reglages')}")
dit(_m2.temoin is None and _m2.code == 0 and _m2.agent == AGENT_TEMOIN,
    "sans jeton, elle met a jour l'agent et ne demarre rien",
    f"code {_m2.code}")


# ══════════════════ 5. le lanceur Windows ════════════════════════════
# « LANCER ComfyStudio.bat » codait en dur
# « ..\ComfyUI_windows_portable\python_embeded\python.exe » et sortait en 1
# sinon. Or installation.py accepte HUIT emplacements et installer_comfyui()
# clone dans ../ComfyUI avec un venv : suivre le README a la lettre sous Windows
# echouait. La resolution existait deja dans le depot — python_du_studio() — et
# c'est elle qu'on branche, plutot que d'en ecrire une seconde qui deriverait.
#
# LA MOITIE QUI TOURNE POUR DE VRAI est ci-dessous : le sous-processus est
# lance, sa sortie est lue, et l'interpreteur qu'il nomme doit exister.
# LA MOITIE QUI EST UN RELEVE DE TEXTE vient apres, et elle est annoncee comme
# telle : cmd.exe n'est pas sur les runners Ubuntu de la CI.
print("\nQuel Python fera tourner le studio")
print("-" * 33)


def demander_le_python(**variables):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    env.pop("STUDIO_PYTHON", None)
    env.update(variables)
    fini = subprocess.run([sys.executable, os.path.join(ICI, "installer.py"),
                           "--python-du-studio"], cwd=ICI, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          timeout=120)
    return (fini.returncode, fini.stdout.decode("utf-8", "replace").strip(),
            fini.stderr.decode("utf-8", "replace").strip())


_code, _chemin, _raison = demander_le_python()
dit(_code == 0 and len(_chemin.splitlines()) == 1 and os.path.exists(_chemin),
    "l'installeur sait dire quel interpreteur fera tourner le studio",
    f"code {_code}, « {_chemin} »")
dit(_raison != "",
    "et il dit sur quelle piste, pour qu'on puisse le contredire", _raison[:60])

# UN CHEMIN QUI N'EXISTE PAS, ET C'EST EXPRES. On mesure ici que la variable
# L'EMPORTE, pas qu'elle designe quelque chose de valide — _chemin_reel() rend
# le chemin tel quel quand il ne peut pas le lancer. Avec un interpreteur REEL,
# le cas se serait confondu avec le repli « celui qui execute cet installeur »
# partout ou les deux coincident, c'est-a-dire sur la CI Ubuntu : la panne
# « STUDIO_PYTHON est ignoree » y serait passee inapercue, et la mutation qui la
# joue serait restee verte sur la moitie des machines.
_impose_voulu = os.path.join(tempfile.gettempdir(), "interpreteur_impose_par_le_banc")
_code, _impose, _raison = demander_le_python(STUDIO_PYTHON=_impose_voulu)
dit(_code == 0 and _impose == _impose_voulu and "STUDIO_PYTHON" in _raison,
    "STUDIO_PYTHON l'emporte : le lanceur sait, il n'a pas a deduire",
    f"« {_impose} » — {_raison}")

# RELEVE DE TEXTE, ET RIEN DE PLUS — voir l'en-tete. Ce qu'on exige : que les
# deux .bat ne s'arretent plus au seul chemin en dur, et qu'ils aillent poser la
# question la ou la reponse est deja ecrite. On cherche l'APPEL et non le seul
# nom de l'option, qu'un commentaire suffirait a poser.
for _bat in ("LANCER ComfyStudio.bat",
             os.path.join("paquet", "construire_windows.bat")):
    with io.open(os.path.join(ICI, _bat), encoding="utf-8", errors="replace") as f:
        _texte = f.read()
    dit(re.search(r'installer\.py"?\s+--python-du-studio', _texte) is not None,
        f"{os.path.basename(_bat)} demande l'interpreteur a l'installeur "
        f"au lieu de le coder en dur",
        "releve de texte : cmd.exe n'est pas sur les runners de la CI")

print(f"\n  {len(ok)} verifications passees, {len(rate)} echouees "
      f"— {time.time() - _depart:.1f} s")
sys.exit(1 if rate else 0)
