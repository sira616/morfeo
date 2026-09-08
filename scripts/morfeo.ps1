# Arranca Morfeo: un proceso, un puerto, servido a la wifi de casa.
#
# El backend sirve también el frontend construido, así que no hay dos servidores ni
# proxy que mantener. Si el build no existe, avisa y arranca solo la API en vez de
# negarse: quedarse sin app por un `npm run build` que falta sería peor.
#
# Se ejecuta solo al iniciar sesión (ver scripts/instalar-arranque.ps1).

$ErrorActionPreference = 'Stop'

$backend = Split-Path -Parent $PSScriptRoot
$frontendDist = Join-Path (Split-Path -Parent $backend) 'morfeo-frontend\dist'
$python = Join-Path $backend 'venv\Scripts\python.exe'
$port = 8000

if (-not (Test-Path $python)) {
    Write-Error "No existe el entorno virtual en $python. Crea el venv e instala requirements.txt."
}

if (-not (Test-Path (Join-Path $frontendDist 'index.html'))) {
    Write-Warning "No hay build del frontend en $frontendDist."
    Write-Warning "Ejecuta 'npm run build' en morfeo-frontend. Mientras tanto solo responde la API."
}

Set-Location $backend
$env:FRONTEND_DIST = $frontendDist

# 0.0.0.0 y no 127.0.0.1: sin esto el móvil no llega, por mucho que el firewall esté
# abierto. Es una red doméstica y la app pide autenticación en cada ruta.
& $python -m uvicorn app.main:app --host 0.0.0.0 --port $port
