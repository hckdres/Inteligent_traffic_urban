from __future__ import annotations

import argparse
import threading
from datetime import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.common_bootstrap import bootstrap_project_root

bootstrap_project_root()

from src.pc1.main_pc1 import cargar_sensores_desde_config
from src.pc1.secuenciador_eventos import SecuenciadorEventos
from src.messaging.zmq_publisher import ZMQPublisher
from src.utils.timezones import COLOMBIA_TZ


def _hora_colombia() -> str:
    return datetime.now(COLOMBIA_TZ).strftime("%H:%M:%S")


def publicar_eventos_sensor(sensor, publisher: ZMQPublisher, secuenciador: SecuenciadorEventos, stop_event: threading.Event) -> None:
    for evento in sensor.generar_eventos():
        if stop_event.is_set():
            break
        try:
            evento["seq"] = secuenciador.siguiente()
            topico = evento.pop("topico")
            publisher.publicar(topico, evento)
            print(
                f"[{_hora_colombia()}][PC1][seq={evento['seq']}][{sensor.sensor_id}] "
                f"topico='{topico}' interseccion={evento.get('interseccion')} "
                f"ts={evento.get('timestamp') or evento.get('timestamp_fin')}"
            )
        except Exception as exc:
            print(f"[PC1][ERROR][{sensor.sensor_id}] {exc}")


def main(broker_ip: str, broker_port: int) -> None:
    endpoint = f"tcp://{broker_ip}:{broker_port}"
    publisher = ZMQPublisher(endpoint)
    secuenciador = SecuenciadorEventos()
    stop_event = threading.Event()
    sensores = cargar_sensores_desde_config()

    print(f"[PC1-SENSORES] publicando en {endpoint}")
    print(f"[PC1-SENSORES] sensores activos={len(sensores)}")

    hilos = []
    for sensor in sensores:
        hilo = threading.Thread(
            target=publicar_eventos_sensor,
            args=(sensor, publisher, secuenciador, stop_event),
            name=f"sensor-{sensor.sensor_id}",
        )
        hilo.start()
        hilos.append(hilo)

    try:
        for hilo in hilos:
            hilo.join()
    except KeyboardInterrupt:
        stop_event.set()
    finally:
        secuenciador.flush()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PC1 - Sensores (componente separado)")
    parser.add_argument("--broker-ip", default="127.0.0.1")
    parser.add_argument("--broker-port", type=int, default=5556)
    args = parser.parse_args()
    main(args.broker_ip, args.broker_port)
