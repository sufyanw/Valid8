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
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from engine.hypothesis_engine import investigate  # noqa: E402

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
