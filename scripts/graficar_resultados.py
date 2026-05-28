from __future__ import annotations

from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt


# ============================================================
# VALORES TOMADOS DE TU TABLA
# ============================================================
datos = {
    "E1-Base": {
        "config": "1 sensor/tipo, 10s, broker simple",
        "eventos": 89,
        "tiempo": 0.004,
        "minimo": 0.003,
        "maximo": 0.006,
    },
    "E1-Multi": {
        "config": "1 sensor/tipo, 10s, broker multihilo",
        "eventos": 86,
        "tiempo": 0.005,
        "minimo": 0.004,
        "maximo": 0.006,
    },
    "E2-Base": {
        "config": "2 sensores/tipo, 5s, broker simple",
        "eventos": 156,
        "tiempo": 0.005,
        "minimo": 0.003,
        "maximo": 0.006,
    },
    "E2-Multi": {
        "config": "2 sensores/tipo, 5s, broker multihilo",
        "eventos": 251,
        "tiempo": 0.005,
        "minimo": 0.004,
        "maximo": 0.007,
    },
}
# ============================================================


def _anotar_barras(ax: plt.Axes, bars, fmt: str = "{:.0f}", offset: float = 0.0) -> None:
    for bar in bars:
        valor = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            valor + offset,
            fmt.format(valor),
            ha="center",
            va="bottom",
            fontsize=10,
        )


def main() -> None:
    etiquetas = list(datos.keys())
    eventos = [datos[e]["eventos"] for e in etiquetas]
    tiempos = [datos[e]["tiempo"] for e in etiquetas]
    minimos = [datos[e]["minimo"] for e in etiquetas]
    maximos = [datos[e]["maximo"] for e in etiquetas]

    colores = ["#378ADD", "#185FA5", "#EF9F27", "#BA7517"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Comparacion de Desempeno: Diseño Base vs Multihilo", fontsize=13)

    # Grafica 1: eventos almacenados
    bars1 = ax1.bar(etiquetas, eventos, color=colores, edgecolor="none", width=0.55)
    ax1.set_title("Eventos almacenados en 2 minutos", fontsize=11)
    ax1.set_ylabel("Cantidad de registros en BD")
    ax1.set_xlabel("Experimento")
    ax1.grid(axis="y", alpha=0.2)
    _anotar_barras(ax1, bars1, fmt="{:.0f}", offset=max(eventos) * 0.01)

    # Grafica 2: tiempo promedio con barras de error usando min/max
    yerr = [
        [tiempo - minimo for tiempo, minimo in zip(tiempos, minimos)],
        [maximo - tiempo for tiempo, maximo in zip(tiempos, maximos)],
    ]
    bars2 = ax2.bar(
        etiquetas,
        tiempos,
        color=colores,
        edgecolor="none",
        width=0.55,
        yerr=yerr,
        capsize=6,
        ecolor="#444444",
    )
    ax2.set_title("Tiempo de respuesta promedio", fontsize=11)
    ax2.set_ylabel("Segundos")
    ax2.set_xlabel("Experimento")
    ax2.grid(axis="y", alpha=0.2)
    for bar, val in zip(bars2, tiempos):
        ax2.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.0002,
            f"{val:.3f}s",
            ha="center",
            va="bottom",
            fontsize=10,
        )

    legend = [
        mpatches.Patch(color="#378ADD", label="E1 - 1 sensor/tipo, 10s, base"),
        mpatches.Patch(color="#185FA5", label="E1 - 1 sensor/tipo, 10s, multihilo"),
        mpatches.Patch(color="#EF9F27", label="E2 - 2 sensores/tipo, 5s, base"),
        mpatches.Patch(color="#BA7517", label="E2 - 2 sensores/tipo, 5s, multihilo"),
    ]
    fig.legend(handles=legend, loc="lower center", ncol=2, fontsize=9, bbox_to_anchor=(0.5, -0.02))

    plt.tight_layout()

    salida = Path("resultados_desempeno.png")
    plt.savefig(salida, dpi=150, bbox_inches="tight")
    print(f"Grafica guardada en {salida}")
    plt.show()


if __name__ == "__main__":
    main()
