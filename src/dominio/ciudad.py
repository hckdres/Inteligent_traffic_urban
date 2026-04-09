from dataclasses import dataclass, field
from typing import List, Dict, Any
from src.dominio.interseccion import Interseccion

@dataclass
class Ciudad:
    filas: int
    columnas: int
    intersecciones: Dict[str, Interseccion] = field(default_factory=dict)
    
    def agregarInterseccion(self, i: Interseccion) -> None:
        self.intersecciones[i.getId()] = i

    def obtenerInterseccion(self, id: str) -> Interseccion | None:
        return self.intersecciones.get(id)

    def listarIntersecciones(self) -> List[Interseccion]:
        return list(self.intersecciones.values())

    def obtenerSensoresDeInterseccion(self, id: str) -> List[Any]:
        # Pendiente implementar relación con Sensores según diagrama
        return []

    def toString(self) -> str:
        return f"Ciudad(filas={self.filas}, columnas={self.columnas}, intersecciones={len(self.intersecciones)})"

