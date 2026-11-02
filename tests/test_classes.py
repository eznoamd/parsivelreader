import numpy as np

import parsivelreader as pr


def test_32_classes_de_cada():
    for vetor in (pr.DIAMETRO_CLASSES, pr.LARGURA_DIAMETRO,
                  pr.VELOCIDADE_CLASSES, pr.LARGURA_VELOCIDADE, pr.DIAMETRO_AVALIADO):
        assert vetor.shape == (pr.N_CLASSES,)


def test_classes_sao_contiguas():
    # o fim de cada classe e o comeco da proxima; tolerancia porque o manual
    # arredonda os centros para 3 casas (0.062 em vez de 0.0625)
    for centro, largura in ((pr.DIAMETRO_CLASSES, pr.LARGURA_DIAMETRO),
                            (pr.VELOCIDADE_CLASSES, pr.LARGURA_VELOCIDADE)):
        fim = centro[:-1] + largura[:-1] / 2
        comeco = centro[1:] - largura[1:] / 2
        np.testing.assert_allclose(fim, comeco, atol=1e-3)


def test_classes_1_e_2_nao_avaliadas():
    assert not pr.DIAMETRO_AVALIADO[:2].any()
    assert pr.DIAMETRO_AVALIADO[2:].all()


def test_area_de_medicao():
    assert pr.AREA_MEDICAO_M2 == 180e-3 * 30e-3
