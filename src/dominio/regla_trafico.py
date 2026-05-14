import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from src.enums.accion_semaforo import AccionSemaforo
from src.enums.estado_circulacion import EstadoCirculacion
from src.dominio.evento_trafico import EventoCamara, EventoEspira, EventoGPS

logger = logging.getLogger("Analitica")


@dataclass
class CondicionRegla:
    variable: str
    operador: str
    valor: Any

    def evaluar(self, contexto: Dict[str, Any]) -> bool:
        actual = contexto.get(self.variable)
        if actual is None:
            return False

        if self.operador == "==":
            return actual == self.valor
        if self.operador == "!=":
            return actual != self.valor
        if self.operador == ">":
            return actual > self.valor
        if self.operador == ">=":
            return actual >= self.valor
        if self.operador == "<":
            return actual < self.valor
        if self.operador == "<=":
            return actual <= self.valor
        return False

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
    condiciones_todas: List[CondicionRegla] = field(default_factory=list)
    condiciones_alguna: List[CondicionRegla] = field(default_factory=list)

    def evaluar(
        self,
        cam: 'EventoCamara',
        esp: 'EventoEspira',
        gps: 'EventoGPS',
        contexto: Optional[Dict[str, Any]] = None,
    ) -> bool:
        if not cam or not esp or not gps:
            return False

        contexto_regla = self._construir_contexto(cam, esp, gps, contexto)
        if not self.condiciones_todas and not self.condiciones_alguna:
            return False

        todas_ok = all(cond.evaluar(contexto_regla) for cond in self.condiciones_todas)
        alguna_ok = True if not self.condiciones_alguna else any(
            cond.evaluar(contexto_regla) for cond in self.condiciones_alguna
        )
        return todas_ok and alguna_ok

    def getEstadoResultado(self) -> EstadoCirculacion:
        return self.estadoResultado

    def getAccion(self) -> AccionSemaforo:
        return self.accion

    def getExtensionVerde(self) -> int:
        return self.extensionVerdeSegundos

    def validar(self) -> bool:
        return bool(self.reglaId and self.nombre)

    def _construir_contexto(
        self,
        cam: 'EventoCamara',
        esp: 'EventoEspira',
        gps: 'EventoGPS',
        contexto: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        contexto_regla = dict(contexto or {})
        contexto_regla.setdefault("cola", cam.getVolumen())
        contexto_regla.setdefault("velocidad_promedio", gps.getVelocidadPromedio())
        contexto_regla.setdefault("vehiculos_por_minuto", esp.getVehiculosPorMinuto())
        return contexto_regla

    @staticmethod
    def desde_dict(data: Dict[str, Any]) -> 'ReglaTrafico':
        res = data.get("resultado", {})
        
        # Intentamos mapear las condiciones dinámicas al modelo estricto UML
        cola, vel, den, vpm = 0, 0.0, 0.0, 0.0
        condiciones_todas = [
            CondicionRegla(
                variable=cond["variable"],
                operador=cond["operador"],
                valor=cond["valor"],
            )
            for cond in data.get("condiciones", {}).get("todas", [])
        ]
        condiciones_alguna = [
            CondicionRegla(
                variable=cond["variable"],
                operador=cond["operador"],
                valor=cond["valor"],
            )
            for cond in data.get("condiciones", {}).get("alguna", [])
        ]

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
            motivo=data["nombre"],
            condiciones_todas=condiciones_todas,
            condiciones_alguna=condiciones_alguna,
        )

def seleccionar_mejor_regla(
    reglas: list[ReglaTrafico],
    cam: EventoCamara,
    esp: EventoEspira,
    gps: EventoGPS,
    contexto: Optional[Dict[str, Any]] = None,
) -> ReglaTrafico | None:
    for regla in reglas:
        if regla.evaluar(cam, esp, gps, contexto):
            return regla
    return None
