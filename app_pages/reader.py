import time

import streamlit as st

from core import curriculum, db, grading, ui

st.title("Module reader")
mid = ui.module_picker()
m = curriculum.load(mid)
if m is None:
    st.info("This module is on the curriculum map but not yet authored in this build.")
    st.stop()
locked = ui.locked_guard(mid)
st.caption(f"{curriculum.LEVELS[m['level']]} · est. {m['hours']} h · prerequisites: {', '.join(m['prereqs']) or 'none'} · status: {curriculum.status(mid)}")
ui.md(m["summary"])

if "read_start" not in st.session_state or st.session_state.get("read_mod") != mid:
    st.session_state["read_start"], st.session_state["read_mod"] = time.time(), mid

tabs = st.tabs(["Concepts (why · how · impact)", "Practitioner lens", "Quiz", "Notes", "Claims in this module"])

with tabs[0]:
    for i, c in enumerate(m["concepts"], 1):
        st.subheader(f"{i}. {c['title']}")
        a, b, cc = st.tabs(["① Why", "② How", "③ Business impact"])
        with a:
            ui.md(c["why"])
        with b:
            ui.md(c["how"])
            st.markdown("**Minimal example** (run or edit it in the Code lab)")
            st.code(c["code"], language="python")
            if st.button("Run this example", key=f"run_{mid}_{i}"):
                from core.runner import run_code
                with st.spinner("Running in a separate Python process…"):
                    ui.show_result(run_code(c["code"]), key=f"ex_{mid}_{i}")
        with cc:
            ui.md(c["impact"])
        st.divider()

with tabs[1]:
    L = m["lens"]
    st.markdown("#### How a practitioner looks at it"); ui.md(L["look"])
    st.markdown("#### What decision it feeds"); ui.md(L["decision"])
    st.markdown("#### Why that decision is justified"); ui.md(L["justified"])
    st.markdown("#### Common mistakes"); ui.md("\n".join(f"- {x}" for x in L["mistakes"]))
    st.markdown("#### Likely impact of those mistakes"); ui.md(L["impact"])
    st.markdown("#### Empirical test"); ui.md(L["test"] + "  \n→ run it on the **Empirical lab** page.")

with tabs[2]:
    best = db.best_quiz(mid)
    st.caption(f"Mastery gate: ≥{int(curriculum.MASTERY_QUIZ*100)}%. Best so far: {('%.0f%%' % (100*best)) if best is not None else '—'}")
    with st.form(f"quiz_{mid}"):
        answers = {}
        for q in m["quiz"]:
            st.markdown(f"**{q['q']}**")
            if q["type"] == "mc":
                answers[q["id"]] = st.radio("Answer", list(range(len(q["options"]))), format_func=lambda i, q=q: q["options"][i],
                                            index=None, key=f"{mid}_{q['id']}", label_visibility="collapsed")
            else:
                answers[q["id"]] = st.text_area("Your answer", key=f"{mid}_{q['id']}", height=90, label_visibility="collapsed")
        submitted = st.form_submit_button("Submit for grading", disabled=locked)
    if submitted:
        detail, total = [], 0.0
        for q in m["quiz"]:
            a = answers[q["id"]]
            if q["type"] == "mc":
                ok = a == q["answer"]; s = 1.0 if ok else 0.0
                detail.append({"id": q["id"], "score": s, "tags": q.get("tags", []), "given": a})
                if not ok:
                    st.error(f"✗ {q['q']}\n\nCorrect: **{q['options'][q['answer']]}**. {q['explain']}")
            else:
                s, missing = grading.grade_short(a or "", q["must"])
                detail.append({"id": q["id"], "score": s, "tags": q.get("tags", []), "given": a})
                if s < 1:
                    st.warning(f"◐ {q['q']}\n\nScore {s:.0%}. Missing: {grading.describe_missing(missing)}. "
                               f"Model answer: {q['explain']}")
            total += s
        score = total/len(m["quiz"])
        db.insert("quiz_attempts", module_id=mid, kind="quiz", score=score, n_questions=len(m["quiz"]), detail=detail)
        db.log_study(mid, (time.time() - st.session_state["read_start"])/60)
        st.session_state["read_start"] = time.time()
        curriculum.refresh_gates()
        if score >= curriculum.MASTERY_QUIZ:
            st.success(f"{score:.0%}. Above the gate. Don't relax: the code exercise and lab report are still between you and mastery.")
        else:
            wrong_tags = sorted({t for d in detail if d['score'] < 1 for t in d['tags']})
            st.error(f"{score:.0%}. Below the {int(curriculum.MASTERY_QUIZ*100)}% gate. Weak on: {', '.join(wrong_tags)}. "
                     "Re-read those concepts, then retake. Guessing your way past this gate will cost you in front of a client.")

with tabs[3]:
    note = st.text_area("Your notes (saved locally)", value=db.get_note(mid), height=300, key=f"note_{mid}")
    if st.button("Save notes"):
        db.save_note(mid, note); st.success("Saved.")

with tabs[4]:
    for c in m["claims"]:
        name = {"M": "Measured", "S": "Sourced", "J": "Judgement"}[c["tag"]]
        line = f"**{name}** — {c['text']}"
        if c["tag"] == "S":
            s = c["source"]
            line += f"  \n_{s['title']}_, {s['publisher']}, {s['date']}. [link]({s['url']}) · last verified {c.get('last_verified')}"
        st.markdown(line)
