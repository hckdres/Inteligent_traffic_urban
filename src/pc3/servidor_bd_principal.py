from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

import zmq

from src.persistence.repositorio_sqlite import RepositorioSQLite

PRIMARY_PERSIST_ENDPOINT = "tcp://127.0.0.1:5561"
PRIMARY_QUERY_ENDPOINT   = "tcp://127.0.0.1:5564"
PRIMARY_HEALTH_ENDPOINT  = "tcp://127.0.0.1:5563"

logger = logging.getLogger("pc3_db")


class ServidorBDPrincipal:
    def __init__(self, ruta_db: str = "data/traffic_primary.db") -> None:
        self.repo = RepositorioSQLite(ruta_db)
        self._seed_hecho = False
        
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(log_dir / "pc3_db.log", encoding='utf-8')
        file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(file_handler)
        logger.setLevel(logging.INFO)

        self.context = zmq.Context.instance()

        self.pull_socket = self.context.socket(zmq.PULL)
        self.pull_socket.bind(PRIMARY_PERSIST_ENDPOINT)

        self.rep_socket = self.context.socket(zmq.REP)
        self.rep_socket.bind(PRIMARY_QUERY_ENDPOINT)

        self.health_socket = self.context.socket(zmq.REP)
        self.health_socket.bind(PRIMARY_HEALTH_ENDPOINT)

    def seed(self, config: Dict[str, Any]) -> None:
        if not self._seed_hecho:
            self.repo.seed_desde_config(config)
            self._seed_hecho = True
            logger.info("[BD_PRINCIPAL] catálogos inicializados desde config")

    def iniciar(self) -> None:
        poller = zmq.Poller()
        poller.register(self.pull_socket, zmq.POLLIN)
        poller.register(self.rep_socket, zmq.POLLIN)
        poller.register(self.health_socket, zmq.POLLIN)

        logger.info("[BD_PRINCIPAL] lista")
        while True:
            eventos = dict(poller.poll())
            if self.pull_socket in eventos:
                self._manejar_persistencia(self.pull_socket.recv_json())
            if self.rep_socket in eventos:
                respuesta = self._manejar_consulta(self.rep_socket.recv_json())
                self.rep_socket.send_json(respuesta)
            if self.health_socket in eventos:
                self.health_socket.recv_json()
                self.health_socket.send_json({"ok": True, "servidor": "primary"})

    def _manejar_persistencia(self, mensaje: Dict[str, Any]) -> None:
        tipo = mensaje.get("tipo")
        payload = mensaje.get("payload", {})
        try:
            if tipo == "guardar_decision":
                self.repo.guardar_decision(payload)
                logger.debug(f"[BD_PRINCIPAL] decision guardada: {payload.get('interseccion')} {payload.get('estado_circulacion')}")
            elif tipo == "guardar_solicitud":
                self.repo.guardar_solicitud(payload)
            elif tipo == "registrar_failover":
                self.repo.guardar_failover(payload)
            elif tipo == "guardar_evento_sensor":
                self._guardar_evento_sensor(payload)
            elif tipo == "seed":
                self.seed(payload)
        except Exception as exc:
            logger.error(f"[BD_PRINCIPAL] error en persistencia tipo={tipo}: {exc}")

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
            if tipo in ("consultar_evento_seq", "consultar_sensor_seq"):
                data = self.repo.consultar_evento_seq(
                    int(consulta["seq"]), int(consulta.get("limite", 50))
                )
                return {"ok": bool(data), "data": data}
            if tipo == "contar_filas":
                return {"ok": True, "data": self.repo.contar_filas()}
            return {"ok": False, "error": f"consulta no soportada: {tipo}"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}


def main() -> None:
    ServidorBDPrincipal().iniciar()

if __name__ == "__main__":
    main()
