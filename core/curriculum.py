"""Curriculum registry, module loading and mastery gates.

Built modules live in content/modules/<id>.py and expose MODULE (see content/SCHEMA.md).
Planned modules appear on the curriculum map but are not yet authored.
"""
from __future__ import annotations

import importlib
from functools import lru_cache

from core import db

MASTERY_QUIZ = 0.80
MASTERY_CODE = 0.80

LEVELS = {
    0: "Level 0 · Prerequisites (testable out)",
    1: "Level 1 · Basic",
    2: "Level 2 · Intermediate",
    3: "Level 3 · Advanced",
    "Q": "Track Q · Qiskit in practice",
}

# (id, level, title, est_hours, prereqs, built)
REGISTRY: list[tuple] = [
    ("P1", 0, "Linear algebra for quantum", 8, [], True),
    ("P2", 0, "Probability and statistics refresh", 6, [], True),
    ("P3", 0, "Complexity and oracles", 4, [], True),
    ("P4", 0, "Finance models used in the labs", 6, [], True),
    ("P5", 0, "Cryptography foundations", 8, [], True),
    ("P6", 0, "Python engineering for research", 4, [], True),
    ("B1", 1, "Qubits and measurement", 6, ["P1", "P2"], True),
    ("B2", 1, "Gates and circuits", 6, ["B1"], True),
    ("B3", 1, "Entanglement and multi-qubit systems", 6, ["B2"], True),
    ("B4", 1, "Qiskit 2.x fundamentals", 8, ["B3", "P6"], True),
    ("B5", 1, "Noise basics", 6, ["B4"], True),
    ("B6", 1, "Reading the hardware landscape", 5, ["B5"], True),
    ("B7", 1, "The quantum threat to cryptography, first pass", 5, ["B2", "P5"], True),
    ("Q1", "Q", "Version churn", 2, ["B4"], True),
    ("Q2", "Q", "Bit ordering", 2, ["B3"], True),
    ("Q3", "Q", "Counting resources correctly", 3, ["B4"], True),
    ("Q4", "Q", "Simulator limits", 2, ["B5"], True),
    ("I1", 2, "Grover search and amplitude amplification", 6, ["B7", "B6", "Q2"], False),
    ("I2", 2, "QFT and quantum phase estimation", 6, ["I1"], False),
    ("I3", 2, "Quantum amplitude estimation (QAE)", 10, ["I2"], False),
    ("I4", 2, "Data loading (state preparation)", 8, ["I3"], False),
    ("I5", 2, "Option pricing with QAE", 10, ["I4"], False),
    ("I6", 2, "VaR and ES with QAE", 8, ["I5"], False),
    ("I7", 2, "Credit portfolio risk with QAE", 10, ["I6"], False),
    ("I8", 2, "Optimisation: QUBO, Ising and QAOA", 10, ["I3"], False),
    ("I9", 2, "Quantum machine learning", 10, ["I8"], False),
    ("I10", 2, "Error mitigation vs error correction", 6, ["I5"], False),
    ("I11", 2, "PQC algorithms", 8, ["B7"], False),
    ("I12", 2, "Cryptographic inventory (CBOM)", 10, ["I11"], False),
    ("Q5", "Q", "ISA circuits and IBM Runtime", 3, ["I3"], False),
    ("Q6", "Q", "Estimator pitfalls", 3, ["I3"], False),
    ("Q7", "Q", "QAOA pitfalls", 3, ["I8"], False),
    ("Q8", "Q", "Debugging discipline", 2, ["I3"], False),
    ("Q9", "Q", "Reproducibility", 2, ["I3"], False),
    ("A1", 3, "Quantum error correction", 12, ["I10"], False),
    ("A2", 3, "Fault-tolerant resource estimation", 10, ["A1", "I7"], False),
    ("A3", 3, "Runtime, cost and crossover analysis", 8, ["A2"], False),
    ("A4", 3, "Advanced pricing and Greeks", 8, ["A3"], False),
    ("A5", 3, "Rigorous benchmarking", 6, ["I9"], False),
    ("A6", 3, "Cryptanalytic resource estimates and Q-day risk", 6, ["A2", "I12"], False),
    ("A7", 3, "PQC migration engineering", 10, ["I12"], False),
    ("A8", 3, "Regulation, supervision and governance", 8, ["A7"], False),
    ("A9", 3, "Model risk for quantum and hybrid models", 6, ["A5"], False),
    ("A10", 3, "Advisory and business case", 8, ["A3", "A8"], False),
]

CAPSTONES = [
    ("C1", "Replicate the evidence pack", 2, ["I5", "I6", "I7", "I8"]),
    ("C2", "Credit-capital QAE pilot", 3, ["A2", "A3", "I7"]),
    ("C3", "PQC programme for a mock $200B bank", 3, ["A7", "A8", "I12"]),
    ("C4", "QML ablation study", 3, ["I9", "A5"]),
    ("C5", "Pricing on your own options data", 3, ["A3", "A4", "I5"]),
]


_MOD_DIR = __import__("pathlib").Path(__file__).resolve().parent.parent / "content" / "modules"


def registry() -> list[dict]:
    return [
        {"id": i, "level": lv, "title": t, "hours": h, "prereqs": p,
         "built": b and (_MOD_DIR / f"{i.lower()}.py").exists()}
        for i, lv, t, h, p, b in REGISTRY
    ]


def entry(module_id: str) -> dict:
    for e in registry():
        if e["id"] == module_id:
            return e
    raise KeyError(module_id)


@lru_cache(maxsize=None)
def load(module_id: str) -> dict | None:
    e = entry(module_id)
    if not e["built"]:
        return None
    mod = importlib.import_module(f"content.modules.{module_id.lower()}")
    m = dict(mod.MODULE)
    m.setdefault("id", module_id)
    m.setdefault("title", e["title"])
    m["level"] = e["level"]
    m["hours"] = e["hours"]
    m["prereqs"] = e["prereqs"]
    return m


def built_modules() -> list[dict]:
    return [load(e["id"]) for e in registry() if e["built"]]


# ---------- mastery ----------
def is_done(module_id: str) -> bool:
    return db.get_status(module_id) in ("mastered", "tested_out")


def mastery_parts(module_id: str) -> dict:
    q = db.best_quiz(module_id)
    c = db.best_code(module_id)
    r = db.has_passing_report(module_id)
    return {
        "quiz": q,
        "code": c,
        "report_passed": r,
        "quiz_ok": q is not None and q >= MASTERY_QUIZ,
        "code_ok": c is not None and c >= MASTERY_CODE,
    }


def mastery_score(module_id: str) -> float:
    """0..1 composite used on the dashboard: quiz 40%, code 40%, report 20%."""
    if db.get_status(module_id) == "tested_out":
        return 1.0
    p = mastery_parts(module_id)
    rep = db.best_report(module_id)
    return round(0.4 * (p["quiz"] or 0) + 0.4 * (p["code"] or 0) + 0.2 * min(1.0, (rep or 0)), 3)


def refresh_gates() -> None:
    """Recompute statuses: promote to mastered when the gate is met; unlock modules whose prereqs are done."""
    for e in registry():
        mid = e["id"]
        st = db.get_status(mid)
        if st in ("mastered", "tested_out"):
            continue
        if e["built"] and st == "open":
            p = mastery_parts(mid)
            if p["quiz_ok"] and p["code_ok"] and p["report_passed"]:
                db.set_status(mid, "mastered")
                continue
        if st in (None, "locked"):
            if all(is_done(p) for p in e["prereqs"]):
                db.set_status(mid, "open")
            elif st is None:
                db.set_status(mid, "locked")


def status(module_id: str) -> str:
    return db.get_status(module_id) or "locked"


def gate_message(module_id: str) -> str:
    e = entry(module_id)
    missing = [p for p in e["prereqs"] if not is_done(p)]
    if missing:
        return "Locked. Master or test out of: " + ", ".join(missing)
    return ""


def level_modules(level) -> list[dict]:
    return [e for e in registry() if e["level"] == level]
