from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> None:
    from src.pc2.servidor_bd_replica import ServidorBDReplica

    replica = ServidorBDReplica()
    try:
        config_path = Path("src/config/system.json")
        if config_path.exists():
            with config_path.open("r", encoding="utf-8") as f:
                config = json.load(f)
            replica.repo.seed_desde_config(config)
            print("[PC2-REPLICA] BD replica sembrada con catalogos.")
    except Exception as exc:
        print(f"[PC2-REPLICA] Error sembrando BD replica: {exc}")

    replica.iniciar()


if __name__ == "__main__":
    main()
