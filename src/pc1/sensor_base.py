from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List

from src.persistence.repositorio_json import RepositorioJSON
from src.enums.tipo_sensor import TipoSensor


class SensorBase(ABC):
    def __init__(
        self,
        sensor_id: str,
        tipo_sensor: str,
        interseccion: str,
        intervalo_segundos: int = 10,
        ruta_eventos: str = "tests/muestras/events_sensores.json",
    ) -> None:
        self.sensor_id = sensor_id
        self.tipo_sensor = tipo_sensor
        self.interseccion = interseccion
        self.intervalo_segundos = intervalo_segundos
        self.repositorio = RepositorioJSON(ruta_eventos=ruta_eventos)
        self._tipo_sensor_enum = TipoSensor[tipo_sensor.upper()] if tipo_sensor.upper() in TipoSensor.__members__ else None

    def _nuevo_evento_id(self) -> str:
        return str(uuid.uuid4())

    def _ts_ahora(self) -> datetime:
        return datetime.now(timezone.utc)

    def cargar_eventos(self) -> List[Dict[str, Any]]:
        eventos = self.repositorio.filtrar_eventos_por_sensor(self.sensor_id)
        return [evento for evento in eventos if evento.get("tipo_sensor") == self.tipo_sensor]

    @abstractmethod
    def construir_payload(self, evento: Dict[str, Any]) -> Dict[str, Any]:
        pass

    def generar_eventos(self):
        """Genera eventos en loop continuo, reciclando el archivo JSON cuando se agota."""
        eventos = self.cargar_eventos()
        if not eventos:
            print(f"[SENSOR][{self.sensor_id}] Sin eventos en JSON — hilo terminado")
            return

        while True:
            for evento in eventos:
                yield self.construir_payload(evento)
                time.sleep(self.intervalo_segundos)