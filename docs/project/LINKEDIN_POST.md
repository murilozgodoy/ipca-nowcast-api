# Rascunho de post no LinkedIn — Painel Macro Brasil

> Edite antes de publicar: ajuste tom, confirme números finais e troque o
> link do GitHub pelo seu LinkedIn.

---

🚀 Terminei o **Painel Macro Brasil** — um projeto open-source que coleta
dados macroeconômicos oficiais, prevê a inflação (IPCA) do mês corrente e
dos próximos meses e **compara a acurácia dos modelos com o consenso do
mercado** (mediana do Boletim Focus) de forma honesta e reprodutível.

🧪 **Pergunta central:** um modelo aberto, usando apenas dados públicos,
consegue prever o IPCA tão bem quanto o consenso dos economistas? Em
quais horizontes e em quais períodos?

🧰 **Stack:**
• Backend em Python 3.12 com FastAPI, SQLAlchemy 2.0, PostgreSQL 16,
  statsmodels e scikit-learn
• Frontend em React 18, Vite, TypeScript estrito, TanStack Query,
  Tailwind e Recharts
• Testes unitários + integração offline (fixtures gravadas), CI no GitHub
  Actions com PostgreSQL como service

🔎 **Rigor técnico:** o maior cuidado é com *look-ahead bias*. Cada série
tem defasagem de publicação configurada; o Focus usado como benchmark é a
mediana conhecida na data de origem (nunca uma revisão posterior). Isso é
verificado por testes dedicados.

📊 **Modelos comparados:** random walk, média histórica, sazonal ingênuo,
Focus, SARIMA, ElasticNet, Gradient Boosting e uma combinação (média). O
teste de **Diebold-Mariano** valida se a diferença de acurácia é
estatisticamente significativa.

🧭 **Resultado honesto (backtest 2015→hoje, 141 observações mensais):**
no **horizonte 0 (nowcast)** o Focus bate todos os modelos abertos com
significância forte (p < 0.001) — mediana de ~100 analistas acessa
informação de alta frequência (câmbio intradiário, julgamento sobre
COPOM) que o modelo não usa.

Mas no **horizonte 1 (um mês à frente)** a história muda: a *média
histórica* fica estatisticamente empatada com o Focus (p = 0.075) e o
*SARIMA* reduz a diferença para apenas 10% de RMSE a mais (p = 0.041,
marginal). Em outras palavras: **para prever o próximo mês, um modelo
simples abertamente especificado chega perto do consenso dos economistas.**

Código: https://github.com/murilozgodoy/ipca-nowcast-api
Dashboard: https://github.com/murilozgodoy/ipca-nowcast-web
LinkedIn: https://www.linkedin.com/in/murilozgodoy

#DataScience #Economia #Python #React #BancoCentral #IPCA #Brasil
