@echo off
REM Installe ou met a jour l'agent sur une machine-noeud (Windows).
REM
REM L'agent est servi par le studio lui-meme : mettre a jour un parc de machines
REM revient a relancer ce fichier sur chacune.
REM
REM   maj_noeud.bat http://192.0.2.10:8199            met a jour l agent
REM   maj_noeud.bat http://192.0.2.10:8199 JETON      installe puis demarre
REM   maj_noeud.bat http://192.0.2.10:8199 JETON EMPREINTE
REM
REM Ce fichier telecharge du code Python et l'execute. En HTTP simple, quiconque
REM s'intercale sur le reseau choisit ce code. Le troisieme argument, ou
REM AGENT_EMPREINTE, est le sha256 attendu : il n'aide que s'il a ete releve
REM AILLEURS que sur ce meme lien, par "sha256sum agent_noeud.py" sur l'hote
REM du studio. L'empreinte installee est affichee dans tous les cas.
setlocal enabledelayedexpansion
title Agent ComfyStudio - mise a jour
cd /d "%~dp0"

set STUDIO=%~1
set JETON=%~2
set EMPREINTE=%~3
if "%EMPREINTE%"=="" set EMPREINTE=%AGENT_EMPREINTE%

if "%STUDIO%"=="" (
  echo.
  echo   Adresse du studio manquante :
  echo     maj_noeud.bat http://192.0.2.10:8199 [JETON]
  echo.
  pause & exit /b 1
)

REM On verifie la VERSION, pas seulement la presence : un Python 2 demarre
REM parfaitement puis echoue sur la premiere f-string de l'agent.
set PY=..\ComfyUI_windows_portable\python_embeded\python.exe
if exist "%PY%" call :essayer "%PY%" && goto :ok
where py >nul 2>nul && (call :essayer py && goto :ok)
where python >nul 2>nul && (call :essayer python && goto :ok)
echo   Aucun Python 3.8 ou plus recent : winget install Python.Python.3.12
pause & exit /b 1

:essayer
"%~1" -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" 2>nul
if errorlevel 1 exit /b 1
set PY=%~1
exit /b 0

:ok
echo   telechargement de l'agent depuis %STUDIO%
powershell -NoProfile -Command ^
  "try { Invoke-WebRequest -UseBasicParsing '%STUDIO%/api/noeud/agent' -OutFile 'agent_noeud.py.neuf' } catch { exit 1 }"
if errorlevel 1 (
  echo   studio injoignable : %STUDIO%
  pause & exit /b 1
)

REM On ne remplace qu'apres verification : une page d'erreur du studio
REM ecraserait sinon un agent qui fonctionnait.
REM Le sha256 n'est imprime que si le fichier est du Python analysable : une
REM variable vide dit les deux echecs a la fois. "for /f" ne rapporte pas le
REM code de sortie de ce qu'il lance, il ne faut donc pas s'y fier.
REM Entre guillemets, et relu en !VERIF! : developpe en %VERIF%, le ".read()"
REM du code arrive dans les parentheses du "for" comme un bloc vide, et cmd
REM refuse la ligne entiere. La lecture retardee developpe apres l'analyse.
set "VERIF=import ast,hashlib,sys;o=open(sys.argv[1],'rb').read();ast.parse(o.decode('utf-8'));print(hashlib.sha256(o).hexdigest())"
set EMP=
for /f "delims=" %%h in ('""%PY%" -c "!VERIF!" agent_noeud.py.neuf" 2^>nul') do set EMP=%%h
if not defined EMP (
  echo   ce que le studio a renvoye n'est pas un script valide - rien remplace
  del agent_noeud.py.neuf
  pause & exit /b 1
)
if not "%EMPREINTE%"=="" if /i not "%EMP%"=="%EMPREINTE%" (
  echo   EMPREINTE INATTENDUE - rien remplace
  echo     recue    : %EMP%
  echo     attendue : %EMPREINTE%
  del agent_noeud.py.neuf
  pause & exit /b 1
)
if exist agent_noeud.py copy /y agent_noeud.py agent_noeud.py.precedent >nul
move /y agent_noeud.py.neuf agent_noeud.py >nul
echo   agent a jour - sha256 %EMP%

if not "%JETON%"=="" (
  "%PY%" agent_noeud.py --studio %STUDIO% --jeton %JETON%
  pause & exit /b 0
)
echo.
echo   Pour le demarrer :
echo     %PY% agent_noeud.py --studio %STUDIO% --jeton TON_JETON
echo   (le jeton se cree dans %STUDIO%/admin)
echo.
pause
