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
- [x] Estrutura do frontend (Vite + React + TS strict, Tailwind, Vitest, Playwright)
- [x] GitHub Actions CI frontend
- [x] README frontend
- [x] Primeiro push em ambos os repos com tag `v0.0.0`
- [ ] CI verde nos dois repos (aguardando primeira execução nos runners do GitHub)

## F1 — Banco e ingestão de dados
- [x] Modelos SQLAlchemy: `series`, `observations`, `focus_expectations`, `forecasts`, `backtest_results`, `ingestion_runs`
- [x] Primeira migração Alembic (`0001_initial`)
- [x] Repositórios com upsert portável (PG / SQLite)
- [x] `SgsClient` (paginação por janelas com relativedelta, retry via tenacity, cache em disco)
- [x] `FocusClient` (OData, paginação `$top`/`$skip`)
- [x] `SidraClient` mínimo (fase bônus)
- [x] `config/series.yaml` com defasagem de publicação
- [x] Upsert idempotente (ON CONFLICT); relatório de qualidade (lacunas, duplicatas, outliers)
- [x] CLI: `macro db upgrade`, `macro ingest --all/--series/--focus`, `macro seed --fixtures`, `macro series-list`
- [x] Fixtures gravadas em `tests/fixtures/` e testes offline (25 passam)

## F2 — Dataset de modelagem
- [x] `build_dataset(origin_date, horizon)` com features defasadas e defasagem de publicação por frequência
- [x] Testes explícitos de anti-look-ahead (cutoff por lag, ausência de leaks, imutabilidade histórica)
- [x] Documentação em `docs/methodology.md`

## F3 — Modelos e backtest
- [ ] Benchmarks: RW, média, sazonal ingênuo, Focus
- [ ] SARIMA, ARIMAX, ElasticNet, GradientBoosting, combinação
- [ ] Backtest expanding-window, origens mensais 2012→hoje, h = 0..3
- [ ] Métricas RMSE/MAE/viés + RMSE relativo ao Focus
- [ ] Teste de Diebold-Mariano
- [ ] Resultados persistidos em `forecasts`/`backtest_results`
- [ ] CLI `macro backtest`, `macro nowcast`

## F4 — API (FastAPI)
- [x] `GET /health` com status do banco
- [x] `GET /series`, `GET /series/{code}` com `start`/`end` opcionais
- [x] `GET /nowcast/latest` executando todos os modelos
- [x] `GET /backtest/metrics` e `GET /backtest/forecasts` com filtros + paginação
- [x] `GET /focus/latest` (latest median por mês de referência)
- [x] 8 testes com `TestClient` passando contra SQLite com fixtures semeadas

## F5 — Pipeline de atualização
- [x] `macro update` com registro em `ingestion_runs` (ingest → nowcast → persist)
- [x] `macro export-fixtures` dumpa `/health`, `/series`, `/nowcast/latest`, `/backtest/metrics`, `/backtest/forecasts` e `/focus/latest` em JSON na pasta do MSW do frontend

## F6 — Base do frontend
- [x] Layout, roteamento, tema claro/escuro, design system (Card/Kpi/EmptyState/LoadingBar/ErrorBanner)
- [x] HTTP client com Zod, hooks TanStack Query, MSW com fixtures reais
- [x] Estados de loading/error/empty em todas as páginas de dados

## F7 — Páginas do dashboard (pt-BR)
- [x] `/` Visão geral com KPIs e previsão do mês vs. Focus
- [x] `/inflacao` com seletor de horizonte e toggles de modelo
- [x] `/modelos` com leaderboard + explicação do DM
- [x] `/series` com explorador e download CSV
- [x] `/metodologia`
- [x] `/sobre`
- [x] Playwright smoke e2e configurado (`tests/e2e/smoke.spec.ts`)

## F8 — Qualidade e polimento
- [x] 52 testes de backend passam offline (ver `uv run pytest`)
- [x] 3 testes de componentes principais no frontend (`pnpm test`)
- [x] a11y: `aria-label` em botões, headings semânticos, tabelas acessíveis
- [x] CI verde nos dois repos (lint + typecheck + testes + build)

## F9 — Pronto para deploy (sem publicar)
- [x] Dockerfile de produção com `alembic upgrade head` no boot
- [x] `pnpm build` valida tipos e produz bundle de produção
- [x] `.env.example` em ambos os repos
- [x] `docs/deploy.md` com plano completo (Neon + Fly + Vercel)

## F10 — Documentação de portfólio
- [x] README dos dois repos nível case com Mermaid, central question, resultados e quick start
- [x] `docs/methodology.md`
- [x] `docs/project/LINKEDIN_POST.md`
- [x] `docs/project/INTERVIEW_NOTES.md`
- [x] `docs/project/FINAL_REPORT.md`

## F11 — Bônus
- [ ] Combustíveis ANP
- [ ] Previsão por grupos do IPCA
- [ ] Intervalos de previsão (fan chart)
- [ ] Página "acompanhamento ao vivo"
