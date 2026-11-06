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
             *(["--api-only"] if "--api-only" in sys.argv else []),
             sysconfig.get_paths()["purelib"], f"{sys.version_info.major}.{sys.version_info.minor}"],
            cwd=ROOT, env=env, check=False,
        ).returncode

    arguments = sys.argv[sys.argv.index("--") + 1:]
    api_only = "--api-only" in arguments
    site_packages, expected_version = [arg for arg in arguments if arg != "--api-only"]
    actual_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    if actual_version != expected_version:
        raise RuntimeError(f"Use Python {actual_version} for Poetry; Blender uses it, but Poetry uses {expected_version}")
    sys.path[:0] = [str(ROOT), site_packages]
    from basilisp.lang.keyword import keyword
    from basilisp_blender.eval import eval_file, eval_str

    suites = [("tests/test_core.lpy", "fawltypoly.test-core")]
    if not api_only:
        suites.append(("tests/test_demos.lpy", "fawltypoly.test-demos"))
    results = {}
    for path, namespace in suites:
        eval_file(str(ROOT / path))
        suite = eval_str(f"""(into {{}} (for [[sym v] (ns-interns '{namespace})
                                            :when (:basilisp.test/test (meta v))]
                                        [sym ((deref v))]))""")
        results.update(suite.items())
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
