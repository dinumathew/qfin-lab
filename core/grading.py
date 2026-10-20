"""Offline graders: short answers (concept groups), lab reports (nine-heading rubric).

These are deliberately strict. When a Claude API key is configured, core.tutor
adds a second, model-based critique on top; the offline score still counts.
"""
from __future__ import annotations

import re

REPORT_HEADINGS = [
    ("question", "1. Question and hypothesis",
     "State the hypothesis and the numeric pass/fail threshold BEFORE running anything."),
    ("data", "2. Data and provenance",
     "Source, date range, real or synthetic, cleaning steps, leakage risks."),
    ("baseline", "3. Classical baseline, optimised first",
     "Vectorised NumPy, variance reduction or closed form; timed on your machine."),
    ("quantum", "4. Quantum method",
     "Circuit design, qubit count, data loading method, estimator (or N/A with reason)."),
    ("metrics", "5. Metrics",
     "Bias, RMSE, CIs over >=30 seeds, log-log slope, transpiled resource counts, wall time, cost."),
    ("controls", "6. Controls and ablations",
     "What else could explain the result: noise, leakage, transpiler randomness, feature expansion."),
    ("repeat", "7. Repeatability",
     "Seeds, versions, re-runs, tolerances met or not."),
    ("decision", "8. Decision",
     "Pass/fail against the thresholds fixed in step 1. Never moved after seeing results."),
    ("business", "9. Business translation",
     "What it means for cost, capital, risk or timeline, and what it does NOT mean."),
]

# signals a section must contain to earn full marks (any synonym in a group)
REPORT_SIGNALS = {
    "question": [[r"\d"], ["hypothes", "expect", "predict"], ["threshold", "pass", "fail", "tolerance", "±", "+/-", "within"]],
    "data": [["synthetic", "real", "simulat", "source", "generated"], ["leak", "look-ahead", "lookahead", "contamina", "n/a", "none because"]],
    "baseline": [["numpy", "vector", "closed form", "closed-form", "analytic", "black-scholes", "exact", "antithetic", "control variate"], ["ms", "seconds", " s ", "time", "timed", "µs", "us"]],
    "quantum": [["qubit", "circuit", "n/a", "not applicable", "classical-only"]],
    "metrics": [[r"\d"], ["rmse", "bias", "slope", "ci", "confidence", "fidelity", "error", "cx", "depth"]],
    "controls": [["control", "ablation", "noise", "seed", "leak", "shuffle", "altern"]],
    "repeat": [["seed"], ["version", "qiskit", "numpy", "re-run", "rerun", "repeat"]],
    "decision": [["pass", "fail"], ["threshold", "step 1", "pre-registered", "preregistered", "fixed"]],
    "business": [["client", "bank", "cost", "capital", "risk", "desk", "board", "cro", "budget"], ["not mean", "does not", "doesn't", "cannot", "limit", "caveat", "only"]],
}

PASS_TOTAL = 0.70  # fraction of rubric points


def _has(text: str, group: list[str]) -> bool:
    t = text.lower()
    for g in group:
        if g.startswith("\\") or any(ch in g for ch in "[]()*+?"):
            if re.search(g, t):
                return True
        elif g in t:
            return True
    return False


def grade_report(report: dict[str, str]) -> dict:
    """Each heading scores 0 (missing), 1 (thin) or 2 (solid). Pass needs >=70% and non-zero on question and decision."""
    scores, feedback = {}, []
    for key, title, hint in REPORT_HEADINGS:
        txt = (report.get(key) or "").strip()
        words = len(txt.split())
        if words < 8:
            scores[key] = 0
            feedback.append(f"**{title}**: missing or one-liner. Required: {hint}")
            continue
        sig = REPORT_SIGNALS.get(key, [])
        hits = [g for g in sig if _has(txt, g)]
        if len(hits) == len(sig) and words >= 25:
            scores[key] = 2
        else:
            scores[key] = 1
            miss = [g for g in sig if g not in hits]
            need = "; ".join("/".join(g[:3]) for g in miss) or "more substance (25+ words of specifics)"
            feedback.append(f"**{title}**: thin. Missing: {need}.")
    total = sum(scores.values()) / (2 * len(REPORT_HEADINGS))
    passed = total >= PASS_TOTAL and scores["question"] > 0 and scores["decision"] > 0
    if report.get("question") and report.get("decision"):
        nums_q = set(re.findall(r"\d+(?:\.\d+)?", report["question"]))
        nums_d = set(re.findall(r"\d+(?:\.\d+)?", report["decision"]))
        if nums_q and nums_d and not (nums_q & nums_d):
            feedback.append("**Decision**: none of the thresholds from step 1 appear in your decision. "
                            "Either you moved the goalposts or you did not compare against them. Fix it.")
    return {"scores": scores, "total": round(total, 3), "passed": passed, "feedback": feedback}


def grade_short(answer: str, must: list[list[str]]) -> tuple[float, list[list[str]]]:
    """Return (score 0..1, missing concept groups). Each group is a list of acceptable synonyms."""
    if not must:
        return (1.0 if answer.strip() else 0.0), []
    missing = [g for g in must if not _has(answer, g)]
    return 1 - len(missing) / len(must), missing


def describe_missing(missing: list[list[str]]) -> str:
    return "; ".join(f"'{g[0]}'" + (f" (or {', '.join(g[1:3])})" if len(g) > 1 else "") for g in missing)
