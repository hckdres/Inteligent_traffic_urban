# Scripts organizados

## 1) Ejecución por componentes (nuevo)
- `scripts/pc1/`: broker y sensores
- `scripts/pc2/`: replica, control y analitica
- `scripts/pc3/`: bd principal y monitoreo/consulta

## 2) Operación y diagnóstico
- `scripts/ops/db/ver_db.py`: visor y limpieza de BD
- `scripts/ops/db/verificar_estado_demo.py`: resumen rápido de estado
- `scripts/ops/monitoring/monitor_grid.py`: monitor textual en grilla
- `scripts/ops/windows/*.ps1`: atajos de Windows para reiniciar/abrir monitor

## 3) Pruebas puntuales
- `scripts/testing/test_emergencia.py`: prueba manual de priorización de ambulancia

## 4) Compatibilidad (legacy)
- `scripts/run_pc1.py`, `scripts/run_pc2.py`, `scripts/run_pc3.py` (wrappers)
- implementación legacy real en `scripts/launch/legacy/`

## Notas
- `__init__.py` en `src/` y submódulos se conservan porque ayudan a tratar carpetas como paquetes Python (imports estables).
- Se eliminó `scripts/simulate_pc3_failure.py` por ser solo texto explicativo.
- Se eliminaron carpetas `__pycache__` generadas automáticamente.
