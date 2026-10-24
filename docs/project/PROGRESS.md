PRÓXIMO PASSO: F2 — construir o dataset real-time (`build_dataset(origin_date, horizon)`) com defasagens de publicação, lags explícitos e testes anti-look-ahead.

# PROGRESS

Log cronológico de tarefas concluídas. A linha `PRÓXIMO PASSO:` no topo é a
âncora para o protocolo de retomada da seção 3 do PROMPT.

## 2026-10-23

- Verificação do ambiente: Python 3.13 nativo, Node 22, Docker 29, gh
  autenticado como `murilozgodoy`. `uv` e `pnpm` instalados (uv via
  `python -m pip install --user uv`; pnpm via `npm install -g pnpm`).
- Porta 5432 estava ocupada por um container `n8n_postgres` já existente:
  decidido usar **5433:5432** para este projeto (registrado em
  `DECISIONS.md`).
- F0 backend: estrutura em camadas criada (`src/ipca_nowcast/{api,cli,db,
  features,ingestion,models,evaluation}`), `pyproject.toml` com dependências e
  dev-tools, `.gitignore`, `.editorconfig`, `.env.example`, `LICENSE` (MIT),
  `Dockerfile` multi-stage, `docker-compose.yml` (Postgres 16 em 5433),
  `Makefile`, pre-commit, esqueleto Alembic, CI backend em
  `.github/workflows/ci.yml` com Postgres como service.
- Testes placeholder (`tests/test_smoke.py`) incluindo health check do
  FastAPI e o CLI `macro`.
- Arquivos de controle criados: `PLAN.md`, `PROGRESS.md`, `DECISIONS.md`,
  `BLOCKERS.md`.
- F0 frontend concluído: Vite + React 18 + TS strict com Tailwind, MSW,
  TanStack Query, Vitest, Playwright. CI roda lint, format:check,
  typecheck, vitest, build. Primeiro push nos dois repos com tag `v0.0.0`.
- F1 backend: modelos SQLAlchemy (series, observations, focus_expectations,
  forecasts, backtest_results, ingestion_runs) e primeira migração Alembic
  (`0001_initial`). Repositórios com upsert portável (ON CONFLICT no PG e
  SQLite, merge no fallback). Clientes `SgsClient` (paginação por janelas
  com `dateutil.relativedelta`), `FocusClient` (OData `$top`/`$skip`),
  `SidraClient` mínimo. `IngestionService` orquestra o ciclo
  fetch→validate→upsert. Fixtures em `tests/fixtures/` para testes
  offline (24 fixtures + 25 testes passam).
- CLI `macro`: `db upgrade`, `ingest --all/--series/--focus`, `seed
  --fixtures`, `series-list`.
- `macro seed --fixtures` populou Postgres local (porta 5433) com 7 séries,
  90 observações e 6 pontos de Focus. Alembic rodou contra Postgres sem
  erro (0001 aplicada).
