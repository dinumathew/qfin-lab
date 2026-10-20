import streamlit as st

from core import curriculum

st.title("Capstones")
st.caption("Each capstone unlocks when its prerequisite modules are mastered or tested out. Briefs below are the full specification; "
           "the guided build arrives with the Level 2–3 content.")
BRIEFS = {
    "C1": """Rebuild the pricing (I5), VaR (I6), credit (I7) and QAOA (I8) toys from scratch and match the replication targets within stated tolerances:
circuit counts; data-loading shares; RMSE against Monte Carlo at 6,800 queries; error-vs-queries slopes; the noise sweep at per-CX error rates
of 1e-2, 1e-3 and 1e-4; maximum logical error per CX for 90% success (≈ 0.1 ÷ CX count). Write a lab report explaining every discrepancy.""",
    "C2": """Synthetic or public loan portfolio (e.g. built from Freddie Mac single-family loan-level data) with PDs from a simple model: toy QAE on the
emulator; client-scale resource estimate; projected runtime across clock rates; a timed, optimised classical baseline (importance sampling);
an S1–S8 style stop-rule decision and a one-page CRO memo.""",
    "C3": """CBOM from the lab scan, extrapolated with stated assumptions; regulatory obligations map; Mosca prioritisation; 3-year migration plan with
cost ranges; board paper. Scan only systems you own or have permission to test.""",
    "C4": """Rerun an HSBC-style quantum feature-map experiment at small scale on public data with all controls: classical random features of equal
dimension; calibrated noisy simulation; shuffled features; five or more rolling windows with confidence intervals; blinding-gap sweep. Conclude
whether any gain is attributable to quantum effects.""",
    "C5": """Use NIFTY or Bank Nifty option-chain data you supply to calibrate a distribution. Price a vanilla and a path-dependent payoff classically.
Build the QAE toy version, produce a full-scale resource and runtime estimate, and state when, if ever, it would beat the classical engine for that desk.""",
}
for cid, title, level, req in curriculum.CAPSTONES:
    ready = all(curriculum.is_done(r) for r in req)
    with st.expander(f"{'🔓' if ready else '🔒'} {cid} · {title}  (after {', '.join(req)})", expanded=ready):
        st.markdown(BRIEFS[cid])
        if not ready:
            missing = [r for r in req if not curriculum.is_done(r)]
            st.caption("Still needed: " + ", ".join(missing))
