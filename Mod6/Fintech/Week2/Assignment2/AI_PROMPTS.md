# AI prompts used to build the robo

AI tool: Claude (Claude Code).

## Prompt 1 (request)
"I need to do this assignment for my Fintech course. The assignment document is in the Fintech/Week2 folder. Create a new folder for any files you create, called Assignment2, within the Week2 folder. I would also like to make it into a streamlit app at the end of doing this."

The assignment document (Build your own robo) asks for a robo advisor that gathers the client's financial condition, maps it to investment recommendations, displays projections, and answers what advice it would give a 30 year old saver, a 55 year old with $200K, and a 70 year old with $2 million.

## Design decisions made while building
1. Keep it simple: one engine file (robo_engine.py) with the logic and one Streamlit file (app.py) for the interface.
2. Work in today's dollars so projections are easy to read.
3. Allocation rule: stocks = (120 minus age) plus or minus a risk adjustment from a five question quiz, trimmed when the planned withdrawal rate is high.
4. Dated goals (a house) are funded in a separate safe bucket, because money needed in 2 years should not be in stocks.
5. Monte Carlo (2,000 runs) for the chance the money lasts, plus a simple expected path.
6. Sustainable spending is the highest spending level that still gives an 85% chance of success.
