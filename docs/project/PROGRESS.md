PRÓXIMO PASSO: Finalizar F0 do frontend (Vite+React+TS strict, Tailwind, Vitest, CI) e dar o primeiro push nos dois repos.

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
