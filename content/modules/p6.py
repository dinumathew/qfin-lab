MODULE = {
    "summary": (
        "Quantum-finance results are fragile: they move with library versions, transpiler seeds and random seeds. "
        "This module sets the research-engineering standard used in every lab: pinned environments, explicit seeds "
        "(including seed_transpiler), profiling before optimising, unit tests with stated tolerances, and machine-readable "
        "run records. It is also the standard a model validator will hold your pilot to."
    ),
    "concepts": [
        {
            "title": "Environments, pinning and version reporting",
            "why": (
                "Qiskit changes fast: 1.0 removed `execute()`, 2.x removed Pulse and older backend interfaces (Track Q1). A "
                "notebook that ran last year may fail or, worse, run and give different resource counts. Without pinned "
                "versions you cannot reproduce or defend a result."
            ),
            "how": r"""
* One virtual environment per project (`python -m venv .venv`).
* Pin with compatible-release specifiers in `requirements.txt` (`qiskit==2.6.*`) and freeze exact versions per run (`pip freeze > lock.txt`).
* Every run record stores `importlib.metadata.version(pkg)` for the key packages, Python version and platform.
* Read deprecation warnings: they are scheduled breakages.
""",
            "code": """from importlib import metadata
import sys, platform
for p in ["qiskit", "qiskit-aer", "numpy", "scipy"]:
    print(f"{p:12s} {metadata.version(p)}")
print("python", sys.version.split()[0], "|", platform.system())
""",
            "impact": (
                "In a client pilot, 'which version produced the number in the board memo?' must have an answer. Version "
                "records are the cheapest model-risk control you will ever implement."
            ),
        },
        {
            "title": "Seeds and reproducibility: NumPy, simulators and the transpiler",
            "why": (
                "Three sources of randomness move quantum results: sampling (shots), simulator noise, and the transpiler's "
                "stochastic layout and routing. Forgetting `seed_transpiler` is the commonest reason resource counts don't "
                "replicate {{c:p6_seeded}}."
            ),
            "how": r"""
* NumPy: `rng = np.random.default_rng(seed)`; never the global `np.random.seed` in library code.
* Independent streams for parallel workers: `np.random.SeedSequence(seed).spawn(k)`.
* Qiskit: `transpile(qc, backend, seed_transpiler=s, optimization_level=L)`; Aer: `seed_simulator=s`; Sampler V2: `SamplerV2(seed=s)`.
* Report the seed with every number; for statistical claims run **many** seeds (≥30) and report the distribution, not one lucky seed.
""",
            "code": """import numpy as np
ss = np.random.SeedSequence(1234)
streams = [np.random.default_rng(s) for s in ss.spawn(3)]
print([round(r.standard_normal(), 4) for r in streams])
print([round(np.random.default_rng(s).standard_normal(), 4) for s in np.random.SeedSequence(1234).spawn(3)])
""",
            "impact": (
                "Reproducibility is a validation requirement (SR 11-7 expects replicable results). Seed discipline also "
                "protects you from yourself: a result that only appears for one seed is noise, and your client will find out."
            ),
        },
        {
            "title": "Profiling and vectorisation",
            "why": (
                "Your classical baseline must be optimised before comparison (lab framework step 3). A Python loop baseline "
                "can be 100× slower than vectorised NumPy, which would fabricate a 'quantum advantage' of 100× {{c:p6_vec}}."
            ),
            "how": r"""
* Measure first: `time.perf_counter` for wall time, `timeit` for micro-benchmarks, `cProfile` to find hotspots.
* Vectorise across paths/scenarios; avoid Python loops in inner kernels; use float64 unless you have measured float32 is enough.
* Report the median of repeated timings, with the machine described.
""",
            "code": """import numpy as np, time
z = np.random.default_rng(0).standard_normal(1_000_000)
t=time.perf_counter(); s=0.0
for x in z[:100_000]: s += max(100*np.exp(0.2*x)-100, 0)
loop=(time.perf_counter()-t)*10
t=time.perf_counter(); v=np.maximum(100*np.exp(0.2*z)-100,0).sum(); vec=time.perf_counter()-t
print(f"loop (extrapolated) {loop:.2f}s  vectorised {vec:.4f}s  ratio {loop/vec:.0f}x")
""",
            "impact": "Any benchmark you show a client must survive the question 'did you optimise the classical side?'. If the answer is no, the result is void.",
        },
        {
            "title": "Unit tests with stated tolerances, and run records",
            "why": (
                "Quantum code is tested at toy size against exact answers. A test without a stated tolerance is either "
                "flaky (too tight) or useless (too loose). A result without a machine-readable record cannot be audited."
            ),
            "how": r"""
* `pytest`; `np.testing.assert_allclose(x, ref, rtol, atol)`; state *why* the tolerance is what it is (float rounding ~1e-12; shot noise ~3/√shots).
* Statistical tests: assert within $k$ standard errors, not equality.
* Run record (JSON): code hash or text, seeds, versions, parameters, outputs, wall time, timestamp. Save transpiled circuits with QPY (`qiskit.qpy.dump`) so counts can be re-inspected.
""",
            "code": """import json, numpy as np, io
from qiskit import QuantumCircuit, qpy
qc = QuantumCircuit(2); qc.h(0); qc.cx(0, 1)
buf = io.BytesIO(); qpy.dump(qc, buf); buf.seek(0)
assert qpy.load(buf)[0] == qc
shots, p_hat, p = 4000, 0.507, 0.5
se = np.sqrt(p*(1-p)/shots)
print("within 3 SE:", abs(p_hat-p) < 3*se, "| SE =", round(se, 4))
print(json.dumps({"seed": 7, "shots": shots, "p_hat": p_hat}))
""",
            "impact": "A complete run record turns 'trust me' into 'rerun it'. It is what lets a client's validation team sign off a pilot in weeks rather than months.",
        },
    ],
    "lens": {
        "look": "For any result: which versions, which seeds, which optimisation level, which hardware/simulator, how many repeats, what tolerance, and is the baseline optimised?",
        "decision": "Whether a result is reproducible enough to be reported to a client or a validator.",
        "justified": "Irreproducible numbers carry unquantified model risk; reproducibility is cheap to build in and expensive to retrofit.",
        "mistakes": [
            "No seed_transpiler: CX counts change between runs.",
            "Global np.random.seed in library code, coupling unrelated streams.",
            "Unoptimised classical baseline (Python loops).",
            "Exact-equality tests on floats; or tolerances so loose bugs pass.",
            "Results saved as screenshots instead of JSON + QPY.",
        ],
        "impact": "Unreplicable pilot numbers, failed validation, and inflated advantage claims that collapse under review.",
        "test": "Lab P6: show seeded vs unseeded transpilation variability, measure loop vs vectorised timing, and export a run record.",
    },
    "claims": [
        {"id": "p6_seeded", "tag": "M", "text": "With a fixed seed_transpiler, repeated transpilation of the same circuit to a fake backend gives identical CX counts.",
         "check": """from qiskit import transpile
from qiskit.circuit.random import random_circuit
from qiskit_ibm_runtime.fake_provider import FakeManilaV2
qc=random_circuit(5,6,seed=3); b=FakeManilaV2()
c={transpile(qc,b,seed_transpiler=11,optimization_level=3).count_ops().get('cx',0) for _ in range(5)}
assert len(c)==1, c"""},
        {"id": "p6_vec", "tag": "M", "text": "A Python-loop payoff evaluation is at least 20× slower than vectorised NumPy on 100,000 paths.",
         "check": """import numpy as np, time
z=np.random.default_rng(0).standard_normal(100000)
t=time.perf_counter(); s=0.0
for x in z: s+=max(100*np.exp(.2*x)-100,0)
a=time.perf_counter()-t; t=time.perf_counter(); np.maximum(100*np.exp(.2*z)-100,0).sum(); b=time.perf_counter()-t
assert a/b>20, a/b"""},
        {"id": "p6_qiskit_seed_doc", "tag": "S", "text": "transpile() exposes seed_transpiler to fix stochastic passes.",
         "source": {"title": "qiskit.compiler.transpile (API reference)", "publisher": "IBM Quantum / Qiskit documentation", "date": "2026 (Qiskit 2.x docs)", "url": "https://quantum.cloud.ibm.com/docs/en/api/qiskit/compiler"},
         "time_sensitive": True, "last_verified": "2026-10-19"},
    ],
    "lab": {
        "id": "p6_lab",
        "title": "Reproducibility audit: transpiler seeds, NumPy streams, and an optimised baseline",
        "hypothesis": (
            "H1: with seed_transpiler fixed, 20 transpilations of a random 5-qubit circuit to FakeManilaV2 at optimisation level 3 give exactly 1 distinct CX count. "
            "H2: the vectorised payoff kernel is ≥20× faster than the loop. H3: two runs with the same SeedSequence produce identical draws."
        ),
        "thresholds": "H1 distinct counts = 1; H2 ratio ≥ 20; H3 exact equality.",
        "data": "Random circuit (seeded) and synthetic normals.",
        "code": r'''import numpy as np, pandas as pd, time, json
import plotly.graph_objects as go
from qiskit import transpile
from qiskit.circuit.random import random_circuit
from qiskit_ibm_runtime.fake_provider import FakeManilaV2
from qlab_helpers import SEED, show, record, table

qc = random_circuit(5, 8, seed=SEED % 1000, max_operands=2)
backend = FakeManilaV2()
seeded = [transpile(qc, backend, seed_transpiler=SEED, optimization_level=3).count_ops().get("cx", 0) for _ in range(20)]
unseeded = [transpile(qc, backend, optimization_level=3).count_ops().get("cx", 0) for _ in range(20)]
by_seed = [transpile(qc, backend, seed_transpiler=s, optimization_level=3).count_ops().get("cx", 0) for s in range(30)]
fig = go.Figure()
fig.add_trace(go.Histogram(x=by_seed, name="30 different seeds"))
fig.add_trace(go.Histogram(x=unseeded, name="20 unseeded runs"))
fig.update_layout(barmode="overlay", title="CX count after transpilation depends on the seed", xaxis_title="CX count")
show(fig)
table(pd.DataFrame({"setting": ["fixed seed x20", "unseeded x20", "seeds 0..29"],
                    "distinct CX counts": [len(set(seeded)), len(set(unseeded)), len(set(by_seed))],
                    "min": [min(seeded), min(unseeded), min(by_seed)], "max": [max(seeded), max(unseeded), max(by_seed)]}),
      "Transpiler reproducibility")
record("distinct_seeded", len(set(seeded)))
record("cx_range_over_seeds", [min(by_seed), max(by_seed)])

z = np.random.default_rng(SEED).standard_normal(200_000)
t = time.perf_counter(); s = 0.0
for x in z[:20_000]: s += max(100*np.exp(0.2*x) - 100, 0)
loop = (time.perf_counter() - t)*10
t = time.perf_counter(); np.maximum(100*np.exp(0.2*z) - 100, 0).sum(); vec = time.perf_counter() - t
record("loop_over_vectorised", loop/vec)
a = [np.random.default_rng(s).standard_normal(3).tolist() for s in np.random.SeedSequence(SEED).spawn(2)]
b = [np.random.default_rng(s).standard_normal(3).tolist() for s in np.random.SeedSequence(SEED).spawn(2)]
record("seedsequence_reproducible", a == b)
print("seeded distinct:", len(set(seeded)), "| CX over seeds:", min(by_seed), "-", max(by_seed), "| loop/vec:", round(loop/vec))
''',
        "expect": {"distinct_seeded": "x == 1", "loop_over_vectorised": "x >= 20", "seedsequence_reproducible": "x is True"},
        "report_hints": "Report the CX range across seeds; that range is a tolerance you must quote when replicating I5–I7 counts.",
    },
    "quiz": [
        {"id": "p6q1", "type": "mc", "q": "Which argument fixes stochastic layout/routing in Qiskit's transpile?", "options": ["seed_simulator", "seed_transpiler", "random_seed", "optimization_level"], "answer": 1,
         "explain": "seed_transpiler.", "tags": ["seeds"]},
        {"id": "p6q2", "type": "mc", "q": "Best way to give 8 parallel workers independent random streams:", "options": ["np.random.seed(i)", "SeedSequence(seed).spawn(8)", "Same seed for all", "time-based seeds"], "answer": 1,
         "explain": "SeedSequence.spawn gives statistically independent streams.", "tags": ["seeds"]},
        {"id": "p6q3", "type": "mc", "q": "`qiskit==2.6.*` in requirements means:", "options": ["Exactly 2.6.0", "Any 2.6.x patch release", "Any 2.x", "Latest"], "answer": 1, "explain": "Compatible patch releases.", "tags": ["pinning"]},
        {"id": "p6q4", "type": "mc", "q": "A good tolerance for comparing a 4000-shot probability estimate with its exact value is about:", "options": ["1e-12", "3·√(p(1−p)/4000)", "0.5", "0"], "answer": 1,
         "explain": "A few standard errors of shot noise.", "tags": ["testing"]},
        {"id": "p6q5", "type": "mc", "q": "To save a transpiled circuit for later inspection, use:", "options": ["pickle only", "QPY (qiskit.qpy.dump)", "A screenshot", "print(qc)"], "answer": 1, "explain": "QPY is Qiskit's serialisation format.", "tags": ["records"]},
        {"id": "p6q6", "type": "mc", "q": "Why profile before optimising?", "options": ["It's tradition", "To find the actual hotspot instead of guessing", "Profilers make code faster", "Required by Qiskit"], "answer": 1, "explain": "Measure first.", "tags": ["profiling"]},
        {"id": "p6q7", "type": "mc", "q": "Reporting a single seed's result for a stochastic algorithm is:", "options": ["Fine if it looks good", "Insufficient: report the distribution over many seeds", "Required", "Better than many seeds"], "answer": 1,
         "explain": "Distributions, not anecdotes.", "tags": ["seeds"]},
        {"id": "p6q8", "type": "mc", "q": "Which is NOT part of a complete run record?", "options": ["Seeds", "Library versions", "Outputs", "The IDE theme used"], "answer": 3, "explain": "Seeds, versions and outputs are required; the IDE is irrelevant.", "tags": ["records"]},
        {"id": "p6q9", "type": "mc", "q": "Deprecation warnings in Qiskit should be:", "options": ["Silenced", "Read: they announce future breakage", "Ignored", "Treated as errors only in production"], "answer": 1, "explain": "Read them (Track Q1).", "tags": ["pinning"]},
        {"id": "p6q10", "type": "mc", "q": "A Python-loop classical baseline compared with a quantum method mostly measures:", "options": ["Quantum advantage", "Python interpreter overhead", "Hardware noise", "Nothing"], "answer": 1, "explain": "Optimise the baseline first.", "tags": ["profiling"]},
        {"id": "p6q11", "type": "short", "q": "List the fields you would put in a run record for a QAE pilot result.",
         "must": [["seed"], ["version"], ["optimi", "optimization_level", "transpile"], ["output", "result", "estimate"], ["shots", "backend", "simulator", "hardware"]],
         "explain": "Seeds (sim + transpiler), versions, transpile settings, backend/shots, outputs, timing.", "tags": ["records"]},
        {"id": "p6q12", "type": "short", "q": "Why must replication targets for CX counts come with a tolerance?",
         "must": [["seed", "transpiler", "stochastic", "random"], ["version", "optimization", "optimisation", "level"]],
         "explain": "Counts vary with transpiler seed, optimisation level and library version.", "tags": ["seeds"]},
    ],
    "exercise": {
        "id": "p6_ex",
        "title": "Reproducibility utilities",
        "prompt": (
            "Implement:\n1. `spawn_rngs(seed, k)` → list of k independent numpy Generators.\n"
            "2. `within_se(estimate, p, shots, k=3)` → True if |estimate − p| ≤ k·√(p(1−p)/shots).\n"
            "3. `run_record(label, seed, params, outputs)` → dict with keys label, seed, params, outputs, versions (qiskit, numpy) and timestamp.\n"
            "4. `vectorised_call_payoff(S0, K, r, sigma, T, z)` → discounted payoffs for an array z (no Python loops)."
        ),
        "starter": '''import numpy as np

def spawn_rngs(seed, k):
    raise NotImplementedError

def within_se(estimate, p, shots, k=3):
    raise NotImplementedError

def run_record(label, seed, params, outputs):
    raise NotImplementedError

def vectorised_call_payoff(S0, K, r, sigma, T, z):
    raise NotImplementedError
''',
        "solution": '''import numpy as np, time
from importlib import metadata

def spawn_rngs(seed, k):
    return [np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(k)]

def within_se(estimate, p, shots, k=3):
    return abs(estimate - p) <= k*np.sqrt(p*(1-p)/shots)

def run_record(label, seed, params, outputs):
    return {"label": label, "seed": seed, "params": params, "outputs": outputs,
            "versions": {p: metadata.version(p) for p in ("qiskit", "numpy")},
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")}

def vectorised_call_payoff(S0, K, r, sigma, T, z):
    z = np.asarray(z)
    return np.exp(-r*T)*np.maximum(S0*np.exp((r - sigma**2/2)*T + sigma*np.sqrt(T)*z) - K, 0.0)
''',
        "tests": '''import numpy as np, json, inspect

def test_spawn_independent_and_reproducible():
    a = [g.standard_normal() for g in spawn_rngs(5, 3)]
    b = [g.standard_normal() for g in spawn_rngs(5, 3)]
    assert a == b and len(set(a)) == 3

def test_within_se():
    assert within_se(0.51, 0.5, 4000) and not within_se(0.55, 0.5, 4000)

def test_run_record():
    r = run_record("x", 7, {"shots": 10}, {"p": 0.5})
    for k in ("label", "seed", "params", "outputs", "versions", "timestamp"):
        assert k in r
    assert "qiskit" in r["versions"]
    json.dumps(r)

def test_vectorised():
    z = np.array([-1.0, 0.0, 2.0])
    out = vectorised_call_payoff(100, 100, 0.0, 0.2, 1.0, z)
    assert out.shape == (3,) and out[0] == 0
    assert "for " not in inspect.getsource(vectorised_call_payoff)
''',
    },
    "cards": [
        {"front": "Fix transpiler randomness", "back": "transpile(..., seed_transpiler=s)", "kind": "definition"},
        {"front": "Fix Aer sampling randomness", "back": "seed_simulator=s (or SamplerV2(seed=s))", "kind": "definition"},
        {"front": "Independent parallel streams", "back": "np.random.SeedSequence(seed).spawn(k)", "kind": "definition"},
        {"front": "Shot-noise standard error", "back": "√(p(1−p)/shots)", "kind": "formula"},
        {"front": "Save circuits", "back": "qiskit.qpy.dump / load", "kind": "definition"},
        {"front": "Run record fields", "back": "label, code, seeds, versions, params, outputs, wall time, timestamp", "kind": "definition"},
        {"front": "Mistake: Python-loop baseline", "back": "Inflates 'advantage' by interpreter overhead; vectorise first", "kind": "mistake"},
        {"front": "Mistake: global np.random.seed", "back": "Couples streams; use Generator objects", "kind": "mistake"},
        {"front": "Mistake: one lucky seed", "back": "Report distributions over ≥30 seeds", "kind": "mistake"},
        {"front": "Compatible-release pin", "back": "pkg==2.6.* accepts 2.6.x patches", "kind": "definition"},
    ],
    "defend": {
        "persona": "validator",
        "questions": [
            {"q": "Rerun your resource count and get a different CX number. Why, and is it a problem?",
             "must": [["seed", "transpiler"], ["tolerance", "range", "report"]],
             "model": "Transpiler layout/routing is stochastic; I fix seed_transpiler and report the range across seeds as a tolerance."},
            {"q": "How do I reproduce your headline number next year?",
             "must": [["version", "lock", "pinned", "freeze"], ["seed"], ["record", "json", "qpy"]],
             "model": "Pinned and frozen versions, all seeds, JSON run record and QPY files of transpiled circuits."},
            {"q": "Was your classical comparator optimised?",
             "must": [["vector", "numpy"], ["profil", "timed", "median"]],
             "model": "Yes: vectorised NumPy with variance reduction, profiled, timed as a median over repeats on stated hardware."},
            {"q": "Your tests pass. With what tolerance, and why that one?",
             "must": [["standard error", "se", "shot"], ["float", "1e-", "rounding"]],
             "model": "Exact-statevector tests at ~1e-10 (float rounding); sampled tests within 3 standard errors of shot noise."},
            {"q": "How many seeds behind the result in your memo?",
             "must": [["30", "thirty", "many", "distribution"]],
             "model": "At least 30; the memo reports the median and CI, not the best seed."},
        ],
    },
    "glossary": {
        "seed_transpiler": "Seed for Qiskit's stochastic transpiler passes; fixes layout/routing.",
        "QPY": "Qiskit's binary serialisation format for circuits.",
        "SeedSequence": "NumPy mechanism for spawning independent random streams.",
        "Run record": "JSON capturing code, seeds, versions, parameters and outputs of a run.",
    },
}
