"""
PC3 — Nodo de Monitoreo y BD Principal
Lanza: servidor_bd_principal (hilo daemon) + monitoreo_consulta (CLI interactivo)

Uso:
    python scripts/run_pc3.py                                        # todo en localhost
    python scripts/run_pc3.py --pc2-ip 192.168.1.20                  # PC2 en otra máquina
"""
from __future__ import annotations

import argparse
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import src.pc3.monitoreo_consulta as mc_mod
from src.pc3.monitoreo_consulta import MonitoreoConsulta
from src.pc3.servidor_bd_principal import ServidorBDPrincipal


def main(pc2_ip: str) -> None:
    analitica_cmd = f"tcp://{pc2_ip}:5562"
    replica_query = f"tcp://{pc2_ip}:5565"

    # PC3 escucha en 0.0.0.0 para que PC2 pueda conectarse
    import src.pc3.servidor_bd_principal as sbp_mod
    sbp_mod.PRIMARY_PERSIST_ENDPOINT = "tcp://0.0.0.0:5561"
    sbp_mod.PRIMARY_QUERY_ENDPOINT   = "tcp://0.0.0.0:5564"
    sbp_mod.PRIMARY_HEALTH_ENDPOINT  = "tcp://0.0.0.0:5563"

    # MonitoreoConsulta apunta a PC2 para comandos y réplica
    mc_mod.ANALITICA_COMMAND_ENDPOINT = analitica_cmd
    mc_mod.REPLICA_QUERY_ENDPOINT     = replica_query
    mc_mod.PRIMARY_QUERY_ENDPOINT     = "tcp://127.0.0.1:5564"   # local

    print(f"[PC3] Iniciando — analítica en PC2 ({pc2_ip})")
    print(f"[PC3]   PULL persistencia : tcp://0.0.0.0:5561")
    print(f"[PC3]   REP consultas     : tcp://0.0.0.0:5564")
    print(f"[PC3]   REP health        : tcp://0.0.0.0:5563")
    print(f"[PC3]   REQ -> analítica  : {analitica_cmd}")
    print(f"[PC3]   REQ -> réplica    : {replica_query}")

    hilo_bd = threading.Thread(
        target=lambda: ServidorBDPrincipal().iniciar(),
        daemon=True,
        name="bd-principal",
    )
    hilo_bd.start()
    print("[PC3] BD Principal iniciada")

    MonitoreoConsulta().ejecutar()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PC3 — Monitoreo y BD Principal")
    parser.add_argument("--pc2-ip", default="127.0.0.1", help="IP de PC2 (default: 127.0.0.1)")
    args = parser.parse_args()
    main(pc2_ip=args.pc2_ip)