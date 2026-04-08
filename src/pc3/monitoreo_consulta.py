from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

import zmq


PRIMARY_QUERY_ENDPOINT = "tcp://127.0.0.1:5564"
REPLICA_QUERY_ENDPOINT = "tcp://127.0.0.1:5565"
ANALITICA_COMMAND_ENDPOINT = "tcp://127.0.0.1:5562"


class MonitoreoConsulta:
    def __init__(self) -> None:
        self.context = zmq.Context.instance()
        self.timeout_ms = 1500

    def ejecutar(self) -> None:
        print("[MONITOREO] 1) Consulta puntual 2) Histórico 3) Priorizar vía 4) Cambio manual 5) Salir")
        while True:
            opcion = input("Seleccione opción: ").strip()
            if opcion == "1":
                inter = input("Intersección: ").strip()
                print(self.consultar_interseccion(inter))
            elif opcion == "2":
                inicio = input("Fecha inicio (YYYY-MM-DD HH:MM:SS): ").strip()
                fin = input("Fecha fin (YYYY-MM-DD HH:MM:SS): ").strip()
                print(self.consultar_historico(inicio, fin))
            elif opcion == "3":
                inter = input("Intersección: ").strip()
                detalle = input("Detalle: ").strip()
                print(self.enviar_indicacion({
                    "tipo": "priorizar_via",
                    "interseccion": inter,
                    "detalle": detalle,
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "duracion_verde_segundos": 20,
                }))
            elif opcion == "4":
                inter = input("Intersección: ").strip()
                accion = input("Acción (CAMBIAR_A_VERDE/CAMBIAR_A_ROJO): ").strip()
                print(self.enviar_indicacion({
                    "tipo": "cambio_manual",
                    "interseccion": inter,
                    "accion": accion,
                    "detalle": "cambio manual desde PC3",
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "duracion_verde_segundos": 15,
                }))
            elif opcion == "5":
                break
            else:
                print("Opción inválida")

    def consultar_interseccion(self, interseccion: str) -> Dict[str, Any]:
        return self._consultar_con_failover({"tipo": "consultar_interseccion", "interseccion": interseccion})

    def consultar_historico(self, fecha_inicio: str, fecha_fin: str) -> Dict[str, Any]:
        return self._consultar_con_failover({"tipo": "consultar_historico", "fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin})

    def enviar_indicacion(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        socket = self.context.socket(zmq.REQ)
        socket.connect(ANALITICA_COMMAND_ENDPOINT)
        socket.setsockopt(zmq.RCVTIMEO, self.timeout_ms)
        socket.setsockopt(zmq.SNDTIMEO, self.timeout_ms)
        try:
            socket.send_json(payload)
            return socket.recv_json()
        except zmq.ZMQError as exc:
            return {"ok": False, "error": str(exc)}
        finally:
            socket.close(0)

    def _consultar_con_failover(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        respuesta = self._consultar(PRIMARY_QUERY_ENDPOINT, payload)
        if respuesta.get("ok"):
            respuesta["fuente"] = "PRIMARY"
            return respuesta

        respuesta = self._consultar(REPLICA_QUERY_ENDPOINT, payload)
        respuesta["fuente"] = "REPLICA"
        return respuesta

    def _consultar(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        socket = self.context.socket(zmq.REQ)
        socket.connect(endpoint)
        socket.setsockopt(zmq.RCVTIMEO, self.timeout_ms)
        socket.setsockopt(zmq.SNDTIMEO, self.timeout_ms)
        try:
            socket.send_json(payload)
            return socket.recv_json()
        except zmq.ZMQError as exc:
            return {"ok": False, "error": str(exc)}
        finally:
            socket.close(0)
