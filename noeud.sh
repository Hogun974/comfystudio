#!/usr/bin/env bash
# Met une machine au service d'un ComfyStudio, d'un seul geste.
#
# Verifie ce qu'il faut, demarre ComfyUI s'il dort, recupere l'agent aupres du
# studio, demande le jeton, et se met en service. Concu pour etre le seul
# fichier a poser sur une machine-noeud :
#
#   curl -fsS http://LE-STUDIO:8199/api/noeud/noeud.sh -o noeud.sh
#   bash noeud.sh
#
#   bash noeud.sh --verifier                    diagnostic, sans rien lancer
#   bash noeud.sh --studio URL --jeton XXXX     sans aucune question
#   bash noeud.sh --fond                        laisse tourner en tache de fond
#   bash noeud.sh --empreinte SHA256            n'installe que cet agent-la
#   bash noeud.sh --ollama URL                  ou joindre le modele de langage
#
# Ce script telecharge du code Python et l'execute. En HTTP simple, quiconque
# s'intercale sur le reseau choisit ce code. --empreinte (ou AGENT_EMPREINTE)
# n'aide que si le sha256 a ete releve AILLEURS que sur ce meme lien : par
# « sha256sum agent_noeud.py » sur l'hote du studio, en SSH.
set -uo pipefail
cd "$(dirname "$0")"

STUDIO=""; JETON=""; VERIFIER=0; FOND=0
EMPREINTE="${AGENT_EMPREINTE:-}"
COMFY_URL="${COMFY_URL:-http://127.0.0.1:8188}"
OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
CONFIG="agent_noeud.json"
AGENT="agent_noeud.py"

while [ $# -gt 0 ]; do
  case "$1" in
    --studio)   STUDIO="${2:-}"; shift 2 ;;
    --jeton)    JETON="${2:-}"; shift 2 ;;
    --sorties)  SORTIES="${2:-}"; shift 2 ;;
    --comfy)    COMFY_URL="${2:-}"; shift 2 ;;
    --ollama)   OLLAMA_URL="${2:-}"; shift 2 ;;
    --verifier) VERIFIER=1; shift ;;
    --fond)     FOND=1; shift ;;
    --empreinte) EMPREINTE="${2:-}"; shift 2 ;;
    -h|--help)  sed -n '2,21p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)          echo "  argument inconnu : $1"; exit 1 ;;
  esac
done

vert()  { printf '  \033[32m✓\033[0m %s\n' "$1"; }
rouge() { printf '  \033[31m✗\033[0m %s\n' "$1"; }
jaune() { printf '  \033[33m!\033[0m %s\n' "$1"; }
gris()  { printf '    \033[2m%s\033[0m\n' "$1"; }
titre() { printf '\n%s\n%s\n' "$1" "$(printf '%*s' ${#1} '' | tr ' ' '-')"; }

# DEUX COMPTEURS, ET NON UN. Tout ce qui suit comptait un seul « ENNUIS » et
# sortait en 1 des qu'il valait plus de zero — y compris pour des cas que ce
# script declare benins DEUX LIGNES PLUS BAS : « aucun Ollama : le studio le
# fera ailleurs », « ComfyUI arrete : l'agent attendra qu'il reponde », « Ollama
# sans modele ». Une machine a carte sans Ollama ne pouvait donc pas s'enroler,
# c'est-a-dire exactement le montage que le README recommande — studio sur le
# NAS, cartes ailleurs — et cela contredisait son encadre « le studio produit
# meme sans modele de langage ».
#
# LA LIGNE DE PARTAGE : est bloquant ce qui empeche l'agent de DEMARRER ou de
# S'ENROLER (pas de Python, pas d'adresse de studio, pas d'agent, un agent dont
# l'empreinte ne repond pas de lui) ; est consultatif tout ce que l'agent
# rattrapera en service — un ComfyUI qui n'est pas encore la, un modele de
# langage qui manque. Ce n'est pas un garde-fou qu'on retire : chaque remarque
# est toujours dite, et --verifier les compte a part.
ENNUIS=0
REMARQUES=0
souci()    { rouge "$1"; ENNUIS=$((ENNUIS + 1)); }
remarque() { jaune "$1"; REMARQUES=$((REMARQUES + 1)); }

# ══════════════════════════ 1. Python ══════════════════════════════════
titre "Python"
# On verifie la VERSION, pas seulement la presence : un Python 2 demarre
# parfaitement puis echoue sur la premiere f-string de l'agent.
PY=""
for py in python3 python3.13 python3.12 python3.11 python3.10 python3.9 python; do
  if command -v "$py" >/dev/null 2>&1 &&
     "$py" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' 2>/dev/null; then
    PY="$py"; break
  fi
done
if [ -z "$PY" ]; then
  souci "aucun Python 3.8 ou plus recent"
  gris "Debian, Ubuntu   sudo apt install python3"
  gris "Fedora           sudo dnf install python3"
  gris "Arch             sudo pacman -S python"
  exit 1
fi
vert "$($PY -V 2>&1) — $(command -v "$PY")"

# ══════════════════════════ 2. carte et memoire ════════════════════════
# Le modele de langage a conseiller, d'apres la carte. On ne prend jamais plus
# gros que la carte en esperant le debordement : Ollama y arrive, mais une
# analyse de trois minutes devant chaque rendu ne sert personne — mesure sur une
# 2080 Ti, un modele de 26 milliards a mis 165 s a rendre son premier mot.
modele_conseille() {
  go=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null        | head -1 | awk '{printf "%.0f", $1/1024}')
  if   [ "${go:-0}" -ge 20 ] 2>/dev/null; then echo "gemma3:27b"
  elif [ "${go:-0}" -ge 11 ] 2>/dev/null; then echo "gemma3:12b"
  elif [ "${go:-0}" -ge  6 ] 2>/dev/null; then echo "qwen3:8b"
  else echo "qwen3:4b"
  fi
}

titre "Materiel"
if command -v nvidia-smi >/dev/null 2>&1; then
  CARTE=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null | head -1)
  # Consultatif : une machine sans carte rend quand meme service — lentement,
  # sur son processeur — et c'est a celui qui l'enrole d'en decider, pas a ce
  # script de le lui refuser.
  [ -n "$CARTE" ] && vert "carte : $CARTE" || remarque "nvidia-smi ne rend aucune carte"
else
  remarque "nvidia-smi introuvable : pas de carte NVIDIA utilisable"
  gris "ComfyUI tournera sur le processeur, tres lentement"
fi
if [ -r /proc/meminfo ]; then
  RAM=$(awk '/MemTotal/ {printf "%.0f", $2/1048576}' /proc/meminfo)
  vert "memoire : ${RAM} Go"
  [ "$RAM" -lt 16 ] 2>/dev/null && gris "moins de 16 Go : les modeles lourds seront a la peine"
elif command -v sysctl >/dev/null 2>&1; then
  vert "memoire : $(( $(sysctl -n hw.memsize) / 1073741824 )) Go"
fi
LIBRE=$(df -Pk . 2>/dev/null | awk 'NR==2 {printf "%.0f", $4/1048576}')
[ -n "$LIBRE" ] && vert "disque : ${LIBRE} Go libres ici"

# ══════════════════════════ 3. ComfyUI ═════════════════════════════════
titre "ComfyUI"
joignable() { curl -fsS --max-time 4 "$COMFY_URL/system_stats" >/dev/null 2>&1; }

if joignable; then
  vert "deja en service sur $COMFY_URL"
else
  RACINE="${COMFY_DIR:-}"
  if [ -z "$RACINE" ]; then
    for c in ./ComfyUI ../ComfyUI "$HOME/ComfyUI" /opt/ComfyUI /srv/ComfyUI; do
      [ -f "$c/main.py" ] && RACINE="$c" && break
    done
  fi
  if [ -z "$RACINE" ]; then
    # Consultatif, comme « ComfyUI arrete » plus bas et pour la meme raison :
    # l'agent attendra qu'il reponde. COMFY_URL peut d'ailleurs designer une
    # autre machine, auquel cas il n'y a rien a trouver ici.
    remarque "ComfyUI introuvable"
    gris "indique-le par COMFY_DIR=/chemin/vers/ComfyUI, ou installe-le"
  else
    # le Python de son environnement dedie, sinon celui du systeme
    PYC="$PY"
    for v in "$RACINE/venv/bin/python" "$RACINE/.venv/bin/python"; do
      [ -x "$v" ] && PYC="$v" && break
    done
    echo "  ComfyUI trouve dans $RACINE"
    if [ "$VERIFIER" = 1 ]; then
      remarque "il ne repond pas (mode verification : on ne le demarre pas)"
    else
      printf '  Le demarrer maintenant ? [O/n] '
      read -r rep || rep=""
      case "${rep:-o}" in
        [nN]*) remarque "ComfyUI arrete : l'agent attendra qu'il reponde" ;;
        *)
          # --disable-auto-launch : pas de navigateur qui s'ouvre sur un serveur
          nohup "$PYC" "$RACINE/main.py" --disable-auto-launch \
                > comfyui.log 2>&1 &
          echo "  demarrage (journal : $(pwd)/comfyui.log)"
          for _ in $(seq 1 60); do
            joignable && break
            sleep 2
          done
          if joignable; then
            vert "ComfyUI repond sur $COMFY_URL"
          else
            # Consultatif : le journal est ecrit, l'agent attendra, et une
            # machine dont le ComfyUI met trois minutes a s'ouvrir n'a pas a
            # etre refusee au parc pour autant.
            remarque "ComfyUI n'a pas repondu en deux minutes — regarde comfyui.log"
          fi ;;
      esac
    fi
  fi
fi

if joignable; then
  MOD=$(curl -fsS --max-time 6 "$COMFY_URL/models/diffusion_models" 2>/dev/null |
        "$PY" -c "import json,sys;print(len(json.load(sys.stdin)))" 2>/dev/null)
  gris "modeles de diffusion vus : ${MOD:-0}"
fi

# ══════════════════════ 3 bis. le modele de langage ════════════════════
# Le studio emprunte le modele de langage de CETTE machine pour analyser une
# demande. Depuis qu'une carte ne fait qu'une tache a la fois, en avoir un ici
# change la donne : la petite carte reflechit pendant que la grosse rend. Sans
# Ollama sur aucune machine sauf une, toutes les analyses passent par elle et
# elle devient le goulot.
titre "Modele de langage"
if curl -fsS --max-time 5 "$OLLAMA_URL/api/tags" -o /tmp/.ollama.$$ 2>/dev/null; then
  NBM=$("$PY" -c "import json;print(len(json.load(open('/tmp/.ollama.$$')).get('models',[])))" 2>/dev/null)
  rm -f /tmp/.ollama.$$
  if [ "${NBM:-0}" -gt 0 ] 2>/dev/null; then
    vert "Ollama repond sur $OLLAMA_URL — ${NBM} modele(s)"
  else
    remarque "Ollama repond mais n'a aucun modele"
    gris "  ollama pull $(modele_conseille)"
  fi
else
  # Consultatif, et la ligne suivante le dit deja : « le studio le fera
  # ailleurs ». C'est le montage que le README recommande.
  remarque "aucun Ollama sur $OLLAMA_URL"
  gris "cette machine ne pourra pas analyser : le studio le fera ailleurs"
  gris "pour l'installer :  curl -fsSL https://ollama.com/install.sh | sh"
  gris "puis :              ollama pull $(modele_conseille)"
fi

# ══════════════════════════ 4. le studio ═══════════════════════════════
titre "Studio"
if [ -z "$STUDIO" ] && [ -f "$CONFIG" ]; then
  STUDIO=$("$PY" -c "import json;print(json.load(open('$CONFIG')).get('studio',''))" 2>/dev/null)
  [ -n "$STUDIO" ] && gris "adresse retenue du dernier lancement"
fi
if [ -z "$STUDIO" ] && [ "$VERIFIER" = 0 ]; then
  printf '  Adresse du studio (ex : http://192.0.2.10:8199) : '
  read -r STUDIO || STUDIO=""
fi
STUDIO="${STUDIO%/}"
if [ -z "$STUDIO" ]; then
  souci "aucune adresse de studio"
elif curl -fsS --max-time 6 "$STUDIO/api/compte" >/dev/null 2>&1; then
  vert "studio joignable sur $STUDIO"
else
  souci "studio injoignable sur $STUDIO"
  gris "verifie qu'il tourne avec STUDIO_HOTE=0.0.0.0, et le pare-feu"
fi

# ══════════════════════════ 5. l'agent ═════════════════════════════════
titre "Agent"
if [ -n "$STUDIO" ] && curl -fsS --max-time 20 "$STUDIO/api/noeud/agent" -o "$AGENT.neuf" 2>/dev/null; then
  # On ne remplace qu'apres verification : une page d'erreur du studio
  # ecraserait sinon un agent qui fonctionnait. Le meme appel rend l'empreinte
  # du fichier recu et sort en 2 si elle n'est pas celle qu'on attendait.
  VERIF="import ast,hashlib,sys
o=open(sys.argv[1],'rb').read()
ast.parse(o.decode('utf-8'))
e=hashlib.sha256(o).hexdigest()
print(e)
attendue=(sys.argv[2] if len(sys.argv)>2 else '').strip().lower()
sys.exit(2 if attendue and attendue!=e else 0)"
  EMP=$("$PY" -c "$VERIF" "$AGENT.neuf" "$EMPREINTE" 2>/dev/null) && RC=0 || RC=$?
  if [ "$RC" = 0 ]; then
    [ -f "$AGENT" ] && cp "$AGENT" "$AGENT.precedent"
    mv "$AGENT.neuf" "$AGENT"
    vert "agent a jour ($(wc -c < "$AGENT") octets, sha256 $EMP)"
  elif [ "$RC" = 2 ]; then
    rm -f "$AGENT.neuf"
    souci "empreinte inattendue : $EMP au lieu de $EMPREINTE — rien remplace"
  else
    rm -f "$AGENT.neuf"
    souci "ce que le studio a renvoye n'est pas un script valide"
  fi
elif [ -f "$AGENT" ]; then
  rm -f "$AGENT.neuf"
  gris "telechargement impossible — on garde l'agent deja present"
else
  rm -f "$AGENT.neuf"
  souci "agent absent et non telechargeable"
fi

if [ -z "$JETON" ] && [ -f "$CONFIG" ]; then
  JETON=$("$PY" -c "import json;print(json.load(open('$CONFIG')).get('jeton',''))" 2>/dev/null)
  [ -n "$JETON" ] && vert "jeton retenu du dernier lancement"
fi

# ══════════════════════════ 6. verdict ═════════════════════════════════
# Les remarques sont dites, jamais comptees dans le code de sortie : celui de
# --verifier est le nombre de points BLOQUANTS, pour qu'un script d'installation
# de parc puisse s'y fier. Un « 0 » qui voulait dire « rien a signaler » aurait
# pousse a taire les remarques pour l'obtenir.
dire_les_remarques() {
  [ "$REMARQUES" -gt 0 ] &&
    gris "$REMARQUES remarque(s) ci-dessus : l'agent s'en accommode en service"
}
if [ "$VERIFIER" = 1 ]; then
  titre "Verdict"
  dire_les_remarques
  [ "$ENNUIS" = 0 ] && vert "tout est pret" || rouge "$ENNUIS point(s) a regler"
  exit "$ENNUIS"
fi
if [ "$ENNUIS" -gt 0 ]; then
  titre "Verdict"
  dire_les_remarques
  rouge "$ENNUIS point(s) a regler avant de se mettre en service"
  exit 1
fi

# DEFINIE ICI, AU PREMIER NIVEAU, et non dans le « if » du jeton ou elle etait.
# Avec --jeton — la commande exacte que /admin affiche et que
# docs/machines-a-agent.md recopie — cette branche-la n'est pas prise : la
# fonction n'existait pas au moment des deux appels ci-dessous, « command not
# found » ne tue rien (ce script n'a pas de set -e), et « exec "$PY" "$AGENT" »
# demarrait l'agent SANS configuration. Il sortait sur « Il manque l'adresse du
# studio », a tous les coups. Toute PREMIERE mise en service echouait ; une
# machine deja enrolee survivait parce que agent_noeud.json etait deja la, et
# c'est ce qui a cache le defaut.
#
# Le jeton passe par ce fichier de reglages, jamais par la ligne de commande :
# celle d'un processus est lisible par tout le monde sur la machine, ce qui
# annulait le masquage de la saisie.
ecrire_reglages() {
  # L'adresse d'Ollama est retenue comme les autres : sans elle, une machine qui
  # a bien un modele de langage ne le pretait pas au studio des le second
  # lancement, celui ou l'on ne repasse plus d'arguments.
  "$PY" - "$CONFIG" "$STUDIO" "$JETON" "$COMFY_URL" "${SORTIES:-}" "$OLLAMA_URL" <<'PYFIN'
import json, io, os, sys
p, studio, jeton, comfy, sorties, ollama = sys.argv[1:7]
c = json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else {}
c.update(studio=studio, jeton=jeton, comfy=comfy)
if sorties:
    c["sorties"] = sorties
if ollama:
    c["ollama"] = ollama
json.dump(c, io.open(p, "w", encoding="utf-8"), indent=1)
PYFIN
}

if [ -z "$JETON" ]; then
  titre "Jeton"
  echo "  Il se cree dans $STUDIO/admin, sur la machine du studio."
  echo "  Il n'est affiche qu'une seule fois, a la creation de la machine."
  printf '  Jeton : '
  # -s : le jeton ne s'affiche pas a l'ecran, et ne reste pas dans l'historique
  read -r -s JETON || JETON=""
  echo
  [ -z "$JETON" ] && { rouge "aucun jeton — rien a faire"; exit 1; }
fi

dire_les_remarques
titre "En service"
if [ "$FOND" = 1 ]; then
  ecrire_reglages
  nohup "$PY" "$AGENT" \
        > agent.log 2>&1 &
  sleep 3
  vert "agent lance en tache de fond (journal : $(pwd)/agent.log)"
  gris "pour l'arreter : pkill -f $AGENT"
else
  ecrire_reglages
exec "$PY" "$AGENT"
fi
