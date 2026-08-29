@echo off
REM Lanceur Windows de l'installeur. Il ne fait que trouver un Python
REM convenable : toute la logique est dans installer.py, commune aux deux
REM systemes.
title Installeur ComfyStudio
cd /d "%~dp0"

REM On verifie la VERSION, pas seulement la presence. Un Python 2 demarre
REM parfaitement, puis echoue sur la premiere f-string avec un SyntaxError
REM qui ne dit rien de ce qui manque vraiment.
set PY=..\ComfyUI_windows_portable\python_embeded\python.exe
if exist "%PY%" call :essayer "%PY%" && goto :lancer

where py >nul 2>nul && (call :essayer py && goto :lancer)
where python >nul 2>nul && (call :essayer python && goto :lancer)

echo.
echo   Aucun Python 3.8 ou plus recent trouve.
echo   Installe-le puis relance ce fichier :
echo     winget install Python.Python.3.12
echo   ou telecharge-le sur https://www.python.org/downloads/
echo.
pause & exit /b 1

:essayer
"%~1" -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" 2>nul
if errorlevel 1 exit /b 1
set PY=%~1
exit /b 0

:lancer
REM Le studio sera lance avec ce Python-la, celui que trouve aussi
REM "LANCER ComfyStudio.bat". C'est donc dans celui-ci, et nulle part ailleurs,
REM qu'il faut poser aiohttp : installer dans un autre interpreteur donne un
REM "Successfully installed" suivi, au demarrage, d'un ImportError sur le meme
REM paquet, sans que rien ne relie les deux messages.
REM
REM On se contente de le nommer : installation.py le resout en chemin absolu en
REM le lui demandant (sys.executable), puis teste les imports et n'installe que
REM ce qui manque. Recopier cette logique ici aurait garanti qu'elle diverge de
REM celle des deux autres systemes.
set STUDIO_PYTHON=%PY%
"%PY%" installer.py %*
echo.
pause
