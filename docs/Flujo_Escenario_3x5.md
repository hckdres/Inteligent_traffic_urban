# Flujo de ejecucion del escenario 3x5

Este flujo usa la ciudad de `src/config/system_3x5.json`: 3 filas numericas (`1`, `2`, `3`) y 5 columnas alfabeticas (`A`, `B`, `C`, `D`, `E`). Cada cruce tiene 3 sensores: camara, espira inductiva y GPS.

## Orden recomendado

1. Levanta PC3 primero, para que queden listos la BD principal, el healthcheck y el panel de consulta.
2. Levanta PC2 despues, para que la replica y la analitica se conecten a PC3.
3. Levanta PC1 al final, para que empiece a publicar sensores sobre el broker.
4. Abre el monitor textual 3x5 cuando quieras ver toda la ciudad.
5. Ejecuta el escenario programado, que inyecta congestiones, ambulancias y la caida de la BD principal.

## Ejecucion por componentes

### Terminal 1: PC3 BD principal

```powershell
python scripts/pc3/run_bd_principal.py --bind-host 0.0.0.0 --persist-port 5561 --query-port 5564 --health-port 5563 --admin-port 5566 --seed-path src/config/system_3x5.json
```

### Terminal 2: PC2 replica

```powershell
python scripts/pc2/run_replica.py --bind-host 0.0.0.0 --persist-port 5560 --query-port 5565 --seed-path src/config/system_3x5.json
```

### Terminal 3: PC2 control de semaforos

```powershell
python scripts/pc2/run_control.py --control-host 127.0.0.1 --control-port 5570
```

### Terminal 4: PC2 analitica

```powershell
python scripts/pc2/run_analitica.py --pc3-ip 127.0.0.1 --primary-persist-port 5561 --primary-health-port 5563 --bind-host 0.0.0.0 --pull-port 5557 --command-port 5562 --control-host 127.0.0.1 --control-port 5570 --config src/config/system_3x5.json
```

### Terminal 5: PC1 broker

```powershell
python scripts/pc1/run_broker.py --pc2-ip 127.0.0.1 --pc2-port 5557
```

### Terminal 6: PC1 sensores

```powershell
python scripts/pc1/run_sensores.py --broker-ip 127.0.0.1 --broker-port 5556 --config src/config/system_3x5.json
```

### Terminal 7: PC3 consultas interactivas

```powershell
python scripts/pc3/run_monitoreo_consulta.py --pc2-ip 127.0.0.1 --analitica-port 5562 --replica-query-port 5565 --primary-ip 127.0.0.1 --primary-query-port 5564 --config src/config/system_3x5.json
```

### Terminal 8: monitor textual 3x5

```powershell
python scripts/ops/monitoring/monitor_grid.py --config src/config/system_3x5.json
```

### Terminal 9: escenario programado

```powershell
python scripts/pc3/run_escenario_programado.py --config src/config/system_3x5.json --scenario src/config/escenario_3x5_programado.json
```

## Que dispara el escenario

- Segundo 60: congestion en `INT-B2`.
- Segundo 95: segunda congestion en `INT-D3`.
- Segundo 130: ambulancia en fila 1, desde `INT-A1`.
- Segundo 140: caida simulada de la BD principal; las consultas pasan a la replica.
- Segundo 150: segunda ambulancia desde `INT-A3`.

## Ajuste rapido

- Si quieres acelerar la demo, agrega `--time-scale 0.1` al escenario.
- Si tu Windows no reconoce `python`, usa la ruta del Python instalado o instala Python y marca la opcion de agregarlo al `PATH`.
