"""Calibracao: fiabilidade historica (Beta), score de confianca e metricas (ECE)."""

from arbitrationlab.calibration.metrics import expected_calibration_error, reliability_bins
from arbitrationlab.calibration.reliability import ReliabilityTable
from arbitrationlab.calibration.scoring import FEATURE_NAMES, ConfidenceModel

__all__ = [
    "FEATURE_NAMES",
    "ConfidenceModel",
    "ReliabilityTable",
    "expected_calibration_error",
    "reliability_bins",
]
