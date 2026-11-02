"""Testes dos calculos que os graficos usam: contra os proprios campos do
sensor (gabarito) e contra casos analiticos."""

import numpy as np
import pytest

import parsivelreader as pr

CHUVA = [f"20261008{h}.txt" for h in
         ("040800", "041000", "041200", "041400", "041600", "041800", "042000")]


@pytest.fixture
def chuva(registros):
    return [registros[nome] for nome in CHUVA]


def test_espectro_linear_desfaz_o_log_do_campo_90(chuva):
    for r in chuva:
        N = pr.espectro_linear(r.N_d)
        com_gota = r.N_d > pr.SENTINELA_SEM_DADO
        np.testing.assert_allclose(np.log10(N[com_gota]), r.N_d[com_gota])
        assert np.all(N[~com_gota] == 0)


def test_espectro_linear_ignora_classes_nao_avaliadas():
    N_d = np.full(32, 2.0)
    N = pr.espectro_linear(N_d)
    assert np.all(N[~pr.DIAMETRO_AVALIADO] == 0)
    assert np.all(N[pr.DIAMETRO_AVALIADO] == 100)


def test_dm_de_espectro_exponencial():
    # N(D) = N0 exp(-L D) tem Dm = 4 / L
    L = 2.0
    N_d = np.log10(8000 * np.exp(-L * pr.DIAMETRO_CLASSES))
    assert pr.diametro_medio_massa(N_d) == pytest.approx(4 / L, rel=0.03)


def test_dm_fisicamente_razoavel_e_pilha_igual_a_um_por_um(chuva):
    pilha = np.stack([r.N_d for r in chuva])
    dm = pr.diametro_medio_massa(pilha)
    assert np.all((0.5 < dm) & (dm < 4))   # 3 mm na leitura de 49.6 mm/h (04:14), normal em chuva forte
    for i, r in enumerate(chuva):
        assert pr.diametro_medio_massa(r.N_d) == pytest.approx(dm[i])


def test_dm_sem_gota_e_nan(registros):
    assert np.isnan(pr.diametro_medio_massa(registros["20261021160000.txt"].N_d))


def test_chuva_por_leitura_bate_com_campo_24(registros):
    # o campo 24 e a mesma chuva da leitura, truncada em 0.01 mm
    dados = pr.concatenar(list(registros.values()))
    dif = pr.chuva_por_leitura(dados) - dados["chuva_absoluta"]
    assert np.all((dif >= -1e-9) & (dif < 0.01))


def test_chuva_por_leitura_sem_campo_01_conta_zero():
    dados = {"intensidade_chuva": np.array([np.nan, 36.0]), "intervalo": np.array([120.0, 120.0])}
    np.testing.assert_allclose(pr.chuva_por_leitura(dados), [0.0, 1.2])


def test_velocidade_terminal():
    vt = pr.velocidade_terminal(np.array([1.0, 5.0]))
    assert vt[0] == pytest.approx(4.0, abs=0.2)
    assert vt[1] == pytest.approx(9.1, abs=0.2)
