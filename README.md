# QFin Lab

A local learning app for quantum computing in financial services: quantum computation for finance, post-quantum
cryptography, and regulation. Built in Streamlit; every lab runs real Qiskit 2.6 / Aer 0.17 code in a separate
Python process on your machine.

## What is in this build (first pass)

| Area | Status |
|---|---|
| App shell: 13 pages, SQLite progress, mastery gates, placement test, SM-2 review, JSON run records, self-test | Done |
| Level 0 (P1–P6) and Level 1 (B1–B7) | Fully authored: three-step concepts, practitioner lens, runnable lab, quiz (12 each), graded coding exercise, 10–12 cards, 5-question "Defend it" round |
| Track Q items 1–4 (version churn, bit ordering, counting resources, simulator limits) | Fully authored |
| Regulatory tracker | 27 items verified on 2026-10-19 (primary or flagged secondary) |
| Levels 2–3, Track Q5–Q9, capstone guided builds | On the curriculum map as "planned"; next passes |

## Install

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt      # or requirements.lock.txt for the exact tested versions
streamlit run app.py
```

**PQC (liboqs-python).** On first `import oqs`, liboqs-python downloads and builds the liboqs C library (needs `git`,
`cmake` and a C compiler; takes 5–10 minutes once). Level 0–1 labs do not need it; I11 will. On Windows, building
liboqs is easier under WSL.

**Claude tutor (optional).** Set `ANTHROPIC_API_KEY`, or paste a key on *Lab environment & settings*. Without a key the
tutor and "Defend it" rounds run offline from built-in question banks with strict concept-group grading.

## How the course works

* **Gate per module:** ≥80% quiz, ≥80% unit tests on the coding exercise, and a passing lab report (≥70% on the
  nine-heading rubric, with non-zero hypothesis and decision). Or test out on the *Placement test* page (≥80%).
* **Every lab** follows the nine-step empirical framework; hypotheses and thresholds are pre-registered in the lab.
* **Every claim** is tagged Measured (re-checked by code), Sourced (title, publisher, date, link, last-verified) or
  Judgement. Time-sensitive sources are flagged after six months on the *Evidence ledger*.
* **Reproducibility:** seed shown on every run; `seed_transpiler` fixed; each lab run exported to `runs/*.json`
  with versions, seeds and outputs.

## Deploy to the cloud

See `DEPLOY.md`: Streamlit Community Cloud (free), private web URL with username and password.

## Self-test

```bash
pytest -q tests/                 # full (~4 min)
QLAB_FAST=1 pytest -q tests/     # skips the two heavy labs
```
It executes every concept example, every lab (checking pre-registered thresholds), every Measured-claim check, every
exercise solution against its tests, confirms starter code fails, validates the tracker schema, and renders every page.

## Layout

```
app.py                 navigation
app_pages/             one file per page
core/                  db, curriculum & gates, runner (subprocess execution + grading), grading rubrics, SM-2, tutor, claims
content/modules/       one file per module (schema in content/SCHEMA.md)
data/regulatory.json   tracker, with verification status per item
tests/                 self-test and page smoke tests
```

## Known limits

* Hardware, roadmap and regulatory facts change quickly: the tracker and Sourced claims were verified on 2026-10-19.
  Re-verify before client use; items marked *secondary* were not confirmed from the primary document.
* Lab timing thresholds (P5, Q4) are machine-dependent; a failed timing hypothesis on your machine is a finding, not a bug.
* Offline short-answer grading checks for required concepts; it cannot judge reasoning quality. Use the Claude tutor for that.
