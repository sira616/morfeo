# Reinicia Morfeo de verdad.
#
# `Stop-ScheduledTask` no siempre se lleva por delante al uvicorn: queda escuchando en
# el puerto, el arranque nuevo no puede enlazarlo y muere en silencio. El resultado es
# el peor posible, porque el servidor responde —el viejo— y parece que el reinicio ha
# funcionado, mientras sigue sirviendo el código anterior.
#
#     powershell -ExecutionPolicy Bypass -File scripts\reiniciar.ps1

$ErrorActionPreference = 'Stop'
$port = 8000

Stop-ScheduledTask -TaskName Morfeo -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Se mata por puerto, no por nombre de proceso: es lo único que garantiza que el
# arranque siguiente pueda enlazar.
$listeners = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
foreach ($listener in $listeners) {
    Write-Host "Cerrando el proceso $($listener.OwningProcess), que aun escuchaba en el $port."
    Stop-Process -Id $listener.OwningProcess -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 2

Start-ScheduledTask -TaskName Morfeo
Start-Sleep -Seconds 6

try {
    $health = Invoke-WebRequest "http://127.0.0.1:$port/health" -UseBasicParsing -TimeoutSec 5
    $started = (Get-Process -Id (Get-NetTCPConnection -LocalPort $port -State Listen).OwningProcess).StartTime
    Write-Host "Morfeo responde ($($health.StatusCode)). Proceso iniciado a las $started." -ForegroundColor Green
} catch {
    Write-Warning "Morfeo no responde: $($_.Exception.Message)"
    Write-Warning "Mira la tarea 'Morfeo' en el Programador de tareas."
}
