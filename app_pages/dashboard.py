import json
from collections import defaultdict
from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import curriculum, db, tutor

st.title("QFin Lab")
st.caption("Quantum computing for financial services · prerequisites → practice · taskmaster mode")
curriculum.refresh_gates()
from core import auth
if auth.enabled() and db.get_setting("last_backup") != db.today():
    st.info("Cloud storage resets when the app restarts. Download a progress backup before you leave "
            "(Lab environment & settings → Back up and restore).", icon="💾")

# ---------- learning plan ----------
hours = db.get_setting("hours_per_week")
start = db.get_setting("plan_start")
with st.expander("Learning plan" + ("" if hours else " — set this first"), expanded=not hours):
    h = st.number_input("How many hours per week can you genuinely commit?", 1.0, 60.0, float(hours or 8.0), 0.5)
    s = st.date_input("Plan start", value=date.fromisoformat(start) if start else date.today())
    if st.button("Save plan"):
        db.set_setting("hours_per_week", h); db.set_setting("plan_start", s.isoformat()); st.rerun()
    lg = st.number_input("Log study hours not captured automatically", 0.0, 40.0, 0.0, 0.5)
    if st.button("Log hours") and lg > 0:
        db.log_study("manual", lg*60); st.success("Logged.")
if not hours:
    st.info("Set your weekly hours to get a schedule."); st.stop()

order = [e for e in curriculum.registry() if e["level"] in (0, 1, "Q")] + \
        [e for e in curriculum.registry() if e["level"] == 2] + [e for e in curriculum.registry() if e["level"] == 3]
plan, t = [], date.fromisoformat(start)
for e in order:
    t = t + timedelta(days=7*e["hours"]/hours)
    plan.append({"id": e["id"], "title": e["title"], "planned_done": t, "built": e["built"]})
plan_df = pd.DataFrame(plan)
done = {e["id"] for e in curriculum.registry() if curriculum.is_done(e["id"])}
overdue = plan_df[(plan_df.planned_done < date.today()) & (~plan_df.id.isin(done)) & plan_df.built]
logged_h = (db.query("SELECT COALESCE(SUM(minutes),0) AS m FROM study_log")[0]["m"] or 0)/60
weeks = max(1e-9, (date.today() - date.fromisoformat(start)).days/7)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Modules mastered / tested out", f"{len(done)}/{sum(e['built'] for e in curriculum.registry())} built")
c2.metric("Hours logged", f"{logged_h:.1f}", f"{logged_h/weeks:.1f}/wk vs {hours:.0f} planned" if weeks >= 1 else None)
_open = [e["id"] for e in curriculum.registry() if e["built"] and curriculum.status(e["id"]) != "locked"]
due = db.query(f"SELECT COUNT(*) AS n FROM cards WHERE due <= ? AND module_id IN ({','.join('?'*len(_open)) or 'NULL'})",
               (date.today().isoformat(), *_open))[0]["n"]
c3.metric("Cards due", due)
oral = db.query("SELECT AVG(score) AS s FROM (SELECT module_id, MAX(score) AS score FROM oral_rounds GROUP BY module_id)")[0]["s"]
c4.metric("Can I defend this to a client?", f"{oral:.0%}" if oral is not None else "—")
c5.metric("Behind plan", f"{len(overdue)} modules" if len(overdue) else "on track")

if len(overdue):
    remaining = [e for e in order if e["id"] not in done]
    t2, replan = date.today(), []
    for e in remaining:
        t2 = t2 + timedelta(days=7*e["hours"]/hours)
        replan.append({"id": e["id"], "title": e["title"], "re-planned completion": t2})
    st.warning(f"You are behind on {', '.join(overdue.id)}. Re-planned from today at {hours:.0f} h/week below. "
               "Either raise the hours or accept the later dates; do not skip the gates.")
    with st.expander("Re-planned schedule"):
        st.dataframe(pd.DataFrame(replan), hide_index=True, use_container_width=True)
with st.expander("Original schedule"):
    st.dataframe(plan_df, hide_index=True, use_container_width=True)

# ---------- mastery ----------
built = [e for e in curriculum.registry() if e["built"]]
fig = go.Figure(go.Bar(x=[e["id"] for e in built], y=[curriculum.mastery_score(e["id"]) for e in built],
                       marker_color=["#1b7f4b" if curriculum.is_done(e["id"]) else "#0f5c63" for e in built]))
fig.add_hline(y=0.8, line_dash="dot", annotation_text="gate")
fig.update_layout(title="Mastery by module (quiz 40% · code 40% · report 20%)", yaxis_range=[0, 1], height=320, margin=dict(t=40, b=20))
st.plotly_chart(fig, use_container_width=True)

# ---------- weak areas ----------
tag_scores = defaultdict(list)
for row in db.query("SELECT module_id, detail FROM quiz_attempts WHERE kind='quiz'"):
    for d in json.loads(row["detail"] or "[]"):
        for tg in d.get("tags", []):
            tag_scores[(row["module_id"], tg)].append(d["score"])
weak = sorted(((k, sum(v)/len(v), len(v)) for k, v in tag_scores.items()), key=lambda x: x[1])[:10]
c1, c2 = st.columns(2)
with c1:
    st.subheader("Weak areas (from quiz errors)")
    if weak:
        st.dataframe(pd.DataFrame([{"module": k[0], "topic": k[1], "avg score": f"{s:.0%}", "answers": n} for k, s, n in weak]),
                     hide_index=True, use_container_width=True)
    else:
        st.caption("No quiz data yet.")
with c2:
    st.subheader("Lab reports")
    reps = db.query("SELECT module_id, MAX(total) AS best, MAX(passed) AS passed, COUNT(*) AS n FROM lab_reports GROUP BY module_id")
    if reps:
        st.dataframe(pd.DataFrame(reps), hide_index=True, use_container_width=True)
    else:
        st.caption("No reports yet.")

# ---------- level assessment ----------
st.subheader("End-of-level assessment")
lvl = st.selectbox("Level", [0, 1, "Q"], format_func=lambda x: curriculum.LEVELS[x])
mods = [e for e in curriculum.level_modules(lvl) if e["built"]]
complete = all(curriculum.is_done(e["id"]) for e in mods)
if st.button("Write my assessment" + ("" if complete else " (level not complete: interim)")):
    lines, solid, weak_m = [], [], []
    for e in mods:
        p = curriculum.mastery_parts(e["id"]); o = db.best_oral(e["id"])
        (solid if curriculum.is_done(e["id"]) and (o or 0) >= 0.8 else weak_m).append(
            f"{e['id']} {e['title']}: quiz {p['quiz'] or 0:.0%}, code {p['code'] or 0:.0%}, report {'pass' if p['report_passed'] else 'none'}, defend {o or 0:.0%}")
    st.markdown("**Solid**\n" + ("\n".join(f"- {x}" for x in solid) or "- Nothing yet. That is the honest answer."))
    st.markdown("**Weak**\n" + ("\n".join(f"- {x}" for x in weak_m) or "- Nothing flagged."))
    actions = []
    for e in mods:
        p = curriculum.mastery_parts(e["id"])
        if not p["quiz_ok"]: actions.append(f"{e['id']}: retake the quiz after re-reading the concepts you missed.")
        if not p["code_ok"]: actions.append(f"{e['id']}: get the unit tests to ≥80%; read the failure messages literally.")
        if not p["report_passed"]: actions.append(f"{e['id']}: write a lab report that states thresholds before results and decides against them.")
        if (db.best_oral(e["id"]) or 0) < 0.8: actions.append(f"{e['id']}: rerun 'Defend it' until you would survive the room.")
    st.markdown("**Exact next actions**\n" + ("\n".join(f"{i+1}. {a}" for i, a in enumerate(actions[:12])) or "Move to the next level. Don't coast."))
    if tutor.available():
        try:
            st.markdown("**Tutor's verdict (Claude)**\n\n" + tutor.chat("tutor", [{"role": "user", "content":
                "Write a short, blunt end-of-level assessment from this data: what is solid, what is weak, and the exact next actions.\n" +
                "\n".join(solid + weak_m)}]))
        except Exception as ex:
            st.caption(f"(Claude unavailable: {ex})")
