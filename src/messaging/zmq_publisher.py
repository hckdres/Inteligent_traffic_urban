from __future__ import annotations

import json
import threading
import zmq


class ZMQPublisher:
    def __init__(self, endpoint: str) -> None:
        self.context = zmq.Context.instance()
        self.endpoint = endpoint
        self._local = threading.local()

    def _socket(self) -> zmq.Socket:
        socket = getattr(self._local, "socket", None)
        if socket is None:
            socket = self.context.socket(zmq.PUB)
            socket.setsockopt(zmq.LINGER, 0)
            socket.connect(self.endpoint)
            self._local.socket = socket
        return socket

    def publicar(self, topico: str, mensaje: dict) -> None:
        payload = json.dumps(mensaje)
        self._socket().send_string(f"{topico} {payload}")
