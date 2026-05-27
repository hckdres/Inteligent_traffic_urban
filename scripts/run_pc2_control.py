from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main(control_endpoint: str) -> None:
    import src.pc2.servicio_control_semaforos as scs
    scs.CONTROL_SEMAFOROS_ENDPOINT = control_endpoint

    from src.pc2.servicio_control_semaforos import ServicioControlSemaforos

    print(f"[PC2-CONTROL] esperando decisiones en {control_endpoint}")
    ServicioControlSemaforos().ejecutar()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PC2 - Servicio de Control de Semaforos (separado)")
    parser.add_argument(
        "--control-endpoint",
        default="tcp://127.0.0.1:5570",
        help="Endpoint PUSH/PULL para control de semaforos",
    )
    args = parser.parse_args()
    main(control_endpoint=args.control_endpoint)
