from __future__ import annotations

import sqlite3
from pathlib import Path


DB_PATH = Path("data/traffic_primary.db")


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit("No existe data/traffic_primary.db")

    conn = sqlite3.connect(DB_PATH)
    try:
        sensores = conn.execute("SELECT COUNT(*) FROM sensor").fetchone()[0]
        intersecciones = conn.execute("SELECT COUNT(*) FROM interseccion").fetchone()[0]
        eventos = conn.execute(
            """
            SELECT i.codigo, COUNT(*)
            FROM evento_sensor es
            JOIN interseccion i ON i.id = es.interseccion_id
            GROUP BY i.codigo
            ORDER BY i.codigo
            """
        ).fetchall()
        estados = conn.execute(
            """
            SELECT i.codigo, COUNT(*)
            FROM estado_trafico et
            JOIN interseccion i ON i.id = et.interseccion_id
            GROUP BY i.codigo
            ORDER BY i.codigo
            """
        ).fetchall()
    finally:
        conn.close()

    print(f"Intersecciones catalogadas: {intersecciones}")
    print(f"Sensores catalogados: {sensores}")
    print("Eventos por interseccion:")
    for codigo, total in eventos:
        print(f"  {codigo}: {total}")
    print("Estados por interseccion:")
    for codigo, total in estados:
        print(f"  {codigo}: {total}")


if __name__ == "__main__":
    main()
