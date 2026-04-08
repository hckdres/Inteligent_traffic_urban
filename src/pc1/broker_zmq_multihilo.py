from __future__ import annotations

import queue
import threading
from typing import Optional

import zmq


SENSOR_PUB_ENDPOINT = "tcp://127.0.0.1:5556"
PC2_PULL_ENDPOINT = "tcp://127.0.0.1:5557"
NUM_WORKERS = 4


class BrokerMultihilo:
    def __init__(self, num_workers: int = NUM_WORKERS) -> None:
        self.num_workers = num_workers
        self.buffer: "queue.Queue[Optional[str]]" = queue.Queue(maxsize=10000)
        self.context = zmq.Context.instance()

    def iniciar(self) -> None:
        subscriber = self.context.socket(zmq.SUB)
        subscriber.bind(SENSOR_PUB_ENDPOINT)
        for topico in ("camara", "espira", "gps"):
            subscriber.setsockopt_string(zmq.SUBSCRIBE, topico)

        workers = [
            threading.Thread(target=self._worker, args=(i,), daemon=True)
            for i in range(self.num_workers)
        ]
        for worker in workers:
            worker.start()

        print(f"[BROKER_PC1_MULTIHILO] iniciado con {self.num_workers} workers")
        while True:
            mensaje = subscriber.recv_string()
            self.buffer.put(mensaje)

    def _worker(self, worker_id: int) -> None:
        push_socket = self.context.socket(zmq.PUSH)
        push_socket.connect(PC2_PULL_ENDPOINT)

        while True:
            mensaje = self.buffer.get()
            if mensaje is None:
                break
            push_socket.send_string(mensaje)
            print(f"[BROKER_PC1_MULTIHILO][W{worker_id}] reenviado: {mensaje}")
            self.buffer.task_done()


def main() -> None:
    BrokerMultihilo().iniciar()


if __name__ == "__main__":
    main()
