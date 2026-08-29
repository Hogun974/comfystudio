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

    La tache se relance toute seule si l'agent s'arrete : c'est la difference
    entre « lance au demarrage » et « en service ».

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
Write-Host "  se lance a l'ouverture de session, 45 s apres, et se relance si elle tombe"
