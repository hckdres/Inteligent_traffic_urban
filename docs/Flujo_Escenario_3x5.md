# Flujo de ejecución del escenario 3x5

Este flujo usa la configuración nueva de ciudad en `src/config/system_3x5.json` y el escenario programado en `src/config/escenario_3x5_programado.json`.

## Orden recomendado

1. Levanta PC3 primero, para que queden listos la BD principal, el healthcheck y el panel de monitoreo.
2. Levanta PC2 después, para que la réplica y la analítica se conecten a PC3.
3. Levanta PC1 al final, para que empiece a publicar sensores sobre el broker.
4. Ejecuta el escenario programado, que inyecta congestiones, ambulancias y la caída de la BD principal.

## Ejecución unificada

```powershell
python scripts/run_pc3.py --pc2-ip 127.0.0.1 --config src/config/system_3x5.json
python scripts/run_pc2.py --pc3-ip 127.0.0.1 --config src/config/system_3x5.json
python scripts/run_pc1.py --config src/config/system_3x5.json
python scripts/pc3/run_escenario_programado.py --config src/config/system_3x5.json --scenario src/config/escenario_3x5_programado.json
```

## Ejecución por componentes

### PC3

```powershell
python scripts/pc3/run_bd_principal.py --bind-host 0.0.0.0 --persist-port 5561 --query-port 5564 --health-port 5563 --admin-port 5566 --seed-path src/config/system_3x5.json
python scripts/pc3/run_monitoreo_consulta.py --pc2-ip 127.0.0.1 --analitica-port 5562 --replica-query-port 5565 --primary-ip 127.0.0.1 --primary-query-port 5564 --config src/config/system_3x5.json
```

### PC2

```powershell
python scripts/pc2/run_replica.py --bind-host 0.0.0.0 --persist-port 5560 --query-port 5565 --seed-path src/config/system_3x5.json
python scripts/pc2/run_analitica.py --pc3-ip 127.0.0.1 --primary-persist-port 5561 --primary-health-port 5563 --bind-host 0.0.0.0 --pull-port 5557 --command-port 5562 --control-host 127.0.0.1 --control-port 5570 --config src/config/system_3x5.json
```

### PC1

```powershell
python scripts/run_pc1.py --config src/config/system_3x5.json
```

### Escenario

```powershell
python scripts/pc3/run_escenario_programado.py --config src/config/system_3x5.json --scenario src/config/escenario_3x5_programado.json
```

## Qué dispara el escenario

- Segundo 60: congestión en `INT-B2`.
- Segundo 95: segunda congestión en `INT-C4`.
- Segundo 130: primera ambulancia en la fila `INT-A1`.
- Segundo 140: caída simulada de la BD principal.
- Segundo 150: segunda ambulancia en la fila `INT-A3`.

## Ajuste rápido

- Si quieres acelerar la demo, agrega `--time-scale 0.1` al escenario.
- Si quieres cambiar la ciudad, genera otro JSON con `scripts/ops/generar_config_ciudad.py` y apunta todos los comandos al nuevo archivo.
