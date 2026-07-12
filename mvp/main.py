"""
4sight MVP runner.

Usage:
    python main.py

Runs the hypothesis engine against the fixture incident (fixtures/) and
writes report/report.html. Uses a real OpenRouter call if OPENROUTER_API_KEY
is set (env var or .env file in this directory), otherwise falls back to a
clearly-labeled stub.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from engine.hypothesis_engine import investigate
from report.render import render


def main():
    base_dir = os.path.dirname(__file__)
    fixtures_dir = os.path.join(base_dir, "fixtures")
    out_path = os.path.join(base_dir, "report", "report.html")

    investigation = investigate(fixtures_dir)
    render(investigation, out_path)

    print(f"Mode: {investigation.mode}")
    print(f"Hypotheses shown: {len(investigation.hypotheses)}")
    print(f"Hypotheses discarded (no verifiable evidence): {investigation.dropped_hypotheses}")
    print(f"Report written to: {out_path}")


if __name__ == "__main__":
    main()
