"""Run integration tests in a factory-startup Blender, without touching an open file.

Usage: poetry run python tests/run_blender.py
The Poetry and Blender interpreters must have matching Python major/minor versions.
"""

import os
from pathlib import Path
import subprocess
import sys
import sysconfig

ROOT = Path(__file__).resolve().parents[1]


def main():
    if "--" not in sys.argv:
        env = dict(os.environ, ALSOFT_DRIVERS="null")
        return subprocess.run(
            ["blender", "--background", "--factory-startup", "--python-exit-code", "1",
             "--python", str(Path(__file__).resolve()), "--",
             sysconfig.get_paths()["purelib"], f"{sys.version_info.major}.{sys.version_info.minor}"],
            cwd=ROOT, env=env, check=False,
        ).returncode

    site_packages, expected_version = sys.argv[sys.argv.index("--") + 1:]
    actual_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    if actual_version != expected_version:
        raise RuntimeError(f"Use Python {actual_version} for Poetry; Blender uses it, but Poetry uses {expected_version}")
    sys.path[:0] = [str(ROOT), site_packages]
    from basilisp.lang.keyword import keyword
    from basilisp_blender.eval import eval_file, eval_str

    eval_file(str(ROOT / "tests/test_core.lpy"))
    results = eval_str("""(into {} (for [[sym v] (ns-interns 'fawltypoly.test-core)
                                         :when (:basilisp.test/test (meta v))]
                                     [sym ((deref v))]))""")
    if len(results) == 0:
        raise AssertionError("No Blender integration tests were discovered")
    failed = False
    for name, result in results.items():
        failures = result.val_at(keyword("failures"))
        has_failures = len(failures) > 0
        print(f"{'FAIL' if has_failures else 'PASS'} {name}", flush=True)
        for failure in failures:
            print(f"  {failure}", flush=True)
        failed |= has_failures
    if failed:
        raise AssertionError("Blender integration tests failed")
    print(f"Passed {len(results)} Blender integration tests", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
