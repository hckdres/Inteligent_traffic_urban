"""
Repositorio SQLite normalizado.
Implementa el esquema completo: interseccion, sensor, semaforo,
evento_sensor + subtipos, estado_trafico, comando_semaforo,
solicitud_usuario, solicitud_comando, evento_failover.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


_SCHEMA = Path(__file__).parent.parent.parent / "data" / "schema.sql"
_MAX_ROWS_DISPLAY = 50   # límite para consultas de monitoreo


class RepositorioSQLite:
    def __init__(self, ruta_db: str) -> None:
        self.ruta_db = Path(ruta_db)
        self.ruta_db.parent.mkdir(parents=True, exist_ok=True)
        self._inicializar()

    # ------------------------------------------------------------------ #
    # Setup                                                                #
    # ------------------------------------------------------------------ #

    def _inicializar(self) -> None:
        with self._conn() as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            if not self._tablas_existen(conn):
                script = _SCHEMA.read_text(encoding="utf-8")
                conn.executescript(script)

    def _tablas_existen(self, conn: sqlite3.Connection) -> bool:
        filas = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='interseccion'"
        ).fetchone()
        return filas[0] > 0

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.ruta_db, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")   # mejor concurrencia
        return conn

    # ------------------------------------------------------------------ #
    # Seed — poblar catálogos desde config                                 #
    # ------------------------------------------------------------------ #

    def seed_desde_config(self, config: Dict[str, Any]) -> None:
        """Inserta intersecciones, sensores y semáforos si no existen."""
        with self._conn() as conn:
            # Intersecciones
            for codigo in config.get("ciudad", {}).get("intersecciones", []):
                fila = codigo.split("-")[1][0]          # "INT-A1" -> "A"
                columna = int(codigo.split("-")[1][1:]) # "INT-A1" -> 1
                conn.execute(
                    "INSERT OR IGNORE INTO interseccion (codigo, fila, columna) VALUES (?,?,?)",
                    (codigo, fila, columna),
                )

            # Sensores
            tipo_map = {
                "camara": "CAMARA",
                "espira_inductiva": "ESPIRA_INDUCTIVA",
                "gps": "GPS",
            }
            for s in config.get("sensores", []):
                inter_id = self._id_interseccion(conn, s["interseccion"])
                if inter_id:
                    conn.execute(
                        """INSERT OR IGNORE INTO sensor
                           (codigo, tipo_sensor, interseccion_id, frecuencia_seg)
                           VALUES (?,?,?,?)""",
                        (s["sensor_id"], tipo_map.get(s["tipo_sensor"], s["tipo_sensor"]),
                         inter_id, s.get("intervalo_segundos")),
                    )

            # Semáforos
            for sem in config.get("semaforos", []):
                inter_id = self._id_interseccion(conn, sem["interseccion"])
                if inter_id:
                    conn.execute(
                        """INSERT OR IGNORE INTO semaforo
                           (interseccion_id, codigo, estado_actual, duracion_base_seg)
                           VALUES (?,?,?,?)""",
                        (inter_id, sem["semaforo_id"],
                         sem.get("estado_inicial", "ROJO"),
                         sem.get("duracion_verde_segundos", 15)),
                    )
            conn.commit()

    # ------------------------------------------------------------------ #
    # Guardar eventos de sensor                                            #
    # ------------------------------------------------------------------ #

    def guardar_evento_camara(self, evento: Dict[str, Any]) -> None:
        with self._conn() as conn:
            sensor_id = self._id_sensor(conn, evento["sensor_id"])
            inter_id  = self._id_interseccion(conn, evento["interseccion"])
            if not sensor_id or not inter_id:
                return
            cur = conn.execute(
                """INSERT INTO evento_sensor
                   (sensor_id, interseccion_id, tipo_evento, ts_evento, payload_json)
                   VALUES (?,?,?,?,?)""",
                (sensor_id, inter_id, "LONGITUD_COLA",
                 evento.get("timestamp", datetime.now().isoformat()),
                 json.dumps(evento)),
            )
            conn.execute(
                "INSERT INTO evento_camara (evento_id, volumen, velocidad_promedio) VALUES (?,?,?)",
                (cur.lastrowid, evento["volumen"], evento["velocidad_promedio"]),
            )
            conn.commit()

    def guardar_evento_espira(self, evento: Dict[str, Any]) -> None:
        with self._conn() as conn:
            sensor_id = self._id_sensor(conn, evento["sensor_id"])
            inter_id  = self._id_interseccion(conn, evento["interseccion"])
            if not sensor_id or not inter_id:
                return
            cur = conn.execute(
                """INSERT INTO evento_sensor
                   (sensor_id, interseccion_id, tipo_evento, ts_evento, payload_json)
                   VALUES (?,?,?,?,?)""",
                (sensor_id, inter_id, "CONTEO_VEHICULAR",
                 evento.get("timestamp_fin", datetime.now().isoformat()),
                 json.dumps(evento)),
            )
            conn.execute(
                """INSERT INTO evento_espira
                   (evento_id, vehiculos_contados, intervalo_segundos,
                    timestamp_inicio, timestamp_fin)
                   VALUES (?,?,?,?,?)""",
                (cur.lastrowid, evento["vehiculos_contados"],
                 evento["intervalo_segundos"],
                 evento["timestamp_inicio"], evento["timestamp_fin"]),
            )
            conn.commit()

    def guardar_evento_gps(self, evento: Dict[str, Any]) -> None:
        with self._conn() as conn:
            sensor_id = self._id_sensor(conn, evento["sensor_id"])
            inter_id  = self._id_interseccion(conn, evento["interseccion"])
            if not sensor_id or not inter_id:
                return
            cur = conn.execute(
                """INSERT INTO evento_sensor
                   (sensor_id, interseccion_id, tipo_evento, ts_evento, payload_json)
                   VALUES (?,?,?,?,?)""",
                (sensor_id, inter_id, "DENSIDAD_TRAFICO",
                 evento.get("timestamp", datetime.now().isoformat()),
                 json.dumps(evento)),
            )
            conn.execute(
                """INSERT INTO evento_gps
                   (evento_id, nivel_congestion, velocidad_promedio)
                   VALUES (?,?,?)""",
                (cur.lastrowid, evento["nivel_congestion"],
                 evento["velocidad_promedio"]),
            )
            conn.commit()

    # ------------------------------------------------------------------ #
    # Guardar estado de tráfico (decisión de analítica)                   #
    # ------------------------------------------------------------------ #

    def guardar_decision(self, decision: Dict[str, Any]) -> None:
        with self._conn() as conn:
            inter_id = self._id_interseccion(conn, decision["interseccion"])
            if not inter_id:
                return
            contexto = decision.get("contexto", {})

            # Mapear clasificación al CHECK de la BD
            clasificacion_raw = decision.get("estado_circulacion", "NORMAL")
            if clasificacion_raw == "PRIORIZACION":
                clasificacion = "PRIORIZACION"
            elif "CONGESTION" in clasificacion_raw:
                clasificacion = "CONGESTION"
            elif clasificacion_raw == "NORMAL":
                clasificacion = "NORMAL"
            else:
                clasificacion = "NORMAL"   # SIN_CLASIFICAR cae como NORMAL

            # La tabla comando_semaforo acepta: ANALITICA | USUARIO | SISTEMA
            origen_decision = decision.get("origen", "ANALITICA")
            origen = "USUARIO" if origen_decision == "MANUAL" else "ANALITICA"

            conn.execute(
                """INSERT INTO estado_trafico
                   (interseccion_id, ts_estado, longitud_cola, conteo_vehicular,
                    densidad_trafico, velocidad_promedio, clasificacion,
                    regla_aplicada, origen)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    inter_id,
                    contexto.get("timestamp", datetime.now().isoformat()),
                    contexto.get("cola"),
                    contexto.get("vehiculos_contados"),
                    contexto.get("densidad"),
                    contexto.get("velocidad_promedio"),
                    clasificacion,
                    decision.get("regla_aplicada"),
                    origen,
                ),
            )

            # Guardar comando de semáforo asociado
            accion = decision.get("accion", "")
            tipo_cmd = self._accion_a_tipo_comando(accion)
            semaforo_id = self._id_semaforo_por_interseccion(conn, inter_id)
            if tipo_cmd and semaforo_id:
                conn.execute(
                    """INSERT INTO comando_semaforo
                       (semaforo_id, interseccion_id, tipo_comando, valor_segundos,
                        motivo, origen, estado_ejecucion, ejecutado_en)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (
                        semaforo_id, inter_id, tipo_cmd,
                        decision.get("duracion_verde_segundos"),
                        decision.get("regla_aplicada"),
                        origen,
                        "EJECUTADO",
                        datetime.now().isoformat(),
                    ),
                )

            conn.commit()

    # ------------------------------------------------------------------ #
    # Guardar solicitud de usuario                                         #
    # ------------------------------------------------------------------ #

    def guardar_solicitud(self, solicitud: Dict[str, Any]) -> None:
        with self._conn() as conn:
            tipo_raw = solicitud.get("tipo_solicitud", "CAMBIO_MANUAL")
            tipo_map = {
                "PRIORIZAR_VIA": "PRIORIZAR_AMBULANCIA",
                "CAMBIO_MANUAL": "CAMBIO_MANUAL",
                "CONSULTA_HISTORICA": "CONSULTA_HISTORICA",
                "CONSULTA_PUNTUAL": "CONSULTA_PUNTUAL",
            }
            tipo = tipo_map.get(tipo_raw, "CAMBIO_MANUAL")

            inter_codigo = solicitud.get("interseccion")
            inter_id = self._id_interseccion(conn, inter_codigo) if inter_codigo else None

            conn.execute(
                """INSERT INTO solicitud_usuario
                   (tipo_solicitud, interseccion_id, detalle, resultado_resumen, atendida_en)
                   VALUES (?,?,?,?,?)""",
                (tipo, inter_id, solicitud.get("detalle"),
                 solicitud.get("resultado_resumen"),
                 datetime.now().isoformat()),
            )
            conn.commit()

    # ------------------------------------------------------------------ #
    # Guardar evento de failover                                           #
    # ------------------------------------------------------------------ #

    def guardar_failover(self, evento: Dict[str, Any]) -> None:
        tipo_raw = evento.get("tipo_evento", "SWITCH_TO_REPLICA")
        # Asegurar que el tipo sea uno de los válidos
        tipos_validos = {"HEALTHCHECK_OK", "HEALTHCHECK_FAIL",
                         "SWITCH_TO_REPLICA", "RETURN_TO_PRIMARY"}
        tipo = tipo_raw if tipo_raw in tipos_validos else "SWITCH_TO_REPLICA"
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO evento_failover (tipo_evento, nodo_origen, descripcion) VALUES (?,?,?)",
                (tipo, evento.get("nodo_origen", "PC2"), evento.get("descripcion")),
            )
            conn.commit()

    # ------------------------------------------------------------------ #
    # Consultas                                                            #
    # ------------------------------------------------------------------ #

    def consultar_interseccion(self, codigo: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            fila = conn.execute(
                """SELECT i.codigo, et.ts_estado, et.clasificacion,
                          et.regla_aplicada, et.longitud_cola,
                          et.velocidad_promedio, et.densidad_trafico,
                          s.estado_actual, s.duracion_base_seg
                   FROM estado_trafico et
                   JOIN interseccion i ON i.id = et.interseccion_id
                   LEFT JOIN semaforo s ON s.interseccion_id = et.interseccion_id
                   WHERE i.codigo = ?
                   ORDER BY et.id DESC LIMIT 1""",
                (codigo,),
            ).fetchone()
            return dict(fila) if fila else None

    def consultar_historico(
        self, fecha_inicio: str, fecha_fin: str, limite: int = _MAX_ROWS_DISPLAY
    ) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            filas = conn.execute(
                """SELECT i.codigo AS interseccion, et.ts_estado,
                          et.clasificacion, et.regla_aplicada,
                          et.longitud_cola, et.velocidad_promedio,
                          et.densidad_trafico, et.origen
                   FROM estado_trafico et
                   JOIN interseccion i ON i.id = et.interseccion_id
                   WHERE et.ts_estado BETWEEN ? AND ?
                   ORDER BY et.ts_estado ASC
                   LIMIT ?""",
                (fecha_inicio, fecha_fin, limite),
            ).fetchall()
            return [dict(f) for f in filas]

    def contar_filas(self) -> Dict[str, int]:
        """Útil para monitorear el tamaño de la BD sin traer datos."""
        tablas = [
            "interseccion", "sensor", "semaforo",
            "evento_sensor", "evento_camara", "evento_espira", "evento_gps",
            "estado_trafico", "comando_semaforo",
            "solicitud_usuario", "evento_failover",
        ]
        with self._conn() as conn:
            return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                    for t in tablas}

    def limpiar_datos_antiguos(self, dias: int = 1) -> int:
        """Borra eventos y estados con más de N días. Retorna filas eliminadas."""
        with self._conn() as conn:
            cur = conn.execute(
                """DELETE FROM evento_sensor
                   WHERE recibido_en < datetime('now', ? )""",
                (f"-{dias} days",),
            )
            eliminados = cur.rowcount
            conn.execute(
                """DELETE FROM estado_trafico
                   WHERE ts_estado < datetime('now', ?)""",
                (f"-{dias} days",),
            )
            conn.commit()
        return eliminados

    # ------------------------------------------------------------------ #
    # Helpers internos                                                     #
    # ------------------------------------------------------------------ #

    def _id_interseccion(self, conn: sqlite3.Connection, codigo: str) -> Optional[int]:
        if not codigo:
            return None
        fila = conn.execute(
            "SELECT id FROM interseccion WHERE codigo = ?", (codigo,)
        ).fetchone()
        return fila[0] if fila else None

    def _id_sensor(self, conn: sqlite3.Connection, codigo: str) -> Optional[int]:
        fila = conn.execute(
            "SELECT id FROM sensor WHERE codigo = ?", (codigo,)
        ).fetchone()
        return fila[0] if fila else None

    def _id_semaforo_por_interseccion(
        self, conn: sqlite3.Connection, interseccion_id: int
    ) -> Optional[int]:
        fila = conn.execute(
            "SELECT id FROM semaforo WHERE interseccion_id = ? LIMIT 1",
            (interseccion_id,),
        ).fetchone()
        return fila[0] if fila else None

    @staticmethod
    def _accion_a_tipo_comando(accion: str) -> Optional[str]:
        mapa = {
            "CAMBIAR_A_VERDE":              "CAMBIAR_A_VERDE",
            "CAMBIAR_A_ROJO":               "CAMBIAR_A_ROJO",
            "EXTENDER_VERDE":               "EXTENDER_VERDE",
            "EXTENDER_VERDE_Y_GENERAR_ALERTA": "EXTENDER_VERDE",
            "OLA_VERDE":                    "PRIORIZAR_VIA",
            "PRIORIZAR_VIA":                "PRIORIZAR_VIA",
            "MANTENER_TEMPORIZACION":       None,
            "RESTAURAR_TEMPORIZACION":      "RESET_CICLO",
            "SIN_ACCION":                   None,
        }
        return mapa.get(accion)