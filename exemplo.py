#!/usr/bin/env python3
"""
Exemplo de uso: le o ZIP do SD e salva os graficos.

    python3 exemplo.py CAMINHO_DO_ZIP_DO_SD [PASTA_SAIDA]
"""

import sys
from pathlib import Path

import parsivelreader as pr
from parsivelreader import graficos


def main():
    if len(sys.argv) not in (2, 3):
        print("Uso: python3 exemplo.py CAMINHO_DO_ZIP_DO_SD [PASTA_SAIDA]")
        sys.exit(1)
    saida = Path(sys.argv[2] if len(sys.argv) == 3 else "graficos")
    (saida / "eventos").mkdir(parents=True, exist_ok=True)

    registros = pr.ler_zip(sys.argv[1])
    dados = pr.concatenar(registros)
    print(f"{len(registros)} arquivos lidos, {len(dados['tempo'])} validos "
          f"({dados['descartados']} descartados por estarem incompletos).")
    if len(dados["tempo"]) == 0:
        return

    eventos = pr.detectar_eventos(dados)
    graficos.grafico_matriz(dados).savefig(saida / "matriz.png", dpi=120)
    graficos.grafico_dsd_media(dados).savefig(saida / "dsd_media.png", dpi=120)
    graficos.grafico_serie_temporal(dados, eventos).savefig(saida / "serie_temporal.png", dpi=120)
    graficos.grafico_diagnostico(dados).savefig(saida / "diagnostico.png", dpi=120)

    print(f"{len(eventos)} evento(s) de chuva:")
    for ev in eventos:
        nome = f"evento_{ev['inicio']:%Y%m%d_%H%M}.png"
        graficos.grafico_evento(dados, ev).savefig(saida / "eventos" / nome, dpi=110)
        print(f"  {ev['inicio']:%d/%m %H:%M} - {ev['fim']:%d/%m %H:%M}: "
              f"{ev['chuva_total_mm']:.1f} mm, maxima {ev['intensidade_maxima']:.1f} mm/h")
    print(f"Graficos salvos em {saida}/")


if __name__ == "__main__":
    main()
