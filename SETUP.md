# Running 4sight locally

Three things run at once, each in its own terminal, in this order:

1. `mockAgent/` — the demo target app being monitored (port 8001)
2. `mvp/` — the 4sight investigation backend (port 8000)
3. `4sight/` — the Next.js UI (port 3000)

---

## 1. mockAgent (demo target app)

```bash
cd mockAgent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ALLOW_FAKE_LLM=true    # skip needing a real Gemini key
export OTEL_ENABLED=false
python3 -m uvicorn app.main:app --port 8001
```

Leave this running. Verify: `curl -s http://localhost:8001/api/health` → `{"ok":true,...}`.

**If your Python is older than 3.10** (`python3 --version`), you'll also need:
```bash
pip install eval_type_backport
```
before starting uvicorn — the app uses `X | None` type syntax that needs either Python 3.10+ or that shim. Not needed on 3.10+.

Each new terminal tab needs `source .venv/bin/activate` run again — it's per-shell, not permanent.

---

## 2. mvp (4sight backend)

```bash
cd mvp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional but recommended — real investigations instead of stub mode:
```bash
echo "OPENROUTER_API_KEY=sk-or-v1-..." > .env
```
Get a free key at https://openrouter.ai/keys (no card needed for `:free` models). Without this, the engine still runs end-to-end but returns clearly-labeled placeholder data instead of a real analysis.

```bash
python3 -m uvicorn server:app --reload --port 8000
```

Verify: `curl -s http://localhost:8000/health` → `{"status":"ok"}`.

---

## 3. 4sight UI (Next.js)

```bash
cd 4sight
npm install    # only needed once, already done if node_modules exists
npm run dev
```

Open http://localhost:3000. It proxies to `mvp`'s server at `localhost:8000` by default (override with `PYTHON_API_URL` env var if needed) — the browser never talks to the Python backend directly.

---

## One-time git setup (needed once, before testing failures)

The `force_failure` demo flag only produces a real, citable diff for 4sight if it's already tracked in git — otherwise the first flip is invisible to `git diff`. Commit the tracking scaffolding once:

```bash
git add mockAgent/app/tracing.py mockAgent/config/feature_flags.json \
        mockAgent/app/main.py mockAgent/app/recommendation.py mockAgent/.gitignore
git commit -m "Add 4sight trace logging and force_failure test flag"
```

---

## Testing the full flow from the UI

1. In the UI, enter the repo path to watch: `/Users/heyeso/workspace/Valid8/mockAgent` (absolute path, no trailing slash).
2. Trigger a healthy request so a baseline exists — either through the UI if it has a way to hit mockAgent, or directly:
   ```bash
   curl -s -X POST http://localhost:8001/api/recommend -H "Content-Type: application/json" -d '{
     "quick_tags": ["mobility"], "transport_modes": ["rail"],
     "duration_days": 3, "trip_duration": "3 days",
     "needs_description": "wheelchair", "plain_language": true
   }'
   ```
3. Trigger the regression:
   ```bash
   curl -s -X PUT http://localhost:8001/api/feature-flags -H "Content-Type: application/json" -d '{"force_failure": true}'
   curl -s -X POST http://localhost:8001/api/recommend -H "Content-Type: application/json" -d '{
     "quick_tags": ["mobility"], "transport_modes": ["rail"],
     "duration_days": 3, "trip_duration": "3 days",
     "needs_description": "wheelchair", "plain_language": true
   }'
   ```
4. Watch the UI (it polls `/status`) — an investigation should appear automatically, citing the real committed diff.
5. Apply "the fix":
   ```bash
   curl -s -X PUT http://localhost:8001/api/feature-flags -H "Content-Type: application/json" -d '{"force_failure": false}'
   ```
   One more successful request re-establishes a healthy baseline, so a future regression triggers a fresh investigation instead of being deduped as a repeat.

---

## Resetting to a clean slate

```bash
rm -f mockAgent/.4sight/traces.jsonl
curl -s -X POST http://localhost:8000/watch -H "Content-Type: application/json" -d '{"repo_path": "/Users/heyeso/workspace/Valid8/mockAgent"}'
```
Deleting the log file alone isn't enough — the 4sight server's in-memory state (baseline, known tools, last investigation) survives independently of the file. Re-`/watch`ing resets both together.

---

## Known rough edges

- The free OpenRouter model (`openai/gpt-oss-120b:free`) has inconsistent latency — one investigation took 15 seconds, another over 2 minutes. Don't assume a fast response.
- Free tier is 20 requests/min, 50/day (1000/day after ever buying $10+ in credits) — repeated failures without the dedup logic could burn through this fast; the watcher now suppresses re-investigating the same ongoing incident (see `watcher.py`'s `_last_investigated_reason`/`_last_investigated_baseline_id`).
- Nothing is persisted except `mockAgent/.4sight/traces.jsonl` itself. Investigation results and job results live in memory only — restarting either server loses them (see prior discussion in `founder-journey.md` if tracking this down later).
