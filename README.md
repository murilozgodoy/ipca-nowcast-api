# ipca-nowcast-api

**Painel Macro Brasil** — open-data backend that ingests Brazilian macroeconomic
series, produces monthly inflation (IPCA) nowcasts and compares model accuracy
with the Boletim Focus consensus using rigorous out-of-sample backtests.

> **Central question**
> *Can an open model, using only public data, forecast the IPCA as well as the
> consensus of market economists? At which horizons, and in which periods?*

This repository is the Python backend (FastAPI + SQLAlchemy + Pandas +
statsmodels/scikit-learn). The React dashboard lives in
[`ipca-nowcast-web`](https://github.com/murilozgodoy/ipca-nowcast-web).

Status: 🚧 **under active development** — see
[`docs/project/PROGRESS.md`](docs/project/PROGRESS.md) for the live log and the
`PRÓXIMO PASSO` line.

## Stack

- Python 3.12 managed with [`uv`](https://github.com/astral-sh/uv)
- FastAPI + Pydantic v2 (OpenAPI auto-docs)
- PostgreSQL 16 (SQLAlchemy 2.0 + `psycopg` 3, Alembic migrations)
- `httpx` + `tenacity` for ingestion with retries and disk cache
- `pandas` + `pandera` for data wrangling and schema validation
- `statsmodels` (SARIMA/ARIMAX), `scikit-learn` (ElasticNet, GBM)
- `typer` CLI exposed as `macro`
- Testing: `pytest` with offline fixtures; CI runs ruff, mypy, pytest with
  Postgres as a service

## Quick start

```bash
# 1. install uv (https://github.com/astral-sh/uv) then
uv sync --all-extras

# 2. bring Postgres up (uses port 5433 locally)
docker compose up -d postgres

# 3. apply migrations and run tests
cp .env.example .env
uv run alembic upgrade head
uv run pytest
```

Start the API in dev mode:

```bash
uv run uvicorn ipca_nowcast.api.main:app --reload
```

The OpenAPI browser is at <http://localhost:8000/docs>.

## 🇧🇷 Resumo em português

Backend em Python 3.12 do **Painel Macro Brasil**. Coleta séries do BCB
(SGS/Focus) e do IBGE, constrói um dataset mensal com rigor contra
*look-ahead bias*, treina modelos de nowcasting do IPCA (SARIMA, ARIMAX,
ElasticNet, GradientBoosting e uma combinação) e compara a acurácia dos modelos
com a mediana do Boletim Focus via backtest *pseudo out-of-sample*, usando
métricas (RMSE, MAE, viés) e o teste de **Diebold-Mariano**. Os resultados são
expostos por uma API FastAPI que alimenta o dashboard em
[`ipca-nowcast-web`](https://github.com/murilozgodoy/ipca-nowcast-web).

## Project layout

```
src/ipca_nowcast/
├── api/          # FastAPI app and routers
├── cli/          # `macro` CLI (typer)
├── db/           # SQLAlchemy models and repositories
├── features/     # real-time dataset builder (anti-look-ahead)
├── ingestion/    # BCB SGS / Focus / IBGE SIDRA clients
├── models/       # forecasting models (SARIMA, ElasticNet, GBM, ...)
└── evaluation/   # backtest and Diebold-Mariano
```

## License

MIT — see [LICENSE](LICENSE).
