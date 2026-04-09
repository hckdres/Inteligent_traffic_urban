from __future__ import annotations

import threading
import time
from typing import Callable

import zmq


PRIMARY_HEALTH_ENDPOINT = "tcp://10.43.99.71:5563"


class HealthCheckPC3(threading.Thread):
    def __init__(self, on_status_change: Callable[[bool], None], intervalo_segundos: int = 2) -> None:
        super().__init__(daemon=True)
        self.on_status_change = on_status_change
        self.intervalo_segundos = intervalo_segundos
        self.context = zmq.Context.instance()
        self._ultimo_estado: bool | None = None

    def _nuevo_socket(self) -> zmq.Socket:
        """Crea un socket REQ fresco. Necesario tras cada fallo porque ZMQ REQ
        queda en estado corrupto si recv() no se completa correctamente."""
        socket = self.context.socket(zmq.REQ)
        socket.setsockopt(zmq.RCVTIMEO, 1000)
        socket.setsockopt(zmq.SNDTIMEO, 1000)
        socket.setsockopt(zmq.LINGER, 0)
        socket.connect(PRIMARY_HEALTH_ENDPOINT)
        return socket

    def run(self) -> None:
        socket = self._nuevo_socket()

        while True:
            disponible, socket = self._hacer_ping(socket)
            if self._ultimo_estado is None or disponible != self._ultimo_estado:
                estado_str = "DISPONIBLE" if disponible else "CAÍDO"
                print(f"[HEALTH_CHECK] PC3 {estado_str}")
                self.on_status_change(disponible)
                self._ultimo_estado = disponible
            time.sleep(self.intervalo_segundos)

    def _hacer_ping(self, socket: zmq.Socket) -> tuple[bool, zmq.Socket]:
        """Retorna (disponible, socket). Si falla, cierra el socket y crea uno nuevo
        para evitar que el REQ quede en estado SEND/RECV bloqueado indefinidamente."""
        try:
            socket.send_json({"tipo": "healthcheck"})
            respuesta = socket.recv_json()
            return respuesta.get("ok", False) is True, socket
        except zmq.ZMQError:
            # Socket corrompido: cerrar y recrear
            socket.close(0)
            return False, self._nuevo_socket()
