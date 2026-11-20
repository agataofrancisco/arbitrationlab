# 04 — Calibração e ECE

## O problema

Um score de confiança só serve se for honesto. Se o sistema diz 0.9 para um conjunto de casos em que acerta 50% das vezes, os limiares de aceitação deixam passar erros. A calibração mede se as probabilidades correspondem às frequências reais.

## O que entra e o que sai

- **Entra**: para cada campo, três features: `agreement` (acordo), `evidence` (score de evidência) e `reliability` (fiabilidade média dos modelos que concordam). Na calibração, também a etiqueta: o valor proposto estava certo?
- **Sai**: uma confiança em [0, 1]. Nas métricas, o ECE (expected calibration error) e o diagrama de fiabilidade.

Exemplo real do ECE (`expected_calibration_error`):

```
[0.9]*10 com acertos [1,1,1,1,1,0,0,0,0,0] -> ECE = 0.4
```

Uma confiança de 0.9 com 50% de acerto dá um erro de calibração de 0.4.

## Como funciona por dentro

1. **Fiabilidade Beta** (`src/arbitrationlab/calibration/reliability.py:15-38`): para cada par `(modelo, campo)`, conta acertos e erros e devolve a média posterior de `Beta(α₀ + acertos, β₀ + erros)`. Sem histórico, o prior dá 0.5.
2. **Score** (`src/arbitrationlab/calibration/scoring.py:27-60`): regressão logística sobre as três features. Sem calibração feita, usam-se pesos fixos (`intercept -4`, `pesos 3, 3, 2`), que são uma baseline explicável. Com dados, `fit` usa `LogisticRegression` do scikit-learn com `C=1`. Se a amostra tiver uma só classe, mantém-se a taxa observada como probabilidade constante.
3. **ECE** (`src/arbitrationlab/calibration/metrics.py:41-56`): divide as confianças em 10 intervalos. Em cada intervalo, mede-se `|acerto - confiança média|` e pondera-se pelo número de casos. Soma-se tudo.
4. **Separação de dados**: a fiabilidade e o `fit` usam só o split de calibração (40% do dataset). A avaliação usa o restante (60%). Assim não há fuga de informação.

## Porquê esta escolha

- **Regressão logística** dá probabilidades, é explicável pelos coeficientes e funciona com poucos dados. Uma árvore ou uma rede neural exigiria mais dados e seria opaca numa auditoria.
- **Prior Beta** evita que um modelo com 2 casos tenha fiabilidade 1.0. Com poucos dados, a média fica perto de 0.5.
- **ECE** é uma métrica simples e comparável. Um diagrama de fiabilidade mostra onde falha.

## Alternativas

- **Regra ponderada fixa sem treino**: o que o sistema usa sem calibração. Bom para começar, mas não se sabe se está calibrada.
- **Platt scaling ou isotonic regression**: calibram um score já existente. Não permitem combinar três features com interpretação directa.
- **Brier score**: também mede calibração, mas mistura calibração e discriminação. O ECE isola melhor a calibração.

## Como falha

- **Poucos dados**: com 48 casos de calibração e 10 intervalos, alguns intervalos ficam vazios ou com 1 ou 2 casos. O ECE desses intervalos é ruído. Por isso o diagrama mostra a contagem em cada um.
- **Mudança de distribuição**: se os documentos reais forem diferentes do dataset sintético, a calibração não se transfere. Os números do projecto são de mock e estão marcados como tal.
- **Fiabilidade enviesada**: se a fiabilidade for estimada com erros correlacionados, o modelo aprende que dois modelos concordantes são fiáveis. A evidência é a defesa.
- **Testes**: `tests/test_calibration.py` (ECE zero para uma calibração perfeita e 0.4 para o caso de 0.9 com 50%, prior Beta, fit com uma classe, separação logística).

## Perguntas de entrevista

1. **O que é o ECE?** A média ponderada, por intervalo de confiança, do desvio entre a confiança média e a taxa de acerto observada.
2. **Porque é que o ECE pode ser zero e o sistema continuar mau?** Porque o ECE mede calibração, não discriminação. Um sistema que dá 0.5 a tudo e acerta 50% tem ECE zero e é inútil.
3. **Porque é que o `fit` não usa o split de avaliação?** Para não haver fuga de informação. Os números de avaliação só fazem sentido se os parâmetros foram aprendidos sem os ver.
4. **Porque é que a fiabilidade começa em 0.5?** É o prior neutro de Beta(1,1). Um modelo sem histórico não deve ser nem confiável nem não confiável.
