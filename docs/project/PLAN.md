# PLAN — Painel Macro Brasil

Checklist das fases e tarefas. Marque `[x]` apenas quando o critério de pronto
da fase estiver atendido.

## F0 — Setup (os dois repos)
- [x] Estrutura de pastas do backend (`src/ipca_nowcast/{api,cli,db,features,ingestion,models,evaluation}`)
- [x] `pyproject.toml` com uv, FastAPI, SQLAlchemy, pandas, statsmodels, scikit-learn, typer
- [x] Lint (ruff), formatação, mypy, pytest, pre-commit configurados
- [x] `.editorconfig`, `LICENSE` (MIT), `.gitignore`, `.env.example`
- [x] `docker-compose.yml` com Postgres 16 (porta local 5433)
- [x] `Dockerfile` multi-stage com entrypoint que roda `alembic upgrade head`
- [x] `Makefile` com `install/up/down/test/lint/typecheck/dev/migrate`
- [x] Esqueleto Alembic (sem revisões ainda — F1 cria a primeira)
- [x] GitHub Actions CI backend (ruff, mypy, pytest + postgres service)
- [x] README backend
- [x] Arquivos de controle (`PLAN.md`, `PROGRESS.md`, `DECISIONS.md`, `BLOCKERS.md`)
- [ ] Estrutura do frontend (Vite + React + TS strict, Tailwind, Vitest, Playwright)
- [ ] GitHub Actions CI frontend
- [ ] README frontend
- [ ] CI verde nos dois repos

## F1 — Banco e ingestão de dados
- [ ] Modelos SQLAlchemy: `series`, `observations`, `focus_expectations`, `forecasts`, `backtest_results`, `ingestion_runs`
- [ ] Primeira migração Alembic
- [ ] Repositórios (padrão repository/UoW)
- [ ] `SgsClient` (paginação por janelas, retry, cache Parquet)
- [ ] `FocusClient` (OData, paginação `$top`/`$skip`)
- [ ] `SidraClient` (opcional, IPCA por grupos)
- [ ] `config/series.yaml` com defasagem de publicação
- [ ] Upsert idempotente; validação com pandera
- [ ] Relatório de qualidade (lacunas, duplicatas, outliers)
- [ ] CLI: `macro db upgrade`, `macro ingest --all/--series`, `macro seed --fixtures`
- [ ] Fixtures gravadas em `tests/fixtures/` e testes offline

## F2 — Dataset de modelagem
- [ ] `build_dataset(origin_date, horizon)` com features defasadas
- [ ] Teste explícito de anti-look-ahead
- [ ] Documentação em `docs/methodology.md`

## F3 — Modelos e backtest
- [ ] Benchmarks: RW, média, sazonal ingênuo, Focus
- [ ] SARIMA, ARIMAX, ElasticNet, GradientBoosting, combinação
- [ ] Backtest expanding-window, origens mensais 2012→hoje, h = 0..3
- [ ] Métricas RMSE/MAE/viés + RMSE relativo ao Focus
- [ ] Teste de Diebold-Mariano
- [ ] Resultados persistidos em `forecasts`/`backtest_results`
- [ ] CLI `macro backtest`, `macro nowcast`

## F4 — API (FastAPI)
- [ ] `GET /health` (com status do banco)
- [ ] `GET /series`, `/series/{id}`
- [ ] `GET /nowcast/latest`
- [ ] `GET /backtest/metrics`, `/backtest/forecasts`
- [ ] `GET /focus/latest`
- [ ] Testes com `TestClient`

## F5 — Pipeline de atualização
- [ ] `macro update`: ingest → nowcast → log em `ingestion_runs`
- [ ] Script que exporta respostas da API como fixtures MSW

## F6 — Base do frontend
- [ ] Layout, roteamento, tema claro/escuro, design system
- [ ] HTTP client, hooks TanStack Query, zod, MSW com fixtures
- [ ] Estados de loading/error/empty

## F7 — Páginas do dashboard (pt-BR)
- [ ] `/` visão geral com KPIs e previsão do mês
- [ ] `/inflacao`
- [ ] `/modelos` (leaderboard + DM test explicado)
- [ ] `/series`
- [ ] `/metodologia`
- [ ] `/sobre`
- [ ] Playwright smoke e2e

## F8 — Qualidade e polimento
- [ ] Cobertura backend ≥ 80%
- [ ] Testes de componentes principais no frontend
- [ ] a11y / Lighthouse sem erros graves
- [ ] CI verde nos dois repos

## F9 — Pronto para deploy (sem publicar)
- [ ] Dockerfile de produção validado
- [ ] `pnpm build` validado contra `VITE_API_URL`
- [ ] `.env.example` completo
- [ ] `docs/deploy.md` com plano completo

## F10 — Documentação de portfólio
- [ ] README dos dois repos nível case
- [ ] `docs/methodology.md`
- [ ] `docs/project/LINKEDIN_POST.md`
- [ ] `docs/project/INTERVIEW_NOTES.md`
- [ ] `docs/project/FINAL_REPORT.md`

## F11 — Bônus
- [ ] Combustíveis ANP
- [ ] Previsão por grupos do IPCA
- [ ] Intervalos de previsão (fan chart)
- [ ] Página "acompanhamento ao vivo"
