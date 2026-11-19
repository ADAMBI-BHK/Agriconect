# Lance le backend (port 8000) et le frontend (port 3000). Ctrl+C arrête les deux.
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$py = "$root\backend\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Environnement absent : exécutez d'abord .\scripts\setup.ps1" }
$demo = $env:DEV_SEED_DEMO -ne "false"
$env:BILLING_ENABLED = if ($env:DEV_BILLING_ENABLED) { $env:DEV_BILLING_ENABLED } else { "false" }
# Applique les nouvelles migrations avant de lancer l'API (utile après une mise à jour du ZIP).
Push-Location "$root\backend"
& $py -m app.cli init-db
if ($LASTEXITCODE -ne 0) { Pop-Location; throw "La migration de la base a échoué. Consultez le message ci-dessus." }
if ($demo) { & $py -m app.cli seed-demo }
Pop-Location
$back = Start-Process -PassThru -WorkingDirectory "$root\backend" -FilePath $py -ArgumentList "-m","uvicorn","app.main:app","--reload","--port","8000"
try { Set-Location "$root\frontend"; npm run dev } finally { Stop-Process -Id $back.Id -Force -ErrorAction SilentlyContinue }
