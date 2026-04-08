from __future__ import annotations

from src.pc2.servicio_analitica import ServicioAnalitica


def main() -> None:
    servicio = ServicioAnalitica()
    servicio.escuchar_eventos()


if __name__ == "__main__":
    main()