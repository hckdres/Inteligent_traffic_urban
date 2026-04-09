
from __future__ import annotations

from typing import Any, Dict

import zmq

from src.persistence.repositorio_sqlite import RepositorioSQLite

REPLICA_PERSIST_ENDPOINT = "tcp://127.0.0.1:5560"
REPLICA_QUERY_ENDPOINT   = "tcp://127.0.0.1:5565"


class ServidorBDReplica:
    def __init__(self, ruta_db: str = "data/traffic_replica.db") -> None:
        self.repo = RepositorioSQLite(ruta_db)

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

    def _manejar_persistencia(self, mensaje: Dict[str, Any]) -> None:
        tipo = mensaje.get("tipo")
        payload = mensaje.get("payload", {})
        try:
            if tipo == "guardar_decision":
                self.repo.guardar_decision(payload)
                print(f"[BD_REPLICA] decision guardada: {payload.get('interseccion')} {payload.get('estado_circulacion')}")
            elif tipo == "guardar_solicitud":
                self.repo.guardar_solicitud(payload)
            elif tipo == "registrar_failover":
                self.repo.guardar_failover(payload)
            elif tipo == "guardar_evento_sensor":
                self._guardar_evento_sensor(payload)
            elif tipo == "seed":
                self.repo.seed_desde_config(payload)
        except Exception as exc:
            print(f"[BD_REPLICA] error en persistencia tipo={tipo}: {exc}")

    def _guardar_evento_sensor(self, payload: Dict[str, Any]) -> None:
        tipo_sensor = payload.get("tipo_sensor")
        if tipo_sensor == "camara":
            self.repo.guardar_evento_camara(payload)
        elif tipo_sensor == "espira_inductiva":
            self.repo.guardar_evento_espira(payload)
        elif tipo_sensor == "gps":
            self.repo.guardar_evento_gps(payload)

    def _manejar_consulta(self, consulta: Dict[str, Any]) -> Dict[str, Any]:
        tipo = consulta.get("tipo")
        try:
            if tipo == "consultar_interseccion":
                data = self.repo.consultar_interseccion(consulta["interseccion"])
                return {"ok": bool(data), "data": data}
            if tipo == "consultar_historico":
                data = self.repo.consultar_historico(
                    consulta["fecha_inicio"], consulta["fecha_fin"]
                )
                return {"ok": True, "data": data}
            if tipo == "contar_filas":
                return {"ok": True, "data": self.repo.contar_filas()}
            if tipo == "healthcheck":
                return {"ok": True, "servidor": "replica"}
            return {"ok": False, "error": f"consulta no soportada: {tipo}"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}


def main() -> None:
    ServidorBDReplica().iniciar()

if __name__ == "__main__":
    main()