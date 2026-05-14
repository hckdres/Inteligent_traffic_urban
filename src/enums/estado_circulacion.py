from enum import Enum

class EstadoCirculacion(Enum):
    NORMAL = "NORMAL"
    CONGESTION = "CONGESTION"
    PRIORIZACION = "PRIORIZACION"
    SIN_CLASIFICAR = "SIN_CLASIFICAR"
