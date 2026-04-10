"""
Visor interactivo de la BD SQLite del sistema de tráfico.
Muestra tablas, conteos, últimos registros con paginación.

Uso:
    python scripts/ver_db.py                           # BD principal
    python scripts/ver_db.py --db data/traffic_replica.db
    python scripts/ver_db.py --limpiar --dias 1        # borrar datos > 1 día
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    RICH = True
except ImportError:
    RICH = False


COLOMBIA_TZ = ZoneInfo("America/Bogota")
UTC_TZ = ZoneInfo("UTC")


def formatear_valor(v):
    if v is None:
        return None
    if isinstance(v, str):
        try:
            if "T" in v:
                texto = v[:-1] + "+00:00" if v.endswith("Z") else v
                dt = datetime.fromisoformat(texto)
            elif len(v) == 19 and " " in v:
                # SQLite CURRENT_TIMESTAMP llega naive; lo tratamos como UTC.
                dt = datetime.strptime(v, "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZoneInfo("UTC"))
            else:
                return v

            if dt.tzinfo is not None:
                return dt.astimezone(COLOMBIA_TZ).strftime("%Y-%m-%d %H:%M:%S %Z")
        except Exception:
            return v
    return v


def convertir_colombia_a_utc(texto: str) -> str:
    dt = datetime.strptime(texto, "%Y-%m-%d %H:%M:%S").replace(tzinfo=COLOMBIA_TZ)
    return dt.astimezone(UTC_TZ).strftime("%Y-%m-%d %H:%M:%S")


def conectar(ruta: str) -> sqlite3.Connection:
    conn = sqlite3.connect(ruta)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def mostrar_conteos(conn: sqlite3.Connection, console) -> None:
    tablas = [
        "interseccion", "sensor", "semaforo",
        "evento_sensor", "estado_trafico", "comando_semaforo",
        "solicitud_usuario", "evento_failover",
    ]
    if RICH:
        t = Table(title="Conteo de filas por tabla", box=box.ROUNDED)
        t.add_column("Tabla", style="cyan")
        t.add_column("Filas", style="bold white", justify="right")
        for tabla in tablas:
            try:
                n = conn.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
                color = "green" if n > 0 else "dim"
                t.add_row(tabla, f"[{color}]{n}[/{color}]")
            except Exception:
                t.add_row(tabla, "[red]ERROR[/red]")
        console.print(t)
    else:
        print("\n=== CONTEO DE FILAS ===")
        for tabla in tablas:
            try:
                n = conn.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
                print(f"  {tabla:30s}: {n}")
            except Exception as e:
                print(f"  {tabla:30s}: ERROR ({e})")


def mostrar_tabla(conn: sqlite3.Connection, console, query: str,
                  titulo: str, limite: int = 20, params: tuple = ()) -> None:
    filas = conn.execute(query, params).fetchall()
    if not filas:
        if RICH:
            console.print(f"[dim]{titulo}: sin datos[/dim]")
        else:
            print(f"\n{titulo}: sin datos")
        return

    cols = filas[0].keys()
    if RICH:
        t = Table(title=f"{titulo} (últimas {min(len(filas),limite)})", box=box.SIMPLE_HEAVY)
        for c in cols:
            t.add_column(c, style="white", no_wrap=False, max_width=30)
        for fila in filas[:limite]:
            vals = []
            for v in fila:
                v = formatear_valor(v)
                s = str(v) if v is not None else "[dim]NULL[/dim]"
                if s in ("CONGESTION",):
                    s = f"[red]{s}[/red]"
                elif s in ("NORMAL",):
                    s = f"[green]{s}[/green]"
                elif s in ("PRIORIZACION",):
                    s = f"[blue]{s}[/blue]"
                elif s in ("VERDE",):
                    s = f"[green]{s}[/green]"
                elif s in ("ROJO",):
                    s = f"[red]{s}[/red]"
                vals.append(s)
            t.add_row(*vals)
        if len(filas) > limite:
            t.caption = f"[dim]... y {len(filas)-limite} filas más (usa --limite para ver más)[/dim]"
        console.print(t)
    else:
        print(f"\n=== {titulo} ===")
        print(" | ".join(cols))
        print("-" * 80)
        for fila in filas[:limite]:
            print(" | ".join(str(formatear_valor(v)) if v is not None else "NULL" for v in fila))
        if len(filas) > limite:
            print(f"... y {len(filas)-limite} filas más")


def menu_interactivo(ruta_db: str, limite: int) -> None:
    if RICH:
        console = Console()
    else:
        console = None

    def pr(msg):
        if RICH: console.print(msg)
        else: print(msg)

    pr(f"\n[bold cyan]Visor BD: {ruta_db}[/bold cyan]" if RICH else f"\nVisor BD: {ruta_db}")

    while True:
        pr("\n[bold yellow]Opciones:[/bold yellow]" if RICH else "\nOpciones:")
        opciones = [
            ("1", "Resumen (conteo de filas)"),
            ("2", "Últimos estados de tráfico"),
            ("3", "Últimos comandos de semáforo"),
            ("4", "Eventos de sensores recientes"),
            ("5", "Semáforos y su estado actual"),
            ("6", "Solicitudes de usuario"),
            ("7", "Eventos de failover"),
            ("8", "Buscar intersección específica"),
            ("9", "Buscar por sensor"),
            ("10", "Buscar por rango horario"),
            ("11", "Salir"),
        ]
        for num, desc in opciones:
            pr(f"  {num}) {desc}")

        opcion = input("\nOpción: ").strip()

        try:
            conn = conectar(ruta_db)

            if opcion == "1":
                mostrar_conteos(conn, console)

            elif opcion == "2":
                mostrar_tabla(conn, console,
                    f"""SELECT i.codigo as interseccion, et.ts_estado,
                               et.clasificacion, et.regla_aplicada,
                               et.longitud_cola as cola,
                               et.velocidad_promedio as vel,
                               et.densidad_trafico as densidad,
                               et.origen
                        FROM estado_trafico et
                        JOIN interseccion i ON i.id = et.interseccion_id
                        ORDER BY et.id DESC LIMIT {limite}""",
                    "Estados de Tráfico", limite)

            elif opcion == "3":
                mostrar_tabla(conn, console,
                    f"""SELECT i.codigo as interseccion, s.codigo as semaforo,
                               cs.tipo_comando, cs.valor_segundos,
                               cs.motivo, cs.origen, cs.estado_ejecucion,
                               cs.solicitado_en
                        FROM comando_semaforo cs
                        JOIN interseccion i ON i.id = cs.interseccion_id
                        JOIN semaforo s ON s.id = cs.semaforo_id
                        ORDER BY cs.id DESC LIMIT {limite}""",
                    "Comandos de Semáforo", limite)

            elif opcion == "4":
                mostrar_tabla(conn, console,
                    f"""SELECT i.codigo as interseccion, s.codigo as sensor,
                               es.tipo_evento, es.ts_evento,
                               COALESCE(ec.volumen, ee.vehiculos_contados) as valor_principal,
                               COALESCE(ec.velocidad_promedio, eg.velocidad_promedio) as velocidad
                        FROM evento_sensor es
                        JOIN sensor s ON s.id = es.sensor_id
                        JOIN interseccion i ON i.id = es.interseccion_id
                        LEFT JOIN evento_camara ec ON ec.evento_id = es.id
                        LEFT JOIN evento_espira ee ON ee.evento_id = es.id
                        LEFT JOIN evento_gps eg ON eg.evento_id = es.id
                        ORDER BY es.id DESC LIMIT {limite}""",
                    "Eventos de Sensores", limite)

            elif opcion == "5":
                mostrar_tabla(conn, console,
                    """SELECT s.codigo, i.codigo as interseccion,
                              s.estado_actual, s.duracion_base_seg,
                              s.updated_at
                       FROM semaforo s
                       JOIN interseccion i ON i.id = s.interseccion_id
                       ORDER BY i.codigo""",
                    "Estado de Semáforos", 50)

            elif opcion == "6":
                mostrar_tabla(conn, console,
                    f"""SELECT su.tipo_solicitud,
                               COALESCE(i.codigo, 'N/A') as interseccion,
                               su.detalle, su.resultado_resumen,
                               su.solicitada_en, su.atendida_en
                        FROM solicitud_usuario su
                        LEFT JOIN interseccion i ON i.id = su.interseccion_id
                        ORDER BY su.id DESC LIMIT {limite}""",
                    "Solicitudes de Usuario", limite)

            elif opcion == "7":
                mostrar_tabla(conn, console,
                    f"""SELECT tipo_evento, nodo_origen, descripcion, ocurrido_en
                        FROM evento_failover
                        ORDER BY id DESC LIMIT {limite}""",
                    "Eventos de Failover", limite)

            elif opcion == "8":
                inter = input("Código intersección (ej. INT-A1): ").strip()
                mostrar_tabla(conn, console,
                    f"""SELECT et.ts_estado, et.clasificacion, et.regla_aplicada,
                               et.longitud_cola, et.velocidad_promedio,
                               et.densidad_trafico, et.origen
                        FROM estado_trafico et
                        JOIN interseccion i ON i.id = et.interseccion_id
                        WHERE i.codigo = ?
                        ORDER BY et.id DESC LIMIT {limite}""",
                    f"Historial {inter}", limite, (inter,))

            elif opcion == "9":
                sensor = input("Código sensor (ej. CAM-A1): ").strip()
                mostrar_tabla(conn, console,
                    f"""SELECT s.codigo as sensor, i.codigo as interseccion,
                               es.tipo_evento, es.ts_evento,
                               COALESCE(ec.volumen, ee.vehiculos_contados) as valor_principal,
                               COALESCE(ec.velocidad_promedio, eg.velocidad_promedio) as velocidad,
                               eg.nivel_congestion
                        FROM evento_sensor es
                        JOIN sensor s ON s.id = es.sensor_id
                        JOIN interseccion i ON i.id = es.interseccion_id
                        LEFT JOIN evento_camara ec ON ec.evento_id = es.id
                        LEFT JOIN evento_espira ee ON ee.evento_id = es.id
                        LEFT JOIN evento_gps eg ON eg.evento_id = es.id
                        WHERE s.codigo = ?
                        ORDER BY es.id DESC LIMIT {limite}""",
                    f"Flujo del sensor {sensor}", limite, (sensor,))

            elif opcion == "10":
                print("Formato: YYYY-MM-DD HH:MM:SS")
                inicio = input("Hora inicio (Colombia): ").strip()
                fin = input("Hora fin (Colombia): ").strip()
                inicio_utc = convertir_colombia_a_utc(inicio)
                fin_utc = convertir_colombia_a_utc(fin)
                mostrar_tabla(conn, console,
                    f"""SELECT i.codigo as interseccion, s.codigo as sensor,
                               es.tipo_evento, es.ts_evento,
                               COALESCE(ec.volumen, ee.vehiculos_contados) as valor_principal,
                               COALESCE(ec.velocidad_promedio, eg.velocidad_promedio) as velocidad
                        FROM evento_sensor es
                        JOIN sensor s ON s.id = es.sensor_id
                        JOIN interseccion i ON i.id = es.interseccion_id
                        LEFT JOIN evento_camara ec ON ec.evento_id = es.id
                        LEFT JOIN evento_espira ee ON ee.evento_id = es.id
                        LEFT JOIN evento_gps eg ON eg.evento_id = es.id
                        WHERE datetime(es.ts_evento) BETWEEN datetime(?) AND datetime(?)
                        ORDER BY es.ts_evento ASC LIMIT {limite}""",
                    f"Eventos entre {inicio} y {fin}", limite, (inicio_utc, fin_utc))

            elif opcion == "11":
                pr("[bold]Saliendo...[/bold]" if RICH else "Saliendo...")
                break
            else:
                pr("[red]Opción inválida[/red]" if RICH else "Opción inválida")

            conn.close()

        except Exception as exc:
            pr(f"[red]Error: {exc}[/red]" if RICH else f"Error: {exc}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visor interactivo de BD de tráfico")
    parser.add_argument("--db", default="data/traffic_primary.db", help="Ruta a la BD")
    parser.add_argument("--limite", type=int, default=20, help="Máx filas a mostrar (default: 20)")
    parser.add_argument("--limpiar", action="store_true", help="Limpiar datos antiguos")
    parser.add_argument("--dias", type=int, default=1, help="Días a conservar al limpiar")
    args = parser.parse_args()

    if not Path(args.db).exists():
        print(f"[ERROR] No existe la BD: {args.db}")
        print("Asegúrate de haber ejecutado el sistema al menos una vez.")
        sys.exit(1)

    if args.limpiar:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from src.persistence.repositorio_sqlite import RepositorioSQLite
        repo = RepositorioSQLite(args.db)
        n = repo.limpiar_datos_antiguos(args.dias)
        print(f"Eliminados {n} registros anteriores a {args.dias} día(s)")
    else:
        menu_interactivo(args.db, args.limite)
