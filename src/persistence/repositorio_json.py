from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


class RepositorioJSON:
    def __init__(
        self,
        ruta_eventos: str = "data/events_sensores.json",
        ruta_indicaciones: str = "data/indicaciones_directas.json",
    ) -> None:
        self.ruta_eventos = Path(ruta_eventos)
        self.ruta_indicaciones = Path(ruta_indicaciones)

    def cargar_eventos_sensores(self) -> List[Dict[str, Any]]:
        return self._cargar_lista_json(self.ruta_eventos)

    def cargar_indicaciones_directas(self) -> List[Dict[str, Any]]:
        return self._cargar_lista_json(self.ruta_indicaciones)

    def filtrar_eventos_por_sensor(self, sensor_id: str) -> List[Dict[str, Any]]:
        eventos = self.cargar_eventos_sensores()
        return [evento for evento in eventos if evento.get("sensor_id") == sensor_id]

    def filtrar_eventos_por_interseccion(self, interseccion: str) -> List[Dict[str, Any]]:
        eventos = self.cargar_eventos_sensores()
        return [evento for evento in eventos if evento.get("interseccion") == interseccion]

    def _cargar_lista_json(self, ruta: Path) -> List[Dict[str, Any]]:
        if not ruta.exists():
            raise FileNotFoundError(f"No existe el archivo JSON: {ruta}")

        with ruta.open("r", encoding="utf-8") as archivo:
            contenido = json.load(archivo)

        if not isinstance(contenido, list):
            raise ValueError(f"El archivo {ruta} debe contener una lista JSON")

        return contenido