"""Escrita do relatorio: Markdown, JSON e grafico qualidade-vs-custo. Os numeros vem da run."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from arbitrationlab.experiments.strategies import LABELS, STRATEGIES  # noqa: E402
from arbitrationlab.schema import CLAIM_FIELDS  # noqa: E402


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _money(value: float) -> str:
    return f"{value:.4f}"


def build_markdown(payload: dict[str, Any]) -> str:
    meta = payload["meta"]
    summaries = payload["summaries"]
    analysis = payload["analysis"]
    lines: list[str] = [
        f"# Relatório da experiência — provider: {meta['provider']}",
        "",
        f"- Modo: **{meta['mode']}** (provider: `{meta['provider']}`; custos e respostas são simulados)",
        f"- Data (UTC): {meta['generated_at']}",
        f"- Commit do código: `{meta['commit']}`"
        + (" (árvore com alterações não commitadas)" if meta["dirty"] else ""),
        f"- Dataset: {meta['dataset_cases']} casos, sha256 `{meta['dataset_sha256'][:16]}…`; "
        f"calibração {meta['n_calibration']}, avaliação {meta['n_evaluation']}",
        f"- Custo de revisão humana simulado: {meta['review_cost_usd']} USD por campo revisto",
        "- Preços simulados por chamada: "
        + ", ".join(f"`{k}` {v} USD" for k, v in meta["prices"].items()),
        f"- Confiança: regressão logística ajustada no split de calibração "
        f"(`fitted={meta['calibrator']['fitted']}`, n={meta['calibrator']['n_train']})",
        "",
        "## Qualidade vs custo (split de avaliação)",
        "",
        "| Estratégia | Exact match | F1 macro | Cobertura | Erros críticos | Revisão | Custo/caso (USD) | Custo total (USD) | Latência média (ms) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for key in STRATEGIES:
        s = summaries[key]
        lines.append(
            f"| {LABELS[key]} | {_pct(s['exact_match'])} | {s['macro_f1']:.3f} | {_pct(s['coverage'])} | "
            f"{_pct(s['critical_error_rate'])} | {_pct(s['review_rate'])} | {_money(s['mean_cost_usd'])} | "
            f"{_money(s['total_cost_usd'])} | {s['mean_latency_ms']:.2f} |"
        )
    lines += ["", "![qualidade vs custo](mock-accuracy-vs-cost.png)", "", "## F1 por campo", ""]
    lines.append("| Estratégia | " + " | ".join(CLAIM_FIELDS) + " |")
    lines.append("|---|" + "---|" * len(CLAIM_FIELDS))
    for key in STRATEGIES:
        row = [f"{summaries[key]['field_f1'][f]:.3f}" for f in CLAIM_FIELDS]
        lines.append(f"| {LABELS[key]} | " + " | ".join(row) + " |")
    difficulties = sorted(summaries[STRATEGIES[0]]["exact_match_by_difficulty"])
    lines += ["", "## Exact match por dificuldade", ""]
    lines.append("| Estratégia | " + " | ".join(difficulties) + " |")
    lines.append("|---|" + "---|" * len(difficulties))
    for key in STRATEGIES:
        by = summaries[key]["exact_match_by_difficulty"]
        lines.append(
            f"| {LABELS[key]} | " + " | ".join(_pct(by.get(d, 0.0)) for d in difficulties) + " |"
        )
    corr = analysis["correlated_dates"]
    lines += [
        "",
        "## Erros correlacionados (data)",
        "",
        f"- Casos em que `cheap-a` e `cheap-b` dão a mesma data errada: **{corr['total']}**",
        f"- Apanhados pela evidência (não aceites): **{corr['caught']}**",
        f"- Escaparam (aceites com valor errado): **{corr['escaped']}**",
        "",
    ]
    for example in corr["examples"][:5]:
        lines.append(
            f"- `{example['case_id']}`: gold {example['gold']}, errado {example['wrong_value']}, "
            f"decisão por evidência `{example['evidence_decision']}`, maioria final {example['majority_final']}"
        )
    wrong = analysis["accepted_wrong"]
    lines += ["", "## Valores aceites erradamente pela arbitragem por evidência", ""]
    lines.append(f"Total: **{len(wrong)}** campos.")
    for item in wrong[:8]:
        lines.append(
            f"- `{item['case_id']}` ({item['difficulty']}) campo `{item['field']}`: "
            f"aceite {item['accepted']}, gold {item['gold']}"
        )
    free = analysis["cost_without_gain"]
    lines += [
        "",
        "## Custo sem ganho",
        "",
        f"Casos em que a arbitragem com revisão custa mais do que o modelo barato, que já acertava: "
        f"**{free['count']}** (exemplos: {', '.join(free['case_ids']) or 'nenhum'}).",
        "",
        "## Sensibilidade ao custo de revisão (arbitragem + revisão)",
        "",
        "| Custo de revisão por campo (USD) | Custo médio por caso (USD) |",
        "|---|---|",
    ]
    for row in analysis["sensitivity"]:
        lines.append(f"| {row['review_cost_usd']:.2f} | {_money(row['mean_cost_usd'])} |")
    lines += [
        "",
        "## Limitações",
        "",
        "- Mock determinista: os erros são injectados por perfis, não medidos em modelos reais. "
        "Os números NÃO representam desempenho de LLMs.",
        "- A revisão humana é simulada a partir dos labels, o que é optimista: um revisor real pode errar.",
        "- O split de avaliação tem poucos casos por dificuldade; intervalos de confiança não foram calculados.",
        "- Latência é medida na máquina de execução e não representa a latência de APIs de modelos.",
        "- Execução com modelos reais: pendente (requer chaves e execução manual, identificada como `provider: <modelo>`).",
        "",
    ]
    return "\n".join(lines)


def write_plot(path: Path, summaries: dict[str, dict[str, Any]]) -> None:
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for key in STRATEGIES:
        s = summaries[key]
        ax.scatter(s["mean_cost_usd"], s["exact_match"], s=60)
        ax.annotate(LABELS[key], (s["mean_cost_usd"], s["exact_match"]),
                    textcoords="offset points", xytext=(6, 4), fontsize=8)  # fmt: skip
    ax.set_xlabel("custo médio por caso (USD, simulado)")
    ax.set_ylabel("exact match (avaliação)")
    ax.set_title("Qualidade vs custo — provider: mock")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def write_outputs(out_dir: Path, payload: dict[str, Any]) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    mode = payload["meta"]["mode"]
    markdown = out_dir / f"{mode}-report.md"
    plot = out_dir / f"{mode}-accuracy-vs-cost.png"
    data = out_dir / f"{mode}-results.json"
    write_plot(plot, payload["summaries"])
    markdown.write_text(build_markdown(payload), encoding="utf-8", newline="\n")
    data.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
                    newline="\n")  # fmt: skip
    return {"markdown": markdown, "plot": plot, "json": data}
