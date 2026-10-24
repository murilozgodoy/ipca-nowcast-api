# Notas de entrevista — Painel Macro Brasil

Dez perguntas que um entrevistador costuma fazer sobre o projeto, com
respostas curtas baseadas no que foi efetivamente implementado. Use como
roteiro, não como leitura literal.

### 1. Qual é a pergunta que o projeto responde?

> Um modelo aberto, usando apenas dados públicos, consegue prever o IPCA
> tão bem quanto o consenso do mercado (Focus)? Em quais horizontes e em
> quais períodos?

A resposta é um relatório, não um sim/não — e isso é intencional.

### 2. Como você evita *look-ahead bias*?

Cada série carrega uma defasagem de publicação em `config/series.yaml`.
Para séries mensais ela é contada a partir do fim do mês de referência;
para diárias, da própria data. A função `build_dataset(origin_date,
horizon)` só inclui pontos cuja data de publicação é ≤ `origin_date`. O
Focus usado como benchmark é a mediana conhecida em `origin_date`, nunca
uma coleta posterior. Isso é verificado por testes em
`tests/test_dataset.py`.

### 3. Que modelos você compara e por quê?

Benchmarks triviais (random walk, média, sazonal), o Focus como
benchmark de mercado, e três famílias de modelos: SARIMA (tempo-série
clássico), ElasticNet (regularização sparse) e Gradient Boosting
(não-linearidade). Mais uma **combinação por média**, porque na
literatura combinações frequentemente batem modelos individuais.

### 4. Como você mede acurácia?

RMSE, MAE e viés por horizonte e por subperíodo (pré-2020, pandemia,
pós-2022). O RMSE relativo ao Focus permite comparação direta e o teste
de **Diebold-Mariano** (com correção Harvey-Leybourne-Newbold) testa se a
diferença de acurácia é estatisticamente significativa.

### 5. Por que PostgreSQL e SQLAlchemy, e não só pandas?

Porque o projeto é um dashboard que precisa evoluir: adicionar séries,
guardar previsões, auditar execuções. SQLAlchemy + Alembic dão schema
versionado e permitem rodar o mesmo código contra SQLite em dev e
Postgres em CI/prod. É um padrão que escala para um sistema de verdade.

### 6. Como a API foi desenhada?

Camadas: `ingestion` (clientes HTTP com retry/cache), `db` (modelos +
repositórios), `features` (dataset), `models` (forecasters), `evaluation`
(backtest + DM), `api` (FastAPI thin layer). As rotas da API usam
Pydantic v2 para schemas e dependências para injetar sessão. Zero lógica
de negócio dentro dos endpoints.

### 7. Como o frontend consome a API?

TanStack Query faz o cache HTTP, o Zod valida as respostas no runtime
(dupla rede de proteção com o OpenAPI do backend), e o MSW com fixtures
geradas pelo comando `macro export-fixtures` permite rodar o dashboard
sem backend durante desenvolvimento e testes.

### 8. Quais testes você escreveu?

- Backend: 52 testes offline (fixtures gravadas, zero rede). Cobrem o
  parser do SGS, paginação do Focus, upserts idempotentes, qualidade dos
  dados (gaps/duplicatas/outliers), *dataset builder* com três testes
  anti-look-ahead, Diebold-Mariano com casos conhecidos, backtest
  smoke-test e todos os endpoints via `TestClient`.
- Frontend: Vitest + Testing Library para navegação, Playwright para
  smoke e2e.
- CI: GitHub Actions roda tudo com Postgres 16 como service.

### 9. Qual é a maior limitação, e como você resolveria?

Horizonte curto depende muito de dados em alta frequência. Hoje uso
`SGS` e Focus; preços semanais da ANP são a próxima feature (fase bônus).
Também não ajusto revisões do IPCA — comparo contra a primeira
divulgação. Para um case mais sério trocaria por *vintage data*.

### 10. Se tivesse mais tempo, o que acrescentaria?

- Intervalos de previsão (fan chart) para todos os modelos.
- Previsão por grupos do IPCA (alimentação, administrados, livres).
- Página "acompanhamento ao vivo" com histórico das previsões feitas e
  medindo *out-of-sample* real (não só backtest).
- Observabilidade: `/metrics` Prometheus + dashboards Grafana.
