from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import yaml
import zmq

from src.dominio.regla_trafico import ReglaTrafico, seleccionar_mejor_regla
from src.pc2.control_semaforos import ControlSemaforos
from src.pc2.gestor_persistencia import GestorPersistencia


PC2_PULL_ENDPOINT = "tcp://127.0.0.1:5557"


class ServicioAnalitica:
    def __init__(self, ruta_reglas: str = "config/rules.yaml") -> None:
        self.ruta_reglas = Path(ruta_reglas)
        self.reglas = self._cargar_reglas()
        self.control_semaforos = ControlSemaforos()
        self.persistencia = GestorPersistencia()

        self.context = zmq.Context.instance()
        self.pull_socket = self.context.socket(zmq.PULL)
        self.pull_socket.connect(PC2_PULL_ENDPOINT)

        self.contextos_por_interseccion: Dict[str, Dict[str, Any]] = {}

    def _cargar_reglas(self) -> List[ReglaTrafico]:
        if not self.ruta_reglas.exists():
            raise FileNotFoundError(f"No existe el archivo de reglas: {self.ruta_reglas}")

        with self.ruta_reglas.open("r", encoding="utf-8") as archivo:
            data = yaml.safe_load(archivo)

        return [ReglaTrafico.desde_dict(item) for item in data.get("reglas", [])]

    def escuchar_eventos(self) -> None:
        print("[ANALITICA] escuchando eventos desde el broker...")

        while True:
            mensaje = self.pull_socket.recv_string()
            topico, payload_json = mensaje.split(" ", 1)
            evento = json.loads(payload_json)

            print(f"[ANALITICA] recibido topico={topico} evento={evento}")

            decision = self.procesar_evento(topico, evento)
            if decision:
                self.control_semaforos.aplicar_accion(decision)
                self.persistencia.persistir_evento_procesado(decision)

    def procesar_evento(self, topico: str, evento: Dict[str, Any]) -> Dict[str, Any] | None:
        interseccion = evento["interseccion"]

        if interseccion not in self.contextos_por_interseccion:
            self.contextos_por_interseccion[interseccion] = {
                "interseccion": interseccion
            }

        contexto = self.contextos_por_interseccion[interseccion]

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
            }
        else:
            decision = {
                "interseccion": interseccion,
                "estado_circulacion": regla.resultado.estado_circulacion,
                "accion": regla.resultado.accion,
                "duracion_verde_segundos": regla.resultado.duracion_verde_segundos,
                "regla_aplicada": regla.id,
                "contexto": dict(contexto),
            }

        print(
            f"[ANALITICA] decision -> interseccion={decision['interseccion']} | "
            f"estado={decision['estado_circulacion']} | accion={decision['accion']}"
        )

        return decision