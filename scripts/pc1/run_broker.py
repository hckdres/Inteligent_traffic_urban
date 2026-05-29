from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.common_bootstrap import bootstrap_project_root

bootstrap_project_root()


def main(pc2_ip: str, pc2_port: int, multihilo: bool) -> None:
    if multihilo:
        import src.pc1.broker_zmq_multihilo as bm
        from src.pc1.broker_zmq_multihilo import BrokerMultihilo

        bm.PC2_PULL_ENDPOINT = f"tcp://{pc2_ip}:{pc2_port}"
        print(f"[PC1-BROKER] modo=multihilo pc2={bm.PC2_PULL_ENDPOINT}")
        BrokerMultihilo().iniciar()
        return

    import src.pc1.broker_zmq as b
    b.PC2_PUSH_ENDPOINT = f"tcp://{pc2_ip}:{pc2_port}"
    print(f"[PC1-BROKER] modo=simple pc2={b.PC2_PUSH_ENDPOINT}")
    b.main()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PC1 - Broker (componente separado)")
    parser.add_argument("--pc2-ip", default="127.0.0.1")
    parser.add_argument("--pc2-port", type=int, default=5557)
    parser.add_argument("--multihilo", action="store_true")
    args = parser.parse_args()
    main(args.pc2_ip, args.pc2_port, args.multihilo)
