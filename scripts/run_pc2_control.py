import argparse

from scripts.pc2.run_control import main


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PC2 - Servicio de Control de Semaforos (separado)")
    parser.add_argument("--control-host", default="127.0.0.1")
    parser.add_argument("--control-port", type=int, default=5570)
    args = parser.parse_args()
    main(control_host=args.control_host, control_port=args.control_port)
