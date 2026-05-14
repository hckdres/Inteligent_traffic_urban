from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List

from src.persistence.repositorio_json import RepositorioJSON
from src.enums.tipo_sensor import TipoSensor
from src.utils.timezones import COLOMBIA_TZ


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
        self._usa_perfil_sintetico = False

    def _payload_base(self) -> Dict[str, Any]:
        return {"sensor_id": self.sensor_id}

    def _nuevo_evento_id(self) -> str:
        return str(uuid.uuid4())

    def _ts_ahora(self) -> datetime:
        return datetime.now(COLOMBIA_TZ)

    def cargar_eventos(self) -> List[Dict[str, Any]]:
        eventos = self.repositorio.filtrar_eventos_por_sensor(self.sensor_id)
        eventos_filtrados = [evento for evento in eventos if evento.get("tipo_sensor") == self.tipo_sensor]
        if eventos_filtrados:
            return eventos_filtrados

        self._usa_perfil_sintetico = True
        return self._generar_eventos_sinteticos()

    @abstractmethod
    def construir_payload(self, evento: Dict[str, Any]) -> Dict[str, Any]:
        pass

    def generar_eventos(self):
        """Genera eventos en loop continuo, reciclando el archivo JSON cuando se agota."""
        eventos = self.cargar_eventos()
        if not eventos:
            print(f"[SENSOR][{self.sensor_id}] Sin eventos en JSON — hilo terminado")
            return

        if self._usa_perfil_sintetico:
            print(
                f"[SENSOR][{self.sensor_id}] usando perfil sintetico para {self.interseccion}"
            )

        while True:
            for evento in eventos:
                yield self.construir_payload(evento)
                time.sleep(self.intervalo_segundos)

    def _generar_eventos_sinteticos(self) -> List[Dict[str, Any]]:
        fila, columna = self._descomponer_interseccion()
        offset = (ord(fila) - ord("A")) * 3 + (columna - 1)

        plantillas = {
            "camara": [
                {"volumen": 3, "velocidad_promedio": 42},
                {"volumen": 8, "velocidad_promedio": 23},
                {"volumen": 14, "velocidad_promedio": 11},
                {"volumen": 4, "velocidad_promedio": 37},
            ],
            "espira_inductiva": [
                {"vehiculos_contados": 5, "intervalo_segundos": 30},
                {"vehiculos_contados": 14, "intervalo_segundos": 30},
                {"vehiculos_contados": 26, "intervalo_segundos": 30},
                {"vehiculos_contados": 6, "intervalo_segundos": 30},
            ],
            "gps": [
                {"nivel_congestion": "NORMAL", "velocidad_promedio": 40, "densidad": 14},
                {"nivel_congestion": "BAJA", "velocidad_promedio": 21, "densidad": 24},
                {"nivel_congestion": "BAJA", "velocidad_promedio": 9, "densidad": 37},
                {"nivel_congestion": "ALTA", "velocidad_promedio": 36, "densidad": 16},
            ],
        }

        ajustes = {
            "camara": {"volumen": offset % 3, "velocidad_promedio": (offset % 4) - 1},
            "espira_inductiva": {"vehiculos_contados": offset % 5},
            "gps": {"velocidad_promedio": offset % 3, "densidad": offset % 4},
        }

        eventos = []
        tipo_plantillas = plantillas.get(self.tipo_sensor, [])
        tipo_ajustes = ajustes.get(self.tipo_sensor, {})

        for indice in range(len(tipo_plantillas)):
            base = dict(tipo_plantillas[(indice + offset) % len(tipo_plantillas)])
            for clave, delta in tipo_ajustes.items():
                if clave not in base:
                    continue
                if clave == "velocidad_promedio" and indice == 2:
                    base[clave] = max(5, float(base[clave]) - delta)
                else:
                    base[clave] = max(1, float(base[clave]) + delta) if isinstance(base[clave], float) else max(1, int(base[clave]) + delta)
            eventos.append(base)

        return eventos

    def _descomponer_interseccion(self) -> tuple[str, int]:
        sufijo = self.interseccion.split("-", 1)[1]
        return sufijo[0], int(sufijo[1:])
