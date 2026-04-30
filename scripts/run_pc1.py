"""
PC1 — Nodo de Captura
Lanza: broker_zmq + todos los sensores en hilos separados

Uso:
    python scripts/run_pc1.py                        # IPs por defecto (localhost)
    python scripts/run_pc1.py --pc2-ip 192.168.1.20  # PC2 en otra máquina
"""
from __future__ import annotations

import argparse
import os
import sys
import threading
from datetime import datetime
from pathlib import Path

# Permitir imports desde la raíz del proyecto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from src.pc1.broker_zmq import main as broker_simple
from src.pc1.broker_zmq_multihilo import BrokerMultihilo
from src.pc1.sensor_camara import SensorCamara
from src.pc1.sensor_espira import SensorEspira
from src.pc1.sensor_gps import SensorGPS
from src.messaging.zmq_publisher import ZMQPublisher
from src.utils.timezones import COLOMBIA_TZ


def _hora_colombia() -> str:
    return datetime.now(COLOMBIA_TZ).strftime("%H:%M:%S")


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
            f"[{_hora_colombia()}][PC1][seq={evento['seq']}][{sensor.sensor_id}] "
            f"topico='{topico}' interseccion={evento.get('interseccion')} "
            f"ts={evento.get('timestamp') or evento.get('timestamp_fin')}"
        )


def main(pc2_ip: str, multihilo: bool) -> None:
    broker_endpoint_local = "tcp://127.0.0.1:5556"
    broker_pc2_endpoint   = f"tcp://{pc2_ip}:5557"

    print(f"[PC1] Iniciando — broker enviará eventos a PC2 en {broker_pc2_endpoint}")

    # Parchear endpoints del broker con la IP real de PC2
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

    publisher = ZMQPublisher(broker_endpoint_local)
    secuenciador = SecuenciadorEventos()

    sensores = [
        SensorCamara("CAM-A1", "INT-A1", intervalo_segundos=2),
        SensorEspira("ESP-A1", "INT-A1", intervalo_segundos=2),
        SensorGPS   ("GPS-A1", "INT-A1", intervalo_segundos=2),

        SensorCamara("CAM-B2", "INT-B2", intervalo_segundos=2),
        SensorEspira("ESP-B2", "INT-B2", intervalo_segundos=2),
        SensorGPS   ("GPS-B2", "INT-B2", intervalo_segundos=2),

        SensorCamara("CAM-C3", "INT-C3", intervalo_segundos=2),
        SensorEspira("ESP-C3", "INT-C3", intervalo_segundos=2),
        SensorGPS   ("GPS-C3", "INT-C3", intervalo_segundos=2),
    ]

    hilos = []
    for sensor in sensores:
        hilo = threading.Thread(
            target=publicar_eventos_sensor,
            args=(sensor, publisher, secuenciador),
            daemon=True,
            name=f"sensor-{sensor.sensor_id}",
        )
        hilo.start()
        hilos.append(hilo)

    print(f"[PC1] {len(sensores)} sensores activos")
    for hilo in hilos:
        hilo.join()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PC1 — Nodo de Captura")
    parser.add_argument("--pc2-ip", default="127.0.0.1", help="IP de PC2 (default: 127.0.0.1)")
    parser.add_argument("--multihilo", action="store_true", help="Usar broker multihilo")
    args = parser.parse_args()
    main(pc2_ip=args.pc2_ip, multihilo=args.multihilo)
