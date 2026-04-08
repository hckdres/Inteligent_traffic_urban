from __future__ import annotations

import json
import zmq


class ZMQPublisher:
    def __init__(self, endpoint: str) -> None:
        self.context = zmq.Context.instance()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.connect(endpoint)

    def publicar(self, topico: str, mensaje: dict) -> None:
        payload = json.dumps(mensaje)
        self.socket.send_string(f"{topico} {payload}")