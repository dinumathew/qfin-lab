import pandas as pd
import streamlit as st

from core import claims, curriculum, runner

st.title("Evidence ledger")
st.markdown("Every factual claim in the app, with its tag. **Measured** claims are re-checked by code; **Sourced** claims carry "
            "title, publisher, date, link and a last-verified stamp (flagged after six months if time-sensitive); **Judgement** is opinion, labelled.")
rows = []
for m in curriculum.built_modules():
    for c in m["claims"]:
        s = c.get("source", {})
        rows.append({"module": m["id"], "id": c["id"], "tag": claims.TAG_STYLE[c["tag"]][0], "claim": c["text"],
                     "source": f"{s.get('title','')} — {s.get('publisher','')}" if s else "", "date": s.get("date", ""),
                     "link": s.get("url", ""), "last verified": c.get("last_verified", ""),
                     "re-verify": "⚠ yes" if c.get("time_sensitive") and claims.is_stale(c.get("last_verified")) else ""})
df = pd.DataFrame(rows)
f1, f2 = st.columns(2)
tag = f1.multiselect("Tag", ["Measured", "Sourced", "Judgement"], default=["Measured", "Sourced", "Judgement"])
mod = f2.multiselect("Module", sorted(df.module.unique()))
v = df[df.tag.isin(tag) & (df.module.isin(mod) if mod else True)]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Claims", len(v)); c2.metric("Measured", (v.tag == "Measured").sum()); c3.metric("Sourced", (v.tag == "Sourced").sum())
c4.metric("Need re-verification", (v["re-verify"] != "").sum())
st.dataframe(v, hide_index=True, use_container_width=True, column_config={"link": st.column_config.LinkColumn()})

st.subheader("Re-run Measured claims")
st.caption("Implementation checks, not value claims: they prove the code says what the text says.")
if st.button("Re-check all Measured claims now"):
    out = []
    for m in curriculum.built_modules():
        for c in m["claims"]:
            if c["tag"] == "M":
                r = runner.run_code(c["check"], timeout=300)
                out.append({"id": c["id"], "holds": "✅" if r.ok else "❌", "error": "" if r.ok else r.stderr.strip().splitlines()[-1][:200]})
    st.dataframe(pd.DataFrame(out), hide_index=True, use_container_width=True)
