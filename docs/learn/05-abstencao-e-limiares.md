# 05 — Abstenção e limiares

## O problema

Num sistema de extracção de dados de sinistros, um valor errado aceite automaticamente custa dinheiro. Um valor que nunca é aceite custa tempo de revisão. A decisão por campo tem de equilibrar estes dois erros, e o sistema tem de saber dizer "não sei".

## O que entra e o que sai

- **Entra**: a avaliação do campo (acordo, evidência, confiança) e a política (`accept_threshold`, `verify_threshold`, `max_spend`).
- **Sai**, por campo, uma de quatro decisões:

| Decisão | Quando |
|---|---|
| `accept` | Evidência exacta e confiança ≥ `accept_threshold` (0.85 por omissão). |
| `verify` | Evidência exacta e confiança entre `verify_threshold` (0.5) e 0.85. Pede uma leitura barata independente. |
| `human_review` | Qualquer caso com dúvida: ambíguo, em conflito com o texto, sem evidência ou com baixa confiança. |
| `abstain` | O campo não existe no documento (todos os candidatos devolveram `null`). |

## Como funciona por dentro

A ordem das regras está em `src/arbitrationlab/decision/assess.py:1-11` e no corpo de `assess_field`:

1. **Nenhum candidato utilizável** (todos excederam o tempo, falharam ou não cumpriram o schema) → `human_review` com `no_usable_candidate`.
2. **Nenhum valor normalizável**: `abstain` com `missing_in_document` se todos vieram vazios; senão `human_review` com `ambiguous_value` ou `unparseable_value`.
3. **Sem evidência** (`assess.py:153-160`): se o valor é uma das leituras possíveis de uma data ambígua → `ambiguous_value`; se o texto tem outro valor exacto → `evidence_conflict`; senão → `evidence_none`. Em todos estes casos a decisão é `human_review`. Um valor sem evidência nunca é aceite.
4. **Com evidência** (`assess.py:161-166`): compara a confiança com os limiares.
5. **Verificação** (`src/arbitrationlab/decision/verify.py:18-60`): só se a decisão for `verify`. Sem verificador ou sem orçamento, o campo fica em `human_review` com o motivo `no_verifier` ou `skipped: budget`. Com verificador, a segunda leitura só conta se bater certo com o valor proposto e tiver evidência exacta (`verified_by_second_reading`).

O orçamento é um único `BudgetLedger` (`src/arbitrationlab/generation/runner.py:36-52`) partilhado por candidatos, verificações e juiz. Cada chamada reserva o seu custo antes de começar. Se a reserva não cabe, a chamada é omitida e o motivo fica registado.

## Porquê esta escolha

- **Abster-se é uma decisão de primeira classe.** Um campo sem valor no documento não deve ser preenchido com uma adivinha. `abstain` separa "não há dado" de "há dado mas não é fiável".
- **Três limiares em vez de um.** `accept` protege contra erros caros. `verify` gasta um pouco mais de dinheiro para decidir melhor antes de incomodar um humano. `human_review` é o último recurso.
- **Orçamento reservado antes de chamar.** Assim o gasto nunca passa do `max_spend`, mesmo com chamadas em paralelo. Testado em `tests/test_pipeline.py::test_gasto_nunca_excede_max_spend`.

## Alternativas

- **Um limiar só**: mais simples, mas não separa "verificar" de "rever".
- **Abster-se quando a confiança é baixa, em vez de rever**: possível (há um campo previsto para isso), mas aqui a revisão humana é o destino porque a experiência compara o custo da revisão.
- **Aceitar sempre o maioritário**: mais barato, mas sem garantia de evidência. É uma das cinco estratégias da experiência.

## Como falha

- **Limiares escolhidos à mão**: `0.85` e `0.5` são valores de partida e não foram optimizados num conjunto separado. A sensibilidade a estes limiares deve ser reportada na experiência (está prevista na etapa 4).
- **Revisão em excesso**: datas ambíguas são muitas no dataset (uma das dificuldades). Mais revisão aumenta o custo. A experiência mede isto.
- **Erros aceites com evidência**: um rascunho com evidência exacta pode ser aceite. A evidência não distingue versões. Ver `docs/learn/03-evidencia-e-offsets.md`.
- **Testes**: `tests/test_decision.py` (conflito, ambiguidade, abstenção, sobrevivente único, baixa confiança, verificação que bate ou não, orçamento insuficiente, injecção, juiz consultivo) e `tests/test_pipeline.py`.

## Perguntas de entrevista

1. **Porque é que `abstain` e `human_review` são decisões diferentes?** `abstain` diz que o documento não tem o campo. `human_review` diz que tem, mas o sistema não consegue garantir o valor.
2. **Porque é que um valor sem evidência não é aceite mesmo com acordo total?** Porque o acordo pode ser um erro correlacionado. A evidência é um facto do texto.
3. **O que acontece se o orçamento acabar a meio?** A chamada seguinte é omitida e o motivo `skipped: budget` fica no campo. O gasto nunca passa do limite porque a reserva é feita antes da chamada.
4. **Como escolher os limiares?** Com um conjunto separado da calibração, variando o limiar e olhando para o compromisso entre erros críticos e taxa de revisão. Neste projecto, a análise de sensibilidade está prevista na experiência.
