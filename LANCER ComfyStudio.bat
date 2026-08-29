@echo off
title ComfyStudio
cd /d "%~dp0"

REM Utilise le Python embarque de ComfyUI : rien n'est installe sur la machine.
set PY=%~dp0..\ComfyUI_windows_portable\python_embeded\python.exe
if not exist "%PY%" (
  echo Python embarque introuvable : %PY%
  echo Verifie que ComfyStudio est bien a cote de ComfyUI_windows_portable.
  pause & exit /b 1
)

REM --- Partage sur le reseau local ---
REM  0.0.0.0 : toutes les machines du reseau peuvent se connecter.
REM  127.0.0.1 : cette machine uniquement.
REM  Une connexion est exigee (compte « admin » cree au premier demarrage,
REM  espace prive, mais quiconque atteint le port peut generer et occuper le GPU.
set STUDIO_HOTE=0.0.0.0

REM --- Dependances Python ---
REM Verifiees a chaque lancement, installees seulement si elles manquent. Un
REM "pip install -r requirements.txt" inconditionnel couterait plusieurs
REM secondes et un aller-retour vers PyPI a chaque demarrage pour ne rien
REM faire ; trois "import" testes coutent moins d'une seconde et ne touchent
REM pas au reseau.
REM
REM STUDIO_PYTHON designe l'interpreteur a equiper : le meme que celui qui
REM lancera serveur.py plus bas, jamais un autre. Sans cette variable,
REM l'installeur devrait deviner, et un paquet pose dans le mauvais Python
REM produit un "Successfully installed" suivi d'un ImportError au demarrage.
REM
REM Sortie non nulle = aiohttp manque toujours : serveur.py mourrait a
REM l'import, avant meme d'ouvrir son port. Autant s'arreter ici, pendant
REM qu'une fenetre est ouverte et qu'un humain la regarde.
set STUDIO_PYTHON=%PY%
"%PY%" installer.py --dependances
if errorlevel 1 (
  echo.
  echo   Demarrage annule : voir le message ci-dessus.
  echo.
  pause & exit /b 1
)

echo Verification de ComfyUI...
"%PY%" -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8188/',timeout=3)" 2>nul
if errorlevel 1 (
  echo.
  echo   ComfyUI ne repond pas encore. Ce n'est pas bloquant :
  echo   le bouton "demarrer" en bas de la barre laterale le lance pour toi.
  echo.
)

start "" http://127.0.0.1:8199
"%PY%" -s serveur.py
pause
