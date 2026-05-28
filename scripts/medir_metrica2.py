from __future__ import annotations

import argparse
import json
import os
import socket as std_socket
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import zmq

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DEFAULT_PC2_IP = "127.0.0.1"
DEFAULT_PC2_PORT = 5562
DEFAULT_INTERSECCIONES = ["INT-A1", "INT-B2", "INT-C3"]


def construir_endpoint_pc2(pc2_ip: str, pc2_port: int) -> str:
    return f"tcp://{pc2_ip}:{pc2_port}"


def _parsear_endpoint_tcp(endpoint: str) -> tuple[str, int] | None:
    if not endpoint.startswith("tcp://"):
        return None
    host_port = endpoint.removeprefix("tcp://")
    if ":" not in host_port:
        return None
    host, port_texto = host_port.rsplit(":", 1)
    try:
        return host, int(port_texto)
    except ValueError:
        return None


def resolver_endpoint_pc2(pc2_ip: str | None, pc2_port: int | None) -> str:
    endpoint_env = os.getenv("PC2_COMMAND_ENDPOINT", "").strip()
    if endpoint_env:
        return endpoint_env

    ip_env = os.getenv("PC2_IP", "").strip()
    port_env = os.getenv("PC2_COMMAND_PORT", "").strip()

    ip_final = pc2_ip or ip_env or DEFAULT_PC2_IP
    port_final = pc2_port or (int(port_env) if port_env else DEFAULT_PC2_PORT)
    return construir_endpoint_pc2(ip_final, port_final)


def verificar_conectividad_tcp(endpoint: str, timeout_ms: int) -> None:
    parsed = _parsear_endpoint_tcp(endpoint)
    if not parsed:
        print(f"[TEST] ADVERTENCIA: no pude interpretar el endpoint {endpoint}")
        return

    host, port = parsed
    try:
        with std_socket.create_connection((host, port), timeout=timeout_ms / 1000):
            print(f"[TEST] TCP OK -> {host}:{port}")
    except OSError as exc:
        print(f"[TEST] TCP FALLA -> {host}:{port} ({exc})")


def _construir_payload(interseccion_codigo: str, detalle: str, duracion_verde_segundos: int) -> dict[str, object]:
    return {
        "tipo": "priorizar_via",
        "interseccion": interseccion_codigo,
        "modo_corredor": "FILA",
        "direccion": "ADELANTE",
        "detalle": detalle,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "duracion_verde_segundos": duracion_verde_segundos,
    }


def medir_una_solicitud(endpoint: str, interseccion_codigo: str, timeout_ms: int) -> float | None:
    context = zmq.Context.instance()
    socket = context.socket(zmq.REQ)
    socket.connect(endpoint)
    socket.setsockopt(zmq.RCVTIMEO, timeout_ms)
    socket.setsockopt(zmq.SNDTIMEO, timeout_ms)
    socket.setsockopt(zmq.LINGER, 0)

    payload = _construir_payload(
        interseccion_codigo=interseccion_codigo,
        detalle=f"Ruta prioritaria - Ambulancia AMB-505",
        duracion_verde_segundos=10,
    )

    print(f"[TEST] Iniciando protocolo de emergencia para ambulancia AMB-505 en ruta hacia {interseccion_codigo}")
    print(f"[TEST] Enviando solicitud a PC2 ({endpoint})...")
    inicio = time.perf_counter()
    try:
        socket.send_json(payload)
        print("[TEST] Esperando respuesta de Analitica...")
        respuesta = socket.recv_json()
        delta = time.perf_counter() - inicio
        print(f"[TEST] delta_seg={delta:.3f}")
        print(f"[TEST] Respuesta recibida: {json.dumps(respuesta, indent=2, ensure_ascii=False)}")
        if respuesta.get("ok"):
            print("[TEST] ¡ÉXITO! Semaforos ajustados.")
        else:
            print(f"[TEST] FALLO en la aplicacion: {respuesta.get('error')}")
        return delta
    except zmq.ZMQError as exc:
        delta = time.perf_counter() - inicio
        print(f"[TEST] ERROR DE COMUNICACION: {exc} (endpoint={endpoint}, timeout_ms={timeout_ms}, delta_seg={delta:.3f})")
        return None
    finally:
        socket.close(0)
        print("[TEST] Conexión cerrada.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Mide la latencia de priorizacion de ambulancia")
    parser.add_argument("--pc2-ip", default=None, help="IP de PC2 donde escucha la analitica")
    parser.add_argument("--pc2-port", type=int, default=None, help="Puerto de comando de analitica en PC2")
    parser.add_argument("--timeout-ms", type=int, default=5000, help="Tiempo de espera para respuesta")
    parser.add_argument("--escenario", default="E1-Base", help="Nombre del escenario a imprimir")
    parser.add_argument(
        "--intersecciones",
        nargs="*",
        default=DEFAULT_INTERSECCIONES,
        help="Lista de intersecciones a medir; por defecto INT-A1 INT-B2 INT-C3",
    )
    args = parser.parse_args()

    endpoint = resolver_endpoint_pc2(args.pc2_ip, args.pc2_port)
    verificar_conectividad_tcp(endpoint, min(args.timeout_ms, 1500))

    deltas: list[float] = []
    for interseccion in args.intersecciones:
        delta = medir_una_solicitud(endpoint, interseccion, args.timeout_ms)
        if delta is not None:
            deltas.append(delta)

    print(f"{args.escenario}:")
    print(f"  N solicitudes : {len(deltas)}")
    if deltas:
        print(f"  Promedio      : {statistics.mean(deltas):.3f} s")
        print(f"  Mínimo        : {min(deltas):.3f} s")
        print(f"  Máximo        : {max(deltas):.3f} s")
    else:
        print("  Promedio      : N/A")
        print("  Mínimo        : N/A")
        print("  Máximo        : N/A")


if __name__ == "__main__":
    main()
