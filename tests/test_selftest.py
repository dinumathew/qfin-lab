"""Self-test: executes all lab code and checks every module meets the definition of done.

Run:  pytest -q tests/            (or the button on the Lab environment page)
Fast mode (skip heavy labs): QLAB_FAST=1 pytest -q tests/
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import claims, curriculum, runner  # noqa: E402

MODULES = curriculum.built_modules()
IDS = [m["id"] for m in MODULES]
FAST = os.environ.get("QLAB_FAST") == "1"


def _all_text(m):
    parts = [m.get("summary", "")]
    for c in m["concepts"]:
        parts += [c["why"], c["how"], c["impact"]]
    parts += [str(v) for v in m["lens"].values()]
    return "\n".join(parts)


@pytest.mark.parametrize("m", MODULES, ids=IDS)
def test_structure(m):
    assert len(m["concepts"]) >= 2
    for c in m["concepts"]:
        for k in ("title", "why", "how", "impact", "code"):
            assert c.get(k), f"{m['id']}: concept missing {k}"
    for k in ("look", "decision", "justified", "mistakes", "impact", "test"):
        assert m["lens"].get(k), f"{m['id']}: lens missing {k}"
    assert 10 <= len(m["quiz"]) <= 15, f"{m['id']}: quiz has {len(m['quiz'])} items"
    assert 10 <= len(m["cards"]) <= 20, f"{m['id']}: {len(m['cards'])} cards"
    assert len(m["defend"]["questions"]) == 5
    for q in m["quiz"]:
        if q["type"] == "mc":
            assert 0 <= q["answer"] < len(q["options"])
        else:
            assert q["must"]


@pytest.mark.parametrize("m", MODULES, ids=IDS)
def test_claims_tagged_and_resolved(m):
    idx = claims.claim_index(MODULES)
    for cid in claims.referenced_ids(_all_text(m)):
        assert cid in idx, f"{m['id']}: text references unknown claim {cid}"
    for c in m["claims"]:
        assert c["tag"] in "MSJ"
        if c["tag"] == "S":
            s = c.get("source", {})
            for k in ("title", "publisher", "date", "url"):
                assert s.get(k), f"{c['id']}: sourced claim missing {k}"
            assert c.get("last_verified"), f"{c['id']}: no last_verified"
        if c["tag"] == "M":
            assert c.get("check"), f"{c['id']}: measured claim without check code"


@pytest.mark.parametrize("m", MODULES, ids=IDS)
def test_measured_claims_hold(m):
    for c in m["claims"]:
        if c["tag"] == "M":
            r = runner.run_code(c["check"], timeout=300)
            assert r.ok, f"{c['id']} failed:\n{r.stderr[-2000:]}"


@pytest.mark.parametrize("m", MODULES, ids=IDS)
def test_concept_code_runs(m):
    for c in m["concepts"]:
        r = runner.run_code(c["code"], timeout=300)
        assert r.ok, f"{m['id']} / {c['title']}:\n{r.stderr[-2000:]}"


@pytest.mark.parametrize("m", MODULES, ids=IDS)
def test_lab_runs(m):
    if FAST and m["lab"].get("heavy"):
        pytest.skip("heavy lab skipped in fast mode")
    r = runner.run_code(m["lab"]["code"], timeout=900)
    assert r.ok, f"{m['id']} lab:\n{r.stderr[-3000:]}"
    for name, cond in m["lab"].get("expect", {}).items():
        assert name in r.record, f"{m['id']} lab did not record {name}"
        assert eval(cond, {"x": r.record[name]}), f"{m['id']} lab: {name}={r.record[name]!r} fails {cond}"


@pytest.mark.parametrize("m", MODULES, ids=IDS)
def test_exercise_solution_passes(m):
    ex = m["exercise"]
    g = runner.grade(ex["solution"], ex["tests"], timeout=600)
    assert g.load_error is None, g.load_error
    failed = [r for r in g.results if not r["passed"]]
    assert not failed, json.dumps(failed, indent=1)
    assert g.total >= 3


@pytest.mark.parametrize("m", MODULES, ids=IDS)
def test_exercise_starter_fails(m):
    ex = m["exercise"]
    g = runner.grade(ex["starter"], ex["tests"], timeout=600)
    assert g.passed < g.total, "starter code should not pass the tests"


def test_regulatory_tracker_complete():
    data = json.loads((ROOT / "data" / "regulatory.json").read_text())
    for it in data["items"]:
        for k in ("jurisdiction", "body", "title", "url", "date", "status", "binding", "requirement", "deadlines", "last_verified"):
            assert it.get(k) not in (None, ""), f"{it.get('title')}: missing {k}"
