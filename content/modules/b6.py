MODULE = {
    "summary": (
        "Clients forward you press releases. This module gives you the vocabulary and the arithmetic to read them: "
        "hardware modalities, physical vs logical qubits, error-detected vs error-corrected logical qubits, postselection, "
        "gate fidelity, connectivity and logical clock rate. The exercise is to rewrite vendor claims in 'what was actually "
        "shown' form, which is the most frequent thing a quantum adviser is asked to do. Every hardware fact here is "
        "dated; re-verify anything older than six months."
    ),
    "concepts": [
        {
            "title": "Modalities: superconducting, trapped ion, neutral atom, photonic",
            "why": (
                "Modality determines gate speed, fidelity, connectivity and scaling route. Those, not qubit count, decide how "
                "fast a fault-tolerant algorithm runs (logical clock rate) and therefore any crossover date (A3)."
            ),
            "how": r"""
| Modality | Typical strengths | Typical constraints | Examples (dated, Sourced) |
|---|---|---|---|
| Superconducting | Fast gates (tens–hundreds of ns), mature fabrication | Nearest-neighbour connectivity, cryogenics, wiring | Google Willow, 105 qubits (Dec 2024) {{c:b6_willow}}; IBM roadmap to Starling, 200 logical qubits by 2029 {{c:b6_ibm}} |
| Trapped ion | High fidelity, all-to-all connectivity within a trap | Slower gates (~µs–ms per layer), transport overheads | Quantinuum Helios, 98 qubits, 99.921% two-qubit fidelity (Nov 2025) {{c:b6_helios}} |
| Neutral atom | Large arrays, reconfigurable connectivity | Atom loss, slower cycles | Microsoft/Atom Computing: 24 entangled logical qubits (Nov 2024) {{c:b6_atom}} |
| Photonic | Room-temperature components, networking | Probabilistic sources/gates, loss | Fusion-based architectures (no dated benchmark cited here) |

Judgement {{c:b6_modality_j}}: no modality has yet shown the combination (≥1,000 logical qubits, ≥MHz logical clock) that pricing workloads need.
""",
            "code": """# logical clock and wall time: same algorithm, different modality assumptions (illustrative, not vendor data)
t_depth = 5.4e7   # illustrative T-depth, the order the learner prompt cites for published pricing estimates; A2 verifies it
for name, rate in [("10 kHz", 1e4), ("100 kHz", 1e5), ("1 MHz", 1e6), ("10 MHz", 1e7)]:
    print(f"logical clock {name:>7}: {t_depth/rate:,.0f} s = {t_depth/rate/3600:,.2f} h per run")
""",
            "impact": "Ask every vendor for logical clock rate projections with dates, not qubit counts. A 100× slower clock turns a one-second pricing answer into minutes, which ends a trading use case.",
        },
        {
            "title": "Physical vs logical qubits; error-detected vs error-corrected; postselection",
            "why": (
                "'Logical qubit' is used loosely. An **error-detected** logical qubit flags errors and discards the run "
                "(postselection); an **error-corrected** logical qubit fixes errors in real time and keeps running. Only the "
                "second scales to long algorithms, because discarding runs costs exponentially more shots as circuits deepen."
            ),
            "how": r"""
* **Physical qubit**: a hardware device. **Logical qubit**: information encoded across many physical qubits by a code of distance $d$.
* **Error detection** (distance-2 codes, e.g. [[4,2,2]]): detects any single error, cannot locate it. Runs with a detected error are **discarded** (postselection). Acceptance rate falls like $(1-p_{\text{detect}})^{\text{#checks}}$.
* **Error correction** (distance ≥3, e.g. surface code): locates and corrects errors via repeated syndrome measurement and a real-time decoder.
* Below threshold, the logical error rate falls exponentially with $d$: $\varepsilon_L\approx A(p/p_{th})^{(d+1)/2}$. Evidence of suppression: logical error falls by a factor Λ per step $d\to d+2$; Google reported Λ ≈ 2.14 (d = 3→5→7) {{c:b6_willow}}.
* **Ratio**: surface-code overhead is ~$2d^2$ physical per logical qubit (e.g. ~1,000 at $d=23$), plus magic-state factories; qLDPC codes target lower overhead {{c:b6_ibm}}.
""",
            "code": """import numpy as np
# postselection cost: fraction of shots kept vs number of detection rounds
for p_flag in [0.01, 0.03]:
    print(f"p_flag={p_flag}: kept after 10/100/1000 rounds =", [round((1-p_flag)**r, 4) for r in (10, 100, 1000)])
# surface code logical error vs distance (A=0.1, p/p_th=0.5)
for d in [3, 5, 7, 11, 15, 25]:
    print(f"d={d:2d}: eps_L ~ {0.1*0.5**((d+1)/2):.1e}, physical/logical ~ {2*d*d}")
""",
            "impact": (
                "When a client hears '48 logical qubits', the advisory answer is: which code distance, error-detected or "
                "-corrected, what fraction of runs were discarded, for how many rounds, and what logical error rate per "
                "operation. Without those, the number is not comparable across vendors."
            ),
        },
        {
            "title": "Fidelity, connectivity and the logical clock rate",
            "why": (
                "Headline fidelities are usually best-case medians for isolated gates. What a finance circuit experiences is "
                "the layered, routed, many-gate reality. Connectivity adds SWAPs; clock rate converts depth into seconds."
            ),
            "how": r"""
* **Two-qubit gate fidelity** $F_2$: error $\epsilon_2=1-F_2$. Check whether reported as median/mean, isolated or simultaneous (crosstalk), and with or without leakage/SPAM.
* **Connectivity**: on a line or heavy-hex lattice, a CX between distant qubits costs SWAPs (3 CX each). All-to-all (ions) avoids that but usually with slower gates.
* **Logical clock rate**: syndrome-cycle time × cycles per logical operation. Surface code on superconducting hardware: ~1 µs cycles, ~$d$ cycles per logical step → ~$10^4$–$10^5$ logical ops/s before magic-state limits. Seconds per answer ≈ T-depth ÷ logical clock (A3).
""",
            "code": """from qiskit import QuantumCircuit, transpile
from qiskit.transpiler import CouplingMap
n = 8
qc = QuantumCircuit(n)
for i in range(n):
    for j in range(i+1, n): qc.cx(i, j)
line = transpile(qc, coupling_map=CouplingMap.from_line(n), basis_gates=["cx","rz","sx","x"], optimization_level=1, seed_transpiler=1)
full = transpile(qc, coupling_map=CouplingMap.from_full(n), basis_gates=["cx","rz","sx","x"], optimization_level=1, seed_transpiler=1)
print("CX all-to-all:", full.count_ops().get("cx"), "| CX on a line:", line.count_ops().get("cx"))
""",
            "impact": "Fidelity and connectivity together set the usable circuit size; the clock sets the wall time. A client roadmap needs all three, dated and sourced, per vendor.",
        },
    ],
    "lens": {
        "look": "Rewrite every hardware claim as: what was measured, on how many physical qubits, with which code and distance, detected or corrected, postselected fraction, rounds, logical error per operation, and date.",
        "decision": "Whether a hardware announcement changes a client's timeline assumptions (A3 trigger list) or not.",
        "justified": "Hardware news is frequent and marketing-led; only like-for-like metrics move a crossover date.",
        "mistakes": [
            "Comparing physical qubit counts across modalities.",
            "Treating error-detected (postselected) logical qubits as error-corrected.",
            "Quoting best-case isolated gate fidelity as circuit-level fidelity.",
            "Ignoring clock speed: high fidelity at slow gates can still be too slow for a use case.",
            "Using an undated or six-month-old hardware figure in a client deck.",
        ],
        "impact": "Timelines pulled forward on misread claims; premature pilots; credibility loss with technical client staff.",
        "test": "Lab B6: quantify postselection cost, SWAP overhead from connectivity, and circuit success vs fidelity for an I5-sized circuit; then rewrite three vendor claims.",
    },
    "claims": [
        {"id": "b6_willow", "tag": "S", "text": "Google's 105-qubit Willow processor showed surface-code logical error suppression by Λ ≈ 2.14 per distance step (3→5→7).",
         "source": {"title": "Making quantum error correction work (blog) / Quantum error correction below the surface code threshold (Nature, s41586-024-08449-y)", "publisher": "Google Quantum AI / Nature", "date": "2024-12-09", "url": "https://research.google/blog/making-quantum-error-correction-work/"},
         "time_sensitive": True, "last_verified": "2026-10-19"},
        {"id": "b6_ibm", "tag": "S", "text": "IBM roadmap: Starling, 200 logical qubits and 100 million operations by 2029, using qLDPC codes; Loon (2025), Kookaburra (2026), Cockatoo (2027) as steps.",
         "source": {"title": "IBM Offers Roadmap Toward Large-Scale, Fault-Tolerant Quantum Computer", "publisher": "The Quantum Insider (reporting IBM announcement)", "date": "2025-06-10", "url": "https://thequantuminsider.com/2025/06/10/ibm-offers-roadmap-toward-large-scale-fault-tolerant-quantum-computer/"},
         "time_sensitive": True, "last_verified": "2026-10-19"},
        {"id": "b6_helios", "tag": "S", "text": "Quantinuum Helios: 98 physical qubits, 99.921% two-qubit fidelity; claims of 48 error-corrected and 94 error-detected logical qubits.",
         "source": {"title": "Quantinuum Announces Commercial Launch of Helios", "publisher": "The Quantum Insider (reporting Quantinuum announcement)", "date": "2025-11-05", "url": "https://thequantuminsider.com/2025/11/05/quantinuum-announces-commercial-launch-of-helios-a-quantum-computer-with-accuracy-to-enable-generative-quantum-ai/"},
         "time_sensitive": True, "last_verified": "2026-10-19"},
        {"id": "b6_atom", "tag": "S", "text": "Microsoft and Atom Computing entangled 24 logical qubits; logical error 10.2% with errors and losses detected (vs 42% physical); 28 logical qubits from 112 physical for Bernstein–Vazirani.",
         "source": {"title": "Microsoft and Atom Computing offer a commercial quantum machine with the largest number of entangled logical qubits on record", "publisher": "Microsoft Azure Quantum blog", "date": "2024-11-19", "url": "https://azure.microsoft.com/en-us/blog/quantum/2024/11/19/microsoft-and-atom-computing-offer-a-commercial-quantum-machine-with-the-largest-number-of-entangled-logical-qubits-on-record/"},
         "time_sensitive": True, "last_verified": "2026-10-19"},
        {"id": "b6_modality_j", "tag": "J", "text": "No modality has publicly demonstrated ≥1,000 logical qubits with ≥MHz logical clock; pricing-class workloads need both. Re-check at each verification cycle."},
        {"id": "b6_swap", "tag": "M", "text": "An all-pairs CX circuit on 8 qubits needs more CX on a line coupling map than with all-to-all connectivity.",
         "check": """from qiskit import QuantumCircuit, transpile
from qiskit.transpiler import CouplingMap
qc=QuantumCircuit(8)
for i in range(8):
    for j in range(i+1,8): qc.cx(i,j)
b=['cx','rz','sx','x']
l=transpile(qc,coupling_map=CouplingMap.from_line(8),basis_gates=b,optimization_level=1,seed_transpiler=1).count_ops()['cx']
f=transpile(qc,coupling_map=CouplingMap.from_full(8),basis_gates=b,optimization_level=1,seed_transpiler=1).count_ops()['cx']
assert l>f,(l,f)"""},
    ],
    "lab": {
        "id": "b6_lab",
        "title": "Read hardware claims with numbers: postselection, connectivity and fidelity",
        "hypothesis": (
            "H1: with a 2% per-round detection-flag probability, fewer than 15% of shots survive 100 rounds of postselection. "
            "H2: routing a random 8-qubit, depth-20 circuit to a line coupling map increases CX count by ≥50% vs all-to-all (seed fixed). "
            "H3: for a 620-CX circuit, two-qubit fidelity must be ≥ 99.98% for ≥90% circuit success."
        ),
        "thresholds": "H1 survival < 0.15; H2 ratio ≥ 1.5; H3 required fidelity ≥ 0.9998.",
        "data": "Analytic models and synthetic circuits. Vendor figures used only in the written exercise, each with date and source.",
        "code": r'''import numpy as np, pandas as pd
import plotly.graph_objects as go
from qiskit import transpile
from qiskit.circuit.random import random_circuit
from qiskit.transpiler import CouplingMap
from qlab_helpers import SEED, show, record, table

rounds = np.arange(0, 301, 10)
fig = go.Figure()
for p in [0.005, 0.01, 0.02, 0.05]:
    fig.add_trace(go.Scatter(x=rounds, y=(1-p)**rounds, name=f"flag prob {p}/round"))
fig.update_layout(title="Postselection: fraction of shots kept", xaxis_title="detection rounds", yaxis_title="kept", yaxis_type="log")
show(fig)
record("survival_2pct_100", float(0.98**100))

qc = random_circuit(8, 20, max_operands=2, seed=SEED % 997)
b = ["cx", "rz", "sx", "x"]
rows = []
for name, cmap in [("all-to-all", CouplingMap.from_full(8)), ("heavy-hex-like ring", CouplingMap.from_ring(8)), ("line", CouplingMap.from_line(8))]:
    t = transpile(qc, coupling_map=cmap, basis_gates=b, optimization_level=1, seed_transpiler=SEED)
    rows.append({"connectivity": name, "cx": t.count_ops().get("cx", 0), "depth": t.depth()})
df = pd.DataFrame(rows); df["cx vs all-to-all"] = df.cx/df.cx.iloc[0]
table(df, "Connectivity overhead (same circuit, same seed)")
record("line_over_full_cx", float(df["cx vs all-to-all"].iloc[-1]))

cx_counts = [100, 620, 1467, 3041, 10000]
req = pd.DataFrame({"CX count": cx_counts, "F2 for 90% success": [0.9**(1/n) for n in cx_counts], "F2 for 50% success": [0.5**(1/n) for n in cx_counts]})
table(req, "Required two-qubit fidelity (product rule)")
record("f2_needed_620", float(0.9**(1/620)))
print(df.to_string(index=False)); print(req.to_string(index=False))
''',
        "expect": {"survival_2pct_100": "x < 0.15", "f2_needed_620": "x >= 0.9998"},
        "report_hints": (
            "Use the report's section 9 for the exercise: take three vendor claims (e.g. Willow Dec 2024, IBM Starling roadmap June 2025, "
            "Helios Nov 2025, or newer ones you find), and rewrite each as 'what was actually shown' with physical qubits, code, distance, "
            "detected/corrected, postselection, logical error per operation, and date. Tag each sentence Sourced or Judgement."
        ),
    },
    "quiz": [
        {"id": "b6q1", "type": "mc", "q": "An error-detected logical qubit:", "options": ["Corrects errors in real time", "Flags errors; flagged runs are discarded (postselection)", "Has no errors", "Is a physical qubit"], "answer": 1, "explain": "Detection, not correction.", "tags": ["logical"]},
        {"id": "b6q2", "type": "mc", "q": "Why does postselection not scale to long algorithms?", "options": ["It's illegal", "Kept fraction decays exponentially with rounds", "It needs more qubits", "It increases fidelity too much"], "answer": 1, "explain": "(1−p)^rounds.", "tags": ["logical"]},
        {"id": "b6q3", "type": "mc", "q": "Λ in surface-code experiments measures:", "options": ["Gate speed", "Logical error reduction factor per d→d+2", "Qubit count", "Readout fidelity"], "answer": 1, "explain": "Suppression factor.", "tags": ["qec"]},
        {"id": "b6q4", "type": "mc", "q": "Google reported Λ ≈ ? on Willow (Dec 2024)", "options": ["1.0", "2.14", "10", "0.5"], "answer": 1, "explain": "Sourced: Google Quantum AI, 2024-12-09.", "tags": ["dated"]},
        {"id": "b6q5", "type": "mc", "q": "Surface-code physical qubits per logical qubit scale as:", "options": ["d", "~2d²", "2^d", "log d"], "answer": 1, "explain": "Data + measurement qubits.", "tags": ["qec"]},
        {"id": "b6q6", "type": "mc", "q": "Trapped ions typically trade:", "options": ["Low fidelity for speed", "Slower gates for high fidelity and all-to-all connectivity", "Connectivity for cryogenics", "Nothing"], "answer": 1, "explain": "Typical modality trade-off.", "tags": ["modality"]},
        {"id": "b6q7", "type": "mc", "q": "Seconds per answer for a FT algorithm ≈", "options": ["Qubits / fidelity", "T-depth ÷ logical clock rate", "Shots × qubits", "Gate count × 1 ns"], "answer": 1, "explain": "A3 formula.", "tags": ["clock"]},
        {"id": "b6q8", "type": "mc", "q": "Required F₂ for 90% success on 620 CX ≈", "options": ["99%", "99.9%", "99.98%", "99.9999%"], "answer": 2, "explain": "0.9^(1/620) ≈ 0.99983.", "tags": ["fidelity"]},
        {"id": "b6q9", "type": "mc", "q": "A SWAP costs how many CX?", "options": ["1", "2", "3", "6"], "answer": 2, "explain": "Three CNOTs.", "tags": ["connectivity"]},
        {"id": "b6q10", "type": "mc", "q": "The right comparison across vendors is:", "options": ["Physical qubit count", "Logical error per operation, logical qubits, clock, dated", "Press-release adjectives", "Number of partners"], "answer": 1, "explain": "Like-for-like metrics.", "tags": ["reading"]},
        {"id": "b6q11", "type": "short", "q": "Rewrite: 'Vendor X achieves 48 logical qubits.' List the questions you need answered before repeating it to a client.",
         "must": [["distance", "code"], ["detect", "correct"], ["postselect", "discard", "acceptance"], ["logical error", "error rate", "error per"], ["date", "when", "dated"]],
         "explain": "Code and distance, detected vs corrected, postselection rate, logical error per operation, date and source.", "tags": ["reading"]},
        {"id": "b6q12", "type": "short", "q": "Why do clock rates matter more than qubit counts for a trading use case?",
         "must": [["second", "time", "latency", "wall"], ["depth", "t-depth", "clock"]],
         "explain": "Wall time = T-depth / logical clock; a slow clock can make the answer arrive too late regardless of qubits.", "tags": ["clock"]},
    ],
    "exercise": {
        "id": "b6_ex",
        "title": "Hardware-claim calculator",
        "prompt": (
            "Implement:\n1. `kept_fraction(p_flag, rounds)`.\n2. `effective_shots(target_kept_shots, p_flag, rounds)` → raw shots needed (ceil).\n"
            "3. `surface_overhead(d)` → 2·d² − 1 physical qubits per logical qubit.\n"
            "4. `logical_error(p, p_th, d, A=0.1)` → A·(p/p_th)^((d+1)/2).\n"
            "5. `min_distance(p, p_th, target, A=0.1)` → smallest odd d ≥ 3 with logical_error ≤ target.\n"
            "6. `seconds_per_answer(t_depth, logical_hz)`."
        ),
        "starter": '''def kept_fraction(p_flag, rounds):
    raise NotImplementedError

def effective_shots(target_kept_shots, p_flag, rounds):
    raise NotImplementedError

def surface_overhead(d):
    raise NotImplementedError

def logical_error(p, p_th, d, A=0.1):
    raise NotImplementedError

def min_distance(p, p_th, target, A=0.1):
    raise NotImplementedError

def seconds_per_answer(t_depth, logical_hz):
    raise NotImplementedError
''',
        "solution": '''import math

def kept_fraction(p_flag, rounds):
    return (1 - p_flag)**rounds

def effective_shots(target_kept_shots, p_flag, rounds):
    return math.ceil(target_kept_shots/kept_fraction(p_flag, rounds))

def surface_overhead(d):
    return 2*d*d - 1

def logical_error(p, p_th, d, A=0.1):
    return A*(p/p_th)**((d + 1)/2)

def min_distance(p, p_th, target, A=0.1):
    if p >= p_th:
        raise ValueError("above threshold: no distance suffices")
    d = 3
    while logical_error(p, p_th, d, A) > target:
        d += 2
    return d

def seconds_per_answer(t_depth, logical_hz):
    return t_depth/logical_hz
''',
        "tests": '''import math

def test_kept():
    assert abs(kept_fraction(0.02, 100) - 0.98**100) < 1e-12

def test_effective_shots():
    assert effective_shots(1000, 0.02, 100) == math.ceil(1000/0.98**100)

def test_overhead():
    assert surface_overhead(3) == 17 and surface_overhead(25) == 1249

def test_min_distance():
    d = min_distance(1e-3, 1e-2, 1e-12)
    assert d % 2 == 1 and logical_error(1e-3, 1e-2, d) <= 1e-12 < logical_error(1e-3, 1e-2, d - 2)

def test_above_threshold_raises():
    try:
        min_distance(2e-2, 1e-2, 1e-6); assert False
    except ValueError:
        pass

def test_seconds():
    assert seconds_per_answer(5.4e7, 1e6) == 54.0
''',
    },
    "cards": [
        {"front": "Error-detected vs error-corrected", "back": "Detected: flag & discard (postselect). Corrected: decode & fix in real time; only this scales", "kind": "definition"},
        {"front": "Postselection kept fraction", "back": "(1 − p_flag)^rounds", "kind": "formula"},
        {"front": "Surface-code overhead", "back": "~2d² physical per logical (plus factories)", "kind": "formula"},
        {"front": "Below-threshold scaling", "back": "ε_L ≈ A (p/p_th)^((d+1)/2)", "kind": "formula"},
        {"front": "Willow (Google, Dec 2024)", "back": "105 qubits; Λ ≈ 2.14 per d step 3→5→7 (Sourced)", "kind": "number"},
        {"front": "IBM Starling (roadmap, June 2025)", "back": "200 logical qubits, 1e8 ops, by 2029; qLDPC (Sourced roadmap, not delivered)", "kind": "number"},
        {"front": "Quantinuum Helios (Nov 2025)", "back": "98 physical qubits; 99.921% 2q fidelity (Sourced)", "kind": "number"},
        {"front": "Seconds per answer", "back": "T-depth ÷ logical clock rate", "kind": "formula"},
        {"front": "SWAP cost", "back": "3 CX", "kind": "number"},
        {"front": "Mistake: comparing physical qubit counts", "back": "Compare logical error per op, logical qubits, clock, dated", "kind": "mistake"},
        {"front": "Mistake: stale hardware figure", "back": "Re-verify anything older than six months", "kind": "mistake"},
    ],
    "defend": {
        "persona": "cro",
        "questions": [
            {"q": "Vendor X says they have 48 logical qubits. Are they ahead?",
             "must": [["detect", "correct", "postselect"], ["distance", "logical error", "error rate"]],
             "model": "Depends on code distance, detection vs correction, postselection and logical error per operation; I'll rewrite their claim like-for-like before comparing."},
            {"q": "When will a machine price our book?",
             "must": [["clock", "logical"], ["source", "date", "roadmap", "not delivered"], ["trigger", "monitor", "watch"]],
             "model": "Not before logical qubit counts and clocks reach thresholds in A3; current dates are vendor roadmaps, sourced and dated, which I track against triggers."},
            {"q": "Why do you keep asking about clock speed?",
             "must": [["seconds", "time", "wall"], ["t-depth", "depth"]], "model": "Wall time is T-depth ÷ logical clock; at 10 kHz a 54M T-depth job takes ~1.5 hours."},
            {"q": "Which modality should we bet on?",
             "must": [["no", "not", "neutral", "don't"], ["metric", "logical error", "clock", "evidence"]], "model": "We shouldn't bet; we track like-for-like metrics across modalities and stay vendor-neutral."},
            {"q": "Is this figure current?",
             "must": [["date", "verified", "last verified"], ["six months", "6 months", "re-verify", "reverify"]],
             "model": "Every hardware number carries a date and last-verified stamp; anything older than six months is re-verified before use."},
        ],
    },
    "glossary": {
        "Logical qubit": "Qubit encoded in many physical qubits by an error-correcting or -detecting code.",
        "Postselection": "Discarding runs where an error was detected.",
        "Code distance": "Minimum number of physical errors that can cause an undetected logical error.",
        "Threshold": "Physical error rate below which increasing distance reduces logical error.",
        "Λ (Lambda)": "Logical error suppression factor per distance step.",
        "Logical clock rate": "Logical operations per second on an error-corrected machine.",
        "qLDPC codes": "Quantum low-density parity-check codes with lower overhead than the surface code.",
    },
}
