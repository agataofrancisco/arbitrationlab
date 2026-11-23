# Estudo de caso — ArbitrationLab

## Problema

Extrair de participações de sinistro sete campos (apólice, data, matrícula, montante, moeda, terceiro envolvido, feridos). Um valor errado aceite automaticamente custa dinheiro. Votar entre modelos não resolve, porque dois modelos podem errar da mesma forma.

## Abordagem

Cada valor tem de existir no texto (com offsets), a confiança vem de acordo, evidência e fiabilidade histórica, e o sistema abstém-se ou pede revisão quando não tem certeza. A revisão humana fica auditada e as decisões podem ser exportadas como etiquetas, só depois de revisão do dataset.

## O que foi construído

- Pipeline ponta a ponta com um orçamento por arbitragem.
- API com papéis, validação na fronteira, revisão auditada, exportação JSONL e métricas.
- Painel de três colunas (candidatos, evidências com destaque, veredicto e revisão).
- Dataset sintético determinista de 120 casos, em 8 dificuldades e dois splits (48 calibração, 72 avaliação).
- Experiência comparativa de cinco estratégias com relatório, gráfico e JSON.
- Testes: 183 testes na suite principal, mais 11 na experiência (ver validação abaixo).

## Resultados medidos (provider: mock)

Fonte: `experiments/reports/mock-report.md`, gerado por `python -m arbitrationlab.experiments.run --mode mock`.

| Estratégia | Exact match | F1 macro | Erros críticos | Revisão | Custo/caso (USD) |
|---|---|---|---|---|---|
| modelo barato único | 75.0% | 0.972 | 2.0% | 0.0% | 0.0020 |
| modelo forte único | 83.3% | 0.986 | 0.0% | 0.0% | 0.0200 |
| voto maioritário | 75.0% | 0.972 | 2.0% | 0.0% | 0.0240 |
| arbitragem por evidência | 75.0% | 0.973 | 1.8% | 0.0% | 0.0240 |
| arbitragem + revisão | 87.5% | 0.982 | 1.8% | 3.6% | 0.0990 |

Os custos são simulados. A revisão é simulada a partir dos labels (0.30 USD por campo).

## O que os números dizem

1. Sem revisão humana, a arbitragem por evidência **não bate** o modelo forte único neste dataset, e custa mais. Não se deve afirmar que a arbitragem melhora a qualidade sem revisão.
2. A arbitragem com revisão sobe o exact match, mas a diferença depende de um revisor perfeito e do custo por campo. Com 1.00 USD por campo, o custo médio por caso sobe para 0.274 USD.
3. A evidência não detecta valores de rascunho. Nove campos `claimed_amount` foram aceites com valor errado, porque a linha de rascunho contém um valor real do texto.
4. Houve um erro correlacionado de data no split de avaliação (um caso). A evidência apanhou-o. Uma amostra de um caso não estabelece uma taxa.
5. Em 54 casos a arbitragem com revisão custou mais do que o modelo barato, que já acertava.

## O que ainda não foi medido

- Nenhum modelo real foi executado. Não há chaves de API neste ambiente. A execução real é tarefa manual pendente, e os números seriam identificados com o nome do provider.
- Não há intervalos de confiança. Com 72 casos, a incerteza é grande.
- A latência medida é de mocks em memória, não de APIs.
- Docker e o compose não foram testados localmente. O workflow de CI foi validado apenas como YAML (não correu no GitHub).
- O adaptador RegressionGuard (4.3) está feito e verificado só numa suite de smoke de 8 casos; não há métricas de regressão sobre uma suite maior.

## Validação executada

- `ruff check .` e `ruff format --check .`: sem erros.
- `pytest`: 183 testes na suite principal (inclui API, export, dataset, normalização, evidência, calibração, decisão, pipeline e OpenAI-adapter com MockTransport). Os 11 testes de experiência correm separadamente (`tests/test_experiments.py`) e passam; a suite completa é de 194 testes.
- `npm run build` no `frontend/`: passou.
- Experiência em mock: corre e gera o relatório.
- Dogfood da API via curl e do painel no browser: criação, resultado, revisão, 403, 409, 422, exportação e métricas.
- YAML do workflow de CI e do compose: validados como YAML.

## Lições

- Um sistema que se abstém precisa de medir a abstenção; caso contrário, parece melhor do que é.
- A evidência prova presença, não correcção. Um rascunho no texto também é texto.
- Separar calibração e avaliação é a única forma de evitar que o relatório se engane a si próprio.
