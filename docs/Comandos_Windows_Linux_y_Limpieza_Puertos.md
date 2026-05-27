# Comandos del proyecto (Windows y Linux)

Guia actualizada para ejecutar el sistema con la nueva organizacion de `scripts/`.

## 1) Preparacion del entorno

### Windows (PowerShell)
```powershell
cd C:\Users\felip\Documentos\Academico\Universidad\Inteligent_traffic_urban
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = (Get-Location).Path
```

### Linux (bash)
```bash
cd /ruta/a/Inteligent_traffic_urban
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=$(pwd)
```

## 2) Escenario A: ejecucion local (todo en el mismo PC)

En local, usa `127.0.0.1` para conexiones entre componentes.

### Windows (PowerShell)

Terminal 1 (PC3 - BD principal):
```powershell
python scripts/pc3/run_bd_principal.py --bind-host 0.0.0.0 --persist-port 5561 --query-port 5564 --health-port 5563
```

Terminal 2 (PC2 - Replica):
```powershell
python scripts/pc2/run_replica.py --bind-host 0.0.0.0 --persist-port 5560 --query-port 5565
```

Terminal 3 (PC2 - Control):
```powershell
python scripts/pc2/run_control.py --control-host 127.0.0.1 --control-port 5570
```

Terminal 4 (PC2 - Analitica):
```powershell
python scripts/pc2/run_analitica.py --pc3-ip 127.0.0.1 --bind-host 0.0.0.0 --pull-port 5557 --command-port 5562 --control-host 127.0.0.1 --control-port 5570
```

Terminal 5 (PC1 - Broker):
```powershell
python scripts/pc1/run_broker.py --pc2-ip 127.0.0.1 --pc2-port 5557
```

Terminal 6 (PC1 - Sensores):
```powershell
python scripts/pc1/run_sensores.py --broker-ip 127.0.0.1 --broker-port 5556
```

Terminal 7 (PC3 - Monitoreo):
```powershell
python scripts/pc3/run_monitoreo_consulta.py --pc2-ip 127.0.0.1 --analitica-port 5562 --replica-query-port 5565 --primary-ip 127.0.0.1 --primary-query-port 5564
```

### Linux (bash)

Terminal 1:
```bash
python scripts/pc3/run_bd_principal.py --bind-host 0.0.0.0 --persist-port 5561 --query-port 5564 --health-port 5563
```

Terminal 2:
```bash
python scripts/pc2/run_replica.py --bind-host 0.0.0.0 --persist-port 5560 --query-port 5565
```

Terminal 3:
```bash
python scripts/pc2/run_control.py --control-host 127.0.0.1 --control-port 5570
```

Terminal 4:
```bash
python scripts/pc2/run_analitica.py --pc3-ip 127.0.0.1 --bind-host 0.0.0.0 --pull-port 5557 --command-port 5562 --control-host 127.0.0.1 --control-port 5570
```

Terminal 5:
```bash
python scripts/pc1/run_broker.py --pc2-ip 127.0.0.1 --pc2-port 5557
```

Terminal 6:
```bash
python scripts/pc1/run_sensores.py --broker-ip 127.0.0.1 --broker-port 5556
```

Terminal 7:
```bash
python scripts/pc3/run_monitoreo_consulta.py --pc2-ip 127.0.0.1 --analitica-port 5562 --replica-query-port 5565 --primary-ip 127.0.0.1 --primary-query-port 5564
```

## 3) Escenario A2: ejecucion unificada (run_pc1.py, run_pc2.py, run_pc3.py)

Este modo lanza cada PC como proceso integrado (sin separar componentes).

### Local (mismo PC, Windows o Linux)

Terminal 1 (PC3):
```bash
python scripts/run_pc3.py --pc2-ip 127.0.0.1
```

Terminal 2 (PC2):
```bash
python scripts/run_pc2.py --pc3-ip 127.0.0.1
```

Terminal 3 (PC1):
```bash
python scripts/run_pc1.py --pc2-ip 127.0.0.1
```

Terminal 3 (PC1 multihilo):
```bash
python scripts/run_pc1.py --pc2-ip 127.0.0.1 --multihilo
```

### Distribuido (IP distintas)

Ejemplo:
- PC1: `192.168.1.10`
- PC2: `192.168.1.20`
- PC3: `192.168.1.30`

En PC3:
```bash
python scripts/run_pc3.py --pc2-ip 192.168.1.20
```

En PC2:
```bash
python scripts/run_pc2.py --pc3-ip 192.168.1.30
```

En PC1:
```bash
python scripts/run_pc1.py --pc2-ip 192.168.1.20
```

En PC1 (multihilo):
```bash
python scripts/run_pc1.py --pc2-ip 192.168.1.20 --multihilo
```

## 4) Escenario B: ejecucion distribuida (PCs diferentes con IP distinta)

Ejemplo de red:
- PC1 (sensores y broker): `192.168.1.10`
- PC2 (analitica, control, replica): `192.168.1.20`
- PC3 (BD principal, monitoreo): `192.168.1.30`

Importante:
- En los servicios que reciben conexiones remotas usa `--bind-host 0.0.0.0`.
- Debes abrir firewall para los puertos `5556, 5557, 5560, 5561, 5562, 5563, 5564, 5565, 5570`.

### Comandos en PC3 (`192.168.1.30`)

Terminal 1 (BD principal):
```bash
python scripts/pc3/run_bd_principal.py --bind-host 0.0.0.0 --persist-port 5561 --query-port 5564 --health-port 5563
```

Terminal 2 (Monitoreo apuntando a PC2 y PC3):
```bash
python scripts/pc3/run_monitoreo_consulta.py --pc2-ip 192.168.1.20 --analitica-port 5562 --replica-query-port 5565 --primary-ip 127.0.0.1 --primary-query-port 5564
```

### Comandos en PC2 (`192.168.1.20`)

Terminal 1 (Replica):
```bash
python scripts/pc2/run_replica.py --bind-host 0.0.0.0 --persist-port 5560 --query-port 5565
```

Terminal 2 (Control):
```bash
python scripts/pc2/run_control.py --control-host 127.0.0.1 --control-port 5570
```

Terminal 3 (Analitica conectando a PC3):
```bash
python scripts/pc2/run_analitica.py --pc3-ip 192.168.1.30 --bind-host 0.0.0.0 --pull-port 5557 --command-port 5562 --control-host 127.0.0.1 --control-port 5570
```

### Comandos en PC1 (`192.168.1.10`)

Terminal 1 (Broker enviando a PC2):
```bash
python scripts/pc1/run_broker.py --pc2-ip 192.168.1.20 --pc2-port 5557
```

Terminal 2 (Sensores publicando al broker local):
```bash
python scripts/pc1/run_sensores.py --broker-ip 127.0.0.1 --broker-port 5556
```

## 5) Monitoreo, diagnostico y utilidades

Monitor textual:
```bash
python scripts/ops/monitoring/monitor_grid.py
```

Visor de BD principal:
```bash
python scripts/ops/db/ver_db.py --db data/traffic_primary.db
```

Visor de BD replica:
```bash
python scripts/ops/db/ver_db.py --db data/traffic_replica.db
```

Resumen rapido:
```bash
python scripts/ops/db/verificar_estado_demo.py
```

Prueba de emergencia:
```bash
python scripts/testing/test_emergencia.py INT-A1
```

## 6) Logs por PC

Logs que se generan:
- PC3: `logs/pc3_db.log`
- PC2 (persistencia/failover): `logs/pc2_persistencia.log`
- PC1: salida principal en consola (no archivo dedicado por defecto)
- PC2 replica/control/analitica: salida principal en consola (excepto persistencia/failover)

Ver logs en Linux:
```bash
tail -f logs/pc3_db.log
tail -f logs/pc2_persistencia.log
```

Ver logs en Windows PowerShell:
```powershell
Get-Content .\logs\pc3_db.log -Wait
Get-Content .\logs\pc2_persistencia.log -Wait
```

## 7) Atajos Windows (.ps1)

Reiniciar demo:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\ops\windows\reiniciar_demo.ps1
```

Abrir monitor:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\ops\windows\abrir_monitor_grid.ps1
```

## 8) Mapa de puertos

- `5556`: Broker local PC1
- `5557`: Recepcion de eventos en PC2
- `5560`: Persistencia replica PC2
- `5561`: Persistencia principal PC3
- `5562`: Comandos a analitica PC2
- `5563`: Health endpoint PC3
- `5564`: Query principal PC3
- `5565`: Query replica PC2
- `5570`: Canal analitica -> control (PC2)
