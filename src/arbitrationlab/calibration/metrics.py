"""Metricas de calibracao: expected calibration error (ECE) e diagrama de fiabilidade."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


def _bin_index(confidence: float, n_bins: int) -> int:
    return min(int(confidence * n_bins), n_bins - 1)


def reliability_bins(
    confidences: Sequence[float], outcomes: Sequence[int], n_bins: int = 10
) -> list[dict[str, Any]]:
    """Por cada intervalo de confianca: contagem, confianca media e taxa de acerto."""
    if len(confidences) != len(outcomes):
        raise ValueError("confidences e outcomes tem de ter o mesmo tamanho")
    if n_bins < 1:
        raise ValueError("n_bins tem de ser pelo menos 1")
    buckets: list[list[tuple[float, int]]] = [[] for _ in range(n_bins)]
    for confidence, outcome in zip(confidences, outcomes, strict=True):
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("as confiancas tem de estar em [0, 1]")
        buckets[_bin_index(confidence, n_bins)].append((confidence, int(outcome)))
    bins: list[dict[str, Any]] = []
    for index, bucket in enumerate(buckets):
        count = len(bucket)
        bins.append(
            {
                "lower": index / n_bins,
                "upper": (index + 1) / n_bins,
                "count": count,
                "mean_confidence": sum(c for c, _ in bucket) / count if count else None,
                "accuracy": sum(o for _, o in bucket) / count if count else None,
            }
        )
    return bins


def expected_calibration_error(
    confidences: Sequence[float], outcomes: Sequence[int], n_bins: int = 10
) -> float:
    """ECE = soma sobre os intervalos de (n_b / N) * |acerto_b - confianca_b|. Zero se vazio."""
    total = len(confidences)
    if total == 0:
        return 0.0
    error = 0.0
    for item in reliability_bins(confidences, outcomes, n_bins):
        if item["count"]:
            gap = abs(item["accuracy"] - item["mean_confidence"])
            error += item["count"] / total * gap
    return error
