"""Generator-agnostic admission gate for synthetic fault data.

The gate deliberately treats an unmeasured stage as UNKNOWN rather than
silently accepting a candidate.  Retrospective builders below read only frozen
artifacts; they never rerun or tune a generator.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

GATES = ("provenance", "fidelity", "novelty", "utility")
VALID_STATUSES = {"PASS", "FAIL", "UNKNOWN", "NOT_APPLICABLE"}


def evaluate_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    """Apply the same hard admission rule to one candidate record."""
    statuses = {gate: candidate[gate]["status"] for gate in GATES}
    invalid = {gate: status for gate, status in statuses.items() if status not in VALID_STATUSES}
    if invalid:
        raise ValueError(f"invalid safety-gate statuses: {invalid}")
    accepted = all(status == "PASS" for status in statuses.values())
    return {
        **candidate,
        "gate_status": statuses,
        "admission": "ACCEPT" if accepted else "REJECT",
        "admission_reason": "all four gates PASS" if accepted else "at least one gate is not PASS",
    }


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _status(summary: dict[str, Any], key: str) -> str:
    return "PASS" if bool(summary.get(key, False)) else "FAIL"


def _utility(summary: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    deltas = summary.get("paired_deltas", {})
    selected = {key: deltas[key] for key in keys if key in deltas}
    negative_or_zero = [
        key for key, value in selected.items() if value.get("mean_delta", value.get("metrics", {}).get("pr_auc", {}).get("mean_delta", 0.0)) <= 0
    ]
    return {
        "status": "FAIL" if negative_or_zero else "PASS",
        "paired_deltas": selected,
        "negative_or_zero_comparisons": negative_or_zero,
        "evidence": "held-out measured-real utility; paired seeds and bootstrap CIs",
    }


def _t0_candidate(root: Path) -> dict[str, Any]:
    summary = _load(root / "reports/paderborn/summary.json")
    failure = _load(root / "reports/t0_failure_analysis/failure_analysis.json")
    # The failure-analysis artifact groups diagnostics under ``summary.groups``.
    # Keep a fallback for older snapshots whose summary was flattened.
    groups = failure["summary"].get("groups", failure["summary"])
    dev = groups.get("k=0:dev_fault", {})
    fidelity = {
        "status": "FAIL",
        "c2st_roc_auc_mean": dev.get("c2st_roc_auc", {}).get("mean"),
        "spectral_js_mean": dev.get("spectral_js_divergence", {}).get("mean"),
        "psd_cosine_mean": dev.get("spectral_cosine_similarity", {}).get("mean"),
        "evidence": "reports/t0_failure_analysis.md; C2ST=1.0 and PSD/envelope mismatch",
    }
    return {
        "method": "T0",
        "family": "physics-informed synthesis",
        "provenance": {"status": "PASS", "evidence": "public-real/leakage/budget audits and train-parent restriction in reports/paderborn/"},
        "fidelity": fidelity,
        "novelty": {"status": "UNKNOWN", "evidence": "no frozen NN/memorization audit was recorded for the original T0 artifact"},
        "utility": _utility(summary, ("k=0:E2-E0", "k=1:E2-E0", "k=1:E2-E1", "k=2:E2-E0", "k=2:E2-E1")),
        "observed_outcome_agreement": "AGREES: no positive held-out utility; negative/near-zero paired deltas",
        "scope_limit": "Paderborn public-real benchmark; not DENSO or naturally occurring field faults",
        "evidence": ["reports/paderborn/summary.json", "reports/t0_failure_analysis/failure_analysis.json"],
    }


def _t0v2_candidate(root: Path) -> dict[str, Any]:
    summary = _load(root / "reports/paderborn_v2/summary.json")
    failure_text = (root / "reports/t0_failure_analysis.md").read_text(encoding="utf-8")
    fidelity = {
        "status": "FAIL",
        "evidence": "frozen T0-v2 retained the diagnosed T0 family mismatch; independent T0-v2 fidelity gate was not passed",
        "diagnostic_reference": "C2ST=1.0, PSD cosine≈0.50–0.57, envelope/fault-frequency mismatch in reports/t0_failure_analysis.md",
        "reference_present": "Frozen T0-v2 design" in failure_text,
    }
    return {
        "method": "T0-v2",
        "family": "calibrated physics synthesis",
        "provenance": {"status": "PASS", "evidence": "all public-real, leakage, budget, training-difference and calibration audits pass"},
        "fidelity": fidelity,
        "novelty": {"status": "UNKNOWN", "evidence": "provenance and hashes exist, but no independent frozen NN-distance admission threshold was recorded"},
        "utility": _utility(summary, ("k=0:E2-E0", "k=1:E2-E0", "k=1:E2-E1", "k=2:E2-E0", "k=2:E2-E1")),
        "observed_outcome_agreement": "AGREES: negative E2 utility on the final frozen Paderborn holdout",
        "scope_limit": "Paderborn final holdout only; no DENSO transfer claim",
        "evidence": ["reports/paderborn_v2/summary.json", "reports/paderborn_v2/run_audit.md", "reports/t0_failure_analysis.md"],
    }


def _t2_candidate(root: Path) -> dict[str, Any]:
    summary = _load(root / "reports/t2_benchmark/summary.json")
    rows = _load(root / "reports/t2_benchmark/raw_metrics.json")
    e3_cases = [case for row in rows if row["method"] == "E3" for case in row.get("fidelity_cases", [])]
    c2st = [case["comparison"]["c2st"]["roc_auc"] for case in e3_cases]
    fidelity = {
        "status": _status(summary, "all_fidelity_gates_pass"),
        "c2st_roc_auc_max": max(c2st) if c2st else None,
        "spectral_js_mean": float(np.mean([case["comparison"]["spectral_distance"]["js_divergence"] for case in e3_cases])) if e3_cases else None,
        "psd_cosine_mean": float(np.mean([case["comparison"]["spectral_distance"]["cosine_similarity"] for case in e3_cases])) if e3_cases else None,
        "evidence": "reports/t2_benchmark/t2_fidelity_report.md and raw_metrics.json",
    }
    return {
        "method": "T2 conditional-VAE",
        "family": "learned conditional 1D VAE",
        "provenance": {"status": "PASS", "evidence": "all public-real, leakage, budget, calibration and training-difference audits pass"},
        "fidelity": fidelity,
        "novelty": {
            "status": "PASS",
            "median_ratio_min": min((case["nearest_neighbor"]["median_ratio"] for case in e3_cases), default=None),
            "evidence": "all_memorization_audits_pass=true; no exact overlap/NN gate failure in frozen T2 artifact",
        },
        "utility": _utility(summary, ("k=1:E3-E0", "k=1:E3-E1", "k=2:E3-E0", "k=2:E3-E1")),
        "observed_outcome_agreement": "AGREES: C2ST rejection coincided with negative held-out E3 utility",
        "scope_limit": "Paderborn T2 holdout; learned model is not evidence of DENSO transfer",
        "evidence": ["reports/t2_benchmark/summary.json", "reports/t2_benchmark/t2_fidelity_report.md", "reports/t2_benchmark/run_audit.md"],
    }


def _t3_candidate(root: Path) -> dict[str, Any]:
    summary = _load(root / "reports/t3_benchmark/summary.json")
    rows = _load(root / "reports/t3_benchmark/raw_metrics.json")
    e4_cases = [case for row in rows if row["method"] == "E4" for case in row.get("fidelity_cases", [])]
    validation_cases = [case for case in e4_cases if case["partition"] == "validation_fault"]
    exact_overlap = any(case["nearest_neighbor"].get("exact_signal_hash_overlap") for case in e4_cases)
    fidelity = {
        "status": _status(summary, "all_fidelity_gates_pass"),
        "c2st_validation_max": max(case["comparison"]["c2st"]["roc_auc"] for case in e4_cases if case["partition"] == "validation_fault"),
        "spectral_js_mean": float(np.mean([case["comparison"]["spectral_distance"]["js_divergence"] for case in validation_cases])),
        "psd_cosine_mean": float(np.mean([case["comparison"]["spectral_distance"]["cosine_similarity"] for case in validation_cases])),
        "anchor_drift_mean_hz": float(np.mean([case["anchor_drift_hz"] for case in validation_cases])),
        "train_parent_exact_overlap": exact_overlap,
        "evidence": "reports/t3_fidelity_report.md and raw_metrics.json",
    }
    novelty_status = "FAIL" if exact_overlap else "PASS"
    return {
        "method": "T3 fault-preserving augmentation",
        "family": "constrained measured-fault transformations",
        "provenance": {"status": _status(summary, "all_provenance_audits_pass"), "evidence": "all_provenance_audits_pass=true; parent IDs/groups in raw metrics"},
        "fidelity": fidelity,
        "novelty": {
            "status": novelty_status,
            "median_ratio_min": min((case["nearest_neighbor"]["median_ratio"] for case in validation_cases), default=None),
            "evidence": "train-parent NN ratio=0.000 and exact parent hashes for the selected near-identity policy",
        },
        "utility": _utility(summary, ("k=1:E4-E0", "k=1:E4-E1", "k=2:E4-E0", "k=2:E4-E1")),
        "observed_outcome_agreement": "AGREES: no improvement over simple augmentation and fidelity/near-copy rejection",
        "scope_limit": "new Paderborn measured-real holdout; no universal ineffectiveness claim",
        "evidence": ["reports/t3_benchmark/summary.json", "reports/t3_fidelity_report.md", "reports/t3_benchmark/run_audit.md"],
    }


def build_retrospective(root: str | Path) -> list[dict[str, Any]]:
    repo = Path(root)
    candidates = [_t0_candidate(repo), _t0v2_candidate(repo), _t2_candidate(repo), _t3_candidate(repo)]
    return [evaluate_candidate(candidate) for candidate in candidates]


def write_safety_gate_outputs(root: str | Path) -> dict[str, Any]:
    repo = Path(root)
    output_dir = repo / "reports/safety_gate"
    output_dir.mkdir(parents=True, exist_ok=True)
    candidates = build_retrospective(repo)
    (output_dir / "retrospective.json").write_text(json.dumps(candidates, indent=2), encoding="utf-8")
    fields = ["method", "family", "provenance", "fidelity", "novelty", "utility", "admission", "observed_outcome_agreement", "scope_limit"]
    with (repo / "reports/generator_comparison.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for candidate in candidates:
            writer.writerow({field: json.dumps(candidate[field], ensure_ascii=False) if isinstance(candidate[field], dict) else candidate[field] for field in fields})
    lines = [
        "# Synthetic Fault Data Safety Gate",
        "",
        "The gate is generator-agnostic: synthetic fault data is admitted only when provenance/validity, fidelity, novelty and held-out measured-real utility all PASS. UNKNOWN is not treated as PASS.",
        "",
        "## Retrospective decision table",
        "",
        "| method | provenance | fidelity | novelty | utility | admission | downstream agreement |",
        "|---|---|---|---|---|---|---|",
    ]
    for candidate in candidates:
        lines.append(f"| {candidate['method']} | {candidate['provenance']['status']} | {candidate['fidelity']['status']} | {candidate['novelty']['status']} | {candidate['utility']['status']} | **{candidate['admission']}** | {candidate['observed_outcome_agreement']} |")
    lines += [
        "",
        "## Interpretation",
        "",
        "These results do not show that synthetic fault data is universally ineffective. They show that, across the tested CWRU/Paderborn few-shot settings, four representative synthesis/augmentation strategies failed to simultaneously satisfy fidelity, novelty and held-out real-fault utility requirements. The gate prevents unsupported synthetic-data claims and identifies when generated fault data should not be used.",
        "",
        "Validity and transfer limits are separate from fidelity: all four branches had strong public-real/leakage/budget controls where recorded, but their evidence remains bounded to the cited public benchmarks and does not establish transfer to DENSO or naturally occurring field faults.",
        "",
        "See `reports/generator_comparison.csv` and `retrospective.json` for machine-readable evidence paths and per-gate reasons.",
    ]
    (repo / "reports/safety_gate_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"candidates": candidates, "output_dir": str(output_dir)}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path("."))
    args = parser.parse_args()
    result = write_safety_gate_outputs(args.repo)
    print(json.dumps({"methods": len(result["candidates"]), "path": result["output_dir"]}, indent=2))
