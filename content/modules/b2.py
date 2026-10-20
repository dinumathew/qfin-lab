MODULE = {
    "summary": (
        "Circuits are sequences of gates; costs are counted in gates. This module covers the standard gate set, how "
        "multi-qubit gates decompose, what 'universal' means, and why the Clifford+T gate set makes non-Clifford "
        "rotations (T gates) the scarce, expensive resource on a fault-tolerant machine. By the end you can count "
        "the T-type cost of a circuit, which is the currency of every resource estimate in A2."
    ),
    "concepts": [
        {
            "title": "Single-qubit gates: H, X, Y, Z, S, T and rotations",
            "why": (
                "Every algorithm is built from a small vocabulary. Knowing the algebra (HZH = X, T² = S, S² = Z) lets you read "
                "and simplify circuits, and spot when a transpiler has done something surprising."
            ),
            "how": r"""
* Paulis $X,Y,Z$; Hadamard $H=\tfrac{1}{\sqrt2}\begin{pmatrix}1&1\\1&-1\end{pmatrix}$ ($H|0\rangle=|+\rangle$, $HZH=X$).
* Phase gates: $S=\mathrm{diag}(1,i)=R_Z(\pi/2)$ up to global phase; $T=\mathrm{diag}(1,e^{i\pi/4})=R_Z(\pi/4)$ up to global phase. $T^2=S$, $S^2=Z$.
* Rotations $R_P(\theta)=e^{-i\theta P/2}$. IBM hardware's native single-qubit set is $\{R_Z(\theta),\sqrt X, X\}$: $R_Z$ is "virtual" (a frame change) on superconducting devices.
""",
            "code": """import numpy as np
from qiskit.quantum_info import Operator
from qiskit.circuit.library import HGate, ZGate, XGate, TGate, SGate
H, Z, X, T, S = (Operator(g()).data for g in (HGate, ZGate, XGate, TGate, SGate))
print("HZH == X:", np.allclose(H@Z@H, X))
print("T^2 == S:", np.allclose(T@T, S), "| S^2 == Z:", np.allclose(S@S, Z))
""",
            "impact": "Gate algebra is how you sanity-check a vendor's 'optimised' circuit: if their gate counts can't be reproduced from the algebra and a fixed transpile, the numbers are not evidence.",
        },
        {
            "title": "Multi-qubit gates: CNOT, CZ, Toffoli and their decompositions",
            "why": (
                "Two-qubit gates are the dominant error source on today's hardware and the main depth driver; the Toffoli "
                "(controlled-controlled-NOT) is the workhorse of arithmetic (payoffs, adders, comparators) and is expensive."
            ),
            "how": r"""
* CNOT: flips target if control is 1. CZ: phase $-1$ on $|11\rangle$; $\mathrm{CZ}=(I\otimes H)\,\mathrm{CNOT}\,(I\otimes H)$.
* Toffoli in Clifford+T: 6 CNOT + 7 T/T† + 2 H, standard decomposition. {{c:b2_toffoli}}
* Arithmetic on $n$-bit registers (adders, comparators) costs $O(n)$ Toffolis; payoffs like $\max(S-K,0)$ need comparators and multiplications, which is why oracle depth grows quickly (I5).
""",
            "code": """from qiskit import QuantumCircuit, transpile
qc = QuantumCircuit(3); qc.ccx(0, 1, 2)
t = transpile(qc, basis_gates=["cx", "h", "s", "sdg", "t", "tdg"], optimization_level=1, seed_transpiler=1)
print(t.count_ops())
print(t.draw(output="text", fold=120))
""",
            "impact": (
                "When a proposal says 'the payoff oracle uses an adder', ask how many Toffolis. Each one is 7 T-type gates in "
                "Clifford+T, and T gates set fault-tolerant runtime (A2)."
            ),
        },
        {
            "title": "Universality, the Clifford+T gate set, and why T gates are the expensive resource",
            "why": (
                "A fault-tolerant computer implements a finite gate set. Clifford gates (H, S, CNOT) are cheap to protect but "
                "classically simulable on their own (Gottesman–Knill {{c:b2_gk}}). Adding T makes the set universal. T gates "
                "cannot be applied transversally in the surface code and need **magic-state distillation**, so they dominate "
                "space and time cost."
            ),
            "how": r"""
* **Universal**: any unitary can be approximated to accuracy $\varepsilon$ by a finite gate sequence. {H, T, CNOT} is universal.
* **Clifford group**: maps Paulis to Paulis under conjugation. Circuits of Clifford gates + Pauli measurements are efficiently simulable classically (stabiliser formalism).
* **Cost model**: in fault-tolerant estimates, count T gates (T-count) and T-layers (T-depth). An arbitrary $R_Z(\theta)$ is not Clifford+T exactly; it is **synthesised** to accuracy $\varepsilon$ with about $3\log_2(1/\varepsilon)$ T gates (Ross–Selinger). {{c:b2_rs}}
* After transpiling to {cx, rz, sx, x}: an $R_Z$ angle that is a multiple of $\pi/2$ is Clifford; an odd multiple of $\pi/4$ is a T-type gate (1 T); anything else is an arbitrary rotation needing synthesis.
""",
            "code": """import numpy as np
from qiskit import QuantumCircuit, transpile
qc = QuantumCircuit(3); qc.ccx(0, 1, 2); qc.ry(0.3, 0)
t = transpile(qc, basis_gates=["cx", "rz", "sx", "x"], optimization_level=1, seed_transpiler=1)
def kind(a):
    k = float(a)/(np.pi/4)
    if abs(k - round(k)) > 1e-9: return "arbitrary"
    return "clifford" if round(k) % 2 == 0 else "T-type"
kinds = [kind(i.operation.params[0]) for i in t.data if i.operation.name == "rz"]
print({k: kinds.count(k) for k in set(kinds)})
eps = 1e-10
print("T per arbitrary rotation at eps=1e-10 ~", round(3*np.log2(1/eps)))
""",
            "impact": (
                "The client-ready translation: 'the cost of a fault-tolerant algorithm is mostly its T gates, and every continuous "
                "rotation (e.g. encoding a PD as an angle) is worth ~100 T gates at useful precision.' This is why loading data as "
                "rotations is expensive, and why resource estimates in the literature are quoted in T-count and T-depth."
            ),
        },
    ],
    "lens": {
        "look": "Transpile to a fixed basis with fixed seed and optimisation level; separate Clifford from non-Clifford operations; count T-type gates and arbitrary rotations; estimate total T with the synthesis formula.",
        "decision": "Which circuit design (and which oracle construction) is cheapest in the resource that matters: T gates for fault tolerance, two-qubit gates for today's noisy hardware.",
        "justified": "Fault-tolerant runtime and footprint scale with T-count/T-depth; NISQ fidelity scales with two-qubit gate count and depth. Counting the wrong thing misprices the circuit.",
        "mistakes": [
            "Counting gates before transpiling (an abstract 'ccx' is 15+ physical gates).",
            "Treating every rz as free because rz is virtual on IBM hardware: virtual on NISQ, but costly in fault tolerance.",
            "Lumping Clifford and non-Clifford rz together.",
            "Forgetting rotation synthesis: arbitrary angles cost ~3·log₂(1/ε) T each.",
            "Reporting counts without basis, optimisation level and seed.",
        ],
        "impact": "Resource estimates off by orders of magnitude; wrong crossover dates in client memos; vendor circuits accepted as 'small' when they are not.",
        "test": "Lab B2: decompose a Toffoli and a small payoff-like circuit, classify every rz, and estimate T-count with synthesis at several precisions.",
    },
    "claims": [
        {"id": "b2_toffoli", "tag": "M", "text": "Qiskit transpiles a Toffoli to Clifford+T as 6 CX and 7 T/T† gates (plus 2 H).",
         "check": """from qiskit import QuantumCircuit, transpile
qc=QuantumCircuit(3); qc.ccx(0,1,2)
c=transpile(qc,basis_gates=['cx','h','s','sdg','t','tdg'],optimization_level=1,seed_transpiler=1).count_ops()
assert c['cx']==6 and c.get('t',0)+c.get('tdg',0)==7, c"""},
        {"id": "b2_gk", "tag": "S", "text": "Gottesman–Knill: Clifford circuits with stabiliser inputs and Pauli measurements are efficiently classically simulable.",
         "source": {"title": "The Heisenberg Representation of Quantum Computers (arXiv:quant-ph/9807006)", "publisher": "D. Gottesman", "date": "1998-07", "url": "https://arxiv.org/abs/quant-ph/9807006"},
         "last_verified": "2026-10-19"},
        {"id": "b2_rs", "tag": "S", "text": "Ancilla-free Clifford+T approximation of an arbitrary Z-rotation to precision ε uses about 3·log₂(1/ε) T gates.",
         "source": {"title": "Optimal ancilla-free Clifford+T approximation of z-rotations (arXiv:1403.2975)", "publisher": "Quantum Information & Computation 16 (Ross & Selinger)", "date": "2016", "url": "https://arxiv.org/abs/1403.2975"},
         "last_verified": "2026-10-19"},
    ],
    "lab": {
        "id": "b2_lab",
        "title": "Count what matters: Clifford vs T-type vs arbitrary rotations",
        "hypothesis": (
            "H1: a Toffoli transpiled to {cx, rz, sx, x} (seed 1, level 1) has exactly 7 T-type rz and 6 CX. "
            "H2: a 3-qubit circuit with one RY per qubit plus two Toffolis has ≥3 arbitrary rotations; at ε=1e-10 per rotation, "
            "the arbitrary rotations dominate the estimated T-count."
        ),
        "thresholds": "H1 exact; H2: arbitrary-rotation T share > 50%.",
        "data": "Synthetic circuits.",
        "code": r'''import numpy as np, pandas as pd
import plotly.graph_objects as go
from qiskit import QuantumCircuit, transpile
from qlab_helpers import SEED, show, record, table

def classify(t):
    out = {"clifford_rz": 0, "t_type_rz": 0, "arbitrary_rz": 0, "cx": 0, "sx": 0, "x": 0}
    for ins in t.data:
        n = ins.operation.name
        if n == "rz":
            k = float(ins.operation.params[0])/(np.pi/4)
            if abs(k - round(k)) > 1e-9: out["arbitrary_rz"] += 1
            elif round(k) % 2 == 0: out["clifford_rz"] += 1
            else: out["t_type_rz"] += 1
        elif n in out: out[n] += 1
    return out

basis = ["cx", "rz", "sx", "x"]
tof = QuantumCircuit(3); tof.ccx(0, 1, 2)
c_tof = classify(transpile(tof, basis_gates=basis, optimization_level=1, seed_transpiler=1))
mix = QuantumCircuit(3)
for q, a in enumerate([0.31, 1.07, 2.2]): mix.ry(a, q)
mix.ccx(0, 1, 2); mix.ccx(2, 1, 0)
c_mix = classify(transpile(mix, basis_gates=basis, optimization_level=1, seed_transpiler=SEED))
table(pd.DataFrame([dict(circuit="Toffoli", **c_tof), dict(circuit="3 RY + 2 Toffoli", **c_mix)]), "Gate classification after transpiling to {cx, rz, sx, x}")
rows = []
for eps in [1e-3, 1e-6, 1e-10, 1e-15]:
    per = int(np.ceil(3*np.log2(1/eps)))
    arb = c_mix["arbitrary_rz"]*per
    rows.append({"eps": eps, "T per rotation": per, "T from rotations": arb, "T from T-type": c_mix["t_type_rz"],
                 "total T": arb + c_mix["t_type_rz"], "rotation share": arb/(arb + c_mix["t_type_rz"])})
df = pd.DataFrame(rows); table(df, "Estimated T-count vs synthesis precision")
fig = go.Figure([go.Bar(x=[f"{e:.0e}" for e in df.eps], y=df["T from rotations"], name="from arbitrary rotations"),
                 go.Bar(x=[f"{e:.0e}" for e in df.eps], y=df["T from T-type"], name="from T-type gates")])
fig.update_layout(barmode="stack", title="Where the T gates come from", xaxis_title="synthesis precision ε per rotation", yaxis_title="T gates")
show(fig)
record("toffoli_t_type", c_tof["t_type_rz"]); record("toffoli_cx", c_tof["cx"])
record("rotation_share_1e-10", float(df.loc[df.eps == 1e-10, "rotation share"].item()))
print(c_tof, c_mix)
''',
        "expect": {"toffoli_t_type": "x == 7", "toffoli_cx": "x == 6", "rotation_share_1e-10": "x > 0.5"},
        "report_hints": "In the business section, explain why 'number of gates' is not a cost, and which count matters for which hardware era.",
    },
    "quiz": [
        {"id": "b2q1", "type": "mc", "q": "HZH equals:", "options": ["Z", "X", "Y", "I"], "answer": 1, "explain": "Hadamard swaps X and Z bases.", "tags": ["gates"]},
        {"id": "b2q2", "type": "mc", "q": "T² equals:", "options": ["Z", "S", "I", "X"], "answer": 1, "explain": "diag(1, e^{iπ/2}) = S.", "tags": ["gates"]},
        {"id": "b2q3", "type": "mc", "q": "Which set is universal?", "options": ["{H, S, CNOT}", "{H, T, CNOT}", "{X, Z}", "{CNOT}"], "answer": 1, "explain": "Clifford + T.", "tags": ["universality"]},
        {"id": "b2q4", "type": "mc", "q": "Gottesman–Knill says Clifford-only circuits are:", "options": ["Universal", "Efficiently classically simulable", "Impossible on hardware", "Error-free"], "answer": 1, "explain": "Stabiliser simulation.", "tags": ["clifford"]},
        {"id": "b2q5", "type": "mc", "q": "In the surface code, the expensive gate is:", "options": ["CNOT", "H", "T", "S"], "answer": 2, "explain": "Requires magic-state distillation.", "tags": ["ft"]},
        {"id": "b2q6", "type": "mc", "q": "Toffoli in Clifford+T uses how many T/T† gates (standard decomposition)?", "options": ["4", "6", "7", "15"], "answer": 2, "explain": "7 T-type, 6 CNOT.", "tags": ["toffoli"]},
        {"id": "b2q7", "type": "mc", "q": "After transpiling to {cx, rz, sx, x}, an rz(π/2) is:", "options": ["T-type", "Clifford", "Arbitrary", "Measurement"], "answer": 1, "explain": "S up to global phase.", "tags": ["counting"]},
        {"id": "b2q8", "type": "mc", "q": "An rz(0.31) needs, at ε = 1e-10, roughly how many T gates?", "options": ["1", "7", "≈100", "≈10,000"], "answer": 2, "explain": "3·log₂(1e10) ≈ 100.", "tags": ["synthesis"]},
        {"id": "b2q9", "type": "mc", "q": "On IBM superconducting hardware, rz is:", "options": ["The most error-prone gate", "Implemented virtually (frame change)", "Not supported", "A two-qubit gate"], "answer": 1, "explain": "Virtual Z.", "tags": ["hardware"]},
        {"id": "b2q10", "type": "mc", "q": "CZ equals:", "options": ["(H⊗H) CNOT (H⊗H)", "(I⊗H) CNOT (I⊗H)", "CNOT²", "SWAP·CNOT"], "answer": 1, "explain": "Conjugate the target by H.", "tags": ["gates"]},
        {"id": "b2q11", "type": "short", "q": "Why are counts reported 'before transpilation' not evidence of circuit cost?",
         "must": [["decompos", "transpil", "basis"], ["seed", "optimi", "level"]],
         "explain": "High-level gates decompose into many native gates; counts depend on basis, optimisation level and seed.", "tags": ["counting"]},
        {"id": "b2q12", "type": "short", "q": "Explain to a CTO why loading a probability as a rotation angle is expensive on a fault-tolerant machine.",
         "must": [["arbitrary", "continuous", "angle"], ["synthes", "approximat"], ["t gate", "t-count", "t count", "magic"]],
         "explain": "Arbitrary angles are not native; they are synthesised to precision ε with ~3log₂(1/ε) T gates, each needing magic states.", "tags": ["synthesis"]},
    ],
    "exercise": {
        "id": "b2_ex",
        "title": "A T-cost counter",
        "prompt": (
            "Implement:\n1. `rz_kind(theta, tol=1e-9)` → 'clifford' | 't_type' | 'arbitrary' (multiples of π/4).\n"
            "2. `classify_circuit(qc, seed=1)` → dict with keys clifford_rz, t_type_rz, arbitrary_rz, cx after transpiling to "
            "['cx','rz','sx','x'] at optimisation level 1.\n3. `t_estimate(counts, eps)` → t_type_rz + arbitrary_rz·ceil(3·log2(1/eps))."
        ),
        "starter": '''import numpy as np
from qiskit import transpile

def rz_kind(theta, tol=1e-9):
    raise NotImplementedError

def classify_circuit(qc, seed=1):
    raise NotImplementedError

def t_estimate(counts, eps):
    raise NotImplementedError
''',
        "solution": '''import numpy as np, math
from qiskit import transpile

def rz_kind(theta, tol=1e-9):
    k = float(theta)/(np.pi/4)
    if abs(k - round(k)) > tol:
        return "arbitrary"
    return "clifford" if round(k) % 2 == 0 else "t_type"

def classify_circuit(qc, seed=1):
    t = transpile(qc, basis_gates=["cx", "rz", "sx", "x"], optimization_level=1, seed_transpiler=seed)
    out = {"clifford_rz": 0, "t_type_rz": 0, "arbitrary_rz": 0, "cx": 0}
    for ins in t.data:
        if ins.operation.name == "rz":
            out[rz_kind(ins.operation.params[0]) + "_rz"] += 1
        elif ins.operation.name == "cx":
            out["cx"] += 1
    return out

def t_estimate(counts, eps):
    return counts["t_type_rz"] + counts["arbitrary_rz"]*math.ceil(3*math.log2(1/eps))
''',
        "tests": '''import numpy as np
from qiskit import QuantumCircuit

def test_rz_kind():
    assert rz_kind(np.pi/2) == "clifford" and rz_kind(-np.pi) == "clifford"
    assert rz_kind(np.pi/4) == "t_type" and rz_kind(-3*np.pi/4) == "t_type"
    assert rz_kind(0.3) == "arbitrary"

def test_toffoli():
    qc = QuantumCircuit(3); qc.ccx(0, 1, 2)
    c = classify_circuit(qc)
    assert c["t_type_rz"] == 7 and c["cx"] == 6 and c["arbitrary_rz"] == 0

def test_rotation_is_arbitrary():
    qc = QuantumCircuit(1); qc.ry(0.3, 0)
    assert classify_circuit(qc)["arbitrary_rz"] >= 1

def test_t_estimate():
    assert t_estimate({"t_type_rz": 7, "arbitrary_rz": 2}, 1e-10) == 7 + 2*100
''',
    },
    "cards": [
        {"front": "HZH", "back": "X", "kind": "formula"},
        {"front": "T², S²", "back": "T² = S, S² = Z", "kind": "formula"},
        {"front": "Universal gate set used in FT", "back": "Clifford + T ({H, S, CNOT, T})", "kind": "definition"},
        {"front": "Gottesman–Knill", "back": "Clifford circuits are efficiently classically simulable", "kind": "definition"},
        {"front": "Toffoli in Clifford+T", "back": "6 CNOT + 7 T/T† + 2 H", "kind": "number"},
        {"front": "T per arbitrary rotation", "back": "≈ 3·log₂(1/ε) (Ross–Selinger); ~100 at ε=1e-10", "kind": "formula"},
        {"front": "rz(kπ/4) classification", "back": "k even → Clifford; k odd → T-type; else arbitrary", "kind": "definition"},
        {"front": "Why T is expensive", "back": "Not transversal in surface code; needs magic-state distillation/cultivation", "kind": "definition"},
        {"front": "IBM native 1q gates", "back": "rz (virtual), sx, x", "kind": "definition"},
        {"front": "Mistake: counting before transpiling", "back": "Always count after transpiling to a fixed basis, seed and level", "kind": "mistake"},
        {"front": "NISQ cost driver vs FT cost driver", "back": "NISQ: 2-qubit gates/depth. FT: T-count/T-depth", "kind": "definition"},
    ],
    "defend": {
        "persona": "validator",
        "questions": [
            {"q": "Your slide says the oracle has 40 gates. In what basis, and does that number mean anything?",
             "must": [["basis", "transpil"], ["seed", "optimi", "level"], ["t", "two-qubit", "cx", "non-clifford"]],
             "model": "Only after transpiling to a fixed basis with seed and level; I report CX and non-Clifford counts separately."},
            {"q": "Why do you separate T-type from arbitrary rotations?",
             "must": [["synthes", "approximat"], ["log", "precision", "epsilon"]],
             "model": "Arbitrary rotations must be synthesised; each costs ~3log₂(1/ε) T, so they dominate at useful precision."},
            {"q": "If rz is free on IBM hardware, why do you count it?",
             "must": [["fault", "error correct", "ft"], ["virtual", "nisq", "today"]],
             "model": "rz is virtual on today's NISQ devices, but on a fault-tolerant machine non-Clifford rotations are the dominant cost."},
            {"q": "How many T gates does your payoff comparator need?",
             "must": [["toffoli"], ["7", "seven"]],
             "model": "Comparators/adders cost O(n) Toffolis, each ~7 T in Clifford+T; I give the exact count after decomposition."},
            {"q": "Could a classical computer simulate your circuit easily?",
             "must": [["clifford", "stabiliser", "stabilizer"], ["t", "non-clifford", "magic"]],
             "model": "Only if it were Clifford-only (Gottesman–Knill). Its non-Clifford content makes general simulation exponential."},
        ],
    },
    "glossary": {
        "Clifford gates": "Gates mapping Paulis to Paulis (H, S, CNOT); classically simulable alone.",
        "T gate": "π/8 phase gate; the costly non-Clifford gate in fault tolerance.",
        "T-count / T-depth": "Number of T gates / number of sequential T layers.",
        "Toffoli": "Controlled-controlled-NOT; 7 T in Clifford+T.",
        "Rotation synthesis": "Approximating arbitrary rotations with Clifford+T sequences.",
        "Universality": "Ability to approximate any unitary with a finite gate set.",
        "Magic state": "Resource state enabling non-Clifford gates via teleportation.",
    },
}
