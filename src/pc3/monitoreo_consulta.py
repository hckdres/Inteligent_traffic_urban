from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import zmq
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.markup import escape

from src.utils.intersecciones import (
    etiqueta_columna,
    etiqueta_fila,
    posicion_en_ciudad,
)
from src.utils.timezones import COLOMBIA_TZ


PRIMARY_QUERY_ENDPOINT = "tcp://127.0.0.1:5564"
REPLICA_QUERY_ENDPOINT = "tcp://127.0.0.1:5565"
ANALITICA_COMMAND_ENDPOINT = "tcp://127.0.0.1:5562"


class MonitoreoConsulta:
    def __init__(self, ruta_config_sistema: str = "src/config/system.json") -> None:
        self.context = zmq.Context.instance()
        self.timeout_ms = 1200
        self.command_timeout_ms = 4000
        self.console = Console()
        self.ruta_config_sistema = ruta_config_sistema
        self.ciudad = self._cargar_ciudad()
        self._primaria_disponible = True

    def ejecutar(self) -> None:
        self.console.print(Panel("[bold cyan]Gestión Inteligente de Tráfico Urbano[/bold cyan]\n[italic]Panel de Monitoreo y Consulta[/italic]", box=box.DOUBLE))
        while True:
            self.console.print("\n[bold yellow]Menú Principal:[/bold yellow]")
            self.console.print("1) [bold]Consulta puntual[/bold] (Estado actual)")
            self.console.print("2) [bold]Histórico[/bold] (Rango de tiempo)")
            self.console.print("3) [bold]Priorizar vía[/bold] (Ambulancia/Emergencia)")
            self.console.print("4) [bold]Cambio manual[/bold] (Forzar semáforo)")
            self.console.print("5) [bold]Buscar dato por seq[/bold]")
            self.console.print("6) [bold red]Salir[/bold red]")
            
            opcion = self.console.input("\n[green]Seleccione opción:[/green] ").strip()
            if opcion == "1":
                inter = self.console.input("Intersección (ej. [bold]INT-A1[/bold]): ").strip()
                res = self.consultar_interseccion(inter)
                self._mostrar_resultado_puntual(res)
            elif opcion == "2":
                self.console.print("[dim]Formato: YYYY-MM-DD HH:MM:SS[/dim]")
                inicio = self.console.input("Fecha inicio: ").strip()
                fin = self.console.input("Fecha fin: ").strip()
                res = self.consultar_historico(inicio, fin)
                self._mostrar_resultado_historico(res)
            elif opcion == "3":
                inter = self.console.input("Intersección a priorizar: ").strip()
                modo_corredor = self.console.input("Corredor ([bold]FILA[/bold]/[bold]COLUMNA[/bold]): ").strip().upper()
                direccion = self.console.input("Dirección ([bold]ADELANTE[/bold]/[bold]ATRAS[/bold], default ADELANTE): ").strip().upper() or "ADELANTE"
                detalle = self.console.input("Detalle (ej. Ambulancia en camino): ").strip()
                res = self.enviar_indicacion({
                    "tipo": "priorizar_via",
                    "interseccion": inter,
                    "modo_corredor": modo_corredor,
                    "direccion": direccion,
                    "detalle": detalle,
                    "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "duracion_verde_segundos": 10,
                })
                self._mostrar_resultado_priorizacion(res)
            elif opcion == "4":
                inter = self.console.input("Intersección: ").strip()
                accion = self.console.input("Acción ([bold]CAMBIAR_A_VERDE[/bold]/[bold]CAMBIAR_A_ROJO[/bold]): ").strip()
                res = self.enviar_indicacion({
                    "tipo": "cambio_manual",
                    "interseccion": inter,
                    "accion": accion,
                    "detalle": "cambio manual desde PC3",
                    "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "duracion_verde_segundos": 15,
                })
                self.console.print(f"[bold green]Resultado:[/bold green] {escape(str(res))}")
            elif opcion == "5":
                seq = self.console.input("Seq dato (ej. [bold]1[/bold]): ").strip()
                res = self.consultar_evento_seq(seq)
                self._mostrar_resultado_evento_seq(res, seq)
            elif opcion == "6":
                break
            else:
                self.console.print("[bold red]Opción inválida[/bold red]")

    def _mostrar_resultado_puntual(self, res: Dict[str, Any]) -> None:
        if not res.get("ok") or not res.get("data"):
            self.console.print("[bold red]No se encontraron datos o error en la consulta.[/bold red]")
            return

        data = res["data"]
        fuente = res.get("fuente", "UNKNOWN")
        color_fuente = "green" if fuente == "PRIMARY" else "yellow"
        
        table = Table(title=f"Estado Intersección {escape(str(data['codigo']))}", box=box.ROUNDED)
        table.add_column("Propiedad", style="cyan")
        table.add_column("Valor", style="white")
        
        table.add_row("Fuente de Datos", Text(str(fuente), style=f"bold {color_fuente}"))
        table.add_row("Timestamp", escape(self._formatear_ts(data.get("ts_estado"))))
        
        estado = str(data.get("clasificacion"))
        color_estado = "green" if estado == "NORMAL" else "red" if "CONGESTION" in estado else "blue"
        table.add_row("Estado Circulación", Text(estado, style=f"bold {color_estado}"))
        
        table.add_row("Regla Aplicada", escape(str(data.get("regla_aplicada"))))
        table.add_row("Longitud Cola", escape(str(data.get("longitud_cola"))))
        table.add_row("Velocidad Promedio", escape(str(data.get("velocidad_promedio"))))
        table.add_row("Densidad", escape(str(data.get("densidad_trafico"))))
        estado_semaforo = str(data.get("estado_actual") or "DESCONOCIDO")
        color_semaforo = "green" if estado_semaforo == "VERDE" else "red" if estado_semaforo == "ROJO" else "yellow"
        table.add_row("Estado Semáforo", Text(estado_semaforo, style=f"bold {color_semaforo}"))
        table.add_row("Último Comando", escape(str(data.get("ultimo_comando") or "SIN_COMANDO")))
        table.add_row("Duración Programada", escape(f"{data.get('duracion_base_seg')}s"))
        restante = self._prioridad_restante(data)
        if restante is not None:
            table.add_row("Prioridad Restante", Text(f"{restante}s", style="bold yellow"))
        
        self.console.print(table)

    def _mostrar_resultado_priorizacion(self, res: Dict[str, Any]) -> None:
        if not res.get("ok"):
            self.console.print(f"[bold red]No se pudo priorizar la vía:[/bold red] {res.get('error', 'Error desconocido')}")
            return

        decision = res.get("decision", {})
        corredor = decision.get("contexto", {}).get("modo_corredor", "N/A")
        direccion = decision.get("contexto", {}).get("direccion", "N/A")
        afectadas = decision.get("intersecciones_afectadas", [])
        bloqueadas = decision.get("intersecciones_bloqueadas", [])
        interseccion = decision.get("interseccion", "N/A")
        duracion = decision.get("duracion_verde_segundos", "N/A")
        detalle = decision.get("contexto", {}).get("detalle") or "Sin detalle"

        resumen = Table(box=box.ROUNDED, expand=False)
        resumen.add_column("Campo", style="cyan")
        resumen.add_column("Valor", style="white")
        resumen.add_row("Intersección origen", Text(str(interseccion), style="bold yellow"))
        resumen.add_row("Corredor", Text(str(corredor), style="bold green"))
        resumen.add_row("Dirección", Text(str(direccion), style="bold cyan"))
        resumen.add_row("Duración", Text(f"{duracion}s", style="bold"))
        resumen.add_row("Detalle", escape(str(detalle)))
        resumen.add_row("Intersecciones liberadas", escape(", ".join(afectadas) if afectadas else "Ninguna"))
        resumen.add_row("Intersecciones bloqueadas", escape(", ".join(bloqueadas) if bloqueadas else "Ninguna"))

        self.console.print(Panel(resumen, title="[bold green]Prioridad de Ambulancia Activada[/bold green]", border_style="green"))

        mapa = self._render_mapa_corredor(interseccion, afectadas, bloqueadas)
        if mapa is not None:
            self.console.print(mapa)

    def _render_mapa_corredor(self, origen: str, afectadas: list[str], bloqueadas: list[str]) -> Panel | None:
        ciudad = self.ciudad
        intersecciones = ciudad.get("intersecciones", [])
        if not intersecciones:
            return None

        filas = {}
        for codigo in intersecciones:
            fila, columna = posicion_en_ciudad(codigo, ciudad)
            filas.setdefault(fila, {})[columna] = codigo

        tabla = Table(title="Mapa del corredor priorizado", box=box.SIMPLE_HEAVY, expand=False)
        tabla.add_column("Fila", style="bold cyan", justify="center")
        total_columnas = int(ciudad.get("columnas", 0))
        for columna in range(1, total_columnas + 1):
            tabla.add_column(etiqueta_columna(columna, ciudad), justify="center")

        afectadas_set = set(afectadas)
        bloqueadas_set = set(bloqueadas)
        for fila in sorted(filas):
            celdas = [etiqueta_fila(fila, ciudad)]
            for columna in range(1, total_columnas + 1):
                codigo = filas.get(fila, {}).get(columna)
                if not codigo:
                    celdas.append("-")
                    continue

                etiqueta = codigo.split("-", 1)[1]
                if codigo == origen:
                    celda = Text(f"{etiqueta} AMB", style="bold black on bright_yellow")
                elif codigo in afectadas_set:
                    celda = Text(f"{etiqueta} PASO", style="bold black on green")
                elif codigo in bloqueadas_set:
                    celda = Text(f"{etiqueta} BLOQ", style="bold white on red")
                else:
                    celda = Text(f"{etiqueta} NORMAL", style="white on rgb(60,60,60)")
                celdas.append(celda)
            tabla.add_row(*celdas)

        nota = Text("AMB = punto de referencia de la ambulancia | PASO = corredor con prioridad | BLOQ = semáforo en rojo", style="dim")
        tabla.caption = nota
        return Panel(tabla, border_style="bright_green")

    def _cargar_ciudad(self) -> Dict[str, Any]:
        ruta = Path(self.ruta_config_sistema)
        if not ruta.is_absolute():
            ruta = Path(__file__).resolve().parents[2] / ruta
        if not ruta.exists():
            return {}
        try:
            with ruta.open("r", encoding="utf-8") as archivo:
                data = json.load(archivo)
        except (OSError, json.JSONDecodeError):
            return {}
        return data.get("ciudad", {})

    def _mostrar_resultado_evento_seq(self, res: Dict[str, Any], seq: str) -> None:
        if not res.get("ok") or not res.get("data"):
            self.console.print(f"[bold red]No se encontraron datos para seq={escape(str(seq))}.[/bold red]")
            return

        fuente = res.get("fuente", "UNKNOWN")
        color_fuente = "green" if fuente == "PRIMARY" else "yellow"
        table = Table(title=f"Dato seq={escape(str(seq))} ({escape(str(fuente))})", box=box.ROUNDED)
        table.add_column("Seq", style="cyan", justify="right")
        table.add_column("Sensor", style="white")
        table.add_column("Intersección", style="cyan")
        table.add_column("Evento", style="bold")
        table.add_column("Timestamp", style="dim")
        table.add_column("Valor", justify="right")
        table.add_column("Velocidad", justify="right")

        for fila in res["data"]:
            table.add_row(
                escape(str(fila.get("seq"))),
                escape(str(fila.get("sensor"))),
                escape(str(fila.get("interseccion"))),
                escape(str(fila.get("tipo_evento") or "SIN_EVENTOS")),
                escape(self._formatear_ts(fila.get("ts_evento"))),
                escape(str(fila.get("valor_principal"))),
                escape(str(fila.get("velocidad"))),
            )
        table.caption = f"[{color_fuente}]Fuente de datos: {escape(str(fuente))}[/{color_fuente}]"
        self.console.print(table)

    def _mostrar_resultado_historico(self, res: Dict[str, Any]) -> None:
        if not res.get("ok") or not res.get("data"):
            self.console.print("[bold red]No se encontraron datos.[/bold red]")
            return

        table = Table(title="Histórico de Tráfico", box=box.ROUNDED)
        table.add_column("Intersección", style="cyan")
        table.add_column("Timestamp", style="dim")
        table.add_column("Estado", style="bold")
        table.add_column("Regla", style="italic")
        table.add_column("Acción", style="white")

        for fila in res["data"]:
            estado = str(fila.get("clasificacion"))
            color = "green" if estado == "NORMAL" else "red" if "CONGESTION" in estado else "blue"
            table.add_row(
                escape(str(fila.get("interseccion"))),
                escape(self._formatear_ts(fila.get("ts_estado"))),
                f"[{color}]{escape(estado)}[/{color}]",
                escape(str(fila.get("regla_aplicada"))),
                escape(str(fila.get("origen")))
            )
        
        self.console.print(table)

    def _formatear_ts(self, valor: Any) -> str:
        if not valor:
            return "N/A"
        try:
            texto = str(valor)
            if texto.endswith("Z"):
                texto = texto[:-1] + "+00:00"
            dt = datetime.fromisoformat(texto)
            if dt.tzinfo is None:
                return texto
            return dt.astimezone(COLOMBIA_TZ).strftime("%Y-%m-%d %H:%M:%S %Z")
        except Exception:
            return str(valor)

    def consultar_interseccion(self, interseccion: str) -> Dict[str, Any]:
        return self._consultar_con_failover({"tipo": "consultar_interseccion", "interseccion": interseccion})

    def consultar_historico(self, fecha_inicio: str, fecha_fin: str) -> Dict[str, Any]:
        return self._consultar_con_failover({"tipo": "consultar_historico", "fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin})

    def consultar_evento_seq(self, seq: str) -> Dict[str, Any]:
        return self._consultar_con_failover({"tipo": "consultar_evento_seq", "seq": seq, "limite": 20})

    def enviar_indicacion(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        socket = self.context.socket(zmq.REQ)
        socket.connect(ANALITICA_COMMAND_ENDPOINT)
        socket.setsockopt(zmq.RCVTIMEO, self.command_timeout_ms)
        socket.setsockopt(zmq.SNDTIMEO, self.command_timeout_ms)
        try:
            socket.send_json(payload)
            return socket.recv_json()
        except zmq.ZMQError as exc:
            return {"ok": False, "error": str(exc)}
        finally:
            socket.close(0)

    def _consultar_con_failover(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if self._primaria_disponible:
            respuesta = self._consultar(PRIMARY_QUERY_ENDPOINT, payload)
            if respuesta.get("ok"):
                respuesta["fuente"] = "PRIMARY"
                return respuesta
            if respuesta.get("error"):
                self._primaria_disponible = False

        respuesta = self._consultar(REPLICA_QUERY_ENDPOINT, payload)
        if respuesta.get("ok"):
            respuesta["fuente"] = "REPLICA"
            return respuesta

        respuesta = self._consultar(PRIMARY_QUERY_ENDPOINT, payload)
        if respuesta.get("ok"):
            self._primaria_disponible = True
            respuesta["fuente"] = "PRIMARY"
            return respuesta

        respuesta["fuente"] = "REPLICA"
        return respuesta

    def _consultar(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        socket = self.context.socket(zmq.REQ)
        socket.connect(endpoint)
        socket.setsockopt(zmq.RCVTIMEO, self.timeout_ms)
        socket.setsockopt(zmq.SNDTIMEO, self.timeout_ms)
        try:
            socket.send_json(payload)
            return socket.recv_json()
        except zmq.ZMQError as exc:
            return {"ok": False, "error": str(exc)}
        finally:
            socket.close(0)

    def _prioridad_restante(self, data: Dict[str, Any]) -> int | None:
        if data.get("clasificacion") != "PRIORIZACION":
            return None
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
