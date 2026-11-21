"""Corre a experiencia: calibracao no split de calibracao, avaliacao no split de avaliacao.

Uso: python -m arbitrationlab.experiments.run --mode mock --out experiments/reports
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from arbitrationlab.calibration import ConfidenceModel, ReliabilityTable
from arbitrationlab.config import Settings
from arbitrationlab.dataset.validate import load_jsonl
from arbitrationlab.decision import Policy
from arbitrationlab.experiments.analysis import (
    accepted_wrong,
    correlated_date_errors,
    cost_without_gain,
    review_cost_sensitivity,
)
from arbitrationlab.experiments.metrics import summarize
from arbitrationlab.experiments.report import write_outputs
from arbitrationlab.experiments.strategies import (
    STRATEGIES,
    CaseResult,
    normalized_output,
    run_strategy,
    same_value,
)
from arbitrationlab.generation.registry import (
    CHEAP_A,
    CHEAP_B,
    STRONG_C,
    VERIFIER,
    default_mock_models,
)
from arbitrationlab.generation.runner import generate_candidates
from arbitrationlab.pipeline import arbitrate_sync
from arbitrationlab.schema import claim_output_schema, field_specs

ROOT = Path(__file__).resolve().parents[3]
DATASET_DIR = ROOT / "datasets" / "claims"
CALIBRATION_MODELS = (CHEAP_A, CHEAP_B, STRONG_C)


def _git(*args: str) -> str:
    # git local com argumentos fixos; nao recebe entrada do utilizador.
    result = subprocess.run(  # noqa: S603 - git local, argumentos fixos
        ["git", *args],  # noqa: S607
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _git_commit() -> tuple[str, bool]:
    try:
        commit = _git("rev-parse", "HEAD")
        status = _git("status", "--porcelain")
    except (OSError, subprocess.CalledProcessError):
        return "desconhecido", True
    return commit, bool(status)


def fit_calibration(
    cases: list[dict[str, Any]], models: dict[str, Any]
) -> tuple[ReliabilityTable, ConfidenceModel]:
    """Fiabilidade por (modelo, campo) e regressao de confianca, so com o split de calibracao."""
    schema = claim_output_schema()
    specs = field_specs(schema)
    providers = [models[n] for n in CALIBRATION_MODELS]
    reliability = ReliabilityTable()
    for case in cases:
        records = asyncio.run(generate_candidates(
            case["text"], schema, providers, max_spend=1.0, timeout_s=5.0
        ))  # fmt: skip
        for record in records:
            if not record.usable:
                continue
            norm = normalized_output(record.output)
            for name, spec in specs.items():
                gold = case["gold"][name]
                if gold is None:
                    continue
                reliability.observe(
                    record.model, name, same_value(spec["x-type"], norm[name], gold)
                )
    features: list[list[float]] = []
    outcomes: list[int] = []
    policy = Policy(max_spend=0.05, timeout_s=5.0)
    for case in cases:
        outcome = arbitrate_sync(
            case["text"], schema, providers, policy=policy,
            reliability=reliability, verifier=models[VERIFIER],
        )  # fmt: skip
        for name, verdict in outcome.verdicts.items():
            if verdict.suggested_value is None:
                continue
            features.append(list(verdict.features))
            outcomes.append(int(same_value(specs[name]["x-type"], verdict.suggested_value,
                                           case["gold"][name])))  # fmt: skip
    calibrator = ConfidenceModel()
    calibrator.fit(features, outcomes)
    return reliability, calibrator


def run_experiment(
    *,
    out_dir: Path,
    dataset_dir: Path = DATASET_DIR,
    review_cost_usd: float | None = None,
) -> dict[str, Any]:
    settings = Settings.from_env()
    review_cost = settings.human_review_cost_usd if review_cost_usd is None else review_cost_usd
    cases = load_jsonl(dataset_dir / "claims.jsonl")
    manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    calibration = [c for c in cases if c["split"] == "calibration"]
    evaluation = [c for c in cases if c["split"] == "evaluation"]
    models = default_mock_models()
    reliability, calibrator = fit_calibration(calibration, models)

    results: dict[str, list[CaseResult]] = {s: [] for s in STRATEGIES}
    for case in evaluation:
        for strategy in STRATEGIES:
            results[strategy].append(
                run_strategy(
                    strategy,
                    case,
                    models,
                    reliability=reliability,
                    calibrator=calibrator,
                    review_cost_usd=review_cost,
                )  # fmt: skip
            )
    summaries = {s: summarize(results[s]) for s in STRATEGIES}
    by_id = {c["id"]: c for c in evaluation}
    commit, dirty = _git_commit()
    payload = {
        "meta": {
            "mode": "mock",
            "provider": "mock",
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "commit": commit,
            "dirty": dirty,
            "dataset_cases": manifest["n_cases"],
            "dataset_sha256": manifest["sha256"],
            "n_calibration": len(calibration),
            "n_evaluation": len(evaluation),
            "review_cost_usd": review_cost,
            "prices": {
                CHEAP_A: models[CHEAP_A].cost_per_call_usd,
                STRONG_C: models[STRONG_C].cost_per_call_usd,
                VERIFIER: models[VERIFIER].cost_per_call_usd,
            },
            "calibrator": {
                "fitted": calibrator.fitted,
                "n_train": calibrator.n_train,
                "intercept": calibrator.intercept,
                "weights": list(calibrator.weights),
            },
        },
        "summaries": summaries,
        "analysis": {
            "correlated_dates": correlated_date_errors(
                by_id, results["evidence_arbitration"], results["majority_vote"]
            ),
            "accepted_wrong": accepted_wrong(results["evidence_arbitration"]),
            "cost_without_gain": cost_without_gain(
                results["cheap_single"], results["arbitration_review"]
            ),
            "sensitivity": review_cost_sensitivity(results["arbitration_review"]),
        },
    }
    payload["outputs"] = {k: str(v) for k, v in write_outputs(out_dir, payload).items()}
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Experiencia comparativa de estrategias.")
    parser.add_argument("--mode", choices=["mock", "real"], default="mock")
    parser.add_argument("--out", type=Path, default=ROOT / "experiments" / "reports")
    parser.add_argument("--review-cost", type=float, default=None)
    args = parser.parse_args()
    if args.mode == "real":
        raise SystemExit(
            "modo real nao executado: requer chaves de API e execução manual (ver docs/)."
        )
    payload = run_experiment(out_dir=args.out, review_cost_usd=args.review_cost)
    for key in STRATEGIES:
        s = payload["summaries"][key]
        print(f"{key:22s} exact={s['exact_match']:.3f} f1={s['macro_f1']:.3f} "
              f"cost/caso={s['mean_cost_usd']:.4f}")  # fmt: skip
    print(json.dumps(payload["outputs"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
