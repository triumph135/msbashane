"""Streamlit robo advisor. Run with:  streamlit run app.py"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from robo_engine import (FUND_TYPES, LIMITS_2026, action_plan, goal_bucket_allocation, ASSETS, RISK_QUESTIONS, Assumptions, Client, advice_text, recommend,
                         risk_label, risk_score, DEFAULT_NOMINAL_RETURN, DEFAULT_VOL)

st.set_page_config(page_title="Build Your Own Robo", page_icon="📈", layout="wide")

COLORS = {"US Stocks": "#1f4e79", "Intl Stocks": "#5b9bd5", "Bonds": "#8c8c8c", "Cash": "#c9a227"}

PRESETS = {
    "Custom": None,
    "30 year old saver (house in 2 years, retire in 35)": dict(
        age=30, retire_age=65, life_expectancy=95, current_assets=50000, house_set_aside=30000,
        income=90000, income_growth=1.0, savings_rate=20, savings_rate_end=15, house_cost=60000, house_years=2,
        retire_spending=65000, social_security=30000, ss_age=67, bequest=0, answers=[3, 3, 4, 4, 4]),
    "55 year old with $200K saved": dict(
        age=55, retire_age=67, life_expectancy=95, current_assets=200000, house_set_aside=0,
        income=90000, income_growth=0.0, savings_rate=15, savings_rate_end=15, house_cost=0, house_years=0,
        retire_spending=55000, social_security=28000, ss_age=67, bequest=0, answers=[3, 3, 3, 4, 3]),
    "70 year old retiree with $2 million": dict(
        age=70, retire_age=70, life_expectancy=95, current_assets=2000000, house_set_aside=0,
        income=0, income_growth=0.0, savings_rate=0, savings_rate_end=0, house_cost=0, house_years=0,
        retire_spending=120000, social_security=40000, ss_age=70, bequest=0, answers=[3, 3, 2, 5, 3]),
}


def load_preset():
    p = PRESETS[st.session_state["preset"]]
    if p is None:
        return
    for k, v in p.items():
        if k == "answers":
            for i, a in enumerate(v):
                st.session_state[f"q{i}"] = RISK_QUESTIONS[i][1][a - 1]
        else:
            st.session_state[k] = v


def money(x):
    return f"${x:,.0f}"



DEFAULTS = dict(age=30, retire_age=65, life_expectancy=95, current_assets=50000, house_set_aside=0, income=90000,
                income_growth=1.0, savings_rate=15, savings_rate_end=15, house_cost=0, house_years=0,
                retire_spending=65000, social_security=30000, ss_age=67, bequest=0,
                target_conf=85, has_401k=True, match_rate=50, match_cap=6, hsa=False, hsa_family=False, joint=False)
for _k, _v in DEFAULTS.items():
    st.session_state.setdefault(_k, _v)
for _i, (_q, _o) in enumerate(RISK_QUESTIONS):
    st.session_state.setdefault(f"q{_i}", _o[2])
# keep dependent inputs inside their allowed ranges when earlier inputs change
st.session_state["retire_age"] = max(st.session_state["retire_age"], st.session_state["age"])
st.session_state["life_expectancy"] = max(st.session_state["life_expectancy"], st.session_state["retire_age"] + 1)
st.session_state["house_set_aside"] = min(st.session_state["house_set_aside"], st.session_state["current_assets"])

# ---------------------------------------------------------------- sidebar
st.sidebar.title("Client profile")
st.sidebar.selectbox("Start from an example", list(PRESETS), key="preset", on_change=load_preset)

with st.sidebar.expander("1. About you", expanded=True):
    age = st.number_input("Age", 18, 90, key="age")
    retire_age = st.number_input("Retirement age", int(age), 90, key="retire_age")
    life_expectancy = st.number_input("Plan through age", int(retire_age) + 1, 110, key="life_expectancy")
with st.sidebar.expander("2. Money today", expanded=True):
    current_assets = st.number_input("Investable assets ($)", 0, 50_000_000, step=5_000, key="current_assets")
    income = st.number_input("Annual income ($)", 0, 5_000_000, step=5_000, key="income")
    income_growth = st.number_input("Real income growth (% per year)", 0.0, 10.0, step=0.25, key="income_growth")
    savings_rate = st.slider("Savings rate now (% of income)", 0, 60, key="savings_rate")
    savings_rate_end = st.slider("Savings rate just before retirement (%)", 0, 60, key="savings_rate_end")
with st.sidebar.expander("3. Goals", expanded=True):
    st.caption("Retirement")
    retire_spending = st.number_input("Retirement spending per year, today's $", 0, 5_000_000, step=5_000, key="retire_spending")
    social_security = st.number_input("Social Security per year, today's $", 0, 200_000, step=1_000, key="social_security")
    ss_age = st.number_input("Social Security starts at age", 62, 70, key="ss_age")
    bequest = st.number_input("Amount to leave behind, today's $", 0, 50_000_000, step=25_000, key="bequest")
    st.caption("House (optional)")
    house_cost = st.number_input("House down payment target ($)", 0, 5_000_000, step=5_000, key="house_cost")
    house_years = st.number_input("Years until purchase", 0, 30, key="house_years")
    house_set_aside = st.number_input("Already set aside for the house ($)", 0, int(max(current_assets, 1)), step=5_000, key="house_set_aside")
with st.sidebar.expander("4. Risk attitude", expanded=True):
    answers = []
    for i, (q, opts) in enumerate(RISK_QUESTIONS):
        choice = st.radio(q, opts, key=f"q{i}")
        answers.append(opts.index(choice) + 1)
    rs = risk_score(answers)
    st.metric("Risk tolerance", f"{rs} / 10", risk_label(rs))
with st.sidebar.expander("5. Accounts and plan"):
    target_conf = st.slider("Confidence target (chance the plan works, %)", 60, 95, key="target_conf")
    has_401k = st.checkbox("I have a 401(k) or 403(b) at work", key="has_401k")
    match_rate = st.number_input("Employer match rate (% of what you put in)", 0, 200, step=10, key="match_rate")
    match_cap = st.number_input("...on contributions up to (% of pay)", 0, 25, key="match_cap")
    hsa = st.checkbox("I am eligible for an HSA (high deductible health plan)", key="hsa")
    hsa_family = st.checkbox("Family HSA coverage", key="hsa_family")
    joint = st.checkbox("Married filing jointly", key="joint")
with st.sidebar.expander("Market assumptions (advanced)"):
    inflation = st.number_input("Inflation (%)", 0.0, 8.0, 2.5, step=0.25) / 100
    nominal = {a: st.number_input(f"{a} nominal return (%)", 0.0, 15.0, DEFAULT_NOMINAL_RETURN[a] * 100, step=0.25, key=f"r_{a}") / 100 for a in ASSETS}
    vols = {a: st.number_input(f"{a} volatility (%)", 0.0, 40.0, DEFAULT_VOL[a] * 100, step=0.5, key=f"v_{a}") / 100 for a in ASSETS}
    n_sims = st.select_slider("Simulations", [500, 1000, 2000, 5000], value=2000)

client = Client(age=int(age), retire_age=int(retire_age), life_expectancy=int(life_expectancy),
                current_assets=float(current_assets), house_set_aside=float(house_set_aside), income=float(income),
                income_growth=income_growth / 100, savings_rate=savings_rate / 100,
                savings_rate_at_retire=savings_rate_end / 100, house_cost=float(house_cost),
                house_years=int(house_years), retire_spending=float(retire_spending),
                social_security=float(social_security), ss_age=int(ss_age), bequest=float(bequest), risk=rs)
asm = Assumptions(inflation=inflation, nominal_return=nominal, vol=vols, n_sims=int(n_sims))
rec = recommend(client, asm)

# ---------------------------------------------------------------- header
st.title("Build Your Own Robo Advisor")
st.caption("FINC6580 Fintech. All dollar amounts are in today's dollars (inflation adjusted). "
           "This is a classroom model, not personal financial advice.")

sim, hp = rec["sim"], rec["hp"]
k1, k2, k3, k4 = st.columns(4)
k1.metric("Risk profile", risk_label(rs), f"{rs} / 10", delta_color="off")
eq_now = rec["w_now"][0] + rec["w_now"][1]
k2.metric("Stocks today", f"{eq_now:.0%}", f"{rec['w_ret'][0] + rec['w_ret'][1]:.0%} at retirement", delta_color="off")
k3.metric("Chance money lasts", f"{sim['success']:.0%}", f"to age {client.life_expectancy}", delta_color="off")
k4.metric("Sustainable spending", money(rec["sustainable"]), "at 85% confidence", delta_color="off")

st.subheader("Recommendation")
for line in advice_text(rec):
    st.markdown(f"- {line}")

tab0, tab1, tab2, tab3, tab4 = st.tabs(["Action plan", "Allocation", "Savings projection", "Retirement spending", "House goal"])

# ---------------------------------------------------------------- action plan
with tab0:
    opts = dict(has_401k=has_401k, match_rate=match_rate / 100, match_cap=match_cap / 100, hsa=hsa,
                hsa_family=hsa_family, joint=joint)
    ap = action_plan(rec, target_conf / 100, opts)
    wts = rec["w_now"]
    st.caption(f"Targets a {target_conf}% chance of success. 2026 IRS limits. Dollars are in today's dollars.")

    def fund_table(total_dollars, label):
        df = pd.DataFrame({
            "Asset class": ASSETS,
            "Target": [f"{x:.0%}" for x in wts],
            label: [money(total_dollars * x) for x in wts],
            "What to buy": [FUND_TYPES[a][0] for a in ASSETS],
            "Examples": [FUND_TYPES[a][1] for a in ASSETS]})
        st.dataframe(df, hide_index=True, use_container_width=True)

    if ap["retired"]:
        st.markdown("### 1. How much you can take out")
        c1, c2, c3 = st.columns(3)
        c1.metric("Needed from portfolio now", money(ap["annual_need"]) + " / yr", f"{money(ap['annual_need'] / 12)} / month", delta_color="off")
        c2.metric("Sustainable spending", money(rec["sustainable"]) + " / yr", f"at {target_conf}% confidence", delta_color="off")
        gap = rec["sustainable"] - client.retire_spending
        c3.metric("Cushion vs. your plan", money(gap) + " / yr", "room to spend more" if gap >= 0 else "spending is above the safe level", delta_color="off")
        st.markdown("### 2. Three buckets, so you never sell stocks in a crash")
        b = pd.DataFrame({
            "Bucket": ["Cash: next 2 years of withdrawals", "Bonds: years 3 to 7", "Stocks: everything else"],
            "Amount": [money(ap["cash_bucket"]), money(ap["bond_bucket"]), money(ap["stock_bucket"])],
            "Hold in": ["High yield savings, money market, T-bills", "Treasury or total bond index funds", "Total US and international stock index funds"]})
        st.dataframe(b, hide_index=True, use_container_width=True)
        st.caption("Refill the cash bucket each year from bond interest, dividends, and (after a good year) stock sales. After a bad year, spend from cash and let stocks recover.")
        st.markdown("### 3. Which account to draw from")
        st.markdown("""
1. Required minimum distributions first once they start (around age 73 to 75) from traditional IRA or 401(k).
2. Before that, usually take from the taxable account first, then traditional accounts, and leave Roth for last so it can keep growing tax free. A tax professional can fine tune this and plan Roth conversions in low income years.
3. Think about when to claim Social Security. Waiting raises the benefit and acts as inflation protected insurance.
""")
        st.markdown("### 4. Target mix for the whole portfolio")
        fund_table(client.current_assets, "Dollars")
    else:
        st.markdown("### 1. How much to save")
        planned_mo = ap["planned_avg"] / 12
        if ap["on_track"]:
            st.success(f"Your current plan already reaches a {target_conf}% chance of success. Keep saving about "
                       f"{money(ap['planned_avg'])} a year ({money(planned_mo)} a month) toward retirement.")
        elif ap["required"] is None:
            st.error("Saving alone cannot get you there at this confidence level. Combine the options below: retire later, spend less, or lower the target.")
        else:
            st.warning(f"To reach {target_conf}% you need to save about **{money(ap['required'])} a year "
                       f"({money(ap['required'] / 12)} a month)** toward retirement, "
                       f"{ap['required'] / max(client.income, 1):.0%} of your income, versus about {money(ap['planned_avg'])} a year in your current plan.")
        m1, m2, m3 = st.columns(3)
        m1.metric("Retirement saving", money(ap["amount_used"]) + " / yr", f"{money(ap['amount_used'] / 12)} / month", delta_color="off")
        m2.metric("House saving", money(ap["house"]) + " / yr" if ap["house"] else "None",
                  f"for {client.house_years} years" if ap["house"] else "no house goal", delta_color="off")
        total_now = ap["amount_used"] + ap["house"]
        m3.metric("Total to set aside now", money(total_now) + " / yr", f"{money(total_now / 12)} / month ({total_now / max(client.income, 1):.0%} of income)", delta_color="off")
        if not ap["on_track"]:
            st.markdown("**Or reach the same target a different way (pick one):**")
            alt = pd.DataFrame({
                "Option": ["Save more", "Work longer", "Spend less in retirement"],
                "What it takes": [
                    money(ap["required"]) + " a year toward retirement" if ap["required"] is not None else "Not enough by itself",
                    (f"Retire at {ap['retire_age_needed']} instead of {client.retire_age}" if ap["retire_age_needed"] else "Not enough even by age 75"),
                    money(ap["sustainable"]) + f" a year instead of {money(client.retire_spending)}"]})
            st.dataframe(alt, hide_index=True, use_container_width=True)

        st.markdown("### 2. Where to save it (in this order)")
        st.caption("First, an emergency fund of 3 to 6 months of living costs "
                   f"(roughly {money(ap['emergency_low'])} to {money(ap['emergency_high'])}) in a high yield savings account. Then fill these accounts in order:")
        wf = pd.DataFrame([{"Order": i + 1, "Account": s_["account"], "Per year": money(s_["annual"]),
                            "Per month": money(s_["monthly"]), "Why": s_["why"]} for i, s_ in enumerate(ap["waterfall"])])
        st.dataframe(wf, hide_index=True, use_container_width=True)
        st.caption("Roth IRA and Roth 401(k) suit lower tax brackets today. Traditional (pre tax) suits higher brackets. Put bonds in tax deferred accounts and stocks in Roth or taxable when you can.")

        st.markdown("### 3. What to invest in")
        st.markdown("**Retirement money** (same mix in every account, or use a single target date fund near your retirement year)")
        fund_table(ap["amount_used"], "New money per year")
        if ap["house"]:
            hw = goal_bucket_allocation(client.house_years)
            st.markdown(f"**House money** (outside retirement accounts, because you will need it in {client.house_years} years)")
            hdf = pd.DataFrame({
                "Where": ["High yield savings or money market", "Short Treasury bills, CDs, or a short term bond fund"],
                "Share": [f"{hw[3]:.0%}", f"{hw[2]:.0%}"],
                "Per year": [money(ap["house"] * hw[3]), money(ap["house"] * hw[2])]})
            if hw[0] + hw[1] > 0:
                hdf.loc[len(hdf)] = ["Stock index fund", f"{hw[0] + hw[1]:.0%}", money(ap["house"] * (hw[0] + hw[1]))]
            st.dataframe(hdf, hide_index=True, use_container_width=True)
        st.markdown("**What you already have**")
        fund_table(max(client.current_assets - client.house_set_aside, 0), "Dollars today")
        st.caption("Example fund names are illustrations of the fund type, not recommendations. Compare fees (look for expense ratios under 0.20%).")


# ---------------------------------------------------------------- allocation
with tab1:
    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown("**Retirement portfolio today**")
        fig = go.Figure(go.Pie(labels=ASSETS, values=rec["w_now"], hole=0.5, sort=False,
                               marker_colors=[COLORS[a] for a in ASSETS], textinfo="label+percent"))
        fig.update_layout(height=340, margin=dict(t=10, b=10, l=10, r=10), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        dollars = (client.current_assets - client.house_set_aside) * rec["w_now"]
        tbl = pd.DataFrame({"Asset class": ASSETS, "Weight": [f"{w:.1%}" for w in rec["w_now"]],
                            "Amount": [money(d) for d in dollars]})
        st.dataframe(tbl, hide_index=True, use_container_width=True)
    with c2:
        st.markdown("**Glide path: how the mix changes with age**")
        gp = sim["weights"]
        fig = go.Figure()
        for j, a in enumerate(ASSETS):
            fig.add_trace(go.Scatter(x=sim["age_list"], y=gp[:, j], name=a, stackgroup="one",
                                     line=dict(width=0.5, color=COLORS[a]), fillcolor=COLORS[a]))
        fig.add_vline(x=client.retire_age, line_dash="dash", annotation_text="Retire")
        fig.update_layout(height=380, yaxis=dict(tickformat=".0%", title="Share of portfolio"),
                          xaxis_title="Age", margin=dict(t=10, b=10), legend=dict(orientation="h"))
        st.plotly_chart(fig, use_container_width=True)
    if hp["active"]:
        st.markdown("**House money (kept separate and safe)**")
        st.write(f"{hp['weights'][3]:.0%} cash, {hp['weights'][2]:.0%} short term bonds, "
                 f"{hp['weights'][0] + hp['weights'][1]:.0%} stocks.")

# ---------------------------------------------------------------- projection
with tab2:
    ages = np.array(sim["ages"])
    p10, p50, p90 = rec["pct"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ages, y=p90, line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=ages, y=p10, fill="tonexty", fillcolor="rgba(91,155,213,0.25)", line=dict(width=0),
                             name="10th to 90th percentile"))
    fig.add_trace(go.Scatter(x=ages, y=p50, name="Median", line=dict(color="#1f4e79", width=3)))
    ep_ages, ep_bal = zip(*rec["ep"]["rows"])
    fig.add_trace(go.Scatter(x=ep_ages, y=ep_bal, name="Expected path", line=dict(color="#c9a227", dash="dot")))
    fig.add_vline(x=client.retire_age, line_dash="dash", annotation_text="Retire")
    fig.update_layout(height=450, xaxis_title="Age", yaxis_title="Portfolio value (today's $)",
                      yaxis_tickprefix="$", yaxis_tickformat=",.0f", margin=dict(t=10), legend=dict(orientation="h"))
    st.plotly_chart(fig, use_container_width=True)
    rows = dict(zip(ages.tolist(), range(len(ages))))
    milestones = sorted({client.age, min(client.age + 10, client.life_expectancy), client.retire_age,
                         min(client.retire_age + 10, client.life_expectancy), client.life_expectancy})
    mt = pd.DataFrame({"Age": milestones,
                       "Pessimistic (10th)": [money(p10[rows[a]]) for a in milestones],
                       "Median": [money(p50[rows[a]]) for a in milestones],
                       "Optimistic (90th)": [money(p90[rows[a]]) for a in milestones]})
    st.dataframe(mt, hide_index=True, use_container_width=True)

# ---------------------------------------------------------------- spending
with tab3:
    ca, cb = st.columns(2)
    with ca:
        st.markdown("**Annual spending needs vs. sources**")
        ages_r = list(range(client.retire_age, client.life_expectancy))
        ss = [client.social_security if a >= client.ss_age else 0 for a in ages_r]
        wd = [max(client.retire_spending - s, 0) for s in ss]
        fig = go.Figure()
        fig.add_bar(x=ages_r, y=ss, name="Social Security", marker_color="#8c8c8c")
        fig.add_bar(x=ages_r, y=wd, name="Withdrawal from portfolio", marker_color="#1f4e79")
        fig.update_layout(barmode="stack", height=360, xaxis_title="Age", yaxis_tickprefix="$",
                          yaxis_tickformat=",.0f", margin=dict(t=10), legend=dict(orientation="h"))
        st.plotly_chart(fig, use_container_width=True)
    with cb:
        st.markdown("**When does the money run out?**")
        dep = sim["depleted_age"]
        dep = dep[~np.isnan(dep)]
        if len(dep) == 0:
            st.success("The money lasted in every simulation.")
        else:
            fig = go.Figure(go.Histogram(x=dep, xbins=dict(size=1), marker_color="#c0504d"))
            fig.update_layout(height=360, xaxis_title="Age money runs out", yaxis_title="Simulations",
                              margin=dict(t=10))
            st.plotly_chart(fig, use_container_width=True)
            st.caption(f"{len(dep) / len(sim['path'][0]):.0%} of simulations ran out of money before age {client.life_expectancy}.")
    st.markdown(f"Starting withdrawal rate: **{rec['wd_rate']:.1%}** of savings at retirement. "
                f"A rule of thumb for a long retirement is around 4%.")

# ---------------------------------------------------------------- house
with tab4:
    if not hp["active"]:
        st.info("No house goal entered. Add a down payment target and a purchase date in the sidebar.")
    else:
        hr = rec["house_rows"]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[r[0] for r in hr], y=[r[1] for r in hr], mode="lines+markers", name="Projected"))
        fig.add_hline(y=client.house_cost, line_dash="dash", annotation_text="Target")
        fig.update_layout(height=360, xaxis_title="Years from now", yaxis_tickprefix="$", yaxis_tickformat=",.0f",
                          margin=dict(t=10))
        st.plotly_chart(fig, use_container_width=True)
        affordable = client.income * client.savings_rate
        st.write(f"Required saving: **{money(hp['required'])} per year**. "
                 f"Planned total saving: {money(affordable)} per year. "
                 f"Left for retirement during these years: {money(max(affordable - hp['required'], 0))} per year.")
        if rec["house_shortfall"] > 1:
            st.warning(f"The house goal is underfunded by about {money(rec['house_shortfall'])} in total.")

with st.expander("What this robo leaves out"):
    st.markdown("""
- Taxes and account types (401k, Roth, taxable) and which account to draw from first
- Life expectancy tables, spouse and survivor planning, dependents and college savings
- Real estate, pensions, annuities, health care and long term care costs
- Emergency fund sizing, debt payoff, insurance
- Sequence of returns beyond the simple normal return model, fat tails, and changing inflation
- Rebalancing costs and fund fees
""")
