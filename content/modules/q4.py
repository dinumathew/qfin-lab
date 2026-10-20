MODULE = {
    "summary": (
        "Classical simulation is your reference and your sandbox, and it has hard limits. Statevector memory is 16·2ⁿ "
        "bytes, density matrix 16·4ⁿ. This module makes you predict, before you run, whether a simulation fits your laptop, "
        "and when to switch to matrix-product-state methods, which handle many qubits only when entanglement stays low."
    ),
    "concepts": [
        {
            "title": "Memory: statevector 16·2ⁿ, density matrix 16·4ⁿ bytes",
            "why": "A complex128 amplitude is 16 bytes. Doubling with each qubit means 30 qubits needs 16 GiB for the state alone; a density matrix of 15 qubits needs 16 GiB. Exceeding RAM crashes or swaps for hours {{c:q4_mem}}.",
            "how": r"""
Statevector: $16\cdot2^n$ B → 20 q: 16 MiB; 25 q: 512 MiB; 30 q: 16 GiB; 34 q: 256 GiB.
Density matrix: $16\cdot4^n$ B → 10 q: 16 MiB; 13 q: 1 GiB; 15 q: 16 GiB.
Rule of thumb: you need 2–3× the state size in RAM for workspace. Single precision (`precision="single"` in Aer) halves memory at a fidelity cost.
""",
            "code": """for n in [20, 25, 28, 30, 32]:
    print(f"statevector n={n}: {16*2**n/2**30:8.2f} GiB")
for n in [10, 12, 13, 14, 15]:
    print(f"density matrix n={n}: {16*4**n/2**30:8.2f} GiB")
""",
            "impact": "Before quoting 'we simulated it', ask how many qubits and which method. A 40-qubit 'simulation' claim is either MPS, a special structure, or a supercomputer.",
        },
        {
            "title": "Matrix product states: when they work and when they don't",
            "why": "Many circuits on many qubits are simulable when entanglement across cuts stays small. MPS stores the state as a chain of tensors with bond dimension χ; cost grows with χ, not 2ⁿ. Highly entangling circuits blow χ up and MPS loses its advantage.",
            "how": r"""
`AerSimulator(method="matrix_product_state")`. GHZ on 50 qubits has bond dimension 2: trivial for MPS, impossible as a statevector.
Random deep circuits saturate χ≈2^{n/2}: no gain. Truncation thresholds trade accuracy for speed; check them.
""",
            "code": """import time
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
n = 50
qc = QuantumCircuit(n); qc.h(0)
for i in range(n-1): qc.cx(i, i+1)
qc.measure_all()
sim = AerSimulator(method="matrix_product_state")
t0 = time.perf_counter(); c = sim.run(transpile(qc, sim), shots=200, seed_simulator=1).result().get_counts()
print(f"GHZ-50 via MPS in {time.perf_counter()-t0:.2f}s; outcomes: {sorted(set(c))[:2]}")
print(f"statevector would need {16*2**n/2**50:.0f} PiB")
""",
            "impact": "MPS is how you test wide-but-shallow finance circuits locally. It also explains why 'classically hard' claims need checking: low-entanglement circuits are not hard.",
        },
        {
            "title": "Practical limits on a laptop and choosing a method",
            "why": "Choosing the wrong simulator wastes hours or gives a false impression that a circuit is 'too big to check'.",
            "how": r"""
Decision table: exact amplitudes, n ≤ ~28 → statevector. Noise exact, n ≤ ~12 → density matrix. Noise approximate, n ≤ ~28 → statevector + trajectories (shots).
Wide, shallow or low-entanglement → MPS. Clifford-only → `method="stabilizer"` (thousands of qubits). Measure free RAM first.
""",
            "code": """from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
qc = QuantumCircuit(200); qc.h(0)
for i in range(199): qc.cx(i, i+1)
qc.measure_all()
sim = AerSimulator(method="stabilizer")
print("200-qubit Clifford GHZ via stabilizer:", sorted(sim.run(transpile(qc, sim), shots=20, seed_simulator=1).result().get_counts())[0][:10], "...")
""",
            "impact": "Picking the right method lets a consultant verify a vendor's circuit locally in minutes, which is cheap leverage in negotiations.",
        },
    ],
    "lens": {
        "look": "Before running: qubits, entanglement structure, noise needed, Clifford-only or not; predicted memory vs available RAM; chosen method and why.",
        "decision": "Which simulation method to use, or whether a claim of classical intractability is credible.",
        "justified": "Memory and time scale exponentially for generic methods; structure-aware methods change what is feasible.",
        "mistakes": [
            "Running density matrix for 16+ qubits on a laptop.",
            "Assuming MPS is always fast (deep random circuits defeat it).",
            "Forgetting workspace overhead beyond the state itself.",
            "Calling a circuit 'classically hard' because statevector fails, without trying MPS/stabilizer.",
            "Ignoring MPS truncation error.",
        ],
        "impact": "Hours lost to swapping; unverifiable pilot outputs; acceptance of inflated hardness claims.",
        "test": "Lab Q4: predict and measure memory/time for statevector up to ~22 qubits; run GHZ on MPS to 60 qubits; compare MPS on a deep random circuit.",
    },
    "claims": [
        {"id": "q4_mem", "tag": "M", "text": "A 20-qubit statevector held by Qiskit has 2^20 complex128 entries = 16 MiB.",
         "check": """from qiskit.quantum_info import Statevector
sv=Statevector.from_label('0'*20)
assert sv.data.nbytes==16*2**20"""},
        {"id": "q4_mps", "tag": "M", "text": "Aer's MPS method samples a 50-qubit GHZ state with only all-0 and all-1 outcomes.",
         "check": """from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
qc=QuantumCircuit(50); qc.h(0)
for i in range(49): qc.cx(i,i+1)
qc.measure_all(); s=AerSimulator(method='matrix_product_state')
assert set(s.run(transpile(qc,s),shots=100,seed_simulator=1).result().get_counts())<= {'0'*50,'1'*50}"""},
        {"id": "q4_aer_doc", "tag": "S", "text": "Aer simulation methods (statevector, density_matrix, matrix_product_state, stabilizer, …).",
         "source": {"title": "AerSimulator (Qiskit Aer API reference)", "publisher": "Qiskit Aer documentation", "date": "2026 (Aer 0.17 docs)", "url": "https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.AerSimulator.html"},
         "time_sensitive": True, "last_verified": "2026-10-19"},
    ],
    "lab": {
        "id": "q4_lab",
        "title": "Predict, then measure, simulation limits",
        "hypothesis": (
            "H1: statevector wall time from 14 to 22 qubits grows by ≥8× (≈2× per qubit, so ~256× ideal; overheads reduce small-n slope). "
            "H2: MPS runs GHZ-60 in under 30 s. H3: for a deep random 16-qubit circuit, MPS is slower than statevector."
        ),
        "thresholds": "H1 ratio ≥ 8; H2 < 30 s; H3 t_mps > t_sv.",
        "data": "Synthetic circuits; timings are your machine's.",
        "heavy": True,
        "code": r'''import time, numpy as np, pandas as pd
import plotly.graph_objects as go
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.random import random_circuit
from qiskit_aer import AerSimulator
from qlab_helpers import SEED, show, record, table

def layered(n, layers=4):
    qc = QuantumCircuit(n)
    for l in range(layers):
        for q in range(n): qc.ry(0.1*(q+1)*(l+1), q)
        for q in range(l % 2, n-1, 2): qc.cx(q, q+1)
    qc.save_statevector(); return qc
sv = AerSimulator(method="statevector")
rows = []
for n in range(14, 23, 2):
    qc = transpile(layered(n), sv)
    t0 = time.perf_counter(); sv.run(qc).result(); dt = time.perf_counter() - t0
    rows.append({"qubits": n, "predicted MiB": 16*2**n/2**20, "wall s": dt})
df = pd.DataFrame(rows); table(df.round(4), "Statevector cost")
fig = go.Figure([go.Scatter(x=df.qubits, y=df["wall s"], mode="lines+markers", name="wall time"), go.Scatter(x=df.qubits, y=df["predicted MiB"]/df["predicted MiB"].iloc[0]*df["wall s"].iloc[0], name="∝ 2ⁿ", line=dict(dash="dot"))])
fig.update_layout(yaxis_type="log", title="Statevector wall time vs qubits", xaxis_title="qubits"); show(fig)
record("sv_time_ratio_22_over_14", float(df["wall s"].iloc[-1]/df["wall s"].iloc[0]))
mps = AerSimulator(method="matrix_product_state")
g = QuantumCircuit(60); g.h(0)
for i in range(59): g.cx(i, i+1)
g.measure_all()
t0 = time.perf_counter(); mps.run(transpile(g, mps), shots=100, seed_simulator=SEED).result(); record("mps_ghz60_s", time.perf_counter() - t0)
rc = random_circuit(16, 30, max_operands=2, seed=SEED % 1000); rc.measure_all()
t0 = time.perf_counter(); mps.run(transpile(rc, mps, seed_transpiler=1), shots=50, seed_simulator=1).result(); t_mps = time.perf_counter() - t0
t0 = time.perf_counter(); sv.run(transpile(rc, sv, seed_transpiler=1), shots=50, seed_simulator=1).result(); t_sv = time.perf_counter() - t0
record("deep_random_mps_s", t_mps); record("deep_random_sv_s", t_sv)
print(df.to_string(index=False)); print(f"MPS deep random {t_mps:.2f}s vs SV {t_sv:.2f}s")
''',
        "expect": {"sv_time_ratio_22_over_14": "x >= 8", "mps_ghz60_s": "x < 30"},
        "report_hints": "H3 may fail on some machines: that is a finding. Explain why entanglement growth decides MPS cost.",
    },
    "quiz": [
        {"id": "q4q1", "type": "mc", "q": "Statevector memory for 30 qubits (complex128):", "options": ["1 GiB", "16 GiB", "256 GiB", "16 MiB"], "answer": 1, "explain": "16·2³⁰ B.", "tags": ["memory"]},
        {"id": "q4q2", "type": "mc", "q": "Density-matrix memory for 15 qubits:", "options": ["512 KiB", "16 MiB", "16 GiB", "1 TiB"], "answer": 2, "explain": "16·4¹⁵ B.", "tags": ["memory"]},
        {"id": "q4q3", "type": "mc", "q": "MPS cost is driven by:", "options": ["Number of qubits only", "Bond dimension (entanglement across cuts)", "Number of shots", "Basis gates"], "answer": 1, "explain": "χ.", "tags": ["mps"]},
        {"id": "q4q4", "type": "mc", "q": "GHZ-50 on MPS is:", "options": ["Impossible", "Easy (bond dimension 2)", "Requires a supercomputer", "Exact only with noise"], "answer": 1, "explain": "Low entanglement per cut.", "tags": ["mps"]},
        {"id": "q4q5", "type": "mc", "q": "Clifford-only circuit with 1,000 qubits:", "options": ["Statevector", "Density matrix", "Stabilizer method", "Can't simulate"], "answer": 2, "explain": "Gottesman–Knill.", "tags": ["methods"]},
        {"id": "q4q6", "type": "mc", "q": "Adding one qubit to a statevector simulation multiplies memory by:", "options": ["1", "2", "4", "n"], "answer": 1, "explain": "2ⁿ.", "tags": ["memory"]},
        {"id": "q4q7", "type": "mc", "q": "Adding one qubit to a density-matrix simulation multiplies memory by:", "options": ["2", "4", "8", "16"], "answer": 1, "explain": "4ⁿ.", "tags": ["memory"]},
        {"id": "q4q8", "type": "mc", "q": "A deep random 30-qubit circuit:", "options": ["Is easy with MPS", "Defeats MPS (χ saturates)", "Is Clifford", "Needs no simulation"], "answer": 1, "explain": "Entanglement grows.", "tags": ["mps"]},
        {"id": "q4q9", "type": "mc", "q": "Aer precision='single' does what?", "options": ["Doubles memory", "Halves memory with lower numerical precision", "Adds noise", "Uses GPU"], "answer": 1, "explain": "complex64.", "tags": ["memory"]},
        {"id": "q4q10", "type": "mc", "q": "'Our circuit can't be simulated classically' is credible only if:", "options": ["Statevector fails", "Structure-aware methods (MPS, stabilizer, tensor networks) also fail", "It uses >20 qubits", "The vendor says so"], "answer": 1, "explain": "Try the right methods.", "tags": ["methods"]},
        {"id": "q4q11", "type": "short", "q": "You need exact noisy results for a 14-qubit circuit on a 16 GB laptop. What do you do?",
         "must": [["4 gib", "4gib", "4 gb", "density"], ["trajector", "statevector", "shots", "sampl"]],
         "explain": "Density matrix needs 4 GiB (plus workspace), risky; use statevector with noise trajectories (shots) instead, or accept approximate results.", "tags": ["methods"]},
        {"id": "q4q12", "type": "short", "q": "Explain to a client why a 60-qubit GHZ simulation in seconds proves nothing about quantum advantage.",
         "must": [["entangle", "bond", "mps", "structure"], ["low", "simple", "easy"]],
         "explain": "GHZ has low entanglement per cut (MPS bond dimension 2); hardness requires high, unstructured entanglement.", "tags": ["mps"]},
    ],
    "exercise": {
        "id": "q4_ex",
        "title": "A simulation planner",
        "prompt": (
            "Implement:\n1. `sv_bytes(n)` and `dm_bytes(n)`.\n2. `max_qubits(ram_bytes, method, overhead=3)` → largest n whose state × overhead fits.\n"
            "3. `choose_method(n, noisy, clifford_only, low_entanglement, ram_bytes)` → one of 'stabilizer', 'density_matrix', 'statevector', 'matrix_product_state', 'infeasible', "
            "with priority: clifford_only → stabilizer; noisy and dm fits → density_matrix; sv fits → statevector; low_entanglement → matrix_product_state; else infeasible."
        ),
        "starter": '''def sv_bytes(n):
    raise NotImplementedError

def dm_bytes(n):
    raise NotImplementedError

def max_qubits(ram_bytes, method, overhead=3):
    raise NotImplementedError

def choose_method(n, noisy, clifford_only, low_entanglement, ram_bytes):
    raise NotImplementedError
''',
        "solution": '''def sv_bytes(n):
    return 16*2**n

def dm_bytes(n):
    return 16*4**n

def max_qubits(ram_bytes, method, overhead=3):
    f = sv_bytes if method == "statevector" else dm_bytes
    n = 0
    while f(n + 1)*overhead <= ram_bytes:
        n += 1
    return n

def choose_method(n, noisy, clifford_only, low_entanglement, ram_bytes):
    if clifford_only:
        return "stabilizer"
    if noisy and dm_bytes(n)*3 <= ram_bytes:
        return "density_matrix"
    if sv_bytes(n)*3 <= ram_bytes:
        return "statevector"
    if low_entanglement:
        return "matrix_product_state"
    return "infeasible"
''',
        "tests": '''GiB = 2**30

def test_bytes():
    assert sv_bytes(20) == 16*2**20 and dm_bytes(10) == 16*2**20

def test_max_qubits_16gb():
    assert max_qubits(16*GiB, "statevector") == 28
    assert max_qubits(16*GiB, "density_matrix") == 14

def test_choose():
    assert choose_method(500, False, True, False, 16*GiB) == "stabilizer"
    assert choose_method(10, True, False, False, 16*GiB) == "density_matrix"
    assert choose_method(20, True, False, False, 16*GiB) == "statevector"
    assert choose_method(60, False, False, True, 16*GiB) == "matrix_product_state"
    assert choose_method(60, False, False, False, 16*GiB) == "infeasible"
''',
    },
    "cards": [
        {"front": "Statevector memory", "back": "16·2ⁿ bytes (30 q ≈ 16 GiB)", "kind": "formula"},
        {"front": "Density matrix memory", "back": "16·4ⁿ bytes (15 q ≈ 16 GiB)", "kind": "formula"},
        {"front": "MPS cost driver", "back": "Bond dimension χ (entanglement across cuts)", "kind": "definition"},
        {"front": "Clifford-only simulation", "back": "Aer method='stabilizer', thousands of qubits", "kind": "definition"},
        {"front": "Max SV qubits, 16 GiB, 3× overhead", "back": "28", "kind": "number"},
        {"front": "Max DM qubits, 16 GiB, 3× overhead", "back": "14", "kind": "number"},
        {"front": "precision='single'", "back": "Halves memory; lower numerical accuracy", "kind": "definition"},
        {"front": "Mistake: hardness claim from SV failure", "back": "Try MPS/stabilizer/tensor networks first", "kind": "mistake"},
        {"front": "Mistake: MPS on deep random circuits", "back": "χ saturates; slower than statevector", "kind": "mistake"},
        {"front": "Noisy, too big for DM", "back": "Statevector + noise trajectories (shots)", "kind": "definition"},
    ],
    "defend": {
        "persona": "validator",
        "questions": [
            {"q": "How did you verify a 40-qubit circuit locally?",
             "must": [["mps", "matrix product", "stabilizer", "structure"], ["entangle", "bond", "clifford"]],
             "model": "MPS, valid because entanglement stays low (bond dimension checked), with truncation error reported."},
            {"q": "Why not density-matrix simulation for the noisy runs?",
             "must": [["4", "memory", "16"], ["trajector", "shots", "statevector"]], "model": "Memory 16·4ⁿ is prohibitive above ~13 qubits; I used noisy statevector trajectories."},
            {"q": "Vendor says it's classically intractable. Your view?",
             "must": [["structure", "mps", "tensor", "entangle"], ["try", "test", "check"]], "model": "Not until structure-aware simulators fail; I tested MPS/stabilizer."},
            {"q": "What is the largest exact statevector run you can do here?",
             "must": [["28", "27", "29", "30"], ["memory", "gib", "ram"]], "model": "About 28 qubits on 16 GiB with workspace overhead."},
            {"q": "Is MPS exact?",
             "must": [["truncat", "approximat", "threshold"], ["bond", "χ", "chi"]], "model": "Only without truncation; with truncation it's approximate, controlled by bond-dimension/threshold settings."},
        ],
    },
    "glossary": {
        "Matrix product state": "Tensor-chain representation efficient for low-entanglement states.",
        "Bond dimension": "Size of tensor links in an MPS; grows with entanglement.",
        "Stabilizer simulation": "Efficient simulation of Clifford circuits.",
        "Noise trajectories": "Sampling noisy evolutions with statevectors instead of density matrices.",
    },
}
