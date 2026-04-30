from __future__ import annotations

import json
from datetime import datetime

import zmq

from src.utils.timezones import COLOMBIA_TZ


SENSOR_PUB_ENDPOINT = "tcp://127.0.0.1:5556"
PC2_PUSH_ENDPOINT = "tcp://127.0.0.1:5557"


def _hora_colombia() -> str:
    return datetime.now(COLOMBIA_TZ).strftime("%H:%M:%S")


def _ts_colombia(valor: str | None) -> str | None:
    if not valor:
        return None
    texto = valor[:-1] + "+00:00" if valor.endswith("Z") else valor
    try:
        dt = datetime.fromisoformat(texto)
    except ValueError:
        return valor
    if dt.tzinfo is None:
        return valor
    return dt.astimezone(COLOMBIA_TZ).isoformat()


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
            f"seq={payload.get('seq')} sensor={payload.get('sensor_id')} topico={topico} "
            f"interseccion={payload.get('interseccion')} "
            f"ts={_ts_colombia(payload.get('timestamp') or payload.get('timestamp_fin'))}"
        )
        push_socket.send_string(mensaje)
        print(
            f"[{_hora_colombia()}][BROKER_PC1] reenviado a PC2 "
            f"seq={payload.get('seq')} sensor={payload.get('sensor_id')} topico={topico}"
        )


if __name__ == "__main__":
    main()
