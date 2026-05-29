from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.common_bootstrap import bootstrap_project_root

bootstrap_project_root()


def main(control_host: str, control_port: int) -> None:
    import src.pc2.servicio_control_semaforos as scs
    from src.pc2.servicio_control_semaforos import ServicioControlSemaforos

    scs.CONTROL_SEMAFOROS_ENDPOINT = f"tcp://{control_host}:{control_port}"
    print(f"[PC2-CONTROL] endpoint={scs.CONTROL_SEMAFOROS_ENDPOINT}")
    ServicioControlSemaforos().ejecutar()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PC2 - Control de semaforos (componente separado)")
    parser.add_argument("--control-host", default="127.0.0.1")
    parser.add_argument("--control-port", type=int, default=5570)
    args = parser.parse_args()
    main(args.control_host, args.control_port)
