from __future__ import annotations

from typing import Any, Dict

from src.pc1.sensor_base import SensorBase


class SensorGPS(SensorBase):
    def __init__(
        self,
        sensor_id: str,
        interseccion: str,
        intervalo_segundos: int = 10,
        ruta_eventos: str = "data/events_sensores.json",
    ) -> None:
        super().__init__(
            sensor_id=sensor_id,
            tipo_sensor="gps",
            interseccion=interseccion,
            intervalo_segundos=intervalo_segundos,
            ruta_eventos=ruta_eventos,
        )

    def construir_payload(self, evento: Dict[str, Any]) -> Dict[str, Any]:
        from datetime import datetime, timezone
        return {
            "sensor_id": evento["sensor_id"],
            "tipo_sensor": "gps",
            "interseccion": evento["interseccion"],
            "nivel_congestion": evento["nivel_congestion"],
            "velocidad_promedio": evento["velocidad_promedio"],
            "densidad": evento["densidad"],
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "topico": "gps"
        }