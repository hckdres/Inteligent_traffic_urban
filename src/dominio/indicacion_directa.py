from dataclasses import dataclass
from datetime import datetime

@dataclass
class IndicacionDirecta:
    indicacionId: str
    interseccionId: str
    tipo: str
    motivo: str
    timestamp: datetime

    def validar(self) -> bool:
        return bool(self.indicacionId and self.interseccionId and self.tipo)

    def serializar(self) -> str:
        return "" # Implementación JSON a futuro

    def generarComando(self) -> 'ComandoSemaforo':
        pass

