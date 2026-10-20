MODULE = {
    "summary": (
        "Linear algebra is the whole of quantum computing's mathematics at circuit level. After this module you can "
        "build multi-qubit states and gates in NumPy, check that they are physically valid (normalised, unitary), "
        "compute measurement probabilities and expectations, and reconcile your NumPy ordering with Qiskit's. "
        "Every later lab uses these checks as its first line of implementation testing."
    ),
    "concepts": [
        {
            "title": "Complex vectors, inner products and norms",
            "why": (
                "A qubit's state is not a probability vector. It is a vector of complex **amplitudes** whose squared "
                "magnitudes are probabilities. Real-valued intuition from Monte Carlo fails: two paths can carry "
                "amplitudes of opposite sign or phase and cancel. You need complex inner products to compute "
                "overlaps (how alike two states are) and norms to check that probabilities sum to one."
            ),
            "how": r"""
A state of $n$ qubits is $|\psi\rangle \in \mathbb{C}^{2^n}$ with $\langle\psi|\psi\rangle = 1$.

* Inner product (conjugate-linear in the first argument): $\langle a|b\rangle = \sum_i \overline{a_i}\, b_i$.
* Norm: $\lVert a\rVert = \sqrt{\langle a|a\rangle}$.
* Probability of outcome $i$ (Born rule, B1): $p_i = |\langle i|\psi\rangle|^2 = |\psi_i|^2$.
* Fidelity of two pure states: $F = |\langle a|b\rangle|^2 \in [0,1]$.

In NumPy, `np.vdot(a, b)` conjugates `a`; `a @ b` and `np.dot(a, b)` do **not**. That single difference is the
most common silent bug in hand-rolled quantum code. {{c:p1_vdot}}
""",
            "code": """import numpy as np
a = np.array([1, 1j]) / np.sqrt(2)          # |+i>
b = np.array([1, -1j]) / np.sqrt(2)         # |-i>
print("vdot <a|b> =", np.vdot(a, b))        # 0: orthogonal
print("dot  a.b   =", np.dot(a, b))         # 1: WRONG, no conjugation
print("norm a     =", np.linalg.norm(a))
print("fidelity(a,a) =", abs(np.vdot(a, a))**2)
""",
            "impact": (
                "When a vendor or internal team says a circuit 'loads the loss distribution with 99% fidelity', you "
                "can now ask which inner product, against which target, and whether 99% fidelity is enough. For a "
                "pricing oracle, a 1% fidelity loss can translate into a price bias larger than the Monte Carlo "
                "error you were trying to beat {{c:p1_fid_judgement}}. Fidelity is an implementation metric, not a "
                "business metric; translate it into price or capital error before anyone signs off."
            ),
        },
        {
            "title": "Tensor (Kronecker) products",
            "why": (
                "Multi-qubit systems are not lists of single qubits. The joint state lives in the tensor product "
                "space, whose dimension multiplies: 2 qubits → 4 amplitudes, 30 qubits → about 10⁹. That exponential "
                "growth is both the reason quantum computers might help and the reason classical simulation "
                "eventually fails (Track Q4)."
            ),
            "how": r"""
$(A\otimes B)_{(i,j),(k,l)} = A_{ik}B_{jl}$, implemented by `np.kron`. For states, $|a\rangle\otimes|b\rangle$ has
amplitudes $a_i b_j$. Operator on one qubit of many: $I\otimes X$ acts with $X$ on the **rightmost** factor.

Ordering convention matters. In textbook (big-endian) notation, $|q_0 q_1\rangle = |q_0\rangle\otimes|q_1\rangle$.
Qiskit is **little-endian**: qubit 0 is the rightmost factor, so `Operator` of a circuit applying $X$ to qubit 0 of
2 equals `np.kron(I, X)`, not `np.kron(X, I)`. {{c:p1_qiskit_kron}}

Not every 2-qubit state is a tensor product. $\frac{1}{\sqrt2}(|00\rangle+|11\rangle)$ cannot be written as
$|a\rangle\otimes|b\rangle$: it is entangled (B3). Test: reshape the 4-vector into a 2×2 matrix; product states have
matrix rank 1 (Schmidt rank 1).
""",
            "code": """import numpy as np
I = np.eye(2); X = np.array([[0,1],[1,0]])
zero = np.array([1,0]); one = np.array([0,1])
print("|0>(x)|1> =", np.kron(zero, one))            # index 1 -> '01'
print("X on right factor:\\n", np.kron(I, X))
bell = (np.kron(zero, zero) + np.kron(one, one)) / np.sqrt(2)
print("Schmidt rank of Bell:", np.linalg.matrix_rank(bell.reshape(2,2)))
""",
            "impact": (
                "Exponential state size is the headline argument for quantum advantage, and it is often oversold. "
                "The client-relevant question is not 'how big is the state space' but 'can I load my data into it "
                "cheaply and read out the answer efficiently' (I4, I3). When someone quotes 2^n, ask for the "
                "loading cost and the readout cost."
            ),
        },
        {
            "title": "Unitary and Hermitian matrices; eigen-decomposition",
            "why": (
                "Closed quantum evolution must preserve total probability, so gates must be **unitary** "
                "($U^\\dagger U = I$). Measurable quantities (energy, a portfolio cost function in QAOA, a Pauli "
                "observable) are **Hermitian** ($H = H^\\dagger$), so their eigenvalues are real. Confusing the two "
                "is a category error that shows up as non-normalised states or complex 'expected costs'."
            ),
            "how": r"""
* Unitary: $U^\dagger U = I$; eigenvalues lie on the unit circle $e^{i\theta}$. Check
  $\lVert U^\dagger U - I\rVert_F < \varepsilon$ with $\varepsilon \approx 10^{-10}$ for float64 work.
* Hermitian: $H = H^\dagger$; spectral theorem $H = \sum_k \lambda_k |v_k\rangle\langle v_k|$ with real $\lambda_k$.
  Use `np.linalg.eigh` (Hermitian solver, sorted real eigenvalues), not `eig`.
* Bridge: $U = e^{-iH t}$ is unitary for Hermitian $H$ (`scipy.linalg.expm`). Every rotation gate is this:
  $R_X(\theta) = e^{-i\theta X/2}$.
* Expectation of an observable: $\langle H\rangle = \langle\psi|H|\psi\rangle$, real for Hermitian $H$.
""",
            "code": """import numpy as np
from scipy.linalg import expm
X = np.array([[0,1],[1,0]], dtype=complex)
theta = 0.7
RX = expm(-1j*theta*X/2)
print("unitarity residual:", np.linalg.norm(RX.conj().T @ RX - np.eye(2)))
print("matches closed form:", np.allclose(RX, np.cos(theta/2)*np.eye(2) - 1j*np.sin(theta/2)*X))
w, v = np.linalg.eigh(X)
print("eigenvalues of X:", w)
""",
            "impact": (
                "In validation terms, unitarity and normalisation residuals are your **implementation tests**. A "
                "model validator will ask how you know the oracle is correct; 'the residual is below 1e-10 on every "
                "gate and the toy price matches the closed form' is an answer. It proves the code is right. It says "
                "nothing about whether quantum helps the client."
            ),
        },
        {
            "title": "Pauli matrices, outer products and projectors",
            "why": (
                "Paulis are the alphabet of quantum computing: every observable on n qubits is a real combination of "
                "Pauli strings, and Qiskit's `SparsePauliOp` is how you will write QAOA cost functions and Estimator "
                "observables. Projectors are how measurement is described mathematically."
            ),
            "how": r"""
$X=\begin{pmatrix}0&1\\1&0\end{pmatrix},\ Y=\begin{pmatrix}0&-i\\i&0\end{pmatrix},\ Z=\begin{pmatrix}1&0\\0&-1\end{pmatrix}$.
Each is Hermitian **and** unitary, squares to $I$, and $XY=iZ$ (cyclic). Together with $I$ they form an
orthogonal basis for $2\times2$ matrices under $\langle A,B\rangle=\mathrm{Tr}(A^\dagger B)$, so any $M = \tfrac12\sum_P \mathrm{Tr}(PM)\,P$.

Outer product $|a\rangle\langle b|$ = `np.outer(a, b.conj())`. Projector onto $|\psi\rangle$: $P=|\psi\rangle\langle\psi|$,
with $P^2=P$, $P^\dagger=P$. Probability of outcome $\psi$: $\langle\phi|P|\phi\rangle$. $Z = |0\rangle\langle 0| - |1\rangle\langle 1|$,
so $\langle Z\rangle = p_0 - p_1$: the link between Pauli expectations and measurement counts.
""",
            "code": """import numpy as np
X = np.array([[0,1],[1,0]]); Y = np.array([[0,-1j],[1j,0]]); Z = np.diag([1,-1])
print("XY == iZ:", np.allclose(X@Y, 1j*Z))
M = np.array([[2, 1-1j],[1+1j, -1]])
coef = {n: np.trace(P.conj().T @ M)/2 for n, P in zip("IXYZ", [np.eye(2), X, Y, Z])}
print("Pauli decomposition:", {k: np.round(v,3) for k,v in coef.items()})
psi = np.array([np.cos(0.3), np.sin(0.3)])
P0 = np.outer([1,0],[1,0])
print("p0 =", psi @ P0 @ psi, " <Z> =", psi @ Z @ psi, " p0-p1 =", psi[0]**2-psi[1]**2)
""",
            "impact": (
                "Clients will meet Pauli strings when a vendor shows a 'Hamiltonian' for a portfolio problem. The "
                "number of Pauli terms drives measurement cost on hardware: more terms, more circuits, more shots, "
                "more QPU minutes. Ask for the term count and the grouping strategy before accepting a cost estimate."
            ),
        },
    ],
    "lens": {
        "look": (
            "A practitioner treats every state and gate as a data artefact to be validated: dimension (is it 2ⁿ?), "
            "norm (=1?), unitarity residual ‖U†U − I‖, Hermiticity of observables, and ordering convention "
            "(does my kron order match Qiskit's?). They print the statevector at toy size and check it against a "
            "hand calculation before trusting any sampler output."
        ),
        "decision": "Accept or reject a circuit/oracle implementation as correct before it is used for pricing, risk or optimisation.",
        "justified": (
            "Everything downstream (QAE estimates, resource counts, business cases) inherits any error here. "
            "Implementation testing at toy size is the cheapest point in the pipeline to catch it, exactly like "
            "unit-testing a cash-flow engine before running CCAR scenarios."
        ),
        "mistakes": [
            "Using `np.dot`/`@` instead of `np.vdot` for inner products of complex vectors (no conjugation).",
            "Reversing kron order relative to Qiskit's little-endian convention, so the 'correct' state is checked against the wrong qubit.",
            "Using `np.linalg.eig` on a Hermitian matrix and getting tiny complex parts or unsorted eigenvalues.",
            "Tolerance theatre: checking `== 0` (fails on float noise) or `< 1e-2` (passes real bugs).",
            "Calling a Hermitian matrix a gate, or exponentiating without the −i, producing a non-unitary 'gate'.",
        ],
        "impact": (
            "Silent bias in prices and risk numbers; validation findings (SR 11-7 implementation testing gap); wasted QPU "
            "budget on circuits that were wrong before they reached hardware; reputational damage if a pilot result is "
            "later traced to an ordering bug."
        ),
        "test": "Lab P1: build 2- and 3-qubit states and gates, check normalisation and unitarity, and reconcile NumPy ordering with Qiskit's Operator.",
    },
    "claims": [
        {"id": "p1_vdot", "tag": "M", "text": "np.vdot conjugates its first argument; np.dot does not, so they differ for complex vectors.",
         "check": "import numpy as np\na=np.array([1,1j])/2**.5; b=np.array([1,-1j])/2**.5\nassert abs(np.vdot(a,b))<1e-12 and abs(np.dot(a,b)-1)<1e-12"},
        {"id": "p1_qiskit_kron", "tag": "M", "text": "Qiskit Operator of a 2-qubit circuit with X on qubit 0 equals np.kron(I, X) (little-endian).",
         "check": "import numpy as np\nfrom qiskit import QuantumCircuit\nfrom qiskit.quantum_info import Operator\nqc=QuantumCircuit(2); qc.x(0)\nassert np.allclose(Operator(qc).data, np.kron(np.eye(2), [[0,1],[1,0]]))"},
        {"id": "p1_fid_judgement", "tag": "J", "text": "A 1% fidelity loss in an oracle can produce price bias larger than the Monte Carlo error being targeted; size it per use case."},
        {"id": "p1_nc", "tag": "S", "text": "Standard reference for the linear algebra of quantum computing.",
         "source": {"title": "Quantum Computation and Quantum Information (10th anniversary ed.)", "publisher": "Cambridge University Press (Nielsen & Chuang)", "date": "2010", "url": "https://doi.org/10.1017/CBO9780511976667"},
         "last_verified": "2026-10-19"},
    ],
    "lab": {
        "id": "p1_lab",
        "title": "Build 2- and 3-qubit states and gates in NumPy; check unitarity, normalisation and ordering",
        "hypothesis": (
            "H1: every gate built from {H, X, Z, CNOT, Toffoli} via kron has unitarity residual < 1e-12. "
            "H2: every state produced by applying them to |000> has |norm − 1| < 1e-12. "
            "H3: my big-endian NumPy matrices equal Qiskit's Operator only after reversing qubit order."
        ),
        "thresholds": "Residuals < 1e-12; ordering match exact (allclose, atol 1e-12).",
        "data": "Synthetic: exact matrices. No leakage risk (no data).",
        "code": r'''import numpy as np, pandas as pd
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
from qlab_helpers import SEED, record, table

I = np.eye(2); X = np.array([[0,1],[1,0]]); Z = np.diag([1,-1]); H = np.array([[1,1],[1,-1]])/np.sqrt(2)
P0 = np.diag([1,0]); P1 = np.diag([0,1])
def kron(*ops):
    out = np.array([[1.0]])
    for o in ops: out = np.kron(out, o)
    return out
# big-endian (textbook): leftmost factor = qubit 0
CNOT_01 = kron(P0, I) + kron(P1, X)                     # control q0, target q1
TOFF = kron(P0, I, I) + kron(P1, P0, I) + kron(P1, P1, X)
gates = {"H(x)I": kron(H, I), "CNOT_01": CNOT_01, "Z(x)Z(x)H": kron(Z, Z, H), "Toffoli": TOFF,
         "random U3 (x) I(x)I": kron(np.linalg.qr(np.random.default_rng(SEED).normal(size=(2,2))+1j*np.random.default_rng(SEED+1).normal(size=(2,2)))[0], I, I)}
rows = []
for name, U in gates.items():
    res = np.linalg.norm(U.conj().T @ U - np.eye(U.shape[0]))
    rows.append({"gate": name, "dim": U.shape[0], "unitarity_residual": res})
df = pd.DataFrame(rows); table(df, "Unitarity residuals ||U^dag U - I||_F")
record("max_unitarity_residual", float(df.unitarity_residual.max()))

# states: GHZ on 3 qubits in big-endian
s = np.zeros(8); s[0] = 1
s = kron(H, I, I) @ s
s = kron(CNOT_01, I) @ s
s = kron(I, CNOT_01) @ s
print("GHZ amplitudes (big-endian index q0q1q2):", np.round(s, 4))
record("ghz_norm_error", float(abs(np.linalg.norm(s) - 1)))

# ordering reconciliation with Qiskit (little-endian)
qc = QuantumCircuit(2); qc.cx(0, 1)
Uq = Operator(qc).data
print("Qiskit CX(0->1) == my big-endian CNOT_01 ?", np.allclose(Uq, CNOT_01))
SWAP = kron(P0,P0)+kron(P1,P1)+ np.array([[0,0,0,0],[0,0,1,0],[0,1,0,0],[0,0,0,0]])
print("Qiskit CX(0->1) == SWAP @ CNOT_01 @ SWAP ?", np.allclose(Uq, SWAP @ CNOT_01 @ SWAP))
record("ordering_match_after_reversal", bool(np.allclose(Uq, SWAP @ CNOT_01 @ SWAP)))
record("ordering_match_naive", bool(np.allclose(Uq, CNOT_01)))
''',
        "report_hints": "Your decision section must say which hypotheses passed. Your business translation should say what this does NOT prove (anything about value).",
    },
    "quiz": [
        {"id": "p1q1", "type": "mc", "q": "For complex vectors a, b, which NumPy call returns ⟨a|b⟩?",
         "options": ["np.dot(a, b)", "a @ b", "np.vdot(a, b)", "np.inner(a, b)"], "answer": 2,
         "explain": "Only vdot conjugates the first argument. dot, @ and inner do not.", "tags": ["inner product"]},
        {"id": "p1q2", "type": "mc", "q": "How many complex amplitudes describe a general 20-qubit pure state?",
         "options": ["20", "400", "2^20 ≈ 1.05 million", "20^2 · 2"], "answer": 2,
         "explain": "Dimension is 2^n.", "tags": ["tensor"]},
        {"id": "p1q3", "type": "mc", "q": "In Qiskit, a circuit applying X to qubit 0 of a 2-qubit register has Operator equal to:",
         "options": ["kron(X, I)", "kron(I, X)", "X + I", "kron(X, X)"], "answer": 1,
         "explain": "Little-endian: qubit 0 is the rightmost tensor factor.", "tags": ["ordering"]},
        {"id": "p1q4", "type": "mc", "q": "Which property must every quantum gate satisfy?",
         "options": ["Hermitian", "Unitary", "Real-valued", "Diagonal"], "answer": 1,
         "explain": "Gates preserve norm, so U†U = I. Some gates (X, Z, H) are also Hermitian, but that is not required (S, T, RX are not).", "tags": ["unitary"]},
        {"id": "p1q5", "type": "mc", "q": "The eigenvalues of a Hermitian matrix are:",
         "options": ["On the unit circle", "Real", "Purely imaginary", "Always ±1"], "answer": 1,
         "explain": "Spectral theorem. Paulis happen to have ±1, but general Hermitian matrices have any real eigenvalues.", "tags": ["hermitian"]},
        {"id": "p1q6", "type": "mc", "q": "For a 2-qubit state vector reshaped to a 2×2 matrix, rank 1 means:",
         "options": ["The state is entangled", "The state is a product state", "The state is not normalised", "The state is a Bell state"], "answer": 1,
         "explain": "Schmidt rank 1 ⇔ product state.", "tags": ["tensor", "entanglement"]},
        {"id": "p1q7", "type": "mc", "q": "⟨ψ|Z|ψ⟩ equals:",
         "options": ["p0 + p1", "p0 − p1", "p1 − p0", "2·p0"], "answer": 1,
         "explain": "Z = |0⟩⟨0| − |1⟩⟨1|.", "tags": ["pauli"]},
        {"id": "p1q8", "type": "mc", "q": "Which is the right tolerance practice for a unitarity check in float64?",
         "options": ["residual == 0", "residual < 1e-2", "residual < ~1e-10, and investigate anything larger", "No check needed if the code runs"],
         "answer": 2, "explain": "Exact zero fails on rounding; 1e-2 hides real bugs.", "tags": ["validation"]},
        {"id": "p1q9", "type": "mc", "q": "R_X(θ) equals:",
         "options": ["exp(−iθX)", "exp(−iθX/2)", "exp(θX/2)", "cos θ I − i sin θ X"], "answer": 1,
         "explain": "Convention used by Qiskit and most texts: R_P(θ) = exp(−iθP/2).", "tags": ["unitary"]},
        {"id": "p1q10", "type": "mc", "q": "A projector P satisfies:",
         "options": ["P² = I", "P² = P and P† = P", "P†P = I", "Tr(P) = 0"], "answer": 1,
         "explain": "Idempotent and Hermitian.", "tags": ["projector"]},
        {"id": "p1q11", "type": "short", "q": "A colleague's oracle passes all unit tests at 3 qubits. Explain in two sentences what that proves and what it does not.",
         "must": [["implementation", "correct", "code is right", "matches"], ["not", "doesn't", "does not"], ["value", "advantage", "speedup", "helps", "business"]],
         "explain": "It proves the implementation is correct at that size; it proves nothing about value or advantage.", "tags": ["validation", "honesty"]},
        {"id": "p1q12", "type": "short", "q": "Why does np.linalg.eigh beat np.linalg.eig for observables?",
         "must": [["hermitian"], ["real"], ["sort", "ordered", "stable", "numerically"]],
         "explain": "eigh assumes Hermitian input, returns real sorted eigenvalues and orthonormal vectors, and is numerically stabler.", "tags": ["hermitian"]},
    ],
    "exercise": {
        "id": "p1_ex",
        "title": "A validated linear-algebra toolkit",
        "prompt": (
            "Implement six functions. They will be reused in later labs, so make them correct and strict.\n\n"
            "1. `inner(a, b)` → ⟨a|b⟩\n2. `kron_all(*ops)` → left-to-right Kronecker product\n"
            "3. `is_unitary(U, tol=1e-10)` → bool\n4. `is_hermitian(H, tol=1e-10)` → bool\n"
            "5. `projector(psi)` → |ψ⟩⟨ψ| (normalise psi first)\n6. `expectation(psi, O)` → real ⟨ψ|O|ψ⟩ (normalise psi; raise ValueError if O is not Hermitian)"
        ),
        "starter": '''import numpy as np

def inner(a, b):
    raise NotImplementedError

def kron_all(*ops):
    raise NotImplementedError

def is_unitary(U, tol=1e-10):
    raise NotImplementedError

def is_hermitian(H, tol=1e-10):
    raise NotImplementedError

def projector(psi):
    raise NotImplementedError

def expectation(psi, O):
    raise NotImplementedError
''',
        "solution": '''import numpy as np

def inner(a, b):
    return np.vdot(np.asarray(a), np.asarray(b))

def kron_all(*ops):
    out = np.array([[1.0 + 0j]]) if np.asarray(ops[0]).ndim == 2 else np.array([1.0 + 0j])
    for o in ops:
        out = np.kron(out, np.asarray(o))
    return out

def is_unitary(U, tol=1e-10):
    U = np.asarray(U)
    if U.ndim != 2 or U.shape[0] != U.shape[1]:
        return False
    return np.linalg.norm(U.conj().T @ U - np.eye(U.shape[0])) < tol

def is_hermitian(H, tol=1e-10):
    H = np.asarray(H)
    return H.ndim == 2 and H.shape[0] == H.shape[1] and np.linalg.norm(H - H.conj().T) < tol

def projector(psi):
    psi = np.asarray(psi, dtype=complex)
    psi = psi / np.linalg.norm(psi)
    return np.outer(psi, psi.conj())

def expectation(psi, O):
    if not is_hermitian(O):
        raise ValueError("observable must be Hermitian")
    psi = np.asarray(psi, dtype=complex)
    psi = psi / np.linalg.norm(psi)
    return float(np.real(np.vdot(psi, np.asarray(O) @ psi)))
''',
        "tests": '''import numpy as np
X = np.array([[0,1],[1,0]]); Y = np.array([[0,-1j],[1j,0]]); Z = np.diag([1,-1]); I = np.eye(2)

def test_inner_conjugates():
    """inner must conjugate the first argument"""
    a = np.array([1, 1j]) / np.sqrt(2); b = np.array([1, -1j]) / np.sqrt(2)
    assert abs(inner(a, b)) < 1e-12, "inner(|+i>,|-i>) should be 0; are you conjugating?"
    assert abs(inner(a, a) - 1) < 1e-12

def test_kron_order():
    """kron_all must be left-to-right"""
    assert np.allclose(kron_all(I, X), np.kron(I, X))
    assert np.allclose(kron_all(X, I, Z), np.kron(np.kron(X, I), Z))
    assert kron_all(np.array([1,0]), np.array([0,1])).tolist() == [0,1,0,0]

def test_unitary():
    """Paulis, H and random QR unitaries are unitary; a scaled matrix is not"""
    H = np.array([[1,1],[1,-1]])/np.sqrt(2)
    for U in (X, Y, Z, H, np.kron(H, X)):
        assert is_unitary(U)
    assert not is_unitary(2*X)
    assert not is_unitary(np.ones((2,3)))

def test_hermitian():
    """Y is Hermitian; S = diag(1, i) is not"""
    assert is_hermitian(Y)
    assert not is_hermitian(np.diag([1, 1j]))

def test_projector():
    """projector is idempotent, Hermitian, trace 1, and normalises input"""
    P = projector([3, 4j])
    assert np.allclose(P @ P, P) and np.allclose(P, P.conj().T) and abs(np.trace(P) - 1) < 1e-12

def test_expectation():
    """<+|X|+> = 1, <0|Z|0> = 1, non-Hermitian raises"""
    plus = np.array([1, 1])
    assert abs(expectation(plus, X) - 1) < 1e-12
    assert abs(expectation([1, 0], Z) - 1) < 1e-12
    assert isinstance(expectation(plus, Z), float)
    try:
        expectation(plus, np.diag([1, 1j]))
        assert False, "should raise ValueError for non-Hermitian"
    except ValueError:
        pass
''',
    },
    "cards": [
        {"front": "Inner product ⟨a|b⟩ in NumPy", "back": "np.vdot(a, b): conjugates a. np.dot does not.", "kind": "mistake"},
        {"front": "Dimension of n-qubit state space", "back": "2ⁿ complex amplitudes", "kind": "number"},
        {"front": "Unitary condition", "back": "U†U = I (norm-preserving; eigenvalues e^{iθ})", "kind": "formula"},
        {"front": "Hermitian condition", "back": "H = H† (real eigenvalues; observables)", "kind": "formula"},
        {"front": "Qiskit qubit order", "back": "Little-endian: qubit 0 is the rightmost tensor factor / rightmost bit in count strings", "kind": "mistake"},
        {"front": "R_X(θ)", "back": "exp(−iθX/2) = cos(θ/2) I − i sin(θ/2) X", "kind": "formula"},
        {"front": "⟨Z⟩ in terms of probabilities", "back": "p0 − p1", "kind": "formula"},
        {"front": "Product-state test for 2 qubits", "back": "Reshape amplitudes to 2×2; rank 1 ⇒ product, rank 2 ⇒ entangled", "kind": "definition"},
        {"front": "Projector properties", "back": "P² = P, P† = P; P = |ψ⟩⟨ψ|", "kind": "definition"},
        {"front": "Pauli decomposition coefficient", "back": "c_P = Tr(P M)/2 for 2×2 M", "kind": "formula"},
        {"front": "Fidelity of pure states", "back": "|⟨a|b⟩|² ∈ [0, 1]", "kind": "formula"},
        {"front": "Use which eigen-solver for observables?", "back": "np.linalg.eigh (real, sorted, stable)", "kind": "mistake"},
    ],
    "defend": {
        "persona": "validator",
        "questions": [
            {"q": "Your oracle is 'validated'. Show me what you tested and to what tolerance.",
             "must": [["unitar", "residual"], ["norm", "normalis", "normaliz"], ["toy", "small", "exact", "closed form", "analytic"], ["tolerance", "1e-", "10^-"]],
             "model": "Unitarity residual of every gate and the full oracle below 1e-10; state normalisation within 1e-12; toy-size output equal to an exact classical calculation; tolerances fixed in advance."},
            {"q": "How do you know your NumPy reference and Qiskit agree on which qubit is which?",
             "must": [["little-endian", "little endian", "rightmost"], ["operator", "compare", "reconcil", "test"]],
             "model": "Qiskit is little-endian; I compare my matrix with Operator(qc).data after reversing qubit order, in a unit test."},
            {"q": "Passing those tests: does that tell the bank anything about value?",
             "must": [["no", "not"], ["implementation", "correct"], ["value", "advantage", "baseline"]],
             "model": "No. It establishes implementation correctness only. Value needs a timed, optimised classical baseline and resource estimates."},
            {"q": "Why is 'the state space is 2^50' not an argument for advantage?",
             "must": [["load", "loading", "input"], ["readout", "measure", "output", "sampl"]],
             "model": "The state space is not accessible: loading data and extracting answers cost circuits and shots. Advantage depends on those costs."},
            {"q": "Which numerical choices could make your tests pass when the code is wrong?",
             "must": [["tolerance", "loose"], ["dot", "conjugat", "vdot", "order", "kron"]],
             "model": "A loose tolerance; testing symmetric cases where missing conjugation or reversed kron order cancels out; testing only real-valued states."},
        ],
    },
    "glossary": {
        "Amplitude": "Complex coefficient of a basis state; its squared magnitude is a probability.",
        "Kronecker product": "Matrix tensor product; builds multi-qubit states and operators.",
        "Unitary": "Matrix with U†U = I; every gate is unitary.",
        "Hermitian": "Matrix equal to its conjugate transpose; observables are Hermitian.",
        "Pauli matrices": "X, Y, Z: Hermitian, unitary, square to I; a basis for observables.",
        "Projector": "P with P² = P = P†; describes a measurement outcome.",
        "Little-endian (Qiskit)": "Convention where qubit 0 is the least significant (rightmost) bit.",
        "Fidelity": "Overlap measure between states; |⟨a|b⟩|² for pure states.",
    },
}
