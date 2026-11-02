"""
Constantes do OTT Parsivel2: classes de diametro e velocidade e geometria
do sensor.

Valores copiados da tabela do manual (OTT Hydromet, 2016, Apendice C.1 e
Cap. 15), e nao gerados por formula, para bater 1:1 com o documento.
"""

import numpy as np

N_CLASSES = 32

# Diametro de cada classe: centro e largura, em mm.
DIAMETRO_CLASSES = np.array([
    0.062, 0.187, 0.312, 0.437, 0.562,
    0.687, 0.812, 0.937, 1.062, 1.187,
    1.375, 1.625, 1.875, 2.125, 2.375,
    2.750, 3.250, 3.750, 4.250, 4.750,
    5.500, 6.500, 7.500, 8.500, 9.500,
    11.000, 13.000, 15.000, 17.000, 19.000,
    21.500, 24.500,
])
LARGURA_DIAMETRO = np.array(
    [0.125] * 10 +
    [0.250] * 5 +
    [0.500] * 5 +
    [1.000] * 5 +
    [2.000] * 5 +
    [3.000] * 2
)

# Velocidade de cada classe: centro e largura, em m/s.
VELOCIDADE_CLASSES = np.array([
    0.050, 0.150, 0.250, 0.350, 0.450,
    0.550, 0.650, 0.750, 0.850, 0.950,
    1.100, 1.300, 1.500, 1.700, 1.900,
    2.200, 2.600, 3.000, 3.400, 3.800,
    4.400, 5.200, 6.000, 6.800, 7.600,
    8.800, 10.400, 12.000, 13.600, 15.200,
    17.600, 20.800,
])
LARGURA_VELOCIDADE = np.array(
    [0.100] * 10 +
    [0.200] * 5 +
    [0.400] * 5 +
    [0.800] * 5 +
    [1.600] * 5 +
    [3.200] * 2
)

# True nas classes de diametro que o sensor mede. As 2 primeiras ficam
# abaixo da faixa de medicao e nunca tem gota.
DIAMETRO_AVALIADO = np.arange(N_CLASSES) >= 2

# Faixa de luz por onde as gotas passam: 180 x 30 mm.
LARGURA_FAIXA_MM = 180.0
PROFUNDIDADE_FAIXA_MM = 30.0
AREA_MEDICAO_M2 = LARGURA_FAIXA_MM * PROFUNDIDADE_FAIXA_MM * 1e-6

# Valor do campo 90 (que e um log10) numa classe sem gota.
SENTINELA_SEM_DADO = -9.999
