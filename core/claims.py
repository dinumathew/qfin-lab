"""Evidence ledger: every factual claim is Measured, Sourced or Judgement.

In module text, write {{c:claim_id}} after a sentence; it renders as a tag
linking to the ledger entry. Sourced claims must carry title, publisher,
date, url and last_verified. Measured claims carry a `check` snippet that
the self-test executes.
"""
from __future__ import annotations

import re
from datetime import date

STALE_DAYS = 183  # six months

TAG_STYLE = {
    "M": ("Measured", "#1b7f4b"),
    "S": ("Sourced", "#2457a6"),
    "J": ("Judgement", "#9a5b00"),
}

_PAT = re.compile(r"\{\{c:([A-Za-z0-9_\-\.]+)\}\}")


def is_stale(last_verified: str | None, today: date | None = None) -> bool:
    if not last_verified:
        return True
    today = today or date.today()
    try:
        d = date.fromisoformat(last_verified[:10])
    except ValueError:
        return True
    return (today - d).days > STALE_DAYS


def claim_index(modules: list[dict]) -> dict[str, dict]:
    idx = {}
    for m in modules:
        for c in m.get("claims", []):
            c = dict(c)
            c["module"] = m["id"]
            idx[c["id"]] = c
    return idx


def badge(c: dict) -> str:
    name, color = TAG_STYLE[c["tag"]]
    stale = c["tag"] == "S" and c.get("time_sensitive") and is_stale(c.get("last_verified"))
    extra = " ⚠ re-verify" if stale else ""
    return (f'<span title="{c["text"][:180].replace(chr(34), "")}" style="font-size:0.72em;'
            f'padding:1px 6px;border-radius:8px;border:1px solid {color};color:{color};'
            f'white-space:nowrap">{name}{extra}</span>')


def render(text: str, idx: dict[str, dict]) -> str:
    def rep(m):
        c = idx.get(m.group(1))
        if not c:
            return '<span style="color:#b00020;font-size:0.72em">[untagged claim id]</span>'
        return badge(c)
    return _PAT.sub(rep, text)


def referenced_ids(text: str) -> list[str]:
    return _PAT.findall(text)
