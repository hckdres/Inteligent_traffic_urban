from __future__ import annotations

import logging
import os
import queue
import threading
from typing import Any, Dict
from datetime import datetime
from pathlib import Path

import zmq

from src.utils.timezones import COLOMBIA_TZ

PRIMARY_PERSIST_ENDPOINT = "tcp://127.0.0.1:5561"
REPLICA_PERSIST_ENDPOINT = "tcp://127.0.0.1:5560"
MAX_PENDIENTES_DEFAULT = 5000

logger = logging.getLogger("pc2_persistencia")


class GestorFailover:
    def __init__(self) -> None:
        if not logger.handlers:
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            file_handler = logging.FileHandler(log_dir / "pc2_persistencia.log", encoding="utf-8")
            file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
            logger.addHandler(file_handler)
            logger.setLevel(logging.INFO)

        self.context = zmq.Context.instance()

        # Socket hacia PRIMARY con timeout para no bloquear
        self.push_primary = self.context.socket(zmq.PUSH)
        self.push_primary.setsockopt(zmq.SNDTIMEO, 1500)
        self.push_primary.setsockopt(zmq.LINGER, 0)
        self.push_primary.connect(PRIMARY_PERSIST_ENDPOINT)

        # Socket hacia REPLICA (conectamos con timeout para seguridad)
        self.push_replica = self.context.socket(zmq.PUSH)
        self.push_replica.setsockopt(zmq.SNDTIMEO, 1000)
        self.push_replica.setsockopt(zmq.LINGER, 0)
        self.push_replica.connect(REPLICA_PERSIST_ENDPOINT)

        max_pendientes = int(os.getenv("PC2_MAX_PENDIENTES", str(MAX_PENDIENTES_DEFAULT)))
        if max_pendientes <= 0:
            max_pendientes = MAX_PENDIENTES_DEFAULT

        self.primary_disponible = True
        self._lock = threading.Lock()  # Protege primary_disponible ante accesos concurrentes
        self._cola_pendientes: queue.Queue[Dict[str, Any]] = queue.Queue(maxsize=max_pendientes)
        self._mensajes_descartados = 0

        # Hilo dedicado para envíos a PRIMARY — nunca bloquea al hilo de analítica
        self._hilo_primary = threading.Thread(target=self._worker_primary, daemon=True)
        self._hilo_primary.start()

    # ------------------------------------------------------------------ #
    # API pública                                                          #
    # ------------------------------------------------------------------ #

    def actualizar_estado_primaria(self, disponible: bool) -> None:
        """Llamado desde HealthCheckPC3 (hilo externo) cuando cambia el estado de PC3."""
        with self._lock:
            if self.primary_disponible == disponible:
                return
            self.primary_disponible = disponible

        tipo = "RETURN_TO_PRIMARY" if disponible else "SWITCH_TO_REPLICA"
        estado_str = "DISPONIBLE" if disponible else "CAÍDO — usando RÉPLICA"
        hora = datetime.now(COLOMBIA_TZ).strftime("%H:%M:%S")
        print(f"[{hora}][FAILOVER] PC3 {estado_str}")

        # Registrar el evento de failover en ambas BDs
        evento_failover = {
            "tipo": "registrar_failover",
            "payload": {
                "tipo_evento": tipo,
                "nodo_origen": "PC2",
                "descripcion": "Cambio automático de destino de persistencia",
            },
        }
        self._enviar_replica(evento_failover)
        self._encolar_para_primary(evento_failover, critico=True)

    def persistir_decision(self, decision: Dict[str, Any]) -> None:
        """Persiste en REPLICA de forma inmediata y encola para PRIMARY (no bloquea)."""
        mensaje = {"tipo": "guardar_decision", "payload": decision}
        self._enviar_replica(mensaje)
        self._encolar_para_primary(mensaje, critico=True)

    def registrar_solicitud(self, solicitud: Dict[str, Any]) -> None:
        """Registra solicitud de usuario en ambas BDs."""
        mensaje = {"tipo": "guardar_solicitud", "payload": solicitud}
        self._enviar_replica(mensaje)
        self._encolar_para_primary(mensaje, critico=True)

    def persistir_evento_sensor(self, evento: Dict[str, Any]) -> None:
        """Persiste eventos crudos de sensores en ambas BDs."""
        mensaje = {"tipo": "guardar_evento_sensor", "payload": evento}
        self._enviar_replica(mensaje)
        self._encolar_para_primary(mensaje, critico=False)

    # ------------------------------------------------------------------ #
    # Internos                                                             #
    # ------------------------------------------------------------------ #

    def _worker_primary(self) -> None:
        """Hilo dedicado que consume la cola y envía a PRIMARY cuando está disponible.
        Al estar separado del hilo de analítica, un timeout en PRIMARY nunca
        retrasa el procesamiento de eventos de tráfico."""
        while True:
            mensaje = self._cola_pendientes.get()  # bloquea hasta haber algo
            while True:
                with self._lock:
                    disponible = self.primary_disponible
                if not disponible:
                    import time
                    time.sleep(1)
                    continue
                try:
                    self.push_primary.send_json(mensaje)
                    logger.info("[PRIMARY] %s", mensaje["tipo"])
                    break
                except zmq.ZMQError as exc:
                    logger.warning("[PRIMARY] error enviando %s: %s", mensaje["tipo"], exc)
                    self.actualizar_estado_primaria(False)

    def _encolar_para_primary(self, mensaje: Dict[str, Any], critico: bool) -> None:
        """Evita crecimiento sin límite en memoria cuando PRIMARY está caído/lento."""
        try:
            if critico:
                self._cola_pendientes.put(mensaje, timeout=0.5)
            else:
                self._cola_pendientes.put_nowait(mensaje)
        except queue.Full:
            self._mensajes_descartados += 1
            tipo = mensaje.get("tipo", "desconocido")
            if critico:
                logger.error(
                    "[PRIMARY] cola llena (%s). Mensaje crítico descartado tipo=%s descartados=%s",
                    self._cola_pendientes.maxsize,
                    tipo,
                    self._mensajes_descartados,
                )
            else:
                logger.warning(
                    "[PRIMARY] cola llena (%s). Evento no crítico descartado tipo=%s descartados=%s",
                    self._cola_pendientes.maxsize,
                    tipo,
                    self._mensajes_descartados,
                )

    def _enviar_replica(self, mensaje: Dict[str, Any]) -> None:
        try:
            self.push_replica.send_json(mensaje)
            logger.info("[REPLICA] %s", mensaje["tipo"])
        except zmq.ZMQError as exc:
            print(f"[FAILOVER] Error crítico: No se pudo persistir en RÉPLICA local (timeout/bloqueo): {exc}")
