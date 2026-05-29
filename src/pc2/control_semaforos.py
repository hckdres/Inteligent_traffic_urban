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
        intersecciones_verdes = decision.get("intersecciones_afectadas") or [interseccion]
        intersecciones_rojas = [
            codigo
            for codigo in (decision.get("intersecciones_bloqueadas") or [])
            if codigo not in intersecciones_verdes
        ]

        with self._lock:
            cambios: list[str] = []
            for interseccion_actual in intersecciones_verdes:
                cambios.append(
                    self._actualizar_estado(
                        interseccion_actual,
                        "VERDE",
                        duracion,
                        estado_circulacion,
                        accion,
                        interseccion,
                    )
                )

            for interseccion_actual in intersecciones_rojas:
                cambios.append(
                    self._actualizar_estado(
                        interseccion_actual,
                        "ROJO",
                        duracion,
                        estado_circulacion,
                        "CAMBIAR_A_ROJO",
                        interseccion,
                    )
                )

        # Alerta visual si hay congestión severa
        alerta = " ALERTA_CONGESTION" if accion == "EXTENDER_VERDE_Y_GENERAR_ALERTA" else ""
        prioridad = " AMBULANCIA" if accion in ("OLA_VERDE", "PRIORIZAR_VIA") else ""
        corredor = decision.get("contexto", {}).get("modo_corredor")
        sufijo_corredor = f" | corredor={corredor}" if corredor else ""
        detalle_cambios = " | ".join(cambios)
        resumen_rojo = ", ".join(intersecciones_rojas) if intersecciones_rojas else "ninguna"
        resumen_verde = ", ".join(intersecciones_verdes)

        print(
            f"[{datetime.now(COLOMBIA_TZ).strftime('%H:%M:%S')}][SEMAFORO] {interseccion} | {detalle_cambios} | "
            f"verde=[{resumen_verde}] rojo=[{resumen_rojo}] | verde={duracion}s | "
            f"{estado_circulacion}{sufijo_corredor}{alerta}{prioridad}"
        )

    def _actualizar_estado(
        self,
        interseccion_actual: str,
        luz: str,
        duracion: int,
        estado_circulacion: str,
        accion: str,
        interseccion_origen: str,
    ) -> str:
        estado_anterior = self._estados.get(interseccion_actual, {}).get("luz", "DESCONOCIDO")
        self._estados[interseccion_actual] = {
            "luz": luz,
            "duracion_verde_segundos": duracion,
            "estado_circulacion": estado_circulacion,
            "accion": accion,
            "actualizado_en": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "corredor_origen": interseccion_origen,
        }
        return (
            f"{interseccion_actual}:{estado_anterior}->{luz}"
            if estado_anterior != luz
            else f"{interseccion_actual}:mantiene {luz}"
        )

    def obtener_estado(self, interseccion: str) -> Dict[str, Any]:
        with self._lock:
            return dict(self._estados.get(interseccion, {"luz": "DESCONOCIDO"}))

    def obtener_todos(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {k: dict(v) for k, v in self._estados.items()}
