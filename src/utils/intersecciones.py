from __future__ import annotations

import re
from typing import Iterable, List, Tuple


_PATRON_INTERSECCION = re.compile(r"^([A-Za-z]+)(\d+)$")


def descomponer_interseccion(codigo: str) -> Tuple[str, int]:
    try:
        sufijo = codigo.split("-", 1)[1]
    except IndexError as exc:
        raise ValueError(f"Interseccion invalida: {codigo}") from exc

    match = _PATRON_INTERSECCION.fullmatch(sufijo)
    if not match:
        raise ValueError(f"Interseccion invalida: {codigo}")

    fila = match.group(1).upper()
    columna = int(match.group(2))
    if columna <= 0:
        raise ValueError(f"Interseccion invalida: {codigo}")
    return fila, columna


def fila_a_indice(fila: str) -> int:
    fila_normalizada = fila.strip().upper()
    if not fila_normalizada or not fila_normalizada.isalpha():
        raise ValueError(f"Fila invalida: {fila}")

    valor = 0
    for caracter in fila_normalizada:
        valor = valor * 26 + (ord(caracter) - ord("A") + 1)
    return valor


def clave_orden_interseccion(codigo: str) -> Tuple[int, int, str]:
    fila, columna = descomponer_interseccion(codigo)
    return fila_a_indice(fila), columna, codigo


def ordenar_intersecciones(codigos: Iterable[str]) -> List[str]:
    return sorted(codigos, key=clave_orden_interseccion)
