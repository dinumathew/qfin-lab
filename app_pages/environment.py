import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

from core import db, env, tutor

ROOT = Path(__file__).resolve().parent.parent
st.title("Lab environment & settings")

st.subheader("Installed versions")
v = env.versions()
rows = [{"package": "python", "installed": v["python"], "pinned": "3.11+", "ok": "✅" if sys.version_info >= (3, 11) else "❌"},
        {"package": "platform", "installed": v["platform"], "pinned": "", "ok": ""}]
for p, spec in env.PINNED.items():
    ok = env.pin_ok(p, v.get(p))
    rows.append({"package": p, "installed": v.get(p) or "not installed", "pinned": spec, "ok": {True: "✅", False: "❌", None: "—"}[ok]})
st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
if v.get("liboqs-python"):
    try:
        import oqs  # noqa: F401
        st.caption("liboqs loaded: " + oqs.oqs_version())
    except Exception as e:
        st.warning(f"liboqs-python is installed but the C library failed to load: {e}. See README (PQC setup).")

st.subheader("Self-test")
st.caption("Executes every concept example, every lab, every Measured-claim check and every exercise solution against its tests. "
           "Fast mode skips the two heavy labs (B5, Q4).")
fast = st.checkbox("Fast mode", value=True)
if st.button("Run self-test", type="primary"):
    with st.spinner("Running pytest… (2–6 minutes)"):
        envv = dict(__import__("os").environ, QLAB_FAST="1" if fast else "0")
        p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(ROOT / "tests")],
                           cwd=ROOT, capture_output=True, text=True, env=envv)
    (st.success if p.returncode == 0 else st.error)("All checks passed." if p.returncode == 0 else "Failures — read below.")
    st.code(p.stdout[-12000:] + p.stderr[-3000:])

st.subheader("Settings")
seed = st.number_input("Default random seed", value=int(db.get_setting("default_seed", 1234)), step=1)
model = st.text_input("Claude model for the tutor", value=tutor.model_name())
key = st.text_input("Anthropic API key (stored only in your local SQLite; or set ANTHROPIC_API_KEY)", type="password",
                    value=db.get_setting("anthropic_api_key") or "")
if st.button("Save settings"):
    db.set_setting("default_seed", int(seed)); db.set_setting("claude_model", model.strip())
    db.set_setting("anthropic_api_key", key.strip() or None)
    st.success("Saved.")
st.caption(f"Tutor mode: {'Claude API' if tutor.available() else 'offline question banks'} · database: {db._db_path()}")

st.subheader("Back up and restore your progress")
st.caption("On Streamlit Community Cloud the disk is wiped whenever the app restarts, sleeps or is redeployed. "
           "Download a backup at the end of every study session, and restore it after a restart.")
dbp = db._db_path()
if dbp.exists():
    if st.download_button("⬇ Download progress backup", dbp.read_bytes(),
                          file_name=f"qfin_lab_backup_{db.today()}.sqlite", mime="application/octet-stream"):
        db.set_setting("last_backup", db.today())
st.caption(f"Last backup recorded: {db.get_setting('last_backup') or 'never'}")
up = st.file_uploader("Restore from a backup file (.sqlite)", type=["sqlite", "db"])
if up is not None and st.button("Restore now (replaces current progress)"):
    data = up.getvalue()
    if not data.startswith(b"SQLite format 3"):
        st.error("That is not a QFin Lab backup file.")
    else:
        dbp.parent.mkdir(parents=True, exist_ok=True)
        dbp.write_bytes(data)
        from core import bootstrap
        bootstrap.init()
        st.success("Progress restored."); st.rerun()

st.subheader("Run records")
runs = sorted((ROOT / "runs").glob("*.json"), reverse=True)[:30]
st.caption(f"{len(runs)} most recent JSON run records in runs/ (versions, seeds, outputs).")
for r in runs[:10]:
    st.download_button(r.name, r.read_text(), file_name=r.name, key=r.name)
