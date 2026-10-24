# Deploy plan — Painel Macro Brasil

> Nothing in this document was published to a real host. It is a blueprint
> that another engineer (or future me) can execute in under one hour.

## Recommended free/cheap stack

- **Database** — [Neon](https://neon.tech) free tier (Postgres 16, 0.5 GB,
  autosleep). Alternatively Supabase, or a $7/month Railway instance.
- **Backend** — [Fly.io](https://fly.io) `shared-cpu-1x@256MB` or Render
  web service. Build from the included `Dockerfile`; the entrypoint runs
  `alembic upgrade head` on boot.
- **Frontend** — any static host (Vercel/Netlify/Cloudflare Pages). Point
  `VITE_API_URL` to the backend URL and set `VITE_USE_MOCKS=false`.
- **Scheduler** — Fly cron, Render Cron Job, or GitHub Actions scheduled
  workflow calling `macro update` once a day at 11:30 UTC (after the
  IPCA release window).

## Step-by-step

1. **Provision Postgres**
   - Create a Neon project, grab the connection string, enable branch
     databases (optional) for staging.
   - Set `DATABASE_URL=postgresql+psycopg://user:pass@host/db` as a
     secret.
2. **Deploy the backend**
   - `fly launch --no-deploy` (or Render → Web Service → Dockerfile).
   - Set env vars: `DATABASE_URL`, `API_CORS_ORIGINS=https://<frontend>`.
   - Push to `main` — the image builds, `alembic upgrade head` runs on
     start.
   - Smoke test: `curl https://<api>/health` → `{"status": "ok", ...}`.
3. **Seed the first dataset**
   - `fly ssh console` (or Render shell) → `macro ingest --all --focus`
     then `macro backtest`.
4. **Deploy the frontend**
   - `pnpm build` locally first to confirm. On the host set `VITE_API_URL`
     to the backend URL. Deploy the `dist/` folder (Vercel/Netlify auto
     detect Vite).
5. **Automate updates**
   - Preferred: a GitHub Actions cron workflow that `ssh`-es into the Fly
     VM and runs `macro update`. See `.github/workflows/update.yml`
     (to be created at deploy time).
   - Simpler: Fly `fly machine schedule` with the same command, once per
     weekday at 11:30 UTC.

## Env variables summary

| Variable | Required | Example |
|---|---|---|
| `DATABASE_URL` | yes | `postgresql+psycopg://user:pass@host/db` |
| `API_CORS_ORIGINS` | yes | `https://painel.example.com` |
| `LOG_LEVEL` | no | `INFO` |
| `HTTP_TIMEOUT_SECONDS` | no | `30` |
| `HTTP_MAX_RETRIES` | no | `5` |
| `RAW_DATA_DIR` | no | `/tmp/raw` (ephemeral is fine) |

Frontend uses `VITE_API_URL` and `VITE_USE_MOCKS` only.

## Rollback

- Fly: `fly deploy --image-label=<previous>` (previous image is retained
  for 7 days). Render: redeploy a previous build from the dashboard.
- Database: run `alembic downgrade -1`. Each migration is reversible.

## Observability

- Fly provides request logs and CPU/memory. Add a `/metrics` route and
  the `prometheus-fastapi-instrumentator` package if a Grafana Cloud free
  tier is in play.
- The `ingestion_runs` table is the historical audit of pipeline runs —
  `SELECT * FROM ingestion_runs ORDER BY started_at DESC LIMIT 20`.

## Cost estimate (per month)

| Resource | Free tier | Paid alternative |
|---|---|---|
| Postgres | Neon free (0.5 GB) | Railway $7 |
| Backend | Fly `shared-cpu-1x` free | Render Starter $7 |
| Frontend | Vercel/Netlify free | — |
| **Total** | **$0** | **~$15** |
