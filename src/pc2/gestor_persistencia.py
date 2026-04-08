from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict


class GestorPersistencia:
    def __init__(self, ruta_db: str = "data/traffic.db") -> None:
        self.ruta_db = Path(ruta_db)
        self.ruta_db.parent.mkdir(parents=True, exist_ok=True)
        self._inicializar_bd()

    def _inicializar_bd(self) -> None:
        with sqlite3.connect(self.ruta_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS decisiones_trafico (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    interseccion TEXT NOT NULL,
                    estado_circulacion TEXT NOT NULL,
                    accion TEXT NOT NULL,
                    duracion_verde_segundos INTEGER NOT NULL,
                    regla_aplicada TEXT,
                    timestamp_evento TEXT,
                    contexto_json TEXT NOT NULL,
                    creado_en DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    def persistir_evento_procesado(self, decision: Dict[str, Any]) -> None:
        contexto = decision.get("contexto", {})
        timestamp_evento = contexto.get("timestamp")

        with sqlite3.connect(self.ruta_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO decisiones_trafico (
                    interseccion,
                    estado_circulacion,
                    accion,
                    duracion_verde_segundos,
                    regla_aplicada,
                    timestamp_evento,
                    contexto_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision["interseccion"],
                    decision["estado_circulacion"],
                    decision["accion"],
                    decision["duracion_verde_segundos"],
                    decision.get("regla_aplicada"),
                    timestamp_evento,
                    json.dumps(contexto, ensure_ascii=False),
                ),
            )
            conn.commit()

        print(
            f"[PERSISTENCIA] guardado en SQLite -> "
            f"interseccion={decision['interseccion']} | "
            f"estado={decision['estado_circulacion']} | "
            f"accion={decision['accion']}"
        )