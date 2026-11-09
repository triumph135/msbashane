# Build Your Own Robo: write up

FINC6580 Fintech, Fall 2026

## How to run it
Double click run_app.bat, or in a terminal run:

    pip install -r requirements.txt
    python -m streamlit run app.py

Pick one of the three example clients in the sidebar, or enter your own numbers.

## What the robo does
1. Gathers: age, retirement age, plan horizon, assets, income and growth, savings rates, retirement spending, Social Security, a house goal, and a five question risk quiz.
2. Maps to a recommendation: stocks equal 120 minus age, adjusted up or down about 13 points by risk score, and cut by up to 15 points when the starting withdrawal rate is above 4%. Stocks are 70% US and 30% international. The rest is bonds with a small cash sleeve. A house goal gets its own bucket that stays in cash and short bonds.
3. Action plan tab: solves for the yearly saving needed to reach a chosen confidence level (default 85%), shows the same target reached by working longer or spending less, then lists which accounts to fund in order (employer match, HSA, Roth IRA, 401(k) to the limit, taxable) using 2026 IRS limits, and the fund types to buy with dollar amounts. Retirees get a three bucket plan (cash, bonds, stocks) and a withdrawal order instead. House money is kept outside retirement accounts in savings and Treasury bills.
4. Displays: allocation chart, glide path, savings fan chart (10th, median, 90th percentile), spending and withdrawal chart, year money runs out, house goal chart, and written advice.

Account limits used (2026): 401(k) $24,500 (+$8,000 at 50, $11,250 at 60 to 63), IRA $7,500 (+$1,100 at 50), HSA $4,400 single or $8,750 family (+$1,000 at 55), Roth IRA income phase out $153K to $168K single, $242K to $252K married filing jointly.

## Advice for the three clients
These use assumptions I chose for the example (they are editable in the app). All dollars are in today's dollars.

| Client | Key assumptions | Stocks now | Stocks at retirement | Result |
|---|---|---|---|---|
| 30 year old saver | Income $90K, $50K saved of which $30K is for a $60K house in 2 years, saves 20% falling to 15%, retire at 65 spending $65K, Social Security $30K, risk score 6.9 | 90% | 57% | Save about $14,700 per year for the house, held 70% cash and 30% short bonds. Expected balance at 65 is about $1.33M. About 80% chance money lasts to 95 (borderline). Spending near $61K, or saving about $19.6K a year toward retirement (plus the house money), gives 85%. |
| 55 year old | $200K saved, income $90K, saves 15%, retire at 67 spending $55K, Social Security $28K, risk score 6.0 | 66% | 51% | Expected balance at 67 is about $500K. Only about a 36% chance the plan works. To reach 85% it would take saving about $33.5K a year, retiring at 74, or spending about $44K a year. |
| 70 year old retiree | $2M, spends $120K, Social Security $40K, risk score 6.0 | 52% | 52% | Starting withdrawal rate is 4.0%. About a 91% chance the money lasts to 95. Keep a balanced mix with a cash reserve and rebalance yearly. |

## Features I did not have time to add
Life expectancy tables and joint (spouse) planning, dependents and college savings, tax status of accounts (401K, Roth, taxable) and withdrawal order, real estate and mortgage, pensions and annuities, health care and long term care costs, emergency fund and debt payoff, fees, rebalancing costs, fat tailed market returns and changing inflation.

## Files
- app.py: Streamlit interface
- robo_engine.py: allocation, projection and Monte Carlo logic
- AI_PROMPTS.md: prompts used
- requirements.txt, run_app.bat: setup helpers
