#!/usr/bin/env python3
"""Diagnostico de maquinas/VMs para el proyecto de trafico urbano.

Incluye:
- Inventario del host: CPU, RAM, OS, Python, pyzmq, SQLite
- Resumen de red para distinguir localhost/LAN/entorno virtualizado
- Herramientas de medicion con time.time()
- Analisis basico de logs
- Consultas SQLite desde CLI
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import platform
import re
import socket
import sqlite3
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class NetworkInfo:
    hostname: str
    fqdn: str
    local_ips: list[str]
    has_loopback_only: bool
    private_ips: list[str]
    public_ips: list[str]
    guessed_network_type: str


@dataclass
class SystemInventory:
    timestamp_utc: str
    machine_name: str
    os: str
    os_release: str
    os_version: str
    architecture: str
    cpu_cores_logical: int | None
    cpu_cores_physical: int | None
    ram_total_bytes: int | None
    ram_total_gb: float | None
    python_version: str
    pyzmq_version: str
    sqlite_version: str
    virtualization_hint: str
    network: NetworkInfo


def _bytes_to_gb(value: int | None) -> float | None:
    if value is None:
        return None
    return round(value / (1024 ** 3), 2)


def _get_total_ram_bytes() -> int | None:
    # Sin dependencias externas: preferimos stdlib.
    try:
        if hasattr(os, "sysconf"):
            page_size = os.sysconf("SC_PAGE_SIZE")
            phys_pages = os.sysconf("SC_PHYS_PAGES")
            if isinstance(page_size, int) and isinstance(phys_pages, int):
                return page_size * phys_pages
    except Exception:
        pass

    # Fallback Windows via ctypes
    try:
        import ctypes

        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatus()
        status.dwLength = ctypes.sizeof(MemoryStatus)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return int(status.ullTotalPhys)
    except Exception:
        pass

    return None


def _get_physical_cores() -> int | None:
    try:
        # Esta opcion existe en varios SOs modernos.
        return os.cpu_count()
    except Exception:
        return None


def _detect_virtualization_hint() -> str:
    text = " ".join(
        [
            platform.platform(),
            platform.uname().system,
            platform.uname().release,
            platform.uname().version,
            platform.uname().machine,
            platform.uname().node,
        ]
    ).lower()

    markers = {
        "virtualbox": "VirtualBox",
        "vmware": "VMware",
        "kvm": "KVM",
        "hyper-v": "Hyper-V",
        "hyperv": "Hyper-V",
        "qemu": "QEMU",
        "xen": "Xen",
        "wsl": "WSL",
    }

    for key, label in markers.items():
        if key in text:
            return f"Posible entorno virtualizado ({label})"

    return "No concluyente"


def _get_ips() -> list[str]:
    ips = set()
    hostname = socket.gethostname()

    try:
        for res in socket.getaddrinfo(hostname, None):
            ip = res[4][0]
            if ":" in ip:
                # Ignoramos IPv6 para simplificar inventario LAN de la U.
                continue
            ips.add(ip)
    except socket.gaierror:
        pass

    # Metodo extra para obtener IP saliente principal.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ips.add(s.getsockname()[0])
    except OSError:
        pass

    if not ips:
        ips.add("127.0.0.1")

    return sorted(ips)


def _classify_network(ips: list[str]) -> tuple[list[str], list[str], bool, str]:
    private_ips: list[str] = []
    public_ips: list[str] = []

    for ip in ips:
        addr = ipaddress.ip_address(ip)
        if addr.is_private or addr.is_loopback or addr.is_link_local:
            private_ips.append(ip)
        else:
            public_ips.append(ip)

    has_loopback_only = all(ip.startswith("127.") for ip in ips)

    if has_loopback_only:
        network_type = "Solo localhost (sin LAN detectable)"
    elif private_ips and not public_ips:
        network_type = "LAN privada/local (posible red de la universidad o VM en red interna)"
    elif private_ips and public_ips:
        network_type = "Mixta (LAN privada + IP publica)"
    else:
        network_type = "IP publica directa"

    return private_ips, public_ips, has_loopback_only, network_type


def build_inventory() -> SystemInventory:
    hostname = socket.gethostname()
    fqdn = socket.getfqdn()
    ips = _get_ips()
    private_ips, public_ips, has_loopback_only, network_type = _classify_network(ips)

    try:
        import zmq

        pyzmq_version = zmq.__version__
    except Exception:
        pyzmq_version = "No disponible"

    ram_bytes = _get_total_ram_bytes()

    network = NetworkInfo(
        hostname=hostname,
        fqdn=fqdn,
        local_ips=ips,
        has_loopback_only=has_loopback_only,
        private_ips=private_ips,
        public_ips=public_ips,
        guessed_network_type=network_type,
    )

    return SystemInventory(
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        machine_name=hostname,
        os=platform.system(),
        os_release=platform.release(),
        os_version=platform.version(),
        architecture=platform.machine(),
        cpu_cores_logical=os.cpu_count(),
        cpu_cores_physical=_get_physical_cores(),
        ram_total_bytes=ram_bytes,
        ram_total_gb=_bytes_to_gb(ram_bytes),
        python_version=platform.python_version(),
        pyzmq_version=pyzmq_version,
        sqlite_version=sqlite3.sqlite_version,
        virtualization_hint=_detect_virtualization_hint(),
        network=network,
    )


def print_inventory_markdown(inventory: SystemInventory) -> None:
    n = inventory.network
    print("# Inventario de maquina")
    print(f"- Timestamp UTC: {inventory.timestamp_utc}")
    print(f"- Maquina: {inventory.machine_name}")
    print(f"- OS: {inventory.os} {inventory.os_release} ({inventory.os_version})")
    print(f"- Arquitectura: {inventory.architecture}")
    print(f"- CPU (logicos): {inventory.cpu_cores_logical}")
    print(f"- CPU (fisicos, aprox): {inventory.cpu_cores_physical}")
    print(f"- RAM total (GB): {inventory.ram_total_gb}")
    print(f"- Python: {inventory.python_version}")
    print(f"- pyzmq: {inventory.pyzmq_version}")
    print(f"- SQLite: {inventory.sqlite_version}")
    print(f"- Virtualizacion: {inventory.virtualization_hint}")
    print("\n## Red")
    print(f"- Hostname: {n.hostname}")
    print(f"- FQDN: {n.fqdn}")
    print(f"- IPs locales: {', '.join(n.local_ips)}")
    print(f"- IPs privadas/locales: {', '.join(n.private_ips) if n.private_ips else '-'}")
    print(f"- IPs publicas: {', '.join(n.public_ips) if n.public_ips else '-'}")
    print(f"- Tipo detectado: {n.guessed_network_type}")


def time_demo(iterations: int) -> None:
    print(f"Midiendo {iterations} iteraciones con time.time()...")
    t0 = time.time()
    checksum = 0
    for i in range(iterations):
        checksum += (i * 17) % 13
    t1 = time.time()
    elapsed = t1 - t0
    print(f"Resultado checksum={checksum}")
    print(f"Inicio (epoch): {t0}")
    print(f"Fin (epoch): {t1}")
    print(f"Duracion (s): {elapsed:.6f}")


def analyze_logs(path: Path, level_regex: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"No existe: {path}")

    counts = {
        "DEBUG": 0,
        "INFO": 0,
        "WARNING": 0,
        "ERROR": 0,
        "CRITICAL": 0,
        "OTHER": 0,
        "TOTAL": 0,
    }

    level_re = re.compile(level_regex)

    for file in ([path] if path.is_file() else sorted(path.rglob("*.log"))):
        try:
            with file.open("r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    counts["TOTAL"] += 1
                    m = level_re.search(line)
                    if not m:
                        counts["OTHER"] += 1
                        continue
                    lvl = m.group(1).upper()
                    counts[lvl if lvl in counts else "OTHER"] += 1
        except OSError as e:
            print(f"No se pudo leer {file}: {e}")

    print(json.dumps(counts, indent=2, ensure_ascii=False))


def run_sqlite_query(db_path: Path, query: str, limit: int) -> None:
    if not db_path.exists():
        raise FileNotFoundError(f"No existe la BD: {db_path}")

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(query)
        rows = cur.fetchmany(limit)

    result = [dict(r) for r in rows]
    print(json.dumps(result, indent=2, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnostico para hosts/VMs del proyecto")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_inventory = sub.add_parser("inventory", help="Inventario de sistema y red")
    p_inventory.add_argument("--format", choices=["json", "md"], default="json")
    p_inventory.add_argument("--out", type=Path, help="Ruta opcional para guardar resultado")

    p_time = sub.add_parser("time-demo", help="Demo de medicion con time.time()")
    p_time.add_argument("--iterations", type=int, default=2_000_000)

    p_logs = sub.add_parser("log-analyze", help="Analisis basico de logs")
    p_logs.add_argument("path", type=Path, help="Archivo .log o carpeta de logs")
    p_logs.add_argument(
        "--level-regex",
        default=r"\\b(DEBUG|INFO|WARNING|ERROR|CRITICAL)\\b",
        help="Regex con grupo para nivel de log",
    )

    p_sql = sub.add_parser("sqlite-query", help="Ejecuta consulta SELECT en SQLite")
    p_sql.add_argument("db", type=Path, help="Ruta del .db/.sqlite")
    p_sql.add_argument("query", help="Consulta SQL (recomendado SELECT)")
    p_sql.add_argument("--limit", type=int, default=100)

    args = parser.parse_args()

    if args.cmd == "inventory":
        inventory = build_inventory()
        if args.format == "json":
            text = json.dumps(asdict(inventory), indent=2, ensure_ascii=False)
            print(text)
        else:
            print_inventory_markdown(inventory)
            text = None

        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            if args.format == "md":
                # Para markdown, reconstruimos salida en formato JSON si se quiere persistir estructurado.
                if text is None:
                    text = json.dumps(asdict(inventory), indent=2, ensure_ascii=False)
            args.out.write_text(text, encoding="utf-8")
            print(f"Guardado en: {args.out}")

    elif args.cmd == "time-demo":
        time_demo(args.iterations)

    elif args.cmd == "log-analyze":
        analyze_logs(args.path, args.level_regex)

    elif args.cmd == "sqlite-query":
        run_sqlite_query(args.db, args.query, args.limit)


if __name__ == "__main__":
    main()
