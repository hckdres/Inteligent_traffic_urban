from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from src.persistence.repositorio_json import RepositorioJSON


class SensorBase(ABC):
    def __init__(
        self,
        sensor_id: str,
        tipo_sensor: str,
        interseccion: str,
        intervalo_segundos: int = 10,
        ruta_eventos: str = "data/events_sensores.json",
    ) -> None:
        self.sensor_id = sensor_id
        self.tipo_sensor = tipo_sensor
        self.interseccion = interseccion
        self.intervalo_segundos = intervalo_segundos
        self.repositorio = RepositorioJSON(ruta_eventos=ruta_eventos)

    def cargar_eventos(self) -> List[Dict[str, Any]]:
        eventos = self.repositorio.filtrar_eventos_por_sensor(self.sensor_id)
        return [evento for evento in eventos if evento.get("tipo_sensor") == self.tipo_sensor]

    @abstractmethod
    def construir_payload(self, evento: Dict[str, Any]) -> Dict[str, Any]:
        pass

    def generar_eventos(self):
        eventos = self.cargar_eventos()
        for evento in eventos:
            yield self.construir_payload(evento)
            time.sleep(self.intervalo_segundos)