import streamlit as st

from core import curriculum, db, runner, ui

st.title("Code lab")
mid = ui.module_picker()
m = curriculum.load(mid)
if m is None:
    st.info("Not yet authored in this build."); st.stop()
locked = ui.locked_guard(mid)
ex = m["exercise"]

st.markdown(
    """
    <style>textarea {font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace !important; font-size: 0.86rem !important;}</style>
    """, unsafe_allow_html=True)

tab_ex, tab_scratch, tab_examples = st.tabs(["Graded exercise", "Scratch cell", "Concept examples"])

with tab_ex:
    st.subheader(ex["title"])
    st.markdown(ex["prompt"])
    key = f"code_{mid}"
    if key not in st.session_state:
        last = db.query("SELECT code FROM code_attempts WHERE module_id=? ORDER BY id DESC LIMIT 1", (mid,))
        st.session_state[key] = last[0]["code"] if last else ex["starter"]
    code = st.text_area("Your code", key=key, height=420)
    seed = ui.seed_input(f"seed_ex_{mid}")
    c1, c2, c3 = st.columns(3)
    run_clicked = c1.button("▶ Run", key=f"run_{mid}")
    grade_clicked = c2.button("✔ Run unit tests (graded)", type="primary", disabled=locked, key=f"grade_{mid}")
    if c3.button("Reset to starter", key=f"reset_{mid}"):
        st.session_state.pop(key, None); st.rerun()
    if run_clicked:
        with st.spinner("Running…"):
            ui.show_result(runner.run_code(code, seed=seed), key=f"exrun_{mid}")
    if grade_clicked:
        with st.spinner("Grading in a separate process…"):
            g = runner.grade(code, ex["tests"], seed=seed)
        db.insert("code_attempts", module_id=mid, exercise_id=ex["id"], score=g.score, passed=g.passed,
                  total=g.total, code=code, detail=g.results)
        curriculum.refresh_gates()
        if g.load_error:
            st.error("Your code does not even load. Fix this first:"); st.code(g.load_error)
        else:
            for r in g.results:
                if r["passed"]:
                    st.markdown(f"✅ `{r['test']}` {r['doc']}")
                else:
                    st.markdown(f"❌ `{r['test']}` {r['doc']}  \n&nbsp;&nbsp;&nbsp;→ {r.get('error', '')}")
            if g.score >= curriculum.MASTERY_CODE:
                st.success(f"{g.passed}/{g.total} passed ({g.score:.0%}). Gate met. Now explain to yourself why each test exists.")
            else:
                st.error(f"{g.passed}/{g.total} passed ({g.score:.0%}). Below {int(curriculum.MASTERY_CODE*100)}%. "
                         "Read each failure message literally; it tells you what is wrong.")
    with st.expander("Unit tests (read them: they are the specification)"):
        st.code(ex["tests"], language="python")
    attempts = db.query("SELECT score FROM code_attempts WHERE module_id=?", (mid,))
    best = max((a["score"] for a in attempts), default=0)
    if best >= 1.0 or len(attempts) >= 3:
        with st.expander("Reference solution (unlocked after 3 attempts or a full pass)"):
            st.code(ex["solution"], language="python")
    else:
        st.caption(f"Reference solution unlocks after 3 graded attempts or a full pass ({len(attempts)}/3).")

with tab_scratch:
    st.caption("Free cell. `from qlab_helpers import SEED, rng, show, record, table` gives you seeds, plotting and run records.")
    sk = f"scratch_{mid}"
    st.session_state.setdefault(sk, "from qlab_helpers import SEED, rng, show, record\nimport numpy as np\nprint('seed', SEED, rng.standard_normal(3))\n")
    scode = st.text_area("Scratch", key=sk, height=300)
    sseed = ui.seed_input(f"seed_sc_{mid}")
    if st.button("▶ Run scratch", key=f"runs_{mid}"):
        with st.spinner("Running…"):
            res = runner.run_code(scode, seed=sseed)
        ui.show_result(res, key=f"scr_{mid}")
        rec = res.to_record(f"{mid}-scratch", scode)
        ui.json_download(rec, f"{mid}_scratch_seed{sseed}.json", key=f"dl_s_{mid}")

with tab_examples:
    for i, c in enumerate(m["concepts"]):
        ek = f"exc_{mid}_{i}"
        st.session_state.setdefault(ek, c["code"])
        st.markdown(f"**{c['title']}**")
        ecode = st.text_area("Example", key=ek, height=200, label_visibility="collapsed")
        if st.button("▶ Run", key=f"runx_{mid}_{i}"):
            ui.show_result(runner.run_code(ecode), key=f"exx_{mid}_{i}")
