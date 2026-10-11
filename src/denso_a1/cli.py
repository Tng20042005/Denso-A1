from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from denso_a1.benchmark import run_benchmark
from denso_a1.data.simulated import make_simulated_dataset
from denso_a1.generators.physics import PhysicsConfig, T0Generator, envelope_spectrum


def _demo(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    corpus = make_simulated_dataset(normal_groups=2, fault_groups=1, windows_per_group=2, seed=11)
    normal_index = int(np.flatnonzero(corpus.labels == 0)[0])
    generator = T0Generator(PhysicsConfig())
    generated = generator.generate_from_parents(corpus, [normal_index], seed=99, split_seed=0)
    frequencies, spectrum = envelope_spectrum(generated.signals[0], generated.metadata[0].fs_hz)
    np.savez_compressed(out / "demo_signals.npz", normal=corpus.signals[normal_index], generated=generated.signals[0], frequencies=frequencies, envelope_spectrum=spectrum)
    fig, axes = plt.subplots(2, 1, figsize=(10, 6), constrained_layout=True)
    axes[0].plot(corpus.signals[normal_index], label="normal simulated")
    axes[0].plot(generated.signals[0], label="T0 generated", alpha=0.8)
    axes[0].set_title("T0 mechanism-like injection")
    axes[0].legend()
    axes[1].plot(frequencies, spectrum)
    axes[1].axvline(generator.config.f_fault_hz, color="red", linestyle="--", label="f_fault")
    axes[1].set_xlim(0, 250)
    axes[1].set_title("Envelope spectrum diagnostic")
    axes[1].legend()
    fig.savefig(out / "t0_diagnostic.png", dpi=140)
    plt.close(fig)
    manifest = [item.to_dict() for item in generated.metadata]
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(prog="denso-a1")
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo")
    demo.add_argument("--out", type=Path, default=Path("reports/demo"))
    benchmark = sub.add_parser("benchmark")
    benchmark.add_argument("--out", type=Path, default=Path("reports/benchmark"))
    benchmark.add_argument("--seeds", type=int, default=5)
    public_benchmark = sub.add_parser("public-benchmark")
    public_benchmark.add_argument("--raw-root", type=Path, default=Path("data/raw/cwru"))
    public_benchmark.add_argument("--out", type=Path, default=Path("reports/cwru"))
    public_benchmark.add_argument("--seeds", type=int, default=5)
    public_benchmark.add_argument(
        "--split-mode", choices=("random_group", "cross_load"), default="random_group"
    )
    paderborn_benchmark = sub.add_parser("paderborn-benchmark")
    paderborn_benchmark.add_argument("--raw-root", type=Path, default=Path("data/raw/paderborn/extracted"))
    paderborn_benchmark.add_argument("--out", type=Path, default=Path("reports/paderborn"))
    paderborn_benchmark.add_argument("--seeds", type=int, default=5)
    paderborn_benchmark.add_argument("--condition", default="N15_M07_F10")
    paderborn_benchmark.add_argument("--measurements", type=int, default=5)
    report = sub.add_parser("report")
    report.add_argument("--benchmark", type=Path, default=Path("reports/benchmark"))
    public_report = sub.add_parser("public-report")
    public_report.add_argument("--benchmark", type=Path, default=Path("reports/cwru"))
    failure_analysis = sub.add_parser("t0-failure-analysis")
    failure_analysis.add_argument("--raw-root", type=Path, default=Path("data/raw/paderborn/extracted"))
    failure_analysis.add_argument("--out", type=Path, default=Path("reports/t0_failure_analysis"))
    failure_analysis.add_argument("--seeds", type=int, default=5)
    failure_analysis.add_argument("--condition", default="N15_M07_F10")
    failure_analysis.add_argument("--measurements", type=int, default=5)
    v2_freeze = sub.add_parser("t0-v2-freeze")
    v2_freeze.add_argument("--out", type=Path, default=Path("reports/t0_v2_protocol_freeze.json"))
    v2_freeze.add_argument("--measurements", type=int, default=5)
    v2_benchmark = sub.add_parser("paderborn-v2-benchmark")
    v2_benchmark.add_argument("--raw-root", type=Path, default=Path("data/raw/paderborn/extracted"))
    v2_benchmark.add_argument("--out", type=Path, default=Path("reports/paderborn_v2"))
    v2_benchmark.add_argument("--freeze", type=Path, default=Path("reports/t0_v2_protocol_freeze.json"))
    v2_benchmark.add_argument("--seeds", type=int, default=5)
    v2_benchmark.add_argument("--measurements", type=int, default=5)
    t2_freeze = sub.add_parser("t2-freeze")
    t2_freeze.add_argument("--out", type=Path, default=Path("reports/t2_protocol_freeze.json"))
    t2_benchmark = sub.add_parser("paderborn-t2-benchmark")
    t2_benchmark.add_argument("--raw-root", type=Path, default=Path("data/raw/paderborn/extracted"))
    t2_benchmark.add_argument("--out", type=Path, default=Path("reports/t2_benchmark"))
    t2_benchmark.add_argument("--freeze", type=Path, default=Path("reports/t2_protocol_freeze.json"))
    t2_benchmark.add_argument("--seeds", type=int, default=5)
    t2_benchmark.add_argument("--measurements", type=int, default=5)
    t2_report = sub.add_parser("t2-report")
    t2_report.add_argument("--benchmark", type=Path, default=Path("reports/t2_benchmark"))
    t3_development = sub.add_parser("t3-development")
    t3_development.add_argument("--raw-root", type=Path, default=Path("data/raw/paderborn/extracted"))
    t3_development.add_argument("--out", type=Path, default=Path("reports/t3_development"))
    t3_development.add_argument("--seeds", type=int, default=5)
    t3_development.add_argument("--measurements", type=int, default=5)
    t3_freeze = sub.add_parser("t3-freeze")
    t3_freeze.add_argument("--selection", type=Path, default=Path("reports/t3_development/selection.json"))
    t3_freeze.add_argument("--out", type=Path, default=Path("reports/t3_protocol_freeze.json"))
    t3_benchmark = sub.add_parser("paderborn-t3-benchmark")
    t3_benchmark.add_argument("--raw-root", type=Path, default=Path("data/raw/paderborn/extracted"))
    t3_benchmark.add_argument("--out", type=Path, default=Path("reports/t3_benchmark"))
    t3_benchmark.add_argument("--freeze", type=Path, default=Path("reports/t3_protocol_freeze.json"))
    t3_benchmark.add_argument("--seeds", type=int, default=5)
    t3_benchmark.add_argument("--measurements", type=int, default=5)
    safety_gate = sub.add_parser("safety-gate")
    safety_gate.add_argument("--repo", type=Path, default=Path("."))
    safety_gate_validate = sub.add_parser("safety-gate-validate")
    safety_gate_validate.add_argument("--repo", type=Path, default=Path("."))
    safety_gate_validate.add_argument("--raw-root", type=Path, default=Path("data/raw/paderborn/extracted"))
    safety_gate_validate.add_argument("--sample-count", type=int, default=128)
    args = parser.parse_args()
    if args.command == "demo":
        _demo(args.out)
        print(f"demo written to {args.out}")
    elif args.command == "benchmark":
        result = run_benchmark(args.out, seeds=args.seeds)
        print(json.dumps(result["summary"], indent=2))
    elif args.command == "public-benchmark":
        from denso_a1.public_benchmark import run_cwru_benchmark

        result = run_cwru_benchmark(
            args.raw_root, args.out, seeds=args.seeds, split_mode=args.split_mode
        )
        print(json.dumps(result["summary"], indent=2))
    elif args.command == "paderborn-benchmark":
        from denso_a1.paderborn_benchmark import run_paderborn_benchmark

        result = run_paderborn_benchmark(
            args.raw_root,
            args.out,
            seeds=args.seeds,
            condition_id=args.condition,
            measurement_indices=tuple(range(1, args.measurements + 1)),
        )
        print(json.dumps(result["summary"], indent=2))
    elif args.command == "report":
        from denso_a1.report import write_benchmark_report

        path = write_benchmark_report(args.benchmark)
        print(f"report written to {path}")
    elif args.command == "public-report":
        from denso_a1.public_report import write_public_benchmark_report

        path = write_public_benchmark_report(args.benchmark)
        print(f"public report written to {path}")
    elif args.command == "t0-failure-analysis":
        from denso_a1.failure_analysis import run_failure_analysis, write_failure_analysis_report

        run_failure_analysis(
            args.raw_root,
            args.out,
            seeds=args.seeds,
            condition_id=args.condition,
            measurement_indices=tuple(range(1, args.measurements + 1)),
        )
        path = write_failure_analysis_report(args.out)
        root_path = Path("reports/t0_failure_analysis.md")
        root_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"failure analysis written to {path} and {root_path}")
    elif args.command == "t0-v2-freeze":
        from denso_a1.paderborn_v2_benchmark import write_t0_v2_protocol_freeze

        path = write_t0_v2_protocol_freeze(
            args.out, measurements=tuple(range(1, args.measurements + 1))
        )
        print(f"T0-v2 protocol frozen at {path}")
    elif args.command == "paderborn-v2-benchmark":
        from denso_a1.paderborn_v2_benchmark import run_paderborn_v2_benchmark

        result = run_paderborn_v2_benchmark(
            args.raw_root,
            args.out,
            freeze_path=args.freeze,
            seeds=args.seeds,
            measurements=tuple(range(1, args.measurements + 1)),
        )
        print(json.dumps(result["summary"], indent=2))
    elif args.command == "t2-freeze":
        from denso_a1.paderborn_t2_benchmark import write_t2_protocol_freeze

        path = write_t2_protocol_freeze(args.out)
        print(f"T2 protocol frozen at {path}")
    elif args.command == "paderborn-t2-benchmark":
        from denso_a1.paderborn_t2_benchmark import run_paderborn_t2_benchmark

        result = run_paderborn_t2_benchmark(
            args.raw_root,
            args.out,
            freeze_path=args.freeze,
            seeds=args.seeds,
            measurements=tuple(range(1, args.measurements + 1)),
        )
        print(json.dumps(result["summary"], indent=2))
    elif args.command == "t2-report":
        from denso_a1.paderborn_t2_benchmark import (
            write_t2_benchmark_report,
            write_t2_fidelity_report,
        )

        benchmark_report = write_t2_benchmark_report(args.benchmark, Path("reports/t2_benchmark_report.md"))
        fidelity_report = write_t2_fidelity_report(args.benchmark, Path("reports/t2_fidelity_report.md"))
        print(f"T2 reports written to {benchmark_report} and {fidelity_report}")
    elif args.command == "t3-development":
        from denso_a1.paderborn_t3_benchmark import run_t3_development

        result = run_t3_development(
            args.raw_root,
            args.out,
            seeds=args.seeds,
            measurements=tuple(range(1, args.measurements + 1)),
        )
        print(json.dumps({"selected_policy": result["selected_policy"], "development_gate_pass": result["development_gate_pass"]}, indent=2))
    elif args.command == "t3-freeze":
        from denso_a1.paderborn_t3_benchmark import write_t3_protocol_freeze

        path = write_t3_protocol_freeze(args.selection, args.out)
        print(f"T3 protocol frozen at {path}")
    elif args.command == "paderborn-t3-benchmark":
        from denso_a1.paderborn_t3_benchmark import run_paderborn_t3_benchmark

        result = run_paderborn_t3_benchmark(
            args.raw_root,
            args.out,
            freeze_path=args.freeze,
            seeds=args.seeds,
            measurements=tuple(range(1, args.measurements + 1)),
        )
        print(json.dumps(result["summary"], indent=2))
    elif args.command == "safety-gate":
        from denso_a1.safety_gate import write_safety_gate_outputs

        result = write_safety_gate_outputs(args.repo)
        print(json.dumps({"methods": len(result["candidates"]), "output_dir": result["output_dir"]}, indent=2))
    elif args.command == "safety-gate-validate":
        from denso_a1.safety_gate_validation import run_validation

        result = run_validation(args.repo, args.raw_root, sample_count=args.sample_count)
        print(json.dumps({"corruption_rows": result["corruption_rows"], "utility_rows": result["utility_rows"], "protocol_sha256": result["protocol_sha256"]}, indent=2))
if __name__ == "__main__":
    main()
