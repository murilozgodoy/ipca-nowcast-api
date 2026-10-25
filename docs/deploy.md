# Deploy — Painel Macro Brasil

> **Status**: configs prontos no repo (`fly.toml`, `vercel.json`,
> `.github/workflows/fly-deploy.yml`). Falta você executar 5 passos
> abaixo. Total: ~45 min no primeiro deploy, ~0 min nos próximos
> (push → auto-deploy).

Stack escolhido pelo custo zero + simplicidade:

| Camada | Serviço | Plano | O que faz |
|---|---|---|---|
| Banco | **Neon** | Free (0.5 GB, autosleep) | Postgres 16 serverless |
| Backend | **Fly.io** | Free (1 VM shared-cpu-1x@512MB em GRU) | FastAPI em Docker |
| Frontend | **Vercel** | Hobby (100 GB/mês) | React SPA via Vite |

Não precisa cartão de crédito em nenhum dos três. Fly pede um só para
verificar identidade (não cobra enquanto você ficar no free tier).

---

## 1. Postgres no Neon (5 min)

1. Abra <https://console.neon.tech> → "Sign in with GitHub".
2. "Create project":
   - **Name**: `ipca-nowcast`
   - **Postgres version**: 16
   - **Region**: `AWS us-east-1` (sem opção BR no free; Fly em GRU
     chega lá em ~110ms, aceitável).
3. Copie a **Connection string** (seção "Direct connection", não a
   "Pooled" — o SQLAlchemy já faz pool). Formato:
   ```
   postgresql://user:pass@ep-xxx.us-east-1.aws.neon.tech/neondb?sslmode=require
   ```
4. **Prefixe com `+psycopg`** (nosso driver). O valor final que você
   vai usar na próxima etapa é:
   ```
   postgresql+psycopg://user:pass@ep-xxx.us-east-1.aws.neon.tech/neondb?sslmode=require
   ```

Opcional: no Neon → *Settings* → *Compute*, deixe autoscale 0.25-0.5 CU
(default). Sleep after 5 min (default). Perfeito pro free tier.

---

## 2. Fly.io: deploy do backend (15 min)

```powershell
# flyctl já está instalado (c:\Users\<você>\.fly\bin\flyctl.exe
# — se não estiver, rode: iwr https://fly.io/install.ps1 -useb | iex)

cd c:\macro_br\ipca-nowcast-api

# 2.1 login (abre o navegador)
flyctl auth signup   # ou `flyctl auth login` se já tiver conta

# 2.2 criar app (NÃO rode `fly launch` — ele sobrescreve o fly.toml).
#     Em vez disso use `apps create` e deixe nosso fly.toml no comando.
#     Se o nome já estiver tomado, troque `app = ...` em fly.toml.
flyctl apps create ipca-nowcast-api --org personal

# 2.3 secrets (sem aspas no PowerShell; use string com crase se der problema)
flyctl secrets set `
  DATABASE_URL='postgresql+psycopg://user:pass@ep-xxx.us-east-1.aws.neon.tech/neondb?sslmode=require' `
  API_CORS_ORIGINS='https://ipca-nowcast-web.vercel.app' `
  LOG_LEVEL='INFO' `
  -a ipca-nowcast-api

# 2.4 deploy inicial (builda a imagem no Fly, roda alembic, publica)
flyctl deploy --remote-only -a ipca-nowcast-api
```

No fim o Fly imprime a URL — algo como
`https://ipca-nowcast-api.fly.dev`. Teste:

```powershell
curl https://ipca-nowcast-api.fly.dev/health
```

Esperado: `{"status":"ok","version":"0.1.0","database":"up"}`

**Primeira ingestão de dados**:

```powershell
flyctl ssh console -a ipca-nowcast-api
# dentro da VM:
macro ingest --all --focus --focus-start 2015-01-01
macro backtest --start 2015-01-15
exit
```

Isso leva ~15 min e consome ~50 MB no Neon.

---

## 3. Deploy contínuo pelo GitHub Actions (3 min)

Já existe `.github/workflows/fly-deploy.yml` que dispara após o
`backend-ci` passar. Falta só o token:

```powershell
cd c:\macro_br\ipca-nowcast-api

# Gere um token de deploy escopado ao app
flyctl tokens create deploy -a ipca-nowcast-api
# → copie o output completo (começa com "FlyV1 ...")

# Grave como secret no GitHub
gh secret set FLY_API_TOKEN --repo murilozgodoy/ipca-nowcast-api --body "FlyV1 ..."
```

Daqui pra frente, cada push em `main` que passar no CI dispara deploy
automático.

---

## 4. Vercel: deploy do frontend (10 min)

### Via dashboard (recomendado)

1. <https://vercel.com> → "Sign in with GitHub" → autorize.
2. "Add New" → "Project" → selecione `ipca-nowcast-web`.
3. **Framework Preset**: `Vite` (detectado automaticamente).
4. **Environment Variables** (clique "Add"):
   - `VITE_API_URL` = `https://ipca-nowcast-api.fly.dev` (sua URL do Fly)
   - `VITE_USE_MOCKS` = `false`
5. "Deploy". Aguarde ~1 min.
6. Copie a URL definitiva (`https://ipca-nowcast-web.vercel.app` ou
   com sufixo aleatório).

### Atualizar o CORS no Fly

```powershell
flyctl secrets set API_CORS_ORIGINS='https://ipca-nowcast-web.vercel.app' -a ipca-nowcast-api
```

(O Fly reinicia automaticamente.)

Pronto. Teste a URL do Vercel no navegador: todos os endpoints devem
estar vindo da API real agora.

---

## 5. Agendar `macro update` diário (opcional, 5 min)

Cron no Fly roda numa VM dedicada. A opção mais barata é um GitHub
Actions `schedule` chamando `flyctl ssh console --command`:

```yaml
# .github/workflows/daily-update.yml
name: daily-update
on:
  schedule:
    - cron: "30 11 * * *"   # 11:30 UTC = 08:30 BRT, após divulgação do IPCA
  workflow_dispatch:
jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: superfly/flyctl-actions/setup-flyctl@master
      - run: |
          flyctl ssh console -a ipca-nowcast-api --command "macro update"
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
```

Copie esse arquivo pra `.github/workflows/daily-update.yml` quando
quiser ativar.

---

## Troubleshooting

### `database "up": "down"` no /health
- Confira se `DATABASE_URL` tem o prefixo `postgresql+psycopg://`.
- No Neon: dashboard → *Operations* → cheque se o compute está
  acordando (demora 1-2s na primeira query após autosleep).

### CORS error no console do navegador
- `API_CORS_ORIGINS` precisa ser **exatamente** a URL do Vercel
  (sem `/` no fim, com `https`).
- Reinicie o app: `flyctl apps restart ipca-nowcast-api`.

### Deploy do Fly falha com "no builder"
- Rode novamente — Fly às vezes falha na alocação do builder remoto.
- Alternativa: `flyctl deploy --local-only` (precisa Docker rodando).

### Vercel build falha com "pnpm not found"
- Em *Settings → General → Build and Development Settings*, deixe
  **Install Command** vazio (Vercel detecta pnpm pelo
  `packageManager` no `package.json`).

---

## Rollback

- **Fly**: `flyctl releases -a ipca-nowcast-api` lista versões,
  `flyctl deploy --image <registry.fly.io/ipca-nowcast-api:v<N>>`
  volta para uma anterior.
- **Vercel**: dashboard → *Deployments* → clique nos três pontinhos
  do deploy anterior → "Promote to Production".
- **Neon**: ponto-de-restauração automático a cada minuto nos
  últimos 7 dias (free tier).

---

## Custo esperado

| Mês | Fly | Neon | Vercel | **Total** |
|---|---|---|---|---|
| Ocioso | $0 | $0 | $0 | **$0** |
| 1k views/dia | $0 | $0 | $0 | **$0** |
| Projeto bem-sucedido (10k views/dia) | $0 | ~$5 (quando passar da camada free) | $0 | **~$5** |
