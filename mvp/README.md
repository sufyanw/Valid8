# 4sight MVP

Tests the riskiest assumption from `founder-journey.md` Stage 4: can a hypothesis
engine ground root-cause claims for AI-agent non-determinism in verifiable
evidence well enough that an experienced engineer trusts the output?

## What this is

One fixture incident (`fixtures/`): a support agent that correctly calls
`lookup_order_status` in a healthy run (`trace_a.json`), then in a later run
states intent to look it up but never calls it and gives an unverified answer
(`trace_b.json`). `deploy_diff.txt` contains the real cause (a softened system
prompt) plus one irrelevant decoy change, to test whether the engine points at
the right line.

The engine (`engine/hypothesis_engine.py`) calls `openai/gpt-oss-120b:free` via
OpenRouter for ranked hypotheses, each required to cite a verbatim excerpt from
the evidence. Citations are then checked in code against the actual source
files -- any hypothesis whose "evidence" isn't a real substring of the fixtures
is silently dropped before it ever reaches the report. That verification step
is the actual product; everything else is scaffolding around it.

Free/open-weight models are noticeably worse than frontier models at exact
verbatim citation, so if verification drops every hypothesis on the first
attempt, the engine automatically retries once, telling the model exactly
which excerpts failed (see `MAX_ATTEMPTS` in `hypothesis_engine.py`). Worst
case is 2 API calls per investigation, not 1.

## Run it

```
pip install -r requirements.txt
export OPENROUTER_API_KEY=sk-or-...   # skip this to run in stub mode
python main.py
open report/report.html
```

Get a key at https://openrouter.ai/keys (free account, no card required for
the free-tier models). Free tier is 20 requests/min, 50/day (1000/day once
you've ever purchased $10+ in credits) -- plenty for hackathon testing.

Without a key, it runs in stub mode -- the report is clearly banner-marked
as mock data. Stub mode only proves the pipeline works, not that the reasoning
is trustworthy. The real test requires a real key and, per Stage 4, a reaction
from Baraa: would he act on the top hypothesis, or still go verify it himself?
