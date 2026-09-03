#!/usr/bin/env bash
# Installe ou met a jour l'agent sur une machine-noeud (Linux, macOS).
#
# L'agent est servi par le studio lui-meme : mettre a jour un parc de machines
# revient a relancer ce script sur chacune, sans depot a cloner ni fichier a
# recopier a la main.
#
#   ./maj_noeud.sh http://192.0.2.10:8199            met a jour l agent
#   ./maj_noeud.sh http://192.0.2.10:8199 JETON      installe puis demarre
#   ./maj_noeud.sh http://192.0.2.10:8199 JETON EMPREINTE
#
# Ce script telecharge du code Python et l'execute. En HTTP simple, quiconque
# s'intercale sur le reseau — ARP, DNS, un Wi-Fi partage — choisit le code qui
# tournera sur cette machine. Le troisieme argument, ou AGENT_EMPREINTE, est le
# sha256 attendu de l'agent : il n'est utile que s'il a ete releve AILLEURS que
# sur ce meme lien HTTP, par exemple par « sha256sum agent_noeud.py » sur l'hote
# du studio, en SSH. L'empreinte installee est de toute façon affichee.
set -euo pipefail
cd "$(dirname "$0")"

STUDIO="${1:-}"
JETON="${2:-}"
EMPREINTE="${3:-${AGENT_EMPREINTE:-}}"
AGENT="agent_noeud.py"

if [ -z "$STUDIO" ] && [ -f agent_noeud.json ]; then
  STUDIO=$(python3 -c "import json;print(json.load(open('agent_noeud.json')).get('studio',''))" 2>/dev/null || true)
fi
if [ -z "$STUDIO" ]; then
  echo "  Adresse du studio manquante :"
  echo "    ./maj_noeud.sh http://192.0.2.10:8199 [JETON]"
  exit 1
fi
STUDIO="${STUDIO%/}"

# On ESSAIE chaque candidat, et on exige Python 3.8 : sous macOS « python »
# est souvent le 2.7 du systeme, qui demarre parfaitement puis echoue sur la
# premiere f-string avec un SyntaxError incomprehensible. Verifier que Python
# repond ne suffit donc pas : il faut verifier sa VERSION.
PY=""
for py in python3 python3.13 python3.12 python3.11 python3.10 python3.9 python py; do
  if command -v "$py" >/dev/null 2>&1      && "$py" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' 2>/dev/null; then
    PY="$py"
    break
  fi
done
if [ -z "$PY" ]; then
  echo "  Aucun Python 3.8 ou plus recent trouve. Installe-le :"
  echo "    macOS            brew install python"
  echo "                     ou xcode-select --install"
  echo "    Debian, Ubuntu   sudo apt install python3 python3-venv"
  echo "    Fedora           sudo dnf install python3"
  echo "    Arch             sudo pacman -S python"
  exit 1
fi

echo "  telechargement de l'agent depuis $STUDIO"
if command -v curl >/dev/null 2>&1; then
  curl -fsS "$STUDIO/api/noeud/agent" -o "$AGENT.neuf"
elif command -v wget >/dev/null 2>&1; then
  wget -q "$STUDIO/api/noeud/agent" -O "$AGENT.neuf"
else
  echo "  ni curl ni wget — installe l'un des deux"
  exit 1
fi

# On ne remplace qu'apres avoir verifie que le fichier est du Python valide :
# une reponse d'erreur du studio ecraserait sinon un agent qui marchait. Le
# meme appel rend l'empreinte et sort en 2 si elle n'est pas celle attendue.
VERIF="import ast,hashlib,sys
o=open(sys.argv[1],'rb').read()
ast.parse(o.decode('utf-8'))
e=hashlib.sha256(o).hexdigest()
print(e)
attendue=(sys.argv[2] if len(sys.argv)>2 else '').strip().lower()
sys.exit(2 if attendue and attendue!=e else 0)"
EMP=$("$PY" -c "$VERIF" "$AGENT.neuf" "$EMPREINTE" 2>/dev/null) && RC=0 || RC=$?
if [ "$RC" = 2 ]; then
  echo "  EMPREINTE INATTENDUE — rien n'a ete remplace"
  echo "    recue   : $EMP"
  echo "    attendue: $EMPREINTE"
  rm -f "$AGENT.neuf"
  exit 1
elif [ "$RC" != 0 ]; then
  echo "  ce que le studio a renvoye n'est pas un script valide — rien n'a ete remplace"
  rm -f "$AGENT.neuf"
  exit 1
fi
# En « if » et non en « && » : sous « set -e », un test qui echoue termine le
# script. Or il echoue exactement au cas qui compte, la PREMIERE installation,
# ou aucun agent n'est encore la — juste avant le « mv » qui l'installe. On
# voyait l'empreinte s'afficher, aucune erreur, un code de sortie 1, et pas
# d'agent.
if [ -f "$AGENT" ]; then cp "$AGENT" "$AGENT.precedent"; fi
mv "$AGENT.neuf" "$AGENT"
chmod +x "$AGENT"
echo "  agent a jour — sha256 $EMP"

if [ -n "$JETON" ]; then
  # LE JETON PASSE PAR LE FICHIER DE REGLAGES, ET NON PAR LA LIGNE DE COMMANDE
  # DE L'AGENT. noeud.sh l'interdit en toutes lettres — « celle d'un processus
  # est lisible par tout le monde sur la machine, ce qui annulait le masquage de
  # la saisie » — et ce script-ci la contredisait. La difference n'est pas de
  # principe : l'argument passe a CE script-ci ne vit que le temps du
  # telechargement, celui de l'agent reste lisible dans « ps » tant que la
  # machine sert, c'est-a-dire des semaines. Un jeton de noeud vaut droit de
  # faire travailler sa carte.
  "$PY" - agent_noeud.json "$STUDIO" "$JETON" <<'PYFIN'
import io, json, os, sys
p, studio, jeton = sys.argv[1:4]
c = json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else {}
c.update(studio=studio, jeton=jeton)
json.dump(c, io.open(p, "w", encoding="utf-8"), indent=1)
PYFIN
  exec "$PY" "$AGENT"
fi
echo
echo "  Pour le mettre en service :"
echo "    ./maj_noeud.sh $STUDIO TON_JETON"
echo "  (le jeton se cree dans $STUDIO/admin ; il est ecrit dans"
echo "   agent_noeud.json, jamais sur la ligne de commande de l'agent)"
