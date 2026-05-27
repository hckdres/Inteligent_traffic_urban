from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main(pc3_ip: str, control_endpoint: str) -> None:
    import src.pc2.gestor_failover as gf
    gf.PRIMARY_PERSIST_ENDPOINT = f"tcp://{pc3_ip}:5561"

    import src.pc2.health_check as hc
    hc.PRIMARY_HEALTH_ENDPOINT = f"tcp://{pc3_ip}:5563"

    import src.pc2.servicio_analitica as sa
    sa.PC2_PULL_ENDPOINT = "tcp://0.0.0.0:5557"
    sa.ANALITICA_COMMAND_ENDPOINT = "tcp://0.0.0.0:5562"
    sa.CONTROL_SEMAFOROS_ENDPOINT = control_endpoint

    from src.pc2.servicio_analitica import ServicioAnalitica

    print(f"[PC2-ANALITICA] escuchando eventos en tcp://0.0.0.0:5557")
    print(f"[PC2-ANALITICA] escuchando comandos en tcp://0.0.0.0:5562")
    print(f"[PC2-ANALITICA] enviando decisiones a control en {control_endpoint}")
    print(f"[PC2-ANALITICA] persistencia principal hacia PC3 en {pc3_ip}")
    ServicioAnalitica().escuchar_eventos()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PC2 - Servicio de Analitica (separado)")
    parser.add_argument("--pc3-ip", default="127.0.0.1", help="IP de PC3 (default: 127.0.0.1)")
    parser.add_argument(
        "--control-endpoint",
        default="tcp://127.0.0.1:5570",
        help="Endpoint PUSH/PULL para control de semaforos",
    )
    args = parser.parse_args()
    main(pc3_ip=args.pc3_ip, control_endpoint=args.control_endpoint)
