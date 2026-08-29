#!/usr/bin/env bash
# Installe ou met a jour l'agent sur une machine-noeud (Linux, macOS).
#
# L'agent est servi par le studio lui-meme : mettre a jour un parc de machines
# revient a relancer ce script sur chacune, sans depot a cloner ni fichier a
# recopier a la main.
#
#   ./maj_noeud.sh http://192.0.2.10:8199            met a jour l agent
#   ./maj_noeud.sh http://192.0.2.10:8199 JETON      installe puis demarre
set -euo pipefail
cd "$(dirname "$0")"

STUDIO="${1:-}"
JETON="${2:-}"
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
# une reponse d'erreur du studio ecraserait sinon un agent qui marchait.
if ! "$PY" -c "import ast,sys;ast.parse(open(sys.argv[1],encoding='utf-8').read())" "$AGENT.neuf"; then
  echo "  ce que le studio a renvoye n'est pas un script valide — rien n'a ete remplace"
  rm -f "$AGENT.neuf"
  exit 1
fi
[ -f "$AGENT" ] && cp "$AGENT" "$AGENT.precedent"
mv "$AGENT.neuf" "$AGENT"
chmod +x "$AGENT"
echo "  agent a jour"

if [ -n "$JETON" ]; then
  exec "$PY" "$AGENT" --studio "$STUDIO" --jeton "$JETON"
fi
echo
echo "  Pour le demarrer :"
echo "    $PY $AGENT --studio $STUDIO --jeton TON_JETON"
echo "  (le jeton se cree dans $STUDIO/admin)"
