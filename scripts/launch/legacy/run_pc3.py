from scripts.launch.legacy.run_pc3 import main


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="PC3 — Monitoreo y BD Principal")
    parser.add_argument("--pc2-ip", default="127.0.0.1", help="IP de PC2 (default: 127.0.0.1)")
    args = parser.parse_args()
    main(pc2_ip=args.pc2_ip)
