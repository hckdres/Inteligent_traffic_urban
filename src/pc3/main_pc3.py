from __future__ import annotations

import threading

from src.pc3.monitoreo_consulta import MonitoreoConsulta
from src.pc3.servidor_bd_principal import ServidorBDPrincipal


def main() -> None:
    hilo_bd = threading.Thread(target=lambda: ServidorBDPrincipal().iniciar(), daemon=True)
    hilo_bd.start()

    MonitoreoConsulta().ejecutar()


if __name__ == "__main__":
    main()
