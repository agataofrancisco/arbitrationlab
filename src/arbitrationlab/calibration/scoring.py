"""Score de confianca: regressao logistica sobre (acordo, evidencia, fiabilidade).

Antes de existir um split de calibracao usam-se pesos fixos (baseline explicavel). Depois de
`fit`, os pesos vem da regressao logistica do scikit-learn. Se a amostra tiver so uma classe,
a regressao nao e possivel e mantem-se uma probabilidade constante com a taxa observada.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from sklearn.linear_model import LogisticRegression

FEATURE_NAMES: tuple[str, ...] = ("agreement", "evidence", "reliability")
DEFAULT_INTERCEPT = -4.0
DEFAULT_WEIGHTS: tuple[float, float, float] = (3.0, 3.0, 2.0)


def _sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    exp_z = math.exp(z)
    return exp_z / (1.0 + exp_z)


class ConfidenceModel:
    def __init__(self) -> None:
        self.intercept = DEFAULT_INTERCEPT
        self.weights: tuple[float, ...] = DEFAULT_WEIGHTS
        self.fitted = False
        self.n_train = 0

    def fit(self, features: Sequence[Sequence[float]], outcomes: Sequence[int]) -> None:
        """Ajusta a regressao. `outcomes` e 1 se o valor proposto estava certo, 0 caso contrario."""
        if len(features) != len(outcomes):
            raise ValueError("features e outcomes tem de ter o mesmo tamanho")
        if not features:
            raise ValueError("sao precisos exemplos de calibracao")
        if any(len(row) != len(FEATURE_NAMES) for row in features):
            raise ValueError(f"cada linha tem de ter {len(FEATURE_NAMES)} features")
        self.n_train = len(features)
        if len(set(outcomes)) < 2:
            rate = min(max(sum(outcomes) / len(outcomes), 1e-3), 1 - 1e-3)
            self.intercept = math.log(rate / (1 - rate))
            self.weights = tuple(0.0 for _ in FEATURE_NAMES)
        else:
            model = LogisticRegression(C=1.0, max_iter=1000)
            model.fit([list(map(float, row)) for row in features], list(outcomes))
            self.intercept = float(model.intercept_[0])
            self.weights = tuple(float(w) for w in model.coef_[0])
        self.fitted = True

    def predict(self, features: Sequence[float]) -> float:
        if len(features) != len(FEATURE_NAMES):
            raise ValueError(f"sao precisas {len(FEATURE_NAMES)} features")
        z = self.intercept + sum(w * float(x) for w, x in zip(self.weights, features, strict=True))
        return _sigmoid(z)
