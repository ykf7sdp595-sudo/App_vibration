$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
if ($env:OS -ne 'Windows_NT') { throw 'Construire ce paquet sur Windows.' }
# Environnement séparé pour ne pas modifier l’environnement de développement.
if (-not (Test-Path '.venv-build\Scripts\python.exe')) {
    py -3.12 -m venv .venv-build
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 est requis pour fabriquer le paquet.' }
}
$buildPython = Join-Path $PWD '.venv-build\Scripts\python.exe'
& $buildPython -m pip install -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw 'Installation des dépendances échouée.' }
& $buildPython -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Tests échoués : compilation annulée.' }
& $buildPython -m PyInstaller --clean --noconfirm App_vibration.spec
if ($LASTEXITCODE -ne 0) { throw 'Compilation PyInstaller échouée.' }
& $buildPython -m pip freeze | Out-File -Encoding utf8 dist\App_vibration\versions-build.txt
Copy-Item packaging\UTILISATION.txt dist\App_vibration\UTILISATION.txt
Write-Host 'Paquet créé : dist\App_vibration. Tester avant de distribuer tout ce dossier.'
