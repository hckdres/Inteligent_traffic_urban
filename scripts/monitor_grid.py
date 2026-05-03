from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import zmq
from rich.console import Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.utils.timezones import COLOMBIA_TZ


PRIMARY_QUERY_ENDPOINT = "tcp://127.0.0.1:5564"
REPLICA_QUERY_ENDPOINT = "tcp://127.0.0.1:5565"
DEFAULT_INTERVAL_SECONDS = 1.0


def cargar_intersecciones() -> Tuple[List[str], int, int]:
    ruta = Path("src/config/system.json")
    if not ruta.exists():
        return [], 0, 0

    with ruta.open("r", encoding="utf-8") as archivo:
        data = json.load(archivo)

    intersecciones = data.get("ciudad", {}).get("intersecciones", [])
    filas = int(data.get("ciudad", {}).get("filas", 0))
    columnas = int(data.get("ciudad", {}).get("columnas", 0))
    return intersecciones, filas, columnas


class ConsultorEstado:
    def __init__(self, timeout_ms: int = 500, reintento_primaria_segundos: float = 3.0) -> None:
        self.context = zmq.Context.instance()
        self.timeout_ms = timeout_ms
        self.reintento_primaria_segundos = reintento_primaria_segundos
        self._primaria_disponible = True
        self._reintentar_primaria_en = 0.0

    def consultar_interseccion(self, interseccion: str) -> Dict[str, Any]:
        payload = {"tipo": "consultar_interseccion", "interseccion": interseccion}

        ahora = time.monotonic()
        if self._primaria_disponible or ahora >= self._reintentar_primaria_en:
            respuesta = self._consultar(PRIMARY_QUERY_ENDPOINT, payload)
            if respuesta.get("ok"):
                self._primaria_disponible = True
                respuesta["fuente"] = "PRIMARY"
                return respuesta
            if not respuesta.get("error"):
                self._primaria_disponible = True
                respuesta["fuente"] = "PRIMARY"
                return respuesta
            self._primaria_disponible = False
            self._reintentar_primaria_en = ahora + self.reintento_primaria_segundos

        respuesta = self._consultar(REPLICA_QUERY_ENDPOINT, payload)
        if respuesta.get("ok"):
            respuesta["fuente"] = "REPLICA"
            return respuesta
        if not respuesta.get("error"):
            respuesta["fuente"] = "REPLICA"
            return respuesta

        respuesta["fuente"] = "SIN_CONEXION"
        return respuesta

    def _consultar(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        socket = self.context.socket(zmq.REQ)
        socket.setsockopt(zmq.RCVTIMEO, self.timeout_ms)
        socket.setsockopt(zmq.SNDTIMEO, self.timeout_ms)
        socket.setsockopt(zmq.LINGER, 0)
        socket.connect(endpoint)
        try:
            socket.send_json(payload)
            return socket.recv_json()
        except zmq.ZMQError as exc:
            return {"ok": False, "error": str(exc)}
        finally:
            socket.close(0)


def color_estado(estado: str) -> str:
    if estado == "NORMAL":
        return "green"
    if "CONGESTION" in estado:
        return "red"
    if estado == "PRIORIZACION":
        return "yellow"
    if estado in {"SIN_DATOS", "SIN_CLASIFICAR", "DESCONOCIDO"}:
        return "bright_black"
    return "cyan"


def formatear_timestamp(valor: Any) -> str:
    if not valor:
        return "N/A"
    try:
        texto = str(valor)
        if texto.endswith("Z"):
            texto = texto[:-1] + "+00:00"
        dt = datetime.fromisoformat(texto)
        if dt.tzinfo is None:
            return texto
        return dt.astimezone(COLOMBIA_TZ).strftime("%H:%M:%S")
    except Exception:
        return str(valor)


def construir_panel(interseccion: str, respuesta: Dict[str, Any]) -> Panel:
    ahora = datetime.now(COLOMBIA_TZ).strftime("%H:%M:%S")
    fuente = respuesta.get("fuente", "UNKNOWN")

    if not respuesta.get("ok") or not respuesta.get("data"):
        estado = "SIN_CONEXION" if respuesta.get("error") else "SIN_EVENTOS"
        accion = "REVISAR_SERVICIO" if respuesta.get("error") else "PENDIENTE"
        fuente = "SIN_CONEXION" if respuesta.get("error") else fuente
        contenido = Text.assemble(
            ("Hora COL: ", "bold"),
            (ahora, "white"),
            ("\nIntersección: ", "bold"),
            (interseccion, "cyan"),
            ("\nEstado: ", "bold"),
            (estado, "bright_black"),
            ("\nAcción: ", "bold"),
            (accion, "yellow"),
            ("\nFuente: ", "bold"),
            (fuente, "magenta"),
        )
        return Panel(
            contenido,
            title="Decisión de Tráfico",
            border_style="bright_black",
        )

    data = respuesta["data"]
    estado = str(data.get("clasificacion") or "SIN_CLASIFICAR")
    accion = str(data.get("estado_actual") or "SIN_ACCION")
    regla = str(data.get("regla_aplicada") or "SIN_REGLA")
    duracion = f"{data.get('duracion_base_seg', 'N/A')}s"
    ultimo_comando = str(data.get("ultimo_comando") or "SIN_COMANDO")
    cola = str(data.get("longitud_cola", "N/A"))
    velocidad = str(data.get("velocidad_promedio", "N/A"))
    densidad = str(data.get("densidad_trafico", "N/A"))
    ts_estado = formatear_timestamp(data.get("ts_estado"))
    color = color_estado(estado)
    prioridad_restante = calcular_prioridad_restante(data) if estado == "PRIORIZACION" else None

    lineas = [
        Text.assemble(("Hora COL: ", "bold"), (ahora, "white")),
        Text.assemble(("Intersección: ", "bold"), (interseccion, "cyan")),
        Text.assemble(("Estado: ", "bold"), (estado, color)),
        Text.assemble(("Semáforo: ", "bold"), (accion, "bold yellow")),
        Text.assemble(("Último comando: ", "bold"), (ultimo_comando, "white")),
        Text.assemble(("Duración: ", "bold"), (duracion, "white")),
        Text.assemble(("Regla: ", "bold"), (regla, "white")),
        Text.assemble(("Cola: ", "bold"), (cola, "white")),
        Text.assemble(("Velocidad: ", "bold"), (velocidad, "white")),
        Text.assemble(("Densidad: ", "bold"), (densidad, "white")),
        Text.assemble(("Actualizado: ", "bold"), (ts_estado, "white")),
        Text.assemble(("Fuente: ", "bold"), (fuente, "magenta")),
    ]

    if prioridad_restante is not None:
        lineas.insert(
            5,
            Text.assemble(("Prioridad restante: ", "bold"), (f"{prioridad_restante}s", "bold yellow")),
        )

    contenido = Group(*lineas)

    return Panel(contenido, title="Decisión de Tráfico", border_style=color)


def calcular_prioridad_restante(data: Dict[str, Any]) -> int | None:
    ts_estado = data.get("ts_estado")
    duracion = data.get("duracion_base_seg")
    if not ts_estado or not duracion:
        return None
    try:
        texto = str(ts_estado)
        if texto.endswith("Z"):
            texto = texto[:-1] + "+00:00"
        inicio = datetime.fromisoformat(texto)
        if inicio.tzinfo is None:
            return None
        restante = int(duracion) - int((datetime.now(COLOMBIA_TZ) - inicio.astimezone(COLOMBIA_TZ)).total_seconds())
        return max(0, restante)
    except Exception:
        return None


def construir_layout(intersecciones: List[str], consultor: ConsultorEstado, filas: int, columnas: int) -> Layout:
    layout = Layout(name="root")
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="grid"),
    )

    timestamp = datetime.now(COLOMBIA_TZ).strftime("%Y-%m-%d %H:%M:%S")
    header_text = Text(
        f"Centro de Monitoreo Textual | Actualización {timestamp} | Q para salir",
        justify="center",
        style="bold white on blue",
    )
    layout["header"].update(Panel(header_text, border_style="blue"))

    filas = max(1, filas or 1)
    columnas = max(1, columnas or len(intersecciones) or 1)
    total_celdas = max(len(intersecciones), filas * columnas)

    filas_layout = [Layout(name=f"row_{fila}") for fila in range(filas)]
    layout["grid"].split_column(*filas_layout)

    for fila in range(filas):
        columnas_layout = [Layout(name=f"p_{fila}_{columna}") for columna in range(columnas)]
        layout[f"row_{fila}"].split_row(*columnas_layout)

    for index in range(total_celdas):
        fila = index // columnas
        columna = index % columnas
        nombre_panel = f"p_{fila}_{columna}"
        if index >= len(intersecciones):
            layout[nombre_panel].update(Panel("Sin intersección asignada", border_style="bright_black"))
            continue

        interseccion = intersecciones[index]
        respuesta = consultor.consultar_interseccion(interseccion)
        layout[nombre_panel].update(construir_panel(interseccion, respuesta))

    return layout


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monitor textual de la grilla de intersecciones.")
    parser.add_argument(
        "--intersections",
        nargs="+",
        dest="intersections",
        help="Lista de intersecciones a mostrar.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_INTERVAL_SECONDS,
        help="Intervalo de refresco en segundos.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    intersecciones_config, filas, columnas = cargar_intersecciones()
    intersecciones = args.intersections or intersecciones_config
    if not intersecciones:
        raise SystemExit("No se encontraron intersecciones para monitorear.")

    consultor = ConsultorEstado()
    with Live(construir_layout(intersecciones, consultor, filas, columnas), refresh_per_second=4, screen=True) as live:
        while True:
            live.update(construir_layout(intersecciones, consultor, filas, columnas))
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
