# Comandos del proyecto (Windows y Linux)

Este documento resume los comandos que estamos usando en este repositorio para ejecutar los nodos, monitorear y limpiar puertos.

## 1) Preparación del entorno

### Windows (PowerShell)
```powershell
cd C:\Users\felip\Documentos\Academico\Universidad\Inteligent_traffic_urban
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Linux (bash)
```bash
cd /ruta/a/Inteligent_traffic_urban
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2) Ejecucion por componente

### PC3 (primero)
```bash
python scripts/run_pc3.py
```

### PC2 (segundo)
```bash
python scripts/run_pc2.py
```

### PC1 (tercero)
```bash
python scripts/run_pc1.py
```

### Monitor Grid
```bash
python scripts/monitor_grid.py
```

## 3) Ejecucion automatica en Windows

Script existente para reiniciar demo (limpia puertos y vuelve a levantar procesos):
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\reiniciar_demo.ps1
```

Script existente para abrir monitor:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\abrir_monitor_grid.ps1
```

## 4) Limpieza de puertos en Linux con .sh

Ya existen estos scripts:

### Limpiar puertos de PC1
```bash
chmod +x start_pc1.sh
./start_pc1.sh
```

Puertos que limpia: `5556`

### Limpiar puertos de PC2
```bash
chmod +x start_pc2.sh
./start_pc2.sh
```

Puertos que limpia: `5557 5560 5562 5565`

### Limpiar puertos de PC3
```bash
chmod +x start_pc3.sh
./start_pc3.sh
```

Puertos que limpia: `5561 5563 5564`

## 5) Limpieza manual de puertos (comandos directos)

### Linux
```bash
# ver quien usa el puerto
lsof -i :5556

# matar proceso por puerto (ejemplo puerto 5556)
kill -9 $(lsof -ti tcp:5556)
```

### Windows (PowerShell)
```powershell
# ver conexiones por puerto
Get-NetTCPConnection -LocalPort 5556

# matar proceso por PID
Stop-Process -Id <PID> -Force
```

## 6) Mapa rapido de puertos del sistema

- `5556`: Broker local PC1
- `5557`: Recepcion eventos PC2
- `5560`: Replica persistencia PC2
- `5561`: Persistencia principal PC3
- `5562`: Comandos analitica PC2
- `5563`: Health check PC3
- `5564`: Consultas principal PC3
- `5565`: Consultas replica PC2

## 7) Activar multihilo (PC1)

### Windows / Linux
```bash
python scripts/run_pc1.py --multihilo
```

### Con IP de PC2 remota
```bash
python scripts/run_pc1.py --pc2-ip 192.168.1.20 --multihilo
```

## 8) Ver logs

## Archivos de log actuales

- `logs/pc3_db.log` (BD principal en PC3)
- `logs/pc2_persistencia.log` (persistencia/failover desde PC2)

### Linux (tiempo real)
```bash
tail -f logs/pc3_db.log
tail -f logs/pc2_persistencia.log
```

### Windows PowerShell (tiempo real)
```powershell
Get-Content .\logs\pc3_db.log -Wait
Get-Content .\logs\pc2_persistencia.log -Wait
```

## Log de BD replica

La replica (`src/pc2/servidor_bd_replica.py`) actualmente imprime en consola (`print`) y no crea un archivo de log dedicado.

## 9) Ver DB principal y replica

## Visor interactivo

### Principal
```bash
python scripts/ver_db.py --db data/traffic_primary.db
```

### Replica
```bash
python scripts/ver_db.py --db data/traffic_replica.db
```

## Resumen rapido de estado (principal)
```bash
python scripts/verificar_estado_demo.py
```

## Limpieza de historico en DB (opcional)

### Principal
```bash
python scripts/ver_db.py --db data/traffic_primary.db --limpiar --dias 1
```

### Replica
```bash
python scripts/ver_db.py --db data/traffic_replica.db --limpiar --dias 1
```
