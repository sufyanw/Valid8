"""
Local API server exposing the 4sight hypothesis engine to the Next.js UI.

Run:
    uvicorn server:app --reload --port 8000

The Next.js app should NOT call this directly from the browser -- proxy it
through a Next.js Route Handler (server-side fetch) so OPENROUTER_API_KEY
never has to exist outside this Python process. See mvp/README.md.
"""

import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from engine.hypothesis_engine import investigate  # noqa: E402
from watcher import watcher  # noqa: E402

app = FastAPI(title="4sight investigation engine")

# Same-origin proxying via Next.js is the intended path; CORS is enabled
# too so localhost:3000 can call this directly during local dev if useful.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _serialize(investigation):
    return {
        "mode": investigation.mode,
        "incident_summary": investigation.incident_summary,
        "recommended_action": investigation.recommended_action,
        "dropped_hypotheses": investigation.dropped_hypotheses,
        "hypotheses": [
            {
                "rank": i,
                "claim": h.claim,
                "confidence": h.confidence,
                "evidence": [
                    {"source": e.source, "excerpt": e.excerpt} for e in h.evidence
                ],
            }
            for i, h in enumerate(investigation.hypotheses, start=1)
        ],
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/investigate")
def run_investigation():
    """Runs a fresh investigation against the fixture incident.
    Real OpenRouter call if OPENROUTER_API_KEY is set, stub otherwise."""
    investigation = investigate(FIXTURES_DIR)
    return _serialize(investigation)


class WatchRequest(BaseModel):
    repo_path: str


@app.post("/watch")
def start_watch(body: WatchRequest):
    """Start monitoring a local repo's .4sight/traces.jsonl in the
    background. Auto-triggers an investigation when the tool-call/intent
    mismatch anomaly is detected against a healthy baseline run."""
    try:
        return watcher.start(body.repo_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.delete("/watch")
def stop_watch():
    """Stop the active repository watcher, if one is running."""
    return watcher.stop()


@app.get("/status")
def get_status():
    """Poll this while watching -- log tail, known tools, and
    latest_investigation (null until an anomaly is auto-detected)."""
    return watcher.get_status()


@app.post("/investigate/now")
def force_investigate():
    """Manual override: investigate using the current baseline + most
    recent completed run, independent of anomaly detection. Falls back to
    the fixture scenario if there isn't enough live data yet (no watcher
    running, or no baseline/second run collected)."""
    result = watcher.force_investigate()
    if result is not None:
        return result

    investigation = investigate(FIXTURES_DIR)
    return _serialize(investigation)
