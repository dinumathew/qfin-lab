"""QFin Lab — quantum computing for financial services, from prerequisites to practice.

Run:  streamlit run app.py
"""
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core import auth, bootstrap  # noqa: E402

st.set_page_config(page_title="QFin Lab", page_icon="⚛️", layout="wide")


@st.cache_resource
def _init():
    bootstrap.init()
    return True


auth.require_login()
_init()
auth.logout_button()

P = lambda f, t, i, **k: st.Page(f"app_pages/{f}.py", title=t, icon=i, **k)
pages = {
    "Learn": [
        P("dashboard", "Progress dashboard", "📊", default=True),
        P("placement", "Placement test", "🎯"),
        P("curriculum", "Curriculum map", "🗺️"),
        P("reader", "Module reader", "📖"),
        P("code_lab", "Code lab", "💻"),
        P("empirical_lab", "Empirical lab", "🧪"),
        P("tutor", "Tutor & Defend it", "🧑‍🏫"),
        P("review", "Spaced repetition", "🔁"),
        P("capstones", "Capstones", "🏁"),
    ],
    "Reference": [
        P("evidence", "Evidence ledger", "🧾"),
        P("regulatory", "Regulatory tracker", "⚖️"),
        P("glossary", "Glossary", "🔤"),
        P("environment", "Lab environment & settings", "⚙️"),
    ],
}
st.navigation(pages, expanded=True).run()
