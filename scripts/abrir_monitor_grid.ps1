$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    $pythonExe = "python"
}

$command = "Set-Location '$repoRoot'; `$env:PYTHONPATH='$repoRoot'; & '$pythonExe' 'scripts/monitor_grid.py'"

Start-Process wt.exe -ArgumentList @(
    "new-tab",
    "powershell",
    "-NoExit",
    "-Command",
    $command
)
