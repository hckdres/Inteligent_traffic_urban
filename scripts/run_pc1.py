"""
PC1 — Nodo de Captura
Lanza: broker_zmq + todos los sensores en hilos separados

Uso:
    python scripts/run_pc1.py                        # IPs por defecto (localhost)
    python scripts/run_pc1.py --pc2-ip 192.168.1.20  # PC2 en otra máquina
    python scripts/run_pc1.py --config src/config/system_escenario1.json
"""
from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(line_buffering=True)

# Permitir imports desde la raíz del proyecto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pc1.broker_zmq import main as broker_simple
from src.pc1.broker_zmq_multihilo import BrokerMultihilo
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
            if stop_event.is_set():
                break


def main(pc2_ip: str, multihilo: bool, config_path: str) -> None:
    broker_endpoint_local = "tcp://127.0.0.1:5556"
    broker_pc2_endpoint = f"tcp://{pc2_ip}:5557"

    print(f"[PC1] Iniciando — broker enviará eventos a PC2 en {broker_pc2_endpoint}")

    if multihilo:
        import src.pc1.broker_zmq_multihilo as bm
        bm.PC2_PULL_ENDPOINT = broker_pc2_endpoint
        hilo_broker = threading.Thread(target=lambda: BrokerMultihilo().iniciar(), daemon=True)
    else:
        import src.pc1.broker_zmq as b
        b.PC2_PUSH_ENDPOINT = broker_pc2_endpoint
        hilo_broker = threading.Thread(target=broker_simple, daemon=True)

    hilo_broker.start()
    print(f"[PC1] Broker {'multihilo' if multihilo else 'simple'} iniciado")

    print("[PC1] Esperando estabilización de sockets ZMQ...")
    time.sleep(2)

    publisher = ZMQPublisher(broker_endpoint_local)
    secuenciador = SecuenciadorEventos()
    stop_event = threading.Event()
    sensores = cargar_sensores_desde_config(config_path)

    hilos = []
    for sensor in sensores:
        hilo = threading.Thread(
            target=publicar_eventos_sensor,
            args=(sensor, publisher, secuenciador, stop_event),
            name=f"sensor-{sensor.sensor_id}",
        )
        hilo.start()
        hilos.append(hilo)

    print(f"[PC1] {len(sensores)} sensores activos")
    try:
        for hilo in hilos:
            hilo.join()
    except KeyboardInterrupt:
        print("[PC1] Deteniendo captura...")
        stop_event.set()
    finally:
        secuenciador.flush()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PC1 — Nodo de Captura")
    parser.add_argument("--pc2-ip", default="127.0.0.1", help="IP de PC2 (default: 127.0.0.1)")
    parser.add_argument("--multihilo", action="store_true", help="Usar broker multihilo")
    parser.add_argument(
        "--config",
        default="src/config/system.json",
        help="Ruta al archivo de configuración del sistema",
    )
    args = parser.parse_args()
    main(pc2_ip=args.pc2_ip, multihilo=args.multihilo, config_path=args.config)
