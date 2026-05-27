import argparse

from scripts.pc2.run_analitica import main


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PC2 - Servicio de Analitica (separado)")
    parser.add_argument("--pc3-ip", default="127.0.0.1")
    parser.add_argument("--control-host", default="127.0.0.1")
    parser.add_argument("--control-port", type=int, default=5570)
    args = parser.parse_args()
    main(
        pc3_ip=args.pc3_ip,
        primary_persist_port=5561,
        primary_health_port=5563,
        bind_host="0.0.0.0",
        pull_port=5557,
        command_port=5562,
        control_host=args.control_host,
        control_port=args.control_port,
    )
