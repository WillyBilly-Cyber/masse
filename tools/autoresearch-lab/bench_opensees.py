"""bench_opensees.py

Deterministic OpenSeesPy benchmark implementations.

We use OpenSeesPy Python API (not Tcl), because the installed openseespy build
in MASSE's venv does not expose a Tcl `source()` interface.

Usage:
  python bench_opensees.py <benchmark_id> <case_dir> <spec_json_path>

Writes:
  <case_dir>/case_outputs.json
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import openseespy.opensees as ops  # type: ignore


def _write(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def _apply_solver_defaults(spec: dict) -> None:
    solver = (spec or {}).get("solver", {})
    # Map only a minimal subset for Gen 1.
    ops.constraints(str(solver.get("constraints", "Plain")))
    ops.numberer(str(solver.get("numberer", "RCM")))
    ops.system(str(solver.get("system", "UmfPack")))
    test = solver.get("test", {})
    ops.test(str(test.get("name", "NormDispIncr")), float(test.get("tol", 1e-6)), int(test.get("maxIter", 30)))
    alg = solver.get("algorithm", {})
    ops.algorithm(str(alg.get("name", "Newton")))


def _b1_frame_2d(spec: dict) -> dict:
    """3-story, 3-bay 2D elastic frame. Outputs roof drift and base shear."""
    ops.wipe()
    ops.model("basic", "-ndm", 2, "-ndf", 3)

    Lb = 30.0
    Hs = 12.0
    nStories = 3
    nBays = 3

    # Nodes: tag = i*(nStories+1)+j+1
    def node_tag(i: int, j: int) -> int:
        return i * (nStories + 1) + j + 1

    for i in range(nBays + 1):
        for j in range(nStories + 1):
            ops.node(node_tag(i, j), i * Lb, j * Hs)

    # Fix base
    for i in range(nBays + 1):
        ops.fix(node_tag(i, 0), 1, 1, 1)

    # Properties (placeholder)
    E = 29000.0
    A = 100.0
    Iz = 1000.0

    # Geom transf
    pdelta = ((spec.get("stability", {}) or {}).get("pDelta", {}) or {}).get("enabledByDefault", True)
    ops.geomTransf("PDelta" if pdelta else "Linear", 1)

    # Elements
    etag = 1

    # Columns
    for i in range(nBays + 1):
        for j in range(nStories):
            ni = node_tag(i, j)
            nj = node_tag(i, j + 1)
            ops.element("elasticBeamColumn", etag, ni, nj, A, E, Iz, 1)
            etag += 1

    # Beams
    for j in range(1, nStories + 1):
        for i in range(nBays):
            ni = node_tag(i, j)
            nj = node_tag(i + 1, j)
            ops.element("elasticBeamColumn", etag, ni, nj, A, E, Iz, 1)
            etag += 1

    # Mass at roof line nodes (simplified)
    m = 10.0
    for i in range(nBays + 1):
        ops.mass(node_tag(i, nStories), m, 0.0, 0.0)

    _apply_solver_defaults(spec)

    # Lateral load pattern
    ops.timeSeries("Linear", 1)
    ops.pattern("Plain", 1, 1)
    # Apply lateral loads at each roof node
    for i in range(nBays + 1):
        ops.load(node_tag(i, nStories), 1.0, 0.0, 0.0)

    # Static analysis
    ops.integrator("LoadControl", 0.1)
    ops.analysis("Static")

    ok = 0
    for _ in range(10):
        ok = ops.analyze(1)
        if ok != 0:
            break

    roof_node = node_tag(nBays // 2, nStories)
    roof_disp = ops.nodeDisp(roof_node, 1)
    roof_drift = float(roof_disp) / (nStories * Hs)

    # Base shear: sum reactions at base
    # Need reactions computed
    ops.reactions()
    base_shear = 0.0
    for i in range(nBays + 1):
        base_shear += float(ops.nodeReaction(node_tag(i, 0), 1))

    return {
        "converged": (ok == 0),
        "roof_drift": roof_drift,
        "base_shear": base_shear,
    }


def _b2_modal_2d(spec: dict) -> dict:
    ops.wipe()
    ops.model("basic", "-ndm", 2, "-ndf", 3)

    Lb = 30.0
    Hs = 12.0
    nStories = 3
    nBays = 3

    def node_tag(i: int, j: int) -> int:
        return i * (nStories + 1) + j + 1

    for i in range(nBays + 1):
        for j in range(nStories + 1):
            ops.node(node_tag(i, j), i * Lb, j * Hs)

    for i in range(nBays + 1):
        ops.fix(node_tag(i, 0), 1, 1, 1)

    E = 29000.0
    A = 100.0
    Iz = 1000.0

    ops.geomTransf("Linear", 1)

    etag = 1
    for i in range(nBays + 1):
        for j in range(nStories):
            ops.element("elasticBeamColumn", etag, node_tag(i, j), node_tag(i, j + 1), A, E, Iz, 1)
            etag += 1

    for j in range(1, nStories + 1):
        for i in range(nBays):
            ops.element("elasticBeamColumn", etag, node_tag(i, j), node_tag(i + 1, j), A, E, Iz, 1)
            etag += 1

    m = 10.0
    for i in range(nBays + 1):
        ops.mass(node_tag(i, nStories), m, 0.0, 0.0)

    # Eigen
    num_modes = 3
    # Use a more robust solver for small problems
    try:
        lambdas = ops.eigen("-fullGenLapack", num_modes)
    except Exception:
        lambdas = ops.eigen(num_modes)
    periods = {}
    for k in range(num_modes):
        lam = float(lambdas[k])
        periods[f"T{k+1}"] = 2.0 * math.pi / math.sqrt(lam) if lam > 0 else float("nan")

    return {"periods": periods}


def _b3_frame_3d_base(spec: dict):
    """Shared 3D frame geometry for diaphragm benchmarks."""
    ops.wipe()
    ops.model("basic", "-ndm", 3, "-ndf", 6)

    Lx, Ly, H = 120.0, 80.0, 15.0

    base = [(1, 0, 0), (2, Lx, 0), (3, Lx, Ly), (4, 0, Ly)]
    for tag, x, y in base:
        ops.node(tag, x, y, 0.0)
        ops.fix(tag, 1, 1, 1, 1, 1, 1)

    roof = [(11, 0, 0), (12, Lx, 0), (13, Lx, Ly), (14, 0, Ly)]
    for tag, x, y in roof:
        ops.node(tag, x, y, H)

    # Columns + perimeter beams
    E = 29000.0
    A = 50.0
    Iz = 500.0
    Iy = 500.0
    G = 11500.0
    J = 10.0

    # Coordinate transforms
    ops.geomTransf("Linear", 1, 0, 1, 0)  # columns
    ops.geomTransf("Linear", 2, 0, 0, 1)  # beams

    etag = 1
    for b, r in zip([1, 2, 3, 4], [11, 12, 13, 14]):
        ops.element("elasticBeamColumn", etag, b, r, A, E, G, J, Iy, Iz, 1)
        etag += 1

    perim = [(11, 12), (12, 13), (13, 14), (14, 11)]
    for ni, nj in perim:
        ops.element("elasticBeamColumn", etag, ni, nj, A, E, G, J, Iy, Iz, 2)
        etag += 1

    return Lx, Ly, H, roof


def _b3r_diaphragm_rigid_3d(spec: dict) -> dict:
    """Rigid diaphragm torsion benchmark."""
    Lx, Ly, H, roof = _b3_frame_3d_base(spec)

    cm_tag = 100
    ops.node(cm_tag, Lx / 2.0, Ly / 2.0, H)
    ops.mass(cm_tag, 50.0, 50.0, 50.0, 0.0, 0.0, 0.0)
    ops.fix(cm_tag, 0, 0, 1, 1, 1, 0)

    ops.rigidDiaphragm(3, cm_tag, *[t for t, _, _ in roof])

    _apply_solver_defaults(spec)

    ops.timeSeries("Linear", 1)
    ops.pattern("Plain", 1, 1)
    ops.load(12, 10.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    ops.load(13, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    ops.integrator("LoadControl", 0.1)
    ops.analysis("Static")

    ok = 0
    for _ in range(10):
        ok = ops.analyze(1)
        if ok != 0:
            break

    ux11 = float(ops.nodeDisp(11, 1))
    ux12 = float(ops.nodeDisp(12, 1))
    ux13 = float(ops.nodeDisp(13, 1))
    rot_est = -((ux13 - ux12) / Ly)

    return {
        "converged": (ok == 0),
        "drift_node11": ux11,
        "drift_node12": ux12,
        "drift_node13": ux13,
        "rotation": rot_est,
    }


def _b3s_diaphragm_semirigid_membrane_proxy_3d(spec: dict) -> dict:
    """Semi-rigid diaphragm benchmark using an explicit in-plane shell mesh.

    Uses ShellMITC4 + PlateFiber, then locks out-of-plane DOF and rotations at diaphragm
    nodes so behavior is pure in-plane membrane.

    The knob `diaphragm.semi_rigid.effectiveStiffnessFactor` scales shell thickness.
    """
    Lx, Ly, H, roof = _b3_frame_3d_base(spec)

    kfac = float(((spec.get("diaphragm", {}) or {}).get("semi_rigid", {}) or {}).get("effectiveStiffnessFactor", 1.0))
    kfac = max(kfac, 1e-9)

    pts = {
        201: (0.0, 0.0),
        202: (Lx / 2.0, 0.0),
        203: (Lx, 0.0),
        204: (0.0, Ly / 2.0),
        205: (Lx / 2.0, Ly / 2.0),
        206: (Lx, Ly / 2.0),
        207: (0.0, Ly),
        208: (Lx / 2.0, Ly),
        209: (Lx, Ly),
    }
    for tag, (x, y) in pts.items():
        ops.node(tag, x, y, H)
        ops.fix(tag, 0, 0, 1, 1, 1, 1)

    # Minimal in-plane restraint
    ops.fix(201, 0, 1, 0, 0, 0, 0)
    ops.fix(203, 1, 0, 0, 0, 0, 0)

    # Tie roof corners into diaphragm corners (in-plane)
    corner_map = {11: 201, 12: 203, 13: 209, 14: 207}
    for roof_tag, dia_tag in corner_map.items():
        ops.equalDOF(roof_tag, dia_tag, 1, 2)

    # Shell section
    E = 29000.0
    nu = 0.30
    t0 = 1.0
    t = t0 * kfac
    ops.nDMaterial("ElasticIsotropic", 401, E, nu)
    ops.section("PlateFiber", 401, 401, t)

    eid = 5000
    quads = [
        (201, 202, 205, 204),
        (202, 203, 206, 205),
        (204, 205, 208, 207),
        (205, 206, 209, 208),
    ]
    for n1, n2, n3, n4 in quads:
        ops.element("ShellMITC4", eid, n1, n2, n3, n4, 401)
        eid += 1

    _apply_solver_defaults(spec)

    ops.timeSeries("Linear", 1)
    ops.pattern("Plain", 1, 1)
    ops.load(12, 10.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    ops.load(13, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    ops.integrator("LoadControl", 0.1)
    ops.analysis("Static")

    ok = 0
    for _ in range(10):
        ok = ops.analyze(1)
        if ok != 0:
            break

    ux11 = float(ops.nodeDisp(11, 1))
    ux12 = float(ops.nodeDisp(12, 1))
    ux13 = float(ops.nodeDisp(13, 1))
    rot_est = -((ux13 - ux12) / Ly)

    return {
        "converged": (ok == 0),
        "drift_node11": ux11,
        "drift_node12": ux12,
        "drift_node13": ux13,
        "rotation": rot_est,
        "t_shell": t,
    }


def run(bench_id: str, case_dir: Path, spec: dict) -> dict:
    if bench_id.startswith("B1"):
        return _b1_frame_2d(spec)
    if bench_id.startswith("B2"):
        return _b2_modal_2d(spec)
    if bench_id.startswith("B3R"):
        return _b3r_diaphragm_rigid_3d(spec)
    if bench_id.startswith("B3S"):
        return _b3s_diaphragm_semirigid_membrane_proxy_3d(spec)
    raise ValueError(f"Unknown benchmark id: {bench_id}")


def main() -> int:
    if len(sys.argv) != 4:
        print("Usage: python bench_opensees.py <benchmark_id> <case_dir> <spec_json>", file=sys.stderr)
        return 2

    bench_id = sys.argv[1]
    case_dir = Path(sys.argv[2]).resolve()
    spec_path = Path(sys.argv[3]).resolve()

    spec = json.loads(spec_path.read_text(encoding="utf-8"))

    started = time.time()
    status = "ok"
    reason = ""
    metrics = {}

    try:
        metrics = run(bench_id, case_dir, spec)
    except Exception as e:
        status = "fail"
        reason = str(e)

    runtime_s = time.time() - started

    out = {
        "benchmark_id": bench_id,
        "status": status,
        "reason": reason,
        "runtime_s": runtime_s,
        "metrics": metrics,
    }

    case_dir.mkdir(parents=True, exist_ok=True)
    _write(case_dir / "case_outputs.json", out)
    print(json.dumps(out, indent=2))
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
