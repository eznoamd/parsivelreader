# parsivelreader

Biblioteca Python para leitura, processamento e análise dos dados do disdrômetro **OTT Parsivel²**, armazenados em arquivos `.txt` no cartão SD do datalogger XLink 500.

## Funcionalidades

- Leitura de arquivos individuais, diretórios e arquivos ZIP exportados do cartão SD.
- Conversão dos registros para estruturas Python e arrays NumPy.
- Tratamento de arquivos incompletos ou corrompidos.
- Concatenação de leituras em séries temporais.
- Detecção de eventos de precipitação.
- Geração de gráficos para análise do espectro de gotas, intensidade de chuva e diagnóstico do sensor.
- Compatibilidade com arquivos de versões antigas do formato de aquisição.

## Instalação

Crie um ambiente virtual e instale a biblioteca conforme os recursos necessários:

```bash
python3 -m venv venv

# Instalação básica: leitura e processamento
venv/bin/pip install -e .

# Instalação com suporte a gráficos
venv/bin/pip install -e ".[graficos]"

# Instalação com ferramentas de teste
venv/bin/pip install -e ".[testes]"
```

O suporte a gráficos utiliza o Matplotlib. A instalação básica utiliza o NumPy para processamento dos dados.

## Uso

### Leitura dos dados

A função `ler_zip()` lê os arquivos de um ZIP exportado do cartão SD e retorna uma lista de objetos `RegistroParsivel`, um por arquivo de leitura.

```python
import parsivelreader as pr

registros = pr.ler_zip("SD.zip")

# Alternativa: ler uma pasta já extraída
# registros = pr.ler_pasta("SD/")

registro = registros[0]

registro.intensidade_chuva  # mm/h — campo 01
registro.status_sensor      # diagnóstico — campo 18
registro.raw                # matriz 32 × 32 — campo 93
```

O atributo `raw` contém as contagens de partículas organizadas por classe de velocidade e diâmetro. Quando a matriz não está disponível, o atributo pode ser `None`.

Os campos e seus respectivos números no protocolo do sensor estão documentados em `parsivelreader/leitura.py`.

### Consolidação das leituras

A função `concatenar()` reúne os registros em arrays NumPy, facilitando análises temporais e operações sobre conjuntos maiores de dados.

```python
dados = pr.concatenar(registros)

dados["refletividade"]  # campo 07
dados["intervalo"]      # duração da leitura, em segundos — campo 09
```

Os campos numéricos são representados por arrays. Quando um registro não contém determinado campo, seu valor correspondente é representado por `NaN`. Registros corrompidos são descartados durante a consolidação.

### Detecção de eventos de precipitação

A função `detectar_eventos()` identifica eventos de chuva a partir das leituras consolidadas.

```python
eventos = pr.detectar_eventos(dados)

evento = eventos[0]

evento["chuva_total_mm"]
evento["intensidade_maxima"]
```

Uma leitura é considerada associada à precipitação quando a matriz de partículas do campo 93 contém contagens. Leituras com intervalos inferiores a 30 minutos entre si são agrupadas no mesmo evento.

Por padrão, são considerados apenas eventos com precipitação acumulada de pelo menos **0,2 mm**. Esse limiar reduz a inclusão de ocorrências isoladas de pequena magnitude, que podem estar associadas a garoa, insetos ou poeira.

Para incluir também eventos abaixo desse limite, utilize `chuva_minima_mm=0`.

```python
eventos = pr.detectar_eventos(
    dados,
    chuva_minima_mm=0,
)
```

## Visualização dos dados

O módulo `parsivelreader.graficos` disponibiliza funções para explorar as leituras, acompanhar a evolução temporal da precipitação e avaliar o estado do equipamento.

Todas as funções retornam objetos `Figure` do Matplotlib, sem abrir automaticamente janelas ou depender da interface do `pyplot`. Assim, quem utiliza a biblioteca decide se deseja exibir, modificar ou salvar cada figura.

```python
from parsivelreader import graficos

# Distribuição das partículas por diâmetro e velocidade
fig_matriz = graficos.grafico_matriz(dados)

# Distribuição média do espectro de gotas
fig_dsd = graficos.grafico_dsd_media(dados)

# Evolução temporal das principais variáveis
fig_serie = graficos.grafico_serie_temporal(dados)

# Detalhamento de um evento de precipitação
fig_evento = graficos.grafico_evento(dados, eventos[0])

# Gráficos individuais para todos os eventos
figuras_eventos = graficos.graficos_eventos(dados)

# Diagnóstico do equipamento
fig_diagnostico = graficos.grafico_diagnostico(dados)
```

Os gráficos disponíveis contemplam:

| Função | Conteúdo |
|---|---|
| `grafico_matriz()` | Matriz de contagens do campo 93 e curva de velocidade terminal |
| `grafico_dsd_media()` | Espectro médio de gotas, calculado a partir do campo 90 |
| `grafico_serie_temporal()` | Intensidade, precipitação acumulada, diâmetro médio e refletividade |
| `grafico_evento()` | Evolução da intensidade e do espectro de gotas durante um evento |
| `graficos_eventos()` | Conjunto de gráficos individuais dos eventos detectados |
| `grafico_diagnostico()` | Status, laser, temperaturas, alimentação e contagens de partículas |

Para salvar uma figura:

```python
graficos.grafico_serie_temporal(dados).savefig(
    "serie.png",
    dpi=120,
)
```

### Executando o exemplo

O script `exemplo.py` demonstra o fluxo completo de leitura e geração dos gráficos a partir de um arquivo ZIP.

```bash
venv/bin/python exemplo.py caminho/do/SD.zip pasta_saida/
```

## Formato dos arquivos de entrada

A biblioteca espera arquivos de leitura no formato `AAAAMMDDHHMMSS.txt`, em que o nome representa o horário da coleta no XLink. Esses arquivos normalmente estão organizados em diretórios no formato `AAAAMMDDHH`.

Cada arquivo contém os campos identificados pelo número do protocolo do Parsivel2:

```text
TYP OP4A
01:0000.000
02:0258.64
...
90:-9.999;-9.999;...   (32 valores)
91:00.000;00.000;...   (32 valores)
93:000;000;...         (1024 valores)
...
18:0
```

O exemplo é ilustrativo; a quantidade de valores e a disponibilidade dos campos dependem do registro e da versão do formato de aquisição.

Arquivos sem os campos 90, 91 ou 93 completos são considerados corrompidos. Outros arquivos encontrados no cartão SD, como `parsivel_erros.log` e logs do XLink, são ignorados.

### Compatibilidade com dados antigos

Os arquivos coletados até outubro de 2026 contêm apenas os campos:

`01`, `02`, `11`, `12`, `17`, `19–21`, `24`, `25`, `30–32`, `34` e `90–93`.

Esses registros continuam sendo aceitos pela biblioteca. Campos ausentes são representados por `None` ou `NaN`, conforme a estrutura de dados utilizada, e os gráficos sinalizam a ausência de informações nos painéis correspondentes.

Como os registros antigos não contêm o campo 09, a duração da leitura é estimada a partir do espaçamento mais frequente entre as leituras, normalmente de 120 segundos.

## Particularidades dos dados do Parsivel2

Alguns detalhes do protocolo e da aquisição precisam ser considerados para evitar interpretações incorretas.

**Orientação da matriz de partículas**

A matriz `raw` utiliza a convenção:

```python
raw[i, j]
# i: classe de velocidade
# j: classe de diâmetro
```

O campo 93 contém as contagens agrupadas por velocidade, com os 32 diâmetros de cada classe de velocidade dispostos consecutivamente. Essa organização corresponde a `reshape(32, 32)` em NumPy.

A transformação adicional utilizada pela implementação MATLAB de referência decorre da forma como o MATLAB preenche matrizes, por coluna, e não deve ser aplicada diretamente à leitura em NumPy.

**Classes de diâmetro não avaliadas**

As duas primeiras classes de diâmetro não são avaliadas pelo sensor, conforme o Apêndice C do manual. A constante `pr.DIAMETRO_AVALIADO` identifica as classes consideradas válidas.

**Temperatura do equipamento**

O campo 12 representa a temperatura interna da carcaça do sensor, não a temperatura do ar. Por isso, o atributo correspondente é denominado `temperatura_sensor`.

**Campo 02 — precipitação desde a inicialização**

O campo 02 representa a precipitação acumulada desde que o sensor foi ligado e retorna a zero ao atingir 300 mm.

Nos dados de outubro de 2026, seu crescimento foi aproximadamente 16 vezes superior à integral da intensidade do campo 01. Por esse motivo, **não utilize o campo 02 para calcular os totais de precipitação** sem antes investigar a divergência.

**Campo 24 — precipitação por leitura**

No modo de consulta utilizado pelo XLink, o campo 24 representa a precipitação da leitura, correspondente a `intensidade × duração`. Seu valor é truncado em incrementos de 0,01 mm.

Nos dados de outubro de 2026, a soma desses valores apresentou uma diferença de aproximadamente 4% em relação à precipitação calculada a partir do campo 01. Para evitar esse erro de quantização acumulado, a biblioteca calcula a precipitação por leitura usando a intensidade e a duração.

**Valores sentinela dos campos 90 e 07**

O valor `-9.999` indica ausência de gotas nos campos 90 e 07. Ele não deve ser interpretado como uma medição física válida.

## Cálculos derivados

A biblioteca prioriza os valores fornecidos diretamente pelo equipamento. A intensidade de precipitação (campo 01), a refletividade (campo 07), a energia cinética (campo 34) e o espectro de gotas (campo 90) são obtidos diretamente dos registros.

O módulo `parsivelreader/calculos.py` reúne os cálculos derivados necessários para as análises e visualizações.

| Função | Descrição | Aplicação |
|---|---|---|
| `chuva_por_leitura` | Calcula a precipitação a partir da intensidade e da duração da leitura | Acumulados e totais dos eventos |
| `diametro_medio_massa` | Calcula o diâmetro médio ponderado pela massa, \(D_m = M_4/M_3\), a partir do campo 90 | Série temporal |
| `espectro_linear` | Converte os valores logarítmicos do campo 90 para escala linear | Espectro médio e diâmetro médio |
| `velocidade_terminal` | Calcula a curva de velocidade terminal baseada em Atlas et al. (1973) | Gráfico da matriz de partículas |

Essas operações complementam os dados do sensor sem substituir desnecessariamente as medições originais.

## Testes

Execute a suíte de testes com:

```bash
venv/bin/python -m pytest
```

O diretório `tests/dados/` contém 13 arquivos reais do cartão SD, representativos do formato antigo. Entre os casos cobertos estão:

- Um trecho de precipitação intensa.
- Um arquivo sem a linha correspondente ao campo 93.
- Uma leitura com partículas indicadas pelo campo 11, mas com a matriz 93 vazia.
- Uma leitura sem precipitação.

O formato mais recente também é testado por meio da inclusão dos novos campos nos registros de teste, utilizando valores no formato especificado pelo manual. Esses dados são definidos por `CAMPOS_NOVOS`, em `tests/test_leitura.py`, até que haja um arquivo real representativo do novo formato.

## Estrutura do projeto

| Arquivo | Responsabilidade |
|---|---|
| `parsivelreader/classes.py` | Classes, larguras e área de medição definidas a partir do manual |
| `parsivelreader/leitura.py` | Leitura dos arquivos `.txt` e ZIP, criação de `RegistroParsivel` e concatenação |
| `parsivelreader/calculos.py` | Cálculos derivados utilizados nas análises |
| `parsivelreader/eventos.py` | Detecção de eventos de precipitação a partir da matriz 93 |
| `parsivelreader/graficos.py` | Geração dos gráficos; requer Matplotlib |
| `exemplo.py` | Exemplo de leitura e geração de gráficos a partir de um ZIP |

## Referências

- **OTT Hydromet.** *Operating Instructions – Present Weather Sensor OTT Parsivel².* Referência principal para os códigos, formatos e unidades dos campos (Capítulo 11.2), o status do sensor (Capítulo 12.1) e as classes de diâmetro e velocidade (Apêndice C).

- **Jairo Valdivia.** [parsivel2 — Toolbox MATLAB](https://github.com/JValdivia23/parsivel2). Implementação de referência que inspirou a metodologia de leitura, concatenação e visualização dos dados. O `parsivelreader` foi desenvolvido do zero para o formato de arquivos gerado pelo XLink.

  DOI: https://zenodo.org/badge/latestdoi/203242951
