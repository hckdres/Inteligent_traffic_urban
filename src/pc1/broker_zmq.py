from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

import zmq


SENSOR_PUB_ENDPOINT = "tcp://127.0.0.1:5556"
PC2_PUSH_ENDPOINT = "tcp://127.0.0.1:5557"
COLOMBIA_TZ = ZoneInfo("America/Bogota")


def _hora_colombia() -> str:
    return datetime.now(COLOMBIA_TZ).strftime("%H:%M:%S")


def main() -> None:
    context = zmq.Context.instance()

    subscriber = context.socket(zmq.SUB)
    subscriber.bind(SENSOR_PUB_ENDPOINT)
    subscriber.setsockopt_string(zmq.SUBSCRIBE, "camara")
    subscriber.setsockopt_string(zmq.SUBSCRIBE, "espira")
    subscriber.setsockopt_string(zmq.SUBSCRIBE, "gps")

    push_socket = context.socket(zmq.PUSH)
    push_socket.connect(PC2_PUSH_ENDPOINT)

    print("[BROKER_PC1] iniciado. Escuchando sensores y reenviando a PC2...")

    while True:
        mensaje = subscriber.recv_string()
        topico, payload_json = mensaje.split(" ", 1)
        payload = json.loads(payload_json)
        print(
            f"[{_hora_colombia()}][BROKER_PC1] recibido "
            f"sensor={payload.get('sensor_id')} topico={topico} "
            f"interseccion={payload.get('interseccion')} "
            f"ts={payload.get('timestamp') or payload.get('timestamp_fin')}"
        )
        push_socket.send_string(mensaje)
        print(
            f"[{_hora_colombia()}][BROKER_PC1] reenviado a PC2 "
            f"sensor={payload.get('sensor_id')} topico={topico}"
        )


if __name__ == "__main__":
    main()
