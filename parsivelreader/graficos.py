"""
Graficos dos dados do Parsivel2, feitos a partir dos campos do proprio
sensor (01, 07, 90, 93 e os de diagnostico) e de calculos.py.

Unico modulo que depende do matplotlib (pip install parsivelreader[graficos]);
o resto do pacote funciona sem ele.

Todas as funcoes devolvem uma matplotlib.figure.Figure criada sem o pyplot:
nada fica aberto em estado global, entao da pra gerar quantos graficos
quiser num aplicativo/servidor. Quem chama decide o que fazer com a figura:

    fig = grafico_serie_temporal(dados)
    fig.savefig("serie.png", dpi=120)
"""

from __future__ import annotations

import matplotlib.dates as mdates
import numpy as np
from matplotlib.figure import Figure

from .calculos import chuva_por_leitura, diametro_medio_massa, espectro_linear, velocidade_terminal
from .classes import (
    DIAMETRO_AVALIADO,
    DIAMETRO_CLASSES,
    LARGURA_DIAMETRO,
    LARGURA_VELOCIDADE,
    SENTINELA_SEM_DADO,
    VELOCIDADE_CLASSES,
)
from .eventos import detectar_eventos


def _bordas(centros: np.ndarray, larguras: np.ndarray) -> np.ndarray:
    """Bordas das classes (33 valores) a partir de centros e larguras do manual."""
    return np.append(centros - larguras / 2, centros[-1] + larguras[-1] / 2)


def _log10_ou_nan(valor: np.ndarray) -> np.ndarray:
    """log10 onde > 0; NaN onde nao ha gota (fica em branco no grafico)."""
    valor = np.asarray(valor, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(valor > 0, np.log10(np.where(valor > 0, valor, 1)), np.nan)


def _diametro_maximo_visivel(contagem_por_diametro: np.ndarray, minimo: float) -> float:
    """Limite do eixo de diametro: borda da maior classe com gota (ou `minimo`)."""
    com_gota = np.nonzero(contagem_por_diametro)[0]
    if com_gota.size == 0:
        return minimo
    j = com_gota.max()
    return max(minimo, DIAMETRO_CLASSES[j] + LARGURA_DIAMETRO[j] / 2)


def _formatar_tempo(ax) -> None:
    localizador = mdates.AutoDateLocator(minticks=3, maxticks=8)
    ax.xaxis.set_major_locator(localizador)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(localizador))


def _sem_campo(ax, campo: str) -> None:
    """Aviso no lugar da curva quando os arquivos nao tem o campo (dados
    gravados antes do script pedir os campos novos)."""
    ax.text(0.5, 0.5, f"sem o campo {campo} nestes dados", ha="center", va="center",
            transform=ax.transAxes, color="gray")


def _plotar_campo(ax, tempo, valores, campo: str, **estilo) -> None:
    if np.isnan(valores).all():
        _sem_campo(ax, campo)
    else:
        ax.plot(tempo, valores, **estilo)


def grafico_matriz(dados: dict, curva_terminal: bool = True) -> Figure:
    """Mapa de calor do numero de gotas (log10) por diametro x velocidade,
    somando todas as leituras de `dados` (campo 93), com a curva de
    velocidade terminal da chuva para comparacao.
    """
    raw = dados["raw"].sum(axis=0) if dados["raw"].ndim == 3 else dados["raw"]
    raw = np.where(DIAMETRO_AVALIADO, raw, 0)

    fig = Figure(figsize=(8, 6))
    ax = fig.subplots()
    malha = ax.pcolormesh(
        _bordas(DIAMETRO_CLASSES, LARGURA_DIAMETRO),
        _bordas(VELOCIDADE_CLASSES, LARGURA_VELOCIDADE),
        _log10_ou_nan(raw),
        cmap="viridis",
    )
    fig.colorbar(malha, ax=ax, label="log10(numero de gotas)")
    if curva_terminal:
        D = np.linspace(0.3, 8, 100)
        ax.plot(D, velocidade_terminal(D), "r-", lw=1.5, label="velocidade terminal (Atlas et al., 1973)")
        ax.legend(loc="lower right")
    d_max = _diametro_maximo_visivel(raw.sum(axis=0), minimo=4)
    ax.set_xlim(0, d_max)
    ax.set_ylim(0, min(22, velocidade_terminal(np.array([d_max]))[0] * 1.6))
    ax.set_xlabel("Diametro [mm]")
    ax.set_ylabel("Velocidade [m/s]")
    n = len(dados["tempo"]) if dados["raw"].ndim == 3 else 1
    ax.set_title(f"Gotas por diametro x velocidade ({n} leituras, {int(raw.sum())} gotas)")
    return fig


def grafico_dsd_media(dados: dict, intensidade_minima: float = 0.1) -> Figure:
    """Distribuicao media de tamanho de gotas, N(D) do campo 90, nas leituras
    com pelo menos `intensidade_minima` mm/h no campo 01 (as leituras sem
    chuva so puxariam a media para zero)."""
    N = espectro_linear(dados["N_d"])
    com_chuva = np.nan_to_num(dados["intensidade_chuva"]) >= intensidade_minima

    fig = Figure(figsize=(8, 5))
    ax = fig.subplots()
    if com_chuva.any():
        media = N[com_chuva].mean(axis=0)
        visivel = media > 0
        ax.semilogy(DIAMETRO_CLASSES[visivel], media[visivel], "o-")
        ax.set_xlim(0, _diametro_maximo_visivel(media, minimo=4))
    else:
        ax.text(0.5, 0.5, "nenhuma leitura com chuva", ha="center", va="center", transform=ax.transAxes)
    ax.set_xlabel("Diametro [mm]")
    ax.set_ylabel("N(D) [1/(m3 mm)]")
    ax.set_title(f"Distribuicao media de tamanho de gotas "
                 f"({int(com_chuva.sum())} leituras com R >= {intensidade_minima} mm/h)")
    ax.grid(True, which="both", alpha=0.3)
    return fig


def grafico_serie_temporal(dados: dict, eventos: list[dict] | None = None) -> Figure:
    """Intensidade (01), chuva acumulada, Dm (do campo 90) e refletividade
    (07) ao longo do tempo. Os eventos (detectar_eventos, por padrao)
    aparecem sombreados. Dm e refletividade so sao mostrados quando ha gota."""
    tempo = dados["tempo"]
    if eventos is None:
        eventos = detectar_eventos(dados)
    dm = diametro_medio_massa(dados["N_d"])
    com_gota = ~np.isnan(dm)
    z = np.where(dados["refletividade"] > SENTINELA_SEM_DADO, dados["refletividade"], np.nan)

    fig = Figure(figsize=(12, 10))
    axs = fig.subplots(4, 1, sharex=True)
    axs[0].plot(tempo, dados["intensidade_chuva"], lw=0.8)
    axs[0].set_ylabel("R [mm/h]")
    acumulada = np.cumsum(chuva_por_leitura(dados))
    axs[1].plot(tempo, acumulada)
    axs[1].set_ylabel("Chuva acumulada [mm]")
    if len(acumulada):
        axs[1].set_title(f"total no periodo: {acumulada[-1]:.1f} mm", fontsize=9, loc="left")
    axs[2].plot(tempo[com_gota], dm[com_gota], ".", ms=3, color="tab:green")
    axs[2].set_ylabel("Dm [mm]")
    _plotar_campo(axs[3], tempo, z, "07", ls="", marker=".", ms=3, color="tab:red")
    axs[3].set_ylabel("Z [dBZ]")
    for ax in axs:
        for ev in eventos:
            ax.axvspan(ev["inicio"], ev["fim"], color="tab:blue", alpha=0.08, lw=0)
        ax.grid(True, alpha=0.3)
    _formatar_tempo(axs[-1])
    fig.suptitle(f"Parsivel2 -- serie temporal ({len(eventos)} eventos sombreados)")
    return fig


def grafico_evento(dados: dict, evento: dict) -> Figure:
    """Um evento de chuva: intensidade (01) em cima e, embaixo, o espectro
    N(D) do campo 90 ao longo do tempo, com o eixo de diametro cortado na
    maior gota do evento."""
    idx = evento["indices"]
    tempo = dados["tempo"][idx]
    N_d = np.where((dados["N_d"][idx] > SENTINELA_SEM_DADO) & DIAMETRO_AVALIADO, dados["N_d"][idx], np.nan)

    fig = Figure(figsize=(11, 7))
    ax_r, ax_n = fig.subplots(2, 1, sharex=True, gridspec_kw={"height_ratios": [1, 2]})
    ax_r.plot(tempo, dados["intensidade_chuva"][idx], lw=1)
    ax_r.set_ylabel("R [mm/h]")
    ax_r.grid(True, alpha=0.3)

    # cada leitura cobre o seu intervalo (campo 09) antes do horario da coleta
    t = mdates.date2num(tempo)
    bordas_t = np.append(t - dados["intervalo"][idx] / 86400, t[-1])
    malha = ax_n.pcolormesh(
        bordas_t,
        _bordas(DIAMETRO_CLASSES, LARGURA_DIAMETRO),
        N_d.T,
        cmap="viridis",
    )
    fig.colorbar(malha, ax=[ax_r, ax_n], label="log10 N(D) [1/(m3 mm)] (campo 90)")
    ax_n.set_ylim(0, _diametro_maximo_visivel((~np.isnan(N_d)).sum(axis=0), minimo=3))
    ax_n.set_ylabel("Diametro [mm]")
    _formatar_tempo(ax_n)
    fig.suptitle(
        "Evento {:%d/%m %H:%M} - {:%d/%m %H:%M}: {:.1f} mm, maxima {:.1f} mm/h "
        "({} leituras com gota)".format(
            evento["inicio"], evento["fim"], evento["chuva_total_mm"],
            evento["intensidade_maxima"], evento["n_registros_validos"],
        )
    )
    return fig


def graficos_eventos(dados: dict, **opcoes_eventos) -> list[tuple[Figure, dict]]:
    """Detecta os eventos (opcoes repassadas para detectar_eventos, ex.:
    chuva_minima_mm=0) e devolve [(figura, evento), ...], um por evento."""
    eventos = detectar_eventos(dados, **opcoes_eventos)
    return [(grafico_evento(dados, ev), ev) for ev in eventos]


def grafico_diagnostico(dados: dict) -> Figure:
    """Saude do sensor ao longo do tempo:
        status (18): 0 OK, 1 lentes sujas, 2 sem medida utilizavel, 3 laser danificado
        amplitude do laser (10): cai aos poucos com a lente suja
        temperaturas (12 carcaca, 26 placa, 27/28 cabecas)
        alimentacao (17 tensao, 16 corrente de aquecimento)
        particulas validadas (11) x detectadas (60)
    Paineis de campos que os arquivos nao tem mostram um aviso."""
    tempo = dados["tempo"]

    fig = Figure(figsize=(12, 12))
    axs = fig.subplots(5, 1, sharex=True)

    _plotar_campo(axs[0], tempo, dados["status_sensor"], "18", drawstyle="steps-post")
    axs[0].set_ylim(-0.3, 3.3)
    axs[0].set_yticks([0, 1, 2, 3], ["0 OK", "1 sujo", "2 inutil", "3 laser"])
    axs[0].set_ylabel("Status")

    _plotar_campo(axs[1], tempo, dados["amplitude_laser"], "10", lw=0.8)
    axs[1].set_ylabel("Amplitude laser")

    temperaturas = [
        ("temperatura_sensor", "12 carcaca"),
        ("temperatura_placa", "26 placa"),
        ("temperatura_cabeca_direita", "27 cabeca dir."),
        ("temperatura_cabeca_esquerda", "28 cabeca esq."),
    ]
    for chave, rotulo in temperaturas:
        if not np.isnan(dados[chave]).all():
            axs[2].plot(tempo, dados[chave], lw=0.8, label=rotulo)
    if axs[2].lines:
        axs[2].legend(loc="upper right", fontsize=8)
    axs[2].set_ylabel("Temperatura [C]")

    _plotar_campo(axs[3], tempo, dados["tensao"], "17", lw=0.8, color="tab:blue")
    axs[3].set_ylabel("Tensao [V] (17)")
    if not np.isnan(dados["corrente_aquecimento"]).all():
        ax_i = axs[3].twinx()
        ax_i.plot(tempo, dados["corrente_aquecimento"], lw=0.8, color="tab:orange")
        ax_i.set_ylabel("Aquecimento [A] (16)", color="tab:orange")

    axs[4].plot(tempo, dados["n_particulas"], lw=0.8, label="11 validadas")
    if not np.isnan(dados["n_particulas_total"]).all():
        axs[4].plot(tempo, dados["n_particulas_total"], lw=0.8, label="60 detectadas")
    axs[4].legend(loc="upper right", fontsize=8)
    axs[4].set_ylabel("Particulas")

    for ax in axs:
        ax.grid(True, alpha=0.3)
    _formatar_tempo(axs[-1])
    fig.suptitle("Parsivel2 -- diagnostico do sensor")
    return fig
