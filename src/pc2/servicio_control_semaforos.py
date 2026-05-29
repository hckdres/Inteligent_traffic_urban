from __future__ import annotations

import zmq

from src.pc2.control_semaforos import ControlSemaforos


CONTROL_SEMAFOROS_ENDPOINT = "tcp://127.0.0.1:5570"


class ServicioControlSemaforos:
    def __init__(self) -> None:
        self.context = zmq.Context.instance()
        self.pull_socket = self.context.socket(zmq.PULL)
        self.pull_socket.connect(CONTROL_SEMAFOROS_ENDPOINT)
        self.control = ControlSemaforos()

    def ejecutar(self) -> None:
        print(f"[CONTROL_SEMAFOROS] escuchando decisiones en {CONTROL_SEMAFOROS_ENDPOINT}")
        while True:
            decision = self.pull_socket.recv_json()
            self.control.aplicar_accion(decision)


def main() -> None:
    ServicioControlSemaforos().ejecutar()


if __name__ == "__main__":
    main()
