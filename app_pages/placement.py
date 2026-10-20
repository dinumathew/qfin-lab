import random

import streamlit as st

from core import curriculum, db, grading

st.title("Placement test")
st.markdown(
    "Test out of any authored module. You get 6 questions per module (mixed multiple choice and short answer), drawn "
    "from a fixed seed so retakes see a different mix. **≥80% marks the module as tested out** and unlocks what depends on it. "
    "Below that, you study it. No partial credit for confidence."
)
built = [e for e in curriculum.registry() if e["built"]]
choices = st.multiselect("Modules to test out of", [e["id"] for e in built],
                         format_func=lambda i: f"{i} · {curriculum.entry(i)['title']} ({curriculum.status(i)})",
                         default=[e["id"] for e in built if e["level"] == 0 and curriculum.status(e["id"]) not in ("mastered", "tested_out")][:2])
attempt = len(db.query("SELECT id FROM quiz_attempts WHERE kind='placement'"))
rng = random.Random(1000 + attempt)

if choices:
    picks = {}
    for mid in choices:
        m = curriculum.load(mid)
        mc = [q for q in m["quiz"] if q["type"] == "mc"]; sa = [q for q in m["quiz"] if q["type"] == "short"]
        picks[mid] = rng.sample(mc, min(5, len(mc))) + rng.sample(sa, min(1, len(sa)))
    with st.form("placement"):
        answers = {}
        for mid, qs in picks.items():
            st.subheader(f"{mid} · {curriculum.entry(mid)['title']}")
            for q in qs:
                k = f"pl_{attempt}_{mid}_{q['id']}"
                st.markdown(f"**{q['q']}**")
                if q["type"] == "mc":
                    answers[(mid, q["id"])] = st.radio("a", list(range(len(q["options"]))), format_func=lambda i, q=q: q["options"][i],
                                                       index=None, key=k, label_visibility="collapsed")
                else:
                    answers[(mid, q["id"])] = st.text_area("a", key=k, height=80, label_visibility="collapsed")
        sub = st.form_submit_button("Submit placement test")
    if sub:
        for mid, qs in picks.items():
            tot = 0.0
            for q in qs:
                a = answers[(mid, q["id"])]
                tot += (1.0 if a == q["answer"] else 0.0) if q["type"] == "mc" else grading.grade_short(a or "", q["must"])[0]
            score = tot/len(qs)
            db.insert("quiz_attempts", module_id=mid, kind="placement", score=score, n_questions=len(qs), detail=[q["id"] for q in qs])
            if score >= 0.8:
                db.set_status(mid, "tested_out")
                st.success(f"{mid}: {score:.0%}. Tested out.")
            else:
                st.error(f"{mid}: {score:.0%}. Not enough. Study the module.")
        curriculum.refresh_gates()
