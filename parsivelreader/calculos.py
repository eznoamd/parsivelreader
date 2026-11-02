"""
Os poucos calculos que os graficos precisam. Tudo o que o Parsivel ja
entrega pronto (intensidade 01, refletividade 07, energia cinetica 34,
espectro 90 etc.) vem direto dos campos lidos; aqui fica so o que o sensor
nao da:

    velocidade_terminal   curva de referencia no grafico da matriz
    espectro_linear       campo 90 (log10) -> N(D) linear, para tirar medias
    diametro_medio_massa  Dm, a partir do campo 90
    chuva_por_leitura     mm de chuva em cada leitura, para acumular

Unidades: D em mm, N(D) em 1/(m3 mm), chuva em mm.
"""

from __future__ import annotations

import numpy as np

from .classes import DIAMETRO_AVALIADO, DIAMETRO_CLASSES, LARGURA_DIAMETRO, SENTINELA_SEM_DADO


def velocidade_terminal(D: np.ndarray = DIAMETRO_CLASSES) -> np.ndarray:
    """Velocidade de queda esperada de uma gota de chuva (m/s).

        v(D) = 9.65 - 10.3 exp(-0.6 D)      (Atlas et al., 1973)
    """
    return 9.65 - 10.3 * np.exp(-0.6 * D)


def espectro_linear(N_d: np.ndarray) -> np.ndarray:
    """Campo 90 (log10 de N(D)) em N(D) linear, 1/(m3 mm), com 0 nas classes
    sem gota (-9.999) e nas que o sensor nao avalia. (32,) ou (N, 32)."""
    N_d = np.asarray(N_d, dtype=float)
    com_gota = (N_d > SENTINELA_SEM_DADO) & DIAMETRO_AVALIADO
    return np.where(com_gota, 10.0 ** np.where(com_gota, N_d, 0), 0.0)


def diametro_medio_massa(N_d: np.ndarray) -> np.ndarray:
    """Diametro medio ponderado pela massa, em mm, a partir do campo 90:

        Dm = M4 / M3,   Mk = sum_i N(D_i) D_i^k dD_i

    NaN nas leituras sem gota."""
    N = espectro_linear(N_d)
    m3 = (N * DIAMETRO_CLASSES**3 * LARGURA_DIAMETRO).sum(axis=-1)
    m4 = (N * DIAMETRO_CLASSES**4 * LARGURA_DIAMETRO).sum(axis=-1)
    return np.where(m3 > 0, m4 / np.where(m3 > 0, m3, 1), np.nan)


def chuva_por_leitura(dados: dict) -> np.ndarray:
    """Chuva de cada leitura, em mm: intensidade (01) x duracao (09) / 3600.

    O campo 24 traz o mesmo valor, mas truncado em 0.01 mm: somado num mes
    de dados perde ~4% da chuva (out/2026), por isso nao e usado aqui.
    Leituras sem o 01 contam como 0."""
    return np.nan_to_num(dados["intensidade_chuva"] * dados["intervalo"] / 3600)
