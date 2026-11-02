import zipfile
from datetime import datetime

import numpy as np

import parsivelreader as pr


def test_le_todos_os_arquivos_da_amostra(registros):
    assert len(registros) == 13


def test_campos_simples(registros):
    r = registros["20261008041600.txt"]
    assert r.tempo == datetime(2026, 10, 8, 4, 16)
    assert not r.corrompido
    assert r.intensidade_chuva == 42.121
    assert r.codigo_erro == "000"
    assert r.hora_sensor is not None and len(r.hora_sensor) == 8


def test_formas_dos_vetores(registros):
    r = registros["20261008041600.txt"]
    assert r.N_d.shape == (32,)
    assert r.v_d.shape == (32,)
    assert r.raw.shape == (32, 32)


def test_orientacao_raw_velocidade_por_diametro(registros):
    # raw e [velocidade, diametro]: numa chuva, a velocidade em que cai o
    # maior numero de gotas tem que crescer com o diametro (curva de
    # velocidade terminal). Com a matriz transposta isso se inverte.
    raw = sum(registros[f"20261008{h}.txt"].raw
              for h in ("040800", "041000", "041200", "041400", "041600", "041800", "042000"))
    contagem_por_diametro = raw.sum(axis=0)
    diametros = np.where(contagem_por_diametro > 100)[0]
    vel_mais_comum = [pr.VELOCIDADE_CLASSES[raw[:, j].argmax()] for j in diametros]
    assert np.all(np.diff(vel_mais_comum) >= 0)
    assert pr.VELOCIDADE_CLASSES[raw[:, 5].argmax()] < pr.VELOCIDADE_CLASSES[raw[:, 15].argmax()]


def test_classes_nao_avaliadas_vazias(registros):
    for r in registros.values():
        if r.raw is not None:
            assert r.raw[:, ~pr.DIAMETRO_AVALIADO].sum() == 0


def test_arquivo_sem_linha_93_e_corrompido(registros):
    r = registros["20261011051200.txt"]
    assert r.corrompido
    assert r.raw is None
    assert r.N_d is not None  # o resto do arquivo continua lido


def test_conteudo_vazio_e_corrompido():
    r = pr.ler_conteudo("TYP OP4A\r\n", "20261008041600.txt")
    assert r.corrompido


def test_93_com_tamanho_errado_e_rejeitado(registros, pasta_dados):
    texto = (pasta_dados / "2026100804" / "20261008041600.txt").read_text()
    linhas = [l if not l.startswith("93:") else l[:-4] for l in texto.splitlines()]
    r = pr.ler_conteudo("\n".join(linhas), "20261008041600.txt")
    assert r.raw is None and r.corrompido


def test_nomes_que_nao_sao_do_parsivel():
    assert pr.eh_arquivo_parsivel("2026100804/20261008041600.txt")
    assert not pr.eh_arquivo_parsivel("parsivel_erros.log")
    assert not pr.eh_arquivo_parsivel("Sutron_XLink_log_backup_.csv")
    assert not pr.eh_arquivo_parsivel("2026100804.txt")


def test_ler_zip_igual_a_ler_pasta(pasta_dados, tmp_path):
    caminho = tmp_path / "SD.zip"
    with zipfile.ZipFile(caminho, "w") as z:
        for arq in pasta_dados.rglob("*.txt"):
            z.write(arq, arq.relative_to(pasta_dados))
        z.writestr("parsivel_erros.log", "20261008041600 resposta invalida nos campos: 93\r\n")
    do_zip = pr.ler_zip(caminho)
    da_pasta = pr.ler_pasta(pasta_dados)
    assert [r.arquivo for r in do_zip] == [r.arquivo for r in da_pasta]
    assert [r.arquivo for r in do_zip] == sorted(r.arquivo for r in do_zip)


def test_concatenar_descarta_corrompidos(registros):
    dados = pr.concatenar(list(registros.values()))
    assert dados["descartados"] == 1
    assert dados["raw"].shape == (12, 32, 32)
    assert dados["N_d"].shape == (12, 32)


def test_concatenar_lista_vazia():
    dados = pr.concatenar([])
    assert dados["raw"].shape == (0, 32, 32)
    assert pr.detectar_eventos(dados) == []


# Campos que o script passou a pedir em nov/2026, com valores no formato do
# manual (Cap. 11.2). Ainda nao ha arquivo real do SD com eles.
CAMPOS_NOVOS = """03:61
04:61
05:RA
07:42.350
08:01500
09:00120
10:15759
13:450123
14:2.11.6
15:2.11.6
16:0.00
18:1
26:031
27:029
28:028
60:00003502
"""


def test_formato_novo(pasta_dados):
    texto = (pasta_dados / "2026100804" / "20261008041600.txt").read_text()
    r = pr.ler_conteudo(texto + CAMPOS_NOVOS, "20261008041600.txt")
    assert not r.corrompido
    assert r.codigo_synop_wawa == 61 and r.codigo_synop_ww == 61
    assert r.codigo_metar == "RA"
    assert r.refletividade == 42.35
    assert r.visibilidade_mor == 1500
    assert r.intervalo_amostragem == 120
    assert r.amplitude_laser == 15759
    assert r.numero_serie == "450123"
    assert r.firmware_iop == "2.11.6" and r.firmware_dsp == "2.11.6"
    assert r.corrente_aquecimento == 0
    assert r.status_sensor == 1
    assert (r.temperatura_placa, r.temperatura_cabeca_direita, r.temperatura_cabeca_esquerda) == (31, 29, 28)
    assert r.n_particulas_total == 3502


def test_formato_antigo_deixa_campos_novos_vazios(registros):
    r = registros["20261008041600.txt"]
    assert r.intervalo_amostragem is None and r.status_sensor is None and r.refletividade is None
    dados = pr.concatenar([r])
    assert np.isnan(dados["status_sensor"]).all()


def test_intervalo_vem_do_campo_09(pasta_dados):
    texto = (pasta_dados / "2026100804" / "20261008041600.txt").read_text()
    dados = pr.concatenar([pr.ler_conteudo(texto + "09:00060\n", "20261008041600.txt")])
    assert dados["intervalo"][0] == 60


def test_intervalo_sem_campo_09_usa_espacamento_das_leituras(registros):
    # leituras de 2 em 2 min (com buracos maiores entre dias)
    dados = pr.concatenar(list(registros.values()))
    assert np.all(dados["intervalo"] == 120)
