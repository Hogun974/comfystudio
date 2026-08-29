#!/usr/bin/env bash
# Lanceur macOS et Linux de l'installeur. Il ne fait que trouver un Python
# convenable : toute la logique est dans installer.py, commune aux deux systemes.
set -euo pipefail
cd "$(dirname "$0")"

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

# Le studio sera lance avec CE Python-la (« python3 serveur.py », ou l'unite
# systemd que pose service/installer_service.sh). C'est donc dans celui-ci, et
# nulle part ailleurs, qu'il faut poser aiohttp : installer dans un autre
# interpreteur donne un « Successfully installed » suivi, au demarrage, d'un
# ImportError sur le meme paquet — deux messages qui se contredisent sans que
# rien n'explique pourquoi.
#
# On transmet le chemin ABSOLU : « python3 » nu resterait a la merci du PATH de
# celui qui appelle. La verification et l'installation, elles, restent dans
# installation.py, commun aux trois systemes : les recopier ici aurait garanti
# qu'elles divergent, ce que ce lanceur evite deja pour le reste.
if [ -z "${STUDIO_PYTHON:-}" ]; then
  STUDIO_PYTHON=$(command -v "$PY" 2>/dev/null || printf '%s' "$PY")
fi
export STUDIO_PYTHON

exec "$PY" installer.py "$@"
