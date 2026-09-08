param([switch]$Background, [string]$EnvFile, [string]$Provider)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$pocPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pocPython)) { throw 'Run the local environment setup in docs/LOCAL_POC.md first.' }
Set-Location -LiteralPath $projectRoot
if ($EnvFile) { $env:AI_MATE_ENV_FILE = (Resolve-Path -LiteralPath $EnvFile).Path }
if ($Provider) { $env:AI_MATE_LLM_PROVIDER = $Provider }
if ($Background) {
    try {
        $pocState = Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/bootstrap' -TimeoutSec 2
        if ($pocState.token -and $null -ne $pocState.scenes) {
            Write-Output 'AI-mate is already running at http://127.0.0.1:8765. Restart the existing process if configuration changed.'
            exit 0
        }
    } catch { }
    $pocLogDir = Join-Path $projectRoot '.cache\local-poc'
    New-Item -ItemType Directory -Path $pocLogDir -Force | Out-Null
    $pocStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $pocOut = Join-Path $pocLogDir ('server-' + $pocStamp + '.out.log')
    $pocErr = Join-Path $pocLogDir ('server-' + $pocStamp + '.err.log')
    $pocProcess = Start-Process -FilePath $pocPython -ArgumentList @('-u', '-m', 'local_app.server') -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput $pocOut -RedirectStandardError $pocErr -PassThru
    @{ launcher_pid=$pocProcess.Id; stdout=$pocOut; stderr=$pocErr; started=(Get-Date).ToString('o') } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $pocLogDir 'running-server.json') -Encoding UTF8
    Write-Output "Starting AI-mate in the background (launcher PID $($pocProcess.Id))."
    Write-Output 'Open http://127.0.0.1:8765 and wait for models. Startup errors are in .cache/local-poc/server-*.log.'
    exit 0
}
& $pocPython -m local_app.server
