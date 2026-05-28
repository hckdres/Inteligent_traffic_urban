$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    $pythonExe = "python"
}

$command = "Set-Location '$repoRoot'; `$env:PYTHONPATH='$repoRoot'; & '$pythonExe' 'scripts/ops/monitoring/monitor_grid.py' --config 'src/config/system_3x5.json'"

Start-Process wt.exe -ArgumentList @(
    "new-tab",
    "powershell",
    "-NoExit",
    "-Command",
    $command
)
