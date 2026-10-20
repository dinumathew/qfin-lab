MODULE = {
    "summary": (
        "This is the working API for every later lab: build a `QuantumCircuit`, `transpile` it to a basis with a fixed "
        "seed, simulate it exactly (statevector, density matrix) with Aer, and run it through the V2 primitives "
        "(`SamplerV2` for counts, `EstimatorV2` for expectation values), reading their results correctly, including "
        "parameter sweeps with array broadcasting. Code here targets Qiskit 2.6 and Aer 0.17."
    ),
    "concepts": [
        {
            "title": "QuantumCircuit and transpile",
            "why": (
                "The circuit you write is not the circuit that runs. `transpile` rewrites it into a target's basis gates and "
                "connectivity, optimises, and introduces seed-dependent choices. Every resource count and every hardware job "
                "goes through it."
            ),
            "how": r"""
```python
qc = QuantumCircuit(n)                     # optionally classical bits
qc.h(0); qc.cx(0, 1); qc.measure_all()     # measure_all adds a 'meas' register
t = transpile(qc, basis_gates=["cx","rz","sx","x"], optimization_level=1, seed_transpiler=7)
t = transpile(qc, backend=fake_backend, optimization_level=2, seed_transpiler=7)   # adds layout/routing
```
`optimization_level` 0–3 trades compile time for gate reduction (2 is the default in recent Qiskit releases; check yours). Inspect with `t.count_ops()`, `t.depth()`,
`t.num_nonlocal_gates()`, `t.draw()`. Parameters (`Parameter('θ')`) stay symbolic through transpilation, so you transpile once and bind many values.
""",
            "code": """from qiskit import QuantumCircuit, transpile
from qiskit.circuit import Parameter
th = Parameter("θ")
qc = QuantumCircuit(3); qc.ry(th, 0); qc.cx(0, 1); qc.cx(1, 2); qc.measure_all()
t = transpile(qc, basis_gates=["cx", "rz", "sx", "x"], optimization_level=1, seed_transpiler=7)
print(t.count_ops(), "depth", t.depth(), "| params:", t.parameters)
""",
            "impact": "Transpilation is where counts, depth and therefore cost are decided. A client resource estimate that does not state basis, optimisation level and seed is not reproducible and should not be accepted.",
        },
        {
            "title": "Aer simulators: statevector and density matrix",
            "why": (
                "Exact simulation is your reference. Statevector gives amplitudes for pure, noiseless circuits; density matrix "
                "handles noise and mixed states exactly but costs the square of the memory. Choosing correctly decides whether "
                "a 20-qubit check takes seconds or exhausts your laptop (Track Q4)."
            ),
            "how": r"""
* `Statevector(qc)` (qiskit.quantum_info): exact, no measurement, quick for small $n$.
* `AerSimulator(method="statevector")` with `qc.save_statevector()`: same, faster for larger $n$, supports noise via trajectories.
* `AerSimulator(method="density_matrix")` with `qc.save_density_matrix()`: exact mixed-state evolution; memory $16\cdot4^n$ bytes.
* Purity $\mathrm{Tr}\rho^2$ tells you how much noise has mixed the state (1 = pure).
""",
            "code": """from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
qc = QuantumCircuit(2); qc.h(0); qc.cx(0, 1)
a = qc.copy(); a.save_statevector()
sv = AerSimulator(method="statevector").run(transpile(a, AerSimulator())).result().get_statevector()
b = qc.copy(); b.save_density_matrix()
dm = AerSimulator(method="density_matrix").run(transpile(b, AerSimulator())).result().data()["density_matrix"]
print(sv.probabilities().round(3), "| purity", round(dm.purity().real, 6))
""",
            "impact": "Exact references at toy size are what convert 'it looks right' into 'it is right'. They are the implementation tests behind every pilot result.",
        },
        {
            "title": "Primitives V2: SamplerV2 and EstimatorV2",
            "why": (
                "IBM's runtime and Aer expose the same V2 interface, so code written against the primitives runs on the "
                "simulator today and on hardware later. The older `execute()` and V1 primitives are gone (Track Q1). Misreading "
                "V2 results (shapes, registers, broadcasting) is a common source of wrong numbers."
            ),
            "how": r"""
* **PUBs** (primitive unified blocs): Sampler `(circuit, parameter_values)`; Estimator `(circuit, observables, parameter_values)`.
* `SamplerV2(seed=s).run([pub], shots=N).result()[0].data.<register_name>`: a `BitArray`; `.get_counts()`; with `measure_all` the register is `meas`.
  For a parameter array of shape $(k,1)$, `data.meas` has shape $(k,)$ and `data.meas[i].get_counts()` is the $i$-th point.
* `EstimatorV2().run([(qc, obs, vals)], precision=p).result()[0].data.evs` and `.stds`. Observables and parameter arrays **broadcast** like NumPy:
  obs shape $(2,1)$ × params $(5,1)$ → evs shape $(2,5)$. Aer's EstimatorV2 with `precision=0` (default) returns exact values; set `precision` to emulate shot noise.
""",
            "code": """import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.quantum_info import SparsePauliOp
from qiskit_aer.primitives import SamplerV2, EstimatorV2
th = Parameter("θ"); qc = QuantumCircuit(2); qc.ry(th, 0); qc.cx(0, 1)
vals = np.linspace(0, np.pi, 5).reshape(-1, 1)
evs = EstimatorV2().run([(qc, [[SparsePauliOp("ZZ")], [SparsePauliOp("IZ")]], vals)]).result()[0].data.evs
print("evs shape", evs.shape, "\\n", evs.round(3))
m = qc.copy(); m.measure_all()
res = SamplerV2(seed=1).run([(m, vals)], shots=1000).result()[0].data.meas
print("sampler shape", res.shape, "| point 2 counts:", res[2].get_counts())
""",
            "impact": (
                "Writing to the primitives makes a pilot portable from emulator to hardware without rewriting, and the V2 "
                "result objects carry the metadata a validator needs. That shortens the path from prototype to a controlled test."
            ),
        },
    ],
    "lens": {
        "look": "For each run: circuit → transpiled circuit (basis, level, seed) → simulator method or primitive → result object shape and register → numbers with standard errors.",
        "decision": "Which execution path (exact statevector, density matrix, sampler, estimator) is the right reference for a given test, and whether outputs agree across paths.",
        "justified": "Cross-path agreement (exact vs sampled vs estimated) is the strongest cheap evidence that the implementation is right.",
        "mistakes": [
            "Using `execute()` or V1 primitive code from old tutorials (removed).",
            "Reading `data.c` when `measure_all` named the register `meas` (or vice versa).",
            "Wrong broadcasting shapes in Estimator PUBs, silently computing the wrong grid or raising errors.",
            "Forgetting that Aer's EstimatorV2 is exact by default and claiming its output includes shot noise.",
            "Re-transpiling inside a parameter loop instead of binding parameters on one transpiled circuit.",
        ],
        "impact": "Wrong numbers from mis-read result objects; slow, unreproducible sweeps; code that cannot move to hardware.",
        "test": "Lab B4: run one parameterised circuit through five execution paths and reconcile them within stated tolerances.",
    },
    "claims": [
        {"id": "b4_est_exact", "tag": "M", "text": "Aer EstimatorV2 without precision returns the exact expectation (⟨Z₀⟩ = cos θ for RY(θ) on qubit 0) to 1e-9.",
         "check": """import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp
from qiskit_aer.primitives import EstimatorV2
qc=QuantumCircuit(1); qc.ry(0.7,0)
ev=EstimatorV2().run([(qc,SparsePauliOp('Z'))]).result()[0].data.evs
assert abs(float(ev)-np.cos(0.7))<1e-9"""},
        {"id": "b4_primitives_doc", "tag": "S", "text": "Qiskit primitives V2 interface (PUBs, BitArray, broadcasting).",
         "source": {"title": "Primitives (Qiskit SDK guide)", "publisher": "IBM Quantum documentation", "date": "2026 (Qiskit 2.x docs)", "url": "https://quantum.cloud.ibm.com/docs/en/guides/primitives"},
         "time_sensitive": True, "last_verified": "2026-10-19"},
    ],
    "lab": {
        "id": "b4_lab",
        "title": "Five execution paths, one answer",
        "hypothesis": (
            "H1: for RY(θ)+CNOT over 9 values of θ, P('11') from Statevector, Aer statevector, Aer density matrix agree to 1e-9. "
            "H2: SamplerV2 at 8,000 shots agrees within 4 SE at every θ. H3: EstimatorV2 ⟨Z₁Z₀⟩ equals 1 and ⟨Z₀⟩ equals cos θ to 1e-9."
        ),
        "thresholds": "1e-9 exact paths; 4 SE sampled.",
        "data": "Synthetic parameterised circuit; ideal simulation.",
        "code": r'''import numpy as np, pandas as pd
import plotly.graph_objects as go
from qiskit import QuantumCircuit, transpile
from qiskit.circuit import Parameter
from qiskit.quantum_info import Statevector, SparsePauliOp
from qiskit_aer import AerSimulator
from qiskit_aer.primitives import SamplerV2, EstimatorV2
from qlab_helpers import SEED, show, record, table

th = Parameter("θ"); qc = QuantumCircuit(2); qc.ry(th, 0); qc.cx(0, 1)
thetas = np.linspace(0, np.pi, 9)
sv_sim, dm_sim = AerSimulator(method="statevector"), AerSimulator(method="density_matrix")
rows = []
for t in thetas:
    b = qc.assign_parameters({th: t})
    p_ref = Statevector(b).probabilities_dict().get("11", 0.0)
    a = b.copy(); a.save_statevector()
    p_sv = sv_sim.run(transpile(a, sv_sim, seed_transpiler=SEED)).result().get_statevector().probabilities_dict().get("11", 0.0)
    d = b.copy(); d.save_density_matrix()
    p_dm = dm_sim.run(transpile(d, dm_sim, seed_transpiler=SEED)).result().data()["density_matrix"].probabilities_dict().get("11", 0.0)
    rows.append({"theta": t, "exact": p_ref, "aer_sv": p_sv, "aer_dm": p_dm})
df = pd.DataFrame(rows)
m = qc.copy(); m.measure_all()
bits = SamplerV2(seed=SEED).run([(m, thetas.reshape(-1, 1))], shots=8000).result()[0].data.meas
df["sampler"] = [bits[i].get_counts().get("11", 0)/8000 for i in range(len(thetas))]
df["z_sampler"] = (df.sampler - df.exact)/np.sqrt(np.clip(df.exact*(1-df.exact), 1e-12, None)/8000)
df.loc[(df.exact < 1e-12) | (df.exact > 1-1e-12), "z_sampler"] = 0.0
evs = EstimatorV2().run([(qc, [[SparsePauliOp("ZZ")], [SparsePauliOp("IZ")]], thetas.reshape(-1, 1))]).result()[0].data.evs
df["<ZZ>"] = evs[0]; df["<Z0>"] = evs[1]
table(df.round(6), "Agreement across execution paths")
fig = go.Figure([go.Scatter(x=df.theta, y=df.exact, name="exact P(11)"), go.Scatter(x=df.theta, y=df.sampler, mode="markers", name="SamplerV2, 8000 shots"),
                 go.Scatter(x=df.theta, y=df["<Z0>"], name="EstimatorV2 <Z0>", line=dict(dash="dot"))])
fig.update_layout(title="RY(θ)+CNOT", xaxis_title="θ"); show(fig)
record("max_exact_dev", float(max((df.aer_sv-df.exact).abs().max(), (df.aer_dm-df.exact).abs().max())))
record("max_abs_z_sampler", float(df.z_sampler.abs().max()))
record("estimator_dev", float(max(np.abs(evs[0]-1).max(), np.abs(evs[1]-np.cos(thetas)).max())))
''',
        "expect": {"max_exact_dev": "x < 1e-9", "max_abs_z_sampler": "x < 4", "estimator_dev": "x < 1e-9"},
        "report_hints": "Explain why exact agreement across three simulators is an implementation test, and what it does not show (noise behaviour, value).",
    },
    "quiz": [
        {"id": "b4q1", "type": "mc", "q": "In Qiskit 2.x, how do you run a circuit on Aer and get counts?", "options": ["execute(qc, backend)", "SamplerV2().run([qc]).result()[0].data.meas.get_counts()", "qc.run()", "Aer.get_backend('qasm_simulator').execute(qc)"], "answer": 1, "explain": "execute() was removed in 1.0.", "tags": ["api"]},
        {"id": "b4q2", "type": "mc", "q": "With qc.measure_all(), the SamplerV2 result register is named:", "options": ["c", "meas", "cr", "bits"], "answer": 1, "explain": "measure_all creates 'meas'.", "tags": ["api"]},
        {"id": "b4q3", "type": "mc", "q": "Observables of shape (2,1) and parameter values of shape (5,1) give evs of shape:", "options": ["(5,)", "(2,)", "(2,5)", "error"], "answer": 2, "explain": "NumPy broadcasting.", "tags": ["broadcasting"]},
        {"id": "b4q4", "type": "mc", "q": "Aer's EstimatorV2 with default options returns:", "options": ["Shot-noise estimates at 1024 shots", "Exact expectation values", "Hardware results", "Counts"], "answer": 1, "explain": "precision=0 → exact; set precision to emulate sampling.", "tags": ["estimator"]},
        {"id": "b4q5", "type": "mc", "q": "Density-matrix simulation memory for n qubits scales as:", "options": ["16·2ⁿ bytes", "16·4ⁿ bytes", "n² bytes", "2ⁿ bytes"], "answer": 1, "explain": "Squared dimension, complex128.", "tags": ["simulators"]},
        {"id": "b4q6", "type": "mc", "q": "To sweep 1,000 parameter values efficiently you should:", "options": ["Transpile 1,000 times", "Transpile once with symbolic Parameters, then pass a values array in the PUB", "Use 1,000 separate circuits with hard-coded angles", "Use execute()"], "answer": 1, "explain": "Bind at run time.", "tags": ["api"]},
        {"id": "b4q7", "type": "mc", "q": "Which result attribute gives the Estimator's standard errors?", "options": ["data.std", "data.stds", "metadata.errors", "data.var"], "answer": 1, "explain": "evs and stds.", "tags": ["estimator"]},
        {"id": "b4q8", "type": "mc", "q": "A density-matrix purity of 1 means:", "options": ["The state is mixed", "The state is pure (no decoherence)", "The circuit failed", "Measurement happened"], "answer": 1, "explain": "Tr ρ² = 1.", "tags": ["simulators"]},
        {"id": "b4q9", "type": "mc", "q": "seed_transpiler affects:", "options": ["Shot sampling", "Stochastic layout/routing/optimisation choices", "Noise model", "Estimator precision"], "answer": 1, "explain": "Transpiler only.", "tags": ["transpile"]},
        {"id": "b4q10", "type": "mc", "q": "To compare sampler results to exact values you use:", "options": ["Exact equality", "Standard errors from shots", "Visual inspection", "Purity"], "answer": 1, "explain": "z-scores with √(p(1−p)/N).", "tags": ["validation"]},
        {"id": "b4q11", "type": "short", "q": "Why should pilot code be written against the V2 primitives rather than a simulator-specific API?",
         "must": [["hardware", "runtime", "ibm", "portable"], ["same", "interface", "without rewrit", "unchanged"]],
         "explain": "The same interface runs on Aer and IBM Runtime, so the prototype moves to hardware unchanged.", "tags": ["api"]},
        {"id": "b4q12", "type": "short", "q": "Name the three exact reference paths and one sampled path you would cross-check in an implementation test.",
         "must": [["statevector"], ["density"], ["sampler", "shots"]],
         "explain": "quantum_info Statevector, Aer statevector, Aer density matrix; SamplerV2 (and EstimatorV2).", "tags": ["validation"]},
    ],
    "exercise": {
        "id": "b4_ex",
        "title": "A primitives toolkit",
        "prompt": (
            "Implement:\n1. `probs_exact(qc)` → dict of exact probabilities (keys as Qiskit strings; drop < 1e-12).\n"
            "2. `probs_sampled(qc, shots, seed)` → dict of sampled frequencies using SamplerV2 (add measure_all to a copy if the circuit has no measurements).\n"
            "3. `expectations(qc, labels)` → numpy array of exact expectations for a list of Pauli labels via EstimatorV2.\n"
            "4. `sweep_p(qc, param, values, key, shots, seed)` → numpy array of sampled P(key) for each value, using ONE sampler call."
        ),
        "starter": '''import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, SparsePauliOp
from qiskit_aer.primitives import SamplerV2, EstimatorV2

def probs_exact(qc):
    raise NotImplementedError

def probs_sampled(qc, shots, seed):
    raise NotImplementedError

def expectations(qc, labels):
    raise NotImplementedError

def sweep_p(qc, param, values, key, shots, seed):
    raise NotImplementedError
''',
        "solution": '''import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, SparsePauliOp
from qiskit_aer.primitives import SamplerV2, EstimatorV2

def probs_exact(qc):
    q = qc.remove_final_measurements(inplace=False)
    return {k: v for k, v in Statevector(q).probabilities_dict().items() if v > 1e-12}

def _measured(qc):
    if qc.num_clbits:
        return qc
    m = qc.copy(); m.measure_all(); return m

def probs_sampled(qc, shots, seed):
    m = _measured(qc)
    data = SamplerV2(seed=seed).run([m], shots=shots).result()[0].data
    reg = next(iter(data.keys())) if hasattr(data, "keys") else "meas"
    c = getattr(data, reg).get_counts()
    return {k: v/shots for k, v in c.items()}

def expectations(qc, labels):
    q = qc.remove_final_measurements(inplace=False)
    obs = [[SparsePauliOp(l)] for l in labels]
    return np.asarray(EstimatorV2().run([(q, obs)]).result()[0].data.evs).reshape(-1)

def sweep_p(qc, param, values, key, shots, seed):
    m = _measured(qc)
    vals = np.asarray(values, dtype=float).reshape(-1, 1)
    bits = SamplerV2(seed=seed).run([(m, vals)], shots=shots).result()[0].data.meas
    return np.array([bits[i].get_counts().get(key, 0)/shots for i in range(len(vals))])
''',
        "tests": '''import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter

def bell():
    qc = QuantumCircuit(2); qc.h(0); qc.cx(0, 1); return qc

def test_exact():
    p = probs_exact(bell())
    assert set(p) == {"00", "11"} and abs(p["00"] - 0.5) < 1e-12

def test_sampled():
    p = probs_sampled(bell(), 4000, 3)
    assert abs(p.get("11", 0) - 0.5) < 4*np.sqrt(0.25/4000) and set(p) <= {"00", "11"}

def test_expectations():
    e = expectations(bell(), ["ZZ", "IZ", "XX"])
    assert np.allclose(e, [1, 0, 1], atol=1e-9)

def test_sweep_single_call():
    th = Parameter("t"); qc = QuantumCircuit(1); qc.ry(th, 0)
    vals = np.linspace(0, np.pi, 7)
    p = sweep_p(qc, th, vals, "1", 4000, 5)
    assert p.shape == (7,)
    assert np.all(np.abs(p - np.sin(vals/2)**2) < 4*np.sqrt(0.25/4000) + 1e-9)
''',
    },
    "cards": [
        {"front": "Sampler V2 result access (measure_all)", "back": "result()[0].data.meas.get_counts()", "kind": "definition"},
        {"front": "Estimator V2 result access", "back": "result()[0].data.evs and .stds", "kind": "definition"},
        {"front": "PUB (Sampler)", "back": "(circuit, parameter_values)", "kind": "definition"},
        {"front": "PUB (Estimator)", "back": "(circuit, observables, parameter_values) with NumPy broadcasting", "kind": "definition"},
        {"front": "Aer EstimatorV2 default", "back": "Exact (precision=0); set precision to add shot noise", "kind": "mistake"},
        {"front": "Removed in Qiskit 1.0", "back": "execute(); use primitives or backend.run", "kind": "mistake"},
        {"front": "Statevector memory", "back": "16·2ⁿ bytes", "kind": "number"},
        {"front": "Density matrix memory", "back": "16·4ⁿ bytes", "kind": "number"},
        {"front": "Purity", "back": "Tr ρ²; 1 pure, 1/2ⁿ maximally mixed", "kind": "formula"},
        {"front": "Parameter sweep pattern", "back": "Transpile once with Parameter; pass values array (k,1) in PUB", "kind": "definition"},
        {"front": "Count resources from", "back": "transpiled circuit: count_ops(), depth(), num_nonlocal_gates()", "kind": "definition"},
    ],
    "defend": {
        "persona": "validator",
        "questions": [
            {"q": "Which simulator produced your reference numbers, and why that one?",
             "must": [["statevector", "density"], ["exact", "noise", "pure", "mixed"]],
             "model": "Statevector for noiseless exact amplitudes; density matrix when noise is included, because it's exact for mixed states."},
            {"q": "Your Estimator numbers have no error bars. Why?",
             "must": [["exact", "precision"], ["aer", "simulator", "default"]],
             "model": "Aer EstimatorV2 is exact by default; for hardware-like results I set precision and report stds."},
            {"q": "How do you know the sampler output and the exact output agree?",
             "must": [["standard error", "se", "z"], ["shots"]],
             "model": "z-scores against √(p(1−p)/shots), all within 4 SE at each point."},
            {"q": "Will this code run on IBM hardware?",
             "must": [["primitive", "v2", "runtime"], ["isa", "transpile", "backend"]],
             "model": "Yes via the V2 primitives in qiskit-ibm-runtime, after transpiling to the backend's ISA (Track Q5)."},
            {"q": "Your sweep has 500 points. How many times did you transpile?",
             "must": [["once", "one"], ["parameter", "bind"]],
             "model": "Once; Parameters bound at run time in a single PUB."},
        ],
    },
    "glossary": {
        "transpile": "Rewrite a circuit to a target's basis gates and connectivity.",
        "SamplerV2": "Primitive returning measurement samples (BitArray) per PUB.",
        "EstimatorV2": "Primitive returning expectation values and standard errors.",
        "PUB": "Primitive unified bloc: the unit of work submitted to a primitive.",
        "BitArray": "Sampler V2 container for measured bits; get_counts() summarises.",
        "Aer": "Qiskit's high-performance simulator package (qiskit-aer).",
    },
}
