from __future__ import annotations

import zmq


PC2_PULL_ENDPOINT = "tcp://127.0.0.1:5557"


def main() -> None:
    context = zmq.Context.instance()

    pull_socket = context.socket(zmq.PULL)
    pull_socket.connect(PC2_PULL_ENDPOINT)

    print("[TEST_PC2] escuchando mensajes reenviados por el broker...")

    while True:
        mensaje = pull_socket.recv_string()
        print(f"[TEST_PC2] recibido: {mensaje}")


if __name__ == "__main__":
    main()