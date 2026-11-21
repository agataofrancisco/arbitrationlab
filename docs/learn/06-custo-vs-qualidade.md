# 06 — Custo vs qualidade

## O problema

Arbitrar custa mais do que chamar um modelo barato: mais chamadas, verificação e, sobretudo, revisão humana. Só vale a pena se a qualidade subir o suficiente. Este documento mede isso, incluindo os casos em que **não** compensa e os erros que o sistema não apanha.

## O que entra e o que sai

- **Entra**: o split de avaliação (72 casos) e cinco estratégias sobre os mesmos casos. A calibração usa o split de 48 casos, separado.
- **Sai**: `experiments/reports/mock-report.md`, `mock-accuracy-vs-cost.png` e `mock-results.json`.

Resultados reais da run (provider: **mock**, custos simulados, revisão simulada a partir dos labels):

| Estratégia | Exact match | F1 macro | Erros críticos | Revisão | Custo/caso (USD) | Latência média (ms) |
|---|---|---|---|---|---|---|
| modelo barato único | 75.0% | 0.972 | 2.0% | 0.0% | 0.0020 | 6.37 |
| modelo forte único | 83.3% | 0.986 | 0.0% | 0.0% | 0.0200 | 4.42 |
| voto maioritário | 75.0% | 0.972 | 2.0% | 0.0% | 0.0240 | 7.15 |
| arbitragem por evidência | 75.0% | 0.973 | 1.8% | 0.0% | 0.0240 | 26.02 |
| arbitragem + revisão | 87.5% | 0.982 | 1.8% | 3.6% | 0.0990 | 26.14 |

Leitura direta: o modelo forte único tem melhor exact match que a arbitragem por evidência, e custa menos (0.020 contra 0.024 por caso). A arbitragem por evidência não ganha qualidade sem revisão humana neste dataset. Com revisão, ganha, mas paga 0.30 USD por campo revisto (ver sensibilidade).

## Como funciona por dentro

- Estratégias e revisão simulada: `src/arbitrationlab/experiments/strategies.py` (`run_strategy`, e em `_arbitration` o ramo `REVIEWABLE`, que copia o gold para campos `human_review` e `abstain`).
- Métricas: `src/arbitrationlab/experiments/metrics.py` (`field_scores`, `exact_match`, `critical_error_rate`).
- Análise de casos desfavoráveis: `src/arbitrationlab/experiments/analysis.py`.
- Calibração sem fuga de informação: `src/arbitrationlab/experiments/run.py` (`fit_calibration`), que usa só o split de calibração.

## Porquê esta escolha

- **Mesmos casos para todas as estratégias**: a comparação é justa.
- **Revisão simulada declarada como optimista**: o revisor simulado acerta sempre. Um revisor real errará algumas vezes, e o custo real é maior. O relatório diz isto.
- **Custo de revisão como parâmetro**: com 0.05, 0.30 e 1.00 USD por campo, a arbitragem com revisão custa 0.037, 0.099 e 0.274 USD por caso. A decisão de compensar depende deste número, que não é medido aqui.

## Onde falha (números da run)

1. **Valores de rascunho aceites com evidência exacta**. Nos casos `inconsistent_amount`, a linha `Valor reclamado (rascunho): ...` tem um valor que aparece literalmente no texto. Os modelos baratos leem a primeira ocorrência do rótulo e a evidência confirma o valor errado. Resultado: **9 campos aceites erradamente** pela arbitragem por evidência, todos em `claimed_amount` (por exemplo `CLM-0053`: aceite 4655.47, gold 3879.56). Este é o erro que a evidência não apanha. Nesses casos, a revisão humana é o que corrige, e só quando é aplicada.
2. **Erros correlacionados**. No split de avaliação há **1** caso em que `cheap-a` e `cheap-b` dão a mesma data errada (`CLM-0114`, gold 2026-03-07, errado 2026-07-03). A evidência apanhou-o (`human_review`). Com um só caso, a amostra não permite concluir nada sobre a taxa real.
3. **Custo sem ganho**. Em **54** casos, a arbitragem com revisão custa mais do que o modelo barato, que já acertava em todos os campos. É o custo de confirmar o que já estava certo.
4. **Datas ambíguas**. Nenhuma estratégia sem revisão acerta os 9 casos `ambiguous_date` do split de avaliação. Com revisão, os 9 ficam certos. A ambiguidade não é resolvida por convenção, por desenho (ver `docs/learn/02-normalizacao.md`).
5. **Latência**. A arbitragem é ~4x mais lenta que o modelo barato, mas aqui ambas são medidas sobre mocks em memória. Não representam a latência de APIs reais.

## Alternativas

- **Escolher só o modelo forte**: neste dataset, é a melhor relação qualidade-custo sem revisão. Mas o modelo forte também não tem evidência nem abstenção, e o dataset é pequeno e sintético.
- **Verificação mais agressiva**: subir o número de verificações baratas reduziria a revisão, mas o verificador mock lê os mesmos rótulos e não apanha o rascunho.
- **Não reportar os casos desfavoráveis**: rejeitado. O projecto existe para medir quando arbitrar não compensa.

## Perguntas de entrevista

1. **Porque é que a arbitragem por evidência não melhora sobre o modelo forte neste dataset?** Porque o dataset tem um padrão (rascunhos) que a evidência não distingue, e o modelo forte lê o rótulo certo. A evidência prova presença no texto, não que é o valor final.
2. **Qual é o custo de uma revisão humana, e como se decide se compensa?** É um parâmetro explícito (0.30 USD por campo por omissão). Compensa quando o custo de um erro aceite, multiplicado pela sua probabilidade, supera o custo da revisão. A tabela de sensibilidade mostra o ponto de partida.
3. **Porque é que a revisão simulada é optimista?** Porque usa o gold. Um revisor real pode errar, demorar e ter custo de contexto. Por isso o relatório declara a limitação.
4. **Porque não há intervalos de confiança?** Com 72 casos e um erro correlacionado, a incerteza é grande. Calcular intervalos sem reconhecer a amostra pequena daria uma falsa precisão. O relatório declara a limitação em vez de a esconder.
