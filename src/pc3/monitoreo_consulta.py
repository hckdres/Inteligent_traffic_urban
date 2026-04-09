from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

import zmq
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich import box


PRIMARY_QUERY_ENDPOINT = "tcp://127.0.0.1:5564"
REPLICA_QUERY_ENDPOINT = "tcp://127.0.0.1:5565"
ANALITICA_COMMAND_ENDPOINT = "tcp://127.0.0.1:5562"


class MonitoreoConsulta:
    def __init__(self) -> None:
        self.context = zmq.Context.instance()
        self.timeout_ms = 1500
        self.console = Console()

    def ejecutar(self) -> None:
        self.console.print(Panel("[bold cyan]Gestión Inteligente de Tráfico Urbano[/bold cyan]\n[italic]Panel de Monitoreo y Consulta[/italic]", box=box.DOUBLE))
        while True:
            self.console.print("\n[bold yellow]Menú Principal:[/bold yellow]")
            self.console.print("1) [bold]Consulta puntual[/bold] (Estado actual)")
            self.console.print("2) [bold]Histórico[/bold] (Rango de tiempo)")
            self.console.print("3) [bold]Priorizar vía[/bold] (Ambulancia/Emergencia)")
            self.console.print("4) [bold]Cambio manual[/bold] (Forzar semáforo)")
            self.console.print("5) [bold red]Salir[/bold red]")
            
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
                detalle = self.console.input("Detalle (ej. Ambulancia en camino): ").strip()
                res = self.enviar_indicacion({
                    "tipo": "priorizar_via",
                    "interseccion": inter,
                    "detalle": detalle,
                    "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "duracion_verde_segundos": 20,
                })
                self.console.print(f"[bold green]Resultado:[/bold green] {res}")
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
        
        table = Table(title=f"Estado Intersección {data[0]}", box=box.ROUNDED)
        table.add_column("Propiedad", style="cyan")
        table.add_column("Valor", style="white")
        
        table.add_row("Fuente de Datos", f"[{color_fuente}]{fuente}[/{color_fuente}]")
        table.add_row("Timestamp", str(data[1]))
        
        estado = str(data[2])
        color_estado = "green" if estado == "NORMAL" else "red" if "CONGESTION" in estado else "blue"
        table.add_row("Estado Circulación", f"[{color_estado}]{estado}[/{color_estado}]")
        
        table.add_row("Regla Aplicada", str(data[3]))
        table.add_row("Acción Semáforo", f"[bold]{data[4]}[/bold]")
        table.add_row("Duración Verde", f"{data[5]}s")
        
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
            estado = str(fila[2])
            color = "green" if estado == "NORMAL" else "red" if "CONGESTION" in estado else "blue"
            table.add_row(
                str(fila[0]),
                str(fila[1]),
                f"[{color}]{estado}[/{color}]",
                str(fila[3]),
                str(fila[4])
            )
        
        self.console.print(table)

    def consultar_interseccion(self, interseccion: str) -> Dict[str, Any]:
        return self._consultar_con_failover({"tipo": "consultar_interseccion", "interseccion": interseccion})

    def consultar_historico(self, fecha_inicio: str, fecha_fin: str) -> Dict[str, Any]:
        return self._consultar_con_failover({"tipo": "consultar_historico", "fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin})

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
        respuesta = self._consultar(PRIMARY_QUERY_ENDPOINT, payload)
        if respuesta.get("ok"):
            respuesta["fuente"] = "PRIMARY"
            return respuesta

        respuesta = self._consultar(REPLICA_QUERY_ENDPOINT, payload)
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
