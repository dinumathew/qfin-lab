import streamlit as st

from core import curriculum

st.title("Glossary")
terms = {}
for m in curriculum.built_modules():
    for k, v in m.get("glossary", {}).items():
        terms.setdefault(k, (v, []))[1].append(m["id"])
q = st.text_input("Search")
for k in sorted(terms, key=str.lower):
    v, mods = terms[k]
    if q and q.lower() not in (k + v).lower():
        continue
    st.markdown(f"**{k}** — {v}  \n<span style='color:#6b7280;font-size:0.8em'>{', '.join(mods)}</span>", unsafe_allow_html=True)
