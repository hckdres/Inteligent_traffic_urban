from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any, Dict

from src.utils.timezones import COLOMBIA_TZ


class ControlSemaforos:
    """Simula el estado de los semáforos por intersección y aplica decisiones de analítica."""

    ACCIONES_A_ESTADO = {
        "MANTENER_TEMPORIZACION": "VERDE",
        "RESTAURAR_TEMPORIZACION": "VERDE",
        "EXTENDER_VERDE": "VERDE",
        "EXTENDER_VERDE_Y_GENERAR_ALERTA": "VERDE",
        "OLA_VERDE": "VERDE",
        "PRIORIZAR_VIA": "VERDE",
        "CAMBIAR_A_VERDE": "VERDE",
        "CAMBIAR_A_ROJO": "ROJO",
    }

    def __init__(self) -> None:
        self._estados: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def aplicar_accion(self, decision: Dict[str, Any]) -> None:
        interseccion = decision["interseccion"]
        accion = decision["accion"]
        duracion = decision["duracion_verde_segundos"]
        estado_circulacion = decision.get("estado_circulacion", "DESCONOCIDO")
        intersecciones_objetivo = decision.get("intersecciones_afectadas") or [interseccion]

        nuevo_estado = self.ACCIONES_A_ESTADO.get(accion, "VERDE")

        with self._lock:
            cambios: list[str] = []
            for interseccion_actual in intersecciones_objetivo:
                estado_anterior = self._estados.get(interseccion_actual, {}).get("luz", "DESCONOCIDO")
                self._estados[interseccion_actual] = {
                    "luz": nuevo_estado,
                    "duracion_verde_segundos": duracion,
                    "estado_circulacion": estado_circulacion,
                    "accion": accion,
                    "actualizado_en": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "corredor_origen": interseccion,
                }
                cambio = (
                    f"{interseccion_actual}:{estado_anterior}->{nuevo_estado}"
                    if estado_anterior != nuevo_estado
                    else f"{interseccion_actual}:mantiene {nuevo_estado}"
                )
                cambios.append(cambio)

        # Alerta visual si hay congestión severa
        alerta = " ALERTA_CONGESTION" if accion == "EXTENDER_VERDE_Y_GENERAR_ALERTA" else ""
        prioridad = " AMBULANCIA" if accion in ("OLA_VERDE", "PRIORIZAR_VIA") else ""
        corredor = decision.get("contexto", {}).get("modo_corredor")
        sufijo_corredor = f" | corredor={corredor}" if corredor else ""
        detalle_cambios = " | ".join(cambios)

        print(
            f"[{datetime.now(COLOMBIA_TZ).strftime('%H:%M:%S')}][SEMAFORO] {interseccion} | {detalle_cambios} | "
            f"verde={duracion}s | {estado_circulacion}{sufijo_corredor}{alerta}{prioridad}"
        )

    def obtener_estado(self, interseccion: str) -> Dict[str, Any]:
        with self._lock:
            return dict(self._estados.get(interseccion, {"luz": "DESCONOCIDO"}))

    def obtener_todos(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {k: dict(v) for k, v in self._estados.items()}
