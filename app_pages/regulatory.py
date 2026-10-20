import json
from pathlib import Path

import pandas as pd
import streamlit as st

from core import claims

DATA = Path(__file__).resolve().parent.parent / "data" / "regulatory.json"
d = json.loads(DATA.read_text())

st.title("Regulatory tracker")
st.markdown(f"Quantum readiness and cryptographic-inventory expectations for large banks. **As of {d['as_of']}.** {d['method']}")
st.error("Where a row says **NO BINDING BANK DEADLINE**, there is none. Do not imply otherwise in client material.", icon="⚖️")

df = pd.DataFrame(d["items"])
df["stale"] = df.last_verified.map(lambda x: "⚠ re-verify" if claims.is_stale(x) else "")
c1, c2, c3 = st.columns(3)
jur = c1.multiselect("Jurisdiction", sorted(df.jurisdiction.unique()))
binding = c2.selectbox("Binding on banks", ["all", "direct only", "indirect / none"])
ver = c3.selectbox("Verification", ["all", "primary", "secondary"])
v = df.copy()
if jur: v = v[v.jurisdiction.isin(jur)]
if binding == "direct only": v = v[v.binding.str.startswith("direct")]
if binding == "indirect / none": v = v[~v.binding.str.startswith("direct")]
if ver != "all": v = v[v.verification.str.startswith(ver)]
st.dataframe(v[["jurisdiction", "body", "title", "date", "verification", "stale"]], hide_index=True, use_container_width=True)
st.caption(f"{len(v)} items. Open an item for the requirement, deadlines and binding status.")
for _, r in v.iterrows():
    flag = " ⚠" if r.stale else ""
    no_deadline = "NO BINDING BANK DEADLINE" in str(r.deadlines)
    with st.expander(f"{r.jurisdiction} · {r.body} — {r.title}{flag}"):
        st.markdown(f"**Status:** {r.status}  \n**Date:** {r.date}  \n**Binds banks:** {r.binding}")
        st.markdown(f"**Requirement:** {r.requirement}")
        (st.error if no_deadline else st.info)(f"Deadlines: {r.deadlines}")
        st.markdown(f"[Source]({r.url}) · verification: {r.verification} · last verified {r.last_verified}")

st.subheader("Turn this into a bank deliverable")
st.markdown("""
1. **Regulatory obligations map** by jurisdiction: filter above to the bank's footprint; separate *direct* (DORA RTS, PCI DSS 12.3.3) from *indirect* (federal mandates via vendors, supervisory roadmaps).
2. **CBOM-based inventory standard**: fields (algorithm, key length, protocol, library, location, owner, data classification, shelf life, vendor dependency, migration difficulty), ownership, refresh cycle (PCI: at least every 12 months). Built in I12.
3. **Mosca-based prioritisation** (B7 lab, extended in I12).
4. **Board risk-appetite statement**: e.g. "no data class with P(exposed) above X% under the reference CRQC distribution after year Y" (Judgement template).
5. **Supervisor-ready migration plan** with milestones mapped to the dates above (2028 / 2030–2031 / 2035).

The regulator's 'Defend it' question: *"Show me your inventory, how complete it is, how you know, and what you will have migrated by 2030."*
""")
st.download_button("Download tracker (JSON)", DATA.read_text(), file_name="regulatory_tracker.json")
