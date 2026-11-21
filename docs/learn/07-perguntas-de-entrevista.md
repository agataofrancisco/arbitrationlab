# 07 — Perguntas de entrevista

Respostas com referência ao código e aos resultados reais do projecto. Os números de mock estão marcados como tal.

## Arquitectura e decisão

**1. Porque é que o voto maioritário não basta?**
Porque mede concordância, não correspondência com o texto. Dois modelos com o mesmo viés concordam e o voto dá-lhes confiança. Ver `docs/learn/01`. O caso `CLM-0042` mostra dois modelos a repetirem a mesma data trocada.

**2. Qual é a diferença entre `abstain` e `human_review`?**
`abstain` significa que o documento não tem o campo (todos os candidatos devolveram vazio). `human_review` significa que há um valor mas o sistema não consegue garantí-lo. Ver `decision/assess.py`.

**3. Porque é que um valor sem evidência nunca é aceite, mesmo com acordo total?**
Porque o acordo pode ser erro correlacionado. A evidência é uma propriedade verificável do texto. Ver `evidence/locate.py`.

**4. Quais são os quatro veredictos e quando se usa cada um?**
`accept` (evidência exacta, confiança acima do limiar), `verify` (confiança intermédia, pede segunda leitura barata), `human_review` (dúvida, conflito ou ambiguidade) e `abstain` (campo ausente). Ver `docs/learn/05`.

**5. Como funciona o orçamento?**
Um `BudgetLedger` partilhado reserva o custo de cada chamada antes de a iniciar. Se não couber, a chamada é omitida e o motivo `skipped: budget` fica registado. Ver `generation/runner.py`.

**6. Porque é que o orçamento é reservado antes das chamadas paralelas?**
Para o resultado não depender da ordem de conclusão. Se o orçamento fosse verificado ao concluir, dois candidatos paralelos poderiam ultrapassar o limite juntos.

**7. O que faz o juiz LLM neste sistema?**
Nada que altere a decisão. Regista uma sugestão e as discordâncias. A autoridade é a regra por campo. Testado em `tests/test_decision.py::test_juiz_e_apenas_consultivo`.

**8. Porque o denominador do acordo inclui candidatos que falharam?**
Para que um único sobrevivente não tenha acordo de 100%. Com 1 de 3, a confiança desce e o campo pede verificação. Decisão D3 em `docs/decisions.md`.

## Normalização

**9. Porque é que `3/2/2026` é ambíguo?**
Porque dia/mês e mês/dia dão ambas datas válidas e diferentes. O sistema não escolhe por convenção; devolve as duas opções e envia para revisão.

**10. Porque é que `18/02/2026` não é ambíguo?**
Porque 18 não é um mês válido. Só uma leitura é possível.

**11. Como se lê "mil duzentos e cinquenta euros e cinquenta cêntimos"?**
Com `normalize/numerals.py` (palavras para inteiro) e `normalize/amounts.py` (separação de euros e cêntimos). Resultado: 1250.5.

**12. Porque é que os parsers nunca lançam excepção?**
Porque os valores vêm de modelos e podem ser qualquer coisa. Devolver `unparseable` mantém o pipeline a correr. Testado com objectos estranhos em `tests/test_normalize.py`.

**13. Porque é que a plegagem de texto não pode mudar o comprimento?**
Porque os offsets do texto plegado têm de corresponder ao original. Ver `normalize/text.py`.

## Evidência

**14. O que é um span com offsets exactos?**
Um intervalo `[start, end)` no texto original tal que `texto[start:end]` é o valor citado. É exacto porque o valor é lido da linha, com o deslocamento de cada linha somado.

**15. Porque é que a evidência só procura nas linhas rotuladas?**
Para evitar falsos conflitos: um ano de apólice seria lido como montante. Compromisso: uma paráfrase fora do rótulo não tem evidência.

**16. Como se defende um sistema de instruções escondidas no texto?**
Linhas com padrões de instrução são marcadas; os valores nelas não contam como evidência; o caso recebe `suspected_injection`. O texto é dados. Testado em `tests/test_evidence.py`.

**17. Porque é que o rascunho é um problema para a evidência?**
Porque a evidência prova presença, não versão final. Um valor de rascunho com evidência exacta é aceite se os modelos o lerem. Este é o erro que a evidência não apanha: 9 campos `claimed_amount` na run de mock.

**18. Porque é que a matrícula tem tolerância a erros e o montante não?**
Uma matrícula com um carácter trocado é quase sempre o mesmo veículo e a revisão confirma. Um montante com um dígito trocado é outro valor.

## Calibração

**19. O que é o ECE?**
A média ponderada, por intervalo de confiança, do desvio entre a confiança média e a taxa de acerto. Implementado em `calibration/metrics.py`. Exemplo: confiança 0.9 com 50% de acerto dá ECE 0.4.

**20. Pode o ECE ser zero e o sistema ser inútil?**
Sim. Um sistema que dá sempre 0.5 e acerta 50% tem ECE zero. O ECE mede calibração, não discriminação.

**21. Porque é que a fiabilidade começa em 0.5?**
É o prior neutro de Beta(1,1). Um modelo sem histórico não deve ser nem confiável nem não confiável.

**22. Porque é que o `fit` não usa o split de avaliação?**
Para não haver fuga de informação. Os números de avaliação só fazem sentido se os parâmetros foram aprendidos sem os ver. `experiments/run.py::fit_calibration`.

**23. Porque regressão logística e não uma rede neural?**
Dá probabilidades, é explicável pelos coeficientes e funciona com poucos dados. Com 48 casos de calibração, uma rede seria opaca e instável.

## Experiência e custo

**24. Porque é que a arbitragem por evidência não ganha ao modelo forte sem revisão?**
Na run de mock, o modelo forte único tem 83.3% de exact match e custa 0.020 por caso. A arbitragem por evidência tem 75.0% e custa 0.024. O padrão de rascunhos é um caso que a evidência não distingue, e o modelo forte lê o rótulo certo. Ver `docs/learn/06`.

**25. Quanto custa a arbitragem com revisão, e como se decide se compensa?**
Na run: 0.099 USD por caso com revisão a 0.30 USD por campo (3.6% dos campos revistos). Compensa quando o custo esperado de um erro aceite supera o custo da revisão. Com revisão a 0.05 USD por campo o custo por caso é 0.037; a 1.00 USD por campo, 0.274.

**26. Porque é que a revisão simulada é optimista?**
Usa o gold. Um revisor real erra e demora. O relatório declara a limitação.

**27. Porque é que não há intervalos de confiança no relatório?**
Com 72 casos de avaliação e um erro correlacionado, a incerteza é grande. Intervalos calculados sobre esta amostra dariam precisão falsa. A limitação está declarada.

**28. Porque é que o dataset é sintético e determinista?**
Para reprodutibilidade e para não haver PII. A geração usa uma semente por caso, e o ficheiro versionado é o resultado (verificado por teste).

**29. Como se garante que os mocks não enviesam a comparação?**
Os mocks leem os rótulos do documento e aplicam perfis de erro por hash do texto. Não recebem o gold. O erro correlacionado é explícito (`correlated=True`).

## API e segurança

**30. Como se trata um pedido inválido?**
A validação é feita na fronteira (pydantic com `extra="forbid"`, limites de tamanho) e o schema é validado antes de qualquer modelo. Resposta 422 sem chamadas a modelos. Testado em `tests/test_api.py`.

**31. Qual é a diferença entre 401 e 403 neste projecto?**
401: token ausente ou inválido. 403: token válido sem o papel exigido (por exemplo, `client` a tentar rever). Ver `api/auth.py`.

**32. O que garante a auditoria da revisão?**
Cada alteração grava actor, valor anterior, novo valor, texto e data numa tabela própria. Não há actualização sem registo porque ambas as escritas estão na mesma transacção.

**33. O que fica por resolver na autenticação?**
O `X-Actor` é declarado e não autenticado; os tokens de demo estão no código com override por ambiente. Achados 1 e 2 em `docs/architecture.md`.

**34. Porque é que a revisão só aceita campos `human_review` ou `abstain`?**
Porque campos aceites não precisam de revisão e alterá-los sem razão corrompe o registo de decisões automáticas. Um segundo pedido de revisão para o mesmo campo devolve 409.

**35. Porque é que o painel não guarda o token em `localStorage`?**
Porque é um segredo de acesso e `localStorage` persiste entre sessões e é legível por qualquer script da mesma origem. Fica em memória.

**36. Como se exporta uma revisão como etiqueta?**
`GET /reviews/export` (papel `reviewer`) gera JSONL com `source: human_review`, só para `confirm` e `correct`. Não entra no dataset sem revisão do dataset.

## Engenharia

**37. Porque SQLite e SQLAlchemy?**
SQLite não exige serviço externo para a demo; SQLAlchemy mantém o código independente do motor. Postgres seria uma URL diferente, com bloqueio de linha para revisões concorrentes (achado 4).

**38. Porque é que os ficheiros têm limite de linhas?**
Para os módulos continuarem legíveis e testáveis. Nenhum módulo ultrapassa 500 linhas nesta entrega.

**39. Como se garante que o frontend compila?**
`npm run build` no `frontend/`, também no CI. Verificado localmente.

**40. Porque é que o adaptador OpenAI-compatível não é usado pela API?**
Porque não há chaves neste ambiente e porque a API deve correr sem custos por defeito. O adaptador está testado com `httpx.MockTransport` e nunca regista a chave.

**41. O que é o `BackgroundTasks` aqui e quais são os limites?**
Corre a arbitragem depois de devolver 201. Com um só processo é suficiente; em produção seria preciso uma fila (e um worker), porque uma falha ou reinício perde a tarefa em curso. Hoje, a falha fica registada como `failed`.

**42. Como se testa uma API com trabalho em segundo plano?**
O `TestClient` executa as tarefas antes de devolver a resposta, por isso o `GET` seguinte vê o estado final. Testado em `tests/test_api.py`.

**43. Porque é que o CI corre a experiência em mock?**
Para verificar que o pipeline de experiência não quebra, sem custos. Os resultados com modelos reais seriam executados manualmente e identificados.

**44. Porque é que o relatório regista o commit e o estado da árvore?**
Para que um número possa ser ligado ao código que o produziu. Se a árvore tiver alterações, o relatório diz isso.

**45. O que falta para pôr isto em produção?**
Modelos reais medidos com intervalos de confiança; autenticação por identidade; fila para o trabalho de arbitragem; Postgres; revisão de segurança externa; cifra e retenção do texto; execução e teste do Docker.
