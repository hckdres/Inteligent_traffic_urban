import logging
from dataclasses import dataclass
from typing import Dict, Any
from src.enums.accion_semaforo import AccionSemaforo
from src.enums.estado_circulacion import EstadoCirculacion
from src.dominio.evento_trafico import EventoCamara, EventoEspira, EventoGPS

logger = logging.getLogger("Analitica")

@dataclass
class ReglaTrafico:
    reglaId: str
    nombre: str
    umbralCola: int
    umbralVelocidad: float
    umbralDensidad: float
    umbralVehiculosPorMinuto: float
    estadoResultado: EstadoCirculacion
    accion: AccionSemaforo
    extensionVerdeSegundos: int
    motivo: str

    def evaluar(self, cam: 'EventoCamara', esp: 'EventoEspira', gps: 'EventoGPS') -> bool:
        if not cam or not esp or not gps:
            return False

        # Extraemos la heurística actual de congestion según el YAML preexistente
        cola_ok = cam.getVolumen() >= self.umbralCola if self.umbralCola > 0 else True
        vel_ok = gps.getVelocidadPromedio() <= self.umbralVelocidad if self.umbralVelocidad > 0 else True
        
        # Para simplificar la compatibilidad con el engine antiguo que era generico:
        return cola_ok and vel_ok

    def getEstadoResultado(self) -> EstadoCirculacion:
        return self.estadoResultado

    def getAccion(self) -> AccionSemaforo:
        return self.accion

    def getExtensionVerde(self) -> int:
        return self.extensionVerdeSegundos

    def validar(self) -> bool:
        return bool(self.reglaId and self.nombre)

    @staticmethod
    def desde_dict(data: Dict[str, Any]) -> 'ReglaTrafico':
        res = data.get("resultado", {})
        
        # Intentamos mapear las condiciones dinámicas al modelo estricto UML
        cola, vel, den, vpm = 0, 0.0, 0.0, 0.0
        for cond in data.get("condiciones", {}).get("todas", []) + data.get("condiciones", {}).get("alguna", []):
            if cond["variable"] == "cola": cola = int(cond["valor"])
            elif cond["variable"] == "velocidad_promedio": vel = float(cond["valor"])
            elif cond["variable"] == "densidad": den = float(cond["valor"])

        return ReglaTrafico(
            reglaId=data["id"],
            nombre=data["nombre"],
            umbralCola=cola,
            umbralVelocidad=vel,
            umbralDensidad=den,
            umbralVehiculosPorMinuto=vpm,
            estadoResultado=EstadoCirculacion(res.get("estado_circulacion", "NORMAL")),
            accion=AccionSemaforo(res.get("accion", "SIN_ACCION")) if res.get("accion") in AccionSemaforo.__members__ else AccionSemaforo.MANTENER_TEMPORIZACION,
            extensionVerdeSegundos=res.get("duracion_verde_segundos", 15),
            motivo=data["nombre"]
        )

def seleccionar_mejor_regla(reglas: list[ReglaTrafico], cam: EventoCamara, esp: EventoEspira, gps: EventoGPS) -> ReglaTrafico | None:
    for regla in reglas:
        if regla.evaluar(cam, esp, gps):
            return regla
    return None