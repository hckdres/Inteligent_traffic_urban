# Scripts organizados

## 1) Ejecución por componentes (nuevo)
- `scripts/pc1/`: broker y sensores
- `scripts/pc2/`: replica, control y analitica
- `scripts/pc3/`: bd principal y monitoreo/consulta

## 2) Operación y diagnóstico
- `scripts/ops/db/ver_db.py`: visor y limpieza de BD
- `scripts/ops/db/verificar_estado_demo.py`: resumen rápido de estado
- `scripts/ops/monitoring/monitor_grid.py`: monitor textual en grilla
- `scripts/ops/diagnostico_maquina.py`: inventario de máquina/VM, red, tiempos, logs y SQLite
- `scripts/ops/windows/*.ps1`: atajos de Windows para reiniciar/abrir monitor

## 3) Pruebas puntuales
- `scripts/testing/test_emergencia.py`: prueba manual de priorización de ambulancia y emite `delta_seg`

## 4) Métricas
- `scripts/medir_metrica1.py`: conteo por ventana temporal en BD réplica y principal
- `scripts/medir_metrica2.py`: resumen de `delta_seg` desde los logs de emergencias

## 5) Estado actual de lanzamiento
- Lanzamiento oficial por componentes en `scripts/pc1/`, `scripts/pc2/` y `scripts/pc3/`.
- Los `run_*.py` de la raiz de `scripts/` ya no se usan.

## Notas
- `__init__.py` en `src/` y submódulos se conservan porque ayudan a tratar carpetas como paquetes Python (imports estables).
- Se eliminó `scripts/simulate_pc3_failure.py` por ser solo texto explicativo.
- Se eliminaron carpetas `__pycache__` generadas automáticamente.

## Uso rápido de diagnóstico
- Inventario JSON: `python scripts/ops/diagnostico_maquina.py inventory --format json`
- Inventario Markdown: `python scripts/ops/diagnostico_maquina.py inventory --format md`
- Guardar inventario en archivo: `python scripts/ops/diagnostico_maquina.py inventory --out data/inventario_pc1.json`
- Medición con `time.time()`: `python scripts/ops/diagnostico_maquina.py time-demo --iterations 2000000`
- Análisis de logs: `python scripts/ops/diagnostico_maquina.py log-analyze logs`
- Consulta SQLite: `python scripts/ops/diagnostico_maquina.py sqlite-query data/traffic.db "SELECT name FROM sqlite_master WHERE type='table'"`
