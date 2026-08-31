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
REM   noeud.bat --sorties CHEMIN             output de ComfyUI, pour le menage
REM   noeud.bat --fond                       laisse tourner en tache de fond
REM   noeud.bat --empreinte SHA256           n'installe que cet agent-la
REM   noeud.bat --ollama URL                 ou joindre le modele de langage
REM
REM Ce fichier telecharge du code Python et l'execute. En HTTP simple, quiconque
REM s'intercale sur le reseau choisit ce code. --empreinte (ou AGENT_EMPREINTE)
REM n'aide que si le sha256 a ete releve AILLEURS que sur ce meme lien, par
REM "sha256sum agent_noeud.py" sur l'hote du studio.
REM
REM Ce fichier est volontairement en ASCII strict : cmd.exe le lit dans la page
REM de codes de la console, ou tout accent devient illisible.
setlocal enabledelayedexpansion
title Noeud ComfyStudio
cd /d "%~dp0"

set "STUDIO="
set "JETON="
set "SORTIES="
set "VERIFIER=0"
set "FOND=0"
if not defined EMPREINTE set "EMPREINTE=%AGENT_EMPREINTE%"
if not defined COMFY_URL set "COMFY_URL=http://127.0.0.1:8188"
if not defined OLLAMA_URL set "OLLAMA_URL=http://127.0.0.1:11434"
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
if /i "%~1"=="--ollama" goto :a_ollama
if /i "%~1"=="--sorties" goto :a_sorties
if /i "%~1"=="--verifier" goto :a_verifier
if /i "%~1"=="--fond" goto :a_fond
if /i "%~1"=="--empreinte" goto :a_empreinte
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

:a_empreinte
set "EMPREINTE=%~2"
shift
shift
goto :args

:a_ollama
set "OLLAMA_URL=%~2"
shift
shift
goto :args

:a_comfy
set "COMFY_URL=%~2"
shift
shift
goto :args

:a_sorties
set "SORTIES=%~2"
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
echo Modele de langage
echo -----------------
REM Le studio emprunte le modele de langage de CETTE machine pour analyser une
REM demande. Depuis qu'une carte ne fait qu'une tache a la fois, en avoir un ici
REM change la donne : la petite carte reflechit pendant que la grosse rend. Sans
REM Ollama nulle part sauf sur une machine, toutes les analyses passent par elle.
REM
REM Le modele conseille depend de la carte : au-dela du plafond, Ollama deborde
REM sur la RAM et l'analyse, qui precede CHAQUE rendu, met des minutes.
set "CONSEIL=qwen3:4b"
set "GOCARTE="
for /f "delims=" %%g in ('nvidia-smi --query-gpu^=memory.total --format^=csv^,noheader^,nounits 2^>nul') do if not defined GOCARTE set /a "GOCARTE=%%g/1024"
if defined GOCARTE (
  if !GOCARTE! GEQ 6 set "CONSEIL=qwen3:8b"
  if !GOCARTE! GEQ 11 set "CONSEIL=gemma3:12b"
  if !GOCARTE! GEQ 20 set "CONSEIL=gemma3:27b"
)
set "NBMOD="
for /f "delims=" %%o in ('powershell -NoProfile -Command "try{ (Invoke-RestMethod -TimeoutSec 6 '%OLLAMA_URL%/api/tags').models.Count } catch { -1 }" 2^>nul') do set "NBMOD=%%o"
REM Trois ifs et un drapeau, plutot qu'un « else if » enchaine : cmd rattache
REM le « else » au SECOND if, et l'on saute alors le cas qu'on croyait traiter.
REM Le piege a deja coute une soiree sur ce meme fichier.
if not defined NBMOD set "NBMOD=-1"
if "!NBMOD!"=="-1" (
  call :souci "aucun Ollama sur !OLLAMA_URL!"
  echo       cette machine ne pourra pas analyser : le studio le fera ailleurs
  echo       a installer depuis https://ollama.com/download
  echo       puis :  ollama pull !CONSEIL!
)
if "!NBMOD!"=="0" (
  call :souci "Ollama repond mais n'a aucun modele"
  echo       ollama pull !CONSEIL!
)
if not "!NBMOD!"=="-1" if not "!NBMOD!"=="0" (
  echo   [ok] Ollama repond sur !OLLAMA_URL! - !NBMOD! modele^(s^)
)

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
  REM ecraserait sinon un agent qui fonctionnait. Le sha256 n'est imprime que
  REM si le fichier est du Python analysable : une variable vide dit les deux
  REM echecs a la fois, et "for /f" ne rapporte pas le code de sortie de ce
  REM qu'il lance.
  set "VERIF=import ast,hashlib,sys;o=open(sys.argv[1],'rb').read();ast.parse(o.decode('utf-8'));print(hashlib.sha256(o).hexdigest())"
  set "EMP="
  for /f "delims=" %%h in ('""%PY%" -c "!VERIF!" "%AGENT%.neuf"" 2^>nul') do set "EMP=%%h"
  REM Un motif "else if" enchaine aurait saute l'installation quand aucune
  REM empreinte n'est exigee : le "else" se serait rattache au second "if".
  set "REFUS="
  if not defined EMP set "REFUS=ce que le studio a renvoye n'est pas un script valide"
  if defined EMP if defined EMPREINTE if /i not "!EMP!"=="%EMPREINTE%" set "REFUS=empreinte inattendue : !EMP! au lieu de %EMPREINTE% - rien remplace"
  if defined REFUS (
    del "%AGENT%.neuf"
    call :souci "!REFUS!"
  ) else (
    if exist "%AGENT%" copy /y "%AGENT%" "%AGENT%.precedent" >nul
    move /y "%AGENT%.neuf" "%AGENT%" >nul
    echo   [ok] agent a jour - sha256 !EMP!
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
"%PY%" -c "import json,io,os;f=os.environ['CONFIG'];c=json.load(io.open(f,encoding='utf-8')) if os.path.exists(f) else {};c.update(studio=os.environ['STUDIO'],jeton=os.environ['JETON'],comfy=os.environ['COMFY_URL']);c.update(sorties=os.environ['SORTIES']) if os.environ.get('SORTIES') else None;json.dump(c,io.open(f,'w',encoding='utf-8'),indent=1)"
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
