from __future__ import annotations

import json
import threading
from typing import List

from src.config.configuracion_sistema import cargar_configuracion
from src.pc1.sensor_camara import SensorCamara
from src.pc1.sensor_espira import SensorEspira
from src.pc1.sensor_gps import SensorGPS
from src.pc1.secuenciador_eventos import SecuenciadorEventos
from src.messaging.zmq_publisher import ZMQPublisher


BROKER_PUB_ENDPOINT = "tcp://127.0.0.1:5556"


def publicar_eventos_sensor(sensor, publisher: ZMQPublisher, secuenciador: SecuenciadorEventos, stop_event: threading.Event) -> None:
    for evento in sensor.generar_eventos():
        if stop_event.is_set():
            break
        evento["seq"] = secuenciador.siguiente()
        topico = evento.pop("topico")
        publisher.publicar(topico, evento)
        print(
            f"[PC1][seq={evento['seq']}][{sensor.sensor_id}] "
            f"publicado en topico '{topico}': {json.dumps(evento)}"
        )


def cargar_sensores_desde_config(ruta_config: str = "src/config/system.json") -> List[object]:
    config = cargar_configuracion(ruta_config)
    sensores_config = config.get("sensores", [])
    clases_sensor = {
        "camara": SensorCamara,
        "espira_inductiva": SensorEspira,
        "gps": SensorGPS,
    }

    sensores = []
    for sensor_cfg in sensores_config:
        tipo_sensor = sensor_cfg.get("tipo_sensor")
        clase_sensor = clases_sensor.get(tipo_sensor)
        if clase_sensor is None:
            print(f"[PC1] Sensor omitido por tipo no soportado: {tipo_sensor}")
            continue

        sensores.append(
            clase_sensor(
                sensor_id=sensor_cfg["sensor_id"],
                interseccion=sensor_cfg["interseccion"],
                intervalo_segundos=int(sensor_cfg.get("intervalo_segundos", 2)),
                ruta_eventos=sensor_cfg.get("ruta_eventos", "tests/muestras/events_sensores.json"),
            )
        )

    return sensores


def main() -> None:
    publisher = ZMQPublisher(BROKER_PUB_ENDPOINT)
    secuenciador = SecuenciadorEventos()
    stop_event = threading.Event()

    sensores = cargar_sensores_desde_config()
    print(f"[PC1] Sensores cargados: {len(sensores)}")

    hilos = []
    for sensor in sensores:
        hilo = threading.Thread(target=publicar_eventos_sensor, args=(sensor, publisher, secuenciador, stop_event))
        hilo.start()
        hilos.append(hilo)

    try:
        for hilo in hilos:
            hilo.join()
    except KeyboardInterrupt:
        print("[PC1] Deteniendo sensores...")
        stop_event.set()
    finally:
        secuenciador.flush()


if __name__ == "__main__":
    main()
