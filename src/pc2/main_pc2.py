from __future__ import annotations

import json
import threading
from pathlib import Path

from src.pc2.servicio_analitica import ServicioAnalitica
from src.pc2.servicio_control_semaforos import ServicioControlSemaforos
from src.pc2.servidor_bd_replica import ServidorBDReplica


def main() -> None:
    replica = ServidorBDReplica()
    try:
        config_path = Path("src/config/system.json")
        if config_path.exists():
            with config_path.open("r", encoding="utf-8") as f:
                config = json.load(f)
            replica.repo.seed_desde_config(config)
            print("[PC2] BD réplica sembrada con catálogos.")
    except Exception as e:
        print(f"[PC2] Error sembrando BD réplica: {e}")

    hilo_replica = threading.Thread(target=replica.iniciar, daemon=True)
    hilo_replica.start()

    hilo_control = threading.Thread(target=ServicioControlSemaforos().ejecutar, daemon=True)
    hilo_control.start()

    servicio = ServicioAnalitica()
    servicio.escuchar_eventos()


if __name__ == "__main__":
    main()
