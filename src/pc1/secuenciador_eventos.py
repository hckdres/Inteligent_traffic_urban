from __future__ import annotations

import atexit
import os
import threading
import time
from pathlib import Path


class SecuenciadorEventos:
    def __init__(
        self,
        ruta_estado: str = "data/pc1_event_seq.txt",
        inicio: int = 1,
        persistir_cada: int = 50,
    ) -> None:
        self._ruta_estado = Path(ruta_estado)
        self._ruta_estado.parent.mkdir(parents=True, exist_ok=True)
        self._siguiente = self._cargar_siguiente(inicio)
        self._persistir_cada = max(1, persistir_cada)
        self._pendientes = 0
        self._lock = threading.Lock()
        atexit.register(self.flush)

    def siguiente(self) -> int:
        with self._lock:
            seq = self._siguiente
            self._siguiente += 1
            self._pendientes += 1
            if self._pendientes >= self._persistir_cada:
                self._guardar_siguiente()
            return seq

    def flush(self) -> None:
        with self._lock:
            self._guardar_siguiente()

    def _cargar_siguiente(self, inicio: int) -> int:
        if not self._ruta_estado.exists():
            return inicio
        try:
            valor = int(self._ruta_estado.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            return inicio
        return valor if valor > 0 else inicio

    def _guardar_siguiente(self) -> None:
        if self._pendientes == 0:
            return

        temporal = self._ruta_estado.with_name(
            f"{self._ruta_estado.stem}.{os.getpid()}.tmp"
        )
        for _ in range(3):
            try:
                temporal.write_text(str(self._siguiente), encoding="utf-8")
                temporal.replace(self._ruta_estado)
                self._pendientes = 0
                return
            except PermissionError:
                time.sleep(0.05)
            except OSError:
                break

        try:
            self._ruta_estado.write_text(str(self._siguiente), encoding="utf-8")
            self._pendientes = 0
        except OSError as exc:
            print(f"[PC1][WARN] no se pudo persistir secuencia: {exc}")
