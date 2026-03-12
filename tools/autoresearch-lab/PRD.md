# PRD: MASSE Autonomous Research Lab (Gen 1)

**Owner:** William

**Author:** Wilson

**Date:** 2026-03-11

## 0) One-liner
Build a multi-agent “research lab” that continuously improves MASSE structural modeling defaults and workflow heuristics by running a fixed benchmark suite, scoring results, and keeping only measurable improvements.

## 1) Problem
Right now, structural modeling decisions (diaphragm assumptions, damping, solver settings, element formulations, meshing rules) are mostly hand-tuned. They drift between projects and people, and we rarely get an empirical, repeatable way to prove that a “better default” is actually better.

We want a system that:
- turns modeling heuristics into a controlled, reviewable search space,
- tests them against canonical benchmark problems,
- retains improvements with traceable evidence.

## 2) Goals
### Primary goals
1) **Empirical improvement loop:** automate propose → run → score → keep/discard.
2) **Reproducible artifacts:** every run stores brief, spec, outputs, score, and decision.
3) **Reviewable diffs:** constrain what can change so improvements are auditable.

### Secondary goals
4) **Multi-agent separation of concerns:** planner, researcher, experimenter, evaluator, archivist.
5) **Bootstrap fast:** first end-to-end working loop with 3 benchmarks and 1 editable surface.

## 3) Non-goals (Gen 1)
- Stamped design output. This is decision support.
- Solving every code-jurisdiction nuance.
- Unbounded web crawling. Web sources (if enabled) are allowlisted.

## 4) Users
- **Primary:** William (operator, approves architecture + keeps risk in check)
- **Secondary (later):** internal engineers who want stable “house defaults” and traceable modeling rationale

## 5) Success criteria
- A single command (or orchestrator run) can:
  - run the benchmark suite,
  - compute a scalar score + submetrics,
  - produce artifacts,
  - decide keep/discard,
  - write a ledger entry.
- Within the first 1–2 weeks of use, the lab produces at least 3 “kept” improvements that are:
  - measurable (score improved),
  - explainable (archivist note),
  - reviewable (small diff to the editable surface).

## 6) Architecture overview
This is “Karpathy Gen 0 → Gen 1 multi-agent lab”, adapted to MASSE.

### 6.1 Fixed harness spine (read-only or near read-only)
**Equivalent to `prepare.py` + `evaluate_bpb`**
- **Benchmark suite definition:** canonical structural problems (Gen 1 starts with 3)
- **Runner:** runs MASSE/OpenSees jobs with caps (time, steps, retries)
- **Scorer:** computes scalar `score` plus submetrics
- **Artifact writer:** stores run bundle

The fixed harness is what makes results comparable.

### 6.2 Editable surface (the only thing the Experimenter is allowed to change)
**Gen 1 choice: `masse_study_spec.yaml`** (or `.json`)
- solver strategy (test, algorithm, tolerances)
- damping model and targets
- diaphragm modeling assumption + stiffness rules
- element formulation defaults
- mesh density rules

The Experimenter modifies only this file.

### 6.3 Roles (agents)
1) **Chief Engineer (planner):** chooses benchmark focus, exploration strategy, guardrails.
2) **Researcher:** proposes hypothesis and change, based on literature + prior run deltas.
3) **Experimenter:** edits the spec, runs benchmarks.
4) **Evaluator:** extracts metrics, scores, keep/discard, writes ledger.
5) **Archivist:** writes distilled learnings, prevents repeats.

## 7) Benchmark suite (Gen 1)
Benchmarks are deterministic OpenSeesPy models (not agentic generation).

### B1) Drift + base shear (2D)
- id: `B1_drift_pdelta_2d_moment_frame`

### B2) Modal periods (2D)
- id: `B2_modal_periods_2d_frame`

### B3R) Diaphragm torsion regression (3D, rigid)
- id: `B3R_diaphragm_rigid_torsion_3d`

### B3S) Diaphragm torsion (3D, semi-rigid)
- id: `B3S_diaphragm_semirigid_membrane_3d`
- diaphragm model: ShellMITC4 membrane (PlateFiber section, out-of-plane constrained)

**Reference truth:** `reference/baseline_metrics.json` (unified reference) + per-benchmark run artifacts in `runs/`.

## 8) Scoring
We need a single scalar score so the system can keep/discard.

### 8.1 Submetrics
- **accuracy:** weighted error vs baseline/reference outputs
- **runtime:** wall clock seconds
- **stability:** penalties for nonconvergence, warnings, crashes
- **complexity:** optional penalty for making the spec “more complex” (heuristic)

### 8.2 Default formula (tunable)
Lower is better.

```
score = 0.6 * accuracy_norm + 0.2 * runtime_norm + 0.2 * stability_penalty
```

Notes:
- If a run crashes, assign a very bad score and mark `crash`.
- If runtime increases beyond a cap without accuracy gains, auto-discard.

## 9) Artifacts and logging
### 9.1 Folder structure
Per experiment:

```
tools/autoresearch-lab/runs/<timestamp>_<slug>/
  brief.json
  masse_study_spec.json
  bench_manifest.json
  cases/
    <benchmark_id>/
      case_outputs.json
      bench_stdout.txt
      bench_stderr.txt
  score.json
  decision.json
  trace.json
  run_summary.txt
```

### 9.2 Ledger
Start with TSV for simplicity:

`results.tsv` (untracked by git)
- run_id
- git_commit (if applicable)
- score
- accuracy
- runtime_s
- stability
- status (keep|discard|crash)
- description

Later upgrade: SQLite/DuckDB.

## 10) Operating policies (guardrails)
- No changes to the harness during a run series unless we explicitly “bump harness version”.
- Experimenter edits only the spec.
- Keep requires score improvement greater than epsilon and no guardrail violation.
- Archivist must write a short “why it worked” note for any keep.

## 11) MVP scope (what we build first)
### MVP-1 (end-to-end, single machine)
- benchmark runner with fixed caps
- scorer produces scalar score
- spec file exists and drives MASSE job generation
- ledger update
- manual “chief engineer” (you) approving experiment families

### MVP-2 (multi-agent orchestration)
- formalize the agent contracts (inputs/outputs)
- add archivist notes store

## 12) Open questions (to resolve early)
1) Do we store benchmark references as MASSE outputs, pure OpenSees, or both?
2) What is the first guardrail: runtime cap, stability cap, or accuracy band?
3) Where do we want this to live: as an OpenClaw Skill, or as a project folder that later becomes a skill?

## 13) Recommendation: where to put this
**Current:** `tools/autoresearch-lab/` (repo path).

**Next (optional):** promote to `~/.openclaw/skills/masse-autoresearch-lab/` once the interface is stable and we want to call it as a first-class OpenClaw skill.
