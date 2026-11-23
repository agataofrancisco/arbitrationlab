# 08 — Avaliador RegressionGuard (opcional)

## O problema

Uma arbitragem muda com o tempo: um prompt, um limiar ou um modelo novo podem fazer um campo passar a ser aceite com valor errado. Queremos um sinal de regressão reexecutável sobre um conjunto de casos com gold. O RegressionGuard é uma biblioteca para isto: um registo de avaliadores e datasets golden. O adaptador liga a arbitragem a esse registo sem tornar o núcleo dependente dele.

## O que entra e o que sai

- **Entra**: um dataset golden no formato do RegressionGuard (primeira linha `manifest`, depois um caso por linha) e o texto de cada caso.
- **Sai**: por caso, `passed`, `reason` estável e a severidade. Um caso falha quando a arbitragem aceita um valor diferente do gold.

Saída real da suite de smoke (`experiments/regressionguard/claims-smoke.jsonl`, 8 casos, um por dificuldade):

```
CLM-0001 clean normal True None
CLM-0002 ambiguous_date normal True None
CLM-0003 date_words normal True None
CLM-0004 amount_words normal True None
CLM-0005 inconsistent_amount critical False accepted_wrong:claimed_amount
CLM-0006 missing_field normal True None
CLM-0007 injection critical True None
CLM-0008 plate_variant normal True None
```

## Como funciona por dentro

- **Registo do avaliador** (`src/arbitrationlab/integrations/regressionguard.py:84-93`): `ensure_registered` regista `arbitrationlab.claim_fields` com `register`, uma só vez, porque o registo recusa nomes duplicados.
- **Regra do avaliador** (`:55-81`): lê `ctx.output.data["accepted"]` e `["decisions"]`. Só campos com decisão `accept` contam. Se um deles diferir do gold, falha com `accepted_wrong:<campo>`. Campos em revisão ou abstenção não contam como erro.
- **Saída da arbitragem** (`:96-119`): `arbitration_output` converte o veredicto num `TargetOutput`, com os valores aceites e as decisões.
- **Execução** (`:130-141`): `run_claim_suite` usa `load_dataset` e `evaluate_output` da API pública. Não usa `run_suite`, porque essa função só constrói alvos pela fábrica interna da biblioteca (`extraction`, `minirag`).
- **Dataset de smoke** (`:144-...`): `build_smoke_dataset` gera o ficheiro a partir do dataset sintético versionado. Os `expected` são os labels.

## Porquê esta escolha

- **Extra opcional**. O núcleo da API e a experiência não importam o RegressionGuard. Quem não o quer não o instala, e os testes do adaptador são saltados (`pytest.importorskip`). Verificado com `sys.modules['regressionguard'] = None`: o módulo aparece como `SKIPPED`.
- **API pública, não internals**. `register`, `EvalContext`, `EvalResult`, `load_dataset` e `evaluate_output` são exportados ou documentados no pacote instalado. Não se importa nada de `regressionguard.targets.factory`.
- **Motivo estável**. `accepted_wrong:<campo>` permite agregar falhas em relatórios de regressão sem depender do texto.

## Alternativas

- **Integrar via `run_suite`**: mais limpo na forma, mas exige um alvo na fábrica interna. Rejeitado, porque obrigaria a editar a biblioteca.
- **Copiar a lógica para dentro do projecto**: evita a dependência, mas perde o registo, os relatórios e a comparação entre versões do RegressionGuard.
- **Avaliar só com `exact_match` do RegressionGuard**: não distingue um valor errado aceite de um valor que foi para revisão. A regra específica do domínio é necessária.

## Como falha

- **Ponto cego conhecido**: `CLM-0005` (montante inconsistente, crítico) falha. Um rascunho é lido como valor final porque o texto o contém. O avaliador apanha o erro, mas a suite é pequena: 8 casos, um por dificuldade. Não há taxa estimada.
- **Campos em revisão ocultam erros**: um valor errado enviado para revisão passa no avaliador. É o comportamento pretendido, mas a revisão tem custo e a qualidade depende do revisor (ver `docs/learn/06-custo-vs-qualidade.md`).
- **Dataset e avaliador desalinhados**: se o gold mudar sem regenerar o ficheiro, o teste `test_dataset_de_smoke_versionado_e_reproduzivel` falha.
- **Testes**: `tests/test_regressionguard_adapter.py` (registo idempotente, regra com gold, valor errado em revisão, campo ausente, saída sem dados, suite de smoke, determinismo e reprodutibilidade do dataset).

## Perguntas de entrevista

1. **Porque é que o adaptador é opcional?** Para o núcleo não depender de um pacote de avaliação, e para o projecto continuar a correr sem ele. A dependência fica num extra e os testes são saltados quando falta.
2. **Porque não usar `run_suite`?** Porque aceita só os alvos que a fábrica conhece. Expor a arbitragem como alvo exigiria editar a biblioteca. A API pública de nível mais baixo deu o mesmo resultado sem alterações externas.
3. **Como se evita registar o avaliador duas vezes?** Com `ensure_registered`, que verifica `evaluator_names()` antes de chamar `register`. O registo recusa duplicados, e um módulo pode ser importado mais de uma vez.
4. **O que significa "passou" para este avaliador?** Nenhum valor decidido automaticamente difere do gold. Não mede cobertura nem qualidade de campos revistos.
5. **Porque o `CLM-0005` é crítico e não só um aviso?** Porque é um valor errado aceite sem intervenção humana, que é o pior caso do sistema. Uma regressão aqui deve bloquear uma alteração.
