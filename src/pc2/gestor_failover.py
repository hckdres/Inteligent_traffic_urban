from __future__ import annotations

import queue
from typing import Any, Dict

import zmq


PRIMARY_PERSIST_ENDPOINT = "tcp://127.0.0.1:5561"
REPLICA_PERSIST_ENDPOINT = "tcp://127.0.0.1:5560"


class GestorFailover:
    def __init__(self) -> None:
        self.context = zmq.Context.instance()

        self.push_primary = self.context.socket(zmq.PUSH)
        self.push_primary.setsockopt(zmq.SNDTIMEO, 2000)  # Evitar bloqueo infinito
        self.push_primary.setsockopt(zmq.LINGER, 0)
        self.push_primary.connect(PRIMARY_PERSIST_ENDPOINT)

        self.push_replica = self.context.socket(zmq.PUSH)
        self.push_replica.connect(REPLICA_PERSIST_ENDPOINT)

        self.primary_disponible = True
        self._eventos_pendientes: "queue.Queue[Dict[str, Any]]" = queue.Queue()

    def actualizar_estado_primaria(self, disponible: bool) -> None:
        if self.primary_disponible != disponible:
            self.primary_disponible = disponible
            tipo = "RETURN_TO_PRIMARY" if disponible else "SWITCH_TO_REPLICA"
            self._eventos_pendientes.put(
                {
                    "tipo": "registrar_failover",
                    "payload": {
                        "tipo_evento": tipo,
                        "nodo_origen": "PC2",
                        "descripcion": "Cambio automático de destino de persistencia",
                    },
                }
            )
            print(f"[FAILOVER] primary_disponible={self.primary_disponible}")

    def persistir_decision(self, decision: Dict[str, Any]) -> None:
        self._enviar(self.push_replica, {"tipo": "guardar_decision", "payload": decision}, "REPLICA")

        if self.primary_disponible:
            try:
                self._enviar(self.push_primary, {"tipo": "guardar_decision", "payload": decision}, "PRIMARY")
            except zmq.ZMQError:
                self.actualizar_estado_primaria(False)

        self._vaciar_eventos_pendientes()

    def registrar_solicitud(self, solicitud: Dict[str, Any]) -> None:
        mensaje = {"tipo": "guardar_solicitud", "payload": solicitud}
        self._enviar(self.push_replica, mensaje, "REPLICA")
        if self.primary_disponible:
            try:
                self._enviar(self.push_primary, mensaje, "PRIMARY")
            except zmq.ZMQError:
                self.actualizar_estado_primaria(False)

    def _vaciar_eventos_pendientes(self) -> None:
        while not self._eventos_pendientes.empty():
            evento = self._eventos_pendientes.get()
            self._enviar(self.push_replica, evento, "REPLICA")
            if self.primary_disponible:
                self._enviar(self.push_primary, evento, "PRIMARY")

    @staticmethod
    def _enviar(socket: zmq.Socket, mensaje: Dict[str, Any], destino: str) -> None:
        socket.send_json(mensaje)
        print(f"[PERSISTENCIA->{destino}] {mensaje['tipo']}")
