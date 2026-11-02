import copy
import io
from datetime import datetime, timedelta

import numpy as np
import pytest

import parsivelreader as pr

@pytest.fixture
def dados(registros):
    return pr.concatenar(list(registros.values()))


def test_so_o_evento_com_chuva_de_verdade(dados):
    eventos = pr.detectar_eventos(dados)
    assert len(eventos) == 1
    ev = eventos[0]
    assert ev["inicio"] == datetime(2026, 10, 8, 4, 8)
    assert ev["fim"] == datetime(2026, 10, 8, 4, 20)
    assert ev["n_registros_validos"] == 7
    # chuva do campo 01 x 120 s nas 7 leituras; o campo 24 (truncado) da quase o mesmo
    dentro = (dados["tempo"] >= ev["inicio"]) & (dados["tempo"] <= ev["fim"])
    assert ev["chuva_total_mm"] == pytest.approx(dados["intensidade_chuva"][dentro].sum() * 120 / 3600)
    assert ev["chuva_total_mm"] == pytest.approx(dados["chuva_absoluta"][dentro].sum(), abs=0.07)
    assert ev["intensidade_maxima"] == 49.645


def test_chuva_minima_zero_mantem_os_pequenos(dados):
    eventos = pr.detectar_eventos(dados, chuva_minima_mm=0)
    # 14/10 17:44 tem gotas, mas quase nada de chuva: so entra com chuva_minima_mm=0
    assert [e["inicio"] for e in eventos] == [
        datetime(2026, 10, 8, 4, 8),
        datetime(2026, 10, 14, 17, 44),
    ]


def test_campo_90_sem_matriz_nao_vira_evento(registros):
    # leitura com campo 90 indicando gota mas matriz 93 vazia (intervalos
    # misturados no XLink): nao pode virar evento
    falsa = copy.deepcopy(registros["20261008041600.txt"])
    falsa.raw = np.zeros((32, 32))
    dados = pr.concatenar([falsa])
    assert pr.detectar_eventos(dados, chuva_minima_mm=0) == []


def test_intervalo_maximo_junta_eventos(dados):
    eventos = pr.detectar_eventos(dados, chuva_minima_mm=0,
                                  intervalo_maximo=timedelta(days=30))
    assert len(eventos) == 1


@pytest.fixture
def graficos():
    pytest.importorskip("matplotlib")
    from parsivelreader import graficos
    return graficos


def _salva(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    assert buf.tell() > 1000


def test_graficos_devolvem_figuras_salvaveis(dados, graficos):
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt

    figs = [
        graficos.grafico_matriz(dados),
        graficos.grafico_dsd_media(dados),
        graficos.grafico_serie_temporal(dados),
        graficos.grafico_diagnostico(dados),
    ] + [fig for fig, _ in graficos.graficos_eventos(dados)]
    assert len(figs) == 5
    for fig in figs:
        assert isinstance(fig, Figure)
        _salva(fig)
    # nada fica aberto no pyplot (importante para uso em aplicativo)
    assert plt.get_fignums() == []


def test_graficos_sem_chuva(registros, graficos):
    dados = pr.concatenar([registros["20261021160000.txt"]])
    _salva(graficos.grafico_matriz(dados))
    _salva(graficos.grafico_dsd_media(dados))
    _salva(graficos.grafico_serie_temporal(dados))
    _salva(graficos.grafico_diagnostico(dados))
    assert graficos.graficos_eventos(dados) == []


def test_eixo_de_diametro_cortado_na_maior_gota(dados, graficos):
    ev = pr.detectar_eventos(dados)[0]
    fig = graficos.grafico_evento(dados, ev)
    ax_n = fig.axes[1]
    com_gota = (dados["N_d"][ev["indices"]] > pr.SENTINELA_SEM_DADO).any(axis=0)
    maior = pr.DIAMETRO_CLASSES[np.nonzero(com_gota)[0].max()]
    assert maior < ax_n.get_ylim()[1] <= maior + 3


def test_graficos_com_campos_novos(pasta_dados, graficos):
    from test_leitura import CAMPOS_NOVOS
    registros = [pr.ler_conteudo(arq.read_text() + CAMPOS_NOVOS, arq.name)
                 for arq in sorted((pasta_dados / "2026100804").glob("*.txt"))]
    dados = pr.concatenar(registros)
    assert np.all(dados["status_sensor"] == 1)
    _salva(graficos.grafico_serie_temporal(dados))
    _salva(graficos.grafico_diagnostico(dados))
