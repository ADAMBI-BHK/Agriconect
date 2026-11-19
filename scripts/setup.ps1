<#
 Installation complete d'AgriConnect sous Windows 11 (PowerShell).
 Usage :   .\scripts\setup.ps1            # installation + base de donnees
           .\scripts\setup.ps1 -Demo      # + donnees et comptes de demonstration
#>
param([switch]$Demo)
$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")

# --- Recherche d'un VRAI Python (le raccourci du Microsoft Store est ignore) ---
$pyexe = $null; $pv = $null
foreach ($c in @("py", "python", "python3")) {
  if (Get-Command $c -ErrorAction SilentlyContinue) {
    try {
      $v = & $c -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
      if ($LASTEXITCODE -eq 0 -and $v) { $pyexe = $c; $pv = [version]("$v".Trim()); break }
    } catch { }
  }
}
if (-not $pyexe) {
  throw "Python n'est pas installe (ou seul le raccourci du Microsoft Store est present). Installez Python 3.12 depuis https://www.python.org/downloads/windows/ en cochant 'Add python.exe to PATH', puis FERMEZ et rouvrez PowerShell."
}
if ($pv -lt [version]"3.10") { throw "Python $pv detecte : version 3.10 minimum (3.12 recommandee)." }
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw "Node.js est introuvable. Installez la version LTS depuis https://nodejs.org/ puis rouvrez PowerShell." }
Write-Host "Python $pv ($pyexe) et Node $(node --version) detectes." -ForegroundColor Green

Write-Host "== Backend : environnement Python et dependances ==" -ForegroundColor Green
Set-Location "$root\backend"
if (-not (Test-Path .venv)) { & $pyexe -m venv .venv }
$py = "$root\backend\.venv\Scripts\python.exe"
& $py -m pip install --upgrade pip
& $py -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "L'installation des dependances Python a echoue (voir les messages ci-dessus)." }

if (-not (Test-Path .env)) {
  $secret = & $py -c "import secrets; print(secrets.token_urlsafe(48))"
  (Get-Content .env.example) -replace '^SECRET_KEY=.*', "SECRET_KEY=$secret" | Set-Content .env -Encoding UTF8
  Write-Host "Fichier backend\.env cree avec une SECRET_KEY aleatoire. Changez ADMIN_PASSWORD avant toute mise en ligne." -ForegroundColor Yellow
}
if ($Demo) { (Get-Content .env) -replace '^SEED_DEMO=.*', 'SEED_DEMO=true' | Set-Content .env -Encoding UTF8 }

Write-Host "== Base de donnees : migrations, referentiels, administrateur ==" -ForegroundColor Green
& $py -m app.cli init-db
if ($LASTEXITCODE -ne 0) { throw "L'initialisation de la base a echoue (copiez le message complet)." }
if ($Demo) { & $py -m app.cli seed-demo }

Write-Host "== Frontend : dependances Node ==" -ForegroundColor Green
Set-Location "$root\frontend"
npm install

Write-Host "`nInstallation terminee. Lancez l'application avec :  .\scripts\dev.ps1" -ForegroundColor Green
Write-Host "Application : http://localhost:5173   |   API : http://127.0.0.1:8000/docs"
