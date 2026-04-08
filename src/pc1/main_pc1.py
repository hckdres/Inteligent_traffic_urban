from __future__ import annotations

import json
import threading

from src.pc1.sensor_camara import SensorCamara
from src.pc1.sensor_espira import SensorEspira
from src.pc1.sensor_gps import SensorGPS
from src.messaging.zmq_publisher import ZMQPublisher


BROKER_PUB_ENDPOINT = "tcp://127.0.0.1:5556"


def publicar_eventos_sensor(sensor, publisher: ZMQPublisher) -> None:
    for evento in sensor.generar_eventos():
        topico = evento.pop("topico")
        publisher.publicar(topico, evento)
        print(f"[PC1][{sensor.sensor_id}] publicado en topico '{topico}': {json.dumps(evento)}")


def main() -> None:
    publisher = ZMQPublisher(BROKER_PUB_ENDPOINT)

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
        hilo = threading.Thread(target=publicar_eventos_sensor, args=(sensor, publisher), daemon=True)
        hilo.start()
        hilos.append(hilo)

    for hilo in hilos:
        hilo.join()


if __name__ == "__main__":
    main()