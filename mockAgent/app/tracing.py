"""Minimal trace logging for 4sight.

Appends one JSON line per lifecycle checkpoint of a recommendation request
to .4sight/traces.jsonl in the repo root, so an external watcher can tail
it and reconstruct the whole run, not just its outcome. Intentionally
decoupled from the app's own OpenTelemetry/stdout logging in
observability.py -- this is a separate, simple sink purpose-built for local
4sight monitoring, not a replacement for the app's real observability setup.

The watcher treats a run as complete once it sees a "final_response" span
for that run_id, so every run must end with exactly one of those -- earlier
checkpoints (request_received, processing_started, ...) can use any other
type and are just accumulated as context.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

_TRACE_DIR = Path(__file__).resolve().parents[1] / ".4sight"
_TRACE_FILE = _TRACE_DIR / "traces.jsonl"


def write_span(
    run_id: str,
    span_type: str,
    *,
    content: str,
    status: str | None = None,
    status_code: int | None = None,
    error_type: str | None = None,
) -> None:
    _TRACE_DIR.mkdir(exist_ok=True)
    span = {
        "run_id": run_id,
        "type": span_type,
        "content": content,
        "status": status,
        "status_code": status_code,
        "error_type": error_type,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with open(_TRACE_FILE, "a") as f:
        f.write(json.dumps(span) + "\n")
