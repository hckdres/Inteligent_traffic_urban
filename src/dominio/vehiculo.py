from dataclasses import dataclass
from typing import Optional

@dataclass
class Vehiculo:
    id_vehiculo: str
    tipo: str
    velocidad_actual: float = 0.0
    ubicacion_actual: Optional[str] = None
