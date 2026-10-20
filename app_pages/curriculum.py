import pandas as pd
import streamlit as st

from core import curriculum, db, ui

st.title("Curriculum map")
curriculum.refresh_gates()
st.caption("🔒 locked · 📖 open · ✅ mastered · ⏭️ tested out · ✎ planned for a later build. "
           "Gate: ≥80% quiz, ≥80% code tests, and a passing lab report.")

for level in [0, 1, "Q", 2, 3]:
    ents = curriculum.level_modules(level)
    st.subheader(curriculum.LEVELS[level])
    rows = []
    for e in ents:
        st_ = curriculum.status(e["id"])
        p = curriculum.mastery_parts(e["id"]) if e["built"] else {}
        rows.append({
            "": ui.STATUS_ICON.get(st_, "") if e["built"] else "✎",
            "id": e["id"], "module": e["title"], "hours": e["hours"],
            "prereqs": ", ".join(e["prereqs"]),
            "quiz": f"{p['quiz']:.0%}" if p.get("quiz") is not None else "",
            "code": f"{p['code']:.0%}" if p.get("code") is not None else "",
            "report": "pass" if p.get("report_passed") else "",
            "mastery": f"{curriculum.mastery_score(e['id']):.0%}" if e["built"] else "planned",
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

st.subheader("Capstones")
st.dataframe(pd.DataFrame([{"id": c, "capstone": t, "unlocks after": ", ".join(req),
                            "ready": "yes" if all(curriculum.is_done(r) for r in req) else "no"} for c, t, _, req in curriculum.CAPSTONES]),
             hide_index=True, use_container_width=True)
