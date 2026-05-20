from __future__ import annotations

import argparse
import json
import math
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
from src.utils.intersecciones import (
    descomponer_interseccion as descomponer_interseccion_cfg,
    fila_a_indice,
)


PRIMARY_QUERY_ENDPOINT = "tcp://127.0.0.1:5564"
REPLICA_QUERY_ENDPOINT = "tcp://127.0.0.1:5565"
DEFAULT_INTERVAL_SECONDS = 1.0
AMBULANCIA_STEP_SECONDS = 1.1


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


def descomponer_interseccion(codigo: str) -> Tuple[str, int] | None:
    try:
        return descomponer_interseccion_cfg(codigo)
    except ValueError:
        return None


def calcular_dimensiones_grid(
    total_intersecciones: int, filas_config: int, columnas_config: int
) -> Tuple[int, int]:
    filas = max(0, filas_config)
    columnas = max(0, columnas_config)

    if total_intersecciones <= 0:
        return max(1, filas or 1), max(1, columnas or 1)

    if filas == 0 and columnas == 0:
        columnas = max(1, int(math.ceil(math.sqrt(total_intersecciones))))
        filas = int(math.ceil(total_intersecciones / columnas))
    elif filas == 0:
        columnas = max(1, columnas)
        filas = int(math.ceil(total_intersecciones / columnas))
    elif columnas == 0:
        filas = max(1, filas)
        columnas = int(math.ceil(total_intersecciones / filas))

    if filas * columnas < total_intersecciones:
        filas = int(math.ceil(total_intersecciones / columnas))

    return max(1, filas), max(1, columnas)


def ordenar_intersecciones_corredor(codigos: List[str]) -> List[str]:
    if len(codigos) <= 1:
        return list(codigos)

    try:
        descompuestas = [
            (codigo, *descomponer_interseccion_cfg(codigo))
            for codigo in codigos
        ]
    except ValueError:
        return sorted(codigos)

    filas = {fila for _, fila, _ in descompuestas}
    columnas = {columna for _, _, columna in descompuestas}
    if len(filas) == 1:
        descompuestas.sort(key=lambda item: item[2])
    elif len(columnas) == 1:
        descompuestas.sort(key=lambda item: fila_a_indice(item[1]))
    else:
        descompuestas.sort(key=lambda item: (fila_a_indice(item[1]), item[2]))
    return [codigo for codigo, _, _ in descompuestas]


def construir_ruta_desde_origen(
    corredor: List[str], origen: str | None, direccion: str | None
) -> List[str]:
    ordenados = ordenar_intersecciones_corredor(corredor)
    if not origen or origen not in ordenados:
        return ordenados
    indice_origen = ordenados.index(origen)
    if direccion == "ATRAS":
        return list(reversed(ordenados[:indice_origen + 1]))
    return ordenados[indice_origen:]


def extraer_metadatos_ambulancia(regla_aplicada: str) -> Tuple[str | None, str | None]:
    if not regla_aplicada.startswith("MANUAL_AMBULANCIA_"):
        return None, None
    tokens = regla_aplicada.split("_")
    direccion = next((token for token in tokens if token in {"ADELANTE", "ATRAS"}), None)
    origen = next((token for token in tokens if token.startswith("INT-")), None)
    return origen, direccion


def sumar_ambulancia_a_conteo(conteo_base: Any, amb_en_paso: bool) -> str:
    if not amb_en_paso:
        return str(conteo_base if conteo_base is not None else "N/A")
    if conteo_base in (None, "", "N/A"):
        return "1 (AMB)"
    try:
        return f"{int(conteo_base) + 1} (AMB)"
    except (TypeError, ValueError):
        return f"{conteo_base} +1 AMB"


def calcular_intersecciones_cercanas(
    interseccion_ambulancia: str | None, intersecciones: List[str]
) -> set[str]:
    if not interseccion_ambulancia:
        return set()
    origen = descomponer_interseccion(interseccion_ambulancia)
    if origen is None:
        return set()
    fila_origen, col_origen = origen
    cercanas: set[str] = set()
    for codigo in intersecciones:
        destino = descomponer_interseccion(codigo)
        if destino is None:
            continue
        fila_destino, col_destino = destino
        distancia_manhattan = abs(fila_a_indice(fila_destino) - fila_a_indice(fila_origen)) + abs(col_destino - col_origen)
        if distancia_manhattan == 1:
            cercanas.add(codigo)
    return cercanas


class EstadoAmbulanciaVisual:
    def __init__(self, paso_segundos: float = AMBULANCIA_STEP_SECONDS) -> None:
        self.paso_segundos = paso_segundos
        self._corredor_actual: Tuple[str, ...] = ()
        self._indice_actual = 0
        self._ultimo_avance = 0.0
        self._recorrido_finalizado = False

    def actualizar(self, corredor: List[str]) -> str | None:
        corredor_tuple = tuple(corredor)
        if not corredor_tuple:
            self._corredor_actual = ()
            self._indice_actual = 0
            self._ultimo_avance = 0.0
            self._recorrido_finalizado = False
            return None

        ahora = time.monotonic()
        if corredor_tuple != self._corredor_actual:
            self._corredor_actual = corredor_tuple
            self._indice_actual = 0
            self._ultimo_avance = ahora
            self._recorrido_finalizado = False
            return self._corredor_actual[0]

        if self._recorrido_finalizado:
            return None

        if (ahora - self._ultimo_avance) >= self.paso_segundos:
            self._indice_actual += 1
            self._ultimo_avance = ahora
            if self._indice_actual >= len(self._corredor_actual):
                self._recorrido_finalizado = True
                return None

        return self._corredor_actual[self._indice_actual]


def construir_panel(
    interseccion: str,
    respuesta: Dict[str, Any],
    interseccion_ambulancia: str | None = None,
    intersecciones_corredor: set[str] | None = None,
    intersecciones_cercanas: set[str] | None = None,
) -> Panel:
    corredor = intersecciones_corredor or set()
    cercanas = intersecciones_cercanas or set()
    ahora = datetime.now(COLOMBIA_TZ).strftime("%H:%M:%S")
    fuente = respuesta.get("fuente", "UNKNOWN")
    amb_en_paso = interseccion == interseccion_ambulancia
    en_corredor = interseccion in corredor

    if not respuesta.get("ok") or not respuesta.get("data"):
        estado = "SIN_CONEXION" if respuesta.get("error") else "SIN_EVENTOS"
        accion = "REVISAR_SERVICIO" if respuesta.get("error") else "PENDIENTE"
        fuente = "SIN_CONEXION" if respuesta.get("error") else fuente
        lineas = [
            Text.assemble(("Hora COL: ", "bold"), (ahora, "white")),
            Text.assemble(("Intersección: ", "bold"), (interseccion, "cyan")),
            Text.assemble(("Estado: ", "bold"), (estado, "bright_black")),
            Text.assemble(("Acción: ", "bold"), (accion, "yellow")),
            Text.assemble(("Fuente: ", "bold"), (fuente, "magenta")),
        ]

        if amb_en_paso:
            lineas.insert(2, Text.assemble(("Ambulancia: ", "bold"), ("AMB EN PASO", "bold black on bright_yellow")))
        elif en_corredor:
            lineas.insert(2, Text.assemble(("Corredor AMB: ", "bold"), ("DESPEJADO", "bold green")))
        elif interseccion in cercanas:
            lineas.insert(2, Text.assemble(("Cruce cercano: ", "bold"), ("ALTO TEMPORAL", "bold red")))

        contenido = Group(*lineas)
        border_style = "bright_yellow" if amb_en_paso else "bright_black"
        return Panel(
            contenido,
            title="Decisión de Tráfico",
            border_style=border_style,
        )

    data = respuesta["data"]
    estado = str(data.get("clasificacion") or "SIN_CLASIFICAR")
    accion = str(data.get("estado_actual") or "SIN_ACCION")
    regla = str(data.get("regla_aplicada") or "SIN_REGLA")
    duracion = f"{data.get('duracion_base_seg', 'N/A')}s"
    ultimo_comando = str(data.get("ultimo_comando") or "SIN_COMANDO")
    cola = str(data.get("longitud_cola", "N/A"))
    conteo = sumar_ambulancia_a_conteo(data.get("conteo_vehicular"), amb_en_paso)
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
        Text.assemble(("Conteo: ", "bold"), (conteo, "white")),
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

    if amb_en_paso:
        lineas.insert(4, Text.assemble(("Ambulancia: ", "bold"), ("AMB EN PASO", "bold black on bright_yellow")))
        color = "bright_yellow"
    elif en_corredor:
        lineas.insert(4, Text.assemble(("Corredor AMB: ", "bold"), ("DESPEJADO", "bold green")))
    elif interseccion in cercanas:
        lineas.insert(4, Text.assemble(("Cruce cercano: ", "bold"), ("ALTO TEMPORAL", "bold red")))

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


def _detectar_corredor_prioritario(
    intersecciones: List[str], respuestas: Dict[str, Dict[str, Any]]
) -> List[str]:
    corredor: List[str] = []
    origen: str | None = None
    direccion: str | None = None
    for interseccion in intersecciones:
        respuesta = respuestas.get(interseccion, {})
        data = respuesta.get("data") if respuesta.get("ok") else None
        if not data:
            continue
        if str(data.get("clasificacion")) != "PRIORIZACION":
            continue
        restante = calcular_prioridad_restante(data)
        if restante is not None and restante <= 0:
            continue
        corredor.append(interseccion)
        if origen is None:
            origen, direccion = extraer_metadatos_ambulancia(str(data.get("regla_aplicada") or ""))
    return construir_ruta_desde_origen(corredor, origen, direccion)


def construir_layout(
    intersecciones: List[str],
    consultor: ConsultorEstado,
    filas: int,
    columnas: int,
    estado_ambulancia: EstadoAmbulanciaVisual,
) -> Layout:
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

    total_intersecciones = len(intersecciones)
    filas, columnas = calcular_dimensiones_grid(total_intersecciones, filas, columnas)
    total_celdas = filas * columnas
    respuestas = {
        interseccion: consultor.consultar_interseccion(interseccion)
        for interseccion in intersecciones
    }
    corredor_activo = _detectar_corredor_prioritario(intersecciones, respuestas)
    interseccion_ambulancia = estado_ambulancia.actualizar(corredor_activo)
    intersecciones_cercanas = calcular_intersecciones_cercanas(interseccion_ambulancia, intersecciones)

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
        respuesta = respuestas[interseccion]
        layout[nombre_panel].update(
            construir_panel(
                interseccion,
                respuesta,
                interseccion_ambulancia=interseccion_ambulancia,
                intersecciones_corredor=set(corredor_activo),
                intersecciones_cercanas=intersecciones_cercanas,
            )
        )

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
    estado_ambulancia = EstadoAmbulanciaVisual()
    with Live(
        construir_layout(intersecciones, consultor, filas, columnas, estado_ambulancia),
        refresh_per_second=4,
        screen=True,
    ) as live:
        while True:
            live.update(construir_layout(intersecciones, consultor, filas, columnas, estado_ambulancia))
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
