"""
Background watcher: tails a target repo's .4sight/traces.jsonl, groups spans
by run_id, detects the tool-call/intent-mismatch anomaly, tracks the most
recent healthy run as a baseline, and auto-triggers an investigation (real
git diff as evidence) via the same engine already tested against fixtures.

Single-user, local, in-memory -- no persistence, no concurrency beyond one
watch target at a time. That's the right scope for a hackathon demo tool.
"""

import json
import os
import subprocess
import threading
import time
from datetime import datetime, timezone

from engine.hypothesis_engine import investigate_from_evidence

POLL_INTERVAL_SECONDS = 1.0
LOG_TAIL_MAX = 200


class Watcher:
    def __init__(self):
        self._lock = threading.Lock()
        self._thread = None
        self._stop_event = threading.Event()
        self._reset_state()

    def _reset_state(self):
        self.watching = False
        self.repo_path = None
        self.log_path = None
        self._file_offset = 0
        self._runs = {}  # run_id -> list of span dicts (accumulating, incomplete)
        self.known_tools = set()
        self.baseline_run = None  # {"run_id": ..., "spans": [...]}
        self.latest_investigation = None
        self.active_investigation = None
        self.log_tail = []
        self._most_recent_completed_non_baseline = None
        # Dedup: don't re-investigate the same ongoing incident on every
        # failing run. A recurrence only counts as "new" once a fresh
        # healthy baseline has been established since the last investigation
        # (i.e. it recovered, then broke again) -- not just because time passed.
        self._last_investigated_reason = None
        self._last_investigated_baseline_id = None

    # ---- public API, called from the FastAPI request handlers ----

    def start(self, repo_path):
        repo_path = os.path.abspath(repo_path)
        if not os.path.isdir(repo_path):
            raise ValueError(f"Not a directory: {repo_path}")

        self.stop()

        with self._lock:
            self._reset_state()
            self.watching = True
            self.repo_path = repo_path
            self.log_path = os.path.join(repo_path, ".4sight", "traces.jsonl")

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

        return {
            "status": "watching",
            "repo_path": self.repo_path,
            "log_path": self.log_path,
        }

    def stop(self):
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join(timeout=POLL_INTERVAL_SECONDS * 3)
        self._thread = None
        with self._lock:
            self.watching = False

        return {"status": "stopped", "repo_path": self.repo_path}

    def get_status(self):
        with self._lock:
            return {
                "watching": self.watching,
                "repo_path": self.repo_path,
                "log_tail": list(self.log_tail[-LOG_TAIL_MAX:]),
                "known_tools": sorted(self.known_tools),
                "baseline_run_id": self.baseline_run["run_id"] if self.baseline_run else None,
                "latest_investigation": self.latest_investigation,
                "active_investigation": self.active_investigation,
            }

    def force_investigate(self):
        """Manual override: investigate using whatever's currently available
        (baseline vs. most recent completed non-baseline run), independent of
        whether the anomaly rule fired. Returns None if there isn't enough
        data yet (need at least a baseline and one other completed run)."""
        with self._lock:
            baseline = self.baseline_run
            candidate = self._most_recent_completed_non_baseline

        if not baseline or not candidate:
            return None

        return self._run_investigation(baseline, candidate)

    # ---- background thread ----

    def _poll_loop(self):
        while not self._stop_event.is_set():
            try:
                self._poll_once()
            except Exception as exc:  # noqa: BLE001 -- keep the thread alive
                self._append_log_tail_error(str(exc))
            self._stop_event.wait(POLL_INTERVAL_SECONDS)

    def _poll_once(self):
        if not os.path.exists(self.log_path):
            return

        size = os.path.getsize(self.log_path)
        if size < self._file_offset:
            # File was truncated/rotated -- start over.
            self._file_offset = 0

        if size == self._file_offset:
            return

        with open(self.log_path, "r") as f:
            f.seek(self._file_offset)
            new_content = f.read()
            self._file_offset = f.tell()

        for line in new_content.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                span = json.loads(line)
            except json.JSONDecodeError:
                continue
            self._handle_span(span)

    def _handle_span(self, span):
        run_id = span.get("run_id")
        if not run_id:
            return

        with self._lock:
            self.log_tail.append(span)
            if len(self.log_tail) > LOG_TAIL_MAX:
                self.log_tail = self.log_tail[-LOG_TAIL_MAX:]

            self._runs.setdefault(run_id, []).append(span)

            if span.get("type") == "tool_call" and span.get("tool"):
                self.known_tools.add(span["tool"])

        if span.get("type") == "final_response":
            self._complete_run(run_id)

    def _complete_run(self, run_id):
        with self._lock:
            spans = self._runs.pop(run_id, [])
            known_tools = set(self.known_tools)

        if not spans:
            return

        anomalous, reason = _check_anomaly(spans, known_tools)
        run = {"run_id": run_id, "spans": spans}

        if not anomalous:
            with self._lock:
                self.baseline_run = run
                self._most_recent_completed_non_baseline = None
            return

        with self._lock:
            baseline = self.baseline_run
            self._most_recent_completed_non_baseline = run

        if baseline is None:
            return  # can't compare without a healthy reference run yet

        with self._lock:
            is_duplicate = (
                reason == self._last_investigated_reason
                and baseline["run_id"] == self._last_investigated_baseline_id
            )
            if is_duplicate:
                # Same ongoing incident (same anomaly reason, no recovery
                # since the last investigation) -- don't burn another LLM
                # call re-investigating something already explained.
                if self.latest_investigation is not None:
                    self.latest_investigation["repeat_count"] = (
                        self.latest_investigation.get("repeat_count", 1) + 1
                    )
                    self.latest_investigation["last_seen_run_id"] = run_id
                    self.latest_investigation["last_seen_at"] = datetime.now(timezone.utc).isoformat()
                return

            self.active_investigation = {
                "triggered_run_id": run_id,
                "triggered_at": datetime.now(timezone.utc).isoformat(),
                "anomaly_reason": reason,
            }
            self._last_investigated_reason = reason
            self._last_investigated_baseline_id = baseline["run_id"]

        try:
            result = self._run_investigation(baseline, run, reason=reason)
            with self._lock:
                self.latest_investigation = result
        finally:
            with self._lock:
                self.active_investigation = None

    def _run_investigation(self, baseline_run, failing_run, reason=None):
        trace_a = _serialize_run(baseline_run["run_id"], "healthy", baseline_run["spans"])
        trace_b = _serialize_run(failing_run["run_id"], "failing", failing_run["spans"])
        deploy_diff = _get_git_diff(self.repo_path)

        investigation = investigate_from_evidence(
            trace_a, trace_b, deploy_diff, repo_path=self.repo_path
        )

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
            "triggered_run_id": failing_run["run_id"],
            "triggered_at": datetime.now(timezone.utc).isoformat(),
            "anomaly_reason": reason,
            "repeat_count": 1,
        }

    def _append_log_tail_error(self, message):
        with self._lock:
            self.log_tail.append(
                {
                    "type": "watcher_error",
                    "content": message,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )


def _check_anomaly(spans, known_tools):
    """A completed run is anomalous under either rule:

    1. Tool-call/intent mismatch: a reasoning span mentions a tool that has
       previously been successfully called elsewhere (so it's real, not a
       hallucinated name), but no tool_call span for it appears in this run.
    2. Explicit error status: a response span reports an error outright
       (status == "error", or status_code >= 500) -- the simplest possible
       failure signal, no reasoning/tool-call structure required.
    """
    for span in spans:
        status_code = span.get("status_code")
        if span.get("status") == "error" or (
            isinstance(status_code, int) and status_code >= 500
        ):
            return True, f"http_error:{status_code or span.get('error_type', 'unknown')}"

    called_in_run = {s.get("tool") for s in spans if s.get("type") == "tool_call" and s.get("tool")}
    for span in spans:
        if span.get("type") != "reasoning":
            continue
        content = (span.get("content") or "").lower()
        for tool in known_tools:
            if tool.lower() in content and tool not in called_in_run:
                return True, f"tool_mismatch:{tool}"

    return False, None


def _serialize_run(run_id, label, spans):
    return json.dumps({"run_id": run_id, "label": label, "spans": spans}, indent=2)


def _get_git_diff(repo_path):
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "diff", "--no-color", "--", "."],
            capture_output=True,
            text=True,
            timeout=5,
        )
        diff = result.stdout.strip()
        if diff:
            return diff
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "log", "-1", "-p", "--no-color", "--", "."],
            capture_output=True,
            text=True,
            timeout=5,
        )
        diff = result.stdout.strip()
        if diff:
            return diff
    except Exception:
        pass

    return "(no git diff available -- repo has no matching history)"


watcher = Watcher()
