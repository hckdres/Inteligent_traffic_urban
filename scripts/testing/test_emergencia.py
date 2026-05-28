import sys
import os
import zmq
import json
import time
import socket
from datetime import datetime, timezone
import argparse

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(line_buffering=True)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.dominio.ambulancia import Ambulancia

DEFAULT_PC2_IP = "127.0.0.1"
DEFAULT_PC2_PORT = 5562


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
        with socket.create_connection((host, port), timeout=timeout_ms / 1000):
            print(f"[TEST] TCP OK -> {host}:{port}")
    except OSError as exc:
        print(f"[TEST] TCP FALLA -> {host}:{port} ({exc})")


def probar_ambulancia(interseccion_codigo: str, pc2_ip: str, pc2_port: int, timeout_ms: int) -> None:
    endpoint = resolver_endpoint_pc2(pc2_ip, pc2_port)
    verificar_conectividad_tcp(endpoint, min(timeout_ms, 1500))
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(endpoint)
    socket.setsockopt(zmq.RCVTIMEO, timeout_ms)
    socket.setsockopt(zmq.SNDTIMEO, timeout_ms)
    socket.setsockopt(zmq.LINGER, 0)

    ambulancia = Ambulancia(id_vehiculo="AMB-505", velocidad_actual=60.5, ubicacion_actual=interseccion_codigo, en_emergencia=True)
    
    print(f"[TEST] Iniciando protocolo de emergencia para ambulancia {ambulancia.id_vehiculo} en ruta hacia {interseccion_codigo}")
    
    payload = {
        "tipo": "priorizar_via",
        "interseccion": interseccion_codigo,
        "modo_corredor": "FILA",
        "direccion": "ADELANTE",
        "detalle": f"Ruta prioritaria - Ambulancia {ambulancia.id_vehiculo}",
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "duracion_verde_segundos": 10
    }
    
    print(f"[TEST] Enviando solicitud a PC2 ({endpoint})...")
    socket.send_json(payload)
    
    try:
        print("[TEST] Esperando respuesta de Analítica...")
        respuesta = socket.recv_json()
        print(f"[TEST] Respuesta recibida: {json.dumps(respuesta, indent=2)}")
        if respuesta.get("ok"):
            print("[TEST] ¡ÉXITO! Semáforos ajustados.")
        else:
            print(f"[TEST] FALLO en la aplicación: {respuesta.get('error')}")
    except zmq.ZMQError as e:
        print(f"[TEST] ERROR DE COMUNICACIÓN: {e} (endpoint={endpoint}, timeout_ms={timeout_ms})")
    finally:
        socket.close()
        context.term()
        print("[TEST] Conexión cerrada.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prueba manual de priorización de ambulancia")
    parser.add_argument("interseccion", nargs="?", default="INT-A1", help="Intersección objetivo, ej. INT-C3")
    parser.add_argument("--pc2-ip", default=None, help="IP de PC2 donde escucha la analítica")
    parser.add_argument("--pc2-port", type=int, default=None, help="Puerto de comando de analítica en PC2")
    parser.add_argument("--timeout-ms", type=int, default=5000, help="Tiempo de espera para respuesta")
    args = parser.parse_args()

    probar_ambulancia(args.interseccion, args.pc2_ip, args.pc2_port, args.timeout_ms)

