MODULE = {
    "summary": (
        "Quantum speedups are statements about how cost grows, not about cost today. This module gives you the "
        "language (big-O, polynomial vs exponential, query complexity, oracles) and, more importantly, the arithmetic "
        "to show when a quadratic speedup survives constant factors and slow clocks, and when it disappears. You will "
        "build the first version of the crossover calculation that A3 turns into a client deliverable."
    ),
    "concepts": [
        {
            "title": "Big-O, polynomial vs exponential",
            "why": (
                "Vendors and papers state results asymptotically. 'Exponential speedup' (Shor) and 'quadratic speedup' "
                "(Grover, QAE) are different universes of value, and clients routinely hear them conflated. You must be "
                "able to say which one a claim is, in one sentence."
            ),
            "how": r"""
$f(n)=O(g(n))$ if $f(n)\le c\,g(n)$ for large $n$. Polynomial: $O(n^k)$. Exponential: $O(2^{cn})$.

* **Exponential speedup** (e.g. factoring: best known classical sub-exponential GNFS vs Shor polynomial): problems become feasible that were not.
* **Quadratic speedup** (Grover: $O(N)\to O(\sqrt N)$ queries; QAE: $O(1/\varepsilon^2)\to O(1/\varepsilon)$): the same problem gets cheaper by a square root, *if* the per-step cost is comparable.
* Big-O hides constants. $10^6\sqrt N < N$ only when $N>10^{12}$.
""",
            "code": """import numpy as np
for N in [1e6, 1e9, 1e12, 1e15]:
    classical, quantum = N, 1e6*np.sqrt(N)
    print(f"N={N:.0e}: classical {classical:.1e} vs quantum(const 1e6) {quantum:.1e} -> {'Q wins' if quantum<classical else 'C wins'}")
""",
            "impact": (
                "Client framing: Shor-type exponential speedups are why your cryptography must change regardless of "
                "whether quantum ever helps your P&L. Grover/QAE-type quadratic speedups are why quantum *might* help "
                "pricing and risk, and only if hardware becomes fast enough. Two different decisions, two different budgets."
            ),
        },
        {
            "title": "Query complexity and oracles",
            "why": (
                "Most quantum-finance speedups are proven in the **query model**: count calls to an 'oracle' that "
                "encodes the problem (the payoff, the loss distribution). That count ignores what one oracle call costs "
                "to build and run. Most disappointment in quantum finance lives in that gap."
            ),
            "how": r"""
An oracle $O_f$ is a black-box unitary that encodes $f$: e.g. $O_f|x\rangle|0\rangle=|x\rangle|f(x)\rangle$, or for
amplitude estimation $\mathcal A|0\rangle=\sqrt{1-a}\,|\psi_0\rangle|0\rangle+\sqrt a\,|\psi_1\rangle|1\rangle$ where $a$ is the quantity
you want (e.g. a normalised expected payoff).

Query complexity counts oracle calls. Total cost = queries × (cost per query). In QAE the per-query cost is the
**depth of $\mathcal A$**: data loading + payoff arithmetic, often thousands of gates (I5: ~620 CX for a 4-qubit toy).
Classical MC's per-sample cost is nanoseconds of vectorised arithmetic.
""",
            "code": """eps = 1e-4
mc_samples = (1/eps)**2          # sigma=1
qae_queries = 1/eps
print(f"MC samples {mc_samples:.0e}, QAE queries {qae_queries:.0e}")
print("ratio of counts:", mc_samples/qae_queries)
print("but per-query vs per-sample cost ratio might be ~1e6..1e9 -> net effect depends on that")
""",
            "impact": (
                "When reviewing a proposal, rewrite every 'X× fewer queries' into 'X× fewer queries, each costing Y "
                "seconds on hardware Z'. If Y and Z are absent, the claim is incomplete. This is the single most useful "
                "question a risk executive can ask."
            ),
        },
        {
            "title": "Why a quadratic speedup can vanish after constant factors",
            "why": (
                "A fault-tolerant quantum computer runs logical operations orders of magnitude slower than a CPU core "
                "runs floating-point operations, and error correction multiplies physical resources. A quadratic "
                "speedup must first pay that tax. Published analyses argue that quadratic speedups need very large "
                "problem sizes or long runtimes to win {{c:p3_babbush}}."
            ),
            "how": r"""
Let classical cost $T_c(\varepsilon)=t_c\,(\sigma/\varepsilon)^2$ and quantum cost $T_q(\varepsilon)=t_q\,k/\varepsilon$
(with $t_q$ = seconds per oracle query = depth × logical cycle time, $k$ a constant from the estimator).
Crossover: $T_c=T_q \Rightarrow \varepsilon^* = t_c\sigma^2/(t_q k)$. Quantum wins only for $\varepsilon<\varepsilon^*$.

If $t_q/t_c = 10^8$ (e.g. 10⁴ logical layers per query at 1 μs per layer = 10 ms per query, vs 10⁻¹⁰ s per vectorised MC sample),
$\varepsilon^* \sim 10^{-8}\sigma^2/k$: far below any precision a desk needs. {{c:p3_crossover}}
Parallelism also favours classical: $P$ CPU cores divide $T_c$ by $P$; a single QPU does not divide $T_q$ the same way.
""",
            "code": """def crossover_eps(t_c, t_q, sigma=1.0, k=1.0):
    return t_c*sigma**2/(t_q*k)
for t_q in [1e-6, 1e-4, 1e-2]:
    print(f"t_q={t_q:.0e}s/query, t_c=1e-9 s/sample -> eps* = {crossover_eps(1e-9, t_q):.1e}")
""",
            "impact": (
                "This is the core of the honest answer to 'when will quantum price our book?'. You can turn it into a "
                "trigger list: if logical clock rates reach X and oracle depth falls to Y, the crossover enters the "
                "precision range our desks use; until then, invest in readiness and PQC, not pricing pilots. (Judgement {{c:p3_judgement}})"
            ),
        },
    ],
    "lens": {
        "look": "Separate every claim into (query count) × (cost per query) × (parallelism), and compute the crossover precision explicitly.",
        "decision": "Whether a quantum speedup claim is relevant to a client's workload in a stated time horizon.",
        "justified": "Asymptotic statements cannot be priced. Converting to seconds and money is the only way to compare with a production engine.",
        "mistakes": [
            "Treating quadratic and exponential speedups as interchangeable.",
            "Comparing query counts without per-query cost.",
            "Ignoring classical parallelism (GPUs, grids) while assuming a single QPU.",
            "Using physical gate times instead of logical cycle times for fault-tolerant algorithms.",
            "Assuming the oracle is free ('given an oracle...').",
        ],
        "impact": "Pilots funded on a speedup that cannot materialise at relevant precision; credibility loss with the board when the arithmetic is redone.",
        "test": "Lab P3: compute and plot classical vs quantum time-to-precision across per-query costs, and find the crossover precision.",
    },
    "claims": [
        {"id": "p3_babbush", "tag": "S", "text": "Babbush et al. argue quadratic speedups are unlikely to give practical advantage on early fault-tolerant machines given error-correction overheads.",
         "source": {"title": "Focus beyond quadratic speedups for error-corrected quantum advantage", "publisher": "PRX Quantum 2, 010103 (Babbush, McClean, Newman, Gidney, Boixo, Neven)", "date": "2021-03", "url": "https://doi.org/10.1103/PRXQuantum.2.010103"},
         "last_verified": "2026-10-19"},
        {"id": "p3_crossover", "tag": "M", "text": "With t_c=1e-10 s/sample, t_q=1e-2 s/query, σ=k=1, crossover precision ε* = 1e-8.",
         "check": "eps=1e-10*1/(1e-2*1)\nassert abs(eps-1e-8)<1e-20"},
        {"id": "p3_judgement", "tag": "J", "text": "Until logical clock rates and oracle depths move materially, client spend is better directed at readiness and PQC than pricing pilots."},
    ],
    "lab": {
        "id": "p3_lab",
        "title": "Time-to-precision crossover: classical MC vs idealised QAE",
        "hypothesis": (
            "H1: with σ=1, k=π (a conservative QAE constant), t_c=1e-9 s per MC sample on one core, and per-query "
            "times from 1e-6 to 1e-1 s, the crossover precision ε* is below 1e-3 for every t_q ≥ 1e-5 s. "
            "H2: giving classical 64 cores moves ε* down by exactly 64×."
        ),
        "thresholds": "ε* < 1e-3 for all t_q ≥ 1e-5 s; ratio of ε* (1 core / 64 cores) = 64 ± 1e-9.",
        "data": "Analytic cost model; parameters stated in code. No market data.",
        "code": r'''import numpy as np, pandas as pd
import plotly.graph_objects as go
from qlab_helpers import show, record, table

sigma, k, t_c = 1.0, np.pi, 1e-9
eps = np.logspace(-1, -8, 200)
t_qs = [1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1]
fig = go.Figure()
fig.add_trace(go.Scatter(x=eps, y=t_c*(sigma/eps)**2, name="classical MC, 1 core", line=dict(width=3)))
fig.add_trace(go.Scatter(x=eps, y=t_c*(sigma/eps)**2/64, name="classical MC, 64 cores", line=dict(width=3, dash="dash")))
rows = []
for t_q in t_qs:
    fig.add_trace(go.Scatter(x=eps, y=t_q*k/eps, name=f"QAE, {t_q:.0e} s/query"))
    e1 = t_c*sigma**2/(t_q*k); e64 = e1/64
    rows.append({"t_q (s/query)": t_q, "eps* vs 1 core": e1, "eps* vs 64 cores": e64, "ratio": e1/e64})
fig.update_layout(xaxis_type="log", yaxis_type="log", xaxis_autorange="reversed",
                  xaxis_title="target precision ε (absolute, σ=1)", yaxis_title="seconds to reach ε",
                  title="Crossover: quantum wins only to the right of where its line dips below classical")
show(fig)
df = pd.DataFrame(rows); table(df, "Crossover precision ε* = t_c σ² / (t_q k)")
record("max_eps_star_for_tq_ge_1e-5", float(df[df["t_q (s/query)"] >= 1e-5]["eps* vs 1 core"].max()))
record("core_ratio", float(df["ratio"].iloc[0]))
print(df.to_string(index=False))
''',
        "expect": {"max_eps_star_for_tq_ge_1e-5": "x < 1e-3", "core_ratio": "abs(x-64) < 1e-6"},
        "report_hints": "Translate ε* into basis points of notional for a real desk. Be explicit that the model ignores error-correction overheads beyond t_q.",
    },
    "quiz": [
        {"id": "p3q1", "type": "mc", "q": "Grover search gives which kind of speedup over classical unstructured search?",
         "options": ["Exponential", "Quadratic", "Linear", "None"], "answer": 1, "explain": "O(N) → O(√N) queries.", "tags": ["speedups"]},
        {"id": "p3q2", "type": "mc", "q": "Shor's algorithm vs the best known classical factoring algorithm is:",
         "options": ["Quadratic", "Super-polynomial (exponential-type)", "Constant factor", "None"], "answer": 1,
         "explain": "Polynomial vs sub-exponential GNFS.", "tags": ["speedups"]},
        {"id": "p3q3", "type": "mc", "q": "In query complexity, which cost is ignored?",
         "options": ["Number of oracle calls", "Cost of implementing one oracle call", "Number of measurements", "Classical post-processing of counts only"],
         "answer": 1, "explain": "Query complexity counts calls, not their gate cost.", "tags": ["oracles"]},
        {"id": "p3q4", "type": "mc", "q": "Crossover precision ε* = t_c σ² / (t_q k). If per-query time t_q rises 10×, ε*:",
         "options": ["Rises 10×", "Falls 10×", "Falls 100×", "Unchanged"], "answer": 1, "explain": "Inversely proportional to t_q.", "tags": ["crossover"]},
        {"id": "p3q5", "type": "mc", "q": "Classical parallelism over P cores affects the crossover by:",
         "options": ["Nothing", "Dividing ε* by P (quantum must reach finer precision to win)", "Multiplying ε* by P", "Dividing ε* by √P"],
         "answer": 1, "explain": "T_c/P shifts the classical curve down.", "tags": ["crossover"]},
        {"id": "p3q6", "type": "mc", "q": "10⁶·√N < N requires N greater than:", "options": ["10⁶", "10⁹", "10¹²", "10¹⁸"], "answer": 2,
         "explain": "√N > 10⁶ ⇒ N > 10¹².", "tags": ["constants"]},
        {"id": "p3q7", "type": "mc", "q": "For fault-tolerant algorithms, per-query time is driven by:",
         "options": ["Physical gate time only", "Oracle logical depth × logical cycle time", "Number of physical qubits", "Shots"],
         "answer": 1, "explain": "Logical depth times logical clock period.", "tags": ["oracles"]},
        {"id": "p3q8", "type": "mc", "q": "'Given an oracle for f' in a paper should make you ask:",
         "options": ["Nothing", "How many gates, qubits and how much data loading that oracle needs", "Whether f is convex", "Which language it is written in"],
         "answer": 1, "explain": "The oracle's cost is the real cost.", "tags": ["oracles"]},
        {"id": "p3q9", "type": "mc", "q": "Which statement is correct?",
         "options": ["A quadratic speedup always wins for large enough N, so it is always valuable", "A quadratic speedup wins only beyond a crossover that may lie outside practical sizes or precisions", "Quadratic speedups are exponential speedups in disguise", "Constants don't matter for quantum"],
         "answer": 1, "explain": "Asymptotic win ≠ practical win.", "tags": ["constants"]},
        {"id": "p3q10", "type": "mc", "q": "QAE's query count to reach precision ε is O(?)", "options": ["1/ε²", "1/ε", "log(1/ε)", "1/√ε"], "answer": 1,
         "explain": "Quadratic improvement on MC's 1/ε².", "tags": ["speedups"]},
        {"id": "p3q11", "type": "short", "q": "Rewrite this claim into a testable one: 'Our algorithm needs 1000× fewer queries than Monte Carlo.'",
         "must": [["per query", "per-query", "cost per", "time per", "each"], ["second", "time", "wall", "clock"], ["baseline", "variance", "optimised", "optimized", "precision"]],
         "explain": "Need per-query cost on named hardware, time to a stated precision, and against an optimised baseline.", "tags": ["oracles"]},
        {"id": "p3q12", "type": "short", "q": "Why does PQC deserve budget now even if quantum pricing is decades away?",
         "must": [["shor", "exponential"], ["harvest", "store now", "decrypt later", "migration time", "mosca"]],
         "explain": "Shor's speedup is exponential; harvest-now-decrypt-later and long migration times create exposure today.", "tags": ["speedups"]},
    ],
    "exercise": {
        "id": "p3_ex",
        "title": "A crossover calculator",
        "prompt": (
            "Implement:\n1. `mc_time(eps, sigma, t_c, cores=1)` seconds for plain MC to reach RMSE eps.\n"
            "2. `qae_time(eps, t_q, k=1.0)` seconds for ideal QAE.\n3. `crossover_eps(t_c, t_q, sigma=1, k=1, cores=1)`.\n"
            "4. `max_query_time_for_target(eps, sigma, t_c, k=1, cores=1)` the largest t_q at which QAE still beats MC at precision eps."
        ),
        "starter": '''def mc_time(eps, sigma, t_c, cores=1):
    raise NotImplementedError

def qae_time(eps, t_q, k=1.0):
    raise NotImplementedError

def crossover_eps(t_c, t_q, sigma=1.0, k=1.0, cores=1):
    raise NotImplementedError

def max_query_time_for_target(eps, sigma, t_c, k=1.0, cores=1):
    raise NotImplementedError
''',
        "solution": '''def mc_time(eps, sigma, t_c, cores=1):
    return t_c*(sigma/eps)**2/cores

def qae_time(eps, t_q, k=1.0):
    return t_q*k/eps

def crossover_eps(t_c, t_q, sigma=1.0, k=1.0, cores=1):
    return t_c*sigma**2/(t_q*k*cores)

def max_query_time_for_target(eps, sigma, t_c, k=1.0, cores=1):
    return mc_time(eps, sigma, t_c, cores)*eps/k
''',
        "tests": '''import math

def test_mc_time():
    """1e-9 s/sample, sigma=1, eps=1e-3 -> 1e-3 s"""
    assert math.isclose(mc_time(1e-3, 1.0, 1e-9), 1e-3)
    assert math.isclose(mc_time(1e-3, 1.0, 1e-9, cores=10), 1e-4)

def test_qae_time():
    assert math.isclose(qae_time(1e-3, 1e-2, k=2), 20.0)

def test_crossover_consistency():
    """At eps*, times are equal"""
    e = crossover_eps(1e-9, 1e-3, sigma=2, k=3, cores=4)
    assert math.isclose(mc_time(e, 2, 1e-9, 4), qae_time(e, 1e-3, 3), rel_tol=1e-9)

def test_max_query_time():
    """QAE with exactly max t_q ties MC"""
    tq = max_query_time_for_target(1e-4, 1.0, 1e-9, k=2, cores=8)
    assert math.isclose(qae_time(1e-4, tq, 2), mc_time(1e-4, 1.0, 1e-9, 8), rel_tol=1e-9)
''',
    },
    "cards": [
        {"front": "Grover speedup", "back": "Quadratic: O(N) → O(√N) queries", "kind": "definition"},
        {"front": "Shor speedup", "back": "Super-polynomial vs best known classical factoring (GNFS)", "kind": "definition"},
        {"front": "QAE vs MC query scaling", "back": "O(1/ε) vs O(1/ε²)", "kind": "formula"},
        {"front": "Crossover precision", "back": "ε* = t_c σ² / (t_q k · cores)", "kind": "formula"},
        {"front": "Per-query time in FT quantum", "back": "oracle logical depth × logical cycle time", "kind": "formula"},
        {"front": "Query complexity ignores…", "back": "the cost of each oracle call", "kind": "mistake"},
        {"front": "10⁶√N < N when", "back": "N > 10¹²", "kind": "number"},
        {"front": "Babbush et al. 2021 (PRX Quantum)", "back": "Focus beyond quadratic speedups: FT overheads swamp quadratic gains for modest sizes", "kind": "definition"},
        {"front": "Mistake: ignoring classical parallelism", "back": "P cores divide classical time; crossover shifts by P", "kind": "mistake"},
        {"front": "Oracle", "back": "Black-box unitary encoding the problem; its gate cost is the real cost", "kind": "definition"},
    ],
    "defend": {
        "persona": "cro",
        "questions": [
            {"q": "Is quantum pricing 'exponentially faster'?",
             "must": [["no", "not"], ["quadratic"]], "model": "No. Amplitude estimation offers a quadratic speedup in query count. Exponential speedups (Shor) apply to cryptography, not to pricing."},
            {"q": "Give me the one formula that decides whether this is worth it.",
             "must": [["t_c", "classical time", "per sample"], ["t_q", "per query", "quantum time"], ["precision", "epsilon", "ε"]],
             "model": "Crossover precision ε* = t_c σ² / (t_q k · cores). Quantum wins only for precision finer than ε*."},
            {"q": "What's the per-query time you assumed and where did it come from?",
             "must": [["depth", "logical"], ["clock", "cycle"], ["source", "estimate", "paper", "assum"]],
             "model": "Oracle logical depth from a resource estimate × logical cycle time from a sourced hardware projection, with a sensitivity range."},
            {"q": "My grid has 10,000 cores. Does that change your answer?",
             "must": [["yes"], ["divide", "parallel", "10,000", "10000", "cores"]],
             "model": "Yes. Classical time divides by ~10,000, pushing ε* down 10,000× and making the crossover harder to reach."},
            {"q": "So should I fund anything?",
             "must": [["pqc", "cryptograph", "readiness"], ["trigger", "monitor", "watch", "stop rule"]],
             "model": "Fund PQC now; for quantum computation, fund readiness and monitoring against explicit triggers (clock rates, oracle depth), not production pilots."},
        ],
    },
    "glossary": {
        "Query complexity": "Number of oracle calls an algorithm makes.",
        "Oracle": "Black-box unitary encoding a function or distribution.",
        "Quadratic speedup": "Cost reduced from O(N) to O(√N) (or 1/ε² to 1/ε).",
        "Crossover": "Problem size or precision beyond which one method becomes cheaper.",
    },
}
