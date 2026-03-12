# MASSE Autoresearch Lab (Gen 1)

A small, deterministic benchmark harness that lets us iteratively improve MASSE/OpenSees modeling defaults.

## What you edit (the one knob file)
- `masse_study_spec.json` (authoritative)
  - solver defaults (constraints/system/numberer/test/algorithm)
  - diaphragm semi-rigid stiffness factor for B3S

## What you run (one command)
From the MASSE repo root:

```bash
python tools/autoresearch-lab/run_all.py --tag exp1 --description "what changed" --mode auto
```

If your OpenSeesPy install is in a dedicated venv, point the harness at it:

```bash
export MASSE_VENV_PY=/path/to/venv/bin/python
# On Windows PowerShell:
# $env:MASSE_VENV_PY = "C:\\path\\to\\venv\\Scripts\\python.exe"
```

### Modes
- `--mode auto` (recommended):
  - runs suite
  - scores vs baselines
  - checks `gates.json`
  - keeps only if score beats best KEEP in `results.tsv`
- `--mode keep` / `--mode discard`: force decision

## Outputs
Each run creates a folder:
- `tools/autoresearch-lab/runs/<timestamp>_<tag>/`

Inside each case:
- `case_outputs.json` (machine-readable metrics)

Inside the run folder:
- `score.json`
- `decision.json`
- `trace.json` (git head + spec sha256)

Ledger (untracked):
- `tools/autoresearch-lab/results.tsv`

## Benchmarks
- **B1** `B1_drift_pdelta_2d_moment_frame`: drift + base shear
- **B2** `B2_modal_periods_2d_frame`: T1–T3
- **B3R** `B3R_diaphragm_rigid_torsion_3d`: rigid diaphragm torsion regression
- **B3S** `B3S_diaphragm_semirigid_membrane_3d`: semi-rigid diaphragm using ShellMITC4 membrane

Baselines:
- `reference/baseline_metrics.json` (unified reference for scoring)
- `reference/baseline_metrics_b3s.json` (extra info for B3S)

## Gates (engineering tolerances)
- `gates.json` sets max allowed relative error per benchmark/metric.
- These are set to typical structural-engineering acceptable deltas (not research-grade).

## Common workflow
1) Change one knob in `masse_study_spec.json`
2) Run `run_all.py --mode auto`
3) If decision is KEEP, commit the spec change
4) If DISCARD, revert the spec change

## Notes
- This is decision support, not stamped design.
- Keep benchmark definitions stable during a run series. If you change benchmarks, treat it as a baseline refresh.
