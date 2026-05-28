import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(line_buffering=True)

from src.pc2.main_pc2 import main


def ejecutar_pc2(pc3_ip: str, config_path: str) -> None:
    import src.pc2.gestor_failover as gf
    gf.PRIMARY_PERSIST_ENDPOINT = f"tcp://{pc3_ip}:5561"

    import src.pc2.health_check as hc
    hc.PRIMARY_HEALTH_ENDPOINT = f"tcp://{pc3_ip}:5563"

    import src.pc2.servicio_analitica as sa
    sa.ANALITICA_COMMAND_ENDPOINT = "tcp://0.0.0.0:5562"
    sa.PC2_PULL_ENDPOINT = "tcp://0.0.0.0:5557"

    import src.pc2.servidor_bd_replica as sbr
    sbr.REPLICA_PERSIST_ENDPOINT = "tcp://0.0.0.0:5560"
    sbr.REPLICA_QUERY_ENDPOINT = "tcp://0.0.0.0:5565"

    print(f"[PC2] Conectando a PC3 en {pc3_ip}")
    print("[PC2] Escuchando réplica en 0.0.0.0:5560 y 0.0.0.0:5565")
    main(config_path=config_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PC2 — Análisis y Persistencia Secundaria")
    parser.add_argument("--pc3-ip", default="127.0.0.1", help="IP de PC3 (default: 127.0.0.1)")
    parser.add_argument("--config", default="src/config/system.json", help="Ruta al archivo de configuración del sistema")
    args = parser.parse_args()
    ejecutar_pc2(pc3_ip=args.pc3_ip, config_path=args.config)
