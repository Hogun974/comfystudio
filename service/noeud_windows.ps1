<#
    Met l'agent de noeud en service sur Windows.

    Une machine a carte qui ne revient pas apres un redemarrage est une machine
    perdue : le studio la declare silencieuse, envoie tout ailleurs, et personne
    ne s'en apercoit avant que la file ne traine.

    On passe par une tache planifiee « a l'ouverture de session » plutot que par
    un vrai service Windows, pour deux raisons :

      - un service tourne sans session, or ComfyUI a besoin d'un contexte
        graphique pour voir la carte sur beaucoup d'installations ;
      - creer un service demande l'elevation, une tache utilisateur non.

    LA TACHE REPASSE TOUTES LES DIX MINUTES, et c'est ce qui fait la difference
    entre « lance a l'ouverture de session » et « en service ».

    Ce fichier a longtemps annonce « la tache se relance toute seule si l'agent
    s'arrete » en ne posant que RestartOnFailure. C'etait faux deux fois, et
    mesure le 12 septembre 2026 :

      - avec --fond, le .bat detache l'agent et sort en 0. Le planificateur voit
        une REUSSITE ; l'agent qui meurt ensuite n'est plus son affaire, et il
        ne relance rien ;
      - le 10 septembre la tache est sortie en 1 a l'ouverture de session, et
        RestartOnFailure — pourtant enregistre a 999 essais toutes les minutes —
        n'a rien relance : LastRunTime est reste fige deux jours. La machine est
        restee hors du parc jusqu'a ce qu'une demande soit refusee.

    La repetition, elle, ne suppose rien de l'etat du processus : elle relance
    le lanceur, qui constate. C'est le garde d'instance unique d'agent_noeud.py
    qui rend cela sans danger — sans lui, chaque tour poserait un agent de plus,
    et MultipleInstancesPolicy n'y peut rien puisque l'instance de TACHE, elle,
    est terminee depuis longtemps.

    Usage :
        powershell -ExecutionPolicy Bypass -File service\noeud_windows.ps1 -Dossier D:\NoeudPC
        powershell -ExecutionPolicy Bypass -File service\noeud_windows.ps1 -Desinstaller
#>
param(
    [string]$Dossier = "",
    [string]$Script  = "demarrer.bat",
    [string]$Nom     = "ComfyStudio - agent de noeud",
    [switch]$Desinstaller
)

$ErrorActionPreference = "Stop"

if ($Desinstaller) {
    if (Get-ScheduledTask -TaskName $Nom -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $Nom -Confirm:$false
        Write-Host "  tache retiree : $Nom"
    } else {
        Write-Host "  aucune tache nommee « $Nom »"
    }
    exit 0
}

if (-not $Dossier) { $Dossier = (Get-Location).Path }
$lanceur = Join-Path $Dossier $Script
if (-not (Test-Path $lanceur)) {
    # Mieux vaut refuser tout de suite que d'enregistrer une tache qui echouera
    # en silence a chaque ouverture de session.
    Write-Error "  introuvable : $lanceur"
    exit 1
}

$action = New-ScheduledTaskAction -Execute "cmd.exe" `
    -Argument "/c `"$lanceur`" --fond" -WorkingDirectory $Dossier
$declencheur = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
# Un delai laisse le reseau et les services de la carte se lever : sans lui,
# l'agent teste un ComfyUI qui n'ecoute pas encore et repart en attente longue.
$declencheur.Delay = "PT45S"
# LA REPETITION EST CE QUI TIENT LA PROMESSE DE L'EN-TETE. Un declencheur
# d'ouverture de session ne se produit qu'une fois ; tout ce qui casse ensuite
# — ComfyUI pas encore leve, agent tue, mise a jour ratee — laisse la machine
# dehors jusqu'a la prochaine session. Dix minutes : assez rare pour ne rien
# couter, assez frequent pour qu'une absence ne dure pas la journee.
# On recopie la repetition d'un declencheur « Once », seul moyen de la
# construire avec ce module.
$modele = New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes 10) `
    -RepetitionDuration ([TimeSpan]::MaxValue)
$declencheur.Repetition = $modele.Repetition

$reglages = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero)
# La tache ne doit jamais etre tuee pour cause d'inactivite : un noeud passe
# l'essentiel de son temps a attendre du travail.
$reglages.IdleSettings.StopOnIdleEnd = $false
$reglages.DisallowStartIfOnBatteries = $false

if (Get-ScheduledTask -TaskName $Nom -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $Nom -Confirm:$false
}
Register-ScheduledTask -TaskName $Nom -Action $action -Trigger $declencheur `
    -Settings $reglages -Description `
    "Met cette machine au service d'un ComfyStudio : demarre ComfyUI si besoin, puis l'agent." | Out-Null

Write-Host "  tache enregistree : $Nom"
Write-Host "  dossier           : $Dossier"
Write-Host "  se lance a l'ouverture de session, 45 s apres, puis repasse toutes les 10 min"
Write-Host "  un agent deja en service refuse le doublon et sort en 0 : c'est voulu"
