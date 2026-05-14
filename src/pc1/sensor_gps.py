from __future__ import annotations

from typing import Any, Dict

from src.pc1.sensor_base import SensorBase
from src.enums.tipo_sensor import TipoSensor
from src.enums.nivel_congestion import NivelCongestion
from src.dominio.evento_trafico import EventoGPS


class SensorGPS(SensorBase):
    def __init__(
        self,
        sensor_id: str,
        interseccion: str,
        intervalo_segundos: int = 10,
        ruta_eventos: str = "tests/muestras/events_sensores.json",
    ) -> None:
        super().__init__(
            sensor_id=sensor_id,
            tipo_sensor="gps",
            interseccion=interseccion,
            intervalo_segundos=intervalo_segundos,
            ruta_eventos=ruta_eventos,
        )

    def construir_payload(self, evento: Dict[str, Any]) -> Dict[str, Any]:
        nivel_raw = evento.get("nivel_congestion", "NORMAL")
        try:
            nivel = NivelCongestion(nivel_raw)
        except ValueError:
            nivel = NivelCongestion.NORMAL

        obj = EventoGPS(
            eventoId=self._nuevo_evento_id(),
            sensorId=self.sensor_id,
            interseccionId=self.interseccion,
            tipoSensor=TipoSensor.GPS,
            timestamp=self._ts_ahora(),
            velocidadPromedio=float(evento.get("velocidad_promedio", 0.0)),
            nivelCongestion=nivel,
        )
        payload = {"topico": "gps", "__evento__": obj.serializar()}
        payload.update({
            **self._payload_base(),
            "interseccion": obj.interseccionId,
            "nivel_congestion": obj.nivelCongestion.value,
            "velocidad_promedio": obj.velocidadPromedio,
            "densidad": evento.get("densidad", 0.0),
            "timestamp": obj.timestamp.isoformat(),
            "tipo_sensor": "gps",
        })
        return payload
