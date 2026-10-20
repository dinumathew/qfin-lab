MODULE = {
    "summary": (
        "Today's hardware is noisy, and noise compounds with circuit depth. This module models the main channels "
        "(depolarising, amplitude damping, phase damping, readout error), shows how errors accumulate with depth and "
        "width, and uses IBM's fake backends to see what a real device's noise does to a GHZ state. You will leave able "
        "to estimate, before running anything, whether a circuit is too deep to be meaningful on noisy hardware."
    ),
    "concepts": [
        {
            "title": "Noise channels: depolarising, amplitude damping, phase damping",
            "why": (
                "Real qubits interact with their environment. The result is a mixed state that a statevector cannot describe. "
                "Different physical mechanisms (energy loss, dephasing, random Pauli errors) damage different information, "
                "and mitigation methods (I10) assume specific channel shapes."
            ),
            "how": r"""
Channels act on density matrices via Kraus operators: $\rho\mapsto\sum_k K_k\rho K_k^\dagger$, $\sum K_k^\dagger K_k=I$.
* **Depolarising** ($p$): $\rho\mapsto(1-p)\rho+p\,I/2$ (single qubit). Uniform loss of information.
* **Amplitude damping** ($\gamma$): $|1\rangle\to|0\rangle$ with prob. $\gamma$; models $T_1$ energy relaxation, $\gamma=1-e^{-t/T_1}$.
* **Phase damping** ($\lambda$): destroys off-diagonal coherence, populations untouched; models $T_2$ dephasing.
* Two-qubit gates have error rates ~10× single-qubit ones on most current devices; they dominate. (Check a backend's properties; numbers change with each calibration.)
""",
            "code": """import numpy as np
from qiskit.quantum_info import DensityMatrix, Kraus
from qiskit_aer.noise import depolarizing_error, amplitude_damping_error, phase_damping_error
plus = DensityMatrix.from_label("+")
for name, err in [("depolarising p=0.2", depolarizing_error(0.2, 1)), ("amp damping g=0.2", amplitude_damping_error(0.2)), ("phase damping l=0.2", phase_damping_error(0.2))]:
    rho = plus.evolve(Kraus(err))
    print(f"{name:22s} populations {np.real(np.diag(rho.data)).round(3)}  coherence {abs(rho.data[0,1]):.3f}  purity {rho.purity().real:.3f}")
""",
            "impact": (
                "For a client, noise is the reason today's devices cannot run the circuits in I5–I7 at useful size. "
                "The question is not 'is there noise' but 'what is the probability the whole circuit runs without an error', "
                "which falls exponentially with gate count."
            ),
        },
        {
            "title": "Readout error and error accumulation with depth",
            "why": (
                "Even a perfect circuit is read through imperfect measurements; and every extra gate multiplies in another "
                "chance of error. A simple product rule gives a quick, conservative feasibility test you can do in your head."
            ),
            "how": r"""
* **Readout error**: $P(\text{read }1\mid 0)=e_0$, $P(\text{read }0\mid1)=e_1$. Confusion matrix $M$; observed $= M\cdot$ true. Mitigation inverts $M$ (I10).
* **Success heuristic**: $P_{\text{no error}}\approx\prod_g(1-\epsilon_g)\approx e^{-\sum_g\epsilon_g}$. With $N_2$ two-qubit gates at error $\epsilon_2$:
  $P\approx(1-\epsilon_2)^{N_2}$. For $\epsilon_2=10^{-3}$ and the ~620-CX pricing toy (I5): $P\approx0.54$. For ~3,000 CX: $\approx0.05$. {{c:b5_product}}
* Rule of thumb for meaningful output without heavy mitigation: $N_2\epsilon_2\lesssim 0.1$, i.e. **max error per CX ≈ 0.1 / (CX count)** (Capstone 1).
""",
            "code": """import numpy as np
for e2 in [1e-2, 1e-3, 1e-4]:
    print(f"eps_2q={e2:.0e}: " + ", ".join(f"{n} CX -> {(1-e2)**n:.3f}" for n in [100, 620, 1467, 3041]))
print("max error per CX for 90% success at 620 CX:", 0.1/620)
""",
            "impact": (
                "This one-line calculation is what you put in front of a CRO when a vendor proposes running a pricing oracle on "
                "today's hardware: at 10⁻³ per two-qubit gate, a ~3,000-CX credit circuit succeeds about 5% of the time "
                "before any mitigation. That settles 'production on NISQ' quickly."
            ),
        },
        {
            "title": "Noise models from fake backends",
            "why": (
                "IBM's fake backends package snapshot calibration data (error rates, T1/T2, readout errors, coupling maps) of real "
                "devices. They let you emulate realistic noise locally, including the SWAPs forced by limited connectivity, "
                "without QPU time."
            ),
            "how": r"""
```python
from qiskit_ibm_runtime.fake_provider import FakeTorino
sim = AerSimulator.from_backend(FakeTorino())          # noise model + coupling map + basis
t = transpile(qc, sim, seed_transpiler=1)               # routing to the device's connectivity
counts = sim.run(t, shots=4000, seed_simulator=1).result().get_counts()
```
Snapshot data are historical, not today's device. Use fake backends for *relative* comparisons (deeper vs shallower, layout A vs B), not as forecasts of today's hardware. {{c:b5_fake_doc}}
""",
            "code": """from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit_ibm_runtime.fake_provider import FakeManilaV2
b = FakeManilaV2(); sim = AerSimulator.from_backend(b)
qc = QuantumCircuit(3); qc.h(0); qc.cx(0, 1); qc.cx(1, 2); qc.measure_all()
t = transpile(qc, sim, seed_transpiler=1)
c = sim.run(t, shots=4000, seed_simulator=1).result().get_counts()
print("backend:", b.name, "| P(000)+P(111) =", (c.get('000',0)+c.get('111',0))/4000)
print(dict(sorted(c.items(), key=lambda kv: -kv[1])[:5]))
""",
            "impact": "Fake-backend emulation is how you price a hardware experiment before buying it: if the emulated result is noise-dominated, do not spend QPU budget on it.",
        },
    ],
    "lens": {
        "look": "Count two-qubit gates after routing; multiply by error rates; compare noisy-emulated outputs with ideal; check fidelity or a proxy against width and depth.",
        "decision": "Whether a circuit is runnable on a given hardware generation with meaningful output, and therefore whether to buy QPU time.",
        "justified": "Success probability decays roughly exponentially with gate count; a cheap pre-calculation avoids expensive, uninformative runs.",
        "mistakes": [
            "Counting gates before routing (SWAPs add CX on limited connectivity).",
            "Treating fake-backend snapshots as today's device performance.",
            "Using P(000)+P(111) as GHZ fidelity: it is an upper-bound proxy; true fidelity needs coherence (parity) measurements.",
            "Ignoring readout error in small-probability estimates (tail risk!).",
            "Believing mitigation removes the exponential decay (it trades it for sampling cost, I10).",
        ],
        "impact": "Wasted QPU spend; tail probabilities dominated by readout error; overstated hardware readiness in client materials.",
        "test": "Lab B5: GHZ fidelity vs qubit count with an ideal simulator, a depolarising model (exact fidelity), and a fake-backend noise model (population proxy).",
    },
    "claims": [
        {"id": "b5_product", "tag": "M", "text": "(1 − 1e-3)^620 ≈ 0.54 and (1 − 1e-3)^3041 ≈ 0.048.",
         "check": "assert abs((1-1e-3)**620-0.538)<0.005 and abs((1-1e-3)**3041-0.0477)<0.002"},
        {"id": "b5_fake_doc", "tag": "S", "text": "Fake backends in qiskit_ibm_runtime.fake_provider carry snapshot noise and coupling data of IBM devices for local simulation.",
         "source": {"title": "Fake backends (qiskit-ibm-runtime fake_provider)", "publisher": "IBM Quantum documentation", "date": "2026 (qiskit-ibm-runtime docs)", "url": "https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/fake-provider"},
         "time_sensitive": True, "last_verified": "2026-10-19"},
        {"id": "b5_monotone", "tag": "M", "text": "Under a 1% two-qubit depolarising model, exact GHZ fidelity falls monotonically from 2 to 6 qubits.",
         "check": """from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Statevector, state_fidelity
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error
nm=NoiseModel(); nm.add_all_qubit_quantum_error(depolarizing_error(0.01,2),['cx'])
sim=AerSimulator(method='density_matrix',noise_model=nm); f=[]
for n in range(2,7):
    qc=QuantumCircuit(n); qc.h(0); [qc.cx(i,i+1) for i in range(n-1)]
    ideal=Statevector(qc); q=qc.copy(); q.save_density_matrix()
    f.append(state_fidelity(sim.run(transpile(q,sim,optimization_level=0)).result().data()['density_matrix'],ideal))
assert all(a>b for a,b in zip(f,f[1:])), f"""},
    ],
    "lab": {
        "id": "b5_lab",
        "title": "GHZ fidelity against qubit count, with and without noise",
        "hypothesis": (
            "H1: ideal GHZ fidelity is 1 (to 1e-9) for n = 2..8. "
            "H2: with 1% two-qubit depolarising noise (p=0.01), exact fidelity at n=6 is within 0.002 of the stabiliser-counting prediction "
            "(1−0.75p)(1−0.875p)^(n−2): the first CX acts on a Bell pair (4 of 16 Paulis are harmless: II, XX, YY, ZZ), later CXs only have II and ZZ harmless. "
            "H3: on the FakeTorino noise model, the population proxy P(0…0)+P(1…1) falls from n=2 to n=8."
        ),
        "thresholds": "H1 1e-9; H2 |exact − prediction| < 0.002 at n=6; H3 proxy(8) < proxy(2).",
        "data": "Ideal and noisy simulation. FakeTorino calibration snapshot shipped with qiskit-ibm-runtime (historical, not live).",
        "heavy": True,
        "code": r'''import numpy as np, pandas as pd
import plotly.graph_objects as go
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Statevector, state_fidelity
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error
from qiskit_ibm_runtime.fake_provider import FakeTorino
from qlab_helpers import SEED, show, record, table

def ghz(n):
    qc = QuantumCircuit(n); qc.h(0)
    for i in range(n-1): qc.cx(i, i+1)
    return qc
nm = NoiseModel(); nm.add_all_qubit_quantum_error(depolarizing_error(0.01, 2), ["cx"])
dm_noisy = AerSimulator(method="density_matrix", noise_model=nm)
dm_ideal = AerSimulator(method="density_matrix")
fake = AerSimulator.from_backend(FakeTorino())
rows = []
for n in range(2, 9):
    ideal = Statevector(ghz(n))
    q = ghz(n); q.save_density_matrix()
    f_ideal = state_fidelity(dm_ideal.run(transpile(q, dm_ideal, optimization_level=0)).result().data()["density_matrix"], ideal) if n <= 8 else np.nan
    f_dep = state_fidelity(dm_noisy.run(transpile(q, dm_noisy, optimization_level=0)).result().data()["density_matrix"], ideal) if n <= 7 else np.nan
    m = ghz(n); m.measure_all()
    t = transpile(m, fake, seed_transpiler=SEED, optimization_level=1)
    c = fake.run(t, shots=4000, seed_simulator=SEED).result().get_counts()
    proxy = (c.get("0"*n, 0) + c.get("1"*n, 0))/4000
    twoq = sum(v for k, v in t.count_ops().items() if k in ("cx", "cz", "ecr"))
    rows.append({"n": n, "ideal fidelity": f_ideal, "depol 1% exact fidelity": f_dep,
                 "prediction (1-.75p)(1-.875p)^(n-2)": (1-0.75*0.01)*(1-0.875*0.01)**(n-2), "naive (1-p)^(n-1)": 0.99**(n-1), "FakeTorino population proxy": proxy, "2q gates after routing": twoq})
df = pd.DataFrame(rows); table(df.round(4), "GHZ fidelity vs width")
fig = go.Figure()
for col in ["ideal fidelity", "depol 1% exact fidelity", "prediction (1-.75p)(1-.875p)^(n-2)", "naive (1-p)^(n-1)", "FakeTorino population proxy"]:
    fig.add_trace(go.Scatter(x=df.n, y=df[col], mode="lines+markers", name=col))
fig.update_layout(title="GHZ state quality vs number of qubits", xaxis_title="qubits", yaxis_title="fidelity / proxy", yaxis_range=[0, 1.05])
show(fig)
record("max_ideal_dev", float((1 - df["ideal fidelity"]).abs().max()))
r6 = df[df.n == 6].iloc[0]
record("h2_gap_n6", float(abs(r6["depol 1% exact fidelity"] - r6["prediction (1-.75p)(1-.875p)^(n-2)"])))
record("proxy_n2", float(df.loc[df.n == 2, "FakeTorino population proxy"].item()))
record("proxy_n8", float(df.loc[df.n == 8, "FakeTorino population proxy"].item()))
''',
        "expect": {"max_ideal_dev": "x < 1e-9", "h2_gap_n6": "x < 0.002", "proxy_n8": "x < 0.95"},
        "report_hints": "Discuss why the population proxy overstates fidelity and what an honest fidelity measurement would need. Translate: at what CX count does this device's output become noise?",
    },
    "quiz": [
        {"id": "b5q1", "type": "mc", "q": "Amplitude damping models:", "options": ["Dephasing (T2)", "Energy relaxation |1⟩→|0⟩ (T1)", "Readout error", "Crosstalk"], "answer": 1, "explain": "T1 decay.", "tags": ["channels"]},
        {"id": "b5q2", "type": "mc", "q": "Phase damping changes:", "options": ["Populations", "Off-diagonal coherences", "Both equally", "Nothing"], "answer": 1, "explain": "Destroys coherence only.", "tags": ["channels"]},
        {"id": "b5q3", "type": "mc", "q": "With 2-qubit error 1e-3 and 3,000 CX, P(no error) ≈", "options": ["0.97", "0.5", "0.05", "0.0001"], "answer": 2, "explain": "e^{-3} ≈ 0.05.", "tags": ["accumulation"]},
        {"id": "b5q4", "type": "mc", "q": "Max error per CX for ~90% success on a 1,467-CX circuit:", "options": ["~1e-2", "~7e-5", "~1e-3", "~1e-6"], "answer": 1, "explain": "0.1/1467 ≈ 6.8e-5.", "tags": ["accumulation"]},
        {"id": "b5q5", "type": "mc", "q": "Fake backends provide:", "options": ["Live device calibrations", "Snapshot calibration and coupling data for local simulation", "Hardware access", "Error-corrected qubits"], "answer": 1, "explain": "Historical snapshots.", "tags": ["fake"]},
        {"id": "b5q6", "type": "mc", "q": "P(0…0)+P(1…1) for a noisy GHZ state is:", "options": ["Exactly the fidelity", "An upper-bound proxy; coherence also needed", "A lower bound", "Unrelated"], "answer": 1, "explain": "Fidelity = (populations + coherences)/2-type expression; proxy ignores coherence.", "tags": ["fidelity"]},
        {"id": "b5q7", "type": "mc", "q": "Why do CX counts increase after transpiling to a real backend?", "options": ["Noise", "SWAPs for limited connectivity", "Measurement", "Optimisation level 0"], "answer": 1, "explain": "Routing.", "tags": ["routing"]},
        {"id": "b5q8", "type": "mc", "q": "Single-qubit depolarising channel with parameter p:", "options": ["ρ → (1−p)ρ + p I/2", "ρ → pρ", "ρ → ρ + p", "ρ → XρX"], "answer": 0, "explain": "Mix toward maximally mixed.", "tags": ["channels"]},
        {"id": "b5q9", "type": "mc", "q": "Readout error matters most for estimating:", "options": ["Probabilities near 0.5", "Small tail probabilities", "Phases", "Gate counts"], "answer": 1, "explain": "A 1% misread swamps a 0.1% tail.", "tags": ["readout"]},
        {"id": "b5q10", "type": "mc", "q": "Which gate type typically dominates error budgets today?", "options": ["Single-qubit rotations", "Two-qubit gates", "Measurements only", "Barriers"], "answer": 1, "explain": "~10× worse than 1q gates on most devices.", "tags": ["accumulation"]},
        {"id": "b5q11", "type": "short", "q": "A vendor proposes running a 3,000-CX credit oracle on current hardware. Give the one-line feasibility check.",
         "must": [["(1", "product", "exp", "e^"], ["0.05", "5%", "five percent", "1e-3", "10^-3"]],
         "explain": "(1−ε)^N ≈ e^{−Nε}; at ε=1e-3, N=3,000 → ≈5% success before mitigation.", "tags": ["accumulation"]},
        {"id": "b5q12", "type": "short", "q": "Why are fake-backend results not forecasts of today's device?",
         "must": [["snapshot", "historical", "past", "old"], ["calibrat", "change", "drift"]],
         "explain": "They encode a historical calibration snapshot; real devices drift and are recalibrated.", "tags": ["fake"]},
    ],
    "exercise": {
        "id": "b5_ex",
        "title": "Noise arithmetic and a readout model",
        "prompt": (
            "Implement:\n1. `p_success(counts, errors)` where counts and errors are dicts by gate name → ∏(1−e)^n.\n"
            "2. `max_error_per_gate(n_gates, target=0.9)` → largest uniform error ε with (1−ε)^n ≥ target.\n"
            "3. `readout_matrix(e0, e1)` → 2×2 confusion matrix M with columns = true state, rows = observed.\n"
            "4. `apply_readout(p_true, e0, e1)` → observed distribution for a single qubit.\n"
            "5. `noisy_ghz_proxy(n, p2, shots, seed)` → P(0…0)+P(1…1) using a NoiseModel with depolarising_error(p2, 2) on 'cx' and AerSimulator."
        ),
        "starter": '''import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error

def p_success(counts, errors):
    raise NotImplementedError

def max_error_per_gate(n_gates, target=0.9):
    raise NotImplementedError

def readout_matrix(e0, e1):
    raise NotImplementedError

def apply_readout(p_true, e0, e1):
    raise NotImplementedError

def noisy_ghz_proxy(n, p2, shots, seed):
    raise NotImplementedError
''',
        "solution": '''import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error

def p_success(counts, errors):
    p = 1.0
    for g, n in counts.items():
        p *= (1 - errors.get(g, 0.0))**n
    return p

def max_error_per_gate(n_gates, target=0.9):
    return 1 - target**(1/n_gates)

def readout_matrix(e0, e1):
    return np.array([[1 - e0, e1], [e0, 1 - e1]])

def apply_readout(p_true, e0, e1):
    return readout_matrix(e0, e1) @ np.asarray(p_true, dtype=float)

def noisy_ghz_proxy(n, p2, shots, seed):
    nm = NoiseModel(); nm.add_all_qubit_quantum_error(depolarizing_error(p2, 2), ["cx"])
    sim = AerSimulator(noise_model=nm)
    qc = QuantumCircuit(n); qc.h(0)
    for i in range(n - 1):
        qc.cx(i, i + 1)
    qc.measure_all()
    c = sim.run(transpile(qc, sim, optimization_level=0), shots=shots, seed_simulator=seed).result().get_counts()
    return (c.get("0"*n, 0) + c.get("1"*n, 0))/shots
''',
        "tests": '''import numpy as np

def test_p_success():
    assert abs(p_success({"cx": 620}, {"cx": 1e-3}) - 0.999**620) < 1e-12
    assert abs(p_success({"cx": 10, "sx": 100}, {"cx": 1e-2, "sx": 1e-4}) - 0.99**10*0.9999**100) < 1e-12

def test_max_error():
    e = max_error_per_gate(620)
    assert abs((1 - e)**620 - 0.9) < 1e-9 and 1.6e-4 < e < 1.75e-4

def test_readout():
    M = readout_matrix(0.02, 0.05)
    assert np.allclose(M.sum(axis=0), 1)
    assert np.allclose(apply_readout([1, 0], 0.02, 0.05), [0.98, 0.02])

def test_ghz_proxy_monotone():
    a = noisy_ghz_proxy(2, 0.02, 4000, 1); b = noisy_ghz_proxy(6, 0.02, 4000, 1)
    assert 0.9 < a <= 1.0 and b < a
''',
    },
    "cards": [
        {"front": "Depolarising channel (1 qubit)", "back": "ρ → (1−p)ρ + p I/2", "kind": "formula"},
        {"front": "Amplitude damping", "back": "T1 energy relaxation |1⟩→|0⟩; γ = 1 − e^{−t/T1}", "kind": "definition"},
        {"front": "Phase damping", "back": "T2 dephasing; kills coherences, not populations", "kind": "definition"},
        {"front": "Success heuristic", "back": "P ≈ (1−ε₂)^{N₂} ≈ e^{−N₂ε₂}", "kind": "formula"},
        {"front": "Max error per CX for ~90% success", "back": "≈ 0.1 / CX count", "kind": "formula"},
        {"front": "(1−1e-3)^620", "back": "≈ 0.54", "kind": "number"},
        {"front": "(1−1e-3)^3041", "back": "≈ 0.05", "kind": "number"},
        {"front": "Readout confusion matrix", "back": "observed = M · true; columns sum to 1", "kind": "formula"},
        {"front": "Fake backends", "back": "Snapshot noise + coupling for local emulation; not live", "kind": "definition"},
        {"front": "Mistake: GHZ populations = fidelity", "back": "Populations are an upper-bound proxy; need coherence too", "kind": "mistake"},
        {"front": "Mistake: counting before routing", "back": "SWAPs add CX on limited connectivity", "kind": "mistake"},
    ],
    "defend": {
        "persona": "cro",
        "questions": [
            {"q": "Why can't we run the pricing circuit on today's machines?",
             "must": [["noise", "error"], ["cx", "gate", "depth"], ["exponential", "product", "(1", "probability"]],
             "model": "Each two-qubit gate has ~1e-3 error; success probability decays like (1−ε)^N, so a few thousand gates leaves little signal."},
            {"q": "What error rate would we need?",
             "must": [["0.1", "divide", "/"], ["cx", "gate count"]], "model": "About 0.1 divided by the CX count for ~90% success, e.g. ~1.6e-4 per CX for 620 CX."},
            {"q": "Isn't error mitigation enough?",
             "must": [["sampling", "shots", "cost", "overhead"], ["exponential", "scale", "deep"]], "model": "Mitigation trades error for sampling overhead that grows exponentially with circuit size; it does not scale to deep finance circuits (I10)."},
            {"q": "You ran it on a 'Fake' backend. Is that today's device?",
             "must": [["snapshot", "historical"], ["relative", "comparison", "not"]], "model": "No; it's a historical calibration snapshot, useful for relative comparisons, not forecasts."},
            {"q": "Which of our numbers are most sensitive to readout error?",
             "must": [["tail", "small probabilit", "var", "default"]], "model": "Small tail probabilities (default, VaR exceedance); a 1% misread can swamp them."},
        ],
    },
    "glossary": {
        "Depolarising noise": "Random Pauli errors mixing the state toward maximally mixed.",
        "Amplitude damping": "Energy relaxation channel (T1).",
        "Phase damping": "Dephasing channel (T2).",
        "Readout error": "Misclassification of measurement outcomes.",
        "Fake backend": "Local snapshot of a device's noise and connectivity.",
        "Routing": "Inserting SWAPs to satisfy hardware connectivity.",
        "Kraus operators": "Matrices defining a quantum channel.",
    },
}
