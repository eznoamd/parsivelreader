from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Optional

import numpy as np

from .classes import DIAMETRO_CLASSES, N_CLASSES, VELOCIDADE_CLASSES

_PADRAO_NOME = re.compile(r"^\d{14}$")


def eh_arquivo_parsivel(nome: str) -> bool:
    p = PurePosixPath(nome)
    return p.suffix.lower() == ".txt" and bool(_PADRAO_NOME.match(p.stem))


@dataclass
class RegistroParsivel:
    """Uma leitura do Parsivel (um arquivo .txt do SD). Campos que o arquivo
    nao tem ficam None: os arquivos gravados antes de nov/2026 so tem 01, 02,
    11, 12, 17, 19-21, 24, 25, 30-32, 34 e 90-93."""

    tempo: Optional[datetime]
    arquivo: str
    corrompido: bool

    # medidas
    intensidade_chuva: Optional[float] = None        # 01, mm/h
    chuva_acumulada: Optional[float] = None          # 02, mm desde que o sensor ligou (volta a 0 em 300)
    codigo_synop_wawa: Optional[int] = None          # 03, tempo presente, tabela 4680 (manual, Apendice D)
    codigo_synop_ww: Optional[int] = None            # 04, tempo presente, tabela 4677
    codigo_metar: Optional[str] = None               # 05, tempo presente METAR/SPECI, tabela 4678
    refletividade: Optional[float] = None            # 07, dBZ (-9.999 = sem gota)
    visibilidade_mor: Optional[float] = None         # 08, m
    intervalo_amostragem: Optional[float] = None     # 09, s
    n_particulas: Optional[float] = None             # 11, particulas detectadas e validadas
    temperatura_sensor: Optional[float] = None       # 12, C, dentro da carcaca (nao e a do ar)
    tensao: Optional[float] = None                   # 17, V
    inicio_medida: Optional[str] = None              # 19, DD.MM.YYYY_hh:mm:ss
    hora_sensor: Optional[str] = None                # 20, hh:mm:ss
    data_sensor: Optional[str] = None                # 21, DD.MM.YYYY
    chuva_absoluta: Optional[float] = None           # 24, mm; no modo do XLink e a chuva da leitura (01 x 09, truncada em 0.01)
    codigo_erro: Optional[str] = None                # 25
    intensidade_16bit_30: Optional[float] = None     # 30, mm/h
    intensidade_16bit_1200: Optional[float] = None   # 31, mm/h
    chuva_acumulada_16bit: Optional[float] = None    # 32, mm
    energia_cinetica: Optional[float] = None         # 34, J/(m2 h)
    n_particulas_total: Optional[float] = None       # 60, todas as particulas detectadas, inclusive as nao validadas
    N_d: Optional[np.ndarray] = None                 # 90, log10(1/(m3 mm)) por classe de diametro (32,)
    v_d: Optional[np.ndarray] = None                 # 91, velocidade media por classe de diametro, m/s (32,)
    raw: Optional[np.ndarray] = None                 # 93, contagem de particulas [velocidade, diametro] (32, 32)

    # diagnostico do sensor
    amplitude_laser: Optional[float] = None          # 10, amplitude do sinal da faixa de laser (cai com a lente suja)
    corrente_aquecimento: Optional[float] = None     # 16, A, aquecimento das cabecas
    status_sensor: Optional[int] = None              # 18, 0 OK, 1 lentes sujas, 2 sem medida utilizavel, 3 laser danificado
    temperatura_placa: Optional[float] = None        # 26, C
    temperatura_cabeca_direita: Optional[float] = None   # 27, C
    temperatura_cabeca_esquerda: Optional[float] = None  # 28, C
    numero_serie: Optional[str] = None               # 13
    firmware_iop: Optional[str] = None               # 14
    firmware_dsp: Optional[str] = None               # 15


def _para_float(valor: Optional[str]) -> Optional[float]:
    if valor is None:
        return None
    try:
        return float(valor)
    except ValueError:
        return None


def _para_int(valor: Optional[str]) -> Optional[int]:
    numero = _para_float(valor)
    return None if numero is None else int(numero)


def _para_texto(valor: Optional[str]) -> Optional[str]:
    return valor


# campo do Parsivel -> (atributo do RegistroParsivel, conversao)
_CAMPOS = {
    "01": ("intensidade_chuva", _para_float),
    "02": ("chuva_acumulada", _para_float),
    "03": ("codigo_synop_wawa", _para_int),
    "04": ("codigo_synop_ww", _para_int),
    "05": ("codigo_metar", _para_texto),
    "07": ("refletividade", _para_float),
    "08": ("visibilidade_mor", _para_float),
    "09": ("intervalo_amostragem", _para_float),
    "10": ("amplitude_laser", _para_float),
    "11": ("n_particulas", _para_float),
    "12": ("temperatura_sensor", _para_float),
    "13": ("numero_serie", _para_texto),
    "14": ("firmware_iop", _para_texto),
    "15": ("firmware_dsp", _para_texto),
    "16": ("corrente_aquecimento", _para_float),
    "17": ("tensao", _para_float),
    "18": ("status_sensor", _para_int),
    "19": ("inicio_medida", _para_texto),
    "20": ("hora_sensor", _para_texto),
    "21": ("data_sensor", _para_texto),
    "24": ("chuva_absoluta", _para_float),
    "25": ("codigo_erro", _para_texto),
    "26": ("temperatura_placa", _para_float),
    "27": ("temperatura_cabeca_direita", _para_float),
    "28": ("temperatura_cabeca_esquerda", _para_float),
    "30": ("intensidade_16bit_30", _para_float),
    "31": ("intensidade_16bit_1200", _para_float),
    "32": ("chuva_acumulada_16bit", _para_float),
    "34": ("energia_cinetica", _para_float),
    "60": ("n_particulas_total", _para_float),
}

# atributos que concatenar() devolve como arrays de float (NaN = sem o campo)
_NUMERICOS = [attr for attr, conv in _CAMPOS.values() if conv in (_para_float, _para_int)]


def _para_vetor(valor: Optional[str], tamanho_esperado: int) -> Optional[np.ndarray]:
    if not valor:
        return None
    partes = [p for p in valor.strip().strip(";").split(";") if p != ""]
    try:
        vetor = np.array([float(p) for p in partes])
    except ValueError:
        return None
    if vetor.size != tamanho_esperado:
        return None
    return vetor


def _tempo_do_nome(nome_arquivo: str) -> Optional[datetime]:
    stem = PurePosixPath(nome_arquivo).stem
    try:
        return datetime.strptime(stem, "%Y%m%d%H%M%S")
    except ValueError:
        return None


def ler_conteudo(conteudo: str, nome_arquivo: str = "") -> RegistroParsivel:
    tempo = _tempo_do_nome(nome_arquivo)

    campos: dict[str, str] = {}
    for linha in conteudo.splitlines():
        linha = linha.strip()
        if not linha or ":" not in linha:
            continue
        codigo, _, valor = linha.partition(":")
        codigo = codigo.strip()
        if not codigo.isdigit():
            # pula o cabecalho "TYP OP4A" e qualquer lixo
            continue
        campos[codigo] = valor.strip()

    if not campos:
        return RegistroParsivel(tempo=tempo, arquivo=nome_arquivo, corrompido=True)

    registro = RegistroParsivel(
        tempo = tempo,
        arquivo = nome_arquivo,
        corrompido = False,
        N_d = _para_vetor(campos.get("90"), N_CLASSES),
        v_d = _para_vetor(campos.get("91"), N_CLASSES),
        **{attr: conv(campos.get(codigo)) for codigo, (attr, conv) in _CAMPOS.items()},
    )

    raw_bruto = _para_vetor(campos.get("93"), N_CLASSES * N_CLASSES)
    if raw_bruto is not None:
        registro.raw = raw_bruto.reshape(N_CLASSES, N_CLASSES)

    if registro.N_d is None or registro.v_d is None or registro.raw is None:
        registro.corrompido = True

    return registro


def ler_arquivo(caminho) -> RegistroParsivel:
    caminho = Path(caminho)
    conteudo = caminho.read_text(encoding="utf-8", errors="replace")
    return ler_conteudo(conteudo, nome_arquivo=caminho.name)


def ler_zip(caminho_zip) -> list[RegistroParsivel]:
    registros = []
    with zipfile.ZipFile(caminho_zip) as z:
        itens = [n for n in z.namelist() if eh_arquivo_parsivel(n)]
        itens.sort(key=lambda n: PurePosixPath(n).name)
        for nome in itens:
            conteudo = z.read(nome).decode("utf-8", errors="replace")
            registros.append(ler_conteudo(conteudo, nome_arquivo=PurePosixPath(nome).name))
    return registros


def ler_pasta(caminho_pasta) -> list[RegistroParsivel]:
    pasta = Path(caminho_pasta)
    arquivos = sorted(
        (p for p in pasta.rglob("*.txt") if eh_arquivo_parsivel(p.name)),
        key=lambda p: p.name,
    )
    return [ler_arquivo(p) for p in arquivos]


def _intervalo(tempo: np.ndarray, campo_09: np.ndarray) -> np.ndarray:
    """Duracao de cada leitura, em s: o campo 09. Nos arquivos antigos, que
    nao tem o 09, usa o espacamento mais comum entre as leituras (mediana,
    para nao contar os buracos de leituras perdidas)."""
    if len(tempo) < 2 or not np.isnan(campo_09).any():
        return campo_09
    espacamento = np.median([(b - a).total_seconds() for a, b in zip(tempo[:-1], tempo[1:])])
    return np.where(np.isnan(campo_09), espacamento, campo_09)


def concatenar(registros: list[RegistroParsivel]) -> dict:
    """Junta as leituras validas (descarta as corrompidas) num dict de arrays,
    um valor por leitura: tempo, um array por campo numerico do
    RegistroParsivel (NaN onde o arquivo nao tem o campo), codigo_metar,
    N_d, v_d, raw, intervalo (s), e mais D e vel (centros das classes) e
    descartados (quantas leituras corrompidas ficaram de fora)."""
    validos = [r for r in registros if not r.corrompido]

    dados = {"tempo": np.array([r.tempo for r in validos])}
    for attr in _NUMERICOS:
        dados[attr] = np.array(
            [np.nan if getattr(r, attr) is None else getattr(r, attr) for r in validos], dtype=float)
    dados["codigo_metar"] = np.array([r.codigo_metar for r in validos], dtype=object)
    dados["N_d"] = np.stack([r.N_d for r in validos]) if validos else np.empty((0, N_CLASSES))
    dados["v_d"] = np.stack([r.v_d for r in validos]) if validos else np.empty((0, N_CLASSES))
    dados["raw"] = np.stack([r.raw for r in validos]) if validos else np.empty((0, N_CLASSES, N_CLASSES))
    dados["intervalo"] = _intervalo(dados["tempo"], dados["intervalo_amostragem"])
    dados["D"] = DIAMETRO_CLASSES
    dados["vel"] = VELOCIDADE_CLASSES
    dados["descartados"] = len(registros) - len(validos)
    return dados
