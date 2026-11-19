# Supprime la base SQLite locale et les fichiers téléversés, puis la recrée (migrations + démo si -Demo). IRRÉVERSIBLE.
param([switch]$Demo)
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$py = "$root\backend\.venv\Scripts\python.exe"
Set-Location "$root\backend"
if ((Read-Host "Supprimer toutes les données locales ? (oui/non)") -ne "oui") { exit 0 }
Remove-Item agriconnect.db -ErrorAction SilentlyContinue
Remove-Item uploads -Recurse -ErrorAction SilentlyContinue
& $py -m app.cli init-db
if ($Demo) { & $py -m app.cli seed-demo }
