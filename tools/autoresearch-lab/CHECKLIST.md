# Checklist: MASSE Autonomous Research Lab (Gen 1)

Use this to track progress. Keep it brutally literal.

## A) Decide and lock scope
- [x] Confirm editable surface: `masse_study_spec.yaml` (only file the Experimenter can change)
- [x] Confirm initial benchmark suite: Drift, Modal, Diaphragm flexibility
- [x] Confirm reference truth: baseline models + expected output bands
- [x] Confirm score formula weights (start with 0.6/0.2/0.2)
- [x] Confirm hard guardrails (runtime cap %, stability requirements)

## B) Repo / folder skeleton
- [x] Create folder: `tools/autoresearch-lab/`
- [x] Add `PRD.md`
- [x] Add this `CHECKLIST.md`
- [x] Create `runs/` folder
- [x] Add `.gitignore` entries for `runs/` and `results.tsv`

## C) Define artifact schemas
- [ ] `brief.json` schema (benchmark selection, notes, constraints)
- [ ] `spec` schema (modeling defaults and knobs) (`masse_study_spec.json` is authoritative)
- [x] `case_outputs.json` schema (per-benchmark machine-readable outputs)
- [x] `score.json` schema (score + submetrics) (implemented in score_bench.py)
- [x] `decision.json` schema (keep/discard + reason) (written by run_all.py)
- [x] `trace.json` schema (versions, timestamps, tool invocations) (written by run_all.py)

## D) Implement harness (fixed spine)
- [x] Implement `bench_manifest.json` (list of benchmark cases and inputs)
- [x] Implement `run_bench.py` (executes suite and writes run folders)
- [x] Implement `score_bench.py` (computes scalar score + submetrics)
- [ ] Implement `write_artifacts.py` (optional: extra summarization)
- [x] Implement `update_ledger.py` (append to `results.tsv`)
- [x] Implement `run_all.py` (one-command run → score → decision → ledger)

## E) Create baseline
- [x] Freeze baseline spec (current defaults)
- [x] Run benchmarks and store baseline metrics as reference
- [x] Record baseline in `results.tsv` as KEEP (baseline)

## F) Agent contracts (multi-agent lab)
- [ ] Chief Engineer contract (agenda + guardrails)
- [ ] Researcher contract (proposal schema)
- [ ] Experimenter contract (apply proposal, run harness)
- [ ] Evaluator contract (keep/discard policy)
- [ ] Archivist contract (write learning entries)

## G) First experiment families
- [ ] Damping model variants (Rayleigh targets, modal damping)
- [x] Diaphragm stiffness rules (rigid, semi-rigid, param sweep)
- [x] Solver strategy tuning (test, algorithm, tolerances)

## H) Promotion to Skill (only after MVP works)
- [ ] Create skill folder: `~/.openclaw/skills/masse-autoresearch-lab/`
- [ ] Add `SKILL.md` with clear commands and guardrails
- [ ] Add scripts into `scripts/` (runner, scorer, ledger)
- [ ] Validate it does not depend on unstable paths
- [ ] Document how it interacts with existing `masse` and `masse-job-runner` skills

## I) Done means
- [x] One command runs suite, produces artifacts, and updates ledger
- [x] At least 1 kept improvement beyond baseline
- [x] Archivist note written for each keep
