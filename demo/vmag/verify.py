"""Verify exported equations against Qas probes and density-matrix physicality.

Usage: poetry run python demo/vmag/verify.py [path/to/export.edn]
Runs without Blender or a JVM.
"""

import argparse
import importlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def verify(path):
    from basilisp import main
    main.init()
    import numpy as np
    from basilisp.lang.keyword import keyword as k

    data = importlib.import_module("fawltypoly.symbolic_data").loads(path.read_text())
    compile_equation = importlib.import_module("fawltypoly.expression").compile_
    states = list(data[k("optical")])
    states.extend(state for case in data[k("cases")] for state in case[k("atomic")])
    max_probe_error = max_hermitian_error = max_trace_error = 0.0
    min_eigenvalue = 1.0
    for state in states:
        rho = np.array([[complex(*z) for z in row] for row in state[k("density-matrix")]])
        min_eigenvalue = min(min_eigenvalue, float(np.linalg.eigvalsh(rho).min()))
        max_hermitian_error = max(max_hermitian_error, float(np.abs(rho - rho.conj().T).max()))
        max_trace_error = max(max_trace_error, abs(complex(np.trace(rho)) - state[k("trace")]))
        equation = compile_equation(state[k("expression")])
        for theta, phi, expected in state[k("probes")]:
            max_probe_error = max(max_probe_error, abs(equation(theta, phi) - expected))
    if min_eigenvalue < -1e-10 or max(max_probe_error, max_hermitian_error, max_trace_error) > 1e-10:
        raise AssertionError("VMAG equation/density-matrix verification failed")
    return {"states": len(states), "min_eigenvalue": min_eigenvalue,
            "max_hermitian_error": max_hermitian_error, "max_trace_error": max_trace_error,
            "max_qas_probe_error": max_probe_error,
            "references": [{"case": str(case[k("id")]),
                            "status": str(case[k("reference")][k("status")]),
                            "max_abs_difference": case[k("reference")].get(k("max-abs-difference"))}
                           for case in data[k("cases")]]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path,
                        default=Path(__file__).with_name("data") / "vmag_field_angles.edn")
    args = parser.parse_args()
    print(json.dumps(verify(args.path), indent=2))
