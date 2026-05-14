from dataclasses import dataclass
from datetime import datetime
from src.enums.accion_semaforo import AccionSemaforo

@dataclass
class ComandoSemaforo:
    comandoId: str
    interseccionId: str
    accion: AccionSemaforo
    motivo: str
    extensionSegundos: int
    timestamp: datetime

    def validar(self) -> bool:
        return bool(self.comandoId and self.interseccionId)

    def serializar(self) -> str:
        import json
        from dataclasses import asdict
        d = asdict(self)
        d['accion'] = self.accion.value
        d['timestamp'] = self.timestamp.isoformat()
        return json.dumps(d)

    @staticmethod
    def deserializar(json_str: str) -> 'ComandoSemaforo':
        import json
        d = json.loads(json_str)
        d['accion'] = AccionSemaforo(d['accion'])
        d['timestamp'] = datetime.fromisoformat(d['timestamp'])
        return ComandoSemaforo(**d)


