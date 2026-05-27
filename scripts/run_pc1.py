from scripts.launch.legacy.run_pc1 import main


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="PC1 — Nodo de Captura")
    parser.add_argument("--pc2-ip", default="127.0.0.1", help="IP de PC2 (default: 127.0.0.1)")
    parser.add_argument("--multihilo", action="store_true", help="Usar broker multihilo")
    args = parser.parse_args()
    main(pc2_ip=args.pc2_ip, multihilo=args.multihilo)
