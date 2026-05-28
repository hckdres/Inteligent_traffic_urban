from __future__ import annotations

import json
import threading
from pathlib import Path

from src.pc3.monitoreo_consulta import MonitoreoConsulta
from src.pc3.servidor_bd_principal import ServidorBDPrincipal


def main(config_path: str = "src/config/system.json") -> None:
    servidor = ServidorBDPrincipal()
    try:
        ruta = Path(config_path)
        if ruta.exists():
            with ruta.open("r", encoding="utf-8") as f:
                config = json.load(f)
            servidor.seed(config)
            print("[PC3] BD principal sembrada con catalogos.")
    except Exception as e:
        print(f"[PC3] Error sembrando BD principal: {e}")

    hilo_bd = threading.Thread(target=servidor.iniciar, daemon=True)
    hilo_bd.start()

    MonitoreoConsulta(ruta_config_sistema=config_path).ejecutar()


if __name__ == "__main__":
    main()
