#!/bin/sh
# Installe ComfyStudio en tant que service, sur Linux (systemd) ou macOS
# (launchd). A executer depuis n'importe ou :
#
#   sudo sh service/installer_service.sh              Linux
#   sh service/installer_service.sh                   macOS (SANS sudo)
#   sh service/installer_service.sh --desinstaller
#
# Ecrit en sh POSIX et non en bash : sur Alpine, sur une Debian minimale et dans
# la plupart des conteneurs, /bin/bash n'existe pas, et le script destine a
# reparer l'installation serait le premier a ne pas demarrer.
set -eu

# ══════════════════════════ reglages par defaut ══════════════════════════
NOM_SERVICE="comfystudio"
ETIQUETTE="com.comfystudio"
UTILISATEUR=""
RACINE=""
DONNEES=""
PYTHON=""
HOTE="127.0.0.1"
PORT="8199"
AUTH="obligatoire"
COMFY_URL="http://127.0.0.1:8188"
OLLAMA_URL="http://127.0.0.1:11434"
FICHIER_ENV="/etc/comfystudio.env"
DESINSTALLER=0
IGNORER_AIOHTTP=0

# ══════════════════════════ affichage ══════════════════════════
vert()  { printf '  \033[32mok\033[0m   %s\n' "$1"; }
rouge() { printf '  \033[31mNON\033[0m  %s\n' "$1" >&2; }
jaune() { printf '  \033[33m!\033[0m    %s\n' "$1" >&2; }
gris()  { printf '       \033[2m%s\033[0m\n' "$1"; }
titre() { printf '\n%s\n' "$1"; printf '%s\n' "------------------------------------------------------------"; }
mourir() { rouge "$1"; shift; for l in "$@"; do gris "$l"; done; exit 1; }

aide() {
  sed -n '2,7p' "$0" | sed 's/^# \{0,1\}//'
  cat <<'FIN'

  --utilisateur NOM   compte non privilegie qui fera tourner le studio
                      (Linux : comfystudio, cree si absent ; macOS : toi)
  --racine CHEMIN     dossier contenant serveur.py (par defaut : le dossier
                      parent de ce script)
  --donnees CHEMIN    STUDIO_DONNEES (conversations, comptes, cles d'API)
  --python CHEMIN     interpreteur a utiliser, par exemple celui d'un venv
  --hote ADRESSE      STUDIO_HOTE (127.0.0.1 par defaut : cette machine seule)
  --port N            STUDIO_PORT
  --comfy URL         COMFY_URL
  --ollama URL        OLLAMA_URL
  --ignorer-aiohttp   installe meme si aiohttp est introuvable
  --desinstaller      retire le service, sans toucher aux donnees
  -h, --aide          ce texte
FIN
  exit 0
}

# ══════════════════════════ arguments ══════════════════════════
while [ $# -gt 0 ]; do
  case "$1" in
    --utilisateur)    UTILISATEUR="${2:-}"; shift 2 ;;
    --racine)         RACINE="${2:-}"; shift 2 ;;
    --donnees)        DONNEES="${2:-}"; shift 2 ;;
    --python)         PYTHON="${2:-}"; shift 2 ;;
    --hote)           HOTE="${2:-}"; shift 2 ;;
    --port)           PORT="${2:-}"; shift 2 ;;
    --comfy)          COMFY_URL="${2:-}"; shift 2 ;;
    --ollama)         OLLAMA_URL="${2:-}"; shift 2 ;;
    --ignorer-aiohttp) IGNORER_AIOHTTP=1; shift ;;
    --desinstaller)   DESINSTALLER=1; shift ;;
    -h|--aide|--help) aide ;;
    *) mourir "argument inconnu : $1" "sh $0 --aide" ;;
  esac
done

# ══════════════════════════ ou sommes-nous ══════════════════════════
# On repart du dossier du SCRIPT et non du dossier courant : la ligne de
# commande la plus naturelle est « sudo sh service/installer_service.sh »
# depuis la racine, mais rien n'empeche de l'appeler par un chemin absolu
# depuis /root, et le service pointerait alors sur un serveur.py inexistant.
DOSSIER_SCRIPT=$(cd "$(dirname "$0")" && pwd)
[ -n "$RACINE" ] || RACINE=$(cd "$DOSSIER_SCRIPT/.." && pwd)
# Un chemin relatif passe en --racine donnerait un ExecStart relatif, que
# systemd refuse avec un message qui parle de syntaxe et non de chemin.
RACINE=$(cd "$RACINE" 2>/dev/null && pwd) || mourir "--racine introuvable"

SYSTEME=$(uname -s)

titre "ComfyStudio - installation en service"
vert "systeme      : $SYSTEME"
vert "racine       : $RACINE"

# ══════════════════════════ desinstallation ══════════════════════════
# Placee avant les verifications de Python : on doit pouvoir retirer un service
# meme si c'est justement l'interpreteur qui a disparu, sinon on laisse une
# unite en echec impossible a nettoyer par ce script.
if [ "$DESINSTALLER" = "1" ]; then
  titre "Desinstallation"
  if [ "$SYSTEME" = "Darwin" ]; then
    PLIST="$HOME/Library/LaunchAgents/$ETIQUETTE.plist"
    if [ -f "$PLIST" ]; then
      launchctl bootout "gui/$(id -u)/$ETIQUETTE" 2>/dev/null ||
        launchctl unload -w "$PLIST" 2>/dev/null || true
      rm -f "$PLIST"
      vert "agent retire : $PLIST"
    else
      jaune "aucun agent en $PLIST"
    fi
  else
    [ "$(id -u)" = "0" ] || mourir "il faut etre root pour retirer un service systemd" \
                                   "sudo sh $0 --desinstaller"
    UNITE="/etc/systemd/system/$NOM_SERVICE.service"
    if [ -f "$UNITE" ]; then
      systemctl stop "$NOM_SERVICE" 2>/dev/null || true
      systemctl disable "$NOM_SERVICE" 2>/dev/null || true
      rm -f "$UNITE"
      systemctl daemon-reload 2>/dev/null || true
      # Sans reset-failed, l'unite continue d'apparaitre en « failed » dans
      # « systemctl --failed » alors qu'elle n'existe plus.
      systemctl reset-failed "$NOM_SERVICE" 2>/dev/null || true
      vert "unite retiree : $UNITE"
    else
      jaune "aucune unite en $UNITE"
    fi
  fi
  # On ne supprime NI les donnees NI le compte de service : une desinstallation
  # qui efface les conversations d'un utilisateur est une perte de donnees
  # deguisee en nettoyage. On dit ou c'est, et on laisse decider.
  gris "conserves volontairement :"
  gris "  le compte de service et son groupe"
  gris "  le dossier de donnees (conversations, comptes, cles d'API)"
  gris "  $FICHIER_ENV s'il existe"
  printf '\n'
  exit 0
fi

[ -f "$RACINE/serveur.py" ] || mourir "serveur.py introuvable dans $RACINE" \
  "ce script doit vivre dans service/, a cote du dossier qui contient serveur.py" \
  "sinon : --racine /chemin/vers/ComfyStudio"

# ══════════════════════════ Python ══════════════════════════
titre "Python"
# On teste la VERSION, pas seulement la presence. Sur macOS et sur de vieilles
# distributions, « python » est un Python 2.7 : il demarre parfaitement, puis
# serveur.py echoue au parse sur la premiere f-string avec un SyntaxError qui
# designe une ligne au hasard et n'apprend rien. Un service qui plante ainsi
# entre en boucle de redemarrage sans que le message ne nomme la cause.
convient() {
  [ -n "${1:-}" ] || return 1
  command -v "$1" >/dev/null 2>&1 || return 1
  "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' 2>/dev/null
}

if [ -n "$PYTHON" ]; then
  convient "$PYTHON" || mourir "$PYTHON n'est pas un Python 3.8 ou plus recent" \
    "version vue : $("$PYTHON" -V 2>&1 || echo 'aucune, binaire introuvable')"
else
  for py in python3 python3.13 python3.12 python3.11 python3.10 python3.9 python; do
    if convient "$py"; then PYTHON="$py"; break; fi
  done
  [ -n "$PYTHON" ] || mourir "aucun Python 3.8 ou plus recent trouve" \
    "Debian, Ubuntu   sudo apt install python3 python3-aiohttp" \
    "Fedora           sudo dnf install python3 python3-aiohttp" \
    "Arch             sudo pacman -S python python-aiohttp" \
    "Alpine           sudo apk add python3 py3-aiohttp" \
    "macOS            brew install python" \
    "puis relance, ou pointe un venv : --python /chemin/venv/bin/python3"
fi

# Chemin absolu : systemd exige un ExecStart absolu, et launchd ne dispose
# d'aucun PATH utilisable. « python3 » tel quel donnerait un « No such file or
# directory » qui ne dit meme pas quel fichier manque.
PYTHON=$(command -v "$PYTHON")
case "$PYTHON" in
  /*) : ;;
  *)  mourir "impossible de resoudre $PYTHON en chemin absolu" ;;
esac
vert "$("$PYTHON" -V 2>&1) - $PYTHON"

# Un shim pyenv/asdf est un script qui a besoin de l'environnement de TON shell
# pour trouver le vrai interpreteur. Sous un compte de service, cet
# environnement n'existe pas : le shim s'execute, ne trouve rien, et l'unite
# echoue sur un message qui parle de pyenv et pas de ComfyStudio.
case "$PYTHON" in
  */shims/*|*/.pyenv/*|*/.asdf/*)
    jaune "cet interpreteur est un shim ($PYTHON)"
    gris "un compte de service n'a pas ton environnement : le shim echouera"
    gris "donne le chemin reel : --python \"\$(pyenv which python3)\""
    ;;
esac

# ══════════════════════════ aiohttp ══════════════════════════
titre "Dependance"
if "$PYTHON" -c 'import aiohttp' 2>/dev/null; then
  vert "aiohttp present"
elif [ "$IGNORER_AIOHTTP" = "1" ]; then
  jaune "aiohttp absent - installation forcee par --ignorer-aiohttp"
  gris "le service partira en echec repete jusqu'a ce qu'il soit installe"
else
  # Refus plutot qu'avertissement : sans aiohttp, serveur.py meurt a l'import.
  # Le service serait relance 5 fois puis marque « failed », et le seul indice
  # serait un ImportError enfoui dans journalctl. Autant le dire maintenant,
  # pendant qu'un humain regarde l'ecran.
  mourir "aiohttp introuvable pour $PYTHON" \
    "Debian, Ubuntu   sudo apt install python3-aiohttp" \
    "Fedora           sudo dnf install python3-aiohttp" \
    "Arch             sudo pacman -S python-aiohttp" \
    "Alpine           sudo apk add py3-aiohttp" \
    "venv ou macOS    $PYTHON -m pip install aiohttp" \
    "pour passer outre quand meme : --ignorer-aiohttp"
fi

# ══════════════════════════ outils communs ══════════════════════════
# sed sert a remplir les gabarits. Les chemins peuvent contenir des caracteres
# que sed interprete dans la partie droite d'un s|| : on les protege, sinon un
# dossier nomme « R&D » produirait un chemin faux et silencieux.
echapper() { printf '%s' "$1" | sed -e 's/[\\&|]/\\&/g'; }

# Le depot peut avoir ete clone depuis Windows : .gitattributes force les fins
# de ligne UNIX pour *.sh mais pas pour *.service ni *.plist. Un CR final rend
# l'ExecStart introuvable (« serveur.py\r ») et le plist illisible, avec dans
# les deux cas un message qui designe un fichier qui existe pourtant.
sans_cr() { tr -d '\r' < "$1"; }

# ══════════════════════════════════════════════════════════════════
#                              macOS
# ══════════════════════════════════════════════════════════════════
if [ "$SYSTEME" = "Darwin" ]; then
  titre "macOS - agent launchd"

  # Un LaunchAgent se pose dans le ~/Library de la personne qui l'installe.
  # Lance sous sudo, il irait dans /var/root/Library : charge par personne,
  # invisible, et il tournerait sous root le jour ou quelqu'un le trouverait.
  if [ "$(id -u)" = "0" ]; then
    mourir "n'installe PAS cet agent avec sudo" \
      "un LaunchAgent tourne sous le compte qui le possede : root ici" \
      "relance sans sudo, depuis ta session : sh $0"
  fi
  if [ -n "$UTILISATEUR" ] && [ "$UTILISATEUR" != "$(id -un)" ]; then
    mourir "un LaunchAgent ne peut pas tourner sous un autre compte que le tien" \
      "tu es $(id -un), tu demandes $UTILISATEUR" \
      "pour un compte dedie il faut un LaunchDaemon : voir NOTES.md"
  fi
  UTILISATEUR=$(id -un)

  [ -n "$DONNEES" ] || DONNEES="$HOME/Library/Application Support/ComfyStudio"
  DOSSIER_JOURNAL="$HOME/Library/Logs/ComfyStudio"
  JOURNAL="$DOSSIER_JOURNAL/studio.log"
  JOURNAL_ERR="$DOSSIER_JOURNAL/studio.err"
  PLIST="$HOME/Library/LaunchAgents/$ETIQUETTE.plist"

  mkdir -p "$DONNEES" "$DOSSIER_JOURNAL" "$HOME/Library/LaunchAgents" "$RACINE/sorties"
  # 700 : les conversations contiennent les demandes et les cles d'API. Sur un
  # Mac partage, le ~/Library d'un autre compte reste lisible par defaut.
  chmod 700 "$DONNEES"
  vert "donnees      : $DONNEES"
  vert "journal      : $JOURNAL"

  MODELE="$DOSSIER_SCRIPT/$ETIQUETTE.plist"
  [ -f "$MODELE" ] || mourir "gabarit introuvable : $MODELE"

  sans_cr "$MODELE" \
    | sed -e "s|@@PYTHON@@|$(echapper "$PYTHON")|g" \
          -e "s|@@RACINE@@|$(echapper "$RACINE")|g" \
          -e "s|@@DONNEES@@|$(echapper "$DONNEES")|g" \
          -e "s|@@JOURNAL@@|$(echapper "$JOURNAL")|g" \
          -e "s|@@JOURNAL_ERR@@|$(echapper "$JOURNAL_ERR")|g" \
          -e "s|@@HOTE@@|$(echapper "$HOTE")|g" \
          -e "s|@@PORT@@|$(echapper "$PORT")|g" \
          -e "s|@@AUTH@@|$(echapper "$AUTH")|g" \
          -e "s|@@COMFY_URL@@|$(echapper "$COMFY_URL")|g" \
          -e "s|@@OLLAMA_URL@@|$(echapper "$OLLAMA_URL")|g" \
    > "$PLIST.nouveau"

  # On cherche la FORME d'un jeton (@@MAJUSCULES@@) et non deux arobases : les
  # commentaires du gabarit parlent des jetons, et un grep trop large ferait
  # echouer chaque installation sur un faux positif.
  if grep -q '@@[A-Z_][A-Z_]*@@' "$PLIST.nouveau"; then
    rm -f "$PLIST.nouveau"
    mourir "des jetons @@...@@ n'ont pas ete remplaces dans le gabarit" \
      "le gabarit du depot a change sans que ce script suive"
  fi
  # plutil refuse un plist mal forme AVANT que launchd ne le refuse a son tour
  # avec un code d'erreur numerique et rien d'autre.
  if command -v plutil >/dev/null 2>&1; then
    plutil -lint "$PLIST.nouveau" >/dev/null ||
      { rm -f "$PLIST.nouveau"; mourir "plist invalide, rien n'a ete installe"; }
  fi
  mv "$PLIST.nouveau" "$PLIST"
  chmod 644 "$PLIST"
  vert "agent ecrit  : $PLIST"

  # Recharge : sans bootout prealable, bootstrap echoue avec « Bootstrap failed:
  # 5: Input/output error » quand une version precedente est deja chargee.
  launchctl bootout "gui/$(id -u)/$ETIQUETTE" 2>/dev/null || true
  if launchctl bootstrap "gui/$(id -u)" "$PLIST" 2>/dev/null; then
    vert "agent charge (launchctl bootstrap)"
  elif launchctl load -w "$PLIST" 2>/dev/null; then
    # macOS 10.10 et anterieurs ne connaissent pas bootstrap.
    vert "agent charge (launchctl load, ancienne syntaxe)"
  else
    mourir "launchctl a refuse de charger l'agent" \
      "diagnostic : launchctl print gui/$(id -u)/$ETIQUETTE" \
      "journal    : cat \"$JOURNAL_ERR\""
  fi

  titre "Ensuite"
  gris "etat     : launchctl print gui/$(id -u)/$ETIQUETTE | head -20"
  gris "journal  : tail -f \"$JOURNAL\""
  gris "relancer : launchctl kickstart -k gui/$(id -u)/$ETIQUETTE"
  gris "retirer  : sh $0 --desinstaller"
  gris ""
  gris "l'agent ne tourne QUE quand ta session est ouverte : voir NOTES.md"
  gris "interface : http://$HOTE:$PORT"
  printf '\n'
  exit 0
fi

# ══════════════════════════════════════════════════════════════════
#                              Linux
# ══════════════════════════════════════════════════════════════════
if [ "$SYSTEME" != "Linux" ]; then
  mourir "systeme non pris en charge : $SYSTEME" \
    "ce script connait Linux (systemd) et macOS (launchd)" \
    "sur *BSD, transpose l'unite en script rc.d : voir NOTES.md"
fi

titre "Linux - gestionnaire de services"
# La presence de « systemctl » ne prouve RIEN : le paquet systemd est installe
# sur des machines qui demarrent sous OpenRC, et dans un conteneur base sur une
# image Debian systemctl existe alors que PID 1 est le serveur lui-meme. Le seul
# test fiable est l'existence du repertoire que systemd cree en tant que PID 1.
if [ ! -d /run/systemd/system ]; then
  rouge "systemd n'est pas le gestionnaire de services de cette machine"
  printf '\n'
  if [ -f /.dockerenv ] || grep -qE '(docker|containerd|lxc)' /proc/1/cgroup 2>/dev/null; then
    gris "Conteneur detecte. Un conteneur n'a pas de gestionnaire de services :"
    gris "c'est l'orchestrateur qui redemarre le processus."
    gris "  docker :  docker run --restart=unless-stopped ..."
    gris "  compose : deploy.restart_policy, ou restart: unless-stopped"
    gris "Le depot fournit deja Dockerfile et docker-compose.yml pour cela."
  elif command -v rc-service >/dev/null 2>&1 || [ -x /sbin/openrc-run ]; then
    gris "OpenRC detecte (Alpine, Gentoo, Devuan)."
    gris "Marche a suivre dans service/NOTES.md, section « Sans systemd » :"
    gris "elle donne un /etc/init.d/comfystudio pret a coller, base sur"
    gris "supervise-daemon, qui assure le redemarrage automatique."
  elif [ -d /etc/sv ] || command -v sv >/dev/null 2>&1; then
    gris "runit detecte (Void, Artix). Voir NOTES.md, section « Sans systemd »."
  else
    gris "Aucun gestionnaire connu. Voir NOTES.md, section « Sans systemd »."
  fi
  printf '\n'
  gris "En attendant, pour essayer le studio sans service :"
  gris "  cd \"$RACINE\" && $PYTHON -u serveur.py"
  printf '\n'
  exit 1
fi
vert "systemd actif"
[ "$(id -u)" = "0" ] || mourir "il faut etre root pour poser une unite systemd" \
  "sudo sh $0 $*" \
  "le SERVICE, lui, tournera sous un compte non privilegie"

# ══════════════════════════ compte de service ══════════════════════════
titre "Compte de service"
[ -n "$UTILISATEUR" ] || UTILISATEUR="$NOM_SERVICE"
[ -n "$DONNEES" ] || DONNEES="/var/lib/$NOM_SERVICE"

if id "$UTILISATEUR" >/dev/null 2>&1; then
  vert "compte existant : $UTILISATEUR"
  # Refus net : faire tourner sous root ce que toute l'unite s'emploie a
  # confiner viderait le durcissement de son sens.
  [ "$(id -u "$UTILISATEUR")" != "0" ] ||
    mourir "$UTILISATEUR est root - refuse" "choisis un autre compte : --utilisateur comfystudio"
else
  # Un compte SYSTEME : pas de mot de passe, pas de shell, pas de courrier, et
  # un UID sous 1000 pour qu'il n'apparaisse pas dans l'ecran de connexion.
  # Le shell nologin est ce qui empeche une session interactive si le compte
  # venait a etre compromis par le studio.
  if command -v useradd >/dev/null 2>&1; then
    # useradd de shadow-utils : Debian, Ubuntu, Fedora, Arch, openSUSE.
    useradd --system --no-create-home --home-dir "$DONNEES" \
            --shell /usr/sbin/nologin "$UTILISATEUR" 2>/dev/null ||
    # Arch et Fedora ne fournissent pas /usr/sbin/nologin mais /sbin/nologin ;
    # useradd refuse un shell inexistant sur certaines versions.
    useradd --system --no-create-home --home-dir "$DONNEES" \
            --shell /sbin/nologin "$UTILISATEUR" ||
      mourir "creation du compte $UTILISATEUR impossible"
  elif command -v adduser >/dev/null 2>&1; then
    # busybox adduser (Alpine, images minimales) : options courtes et
    # incompatibles avec celles de shadow-utils.
    adduser -S -D -H -h "$DONNEES" -s /sbin/nologin "$UTILISATEUR" ||
      mourir "creation du compte $UTILISATEUR impossible (adduser busybox)"
  else
    mourir "ni useradd ni adduser sur cette machine" \
      "cree le compte a la main, puis : --utilisateur NOM"
  fi
  vert "compte cree : $UTILISATEUR (systeme, sans shell)"
fi
# Le groupe homonyme n'est pas garanti : busybox adduser -S place le compte dans
# « nogroup ». On lit le groupe reel plutot que de le supposer, sinon l'unite
# echoue sur « Group comfystudio not found » apres une installation « reussie ».
GROUPE=$(id -gn "$UTILISATEUR")
vert "groupe       : $GROUPE"

# ══════════════════════════ dossiers ══════════════════════════
titre "Dossiers"
mkdir -p "$DONNEES" "$RACINE/sorties"
chown -R "$UTILISATEUR:$GROUPE" "$DONNEES" "$RACINE/sorties"
# 700 : conversations, comptes et cles d'API. Personne d'autre n'a a les lire.
chmod 700 "$DONNEES"
vert "donnees      : $DONNEES"
vert "sorties      : $RACINE/sorties"

# Le studio ajoute une ligne a avis.jsonl a chaque generation, DANS son dossier
# d'installation. Le dossier restant la propriete de root, il ne pourrait pas
# creer le fichier ; l'echec est rattrape en silence et le journal des avis se
# perdrait sans que rien ne l'annonce. On cree le fichier et on le lui donne,
# sans rendre le code lui-meme accessible en ecriture.
[ -e "$RACINE/avis.jsonl" ] || : > "$RACINE/avis.jsonl"
chown "$UTILISATEUR:$GROUPE" "$RACINE/avis.jsonl"
vert "avis.jsonl   : accessible en ecriture au service"

# noeuds.json n'est que LU par le studio : il reste la propriete de
# l'administrateur, volontairement. C'est une configuration, pas une donnee.

# ProtectHome=yes rend /home, /root et /run/user inaccessibles au service. Si
# l'installation, les donnees ou l'interpreteur vivent la-dessous, l'unite
# echoue sur « No such file or directory » en designant un fichier qui existe
# pourtant - le pire message de tout systemd. On desactive alors la protection
# en le disant, plutot que de livrer un service qui ne demarre pas.
PROTECT_HOME="yes"
for chemin in "$RACINE" "$DONNEES" "$PYTHON"; do
  case "$chemin" in
    /home/*|/root/*)
      PROTECT_HOME="no"
      jaune "ProtectHome desactive : $chemin est sous /home ou /root"
      gris "pour le durcissement complet, deplace l'installation sous /opt"
      ;;
  esac
done
[ "$PROTECT_HOME" = "no" ] || vert "ProtectHome  : yes"

# ══════════════════════════ fichier d'environnement ══════════════════════════
titre "Configuration"
if [ -f "$FICHIER_ENV" ]; then
  # On n'ecrase JAMAIS : ce fichier contient STUDIO_ADMIN_MDP et les reglages
  # de la machine. Une reinstallation apres mise a jour effacerait le mot de
  # passe admin, et le studio redemarrerait en refusant tout le monde.
  vert "conserve tel quel : $FICHIER_ENV"
  gris "supprime-le d'abord si tu veux repartir des valeurs par defaut"
else
  cat > "$FICHIER_ENV" <<FIN
# Configuration de ComfyStudio, lue par le service a chaque demarrage.
# Apres modification :  systemctl restart $NOM_SERVICE
# (pas besoin de daemon-reload : ce n'est pas l'unite qui change.)

# 127.0.0.1 : cette machine seulement. 0.0.0.0 : tout le reseau local.
# N'ouvre au reseau QUE si STUDIO_AUTH reste « obligatoire » et que
# STUDIO_ADMIN_MDP est renseigne plus bas.
STUDIO_HOTE=$HOTE
STUDIO_PORT=$PORT

# « obligatoire » exige un compte pour entrer, « libre » ouvre a quiconque
# atteint le port. « libre » sur 0.0.0.0 donne a tout le reseau le droit de
# generer, de televerser et de piloter ComfyUI.
STUDIO_AUTH=$AUTH
# Mot de passe du compte admin. VIDE = pas d'administration possible.
STUDIO_ADMIN_MDP=

COMFY_URL=$COMFY_URL
OLLAMA_URL=$OLLAMA_URL

# Dossier de ComfyUI sur CETTE machine, si ComfyUI y tourne. Laisse vide quand
# ComfyUI est ailleurs : tout passe alors par COMFY_URL.
#COMFY_DIR=
#COMFY_MODELES=
#COMFY_ENTREE=

# Modeles Ollama. Vide pour STUDIO_LLM_ECRITURE = le plus gros qui tienne en
# memoire sera choisi au demarrage.
#STUDIO_LLM=qwen2.5vl:7b
#STUDIO_LLM_ECRITURE=
FIN
  # 640 root:service : le mot de passe admin ne doit pas etre lisible par les
  # autres comptes de la machine, et le service n'a besoin que de le lire.
  chown "root:$GROUPE" "$FICHIER_ENV"
  chmod 640 "$FICHIER_ENV"
  vert "cree : $FICHIER_ENV (640 root:$GROUPE)"
  gris "renseigne STUDIO_ADMIN_MDP avant d'ouvrir le studio au reseau"
fi

# ══════════════════════════ unite ══════════════════════════
titre "Unite systemd"
MODELE="$DOSSIER_SCRIPT/$NOM_SERVICE.service"
[ -f "$MODELE" ] || mourir "gabarit introuvable : $MODELE"
UNITE="/etc/systemd/system/$NOM_SERVICE.service"

sans_cr "$MODELE" \
  | sed -e "s|@@UTILISATEUR@@|$(echapper "$UTILISATEUR")|g" \
        -e "s|@@RACINE@@|$(echapper "$RACINE")|g" \
        -e "s|@@DONNEES@@|$(echapper "$DONNEES")|g" \
        -e "s|@@PYTHON@@|$(echapper "$PYTHON")|g" \
        -e "s|@@GROUPE@@|$(echapper "$GROUPE")|g" \
        -e "s|@@ENV@@|$(echapper "$FICHIER_ENV")|g" \
        -e "s|@@PROTECT_HOME@@|$PROTECT_HOME|g" \
  > "$UNITE.nouveau"

# On cherche la FORME d'un jeton (@@MAJUSCULES@@) et non deux arobases : les
# commentaires du gabarit parlent des jetons, et un grep trop large ferait
# echouer chaque installation sur un faux positif.
if grep -q '@@[A-Z_][A-Z_]*@@' "$UNITE.nouveau"; then
  rm -f "$UNITE.nouveau"
  mourir "des jetons @@...@@ n'ont pas ete remplaces dans le gabarit" \
    "le gabarit du depot a change sans que ce script suive"
fi
mv "$UNITE.nouveau" "$UNITE"
chmod 644 "$UNITE"
vert "ecrite : $UNITE"

systemctl daemon-reload
# systemd-analyze verify attrape une faute de frappe dans une directive AVANT
# le premier demarrage. Il n'existe pas partout, et il rale sur des directives
# trop recentes pour lui : on affiche sans faire echouer l'installation.
if command -v systemd-analyze >/dev/null 2>&1; then
  systemd-analyze verify "$UNITE" 2>&1 | sed 's/^/       /' || true
fi

systemctl enable "$NOM_SERVICE" >/dev/null 2>&1 || true
# reset-failed avant restart : si une tentative precedente a epuise le
# StartLimitBurst, « systemctl start » refuse avec « start request repeated too
# quickly » et ne relance pas, meme apres correction du probleme.
systemctl reset-failed "$NOM_SERVICE" 2>/dev/null || true
systemctl restart "$NOM_SERVICE" || true

titre "Etat"
if systemctl is-active --quiet "$NOM_SERVICE"; then
  vert "le service tourne"
  gris "interface : http://$HOTE:$PORT"
else
  rouge "le service n'est pas actif"
  systemctl status "$NOM_SERVICE" --no-pager --lines=15 2>&1 | sed 's/^/       /' || true
fi

titre "Ensuite"
gris "etat     : systemctl status $NOM_SERVICE"
gris "journal  : journalctl -u $NOM_SERVICE -f"
gris "config   : \$EDITOR $FICHIER_ENV  puis  systemctl restart $NOM_SERVICE"
gris "retirer  : sudo sh $0 --desinstaller"
printf '\n'
