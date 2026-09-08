$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$pocPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pocPython)) { throw 'Run the local environment setup in docs/LOCAL_POC.md first.' }
Set-Location -LiteralPath $projectRoot
& $pocPython -m local_app.server
