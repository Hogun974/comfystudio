@echo off
REM Met CETTE machine au service d'un ComfyStudio, d'un seul geste.
REM
REM COPIE CE FICHIER dans le dossier du noeud, sous le nom "demarrer.bat", et
REM change les deux lignes marquees "A REGLER". C'est lui que la tache
REM planifiee lance : service\noeud_windows.ps1 l'attend sous ce nom-la.
REM
REM Pourquoi un fichier a soi plutot que d'appeler noeud.bat directement : il
REM porte ce qui est PROPRE A LA MACHINE - l'adresse du studio, le dossier de
REM sorties de son ComfyUI - et il survit aux mises a jour de noeud.bat, que
REM l'on repose depuis le studio sans rien perdre.
REM
REM LE JETON N'EST JAMAIS ECRIT ICI. Il est lu au vol dans un fichier tenu a
REM part, pour qu'il ne traine ni dans ce fichier, ni dans un depot, ni dans
REM l'historique de la console. Ce fichier-la ne contient QUE le jeton, sur une
REM seule ligne.
REM
REM ASCII STRICT, ET PAS SEULEMENT PAR habitude : cmd.exe lit ce fichier dans
REM la page de codes de la console. Un caractere hors ASCII y devient illisible
REM a l'affichage, et dans une valeur entre guillemets il peut casser la ligne.
setlocal
cd /d "%~dp0."

REM --- A REGLER -----------------------------------------------------------
REM Ou joindre le studio, et ou lire le jeton de cette machine. Le jeton est
REM affiche UNE SEULE FOIS, a la creation de la machine dans /admin.
set "STUDIO=http://192.0.2.10:8199"
set "FICHIER_JETON=%USERPROFILE%\.identifiants\jeton-noeud"

REM Le dossier "output" du ComfyUI de cette machine. Il sert au menage des
REM fichiers deja deposes chez le studio ; laisse la ligne vide pour ne rien
REM effacer ici. Un chemin FAUX est refuse tout de suite par l'agent, plutot
REM que de faire croire a un menage qui n'aurait jamais lieu.
set "SORTIES=D:\ComfyUI_windows_portable\ComfyUI\output"
REM ------------------------------------------------------------------------

if not exist "%FICHIER_JETON%" (
  echo   [X] jeton introuvable : %FICHIER_JETON%
  echo       cree ce fichier avec, dedans, le jeton affiche par /admin
  exit /b 1
)
set /p JETON=<"%FICHIER_JETON%"
if not defined JETON (
  echo   [X] %FICHIER_JETON% est vide
  exit /b 1
)

REM LES ARGUMENTS SONT TRANSMIS PAR "%*", ET CE N'EST PAS UN DETAIL : la tache
REM planifiee lance "demarrer.bat --fond", et sans cette transmission l'agent
REM demarrerait au premier plan. Le lanceur ne rendrait jamais la main, la
REM tache resterait "en cours" pour toujours, et sa repetition ne repasserait
REM plus. "demarrer.bat --verifier" fait le diagnostic sans rien lancer.
if defined SORTIES (
  call "%~dp0noeud.bat" --studio %STUDIO% --jeton %JETON% --sorties "%SORTIES%" %*
) else (
  call "%~dp0noeud.bat" --studio %STUDIO% --jeton %JETON% %*
)
