$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    $pythonExe = "python"
}

$puertos = 5556, 5557, 5561, 5562, 5563, 5564, 5565
$pids = @()

foreach ($puerto in $puertos) {
    try {
        $conexiones = Get-NetTCPConnection -LocalPort $puerto -ErrorAction SilentlyContinue
        if ($conexiones) {
            $pids += $conexiones | Select-Object -ExpandProperty OwningProcess
        }
    } catch {
    }
}

$pids = $pids | Sort-Object -Unique
foreach ($processId in $pids) {
    if ($processId -and $processId -ne 0) {
        try {
            Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        } catch {
        }
    }
}

Start-Sleep -Seconds 2

$commonEnv = "`$env:PYTHONPATH='$repoRoot'; Set-Location '$repoRoot'"

$cmdPc3 = "$commonEnv; & '$pythonExe' 'src/pc3/main_pc3.py'"
$cmdPc2 = "$commonEnv; & '$pythonExe' 'src/pc2/main_pc2.py'"
$cmdPc1 = "$commonEnv; & '$pythonExe' 'src/pc1/main_pc1.py'"
$cmdMon = "$commonEnv; & '$pythonExe' 'scripts/monitor_grid.py'"

Start-Process powershell -WindowStyle Hidden -ArgumentList @("-NoExit", "-Command", $cmdPc3)
Start-Sleep -Seconds 2
Start-Process powershell -WindowStyle Hidden -ArgumentList @("-NoExit", "-Command", $cmdPc2)
Start-Sleep -Seconds 2
Start-Process powershell -WindowStyle Hidden -ArgumentList @("-NoExit", "-Command", $cmdPc1)
Start-Sleep -Seconds 3

Start-Process wt.exe -ArgumentList @(
    "new-tab",
    "powershell",
    "-NoExit",
    "-Command",
    $cmdMon
)
