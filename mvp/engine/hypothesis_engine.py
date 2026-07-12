"""
4sight hypothesis engine (MVP).

Given two agent execution traces (a healthy run and a failing run) and the
deploy diff between them, produce ranked root-cause hypotheses. Every
hypothesis must cite a verbatim excerpt from the source evidence -- citations
are verified programmatically after the model responds, not just requested
in the prompt. Hypotheses that fail verification are dropped rather than
shown, so what reaches the report is grounded by construction.
"""

import json
import os
import re
from dataclasses import dataclass, field

SYSTEM_PROMPT = """You are 4sight's investigation engine. You are given:
- trace_a: a healthy execution of an AI agent
- trace_b: a failing execution of the same agent, on a similar request
- deploy_diff: the changes deployed between when trace_a and trace_b ran

Your job is to explain why trace_b diverged from trace_a's behavior.

Produce 2-4 ranked hypotheses. For each hypothesis:
- "claim": one sentence stating the proposed root cause.
- "evidence": a list of 1-3 items. Each item MUST be a VERBATIM substring
  copied exactly (character for character) from trace_a, trace_b, or
  deploy_diff -- not a paraphrase or summary. Each item has "source"
  (one of "trace_a", "trace_b", "deploy_diff") and "excerpt" (the verbatim
  text).
- "confidence": integer 0-100.

If you cannot support a hypothesis with a verbatim excerpt, do not include
it. Do not include hypotheses you cannot ground in the provided evidence.

Also provide one "recommended_action": a single concrete next step an
engineer should take to confirm or fix the issue.

Respond with ONLY valid JSON, no prose, matching this shape:
{
  "incident_summary": "...",
  "hypotheses": [
    {"claim": "...", "confidence": 0-100,
     "evidence": [{"source": "trace_a|trace_b|deploy_diff", "excerpt": "..."}]}
  ],
  "recommended_action": "..."
}
"""

SYSTEM_PROMPT_WITH_TOOLS = SYSTEM_PROMPT + """
You also have git_log and git_show tools for the repo this incident came
from. deploy_diff only shows one commit or the current uncommitted change --
if it doesn't fully explain trace_b's failure, call git_log to see recent
history and git_show to inspect any commit that looks relevant before
answering. Don't call tools if deploy_diff already explains the failure.

When your evidence comes from a tool result rather than trace_a/trace_b/
deploy_diff, each tool response tells you the exact "source" string to use
for that evidence item -- copy it exactly.

Once you have enough evidence, respond with ONLY the final JSON object (no
further tool calls, no prose) in the shape described above.
"""


@dataclass
class Evidence:
    source: str
    excerpt: str


@dataclass
class Hypothesis:
    claim: str
    confidence: int
    evidence: list = field(default_factory=list)


@dataclass
class Investigation:
    incident_summary: str
    hypotheses: list
    recommended_action: str
    mode: str  # "live" or "stub"
    dropped_hypotheses: int = 0


OPENROUTER_MODEL = "openai/gpt-oss-120b:free"

RETRY_INSTRUCTION_TEMPLATE = """Your previous response had hypotheses where NONE of the
evidence excerpts were verbatim substrings of the source documents (trace_a, trace_b,
deploy_diff) -- every excerpt must match the source text character-for-character, not
paraphrased. Re-read the sources carefully and produce a new response where every
evidence excerpt is copied exactly from the source. Previous attempt's excerpts that
failed verification:
{failed_excerpts}
"""


def _load_fixtures(fixtures_dir):
    with open(os.path.join(fixtures_dir, "trace_a.json")) as f:
        trace_a = f.read()
    with open(os.path.join(fixtures_dir, "trace_b.json")) as f:
        trace_b = f.read()
    with open(os.path.join(fixtures_dir, "deploy_diff.txt")) as f:
        deploy_diff = f.read()
    return trace_a, trace_b, deploy_diff


def _parse_json_response(text):
    """Extract a JSON object from a model response, tolerating markdown code
    fences and stray prose around the JSON -- free/open-weight models are
    less reliable than frontier models about emitting bare JSON."""
    text = text.strip()

    fence_match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


MAX_TOOL_ROUNDS = 3


def _call_llm(trace_a, trace_b, deploy_diff, retry_note=None, repo_path=None):
    from openai import OpenAI

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ.get("OPENROUTER_API_KEY"),
    )
    user_content = (
        f"trace_a:\n{trace_a}\n\ntrace_b:\n{trace_b}\n\n"
        f"deploy_diff:\n{deploy_diff}"
    )
    if retry_note:
        user_content += f"\n\n{retry_note}"

    system_prompt = SYSTEM_PROMPT_WITH_TOOLS if repo_path else SYSTEM_PROMPT
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    if not repo_path:
        try:
            response = client.chat.completions.create(
                model=OPENROUTER_MODEL,
                max_tokens=4000,
                messages=messages,
                response_format={"type": "json_object"},
            )
        except Exception:
            # Some providers reject response_format for this model -- retry
            # without it rather than failing the whole investigation.
            response = client.chat.completions.create(
                model=OPENROUTER_MODEL,
                max_tokens=4000,
                messages=messages,
            )
        return _parse_json_response(response.choices[0].message.content), {}

    from engine.git_tools import TOOL_SCHEMAS, call_tool

    extra_sources = {}
    message = None

    for round_num in range(MAX_TOOL_ROUNDS + 1):
        response = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            max_tokens=4000,
            messages=messages,
            tools=TOOL_SCHEMAS,
        )
        message = response.choices[0].message
        tool_calls = getattr(message, "tool_calls", None)

        if not tool_calls or round_num == MAX_TOOL_ROUNDS:
            break

        messages.append(
            {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in tool_calls
                ],
            }
        )
        for tc in tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            result_text = call_tool(repo_path, tc.function.name, args)
            source_key = f"{tc.function.name}:{args.get('commit_hash') or round_num}"
            extra_sources[source_key] = result_text
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": f'(cite this as source="{source_key}")\n{result_text}',
                }
            )

    if not message.content:
        raise ValueError("Model ended without a final JSON answer (empty content).")
    return _parse_json_response(message.content), extra_sources


def _stub_response():
    """Structurally valid mock, used only when no API key is configured.
    NOT a demonstration of real reasoning quality -- see report banner."""
    return {
        "incident_summary": "[STUB] Placeholder response -- set OPENROUTER_API_KEY "
        "to run the real hypothesis engine.",
        "hypotheses": [
            {
                "claim": "[STUB] This is a mocked hypothesis for pipeline testing only.",
                "confidence": 0,
                "evidence": [
                    {"source": "trace_b", "excerpt": "likely still processing"}
                ],
            }
        ],
        "recommended_action": "[STUB] Configure OPENROUTER_API_KEY and re-run to get a "
        "real, evidence-verified investigation.",
    }


def _verify_and_build(raw, sources):
    """sources: dict of source_key -> full text that key is allowed to cite
    from. An evidence item is valid if its excerpt is a verbatim substring
    of the source text it claims -- or, failing that, of ANY known source,
    in which case it's relabeled to the source it actually came from rather
    than rejected outright (the model can mislabel which tool result an
    excerpt came from without the claim itself being ungrounded)."""
    hypotheses = []
    dropped = 0

    for h in raw.get("hypotheses", []):
        valid_evidence = []
        for e in h.get("evidence", []):
            source = e.get("source")
            excerpt = e.get("excerpt", "")
            if not excerpt:
                continue
            if source in sources and excerpt in sources[source]:
                valid_evidence.append(Evidence(source=source, excerpt=excerpt))
                continue
            for true_source, doc in sources.items():
                if excerpt in doc:
                    valid_evidence.append(Evidence(source=true_source, excerpt=excerpt))
                    break
        if valid_evidence:
            hypotheses.append(
                Hypothesis(
                    claim=h.get("claim", ""),
                    confidence=int(h.get("confidence", 0)),
                    evidence=valid_evidence,
                )
            )
        else:
            dropped += 1

    hypotheses.sort(key=lambda h: h.confidence, reverse=True)
    return hypotheses, dropped


MAX_ATTEMPTS = 2


def investigate(fixtures_dir):
    """Fixture-backed entry point (used by main.py / the static report).
    No repo_path -- git tools stay disabled, identical to pre-tool-calling
    behavior."""
    trace_a, trace_b, deploy_diff = _load_fixtures(fixtures_dir)
    return investigate_from_evidence(trace_a, trace_b, deploy_diff)


def investigate_from_evidence(trace_a, trace_b, deploy_diff, repo_path=None):
    """Core entry point: evidence text in, Investigation out. Used by both
    the fixture-backed investigate() and the live watcher, so the live
    monitoring path exercises exactly the same LLM call, retry, and
    citation-verification logic that was already tested against fixtures.

    If repo_path is given, the model additionally gets git_log/git_show
    tools scoped to that repo, so it can look past the single pre-fetched
    deploy_diff when that alone doesn't explain the failure."""

    base_sources = {"trace_a": trace_a, "trace_b": trace_b, "deploy_diff": deploy_diff}

    if not os.environ.get("OPENROUTER_API_KEY"):
        raw = _stub_response()
        hypotheses, dropped = _verify_and_build(raw, base_sources)
        return Investigation(
            incident_summary=raw.get("incident_summary", ""),
            hypotheses=hypotheses,
            recommended_action=raw.get("recommended_action", ""),
            mode="stub",
            dropped_hypotheses=dropped,
        )

    retry_note = None
    raw = {}
    hypotheses = []
    dropped = 0

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            raw, extra_sources = _call_llm(
                trace_a, trace_b, deploy_diff, retry_note=retry_note, repo_path=repo_path
            )
        except (json.JSONDecodeError, Exception) as exc:
            # Malformed response (bad JSON, API hiccup, etc). Treat as a
            # failed attempt and retry once rather than crashing outright.
            raw, extra_sources = {}, {}
            hypotheses, dropped = [], 0
            if attempt == MAX_ATTEMPTS:
                raise RuntimeError(
                    f"Hypothesis engine failed after {MAX_ATTEMPTS} attempts: {exc}"
                ) from exc
            retry_note = RETRY_INSTRUCTION_TEMPLATE.format(
                failed_excerpts=f"(previous attempt did not return valid JSON: {exc})"
            )
            continue

        sources = {**base_sources, **extra_sources}
        hypotheses, dropped = _verify_and_build(raw, sources)

        if hypotheses or attempt == MAX_ATTEMPTS:
            break

        # Nothing survived verification -- give the model one corrective pass
        # with the specific excerpts that failed, instead of returning empty.
        failed_excerpts = "\n".join(
            f"- ({e.get('source')}): {e.get('excerpt')!r}"
            for h in raw.get("hypotheses", [])
            for e in h.get("evidence", [])
        )
        retry_note = RETRY_INSTRUCTION_TEMPLATE.format(
            failed_excerpts=failed_excerpts or "(no evidence was provided at all)"
        )

    return Investigation(
        incident_summary=raw.get("incident_summary", ""),
        hypotheses=hypotheses,
        recommended_action=raw.get("recommended_action", ""),
        mode="live",
        dropped_hypotheses=dropped,
    )
