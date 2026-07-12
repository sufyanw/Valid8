"""Render an Investigation into a single static HTML report."""

import html

TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>4sight -- Investigation Report</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    max-width: 760px; margin: 40px auto; padding: 0 20px;
    line-height: 1.55; color: #1a1a1a; background: #fff;
  }}
  @media (prefers-color-scheme: dark) {{
    body {{ color: #e8e8e8; background: #121212; }}
    .card {{ background: #1c1c1c !important; border-color: #333 !important; }}
    .evidence {{ background: #26240f !important; border-left-color: #b89b00 !important; }}
    .meta {{ color: #999 !important; }}
  }}
  h1 {{ font-size: 1.5rem; margin-bottom: 4px; }}
  .subtitle {{ color: #666; margin-top: 0; }}
  .banner {{
    background: #b91c1c; color: white; padding: 10px 14px; border-radius: 6px;
    font-weight: 600; margin-bottom: 20px; font-size: 0.9rem;
  }}
  .summary {{
    background: #f4f4f4; border-radius: 8px; padding: 14px 18px; margin-bottom: 24px;
  }}
  @media (prefers-color-scheme: dark) {{ .summary {{ background: #1c1c1c; }} }}
  .card {{
    border: 1px solid #ddd; border-radius: 10px; padding: 16px 20px;
    margin-bottom: 16px; background: #fafafa;
  }}
  .rank {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: #888; }}
  .claim {{ font-size: 1.05rem; font-weight: 600; margin: 4px 0 10px; }}
  .confidence {{ font-size: 0.85rem; color: #444; margin-bottom: 10px; }}
  @media (prefers-color-scheme: dark) {{ .confidence {{ color: #bbb; }} }}
  .evidence {{
    background: #fff8e1; border-left: 3px solid #d4a300; padding: 8px 12px;
    margin: 6px 0; font-family: ui-monospace, monospace; font-size: 0.85rem;
    white-space: pre-wrap; word-break: break-word;
  }}
  .evidence .src {{ font-family: -apple-system, sans-serif; font-size: 0.75rem;
    color: #8a6d00; font-weight: 600; display: block; margin-bottom: 4px; }}
  .action {{
    border-radius: 8px; padding: 14px 18px; background: #e6f4ea;
    border: 1px solid #b7dfc2; margin-top: 24px;
  }}
  @media (prefers-color-scheme: dark) {{
    .action {{ background: #142a1c; border-color: #2d5a3d; }}
  }}
  .meta {{ font-size: 0.8rem; color: #888; margin-top: 30px; }}
</style>
</head>
<body>
<h1>4sight -- Investigation Report</h1>
<p class="subtitle">Grounded root-cause hypotheses for one incident.</p>

{banner}

<div class="summary"><strong>Incident summary:</strong><br>{summary}</div>

<h2>Ranked hypotheses</h2>
{hypotheses}

<div class="action">
  <strong>Recommended next action:</strong><br>{action}
</div>

<p class="meta">
  Mode: {mode} &middot; Hypotheses shown: {shown} &middot;
  Hypotheses discarded for lacking verifiable evidence: {dropped}
</p>
</body>
</html>
"""

HYPOTHESIS_TEMPLATE = """
<div class="card">
  <div class="rank">Hypothesis {rank}</div>
  <div class="claim">{claim}</div>
  <div class="confidence">Confidence: {confidence}%</div>
  {evidence}
</div>
"""

EVIDENCE_TEMPLATE = """<div class="evidence"><span class="src">{source}</span>{excerpt}</div>"""


def render(investigation, out_path):
    banner = ""
    if investigation.mode == "stub":
        banner = (
            '<div class="banner">STUB MODE -- mock data, not a real model '
            "inference. This does not demonstrate reasoning quality. Set "
            "ANTHROPIC_API_KEY and re-run for a real investigation.</div>"
        )

    hyp_html = []
    for i, h in enumerate(investigation.hypotheses, start=1):
        evidence_html = "".join(
            EVIDENCE_TEMPLATE.format(
                source=html.escape(e.source), excerpt=html.escape(e.excerpt)
            )
            for e in h.evidence
        )
        hyp_html.append(
            HYPOTHESIS_TEMPLATE.format(
                rank=i,
                claim=html.escape(h.claim),
                confidence=h.confidence,
                evidence=evidence_html,
            )
        )

    if not hyp_html:
        hyp_html.append(
            '<p><em>No hypotheses survived evidence verification.</em></p>'
        )

    page = TEMPLATE.format(
        banner=banner,
        summary=html.escape(investigation.incident_summary),
        hypotheses="".join(hyp_html),
        action=html.escape(investigation.recommended_action),
        mode=investigation.mode,
        shown=len(investigation.hypotheses),
        dropped=investigation.dropped_hypotheses,
    )

    with open(out_path, "w") as f:
        f.write(page)
