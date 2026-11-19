# Exécute tous les tests : logique pure, parcours API, vérification des types du frontend.
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$py = "$root\backend\.venv\Scripts\python.exe"
Set-Location "$root\backend"
& $py -m pytest -v
$code = $LASTEXITCODE
Set-Location "$root\frontend"
npm run typecheck
if ($LASTEXITCODE -ne 0) { $code = $LASTEXITCODE }
Set-Location $root
exit $code
