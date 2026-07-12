# 4sight

*Intelligence layer for ops at scale.*

---

## Problem

Modern observability platforms can surface relevant telemetry and even correlate related signals. The remaining challenge is determining why an incident occurred, validating competing hypotheses, and identifying the most effective remediation across increasingly complex, AI-driven production systems.

What exists:

- Observability → collecting and presenting evidence.

What to refine:

- Investigation → reasoning about the evidence.
- Decision support → recommending what to do.

---

## Solution

4sight is an investigation and decision-support layer for production systems. It connects to the telemetry and operational tools a team already uses, then investigates incidents across agent traces, logs, metrics, deployments, services, and code changes.

Instead of presenting more raw data, 4sight builds and tests possible explanations for what went wrong. It identifies the most likely root cause, shows the evidence behind that conclusion, and recommends the next action an engineer should take.

The workflow has three stages:

1. **Triage the incident.** Determine the affected users and systems, assess severity, and narrow the investigation to the most relevant signals.
2. **Investigate the cause.** Reconstruct the sequence of events, compare normal and failed executions, and explain why the system or agent behaved unexpectedly.
3. **Validate the response.** Recommend a prioritized remediation and test proposed changes in a safe environment before they reach production.

For AI-agent systems, 4sight must account for non-deterministic execution, large and costly traces, tool calls that do not match stated intent, and failures that span both the agent and its underlying infrastructure. The product should provide this analysis without forcing teams to replace their existing observability stack or send all operational data to a single vendor.

The intended outcome is lower mean time to resolution, less reliance on specialist knowledge, and fewer hours spent manually investigating production failures.

---

## Personas

These personas are provisional because the research sample is small: four substantive conversations, one incomplete conversation, and a set of synthesis notes. The personas represent distinct product needs rather than fictional demographic profiles.

### Persona 1: Production AI Platform Engineer

**Name:** Marcus

Marcus is a software engineer responsible for AI agents that are already running in production. His work includes investigating failures, debugging complex execution traces, and helping teams understand why agents behave differently across similar requests.

He currently relies on internally built monitoring infrastructure because standard telemetry does not explain enough about non-deterministic behavior. When an issue occurs, his team may need to reconstruct the full sequence of events manually and involve data scientists or engineers with direct model experience. Even then, the recreated flow may not closely match the original execution.

**Main problem:** Reproducing and explaining non-deterministic agent failures requires too much manual work and specialized expertise.

**Goals:** He wants incidents to be easier to reconstruct, explain, and resolve without depending on a small group of specialists.

**Needs from the product:** He needs a dependable way to understand why an agent made a decision and to investigate failed executions with enough context to identify the cause.

**Current tools:** Proprietary monitoring systems, custom debugging infrastructure, and internal telemetry.

**Decision factors:** Adoption depends on integration with existing systems, reduced debugging time, trustworthy trace reconstruction, and minimal vendor lock-in.

*Informed by Conversation 1 and the finding that existing tools expose events but often fail to explain why failures occur.*

---

### Persona 2: Engineer Preparing Agents for Production

**Name:** Daniel

Daniel is a software engineer who recently started building AI agents but has not deployed them to production yet. He is responsible for setting up observability, evaluating agent behavior, and establishing a debugging workflow before the system reaches customers.

He currently uses OpenTelemetry and a reflection agent that evaluates the output of the primary agent. Setting up the telemetry takes about half a day, and the resulting logs still leave important questions unanswered. For example, an agent may indicate that it intends to call a tool but never perform the call, with little explanation for the mismatch.

**Main problem:** Existing observability tools collect traces but do not clearly explain unexpected agent behavior.

**Goals:** He wants confidence that agents behave correctly before launch and a monitoring approach that will remain useful once the system reaches production.

**Needs from the product:** He needs fast setup and clear explanations that turn raw execution data into something he can act on.

**Current tools:** OpenTelemetry, reflection agents, logs, and manual investigation.

**Decision factors:** He will consider ease of setup, support for open standards, compatibility with his current stack, and whether the product provides insight beyond ordinary logging.

*Informed by Conversation 2 and the broader finding that teams want explanation rather than more raw telemetry.*

---

### Persona 3: AI Reliability Engineer

**Name:** Ravi

Ravi is a software engineer responsible for validating AI agent behavior before major deployments and supporting reliability during production operations. His team uses evaluation test cases to confirm that agents continue working as expected after changes.

He currently runs a substantial evaluation process before each major release. The process takes about five hours and is expensive to execute, but it is necessary because failures discovered after deployment are harder to diagnose and may affect customers. His team also relies on Solace and expects to gain more operational insight during on-call rotations.

**Main problem:** Agent validation is slow and expensive, while post-deployment failures remain difficult to investigate.

**Goals:** He wants faster release validation and earlier detection of regressions without reducing confidence in the system.

**Needs from the product:** He needs continuous evidence about agent quality and failure patterns so his team can reduce repetitive evaluation work and narrow investigations more quickly.

**Current tools:** Agent evaluation suites, test cases, Solace, deployment checks, and on-call workflows.

**Decision factors:** He will look for measurable reductions in evaluation time and cost, compatibility with release workflows, and evidence that the product improves production reliability.

*Informed by Conversation 3 and the reported five-hour, high-cost evaluation workflow.*

---

### Persona 4: Engineering Leader Responsible for AI Infrastructure

**Name:** Omar

Omar is an engineering leader responsible for the cost, scalability, and operational health of AI systems across multiple teams. He evaluates platform decisions rather than debugging every individual incident himself.

He currently sees traditional logging systems produce large volumes of data because a single agent request can involve many processing steps, tool calls, and large context windows. Capturing everything increases storage and analysis costs, while the additional data does not always make debugging easier. He is also interested in whether semantic approaches, such as AgentSight, can connect application behavior with lower-level system activity and support more efficient models.

**Main problem:** AI observability generates rapidly increasing cost and data volume without a proportional improvement in insight.

**Goals:** He wants observability that scales financially and technically while helping teams improve reliability and model efficiency.

**Needs from the product:** He needs useful operational insight without collecting or storing unnecessary data, and he needs deployment options that fit enterprise requirements.

**Current tools:** Traditional logging systems, internal observability platforms, infrastructure monitoring, and AgentSight research.

**Decision factors:** Cost predictability, scalability, self-hosting, multi-provider support, interoperability, security, and reduced dependence on a single vendor will determine adoption.

*Informed by Conversation 5 and the synthesis notes on cost unpredictability, vendor lock-in, self-hosting, multi-provider support, and manual debugging.*

---

## Jobs to Be Done

Each persona shares a common underlying frustration: raw telemetry collects what happened but does not explain why, and that explanation gap is where engineering time disappears. The following jobs map across all four personas and represent the clearest opportunities for 4sight to deliver value.

| Job | Who feels it most | Current workaround |
|---|---|---|
| Reconstruct why an agent made a specific decision | Marcus, Daniel | Manual trace review, specialist involvement |
| Detect when an agent's stated intent diverges from its actions | Daniel, Ravi | Reflection agents, manual log inspection |
| Reduce evaluation time before each release | Ravi | Accepts the cost; runs it anyway |
| Scope blast radius when an alert fires | Marcus, Omar | War rooms, manual correlation across tools |
| Explain a failure to someone who was not on-call | Marcus, Ravi | Postmortem documents written from memory |
| Control observability cost as agent usage scales | Omar | Sampling, log retention limits |
| Validate a fix before it reaches production | Daniel, Ravi | Staging environments, eval suites |
| Build institutional knowledge from past incidents | All | Wiki pages, Slack threads, tribal knowledge |

---

## Capability Areas

### 1. Trace Intelligence

Standard traces record what happened. 4sight adds a reasoning layer on top: it identifies which steps were anomalous, surfaces the decision points that diverged from expected behavior, and flags tool calls where the agent's expressed intent did not match its actual execution.

This directly answers Marcus's problem of manually reconstructing agent decisions and Daniel's problem of unexplained intent-to-action gaps.

Areas not currently addressed by existing tools:
- **Intent drift detection.** Identify when an agent's plan changes mid-execution without an external trigger.
- **Counterfactual comparison.** Show what a healthy execution looked like for the same input class and highlight where the failing trace diverged.
- **Semantic deduplication.** Group traces by behavioral pattern rather than by exact call sequence, reducing noise in high-volume systems.

### 2. Automated Triage

When an alert fires, the first question is always: what is actually broken, and for whom? 4sight answers this before a human opens a dashboard by automatically scoping the affected users, services, and agent chains, then producing a structured incident brief.

This removes the war-room phase where engineers orient themselves before any real investigation begins.

Areas not currently addressed:
- **Blast radius estimation.** Project how many users or downstream services are likely affected based on dependency graphs and current traffic patterns.
- **Noise suppression.** Distinguish a flapping metric from a genuine degradation and suppress alerts that are symptoms of a known root cause already under investigation.
- **Priority scoring.** Rank simultaneous incidents by customer impact and fix complexity rather than alert severity alone.

### 3. Root Cause Analysis

4sight proposes hypotheses, ranks them by evidence strength, and shows the chain of events that supports each one. Engineers see the reasoning, not just the conclusion, so they can accept, reject, or refine it.

This reduces dependence on specialists and shortens the time between "alert fires" and "team understands what happened."

Areas not currently addressed:
- **Cross-layer causality.** Correlate agent-level failures with underlying infrastructure events such as deployment timing, model version changes, or upstream API degradation.
- **Prompt and context analysis.** Identify whether a failure originates in the prompt template, the retrieved context, or the model's response, without sending full prompts to an external vendor.
- **Multi-agent attribution.** In systems where agents invoke other agents, trace a failure back to the originating agent rather than the last one in the chain.

### 4. Continuous Evaluation

Rather than running a five-hour evaluation suite before every release, 4sight monitors production behavior continuously and surfaces regressions as they emerge. When a change ships, it compares the behavioral fingerprint of the new version against the established baseline.

This directly addresses Ravi's evaluation bottleneck and gives Daniel pre-launch confidence without requiring a full evaluation pass.

Areas not currently addressed:
- **Behavioral fingerprinting.** Represent agent behavior as a compact signature that captures decision patterns rather than raw outputs, making regression detection fast and model-agnostic.
- **Canary-aware evaluation.** Automatically scope evaluation to the subset of traffic hitting the new version and surface differences before full rollout.
- **Eval case suggestion.** Recommend new test cases based on failure patterns observed in production that are not yet covered by the existing evaluation suite.

### 5. Safe Remediation

Before a fix reaches production, 4sight can replay the original failing trace against the proposed change in an isolated environment, confirm the fix resolves the failure, and check for regressions in adjacent behavior.

This closes the loop between investigation and action and reduces the risk that a hotfix creates a new problem.

Areas not currently addressed:
- **Synthetic replay.** Reconstruct a sanitized version of a failing trace from production and replay it in staging without requiring full production data to be copied.
- **Fix confidence scoring.** Estimate the probability that a proposed change resolves the root cause versus treating a symptom, based on how directly it addresses the identified failure point.
- **Rollback prediction.** Before a deployment, identify which failure modes would require a rollback and pre-stage the rollback path.

### 6. Cost Intelligence

For Omar, observability cost is a growing operational concern. 4sight applies selective capture: it collects compressed behavioral summaries during normal operation and expands to full trace capture only when anomalies are detected.

Areas not currently addressed:
- **Per-request cost attribution.** Break down model inference, tool call, and observability costs to the individual agent request or user session, so teams can identify which workflows are disproportionately expensive.
- **Efficiency regression detection.** Alert when a new model version or prompt change causes a measurable increase in token consumption without a corresponding improvement in output quality.
- **Adaptive sampling.** Automatically adjust trace capture granularity based on anomaly signals, collecting more detail when behavior is unusual and less when the system is healthy.

### 7. Incident Knowledge Base

Every investigated incident produces structured output: a timeline, a root cause, the evidence that supported it, and the action taken. 4sight accumulates this into a searchable knowledge base that reduces dependence on tribal knowledge and helps on-call engineers who were not present during the original incident.

Areas not currently addressed:
- **Postmortem generation.** Produce a draft postmortem from the investigation record automatically, covering timeline, impact, root cause, and contributing factors.
- **Recurring failure detection.** Identify when a new incident matches the pattern of a past one and surface the prior investigation and resolution immediately.
- **On-call handoff briefs.** Generate a concise summary of open incidents, recent anomalies, and outstanding risk for the incoming on-call engineer.

---

## Integration Ecosystem

4sight is designed to connect to the tools teams already use. It does not require replacing an existing observability stack.

**Telemetry and tracing:** OpenTelemetry, Datadog, Honeycomb, Grafana, Jaeger, Zipkin

**Log management:** Elastic, Splunk, Loki, CloudWatch Logs

**Metrics:** Prometheus, Datadog, CloudWatch Metrics, InfluxDB

**Incident management:** PagerDuty, OpsGenie, Slack, Jira

**CI/CD and deployment:** GitHub Actions, GitLab CI, ArgoCD, Spinnaker

**AI agent frameworks:** LangChain, LangGraph, CrewAI, AutoGen, custom OpenTelemetry-instrumented agents

**Model providers:** OpenAI, Anthropic, Google, Mistral, and self-hosted models via OpenAI-compatible APIs

**Deployment modes:** SaaS, self-hosted (single-tenant), and VPC-deployed (data never leaves the customer environment)

---

## Phased Roadmap

### Phase 1 — Foundation (Months 1–3)

Target persona: Daniel (pre-production) and Marcus (production debugging).

Goals: Establish the core investigation loop and validate that 4sight explains failures more clearly than existing tools.

- OpenTelemetry ingest and trace parsing
- Intent-to-action gap detection on agent traces
- Basic root cause hypothesis generation with supporting evidence
- Integration with one alerting source (PagerDuty or Slack)
- Self-hosted deployment option

Success signal: Engineers can identify the root cause of a traced failure without opening a second tool.

### Phase 2 — Continuous Quality (Months 4–6)

Target persona: Ravi (reliability and pre-release validation).

Goals: Replace the manual pre-release evaluation cycle with continuous behavioral monitoring.

- Behavioral fingerprinting and baseline establishment
- Regression detection on canary deployments
- Eval case suggestion from production failure patterns
- Postmortem generation

Success signal: Teams reduce pre-release evaluation time by at least 50% without increasing post-deployment incident rate.

### Phase 3 — Scale and Governance (Months 7–12)

Target persona: Omar (infrastructure cost and enterprise requirements).

Goals: Make 4sight economically viable at scale and fit for enterprise procurement.

- Adaptive sampling and cost-aware trace capture
- Per-request cost attribution dashboard
- Multi-tenant self-hosting with role-based access
- SOC 2 Type II, audit logging, and data residency controls
- Multi-provider model support and vendor-agnostic positioning

Success signal: Omar can demonstrate a measurable reduction in observability cost-per-request and produce a compliance report without involving the security team.

---

## Success Metrics

| Metric | Definition | Target |
|---|---|---|
| Mean time to root cause | Time from alert to confirmed root cause | Reduce by 60% vs. baseline |
| Evaluation cycle time | Duration of pre-release agent evaluation | Reduce by 50% |
| Specialist escalations | Incidents requiring data scientist or model expert involvement | Reduce by 40% |
| Observability cost per request | Storage and analysis cost per agent request | Flat or declining as volume grows |
| Postmortem coverage | Percentage of incidents with a structured postmortem | Increase from current baseline |
| Recurring incident rate | Incidents matching a prior pattern that were not caught by existing evals | Target: flagged before customer impact |

---

## Open Questions and Risks

**Data sensitivity.** Agent traces often contain user inputs and model outputs that cannot leave the customer environment. The product must offer a deployment mode where all analysis happens inside the customer's infrastructure, including the reasoning layer.

**Non-determinism as a baseline problem.** Defining "normal" behavior for a non-deterministic system is genuinely hard. Behavioral fingerprinting needs to tolerate acceptable variance without treating every output difference as an anomaly.

**Trust in automated conclusions.** Engineers will not act on a root cause recommendation they cannot verify. Every conclusion must be accompanied by the evidence and reasoning that produced it, and the product must make it easy to disagree and override.

**Integration surface area.** Supporting every observability tool is not feasible in Phase 1. Prioritizing OpenTelemetry as the primary ingest path covers the broadest surface because it is already the integration target for most modern agent frameworks.

**AI-on-AI risk.** Using a model to investigate model failures introduces the possibility that the investigation layer itself makes errors. The product should be explicit about confidence levels and should surface low-confidence conclusions differently from high-confidence ones.

**Regulatory and compliance requirements.** Enterprise customers in regulated industries may require full audit trails of every investigation action, data residency guarantees, and the ability to explain product conclusions to auditors. These requirements should inform the architecture before Phase 3.
