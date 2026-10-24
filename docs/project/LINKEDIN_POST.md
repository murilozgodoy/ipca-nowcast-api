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

🧭 **Resultado honesto:** no horizonte 0 (nowcast), a *combinação* teve
RMSE levemente menor que o Focus no subperíodo pós-2022, mas sem
significância estatística com o tamanho de amostra atual. É o tipo de
resultado que importa para um case: o processo é defensável e os números
são verificáveis.

Código: https://github.com/murilozgodoy/ipca-nowcast-api
Dashboard: https://github.com/murilozgodoy/ipca-nowcast-web

#DataScience #Economia #Python #React #BancoCentral #IPCA #Brasil
