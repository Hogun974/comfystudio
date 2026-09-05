@echo off
REM ====================================================================
REM  ComfyStudio -- construction de l'executable Windows unique
REM
REM  Produit paquet\dist\ComfyStudio.exe : 45 120 925 octets mesures le
REM  5 septembre 2026, 17 817 972 si PAQUET_SANS_AV=1. Environ 29 s de
REM  construction a froid, 23 s ensuite.
REM
REM  CES NOMBRES SONT DATES, ET C'EST VOLONTAIRE. Ceux d'avant — 44 818 543,
REM  17 517 471, « environ 40 s » — dataient du 30 aout et avaient derive de
REM  244 ko sans que rien ne le dise : un nombre sans date ne vieillit pas, il
REM  ment. Deux constructions identiques le meme jour donnent d'ailleurs
REM  45 120 779 et 45 120 925 octets : a 146 octets pres, ce n'est pas
REM  reproductible au bit.
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
set "PY=%PAQUET%..\..\ComfyUI_windows_portable\python_embeded\python.exe"
if exist "%PY%" goto :python_trouve

REM Le meme chemin en dur que celui de "LANCER ComfyStudio.bat", et le meme
REM defaut : le dossier portable n'est pas toujours a cote du studio, et
REM l'installeur, lui, sait ou il a mis les choses. On lui demande plutot que de
REM tenir ici une seconde liste d'emplacements, qui deriverait de la sienne.
set "AMORCE="
for %%p in (py.exe python.exe python3.exe) do if not defined AMORCE set "AMORCE=%%~$PATH:p"
if not defined AMORCE goto :sans_python
set "PY="
for /f "delims=" %%p in ('""%AMORCE%" "%PAQUET%..\installer.py" --python-du-studio"') do set "PY=%%p"
if not defined PY goto :sans_python
if not exist "%PY%" goto :sans_python
REM Et on le DIT, parce que ce n'est pas forcement equivalent : l'exe sera lie a
REM l'aiohttp de CET interpreteur-la. L'installeur retrouve souvent le meme
REM Python embarque a un autre endroit - il en connait huit - mais il peut aussi
REM rendre celui du PATH, et le message ne peut pas trancher a la place de qui
REM construit.
echo [attention] le ComfyUI portable n'est pas a l'emplacement attendu.
echo             L'installeur designe : %PY%
echo             Si ce n'est pas le Python qui fait tourner le studio,
echo             verifiez la version d'aiohttp avant de distribuer l'exe.
goto :python_trouve

:sans_python
echo [erreur] Aucun Python utilisable trouve.
echo          Cherche : %PAQUET%..\..\ComfyUI_windows_portable\python_embeded\python.exe
echo                    puis py, python, python3 dans le PATH.
exit /b 1

:python_trouve

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

REM CE QUE CET EXE ANNONCERA. On RELIT le fichier que la spec vient de graver
REM plutot que de relancer git : c'est ce qui est reellement dans l'exe, et non
REM ce que le depot vaut a la seconde ou l'on regarde. Un fichier vide -- git
REM absent, ou source qui n'est pas un clone -- ne remplit pas la variable, et
REM l'exe dira « inconnue » au demarrage : c'est la verite, pas une panne.
set "VERSION=inconnue"
if exist "%PAQUET%build\version.txt" (
    for /f "usebackq delims=" %%v in ("%PAQUET%build\version.txt") do set "VERSION=%%v"
)
echo Version gravee : %VERSION%   (ligne « Version » de la banniere, et /admin)
echo.
echo Rappel : l'exe ecrit ses donnees (dossier conversations, noeuds.json,
echo   avis.jsonl, dossier sorties) A COTE DE LUI -- c'est ICI_DATA dans
echo   serveur.py, corrige et verifie. Le poser dans D:\ComfyStudio\ pour
echo   qu'il retrouve son voisin ComfyUI_windows_portable ; le laisser dans
echo   dist le fait chercher ComfyUI dans paquet. Voir NOTES.md.
endlocal
