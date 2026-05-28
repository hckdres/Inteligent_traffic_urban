from __future__ import annotations

import argparse
import os
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DEFAULT_LOGS = [
    "logs/E1_base_respuesta.txt",
    "logs/E1_multi_respuesta.txt",
    "logs/E2_base_respuesta.txt",
    "logs/E2_multi_respuesta.txt",
]


def extraer_tiempos(ruta_log: Path) -> list[float]:
    if not ruta_log.exists():
        return []

    texto = ruta_log.read_text(encoding="utf-8", errors="ignore")
    return [float(valor) for valor in re.findall(r"delta_seg=(\d+\.\d+)", texto)]


def imprimir_resumen(ruta_log: Path, deltas: list[float]) -> None:
    print(f"\nArchivo : {ruta_log}")
    if not deltas:
        print("N       : 0 solicitudes")
        print("Promedio: N/A")
        print("Mínimo  : N/A")
        print("Máximo  : N/A")
        return

    print(f"N       : {len(deltas)} solicitudes")
    print(f"Promedio: {statistics.mean(deltas):.3f} s")
    print(f"Mínimo  : {min(deltas):.3f} s")
    print(f"Máximo  : {max(deltas):.3f} s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Resume la latencia de respuesta desde logs de emergencia")
    parser.add_argument("logs", nargs="*", default=DEFAULT_LOGS, help="Archivos log a analizar")
    args = parser.parse_args()

    print("=== MÉTRICA 2 — Tiempo de respuesta ===")
    for log in args.logs:
        ruta = Path(log)
        deltas = extraer_tiempos(ruta)
        imprimir_resumen(ruta, deltas)


if __name__ == "__main__":
    main()
