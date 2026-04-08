from __future__ import annotations

from typing import Dict, Any


class ControlSemaforos:
    def aplicar_accion(self, decision: Dict[str, Any]) -> None:
        interseccion = decision["interseccion"]
        accion = decision["accion"]
        verde = decision["duracion_verde_segundos"]

        print(
            f"[CONTROL_SEMAFOROS] interseccion={interseccion} | "
            f"accion={accion} | duracion_verde={verde}s"
        )