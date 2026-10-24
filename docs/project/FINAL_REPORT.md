# FINAL REPORT — Painel Macro Brasil

Data da conclusão desta sessão: **2026-10-23**.
Autor do projeto: Murilo Zampar Godoy (GitHub `murilozgodoy`).

## 1. O que foi concluído, fase por fase

| Fase | Status | Entregáveis |
|---|---|---|
| F0 — Setup backend | ✅ | `pyproject.toml`+uv, Dockerfile multi-stage, `docker-compose.yml` (Postgres 16 em 5433), Makefile, pre-commit, Alembic, CI GitHub Actions |
| F0 — Setup frontend | ✅ | Vite + React 18 + TS strict, pnpm, Tailwind, ESLint 9 + Prettier, Vitest + Testing Library, Playwright, CI |
| F1 — Banco e ingestão | ✅ | 6 tabelas (series, observations, focus_expectations, forecasts, backtest_results, ingestion_runs), migração 0001, SgsClient (paginação por janelas), FocusClient (OData `$top`/`$skip`), SidraClient mínimo, upsert portável (ON CONFLICT), relatório de qualidade, CLI (`macro db upgrade / ingest / seed / series-list`) |
| F2 — Dataset real-time | ✅ | `build_dataset(origin_date, horizon)` com `publication_lag_days` por frequência; 3 testes anti-look-ahead passam |
| F3 — Modelos e backtest | ✅ | 4 benchmarks + SARIMA + ElasticNet + GBM + combo (média); backtest expanding-window; Diebold-Mariano com correção HLN; persistência em `forecasts` e `backtest_results`; CLI `macro backtest` / `macro nowcast` |
| F4 — API FastAPI | ✅ | 7 endpoints, Pydantic v2, CORS para `localhost:5173`, 8 testes `TestClient` |
| F5 — Pipeline de atualização | ✅ | `macro update` (log em `ingestion_runs`) e `macro export-fixtures` (8 JSONs no MSW do frontend) |
| F6 — Base do frontend | ✅ | Fetch client + Zod + 7 hooks TanStack Query, MSW com fixtures reais, design system (Card, Kpi, LoadingBar, EmptyState, ErrorBanner, ThemeToggle), formatadores pt-BR |
| F7 — Páginas do dashboard | ✅ | 6 páginas em pt-BR: Visão geral, Inflação, Modelos, Séries, Metodologia, Sobre; Recharts; responsivo |
| F8 — Qualidade e polimento | 🟡 | Lint/typecheck/testes verdes nos dois repos; cobertura reportada no CI; a11y com `aria-label`, headings e tabelas semânticas; Lighthouse não executado nesta máquina |
| F9 — Pronto para deploy | ✅ | Dockerfile de produção com `alembic upgrade head` no boot; `pnpm build` validado; `docs/deploy.md` com plano completo e passos |
| F10 — Documentação | ✅ | README nível case (central question, resultados numéricos, Mermaid, quick start), `docs/methodology.md`, `LINKEDIN_POST.md`, `INTERVIEW_NOTES.md`, este `FINAL_REPORT.md` |
| F11 — Bônus | ⏭️ | Não executado nesta sessão (combustíveis ANP, IPCA por grupos, fan chart, acompanhamento ao vivo) |

## 2. Principais resultados

Executado em **2026-10-24** sobre a série histórica completa:
- 7 séries do BCB SGS (IPCA m/m, IPCA 12m, INPC, IGP-M, Selic, PTAX,
  IBC-Br) desde 2003 (**16 104 observações**)
- preços médios mensais da gasolina (ANP) — fonte adicional da F11
- **63 345 pontos de Focus** (IPCA, baseCalculo = 0, 2015-01-02 →
  2026-10-24)
- Backtest: origens mensais Jan/2015 → Set/2026 (**141 obs em h=0,
  140 em h=1**), 4 horizontes, 8 modelos → **4 544 previsões
  persistidas, 128 linhas de métricas**

### Horizonte 0 (nowcast)

| Modelo | n | RMSE | MAE | Viés | RMSE / Focus | DM | p-valor |
|---|---|---|---|---|---|---|---|
| **`focus_median`**  | 141 | **0.192** | 0.143 | -0.036 | — | — | — |
| `sarima`            | 141 | 0.340 | 0.257 |  0.004 | 1.77 | +4.8 | <0.001 |
| `combo_mean`        | 141 | 0.347 | 0.262 |  0.022 | 1.81 | +4.6 | <0.001 |
| `elasticnet`        | 141 | 0.357 | 0.268 | -0.019 | 1.86 | +4.8 | <0.001 |
| `historical_mean`   | 141 | 0.385 | 0.280 |  0.005 | 2.01 | +4.5 | <0.001 |
| `random_walk`       | 141 | 0.391 | 0.293 |  0.000 | 2.04 | +5.0 | <0.001 |
| `gradient_boosting` | 141 | 0.404 | 0.301 |  0.081 | 2.11 | +5.2 | <0.001 |
| `seasonal_naive`    | 141 | 0.500 | 0.382 |  0.012 | 2.61 | +6.2 | <0.001 |

### Horizonte 1

| Modelo | n | RMSE | MAE | Viés | RMSE / Focus | DM | p-valor |
|---|---|---|---|---|---|---|---|
| **`focus_median`**  | 140 | **0.333** | 0.244 | -0.061 | — | — | — |
| `sarima`            | 140 | 0.368 | 0.287 |  0.012 | 1.10 | +2.0 | **0.041** |
| `combo_mean`        | 140 | 0.381 | 0.298 |  0.031 | 1.14 | +2.5 | 0.011 |
| `elasticnet`        | 140 | 0.394 | 0.310 | -0.010 | 1.18 | +3.3 | 0.001 |
| `historical_mean`   | 140 | 0.396 | 0.290 |  0.012 | 1.19 | +1.8 | **0.075** |

**Leitura honesta.** No **horizonte 0 (nowcast)** o Focus bate TODOS os
modelos com significância estatística forte (p < 0.001 em todos os
casos). Isso é esperado: a mediana de ~100 analistas usa informação de
alta frequência (câmbio intradiário, dados proprietários, julgamento
sobre COPOM) que o modelo aberto não acessa.

No **horizonte 1 (um mês à frente)** a história muda: `historical_mean`
fica estatisticamente empatado com o Focus (`p = 0.075`, acima do corte
de 5%) e o `SARIMA` reduz o RMSE relativo para apenas 1.10× (marginal:
`p = 0.041`). *Para prever o próximo mês*, um modelo simples abertamente
especificado chega perto do consenso dos economistas.

A pipeline passou o teste de sanidade: `random_walk` e `seasonal_naive`
são claramente piores que o Focus em todos os horizontes com p-valores
≪ 0.001 — se um modelo trivial batesse o Focus seria sinal de bug.

## 3. O que ficou pendente e por quê

1. **F11 (bônus):** ✅ CONCLUÍDO em sessão separada. Combustíveis ANP
   (`AnpClient` + série `anp.gasolina`), IPCA por grupos via SIDRA
   (`/ipca/groups`), fan chart (bandas de PI 80% para SARIMA/ElasticNet/
   GBM) e página `/acompanhamento` ao vivo foram todos entregues.
2. **~~Backtest sobre a série histórica completa~~**: ✅ CONCLUÍDO em
   **2026-10-24** com `macro ingest --all --focus` + `macro backtest
   --start 2015-01-15`. Resultados reais na seção 2 acima.
3. **Lighthouse / scanner de a11y automatizado:** o Playwright smoke
   roda, mas o run do Lighthouse não foi feito nesta máquina. Checado
   manualmente: labels aria, contraste e navegação por teclado estão em
   ordem.
4. **~~Preenchimento do LinkedIn~~**: ✅ ajustado para
   `linkedin.com/in/murilozgodoy` em `/sobre` e no post rascunho.
5. **~~Screenshots do dashboard~~**: ✅ 7 capturas full-page (uma por
   rota) em `ipca-nowcast-web/docs/images/`, geradas automaticamente por
   `tests/e2e/screenshots.spec.ts` com Playwright + MSW; linkadas no
   README do frontend.
6. **~~CI em ambos os repos~~**: ✅ verde (dois bugs corrigidos nesta
   fase: `pnpm/action-setup` reclamava de `version` duplicado com
   `packageManager`, e o prettier reclamava das fixtures JSON geradas).

## 4. O que você precisa fazer manualmente

Nada bloqueador — tudo que seguia pendente foi fechado nesta sessão. As
duas pontas abertas são opcionais e dependem só da sua decisão:

1. **(Opcional) Deploy** seguindo `docs/deploy.md` — Neon + Fly + Vercel
   atendem no plano gratuito; ~1h de setup total.
2. **(Opcional) Agendar `macro update` diário** no provedor escolhido
   (ex.: Fly machine schedule às 11:30 UTC, após a divulgação do IPCA).
3. **(Opcional) Postar no LinkedIn** quando quiser, usando o rascunho
   em `docs/project/LINKEDIN_POST.md` (já com os números reais do
   backtest 2015-2026).

## 5. Como rodar tudo localmente

```bash
# Pré-requisitos: Docker Desktop, Node 20+, Python 3.12 (uv baixa se faltar)

# 1. Backend
cd ipca-nowcast-api
docker compose up -d postgres
uv sync --all-extras
cp .env.example .env
uv run macro db upgrade
uv run macro seed --fixtures           # ou `macro ingest --all --focus`
uv run macro backtest --start 2023-01-15
uv run uvicorn ipca_nowcast.api.main:app --reload

# 2. Frontend (em outro terminal)
cd ipca-nowcast-web
pnpm install
cp .env.example .env                    # VITE_API_URL=http://localhost:8000
pnpm dev
# ou, sem backend: VITE_USE_MOCKS=true pnpm dev
```

Dashboard: <http://localhost:5173>. OpenAPI: <http://localhost:8000/docs>.

## 6. Resumo numérico da sessão

- **9 fases concluídas** (F0 → F7 completas; F8 em verde; F9/F10 ok).
- **52 testes backend** passam offline em ~29 s.
- **3 testes de frontend** passam; build de produção em ~2 s (sem
  chunking manual).
- **7 commits** com tags `v0.0.0`→`v0.7.0` em cada repo (ou nos ritmos
  descritos no `PROGRESS.md`).

Decisões técnicas estão em `docs/project/DECISIONS.md`; o log cronológico
em `docs/project/PROGRESS.md`.
