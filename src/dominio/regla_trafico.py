from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ResultadoRegla:
    estado_circulacion: str
    accion: str
    duracion_verde_segundos: int


@dataclass
class ReglaTrafico:
    id: str
    nombre: str
    prioridad: int
    condiciones: Dict[str, Any]
    resultado: ResultadoRegla

    def evaluar(self, contexto: Dict[str, Any]) -> bool:
        if "todas" in self.condiciones:
            return all(self._evaluar_condicion(cond, contexto) for cond in self.condiciones["todas"])

        if "alguna" in self.condiciones:
            return any(self._evaluar_condicion(cond, contexto) for cond in self.condiciones["alguna"])

        return False

    def _evaluar_condicion(self, condicion: Dict[str, Any], contexto: Dict[str, Any]) -> bool:
        variable = condicion["variable"]
        operador = condicion["operador"]
        valor_esperado = condicion["valor"]
        valor_actual = contexto.get(variable)

        if valor_actual is None:
            return False

        if operador == "==":
            return valor_actual == valor_esperado
        if operador == "!=":
            return valor_actual != valor_esperado
        if operador == "<":
            return valor_actual < valor_esperado
        if operador == "<=":
            return valor_actual <= valor_esperado
        if operador == ">":
            return valor_actual > valor_esperado
        if operador == ">=":
            return valor_actual >= valor_esperado

        raise ValueError(f"Operador no soportado: {operador}")

    @staticmethod
    def desde_dict(data: Dict[str, Any]) -> "ReglaTrafico":
        resultado = ResultadoRegla(
            estado_circulacion=data["resultado"]["estado_circulacion"],
            accion=data["resultado"]["accion"],
            duracion_verde_segundos=data["resultado"]["duracion_verde_segundos"],
        )
        return ReglaTrafico(
            id=data["id"],
            nombre=data["nombre"],
            prioridad=data["prioridad"],
            condiciones=data["condiciones"],
            resultado=resultado,
        )


def seleccionar_mejor_regla(reglas: List[ReglaTrafico], contexto: Dict[str, Any]) -> Optional[ReglaTrafico]:
    reglas_ordenadas = sorted(reglas, key=lambda r: r.prioridad, reverse=True)
    for regla in reglas_ordenadas:
        if regla.evaluar(contexto):
            return regla
    return None