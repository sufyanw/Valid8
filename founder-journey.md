# Founder Journey — 4sight

_Running log of decisions made while validating this idea at Boundless Founder hackathon._

## The Idea (as of interview)

**4sight** — an investigation and decision-support layer for production systems, focused on AI-agent-driven infrastructure.

- **What exists today:** Observability tools (Datadog, etc.) collect and correlate telemetry well.
- **What's missing:** Reasoning about *why* an incident happened, testing competing hypotheses, and recommending the most effective fix — especially for non-deterministic AI agent systems (traces that don't match stated intent, costly/huge traces, failures spanning agent + infra).
- **Workflow:** Triage → Investigate → Validate (test remediation safely before prod).
- **Constraint:** Must integrate with existing stacks, not replace them or require centralizing all data with one vendor.

## Founder-Market Fit

Founder has personally lived this problem as an on-call engineer:
- Page fires ~minutes after customer impact starts.
- ~10 min to get laptop/tooling set up.
- ~10 min getting AI debugging agent pointed in the right direction.
- ~1 hr of AI-assisted RCA that may be hallucinated (agent can be confidently wrong about root cause).
- 1-2 hrs of manual debugging to actually confirm root cause.
- Then: test fix, peer review, deploy — adds more time.
- **Net result:** 30 min best case to multiple days worst case, for issues that "could be minutes."

## Personas (from prior discovery — 4 conversations + synthesis notes, provisional/small sample)

1. **Marcus — Production AI Platform Engineer.** Already running agents in prod, builds internal tooling because standard telemetry doesn't explain non-determinism. Wants trustworthy trace reconstruction without specialist dependency.
2. **Daniel — Engineer Preparing Agents for Production.** Pre-launch, setting up OTel + reflection agent. Logs don't explain intent/action mismatches (agent says it'll call a tool, doesn't). Wants fast setup + real explanations.
3. **Ravi — AI Reliability Engineer.** Runs ~5hr, expensive eval suites before releases because post-deploy failures are hard to diagnose. Wants faster validation + earlier regression detection.
4. **Omar — Eng Leader, AI Infra.** Owns cost/scale across teams. Sees telemetry volume/cost exploding without proportional insight gain. Wants scalable, self-hostable, multi-vendor-friendly insight.

## Stage Log

### Stage 1 — Problem Check (in progress)

**Restated problem:** On-call engineers running AI agents in prod need to know what actually happened and why during an incident, fast — instead of hand-correlating evidence under page pressure or trusting a possibly-hallucinated AI RCA.

**Pressure test finding:** Of the 4 personas, only Marcus (Persona 1) is squarely "on-call for AI agents in prod, feeling MTTR pain today." Daniel = pre-launch confidence (different urgency). Ravi = pre-deploy eval cost (arguably a different JTBD, not post-deploy investigation). Omar = budget holder, not a user. Real market right now is narrower than "4 personas" — closer to one persona (Marcus-type) plus two adjacent-but-distinct jobs.

**Riskiest assumptions identified:**
1. Demand/frequency — partially de-risked by 4 discovery conversations.
2. **Feasibility/trust (highest risk)** — can 4sight produce hypotheses more trustworthy than the hallucinated AI RCA that's already part of today's pain? Only works if grounded in cited evidence, not LLM narrative.
3. Willingness to pay / data access — new tool needs deep read access to prod data; Omar already named vendor-lock-in fatigue.

**Cheapest test proposed:** Build a small working prototype against ONE real/realistic incident scenario (trace + logs + deploy diff) → generate 2-3 evidence-cited competing hypotheses + ranked recommendation → show to a Marcus-type engineer → ask "would you trust this enough to act on during a live page, or would you still go verify manually?"

**Recommendation:** Refine, then go. Narrow target to Marcus-type persona only for now; narrow build to one scenario + evidence-grounded hypothesis output (not the full 3-stage platform).

**Founder confirmation:** Marcus (production AI platform engineer, on-call, non-deterministic agent debugging) is the core wedge. Daniel, Ravi, and Omar represent secondary usages / future features that build on the same MTTR-reduction thesis, not separate initial targets. Starting small and deliberately in Marcus's problem space.

**Stage 1 status: CLOSED.** Problem confirmed real, lived, and scoped to Marcus.

---

### Stage 2 — Customer Definition

**First customer (validation partner): Baraa** — Senior engineer at Microsoft, personal friend of founder.
- Built proprietary monitoring/debugging system from scratch for AI agents because standard telemetry wasn't enough.
- Had to manually recreate entire non-deterministic execution flow to debug an issue; recreation was not a faithful (≥95%) match to the original.
- Required data scientist expertise / hands-on model experience to interpret — exactly the "specialist dependency" pain the founder is targeting.
- **Explicitly recommended building 4sight to solve: (1) better UI/UX for monitoring AI agents, (2) easier debugging of non-deterministic traces.**

**Caveat noted:** Baraa is an excellent design/validation partner (reachable, lived the exact pain, already prescribed the solution direction) but not a realistic near-term paying customer — Microsoft-scale procurement/security review + existing sunk-cost internal tooling make enterprise sales unrealistic at hackathon stage. Role for now: reactor/validator on the prototype, not revenue.

**Other discovery contacts (secondary/future, per Stage 1 decision):**
- Talal Ghafoor (SDE, Amazon) — pre-prod, OpenTelemetry + reflection-agent setup, wants insight into intent/action mismatches (tool-call-not-made cases).
- Sakib (SDE, Workday) — 5hr expensive pre-deploy eval process; syncing again in ~2 weeks once he's on-call for more insight.
- Faryab — contact only, no substantive notes yet (incomplete conversation).
- Ali (SDM3, Amazon) — logging volume/cost concerns at scale; interested in semantic layers (e.g. AgentSight) connecting app-level and system-level behavior for model efficiency gains.

**Stage 2 status: CLOSED.** First customer = Baraa.

---

### Stage 3 — Existing Alternatives & Competition

**Tier 1 — Agent-native tracing/observability:** Braintrust, LangSmith, AgentOps, Langfuse, Arize Phoenix, MLflow. Strong at evidence collection/presentation for AI agents specifically. Braintrust markets "root cause diagnosis" but it's trace capture + human-applied root-cause labels + clustering — not autonomous hypothesis generation/testing.

**Tier 2 — AIOps/RCA copilots for production infra (real threat):** NeuBird (Agent Context Engine — parallel hypothesis exploration, evidence-cited causal chains, confidence scoring, human-in-the-loop; $19.3M raised, expanding fast as of Apr 2026), Logz.io OrionIQ, Datadog Bits AI. Strong at autonomous causal reasoning, but built on service-map/dependency-graph models for traditional infra/microservices — not for LLM-agent-specific non-determinism.

**Tier 3 — Incident workflow platforms:** Rootly, incident.io, FireHydrant. Own human coordination (paging/comms/retros) with AI bolted on; not deep diagnosis.

**The wedge:** Hypothesis-driven reasoning (Tier 2's strength) applied specifically to AI-agent non-determinism — tool-call/intent mismatches, non-reproducible execution, hallucinated reasoning steps, low-fidelity trace replay (Tier 1's domain, but Tier 1 doesn't reason over it). Nobody occupies this intersection yet. Baraa (sophisticated Microsoft engineer) evaluated/didn't adopt existing tools and built proprietary tooling instead — direct evidence of the gap.

**Risk flagged:** Defensibility is not "first to AI-powered RCA" — that's contested from both directions (NeuBird could extend to agent traces; Braintrust/Arize could bolt reasoning onto data they already collect). Defensibility must come from depth on agent-specific non-determinism + speed of execution.

**Stage 3 status: CLOSED.**

---

### Stage 4 — Riskiest Assumption

**Refined riskiest assumption:** Can 4sight ground a root-cause hypothesis for AI-agent non-determinism in cited, verifiable evidence (trace spans, tool-call diffs, deploy/code changes) well enough that an experienced engineer (Baraa-type) trusts the top hypothesis enough to act on it — without redoing the manual reconstruction himself? (NeuBird already proves the category — evidence-grounded AI causal reasoning engineers trust — works for structured infra dependency graphs. Unproven: whether it works for stochastic/semantic agent decision traces specifically.)

**If wrong:** 4sight is just another plausible-sounding AI narrator — the exact failure mode (hallucinated AI RCA) it's meant to replace. Everything else (integrations, pricing, personas) is moot until this is true.

**Test design (this week, hackathon-scoped):**
- **Type:** Working concierge prototype + reaction interview (stronger than landing page; feasible in hackathon time).
- **Scenario:** One agent that behaves differently across two similar requests (calls a tool in one run, not in a near-identical run) — mirrors both Baraa's and Talal's pain.
- **Input:** two run traces (synthetic/logged), tool-call log, code/prompt diff between runs.
- **Output:** 2-3 ranked competing hypotheses, each citing the specific trace span/diff line supporting it, + one recommended next action.
- **Validation:** 30-min session with Baraa. Ask: "Would this have saved you the manual reconstruction? Would you act on the top hypothesis, or still verify it yourself first?"
- **Success signal:** he'd act on it or only spot-check. **Failure signal:** "I'd still have to go check" — means hypotheses aren't grounded enough yet.

**Stage 4 status: CLOSED.**

---

### Stage 5 — Scope the MVP

**Ships today:**
1. **Handcrafted incident fixture** — two traces of "the same" agent request (run A: calls tool as stated; run B: says it will, doesn't), plus a plausible cause baked in (system-prompt/tool-description diff between runs = the "deploy diff"). Handwritten so ground truth is known, to verify the engine reasons correctly, not just plausibly.
2. **Hypothesis engine** (the actual product) — input: trace A, trace B, diff. Output: 2-3 ranked hypotheses, each REQUIRED to cite a specific line/span as evidence (no citation = discarded), + one recommended action. The evidence-or-discard constraint is what differentiates this from a normal LLM RCA guess.
3. **Minimal report view** — single static HTML page: incident summary → ranked hypotheses w/ highlighted evidence → recommendation. Answers Baraa's ask #1 (better UI/UX) without building a full app.
4. **Baraa validation call** — walk through report, ask Stage 4 trust question.

**Explicitly cut:**
- Real integrations (OTel collector, Datadog, GitHub) — fixture data only for now.
- Multi-user, auth, persistence/database.
- Original Stage 3 of product vision ("validate response in safe environment") — separate future product surface.
- Multi-framework/multi-provider agent support.
- Daniel/Ravi/Omar use cases — future expansion, not today.

**Stage 5 status: CLOSED.**

---

### Stage 6 — Build Plan

**Built (in `mvp/`), this session:**
- `fixtures/` — handcrafted incident: `trace_a.json` (healthy run, agent calls `lookup_order_status` as stated), `trace_b.json` (failing run, agent states intent to look up status but never calls the tool, gives an unverified answer instead), `deploy_diff.txt` (real cause: system prompt softened from "You MUST call lookup_order_status..." to "You can look up order status if needed..."; plus one irrelevant decoy change to a log level, to test whether the engine points at the right line).
- `engine/hypothesis_engine.py` — calls Claude for ranked hypotheses; every hypothesis must cite a source + verbatim excerpt. Citations are re-verified in Python against the actual fixture text after the model responds — any hypothesis whose evidence isn't a real substring of the source is silently dropped. This mechanical check (not just a prompt instruction) is the core trust mechanism from Stage 4. Falls back to a clearly-banner-marked stub when no `ANTHROPIC_API_KEY` is set.
- `report/render.py` — renders the surviving hypotheses into a single static HTML report (summary, ranked hypotheses with highlighted evidence, recommended action, stub-mode warning banner).
- `main.py` — end-to-end runner: fixtures → engine → verification → report.html.
- Verified: (1) pipeline runs end-to-end in stub mode, (2) evidence-verification logic correctly keeps a hypothesis with a real verbatim citation and drops one with a fabricated citation — tested directly against `_verify_and_build`.

**Repo:** built inside existing repo at https://github.com/sufyanw/Valid8 (`mvp/` folder), not a fresh repo — README.md there already contained a full prior product plan (personas, phased roadmap, capability areas) that aligns closely with this session's independently-derived Stage 1-5 conclusions.

**Not done yet (needs a real ANTHROPIC_API_KEY, not code):**
- Running the engine for real (currently only proven in stub mode — stub proves the pipeline works, not that the reasoning is trustworthy).
- The actual Stage 4 validation call with Baraa.

**Stage 6 status: MVP built, pending real API key + Baraa call to close the loop on the riskiest assumption.**

**Post-Stage-6 technical update:** engine switched from Anthropic to OpenRouter (`openai/gpt-oss-120b:free`) with a bounded retry (max 2 attempts) covering both empty-verification and malformed-JSON failures. A real (non-stub) live run succeeded end-to-end: top hypothesis correctly identified the softened system prompt as root cause (90% confidence, correct verbatim citations), second hypothesis was a plausible-but-wrong decoy correctly ranked lower (70%) — first real evidence toward Stage 4's assumption, though only one run so far, and free-tier latency is inconsistent (one call exceeded 2 minutes). Engine refactored (`investigate_from_evidence`) to accept live evidence text, not just fixtures, in preparation for the live-monitoring architecture below. Full details in `mvp/README.md`.

---

### Vision vs. Wedge, and the Moat Question

**The question raised:** should 4sight drop the AI-agent constraint and pivot to a general "proactive intelligence layer for production issues" — not limited to agents?

**Answer: no, not as a scope change to what ships now.** Reasoning: Stage 3 already found that "general production issue investigation" is occupied by funded, working competitors reasoning over infra dependency graphs (NeuBird — $19.3M raised, evidence-cited causal reasoning with confidence scoring; Datadog Bits AI; Logz.io OrionIQ). 4sight's entire wedge is the gap between that tier and the agent-tracing tier (Braintrust, LangSmith — collects evidence, doesn't reason over it). Dropping the agent constraint erases that gap and puts 4sight in head-to-head competition with funded incumbents, backed by zero validated evidence for the broader claim (all discovery conversations validate agent-specific pain, none validate general infra RCA as underserved) and no infra-dependency-graph tech built. It would also reverse the Stage 1 decision to anchor on Baraa's validated pain, before Stage 4's validation test (still pending) has even run.

**Resolution — vision vs. wedge:** the company's broader vision ("an intelligence layer for production operations — investigates incidents, identifies root causes, validates fixes, using the telemetry you already have") stays as the long-term positioning, matching the original README pitch. What ships for Baraa is a **deliberately scoped-down instantiation** of that vision — the agent-non-determinism wedge, not the whole product. This matches the README's own Phase 3 roadmap, which already staged broader scope for *after* the agent wedge is proven, not before. Engineering stays agent-agnostic where it's already cheap to do so (the hypothesis engine and evidence-verification logic don't care whether a citation comes from an agent trace or a service log); GTM focus, anomaly-detection heuristics, and customer conversations stay agent-specific until Baraa's validation closes the loop.

**Moat correction:** "our moat is MTTR cost savings" was proposed and corrected. MTTR reduction is the value proposition / ROI pitch — every competitor in this space (NeuBird, Datadog Bits AI, Rootly, incident.io) claims the identical outcome; the README's own Success Metrics table lists "reduce MTTR by 60%" as a target, same as the category norm. It is not defensible on its own — a competitor can say the same sentence.

Actual moat candidates identified:
1. **Evidence-verification technique** — citations checked mechanically in code (not just requested via prompt) is a real, non-trivial-to-replicate-well technical choice, and it's the thing that makes hypotheses trustworthy rather than merely plausible.
2. **Accumulated per-customer incident history** — every investigation makes the next one better for that customer (recurring failure detection, institutional pattern library, already named in the README's Capability Areas). This is a data-network-effect moat that compounds; MTTR savings don't.
3. **Trust built through track record** — once an on-call engineer has seen 4sight be right and verifiable across multiple real incidents, replacing it carries a workflow/trust switching cost beyond a feature comparison.

**Status: RESOLVED.** Vision stays broad for positioning; wedge stays narrow (Baraa, agent non-determinism) for what actually ships and gets validated next; moat framing corrected to (1) evidence-verification technique, (2) per-customer incident history accumulation, (3) trust/track record — not MTTR savings, which is the value prop, not the defensibility.
