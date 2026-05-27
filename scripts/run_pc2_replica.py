from scripts.pc2.run_replica import main


if __name__ == "__main__":
    main(bind_host="0.0.0.0", persist_port=5560, query_port=5565, seed_path="src/config/system.json")
