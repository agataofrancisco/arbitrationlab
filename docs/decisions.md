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

## D12 — Identidade do revisor derivada do token (principal fixo) (**nova**)
- **Escolha**: cada token mapeia para um principal fixo (`id` + `role`) em `api/auth.py`: `cliente-demo` (client) e `revisor-demo` (reviewer), configuráveis por `ARBITRATIONLAB_CLIENT_ID` e `ARBITRATIONLAB_REVIEWER_ID`. O id gravado na auditoria e como `created_by` vem sempre do token. O cabeçalho `X-Actor` não é lido: enviá-lo não tem efeito.
- **Porquê**: a identidade declarada pelo cliente permitia atribuir uma revisão a outra pessoa. Com o principal derivado do token, um revisor não consegue escrever na auditoria em nome de outro.
- **Limite honesto**: um principal por token. Quem tem o token de revisor é o mesmo principal. Identidade por pessoa exige tokens individuais ou SSO (fora do âmbito demo).
- **Testes**: `tests/test_api.py::test_identidade_do_revisor_vem_do_token_e_x_actor_nao_tem_efeito`, `test_principal_do_token_e_configuravel_e_nao_forjavel`, `test_cliente_nao_pode_escrever_na_auditoria`.
- **Achado resolvido**: ver `docs/architecture.md`, achado 2.

## D13 — Tokens de demo no código, com override por ambiente (**nova**)
- **Escolha**: `config.py` tem tokens de demo por defeito, documentados como não-segredos. O risco de arranque sem override está registado como achado 1.

## D14 — SQLite por omissão, SQLAlchemy como camada
- **Escolha**: SQLite em ficheiro (`data/`, ignorado pelo git). O código é independente do motor; Postgres é uma URL diferente.

## D15 — Experiência em `src/` com saída em `experiments/reports/`
- **Escolha**: a lógica é um pacote testável; os relatórios são artefactos versionados, com `provider: mock` e commit/estado da árvore registados.

## D16 — Painel sem biblioteca de componentes
- **Escolha**: React e Vite simples, sem plugin de React (o plugin exige peers adicionais). Build verificado com `npm run build`.

## D17 — Adaptador RegressionGuard como extra opcional (**nova**)
- **Escolha**: extra `regressionguard` no `pyproject.toml`, apontando à tag publicada `v0.1.0` (`git+https://github.com/agataofrancisco/regressionguard@v0.1.0`). O adaptador (`src/arbitrationlab/integrations/regressionguard.py`) regista `arbitrationlab.claim_fields` no registo público (`register`, `EvalContext`, `EvalResult`) e corre datasets com `load_dataset` e `evaluate_output`.
- **Porquê não `run_suite`**: a função `run_suite` só constrói alvos pela fábrica interna (`extraction`, `minirag`). Para expor a arbitragem como alvo teria de editar a biblioteca. Usou-se a API pública de nível mais baixo.
- **Contrato verificado na instalação**: `evaluate_output(case, output, root, judge)`; `TargetOutput.data` é um dicionário livre; o avaliador lê `data['accepted']` e `data['decisions']`.
- **Limite**: o avaliador só regista um valor se o gold e a saída forem comparados como valores canónicos; não avalia qualidade textual.
- **Verificação**: suite de smoke com 8 casos (um por dificuldade): 7 passam e `CLM-0005` (montante inconsistente, crítico) falha com `accepted_wrong:claimed_amount`, o ponto cego documentado. Testes saltados quando o extra não está instalado (verificado com `sys.modules['regressionguard'] = None`).
