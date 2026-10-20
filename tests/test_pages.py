"""Smoke tests: every page renders without exceptions, and the core learner flows work end to end."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
_tmp = tempfile.mkdtemp()
os.environ["QFIN_DB"] = str(Path(_tmp) / "test.sqlite")

from streamlit.testing.v1 import AppTest  # noqa: E402

from core import bootstrap, curriculum, db  # noqa: E402

PAGES = ["dashboard", "placement", "curriculum", "reader", "code_lab", "empirical_lab", "tutor",
         "review", "capstones", "evidence", "regulatory", "glossary", "environment"]


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    bootstrap.init()
    db.set_setting("hours_per_week", 8.0)
    db.set_setting("plan_start", "2026-10-01")
    yield


def _page(name):
    at = AppTest.from_file(str(ROOT / "app_pages" / f"{name}.py"), default_timeout=120)
    return at


@pytest.mark.parametrize("name", PAGES)
def test_page_renders(name):
    at = _page(name).run()
    assert not at.exception, [e.value for e in at.exception]


def test_gate_flow_p1():
    """quiz 100% + solution code + passing report -> P1 mastered"""
    m = curriculum.load("P1")
    db.insert("quiz_attempts", module_id="P1", kind="quiz", score=1.0, n_questions=12, detail=[])
    from core import runner, grading
    g = runner.grade(m["exercise"]["solution"], m["exercise"]["tests"])
    db.insert("code_attempts", module_id="P1", exercise_id="p1_ex", score=g.score, passed=g.passed, total=g.total, code="", detail=[])
    rep = {k: ("We hypothesise residual below 1e-12 with pass threshold fixed in advance; expect H1 H2 H3 to pass. "
               "Data synthetic exact matrices, no leakage n/a. Baseline numpy closed form timed 3 ms. Quantum circuit 3 qubits. "
               "Metrics: residual 1e-16, error, fidelity 1. Controls: seed, alternative ordering, noise none. Repeat: seed 1234, qiskit 2.6 version, re-run. "
               "Decision: pass against threshold 1e-12 from step 1. Business: for a bank client this shows code correctness, does not mean value; cost limit.")
           for k, _, _ in grading.REPORT_HEADINGS}
    gr = grading.grade_report(rep)
    assert gr["passed"], gr
    db.insert("lab_reports", module_id="P1", lab_id="p1_lab", report=rep, scores=gr["scores"], total=gr["total"], passed=1, feedback="")
    curriculum.refresh_gates()
    assert curriculum.status("P1") == "mastered"


def test_reader_quiz_submit():
    at = _page("reader").run()
    at.button[-1]  # exists
    forms = [b for b in at.button if b.label == "Submit for grading"]
    assert forms
    forms[0].click().run()
    assert not at.exception


def test_review_card_flow():
    at = _page("review").run()
    btn = [b for b in at.button if b.label == "Show answer"]
    assert btn
    btn[0].click().run()
    assert not at.exception
    five = [b for b in at.button if b.label == "5"]
    five[0].click().run()
    assert not at.exception
