from datetime import date

import streamlit as st

from core import curriculum, db
from core.sm2 import CardState, review

st.title("Spaced repetition")
st.caption("SM-2 scheduling. Grade yourself honestly: 5 perfect · 4 hesitated · 3 hard · 2 wrong but familiar · 1 wrong · 0 blank.")

open_mods = [e["id"] for e in curriculum.registry() if e["built"] and curriculum.status(e["id"]) != "locked"]
if not open_mods:
    st.info("No unlocked modules yet."); st.stop()
qs = ",".join("?" * len(open_mods))
due = db.query(f"SELECT * FROM cards WHERE module_id IN ({qs}) AND due <= ? ORDER BY due, module_id", (*open_mods, date.today().isoformat()))
total = db.query(f"SELECT COUNT(*) AS n FROM cards WHERE module_id IN ({qs})", tuple(open_mods))[0]["n"]
c1, c2 = st.columns(2)
c1.metric("Due now", len(due)); c2.metric("Cards in unlocked modules", total)
if not due:
    st.success("Nothing due. Come back tomorrow, or study a new module."); st.stop()

card = due[0]
st.markdown(f"**{card['module_id']}** · _{card['kind']}_")
st.markdown(f"### {card['front']}")
if st.session_state.get("show_back") != card["card_id"]:
    if st.button("Show answer", type="primary"):
        st.session_state["show_back"] = card["card_id"]; st.rerun()
else:
    st.info(card["back"])
    cols = st.columns(6)
    for q, col in zip(range(5, -1, -1), cols):
        if col.button(str(q), key=f"q{q}"):
            new, nxt = review(CardState(card["easiness"], card["interval"], card["repetitions"], card["lapses"]), q)
            with db.conn() as c:
                c.execute("UPDATE cards SET easiness=?, interval=?, repetitions=?, lapses=?, due=?, last_review=? WHERE card_id=?",
                          (new.easiness, new.interval, new.repetitions, new.lapses, nxt.isoformat(), date.today().isoformat(), card["card_id"]))
                c.execute("INSERT INTO card_reviews(card_id,quality,reviewed_at) VALUES(?,?,?)", (card["card_id"], q, db.now()))
            st.session_state.pop("show_back", None); st.rerun()
