from __future__ import annotations

import zmq


SENSOR_PUB_ENDPOINT = "tcp://127.0.0.1:5556"
PC2_PUSH_ENDPOINT = "tcp://127.0.0.1:5557"


def main() -> None:
    context = zmq.Context.instance()

    subscriber = context.socket(zmq.SUB)
    subscriber.bind(SENSOR_PUB_ENDPOINT)
    subscriber.setsockopt_string(zmq.SUBSCRIBE, "camara")
    subscriber.setsockopt_string(zmq.SUBSCRIBE, "espira")
    subscriber.setsockopt_string(zmq.SUBSCRIBE, "gps")

    push_socket = context.socket(zmq.PUSH)
    push_socket.bind(PC2_PUSH_ENDPOINT)

    print("[BROKER_PC1] iniciado. Escuchando sensores y reenviando a PC2...")

    while True:
        mensaje = subscriber.recv_string()
        print(f"[BROKER_PC1] recibido: {mensaje}")
        push_socket.send_string(mensaje)
        print(f"[BROKER_PC1] reenviado a PC2: {mensaje}")


if __name__ == "__main__":
    main()