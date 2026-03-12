"""score_bench.py

Gen 1 scoring.

Computes a scalar score for a run folder produced by run_bench.py.

Inputs:
- cases/*/case_outputs.json (machine readable per benchmark)
- reference/baseline_metrics.json (reference truth for accuracy)

Score (lower is better):
  score = 0.6*accuracy + 0.2*runtime + 0.2*stability

Notes:
- For now runtime is approximated (case_outputs currently does not record runtime).
- Stability is pass/fail (any failed case is huge penalty).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)


def _rel_err(v: float, ref: float, eps: float = 1e-9) -> float:
    return abs(v - ref) / max(abs(ref), eps)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", type=Path, help="Path to runs/<run_id>")
    ap.add_argument(
        "--reference",
        type=Path,
        default=Path(__file__).resolve().parent / "reference" / "baseline_metrics.json",
    )
    args = ap.parse_args()

    cases_dir = args.run_dir / "cases"
    if not cases_dir.exists():
        raise SystemExit(f"Missing cases dir: {cases_dir}")

    ref = _load_json(args.reference)
    ref_bench = ref.get("benchmarks", {})

    case_results = []
    any_fail = False
    accuracy_terms: list[float] = []

    for case_dir in sorted(p for p in cases_dir.iterdir() if p.is_dir()):
        bench_id = case_dir.name
        out_path = case_dir / "case_outputs.json"
        if not out_path.exists():
            any_fail = True
            case_results.append({"case": bench_id, "ok": False, "reason": "missing case_outputs.json"})
            continue

        out = _load_json(out_path)
        ok = out.get("status") == "ok"
        if not ok:
            any_fail = True

        metrics = out.get("metrics", {})
        runtime_case = out.get("runtime_s")
        ref_metrics = ref_bench.get(bench_id, {})

        # Accuracy: simple relative error sum, per benchmark.
        # (We will refine weighting later.)
        case_errs: list[float] = []
        try:
            if bench_id.startswith("B1"):
                if ref_metrics.get("roof_drift") is not None:
                    case_errs.append(_rel_err(metrics["roof_drift"], ref_metrics["roof_drift"]))
                if ref_metrics.get("base_shear") is not None:
                    case_errs.append(_rel_err(metrics["base_shear"], ref_metrics["base_shear"]))
            elif bench_id.startswith("B2"):
                rp = ref_metrics.get("periods", {})
                mp = metrics.get("periods", {})
                for k in ("T1", "T2", "T3"):
                    if rp.get(k) is not None:
                        case_errs.append(_rel_err(mp[k], rp[k]))
            elif bench_id.startswith("B3"):
                for k in ("drift_node11", "drift_node12", "rotation"):
                    if ref_metrics.get(k) is not None:
                        case_errs.append(_rel_err(metrics[k], ref_metrics[k]))
        except Exception as e:
            any_fail = True
            ok = False
            out["reason"] = f"metric parse error: {e}"

        if case_errs:
            accuracy_terms.append(sum(case_errs) / len(case_errs))

        case_results.append({
            "case": bench_id,
            "ok": ok,
            "reason": out.get("reason", ""),
            "runtime_s": runtime_case,
            "metrics": metrics,
            "accuracy_terms": case_errs,
        })

    # Submetrics
    stability = 1.0 if not any_fail else 0.0
    accuracy = float(sum(accuracy_terms) / len(accuracy_terms)) if accuracy_terms else None

    # Runtime: average of per-case runtime_s if present
    runtimes = [c.get("runtime_s") for c in case_results if isinstance(c.get("runtime_s"), (int, float))]
    runtime_s = float(sum(runtimes) / len(runtimes)) if runtimes else None

    # Scalar score
    if any_fail:
        score = 1e9
        status = "crash"
    else:
        # If no reference is populated, treat accuracy as 0 for now.
        acc = accuracy if (accuracy is not None and not math.isnan(accuracy)) else 0.0
        # Normalize runtime: relative to 1s baseline so it has a small but real effect.
        rt = (runtime_s / 1.0) if runtime_s is not None else 0.0
        # Stability: 0 penalty when stable.
        st = 0.0
        score = 0.6 * acc + 0.2 * rt + 0.2 * st
        status = "ok"

    score_obj = {
        "score": score,
        "status": status,
        "submetrics": {
            "accuracy": accuracy,
            "runtime_s": runtime_s,
            "stability": stability,
        },
        "cases": case_results,
        "reference": str(args.reference),
    }

    _write_json(args.run_dir / "score.json", score_obj)
    print(json.dumps(score_obj, indent=2))
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
