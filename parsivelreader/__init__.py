"""
parsivelreader -- leitura e analise dos dados do disdrometro OTT Parsivel2
gravados pelo XLink 500.

    import parsivelreader as pr

    registros = pr.ler_zip("SD.zip")
    dados = pr.concatenar(registros)
    eventos = pr.detectar_eventos(dados)

Os graficos ficam em parsivelreader.graficos (precisa do matplotlib:
pip install parsivelreader[graficos]) e devolvem figuras prontas para
salvar: graficos.grafico_serie_temporal(dados).savefig("serie.png").
"""

from .classes import (
    AREA_MEDICAO_M2,
    DIAMETRO_AVALIADO,
    DIAMETRO_CLASSES,
    LARGURA_DIAMETRO,
    LARGURA_VELOCIDADE,
    N_CLASSES,
    SENTINELA_SEM_DADO,
    VELOCIDADE_CLASSES,
)
from .calculos import (
    chuva_por_leitura,
    diametro_medio_massa,
    espectro_linear,
    velocidade_terminal,
)
from .eventos import detectar_eventos
from .leitura import (
    RegistroParsivel,
    concatenar,
    eh_arquivo_parsivel,
    ler_arquivo,
    ler_conteudo,
    ler_pasta,
    ler_zip,
)

__version__ = "0.2.0"
