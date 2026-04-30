from __future__ import annotations

import json
import threading
from pathlib import Path

from src.pc1.sensor_camara import SensorCamara
from src.pc1.sensor_espira import SensorEspira
from src.pc1.sensor_gps import SensorGPS
from src.messaging.zmq_publisher import ZMQPublisher


BROKER_PUB_ENDPOINT = "tcp://127.0.0.1:5556"


class SecuenciadorEventos:
    def __init__(self, ruta_estado: str = "data/pc1_event_seq.txt", inicio: int = 1) -> None:
        self._ruta_estado = Path(ruta_estado)
        self._ruta_estado.parent.mkdir(parents=True, exist_ok=True)
        self._siguiente = self._cargar_siguiente(inicio)
        self._lock = threading.Lock()

    def siguiente(self) -> int:
        with self._lock:
            seq = self._siguiente
            self._siguiente += 1
            self._guardar_siguiente()
            return seq

    def _cargar_siguiente(self, inicio: int) -> int:
        if not self._ruta_estado.exists():
            return inicio
        try:
            valor = int(self._ruta_estado.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            return inicio
        return valor if valor > 0 else inicio

    def _guardar_siguiente(self) -> None:
        temporal = self._ruta_estado.with_suffix(".tmp")
        temporal.write_text(str(self._siguiente), encoding="utf-8")
        temporal.replace(self._ruta_estado)


def publicar_eventos_sensor(sensor, publisher: ZMQPublisher, secuenciador: SecuenciadorEventos) -> None:
    for evento in sensor.generar_eventos():
        evento["seq"] = secuenciador.siguiente()
        topico = evento.pop("topico")
        publisher.publicar(topico, evento)
        print(
            f"[PC1][seq={evento['seq']}][{sensor.sensor_id}] "
            f"publicado en topico '{topico}': {json.dumps(evento)}"
        )


def main() -> None:
    publisher = ZMQPublisher(BROKER_PUB_ENDPOINT)
    secuenciador = SecuenciadorEventos()

    sensores = [
        SensorCamara("CAM-A1", "INT-A1", intervalo_segundos=2),
        SensorEspira("ESP-A1", "INT-A1", intervalo_segundos=2),
        SensorGPS("GPS-A1", "INT-A1", intervalo_segundos=2),

        SensorCamara("CAM-B2", "INT-B2", intervalo_segundos=2),
        SensorEspira("ESP-B2", "INT-B2", intervalo_segundos=2),
        SensorGPS("GPS-B2", "INT-B2", intervalo_segundos=2),

        SensorCamara("CAM-C3", "INT-C3", intervalo_segundos=2),
        SensorEspira("ESP-C3", "INT-C3", intervalo_segundos=2),
        SensorGPS("GPS-C3", "INT-C3", intervalo_segundos=2),
    ]

    hilos = []
    for sensor in sensores:
        hilo = threading.Thread(target=publicar_eventos_sensor, args=(sensor, publisher, secuenciador), daemon=True)
        hilo.start()
        hilos.append(hilo)

    for hilo in hilos:
        hilo.join()


if __name__ == "__main__":
    main()
