"""run_all.py

One-command runner for MASSE Autoresearch Lab Gen 1.

Pipeline:
  1) run_bench.py
  2) score_bench.py
  3) write decision.json
  4) append to results.tsv

Usage:
  python run_all.py --tag myrun --description "..." --mode discard

Modes:
  --mode keep|discard|auto
    auto: keep only if status==ok and score improved vs best KEEP in ledger

Notes:
- results.tsv is untracked by design.
- This script never edits the spec. You do that manually.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUN_BENCH = HERE / "run_bench.py"
SCORE_BENCH = HERE / "score_bench.py"
UPDATE_LEDGER = HERE / "update_ledger.py"
LEDGER = HERE / "results.tsv"
GATES = HERE / "gates.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _append_decision(run_dir: Path, decision: dict) -> None:
    (run_dir / "decision.json").write_text(json.dumps(decision, indent=2), encoding="utf-8")


def _write_trace(run_dir: Path) -> None:
    """Write trace.json with basic provenance."""
    import hashlib

    spec_path = HERE / "masse_study_spec.json"
    spec_bytes = spec_path.read_bytes() if spec_path.exists() else b""
    spec_sha256 = hashlib.sha256(spec_bytes).hexdigest() if spec_bytes else None

    git_rev = None
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(HERE.parent.parent), capture_output=True, text=True)
        if r.returncode == 0:
            git_rev = r.stdout.strip()
    except Exception:
        pass

    trace = {
        "git_head": git_rev,
        "spec_sha256": spec_sha256,
    }
    (run_dir / "trace.json").write_text(json.dumps(trace, indent=2), encoding="utf-8")


def _write_summary_md(run_dir: Path, score_obj: dict, decision: dict) -> None:
    """Write a human-readable summary.md for quick review."""
    lines: list[str] = []
    lines.append(f"# Run summary: {run_dir.name}")
    lines.append("")
    lines.append(f"Decision: **{decision.get('decision','')}**")
    lines.append(f"Reason: {decision.get('reason','')}")
    lines.append("")

    sub = score_obj.get("submetrics", {})
    lines.append("## Score")
    lines.append(f"- score: `{score_obj.get('score')}`")
    lines.append(f"- status: `{score_obj.get('status')}`")
    lines.append(f"- accuracy: `{sub.get('accuracy')}`")
    lines.append(f"- runtime_s (avg): `{sub.get('runtime_s')}`")
    lines.append(f"- stability: `{sub.get('stability')}`")
    lines.append("")

    gate_ok = decision.get("gates_ok")
    if gate_ok is not None:
        lines.append("## Gates")
        lines.append(f"- gates_ok: `{gate_ok}`")
        problems = decision.get("gate_problems") or []
        if problems:
            lines.append("- problems:")
            for p in problems:
                lines.append(f"  - {p}")
        lines.append("")

    lines.append("## Cases")
    for c in score_obj.get("cases", []):
        cid = c.get("case")
        ok = c.get("ok")
        rt = c.get("runtime_s")
        lines.append(f"- {cid}: ok={ok}, runtime_s={rt}")
    lines.append("")

    (run_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _rel_err(v: float, ref: float, eps: float = 1e-12) -> float:
    return abs(v - ref) / max(abs(ref), eps)


def _passes_gates(run_dir: Path) -> tuple[bool, list[str]]:
    """Gate check based on case_outputs.json vs reference/baseline_metrics.json."""
    problems: list[str] = []

    gates = json.loads(GATES.read_text(encoding="utf-8")) if GATES.exists() else {"benchmarks": {}}
    ref = json.loads((HERE / "reference" / "baseline_metrics.json").read_text(encoding="utf-8"))
    ref_b = ref.get("benchmarks", {})

    cases_dir = run_dir / "cases"
    for case_dir in sorted(p for p in cases_dir.iterdir() if p.is_dir()):
        bid = case_dir.name
        out_path = case_dir / "case_outputs.json"
        if not out_path.exists():
            problems.append(f"{bid}: missing case_outputs.json")
            continue
        out = json.loads(out_path.read_text(encoding="utf-8"))
        metrics = out.get("metrics", {})

        # converged gate
        if gates.get("defaults", {}).get("require_converged", False):
            if ("converged" in metrics) and (metrics.get("converged") is False):
                problems.append(f"{bid}: not converged")

        g = (gates.get("benchmarks", {}) or {}).get(bid)
        if not g:
            continue
        max_rel = g.get("max_rel_error", {})
        refm = ref_b.get(bid, {})

        # Handle nested periods for B2
        if bid.startswith("B2"):
            mp = (metrics.get("periods") or {})
            rp = (refm.get("periods") or {})
            for k, lim in max_rel.items():
                if k not in rp or rp[k] is None:
                    continue
                err = _rel_err(float(mp[k]), float(rp[k]))
                if err > float(lim):
                    problems.append(f"{bid}:{k} rel_err={err:.4g} > {lim}")
            continue

        for k, lim in max_rel.items():
            if k not in refm or refm[k] is None:
                continue
            err = _rel_err(float(metrics[k]), float(refm[k]))
            if err > float(lim):
                problems.append(f"{bid}:{k} rel_err={err:.4g} > {lim}")

    return (len(problems) == 0), problems


def _best_keep_score(ledger_path: Path) -> float | None:
    if not ledger_path.exists():
        return None
    lines = ledger_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    if len(lines) < 2:
        return None
    header = lines[0].split("\t")
    try:
        i_score = header.index("score")
        i_status = header.index("status")
    except ValueError:
        return None

    best = None
    for ln in lines[1:]:
        if not ln.strip():
            continue
        cols = ln.split("\t")
        if len(cols) <= max(i_score, i_status):
            continue
        if cols[i_status].strip().lower() != "keep":
            continue
        try:
            s = float(cols[i_score])
        except ValueError:
            continue
        best = s if best is None else min(best, s)
    return best


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--description", default="")
    ap.add_argument("--mode", choices=["keep", "discard", "auto"], default="auto")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    # 1) run
    run_cmd = ["python", str(RUN_BENCH), "--tag", args.tag]
    if args.dry_run:
        run_cmd.append("--dry-run")

    run_res = subprocess.run(run_cmd, capture_output=True, text=True)
    if run_res.returncode != 0:
        print(run_res.stdout)
        print(run_res.stderr)
        return run_res.returncode

    run_dir = Path(run_res.stdout.strip().splitlines()[-1]).resolve()

    # 2) score
    score_cmd = ["python", str(SCORE_BENCH), str(run_dir)]
    score_res = subprocess.run(score_cmd, capture_output=True, text=True)
    if score_res.returncode not in (0, 1):
        print(score_res.stdout)
        print(score_res.stderr)
        return score_res.returncode

    score_obj = _load_json(run_dir / "score.json")

    # 3) decide
    best_keep = _best_keep_score(LEDGER)
    score = score_obj.get("score")
    status = score_obj.get("status")

    gate_ok, gate_problems = _passes_gates(run_dir)

    decision_mode = args.mode
    decided = "discard"
    reason = ""

    if decision_mode == "keep":
        decided = "keep"
        reason = "forced keep"
    elif decision_mode == "discard":
        decided = "discard"
        reason = "forced discard"
    else:
        # auto
        if status != "ok":
            decided = "discard"
            reason = f"score status={status}"
        elif not gate_ok:
            decided = "discard"
            reason = "failed gates"
        elif best_keep is None:
            decided = "keep"
            reason = "first keep in ledger"
        else:
            try:
                decided = "keep" if float(score) < float(best_keep) else "discard"
                reason = f"best_keep={best_keep}"
            except Exception:
                decided = "discard"
                reason = "could not compare score"

    decision = {
        "mode": decision_mode,
        "decision": decided,
        "reason": reason,
        "score": score,
        "status": status,
        "best_keep_score": best_keep,
        "gates_ok": gate_ok,
        "gate_problems": gate_problems,
        "description": args.description,
    }
    _append_decision(run_dir, decision)
    _write_trace(run_dir)
    _write_summary_md(run_dir, score_obj, decision)

    # 4) ledger
    led_cmd = ["python", str(UPDATE_LEDGER), str(run_dir), "--description", args.description, "--status", decided]
    led_res = subprocess.run(led_cmd, capture_output=True, text=True)
    if led_res.returncode != 0:
        print(led_res.stdout)
        print(led_res.stderr)
        return led_res.returncode

    print(str(run_dir))
    print(json.dumps(decision, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
