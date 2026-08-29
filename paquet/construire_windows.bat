@echo off
REM ====================================================================
REM  ComfyStudio -- construction de l'executable Windows unique
REM
REM  Produit paquet\dist\ComfyStudio.exe : 44 818 543 octets mesures,
REM  17 517 471 octets si PAQUET_SANS_AV=1. Environ 40 s de construction.
REM  A lancer depuis n'importe ou : le script se replace tout seul.
REM ====================================================================
setlocal

REM Le dossier de ce .bat, sans la barre finale : tous les chemins en
REM dependent, et lancer le script par un double-clic depuis l'explorateur
REM place le repertoire courant sur C:\Windows\system32.
set PAQUET=%~dp0
cd /d "%PAQUET%"

REM Le Python embarque de ComfyUI. C'est le meme interpreteur que celui qui
REM fait tourner le studio au quotidien : construire avec un autre Python
REM produirait un exe lie a une version d'aiohttp qui n'est pas celle testee.
set PY=%PAQUET%..\..\ComfyUI_windows_portable\python_embeded\python.exe
if not exist "%PY%" (
    echo [erreur] Python embarque introuvable : %PY%
    echo          Corrigez la variable PY en tete de ce script.
    exit /b 1
)

REM PyInstaller n'est pas une dependance du studio : on ne l'installe qu'ici,
REM et seulement s'il manque, pour ne pas retelecharger a chaque construction.
"%PY%" -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [1/3] Installation de PyInstaller...
    "%PY%" -m pip install pyinstaller
    if errorlevel 1 (
        echo [erreur] pip a echoue. Le Python embarque n'a peut-etre pas pip.
        exit /b 1
    )
) else (
    echo [1/3] PyInstaller deja present.
)

REM Un build/ herite d'une version precedente garde en cache la liste des
REM modules analyses : un fichier de donnees retire de la spec resterait dans
REM l'exe. On repart propre, la construction ne dure que ~40 s.
echo [2/3] Nettoyage de build\ et dist\...
if exist "%PAQUET%build" rmdir /s /q "%PAQUET%build"
if exist "%PAQUET%dist"  rmdir /s /q "%PAQUET%dist"

echo [3/3] Construction...
REM --distpath/--workpath : sans eux PyInstaller ecrit dist\ et build\ dans le
REM repertoire courant, ce qui a deja pollue la racine du depot.
REM Pour un exe leger sans PyAV : set PAQUET_SANS_AV=1 avant de lancer ce .bat.
"%PY%" -m PyInstaller --noconfirm ^
    --distpath "%PAQUET%dist" ^
    --workpath "%PAQUET%build" ^
    "%PAQUET%comfystudio.spec"
if errorlevel 1 (
    echo [erreur] La construction a echoue.
    exit /b 1
)

echo.
echo Termine : %PAQUET%dist\ComfyStudio.exe
for %%F in ("%PAQUET%dist\ComfyStudio.exe") do echo Taille : %%~zF octets
echo.
echo Rappel : l'exe ecrit ses donnees (dossier conversations, noeuds.json,
echo   avis.jsonl, dossier sorties) A COTE DE LUI -- c'est ICI_DATA dans
echo   serveur.py, corrige et verifie. Le poser dans D:\ComfyStudio\ pour
echo   qu'il retrouve son voisin ComfyUI_windows_portable ; le laisser dans
echo   dist le fait chercher ComfyUI dans paquet. Voir NOTES.md.
endlocal
