# 01 — Porque o voto maioritário não é verdade

## O problema

Três modelos leem a mesma participação e dois deles dizem `2026-07-05`. A tentação é aceitar a maioria. Mas os dois podem ter **o mesmo erro pela mesma razão**: ambos leram "07/05/2026" como se fosse mês/dia. Um voto não sabe disto. Conta acordos, não verifica o texto.

No dataset sintético, o caso `CLM-0042` mostra isto. O gold é `2026-05-07`. Os dois modelos baratos (`cheap-a` e `cheap-b`) devolvem `2026-07-05`. O modelo forte (`strong-c`) devolve o texto cru, `07/05/2026`, que é ambíguo.

## O que entra e o que sai

- **Entra**: o texto da participação, o schema de saída e três candidatos (`cheap-a`, `cheap-b`, `strong-c`).
- **Sai**, com `max_spend = 1` e os candidatos mock:

```
CLM-0042 gold 2026-05-07 raws ['2026-07-05', '2026-07-05', '07/05/2026'] -> human_review ambiguous_value conf 0.269 ev none None
```

O voto maioritário teria aceitado `2026-07-05` com dois de três votos. O sistema não aceita: o texto diz `07/05/2026`, que tem duas leituras válidas. O campo vai para revisão com o motivo `ambiguous_value`.

## Como funciona por dentro

1. **Acordo** (`src/arbitrationlab/decision/assess.py:134-138`): `agreement = votos_do_valor_escolhido / total_de_candidatos_pedidos`. O denominador inclui os candidatos que falharam. Assim, um único sobrevivente nunca atinge acordo total por si só.
2. **Evidência** (`src/arbitrationlab/evidence/locate.py:47-64`): um valor só tem evidência se uma leitura da linha rotulada do campo o normalizar para o mesmo valor. O acordo não conta como evidência.
3. **Ambiguidade** (`src/arbitrationlab/decision/assess.py:153-156`): se o valor escolhido é uma das leituras possíveis de uma data ambígua no texto, o campo vai para revisão com `ambiguous_value`.
4. **Confiança calibrada** (`src/arbitrationlab/decision/assess.py:142`): o acordo, a evidência e a fiabilidade histórica do modelo entram num score logístico. Voto nenhum decide sozinho.

## Porquê esta escolha

O voto mede **concordância**. A evidência mede **correspondência com o texto**. Dois modelos com o mesmo viés concordam sempre, e o voto dá-lhes confiança que não merecem. Exigir evidência obriga o valor a existir no documento.

## Alternativas

- **Voto ponderado pela fiabilidade**: melhora, mas continua cego a erros correlacionados se os dois modelos tiverem fiabilidade alta no mesmo campo.
- **Um juiz LLM como árbitro final**: transfere o problema para outro modelo, que pode partilhar o mesmo viés. Aqui o juiz existe, mas é apenas consultivo.
- **Forçar um só modelo forte**: mais caro e sem medida de confiança.

## Como falha

- Um erro correlacionado **que também tem evidência no texto** passa. Exemplo real: no caso com a linha de rascunho, o valor `1.520,00 €` do rascunho aparece no texto. Os modelos baratos leem a primeira linha `Valor reclamado (rascunho)`, a evidência é exacta e a confiança fica acima do limiar. A evidência não distingue um rascunho de um valor final. Testado em `tests/test_decision.py::test_instrucoes_no_texto_nao_aceitam_o_valor_injectado` (o caso de injecção) e documentado em `docs/learn/06-custo-vs-qualidade.md` (a produzir na etapa 4).
- O teste `tests/test_pipeline.py::test_erro_correlacionado_de_data_nao_e_aceite` verifica que, em todos os casos do dataset onde os dois modelos baratos erram, o campo não é aceite.

## Perguntas de entrevista

1. **Se dois modelos concordam, porque não basta aceitar?** Porque concordância não é correspondência. Podem partilhar o mesmo viés de leitura, como trocar dia e mês. O sistema pede uma prova no texto.
2. **O que significa "erro correlacionado" neste projecto?** Dois candidatos que erram do mesmo modo. Nos mocks, o erro depende só do documento (`ErrorProfile(correlated=True)` em `src/arbitrationlab/generation/providers.py:102-106`), por isso ambos erram igual.
3. **O denominador do acordo inclui os candidatos que falharam. Porquê?** Para que um único sobrevivente não tenha acordo de 100%. Com 1 em 3, a confiança desce e o campo pede verificação em vez de aceitação automática.
4. **Porque é que a ambiguidade não se resolve por convenção pt-PT?** Porque `03/02/2026` pode ser 3 de fevereiro ou 2 de março. Escolher a convenção esconde o risco. Melhor enviar para revisão e medir quantas vezes isso acontece.
