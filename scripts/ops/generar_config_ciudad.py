from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def _etiqueta_fila(indice: int) -> str:
    if indice <= 0:
        raise ValueError("El indice de fila debe ser positivo")

    valor = indice
    partes: List[str] = []
    while valor > 0:
        valor, resto = divmod(valor - 1, 26)
        partes.append(chr(ord("A") + resto))
    return "".join(reversed(partes))


def _codigo_interseccion(fila: int, columna: int, columnas_letras_filas_numericas: bool = False) -> str:
    if columnas_letras_filas_numericas:
        return f"INT-{_etiqueta_fila(columna)}{fila}"
    return f"INT-{_etiqueta_fila(fila)}{columna}"


def _generar_config(
    nombre: str,
    filas: int,
    columnas: int,
    intervalo_segundos: int,
    columnas_letras_filas_numericas: bool = False,
) -> Dict[str, Any]:
    intersecciones = [
        _codigo_interseccion(fila, columna, columnas_letras_filas_numericas)
        for fila in range(1, filas + 1)
        for columna in range(1, columnas + 1)
    ]

    semaforos = []
    sensores = []
    for fila in range(1, filas + 1):
        for columna in range(1, columnas + 1):
            codigo = _codigo_interseccion(fila, columna, columnas_letras_filas_numericas)
            sufijo = codigo.split("-", 1)[1]
            semaforos.append(
                {
                    "semaforo_id": f"SEM-{sufijo}",
                    "interseccion": codigo,
                    "estado_inicial": "VERDE" if (fila + columna) % 2 == 0 else "ROJO",
                    "duracion_verde_segundos": 15,
                }
            )
            for tipo_sensor, prefijo in (
                ("camara", "CAM"),
                ("espira_inductiva", "ESP"),
                ("gps", "GPS"),
            ):
                sensores.append(
                    {
                        "sensor_id": f"{prefijo}-{sufijo}",
                        "tipo_sensor": tipo_sensor,
                        "interseccion": codigo,
                        "intervalo_segundos": intervalo_segundos,
                        "modo": "archivo_json",
                    }
                )

    columna_central = max(1, (columnas + 1) // 2)
    via_central = [
        _codigo_interseccion(fila, columna_central, columnas_letras_filas_numericas)
        for fila in range(1, filas + 1)
    ]
    via_fila_1 = [
        _codigo_interseccion(1, columna, columnas_letras_filas_numericas)
        for columna in range(1, columnas + 1)
    ]
    via_diagonal = [
        _codigo_interseccion(fila, fila, columnas_letras_filas_numericas)
        for fila in range(1, min(filas, columnas) + 1)
    ]

    return {
        "ciudad": {
            "nombre": nombre,
            "filas": filas,
            "columnas": columnas,
            "intersecciones": intersecciones,
            "orientacion": (
                "COLUMNAS_LETRAS_FILAS_NUMERICAS"
                if columnas_letras_filas_numericas
                else "FILAS_LETRAS_COLUMNAS_NUMERICAS"
            ),
        },
        "parametros_generales": {
            "intervalo_normal_segundos": 10,
            "intervalo_congestion_segundos": 5,
            "duracion_verde_normal_segundos": 15,
            "extension_verde_congestion_segundos": 10,
            "extension_verde_prioridad_segundos": 20,
        },
        "semaforos": semaforos,
        "sensores": sensores,
        "vias_priorizables": [
            {
                "via_id": "VIA-CENTRAL",
                "intersecciones": via_central,
            },
            {
                "via_id": "VIA-FILA-1",
                "intersecciones": via_fila_1,
            },
            {
                "via_id": "VIA-DIAGONAL",
                "intersecciones": via_diagonal,
            },
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera una configuracion de ciudad parametrica.")
    parser.add_argument("--nombre", default="CiudadDemo", help="Nombre de la ciudad")
    parser.add_argument("--filas", type=int, default=3, help="Numero de filas")
    parser.add_argument("--columnas", type=int, default=5, help="Numero de columnas")
    parser.add_argument("--intervalo-sensores", type=int, default=2, help="Intervalo de los sensores en segundos")
    parser.add_argument(
        "--columnas-letras-filas-numericas",
        action="store_true",
        help="Genera codigos INT-A1 donde A es columna y 1 es fila.",
    )
    parser.add_argument("--salida", required=True, help="Ruta del archivo JSON a generar")
    args = parser.parse_args()

    if args.filas <= 0 or args.columnas <= 0:
        raise SystemExit("filas y columnas deben ser mayores que cero")

    config = _generar_config(
        args.nombre,
        args.filas,
        args.columnas,
        args.intervalo_sensores,
        args.columnas_letras_filas_numericas,
    )
    ruta = Path(args.salida)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] Configuracion generada en {ruta}")


if __name__ == "__main__":
    main()
