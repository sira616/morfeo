# Deja Morfeo arrancado al iniciar sesión, para que sobreviva a un reinicio.
#
# Tarea programada del usuario, no servicio de Windows: un servicio necesitaría
# permisos de administrador y correría sin tu perfil, que es más de lo que hace falta
# para una app doméstica.
#
# Se ejecuta una vez:
#     powershell -ExecutionPolicy Bypass -File scripts\instalar-arranque.ps1
#
# La regla del firewall va aparte porque sí necesita administrador; el script lo dice
# al terminar si detecta que falta.

$ErrorActionPreference = 'Stop'

$name = 'Morfeo'
$script = Join-Path $PSScriptRoot 'morfeo.ps1'
$port = 8000

if (-not (Test-Path $script)) { Write-Error "No encuentro $script" }

# -WindowStyle Hidden para que no se quede una consola abierta en cada arranque.
$action = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`""
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
# Sin límite de duración: es un servidor, no un trabajo que termina. Y que no se pare
# al desconectar la corriente, que es el comportamiento por defecto en un portátil.
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger `
    -Settings $settings -Description 'Servidor local de Morfeo' -Force | Out-Null

Write-Host "Tarea '$name' registrada: arrancará al iniciar sesión." -ForegroundColor Green

$rule = Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue
if (-not $rule) {
    Write-Host ""
    Write-Warning "Falta la regla del firewall. Sin ella el movil no conecta y la pagina"
    Write-Warning "simplemente no carga, sin ningun mensaje que lo explique."
    Write-Host "Abre PowerShell COMO ADMINISTRADOR y ejecuta:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  New-NetFirewallRule -DisplayName '$name' -Direction Inbound -Action Allow ``" -ForegroundColor Cyan
    Write-Host "    -Protocol TCP -LocalPort $port -Profile Private" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "El perfil Private limita el acceso a redes marcadas como domesticas." -ForegroundColor Gray
}

Write-Host "Para arrancarlo ahora sin reiniciar:  Start-ScheduledTask -TaskName $name"
