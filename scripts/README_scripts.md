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

## 4) Estado actual de lanzamiento
- Lanzamiento oficial por componentes en `scripts/pc1/`, `scripts/pc2/` y `scripts/pc3/`.
- Los `run_*.py` de la raiz de `scripts/` ya no se usan.

## Notas
- `__init__.py` en `src/` y submódulos se conservan porque ayudan a tratar carpetas como paquetes Python (imports estables).
- Se eliminó `scripts/simulate_pc3_failure.py` por ser solo texto explicativo.
- Se eliminaron carpetas `__pycache__` generadas automáticamente.
