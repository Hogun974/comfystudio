@echo off
REM Met une machine Windows au service d'un ComfyStudio, d'un seul geste.
REM
REM Verifie ce qu'il faut, demarre ComfyUI s'il dort, recupere l'agent aupres
REM du studio, demande le jeton, et se met en service. Concu pour etre le seul
REM fichier a poser sur une machine-noeud.
REM
REM   noeud.bat                              tout, en posant les questions
REM   noeud.bat --verifier                   diagnostic, sans rien lancer
REM   noeud.bat --studio URL --jeton XXXX    sans aucune question
REM   noeud.bat --fond                       laisse tourner en tache de fond
REM
REM Ce fichier est volontairement en ASCII strict : cmd.exe le lit dans la page
REM de codes de la console, ou tout accent devient illisible.
setlocal enabledelayedexpansion
title Noeud ComfyStudio
cd /d "%~dp0"

set "STUDIO="
set "JETON="
set "VERIFIER=0"
set "FOND=0"
if not defined COMFY_URL set "COMFY_URL=http://127.0.0.1:8188"
set "CONFIG=agent_noeud.json"
set "AGENT=agent_noeud.py"
set /a ENNUIS=0

:args
if "%~1"=="" goto :etape_python
REM Des etiquettes plutot que des blocs entre parentheses : cmd analyse un
REM bloc entier avant de l'executer, et shift y perd son effet.
if /i "%~1"=="--studio" goto :a_studio
if /i "%~1"=="--jeton" goto :a_jeton
if /i "%~1"=="--comfy" goto :a_comfy
if /i "%~1"=="--verifier" goto :a_verifier
if /i "%~1"=="--fond" goto :a_fond
echo   argument inconnu : %~1
exit /b 1

:a_studio
set "STUDIO=%~2"
shift
shift
goto :args

:a_jeton
set "JETON=%~2"
shift
shift
goto :args

:a_comfy
set "COMFY_URL=%~2"
shift
shift
goto :args

:a_verifier
set "VERIFIER=1"
shift
goto :args

:a_fond
set "FOND=1"
shift
goto :args


:etape_python
echo.
echo Python
echo ------
REM On verifie la VERSION, pas seulement la presence : un Python 2 demarre
REM parfaitement puis echoue sur la premiere f-string de l'agent.
set "PY="
if exist "..\ComfyUI_windows_portable\python_embeded\python.exe" call :essayer "..\ComfyUI_windows_portable\python_embeded\python.exe"
if not defined PY where py >nul 2>nul && call :essayer py
if not defined PY where python >nul 2>nul && call :essayer python
if not defined PY (
  echo   [X] aucun Python 3.8 ou plus recent
  echo       winget install Python.Python.3.12
  pause
  exit /b 1
)
for /f "delims=" %%v in ('""%PY%" -V" 2^>^&1') do echo   [ok] %%v


echo.
echo Materiel
echo --------
where nvidia-smi >nul 2>nul
if errorlevel 1 (
  call :souci "nvidia-smi introuvable : pas de carte NVIDIA utilisable"
  echo       ComfyUI tournerait sur le processeur, tres lentement
) else (
  set "CARTE="
  for /f "delims=" %%c in ('nvidia-smi --query-gpu^=name^,memory.total --format^=csv^,noheader 2^>nul') do if not defined CARTE set "CARTE=%%c"
  if defined CARTE (
    echo   [ok] carte : !CARTE!
  ) else (
    call :souci "nvidia-smi ne rend aucune carte"
  )
)
for /f "delims=" %%m in ('powershell -NoProfile -Command "[int]((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB)" 2^>nul') do echo   [ok] memoire : %%m Go
for /f "delims=" %%d in ('powershell -NoProfile -Command "[int]((Get-PSDrive (Get-Location).Drive.Name).Free/1GB)" 2^>nul') do echo   [ok] disque : %%d Go libres ici


echo.
echo ComfyUI
echo -------
call :joignable
if "%VIVANT%"=="1" (
  echo   [ok] deja en service sur %COMFY_URL%
  goto :apres_comfy
)

set "RACINE=%COMFY_DIR%"
if not defined RACINE (
  for %%r in ("ComfyUI" "..\ComfyUI" "..\ComfyUI_windows_portable\ComfyUI" "%USERPROFILE%\ComfyUI") do (
    if exist "%%~r\main.py" if not defined RACINE set "RACINE=%%~r"
  )
)
if not defined RACINE (
  call :souci "ComfyUI introuvable"
  echo       indique-le : set COMFY_DIR=C:\chemin\vers\ComfyUI
  goto :apres_comfy
)
echo       trouve dans %RACINE%
if "%VERIFIER%"=="1" (
  call :souci "il ne repond pas - mode verification, on ne le demarre pas"
  goto :apres_comfy
)

set "rep="
set /p "rep=  Le demarrer maintenant ? [O/n] "
if /i "%rep%"=="n" (
  call :souci "ComfyUI arrete : l'agent attendra qu'il reponde"
  goto :apres_comfy
)
REM le lanceur personnalise s'il existe : il porte les reglages de la machine
set "LANCEUR="
for %%b in ("%RACINE%\..\LANCER ComfyUI*.bat") do if not defined LANCEUR set "LANCEUR=%%~fb"
if defined LANCEUR (
  echo       demarrage par !LANCEUR!
  start "ComfyUI" /min "!LANCEUR!"
) else (
  echo       demarrage de %RACINE%\main.py
  start "ComfyUI" /min "%PY%" "%RACINE%\main.py" --disable-auto-launch
)
for /l %%i in (1,1,60) do (
  call :joignable
  if "!VIVANT!"=="1" goto :comfy_pret
  timeout /t 2 /nobreak >nul
)
:comfy_pret
call :joignable
if "%VIVANT%"=="1" (
  echo   [ok] ComfyUI repond sur %COMFY_URL%
) else (
  call :souci "ComfyUI n'a pas repondu en deux minutes"
)

:apres_comfy
call :joignable
if "%VIVANT%"=="1" for /f "delims=" %%n in ('powershell -NoProfile -Command "try{ (Invoke-RestMethod -TimeoutSec 6 '%COMFY_URL%/models/diffusion_models').Count } catch { 0 }" 2^>nul') do echo       modeles de diffusion vus : %%n


echo.
echo Studio
echo ------
REM Les parentheses du Python embarque fermeraient un bloc if : on lit
REM donc la configuration au premier niveau, jamais entre parentheses.
if defined STUDIO goto :studio_su
if not exist "%CONFIG%" goto :studio_su
for /f "delims=" %%s in ('""%PY%" -c "import json,io;print^(json.load^(io.open^('%CONFIG%'^)^).get^('studio',''^)^)"" 2^>nul') do set "STUDIO=%%s"
if defined STUDIO echo       adresse retenue du dernier lancement
:studio_su
if defined STUDIO goto :studio_connu
if "%VERIFIER%"=="1" goto :studio_connu
echo       exemple : http://192.0.2.10:8199
set /p "STUDIO=  Adresse du studio : "
:studio_connu
if not defined STUDIO (
  call :souci "aucune adresse de studio"
  goto :etape_agent
)
if "%STUDIO:~-1%"=="/" set "STUDIO=%STUDIO:~0,-1%"
powershell -NoProfile -Command "try{ Invoke-WebRequest -UseBasicParsing -TimeoutSec 6 '%STUDIO%/api/compte' | Out-Null; exit 0 } catch { exit 1 }" >nul 2>nul
if errorlevel 1 (
  call :souci "studio injoignable sur %STUDIO%"
  echo       verifie qu'il tourne avec STUDIO_HOTE=0.0.0.0, et le pare-feu
) else (
  echo   [ok] studio joignable sur %STUDIO%
)


:etape_agent
echo.
echo Agent
echo -----
if exist "%AGENT%.neuf" del "%AGENT%.neuf"
if defined STUDIO powershell -NoProfile -Command "try{ Invoke-WebRequest -UseBasicParsing -TimeoutSec 20 '%STUDIO%/api/noeud/agent' -OutFile '%AGENT%.neuf'; exit 0 } catch { exit 1 }" >nul 2>nul
if exist "%AGENT%.neuf" (
  REM On ne remplace qu'apres verification : une page d'erreur du studio
  REM ecraserait sinon un agent qui fonctionnait.
  "%PY%" -c "import ast;ast.parse(open('%AGENT%.neuf',encoding='utf-8').read())" >nul 2>nul
  if errorlevel 1 (
    del "%AGENT%.neuf"
    call :souci "ce que le studio a renvoye n'est pas un script valide"
  ) else (
    if exist "%AGENT%" copy /y "%AGENT%" "%AGENT%.precedent" >nul
    move /y "%AGENT%.neuf" "%AGENT%" >nul
    echo   [ok] agent a jour
  )
) else (
  if exist "%AGENT%" (
    echo       telechargement impossible : on garde l'agent deja present
  ) else (
    call :souci "agent absent et non telechargeable"
  )
)
if defined JETON goto :jeton_su
if not exist "%CONFIG%" goto :jeton_su
for /f "delims=" %%j in ('""%PY%" -c "import json,io;print^(json.load^(io.open^('%CONFIG%'^)^).get^('jeton',''^)^)"" 2^>nul') do set "JETON=%%j"
if defined JETON echo   [ok] jeton retenu du dernier lancement
:jeton_su


echo.
echo Verdict
echo -------
if "%VERIFIER%"=="1" (
  if %ENNUIS%==0 (
    echo   [ok] tout est pret
  ) else (
    echo   [X] %ENNUIS% points a regler
  )
  pause
  exit /b %ENNUIS%
)
if not %ENNUIS%==0 (
  echo   [X] %ENNUIS% points a regler avant de se mettre en service
  pause
  exit /b 1
)
echo   [ok] tout est pret

if not defined JETON (
  echo.
  echo   Le jeton se cree dans %STUDIO%/admin, sur la machine du studio.
  echo   Il n'est affiche qu'une seule fois, a la creation de la machine.
  REM saisie masquee : le jeton ne reste pas affiche a l'ecran
  for /f "delims=" %%j in ('powershell -NoProfile -Command "$s=Read-Host -AsSecureString '  Jeton'; [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($s))"') do set "JETON=%%j"
)
if not defined JETON (
  echo   [X] aucun jeton : rien a faire
  pause
  exit /b 1
)

echo.
echo En service
echo ----------
REM Le jeton passe par le fichier de reglages, pas par la ligne de commande :
REM celle d'un processus est lisible par tout le monde sur la machine, ce qui
REM annulait le masquage de la saisie.
"%PY%" -c "import json,io,os;f=os.environ['CONFIG'];c=json.load(io.open(f,encoding='utf-8')) if os.path.exists(f) else {};c.update(studio=os.environ['STUDIO'],jeton=os.environ['JETON'],comfy=os.environ['COMFY_URL']);json.dump(c,io.open(f,'w',encoding='utf-8'),indent=1)"
if "%FOND%"=="1" (
  start "Agent ComfyStudio" /min "%PY%" "%AGENT%"
  echo   [ok] agent lance dans une fenetre reduite
  timeout /t 3 /nobreak >nul
  exit /b 0
)
"%PY%" "%AGENT%"
pause
exit /b 0


:essayer
"%~1" -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>nul
if errorlevel 1 exit /b 1
set "PY=%~1"
exit /b 0

:joignable
set "VIVANT=0"
powershell -NoProfile -Command "try{ Invoke-WebRequest -UseBasicParsing -TimeoutSec 4 '%COMFY_URL%/system_stats' | Out-Null; exit 0 } catch { exit 1 }" >nul 2>nul
if not errorlevel 1 set "VIVANT=1"
exit /b 0

:souci
echo   [X] %~1
set /a ENNUIS+=1
exit /b 0
