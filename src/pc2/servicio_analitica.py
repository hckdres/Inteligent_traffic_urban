from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
import zmq
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box

from src.dominio.evento_trafico import EventoCamara, EventoEspira, EventoGPS, EventoTrafico
from src.dominio.regla_trafico import ReglaTrafico, seleccionar_mejor_regla
from src.enums.accion_semaforo import AccionSemaforo
from src.enums.estado_circulacion import EstadoCirculacion
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

        # Almacena últimos eventos tipados por intersección
        self._ultimo_cam: Dict[str, EventoCamara] = {}
        self._ultimo_esp: Dict[str, EventoEspira] = {}
        self._ultimo_gps: Dict[str, EventoGPS]    = {}
        # También mantenemos el contexto plano para compatibilidad de persistencia
        self.contextos_por_interseccion: Dict[str, Dict[str, Any]] = {}
        self._ultima_firma_por_interseccion: Dict[str, tuple[str, str, int, str]] = {}

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
                evento_dict = json.loads(payload_json)
                decision = self.procesar_evento(topico, evento_dict)
                if decision:
                    self.control_semaforos.aplicar_accion(decision)
                    self.failover.persistir_decision(decision)

            if self.rep_socket in sockets:
                try:
                    solicitud = self.rep_socket.recv_json()
                    respuesta = self.procesar_solicitud_directa(solicitud)
                    self.rep_socket.send_json(respuesta)
                except Exception as e:
                    print(f"[ANALITICA] Error procesando comando externo: {e}")
                    try:
                        self.rep_socket.send_json({"ok": False, "error": str(e)})
                    except:
                        pass


    def procesar_evento(self, topico: str, evento: Dict[str, Any]) -> Dict[str, Any] | None:
        interseccion = evento.get("interseccion") or evento.get("interseccionId")
        if not interseccion:
            return None

        # --- Actualizar objetos de dominio tipados ---
        if topico == "camara":
            evento_obj = self._parsear_evento_camara(evento)
            self._ultimo_cam[interseccion] = evento_obj
        elif topico == "espira":
            evento_obj = self._parsear_evento_espira(evento)
            self._ultimo_esp[interseccion] = evento_obj
        elif topico == "gps":
            evento_obj = self._parsear_evento_gps(evento)
            self._ultimo_gps[interseccion] = evento_obj
        else:
            return None

        self.failover.persistir_evento_sensor(evento)

        # --- Mantener contexto plano para retrocompatibilidad con failover/persistencia ---
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

        # --- Evaluar con objetos tipados si todos los sensores reportaron ---
        cam = self._ultimo_cam.get(interseccion)
        esp = self._ultimo_esp.get(interseccion)
        gps = self._ultimo_gps.get(interseccion)

        regla = seleccionar_mejor_regla(self.reglas, cam, esp, gps, contexto)

        if regla is None:
            decision = {
                "interseccion": interseccion,
                "regla_aplicada": "SIN_REGLA",
                "estado_circulacion": EstadoCirculacion.SIN_CLASIFICAR.value,
                "accion": AccionSemaforo.SIN_ACCION.value,
                "duracion_verde_segundos": 15,
                "contexto": dict(contexto),
                "origen": "ANALITICA",
            }
        else:
            decision = {
                "interseccion": interseccion,
                "estado_circulacion": regla.getEstadoResultado().value,
                "accion": regla.getAccion().value,
                "duracion_verde_segundos": regla.getExtensionVerde(),
                "regla_aplicada": regla.reglaId,
                "contexto": dict(contexto),
                "origen": "ANALITICA",
            }

        firma = (
            decision["estado_circulacion"],
            decision["accion"],
            decision["duracion_verde_segundos"],
            decision["regla_aplicada"],
        )
        if self._ultima_firma_por_interseccion.get(interseccion) == firma:
            return None
        self._ultima_firma_por_interseccion[interseccion] = firma

        color = "green" if decision["estado_circulacion"] == "NORMAL" else \
                "red" if "CONGESTION" in decision["estado_circulacion"] else "blue"

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
                "estado_circulacion": EstadoCirculacion.PRIORIZACION.value,
                "accion": AccionSemaforo.PRIORIZAR_VIA.value,
                "duracion_verde_segundos": solicitud.get("duracion_verde_segundos", 20),
                "regla_aplicada": "MANUAL",
                "contexto": {"timestamp": solicitud.get("timestamp"), "detalle": solicitud.get("detalle")},
                "origen": "MANUAL",
            }
        elif tipo == "cambio_manual":
            accion_str = solicitud.get("accion", "CAMBIAR_A_VERDE")
            try:
                accion = AccionSemaforo(accion_str)
            except ValueError:
                accion = AccionSemaforo.CAMBIAR_A_VERDE
            decision = {
                "interseccion": interseccion,
                "estado_circulacion": EstadoCirculacion.PRIORIZACION.value,
                "accion": accion.value,
                "duracion_verde_segundos": solicitud.get("duracion_verde_segundos", 15),
                "regla_aplicada": "MANUAL",
                "contexto": {"timestamp": solicitud.get("timestamp"), "detalle": solicitud.get("detalle")},
                "origen": "MANUAL",
            }
        else:
            return {"ok": False, "error": f"tipo de solicitud no soportado: {tipo}"}

        self.control_semaforos.aplicar_accion(decision)
        self.failover.persistir_decision(decision)
        self.failover.registrar_solicitud({
            "tipo_solicitud": tipo.upper(),
            "interseccion": interseccion,
            "detalle": solicitud.get("detalle"),
            "resultado_resumen": f"Acción ejecutada: {decision['accion']}",
        })
        return {"ok": True, "decision": decision}

    # ----- Helpers privados de parseo -----

    def _parsear_evento_camara(self, d: Dict[str, Any]) -> EventoCamara:
        from src.enums.tipo_sensor import TipoSensor
        import uuid
        return EventoCamara(
            eventoId=d.get("eventoId", str(uuid.uuid4())),
            sensorId=d.get("sensor_id", ""),
            interseccionId=d.get("interseccion", ""),
            tipoSensor=TipoSensor.CAMARA,
            timestamp=datetime.now(timezone.utc),
            volumen=int(d.get("volumen", 0)),
            velocidadPromedio=float(d.get("velocidad_promedio", 0.0)),
        )

    def _parsear_evento_espira(self, d: Dict[str, Any]) -> EventoEspira:
        from src.enums.tipo_sensor import TipoSensor
        import uuid
        ts = datetime.now(timezone.utc)
        return EventoEspira(
            eventoId=d.get("eventoId", str(uuid.uuid4())),
            sensorId=d.get("sensor_id", ""),
            interseccionId=d.get("interseccion", ""),
            tipoSensor=TipoSensor.ESPIRA_INDUCTIVA,
            timestamp=ts,
            vehiculosContados=int(d.get("vehiculos_contados", 0)),
            intervaloSegundos=int(d.get("intervalo_segundos", 30)),
        )

    def _parsear_evento_gps(self, d: Dict[str, Any]) -> EventoGPS:
        from src.enums.tipo_sensor import TipoSensor
        from src.enums.nivel_congestion import NivelCongestion
        import uuid
        try:
            nivel = NivelCongestion(d.get("nivel_congestion", "NORMAL"))
        except ValueError:
            nivel = NivelCongestion.NORMAL
        return EventoGPS(
            eventoId=d.get("eventoId", str(uuid.uuid4())),
            sensorId=d.get("sensor_id", ""),
            interseccionId=d.get("interseccion", ""),
            tipoSensor=TipoSensor.GPS,
            timestamp=datetime.now(timezone.utc),
            velocidadPromedio=float(d.get("velocidad_promedio", 0.0)),
            nivelCongestion=nivel,
        )
