$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    $pythonExe = "python"
}

$puertos = 5556, 5557, 5560, 5561, 5562, 5563, 5564, 5565, 5566, 5570
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

$cmdBdPrincipal = "$commonEnv; & '$pythonExe' 'scripts/pc3/run_bd_principal.py' --bind-host 0.0.0.0 --persist-port 5561 --query-port 5564 --health-port 5563 --admin-port 5566 --seed-path 'src/config/system_3x5.json'"
$cmdReplica = "$commonEnv; & '$pythonExe' 'scripts/pc2/run_replica.py' --bind-host 0.0.0.0 --persist-port 5560 --query-port 5565 --seed-path 'src/config/system_3x5.json'"
$cmdControl = "$commonEnv; & '$pythonExe' 'scripts/pc2/run_control.py' --control-host 127.0.0.1 --control-port 5570"
$cmdAnalitica = "$commonEnv; & '$pythonExe' 'scripts/pc2/run_analitica.py' --pc3-ip 127.0.0.1 --primary-persist-port 5561 --primary-health-port 5563 --bind-host 0.0.0.0 --pull-port 5557 --command-port 5562 --control-host 127.0.0.1 --control-port 5570 --config 'src/config/system_3x5.json'"
$cmdBroker = "$commonEnv; & '$pythonExe' 'scripts/pc1/run_broker.py' --pc2-ip 127.0.0.1 --pc2-port 5557"
$cmdSensores = "$commonEnv; & '$pythonExe' 'scripts/pc1/run_sensores.py' --broker-ip 127.0.0.1 --broker-port 5556 --config 'src/config/system_3x5.json'"
$cmdMon = "$commonEnv; & '$pythonExe' 'scripts/ops/monitoring/monitor_grid.py' --config 'src/config/system_3x5.json'"

Start-Process powershell -WindowStyle Hidden -ArgumentList @("-NoExit", "-Command", $cmdBdPrincipal)
Start-Sleep -Seconds 2
Start-Process powershell -WindowStyle Hidden -ArgumentList @("-NoExit", "-Command", $cmdReplica)
Start-Sleep -Seconds 2
Start-Process powershell -WindowStyle Hidden -ArgumentList @("-NoExit", "-Command", $cmdControl)
Start-Sleep -Seconds 1
Start-Process powershell -WindowStyle Hidden -ArgumentList @("-NoExit", "-Command", $cmdAnalitica)
Start-Sleep -Seconds 2
Start-Process powershell -WindowStyle Hidden -ArgumentList @("-NoExit", "-Command", $cmdBroker)
Start-Sleep -Seconds 1
Start-Process powershell -WindowStyle Hidden -ArgumentList @("-NoExit", "-Command", $cmdSensores)
Start-Sleep -Seconds 3

Start-Process wt.exe -ArgumentList @(
    "new-tab",
    "powershell",
    "-NoExit",
    "-Command",
    $cmdMon
)
