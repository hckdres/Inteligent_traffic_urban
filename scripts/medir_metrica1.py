from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.timezones import COLOMBIA_TZ


DEFAULT_REPLICA_DB = Path("data/traffic_replica.db")
DEFAULT_PRIMARY_DB = Path("data/traffic_primary.db")


def _parsear_fecha_local(valor: str) -> datetime:
    texto = valor.strip()
    if not texto:
        raise ValueError("La fecha no puede estar vacia")
    dt = datetime.fromisoformat(texto)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=COLOMBIA_TZ)
    return dt.astimezone(timezone.utc)


def _parsear_timestamp_db(valor: str) -> datetime | None:
    texto = str(valor).strip()
    if not texto:
        return None
    if texto.endswith("Z"):
        texto = texto[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(texto)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _contar_en_rango(db_path: Path, inicio_utc: datetime, fin_utc: datetime) -> dict[str, int]:
    if not db_path.exists():
        raise FileNotFoundError(f"No existe la BD: {db_path}")

    conteos = {
        "evento_sensor": 0,
        "estado_trafico": 0,
        "comando_semaforo": 0,
    }

    with sqlite3.connect(db_path) as conn:
        for (ts_evento,) in conn.execute("SELECT ts_evento FROM evento_sensor"):
            ts = _parsear_timestamp_db(ts_evento)
            if ts and inicio_utc <= ts <= fin_utc:
                conteos["evento_sensor"] += 1

        for (ts_estado,) in conn.execute("SELECT ts_estado FROM estado_trafico"):
            ts = _parsear_timestamp_db(ts_estado)
            if ts and inicio_utc <= ts <= fin_utc:
                conteos["estado_trafico"] += 1

        for (solicitado_en,) in conn.execute("SELECT solicitado_en FROM comando_semaforo"):
            ts = _parsear_timestamp_db(solicitado_en)
            if ts and inicio_utc <= ts <= fin_utc:
                conteos["comando_semaforo"] += 1

    return conteos


def _imprimir_bloque(titulo: str, conteos: dict[str, int]) -> None:
    total = sum(conteos.values())
    print(f"{titulo}:")
    print(f"  {'evento_sensor':<16}: {conteos['evento_sensor']}")
    print(f"  {'estado_trafico':<16}: {conteos['estado_trafico']}")
    print(f"  {'comando_semaforo':<16}: {conteos['comando_semaforo']}")
    print(f"  {'TOTAL':<16}: {total}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Mide la carga por ventana temporal en PC2 y PC3")
    parser.add_argument("fecha_inicio", help="Inicio de ventana, formato YYYY-MM-DD HH:MM:SS")
    parser.add_argument("fecha_fin", help="Fin de ventana, formato YYYY-MM-DD HH:MM:SS")
    parser.add_argument("escenario", help="Nombre del escenario, por ejemplo E1_base")
    parser.add_argument("--replica-db", default=str(DEFAULT_REPLICA_DB), help="Ruta de la BD replica (PC2)")
    parser.add_argument("--primary-db", default=str(DEFAULT_PRIMARY_DB), help="Ruta de la BD principal (PC3)")
    args = parser.parse_args()

    inicio_utc = _parsear_fecha_local(args.fecha_inicio)
    fin_utc = _parsear_fecha_local(args.fecha_fin)
    if fin_utc < inicio_utc:
        raise SystemExit("La fecha fin debe ser mayor o igual que la fecha inicio")

    replica = _contar_en_rango(Path(args.replica_db), inicio_utc, fin_utc)
    primary = _contar_en_rango(Path(args.primary_db), inicio_utc, fin_utc)

    print(f"=== MÉTRICA 1 — {args.escenario} ===")
    print(f"Ventana: {args.fecha_inicio}  ->  {args.fecha_fin}\n")
    _imprimir_bloque("BD Réplica (PC2)", replica)
    print()
    _imprimir_bloque("BD Principal (PC3)", primary)


if __name__ == "__main__":
    main()
