import streamlit as st

from core import curriculum, db, grading, tutor, ui

st.title("Tutor & Defend it")
mid = ui.module_picker()
m = curriculum.load(mid)
if m is None:
    st.info("Not yet authored in this build."); st.stop()
locked = ui.locked_guard(mid)
online = tutor.available()
st.caption(("Claude API connected (model: " + tutor.model_name() + ")") if online else
           "Offline mode: built-in question banks and concept-group grading. Add an API key on the Lab environment page for open dialogue.")

context = m["summary"] + "\n\n" + "\n\n".join(c["title"] + ": " + c["why"] + "\n" + c["how"] for c in m["concepts"])
tab_s, tab_d = st.tabs(["Socratic tutor (taskmaster)", "Defend it (oral round, 5 questions)"])

with tab_s:
    hist_key = f"tutor_hist_{mid}"
    hist = st.session_state.setdefault(hist_key, [])
    if online:
        for h in hist:
            with st.chat_message(h["role"]):
                st.markdown(h["content"])
        if not hist and st.button("Start: ask me the first hard question"):
            hist.append({"role": "user", "content": f"Quiz me on module {mid} ({m['title']}). One hard question at a time."})
            hist.append({"role": "assistant", "content": tutor.chat("tutor", hist, context=context)})
            st.rerun()
        msg = st.chat_input("Answer, or ask a question")
        if msg:
            hist.append({"role": "user", "content": msg})
            db.insert("tutor_log", module_id=mid, role="user", content=msg)
            try:
                reply = tutor.chat("tutor", hist, context=context)
            except Exception as e:
                reply = f"(API error: {e})"
            hist.append({"role": "assistant", "content": reply})
            db.insert("tutor_log", module_id=mid, role="assistant", content=reply)
            st.rerun()
    else:
        bank = [q for q in m["quiz"] if q["type"] == "short"] + [
            {"id": f"d{i}", "q": d["q"], "must": d["must"], "explain": d["model"]} for i, d in enumerate(m["defend"]["questions"])]
        st.session_state.setdefault(f"tq_{mid}", 0)
        q = bank[st.session_state[f"tq_{mid}"] % len(bank)]
        st.markdown(f"#### {q['q']}")
        ans = st.text_area("Your answer", key=f"tans_{mid}_{q['id']}", height=140)
        if st.button("Submit answer", key=f"tsub_{mid}_{q['id']}"):
            s, missing = grading.grade_short(ans, q["must"])
            if s >= 1:
                st.success("Correct. Next one is harder.")
                st.session_state[f"tq_{mid}"] += 1
            elif s >= 0.5:
                st.warning(f"Partially there ({s:.0%}). You did not address: {grading.describe_missing(missing)}. Say it precisely and resubmit.")
            else:
                st.error(f"Vague ({s:.0%}). Missing: {grading.describe_missing(missing)}. Re-read the module section and answer again.")
            with st.expander("Model answer (look only after a genuine attempt)"):
                st.write(q["explain"])
        if st.button("Skip to next question"):
            st.session_state[f"tq_{mid}"] += 1; st.rerun()

with tab_d:
    persona = m["defend"]["persona"]
    label = {"cro": "a sceptical CRO", "validator": "a model validator", "regulator": "a regulator"}[persona]
    st.markdown(f"You are in front of **{label}**. Five questions. Answer as you would in the room: specific, sourced, no hand-waving.")
    with st.form(f"defend_{mid}"):
        answers = [st.text_area(f"Q{i+1}. {d['q']}", key=f"def_{mid}_{i}", height=110) for i, d in enumerate(m["defend"]["questions"])]
        go = st.form_submit_button("Submit the round", disabled=locked)
    if go:
        scores, transcript = [], []
        for d, a in zip(m["defend"]["questions"], answers):
            s, missing = grading.grade_short(a, d["must"])
            scores.append(s)
            transcript.append({"q": d["q"], "a": a, "score": s})
            st.markdown(f"**{d['q']}** — {s:.0%}")
            if missing:
                st.markdown(f"> Missing: {grading.describe_missing(missing)}  \n> A defensible answer: _{d['model']}_")
            if online and a.strip():
                try:
                    st.markdown(tutor.critique_answer(persona, d["q"], a, [d["model"]], context=context))
                except Exception as e:
                    st.caption(f"(Claude critique unavailable: {e})")
        score = sum(scores)/len(scores)
        db.insert("oral_rounds", module_id=mid, persona=persona, score=score, transcript=transcript)
        (st.success if score >= 0.8 else st.error)(
            f"Round score {score:.0%}. " + ("You would survive that meeting." if score >= 0.8 else
                                            "You would lose the room. Fix the gaps and run the round again."))
