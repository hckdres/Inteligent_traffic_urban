from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.common_bootstrap import bootstrap_project_root

bootstrap_project_root()


def main(
    pc3_ip: str,
    primary_persist_port: int,
    primary_health_port: int,
    bind_host: str,
    pull_port: int,
    command_port: int,
    control_host: str,
    control_port: int,
) -> None:
    import src.pc2.gestor_failover as gf
    import src.pc2.health_check as hc
    import src.pc2.servicio_analitica as sa
    from src.pc2.servicio_analitica import ServicioAnalitica

    gf.PRIMARY_PERSIST_ENDPOINT = f"tcp://{pc3_ip}:{primary_persist_port}"
    hc.PRIMARY_HEALTH_ENDPOINT = f"tcp://{pc3_ip}:{primary_health_port}"
    sa.PC2_PULL_ENDPOINT = f"tcp://{bind_host}:{pull_port}"
    sa.ANALITICA_COMMAND_ENDPOINT = f"tcp://{bind_host}:{command_port}"
    sa.CONTROL_SEMAFOROS_ENDPOINT = f"tcp://{control_host}:{control_port}"

    print(f"[PC2-ANALITICA] pull={sa.PC2_PULL_ENDPOINT}")
    print(f"[PC2-ANALITICA] command={sa.ANALITICA_COMMAND_ENDPOINT}")
    print(f"[PC2-ANALITICA] control={sa.CONTROL_SEMAFOROS_ENDPOINT}")
    print(f"[PC2-ANALITICA] primary_persist={gf.PRIMARY_PERSIST_ENDPOINT}")
    print(f"[PC2-ANALITICA] primary_health={hc.PRIMARY_HEALTH_ENDPOINT}")
    ServicioAnalitica().escuchar_eventos()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PC2 - Analitica (componente separado)")
    parser.add_argument("--pc3-ip", default="127.0.0.1")
    parser.add_argument("--primary-persist-port", type=int, default=5561)
    parser.add_argument("--primary-health-port", type=int, default=5563)
    parser.add_argument("--bind-host", default="0.0.0.0")
    parser.add_argument("--pull-port", type=int, default=5557)
    parser.add_argument("--command-port", type=int, default=5562)
    parser.add_argument("--control-host", default="127.0.0.1")
    parser.add_argument("--control-port", type=int, default=5570)
    args = parser.parse_args()
    main(
        args.pc3_ip,
        args.primary_persist_port,
        args.primary_health_port,
        args.bind_host,
        args.pull_port,
        args.command_port,
        args.control_host,
        args.control_port,
    )
