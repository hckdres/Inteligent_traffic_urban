from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.common_bootstrap import bootstrap_project_root

bootstrap_project_root()


def main(bind_host: str, persist_port: int, query_port: int, health_port: int, seed_path: str) -> None:
    import src.pc3.servidor_bd_principal as sbp_mod
    from src.pc3.servidor_bd_principal import ServidorBDPrincipal

    sbp_mod.PRIMARY_PERSIST_ENDPOINT = f"tcp://{bind_host}:{persist_port}"
    sbp_mod.PRIMARY_QUERY_ENDPOINT = f"tcp://{bind_host}:{query_port}"
    sbp_mod.PRIMARY_HEALTH_ENDPOINT = f"tcp://{bind_host}:{health_port}"

    servidor = ServidorBDPrincipal()
    config_path = Path(seed_path)
    if config_path.exists():
        try:
            servidor.seed(json.loads(config_path.read_text(encoding="utf-8")))
            print(f"[PC3-BD] seed cargado desde {config_path}")
        except Exception as exc:
            print(f"[PC3-BD] error haciendo seed: {exc}")

    print(f"[PC3-BD] persist={sbp_mod.PRIMARY_PERSIST_ENDPOINT}")
    print(f"[PC3-BD] query={sbp_mod.PRIMARY_QUERY_ENDPOINT}")
    print(f"[PC3-BD] health={sbp_mod.PRIMARY_HEALTH_ENDPOINT}")
    servidor.iniciar()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PC3 - BD principal (componente separado)")
    parser.add_argument("--bind-host", default="0.0.0.0")
    parser.add_argument("--persist-port", type=int, default=5561)
    parser.add_argument("--query-port", type=int, default=5564)
    parser.add_argument("--health-port", type=int, default=5563)
    parser.add_argument("--seed-path", default="src/config/system.json")
    args = parser.parse_args()
    main(args.bind_host, args.persist_port, args.query_port, args.health_port, args.seed_path)
