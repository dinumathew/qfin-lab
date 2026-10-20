MODULE = {
    "summary": (
        "Every replication target in this course is a resource count (CX, non-Clifford rotations, depth, T estimate). "
        "This module fixes the counting protocol: count after transpiling to a fixed basis, never before; separate "
        "Clifford from non-Clifford rotations; estimate T from rotation synthesis; and always report the seed, the "
        "optimisation level and the library version, because counts change with all three."
    ),
    "concepts": [
        {
            "title": "Count after transpiling to a fixed basis, never before",
            "why": "A high-level circuit hides its cost inside composite gates (`StatePreparation`, `ccx`, `mcx`, library blocks). `count_ops()` on the untranspiled circuit reports 1 for a gate that is hundreds of CX {{c:q3_before_after}}.",
            "how": r"""
**Broken**: `qc.count_ops()` on the logical circuit. **Fix**:
```python
t = transpile(qc, basis_gates=["cx","rz","sx","x"], optimization_level=L, seed_transpiler=s)
t.count_ops(), t.depth(), t.depth(lambda i: i.operation.num_qubits == 2)   # 2-qubit depth
```
Use the same basis everywhere you compare. {cx, rz, sx, x} is the course standard (it matches the replication targets).
""",
            "code": """import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import StatePreparation
p = np.random.default_rng(1).dirichlet(np.ones(16))
qc = QuantumCircuit(4); qc.append(StatePreparation(np.sqrt(p)), range(4))
print("BROKEN (before):", dict(qc.count_ops()))
t = transpile(qc, basis_gates=["cx","rz","sx","x"], optimization_level=1, seed_transpiler=7)
print("FIX (after):", dict(t.count_ops()), "| depth", t.depth(), "| 2q depth", t.depth(lambda i: i.operation.num_qubits == 2))
""",
            "impact": "A vendor quoting pre-transpilation gate counts understates cost by orders of magnitude. Insist on post-transpilation counts in a named basis.",
        },
        {
            "title": "Separate Clifford from non-Clifford rotations; estimate T",
            "why": "On fault-tolerant hardware cost is driven by non-Clifford operations, not by gate totals (B2). Counting all `rz` together mixes free and expensive operations.",
            "how": r"""
Classify each `rz(θ)` by $k=\theta/(\pi/4)$: integer even → Clifford; integer odd → T-type (1 T); non-integer → arbitrary (synthesised
with $\approx 3\log_2(1/\varepsilon)$ T). Report: CX, Clifford rz, T-type rz, arbitrary rz, T estimate at stated $\varepsilon$.
""",
            "code": """import numpy as np, math
from qiskit import QuantumCircuit, transpile
qc = QuantumCircuit(2); qc.ry(0.4, 0); qc.cx(0, 1); qc.t(1); qc.s(0)
t = transpile(qc, basis_gates=["cx","rz","sx","x"], optimization_level=1, seed_transpiler=1)
def kind(a):
    k = float(a)/(math.pi/4)
    return "arbitrary" if abs(k-round(k)) > 1e-9 else ("clifford" if round(k) % 2 == 0 else "t_type")
ks = [kind(i.operation.params[0]) for i in t.data if i.operation.name == "rz"]
c = {k: ks.count(k) for k in ("clifford", "t_type", "arbitrary")}
print(c, "| T estimate at eps=1e-10:", c["t_type"] + c["arbitrary"]*math.ceil(3*math.log2(1e10)))
""",
            "impact": "This is what turns a circuit into a fault-tolerant cost line. It is the input to every client resource estimate (A2).",
        },
        {
            "title": "Report seed_transpiler, optimisation level and version: counts move with all three",
            "why": "Counts are not constants. Different seeds and levels give different counts; library upgrades change passes. A replication target without these is not reproducible {{c:q3_level}}.",
            "how": r"""
Protocol: for each circuit, transpile at levels {1, 3} over seeds 0..19; report median and min–max; save the median-seed transpiled circuit as QPY;
record Qiskit version. Replication tolerances in I5–I7 are stated as ranges for this reason.
""",
            "code": """import numpy as np
from qiskit import transpile
from qiskit.circuit.random import random_circuit
qc = random_circuit(5, 10, max_operands=3, seed=4)
for L in (1, 3):
    cx = [transpile(qc, basis_gates=["cx","rz","sx","x"], optimization_level=L, seed_transpiler=s).count_ops().get("cx", 0) for s in range(10)]
    print(f"level {L}: CX median {int(np.median(cx))}, range {min(cx)}-{max(cx)}")
""",
            "impact": "When your numbers differ from a paper's, this protocol tells you whether the gap is real or a seed/level/version artefact, before a client or validator asks.",
        },
    ],
    "lens": {
        "look": "A count table per circuit: basis, level, seeds (median, range), version, CX, 2q depth, Clifford/T-type/arbitrary rz, T estimate at stated ε; QPY saved.",
        "decision": "Which circuit design is cheaper, whether a replication target is met, and what goes into a resource estimate.",
        "justified": "Counts drive cost and feasibility estimates; without protocol they are not comparable or reproducible.",
        "mistakes": [
            "Counting before transpiling.",
            "Different bases for different circuits being compared.",
            "Single seed; no level stated.",
            "Lumping all rz together.",
            "Not saving transpiled circuits (QPY) for audit.",
        ],
        "impact": "Resource estimates off by orders of magnitude; irreproducible replication claims; validation findings.",
        "test": "Lab Q3: count a 4-qubit StatePreparation and a Toffoli-heavy block under the protocol, before vs after, across seeds and levels; save QPY.",
    },
    "claims": [
        {"id": "q3_before_after", "tag": "M", "text": "A 4-qubit StatePreparation shows 1 gate before transpiling and more than 10 CX after transpiling to {cx, rz, sx, x}.",
         "check": """import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import StatePreparation
p=np.random.default_rng(1).dirichlet(np.ones(16)); qc=QuantumCircuit(4); qc.append(StatePreparation(np.sqrt(p)),range(4))
assert sum(qc.count_ops().values())==1
assert transpile(qc,basis_gates=['cx','rz','sx','x'],optimization_level=1,seed_transpiler=7).count_ops()['cx']>10"""},
        {"id": "q3_level", "tag": "M", "text": "For a random 5-qubit depth-10 circuit (seed 4), optimisation level 3 gives a median CX count no higher than level 1 over 10 seeds.",
         "check": """import numpy as np
from qiskit import transpile
from qiskit.circuit.random import random_circuit
qc=random_circuit(5,10,max_operands=3,seed=4); b=['cx','rz','sx','x']
m=lambda L: np.median([transpile(qc,basis_gates=b,optimization_level=L,seed_transpiler=s).count_ops().get('cx',0) for s in range(10)])
assert m(3)<=m(1)"""},
    ],
    "lab": {
        "id": "q3_lab",
        "title": "Resource counting protocol",
        "hypothesis": (
            "H1: pre-transpilation counts understate CX by >10× for a 5-qubit StatePreparation. "
            "H2: across 20 seeds, level-3 CX counts have a range of at least 0 (report it) and a median ≤ level 1. "
            "H3: the median-seed transpiled circuit round-trips through QPY with identical counts."
        ),
        "thresholds": "H1 ratio > 10; H2 median(L3) ≤ median(L1); H3 exact.",
        "data": "Synthetic: Dirichlet-random 32-point distribution (seeded) and a 4-Toffoli block.",
        "code": r'''import io, math, numpy as np, pandas as pd
import plotly.graph_objects as go
from qiskit import QuantumCircuit, transpile, qpy
from qiskit.circuit.library import StatePreparation
from importlib import metadata
from qlab_helpers import SEED, show, record, table

B = ["cx", "rz", "sx", "x"]
p = np.random.default_rng(SEED).dirichlet(np.ones(32))
sp = QuantumCircuit(5); sp.append(StatePreparation(np.sqrt(p)), range(5))
tof = QuantumCircuit(5)
for a, b, c in [(0, 1, 2), (1, 2, 3), (2, 3, 4), (0, 3, 4)]: tof.ccx(a, b, c)
def classify(t):
    ks = []
    for i in t.data:
        if i.operation.name == "rz":
            k = float(i.operation.params[0])/(math.pi/4)
            ks.append("arbitrary" if abs(k-round(k)) > 1e-9 else ("clifford" if round(k) % 2 == 0 else "t_type"))
    return {k: ks.count(k) for k in ("clifford", "t_type", "arbitrary")}
rows, dist = [], {}
for name, qc in [("StatePreparation 5q", sp), ("4 Toffolis", tof)]:
    for L in (1, 3):
        cxs = []
        for s in range(20):
            t = transpile(qc, basis_gates=B, optimization_level=L, seed_transpiler=s)
            cxs.append(t.count_ops().get("cx", 0))
        dist[(name, L)] = cxs
        med_seed = int(np.argsort(cxs)[len(cxs)//2])
        t = transpile(qc, basis_gates=B, optimization_level=L, seed_transpiler=med_seed)
        cl = classify(t)
        rows.append({"circuit": name, "level": L, "CX before": qc.count_ops().get("cx", 0), "CX median": int(np.median(cxs)), "CX min": min(cxs), "CX max": max(cxs),
                     "2q depth": t.depth(lambda i: i.operation.num_qubits == 2), **cl, "T est (eps=1e-10)": cl["t_type"] + cl["arbitrary"]*math.ceil(3*math.log2(1e10)),
                     "median seed": med_seed})
df = pd.DataFrame(rows); table(df, f"Counts in basis {B}, 20 seeds, qiskit {metadata.version('qiskit')}")
fig = go.Figure([go.Box(y=v, name=f"{k[0]} L{k[1]}") for k, v in dist.items()]); fig.update_layout(title="CX count across transpiler seeds", yaxis_title="CX"); show(fig)
t = transpile(sp, basis_gates=B, optimization_level=3, seed_transpiler=int(df.iloc[1]["median seed"]))
buf = io.BytesIO(); qpy.dump(t, buf); buf.seek(0); t2 = qpy.load(buf)[0]
record("qpy_roundtrip_equal", dict(t.count_ops()) == dict(t2.count_ops()))
r = df[df.circuit == "StatePreparation 5q"]
record("before_after_ratio", float(r["CX median"].iloc[0] / max(1, sum(sp.count_ops().values()))))
record("median_L3_le_L1", bool(r[r.level == 3]["CX median"].item() <= r[r.level == 1]["CX median"].item()))
''',
        "expect": {"before_after_ratio": "x > 10", "median_L3_le_L1": "x is True", "qpy_roundtrip_equal": "x is True"},
        "report_hints": "Your count table is the deliverable. State the tolerance you would quote for each count if someone else replicated it.",
    },
    "quiz": [
        {"id": "q3q1", "type": "mc", "q": "When should CX be counted?", "options": ["Before transpiling", "After transpiling to a fixed basis", "Either", "Only on hardware"], "answer": 1, "explain": "Composite gates hide cost.", "tags": ["protocol"]},
        {"id": "q3q2", "type": "mc", "q": "rz(3π/4) is:", "options": ["Clifford", "T-type", "Arbitrary", "Measurement"], "answer": 1, "explain": "Odd multiple of π/4.", "tags": ["classification"]},
        {"id": "q3q3", "type": "mc", "q": "rz(π) is:", "options": ["Clifford", "T-type", "Arbitrary", "Identity always"], "answer": 0, "explain": "Z up to phase.", "tags": ["classification"]},
        {"id": "q3q4", "type": "mc", "q": "Counts must be reported with:", "options": ["Seed, level, basis, version", "Only the total", "Only qubits", "Colour of plot"], "answer": 0, "explain": "All four move counts.", "tags": ["protocol"]},
        {"id": "q3q5", "type": "mc", "q": "2-qubit depth in Qiskit:", "options": ["t.depth()", "t.depth(lambda i: i.operation.num_qubits == 2)", "t.size()", "t.width()"], "answer": 1, "explain": "Filter function.", "tags": ["protocol"]},
        {"id": "q3q6", "type": "mc", "q": "To audit counts later, save:", "options": ["A screenshot", "QPY of the transpiled circuit", "The PNG drawing", "Nothing"], "answer": 1, "explain": "QPY.", "tags": ["audit"]},
        {"id": "q3q7", "type": "mc", "q": "An arbitrary rotation at ε=1e-10 costs about:", "options": ["1 T", "7 T", "100 T", "1e10 T"], "answer": 2, "explain": "3·log2(1e10)≈100.", "tags": ["t"]},
        {"id": "q3q8", "type": "mc", "q": "Why report median and range across seeds?", "options": ["Tradition", "Counts vary with stochastic transpilation", "Medians are smaller", "Required by IBM"], "answer": 1, "explain": "Stochastic passes.", "tags": ["protocol"]},
        {"id": "q3q9", "type": "mc", "q": "Comparing two circuits counted in different bases is:", "options": ["Fine", "Not comparable", "Better", "Required"], "answer": 1, "explain": "Same basis.", "tags": ["protocol"]},
        {"id": "q3q10", "type": "mc", "q": "count_ops() on an untranspiled StatePreparation returns:", "options": ["Hundreds of CX", "One 'state_preparation' entry", "Zero", "Error"], "answer": 1, "explain": "Composite gate.", "tags": ["protocol"]},
        {"id": "q3q11", "type": "short", "q": "Your CX count is 15% below the paper's target. List what you check before calling it a discrepancy.",
         "must": [["seed"], ["level", "optimi"], ["version"], ["basis"]],
         "explain": "Seed range, optimisation level, Qiskit version, basis gates (and circuit construction).", "tags": ["protocol"]},
        {"id": "q3q12", "type": "short", "q": "Write the column headers of your standard count table.",
         "must": [["cx"], ["depth"], ["clifford"], ["t"], ["seed"], ["level"]],
         "explain": "Basis, level, seeds (median/range), version, CX, 2q depth, Clifford/T-type/arbitrary rz, T estimate.", "tags": ["protocol"]},
    ],
    "exercise": {
        "id": "q3_ex",
        "title": "A count-table builder",
        "prompt": (
            "Implement `count_table(qc, seeds, level, eps=1e-10)` that transpiles to ['cx','rz','sx','x'] for each seed and returns a dict:\n"
            "{'cx_median', 'cx_min', 'cx_max', 'twoq_depth_median', 'clifford', 't_type', 'arbitrary', 't_estimate', 'level', 'seeds', 'qiskit'}\n"
            "where clifford/t_type/arbitrary/t_estimate come from the median-CX seed's circuit (lowest seed among ties), and qiskit is the installed version."
        ),
        "starter": '''import math, numpy as np
from qiskit import transpile

def count_table(qc, seeds, level, eps=1e-10):
    raise NotImplementedError
''',
        "solution": '''import math, numpy as np
from importlib import metadata
from qiskit import transpile

B = ["cx", "rz", "sx", "x"]

def _kind(a):
    k = float(a)/(math.pi/4)
    if abs(k - round(k)) > 1e-9:
        return "arbitrary"
    return "clifford" if round(k) % 2 == 0 else "t_type"

def count_table(qc, seeds, level, eps=1e-10):
    seeds = list(seeds)
    ts = [transpile(qc, basis_gates=B, optimization_level=level, seed_transpiler=s) for s in seeds]
    cx = np.array([t.count_ops().get("cx", 0) for t in ts])
    d2 = [t.depth(lambda i: i.operation.num_qubits == 2) for t in ts]
    med = float(np.median(cx))
    idx = int(np.argmin(np.abs(cx - med)))
    kinds = [_kind(i.operation.params[0]) for i in ts[idx].data if i.operation.name == "rz"]
    c = {k: kinds.count(k) for k in ("clifford", "t_type", "arbitrary")}
    return {"cx_median": med, "cx_min": int(cx.min()), "cx_max": int(cx.max()),
            "twoq_depth_median": float(np.median(d2)), **c,
            "t_estimate": c["t_type"] + c["arbitrary"]*math.ceil(3*math.log2(1/eps)),
            "level": level, "seeds": seeds, "qiskit": metadata.version("qiskit")}
''',
        "tests": '''from qiskit import QuantumCircuit

def test_toffoli_table():
    qc = QuantumCircuit(3); qc.ccx(0, 1, 2)
    t = count_table(qc, range(3), 1)
    assert t["cx_median"] == 6 and t["t_type"] == 7 and t["arbitrary"] == 0 and t["t_estimate"] == 7

def test_rotation_counts():
    qc = QuantumCircuit(1); qc.ry(0.3, 0)
    t = count_table(qc, [0], 1, eps=1e-10)
    assert t["arbitrary"] >= 1 and t["t_estimate"] >= 100

def test_metadata():
    qc = QuantumCircuit(2); qc.cx(0, 1)
    t = count_table(qc, [0, 1], 3)
    assert t["level"] == 3 and t["seeds"] == [0, 1] and isinstance(t["qiskit"], str)
''',
    },
    "cards": [
        {"front": "Count resources", "back": "After transpile to fixed basis {cx, rz, sx, x}, stated level and seed", "kind": "definition"},
        {"front": "2q depth", "back": "t.depth(lambda i: i.operation.num_qubits == 2)", "kind": "formula"},
        {"front": "rz classification", "back": "θ/(π/4) even → Clifford; odd → T-type; non-integer → arbitrary", "kind": "formula"},
        {"front": "T per arbitrary rotation", "back": "≈ 3·log₂(1/ε)", "kind": "formula"},
        {"front": "Report with every count", "back": "basis, level, seeds (median/range), version", "kind": "definition"},
        {"front": "Audit trail for counts", "back": "Save transpiled circuit as QPY", "kind": "definition"},
        {"front": "Mistake: count_ops before transpile", "back": "Composite gates show as 1", "kind": "mistake"},
        {"front": "Mistake: one seed", "back": "Counts vary; report median and range", "kind": "mistake"},
        {"front": "Mistake: mixing bases", "back": "Counts in different bases are not comparable", "kind": "mistake"},
        {"front": "Mistake: lumping rz", "back": "Separate Clifford, T-type and arbitrary", "kind": "mistake"},
    ],
    "defend": {
        "persona": "validator",
        "questions": [
            {"q": "Show me how you counted CX.",
             "must": [["transpil"], ["basis"], ["seed"], ["level"]], "model": "Transpiled to {cx,rz,sx,x}, level stated, 20 seeds, median and range, QPY saved."},
            {"q": "Why is your T estimate so much larger than your T-type gate count?",
             "must": [["arbitrary", "rotation"], ["synthes", "log"]], "model": "Arbitrary rotations dominate: each is synthesised with ~3log₂(1/ε) T."},
            {"q": "Will your counts match mine?",
             "must": [["version", "seed", "level"], ["range", "tolerance"]], "model": "Within the stated range if you use the same version, basis and level; I give tolerances, not point values."},
            {"q": "Could you have used a different basis?",
             "must": [["yes"], ["same", "consistent", "compare"]], "model": "Yes, but every compared circuit must use the same basis; ours matches the replication targets."},
            {"q": "Where can I inspect the circuit you counted?",
             "must": [["qpy"]], "model": "The QPY file for the median-seed transpiled circuit, referenced in the run record."},
        ],
    },
    "glossary": {
        "Basis gates": "Target gate set for transpilation.",
        "2-qubit depth": "Number of sequential layers of 2-qubit gates.",
        "T estimate": "T-type gates plus synthesised arbitrary rotations at precision ε.",
        "QPY": "Qiskit circuit serialisation format.",
    },
}
