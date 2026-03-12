"""opensees_run.py

Run an OpenSees TCL script using openseespy.

Usage:
  python opensees_run.py path/to/script.tcl

Exit codes:
- 0 ok
- 1 failure
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python opensees_run.py <script.tcl>", file=sys.stderr)
        return 2

    tcl_path = Path(sys.argv[1]).resolve()
    if not tcl_path.exists():
        print(f"Missing TCL script: {tcl_path}", file=sys.stderr)
        return 2

    try:
        import openseespy.opensees as ops  # type: ignore
    except Exception as e:
        print(f"Failed to import openseespy: {e}", file=sys.stderr)
        return 2

    try:
        ops.wipe()
        # Some openseespy builds expose 'source', others don't.
        # Fall back to Tcl command execution.
        if hasattr(ops, "source"):
            ops.source(str(tcl_path))  # type: ignore
        else:
            ops.tcl(f'source "{tcl_path.as_posix()}"')
        return 0
    except Exception as e:
        print(f"OpenSees run failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
