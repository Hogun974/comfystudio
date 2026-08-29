# ComfyStudio en service — ce qui change d'un système à l'autre

Ce dossier ne contient que de quoi **faire tourner ComfyStudio en tâche de fond**.
Il n'installe ni ComfyUI, ni Ollama, ni les modèles : c'est le travail de
`installer.sh` / `installer.py`, à la racine du dépôt, qu'il faut lancer avant.

Sous Windows il n'y a rien ici pour le studio lui-même — on le lance en Docker
ou par `LANCER ComfyStudio.bat`. En revanche `noeud_windows.ps1` remet **l'agent
de nœud** en service, ce qui est le besoin réel : une machine à carte qui ne
revient pas après un redémarrage est perdue en silence.

```powershell
powershell -ExecutionPolicy Bypass -File service\noeud_windows.ps1 -Dossier D:\NoeudPC
powershell -ExecutionPolicy Bypass -File service\noeud_windows.ps1 -Desinstaller
```

```sh
sudo sh service/installer_service.sh          # Linux, systemd
sh      service/installer_service.sh          # macOS, SANS sudo
sh      service/installer_service.sh --aide
sudo sh service/installer_service.sh --desinstaller
```

| Fichier | Rôle |
|---|---|
| `comfystudio.service` | gabarit d'unité systemd |
| `com.comfystudio.plist` | gabarit d'agent launchd (macOS) |
| `installer_service.sh` | détecte le système, remplit le gabarit, l'installe |
| `noeud_windows.ps1` | met l'agent de **nœud** en service sur Windows (tâche planifiée) |
| `NOTES.md` | ce fichier |

Les deux gabarits contiennent des jetons `@@NOM@@` que l'installeur remplace par
les chemins réels. On peut les remplir à la main : c'est écrit en tête de chaque
fichier.

---

## 1. Le compte qui fait tourner le studio

Le studio expose une interface web qui **reçoit des téléversements, télécharge
des modèles et lance des sous-processus**. Sous `root`, la moindre faille dans
aiohttp ou dans le studio donne la machine entière. Il ne tourne donc jamais
sous `root`, et l'installeur refuse explicitement un compte d'UID 0.

### Linux

Par défaut, l'installeur crée un compte **système** nommé `comfystudio` :
sans mot de passe, sans shell de connexion, sans dossier personnel, avec un
UID sous 1000 pour qu'il n'apparaisse pas dans l'écran de connexion.

Deux outils existent, et ils ne partagent **aucune option** :

| Famille | Commande utilisée | Distributions |
|---|---|---|
| shadow-utils | `useradd --system --no-create-home --shell …/nologin` | Debian, Ubuntu, Fedora, RHEL, Arch, openSUSE |
| busybox | `adduser -S -D -H -h … -s …/nologin` | Alpine, images de conteneur minimales |

Le chemin de `nologin` diffère lui aussi : `/usr/sbin/nologin` sur Debian et
Ubuntu, `/sbin/nologin` sur Fedora et Arch. Certaines versions de `useradd`
refusent un shell inexistant ; l'installeur essaie les deux chemins.

Le **groupe** n'est pas supposé homonyme : `adduser -S` de busybox range le
compte dans `nogroup`. L'installeur lit le groupe réel (`id -gn`) et le place
dans l'unité. Sans cela, systemd échoue sur `Group comfystudio not found` après
une installation annoncée réussie.

Pour utiliser un compte existant : `--utilisateur mon-compte`. Il ne sera pas
modifié, seulement vérifié.

### macOS

Il n'y a **pas de compte créé**. L'agent est un `LaunchAgent` : il tourne sous
le compte de la personne qui l'installe, ce qui satisfait « jamais root » sans
rien créer. C'est pourquoi l'installeur **refuse d'être lancé avec `sudo`** sur
macOS : sous `sudo`, le plist irait dans `/var/root/Library/LaunchAgents`, où
personne ne le retrouverait, et il tournerait sous `root`.

Faire tourner le studio sous un compte macOS *dédié* impose un `LaunchDaemon`
(voir §4) — c'est le seul type qui honore les clés `UserName` / `GroupName`.

---

## 2. Où le studio écrit, et pourquoi c'est à deux endroits

C'est le point qui décide de tout le durcissement, donc il mérite d'être écrit
noir sur blanc. `serveur.py` écrit :

| Chemin | Contenu | Réglable |
|---|---|---|
| `STUDIO_DONNEES` | conversations, comptes, clés d'API, registre des nœuds | oui |
| `<installation>/sorties/` | images et vidéos rapatriées des nœuds distants | **non** |
| `<installation>/avis.jsonl` | journal des générations | **non** |

Les deux derniers sont calculés à partir de l'emplacement de `serveur.py` et
**ne suivent pas `STUDIO_DONNEES`**. Conséquences :

- `ProtectSystem=strict` est inutilisable tel quel : il faudrait lister ces
  chemins un par un, et toute omission ne se voit qu'au premier téléversement,
  des semaines après l'installation. L'unité utilise donc `ProtectSystem=full`
  (`/usr`, `/boot`, `/efi`, `/etc` en lecture seule), et `ReadWritePaths`
  documente l'intention pour le jour où ces chemins deviendront configurables.
- L'installeur crée `sorties/` et `avis.jsonl` et les donne au compte de
  service, **sans rendre le code inscriptible**. `avis.jsonl` compte : le studio
  rattrape en silence l'échec d'écriture, et le journal des avis se perdrait
  sans qu'aucun message ne l'annonce.
- `noeuds.json` reste la propriété de l'administrateur : il est seulement *lu*.
  C'est une configuration, pas une donnée.

Défauts retenus : `/var/lib/comfystudio` sur Linux,
`~/Library/Application Support/ComfyStudio` sur macOS, en mode `700` — les
conversations contiennent les demandes des utilisateurs et les clés d'API.

---

## 3. Linux : ce qui change d'une distribution à l'autre

### 3.1 La version de systemd

Le durcissement de l'unité utilise des directives arrivées entre 2016 et 2020.
Une directive inconnue est **ignorée avec un avertissement au journal**, elle ne
casse pas le service — mais elle ne protège rien non plus.

| Directive | systemd requis (env.) |
|---|---|
| `StartLimitIntervalSec` / `Burst` dans `[Unit]` | 229 |
| `ProtectKernelTunables`, `ProtectKernelModules`, `ProtectControlGroups` | 232 |
| `ReadWritePaths`, `RestrictNamespaces` | 233 |
| `LockPersonality` | 235 |
| `Type=exec` | 240 |
| `RestrictSUIDSGID`, `ProtectHostname` | 242 |
| `ProtectKernelLogs` | 244 |
| `ProtectClock` | 245 |
| `ProtectProc`, `ProcSubset` | 247 |

À titre indicatif, et sous réserve de vieillissement de ce tableau :
RHEL/Rocky 8 ≈ 239, Ubuntu 20.04 ≈ 245, Debian 11 ≈ 247, Ubuntu 22.04 ≈ 249,
Debian 12 et RHEL 9 ≈ 252, Ubuntu 24.04 ≈ 255, Arch et Fedora au plus récent.

**Ne fais pas confiance à ce tableau, fais confiance à la machine :**

```sh
systemctl --version | head -1
systemd-analyze verify /etc/systemd/system/comfystudio.service
journalctl -u comfystudio | grep -i 'unknown\|ignoring'
systemd-analyze security comfystudio      # note de 0 (bien) à 10 (nu), systemd 240+
```

C'est pour cette raison que l'unité utilise `Type=simple` et non `Type=exec` :
`exec` ferait échouer `systemctl start` immédiatement quand l'interpréteur est
introuvable — plus clair — mais laisserait RHEL 8 et Ubuntu 18.04 de côté.

### 3.2 Python et le paquetage d'aiohttp

`serveur.py` exige **Python 3.8 ou plus récent** : il contient des f-strings, et
un Python 2 échoue au *parse*, avant même d'exécuter la première ligne. Le
message est un `SyntaxError` qui désigne une ligne au hasard et n'apprend rien —
et dans un service, il défile en boucle. L'installeur teste donc la **version**,
jamais la seule présence du binaire.

`aiohttp` est la seule dépendance obligatoire, et son paquetage varie :

| Distribution | Commande |
|---|---|
| Debian, Ubuntu | `sudo apt install python3 python3-aiohttp` |
| Fedora, RHEL | `sudo dnf install python3 python3-aiohttp` |
| Arch | `sudo pacman -S python python-aiohttp` |
| Alpine | `sudo apk add python3 py3-aiohttp` |
| openSUSE | `sudo zypper install python3-aiohttp` |

L'installeur **refuse d'installer le service si `aiohttp` est introuvable**,
plutôt que d'avertir. Sans lui, le studio meurt à l'import : systemd le relance
cinq fois, l'abandonne, et le seul indice est un `ImportError` enfoui dans
`journalctl`. Autant le dire pendant qu'un humain regarde l'écran.
`--ignorer-aiohttp` passe outre si tu sais ce que tu fais.

**Debian 12, Ubuntu 24.04 et suivantes (PEP 668).** `pip install` hors venv est
refusé avec `error: externally-managed-environment`. Deux issues :

```sh
sudo apt install python3-aiohttp                     # le paquet de la distribution
# ou un venv, et on le désigne au service :
sudo python3 -m venv /opt/comfystudio-venv
sudo /opt/comfystudio-venv/bin/pip install aiohttp huggingface_hub
sudo sh service/installer_service.sh --python /opt/comfystudio-venv/bin/python3
```

**Arch.** Distribution en flux continu : une montée de Python de 3.12 à 3.13
casse un venv existant, qui pointe sur un `lib/python3.12` disparu. Le service
échoue alors à l'import après une simple mise à jour du système. Sur Arch, le
paquet `python-aiohttp` de la distribution vieillit mieux qu'un venv.

**pyenv, asdf, mise.** Un *shim* est un script qui a besoin de **ton**
environnement de shell pour trouver le vrai interpréteur. Un compte de service
n'a pas cet environnement : le shim s'exécute, ne trouve rien, et l'unité échoue
sur un message qui parle de pyenv et pas de ComfyStudio. L'installeur le détecte
et prévient ; donne le chemin réel :
`--python "$(pyenv which python3)"`.

### 3.3 SELinux — Fedora, RHEL, Rocky, AlmaLinux, CentOS Stream

C'est la différence qui surprend le plus, parce que le service démarre *presque*.

- Un fichier posé sous `/opt` ou `/srv` par `git clone` porte souvent le
  contexte `user_home_t` au lieu de `usr_t`. systemd refuse de l'exécuter, avec
  un `Permission denied` sur un fichier qui a pourtant les bons droits Unix.

  ```sh
  sudo restorecon -Rv /opt/ComfyStudio
  ```

- Le port 8199 n'est pas étiqueté. Tant que le studio est un service non
  confiné (`unconfined_service_t`, cas par défaut d'une unité maison) il peut
  s'y attacher. Si tu confines l'unité, il faut l'étiqueter :

  ```sh
  sudo semanage port -a -t http_port_t -p tcp 8199
  ```

- Diagnostic universel : `sudo ausearch -m AVC -ts recent` ou
  `sudo journalctl -t setroubleshoot`. **Ne désactive pas SELinux** pour faire
  passer un service ; `restorecon` suffit dans l'immense majorité des cas.

Debian, Ubuntu et Arch n'ont rien de tout cela par défaut. AppArmor, présent sur
Ubuntu, ne confine que les programmes ayant un profil ; ComfyStudio n'en a pas
et n'est donc pas gêné.

### 3.4 Le pare-feu

Par défaut `STUDIO_HOTE=127.0.0.1` : le studio n'écoute que sur la machine et
aucun pare-feu n'entre en jeu. Pour l'ouvrir au réseau local, il faut
**les deux** : la variable *et* le pare-feu.

```sh
# Ubuntu, Debian
sudo ufw allow 8199/tcp
# Fedora, RHEL
sudo firewall-cmd --add-port=8199/tcp --permanent && sudo firewall-cmd --reload
```

> Avant d'ouvrir : renseigne `STUDIO_ADMIN_MDP` dans `/etc/comfystudio.env` et
> laisse `STUDIO_AUTH=obligatoire`. En `libre` sur `0.0.0.0`, quiconque atteint
> le port peut générer, téléverser et piloter ComfyUI. Pour une exposition
> au-delà du réseau local, mets un reverse proxy avec TLS devant — pas le studio
> nu.

### 3.5 ComfyUI : service séparé, toujours

Le studio *sait* lancer ComfyUI lui-même. **En service, ne le laisse pas faire.**
Deux raisons, toutes deux vérifiables dans l'unité :

1. `KillMode` vaut `control-group` par défaut : un ComfyUI lancé par le studio
   est son enfant, et tombe avec lui à **chaque** redémarrage du studio.
2. `PrivateDevices=yes` prive le studio de `/dev/nvidia*`. Un ComfyUI lancé dans
   ce contexte hérite de la restriction et ne voit aucune carte.

Fais de ComfyUI son propre service, ne renseigne que `COMFY_URL`, et décommente
dans l'unité les lignes `After=` / `Wants=comfyui.service ollama.service`.

---

## 4. macOS : ce que launchd ne sait pas faire

launchd n'est pas un systemd avec une autre syntaxe. Voici la correspondance
honnête, y compris les cases vides.

| systemd | launchd | Remarque |
|---|---|---|
| `Restart=on-failure` | `KeepAlive` → `SuccessfulExit: false` | équivalent réel |
| `RestartSec=5` | `ThrottleInterval` | équivalent réel |
| `StartLimitBurst=5` | **rien** | voir ci-dessous |
| `TimeoutStopSec` | `ExitTimeOut` | équivalent réel |
| `WorkingDirectory` | `WorkingDirectory` | équivalent réel |
| `Environment=` | `EnvironmentVariables` | équivalent réel |
| `EnvironmentFile=` | **rien** | tout est dans le plist |
| `WantedBy=multi-user.target` | `RunAtLoad` + emplacement du plist | approchant |
| `After=network-online.target` | **rien d'utilisable** | voir ci-dessous |
| `User=` / `Group=` | `UserName` / `GroupName` | **LaunchDaemon seulement** |
| `NoNewPrivileges` | **rien** | |
| `PrivateTmp` | **rien** | |
| `ProtectSystem`, `ProtectHome` | **rien de comparable** | voir ci-dessous |
| `ReadWritePaths` | **rien** | |
| `CapabilityBoundingSet` | **rien** | pas de capabilities sur macOS |
| `SystemCallFilter` | **rien de comparable** | voir ci-dessous |
| `RestrictAddressFamilies` | **rien** | |
| `UMask=0077` | `Umask` (entier **décimal**, pas octal) | piège classique |
| `journalctl -u …` | **rien** | voir ci-dessous |
| `systemd-analyze verify` | `plutil -lint` | ne valide que la **syntaxe** |

**Pas de garde-fou anti-boucle.** `ThrottleInterval` espace les relances, mais
launchd **ne renonce jamais**. Un studio qui plante à l'import sera relancé six
fois par minute jusqu'à extinction du Mac, en silence. C'est précisément pour
cela que l'installeur vérifie `aiohttp` *avant* de poser l'agent : sur macOS,
cette vérification n'est pas un confort, c'est le seul garde-fou.

**Pas de durcissement.** Rien dans un plist n'approche `ProtectSystem`,
`NoNewPrivileges` ou `SystemCallFilter`. Ce que macOS offre relève d'autres
mécanismes, et aucun ne se pilote depuis launchd : TCC (autorisations par
dossier, à la main dans Réglages Système), le *hardened runtime* (attribut de
signature de code, pas d'un service), et `sandbox-exec` — déprécié, non
documenté, et à ne pas mettre en production. La seule protection réelle ici est
que l'agent tourne sous un compte utilisateur ordinaire.

**Pas de journal centralisé.** Le journal unifié de macOS ne capture pas la
sortie standard d'un agent. Sans `StandardOutPath` / `StandardErrorPath`, tout
ce que le studio affiche part dans le vide et un plantage devient muet. Et
launchd ne fait **aucune rotation** : le fichier grossit indéfiniment. Pour la
rotation, `newsyslog` :

```sh
sudo tee /etc/newsyslog.d/comfystudio.conf <<'EOF'
# fichier                                              mode  nb  taille  quand  drapeaux
/Users/TOI/Library/Logs/ComfyStudio/studio.log         644   5   5000    *      J
EOF
```

**Pas d'attente du réseau.** launchd n'a pas d'équivalent de
`network-online.target`. Le studio démarrera peut-être avant que le Wi-Fi soit
monté et annoncera « aucun ComfyUI joignable ». Ce n'est pas grave — il se
reconnecte à la première requête — mais le message du démarrage peut mentir.

**L'agent ne tourne que session ouverte.** Un `LaunchAgent` démarre à l'ouverture
de session et s'arrête à la fermeture. Pour un Mac serveur, sans écran et sans
personne devant, il y a deux voies :

1. **Connexion automatique** (Réglages Système → Utilisateurs et groupes →
   Ouverture de session automatique) et rester sur cet agent. Simple, mais le
   trousseau du compte est déverrouillé au démarrage : à éviter sur une machine
   physiquement accessible.
2. **Convertir en `LaunchDaemon`** : déplacer le plist dans
   `/Library/LaunchDaemons/`, le mettre `root:wheel` en `644`, **ajouter les clés
   `UserName` et `GroupName`** pointant sur un compte dédié, et charger avec
   `sudo launchctl bootstrap system /Library/LaunchDaemons/com.comfystudio.plist`.
   Sans `UserName`, le daemon tourne sous **root** — c'est exactement ce qu'on
   voulait éviter. `installer_service.sh` ne fait pas cette conversion :
   elle demande un compte dédié, des droits sur les journaux et sur le dossier
   de données, et une installation à moitié faite ici tournerait sous root sans
   le dire.

**`bootstrap` / `bootout` contre `load` / `unload`.** Depuis macOS 10.11, la
syntaxe moderne est `launchctl bootstrap gui/$(id -u) chemin.plist` et
`launchctl bootout gui/$(id -u)/com.comfystudio`. `load -w` / `unload -w`
fonctionnent encore mais sont dépréciés et donnent des messages d'erreur
inutilisables. L'installeur essaie la syntaxe moderne, puis l'ancienne.
Un `bootstrap` sur un agent déjà chargé échoue avec
`Bootstrap failed: 5: Input/output error` : il faut un `bootout` d'abord, ce que
l'installeur fait systématiquement.

**Modifier la configuration** demande de recharger, puisqu'il n'y a pas de
fichier d'environnement :

```sh
launchctl bootout   gui/$(id -u)/com.comfystudio
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.comfystudio.plist
launchctl kickstart -k gui/$(id -u)/com.comfystudio   # simple redémarrage
launchctl print gui/$(id -u)/com.comfystudio | head -30
```

**TCC.** Si `STUDIO_DONNEES` pointe vers `~/Documents`, `~/Desktop` ou
`~/Downloads`, macOS bloque l'accès tant que l'interpréteur n'a pas l'accès
complet au disque, et l'erreur est un `PermissionError` qui ne mentionne jamais
TCC. Le défaut retenu (`~/Library/Application Support/ComfyStudio`) évite
entièrement le problème.

---

## 5. Sans systemd

`installer_service.sh` détecte le cas et s'arrête proprement. Le test employé
n'est **pas** la présence de `systemctl` : ce binaire est installé sur des
machines qui démarrent sous OpenRC, et il existe dans un conteneur bâti sur une
image Debian alors que PID 1 est le serveur lui-même. Le seul test fiable est
l'existence de `/run/systemd/system`, que systemd ne crée qu'en étant PID 1.

### Conteneur (Docker, Podman, LXC)

Un conteneur n'a pas de gestionnaire de services : c'est l'orchestrateur qui
redémarre le processus. Le dépôt fournit déjà `Dockerfile` et
`docker-compose.yml` — utilise-les, n'installe pas de service à l'intérieur.

```sh
docker run --restart=unless-stopped ...
# compose : restart: unless-stopped
```

### OpenRC — Alpine, Gentoo, Devuan

`supervise-daemon` (OpenRC 0.35+) est le seul mode qui apporte le redémarrage
automatique ; le mode `start-stop-daemon` historique ne surveille rien.
À coller dans `/etc/init.d/comfystudio`, puis `chmod +x` :

```sh
#!/sbin/openrc-run
name="ComfyStudio"
description="Pilotage de ComfyUI en langage naturel"

supervisor="supervise-daemon"
command="/usr/bin/python3"
command_args="-u /opt/ComfyStudio/serveur.py"
command_user="comfystudio:comfystudio"
directory="/opt/ComfyStudio"

# OpenRC ne lit pas de fichier d'environnement : chaque variable est passee ici.
supervise_daemon_args="--env STUDIO_DONNEES=/var/lib/comfystudio
                       --env PYTHONUNBUFFERED=1
                       --env STUDIO_HOTE=127.0.0.1
                       --env STUDIO_PORT=8199"

# L'equivalent de RestartSec / StartLimitBurst / StartLimitIntervalSec.
# Sans respawn_max, un studio qui plante a l'import boucle indefiniment.
respawn_delay=5
respawn_max=5
respawn_period=300

output_log="/var/log/comfystudio.log"
error_log="/var/log/comfystudio.err"

depend() {
    need net
    after ollama comfyui
}
```

```sh
sudo rc-update add comfystudio default
sudo rc-service comfystudio start
sudo rc-service comfystudio status
```

**Aucun durcissement n'est transposable.** OpenRC n'a ni `ProtectSystem`, ni
`NoNewPrivileges`, ni filtre d'appels système. `command_user` — le compte non
privilégié — est la seule protection. Sur Alpine, crée-le avec
`adduser -S -D -H -h /var/lib/comfystudio -s /sbin/nologin comfystudio` et
vérifie son groupe : busybox le range dans `nogroup`.

### runit — Void, Artix

`/etc/sv/comfystudio/run`, `chmod +x`, puis un lien vers `/var/service/` :

```sh
#!/bin/sh
exec 2>&1
cd /opt/ComfyStudio || exit 1
export STUDIO_DONNEES=/var/lib/comfystudio PYTHONUNBUFFERED=1
exec chpst -u comfystudio:comfystudio /usr/bin/python3 -u serveur.py
```

runit relance **toujours**, après une seconde, sans plafond ni ralentissement
progressif. Un studio qui plante à l'import remplira le disque de journaux :
prévois `svlogd` avec une taille maximale dans `/etc/sv/comfystudio/log/run`.

### BSD, ou tout le reste

`installer_service.sh` refuse tout `uname -s` autre que `Linux` et `Darwin`.
Sur FreeBSD, transpose l'unité en script `rc.d` avec `daemon(8)` :
`daemon -r` fournit le redémarrage automatique, `-u comfystudio` le compte non
privilégié, `-o` le journal.

---

## 6. Diagnostic

| Symptôme | Piste |
|---|---|
| `status=203/EXEC` | chemin de `ExecStart` faux, ou fin de ligne CRLF, ou SELinux |
| `Group … not found` | groupe homonyme absent (busybox) |
| `No such file or directory` sur un fichier qui existe | `ProtectHome=yes` alors que l'installation est sous `/home` |
| `start request repeated too quickly` | `StartLimitBurst` atteint → `systemctl reset-failed comfystudio` |
| `ImportError: aiohttp` en boucle | mauvais interpréteur (venv non désigné, ou shim pyenv) |
| `Address already in use` | un studio tourne déjà — `ss -lptn 'sport = :8199'` |
| `Permission denied` sur `conversations/` | `STUDIO_DONNEES` changé sans corriger le propriétaire |
| macOS : rien dans le journal | `StandardOutPath` absent, ou dossier de journaux inexistant |
| macOS : `Bootstrap failed: 5` | agent déjà chargé → `launchctl bootout` d'abord |

```sh
# Linux
systemctl status comfystudio
journalctl -u comfystudio -f
journalctl -u comfystudio -b --no-pager | tail -50
sudo systemd-analyze security comfystudio

# macOS
tail -f ~/Library/Logs/ComfyStudio/studio.err
launchctl print gui/$(id -u)/com.comfystudio | head -30
```

Le CRLF mérite un mot : `.gitattributes` force les fins de ligne UNIX pour
`*.sh`, mais **ne couvre ni `*.service` ni `*.plist`**. Un dépôt cloné sous
Windows puis copié sur un serveur peut donc livrer un gabarit en CRLF, ce qui
produit un `ExecStart` pointant sur `serveur.py\r` — introuvable, avec un
message qui affiche pourtant le bon nom. `installer_service.sh` retire les CR
au moment de remplir le gabarit ; c'est aussi pour cela qu'il vaut mieux passer
par lui que copier les fichiers à la main.

---

## 7. Mise à jour de ComfyStudio

```sh
cd /opt/ComfyStudio && sudo git pull
sudo systemctl restart comfystudio
```

Relancer `installer_service.sh` après une mise à jour est sans danger : il
**n'écrase jamais** `/etc/comfystudio.env`, il recrée seulement l'unité. C'est
délibéré — une réinstallation qui efface `STUDIO_ADMIN_MDP` redémarrerait un
studio qui refuse tout le monde. Pour repartir des valeurs par défaut, supprime
le fichier d'abord.

`--desinstaller` retire l'unité ou l'agent et **ne touche ni au compte de
service, ni au dossier de données, ni au fichier d'environnement**. Une
désinstallation qui efface les conversations serait une perte de données
déguisée en nettoyage. Le script rappelle ce qu'il laisse derrière lui.

---

## 8. Ce qui a été vérifié, et ce qui ne l'a pas été

Écrit sous Windows pour Linux et macOS ; l'honnêteté impose de distinguer.

**Vérifié mécaniquement :**

- `installer_service.sh` passe `sh -n` et `bash --posix -n` — aucune erreur de
  syntaxe, aucun bashisme de structure.
- `com.comfystudio.plist` est un XML bien formé et se charge avec `plistlib`
  (le module de référence, celui qui lit ce que lit macOS) ; toutes les clés
  attendues sont présentes et typées correctement.
- Le remplissage des deux gabarits a été rejoué à blanc, y compris avec un
  chemin macOS contenant une **espace** (`Application Support`) et avec un
  groupe différent du nom d'utilisateur : aucun jeton ne subsiste, et le
  résultat reste un plist valide.
- L'unité systemd a été contrôlée dans sa forme : sections `[Unit]`,
  `[Service]`, `[Install]`, aucune ligne hors commentaire sans `=`.
- Les chemins écrits par `serveur.py` ont été relus dans le code source, pas
  supposés : c'est de là que vient le choix de `ProtectSystem=full`.

**Non vérifié, faute de machine :**

- aucun démarrage réel de service, sur aucun système ;
- le durcissement n'a pas été confronté à l'exécution : si une directive gêne le
  studio, cela se verra au premier lancement. `systemd-analyze verify` est lancé
  par l'installeur et affiche ce qu'il trouve ;
- le comportement de SELinux est décrit d'après la règle générale, non observé
  sur cette installation ;
- les numéros de version du tableau §3.1 sont donnés de mémoire, à vérifier avec
  `systemctl --version` sur la machine concernée.
