from __future__ import annotations

import threading
import time
from typing import Callable

import zmq


PRIMARY_HEALTH_ENDPOINT = "tcp://127.0.0.1:5563"


class HealthCheckPC3(threading.Thread):
    def __init__(self, on_status_change: Callable[[bool], None], intervalo_segundos: int = 2) -> None:
        super().__init__(daemon=True)
        self.on_status_change = on_status_change
        self.intervalo_segundos = intervalo_segundos
        self.context = zmq.Context.instance()
        self._ultimo_estado: bool | None = None

    def run(self) -> None:
        socket = self.context.socket(zmq.REQ)
        socket.connect(PRIMARY_HEALTH_ENDPOINT)
        socket.setsockopt(zmq.RCVTIMEO, 1000)
        socket.setsockopt(zmq.SNDTIMEO, 1000)
        socket.setsockopt(zmq.LINGER, 0)

        while True:
            disponible = self._hacer_ping(socket)
            if self._ultimo_estado is None or disponible != self._ultimo_estado:
                self.on_status_change(disponible)
                self._ultimo_estado = disponible
            time.sleep(self.intervalo_segundos)

    @staticmethod
    def _hacer_ping(socket: zmq.Socket) -> bool:
        try:
            socket.send_json({"tipo": "healthcheck"})
            respuesta = socket.recv_json()
            return respuesta.get("ok", False) is True
        except zmq.ZMQError:
            return False
