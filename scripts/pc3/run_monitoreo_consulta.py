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
    pc2_ip: str,
    analitica_port: int,
    replica_query_port: int,
    primary_ip: str,
    primary_query_port: int,
    config_path: str,
) -> None:
    import src.pc3.monitoreo_consulta as mc_mod
    from src.pc3.monitoreo_consulta import MonitoreoConsulta

    mc_mod.ANALITICA_COMMAND_ENDPOINT = f"tcp://{pc2_ip}:{analitica_port}"
    mc_mod.REPLICA_QUERY_ENDPOINT = f"tcp://{pc2_ip}:{replica_query_port}"
    mc_mod.PRIMARY_QUERY_ENDPOINT = f"tcp://{primary_ip}:{primary_query_port}"

    print(f"[PC3-MON] analitica={mc_mod.ANALITICA_COMMAND_ENDPOINT}")
    print(f"[PC3-MON] replica={mc_mod.REPLICA_QUERY_ENDPOINT}")
    print(f"[PC3-MON] primary={mc_mod.PRIMARY_QUERY_ENDPOINT}")
    print(f"[PC3-MON] config={config_path}")
    MonitoreoConsulta(ruta_config_sistema=config_path).ejecutar()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PC3 - Monitoreo/consulta (componente separado)")
    parser.add_argument("--pc2-ip", default="127.0.0.1")
    parser.add_argument("--analitica-port", type=int, default=5562)
    parser.add_argument("--replica-query-port", type=int, default=5565)
    parser.add_argument("--primary-ip", default="127.0.0.1")
    parser.add_argument("--primary-query-port", type=int, default=5564)
    parser.add_argument("--config", default="src/config/system.json")
    args = parser.parse_args()
    main(args.pc2_ip, args.analitica_port, args.replica_query_port, args.primary_ip, args.primary_query_port, args.config)
