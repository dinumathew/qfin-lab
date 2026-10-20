MODULE = {
    "summary": (
        "Bit ordering is the single most common source of silent errors in finance circuits. This module drills the three "
        "places it bites: count strings, `StatePreparation` amplitude indexing, and mixing big-endian references with "
        "little-endian Qiskit, each with a broken example, the fix and a unit test."
    ),
    "concepts": [
        {
            "title": "Reversed count strings",
            "why": "Count keys are written with qubit 0 on the right. Code that indexes `key[0]` as qubit 0 reads the wrong qubit {{c:q2_key}}.",
            "how": r"""
**Broken**: `bit_of_qubit0 = key[0]`. **Fix**: `bit_of_qubit_k = key[-1-k]` (or `int(key, 2) >> k & 1`).

For a register encoding an integer (a loss level, a grid index): `index = int(key, 2)` is correct *because* of little-endian ordering.
For marginals of a single qubit: use `key[-1-k]`.
""",
            "code": """from qiskit import QuantumCircuit
from qiskit_aer.primitives import SamplerV2
qc = QuantumCircuit(3); qc.x(0); qc.measure_all()
counts = SamplerV2(seed=1).run([qc], shots=100).result()[0].data.meas.get_counts()
key = next(iter(counts))
print("key:", key, "| BROKEN key[0] ->", key[0], "| FIX key[-1-0] ->", key[-1], "| int(key,2) =", int(key, 2))
""",
            "impact": "In a credit circuit, reading obligor 0's default flag from the wrong end swaps obligors. Exposure-weighted losses then attach to the wrong names.",
        },
        {
            "title": "StatePreparation amplitude indexing",
            "why": (
                "`StatePreparation(amplitudes)` puts `amplitudes[i]` on basis index $i$ (little-endian). If you build the "
                "amplitude vector from a grid assuming big-endian qubit roles, the distribution you load is permuted {{c:q2_stateprep}}."
            ),
            "how": r"""
Grid points $x_0<\dots<x_{2^n-1}$ with probabilities $p_i$: load amplitudes $\sqrt{p_i}$ in **index order**. Then the count key
`format(i, f"0{n}b")` corresponds to $x_i$, and `int(key, 2)` recovers $i$. Do **not** reverse bits when building the vector.
**Broken**: building the vector with `reversed` bit labels "to match the textbook". **Fix**: index order, and a unit test checking every $i$.
""",
            "code": """import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import StatePreparation
from qiskit.quantum_info import Statevector
p = np.array([0.05, 0.10, 0.20, 0.30, 0.15, 0.10, 0.06, 0.04])
qc = QuantumCircuit(3); qc.append(StatePreparation(np.sqrt(p)), range(3))
probs = Statevector(qc).probabilities_dict()
print(all(abs(probs[format(i, "03b")] - p[i]) < 1e-12 for i in range(8)))
""",
            "impact": "A permuted loss distribution produces a plausible, wrong VaR. This unit test is mandatory in every pricing or risk circuit you sign off.",
        },
        {
            "title": "Mixing big-endian references with little-endian Qiskit",
            "why": "Papers and NumPy references are usually big-endian; Qiskit is little-endian. Comparing them without reordering produces false failures or, worse, false passes on symmetric cases.",
            "how": r"""
* `Statevector.reverse_qargs()` and `Operator.reverse_qargs()` convert between conventions.
* For a NumPy kron reference $A\otimes B$ (A on "first" qubit), the equivalent Qiskit circuit applies A to the **highest** index.
* Always include an **asymmetric** test case (e.g. X on one qubit only); symmetric states (GHZ, all-zeros) hide ordering bugs.
""",
            "code": """import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
qc = QuantumCircuit(2); qc.x(0)
ref_big_endian = np.kron([0, 1], [1, 0])   # 'qubit 0' first = |10> big-endian
sv = Statevector(qc)
print("naive match:", np.allclose(sv.data, ref_big_endian), "| after reverse_qargs:", np.allclose(sv.reverse_qargs().data, ref_big_endian))
""",
            "impact": "Validation teams will test with asymmetric cases. If you haven't, they will find this before you do.",
        },
    ],
    "lens": {
        "look": "Every register gets a written mapping (qubit k ↔ meaning), an index-order unit test, and at least one asymmetric test against an exact reference.",
        "decision": "Whether a loaded distribution, a default-flag register or an asset-selection register is read correctly.",
        "justified": "Ordering bugs produce plausible numbers; only explicit index-by-index tests catch them.",
        "mistakes": [
            "key[0] as qubit 0.",
            "Reversing amplitude vectors 'to match the paper'.",
            "Testing only symmetric states.",
            "Forgetting that SparsePauliOp labels are also little-endian.",
            "Assuming measure_all and custom registers share ordering conventions in mixed circuits.",
        ],
        "impact": "Wrong VaR, swapped obligors, wrong portfolio selection: all with no error message.",
        "test": "Lab Q2: load a skewed 3-qubit distribution with StatePreparation, verify index mapping by statevector and sampling, then show how a reversed vector changes a tail probability.",
    },
    "claims": [
        {"id": "q2_key", "tag": "M", "text": "X on qubit 0 of 3 gives key '001': key[-1] is qubit 0.",
         "check": """from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
qc=QuantumCircuit(3); qc.x(0)
assert Statevector(qc).probabilities_dict()=={'001':1.0}"""},
        {"id": "q2_stateprep", "tag": "M", "text": "StatePreparation places amplitudes[i] on basis index i: probability of key format(i,'0nb') equals p_i.",
         "check": """import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import StatePreparation
from qiskit.quantum_info import Statevector
p=np.arange(1,9)/36; qc=QuantumCircuit(3); qc.append(StatePreparation(np.sqrt(p)),range(3))
d=Statevector(qc).probabilities_dict()
assert all(abs(d[format(i,'03b')]-p[i])<1e-12 for i in range(8))"""},
        {"id": "q2_doc", "tag": "S", "text": "Qiskit's bit-ordering guide.",
         "source": {"title": "Bit-ordering in the Qiskit SDK", "publisher": "IBM Quantum documentation", "date": "2026 (Qiskit 2.x docs)", "url": "https://quantum.cloud.ibm.com/docs/en/guides/bit-ordering"},
         "time_sensitive": True, "last_verified": "2026-10-19"},
    ],
    "lab": {
        "id": "q2_lab",
        "title": "Load a loss distribution and prove the mapping",
        "hypothesis": (
            "H1: loading √p in index order gives P(key i) = p_i to 1e-12 for all 8 indices. "
            "H2: sampled tail probability P(loss index ≥ 6) at 20,000 shots is within 4 SE of the true value. "
            "H3: the bit-reversed (broken) load changes the tail probability by more than 0.05."
        ),
        "thresholds": "1e-12; 4 SE; |Δtail| > 0.05.",
        "data": "Synthetic skewed loss distribution on 8 levels.",
        "code": r'''import numpy as np, pandas as pd
import plotly.graph_objects as go
from qiskit import QuantumCircuit
from qiskit.circuit.library import StatePreparation
from qiskit.quantum_info import Statevector
from qiskit_aer.primitives import SamplerV2
from qlab_helpers import SEED, show, record, table

p = np.array([0.30, 0.25, 0.15, 0.10, 0.08, 0.06, 0.04, 0.02])   # loss levels 0..7
n = 3
def load(vec):
    qc = QuantumCircuit(n); qc.append(StatePreparation(np.sqrt(vec)), range(n)); return qc
good = Statevector(load(p)).probabilities_dict()
max_err = max(abs(good.get(format(i, "03b"), 0) - p[i]) for i in range(8))
rev_idx = [int(format(i, "03b")[::-1], 2) for i in range(8)]
p_broken = p[rev_idx]                                    # what a 'big-endian' builder accidentally loads
broken = Statevector(load(p_broken)).probabilities_dict()
tail_true = p[6:].sum()
tail_broken = sum(broken.get(format(i, "03b"), 0) for i in (6, 7))
m = load(p); m.measure_all()
# Aer's sampler does not know 'state_preparation': transpile first (another reason to count after transpiling, Q3)
from qiskit import transpile
m = transpile(m, basis_gates=["cx", "rz", "sx", "x", "measure"], seed_transpiler=SEED)
c = SamplerV2(seed=SEED).run([m], shots=20000).result()[0].data.meas.get_counts()
tail_hat = sum(v for k, v in c.items() if int(k, 2) >= 6)/20000
se = np.sqrt(tail_true*(1-tail_true)/20000)
df = pd.DataFrame({"index": range(8), "key": [format(i, "03b") for i in range(8)], "p true": p,
                   "P(key) correct load": [good.get(format(i, "03b"), 0) for i in range(8)],
                   "P(key) reversed load": [broken.get(format(i, "03b"), 0) for i in range(8)]})
table(df.round(4), "Index ↔ key mapping")
fig = go.Figure([go.Bar(x=df.key, y=df["p true"], name="true"), go.Bar(x=df.key, y=df["P(key) reversed load"], name="reversed (broken)")])
fig.update_layout(barmode="group", title=f"Tail P(index ≥ 6): true {tail_true:.3f} vs broken {tail_broken:.3f}"); show(fig)
record("max_err_correct", float(max_err)); record("tail_z", float(abs(tail_hat - tail_true)/se))
record("tail_shift_broken", float(abs(tail_broken - tail_true)))
''',
        "expect": {"max_err_correct": "x < 1e-12", "tail_z": "x < 4", "tail_shift_broken": "x > 0.05"},
        "report_hints": "Your business translation: a bit-order bug in a VaR circuit changes the tail by this much. Express it as a VaR or capital error.",
    },
    "quiz": [
        {"id": "q2q1", "type": "mc", "q": "Bit of qubit k from a count key:", "options": ["key[k]", "key[-1-k]", "key[n-k]", "int(key)[k]"], "answer": 1, "explain": "Rightmost is qubit 0.", "tags": ["keys"]},
        {"id": "q2q2", "type": "mc", "q": "Integer encoded by a register's key:", "options": ["int(key[::-1], 2)", "int(key, 2)", "len(key)", "sum(key)"], "answer": 1, "explain": "Little-endian makes int(key,2) correct.", "tags": ["keys"]},
        {"id": "q2q3", "type": "mc", "q": "StatePreparation(a) puts a[i] on:", "options": ["Bit-reversed index", "Basis index i (little-endian)", "Random index", "Qubit i"], "answer": 1, "explain": "Index order.", "tags": ["stateprep"]},
        {"id": "q2q4", "type": "mc", "q": "Which test state hides ordering bugs?", "options": ["X on qubit 0 only", "GHZ / all-zeros (symmetric)", "Skewed distribution", "Random asymmetric state"], "answer": 1, "explain": "Symmetric under reversal.", "tags": ["testing"]},
        {"id": "q2q5", "type": "mc", "q": "Convert a Qiskit Statevector to big-endian:", "options": ["sv.conjugate()", "sv.reverse_qargs()", "sv.transpose()", "np.flip(sv)"], "answer": 1, "explain": "reverse_qargs.", "tags": ["conversion"]},
        {"id": "q2q6", "type": "mc", "q": "SparsePauliOp('ZI') acts with Z on:", "options": ["qubit 0", "qubit 1", "both", "neither"], "answer": 1, "explain": "Leftmost label char = highest qubit.", "tags": ["paulis"]},
        {"id": "q2q7", "type": "mc", "q": "For 3 qubits, key '110' is index:", "options": ["3", "6", "1", "4"], "answer": 1, "explain": "int('110',2)=6.", "tags": ["keys"]},
        {"id": "q2q8", "type": "mc", "q": "A reversed amplitude vector for an 8-level distribution:", "options": ["Is harmless", "Permutes levels (e.g. 1↔4, 3↔6)", "Normalises it", "Only changes phases"], "answer": 1, "explain": "Bit-reversal permutation.", "tags": ["stateprep"]},
        {"id": "q2q9", "type": "mc", "q": "np.kron(A, B) corresponds in Qiskit to:", "options": ["A on qubit 0, B on qubit 1", "B on qubit 0, A on qubit 1", "A on both", "Undefined"], "answer": 1, "explain": "Rightmost factor is qubit 0.", "tags": ["conversion"]},
        {"id": "q2q10", "type": "mc", "q": "Minimum unit test for a loaded distribution:", "options": ["Sum of probabilities is 1", "Every index i maps to key format(i) with p_i", "Visual check", "Number of qubits"], "answer": 1, "explain": "Index-by-index.", "tags": ["testing"]},
        {"id": "q2q11", "type": "short", "q": "Write the one-line fix for reading obligor k's default flag from a count key, and say why.",
         "must": [["[-1-k]", "-1-k", ">> k", ">>k"], ["little", "rightmost", "qubit 0"]],
         "explain": "key[-1-k] (or int(key,2)>>k & 1) because qubit 0 is the rightmost bit.", "tags": ["keys"]},
        {"id": "q2q12", "type": "short", "q": "Why must ordering tests include an asymmetric state?",
         "must": [["symmetric", "ghz", "invariant", "palindrom"], ["hide", "pass", "mask", "miss"]],
         "explain": "Symmetric states are invariant under bit reversal, so a reversed implementation passes the test.", "tags": ["testing"]},
    ],
    "exercise": {
        "id": "q2_ex",
        "title": "Ordering-safe readers",
        "prompt": (
            "Implement:\n1. `qubit_bit(key, k)`.\n2. `marginal(counts, k)` → P(qubit k = 1).\n"
            "3. `load_distribution(p)` → QuantumCircuit (n = log2(len(p)) qubits) loading √p in index order.\n"
            "4. `prob_by_index(counts, n)` → numpy array of length 2^n with frequency of each integer index."
        ),
        "starter": '''import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import StatePreparation

def qubit_bit(key, k):
    raise NotImplementedError

def marginal(counts, k):
    raise NotImplementedError

def load_distribution(p):
    raise NotImplementedError

def prob_by_index(counts, n):
    raise NotImplementedError
''',
        "solution": '''import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import StatePreparation

def qubit_bit(key, k):
    return int(key[-1 - k])

def marginal(counts, k):
    tot = sum(counts.values())
    return sum(v for kk, v in counts.items() if qubit_bit(kk, k))/tot

def load_distribution(p):
    p = np.asarray(p, dtype=float); n = int(np.log2(len(p)))
    assert 2**n == len(p)
    qc = QuantumCircuit(n); qc.append(StatePreparation(np.sqrt(p/p.sum())), range(n)); return qc

def prob_by_index(counts, n):
    out = np.zeros(2**n); tot = sum(counts.values())
    for k, v in counts.items():
        out[int(k, 2)] += v/tot
    return out
''',
        "tests": '''import numpy as np
from qiskit.quantum_info import Statevector

def test_qubit_bit():
    assert qubit_bit("001", 0) == 1 and qubit_bit("001", 2) == 0 and qubit_bit("100", 2) == 1

def test_marginal():
    c = {"001": 30, "000": 70}
    assert abs(marginal(c, 0) - 0.3) < 1e-12 and marginal(c, 1) == 0

def test_load_asymmetric():
    p = np.array([0.30, 0.25, 0.15, 0.10, 0.08, 0.06, 0.04, 0.02])
    d = Statevector(load_distribution(p)).probabilities()
    assert np.allclose(d, p, atol=1e-12)

def test_prob_by_index():
    c = {"110": 1, "001": 3}
    v = prob_by_index(c, 3)
    assert v[6] == 0.25 and v[1] == 0.75
''',
    },
    "cards": [
        {"front": "Qubit k's bit in key", "back": "key[-1-k]", "kind": "formula"},
        {"front": "Register integer from key", "back": "int(key, 2)", "kind": "formula"},
        {"front": "StatePreparation index rule", "back": "amplitudes[i] → basis index i (little-endian)", "kind": "definition"},
        {"front": "Convert to big-endian", "back": ".reverse_qargs()", "kind": "definition"},
        {"front": "np.kron(A,B) in Qiskit", "back": "B on qubit 0, A on qubit 1", "kind": "definition"},
        {"front": "SparsePauliOp('ZI')", "back": "Z on qubit 1", "kind": "mistake"},
        {"front": "Ordering test must include", "back": "An asymmetric state", "kind": "mistake"},
        {"front": "Bit-reversal on 3 qubits", "back": "1↔4, 3↔6; 0,2,5,7 fixed", "kind": "number"},
        {"front": "Mistake: key[0] as qubit 0", "back": "Reads the highest qubit", "kind": "mistake"},
        {"front": "Mandatory test for loaders", "back": "Every index i → key format(i, '0nb') with p_i", "kind": "definition"},
    ],
    "defend": {
        "persona": "validator",
        "questions": [
            {"q": "Prove obligor 3's default flag is read from the right qubit.",
             "must": [["test", "unit"], ["asymmetric", "x on", "single"], ["-1-k", "rightmost", "little"]],
             "model": "Asymmetric unit test: X on qubit 3 only, check key[-1-3] is 1 and others 0."},
            {"q": "How do you know the loss grid loaded in the right order?",
             "must": [["index", "each", "every"], ["format", "key", "int("]],
             "model": "Index-by-index test: P(format(i)) equals p_i for all i to 1e-12."},
            {"q": "Your NumPy reference disagrees with Qiskit on one test only. Likely cause?",
             "must": [["order", "endian", "reverse"]], "model": "Ordering; check reverse_qargs and kron order."},
            {"q": "What would a reversed loader do to VaR?",
             "must": [["permut", "swap", "reorder"], ["tail", "var", "wrong", "biased"]], "model": "Permutes loss levels, shifting the tail and producing a plausible but wrong VaR."},
            {"q": "Are Pauli labels ordered the same way?",
             "must": [["yes", "same", "little"], ["rightmost", "qubit 0", "last"]], "model": "Yes; the rightmost character is qubit 0."},
        ],
    },
    "glossary": {
        "Little-endian": "Qubit 0 = least significant bit (rightmost).",
        "StatePreparation": "Qiskit gate that prepares a given amplitude vector.",
        "reverse_qargs": "Method reversing qubit order of a state or operator.",
        "Bit-reversal permutation": "Mapping index i to the integer with reversed bits.",
    },
}
