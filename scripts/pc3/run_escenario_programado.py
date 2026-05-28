from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

import zmq

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(line_buffering=True)

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.messaging.zmq_publisher import ZMQPublisher
from src.utils.timezones import COLOMBIA_TZ


DEFAULT_CONFIG_PATH = "src/config/system_3x5.json"
DEFAULT_SCENARIO_PATH = "src/config/escenario_3x5_programado.json"
DEFAULT_BROKER_ENDPOINT = "tcp://127.0.0.1:5556"
DEFAULT_PC2_COMMAND_ENDPOINT = "tcp://127.0.0.1:5562"
DEFAULT_PRIMARY_ADMIN_ENDPOINT = "tcp://127.0.0.1:5566"


def _leer_json(ruta: str) -> Dict[str, Any]:
    path = Path(ruta)
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo: {ruta}")
    with path.open("r", encoding="utf-8") as archivo:
        return json.load(archivo)


def _indice_sensores(config: Dict[str, Any]) -> Dict[tuple[str, str], str]:
    indice: Dict[tuple[str, str], str] = {}
    for sensor in config.get("sensores", []):
        interseccion = str(sensor.get("interseccion", ""))
        tipo = str(sensor.get("tipo_sensor", ""))
        sensor_id = str(sensor.get("sensor_id", ""))
        if interseccion and tipo and sensor_id:
            indice[(interseccion, tipo)] = sensor_id
    return indice


def _hora_colombia() -> str:
    return datetime.now(COLOMBIA_TZ).strftime("%H:%M:%S")


def _nuevo_socket_req(contexto: zmq.Context, endpoint: str, timeout_ms: int) -> zmq.Socket:
    socket = contexto.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, timeout_ms)
    socket.setsockopt(zmq.SNDTIMEO, timeout_ms)
    socket.setsockopt(zmq.LINGER, 0)
    socket.connect(endpoint)
    return socket


def _enviar_req_json(
    contexto: zmq.Context,
    endpoint: str,
    payload: Dict[str, Any],
    timeout_ms: int = 5000,
) -> Dict[str, Any]:
    socket = _nuevo_socket_req(contexto, endpoint, timeout_ms)
    try:
        socket.send_json(payload)
        return socket.recv_json()
    except zmq.ZMQError as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        socket.close(0)


def _payload_camara(sensor_id: str, interseccion: str) -> Dict[str, Any]:
    ahora = datetime.now(COLOMBIA_TZ).isoformat(timespec="seconds")
    return {
        "sensor_id": sensor_id,
        "interseccion": interseccion,
        "volumen": 18,
        "velocidad_promedio": 8,
        "timestamp": ahora,
        "tipo_sensor": "camara",
    }


def _payload_espira(sensor_id: str, interseccion: str) -> Dict[str, Any]:
    ts_fin = datetime.now(COLOMBIA_TZ)
    ts_inicio = ts_fin - timedelta(seconds=30)
    return {
        "sensor_id": sensor_id,
        "interseccion": interseccion,
        "vehiculos_contados": 30,
        "intervalo_segundos": 30,
        "timestamp_inicio": ts_inicio.isoformat(timespec="seconds"),
        "timestamp_fin": ts_fin.isoformat(timespec="seconds"),
        "tipo_sensor": "espira_inductiva",
    }


def _payload_gps(sensor_id: str, interseccion: str) -> Dict[str, Any]:
    ahora = datetime.now(COLOMBIA_TZ).isoformat(timespec="seconds")
    return {
        "sensor_id": sensor_id,
        "interseccion": interseccion,
        "nivel_congestion": "ALTA",
        "velocidad_promedio": 8,
        "densidad": 38,
        "timestamp": ahora,
        "tipo_sensor": "gps",
    }


def _publicar_congestion(
    publisher: ZMQPublisher,
    indice_sensores: Dict[tuple[str, str], str],
    interseccion: str,
) -> None:
    sensor_camara = indice_sensores.get((interseccion, "camara"))
    sensor_espira = indice_sensores.get((interseccion, "espira_inductiva"))
    sensor_gps = indice_sensores.get((interseccion, "gps"))
    if not sensor_camara or not sensor_espira or not sensor_gps:
        raise ValueError(f"No se encontraron los sensores para {interseccion}")

    publisher.publicar("camara", _payload_camara(sensor_camara, interseccion))
    time.sleep(0.05)
    publisher.publicar("espira", _payload_espira(sensor_espira, interseccion))
    time.sleep(0.05)
    publisher.publicar("gps", _payload_gps(sensor_gps, interseccion))


def _emitir_ambulancia(
    contexto: zmq.Context,
    endpoint: str,
    interseccion: str,
    duracion_segundos: int,
) -> Dict[str, Any]:
    payload = {
        "tipo": "priorizar_via",
        "interseccion": interseccion,
        "modo_corredor": "FILA",
        "direccion": "ADELANTE",
        "detalle": f"Ambulancia programada en {interseccion}",
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "duracion_verde_segundos": duracion_segundos,
    }
    return _enviar_req_json(contexto, endpoint, payload)


def _simular_caida_primary(contexto: zmq.Context, endpoint: str) -> Dict[str, Any]:
    return _enviar_req_json(contexto, endpoint, {"tipo": "SIMULAR_CAIDA"})


def main() -> None:
    parser = argparse.ArgumentParser(description="Ejecuta un escenario programado de congestiones y ambulancias.")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Ruta a la configuracion de la ciudad")
    parser.add_argument("--scenario", default=DEFAULT_SCENARIO_PATH, help="Ruta al archivo JSON del escenario")
    parser.add_argument("--broker-endpoint", default=DEFAULT_BROKER_ENDPOINT, help="Endpoint PUB del broker de PC1")
    parser.add_argument("--pc2-command-endpoint", default=DEFAULT_PC2_COMMAND_ENDPOINT, help="Endpoint REQ de analitica en PC2")
    parser.add_argument("--primary-admin-endpoint", default=DEFAULT_PRIMARY_ADMIN_ENDPOINT, help="Endpoint admin de la BD primaria en PC3")
    parser.add_argument("--time-scale", type=float, default=1.0, help="Factor para acelerar o desacelerar el escenario")
    parser.add_argument("--warmup", type=float, default=2.0, help="Espera inicial antes de disparar la primera accion")
    args = parser.parse_args()

    config = _leer_json(args.config)
    escenario = _leer_json(args.scenario)
    indice_sensores = _indice_sensores(config)
    acciones = sorted(escenario.get("acciones", []), key=lambda item: float(item.get("segundo", 0)))

    if not acciones:
        raise SystemExit("El escenario no tiene acciones")

    contexto = zmq.Context.instance()
    publisher = ZMQPublisher(args.broker_endpoint)

    print(f"[ESCENARIO] Configuracion: {args.config}")
    print(f"[ESCENARIO] Escenario: {args.scenario}")
    print(f"[ESCENARIO] Acciones: {len(acciones)}")
    print(f"[ESCENARIO] Warmup: {args.warmup}s | time-scale: {args.time_scale}")
    time.sleep(max(0.0, args.warmup))

    inicio = time.monotonic()
    for accion in acciones:
        segundo_objetivo = float(accion.get("segundo", 0))
        tiempo_objetivo = inicio + (segundo_objetivo * max(args.time_scale, 0.0))
        while True:
            ahora = time.monotonic()
            restante = tiempo_objetivo - ahora
            if restante <= 0:
                break
            time.sleep(min(0.5, restante))

        tipo = str(accion.get("tipo", "")).strip().lower()
        if tipo == "congestion":
            interseccion = str(accion.get("interseccion", "")).strip()
            if not interseccion:
                raise ValueError("La accion de congestion requiere interseccion")
            print(f"[{_hora_colombia()}][ESCENARIO] congestion -> {interseccion} (t={segundo_objetivo}s)")
            _publicar_congestion(publisher, indice_sensores, interseccion)
        elif tipo == "ambulancia":
            interseccion = str(accion.get("interseccion", "")).strip()
            duracion = int(accion.get("duracion_verde_segundos", 20))
            if not interseccion:
                raise ValueError("La accion de ambulancia requiere interseccion")
            print(f"[{_hora_colombia()}][ESCENARIO] ambulancia -> {interseccion} (t={segundo_objetivo}s)")
            respuesta = _emitir_ambulancia(contexto, args.pc2_command_endpoint, interseccion, duracion)
            print(f"[{_hora_colombia()}][ESCENARIO] respuesta ambulancia: {json.dumps(respuesta, ensure_ascii=False)}")
        elif tipo in {"caida_primary", "caida", "fallo_primary"}:
            print(f"[{_hora_colombia()}][ESCENARIO] simulando caida de BD primaria (t={segundo_objetivo}s)")
            respuesta = _simular_caida_primary(contexto, args.primary_admin_endpoint)
            print(f"[{_hora_colombia()}][ESCENARIO] respuesta caida: {json.dumps(respuesta, ensure_ascii=False)}")
        else:
            raise ValueError(f"Tipo de accion no soportado: {tipo}")

    print("[ESCENARIO] Escenario finalizado")


if __name__ == "__main__":
    main()
