@echo off
title ComfyStudio
cd /d "%~dp0"

REM Le Python embarque de ComfyUI d'abord : c'est le cas le plus frequent, rien
REM n'est installe sur la machine, et il ne coute qu'un test de presence.
set "PY=%~dp0..\ComfyUI_windows_portable\python_embeded\python.exe"
if exist "%PY%" goto :python_trouve

REM CE CHEMIN ETAIT LE SEUL, ET LE LANCEUR SORTAIT EN 1 SINON. Or l'installeur
REM n'installe pas cela : installer_comfyui() clone dans ..\ComfyUI et lui monte
REM un venv, et _candidats_comfy() accepte HUIT emplacements. Suivre le README a
REM la lettre sous Windows - installer.bat puis ce fichier - echouait donc sur
REM "Python embarque introuvable", alors qu'un interpreteur parfaitement bon
REM etait la.
REM
REM On ne rajoute pas une seconde liste d'emplacements ici : elle deriverait de
REM celle de l'installeur des la premiere retouche. On lui POSE la question -
REM installation.py:python_du_studio(), la fonction que "--dependances" emploie
REM deja quelques lignes plus bas pour savoir quel interpreteur equiper. Les deux
REM repondent ainsi toujours la meme chose, ce qui est tout le probleme que ce
REM commentaire-la decrit : "un paquet pose dans le mauvais Python produit un
REM Successfully installed suivi d'un ImportError au demarrage".
REM
REM Il faut un interpreteur pour poser la question : n'importe lequel fait
REM l'affaire, installer.py etant ecrit dans une syntaxe que meme Python 2 lit et
REM refusant poliment les versions trop vieilles.
set "AMORCE="
for %%p in (py.exe python.exe python3.exe) do if not defined AMORCE set "AMORCE=%%~$PATH:p"
if not defined AMORCE goto :sans_python
set "PY="
for /f "delims=" %%p in ('""%AMORCE%" installer.py --python-du-studio"') do set "PY=%%p"
if not defined PY goto :sans_python
if not exist "%PY%" goto :sans_python
echo Python du studio : %PY%
goto :python_trouve

:sans_python
echo.
echo   Aucun Python utilisable n'a ete trouve.
echo   Cherche : %~dp0..\ComfyUI_windows_portable\python_embeded\python.exe
echo             puis py, python, python3 dans le PATH.
echo.
echo   Lance installer.bat (il installe ComfyUI et ce qu'il faut), ou installe
echo   Python 3.8 ou plus recent depuis python.org.
echo.
pause & exit /b 1

:python_trouve

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
