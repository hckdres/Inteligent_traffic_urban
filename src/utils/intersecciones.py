from __future__ import annotations

import re
from typing import Any, Iterable, List, Tuple


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


def indice_a_letras(indice: int) -> str:
    if indice <= 0:
        raise ValueError(f"Indice invalido: {indice}")

    valor = indice
    partes: List[str] = []
    while valor > 0:
        valor, resto = divmod(valor - 1, 26)
        partes.append(chr(ord("A") + resto))
    return "".join(reversed(partes))


def ciudad_usa_columnas_letras(ciudad: dict[str, Any] | None) -> bool:
    if not ciudad:
        return False
    orientacion = str(ciudad.get("orientacion", "")).strip().upper()
    return orientacion in {
        "COLUMNAS_LETRAS_FILAS_NUMERICAS",
        "COLUMNAS_LETRAS_FILAS_NUMEROS",
        "LETRAS_COLUMNAS_NUMEROS_FILAS",
    }


def posicion_en_ciudad(codigo: str, ciudad: dict[str, Any] | None = None) -> Tuple[int, int]:
    letras, numero = descomponer_interseccion(codigo)
    if ciudad_usa_columnas_letras(ciudad):
        return numero, fila_a_indice(letras)
    return fila_a_indice(letras), numero


def etiqueta_fila(indice: int, ciudad: dict[str, Any] | None = None) -> str:
    if ciudad_usa_columnas_letras(ciudad):
        return str(indice)
    return indice_a_letras(indice)


def etiqueta_columna(indice: int, ciudad: dict[str, Any] | None = None) -> str:
    if ciudad_usa_columnas_letras(ciudad):
        return indice_a_letras(indice)
    return str(indice)


def clave_orden_interseccion(codigo: str) -> Tuple[int, int, str]:
    fila, columna = descomponer_interseccion(codigo)
    return fila_a_indice(fila), columna, codigo


def clave_orden_ciudad(codigo: str, ciudad: dict[str, Any] | None = None) -> Tuple[int, int, str]:
    fila, columna = posicion_en_ciudad(codigo, ciudad)
    return fila, columna, codigo


def ordenar_intersecciones(codigos: Iterable[str]) -> List[str]:
    return sorted(codigos, key=clave_orden_interseccion)


def ordenar_intersecciones_ciudad(
    codigos: Iterable[str], ciudad: dict[str, Any] | None = None
) -> List[str]:
    return sorted(codigos, key=lambda codigo: clave_orden_ciudad(codigo, ciudad))
