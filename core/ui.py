"""Shared Streamlit rendering helpers."""
from __future__ import annotations

import json

import pandas as pd
import plotly.io as pio
import streamlit as st

from core import claims, curriculum, db
from core.runner import RunResult

STATUS_ICON = {"locked": "🔒", "open": "📖", "mastered": "✅", "tested_out": "⏭️"}


@st.cache_data(show_spinner=False)
def _claim_idx():
    return claims.claim_index(curriculum.built_modules())


def md(text: str) -> None:
    st.markdown(claims.render(text, _claim_idx()), unsafe_allow_html=True)


def show_result(res: RunResult, key: str = "") -> None:
    if res.stdout.strip():
        st.code(res.stdout[-15000:], language="text")
    for i, f in enumerate(res.figures):
        st.plotly_chart(pio.from_json(f), use_container_width=True, key=f"{key}_fig{i}")
    for t in res.tables:
        if t.get("name"):
            st.caption(t["name"])
        st.dataframe(pd.read_json(t["data"], orient="split"), use_container_width=True)
    if not res.ok:
        st.error("Run failed")
        st.code(res.stderr[-6000:], language="text")
    elif res.stderr.strip():
        with st.expander("stderr / warnings (read these: deprecation warnings matter)"):
            st.code(res.stderr[-6000:], language="text")
    st.caption(f"seed={res.seed} · wall time {res.wall_s:.2f}s")


def module_picker(label: str = "Module", only_built: bool = True, key: str = "mod_pick",
                  default: str | None = None) -> str | None:
    curriculum.refresh_gates()
    ents = [e for e in curriculum.registry() if (e["built"] or not only_built)]
    opts = [e["id"] for e in ents]
    fmt = {e["id"]: f'{STATUS_ICON.get(curriculum.status(e["id"]), "")} {e["id"]} · {e["title"]}' for e in ents}
    default = default or st.session_state.get("current_module") or opts[0]
    idx = opts.index(default) if default in opts else 0
    choice = st.selectbox(label, opts, index=idx, format_func=lambda x: fmt[x], key=key)
    st.session_state["current_module"] = choice
    return choice


def locked_guard(module_id: str) -> bool:
    """Return True if locked (and show message)."""
    if curriculum.status(module_id) == "locked":
        st.warning(curriculum.gate_message(module_id) +
                   ". You can still read it, but labs, quizzes and grading unlock with the gate. "
                   "Or test out on the Placement test page.")
        return True
    return False


def seed_input(key: str) -> int:
    default = int(db.get_setting("default_seed", 1234))
    return int(st.number_input("Seed (shown in every run record)", value=default, step=1, key=key))


def json_download(record: dict, name: str, key: str) -> None:
    st.download_button("Export run as JSON", json.dumps(record, indent=2), file_name=name,
                       mime="application/json", key=key)
