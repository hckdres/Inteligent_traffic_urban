from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict

import zmq


REPLICA_PERSIST_ENDPOINT = "tcp://127.0.0.1:5560"
REPLICA_QUERY_ENDPOINT = "tcp://127.0.0.1:5565"


class ServidorBDReplica:
    def __init__(self, ruta_db: str = "data/traffic_replica.db") -> None:
        self.ruta_db = Path(ruta_db)
        self.ruta_db.parent.mkdir(parents=True, exist_ok=True)
        self._inicializar_db()

        self.context = zmq.Context.instance()
        self.pull_socket = self.context.socket(zmq.PULL)
        self.pull_socket.bind(REPLICA_PERSIST_ENDPOINT)

        self.rep_socket = self.context.socket(zmq.REP)
        self.rep_socket.bind(REPLICA_QUERY_ENDPOINT)

    def iniciar(self) -> None:
        poller = zmq.Poller()
        poller.register(self.pull_socket, zmq.POLLIN)
        poller.register(self.rep_socket, zmq.POLLIN)

        print("[BD_REPLICA] lista")
        while True:
            eventos = dict(poller.poll())
            if self.pull_socket in eventos:
                self._manejar_persistencia(self.pull_socket.recv_json())
            if self.rep_socket in eventos:
                respuesta = self._manejar_consulta(self.rep_socket.recv_json())
                self.rep_socket.send_json(respuesta)

    def _inicializar_db(self) -> None:
        with sqlite3.connect(self.ruta_db) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS estado_trafico (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    interseccion TEXT NOT NULL,
                    ts_estado TEXT,
                    clasificacion TEXT NOT NULL,
                    regla_aplicada TEXT,
                    origen TEXT NOT NULL,
                    accion TEXT,
                    duracion_verde_segundos INTEGER,
                    contexto_json TEXT,
                    creado_en DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS solicitud_usuario (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tipo_solicitud TEXT NOT NULL,
                    interseccion TEXT,
                    fecha_inicio TEXT,
                    fecha_fin TEXT,
                    detalle TEXT,
                    resultado_resumen TEXT,
                    solicitada_en DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS evento_failover (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tipo_evento TEXT NOT NULL,
                    nodo_origen TEXT NOT NULL,
                    descripcion TEXT,
                    ocurrido_en DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            conn.commit()

    def _manejar_persistencia(self, mensaje: Dict[str, Any]) -> None:
        tipo = mensaje.get("tipo")
        payload = mensaje.get("payload", {})

        if tipo == "guardar_decision":
            self._guardar_decision(payload)
        elif tipo == "guardar_solicitud":
            self._guardar_solicitud(payload)
        elif tipo == "registrar_failover":
            self._guardar_failover(payload)

    def _guardar_decision(self, decision: Dict[str, Any]) -> None:
        contexto = decision.get("contexto", {})
        with sqlite3.connect(self.ruta_db) as conn:
            conn.execute(
                """
                INSERT INTO estado_trafico (
                    interseccion, ts_estado, clasificacion, regla_aplicada,
                    origen, accion, duracion_verde_segundos, contexto_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision["interseccion"],
                    contexto.get("timestamp"),
                    decision["estado_circulacion"],
                    decision.get("regla_aplicada"),
                    decision.get("origen", "ANALITICA"),
                    decision.get("accion"),
                    decision.get("duracion_verde_segundos"),
                    json.dumps(contexto, ensure_ascii=False),
                ),
            )
            conn.commit()

    def _guardar_solicitud(self, solicitud: Dict[str, Any]) -> None:
        with sqlite3.connect(self.ruta_db) as conn:
            conn.execute(
                """
                INSERT INTO solicitud_usuario (
                    tipo_solicitud, interseccion, fecha_inicio, fecha_fin, detalle, resultado_resumen
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    solicitud.get("tipo_solicitud"),
                    solicitud.get("interseccion"),
                    solicitud.get("fecha_inicio"),
                    solicitud.get("fecha_fin"),
                    solicitud.get("detalle"),
                    solicitud.get("resultado_resumen"),
                ),
            )
            conn.commit()

    def _guardar_failover(self, evento: Dict[str, Any]) -> None:
        with sqlite3.connect(self.ruta_db) as conn:
            conn.execute(
                "INSERT INTO evento_failover (tipo_evento, nodo_origen, descripcion) VALUES (?, ?, ?)",
                (evento.get("tipo_evento"), evento.get("nodo_origen"), evento.get("descripcion")),
            )
            conn.commit()

    def _manejar_consulta(self, consulta: Dict[str, Any]) -> Dict[str, Any]:
        tipo = consulta.get("tipo")
        if tipo == "consultar_interseccion":
            return self._consultar_interseccion(consulta["interseccion"])
        if tipo == "consultar_historico":
            return self._consultar_historico(consulta["fecha_inicio"], consulta["fecha_fin"])
        if tipo == "healthcheck":
            return {"ok": True, "servidor": "replica"}
        return {"ok": False, "error": f"consulta no soportada: {tipo}"}

    def _consultar_interseccion(self, interseccion: str) -> Dict[str, Any]:
        with sqlite3.connect(self.ruta_db) as conn:
            cursor = conn.execute(
                """
                SELECT interseccion, ts_estado, clasificacion, regla_aplicada, accion, duracion_verde_segundos
                FROM estado_trafico
                WHERE interseccion = ?
                ORDER BY id DESC LIMIT 1
                """,
                (interseccion,),
            )
            fila = cursor.fetchone()
        return {"ok": True, "data": fila}

    def _consultar_historico(self, fecha_inicio: str, fecha_fin: str) -> Dict[str, Any]:
        with sqlite3.connect(self.ruta_db) as conn:
            cursor = conn.execute(
                """
                SELECT interseccion, ts_estado, clasificacion, regla_aplicada, accion
                FROM estado_trafico
                WHERE COALESCE(ts_estado, creado_en) BETWEEN ? AND ?
                ORDER BY COALESCE(ts_estado, creado_en) ASC
                """,
                (fecha_inicio, fecha_fin),
            )
            filas = cursor.fetchall()
        return {"ok": True, "data": filas}


def main() -> None:
    ServidorBDReplica().iniciar()


if __name__ == "__main__":
    main()
