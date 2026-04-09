import sys
import os
import zmq
import json
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.dominio.ambulancia import Ambulancia

PC3_COMMAND_ENDPOINT = "tcp://127.0.0.1:5562" # Reenvía a analítica PC2

def probar_ambulancia(interseccion_codigo: str):
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(PC3_COMMAND_ENDPOINT)
    socket.setsockopt(zmq.RCVTIMEO, 2000)

    ambulancia = Ambulancia(id_vehiculo="AMB-505", velocidad_actual=60.5, ubicacion_actual=interseccion_codigo, en_emergencia=True)
    
    print(f"[TEST] Iniciando protocolo de emergencia para ambulancia {ambulancia.id_vehiculo} en ruta hacia {interseccion_codigo}")
    
    payload = {
        "tipo": "priorizar_via",
        "interseccion": interseccion_codigo,
        "detalle": f"Ruta prioritaria - Ambulancia {ambulancia.id_vehiculo}",
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "duracion_verde_segundos": 30
    }
    
    print(f"[TEST] Enviando solicitud a PC2 ({PC3_COMMAND_ENDPOINT})...")
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
        print(f"[TEST] ERROR DE COMUNICACIÓN: {e}")
    finally:
        socket.close()
        context.term()
        print("[TEST] Conexión cerrada.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        inter = sys.argv[1]
    else:
        inter = "INT-A1"
    probar_ambulancia(inter)

