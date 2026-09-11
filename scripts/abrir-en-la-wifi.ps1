# Deja Morfeo accesible desde el movil, en http://morfeo.local:8000
#
# Tres cosas, y las tres necesitan ADMINISTRADOR. Es lo unico del montaje que no se
# puede hacer sin elevar:
#
#   1. Marcar la wifi de casa como red Privada. En Publica, Windows bloquea de entrada
#      casi todo y ninguna regla con -Profile Private llega a aplicarse nunca.
#   2. Abrir el 8000/TCP, que es por donde entra la app.
#   3. Abrir el 5353/UDP, que es por donde el iPhone pregunta "quien es morfeo.local".
#      Sin esto la app responde por IP pero el nombre no resuelve, que es el fallo mas
#      desconcertante de los tres porque parece un problema del servidor.
#
# Se ejecuta una vez, en PowerShell abierto como administrador:
#
#     powershell -ExecutionPolicy Bypass -File scripts\abrir-en-la-wifi.ps1
#
# Para deshacerlo:
#     Remove-NetFirewallRule -DisplayName 'Morfeo','Morfeo mDNS'
#     Set-NetConnectionProfile -Name '<tu red>' -NetworkCategory Public

$ErrorActionPreference = 'Stop'

$puerto = 8000

$identidad = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identidad)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "Hace falta administrador. Abre PowerShell con boton derecho > Ejecutar como administrador."
}

# --- 1. La red, a Privada ------------------------------------------------------
# Solo se tocan las redes conectadas ahora mismo. "Privada" en Windows significa "me
# fio de quien esta en esta red": es lo correcto para la wifi de casa y lo que hace
# que las reglas de abajo sirvan de algo.
$perfiles = Get-NetConnectionProfile | Where-Object { $_.NetworkCategory -eq 'Public' }
foreach ($p in $perfiles) {
    Write-Host "Marcando '$($p.Name)' como red Privada (estaba como Publica)." -ForegroundColor Yellow
    Set-NetConnectionProfile -InterfaceIndex $p.InterfaceIndex -NetworkCategory Private
}
if (-not $perfiles) {
    Write-Host "Las redes conectadas ya estan como Privadas." -ForegroundColor Gray
}

# --- 2 y 3. Las dos reglas -----------------------------------------------------
function Set-ReglaMorfeo {
    param($Nombre, $Protocolo, $Puerto, $Descripcion)

    $existente = Get-NetFirewallRule -DisplayName $Nombre -ErrorAction SilentlyContinue
    if ($existente) {
        Write-Host "La regla '$Nombre' ya existia. Se deja como esta." -ForegroundColor Gray
        return
    }
    New-NetFirewallRule -DisplayName $Nombre -Direction Inbound -Action Allow `
        -Protocol $Protocolo -LocalPort $Puerto -Profile Private `
        -Description $Descripcion | Out-Null
    Write-Host "Regla '$Nombre' creada ($Protocolo/$Puerto, perfil Privado)." -ForegroundColor Green
}

Set-ReglaMorfeo -Nombre 'Morfeo' -Protocolo TCP -Puerto $puerto `
    -Descripcion 'Servidor local de Morfeo'
Set-ReglaMorfeo -Nombre 'Morfeo mDNS' -Protocolo UDP -Puerto 5353 `
    -Descripcion 'Resolucion de morfeo.local desde el movil (Bonjour)'

# --- Comprobacion --------------------------------------------------------------
Write-Host ""
try {
    $salud = Invoke-WebRequest "http://morfeo.local:$puerto/health" -UseBasicParsing -TimeoutSec 10
    Write-Host "morfeo.local responde ($($salud.StatusCode))." -ForegroundColor Green
} catch {
    Write-Warning "morfeo.local no responde todavia: $($_.Exception.Message)"
    Write-Warning "Comprueba que el servidor este arrancado (scripts\morfeo.ps1)."
}

$ip = (Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway }).IPv4Address.IPAddress
Write-Host ""
Write-Host "Desde el iPhone, en la misma wifi:  http://morfeo.local:$puerto" -ForegroundColor Cyan
Write-Host "Si tardara en cargar, la IP directa descarta el nombre:  http://${ip}:$puerto" -ForegroundColor Gray
