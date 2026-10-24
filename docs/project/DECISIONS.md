# DECISIONS

Decisões tomadas sem consulta ao usuário. Formato: decisão, alternativas
consideradas, motivo (≤ 5 linhas por item).

## 2026-10-23 — Postgres local em porta 5433

- **Decisão:** `docker-compose.yml` expõe Postgres em `5433:5432` ao invés da
  5432 padrão.
- **Alternativas:** usar 5432 (padrão) ou parar o container `n8n_postgres`
  existente do usuário.
- **Motivo:** a porta 5432 já estava ocupada pelo container `n8n_postgres` do
  usuário (não relacionado a este projeto). Parar algo externo é intrusivo;
  mudar a porta do projeto é inócuo. CI continua em 5432 (service do workflow).

## 2026-10-23 — `uv` instalado via `python -m pip --user`

- **Decisão:** instalar o `uv` via `python -m pip install --user uv` e adicionar
  `C:\Users\muril\AppData\Roaming\Python\Python313\Scripts` ao PATH do usuário.
- **Alternativas:** `winget install astral-sh.uv` (poderia pedir UAC); instalador
  oficial PowerShell (idem).
- **Motivo:** sem senha, sem UAC, dentro do perfil do usuário, 30 MB. O `.python-version`
  do projeto fixa 3.12 e o `uv` baixa o interpretador automaticamente.

## 2026-10-23 — Python 3.12 (não 3.13 do sistema)

- **Decisão:** fixar `requires-python = ">=3.12,<3.13"` e `.python-version = 3.12`.
- **Alternativas:** permitir 3.13 (versão do sistema).
- **Motivo:** o PROMPT especifica 3.12 e algumas libs científicas
  (`statsmodels`, `pandera`) ainda têm matriz de suporte mais estável em 3.12.
  `uv` baixa 3.12 de forma transparente.

## 2026-10-23 — SQLAlchemy portável + fallback SQLite

- **Decisão:** camada de dados estritamente portável (SQLAlchemy 2.0 + Alembic
  com `render_as_batch=True`), conexão só por `DATABASE_URL`. Dev local pode
  usar SQLite (`sqlite:///./data/dev.db`) sem alterar código.
- **Alternativas:** acoplar a Postgres via tipos específicos (JSONB, etc.).
- **Motivo:** regra de fallback da seção 5 do PROMPT; evita bloquear o projeto
  caso Docker fique indisponível.

## 2026-10-23 — Repositório opcional de LightGBM

- **Decisão:** `lightgbm` NÃO entra na lista de dependências obrigatórias; só é
  carregado se instalado (import opcional em F3).
- **Alternativas:** incluir sempre.
- **Motivo:** reduz atrito em CI (OpenMP no Windows/macOS runners) e tempo de
  build sem perda prática para o backtest. ElasticNet e GradientBoosting já
  cobrem o espaço de modelos requerido.
