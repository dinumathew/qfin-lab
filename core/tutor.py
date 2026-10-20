"""Taskmaster tutor. Uses the Claude API when a key is supplied; otherwise built-in question banks.

The key is read from the ANTHROPIC_API_KEY environment variable or the Settings
field (stored only in local SQLite). Nothing is sent anywhere without a key.
"""
from __future__ import annotations

import os

from core import db

DEFAULT_MODEL = "claude-sonnet-5-5"

PERSONAS = {
    "tutor": (
        "You are a hard-taskmaster tutor in quantum computing for finance. The learner has ~20 years in "
        "credit risk, Basel III/CCAR/CECL and model risk governance, holds the CQF, and runs a live algo "
        "system on Indian index options. Strong in stochastic calculus, Monte Carlo and Python; new to "
        "quantum mechanics and cryptography. Rules: be direct and critical, no gentle validation. Use the "
        "Socratic method: ask one sharp question at a time. When an answer is vague, say exactly what is "
        "missing and ask again. When it is right, confirm in one line and raise the difficulty. Tag any "
        "factual claim you make as [Sourced: title, publisher, date], [Measured] or [Judgement]. Never "
        "state a vendor roadmap, hardware number or regulatory deadline without a source and date; if "
        "unsure, say so. Keep implementation checks separate from value claims."
    ),
    "cro": (
        "You are a sceptical Chief Risk Officer at a large bank. A consultant is pitching quantum or PQC "
        "work. You care about capital, P&L, model risk, cost and reputational exposure. Ask hard, specific "
        "questions; reject hand-waving; demand numbers, baselines and stop rules."
    ),
    "validator": (
        "You are a senior model validator applying SR 11-7-style standards. You probe conceptual soundness, "
        "data, implementation testing, outcomes analysis, reproducibility, and limitations. You do not "
        "accept vendor claims without evidence."
    ),
    "regulator": (
        "You are a bank supervisor examining quantum readiness and cryptographic inventory. You ask: show "
        "me your inventory, how complete it is, how you know, and what you will have migrated by 2030. You "
        "are precise and unimpressed by slides."
    ),
}


def _secret(name: str):
    try:
        import streamlit as st
        return st.secrets.get(name)
    except Exception:
        return None


def api_key() -> str | None:
    return (os.environ.get("ANTHROPIC_API_KEY") or _secret("ANTHROPIC_API_KEY")
            or db.get_setting("anthropic_api_key") or None)


def model_name() -> str:
    return db.get_setting("claude_model") or DEFAULT_MODEL


def available() -> bool:
    if not api_key():
        return False
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return True


def chat(persona: str, messages: list[dict], context: str = "", max_tokens: int = 900) -> str:
    """messages: [{'role': 'user'|'assistant', 'content': str}]."""
    import anthropic

    client = anthropic.Anthropic(api_key=api_key())
    system = PERSONAS.get(persona, PERSONAS["tutor"])
    if context:
        system += "\n\nModule context (what the learner has been taught):\n" + context[:12000]
    resp = client.messages.create(model=model_name(), max_tokens=max_tokens, system=system, messages=messages)
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


def critique_answer(persona: str, question: str, answer: str, key_points: list[str], context: str = "") -> str:
    prompt = (
        f"Question: {question}\n\nLearner's answer:\n{answer}\n\nKey points a strong answer must cover:\n- "
        + "\n- ".join(key_points)
        + "\n\nGrade 0-10. State in bullets exactly what is missing or wrong, then one follow-up question that "
        "raises the difficulty. Start your reply with 'Score: N/10'."
    )
    return chat(persona, [{"role": "user", "content": prompt}], context=context, max_tokens=600)
