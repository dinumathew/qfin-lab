MODULE = {
    "summary": (
        "You know these models professionally. This module re-states them in exactly the form the quantum labs use, "
        "so the toy circuits in I5–I8 map one-to-one onto something you can check classically: GBM pricing and Greeks, "
        "VaR and FRTB expected shortfall, Vasicek/ASRF and the IRB formula, the Gaussian copula, nested simulation, "
        "and portfolio selection rewritten as a QUBO. The emphasis is on exact reference answers, because every "
        "quantum lab needs one."
    ),
    "concepts": [
        {
            "title": "GBM, risk-neutral pricing and Greeks",
            "why": (
                "Option pricing is the flagship QAE use case (I5). To test a quantum pricer you need an exact answer "
                "(Black–Scholes) and a discretised one (the same payoff on a finite grid, which is what the circuit "
                "actually prices). Confusing the two is a classic error: the grid has its own bias."
            ),
            "how": r"""
Under $\mathbb Q$: $S_T=S_0\exp((r-\tfrac12\sigma^2)T+\sigma\sqrt T Z)$, price $=e^{-rT}\mathbb E^{\mathbb Q}[(S_T-K)^+]$.
Black–Scholes closed form; Delta $=N(d_1)$, Vega $=S_0\phi(d_1)\sqrt T$.

A quantum pricer loads a **discretised** lognormal on $2^n$ grid points (I4) and prices the payoff on that grid.
Its target is the **grid price**, not BS. Total error = discretisation bias (grid vs BS) + estimation error (QAE vs grid).
Measure them separately. {{c:p4_grid}}
""",
            "code": """import numpy as np
from scipy.stats import norm, lognorm
S0,K,r,s,T = 100,105,.03,.2,1.
d1=(np.log(S0/K)+(r+s*s/2)*T)/(s*np.sqrt(T)); bs=S0*norm.cdf(d1)-K*np.exp(-r*T)*norm.cdf(d1-s*np.sqrt(T))
mu=np.log(S0)+(r-s*s/2)*T; sd=s*np.sqrt(T)
for n in [3,4,6,8]:
    x=np.linspace(np.exp(mu-3*sd), np.exp(mu+3*sd), 2**n)
    p=lognorm.pdf(x, sd, scale=np.exp(mu)); p/=p.sum()
    print(f"{2**n:4d} grid points: grid price {np.exp(-r*T)*np.sum(p*np.maximum(x-K,0)):.4f} vs BS {bs:.4f}")
""",
            "impact": (
                "When a vendor reports 'price within 1% of Black–Scholes' on 8 grid points, part of that 1% is "
                "discretisation, unrelated to quantum. Ask for the error against the grid price (implementation) and "
                "against the analytic price (model) separately."
            ),
        },
        {
            "title": "VaR, expected shortfall and the FRTB 97.5% ES",
            "why": (
                "Market-risk QAE (I6) estimates tail probabilities and conditional expectations. FRTB replaced 99% VaR "
                "with 97.5% ES for internal models {{c:p4_frtb}}; you need both definitions exactly, including how "
                "bisection over thresholds turns a probability estimator into a quantile estimator."
            ),
            "how": r"""
$\mathrm{VaR}_\alpha=\inf\{\ell:\ P(L>\ell)\le 1-\alpha\}$; $\mathrm{ES}_\alpha=\frac{1}{1-\alpha}\int_\alpha^1\mathrm{VaR}_u\,du$
($=\mathbb E[L\mid L\ge \mathrm{VaR}_\alpha]$ for continuous $L$). For a normal loss, $\mathrm{ES}_{97.5\%}\approx\mathrm{VaR}_{99\%}$
(2.338σ vs 2.326σ): the reason the Basel Committee chose 97.5%.

Quantum route: QAE estimates $P(L\ge\ell)$ for a fixed $\ell$; **bisection** on $\ell$ finds VaR with $\sim\log_2(\text{grid})$
QAE runs, each with its own error. ES needs a further conditional-expectation estimate.
""",
            "code": """import numpy as np
from scipy.stats import norm
print("normal ES97.5 / sigma =", norm.pdf(norm.ppf(.975))/.025, " VaR99 / sigma =", norm.ppf(.99))
L = np.random.default_rng(0).standard_t(4, 200_000)
v = np.quantile(L, .975); es = L[L >= v].mean()
print(f"t(4) losses: VaR97.5={v:.3f}  ES97.5={es:.3f}")
""",
            "impact": (
                "ES is a tail mean; tail estimation is exactly where Monte Carlo is weakest and importance sampling is "
                "strongest. Any quantum ES claim must beat importance-sampled ES, not plain MC (Capstone 2)."
            ),
        },
        {
            "title": "Vasicek / ASRF, the Basel IRB formula and the Gaussian copula",
            "why": (
                "Credit portfolio risk (I7, Egger et al. 2019) is the QAE workload with the lightest data loading, and "
                "its toy model is the one-factor Gaussian copula you already use for IRB. Having the closed-form ASRF "
                "quantile lets you validate every credit circuit exactly."
            ),
            "how": r"""
Obligor $i$ defaults if $\sqrt{\rho}\,Z+\sqrt{1-\rho}\,\varepsilon_i < \Phi^{-1}(PD_i)$, $Z,\varepsilon_i\sim N(0,1)$.
Conditional PD: $p_i(z)=\Phi\!\left(\frac{\Phi^{-1}(PD_i)-\sqrt\rho\,z}{\sqrt{1-\rho}}\right)$.
In a large homogeneous portfolio (ASRF), the loss fraction's $\alpha$-quantile is
$\mathrm{LGD}\cdot\Phi\!\left(\frac{\Phi^{-1}(PD)+\sqrt\rho\,\Phi^{-1}(\alpha)}{\sqrt{1-\rho}}\right)$. {{c:p4_asrf}}

IRB corporate: $K=\left[\mathrm{LGD}\,\Phi\!\left(\frac{G(PD)+\sqrt R\,G(0.999)}{\sqrt{1-R}}\right)-PD\cdot\mathrm{LGD}\right]\frac{1+(M-2.5)b}{1-1.5b}$,
$R=0.12\frac{1-e^{-50PD}}{1-e^{-50}}+0.24\left(1-\frac{1-e^{-50PD}}{1-e^{-50}}\right)$, $b=(0.11852-0.05478\ln PD)^2$, RWA $=12.5\,K\cdot\mathrm{EAD}$. {{c:p4_irb}}

The quantum circuit (I7) encodes $Z$ on a few qubits and each $p_i(z)$ as a controlled $R_Y$ rotation: no large data table to load.
""",
            "code": """import numpy as np
from scipy.stats import norm
def irb_K(PD, LGD=0.45, M=2.5):
    w=(1-np.exp(-50*PD))/(1-np.exp(-50)); R=0.12*w+0.24*(1-w); b=(0.11852-0.05478*np.log(PD))**2
    return (LGD*norm.cdf((norm.ppf(PD)+np.sqrt(R)*norm.ppf(.999))/np.sqrt(1-R)) - PD*LGD)*(1+(M-2.5)*b)/(1-1.5*b)
for pd_ in [0.0003, 0.01, 0.05]:
    print(f"PD={pd_:.4f}: K={irb_K(pd_):.4f}, RW={12.5*irb_K(pd_):.1%}")
""",
            "impact": (
                "Because the credit oracle is built from analytic rotations, credit portfolio risk is where QAE's data-loading "
                "overhead is smallest. If any QAE finance workload reaches advantage first, a reasonable judgement is that it "
                "will be this kind {{c:p4_credit_j}}. But IRB capital is a closed form; quantum only matters for "
                "non-ASRF portfolio models (concentration, multi-factor, economic capital)."
            ),
        },
        {
            "title": "Nested simulation (Solvency II, IFRS 17, XVA)",
            "why": (
                "Nested Monte Carlo (outer scenarios × inner valuations) is the most expensive routine computation in "
                "insurance and XVA: cost is outer × inner, and both have 1/√N error. It is a natural target for quadratic "
                "speedups and for classical tricks (LSMC, proxies)."
            ),
            "how": r"""
$\text{Risk} = \rho\big(V(X)\big)$ with $V(x)=\mathbb E[g(Y)\mid X=x]$. Plain nested MC with $N_o$ outer, $N_i$ inner:
cost $N_oN_i$; bias $O(1/N_i)$ in the quantile, variance $O(1/N_o)$. Optimal allocation for MSE $\varepsilon^2$:
$N_i\sim\varepsilon^{-1}$, $N_o\sim\varepsilon^{-2}$, total $\varepsilon^{-3}$ (Gordy & Juneja 2010).
Classical competitors: least-squares MC (regression proxies), multilevel MC.
""",
            "code": """import numpy as np
rng=np.random.default_rng(0)
# 1y-ahead value of a 1y call (total T=2): outer = S at 1y, inner = payoff given S1
S0,K,r,s=100,100,.02,.2
for No,Ni in [(500,50),(2000,200)]:
    S1=S0*np.exp((r-s*s/2)+s*rng.standard_normal(No))
    V=np.array([np.exp(-r)*np.maximum(x*np.exp((r-s*s/2)+s*rng.standard_normal(Ni))-K,0).mean() for x in S1])
    print(No,Ni,"99% quantile of loss in value:", np.quantile(V.mean()-V, .99).round(3), " cost:", No*Ni)
""",
            "impact": (
                "For an insurer's SCR or a bank's CVA capital, nested simulation runtime constrains how often figures can be "
                "refreshed. The classical bar is LSMC or proxies, not brute nested MC; quantum proposals for Solvency II must "
                "beat the proxy approach the actuarial function already has."
            ),
        },
        {
            "title": "Mean-variance and cardinality-constrained portfolios as a QUBO",
            "why": (
                "QAOA and quantum annealers solve QUBOs: minimise $x^\\top Qx$ over $x\\in\\{0,1\\}^n$. To evaluate any "
                "quantum portfolio claim (I8) you must write the problem as a QUBO yourself, solve it exactly by brute force "
                "at toy size, and know what penalty weights do."
            ),
            "how": r"""
Select $k$ of $n$ assets equally weighted: minimise $q\,x^\top\Sigma x-\mu^\top x+P\,(\mathbf 1^\top x-k)^2$.
Expand the penalty: $(\mathbf 1^\top x-k)^2=x^\top\mathbf 1\mathbf 1^\top x-2k\,\mathbf 1^\top x+k^2$, and use $x_i^2=x_i$ to fold linear terms into
the diagonal: $Q=q\Sigma+P\mathbf 1\mathbf 1^\top+\mathrm{diag}(-\mu-2Pk\mathbf 1)$, constant $Pk^2$.

Penalty $P$ must exceed the largest objective gain from violating the constraint, but too large a $P$ flattens the
landscape and hurts heuristic solvers (I8). Brute force over $2^n$ is instant for $n\le 20$.
""",
            "code": """import numpy as np, itertools
rng=np.random.default_rng(1); n,k,q,P=6,3,1.0,2.0
A=rng.normal(size=(n,n)); Sig=A@A.T/n; mu=rng.uniform(0,.5,n)
Q=q*Sig+P*np.ones((n,n))+np.diag(-mu-2*P*k)
best=min(itertools.product([0,1],repeat=n), key=lambda x: np.array(x)@Q@np.array(x))
print("brute-force optimum:", best, "assets chosen:", sum(best))
""",
            "impact": (
                "Real portfolio construction is continuous, with many constraints, solved in milliseconds by commercial MIQP "
                "solvers. A binary toy that QAOA solves is a code check, not a business result. Ask any vendor for the MIQP "
                "solver's time and gap on the same instance."
            ),
        },
    ],
    "lens": {
        "look": "For each model: write the exact reference (closed form or brute force), the discretised version the circuit will see, and the classical production method (VR-MC, LSMC, MIQP). Three numbers, always.",
        "decision": "What counts as the 'right answer' and the 'baseline' for each quantum lab, before any circuit is built.",
        "justified": "Without an exact reference you cannot separate discretisation, estimation and implementation errors; without the production baseline you cannot claim value.",
        "mistakes": [
            "Comparing a grid-discretised quantum price with Black–Scholes and calling the gap 'quantum error'.",
            "Using 99% VaR when the regulatory measure is 97.5% ES (FRTB IMA).",
            "Forgetting the maturity adjustment or using the wrong correlation function in IRB.",
            "Benchmarking nested-simulation speedups against brute nested MC instead of LSMC.",
            "Choosing QUBO penalties after seeing results, or so large the landscape flattens.",
        ],
        "impact": "Mis-stated errors, wrong capital numbers in pilot memos, and baselines that a model validator will reject on sight.",
        "test": "Lab P4: validate the ASRF closed-form quantile against a large simulated portfolio, compute IRB capital, and estimate VaR/ES on simulated P&L.",
    },
    "claims": [
        {"id": "p4_grid", "tag": "M", "text": "On an 8-point lognormal grid (±3σ), the European call grid price differs from Black–Scholes by more than 1% for S=100, K=105, σ=20%, T=1.",
         "check": """import numpy as np
from scipy.stats import norm, lognorm
S0,K,r,s,T=100,105,.03,.2,1.
d1=(np.log(S0/K)+(r+s*s/2)*T)/(s*T**.5); bs=S0*norm.cdf(d1)-K*np.exp(-r*T)*norm.cdf(d1-s*T**.5)
mu=np.log(S0)+(r-s*s/2)*T; sd=s*T**.5; x=np.linspace(np.exp(mu-3*sd),np.exp(mu+3*sd),8)
p=lognorm.pdf(x,sd,scale=np.exp(mu)); p/=p.sum(); g=np.exp(-r*T)*np.sum(p*np.maximum(x-K,0))
assert abs(g/bs-1)>0.01, g/bs"""},
        {"id": "p4_frtb", "tag": "S", "text": "FRTB internal models use expected shortfall at 97.5% confidence.",
         "source": {"title": "Minimum capital requirements for market risk (d457)", "publisher": "Basel Committee on Banking Supervision", "date": "2019-01", "url": "https://www.bis.org/bcbs/publ/d457.htm"},
         "last_verified": "2026-10-19"},
        {"id": "p4_irb", "tag": "S", "text": "IRB risk-weight function for corporate exposures (correlation, maturity adjustment, 99.9% confidence).",
         "source": {"title": "An Explanatory Note on the Basel II IRB Risk Weight Functions", "publisher": "Basel Committee on Banking Supervision", "date": "2005-07", "url": "https://www.bis.org/bcbs/irbriskweight.pdf"},
         "last_verified": "2026-10-19"},
        {"id": "p4_asrf", "tag": "M", "text": "The ASRF closed-form 99.9% loss-fraction quantile matches a simulated 5,000-obligor homogeneous portfolio within 5%.",
         "check": """import numpy as np
from scipy.stats import norm
PD,rho,N,S=0.02,0.15,5000,20000
rng=np.random.default_rng(0); Z=rng.standard_normal(S)
pz=norm.cdf((norm.ppf(PD)-np.sqrt(rho)*Z)/np.sqrt(1-rho)); L=rng.binomial(N,pz)/N
q=norm.cdf((norm.ppf(PD)+np.sqrt(rho)*norm.ppf(.999))/np.sqrt(1-rho))
assert abs(np.quantile(L,.999)/q-1)<0.05, (np.quantile(L,.999), q)"""},
        {"id": "p4_credit_j", "tag": "J", "text": "If any QAE finance workload reaches advantage first, light-data-loading credit portfolio models are a plausible candidate; this is a judgement, not a forecast."},
    ],
    "lab": {
        "id": "p4_lab",
        "title": "Credit and market-risk references: ASRF vs simulation, IRB capital, VaR and ES",
        "hypothesis": (
            "H1: ASRF closed-form 99.9% loss quantile is within 5% of a simulated 5,000-obligor homogeneous portfolio (PD 2%, ρ 15%). "
            "H2: with 100 obligors the simulated quantile exceeds the ASRF value (granularity add-on > 0). "
            "H3: for normal P&L, ES 97.5% / VaR 99% is within 1% of 1.005."
        ),
        "thresholds": "|sim/ASRF − 1| < 5% at N=5,000; sim(N=100) > ASRF; |ES97.5/VaR99 − 1.005| < 0.01.",
        "data": "Synthetic one-factor Gaussian copula portfolios, 50,000 factor scenarios; normal P&L sample of 1,000,000.",
        "code": r'''import numpy as np, pandas as pd
import plotly.graph_objects as go
from scipy.stats import norm
from qlab_helpers import SEED, rng, show, record, table

PD, rho, LGD, S = 0.02, 0.15, 0.45, 50_000
asrf = LGD*norm.cdf((norm.ppf(PD)+np.sqrt(rho)*norm.ppf(.999))/np.sqrt(1-rho))
Z = rng.standard_normal(S)
pz = norm.cdf((norm.ppf(PD)-np.sqrt(rho)*Z)/np.sqrt(1-rho))
rows, dists = [], {}
for N in [20, 100, 500, 5000]:
    L = LGD*rng.binomial(N, pz)/N
    q = np.quantile(L, .999); dists[N] = L
    rows.append({"obligors": N, "sim 99.9% loss": q, "ASRF": asrf, "ratio": q/asrf, "EL": L.mean()})
df = pd.DataFrame(rows); table(df.round(5), "Loss-fraction 99.9% quantile vs ASRF closed form")
fig = go.Figure()
for N, L in dists.items():
    fig.add_trace(go.Histogram(x=L, name=f"N={N}", histnorm="probability density", opacity=0.5, nbinsx=120))
fig.add_vline(x=asrf, line_dash="dash", annotation_text="ASRF 99.9%")
fig.update_layout(barmode="overlay", title="Portfolio loss distributions (LGD × default fraction)", xaxis_title="loss fraction")
show(fig)
record("asrf_ratio_N5000", float(df.loc[df.obligors==5000, "ratio"].item()))
record("granularity_N100_exceeds", bool(df.loc[df.obligors==100, "sim 99.9% loss"].item() > asrf))

def irb_K(PD, LGD=0.45, M=2.5):
    w=(1-np.exp(-50*PD))/(1-np.exp(-50)); R=0.12*w+0.24*(1-w); b=(0.11852-0.05478*np.log(PD))**2
    return (LGD*norm.cdf((norm.ppf(PD)+np.sqrt(R)*norm.ppf(.999))/np.sqrt(1-R)) - PD*LGD)*(1+(M-2.5)*b)/(1-1.5*b)
irb = pd.DataFrame({"PD": [0.0005, 0.002, 0.01, 0.03, 0.1]})
irb["K"] = irb.PD.map(irb_K); irb["RW"] = 12.5*irb.K
table(irb.round(4), "IRB corporate capital K and risk weight (LGD 45%, M 2.5y)")

pnl = rng.standard_normal(1_000_000)
var99 = np.quantile(-pnl, .99); v975 = np.quantile(-pnl, .975); es975 = (-pnl)[-pnl >= v975].mean()
record("es975_over_var99", float(es975/var99))
print(f"VaR99={var99:.4f}  ES97.5={es975:.4f}  ratio={es975/var99:.4f}")
''',
        "expect": {"asrf_ratio_N5000": "abs(x-1) < 0.05", "granularity_N100_exceeds": "x is True", "es975_over_var99": "abs(x-1.005) < 0.01"},
        "report_hints": "Be explicit that this lab produces the exact references for I6 and I7. Your business translation: what IRB already gives you in closed form, and where simulation (and possibly QAE) is actually needed.",
    },
    "quiz": [
        {"id": "p4q1", "type": "mc", "q": "A QAE option pricer on 8 grid points should first be validated against:",
         "options": ["Black–Scholes", "The exact price on the same 8-point grid", "A vendor's reported number", "Market price"], "answer": 1,
         "explain": "Implementation check against the grid; discretisation error is separate.", "tags": ["pricing"]},
        {"id": "p4q2", "type": "mc", "q": "FRTB internal models capitalise market risk using:", "options": ["99% VaR", "97.5% ES", "99.9% VaR", "95% ES"], "answer": 1,
         "explain": "Expected shortfall at 97.5%.", "tags": ["frtb"]},
        {"id": "p4q3", "type": "mc", "q": "For normal losses, ES 97.5% is approximately equal to:", "options": ["VaR 95%", "VaR 97.5%", "VaR 99%", "VaR 99.9%"], "answer": 2,
         "explain": "2.338σ vs 2.326σ.", "tags": ["frtb"]},
        {"id": "p4q4", "type": "mc", "q": "The IRB formula's confidence level is:", "options": ["99%", "99.5%", "99.9%", "97.5%"], "answer": 2, "explain": "G(0.999).", "tags": ["irb"]},
        {"id": "p4q5", "type": "mc", "q": "In the ASRF model, conditional PD given systematic factor z is:",
         "options": ["Φ((Φ⁻¹(PD) − √ρ z)/√(1−ρ))", "PD·z", "Φ(z)", "Φ⁻¹(PD)+z"], "answer": 0, "explain": "Vasicek conditional PD.", "tags": ["credit"]},
        {"id": "p4q6", "type": "mc", "q": "Why is credit portfolio QAE (Egger et al.) relatively light on data loading?",
         "options": ["It uses qRAM", "Conditional PDs are analytic rotations controlled by a few factor qubits", "It ignores correlation", "It loads only one obligor"], "answer": 1,
         "explain": "No large table: rotations are computed from the formula.", "tags": ["credit"]},
        {"id": "p4q7", "type": "mc", "q": "With a small number of obligors, the simulated 99.9% loss vs ASRF is typically:",
         "options": ["Lower", "Higher (granularity)", "Identical", "Undefined"], "answer": 1, "explain": "Idiosyncratic risk not diversified away.", "tags": ["credit"]},
        {"id": "p4q8", "type": "mc", "q": "Plain nested MC total cost for MSE ε² scales as:", "options": ["ε⁻¹", "ε⁻²", "ε⁻³", "ε⁻⁴"], "answer": 2,
         "explain": "Gordy–Juneja optimal allocation.", "tags": ["nested"]},
        {"id": "p4q9", "type": "mc", "q": "In a QUBO with cardinality penalty P(Σx − k)², the linear term after using x²=x is:",
         "options": ["+2Pk on the diagonal", "−2Pk on the diagonal", "Pk² on the diagonal", "None"], "answer": 1, "explain": "−2Pk·Σx folds to −2Pk on the diagonal.", "tags": ["qubo"]},
        {"id": "p4q10", "type": "mc", "q": "The relevant classical baseline for a binary portfolio toy is:",
         "options": ["Random guessing", "Brute force (toy) and a commercial MIQP solver (realistic)", "Grid search over P", "Nothing"], "answer": 1,
         "explain": "Exact at toy size; MIQP at real size.", "tags": ["qubo"]},
        {"id": "p4q11", "type": "short", "q": "Decompose the error of a quantum option price into its components.",
         "must": [["discretis", "discretiz", "grid", "truncat"], ["estimation", "sampling", "shot", "statistical"], ["implementation", "bug", "noise", "hardware"]],
         "explain": "Discretisation (grid vs model), estimation (QAE statistical), implementation/noise.", "tags": ["pricing"]},
        {"id": "p4q12", "type": "short", "q": "IRB capital is a closed form. Where in credit risk would simulation (and possibly QAE) still be needed?",
         "must": [["concentration", "granular", "name"], ["multi-factor", "multi factor", "sector", "economic capital", "correlation structure"]],
         "explain": "Concentration/granularity, multi-factor economic capital, non-Gaussian dependence.", "tags": ["credit"]},
    ],
    "exercise": {
        "id": "p4_ex",
        "title": "Reference engines for the quantum labs",
        "prompt": (
            "Implement:\n1. `irb_K(PD, LGD=0.45, M=2.5)` corporate IRB capital.\n"
            "2. `var_es(losses, alpha)` returning (VaR, ES) from a sample of losses (ES = mean of losses ≥ VaR).\n"
            "3. `asrf_quantile(PD, rho, alpha, LGD=1.0)`.\n"
            "4. `portfolio_qubo(Sigma, mu, k, q, P)` returning (Q, const) so that x·Q·x + const = q x'Σx − μ'x + P(Σx − k)² for binary x."
        ),
        "starter": '''import numpy as np
from scipy.stats import norm

def irb_K(PD, LGD=0.45, M=2.5):
    raise NotImplementedError

def var_es(losses, alpha):
    raise NotImplementedError

def asrf_quantile(PD, rho, alpha, LGD=1.0):
    raise NotImplementedError

def portfolio_qubo(Sigma, mu, k, q, P):
    raise NotImplementedError
''',
        "solution": '''import numpy as np
from scipy.stats import norm

def irb_K(PD, LGD=0.45, M=2.5):
    w = (1-np.exp(-50*PD))/(1-np.exp(-50)); R = 0.12*w + 0.24*(1-w)
    b = (0.11852 - 0.05478*np.log(PD))**2
    return (LGD*norm.cdf((norm.ppf(PD)+np.sqrt(R)*norm.ppf(.999))/np.sqrt(1-R)) - PD*LGD)*(1+(M-2.5)*b)/(1-1.5*b)

def var_es(losses, alpha):
    L = np.asarray(losses); v = np.quantile(L, alpha)
    return float(v), float(L[L >= v].mean())

def asrf_quantile(PD, rho, alpha, LGD=1.0):
    return LGD*norm.cdf((norm.ppf(PD)+np.sqrt(rho)*norm.ppf(alpha))/np.sqrt(1-rho))

def portfolio_qubo(Sigma, mu, k, q, P):
    n = len(mu)
    Q = q*np.asarray(Sigma) + P*np.ones((n, n)) + np.diag(-np.asarray(mu) - 2*P*k)
    return Q, P*k*k
''',
        "tests": '''import numpy as np, itertools

def test_irb_reference():
    """PD 1%, LGD 45%, M 2.5: K ~ 0.0739 (RW ~ 92%)"""
    assert abs(irb_K(0.01) - 0.0739) < 5e-4

def test_irb_maturity():
    """Longer maturity -> more capital"""
    assert irb_K(0.01, M=5) > irb_K(0.01, M=1)

def test_var_es_normal():
    L = np.random.default_rng(0).standard_normal(400_000)
    v, e = var_es(L, 0.975)
    assert abs(v - 1.96) < 0.02 and abs(e - 2.338) < 0.02

def test_asrf():
    """PD 2%, rho 15%, 99.9% -> 0.1763"""
    assert abs(asrf_quantile(0.02, 0.15, 0.999) - 0.1763) < 2e-3

def test_qubo_matches_direct():
    """x Q x + c equals the direct objective on all 2^5 bitstrings"""
    rng = np.random.default_rng(3); n=5; A=rng.normal(size=(n,n)); S=A@A.T; mu=rng.uniform(size=n)
    Q, c = portfolio_qubo(S, mu, 2, 0.7, 1.5)
    for x in itertools.product([0,1], repeat=n):
        x = np.array(x)
        direct = 0.7*x@S@x - mu@x + 1.5*(x.sum()-2)**2
        assert abs(x@Q@x + c - direct) < 1e-9
''',
    },
    "cards": [
        {"front": "FRTB IMA risk measure", "back": "Expected shortfall at 97.5%", "kind": "number"},
        {"front": "Normal ES97.5 vs VaR99", "back": "2.338σ vs 2.326σ (almost equal)", "kind": "number"},
        {"front": "Vasicek conditional PD", "back": "Φ((Φ⁻¹(PD) − √ρ z)/√(1−ρ))", "kind": "formula"},
        {"front": "ASRF α-quantile of loss fraction", "back": "LGD·Φ((Φ⁻¹(PD) + √ρ Φ⁻¹(α))/√(1−ρ))", "kind": "formula"},
        {"front": "IRB corporate correlation R", "back": "0.12·w + 0.24·(1−w), w = (1−e^{−50PD})/(1−e^{−50})", "kind": "formula"},
        {"front": "IRB maturity factor b", "back": "(0.11852 − 0.05478 ln PD)²", "kind": "formula"},
        {"front": "IRB K at PD 1%, LGD 45%, M 2.5", "back": "≈ 7.39% (RW ≈ 92%)", "kind": "number"},
        {"front": "RWA from K", "back": "12.5 × K × EAD", "kind": "formula"},
        {"front": "Nested MC optimal total cost", "back": "O(ε⁻³)", "kind": "formula"},
        {"front": "QUBO cardinality penalty linear term", "back": "−2Pk on the diagonal; constant Pk²", "kind": "formula"},
        {"front": "Mistake: QAE price vs BS", "back": "Validate against the grid price first; discretisation ≠ quantum error", "kind": "mistake"},
        {"front": "Mistake: nested baseline", "back": "Compare to LSMC/proxies, not brute nested MC", "kind": "mistake"},
    ],
    "defend": {
        "persona": "validator",
        "questions": [
            {"q": "Your quantum price is 2% off Black–Scholes. Is the quantum part wrong?",
             "must": [["grid", "discretis", "discretiz"], ["separate", "decompos", "split"]],
             "model": "Not necessarily: I separate discretisation error (grid vs BS) from estimation/implementation error (QAE vs grid price)."},
            {"q": "Why did you validate the credit circuit against ASRF rather than simulation?",
             "must": [["closed form", "closed-form", "exact", "analytic"], ["granular", "finite", "simulation", "obligors"]],
             "model": "ASRF is exact in the infinite-granularity limit; for a 4-obligor toy I compare to the exact finite-portfolio distribution, and ASRF bounds the large-N case."},
            {"q": "What's your classical baseline for nested simulation?",
             "must": [["lsmc", "least-squares", "least squares", "proxy", "regression"]], "model": "LSMC/proxy models already in production, timed; not brute nested MC."},
            {"q": "You chose penalty P = 10. Why?",
             "must": [["exceed", "larger than", "bigger than", "bound", "violat"], ["advance", "before", "pre", "fixed", "sensitiv"]],
             "model": "P exceeds the largest objective gain from violating the constraint (bounded from Σ and μ), fixed before running, with sensitivity reported."},
            {"q": "Which credit metrics would you actually compute with QAE, and which never?",
             "must": [["var", "cvar", "tail", "economic capital"], ["irb", "regulatory", "closed form"]],
             "model": "Tail metrics of non-ASRF portfolio models (VaR/CVaR, economic capital); never IRB regulatory capital, which is a closed form."},
        ],
    },
    "glossary": {
        "ASRF": "Asymptotic single risk factor model underpinning the Basel IRB formula.",
        "Expected shortfall (ES)": "Mean loss beyond the VaR at a given confidence; FRTB uses 97.5%.",
        "Gaussian copula": "Dependence model where obligors' latent variables share a Gaussian systematic factor.",
        "Nested simulation": "Outer scenarios with inner revaluations; cost outer × inner.",
        "QUBO": "Quadratic unconstrained binary optimisation: minimise x'Qx over binary x.",
        "LSMC": "Least-squares Monte Carlo: regression proxies replacing inner simulations.",
    },
}
