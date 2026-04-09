from __future__ import annotations

from typing import Any, Dict

from src.pc1.sensor_base import SensorBase


class SensorEspira(SensorBase):
    def __init__(
        self,
        sensor_id: str,
        interseccion: str,
        intervalo_segundos: int = 10,
        ruta_eventos: str = "data/events_sensores.json",
    ) -> None:
        super().__init__(
            sensor_id=sensor_id,
            tipo_sensor="espira_inductiva",
            interseccion=interseccion,
            intervalo_segundos=intervalo_segundos,
            ruta_eventos=ruta_eventos,
        )

    def construir_payload(self, evento: Dict[str, Any]) -> Dict[str, Any]:
        from datetime import datetime, timezone, timedelta
        ts_fin = datetime.now(timezone.utc)
        ts_inicio = ts_fin - timedelta(seconds=evento.get("intervalo_segundos", 30))
        fmt = lambda dt: dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        return {
            "sensor_id": evento["sensor_id"],
            "tipo_sensor": "espira_inductiva",
            "interseccion": evento["interseccion"],
            "vehiculos_contados": evento["vehiculos_contados"],
            "intervalo_segundos": evento["intervalo_segundos"],
            "timestamp_inicio": fmt(ts_inicio),
            "timestamp_fin": fmt(ts_fin),
            "topico": "espira"
        }