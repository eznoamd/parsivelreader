"""Deteccao de eventos de chuva nos dados concatenados."""

from __future__ import annotations

from datetime import timedelta

import numpy as np

from .calculos import chuva_por_leitura
from .classes import DIAMETRO_AVALIADO


def detectar_eventos(dados: dict, intervalo_maximo: timedelta = timedelta(minutes=30), margem: timedelta = timedelta(minutes=10), chuva_minima_mm: float = 0.2,) -> list[dict]:
    """Agrupa as leituras com gota em eventos de chuva.

    1. Leitura com gota: alguma contagem na matriz 93 (classes avaliadas).
    2. Leituras com gota a ate `intervalo_maximo` uma da outra formam um evento.
    3. Eventos com menos de `chuva_minima_mm` sao descartados (ruido: garoa,
       inseto, poeira). 0.2 mm e a resolucao de um pluviometro comum; use 0
       para manter todos.

    Entrada:
        dados        retorno de leitura.concatenar()

    Retorna um dict por evento, em ordem cronologica:
        inicio, fim                 1a e ultima leitura com gota
        janela_inicio, janela_fim   inicio e fim com `margem` (para graficos)
        indices                     leituras de `dados` dentro da janela
        n_registros_validos         leituras com gota no evento
        chuva_total_mm              chuva entre inicio e fim (campo 01 x campo 09)
        intensidade_maxima          maior intensidade do evento (campo 01), em mm/h
    """
    tempo = dados["tempo"]
    if len(tempo) == 0:
        return []

    raw = dados["raw"]
    com_gota = raw[..., DIAMETRO_AVALIADO].sum(axis=(-2, -1)) > 0
    indices_com_gota = np.where(com_gota)[0]

    if indices_com_gota.size == 0:
        return []
    chuva = chuva_por_leitura(dados)
    R = np.nan_to_num(dados["intensidade_chuva"])

    # junta leituras com gota consecutivas; um buraco maior que
    # intervalo_maximo fecha o grupo atual e abre outro
    grupos = []
    inicio_grupo = anterior = indices_com_gota[0]
    for idx in indices_com_gota[1:]:
        if tempo[idx] - tempo[anterior] > intervalo_maximo:
            grupos.append((inicio_grupo, anterior))
            inicio_grupo = idx
        anterior = idx
    grupos.append((inicio_grupo, anterior))

    eventos = []
    for ini_idx, fim_idx in grupos:
        chuva_evento = float(chuva[ini_idx : fim_idx + 1].sum())
        if chuva_evento < chuva_minima_mm:
            continue
        janela_inicio = tempo[ini_idx] - margem
        janela_fim = tempo[fim_idx] + margem
        mascara = (tempo >= janela_inicio) & (tempo <= janela_fim)
        eventos.append({
            "inicio": tempo[ini_idx],
            "fim": tempo[fim_idx],
            "janela_inicio": janela_inicio,
            "janela_fim": janela_fim,
            "indices": np.where(mascara)[0],
            "n_registros_validos": int(np.sum(com_gota[ini_idx : fim_idx + 1])),
            "chuva_total_mm": chuva_evento,
            "intensidade_maxima": float(R[ini_idx : fim_idx + 1].max()),
        })
    return eventos
