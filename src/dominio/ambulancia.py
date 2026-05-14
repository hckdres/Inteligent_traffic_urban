from dataclasses import dataclass
from src.dominio.vehiculo import Vehiculo

@dataclass
class Ambulancia(Vehiculo):
    en_emergencia: bool = False
    
    def __init__(self, id_vehiculo: str, velocidad_actual: float = 0.0, ubicacion_actual: str = None, en_emergencia: bool = False):
        super().__init__(id_vehiculo=id_vehiculo, tipo="AMBULANCIA", velocidad_actual=velocidad_actual, ubicacion_actual=ubicacion_actual)
        self.en_emergencia = en_emergencia
