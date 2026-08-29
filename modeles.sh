#!/usr/bin/env bash
# Telecharge sur cette machine les modeles que sa carte peut tenir.
#
# Une seule commande depuis une machine-noeud :
#
#   curl -fsS http://LE-STUDIO:8199/api/noeud/modeles.sh | bash -s -- http://LE-STUDIO:8199
#
# Options, apres l'adresse du studio :
#   --dossier CHEMIN   ou deposer les modeles (defaut : deduit de ComfyUI)
#   --liste A,B        ne prendre que ces moteurs
#   --voir             dire ce qui serait pris, sans rien telecharger
#
# Le studio n'ecrit que sur son propre disque : c'est donc ici, sur la machine
# qui va calculer, qu'il faut lancer ceci.
set -uo pipefail

STUDIO="${1:-}"
shift || true
DOSSIER=""
LISTE=""
VOIR=0
while [ $# -gt 0 ]; do
  case "$1" in
    --dossier) DOSSIER="${2:-}"; shift 2 ;;
    --liste)   LISTE="${2:-}"; shift 2 ;;
    --voir)    VOIR=1; shift ;;
    *)         echo "  argument inconnu : $1"; exit 1 ;;
  esac
done

if [ -z "$STUDIO" ]; then
  echo "  Adresse du studio manquante :"
  echo "    curl -fsS http://LE-STUDIO:8199/api/noeud/modeles.sh | bash -s -- http://LE-STUDIO:8199"
  exit 1
fi
STUDIO="${STUDIO%/}"

# On exige Python 3.8 : un Python 2 demarre puis echoue sur la premiere
# f-string, avec un message qui n'apprend rien.
PY=""
for py in python3 python3.13 python3.12 python3.11 python3.10 python3.9 python; do
  if command -v "$py" >/dev/null 2>&1 &&
     "$py" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' 2>/dev/null; then
    PY="$py"; break
  fi
done
[ -z "$PY" ] && { echo "  aucun Python 3.8 ou plus recent"; exit 1; }

# Ou vont les modeles. Dans l'ordre : ce qui est demande, la variable d'un
# conteneur, un ComfyUI conteneurise sur cette machine, une installation locale.
if [ -z "$DOSSIER" ]; then
  DOSSIER="${COMFY_MODELES:-}"
fi
if [ -z "$DOSSIER" ]; then
  for c in /DATA/AppData/comfyui/models "$HOME/ComfyUI/models" /opt/ComfyUI/models \
           ./ComfyUI/models ../ComfyUI/models; do
    [ -d "$c" ] && DOSSIER="$c" && break
  done
fi
if [ -z "$DOSSIER" ]; then
  echo "  Impossible de deviner ou deposer les modeles."
  echo "  Indique-le : --dossier /chemin/vers/ComfyUI/models"
  exit 1
fi
mkdir -p "$DOSSIER" || { echo "  $DOSSIER n'est pas inscriptible"; exit 1; }

TRAVAIL=$(mktemp -d)
trap 'rm -rf "$TRAVAIL"' EXIT
echo "  studio   : $STUDIO"
echo "  modeles  : $DOSSIER"
echo "  recuperation des scripts"
for f in catalogue.py installation.py installer.py; do
  curl -fsS --max-time 30 "$STUDIO/api/noeud/$f" -o "$TRAVAIL/$f" || {
    echo "  $f introuvable sur le studio"; exit 1; }
done

# COMFY_MODELES pointe l'installeur sur le bon dossier ; COMFY_DIR evite qu'il
# aille chercher une installation de ComfyUI qui n'existe pas ici.
export COMFY_MODELES="$DOSSIER"
export COMFY_DIR="${COMFY_DIR:-$(dirname "$DOSSIER")}"

cd "$TRAVAIL"
if [ "$VOIR" = 1 ]; then
  exec "$PY" installer.py --materiel
fi
if [ -z "$LISTE" ]; then
  # « --tout » installerait aussi ComfyUI et Ollama, ce qui n'a pas de sens ici :
  # on demande donc a l'installeur ce que cette carte peut tenir, et on ne
  # telecharge que cela.
  LISTE=$("$PY" -c "
import installation as i
vram, ram, _ = i.diagnostic()
t, d, _ = i.moteurs_possibles(vram, ram)
print(','.join(t + d))
" 2>/dev/null | tail -1)
fi
if [ -z "$LISTE" ]; then
  echo
  echo "  Aucun moteur ne tient sur cette machine."
  exit 1
fi
echo "  a telecharger : $LISTE"
exec "$PY" installer.py --modeles "$LISTE" --oui
