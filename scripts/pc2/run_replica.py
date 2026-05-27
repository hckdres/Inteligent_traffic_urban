from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.common_bootstrap import bootstrap_project_root

bootstrap_project_root()


def main(bind_host: str, persist_port: int, query_port: int, seed_path: str) -> None:
    import src.pc2.servidor_bd_replica as sbr_mod
    from src.pc2.servidor_bd_replica import ServidorBDReplica

    sbr_mod.REPLICA_PERSIST_ENDPOINT = f"tcp://{bind_host}:{persist_port}"
    sbr_mod.REPLICA_QUERY_ENDPOINT = f"tcp://{bind_host}:{query_port}"

    replica = ServidorBDReplica()
    config_path = Path(seed_path)
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            replica.repo.seed_desde_config(config)
            print(f"[PC2-REPLICA] seed cargado desde {config_path}")
        except Exception as exc:
            print(f"[PC2-REPLICA] error haciendo seed: {exc}")

    print(f"[PC2-REPLICA] persist={sbr_mod.REPLICA_PERSIST_ENDPOINT}")
    print(f"[PC2-REPLICA] query={sbr_mod.REPLICA_QUERY_ENDPOINT}")
    replica.iniciar()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PC2 - BD replica (componente separado)")
    parser.add_argument("--bind-host", default="0.0.0.0")
    parser.add_argument("--persist-port", type=int, default=5560)
    parser.add_argument("--query-port", type=int, default=5565)
    parser.add_argument("--seed-path", default="src/config/system.json")
    args = parser.parse_args()
    main(args.bind_host, args.persist_port, args.query_port, args.seed_path)
