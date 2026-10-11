from pathlib import Path

from denso_a1.safety_gate import build_retrospective, evaluate_candidate


def _candidate(status: str) -> dict:
    gates = {name: {"status": status} for name in ("provenance", "fidelity", "novelty", "utility")}
    return {"method": "test", **gates}


def test_admission_requires_all_four_pass() -> None:
    assert evaluate_candidate(_candidate("PASS"))["admission"] == "ACCEPT"
    candidate = _candidate("PASS")
    candidate["novelty"] = {"status": "UNKNOWN"}
    assert evaluate_candidate(candidate)["admission"] == "REJECT"


def test_retrospective_contains_all_frozen_branches() -> None:
    repo = Path(__file__).parents[1]
    candidates = build_retrospective(repo)
    assert [candidate["method"] for candidate in candidates] == [
        "T0",
        "T0-v2",
        "T2 conditional-VAE",
        "T3 fault-preserving augmentation",
    ]
    assert all(candidate["admission"] == "REJECT" for candidate in candidates)
    assert candidates[0]["fidelity"]["c2st_roc_auc_mean"] == 1.0
    assert candidates[0]["fidelity"]["spectral_js_mean"] > 0.0
    assert candidates[2]["fidelity"]["c2st_roc_auc_max"] == 1.0
    assert candidates[3]["novelty"]["status"] == "FAIL"
