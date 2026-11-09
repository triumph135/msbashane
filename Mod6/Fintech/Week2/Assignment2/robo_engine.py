"""
Robo advisor engine for FINC6580 (Build your own robo).

All dollar figures are in TODAY'S dollars (real terms). Nominal return
assumptions are converted to real returns using the inflation input.

The engine has four jobs:
  1. Turn a short risk questionnaire into a risk tolerance score (1 to 10).
  2. Map the client profile onto a target asset allocation (a glide path).
  3. Project savings, the house goal, and retirement spending, both as a
     simple expected path and as a Monte Carlo fan.
  4. Produce plain English advice.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import numpy as np

ASSETS = ["US Stocks", "Intl Stocks", "Bonds", "Cash"]

# Nominal capital market assumptions (arithmetic mean, volatility). Editable in the app.
DEFAULT_NOMINAL_RETURN = {"US Stocks": 0.075, "Intl Stocks": 0.080, "Bonds": 0.040, "Cash": 0.030}
DEFAULT_VOL = {"US Stocks": 0.16, "Intl Stocks": 0.18, "Bonds": 0.06, "Cash": 0.01}
CORR = np.array([
    [1.00, 0.85, 0.10, 0.00],
    [0.85, 1.00, 0.10, 0.00],
    [0.10, 0.10, 1.00, 0.20],
    [0.00, 0.00, 0.20, 1.00],
])

RISK_QUESTIONS = [
    ("If your portfolio fell 20% in three months, you would...",
     ["Sell everything", "Sell some", "Do nothing", "Buy a little more", "Buy a lot more"]),
    ("How would you describe your investing experience?",
     ["None", "Beginner", "Some", "Experienced", "Very experienced"]),
    ("What matters most for this money?",
     ["Never lose principal", "Mostly safety", "A balance", "Mostly growth", "Maximum growth"]),
    ("How stable is your income?",
     ["Very unstable", "Somewhat unstable", "Average", "Stable", "Very stable"]),
    ("What share of this money might you need within 5 years?",
     ["Almost all", "More than half", "About a third", "A small part", "None"]),
]


def risk_score(answers: list[int]) -> float:
    """answers: five integers 1 to 5. Returns a 1 to 10 risk tolerance score."""
    avg = float(np.mean(answers))          # 1..5
    return round(1 + (avg - 1) * 9 / 4, 1)  # 1..10


def risk_label(score: float) -> str:
    if score < 3.5:
        return "Conservative"
    if score < 5.5:
        return "Moderately conservative"
    if score < 7.5:
        return "Moderate"
    if score < 9:
        return "Moderately aggressive"
    return "Aggressive"


def real_return(nominal: float, inflation: float) -> float:
    return (1 + nominal) / (1 + inflation) - 1


@dataclass
class Client:
    age: int = 30
    retire_age: int = 65
    life_expectancy: int = 95
    current_assets: float = 50_000          # total investable assets
    house_set_aside: float = 0.0            # part of assets earmarked for the house goal
    income: float = 90_000                  # current annual income
    income_growth: float = 0.01             # real wage growth
    savings_rate: float = 0.15              # share of income saved now
    savings_rate_at_retire: float = 0.15    # rate in the last working years (linear blend)
    house_cost: float = 0.0                 # down payment target
    house_years: int = 0                    # years until purchase (0 means none)
    retire_spending: float = 60_000         # desired annual spending in retirement
    social_security: float = 28_000         # annual benefit, today's dollars
    ss_age: int = 67
    bequest: float = 0.0                    # amount to leave at end of plan
    risk: float = 5.5                       # 1 to 10
    retire_saving_override: float | None = None  # flat yearly retirement saving (today's $); used by the solver


@dataclass
class Assumptions:
    inflation: float = 0.025
    nominal_return: dict = field(default_factory=lambda: dict(DEFAULT_NOMINAL_RETURN))
    vol: dict = field(default_factory=lambda: dict(DEFAULT_VOL))
    intl_share_of_equity: float = 0.30
    n_sims: int = 2000
    seed: int = 7

    def mu_vec(self) -> np.ndarray:
        return np.array([real_return(self.nominal_return[a], self.inflation) for a in ASSETS])

    def cov(self) -> np.ndarray:
        s = np.array([self.vol[a] for a in ASSETS])
        return CORR * np.outer(s, s)


# ----------------------------------------------------------------------------
# Allocation rules
# ----------------------------------------------------------------------------
def goal_bucket_allocation(years: float) -> np.ndarray:
    """Allocation for a dated goal such as a house. Short horizons stay safe."""
    if years <= 3:
        eq, bond, cash = 0.0, 0.30, 0.70
    elif years <= 5:
        eq, bond, cash = 0.20, 0.60, 0.20
    elif years <= 10:
        eq, bond, cash = 0.50, 0.45, 0.05
    else:
        eq, bond, cash = 0.70, 0.28, 0.02
    return np.array([eq * 0.7, eq * 0.3, bond, cash])


def equity_target(age: int, client: Client, cap_adj: float, years_to_retire: float) -> float:
    base = 120 - age                                   # modern rule of thumb for longer lives
    risk_adj = (client.risk - 5.5) * 3.0               # about +/- 13 points
    # capacity adjustment phases in over the 10 years before retirement
    phase = float(np.clip((10 - years_to_retire) / 10, 0, 1))
    eq = base + risk_adj - cap_adj * phase
    return float(np.clip(eq, 20, 90)) / 100


def retirement_allocation(age: int, client: Client, cap_adj: float, asm: Assumptions) -> np.ndarray:
    ytr = client.retire_age - age
    eq = equity_target(age, client, cap_adj, ytr)
    non_eq = 1 - eq
    # cash: thin sleeve while working, a spending reserve in retirement
    cash_floor = 0.02 if ytr > 5 else 0.05
    cash = min(non_eq, cash_floor)
    bonds = non_eq - cash
    return np.array([eq * (1 - asm.intl_share_of_equity), eq * asm.intl_share_of_equity, bonds, cash])


def port_stats(w: np.ndarray, asm: Assumptions) -> tuple[float, float]:
    mu = float(w @ asm.mu_vec())
    sd = float(np.sqrt(w @ asm.cov() @ w))
    return mu, sd


# ----------------------------------------------------------------------------
# Cash flow plan
# ----------------------------------------------------------------------------
def house_plan(client: Client, asm: Assumptions) -> dict:
    """Annual saving required to hit the house target using a safe bucket."""
    if client.house_years <= 0 or client.house_cost <= 0:
        return dict(active=False, required=0.0, return_=0.0, weights=None, shortfall=0.0)
    w = goal_bucket_allocation(client.house_years)
    mu, sd = port_stats(w, asm)
    n = client.house_years
    fv_existing = client.house_set_aside * (1 + mu) ** n
    gap = max(client.house_cost - fv_existing, 0)
    annuity = sum((1 + mu) ** (n - 1 - t) for t in range(n))   # end of year deposits
    required = gap / annuity if annuity else 0.0
    return dict(active=True, required=required, return_=mu, sd=sd, weights=w, fv_existing=fv_existing, gap=gap)


def contributions_by_age(client: Client, hp: dict) -> dict:
    """Annual retirement contribution for each working age, in today's dollars."""
    out = {}
    work_years = max(client.retire_age - client.age, 1)
    for i in range(client.retire_age - client.age):
        age = client.age + i
        income = client.income * (1 + client.income_growth) ** i
        rate = client.savings_rate + (client.savings_rate_at_retire - client.savings_rate) * (i / max(work_years - 1, 1))
        total_save = income * rate
        house_part = hp["required"] if (hp["active"] and i < client.house_years) else 0.0
        if client.retire_saving_override is not None:
            ret = client.retire_saving_override
            out[age] = dict(income=income, total=ret + house_part, house=house_part, retirement=ret, shortfall=0.0)
            continue
        out[age] = dict(income=income, total=total_save, house=min(house_part, total_save),
                        retirement=max(total_save - house_part, 0.0), shortfall=max(house_part - total_save, 0.0))
    return out


def withdrawal_by_age(client: Client) -> dict:
    out = {}
    for age in range(client.retire_age, client.life_expectancy):
        ss = client.social_security if age >= client.ss_age else 0.0
        out[age] = max(client.retire_spending - ss, 0.0)
    return out


def simulate(client: Client, asm: Assumptions, spending: float | None = None, n_sims: int | None = None,
             cap_adj: float = 0.0, start_assets: float | None = None) -> dict:
    """Monte Carlo of the retirement account from today to life expectancy."""
    n_sims = n_sims or asm.n_sims
    c = Client(**{**client.__dict__})
    if spending is not None:
        c.retire_spending = spending
    hp = house_plan(c, asm)
    contribs = contributions_by_age(c, hp)
    wds = withdrawal_by_age(c)
    ages = list(range(c.age, c.life_expectancy))
    rng = np.random.default_rng(asm.seed)
    start = (c.current_assets - c.house_set_aside) if start_assets is None else start_assets
    bal = np.full(n_sims, max(start, 0.0))
    path = np.zeros((len(ages) + 1, n_sims))
    path[0] = bal
    chol = np.linalg.cholesky(asm.cov())
    mu = asm.mu_vec()
    alive = np.ones(n_sims, dtype=bool)          # becomes False once depleted
    depleted_age = np.full(n_sims, np.nan)
    weights_path = []
    for k, age in enumerate(ages):
        w = retirement_allocation(age, c, cap_adj, asm)
        weights_path.append(w)
        z = rng.standard_normal((n_sims, 4))
        r = mu + z @ chol.T
        pr = np.clip(r @ w, -0.6, 1.0)
        if age < c.retire_age:
            bal = bal * (1 + pr) + contribs[age]["retirement"]
        else:
            need = wds.get(age, 0.0)
            bal = bal - need
            newly = (bal <= 0) & alive
            depleted_age[newly] = age
            alive &= bal > 0
            bal = np.where(bal > 0, bal * (1 + pr), 0.0)
        path[k + 1] = bal
    success = (path[-1] >= c.bequest) & alive
    return dict(ages=[c.age] + [a + 1 for a in ages], path=path, success=float(success.mean()),
                weights=np.array(weights_path), age_list=ages, contribs=contribs, hp=hp,
                depleted_age=depleted_age, client=c)


def expected_path(client: Client, asm: Assumptions, cap_adj: float = 0.0) -> dict:
    """Single deterministic path using each year's expected portfolio return."""
    hp = house_plan(client, asm)
    contribs = contributions_by_age(client, hp)
    wds = withdrawal_by_age(client)
    bal = max(client.current_assets - client.house_set_aside, 0.0)
    rows = [(client.age, bal)]
    for age in range(client.age, client.life_expectancy):
        w = retirement_allocation(age, client, cap_adj, asm)
        mu, _ = port_stats(w, asm)
        if age < client.retire_age:
            bal = bal * (1 + mu) + contribs[age]["retirement"]
        else:
            bal = max(bal - wds.get(age, 0.0), 0.0) * (1 + mu) if bal > 0 else 0.0
        rows.append((age + 1, bal))
    return dict(rows=rows, hp=hp, contribs=contribs)


def house_path(client: Client, asm: Assumptions) -> list[tuple[int, float]]:
    hp = house_plan(client, asm)
    if not hp["active"]:
        return []
    bal = client.house_set_aside
    rows = [(0, bal)]
    for t in range(client.house_years):
        bal = bal * (1 + hp["return_"]) + hp["required"]
        rows.append((t + 1, bal))
    return rows


def sustainable_spending(client: Client, asm: Assumptions, target_success: float = 0.85, cap_adj: float = 0.0) -> float:
    """Highest spending (today's dollars) that still meets the success target."""
    lo, hi = 0.0, max(client.retire_spending * 3, 50_000)
    for _ in range(18):
        mid = (lo + hi) / 2
        s = simulate(client, asm, spending=mid, n_sims=2000, cap_adj=cap_adj)["success"]
        if s >= target_success + 0.01:
            lo = mid
        else:
            hi = mid
    return lo


def capacity_adjustment(client: Client, asm: Assumptions) -> float:
    """Cut equity if the planned withdrawal rate at retirement is high."""
    ep = expected_path(client, asm, cap_adj=0.0)
    bal_at_ret = dict(ep["rows"]).get(client.retire_age, 0.0)
    need = withdrawal_by_age(client).get(client.retire_age, 0.0)
    if client.age >= client.retire_age:
        bal_at_ret = max(client.current_assets - client.house_set_aside, 1.0)
    wd = need / bal_at_ret if bal_at_ret > 0 else 0.10
    return float(np.clip((wd - 0.04) * 250, 0, 15)), wd


# ----------------------------------------------------------------------------
# Top level recommendation
# ----------------------------------------------------------------------------
def recommend(client: Client, asm: Assumptions) -> dict:
    cap_adj, wd_rate = capacity_adjustment(client, asm)
    hp = house_plan(client, asm)
    sim = simulate(client, asm, cap_adj=cap_adj)
    ep = expected_path(client, asm, cap_adj=cap_adj)
    w_now = retirement_allocation(client.age, client, cap_adj, asm)
    w_ret = retirement_allocation(max(client.retire_age, client.age), client, cap_adj, asm)
    rows = dict(ep["rows"])
    bal_ret = rows.get(max(client.retire_age, client.age), rows[client.age])
    sust = sustainable_spending(client, asm, 0.85, cap_adj)
    pct = np.percentile(sim["path"], [10, 50, 90], axis=1)
    contribs = ep["contribs"]
    shortfall = sum(v["shortfall"] for v in contribs.values())
    return dict(client=client, asm=asm, cap_adj=cap_adj, wd_rate=wd_rate, hp=hp, sim=sim, ep=ep,
                w_now=w_now, w_ret=w_ret, bal_at_retire_expected=bal_ret, sustainable=sust,
                pct=pct, house_rows=house_path(client, asm), house_shortfall=shortfall)


def advice_text(rec: dict) -> list[str]:
    c: Client = rec["client"]
    out = []
    eq_now = rec["w_now"][0] + rec["w_now"][1]
    out.append(f"Your risk profile is {risk_label(c.risk)} ({c.risk:.1f} out of 10). "
               f"For your retirement money we recommend about {eq_now:.0%} in stocks today, "
               f"{rec['w_now'][2]:.0%} in bonds and {rec['w_now'][3]:.0%} in cash, "
               f"drifting to {rec['w_ret'][0] + rec['w_ret'][1]:.0%} stocks by retirement.")
    hp = rec["hp"]
    if hp["active"]:
        out.append(f"House goal: keep the down payment out of stocks. Put {hp['weights'][3]:.0%} in cash and "
                   f"{hp['weights'][2]:.0%} in short term bonds, and save about ${hp['required']:,.0f} per year "
                   f"for {c.house_years} years to reach ${c.house_cost:,.0f}.")
        if rec["house_shortfall"] > 1:
            out.append(f"Warning: the house goal needs more than you plan to save. You are short by about "
                       f"${rec['house_shortfall']:,.0f} in total. Raise savings, lower the target, or push the date out.")
    s = rec["sim"]["success"]
    if c.age >= c.retire_age:
        out.append(f"You are already retired. Spending ${c.retire_spending:,.0f} per year (before Social Security) "
                   f"implies a starting withdrawal rate of {rec['wd_rate']:.1%} of savings.")
    else:
        out.append(f"Expected savings at age {c.retire_age} is about ${rec['bal_at_retire_expected']:,.0f} in today's dollars.")
    verdict = "on track" if s >= 0.85 else ("borderline" if s >= 0.65 else "at risk")
    out.append(f"Chance your money lasts to age {c.life_expectancy} while spending ${c.retire_spending:,.0f} per year: "
               f"{s:.0%} ({verdict}). Spending of about ${rec['sustainable']:,.0f} per year would give an 85% chance.")
    if s < 0.85 and c.age < c.retire_age:
        out.append("To improve the odds: save more, retire later, claim Social Security later, or plan to spend less.")
    if rec["cap_adj"] > 0:
        out.append(f"Your planned withdrawal rate ({rec['wd_rate']:.1%}) is high, so we trimmed stocks by {rec['cap_adj']:.0f} points to limit the damage from a bad market early in retirement.")
    return out


# ----------------------------------------------------------------------------
# Action plan: how much to save, where to put it, what to buy
# ----------------------------------------------------------------------------
# 2026 IRS limits (IRS Notice 2025-67; HSA from Rev. Proc. 2025-19)
LIMITS_2026 = dict(k401=24_500, k401_catch50=8_000, k401_catch60_63=11_250,
                   ira=7_500, ira_catch50=1_100,
                   hsa_self=4_400, hsa_family=8_750, hsa_catch55=1_000,
                   roth_single=(153_000, 168_000), roth_joint=(242_000, 252_000))

FUND_TYPES = {
    "US Stocks": ("Total US stock market index fund", "e.g. VTI, FSKAX, or a target date fund's US sleeve"),
    "Intl Stocks": ("Total international stock index fund", "e.g. VXUS, FTIHX"),
    "Bonds": ("Total bond market or Treasury index fund", "e.g. BND, FXNAX, or a short Treasury fund"),
    "Cash": ("High yield savings, money market, or T-bills", "FDIC insured savings or a Treasury money market fund"),
}


def _clone(client: Client, **kw) -> Client:
    d = dict(client.__dict__)
    d.update(kw)
    return Client(**d)


def solve_required_saving(client: Client, asm: Assumptions, target: float, cap_adj: float):
    """Flat yearly retirement saving (today's $) that reaches the target success rate. None if out of reach."""
    def ok(x):
        return simulate(_clone(client, retire_saving_override=x), asm, n_sims=2000, cap_adj=cap_adj)["success"] >= target + 0.01
    hi = max(client.income * 0.6, 20_000.0)
    if ok(0.0):
        return 0.0
    if not ok(hi):
        return None
    lo = 0.0
    for _ in range(16):
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if ok(mid) else (mid, hi)
    return hi


def solve_retire_age(client: Client, asm: Assumptions, target: float, cap_adj: float, max_age: int = 75):
    """Earliest retirement age (keeping the current saving plan) that reaches the target. None if not by max_age."""
    for ra in range(client.retire_age, min(max_age, client.life_expectancy - 1) + 1):
        c = _clone(client, retire_age=ra, ss_age=max(client.ss_age, min(ra, 70)) if ra > client.ss_age else client.ss_age)
        if simulate(c, asm, n_sims=2000, cap_adj=cap_adj)["success"] >= target + 0.01:
            return ra
    return None


def account_waterfall(client: Client, amount: float, o: dict) -> list[dict]:
    """Fill accounts in a standard priority order. amount = annual retirement saving. o = account options."""
    L = LIMITS_2026
    steps, left = [], max(amount, 0.0)
    age = client.age

    def add(account, amt, why):
        nonlocal left
        amt = min(left, amt)
        if amt <= 0.5:
            return
        steps.append(dict(account=account, annual=amt, monthly=amt / 12, why=why))
        left -= amt

    if o.get("has_401k") and o.get("match_cap", 0) > 0:
        add("401(k) or 403(b) up to the employer match", client.income * o["match_cap"],
            f"Employer adds about {o['match_rate']:.0%} on these dollars. This is free money, so it comes first. "
            f"(The match is a bonus and is not counted in the projections.)")
    if o.get("hsa"):
        lim = (L["hsa_family"] if o.get("hsa_family") else L["hsa_self"]) + (L["hsa_catch55"] if age >= 55 else 0)
        add("HSA", lim, "Triple tax benefit: deductible in, tax free growth, tax free for medical costs. Invest it, do not just spend it.")
    phase = L["roth_joint"] if o.get("joint") else L["roth_single"]
    ira_lim = L["ira"] + (L["ira_catch50"] if age >= 50 else 0)
    if client.income < phase[1]:
        part = " (income is in the phase out range, so the allowed amount is reduced)" if client.income > phase[0] else ""
        add("Roth IRA", ira_lim, "Tax free growth and withdrawals. Best while your tax rate is lower now than it will be in retirement" + part + ".")
    else:
        add("Traditional IRA with a backdoor Roth conversion", ira_lim,
            "Income is above the direct Roth limit. A backdoor Roth is common, but ask a tax professional first.")
    if o.get("has_401k"):
        lim = L["k401"] + (L["k401_catch60_63"] if 60 <= age <= 63 else (L["k401_catch50"] if age >= 50 else 0))
        used = sum(x["annual"] for x in steps if x["account"].startswith("401(k)"))
        add("401(k) or 403(b), rest of the way toward the limit", max(lim - used, 0),
            "Pre-tax (traditional) lowers this year's tax. Roth 401(k) if offered and your bracket is low.")
    add("Taxable brokerage account", left, "No limits and fully flexible. Use tax efficient index funds and hold them long term.")
    return steps


def action_plan(rec: dict, target: float, o: dict) -> dict:
    c: Client = rec["client"]
    asm: Assumptions = rec["asm"]
    cap = rec["cap_adj"]
    w = rec["w_now"]
    out = dict(retired=c.age >= c.retire_age, target=target, w=w)
    if out["retired"]:
        annual_need = max(c.retire_spending - (c.social_security if c.age >= c.ss_age else 0.0), 0.0)
        bal = max(c.current_assets, 0.0)
        cash_b = min(bal, annual_need * 2)
        bond_b = min(bal - cash_b, annual_need * 5)
        stock_b = max(bal - cash_b - bond_b, 0.0)
        out.update(annual_need=annual_need, cash_bucket=cash_b, bond_bucket=bond_b, stock_bucket=stock_b)
        return out
    work = [v for v in rec["ep"]["contribs"].values()]
    planned_avg = float(np.mean([v["retirement"] for v in work])) if work else 0.0
    req = solve_required_saving(c, asm, target, cap)
    ra = solve_retire_age(c, asm, target, cap)
    sust = sustainable_spending(c, asm, target, cap)
    hp = rec["hp"]
    house = hp["required"] if hp["active"] else 0.0
    out.update(planned_avg=planned_avg, required=req, retire_age_needed=ra, sustainable=sust, house=house,
               on_track=rec["sim"]["success"] >= target)
    amount = planned_avg if (out["on_track"] or req is None) else req
    out["amount_used"] = amount
    out["waterfall"] = account_waterfall(c, amount, o)
    out["emergency_low"] = c.income * 0.6 * 3 / 12 * 1.0
    out["emergency_high"] = c.income * 0.6 * 6 / 12 * 1.0
    return out
