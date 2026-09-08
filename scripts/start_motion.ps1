param([switch]$Background, [switch]$FastFP8)
$ErrorActionPreference = 'Stop'
$motionProject = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$motionRoot = Join-Path $motionProject '.cache/local-poc/ComfyUI'
$motionPython = Join-Path $motionProject '.cache/comfy-env/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $motionPython)) { throw 'The isolated ComfyUI environment is not installed. See docs/LOCAL_POC.md.' }
$motionArgs = @('-X','utf8','-u','main.py','--listen','127.0.0.1','--port','8188','--disable-auto-launch','--disable-all-custom-nodes','--disable-api-nodes','--reserve-vram','4')
if ($FastFP8) { $motionArgs += @('--fast','fp8_matrix_mult') }
if ($Background) {
    try {
        $motionState = Invoke-RestMethod -Uri 'http://127.0.0.1:8188/system_stats' -TimeoutSec 2
        if ($motionState.system.comfyui_version) {
            Write-Output 'ComfyUI is already running on loopback port 8188. Restart it to change precision options.'
            exit 0
        }
    } catch { }
    $motionLogs = Join-Path $motionProject '.cache/local-poc'
    $motionStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $motionOut = Join-Path $motionLogs "comfy-$motionStamp.out.log"
    $motionErr = Join-Path $motionLogs "comfy-$motionStamp.err.log"
    $motionProcess = Start-Process -FilePath $motionPython -ArgumentList $motionArgs -WorkingDirectory $motionRoot -WindowStyle Hidden -RedirectStandardOutput $motionOut -RedirectStandardError $motionErr -PassThru
    @{ launcher_pid=$motionProcess.Id; stdout=$motionOut; stderr=$motionErr; fast_fp8=[bool]$FastFP8 } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $motionLogs 'running-motion.json')
    Write-Output "Starting local motion engine (launcher PID $($motionProcess.Id)) at http://127.0.0.1:8188."
} else {
    Push-Location -LiteralPath $motionRoot
    try { & $motionPython @motionArgs } finally { Pop-Location }
}
