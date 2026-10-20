MODULE = {
    "summary": (
        "A qubit is a normalised complex 2-vector; measurement turns its amplitudes into probabilities and gives you one "
        "bit per shot. Everything a quantum computer reports to a bank arrives through that bottleneck. After this module "
        "you can write a single-qubit state, place it on the Bloch sphere, tell global from relative phase, and size the "
        "shots needed to estimate a probability to a given precision."
    ),
    "concepts": [
        {
            "title": "State vectors and superposition",
            "why": (
                "Classical bits are 0 or 1. A qubit's state is a weighted complex combination of |0⟩ and |1⟩. That is not "
                "'both at once' in any useful sense for a client: it is a vector whose amplitudes can interfere. Interference, "
                "not 'parallelism', is what algorithms such as Grover and QAE exploit."
            ),
            "how": r"""
$|\psi\rangle=\alpha|0\rangle+\beta|1\rangle$, $|\alpha|^2+|\beta|^2=1$. Example: $|+\rangle=\tfrac{1}{\sqrt2}(|0\rangle+|1\rangle)$,
$|-\rangle=\tfrac{1}{\sqrt2}(|0\rangle-|1\rangle)$: same measurement probabilities in the Z basis, different states (they differ in sign), and a Hadamard maps them to
$|0\rangle$ and $|1\rangle$ respectively. That sign difference is interference you can exploit.

The rotation $R_Y(\theta)|0\rangle=\cos\tfrac\theta2|0\rangle+\sin\tfrac\theta2|1\rangle$ sets $P(1)=\sin^2\tfrac\theta2$. This is exactly how QAE
encodes a probability (I3) and how credit circuits encode a conditional PD (I7).
""",
            "code": """import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
for theta in [0, np.pi/3, np.pi/2, np.pi]:
    qc = QuantumCircuit(1); qc.ry(theta, 0)
    sv = Statevector(qc)
    print(f"theta={theta:.3f}: amplitudes={np.round(sv.data,4)}, P(1)={sv.probabilities()[1]:.4f}, sin^2(theta/2)={np.sin(theta/2)**2:.4f}")
""",
            "impact": (
                "When a pitch says 'qubits evaluate all scenarios simultaneously', correct it: the circuit prepares a superposition, "
                "but measurement returns one scenario per shot. Value comes only if interference concentrates probability on the "
                "answer, which is what the algorithm must be designed to do."
            ),
        },
        {
            "title": "The Born rule and measurement",
            "why": (
                "You never see amplitudes on hardware, only counts. Every number a quantum computer gives a bank is an estimate "
                "from shots, with sampling error. Measurement also destroys the superposition, so you cannot 'peek' and continue."
            ),
            "how": r"""
Measuring in the computational basis gives outcome $i$ with probability $p_i=|\langle i|\psi\rangle|^2$ and leaves the state in $|i\rangle$.
From $n$ shots with $h$ ones: $\hat p=h/n$, $\mathrm{SE}=\sqrt{p(1-p)/n}$. Shots for precision $\varepsilon$ at 95%:
$n\approx 1.96^2\,p(1-p)/\varepsilon^2$, worst case $p=\tfrac12$: $n\approx 0.96/\varepsilon^2$. {{c:b1_shots}}

So **direct sampling** of a probability has the same $1/\sqrt n$ rate as Monte Carlo. QAE's improvement comes from **amplitude amplification
before measurement**, not from measuring more cleverly.
""",
            "code": """import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer.primitives import SamplerV2
theta = 2*np.arcsin(np.sqrt(0.3))      # P(1) = 0.3
qc = QuantumCircuit(1); qc.ry(theta, 0); qc.measure_all()
for shots in [100, 1000, 10000]:
    c = SamplerV2(seed=7).run([qc], shots=shots).result()[0].data.meas.get_counts()
    p = c.get("1", 0)/shots
    print(f"shots={shots:6d}: p_hat={p:.4f}  SE={np.sqrt(.3*.7/shots):.4f}")
""",
            "impact": (
                "Every quantum result has a shot budget and therefore a cost per answer on a QPU billed per minute (Track Q5). "
                "Ask any vendor for shots used and the resulting standard error. A probability quoted to four decimals from 1,000 "
                "shots is false precision."
            ),
        },
        {
            "title": "The Bloch sphere; global vs relative phase",
            "why": (
                "Two state vectors can differ yet be physically identical (global phase), while a tiny change in relative phase "
                "changes everything after a Hadamard. Confusing the two produces false 'bugs' and missed real ones when comparing "
                "statevectors to references."
            ),
            "how": r"""
Any pure qubit state, up to global phase: $|\psi\rangle=\cos\tfrac\theta2|0\rangle+e^{i\varphi}\sin\tfrac\theta2|1\rangle$ → Bloch vector
$(\sin\theta\cos\varphi,\ \sin\theta\sin\varphi,\ \cos\theta)=(\langle X\rangle,\langle Y\rangle,\langle Z\rangle)$.

* **Global phase** $e^{i\gamma}|\psi\rangle$: unobservable. Compare states with $|\langle a|b\rangle|\approx1$, or `Statevector.equiv`.
* **Relative phase** $\varphi$: observable after a basis change. $|+\rangle$ and $|-\rangle$ have identical Z-basis statistics but opposite $\langle X\rangle$.
""",
            "code": """import numpy as np
from qiskit.quantum_info import Statevector, Pauli
a = Statevector([1, 1])/np.sqrt(2); b = Statevector([1j, 1j])/np.sqrt(2); c = Statevector([1, -1])/np.sqrt(2)
print("a equiv b (global phase):", a.equiv(b), "| a == b:", np.allclose(a.data, b.data))
print("a vs c Z-probs:", a.probabilities(), c.probabilities())
print("<X>: a =", a.expectation_value(Pauli("X")).real, " c =", c.expectation_value(Pauli("X")).real)
""",
            "impact": (
                "For validation work, this is the difference between a false positive (flagging a global-phase mismatch as a bug) "
                "and a false negative (missing a sign error that only shows after interference). Use the right equality test in "
                "every unit test."
            ),
        },
    ],
    "lens": {
        "look": "Read a single-qubit result as (estimate, shots, standard error). Check the state with fidelity or `equiv`, not element-wise equality. Plot estimate error vs shots.",
        "decision": "How many shots (and therefore QPU minutes) are needed to meet a precision target, and whether a statevector matches its reference.",
        "justified": "Shot noise is the irreducible statistical floor of every quantum readout; budgeting it is the first cost line in any pilot.",
        "mistakes": [
            "Comparing statevectors element-wise and failing on a global phase.",
            "Ignoring relative phase because Z-basis probabilities match.",
            "Quoting estimates without standard errors or with digits beyond the shot noise.",
            "Believing measurement-based readout alone improves on 1/√n (it doesn't; amplification does).",
            "Misreading RY(θ): P(1) = sin²(θ/2), not sin²θ.",
        ],
        "impact": "False precision in pilot results; mis-sized QPU budgets; spurious bug hunts that cost days.",
        "test": "Lab B1: estimate P(1) from shots for an RY-prepared state across shot counts; fit the error slope (expect −0.5).",
    },
    "claims": [
        {"id": "b1_shots", "tag": "M", "text": "Sampled estimates of P(1)=0.3 from SamplerV2 have RMSE within 10% of √(p(1−p)/shots) over 200 seeds (40 seeds is too few: one run gave 0.79).",
         "check": """import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer.primitives import SamplerV2
qc=QuantumCircuit(1); qc.ry(2*np.arcsin(.3**.5),0); qc.measure_all()
e=[SamplerV2(seed=s).run([qc],shots=2000).result()[0].data.meas.get_counts().get('1',0)/2000-.3 for s in range(200)]
r=np.sqrt(np.mean(np.square(e))); se=np.sqrt(.21/2000)
assert abs(r/se-1)<0.1, r/se"""},
        {"id": "b1_born", "tag": "S", "text": "Born rule and measurement postulate.",
         "source": {"title": "Quantum Computation and Quantum Information, §2.2", "publisher": "Cambridge University Press (Nielsen & Chuang)", "date": "2010", "url": "https://doi.org/10.1017/CBO9780511976667"},
         "last_verified": "2026-10-19"},
    ],
    "lab": {
        "id": "b1_lab",
        "title": "Estimate a probability from shots and show shot noise shrinking",
        "hypothesis": (
            "H1: for P(1)=0.3 prepared by RY, the RMSE of p̂ over 40 seeds has log-log slope −0.5 ± 0.1 against shots (100 to 25,600). "
            "H2: the 95% normal-approximation CI covers the true p in 90–99% of seeds at 6,400 shots."
        ),
        "thresholds": "Slope in [−0.6, −0.4]; coverage in [0.90, 0.99].",
        "data": "Ideal simulator (Aer SamplerV2), no noise. Seeds SEED..SEED+39.",
        "code": r'''import numpy as np, pandas as pd
import plotly.graph_objects as go
from qiskit import QuantumCircuit
from qiskit_aer.primitives import SamplerV2
from qlab_helpers import SEED, show, record, table

p = 0.3
qc = QuantumCircuit(1); qc.ry(2*np.arcsin(np.sqrt(p)), 0); qc.measure_all()
shots_list = [100, 400, 1600, 6400, 25600]
rows, cover = [], []
for shots in shots_list:
    est = []
    for s in range(40):
        c = SamplerV2(seed=SEED + s).run([qc], shots=shots).result()[0].data.meas.get_counts()
        ph = c.get("1", 0)/shots; est.append(ph)
        if shots == 6400:
            se = np.sqrt(ph*(1-ph)/shots); cover.append(abs(ph - p) <= 1.96*se)
    est = np.array(est)
    rows.append({"shots": shots, "mean p_hat": est.mean(), "bias": est.mean()-p, "rmse": np.sqrt(np.mean((est-p)**2)), "theory SE": np.sqrt(p*(1-p)/shots)})
df = pd.DataFrame(rows)
slope = np.polyfit(np.log(df.shots), np.log(df.rmse), 1)[0]
fig = go.Figure([go.Scatter(x=df.shots, y=df.rmse, mode="markers+lines", name=f"measured RMSE (slope {slope:.2f})"),
                 go.Scatter(x=df.shots, y=df["theory SE"], name="√(p(1−p)/shots)", line=dict(dash="dot"))])
fig.update_layout(xaxis_type="log", yaxis_type="log", xaxis_title="shots", yaxis_title="RMSE of p̂", title="Shot noise, 40 seeds per point")
show(fig); table(df.round(5), "Shot-noise study")
record("slope", float(slope)); record("coverage_6400", float(np.mean(cover)))
print(f"slope={slope:.3f}, coverage at 6400 shots={np.mean(cover):.2f}")
''',
        "expect": {"slope": "-0.6 < x < -0.4", "coverage_6400": "0.85 <= x <= 1.0"},
        "report_hints": "Section 9: convert the shots needed for ±0.001 into QPU time at a stated shot rate, and state that direct sampling has no quantum speedup.",
    },
    "quiz": [
        {"id": "b1q1", "type": "mc", "q": "RY(θ)|0⟩ gives P(1) =", "options": ["sin²θ", "sin²(θ/2)", "cos²(θ/2)", "θ/π"], "answer": 1, "explain": "Half-angle convention.", "tags": ["states"]},
        {"id": "b1q2", "type": "mc", "q": "Which pair differs only by a global phase?", "options": ["|+⟩ and |−⟩", "|0⟩ and |1⟩", "|+⟩ and i|+⟩", "|0⟩ and |+⟩"], "answer": 2, "explain": "Multiplying by i is global.", "tags": ["phase"]},
        {"id": "b1q3", "type": "mc", "q": "|+⟩ and |−⟩ measured in the Z basis give:", "options": ["Different statistics", "Identical 50/50 statistics", "Always 0", "Always 1"], "answer": 1, "explain": "Relative phase invisible in Z basis.", "tags": ["phase"]},
        {"id": "b1q4", "type": "mc", "q": "Standard error of p̂ from n shots:", "options": ["p/n", "√(p(1−p)/n)", "1/n", "p(1−p)/n"], "answer": 1, "explain": "Binomial.", "tags": ["shots"]},
        {"id": "b1q5", "type": "mc", "q": "Worst-case shots for ±0.01 at 95% are roughly:", "options": ["100", "1,000", "10,000", "100,000"], "answer": 2, "explain": "0.96/ε² ≈ 9,600.", "tags": ["shots"]},
        {"id": "b1q6", "type": "mc", "q": "The Bloch vector components equal:", "options": ["(p0, p1, 0)", "(⟨X⟩, ⟨Y⟩, ⟨Z⟩)", "(α, β, 0)", "(θ, φ, 1)"], "answer": 1, "explain": "Pauli expectations.", "tags": ["bloch"]},
        {"id": "b1q7", "type": "mc", "q": "Measuring a qubit:", "options": ["Leaves its superposition intact", "Collapses it to the observed basis state", "Copies it", "Has no effect"], "answer": 1, "explain": "Measurement postulate.", "tags": ["measurement"]},
        {"id": "b1q8", "type": "mc", "q": "Where does QAE's speedup over direct sampling come from?", "options": ["Better measurement", "Amplitude amplification before measurement", "More shots", "Noise"], "answer": 1, "explain": "Interference via Grover powers.", "tags": ["measurement"]},
        {"id": "b1q9", "type": "mc", "q": "The right unit-test equality for two statevectors is:", "options": ["np.array_equal", "Element-wise allclose only", "Fidelity ≈ 1 or Statevector.equiv", "Compare probabilities only"], "answer": 2,
         "explain": "Ignores global phase, keeps relative.", "tags": ["phase"]},
        {"id": "b1q10", "type": "mc", "q": "|1⟩ sits on the Bloch sphere at:", "options": ["North pole", "South pole", "Equator +X", "Equator +Y"], "answer": 1, "explain": "⟨Z⟩ = −1.", "tags": ["bloch"]},
        {"id": "b1q11", "type": "short", "q": "A vendor reports P(default)=0.03142 from 1,000 shots. Critique.",
         "must": [["standard error", "se", "shot noise", "0.005", "0.0055"], ["precision", "digits", "decimal", "false"]],
         "explain": "SE ≈ √(0.03·0.97/1000) ≈ 0.0054; five decimals is false precision.", "tags": ["shots"]},
        {"id": "b1q12", "type": "short", "q": "Explain 'superposition is not parallelism' in two sentences for a CFO.",
         "must": [["one", "single"], ["measure", "shot", "readout"], ["interfer", "amplif"]],
         "explain": "Each measurement returns one outcome; value requires interference that concentrates probability on useful answers.", "tags": ["states"]},
    ],
    "exercise": {
        "id": "b1_ex",
        "title": "Single-qubit tools",
        "prompt": (
            "Implement:\n1. `ry_state(theta)` → numpy amplitudes of RY(θ)|0⟩.\n2. `bloch_vector(psi)` → (x, y, z).\n"
            "3. `same_up_to_global_phase(a, b, tol=1e-9)`.\n4. `p_from_counts(counts, outcome='1')` → (p̂, SE).\n"
            "5. `shots_needed(p, eps, z=1.96)` → integer shots for half-width eps (ceil)."
        ),
        "starter": '''import numpy as np

def ry_state(theta):
    raise NotImplementedError

def bloch_vector(psi):
    raise NotImplementedError

def same_up_to_global_phase(a, b, tol=1e-9):
    raise NotImplementedError

def p_from_counts(counts, outcome="1"):
    raise NotImplementedError

def shots_needed(p, eps, z=1.96):
    raise NotImplementedError
''',
        "solution": '''import numpy as np, math

def ry_state(theta):
    return np.array([np.cos(theta/2), np.sin(theta/2)], dtype=complex)

def bloch_vector(psi):
    psi = np.asarray(psi, dtype=complex); psi = psi/np.linalg.norm(psi)
    X = np.array([[0,1],[1,0]]); Y = np.array([[0,-1j],[1j,0]]); Z = np.diag([1,-1])
    return tuple(float(np.real(np.vdot(psi, P @ psi))) for P in (X, Y, Z))

def same_up_to_global_phase(a, b, tol=1e-9):
    a = np.asarray(a, dtype=complex); b = np.asarray(b, dtype=complex)
    a = a/np.linalg.norm(a); b = b/np.linalg.norm(b)
    return abs(abs(np.vdot(a, b)) - 1) < tol

def p_from_counts(counts, outcome="1"):
    n = sum(counts.values()); p = counts.get(outcome, 0)/n
    return p, math.sqrt(p*(1-p)/n)

def shots_needed(p, eps, z=1.96):
    return math.ceil(z*z*p*(1-p)/eps**2)
''',
        "tests": '''import numpy as np

def test_ry():
    assert np.allclose(np.abs(ry_state(np.pi/2))**2, [0.5, 0.5])
    assert abs(abs(ry_state(2*np.arcsin(np.sqrt(0.3)))[1])**2 - 0.3) < 1e-12

def test_bloch():
    assert np.allclose(bloch_vector([1, 0]), (0, 0, 1))
    assert np.allclose(bloch_vector([1, 1]), (1, 0, 0))
    assert np.allclose(bloch_vector([1, 1j]), (0, 1, 0))

def test_global_phase():
    assert same_up_to_global_phase([1, 1], [1j, 1j])
    assert not same_up_to_global_phase([1, 1], [1, -1])

def test_counts():
    p, se = p_from_counts({"0": 700, "1": 300})
    assert abs(p - 0.3) < 1e-12 and abs(se - np.sqrt(0.21/1000)) < 1e-12

def test_shots():
    assert shots_needed(0.5, 0.01) == 9604
''',
    },
    "cards": [
        {"front": "RY(θ)|0⟩", "back": "cos(θ/2)|0⟩ + sin(θ/2)|1⟩; P(1) = sin²(θ/2)", "kind": "formula"},
        {"front": "Born rule", "back": "P(i) = |⟨i|ψ⟩|²", "kind": "formula"},
        {"front": "Shots for ±ε at 95% (worst case)", "back": "≈ 0.96/ε² (e.g. 9,604 for ε=0.01)", "kind": "number"},
        {"front": "Bloch vector", "back": "(⟨X⟩, ⟨Y⟩, ⟨Z⟩) = (sinθ cosφ, sinθ sinφ, cosθ)", "kind": "formula"},
        {"front": "Global phase", "back": "Unobservable; e^{iγ}|ψ⟩ ≡ |ψ⟩", "kind": "definition"},
        {"front": "Relative phase", "back": "Observable after a basis change (e.g. H)", "kind": "definition"},
        {"front": "|+⟩, |−⟩", "back": "(|0⟩ ± |1⟩)/√2; ⟨X⟩ = ±1", "kind": "definition"},
        {"front": "Mistake: statevector equality", "back": "Use fidelity or Statevector.equiv, not array equality", "kind": "mistake"},
        {"front": "Mistake: 'superposition = parallelism'", "back": "One outcome per shot; value needs interference", "kind": "mistake"},
        {"front": "Direct sampling error rate", "back": "1/√shots: same as Monte Carlo", "kind": "formula"},
    ],
    "defend": {
        "persona": "cro",
        "questions": [
            {"q": "If a qubit holds 0 and 1 at once, why can't I read all my scenarios in one go?",
             "must": [["measure", "measurement"], ["one", "single"]], "model": "Measurement returns one outcome per shot; the superposition is not readable directly."},
            {"q": "How precise is that probability you showed me?",
             "must": [["shots"], ["standard error", "se", "interval"]], "model": "It came from N shots with standard error √(p(1−p)/N); I'll show the interval."},
            {"q": "So quantum sampling beats Monte Carlo?",
             "must": [["no", "not"], ["amplif", "qae", "interference"]], "model": "No; direct sampling has the same 1/√N rate. Gains need amplitude amplification (QAE), with its own costs."},
            {"q": "What does a shot cost me?",
             "must": [["qpu", "minute", "time", "price"], ["verify", "source", "list", "current"]], "model": "QPU time billed per minute on providers' current list prices (verify date); shots × circuit time determines it."},
            {"q": "Your two outputs differ by a phase factor. Is one wrong?",
             "must": [["global"], ["unobservable", "same", "equivalent"]], "model": "A global phase is unobservable; I test equivalence with fidelity, while checking relative phases separately."},
        ],
    },
    "glossary": {
        "Qubit": "Two-level quantum system; state is a normalised complex 2-vector.",
        "Superposition": "Linear combination of basis states with complex amplitudes.",
        "Born rule": "Measurement probability equals squared amplitude magnitude.",
        "Bloch sphere": "Geometric representation of a single-qubit pure state.",
        "Shot": "One execution and measurement of a circuit.",
        "Global phase": "Overall phase factor; physically unobservable.",
        "Relative phase": "Phase between basis components; observable via interference.",
    },
}
