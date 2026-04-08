from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


class ConfiguracionSistema:
    def __init__(self, ruta_config: str = "config/system.json") -> None:
        self.ruta_config = Path(ruta_config)
        self._config: Dict[str, Any] = {}

    def cargar(self) -> Dict[str, Any]:
        if not self.ruta_config.exists():
            raise FileNotFoundError(f"No existe el archivo de configuración: {self.ruta_config}")

        with self.ruta_config.open("r", encoding="utf-8") as archivo:
            self._config = json.load(archivo)

        self._validar_estructura_basica()
        return self._config

    def _validar_estructura_basica(self) -> None:
        campos_obligatorios = ["ciudad", "parametros_generales", "semaforos", "sensores"]
        for campo in campos_obligatorios:
            if campo not in self._config:
                raise ValueError(f"Falta el campo obligatorio '{campo}' en system.json")

        ciudad = self._config["ciudad"]
        if "intersecciones" not in ciudad or not isinstance(ciudad["intersecciones"], list):
            raise ValueError("La ciudad debe incluir una lista de intersecciones")

        if not self._config["sensores"]:
            raise ValueError("Debe existir al menos un sensor configurado")

    def obtener_config(self) -> Dict[str, Any]:
        return self._config

    def obtener_intersecciones(self) -> List[str]:
        return self._config.get("ciudad", {}).get("intersecciones", [])

    def obtener_sensores(self) -> List[Dict[str, Any]]:
        return self._config.get("sensores", [])

    def obtener_parametros_generales(self) -> Dict[str, Any]:
        return self._config.get("parametros_generales", {})


def cargar_configuracion(ruta_config: str = "config/system.json") -> Dict[str, Any]:
    return ConfiguracionSistema(ruta_config).cargar()