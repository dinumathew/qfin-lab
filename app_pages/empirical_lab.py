import json
import re

import streamlit as st

from core import curriculum, db, grading, runner, tutor, ui

st.title("Empirical lab")
mid = ui.module_picker()
m = curriculum.load(mid)
if m is None:
    st.info("Not yet authored in this build."); st.stop()
locked = ui.locked_guard(mid)
lab = m["lab"]
st.subheader(lab["title"])

c1, c2 = st.columns(2)
with c1:
    st.markdown("**1 · Pre-registered hypothesis** (fixed before running)")
    st.info(lab["hypothesis"])
    st.markdown(f"**Pass/fail thresholds:** {lab['thresholds']}")
with c2:
    st.markdown("**2 · Data and provenance**")
    st.write(lab["data"])
    st.markdown("**Leakage checklist**")
    for item in ["Is any test information used to choose parameters?", "Are seeds/windows chosen after seeing results?",
                 "Is the baseline tuned as hard as the method?", "Could look-ahead enter through preprocessing?"]:
        st.checkbox(item, key=f"leak_{mid}_{item[:12]}")

code = lab["code"]
for k in lab.get("learner_blank", []):
    code = re.sub(r'("' + re.escape(k) + r'":\s*)\{[^}]*\}', r'\1{}', code)
key = f"labcode_{mid}"
st.session_state.setdefault(key, code)
with st.expander("Lab code (editable)", expanded=bool(lab.get("learner_blank"))):
    if lab.get("learner_blank"):
        st.warning("Fill in your predictions in PRED before running. The reference answers are hidden.")
    st.text_area("code", key=key, height=420, label_visibility="collapsed")
    if lab.get("learner_blank") and st.checkbox("Reveal reference predictions (after you have run your own)"):
        st.code(lab["code"], language="python")

seed = ui.seed_input(f"labseed_{mid}")
b1, b2 = st.columns(2)
run = b1.button("▶ Run lab", type="primary", disabled=locked)
rep = b2.button("Repeatability: re-run with 3 seeds", disabled=locked)

def _check(rec):
    rows = []
    for name, cond in lab.get("expect", {}).items():
        val = rec.get(name)
        try:
            ok = val is not None and bool(eval(cond, {"x": val, "abs": abs}))
        except Exception:
            ok = False
        rows.append({"metric": name, "value": val, "threshold": cond.replace("x", name), "pass": ok})
    return rows

if run:
    with st.spinner("Running lab in a separate process (some labs take a minute)…"):
        res = runner.run_code(st.session_state[key], seed=seed, timeout=900)
    ui.show_result(res, key=f"lab_{mid}")
    rec = res.to_record(f"{mid}/{lab['id']}", st.session_state[key])
    rec["checks"] = _check(res.record)
    db.insert("lab_runs", module_id=mid, lab_id=lab["id"], seed=seed, record=rec)
    path = runner.export_run(rec, mid, lab["id"])
    st.markdown("**Decision against pre-registered thresholds**")
    st.dataframe(rec["checks"], use_container_width=True)
    st.caption(f"Run record saved to {path.name} in the runs/ folder.")
    ui.json_download(rec, path.name, key=f"dl_{mid}")

if rep:
    out = []
    for s in (seed, seed + 1, seed + 2):
        with st.spinner(f"seed {s}…"):
            r = runner.run_code(st.session_state[key], seed=s, timeout=900)
        out.append({"seed": s, **{k: v for k, v in r.record.items() if isinstance(v, (int, float, bool))}})
    st.dataframe(out, use_container_width=True)
    st.caption("Use these in section 7 (repeatability). State tolerances; do not cherry-pick the best seed.")

st.divider()
st.subheader("Lab report (graded against the nine-step framework)")
if lab.get("report_hints"):
    st.caption("Assessor's hint: " + lab["report_hints"])
last = db.query("SELECT report FROM lab_reports WHERE module_id=? ORDER BY id DESC LIMIT 1", (mid,))
prev = json.loads(last[0]["report"]) if last else {}
report = {}
for k, title, hint in grading.REPORT_HEADINGS:
    default = prev.get(k, "")
    if not default and k == "question":
        default = lab["hypothesis"] + " Thresholds: " + lab["thresholds"]
    if not default and k == "data":
        default = lab["data"]
    report[k] = st.text_area(f"{title}", value=default, help=hint, key=f"rep_{mid}_{k}", height=110)

if st.button("Submit report for grading", disabled=locked):
    g = grading.grade_report(report)
    fb = list(g["feedback"])
    if tutor.available():
        try:
            with st.spinner("Asking the validator persona for a critique…"):
                fb.append("**Validator critique (Claude):**\n\n" + tutor.chat(
                    "validator", [{"role": "user", "content": "Critique this lab report section by section against the nine-step framework. Be harsh and specific.\n\n" +
                                   json.dumps(report, indent=1)}], context=m["summary"]))
        except Exception as e:
            fb.append(f"(Claude critique unavailable: {e})")
    db.insert("lab_reports", module_id=mid, lab_id=lab["id"], report=report, scores=g["scores"], total=g["total"],
              passed=int(g["passed"]), feedback="\n\n".join(fb))
    curriculum.refresh_gates()
    st.dataframe([{"section": t, "score (0-2)": g["scores"][k]} for k, t, _ in grading.REPORT_HEADINGS], use_container_width=True)
    (st.success if g["passed"] else st.error)(f"Rubric {g['total']:.0%} — {'PASS' if g['passed'] else 'FAIL'} (pass needs ≥70% and non-zero hypothesis and decision).")
    for f in fb:
        st.markdown(f)
