MODULE = {
    "summary": (
        "This is the first pass at the reason most banks will spend money on quantum this decade: not quantum advantage, "
        "but the threat to public-key cryptography. You will learn what Shor's algorithm breaks and why, what Grover "
        "does (and does not do) to symmetric keys, the harvest-now-decrypt-later exposure, and Mosca's inequality, turned "
        "into a probability of exposure for each data asset under a dated, sourced view of when a CRQC might arrive."
    ),
    "concepts": [
        {
            "title": "What Shor's algorithm breaks, and why",
            "why": (
                "RSA, finite-field Diffie–Hellman and elliptic-curve cryptography all rest on problems (factoring, discrete "
                "logarithms) that reduce to **period finding**. A quantum computer finds periods efficiently using the quantum "
                "Fourier transform. That is an exponential-type speedup over the best known classical algorithms {{c:b7_shor}}."
            ),
            "how": r"""
Factoring $N$ via order finding: pick $a$ coprime to $N$; find the order $r$ (smallest $r$ with $a^r\equiv1 \bmod N$).
If $r$ is even and $a^{r/2}\not\equiv-1$, then $\gcd(a^{r/2}\pm1,N)$ are non-trivial factors. The quantum part finds $r$ (phase
estimation on modular multiplication, I2); everything else is classical.

Cost is dominated by modular exponentiation: $O(n^3)$ gates naively for $n$-bit $N$, improved by windowing and other tricks.
Published resource estimates for RSA-2048 fell from ~20 million noisy qubits in 8 hours (2019) {{c:b7_ge2019}} to under one million noisy qubits in under a week (2025) {{c:b7_g2025}},
assuming 0.1% gate error and 1 µs surface-code cycles. ECC-256 estimates are lower still in logical qubits (A6) {{c:b7_ecc}}.
""",
            "code": """from math import gcd
def order(a, N):
    r, x = 1, a % N
    while x != 1:
        x = (x*a) % N; r += 1
    return r
N, a = 15, 7
r = order(a, N)
print("order r =", r)                          # the quantum computer's only job
if r % 2 == 0 and pow(a, r//2, N) != N-1:
    print("factors:", gcd(pow(a, r//2)-1, N), gcd(pow(a, r//2)+1, N))
""",
            "impact": (
                "Board message: 'The maths that secures our customer channels, payments and signatures has a known quantum "
                "attack. Engineering estimates of the machine needed keep falling. We cannot wait for proof of the machine "
                "before starting a multi-year migration.'"
            ),
        },
        {
            "title": "What Grover does to symmetric keys",
            "why": (
                "Grover search finds a key among $2^k$ in about $2^{k/2}$ quantum steps. That sounds like it halves AES's "
                "security, and it does on paper, but Grover is sequential and parallelises badly, so practical impact is smaller "
                "than the headline. The standard response is simple: use 256-bit keys."
            ),
            "how": r"""
Grover iterations $\approx\frac\pi4\sqrt{2^k}$. With $P$ parallel machines, each searching $2^k/P$ keys, time falls only as $\sqrt P$
(not $P$). For AES-128: $2^{64}$ *sequential* AES evaluations as reversible circuits, each thousands of logical gates deep:
infeasible under realistic logical clock rates. AES-256: $2^{128}$, beyond any conceivable machine.

Hashes: preimage resistance roughly halves in bits; collision search gets at most a modest quantum gain. SHA-256/384 remain fine.
""",
            "code": """import math
for k in (128, 192, 256):
    it = math.pi/4*2**(k/2)
    print(f"AES-{k}: ~{it:.1e} sequential Grover iterations; at 1e6 iterations/s: {it/1e6/3.15e7:.1e} years")
""",
            "impact": "This keeps symmetric spend small: confirm AES-256 for long-lived data and move on. It also guards against vendors selling 'quantum-safe AES replacements'.",
        },
        {
            "title": "Harvest now, decrypt later; Mosca's inequality",
            "why": (
                "Encrypted traffic recorded today can be decrypted once a CRQC exists. So the risk date is not 'when the machine "
                "arrives' but 'when it arrives minus how long the data must stay secret'. And migration itself takes years."
            ),
            "how": r"""
Mosca's inequality {{c:b7_mosca}}: if $x + y > z$ you have a problem, where
$x$ = years the data must remain confidential (shelf life), $y$ = years to migrate, $z$ = years until a CRQC.

Since $z$ is uncertain, treat it as a distribution. Expert surveys put a CRQC within 10 years at 28–49% and within 15 years at
51–70% (Global Risk Institute, published March 2026) {{c:b7_gri}}. Fitting a lognormal to mid-points gives a probability of exposure
$P(z < x + y)$ for each asset class, a number a CRO can rank and a board can set appetite against.
For signatures, the relevant $x$ is the validity period of what is signed (certificates, firmware, legal documents), not data secrecy.
""",
            "code": """import numpy as np
from scipy.stats import norm
# fit lognormal Z (years from now) to P(Z<=10)=0.385, P(Z<=15)=0.605 (GRI 2026 mid-points)
q1, q2 = norm.ppf(0.385), norm.ppf(0.605)
s = (np.log(15)-np.log(10))/(q2-q1); m = np.log(10) - s*q1
for x, y, name in [(1, 4, "card auth (1y)"), (7, 4, "loan files (7y)"), (25, 4, "mortgage/estate (25y)")]:
    print(f"{name:22s} P(exposed) = {norm.cdf((np.log(x+y)-m)/s):.0%}")
""",
            "impact": (
                "Mosca turns a vague threat into a ranked exposure list per data class and system, with a probability that "
                "a risk committee can compare to appetite. It is also the backbone of the prioritisation in I12 and Capstone 3."
            ),
        },
    ],
    "lens": {
        "look": "For each data class and system: shelf life x, migration time y, protecting primitive (key exchange vs signature vs symmetric), and P(z < x+y) under a dated, sourced CRQC distribution with sensitivity.",
        "decision": "Migration priority and budget timing; whether exposure is within risk appetite.",
        "justified": "Exposure today is determined by data recorded today; migration lead times are long; the threat distribution is uncertain but non-negligible within planning horizons.",
        "mistakes": [
            "Treating Q-day as a single date instead of a distribution.",
            "Ignoring migration time y (often the largest term for payments and PKI).",
            "Using data shelf life for signatures instead of the signed object's validity period.",
            "Scoping AES replacement because 'quantum breaks AES'.",
            "Citing CRQC estimates without date: they have fallen sharply (2019 → 2025).",
        ],
        "impact": "Mis-prioritised migration; long-lived confidential data left exposed; board appetite set against a point estimate that changes with the next paper.",
        "test": "Lab B7: Mosca exposure for a portfolio of bank data classes under a GRI-calibrated CRQC distribution, with sensitivity to y and to the distribution.",
    },
    "claims": [
        {"id": "b7_shor", "tag": "S", "text": "Shor's algorithm factors and computes discrete logs in polynomial time on a quantum computer.",
         "source": {"title": "Polynomial-Time Algorithms for Prime Factorization and Discrete Logarithms on a Quantum Computer", "publisher": "SIAM Journal on Computing 26(5) (P. Shor)", "date": "1997", "url": "https://doi.org/10.1137/S0097539795293172"},
         "last_verified": "2026-10-19"},
        {"id": "b7_ge2019", "tag": "S", "text": "Gidney & Ekerå estimated RSA-2048 factoring in ~8 hours with ~20 million noisy qubits.",
         "source": {"title": "How to factor 2048 bit RSA integers in 8 hours using 20 million noisy qubits", "publisher": "Quantum 5, 433 (Gidney & Ekerå)", "date": "2021-04 (arXiv 2019)", "url": "https://doi.org/10.22331/q-2021-04-15-433"},
         "time_sensitive": True, "last_verified": "2026-10-19"},
        {"id": "b7_g2025", "tag": "S", "text": "Gidney (2025) estimated RSA-2048 factoring with fewer than one million noisy qubits in under a week, assuming 0.1% gate error, 1 µs cycle, 10 µs reaction time.",
         "source": {"title": "How to factor 2048 bit RSA integers with less than a million noisy qubits (arXiv:2505.15917)", "publisher": "C. Gidney, Google Quantum AI", "date": "2025-05-21", "url": "https://arxiv.org/abs/2505.15917"},
         "time_sensitive": True, "last_verified": "2026-10-19"},
        {"id": "b7_ecc", "tag": "S", "text": "Google Quantum AI estimated ECDLP on secp256k1 with ≤1,200–1,450 logical qubits, ~70–90 million Toffolis, under 500,000 physical qubits at 1e-3 error.",
         "source": {"title": "Securing Elliptic Curve Cryptocurrencies against Quantum Vulnerabilities: Resource Estimates and Mitigations (whitepaper)", "publisher": "Google Quantum AI (as reported by PostQuantum.com)", "date": "2026-03-31", "url": "https://quantumai.google/static/site-assets/downloads/cryptocurrency-whitepaper.pdf"},
         "time_sensitive": True, "last_verified": "2026-10-19"},
        {"id": "b7_mosca", "tag": "S", "text": "Mosca's inequality: x + y > z signals a problem (x shelf life, y migration time, z time to CRQC).",
         "source": {"title": "Cybersecurity in an Era with Quantum Computers: Will We Be Ready?", "publisher": "IEEE Security & Privacy 16(5) (M. Mosca)", "date": "2018-09", "url": "https://doi.org/10.1109/MSP.2018.3761723"},
         "last_verified": "2026-10-19"},
        {"id": "b7_gri", "tag": "S", "text": "Expert survey: CRQC within 10 years 28–49% ('quite possible'); within 15 years 51–70% ('likely').",
         "source": {"title": "Quantum Threat Timeline Report 2025", "publisher": "Global Risk Institute (Mosca, Piani)", "date": "2026-03-09", "url": "https://globalriskinstitute.org/publication/quantum-threat-timeline-report-2025b/"},
         "time_sensitive": True, "last_verified": "2026-10-19"},
        {"id": "b7_fit", "tag": "M", "text": "A lognormal fitted to P(Z≤10)=0.385 and P(Z≤15)=0.605 reproduces both quantiles exactly.",
         "check": """import numpy as np
from scipy.stats import norm
q1,q2=norm.ppf(.385),norm.ppf(.605); s=(np.log(15)-np.log(10))/(q2-q1); m=np.log(10)-s*q1
assert abs(norm.cdf((np.log(10)-m)/s)-.385)<1e-12 and abs(norm.cdf((np.log(15)-m)/s)-.605)<1e-12"""},
    ],
    "lab": {
        "id": "b7_lab",
        "title": "Mosca exposure for a bank's data classes",
        "hypothesis": (
            "H1: under a lognormal CRQC distribution fitted to the GRI 2026 mid-points, data with ≥10-year shelf life and a 4-year migration has P(exposed) > 50%. "
            "H2: cutting migration time from 6 to 3 years reduces the probability of exposure for 7-year data by more than 10 percentage points. "
            "H3: ranking of data classes by exposure is unchanged when the distribution is fitted to the low or the high end of the GRI ranges."
        ),
        "thresholds": "H1 > 0.5; H2 > 0.10 absolute; H3 identical ranking (Spearman = 1).",
        "data": "Illustrative bank data classes (Judgement: shelf lives are typical retention/secrecy periods; replace with the client's). CRQC distribution: Sourced GRI ranges, fitted here (Measured).",
        "code": r'''import numpy as np, pandas as pd
import plotly.graph_objects as go
from scipy.stats import norm, spearmanr
from qlab_helpers import show, record, table

def fit(p10, p15):
    q1, q2 = norm.ppf(p10), norm.ppf(p15)
    s = (np.log(15) - np.log(10))/(q2 - q1); return np.log(10) - s*q1, s
fits = {"low (28%,51%)": fit(0.28, 0.51), "mid (38.5%,60.5%)": fit(0.385, 0.605), "high (49%,70%)": fit(0.49, 0.70)}
P = lambda t, ms: norm.cdf((np.log(np.maximum(t, 1e-9)) - ms[0])/ms[1])
classes = pd.DataFrame([
    ("Card auth / session keys", 1), ("Payment messages", 2), ("Trading & market data", 1),
    ("KYC / customer PII", 10), ("Loan files", 7), ("Mortgage & estate records", 25),
    ("M&A / strategy", 5), ("Code-signing (signature validity)", 10), ("Root CA (signature validity)", 20),
], columns=["data class", "shelf life x (y)"])
y = 4
for k, ms in fits.items():
    classes[f"P exposed, {k}"] = P(classes["shelf life x (y)"] + y, ms)
table(classes.round(3), f"Probability of exposure P(z < x + y), migration y = {y} years")
t = np.linspace(0.5, 40, 200)
fig = go.Figure([go.Scatter(x=t, y=P(t, ms), name=k) for k, ms in fits.items()])
fig.update_layout(title="CRQC arrival CDF fitted to GRI expert ranges (published 2026-03-09)", xaxis_title="years from now", yaxis_title="P(CRQC by then)")
show(fig)
mid = fits["mid (38.5%,60.5%)"]
record("p_exposed_10y_shelf_y4", float(P(10 + 4, mid)))
record("delta_7y_shelf_y6_to_y3", float(P(7 + 6, mid) - P(7 + 3, mid)))
rk = [spearmanr(classes["P exposed, mid (38.5%,60.5%)"], classes[c]).statistic for c in classes.columns if c.startswith("P exposed")]
record("min_rank_corr", float(min(rk)))
print(classes.to_string(index=False))
''',
        "expect": {"p_exposed_10y_shelf_y4": "x > 0.5", "delta_7y_shelf_y6_to_y3": "x > 0.10", "min_rank_corr": "x > 0.999"},
        "report_hints": "Section 2 must state which numbers are Sourced (GRI ranges), which are Judgement (shelf lives), and which are Measured (fits). Section 9 is a draft board sentence on risk appetite.",
    },
    "quiz": [
        {"id": "b7q1", "type": "mc", "q": "Shor's algorithm's quantum subroutine finds:", "options": ["Prime numbers", "The order (period) of a modulo N", "Hash collisions", "AES keys"], "answer": 1, "explain": "Order finding; the rest is classical.", "tags": ["shor"]},
        {"id": "b7q2", "type": "mc", "q": "Which is NOT broken by Shor?", "options": ["RSA", "ECDH", "ECDSA", "AES-256"], "answer": 3, "explain": "Symmetric; only Grover applies.", "tags": ["shor"]},
        {"id": "b7q3", "type": "mc", "q": "Mosca's inequality signals a problem when:", "options": ["x + y < z", "x + y > z", "x > y + z", "z > x"], "answer": 1, "explain": "Shelf life + migration > time to CRQC.", "tags": ["mosca"]},
        {"id": "b7q4", "type": "mc", "q": "RSA-2048 resource estimates (Gidney): 2019 vs 2025 physical qubits:", "options": ["20M → <1M", "1M → 20M", "100k → 10k", "Unchanged"], "answer": 0, "explain": "Sourced, dated.", "tags": ["estimates"]},
        {"id": "b7q5", "type": "mc", "q": "With P parallel Grover machines, search time falls by:", "options": ["P", "√P", "log P", "P²"], "answer": 1, "explain": "Grover parallelises poorly.", "tags": ["grover"]},
        {"id": "b7q6", "type": "mc", "q": "For a code-signing key, x in Mosca should be:", "options": ["Data secrecy period", "Validity period of what is signed", "Zero", "Key length"], "answer": 1, "explain": "Forgery matters while signatures are relied on.", "tags": ["mosca"]},
        {"id": "b7q7", "type": "mc", "q": "HNDL means confidentiality exposure starts:", "options": ["When the CRQC arrives", "When the data is recorded in transit/at rest under quantum-vulnerable crypto", "Never", "After 2035"], "answer": 1, "explain": "Harvest now.", "tags": ["hndl"]},
        {"id": "b7q8", "type": "mc", "q": "GRI's 2026 survey put a CRQC within 15 years at:", "options": ["5–10%", "28–49%", "51–70%", ">90%"], "answer": 2, "explain": "Sourced, published 2026-03-09.", "tags": ["dated"]},
        {"id": "b7q9", "type": "mc", "q": "Why model z as a distribution?", "options": ["It looks sophisticated", "Expert views are wide; exposure is a probability to compare with appetite", "Regulators require lognormal", "It isn't needed"], "answer": 1, "explain": "Uncertainty is the point.", "tags": ["mosca"]},
        {"id": "b7q10", "type": "mc", "q": "Standard response to Grover for long-lived data:", "options": ["Replace AES", "Use AES-256", "Use RSA-4096", "Use QKD"], "answer": 1, "explain": "Double the key length.", "tags": ["grover"]},
        {"id": "b7q11", "type": "short", "q": "Explain to a board why falling CRQC resource estimates matter more than hardware announcements.",
         "must": [["estimate", "algorithm", "resource"], ["fall", "drop", "lower", "decreas"], ["meet", "closer", "sooner", "gap", "hardware"]],
         "explain": "Algorithmic improvements lower the bar hardware must clear; the target moves toward the hardware faster than the hardware improves.", "tags": ["estimates"]},
        {"id": "b7q12", "type": "short", "q": "Give the Mosca calculation for 10-year KYC data with a 4-year migration, and what you do with the result.",
         "must": [["14"], ["probabil", "%", "distribution"], ["appetite", "priorit", "rank"]],
         "explain": "x+y = 14 years; P(z<14) under the fitted distribution (~57% mid case); compare with risk appetite and rank against other classes.", "tags": ["mosca"]},
    ],
    "exercise": {
        "id": "b7_ex",
        "title": "Mosca and order finding",
        "prompt": (
            "Implement:\n1. `mosca_exposed(x, y, z)` → bool.\n2. `fit_lognormal(t1, p1, t2, p2)` → (mu, sigma) with P(Z≤t)=Φ((ln t − mu)/sigma).\n"
            "3. `p_exposed(x, y, mu, sigma)` → P(Z < x + y).\n4. `order(a, N)` multiplicative order.\n"
            "5. `shor_classical(N, a)` → tuple of non-trivial factors via the order, or None if this a fails."
        ),
        "starter": '''import numpy as np
from math import gcd
from scipy.stats import norm

def mosca_exposed(x, y, z):
    raise NotImplementedError

def fit_lognormal(t1, p1, t2, p2):
    raise NotImplementedError

def p_exposed(x, y, mu, sigma):
    raise NotImplementedError

def order(a, N):
    raise NotImplementedError

def shor_classical(N, a):
    raise NotImplementedError
''',
        "solution": '''import numpy as np
from math import gcd
from scipy.stats import norm

def mosca_exposed(x, y, z):
    return x + y > z

def fit_lognormal(t1, p1, t2, p2):
    q1, q2 = norm.ppf(p1), norm.ppf(p2)
    s = (np.log(t2) - np.log(t1))/(q2 - q1)
    return float(np.log(t1) - s*q1), float(s)

def p_exposed(x, y, mu, sigma):
    return float(norm.cdf((np.log(x + y) - mu)/sigma))

def order(a, N):
    if gcd(a, N) != 1:
        raise ValueError("a and N not coprime")
    r, v = 1, a % N
    while v != 1:
        v = (v*a) % N; r += 1
    return r

def shor_classical(N, a):
    g = gcd(a, N)
    if 1 < g < N:
        return (g, N//g)
    r = order(a, N)
    if r % 2 or pow(a, r//2, N) == N - 1:
        return None
    f = gcd(pow(a, r//2, N) - 1, N)
    return (f, N//f) if 1 < f < N else None
''',
        "tests": '''import numpy as np

def test_mosca():
    assert mosca_exposed(10, 5, 12) and not mosca_exposed(2, 3, 12)

def test_fit():
    mu, s = fit_lognormal(10, 0.385, 15, 0.605)
    assert abs(p_exposed(10, 0, mu, s) - 0.385) < 1e-9 and abs(p_exposed(15, 0, mu, s) - 0.605) < 1e-9

def test_order():
    assert order(7, 15) == 4 and order(2, 21) == 6

def test_shor():
    assert sorted(shor_classical(15, 7)) == [3, 5]
    assert sorted(shor_classical(21, 2)) == [3, 7]
    assert shor_classical(15, 14) is None   # r=2, a^(r/2) = -1 mod N

def test_shor_lucky_gcd():
    assert sorted(shor_classical(15, 6)) == [3, 5]
''',
    },
    "cards": [
        {"front": "Mosca's inequality", "back": "x (shelf life) + y (migration) > z (time to CRQC) ⇒ problem", "kind": "formula"},
        {"front": "Shor's quantum subroutine", "back": "Order/period finding via QFT/phase estimation", "kind": "definition"},
        {"front": "Shor breaks", "back": "RSA, FF-DH, ECDH, ECDSA/EdDSA", "kind": "definition"},
        {"front": "Grover on k-bit key", "back": "~(π/4)·2^{k/2} sequential iterations; parallel gain only √P", "kind": "formula"},
        {"front": "RSA-2048 estimate 2019 (Gidney–Ekerå)", "back": "~20M noisy qubits, ~8 hours (Sourced)", "kind": "number"},
        {"front": "RSA-2048 estimate 2025 (Gidney)", "back": "<1M noisy qubits, <1 week; 0.1% error, 1 µs cycle (Sourced)", "kind": "number"},
        {"front": "GRI expert survey (pub. 2026-03-09)", "back": "CRQC ≤10y: 28–49%; ≤15y: 51–70% (Sourced)", "kind": "number"},
        {"front": "HNDL", "back": "Harvest now, decrypt later: exposure begins when data is recorded", "kind": "definition"},
        {"front": "Mosca x for signatures", "back": "Validity period of the signed object", "kind": "mistake"},
        {"front": "Mistake: Q-day as a point", "back": "Use a distribution; report P(exposed) with sensitivity", "kind": "mistake"},
        {"front": "Order-finding factor step", "back": "gcd(a^{r/2} ± 1, N) if r even and a^{r/2} ≠ −1 mod N", "kind": "formula"},
    ],
    "defend": {
        "persona": "regulator",
        "questions": [
            {"q": "How did you decide which systems migrate first?",
             "must": [["mosca", "shelf", "x + y", "x+y"], ["probabil", "distribution"], ["inventory", "data class"]],
             "model": "Mosca per data class and system from the inventory, with P(z < x + y) under a sourced CRQC distribution, ranked against appetite."},
            {"q": "What's your assumption for when a CRQC arrives, and where is it from?",
             "must": [["distribution", "range", "probabil"], ["source", "gri", "global risk", "survey"], ["date", "2026", "verified"]],
             "model": "A distribution fitted to the GRI expert ranges (published March 2026), with low/high sensitivity, re-verified every six months."},
            {"q": "Why haven't you replaced AES?",
             "must": [["grover"], ["256", "key length"]], "model": "Grover only halves effective key length; AES-256 remains adequate. We confirmed AES-256 on long-lived data."},
            {"q": "Your 2019 estimate says 20 million qubits. Is that still your planning basis?",
             "must": [["no", "not"], ["2025", "million", "lower", "fell"]], "model": "No; the 2025 estimate is under one million noisy qubits. Estimates are falling and we track them dated."},
            {"q": "What about signatures?",
             "must": [["validity", "lifetime", "long-lived"], ["root", "firmware", "code sign", "certificate"]],
             "model": "For signatures x is the validity period; long-lived roots, firmware and code-signing keys are prioritised accordingly."},
        ],
    },
    "glossary": {
        "Shor's algorithm": "Quantum algorithm for factoring and discrete logarithms via period finding.",
        "Grover's algorithm": "Quantum search with quadratic speedup.",
        "Mosca's inequality": "x + y > z test for quantum exposure.",
        "CRQC": "Cryptographically relevant quantum computer.",
        "Q-day": "Informal term for when a CRQC exists; better treated as a distribution.",
        "Order finding": "Finding the smallest r with a^r ≡ 1 mod N.",
    },
}
