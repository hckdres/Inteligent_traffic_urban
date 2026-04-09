from dataclasses import dataclass
from datetime import datetime
from src.enums.estado_semaforo import EstadoSemaforo

@dataclass
class Semaforo:
    id: str
    interseccionId: str
    estado: EstadoSemaforo
    duracionVerdeSegundos: int
    duracionRojoSegundos: int
    extensionSegundos: int = 0
    ultimoCambio: datetime = None

    def cambiarAVerde(self) -> None:
        self.estado = EstadoSemaforo.VERDE
        self.resetExtension()

    def cambiarARojo(self) -> None:
        self.estado = EstadoSemaforo.ROJO
        self.resetExtension()

    def extenderVerde(self, segundos: int) -> None:
        if self.estado == EstadoSemaforo.VERDE:
            self.extensionSegundos += segundos

    def aplicarComando(self, c: 'ComandoSemaforo') -> None:
        # Lógica para procesar el comando
        pass

    def getEstado(self) -> EstadoSemaforo:
        return self.estado

    def resetExtension(self) -> None:
        self.extensionSegundos = 0

