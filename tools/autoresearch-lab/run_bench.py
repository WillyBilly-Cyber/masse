"""run_bench.py

Gen 1 fixed harness runner.

Reads:
- bench_manifest.json (benchmark definitions)
- masse_study_spec.json (editable surface, only file Experimenter should change)

Runs:
- MASSE headless CLI via the existing OpenClaw MASSE skill runner script.

Writes:
- runs/<timestamp>_<slug>/... artifacts per benchmark case

Notes:
- This is intentionally minimal and conservative.
- Scoring is handled by score_bench.py.

Usage:
  python run_bench.py --dry-run
  python run_bench.py
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_MANIFEST = HERE / "bench_manifest.json"
DEFAULT_SPEC = HERE / "masse_study_spec.json"
DEFAULT_RUNS_DIR = HERE / "runs"

OPENSEES_RUNNER = HERE / "opensees_run.py"


def _python_exe() -> Path:
    env_py = os.environ.get("MASSE_VENV_PY") or os.environ.get("MASSE_PYTHON")
    if env_py:
        py_path = Path(env_py)
        if not py_path.exists():
            raise FileNotFoundError(f"MASSE_VENV_PY not found: {py_path}")
        return py_path
    return Path(sys.executable)


def _slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:80] if len(s) > 80 else s


def _now_run_id() -> str:
    # Local time, sortable.
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _run_opensees(case_dir: Path, tcl_src: Path) -> subprocess.CompletedProcess:
    """Run OpenSees TCL deterministically via a Python env that has openseespy."""
    py = _python_exe()

    # Copy TCL into case dir so recorders write locally.
    tcl_dst = case_dir / tcl_src.name
    shutil.copy2(tcl_src, tcl_dst)

    cmd = [
        str(py),
        str(OPENSEES_RUNNER),
        str(tcl_dst),
    ]
    return subprocess.run(cmd, cwd=str(case_dir), capture_output=True, text=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    ap.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    ap.add_argument("--tag", type=str, default="gen1")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    manifest = _load_json(args.manifest)
    spec = _load_json(args.spec)

    run_id = f"{_now_run_id()}_{_slugify(args.tag)}"
    run_dir = args.runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    # Copy fixed inputs into run folder for traceability
    shutil.copy2(args.manifest, run_dir / "bench_manifest.json")
    shutil.copy2(args.spec, run_dir / "masse_study_spec.json")

    suite_brief = {
        "run_id": run_id,
        "tag": args.tag,
        "created_local": dt.datetime.now().isoformat(),
        "manifest": {"path": str(args.manifest)},
        "spec": {"path": str(args.spec)},
        "benchmarks": [b["id"] for b in manifest.get("benchmarks", [])],
    }
    _write_json(run_dir / "brief.json", suite_brief)

    bench_list = manifest.get("benchmarks", [])
    if not bench_list:
        raise SystemExit("No benchmarks found in manifest")

    summary_lines: list[str] = []

    for i, bench in enumerate(bench_list, start=1):
        bench_id = bench["id"]
        bench_name = bench.get("name", bench_id)
        case_dir = run_dir / "cases" / bench_id
        case_dir.mkdir(parents=True, exist_ok=True)

        case_brief = {
            "benchmark": bench,
            "spec": spec,
            "case": {
                "bench_index": i,
                "bench_id": bench_id,
                "bench_name": bench_name,
            },
        }
        _write_json(case_dir / "brief.json", case_brief)

        # Trace inputs for this case
        _write_text(case_dir / "problem_description.txt", f"Benchmark: {bench_id} ({bench_name})\n")

        if args.dry_run:
            summary_lines.append(f"DRY RUN: would run OpenSeesPy benchmark for {bench_id}")
            continue

        # Run deterministic OpenSeesPy benchmark
        py = _python_exe()
        bench_cmd = [str(py), str(HERE / "bench_opensees.py"), bench_id, str(case_dir), str(args.spec.resolve())]
        result = subprocess.run(bench_cmd, cwd=str(case_dir), capture_output=True, text=True)
        _write_text(case_dir / "bench_stdout.txt", result.stdout)
        _write_text(case_dir / "bench_stderr.txt", result.stderr)
        _write_json(case_dir / "bench_exit.json", {"returncode": result.returncode})

        status = "ok" if result.returncode == 0 else "fail"
        summary_lines.append(f"{bench_id}: {status} (bench={result.returncode})")

    _write_text(run_dir / "run_summary.txt", "\n".join(summary_lines) + "\n")

    print(str(run_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
