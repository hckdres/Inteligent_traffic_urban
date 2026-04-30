from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict

from src.pc1.sensor_base import SensorBase
from src.enums.tipo_sensor import TipoSensor
from src.dominio.evento_trafico import EventoEspira


class SensorEspira(SensorBase):
    def __init__(
        self,
        sensor_id: str,
        interseccion: str,
        intervalo_segundos: int = 10,
        ruta_eventos: str = "tests/muestras/events_sensores.json",
    ) -> None:
        super().__init__(
            sensor_id=sensor_id,
            tipo_sensor="espira_inductiva",
            interseccion=interseccion,
            intervalo_segundos=intervalo_segundos,
            ruta_eventos=ruta_eventos,
        )

    def construir_payload(self, evento: Dict[str, Any]) -> Dict[str, Any]:
        ts_fin = self._ts_ahora()
        intervalo = int(evento.get("intervalo_segundos", 30))
        ts_inicio = ts_fin - timedelta(seconds=intervalo)

        obj = EventoEspira(
            eventoId=self._nuevo_evento_id(),
            sensorId=self.sensor_id,
            interseccionId=self.interseccion,
            tipoSensor=TipoSensor.ESPIRA_INDUCTIVA,
            timestamp=ts_fin,
            vehiculosContados=int(evento.get("vehiculos_contados", 0)),
            intervaloSegundos=intervalo,
            timestampInicio=ts_inicio,
            timestampFin=ts_fin,
        )
        payload = {"topico": "espira", "__evento__": obj.serializar()}
        payload.update({
            **self._payload_base(),
            "interseccion": obj.interseccionId,
            "vehiculos_contados": obj.vehiculosContados,
            "intervalo_segundos": obj.intervaloSegundos,
            "timestamp_inicio": obj.timestampInicio.isoformat(),
            "timestamp_fin": obj.timestampFin.isoformat(),
            "tipo_sensor": "espira_inductiva",
        })
        return payload
