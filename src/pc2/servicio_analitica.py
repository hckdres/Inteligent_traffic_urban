from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import yaml
import zmq
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box

from src.dominio.regla_trafico import ReglaTrafico, seleccionar_mejor_regla
from src.pc2.control_semaforos import ControlSemaforos
from src.pc2.gestor_failover import GestorFailover
from src.pc2.health_check import HealthCheckPC3


PC2_PULL_ENDPOINT = "tcp://127.0.0.1:5557"
ANALITICA_COMMAND_ENDPOINT = "tcp://127.0.0.1:5562"


class ServicioAnalitica:
    def __init__(self, ruta_reglas: str = "config/rules.yaml") -> None:
        self.ruta_reglas = Path(ruta_reglas)
        self.reglas = self._cargar_reglas()
        self.control_semaforos = ControlSemaforos()
        self.failover = GestorFailover()

        self.context = zmq.Context.instance()
        self.pull_socket = self.context.socket(zmq.PULL)
        self.pull_socket.bind(PC2_PULL_ENDPOINT)

        self.rep_socket = self.context.socket(zmq.REP)
        self.rep_socket.bind(ANALITICA_COMMAND_ENDPOINT)

        self.contextos_por_interseccion: Dict[str, Dict[str, Any]] = {}
        self.console = Console()
        self.healthcheck = HealthCheckPC3(self.failover.actualizar_estado_primaria)
        self.healthcheck.start()

    def _cargar_reglas(self) -> List[ReglaTrafico]:
        if not self.ruta_reglas.exists():
            raise FileNotFoundError(f"No existe el archivo de reglas: {self.ruta_reglas}")

        with self.ruta_reglas.open("r", encoding="utf-8") as archivo:
            data = yaml.safe_load(archivo)

        return [ReglaTrafico.desde_dict(item) for item in data.get("reglas", [])]

    def escuchar_eventos(self) -> None:
        print("[ANALITICA] escuchando eventos y comandos...")
        poller = zmq.Poller()
        poller.register(self.pull_socket, zmq.POLLIN)
        poller.register(self.rep_socket, zmq.POLLIN)

        while True:
            sockets = dict(poller.poll())
            if self.pull_socket in sockets:
                mensaje = self.pull_socket.recv_string()
                topico, payload_json = mensaje.split(" ", 1)
                evento = json.loads(payload_json)
                decision = self.procesar_evento(topico, evento)
                if decision:
                    self.control_semaforos.aplicar_accion(decision)
                    self.failover.persistir_decision(decision)

            if self.rep_socket in sockets:
                solicitud = self.rep_socket.recv_json()
                respuesta = self.procesar_solicitud_directa(solicitud)
                self.rep_socket.send_json(respuesta)

    def procesar_evento(self, topico: str, evento: Dict[str, Any]) -> Dict[str, Any] | None:
        interseccion = evento["interseccion"]
        contexto = self.contextos_por_interseccion.setdefault(interseccion, {"interseccion": interseccion})

        if topico == "camara":
            contexto["cola"] = evento.get("volumen")
            contexto["velocidad_promedio"] = evento.get("velocidad_promedio")
            contexto["timestamp"] = evento.get("timestamp")
        elif topico == "espira":
            contexto["vehiculos_contados"] = evento.get("vehiculos_contados")
            contexto["intervalo_segundos"] = evento.get("intervalo_segundos")
            contexto["timestamp"] = evento.get("timestamp_fin")
        elif topico == "gps":
            contexto["nivel_congestion"] = evento.get("nivel_congestion")
            contexto["velocidad_promedio"] = evento.get("velocidad_promedio")
            contexto["densidad"] = evento.get("densidad")
            contexto["timestamp"] = evento.get("timestamp")

        regla = seleccionar_mejor_regla(self.reglas, contexto)
        if regla is None:
            decision = {
                "interseccion": interseccion,
                "estado_circulacion": "SIN_CLASIFICAR",
                "accion": "SIN_ACCION",
                "duracion_verde_segundos": 15,
                "contexto": dict(contexto),
                "origen": "ANALITICA",
            }
        else:
            decision = {
                "interseccion": interseccion,
                "estado_circulacion": regla.resultado.estado_circulacion,
                "accion": regla.resultado.accion,
                "duracion_verde_segundos": regla.resultado.duracion_verde_segundos,
                "regla_aplicada": regla.id,
                "contexto": dict(contexto),
                "origen": "ANALITICA",
            }

        color = "green" if decision["estado_circulacion"] == "NORMAL" else "red" if "CONGESTION" in decision["estado_circulacion"] else "blue"
        
        self.console.print(Panel(
            Text.assemble(
                ("Intersección: ", "bold"), (decision["interseccion"], "cyan"),
                ("\nEstado: ", "bold"), (decision["estado_circulacion"], color),
                ("\nAcción: ", "bold"), (decision["accion"], "bold yellow"),
                ("\nDuración: ", "bold"), (f"{decision['duracion_verde_segundos']}s", "white")
            ),
            title="[bold white]Decisión de Tráfico[/bold white]",
            border_style=color,
            box=box.ROUNDED,
            expand=False
        ))
        return decision

    def procesar_solicitud_directa(self, solicitud: Dict[str, Any]) -> Dict[str, Any]:
        tipo = solicitud.get("tipo")
        interseccion = solicitud.get("interseccion")

        if tipo == "priorizar_via":
            decision = {
                "interseccion": interseccion,
                "estado_circulacion": "PRIORIZACION",
                "accion": "PRIORIZAR_VIA",
                "duracion_verde_segundos": solicitud.get("duracion_verde_segundos", 20),
                "regla_aplicada": "MANUAL",
                "contexto": {"timestamp": solicitud.get("timestamp"), "detalle": solicitud.get("detalle")},
                "origen": "MANUAL",
            }
        elif tipo == "cambio_manual":
            decision = {
                "interseccion": interseccion,
                "estado_circulacion": "PRIORIZACION",
                "accion": solicitud.get("accion", "CAMBIAR_A_VERDE"),
                "duracion_verde_segundos": solicitud.get("duracion_verde_segundos", 15),
                "regla_aplicada": "MANUAL",
                "contexto": {"timestamp": solicitud.get("timestamp"), "detalle": solicitud.get("detalle")},
                "origen": "MANUAL",
            }
        else:
            return {"ok": False, "error": f"tipo de solicitud no soportado: {tipo}"}

        self.control_semaforos.aplicar_accion(decision)
        self.failover.persistir_decision(decision)
        self.failover.registrar_solicitud(
            {
                "tipo_solicitud": tipo.upper(),
                "interseccion": interseccion,
                "detalle": solicitud.get("detalle"),
                "resultado_resumen": f"Acción ejecutada: {decision['accion']}",
            }
        )
        return {"ok": True, "decision": decision}
