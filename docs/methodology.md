# Metodologia

> Esta é a espinha dorsal técnica do projeto. Documento detalhado será
> expandido junto com as fases F2 e F3.

## 1. Pergunta de pesquisa

> *Um modelo aberto, usando apenas dados públicos, consegue prever o IPCA tão
> bem quanto o consenso dos economistas do mercado (Boletim Focus)? Em quais
> horizontes e em quais períodos?*

A resposta pretendida é **honesta e reprodutível** — não "o modelo ganha" como
objetivo prescritivo.

## 2. Dados

Todas as séries vêm de APIs públicas sem chave:

- **BCB SGS** (`api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}`): IPCA m/m
  (433), IPCA 12m (13522), Selic meta (432), PTAX venda (1), IGP-M (189),
  INPC (188), IBC-Br (24364). Séries diárias são paginadas em janelas ≤ 10
  anos.
- **BCB Olinda — Expectativas de Mercado (Focus)**: OData,
  `ExpectativaMercadoMensais`, `Indicador eq 'IPCA'`. Guardamos a *mediana*
  e metadados (data da coleta, data de referência, nº de respondentes).
- **IBGE SIDRA**: IPCA por grupos (tabelas 1737, 7060) — uso opcional.

## 3. Prevenção de look-ahead bias (o principal argumento técnico)

Cada série do registro `config/series.yaml` carrega um campo
`publication_lag_days` — a defasagem típica entre o período de referência da
observação e o momento em que ela se torna pública (ex.: IPCA de mês *t* é
divulgado por volta do dia 11 de *t+1*).

Para uma data de origem *d*, a função `build_dataset(d, horizon)`:

1. Carrega observações de cada série apenas até `d - publication_lag_days`.
2. Monta um painel mensal com defasagens explícitas (lags 1, 3, 6, 12).
3. Garante que o alvo (IPCA m/m do mês *t = d + horizon*) **não** aparece
   entre as features.

A mediana do Focus usada como benchmark é a **conhecida em *d***, nunca uma
revisão posterior.

Esses invariantes são checados em testes dedicados (fase F2).

## 4. Modelos e combinação

- Benchmarks: random walk, média histórica, sazonal ingênuo, Focus (mediana).
- Modelos: SARIMA (ordem (p,d,q)x(P,D,Q,s) selecionada por AIC), ARIMAX com
  exógenas, ElasticNet (regularização L1+L2), GradientBoosting. Uma
  **combinação simples** (média dos modelos) é incluída: literatura mostra
  que combinações batem modelos individuais com frequência.
- Random seed fixa em toda a pipeline para reprodutibilidade.

## 5. Avaliação

- Backtest *expanding-window* com origens mensais do primeiro mês viável até
  hoje. Horizontes h = 0 (nowcast), 1, 2, 3 meses à frente.
- Métricas por horizonte: **RMSE**, **MAE**, **viés**, **RMSE relativo** (vs.
  Focus).
- **Teste de Diebold-Mariano** (DM, com correção HAC) comparando cada modelo
  ao Focus; a hipótese nula é igualdade de perda esperada.
- Análise por subperíodos: pré-2020, pandemia (2020-2021), 2022→.

## 6. Limitações conhecidas

- Horizonte curto (nowcast) favorece modelos que incorporam preços de
  mercado em tempo real; não usamos (ainda) dados semanais da ANP.
- Focus é um alvo movediço (dezenas de analistas; a mediana é defensável).
- Não ajustamos revisões do IPCA — comparamos a primeira divulgação.
