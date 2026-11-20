# 02 — Normalização por tipo

## O problema

Um modelo devolve `3/2/2026`, outro `2026-02-03`, um terceiro `3 de fevereiro de 2026`. Para o motor decidir se concordam, é preciso reduzir cada valor a uma forma canónica. Mas a redução não pode inventar: `3/2/2026` não tem uma forma canónica única sem um pressuposto de locale.

## O que entra e o que sai

- **Entra**: um valor bruto (`str`, `int`, `float`, `bool`, `None` ou qualquer outro objecto) e o tipo do campo (`x-type` do schema).
- **Sai**: um `NormResult` com `status` em `ok | missing | unparseable | ambiguous`, o `value` canónico e, no caso ambíguo, as `options`.

Saídas reais (`python -X utf8` sobre `arbitrationlab.normalize.normalize`):

```
'3/2/2026' ambiguous None ('2026-02-03', '2026-03-02')
'18/02/2026' ok 2026-02-18 ()
'mil duzentos e cinquenta euros e cinquenta cêntimos' ok 1250.5 ()
'1.250,50 €' ok 1250.5 ()
'aa-12-bc' ok AA12BC ()
'Não' ok False ()
```

## Como funciona por dentro

- **Despacho por tipo**: `src/arbitrationlab/normalize/__init__.py:30-36`. Um tipo desconhecido trata-se como texto, nunca lança excepção.
- **Datas** (`src/arbitrationlab/normalize/dates.py:45-80`): ISO, "d de mês de aaaa" e `a/b/aaaa`. Para `a/b/aaaa` constroem-se duas leituras (dia/mês e mês/dia). Se só uma é válida, o valor é `ok`. Se as duas são válidas e diferentes, o resultado é `ambiguous`. Se nenhuma é válida (`31/02/2026`), é `unparseable`.
- **Montantes** (`src/arbitrationlab/normalize/amounts.py:57-80`): formato pt-PT (`1.250,50`) e en (`1,250.50`) por regex com fronteiras claras. Sem dígitos, lê-se o montante por extenso com `numerals.words_to_int`.
- **Numerais** (`src/arbitrationlab/normalize/numerals.py`): ida e volta entre inteiros e palavras, de 0 a 999 999.
- **Matrículas** (`src/arbitrationlab/normalize/identifiers.py`): quatro padrões portugueses (`LLDDDD`, `DDLLDD`, `DDDDLL`, `LLDDLL`) depois de remover separadores e pôr em maiúsculas.
- **Plegagem sem perda de posições** (`src/arbitrationlab/normalize/text.py:8-20`): cada carácter dá exactamente um carácter, por isso os offsets do texto plegado são os do original.

## Porquê esta escolha

Três decisões:

1. **Ambiguidade explícita** em vez de convenção. Uma data `a/b/aaaa` com `a` e `b` ≤ 12 não tem leitura única. Escolher uma leitura esconde um erro que o sistema devia reportar. Por isso o resultado é `ambiguous` e as duas opções ficam visíveis.
2. **Nunca lançar excepção.** Os valores vêm de modelos, e um modelo pode devolver qualquer coisa. Cada parser devolve `unparseable` em vez de lançar. Testado com um teste que percorre todos os parsers com objectos estranhos (`tests/test_normalize.py::test_valores_inesperados_nunca_lancam_excepcao`).
3. **Montantes por extenso** são lidos, porque o dataset os usa e porque um modelo pode devolver a forma escrita. A leitura é determinista e os testes cobrem casos como `oito mil e oitocentos e quarenta e seis euros e oitenta e nove cêntimos` = 8846.89.

## Alternativas

- **Usar `dateutil` ou `babel`**: úteis, mas a ambiguidade `a/b/aaaa` continuaria a ser escolhida por omissão (`dayfirst`). Não expõe o conflito.
- **Pedir ao modelo que devolva ISO**: reduz o problema na origem, mas não elimina a necessidade de validar a saída.
- **Expressões regulares para tudo**: mais frágil para números por extenso.

## Como falha

- Formas não cobertas (por exemplo "no início do mês passado") ficam `unparseable`. O campo vai para revisão. A taxa aparece na experiência.
- Montantes com ponto de milhares e três casas decimais (`1.250`) são lidos como 1250 no formato pt-PT. Um valor en como `1.250` (1,25) fica errado. O formato pt-PT é a convenção do domínio e está documentado; o risco é aceite.
- Testes: `tests/test_normalize.py` (datas, montantes, matrículas, moedas, booleanos, valores inesperados) e `tests/test_numerals.py` (ida e volta de 0 a 999 999).

## Perguntas de entrevista

1. **Porque é que `3/2/2026` é ambíguo mas `18/02/2026` não?** Porque 18 não pode ser mês. Só há uma leitura válida. Com `3/2`, ambas as leituras são datas reais.
2. **Porque devolver `options` em vez de escolher uma data?** Para que a revisão humana veja as duas opções e para que o sistema não aceite nenhuma automaticamente.
3. **O que é uma função pura e defensiva neste contexto?** Uma função que devolve sempre um `NormResult`, não depende de estado, não lança excepção com entradas de tipo errado e trata `None` como ausência.
4. **Porque é que a plegagem não pode mudar o comprimento?** Porque os offsets do texto plegado têm de corresponder aos do original para a evidência apontar o sítio certo.
