"""Execute learner code and grade it with unit tests, in a separate Python process.

Each run is isolated (fresh interpreter, temp dir, timeout) and reproducible
(QLAB_SEED is passed in; every run record carries versions and the seed).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import time
from dataclasses import dataclass, field
from pathlib import Path

from core.env import versions

CORE = Path(__file__).resolve().parent
ROOT = CORE.parent
RUNS = ROOT / "runs"


@dataclass
class RunResult:
    ok: bool
    stdout: str
    stderr: str
    wall_s: float
    seed: int
    figures: list[str] = field(default_factory=list)
    tables: list[dict] = field(default_factory=list)
    record: dict = field(default_factory=dict)

    def to_record(self, label: str, code: str) -> dict:
        return {
            "label": label,
            "seed": self.seed,
            "versions": versions(),
            "ok": self.ok,
            "wall_s": round(self.wall_s, 3),
            "outputs": self.record,
            "stdout": self.stdout[-20000:],
            "stderr": self.stderr[-5000:],
            "code": code,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }


def _env(seed: int, out: Path) -> dict:
    env = os.environ.copy()
    env["QLAB_SEED"] = str(seed)
    env["QLAB_OUT"] = str(out)
    env["PYTHONPATH"] = os.pathsep.join([str(CORE), str(ROOT), env.get("PYTHONPATH", "")])
    env["PYTHONHASHSEED"] = str(seed)
    env.setdefault("MPLBACKEND", "Agg")
    return env


def run_code(code: str, seed: int = 1234, timeout: int = 300) -> RunResult:
    with tempfile.TemporaryDirectory(prefix="qlab_") as td:
        td = Path(td)
        out = td / "out"
        out.mkdir()
        script = td / "cell.py"
        script.write_text(code)
        t0 = time.perf_counter()
        try:
            p = subprocess.run(
                [sys.executable, str(script)], cwd=td, env=_env(seed, out),
                capture_output=True, text=True, timeout=timeout,
            )
            ok, so, se = p.returncode == 0, p.stdout, p.stderr
        except subprocess.TimeoutExpired as e:
            ok, so, se = False, (e.stdout or "") if isinstance(e.stdout, str) else "", f"Timed out after {timeout}s"
        wall = time.perf_counter() - t0
        figs = [f.read_text() for f in sorted(out.glob("fig_*.json"))]
        tabs = [json.loads(f.read_text()) for f in sorted(out.glob("tab_*.json"))]
        rec = json.loads((out / "record.json").read_text()) if (out / "record.json").exists() else {}
    return RunResult(ok, so, se, wall, seed, figs, tabs, rec)


HARNESS = '''
import json, sys, traceback, io, contextlib
ns = {"__name__": "learner"}
results = []
buf = io.StringIO()
try:
    with contextlib.redirect_stdout(buf):
        exec(compile(open("learner.py").read(), "learner.py", "exec"), ns)
except Exception:
    print(json.dumps({"load_error": traceback.format_exc(limit=3), "results": []}))
    sys.exit(0)
exec(compile(open("tests.py").read(), "tests.py", "exec"), ns)
for name in sorted(k for k in list(ns) if k.startswith("test_") and callable(ns[k])):
    fn = ns[name]
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            fn()
        results.append({"test": name, "passed": True, "doc": (fn.__doc__ or "").strip()})
    except AssertionError as e:
        results.append({"test": name, "passed": False, "doc": (fn.__doc__ or "").strip(), "error": str(e) or "assertion failed"})
    except Exception as e:
        results.append({"test": name, "passed": False, "doc": (fn.__doc__ or "").strip(), "error": f"{type(e).__name__}: {e}"})
print("@@RESULTS@@" + json.dumps({"results": results, "stdout": buf.getvalue()[-4000:]}))
'''


@dataclass
class GradeResult:
    passed: int
    total: int
    results: list[dict]
    load_error: str | None
    stderr: str

    @property
    def score(self) -> float:
        return 0.0 if self.total == 0 else self.passed / self.total


def grade(code: str, tests: str, seed: int = 1234, timeout: int = 300) -> GradeResult:
    with tempfile.TemporaryDirectory(prefix="qgrade_") as td:
        td = Path(td)
        (td / "out").mkdir()
        (td / "learner.py").write_text(code)
        (td / "tests.py").write_text(textwrap.dedent(tests))
        (td / "harness.py").write_text(HARNESS)
        try:
            p = subprocess.run(
                [sys.executable, "harness.py"], cwd=td, env=_env(seed, td / "out"),
                capture_output=True, text=True, timeout=timeout,
            )
            stdout, stderr = p.stdout, p.stderr
        except subprocess.TimeoutExpired:
            return GradeResult(0, 1, [], f"Timed out after {timeout}s", "")
    if "@@RESULTS@@" in stdout:
        payload = json.loads(stdout.split("@@RESULTS@@", 1)[1])
        res = payload["results"]
        return GradeResult(sum(r["passed"] for r in res), len(res), res, None, stderr)
    try:
        payload = json.loads(stdout.strip().splitlines()[-1])
        return GradeResult(0, max(1, tests.count("def test_")), [], payload.get("load_error"), stderr)
    except Exception:
        return GradeResult(0, max(1, tests.count("def test_")), [], stderr[-3000:] or "Unknown error", stderr)


def export_run(record: dict, module_id: str, lab_id: str) -> Path:
    RUNS.mkdir(exist_ok=True)
    path = RUNS / f"{module_id}_{lab_id}_seed{record['seed']}_{time.strftime('%Y%m%d-%H%M%S')}.json"
    path.write_text(json.dumps(record, indent=2))
    return path
