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

from src.utils.timezones import COLOMBIA_TZ


PRIMARY_QUERY_ENDPOINT = "tcp://127.0.0.1:5564"
REPLICA_QUERY_ENDPOINT = "tcp://127.0.0.1:5565"
ANALITICA_COMMAND_ENDPOINT = "tcp://127.0.0.1:5562"


class MonitoreoConsulta:
    def __init__(self) -> None:
        self.context = zmq.Context.instance()
        self.timeout_ms = 700
        self.console = Console()
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
                detalle = self.console.input("Detalle (ej. Ambulancia en camino): ").strip()
                res = self.enviar_indicacion({
                    "tipo": "priorizar_via",
                    "interseccion": inter,
                    "modo_corredor": modo_corredor,
                    "detalle": detalle,
                    "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "duracion_verde_segundos": 20,
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
                self.console.print(f"[bold green]Resultado:[/bold green] {res}")
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
        
        table = Table(title=f"Estado Intersección {data['codigo']}", box=box.ROUNDED)
        table.add_column("Propiedad", style="cyan")
        table.add_column("Valor", style="white")
        
        table.add_row("Fuente de Datos", f"[{color_fuente}]{fuente}[/{color_fuente}]")
        table.add_row("Timestamp", self._formatear_ts(data.get("ts_estado")))
        
        estado = str(data.get("clasificacion"))
        color_estado = "green" if estado == "NORMAL" else "red" if "CONGESTION" in estado else "blue"
        table.add_row("Estado Circulación", f"[{color_estado}]{estado}[/{color_estado}]")
        
        table.add_row("Regla Aplicada", str(data.get("regla_aplicada")))
        table.add_row("Longitud Cola", str(data.get("longitud_cola")))
        table.add_row("Velocidad Promedio", str(data.get("velocidad_promedio")))
        table.add_row("Densidad", str(data.get("densidad_trafico")))
        table.add_row("Estado Semáforo", f"[bold]{data.get('estado_actual')}[/bold]")
        table.add_row("Último Comando", str(data.get("ultimo_comando") or "SIN_COMANDO"))
        table.add_row("Duración Programada", f"{data.get('duracion_base_seg')}s")
        restante = self._prioridad_restante(data)
        if restante is not None:
            table.add_row("Prioridad Restante", f"[bold yellow]{restante}s[/bold yellow]")
        
        self.console.print(table)

    def _mostrar_resultado_priorizacion(self, res: Dict[str, Any]) -> None:
        if not res.get("ok"):
            self.console.print(f"[bold red]No se pudo priorizar la vía:[/bold red] {res.get('error', 'Error desconocido')}")
            return

        decision = res.get("decision", {})
        corredor = decision.get("contexto", {}).get("modo_corredor", "N/A")
        afectadas = decision.get("intersecciones_afectadas", [])
        interseccion = decision.get("interseccion", "N/A")
        duracion = decision.get("duracion_verde_segundos", "N/A")
        detalle = decision.get("contexto", {}).get("detalle") or "Sin detalle"

        resumen = Table(box=box.ROUNDED, expand=False)
        resumen.add_column("Campo", style="cyan")
        resumen.add_column("Valor", style="white")
        resumen.add_row("Intersección origen", f"[bold yellow]{interseccion}[/bold yellow]")
        resumen.add_row("Corredor", f"[bold green]{corredor}[/bold green]")
        resumen.add_row("Duración", f"[bold]{duracion}s[/bold]")
        resumen.add_row("Detalle", detalle)
        resumen.add_row("Intersecciones liberadas", ", ".join(afectadas) if afectadas else "Ninguna")

        self.console.print(Panel(resumen, title="[bold green]Prioridad de Ambulancia Activada[/bold green]", border_style="green"))

        mapa = self._render_mapa_corredor(interseccion, afectadas)
        if mapa is not None:
            self.console.print(mapa)

    def _render_mapa_corredor(self, origen: str, afectadas: list[str]) -> Panel | None:
        ciudad = self.ciudad
        intersecciones = ciudad.get("intersecciones", [])
        if not intersecciones:
            return None

        filas = {}
        for codigo in intersecciones:
            sufijo = codigo.split("-", 1)[1]
            fila = sufijo[0]
            columna = int(sufijo[1:])
            filas.setdefault(fila, {})[columna] = codigo

        tabla = Table(title="Mapa del corredor priorizado", box=box.SIMPLE_HEAVY, expand=False)
        tabla.add_column("Fila", style="bold cyan", justify="center")
        total_columnas = int(ciudad.get("columnas", 0))
        for columna in range(1, total_columnas + 1):
            tabla.add_column(str(columna), justify="center")

        afectadas_set = set(afectadas)
        for fila in sorted(filas):
            celdas = [fila]
            for columna in range(1, total_columnas + 1):
                codigo = filas.get(fila, {}).get(columna)
                if not codigo:
                    celdas.append("-")
                    continue

                etiqueta = codigo.split("-", 1)[1]
                if codigo == origen:
                    celda = f"[bold black on bright_yellow]{etiqueta} AMB[/bold black on bright_yellow]"
                elif codigo in afectadas_set:
                    celda = f"[bold black on green]{etiqueta} PASO[/bold black on green]"
                else:
                    celda = f"[white on rgb(60,60,60)]{etiqueta} NORMAL[/white on rgb(60,60,60)]"
                celdas.append(celda)
            tabla.add_row(*celdas)

        nota = Text("AMB = punto de referencia de la ambulancia | PASO = corredor con prioridad", style="dim")
        tabla.caption = nota
        return Panel(tabla, border_style="bright_green")

    def _cargar_ciudad(self) -> Dict[str, Any]:
        ruta = Path(__file__).resolve().parent.parent / "config" / "system.json"
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
            self.console.print(f"[bold red]No se encontraron datos para seq={seq}.[/bold red]")
            return

        fuente = res.get("fuente", "UNKNOWN")
        color_fuente = "green" if fuente == "PRIMARY" else "yellow"
        table = Table(title=f"Dato seq={seq} ({fuente})", box=box.ROUNDED)
        table.add_column("Seq", style="cyan", justify="right")
        table.add_column("Sensor", style="white")
        table.add_column("Intersección", style="cyan")
        table.add_column("Evento", style="bold")
        table.add_column("Timestamp", style="dim")
        table.add_column("Valor", justify="right")
        table.add_column("Velocidad", justify="right")

        for fila in res["data"]:
            table.add_row(
                str(fila.get("seq")),
                str(fila.get("sensor")),
                str(fila.get("interseccion")),
                str(fila.get("tipo_evento") or "SIN_EVENTOS"),
                self._formatear_ts(fila.get("ts_evento")),
                str(fila.get("valor_principal")),
                str(fila.get("velocidad")),
            )
        table.caption = f"[{color_fuente}]Fuente de datos: {fuente}[/{color_fuente}]"
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
                str(fila.get("interseccion")),
                self._formatear_ts(fila.get("ts_estado")),
                f"[{color}]{estado}[/{color}]",
                str(fila.get("regla_aplicada")),
                str(fila.get("origen"))
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
        socket.setsockopt(zmq.RCVTIMEO, self.timeout_ms)
        socket.setsockopt(zmq.SNDTIMEO, self.timeout_ms)
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
