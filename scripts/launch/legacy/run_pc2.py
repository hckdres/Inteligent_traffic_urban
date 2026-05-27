from scripts.launch.legacy.run_pc2 import ejecutar_pc2


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="PC2 — Análisis y Persistencia Secundaria")
    parser.add_argument("--pc3-ip", default="127.0.0.1", help="IP de PC3 (default: 127.0.0.1)")
    args = parser.parse_args()
    ejecutar_pc2(pc3_ip=args.pc3_ip)
