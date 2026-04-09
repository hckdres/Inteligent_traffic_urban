from __future__ import annotations

from typing import Any, Dict

from src.pc1.sensor_base import SensorBase
from src.enums.tipo_sensor import TipoSensor
from src.dominio.evento_trafico import EventoCamara


class SensorCamara(SensorBase):
    def __init__(
        self,
        sensor_id: str,
        interseccion: str,
        intervalo_segundos: int = 10,
        ruta_eventos: str = "tests/muestras/events_sensores.json",
    ) -> None:
        super().__init__(
            sensor_id=sensor_id,
            tipo_sensor="camara",
            interseccion=interseccion,
            intervalo_segundos=intervalo_segundos,
            ruta_eventos=ruta_eventos,
        )

    def construir_payload(self, evento: Dict[str, Any]) -> Dict[str, Any]:
        obj = EventoCamara(
            eventoId=self._nuevo_evento_id(),
            sensorId=self.sensor_id,
            interseccionId=self.interseccion,
            tipoSensor=TipoSensor.CAMARA,
            timestamp=self._ts_ahora(),
            volumen=int(evento.get("volumen", 0)),
            velocidadPromedio=float(evento.get("velocidad_promedio", 0.0)),
        )
        # El payload incluye el json + el topico para el broker
        payload = {"topico": "camara", "__evento__": obj.serializar()}
        # También añadimos los campos planos para compatibilidad con la persistencia de PC3
        payload.update({
            "sensor_id": obj.sensorId,
            "interseccion": obj.interseccionId,
            "volumen": obj.volumen,
            "velocidad_promedio": obj.velocidadPromedio,
            "timestamp": obj.timestamp.isoformat(),
            "tipo_sensor": "camara",
        })
        return payload