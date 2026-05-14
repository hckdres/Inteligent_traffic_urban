from dataclasses import dataclass
from src.enums.estado_circulacion import EstadoCirculacion

@dataclass
class Interseccion:
    id: str
    fila: str
    columna: int
    estadoCirculacion: EstadoCirculacion = EstadoCirculacion.SIN_CLASIFICAR

    def actualizarEstado(self, e: EstadoCirculacion) -> None:
        self.estadoCirculacion = e

    def obtenerEstado(self) -> EstadoCirculacion:
        return self.estadoCirculacion

    def getId(self) -> str:
        return self.id

