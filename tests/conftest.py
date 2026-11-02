from pathlib import Path

import pytest

import parsivelreader as pr

PASTA_DADOS = Path(__file__).parent / "dados"


@pytest.fixture
def pasta_dados():
    return PASTA_DADOS


@pytest.fixture
def registros():
    return {r.arquivo: r for r in pr.ler_pasta(PASTA_DADOS)}
