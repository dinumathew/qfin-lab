MODULE = {
    "summary": (
        "Every quantum-finance claim is a statistical claim: 'error falls as 1/N', 'the quantum model beats XGBoost by "
        "34%'. This module rebuilds the statistics you need to test such claims properly: Monte Carlo error and its "
        "1/√N law, variance reduction (the classical competitor you must beat), maximum likelihood and Fisher "
        "information (the engine of maximum-likelihood amplitude estimation), confidence intervals, the bootstrap, "
        "and the multiple-comparisons trap behind most inflated vendor results."
    ),
    "concepts": [
        {
            "title": "Monte Carlo error and the 1/√N law",
            "why": (
                "Quantum amplitude estimation's headline is 'error ∝ 1/N instead of 1/√N'. You cannot judge that "
                "claim unless you can measure the classical rate yourself, on your machine, with your payoff. "
                "Quoting the textbook rate is not enough: constants, variance and wall time decide the business case."
            ),
            "how": r"""
For i.i.d. samples $Y_i$ with variance $\sigma^2$, $\hat\mu_N = \frac1N\sum Y_i$ has standard error
$\sigma/\sqrt N$. So $\log \text{RMSE} = \log\sigma - \tfrac12\log N$: on a log-log plot the slope is $-0.5$. {{c:p2_slope}}

To cut error by 10× you need 100× the samples. QAE's promise (I3) is error $\propto 1/N_{\text{oracle}}$, slope $-1$:
10× error reduction for 10× queries. Measure slopes by OLS on $(\log N, \log \text{RMSE})$ over ≥30 seeds per $N$.
""",
            "code": """import numpy as np
rng = np.random.default_rng(1)
S0, K, r, sig, T = 100, 105, 0.03, 0.2, 1.0
for N in [10**3, 10**4, 10**5]:
    Z = rng.standard_normal(N)
    pay = np.maximum(S0*np.exp((r-sig**2/2)*T + sig*np.sqrt(T)*Z) - K, 0)*np.exp(-r*T)
    print(N, "price=%.4f  stderr=%.4f" % (pay.mean(), pay.std(ddof=1)/np.sqrt(N)))
""",
            "impact": (
                "For a desk, '1/√N' means compute cost grows with the square of the precision you need. That is why "
                "XVA and FRTB IMA grids are expensive and why a quadratic speedup sounds attractive. The honest client "
                "message: the speedup is in the exponent of a cost curve, and it only matters if the constant factors "
                "and clock speed let the quantum curve cross below the classical one at a precision the desk needs."
            ),
        },
        {
            "title": "Variance reduction: antithetic variates and control variates",
            "why": (
                "Any comparison against 'plain Monte Carlo' is a strawman. Production engines use variance reduction, "
                "which cuts σ (often by large factors) without changing the 1/√N rate. A quantum claim measured "
                "against unreduced MC overstates the gain by exactly that factor."
            ),
            "how": r"""
* **Antithetic**: pair $Z$ with $-Z$; $\hat\mu = \frac1N\sum \tfrac12(f(Z_i)+f(-Z_i))$. Variance falls when $f$ is monotone.
* **Control variate**: with $C$ correlated to $Y$ and known mean $\mu_C$: $Y^{cv} = Y - \beta(C-\mu_C)$,
  $\beta^* = \mathrm{Cov}(Y,C)/\mathrm{Var}(C)$. Variance falls by factor $1-\rho^2$. For a call, $C = e^{-rT}S_T$ with
  $\mathbb E[C]=S_0$.
* **Importance sampling** (used in Capstone 2 for tail risk): sample from $q$, weight by $p/q$.

Compare estimators by **variance reduction factor** at equal cost: $\mathrm{VRF} = \sigma^2_{\text{plain}}/\sigma^2_{\text{method}}$, adjusted for cost per sample.
""",
            "code": """import numpy as np
rng = np.random.default_rng(2)
S0, K, r, sig, T, N = 100, 105, 0.03, 0.2, 1.0, 100_000
Z = rng.standard_normal(N)
ST = lambda z: S0*np.exp((r-sig**2/2)*T + sig*np.sqrt(T)*z)
disc = np.exp(-r*T)
plain = disc*np.maximum(ST(Z)-K, 0)
anti = 0.5*disc*(np.maximum(ST(Z)-K,0) + np.maximum(ST(-Z)-K,0))
C = disc*ST(Z); beta = np.cov(plain, C)[0,1]/C.var(ddof=1)
cv = plain - beta*(C - S0)
for name, y in [("plain", plain), ("antithetic", anti), ("control var", cv)]:
    print(f"{name:12s} mean={y.mean():.4f} var={y.var(ddof=1):.3f}")
print("VRF control variate:", plain.var()/cv.var())
""",
            "impact": (
                "When a client is shown 'quantum needs 100× fewer samples', the first question is: fewer than what? "
                "A control variate that gives a 5–10× variance reduction (common for vanilla payoffs; Measured in this "
                "module's lab) {{c:p2_vrf}} eats a large part of a claimed advantage before a single qubit is used."
            ),
        },
        {
            "title": "Maximum likelihood and Fisher information",
            "why": (
                "Maximum-likelihood amplitude estimation (MLQAE, I3) combines shot counts from circuits of different "
                "depth via a likelihood. Its error rate, and its failure modes (multimodal likelihoods, leaning on "
                "shallow circuits when deep ones decohere), only make sense through Fisher information."
            ),
            "how": r"""
Bernoulli shots with $p=\sin^2\theta$: log-likelihood $\ell(\theta)=h\log p + (n-h)\log(1-p)$.
MLE $\hat\theta$ maximises $\ell$. Fisher information $I(\theta) = -\mathbb E[\ell''(\theta)]$; Cramér–Rao:
$\mathrm{Var}(\hat\theta) \ge 1/I(\theta)$.

For a Bernoulli in $p$: $I(p) = n/(p(1-p))$. In MLQAE, a circuit with $m$ Grover applications measures
$\sin^2((2m+1)\theta)$, so its Fisher information about $\theta$ scales as $n(2m+1)^2$ (×4 for the $\sin^2$ parametrisation; I3 derives it): deep circuits are informative.
That $(2m+1)^2$ is where the quadratic speedup comes from, and noise that kills deep circuits kills it.
""",
            "code": """import numpy as np
from scipy.optimize import minimize_scalar
theta_true, n = 0.35, 200
rng = np.random.default_rng(3)
for m in [0, 1, 4]:
    p = np.sin((2*m+1)*theta_true)**2
    h = rng.binomial(n, p)
    print(f"m={m}: p={p:.3f}, hits={h}, Fisher info about theta ~ {4*n*(2*m+1)**2:.0f}")
""",
            "impact": (
                "Fisher information gives you a defensible way to budget shots and circuit depth before buying QPU time. "
                "It also gives validators a test: if the reported error is better than the Cramér–Rao bound for the "
                "shots used, something is wrong (or cherry-picked)."
            ),
        },
        {
            "title": "Confidence intervals, the bootstrap, hypothesis tests and multiple comparisons",
            "why": (
                "Most inflated quantum-ML results come from three mistakes: one seed, no interval, and many "
                "configurations tried with only the best reported. You need the tools to put an honest interval on any "
                "metric and to correct for the number of comparisons."
            ),
            "how": r"""
* Normal CI: $\hat\mu \pm z_{0.975}\,\hat\sigma/\sqrt n$. With ≥30 seeds per configuration, report the CI of the metric, not a single run.
* **Bootstrap**: resample the $n$ observations with replacement $B$ times, recompute the statistic, take the 2.5/97.5% percentiles. Works for medians, ratios, AUC differences.
* Paired tests: compare two models on the **same** seeds/folds (paired t-test or bootstrap of differences).
* **Multiple comparisons**: testing $k$ configurations at level $\alpha$ gives family-wise false-positive rate $1-(1-\alpha)^k$ (≈64% for $k=20$). Bonferroni: use $\alpha/k$. Holm or Benjamini–Hochberg are less conservative.
""",
            "code": """import numpy as np
rng = np.random.default_rng(4)
k, alpha = 20, 0.05
print("P(at least one false positive) with 20 null tests:", 1-(1-alpha)**k)
x = rng.lognormal(0, 1, 200)
boots = [np.median(rng.choice(x, x.size)) for _ in range(2000)]
print("median %.3f, bootstrap 95%% CI (%.3f, %.3f)" % (np.median(x), *np.percentile(boots, [2.5, 97.5])))
""",
            "impact": (
                "When a vendor reports 'up to 34% improvement', ask: over how many configurations, seeds and time "
                "windows, with what interval, and was the best one chosen after the fact? 'Up to' is the maximum of a "
                "distribution, not its centre. For a board paper, insist on the interval and the median."
            ),
        },
    ],
    "lens": {
        "look": (
            "Plot error against budget on log-log axes with ≥30 seeds per point; fit the slope with its CI; check the "
            "intercept (constant factor) as carefully as the slope; compare at equal cost (samples, oracle queries or "
            "wall time), never at equal 'iterations'."
        ),
        "decision": "Whether an estimator (classical or quantum) meets a precision target within a compute budget, and which estimator to use as the baseline.",
        "justified": (
            "Rates without constants and intervals are not evidence. A pre-registered slope test with CIs is the same "
            "discipline you would apply to a challenger model in outcomes analysis."
        ),
        "mistakes": [
            "Comparing quantum against plain MC instead of variance-reduced MC.",
            "Reporting one seed; or fitting a slope from 3 points.",
            "Comparing at equal 'iterations' when a quantum query and an MC sample cost very different wall time.",
            "Reporting 'up to X%' (the best of many runs) as the expected gain.",
            "Ignoring multiple comparisons across hyperparameters, windows and datasets.",
        ],
        "impact": (
            "Overstated advantage → misallocated innovation budget; in a model inventory, an unchallenged challenger; "
            "reputational damage when the result does not replicate."
        ),
        "test": "Lab P2: RMSE of MC European-call prices vs N on log-log axes (slope ≈ −0.5), with antithetic and control-variate estimators on the same seeds.",
    },
    "claims": [
        {"id": "p2_slope", "tag": "M", "text": "Plain MC RMSE vs N for a European call has log-log slope ≈ −0.5 (within ±0.1 over 30 seeds).",
         "check": """import numpy as np
S0,K,r,s,T=100,105,.03,.2,1.
from scipy.stats import norm
d1=(np.log(S0/K)+(r+s*s/2)*T)/(s*T**.5); bs=S0*norm.cdf(d1)-K*np.exp(-r*T)*norm.cdf(d1-s*T**.5)
Ns=np.array([250,1000,4000,16000]); rmse=[]
for N in Ns:
    errs=[]
    for seed in range(30):
        Z=np.random.default_rng(seed).standard_normal(N)
        errs.append(np.mean(np.maximum(S0*np.exp((r-s*s/2)*T+s*T**.5*Z)-K,0))*np.exp(-r*T)-bs)
    rmse.append(np.sqrt(np.mean(np.square(errs))))
slope=np.polyfit(np.log(Ns),np.log(rmse),1)[0]
assert -0.6<slope<-0.4, slope"""},
        {"id": "p2_vrf", "tag": "M", "text": "For an ATM-ish 1y call (S=100, K=105, σ=20%), the S_T control variate gives a variance reduction factor above 3.",
         "check": """import numpy as np
rng=np.random.default_rng(0); S0,K,r,s,T=100,105,.03,.2,1.
Z=rng.standard_normal(200000); ST=S0*np.exp((r-s*s/2)*T+s*T**.5*Z); d=np.exp(-r*T)
y=d*np.maximum(ST-K,0); C=d*ST; b=np.cov(y,C)[0,1]/C.var(); cv=y-b*(C-S0)
assert y.var()/cv.var()>3, y.var()/cv.var()"""},
        {"id": "p2_cr", "tag": "S", "text": "Cramér–Rao lower bound on estimator variance; standard statistical theory.",
         "source": {"title": "Statistical Inference (2nd ed.)", "publisher": "Duxbury (Casella & Berger)", "date": "2002", "url": "https://www.routledge.com/Statistical-Inference/Casella-Berger/p/book/9781032593036"},
         "last_verified": "2026-10-19"},
        {"id": "p2_glasserman", "tag": "S", "text": "Variance reduction methods for derivative pricing.",
         "source": {"title": "Monte Carlo Methods in Financial Engineering", "publisher": "Springer (Glasserman)", "date": "2003", "url": "https://doi.org/10.1007/978-0-387-21617-1"},
         "last_verified": "2026-10-19"},
    ],
    "lab": {
        "id": "p2_lab",
        "title": "Monte Carlo price of a European call: RMSE vs N on a log-log plot",
        "hypothesis": (
            "H1: plain MC RMSE slope vs N is −0.5 ± 0.1. H2: antithetic and control-variate slopes are also −0.5 ± 0.1 "
            "(variance reduction changes the constant, not the rate). H3: the control variate's RMSE at N=16,000 is at "
            "least 1.7× lower than plain MC (VRF ≥ 3)."
        ),
        "thresholds": "Slopes in [−0.6, −0.4]; RMSE ratio plain/CV ≥ 1.7 at the largest N.",
        "data": "Synthetic GBM paths, exact Black–Scholes reference. Seeds 0..29 (+ SEED offset).",
        "code": r'''import numpy as np, pandas as pd, time
import plotly.graph_objects as go
from scipy.stats import norm
from qlab_helpers import SEED, show, record, table

S0, K, r, sig, T = 100.0, 105.0, 0.03, 0.2, 1.0
d1 = (np.log(S0/K) + (r + sig**2/2)*T) / (sig*np.sqrt(T)); d2 = d1 - sig*np.sqrt(T)
BS = S0*norm.cdf(d1) - K*np.exp(-r*T)*norm.cdf(d2)
disc = np.exp(-r*T)
def paths(z): return S0*np.exp((r - sig**2/2)*T + sig*np.sqrt(T)*z)
def plain(z): return disc*np.maximum(paths(z)-K, 0).mean()
def anti(z):  return 0.5*disc*(np.maximum(paths(z)-K,0) + np.maximum(paths(-z)-K,0)).mean()
def cv(z):
    y = disc*np.maximum(paths(z)-K, 0); c = disc*paths(z)
    b = np.cov(y, c)[0,1]/c.var(ddof=1)
    return (y - b*(c - S0)).mean()
Ns = np.array([250, 500, 1000, 2000, 4000, 8000, 16000])
methods = {"plain": plain, "antithetic": anti, "control variate": cv}
rows = []
for N in Ns:
    for name, f in methods.items():
        n_eff = N//2 if name == "antithetic" else N   # equal number of payoff evaluations
        t0 = time.perf_counter()
        errs = [f(np.random.default_rng(SEED + s).standard_normal(n_eff)) - BS for s in range(30)]
        dt = (time.perf_counter()-t0)/30
        rows.append({"N": N, "method": name, "bias": np.mean(errs), "rmse": np.sqrt(np.mean(np.square(errs))), "sec_per_run": dt})
df = pd.DataFrame(rows)
fig = go.Figure()
slopes = {}
for name in methods:
    d = df[df.method == name]
    k, c0 = np.polyfit(np.log(d.N), np.log(d.rmse), 1); slopes[name] = k
    fig.add_trace(go.Scatter(x=d.N, y=d.rmse, mode="markers+lines", name=f"{name} (slope {k:.2f})"))
fig.add_trace(go.Scatter(x=Ns, y=df[df.method=="plain"].rmse.iloc[0]*(Ns/Ns[0])**-0.5, name="reference −0.5", line=dict(dash="dot")))
fig.update_layout(xaxis_type="log", yaxis_type="log", xaxis_title="payoff evaluations N", yaxis_title="RMSE vs Black–Scholes",
                  title=f"European call, BS = {BS:.4f}; 30 seeds per point")
show(fig); table(df.round(6), "Bias, RMSE and time per run")
for k, v in slopes.items(): record(f"slope_{k.replace(' ', '_')}", float(v))
ratio = df[(df.N==16000)&(df.method=="plain")].rmse.item()/df[(df.N==16000)&(df.method=="control variate")].rmse.item()
record("rmse_ratio_plain_over_cv_at_16000", float(ratio))
record("bs_price", float(BS))
print("slopes:", {k: round(float(v), 3) for k, v in slopes.items()}, " RMSE ratio plain/CV at N=16000:", round(ratio, 2))
''',
        "expect": {"slope_plain": "-0.6 < x < -0.4", "rmse_ratio_plain_over_cv_at_16000": "x > 1.7"},
        "report_hints": "Section 3 is the whole point here: your classical baseline is the variance-reduced estimator, timed. Carry this forward to I5.",
    },
    "quiz": [
        {"id": "p2q1", "type": "mc", "q": "To reduce plain Monte Carlo RMSE by 10×, you need about how many more samples?",
         "options": ["10×", "√10×", "100×", "1000×"], "answer": 2, "explain": "RMSE ∝ N^−1/2.", "tags": ["mc rate"]},
        {"id": "p2q2", "type": "mc", "q": "QAE's ideal error scaling in oracle queries N is:",
         "options": ["1/√N", "1/N", "1/N²", "log N / N"], "answer": 1, "explain": "Heisenberg-like 1/N scaling, before constant factors and noise.", "tags": ["qae rate"]},
        {"id": "p2q3", "type": "mc", "q": "Variance reduction (antithetic, control variates) changes:",
         "options": ["The rate exponent −0.5", "The constant σ, not the exponent", "Both", "Neither"], "answer": 1,
         "explain": "Same 1/√N rate, smaller σ.", "tags": ["variance reduction"]},
        {"id": "p2q4", "type": "mc", "q": "Optimal control-variate coefficient β* is:",
         "options": ["Var(C)/Cov(Y,C)", "Cov(Y,C)/Var(C)", "Corr(Y,C)", "1"], "answer": 1, "explain": "Minimises Var(Y − β(C − μ_C)).", "tags": ["variance reduction"]},
        {"id": "p2q5", "type": "mc", "q": "With correlation ρ between Y and C, the control variate's variance factor is:",
         "options": ["ρ", "1 − ρ", "1 − ρ²", "ρ²"], "answer": 2, "explain": "Var(Y^cv) = (1 − ρ²)Var(Y).", "tags": ["variance reduction"]},
        {"id": "p2q6", "type": "mc", "q": "Fisher information about θ from n shots of a circuit with m Grover iterations scales as:",
         "options": ["n", "n·m", "n·(2m+1)²", "n/(2m+1)"], "answer": 2, "explain": "The phase is amplified by 2m+1; information scales with its square.", "tags": ["fisher"]},
        {"id": "p2q7", "type": "mc", "q": "20 independent hypothesis tests at α=5% under the null: probability of ≥1 false positive is about:",
         "options": ["5%", "20%", "64%", "100%"], "answer": 2, "explain": "1 − 0.95²⁰ ≈ 0.64.", "tags": ["multiple comparisons"]},
        {"id": "p2q8", "type": "mc", "q": "The bootstrap CI for a median is obtained by:",
         "options": ["±1.96σ/√n", "Resampling with replacement and taking percentiles of the recomputed median", "Jackknife only", "Assuming normality of the data"],
         "answer": 1, "explain": "Percentile bootstrap.", "tags": ["bootstrap"]},
        {"id": "p2q9", "type": "mc", "q": "A fair comparison of a quantum estimator and MC is made at equal:",
         "options": ["Number of iterations", "Cost (queries/samples converted to wall time and money)", "Number of qubits", "Code length"],
         "answer": 1, "explain": "Equal-cost comparisons; iterations are not comparable units.", "tags": ["benchmarking"]},
        {"id": "p2q10", "type": "mc", "q": "A reported estimator error below the Cramér–Rao bound for the shots used suggests:",
         "options": ["Quantum advantage", "A bug, leakage or cherry-picking", "A good optimiser", "Nothing"], "answer": 1,
         "explain": "Unbiased estimators cannot beat the bound; investigate.", "tags": ["fisher", "validation"]},
        {"id": "p2q11", "type": "short", "q": "A vendor shows QAE needs 100× fewer samples than Monte Carlo for an option price. List the three things you check first.",
         "must": [["variance reduction", "control variate", "antithetic", "optimised", "optimized"], ["wall", "time", "clock", "cost"], ["seed", "confidence", "interval", "ci"]],
         "explain": "Baseline quality (variance reduction), equal-cost comparison (wall time per query vs per sample), and statistical robustness (seeds, CIs).", "tags": ["benchmarking"]},
        {"id": "p2q12", "type": "short", "q": "Why is 'up to 34% improvement' weak evidence on its own?",
         "must": [["maximum", "best", "up to", "cherry"], ["interval", "median", "distribution", "seeds", "windows"]],
         "explain": "It is the best of several runs; you need the distribution (median, CI) and the number of configurations tried.", "tags": ["multiple comparisons"]},
    ],
    "exercise": {
        "id": "p2_ex",
        "title": "Pricing, variance reduction and slope estimation",
        "prompt": (
            "Implement:\n1. `bs_call(S0, K, r, sigma, T)` Black–Scholes price.\n"
            "2. `mc_call(S0, K, r, sigma, T, N, rng, method='plain'|'antithetic'|'cv')` returning the estimate using exactly N payoff evaluations "
            "(antithetic: N/2 pairs).\n3. `loglog_slope(Ns, errors)` OLS slope of log(error) on log(N).\n"
            "4. `bootstrap_ci(x, stat, B, rng, level=0.95)` percentile CI as a tuple."
        ),
        "starter": '''import numpy as np
from scipy.stats import norm

def bs_call(S0, K, r, sigma, T):
    raise NotImplementedError

def mc_call(S0, K, r, sigma, T, N, rng, method="plain"):
    raise NotImplementedError

def loglog_slope(Ns, errors):
    raise NotImplementedError

def bootstrap_ci(x, stat, B, rng, level=0.95):
    raise NotImplementedError
''',
        "solution": '''import numpy as np
from scipy.stats import norm

def bs_call(S0, K, r, sigma, T):
    d1 = (np.log(S0/K) + (r + sigma**2/2)*T)/(sigma*np.sqrt(T)); d2 = d1 - sigma*np.sqrt(T)
    return S0*norm.cdf(d1) - K*np.exp(-r*T)*norm.cdf(d2)

def mc_call(S0, K, r, sigma, T, N, rng, method="plain"):
    disc = np.exp(-r*T)
    st = lambda z: S0*np.exp((r - sigma**2/2)*T + sigma*np.sqrt(T)*z)
    if method == "antithetic":
        z = rng.standard_normal(N//2)
        return disc*0.5*(np.maximum(st(z)-K, 0) + np.maximum(st(-z)-K, 0)).mean()
    z = rng.standard_normal(N)
    y = disc*np.maximum(st(z)-K, 0)
    if method == "plain":
        return y.mean()
    if method == "cv":
        c = disc*st(z); b = np.cov(y, c)[0, 1]/c.var(ddof=1)
        return (y - b*(c - S0)).mean()
    raise ValueError(method)

def loglog_slope(Ns, errors):
    return float(np.polyfit(np.log(Ns), np.log(errors), 1)[0])

def bootstrap_ci(x, stat, B, rng, level=0.95):
    x = np.asarray(x)
    vals = np.array([stat(rng.choice(x, x.size, replace=True)) for _ in range(B)])
    a = (1 - level)/2*100
    return (float(np.percentile(vals, a)), float(np.percentile(vals, 100 - a)))
''',
        "tests": '''import numpy as np

def test_bs_known_value():
    """BS(100,100,0.05,0.2,1) = 10.4506 (Hull's textbook example)"""
    assert abs(bs_call(100, 100, 0.05, 0.2, 1) - 10.4506) < 1e-3

def test_mc_unbiased_all_methods():
    """All three estimators within 4 standard errors of BS at N=200k"""
    ref = bs_call(100, 105, 0.03, 0.2, 1)
    for m in ("plain", "antithetic", "cv"):
        est = mc_call(100, 105, 0.03, 0.2, 1, 200_000, np.random.default_rng(7), m)
        assert abs(est - ref) < 0.06, (m, est, ref)

def test_cv_reduces_error():
    """CV RMSE over 40 seeds is lower than plain RMSE"""
    ref = bs_call(100, 105, 0.03, 0.2, 1)
    def rmse(m):
        return np.sqrt(np.mean([(mc_call(100,105,.03,.2,1,4000,np.random.default_rng(s),m)-ref)**2 for s in range(40)]))
    assert rmse("cv") < 0.7*rmse("plain")

def test_slope():
    """loglog_slope recovers -0.5 from exact power law"""
    Ns = np.array([100, 1000, 10000]); assert abs(loglog_slope(Ns, 3*Ns**-0.5) + 0.5) < 1e-9

def test_bootstrap_ci_covers():
    """bootstrap CI of the mean of N(0,1) n=500 contains 0 and has width ~0.17"""
    x = np.random.default_rng(1).standard_normal(500)
    lo, hi = bootstrap_ci(x, np.mean, 2000, np.random.default_rng(2))
    assert lo < 0 < hi and 0.12 < hi - lo < 0.24
''',
    },
    "cards": [
        {"front": "Plain MC RMSE scaling", "back": "σ/√N; log-log slope −0.5", "kind": "formula"},
        {"front": "Ideal QAE error scaling", "back": "∝ 1/N oracle queries; slope −1", "kind": "formula"},
        {"front": "Control variate β*", "back": "Cov(Y,C)/Var(C); variance × (1 − ρ²)", "kind": "formula"},
        {"front": "Antithetic variates", "back": "Average f(Z) and f(−Z); helps for monotone payoffs", "kind": "definition"},
        {"front": "Fisher info, Bernoulli p, n shots", "back": "n / (p(1−p))", "kind": "formula"},
        {"front": "Fisher info about θ with m Grover iterations", "back": "∝ n(2m+1)²", "kind": "formula"},
        {"front": "Cramér–Rao bound", "back": "Var(θ̂) ≥ 1/I(θ) for unbiased θ̂", "kind": "formula"},
        {"front": "Family-wise error, k tests at α", "back": "1 − (1 − α)^k; k=20 → ≈64%", "kind": "number"},
        {"front": "Bonferroni correction", "back": "Test each at α/k", "kind": "definition"},
        {"front": "Mistake: QAE vs plain MC", "back": "Always compare against variance-reduced, timed MC", "kind": "mistake"},
        {"front": "Mistake: 'up to X%'", "back": "Max of a distribution; ask for median and CI over seeds/windows", "kind": "mistake"},
        {"front": "BS call, S=K=100, r=5%, σ=20%, T=1", "back": "≈ 10.45", "kind": "number"},
    ],
    "defend": {
        "persona": "cro",
        "questions": [
            {"q": "Your slide says quantum Monte Carlo is quadratically faster. Faster than what, exactly?",
             "must": [["variance reduction", "control variate", "optimised", "optimized", "production"], ["timed", "wall", "time"]],
             "model": "Faster in query count than plain MC asymptotically; the relevant comparison is against our production, variance-reduced engine timed on our hardware."},
            {"q": "If the error rate is 1/N, why doesn't that automatically save me money?",
             "must": [["constant", "overhead", "factor"], ["clock", "speed", "time per", "wall"]],
             "model": "Constant factors (circuit depth per query, error correction overhead) and slow logical clock rates can outweigh the better exponent at precisions a desk needs."},
            {"q": "How many seeds did you run, and what's the interval on that slope?",
             "must": [["30", "thirty", "seeds"], ["confidence", "interval", "ci", "bootstrap"]],
             "model": "≥30 seeds per budget point, OLS slope with bootstrap CI; thresholds fixed beforehand."},
            {"q": "Your vendor reports 'up to 34%'. Do I put that in the business case?",
             "must": [["no", "not"], ["median", "interval", "distribution", "average"], ["comparison", "configuration", "multiple", "best"]],
             "model": "No. That's the best case among many configurations; I need the median gain with a CI across windows and seeds, corrected for multiple comparisons."},
            {"q": "What result would make you stop this line of work?",
             "must": [["threshold", "pre-registered", "fixed", "advance"], ["slope", "rmse", "error", "time"]],
             "model": "A pre-registered stop rule, e.g. the measured slope CI excludes −1 under realistic noise, or projected time exceeds 10× the optimised classical engine."},
        ],
    },
    "glossary": {
        "Variance reduction": "Techniques (antithetic, control variates, importance sampling) that lower σ without changing the 1/√N rate.",
        "Fisher information": "Curvature of the log-likelihood; bounds estimator precision via Cramér–Rao.",
        "Bootstrap": "Resampling with replacement to approximate a statistic's sampling distribution.",
        "Multiple comparisons": "Inflation of false positives when many hypotheses are tested.",
        "Log-log slope": "Exponent of a power law error ∝ N^k, estimated by regression on logs.",
    },
}
