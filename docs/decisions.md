# Decisões

Cada decisão indica o contexto, a escolha, a alternativa rejeitada e onde está no código. As decisões marcadas como **nova** foram tomadas durante a execução por não estarem cobertas pelo desenho; devem ser revistas pelo supervisor.

## D1 — Evidência só nas linhas rotuladas
- **Contexto**: procurar o valor em todo o texto cria falsos conflitos (o ano de uma apólice é lido como montante).
- **Escolha**: `evidence/readings.py` lê apenas linhas `Rótulo: valor` cujo rótulo corresponde ao campo.
- **Rejeitado**: pesquisa em todo o texto (mais valores, mais falsos conflitos).

## D2 — Ambiguidade explícita nas datas
- **Contexto**: `03/02/2026` tem duas leituras válidas.
- **Escolha**: `normalize/dates.py` devolve `ambiguous` com as duas opções; o campo vai para revisão.
- **Rejeitado**: convenção pt-PT (dia/mês) por omissão, que esconderia o risco.

## D3 — Acordo com denominador de todos os candidatos pedidos (**nova**)
- **Contexto**: o enunciado diz que candidatos inválidos "não contam para o acordo". Se o denominador fosse só os utilizáveis, um único sobrevivente teria acordo de 100%.
- **Escolha**: `agreement = votos_do_valor / total_pedido`. Um sobrevivente isolado fica com acordo 1/3 e pede verificação.
- **Teste**: `tests/test_decision.py::test_um_so_sobrevivente_nao_atinge_acordo_total`.

## D4 — Confiança: pesos fixos antes de calibrar (**nova**)
- **Contexto**: o desenho pede regressão logística sobre três features, treinada no split de calibração.
- **Escolha**: `ConfidenceModel` começa com pesos fixos (`-4; 3, 3, 2`) e passa a usar regressão do scikit-learn após `fit`. Com uma só classe, mantém a taxa observada.
- **Rejeitado**: regra fixa sem treino como solução final.

## D5 — Verificação barata só conta com evidência exacta
- **Escolha**: a segunda leitura só aceita se normalizar para o mesmo valor e tiver span no texto (`decision/verify.py`).

## D6 — Juiz apenas consultivo
- **Escolha**: `pipeline._judge_suggestion` regista a sugestão e as discordâncias; nunca altera `accepted_value`.
- **Teste**: `tests/test_decision.py::test_juiz_e_apenas_consultivo`.

## D7 — Linhas com instruções não são evidência
- **Escolha**: `decision/injection.py` marca linhas com padrões de instrução; leituras nessas linhas são excluídas.

## D8 — Orçamento único reservado antes de cada chamada
- **Escolha**: `BudgetLedger` partilhado por candidatos, verificações e juiz. Reserva sequencial antes de iniciar, para o resultado não depender da ordem de conclusão.
- **Teste**: `tests/test_pipeline.py::test_gasto_nunca_excede_max_spend`.

## D9 — Mocks com erros deterministas por hash do documento (**nova**)
- **Contexto**: CI sem custos e erros correlacionados reproduzíveis.
- **Escolha**: `ErrorProfile(correlated=True)` decide o erro pelo texto; `correlated=False` inclui o nome do modelo.
- **Limitação**: os mocks lêem os rótulos do documento; não medem modelos reais.

## D10 — Revisão simulada usa o gold (**nova**)
- **Escolha**: na estratégia 5, cada campo `human_review` ou `abstain` recebe o valor do label, com custo configurável (0.30 USD). Declarado como optimista no relatório.

## D11 — Campos revistos como `unreadable` não são etiquetas (**nova**)
- **Escolha**: `export.py` exporta só `confirm` e `correct`. Um campo ilegível não tem valor verdadeiro conhecido.

## D12 — Identidade do revisor declarada, não autenticada (**nova**)
- **Escolha**: cabeçalho `X-Actor` obrigatório na revisão; regista-se tal como declarado. Tokens são por papel, não por pessoa.
- **Risco aceite**: ver `docs/architecture.md`, achado 2.

## D13 — Tokens de demo no código, com override por ambiente (**nova**)
- **Escolha**: `config.py` tem tokens de demo por defeito, documentados como não-segredos. O risco de arranque sem override está registado como achado 1.

## D14 — SQLite por omissão, SQLAlchemy como camada
- **Escolha**: SQLite em ficheiro (`data/`, ignorado pelo git). O código é independente do motor; Postgres é uma URL diferente.

## D15 — Experiência em `src/` com saída em `experiments/reports/`
- **Escolha**: a lógica é um pacote testável; os relatórios são artefactos versionados, com `provider: mock` e commit/estado da árvore registados.

## D16 — Painel sem biblioteca de componentes
- **Escolha**: React e Vite simples, sem plugin de React (o plugin exige peers adicionais). Build verificado com `npm run build`.

## D17 — Adaptador RegressionGuard não implementado
- **Escolha**: tarefa 4.3 marcada como não feita. O contrato do RegressionGuard é uma função sobre `EvalContext`; integrar exigiria instalar ou importar o pacote vizinho, o que não foi feito para não editar fora do projecto.
