import json
from dataclasses import dataclass
from datetime import datetime
from src.enums.tipo_sensor import TipoSensor
from src.enums.nivel_congestion import NivelCongestion

@dataclass
class EventoTrafico:
    eventoId: str
    sensorId: str
    interseccionId: str
    tipoSensor: TipoSensor
    timestamp: datetime

    def validar(self) -> bool:
        return bool(self.eventoId and self.sensorId and self.interseccionId)

    def serializar(self) -> str:
        from dataclasses import asdict
        from enum import Enum
        
        d = asdict(self)
        d['__class__'] = self.__class__.__name__
        
        # Format types
        for k, v in d.items():
            if isinstance(v, Enum):
                d[k] = v.value
            elif isinstance(v, datetime):
                d[k] = v.isoformat()
        return json.dumps(d)

    @staticmethod
    def deserializar(json_str: str) -> 'EventoTrafico':
        from src.enums.nivel_congestion import NivelCongestion
        
        d = json.loads(json_str)
        cls_name = d.pop('__class__', 'EventoTrafico')
        
        # Parse common types
        d['tipoSensor'] = TipoSensor(d['tipoSensor']) if 'tipoSensor' in d and d['tipoSensor'] else d.get('tipoSensor')
        if 'timestamp' in d and d['timestamp']: d['timestamp'] = datetime.fromisoformat(d['timestamp'])
        if 'timestampInicio' in d and d['timestampInicio']: d['timestampInicio'] = datetime.fromisoformat(d['timestampInicio'])
        if 'timestampFin' in d and d['timestampFin']: d['timestampFin'] = datetime.fromisoformat(d['timestampFin'])
        if 'nivelCongestion' in d and d['nivelCongestion']: d['nivelCongestion'] = NivelCongestion(d['nivelCongestion'])
        
        if cls_name == 'EventoCamara':
            return EventoCamara(**d)
        elif cls_name == 'EventoEspira':
            return EventoEspira(**d)
        elif cls_name == 'EventoGPS':
            return EventoGPS(**d)
        return EventoTrafico(**d)


@dataclass
class EventoCamara(EventoTrafico):
    volumen: int = 0
    velocidadPromedio: float = 0.0
    
    def getVolumen(self) -> int:
        return self.volumen
        
    def getVelocidadPromedio(self) -> float:
        return self.velocidadPromedio

@dataclass
class EventoEspira(EventoTrafico):
    vehiculosContados: int = 0
    intervaloSegundos: int = 0
    timestampInicio: datetime = None
    timestampFin: datetime = None

    def getVehiculosPorMinuto(self) -> float:
        if self.intervaloSegundos == 0: return 0.0
        return (self.vehiculosContados / self.intervaloSegundos) * 60.0

@dataclass
class EventoGPS(EventoTrafico):
    velocidadPromedio: float = 0.0
    nivelCongestion: NivelCongestion = NivelCongestion.NORMAL

    def getVelocidadPromedio(self) -> float:
        return self.velocidadPromedio
        
    def getNivelCongestion(self) -> NivelCongestion:
        return self.nivelCongestion

