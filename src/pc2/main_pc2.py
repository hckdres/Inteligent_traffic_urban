from __future__ import annotations

import threading

from src.pc2.servicio_analitica import ServicioAnalitica
from src.pc2.servidor_bd_replica import ServidorBDReplica


def main() -> None:
    hilo_replica = threading.Thread(target=lambda: ServidorBDReplica().iniciar(), daemon=True)
    hilo_replica.start()

    servicio = ServicioAnalitica()
    servicio.escuchar_eventos()


if __name__ == "__main__":
    main()
