MODULE = {
    "summary": (
        "Entanglement is what makes multi-qubit states more than lists of qubits, and Qiskit's bit ordering is what makes "
        "beginners misread every multi-qubit result. This module covers Bell and GHZ states, tensor ordering, and "
        "little-endian count strings, then drills you until you can predict the exact count keys of a circuit before "
        "you run it."
    ),
    "concepts": [
        {
            "title": "Entanglement: Bell and GHZ states",
            "why": (
                "Entangled states cannot be described qubit by qubit. Correlations in loss events, joint default indicators and "
                "multi-asset grids in quantum finance circuits are all represented by entangled registers. Entanglement is also "
                "fragile: noise destroys it fastest, which is why GHZ fidelity is a standard hardware health check (B5)."
            ),
            "how": r"""
Bell states: $|\Phi^\pm\rangle=\tfrac{1}{\sqrt2}(|00\rangle\pm|11\rangle)$, $|\Psi^\pm\rangle=\tfrac{1}{\sqrt2}(|01\rangle\pm|10\rangle)$.
Prepare $|\Phi^+\rangle$ with $H$ on qubit 0 then CNOT(0→1). GHZ$_n$ $=\tfrac{1}{\sqrt2}(|0\cdots0\rangle+|1\cdots1\rangle)$: H then a chain of CNOTs.

Signature: each qubit alone looks random ($\langle Z_i\rangle=0$) but parities are perfect ($\langle Z_iZ_j\rangle=1$).
Entanglement test for 2 qubits: Schmidt rank $>1$ (P1), equivalently the reduced state of one qubit is mixed (purity $\mathrm{Tr}\rho_A^2<1$).
""",
            "code": """from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, partial_trace, SparsePauliOp
qc = QuantumCircuit(2); qc.h(0); qc.cx(0, 1)
sv = Statevector(qc)
print("amplitudes:", sv.data.round(4))
print("<Z0>=", sv.expectation_value(SparsePauliOp('IZ')).real, " <Z0Z1>=", sv.expectation_value(SparsePauliOp('ZZ')).real)
rhoA = partial_trace(sv, [1])
print("purity of qubit 0:", rhoA.purity().real, "(0.5 = maximally mixed, i.e. maximally entangled pair)")
""",
            "impact": (
                "Entanglement is a resource, not a selling point. A client should hear: 'the algorithm needs entanglement to "
                "represent correlated outcomes, and that is exactly what today's noise erodes first; ask how deep the entangling "
                "circuit is and what fidelity the hardware shows on GHZ benchmarks of that size.'"
            ),
        },
        {
            "title": "Tensor ordering and Qiskit's little-endian convention",
            "why": (
                "Qiskit labels qubit 0 as the least significant (rightmost) bit everywhere: in `Statevector` indices, in "
                "`Operator` matrices and in count strings. Textbooks and most papers use the opposite. Mixing the two silently "
                "permutes your loss distribution or swaps assets, and the code still runs. It is the most common beginner bug. {{c:b3_le}}"
            ),
            "how": r"""
Basis index $i=\sum_k b_k 2^k$ where $b_k$ is the bit of **qubit $k$**. The count string is written $b_{n-1}\cdots b_1b_0$.
* `qc.x(0)` on 3 qubits → count key `'001'`, statevector index 1.
* `Statevector.from_label('001')` puts qubit 0 in $|1\rangle$.
* Pauli labels too: `SparsePauliOp('IZ')` is $Z$ on qubit 0.
* A register loaded with a distribution over $2^n$ points via amplitudes $\sqrt{p_i}$ maps grid point $i$ to the count key `format(i, f'0{n}b')`.
""",
            "code": """from qiskit import QuantumCircuit
from qiskit_aer.primitives import SamplerV2
qc = QuantumCircuit(3); qc.x(0); qc.measure_all()
print(SamplerV2(seed=1).run([qc], shots=10).result()[0].data.meas.get_counts())   # {'001': 10}
qc = QuantumCircuit(3); qc.x(2); qc.measure_all()
print(SamplerV2(seed=1).run([qc], shots=10).result()[0].data.meas.get_counts())   # {'100': 10}
""",
            "impact": (
                "In a pricing or VaR circuit, a reversed register reverses the loss grid: the estimate is plausible and wrong. "
                "Insist on a unit test that maps each grid index to its count key before any result is shown to a client."
            ),
        },
        {
            "title": "Predicting count strings of multi-qubit circuits",
            "why": (
                "Predict-then-verify is the debugging discipline that catches ordering, sign and control/target mistakes at "
                "toy size, where they are cheap. If you cannot predict a 3-qubit circuit's counts, you cannot validate a 7-qubit credit oracle."
            ),
            "how": r"""
Procedure: (1) write the state after each gate in ket notation with qubit 0 rightmost; (2) list outcomes and probabilities;
(3) convert to Qiskit keys; (4) run with a seed and compare within shot noise.

Example: H(0), CX(0→1), X(2): $\tfrac1{\sqrt2}(|100\rangle+|111\rangle)$ → keys `'100'` and `'111'`, each 0.5.
""",
            "code": """from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
qc = QuantumCircuit(3); qc.h(0); qc.cx(0, 1); qc.x(2)
print({k: round(v, 3) for k, v in Statevector(qc).probabilities_dict().items()})
""",
            "impact": "This is the habit that makes your pilots defensible: every circuit ships with predicted outputs at toy size, checked automatically.",
        },
    ],
    "lens": {
        "look": "Write the predicted ket (qubit 0 rightmost), predicted count keys and probabilities; compare to Statevector.probabilities_dict() exactly and to sampled counts within shot noise.",
        "decision": "Whether a multi-qubit register (asset grid, factor register, default flags) is encoded and read in the intended order.",
        "justified": "Ordering errors are silent: results look plausible. Only explicit predictions at toy size catch them.",
        "mistakes": [
            "Reading count strings left-to-right as qubit 0,1,2.",
            "Building a NumPy reference in big-endian and comparing to Qiskit without reordering.",
            "Swapping control and target in CNOT chains.",
            "Assuming each qubit of a Bell pair has a definite value.",
            "Using `measure_all` and also custom classical registers, then reading the wrong register.",
        ],
        "impact": "Mis-mapped loss grids and swapped assets: biased VaR, wrong optimal portfolios, and validation findings that undermine the whole pilot.",
        "test": "Lab B3: predict, then verify, count strings for a set of 3-qubit circuits, and quantify the GHZ correlation signature.",
    },
    "claims": [
        {"id": "b3_le", "tag": "M", "text": "In Qiskit, X on qubit 0 of a 3-qubit circuit yields the count key '001'.",
         "check": """from qiskit import QuantumCircuit
from qiskit_aer.primitives import SamplerV2
qc=QuantumCircuit(3); qc.x(0); qc.measure_all()
assert SamplerV2(seed=1).run([qc],shots=5).result()[0].data.meas.get_counts()=={'001':5}"""},
        {"id": "b3_doc", "tag": "S", "text": "Qiskit documents its bit-ordering convention (qubit 0 least significant).",
         "source": {"title": "Bit-ordering in the Qiskit SDK", "publisher": "IBM Quantum documentation", "date": "2026 (Qiskit 2.x docs)", "url": "https://quantum.cloud.ibm.com/docs/en/guides/bit-ordering"},
         "time_sensitive": True, "last_verified": "2026-10-19"},
    ],
    "lab": {
        "id": "b3_lab",
        "title": "Predict, then verify, the count strings of three-qubit circuits",
        "hypothesis": (
            "H1: for each of 6 circuits, my written predictions (below in PRED) match the exact Statevector probabilities to 1e-9. "
            "H2: sampled counts at 4,000 shots are within 4 standard errors of the predictions for every key."
        ),
        "thresholds": "Exact match 1e-9; sampled within 4 SE.",
        "data": "Synthetic circuits; ideal simulator.",
        "code": r'''import numpy as np, pandas as pd
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from qiskit_aer.primitives import SamplerV2
from qlab_helpers import SEED, record, table

def c1(): qc = QuantumCircuit(3); qc.x(0); return qc
def c2(): qc = QuantumCircuit(3); qc.x(1); qc.x(2); return qc
def c3(): qc = QuantumCircuit(3); qc.h(0); qc.cx(0, 1); qc.x(2); return qc
def c4(): qc = QuantumCircuit(3); qc.h(2); qc.cx(2, 0); return qc
def c5(): qc = QuantumCircuit(3); qc.h(0); qc.cx(0, 1); qc.cx(1, 2); return qc
def c6(): qc = QuantumCircuit(3); qc.x(0); qc.x(1); qc.ccx(0, 1, 2); return qc
# EDIT THESE PREDICTIONS FIRST, before running. Qiskit keys: qubit 0 is the rightmost character.
PRED = {
    "x(0)": {"001": 1.0},
    "x(1),x(2)": {"110": 1.0},
    "h0,cx01,x2": {"100": 0.5, "111": 0.5},
    "h2,cx20": {"000": 0.5, "101": 0.5},
    "GHZ": {"000": 0.5, "111": 0.5},
    "toffoli": {"111": 1.0},
}
circs = dict(zip(PRED, [c1(), c2(), c3(), c4(), c5(), c6()]))
rows, exact_ok, sample_ok = [], True, True
for name, qc in circs.items():
    exact = {k: v for k, v in Statevector(qc).probabilities_dict().items() if v > 1e-12}
    keys = set(exact) | set(PRED[name])
    ex_match = all(abs(exact.get(k, 0) - PRED[name].get(k, 0)) < 1e-9 for k in keys)
    m = qc.copy(); m.measure_all()
    counts = SamplerV2(seed=SEED).run([m], shots=4000).result()[0].data.meas.get_counts()
    worst = max(abs(counts.get(k, 0)/4000 - p)/max(np.sqrt(p*(1-p)/4000), 1e-9) if 0 < p < 1 else abs(counts.get(k, 0)/4000 - p)*1e6
                for k, p in PRED[name].items())
    exact_ok &= ex_match; sample_ok &= worst < 4
    rows.append({"circuit": name, "predicted": PRED[name], "exact": {k: round(v, 4) for k, v in exact.items()},
                 "sampled": dict(sorted(counts.items())), "exact match": ex_match, "worst |z|": round(worst, 2)})
table(pd.DataFrame(rows).astype(str), "Predicted vs exact vs sampled")
record("all_exact_match", bool(exact_ok)); record("all_within_4se", bool(sample_ok))
print("exact:", exact_ok, "| sampled:", sample_ok)
''',
        "expect": {"all_exact_match": "x is True", "all_within_4se": "x is True"},
        "learner_blank": ["x(0)", "x(1),x(2)", "h0,cx01,x2", "h2,cx20", "GHZ", "toffoli"],
        "report_hints": "The skill being assessed is prediction. In the report, include one prediction you got wrong at first and why.",
    },
    "quiz": [
        {"id": "b3q1", "type": "mc", "q": "qc.x(0) on a 3-qubit circuit gives which Qiskit count key?", "options": ["'100'", "'010'", "'001'", "'111'"], "answer": 2, "explain": "Qubit 0 is rightmost.", "tags": ["ordering"]},
        {"id": "b3q2", "type": "mc", "q": "H(0), CX(0→1), X(2) gives keys:", "options": ["'001','111'", "'100','111'", "'000','011'", "'110','101'"], "answer": 1, "explain": "(|100⟩+|111⟩)/√2.", "tags": ["ordering"]},
        {"id": "b3q3", "type": "mc", "q": "In a Bell pair |Φ+⟩, ⟨Z₀⟩ and ⟨Z₀Z₁⟩ are:", "options": ["1 and 1", "0 and 1", "0 and 0", "1 and 0"], "answer": 1, "explain": "Random individually, perfectly correlated jointly.", "tags": ["entanglement"]},
        {"id": "b3q4", "type": "mc", "q": "Purity of one qubit of a Bell pair is:", "options": ["1", "0.5", "0", "0.25"], "answer": 1, "explain": "Maximally mixed.", "tags": ["entanglement"]},
        {"id": "b3q5", "type": "mc", "q": "Statevector index 6 on 3 qubits corresponds to:", "options": ["q0=1,q1=1,q2=0", "q0=0,q1=1,q2=1", "q0=1,q1=0,q2=1", "q0=0,q1=0,q2=1"], "answer": 1, "explain": "6 = 0b110 → q2=1,q1=1,q0=0.", "tags": ["ordering"]},
        {"id": "b3q6", "type": "mc", "q": "SparsePauliOp('IZ') acts with Z on:", "options": ["qubit 1", "qubit 0", "both", "neither"], "answer": 1, "explain": "Labels are little-endian too.", "tags": ["ordering"]},
        {"id": "b3q7", "type": "mc", "q": "A GHZ₃ state measured gives:", "options": ["All 8 outcomes equally", "'000' and '111' only", "'001' only", "'010' and '101'"], "answer": 1, "explain": "Perfect correlation.", "tags": ["entanglement"]},
        {"id": "b3q8", "type": "mc", "q": "A product state of 2 qubits has Schmidt rank:", "options": ["0", "1", "2", "4"], "answer": 1, "explain": "Rank 1.", "tags": ["entanglement"]},
        {"id": "b3q9", "type": "mc", "q": "H(2), CX(2→0) on 3 qubits gives keys:", "options": ["'000','101'", "'000','011'", "'100','001'", "'000','110'"], "answer": 0, "explain": "(|000⟩+|101⟩)/√2.", "tags": ["ordering"]},
        {"id": "b3q10", "type": "mc", "q": "To compare a big-endian NumPy reference with a Qiskit Statevector you must:", "options": ["Nothing", "Reverse the qubit order (e.g. Statevector.reverse_qargs())", "Take complex conjugates", "Normalise again"], "answer": 1, "explain": "Reorder qubits.", "tags": ["ordering"]},
        {"id": "b3q11", "type": "short", "q": "A 3-qubit register encodes 8 loss levels via amplitudes √p_i. Which count key corresponds to loss level i=3, and why?",
         "must": [["011"], ["qubit 0", "rightmost", "least significant", "little"]],
         "explain": "'011': index 3 in binary, with qubit 0 as least significant (rightmost) bit.", "tags": ["ordering"]},
        {"id": "b3q12", "type": "short", "q": "Why is predict-then-verify at toy size a validation control and not just a learning exercise?",
         "must": [["silent", "plausible", "runs"], ["toy", "small", "cheap"], ["order", "sign", "bug", "error"]],
         "explain": "Ordering/sign bugs are silent and plausible; explicit predictions at toy size catch them cheaply.", "tags": ["validation"]},
    ],
    "exercise": {
        "id": "b3_ex",
        "title": "Ordering utilities",
        "prompt": (
            "Implement:\n1. `key_for(bits)` where bits[k] is the bit of qubit k → Qiskit count key string.\n"
            "2. `bits_of(key)` inverse: returns list with bits[k] for qubit k.\n"
            "3. `basis_circuit(key)` → QuantumCircuit preparing that computational basis state (Qiskit key convention).\n"
            "4. `is_entangled_2q(psi, tol=1e-9)` for a 4-amplitude Qiskit-ordered statevector.\n"
            "5. `ghz(n)` → QuantumCircuit preparing GHZ_n (no measurements)."
        ),
        "starter": '''import numpy as np
from qiskit import QuantumCircuit

def key_for(bits):
    raise NotImplementedError

def bits_of(key):
    raise NotImplementedError

def basis_circuit(key):
    raise NotImplementedError

def is_entangled_2q(psi, tol=1e-9):
    raise NotImplementedError

def ghz(n):
    raise NotImplementedError
''',
        "solution": '''import numpy as np
from qiskit import QuantumCircuit

def key_for(bits):
    return "".join(str(b) for b in reversed(bits))

def bits_of(key):
    return [int(c) for c in reversed(key)]

def basis_circuit(key):
    qc = QuantumCircuit(len(key))
    for k, b in enumerate(bits_of(key)):
        if b:
            qc.x(k)
    return qc

def is_entangled_2q(psi, tol=1e-9):
    s = np.linalg.svd(np.asarray(psi, dtype=complex).reshape(2, 2), compute_uv=False)
    return bool(s[1] > tol)

def ghz(n):
    qc = QuantumCircuit(n); qc.h(0)
    for k in range(n - 1):
        qc.cx(k, k + 1)
    return qc
''',
        "tests": '''import numpy as np
from qiskit.quantum_info import Statevector

def test_key_roundtrip():
    assert key_for([1, 0, 0]) == "001" and bits_of("110") == [0, 1, 1]
    for k in ("0101", "1110", "0001"):
        assert key_for(bits_of(k)) == k

def test_basis_circuit():
    for k in ("001", "110", "101"):
        assert Statevector(basis_circuit(k)).probabilities_dict() == {k: 1.0}

def test_entangled():
    bell = np.array([1, 0, 0, 1])/np.sqrt(2)
    prod = np.kron([1, 1], [1, 0])/np.sqrt(2)
    assert is_entangled_2q(bell) and not is_entangled_2q(prod)

def test_ghz():
    p = Statevector(ghz(4)).probabilities_dict()
    assert set(k for k, v in p.items() if v > 1e-9) == {"0000", "1111"}
''',
    },
    "cards": [
        {"front": "Qiskit count key for x(0) on 3 qubits", "back": "'001'", "kind": "mistake"},
        {"front": "Basis index from qubit bits", "back": "i = Σ b_k 2^k (qubit 0 least significant)", "kind": "formula"},
        {"front": "|Φ+⟩ preparation", "back": "H(0), CX(0→1)", "kind": "definition"},
        {"front": "Bell pair correlations", "back": "⟨Z₀⟩=0, ⟨Z₀Z₁⟩=1", "kind": "number"},
        {"front": "GHZ_n", "back": "(|0…0⟩ + |1…1⟩)/√2; H then CNOT chain", "kind": "definition"},
        {"front": "Entanglement test (2 qubits)", "back": "Schmidt rank > 1 ⇔ reduced state mixed (purity < 1)", "kind": "definition"},
        {"front": "Pauli label 'IZ'", "back": "Z on qubit 0 (rightmost)", "kind": "mistake"},
        {"front": "Reorder Qiskit statevector to big-endian", "back": "Statevector.reverse_qargs()", "kind": "definition"},
        {"front": "Index 6 on 3 qubits", "back": "'110': q2=1, q1=1, q0=0", "kind": "number"},
        {"front": "Most common beginner bug", "back": "Reading count strings as q0 q1 q2 left to right", "kind": "mistake"},
    ],
    "defend": {
        "persona": "validator",
        "questions": [
            {"q": "How do you know grid point 3 of the loss distribution is where you think it is?",
             "must": [["unit test", "test"], ["key", "index", "count string"], ["little", "rightmost", "qubit 0"]],
             "model": "A unit test maps each grid index to its little-endian count key and checks the loaded probabilities key by key."},
            {"q": "What does entanglement buy you in this circuit, and what does it cost?",
             "must": [["correlat", "joint"], ["noise", "fragile", "fidelity", "depth"]],
             "model": "It represents correlated outcomes jointly; it is fragile, so entangling depth drives error."},
            {"q": "Show me a prediction you made before running.",
             "must": [["predict", "expected", "before"], ["matched", "match", "within", "exact"]],
             "model": "Predicted keys and probabilities written first; exact match to statevector and within 4 SE on samples."},
            {"q": "Your NumPy reference and Qiskit disagree. First thing you check?",
             "must": [["order", "endian", "reverse"]], "model": "Qubit ordering: reverse_qargs or kron order."},
            {"q": "Can one qubit of a Bell pair be validated on its own?",
             "must": [["no", "not"], ["joint", "correlat", "parity", "zz"]], "model": "No: alone it is maximally mixed; validation needs joint statistics such as ⟨ZZ⟩."},
        ],
    },
    "glossary": {
        "Entanglement": "Correlation not decomposable into individual qubit states.",
        "Bell state": "Maximally entangled 2-qubit state.",
        "GHZ state": "(|0…0⟩+|1…1⟩)/√2; standard multi-qubit entanglement benchmark.",
        "Little-endian": "Qubit 0 is the least significant bit (rightmost in strings).",
        "Partial trace": "Operation giving a subsystem's reduced state.",
        "Purity": "Tr(ρ²); 1 for pure states, <1 for mixed.",
    },
}
