MODULE = {
    "summary": (
        "Most quantum-finance tutorials online were written for Qiskit 0.x and no longer run. This module catalogues the "
        "breaking changes you will hit, each with a broken example, the fix and a unit test, and teaches the habit that "
        "matters more than any list: read deprecation warnings and migration guides, and verify every claim here against "
        "the current release notes."
    ),
    "concepts": [
        {
            "title": "Qiskit 1.0: execute() removed; Aer is qiskit_aer; V2 primitives",
            "why": "Copy-pasting `from qiskit import execute, Aer` is how most learners first fail. The imports no longer exist {{c:q1_execute}}.",
            "how": r"""
**Broken** (pre-1.0 tutorials):
```python
from qiskit import Aer, execute
counts = execute(qc, Aer.get_backend("qasm_simulator"), shots=1000).result().get_counts()
```
**Fix** (Qiskit ≥1.0 / 2.x):
```python
from qiskit_aer.primitives import SamplerV2
counts = SamplerV2(seed=1).run([qc], shots=1000).result()[0].data.meas.get_counts()
# or: from qiskit_aer import AerSimulator; AerSimulator().run(transpile(qc, sim), shots=1000)
```
V1 primitives (`qiskit.primitives.Sampler`, `Estimator`) are gone in 2.x; reference V2 implementations are `StatevectorSampler` and `StatevectorEstimator`.
""",
            "code": """try:
    from qiskit import execute               # broken on Qiskit >= 1.0
    print("execute still importable (old Qiskit)")
except ImportError as e:
    print("BROKEN as expected:", e)
from qiskit import QuantumCircuit
from qiskit_aer.primitives import SamplerV2
qc = QuantumCircuit(1); qc.h(0); qc.measure_all()
print("FIX:", SamplerV2(seed=1).run([qc], shots=100).result()[0].data.meas.get_counts())
""",
            "impact": "When a client's team says 'our quantum PoC from 2022 no longer runs', this is usually why. Budget migration time for any inherited code.",
        },
        {
            "title": "Qiskit 2.x: Pulse removed; GroverOperator class → grover_operator(); library classes → functions",
            "why": (
                "Qiskit 2.x removed Pulse and older backend interfaces and is steadily replacing circuit-library classes with "
                "functions. Old code may still run with deprecation warnings today and break at 3.0 {{c:q1_grover}}."
            ),
            "how": r"""
**Deprecated**: `from qiskit.circuit.library import GroverOperator; G = GroverOperator(oracle)` (warns: deprecated as of 2.1, removed in 3.0).
**Fix**: `from qiskit.circuit.library import grover_operator; G = grover_operator(oracle)`.

Read every `DeprecationWarning`: it names the version deprecated, the version of removal and the replacement. Run tests with
`python -W error::DeprecationWarning` to turn them into failures in CI.
""",
            "code": """import warnings
from qiskit import QuantumCircuit
from qiskit.circuit.library import grover_operator
oracle = QuantumCircuit(2); oracle.cz(0, 1)
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    from qiskit.circuit.library import GroverOperator
    G_old = GroverOperator(oracle)
    msgs = [str(x.message) for x in w if "GroverOperator" in str(x.message)]
print("DEPRECATED:", msgs[0][:120] if msgs else "no warning (check version)")
G = grover_operator(oracle)
print("FIX: grover_operator() ->", G.num_qubits, "qubits")
""",
            "impact": "Deprecation warnings are free advance notice of future breakage; a pilot that ignores them carries avoidable maintenance cost.",
        },
        {
            "title": "Application packages moved to community maintenance",
            "why": (
                "`qiskit-finance`, `qiskit-optimization` and `qiskit-algorithms` were moved out of core Qiskit to community "
                "maintenance. Their release cadence and compatibility with the newest Qiskit are not guaranteed {{c:q1_finance}}. "
                "That is why this course builds amplitude estimation and pricing oracles from primitives."
            ),
            "how": r"""
Check before depending on an application package: latest release date, declared dependency range (`Requires-Dist`),
open issues for the current Qiskit major version, and whether CI tests against it. If in doubt, implement the algorithm
yourself on the primitives (I3 does this for MLQAE) and keep the package as a cross-check only.
""",
            "code": """from importlib import metadata
for p in ["qiskit", "qiskit-aer", "qiskit-finance", "qiskit-algorithms"]:
    try:
        print(f"{p:18s} installed {metadata.version(p)}")
    except metadata.PackageNotFoundError:
        print(f"{p:18s} not installed (by design: the labs do not depend on it)")
""",
            "impact": "Dependency risk is vendor risk. A client pilot built on an unmaintained package is a model-risk finding waiting to happen.",
        },
    ],
    "lens": {
        "look": "For any inherited or online code: Qiskit version it was written for, imports used, warnings emitted under current pins, application-package dependencies and their release dates.",
        "decision": "Port, rewrite on primitives, or discard old code; whether an application package is acceptable as a dependency.",
        "justified": "Breaking changes are documented and frequent; silent drift in behaviour is worse than a crash.",
        "mistakes": [
            "Pinning an old Qiskit to make a tutorial run, then mixing it with new packages.",
            "Silencing deprecation warnings.",
            "Assuming qiskit-finance results are current-version tested.",
            "Translating code line by line instead of re-deriving it on V2 primitives.",
            "Not re-running counts after an upgrade (transpiler changes alter resource counts).",
        ],
        "impact": "Non-reproducible pilots, hidden behaviour changes, and maintenance cost when the next major version lands.",
        "test": "Lab Q1: run a battery of old-API snippets, classify each as removed / deprecated / OK on your pinned versions, and record the replacement.",
    },
    "claims": [
        {"id": "q1_execute", "tag": "M", "text": "On the pinned Qiskit 2.6, `from qiskit import execute` and `from qiskit import Aer` raise ImportError.",
         "check": """ok=0
for s in ['from qiskit import execute','from qiskit import Aer']:
    try: exec(s)
    except ImportError: ok+=1
assert ok==2"""},
        {"id": "q1_grover", "tag": "M", "text": "On Qiskit 2.6, GroverOperator emits a DeprecationWarning (deprecated in 2.1, removal in 3.0); grover_operator() is the replacement.",
         "check": """import warnings
from qiskit import QuantumCircuit
from qiskit.circuit.library import GroverOperator, grover_operator
o=QuantumCircuit(2); o.cz(0,1)
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter('always'); GroverOperator(o)
assert any('GroverOperator' in str(x.message) and '3.0' in str(x.message) for x in w)
assert grover_operator(o).num_qubits==2"""},
        {"id": "q1_finance", "tag": "S", "text": "qiskit-finance is community-driven under qiskit-community; latest release 0.4.1 (29 Feb 2024) added Python 3.12 support.",
         "source": {"title": "Releases · qiskit-community/qiskit-finance", "publisher": "GitHub (qiskit-community)", "date": "2024-02-29", "url": "https://github.com/qiskit-community/qiskit-finance/releases"},
         "time_sensitive": True, "last_verified": "2026-10-19"},
        {"id": "q1_release_notes", "tag": "S", "text": "Qiskit SDK release notes and migration guides list removals per version.",
         "source": {"title": "Qiskit SDK release notes", "publisher": "IBM Quantum documentation", "date": "2026 (rolling)", "url": "https://quantum.cloud.ibm.com/docs/en/api/qiskit/release-notes"},
         "time_sensitive": True, "last_verified": "2026-10-19"},
    ],
    "lab": {
        "id": "q1_lab",
        "title": "Old-API audit on your pinned versions",
        "hypothesis": "H1: of 8 legacy snippets, at least 5 fail or warn on the pinned Qiskit 2.6 environment. H2: every snippet has a working replacement that runs without DeprecationWarning.",
        "thresholds": "H1 ≥ 5 of 8 broken/deprecated; H2 8 of 8 replacements clean.",
        "data": "Code snippets only.",
        "code": r'''import warnings, pandas as pd
from qlab_helpers import record, table
setup = "from qiskit import QuantumCircuit\nqc = QuantumCircuit(2); qc.h(0); qc.cx(0,1); qc.measure_all()\no = QuantumCircuit(2); o.cz(0,1)\n"
cases = [
    ("execute()", "from qiskit import execute", "from qiskit_aer.primitives import SamplerV2"),
    ("qiskit.Aer", "from qiskit import Aer", "from qiskit_aer import AerSimulator"),
    ("V1 Sampler", "from qiskit.primitives import Sampler", "from qiskit.primitives import StatevectorSampler"),
    ("V1 Estimator", "from qiskit.primitives import Estimator", "from qiskit.primitives import StatevectorEstimator"),
    ("Pulse", "from qiskit import pulse", "pass  # Pulse removed; use Qiskit Dynamics or fractional gates where needed"),
    ("GroverOperator class", "from qiskit.circuit.library import GroverOperator\nGroverOperator(o)", "from qiskit.circuit.library import grover_operator\ngrover_operator(o)"),
    ("QuantumCircuit (still fine)", "QuantumCircuit(3)", "QuantumCircuit(3)"),
    ("transpile (still fine)", "from qiskit import transpile\ntranspile(qc, basis_gates=['cx','rz','sx','x'])", "from qiskit import transpile\ntranspile(qc, basis_gates=['cx','rz','sx','x'], seed_transpiler=1)"),
]
def run(snippet):
    ns = {}
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        try:
            exec(setup + snippet, ns)
        except Exception as e:
            return "BROKEN", f"{type(e).__name__}: {e}"[:100]
        dep = [str(x.message) for x in w if issubclass(x.category, DeprecationWarning) and "qiskit" in str(x.message).lower()]
        return ("DEPRECATED", dep[0][:100]) if dep else ("OK", "")
rows = []
for name, old, new in cases:
    so, mo = run(old); sn, mn = run(new)
    rows.append({"case": name, "legacy": so, "legacy detail": mo, "replacement": sn})
df = pd.DataFrame(rows); table(df, "Legacy API audit")
record("n_broken_or_deprecated", int((df.legacy != "OK").sum()))
record("n_clean_replacements", int((df.replacement == "OK").sum()))
print(df[["case", "legacy", "replacement"]].to_string(index=False))
''',
        "expect": {"n_broken_or_deprecated": "x >= 5", "n_clean_replacements": "x == 8"},
        "report_hints": "List each replacement and the release-notes entry that documents it (with the date you checked).",
    },
    "quiz": [
        {"id": "q1q1", "type": "mc", "q": "In Qiskit ≥1.0, `from qiskit import execute`:", "options": ["Works", "Raises ImportError", "Warns only", "Runs on hardware"], "answer": 1, "explain": "Removed in 1.0.", "tags": ["churn"]},
        {"id": "q1q2", "type": "mc", "q": "Where does Aer live now?", "options": ["qiskit.Aer", "qiskit_aer", "qiskit.providers.aer only", "qiskit_ibm_runtime"], "answer": 1, "explain": "Separate package qiskit-aer.", "tags": ["churn"]},
        {"id": "q1q3", "type": "mc", "q": "Replacement for GroverOperator(oracle):", "options": ["Grover(oracle)", "grover_operator(oracle)", "AmplificationProblem", "None"], "answer": 1, "explain": "Function form.", "tags": ["churn"]},
        {"id": "q1q4", "type": "mc", "q": "Qiskit Pulse in 2.x is:", "options": ["Unchanged", "Removed", "Renamed Pulse2", "Default"], "answer": 1, "explain": "Removed in 2.0.", "tags": ["churn"]},
        {"id": "q1q5", "type": "mc", "q": "Reference V2 sampler in qiskit.primitives:", "options": ["Sampler", "StatevectorSampler", "BackendSampler", "AerSampler"], "answer": 1, "explain": "StatevectorSampler.", "tags": ["churn"]},
        {"id": "q1q6", "type": "mc", "q": "To make deprecations fail CI:", "options": ["Ignore them", "python -W error::DeprecationWarning", "Pin old versions", "Delete warnings module"], "answer": 1, "explain": "Turn warnings into errors.", "tags": ["habit"]},
        {"id": "q1q7", "type": "mc", "q": "qiskit-finance is maintained by:", "options": ["IBM core team as part of Qiskit SDK", "The community (qiskit-community)", "Nobody", "NIST"], "answer": 1, "explain": "Community-driven.", "tags": ["packages"]},
        {"id": "q1q8", "type": "mc", "q": "A deprecation warning tells you:", "options": ["Nothing useful", "Version deprecated, planned removal and replacement", "That results are wrong", "To downgrade"], "answer": 1, "explain": "Read it.", "tags": ["habit"]},
        {"id": "q1q9", "type": "mc", "q": "After a Qiskit upgrade, resource counts:", "options": ["Never change", "May change; re-run and re-record", "Always fall", "Always rise"], "answer": 1, "explain": "Transpiler changes.", "tags": ["habit"]},
        {"id": "q1q10", "type": "mc", "q": "Best response to an old tutorial using execute():", "options": ["Pin Qiskit 0.46", "Re-derive the code on V2 primitives", "Use it anyway", "Patch Qiskit"], "answer": 1, "explain": "Port to current API.", "tags": ["habit"]},
        {"id": "q1q11", "type": "short", "q": "A client's 2022 PoC fails on import. Outline your triage.",
         "must": [["version", "release notes", "migration"], ["primitive", "v2", "sampler"], ["re-run", "rerun", "re-validate", "test"]],
         "explain": "Identify the Qiskit version it targeted, port to current APIs (V2 primitives, qiskit_aer) using migration guides, re-run tests and re-validate outputs and counts.", "tags": ["habit"]},
        {"id": "q1q12", "type": "short", "q": "What do you check before depending on qiskit-finance in a pilot?",
         "must": [["release", "date", "maintain"], ["compatib", "requires", "depend", "version"]],
         "explain": "Latest release date, maintenance status, declared dependency ranges and compatibility with current Qiskit.", "tags": ["packages"]},
    ],
    "exercise": {
        "id": "q1_ex",
        "title": "Port a legacy snippet",
        "prompt": (
            "The legacy code was:\n```\nfrom qiskit import Aer, execute\nfrom qiskit.circuit.library import GroverOperator\n"
            "G = GroverOperator(oracle)\ncounts = execute(qc, Aer.get_backend('qasm_simulator'), shots=shots, seed_simulator=seed).result().get_counts()\n```\n"
            "Implement on Qiskit 2.x:\n1. `make_grover(oracle)` using the non-deprecated function.\n"
            "2. `run_counts(qc, shots, seed)` returning counts via SamplerV2 (add measure_all to a copy if needed).\n"
            "3. `deprecations(fn, *args)` returning a list of DeprecationWarning messages raised when calling fn(*args)."
        ),
        "starter": '''from qiskit import QuantumCircuit

def make_grover(oracle):
    raise NotImplementedError

def run_counts(qc, shots, seed):
    raise NotImplementedError

def deprecations(fn, *args):
    raise NotImplementedError
''',
        "solution": '''import warnings
from qiskit import QuantumCircuit
from qiskit.circuit.library import grover_operator
from qiskit_aer.primitives import SamplerV2

def make_grover(oracle):
    return grover_operator(oracle)

def run_counts(qc, shots, seed):
    q = qc if qc.num_clbits else qc.copy()
    if not qc.num_clbits:
        q.measure_all()
    return SamplerV2(seed=seed).run([q], shots=shots).result()[0].data.meas.get_counts()

def deprecations(fn, *args):
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        fn(*args)
    return [str(x.message) for x in w if issubclass(x.category, DeprecationWarning)]
''',
        "tests": '''from qiskit import QuantumCircuit

def oracle():
    o = QuantumCircuit(2); o.cz(0, 1); return o

def test_grover_no_deprecation():
    assert deprecations(make_grover, oracle()) == []
    assert make_grover(oracle()).num_qubits == 2

def test_run_counts():
    qc = QuantumCircuit(2); qc.x(1)
    assert run_counts(qc, 50, 1) == {"10": 50}

def test_deprecations_detects_old_class():
    from qiskit.circuit.library import GroverOperator
    msgs = deprecations(GroverOperator, oracle())
    assert any("GroverOperator" in m for m in msgs)
''',
    },
    "cards": [
        {"front": "execute()", "back": "Removed in Qiskit 1.0; use SamplerV2 / backend.run", "kind": "mistake"},
        {"front": "from qiskit import Aer", "back": "Gone; use from qiskit_aer import AerSimulator", "kind": "mistake"},
        {"front": "V1 Sampler/Estimator", "back": "Removed in 2.x; use V2 (StatevectorSampler/Estimator, Aer SamplerV2/EstimatorV2)", "kind": "mistake"},
        {"front": "Pulse", "back": "Removed in Qiskit 2.0", "kind": "definition"},
        {"front": "GroverOperator", "back": "Deprecated in 2.1, removal in 3.0; use grover_operator()", "kind": "mistake"},
        {"front": "qiskit-finance status", "back": "Community-maintained; last release 0.4.1 (Feb 2024); verify before use", "kind": "number"},
        {"front": "Fail CI on deprecations", "back": "python -W error::DeprecationWarning", "kind": "definition"},
        {"front": "After upgrading Qiskit", "back": "Re-run tests and re-record resource counts", "kind": "definition"},
        {"front": "Where to check removals", "back": "Qiskit release notes and migration guides", "kind": "definition"},
        {"front": "Mistake: pinning ancient Qiskit to run a tutorial", "back": "Port to current API instead", "kind": "mistake"},
    ],
    "defend": {
        "persona": "validator",
        "questions": [
            {"q": "Which Qiskit version is this built on, and how do you know nothing deprecated is used?",
             "must": [["2.6", "pinned", "version"], ["warning", "deprecat", "-w error"]],
             "model": "Pinned 2.6.x; tests run with DeprecationWarning as error, so deprecated APIs fail CI."},
            {"q": "Why didn't you use qiskit-finance?",
             "must": [["community", "maintain", "release"], ["primitive", "own", "implement"]],
             "model": "It's community-maintained with an old last release; I implemented the algorithm on V2 primitives and use the package only as a cross-check."},
            {"q": "What happens when Qiskit 3.0 lands?",
             "must": [["deprecat", "removal", "warning"], ["test", "re-run", "re-record", "counts"]],
             "model": "Deprecations flagged now are removed; our tests fail early, we port, and re-run/re-record counts."},
            {"q": "Your counts differ from last quarter's report. Explain.",
             "must": [["version", "upgrade", "transpiler"], ["seed", "record", "lock"]],
             "model": "A version upgrade changed transpiler passes; run records show versions and seeds, so I can reproduce both."},
            {"q": "How do you port a legacy notebook safely?",
             "must": [["migration", "release notes"], ["test", "compare", "reference"]],
             "model": "Follow migration guides, rewrite on V2 primitives, and compare outputs to exact references and the old recorded results."},
        ],
    },
    "glossary": {
        "Deprecation": "Announced future removal of an API, with a replacement.",
        "V2 primitives": "Current Sampler/Estimator interfaces in Qiskit and Aer.",
        "qiskit-aer": "Separate simulator package (import qiskit_aer).",
        "Community-maintained": "Maintained outside the core SDK team; compatibility not guaranteed.",
    },
}
