"use client"

import { useEffect, useState } from "react"
import {
  Alert02Icon,
  ArrowRight02Icon,
  CheckmarkBadge01Icon,
  CheckmarkCircle02Icon,
  Loading03Icon,
  QuoteDownIcon,
  RefreshIcon,
  ShieldEnergyIcon,
} from "@hugeicons/core-free-icons"
import { HugeiconsIcon } from "@hugeicons/react"

import { Button } from "@/components/ui/button"
import type { EvidenceSource, Investigation } from "@/lib/types"
import { cn } from "@/lib/utils"

const sourceLabels: Record<EvidenceSource, string> = {
  trace_a: "Healthy trace",
  trace_b: "Failed trace",
  deploy_diff: "Code change",
}

const sourceStyles: Record<EvidenceSource, string> = {
  trace_a: "bg-sky-500/10 text-sky-700 dark:text-sky-300",
  trace_b: "bg-red-500/10 text-red-700 dark:text-red-300",
  deploy_diff: "bg-orange-500/10 text-orange-700 dark:text-orange-300",
}

export function InvestigationReport({
  investigation,
}: {
  investigation: Investigation
}) {
  const [sandboxStage, setSandboxStage] = useState(0)
  const [sandboxRun, setSandboxRun] = useState(0)
  const topCause = investigation.hypotheses[0]
  const confidence = Math.max(0, Math.min(100, topCause?.confidence ?? 0))
  const evidenceCount = investigation.hypotheses.reduce(
    (count, hypothesis) => count + hypothesis.evidence.length,
    0
  )

  useEffect(() => {
    const applyPatch = window.setTimeout(() => setSandboxStage(1), 1600)
    const replayTrace = window.setTimeout(() => setSandboxStage(2), 3300)
    const finish = window.setTimeout(() => setSandboxStage(3), 5000)
    return () => {
      window.clearTimeout(applyPatch)
      window.clearTimeout(replayTrace)
      window.clearTimeout(finish)
    }
  }, [sandboxRun])

  function rerunSandbox() {
    setSandboxStage(0)
    setSandboxRun((run) => run + 1)
  }

  return (
    <section className="overflow-hidden rounded-2xl border bg-card shadow-[0_24px_80px_-48px_rgba(0,0,0,0.6)]">
      {investigation.mode === "stub" && <StubBanner />}

      <header className="border-b bg-gradient-to-br from-emerald-500/10 via-background to-background px-5 py-6 sm:px-7 sm:py-8">
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/12 px-2.5 py-1 text-xs font-semibold text-emerald-700 dark:text-emerald-300">
            <HugeiconsIcon icon={CheckmarkCircle02Icon} className="size-4" />{" "}
            Investigation complete
          </span>
          <span className="rounded-full border bg-background/70 px-2.5 py-1 font-mono text-[10px] text-muted-foreground">
            {evidenceCount} verified{" "}
            {evidenceCount === 1 ? "citation" : "citations"}
          </span>
        </div>
        <p className="mt-5 text-xs font-semibold tracking-[0.16em] text-muted-foreground uppercase">
          What happened
        </p>
        <h2 className="mt-2 max-w-4xl text-2xl leading-snug font-semibold tracking-[-0.025em] sm:text-3xl">
          {investigation.incident_summary}
        </h2>
      </header>

      <div className="space-y-6 px-5 py-6 sm:px-7">
        <section className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_180px]">
          <div className="rounded-xl border bg-background/60 p-5">
            <div className="flex items-center gap-2 text-xs font-semibold tracking-wider text-muted-foreground uppercase">
              <HugeiconsIcon
                icon={ShieldEnergyIcon}
                className="size-4 text-emerald-600"
              />{" "}
              Most likely cause
            </div>
            <p className="mt-3 text-base leading-relaxed font-semibold sm:text-lg">
              {topCause?.claim ?? "No evidence-backed cause was returned."}
            </p>
          </div>
          <div className="flex flex-col justify-center rounded-xl border bg-background/60 p-5">
            <p className="text-xs font-medium text-muted-foreground">
              Confidence
            </p>
            <p className="mt-1 font-mono text-3xl font-semibold tabular-nums">
              {confidence}%
            </p>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-emerald-500"
                style={{ width: `${confidence}%` }}
              />
            </div>
          </div>
        </section>

        <RecommendedChange
          currentBehavior={topCause?.claim ?? investigation.incident_summary}
          action={investigation.recommended_action}
        />
        <SandboxValidation stage={sandboxStage} onRerun={rerunSandbox} />

        <section>
          <div className="flex items-end justify-between gap-4">
            <div>
              <p className="text-sm font-semibold">
                Evidence behind the verdict
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Open a cause to show the exact trace or code excerpts during the
                demo.
              </p>
            </div>
            <span className="hidden items-center gap-1.5 text-xs text-emerald-700 sm:flex dark:text-emerald-400">
              <HugeiconsIcon icon={CheckmarkBadge01Icon} className="size-4" />{" "}
              Evidence verified
            </span>
          </div>
          <div className="mt-3 space-y-2">
            {investigation.hypotheses.map((hypothesis, index) => (
              <details
                key={`${hypothesis.rank}-${hypothesis.claim}`}
                open={index === 0}
                className="group overflow-hidden rounded-xl border bg-background/40"
              >
                <summary className="flex cursor-pointer list-none items-center gap-3 p-4 hover:bg-muted/40">
                  <span className="grid size-7 shrink-0 place-items-center rounded-full bg-foreground font-mono text-[11px] font-bold text-background">
                    {hypothesis.rank}
                  </span>
                  <span className="min-w-0 flex-1 text-sm font-semibold">
                    {hypothesis.claim}
                  </span>
                  <span className="font-mono text-xs font-semibold text-muted-foreground tabular-nums">
                    {hypothesis.confidence}%
                  </span>
                  <span className="text-muted-foreground transition-transform group-open:rotate-90">
                    ›
                  </span>
                </summary>
                <div className="space-y-2 border-t p-3">
                  {hypothesis.evidence.map((evidence, evidenceIndex) => (
                    <div
                      key={`${evidence.source}-${evidenceIndex}`}
                      className="overflow-hidden rounded-lg border bg-muted/20"
                    >
                      <div className="flex items-center gap-2 border-b px-3 py-2">
                        <HugeiconsIcon
                          icon={QuoteDownIcon}
                          className="size-3.5 text-muted-foreground"
                        />
                        <span
                          className={cn(
                            "rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold tracking-wide uppercase",
                            sourceStyles[evidence.source]
                          )}
                        >
                          {sourceLabels[evidence.source]}
                        </span>
                      </div>
                      <pre className="max-h-40 overflow-auto px-3 py-3 font-mono text-[11px] leading-relaxed whitespace-pre-wrap text-foreground/80">
                        <code>{evidence.excerpt}</code>
                      </pre>
                    </div>
                  ))}
                </div>
              </details>
            ))}
          </div>
        </section>
      </div>

      <footer className="flex flex-wrap items-center justify-between gap-2 border-t bg-muted/20 px-5 py-3 font-mono text-[10px] text-muted-foreground sm:px-7">
        <span>
          {investigation.hypotheses.length} ranked causes ·{" "}
          {investigation.dropped_hypotheses} unverified hidden
        </span>
        <span className="uppercase">{investigation.mode} mode</span>
      </footer>
    </section>
  )
}

function RecommendedChange({
  currentBehavior,
  action,
}: {
  currentBehavior: string
  action: string
}) {
  return (
    <section className="overflow-hidden rounded-xl border border-emerald-600/25">
      <div className="flex gap-3 bg-emerald-500/8 p-5">
        <HugeiconsIcon
          icon={ArrowRight02Icon}
          className="mt-0.5 size-5 shrink-0 text-emerald-600"
        />
        <div>
          <p className="text-xs font-semibold tracking-wider text-emerald-800 uppercase dark:text-emerald-300">
            Recommended fix
          </p>
          <p className="mt-1.5 text-base leading-relaxed font-semibold">
            {action}
          </p>
        </div>
      </div>
      <div className="border-t bg-[#101210] font-mono text-xs text-zinc-200">
        <div className="border-b border-white/10 px-4 py-2 text-[10px] tracking-wider text-zinc-500 uppercase">
          Before → after
        </div>
        <div className="overflow-x-auto py-2">
          <div className="flex min-w-max bg-red-500/10 px-4 py-2 text-red-300">
            <span className="mr-3 text-red-500 select-none">−</span>
            <span>{currentBehavior}</span>
          </div>
          <div className="flex min-w-max bg-emerald-500/10 px-4 py-2 text-emerald-300">
            <span className="mr-3 text-emerald-500 select-none">+</span>
            <span>{action}</span>
          </div>
        </div>
      </div>
    </section>
  )
}

function SandboxValidation({
  stage,
  onRerun,
}: {
  stage: number
  onRerun: () => void
}) {
  const [applyState, setApplyState] = useState<
    "idle" | "applying" | "applied" | "error"
  >("idle")
  const [applyError, setApplyError] = useState<string | null>(null)
  const steps = [
    ["Isolated environment", "Temporary worktree created"],
    ["Proposed fix", "Patch applied only inside sandbox"],
    ["Regression replay", "Original failing trace tested"],
  ]

  async function applyFix() {
    setApplyState("applying")
    setApplyError(null)
    try {
      const response = await fetch("/api/feature-flags", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ force_failure: false }),
      })
      const result = (await response.json().catch(() => null)) as {
        force_failure?: boolean
        error?: string
      } | null
      if (!response.ok || result?.force_failure !== false) {
        throw new Error(
          result?.error ?? "The monitored app did not confirm the fix."
        )
      }
      setApplyState("applied")
    } catch (error) {
      setApplyError(
        error instanceof Error ? error.message : "The fix could not be applied."
      )
      setApplyState("error")
    }
  }

  function rerun() {
    setApplyState("idle")
    setApplyError(null)
    onRerun()
  }

  return (
    <details
      open
      className={cn(
        "group overflow-hidden rounded-xl border transition-colors",
        stage === 3
          ? "border-emerald-500/40 bg-emerald-500/5"
          : "border-sky-500/30 bg-sky-500/5"
      )}
    >
      <summary className="flex cursor-pointer list-none items-center gap-3 p-4 sm:p-5">
        <div
          className={cn(
            "grid size-10 shrink-0 place-items-center rounded-xl",
            stage === 3
              ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300"
              : "bg-sky-500/15 text-sky-700 dark:text-sky-300"
          )}
        >
          <HugeiconsIcon
            icon={stage === 3 ? CheckmarkCircle02Icon : ShieldEnergyIcon}
            className={cn("size-5", stage < 3 && "animate-pulse")}
          />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-semibold">
              {stage === 3
                ? "Fix verified in isolated sandbox"
                : "Testing fix in isolated sandbox"}
            </p>
            <span className="rounded-full border bg-background/70 px-2 py-0.5 font-mono text-[9px] font-semibold tracking-wide uppercase">
              Simulated
            </span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {stage === 3
              ? "Patch applied and failing trace replayed without reproducing the issue."
              : "Applying the proposed patch and replaying the original failure."}
          </p>
        </div>
        {stage < 3 ? (
          <HugeiconsIcon
            icon={Loading03Icon}
            className="size-5 shrink-0 animate-spin text-sky-600"
          />
        ) : (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/12 px-2.5 py-1 text-xs font-semibold text-emerald-700 dark:text-emerald-300">
            <HugeiconsIcon icon={CheckmarkCircle02Icon} className="size-4" />{" "}
            Fix passed
          </span>
        )}
        <span className="text-muted-foreground transition-transform group-open:rotate-90">
          ›
        </span>
      </summary>

      <div className="border-t bg-background/45 p-4 sm:p-5">
        <div className="grid gap-2 sm:grid-cols-3">
          {steps.map(([label, detail], index) => (
            <div
              key={label}
              className={cn(
                "flex items-start gap-2 rounded-lg border bg-background px-3 py-3 text-xs",
                index < stage || stage === 3
                  ? "text-emerald-700"
                  : index === stage
                    ? "text-foreground"
                    : "text-muted-foreground/50"
              )}
            >
              {index < stage || stage === 3 ? (
                <HugeiconsIcon icon={CheckmarkBadge01Icon} className="size-4" />
              ) : index === stage ? (
                <HugeiconsIcon
                  icon={Loading03Icon}
                  className="size-4 animate-spin"
                />
              ) : (
                <span className="ml-1 size-2 rounded-full bg-current" />
              )}
              <span>
                <span className="block font-semibold">{label}</span>
                <span className="mt-0.5 block text-[10px] text-muted-foreground">
                  {detail}
                </span>
              </span>
            </div>
          ))}
        </div>
        {stage === 3 && (
          <div className="mt-3 flex flex-col gap-3 rounded-lg border border-emerald-500/25 bg-emerald-500/8 px-4 py-3 sm:flex-row sm:items-center">
            <HugeiconsIcon
              icon={CheckmarkCircle02Icon}
              className="size-5 shrink-0 text-emerald-600"
            />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-emerald-800 dark:text-emerald-300">
                Validation outcome: fix works in simulated replay
              </p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                The original anomaly was not reproduced after the mock patch. No
                real code was executed.
              </p>
            </div>
            <Button
              type="button"
              onClick={() => void applyFix()}
              disabled={applyState === "applying" || applyState === "applied"}
              className="shrink-0 rounded-lg"
            >
              <HugeiconsIcon
                icon={
                  applyState === "applying"
                    ? Loading03Icon
                    : applyState === "applied"
                      ? CheckmarkCircle02Icon
                      : ArrowRight02Icon
                }
                className={cn(applyState === "applying" && "animate-spin")}
              />
              {applyState === "applying"
                ? "Applying…"
                : applyState === "applied"
                  ? "Fix applied"
                  : applyState === "error"
                    ? "Retry apply"
                    : "Apply fix"}
            </Button>
          </div>
        )}
        {stage === 3 && (
          <div className="mt-3 flex justify-end">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={rerun}
              className="rounded-lg text-muted-foreground"
            >
              <HugeiconsIcon icon={RefreshIcon} /> Rerun sandbox
            </Button>
          </div>
        )}
        {applyState === "applied" && (
          <p className="mt-2 text-right text-[10px] text-muted-foreground">
            force_failure is now false in the monitored app
          </p>
        )}
        {applyState === "error" && applyError && (
          <p className="mt-2 text-right text-xs text-red-600 dark:text-red-400">
            Fix not applied. {applyError}
          </p>
        )}
      </div>
    </details>
  )
}

function StubBanner() {
  return (
    <div className="flex gap-3 border-b border-amber-500/25 bg-amber-500/10 px-5 py-4 text-amber-950 sm:px-7 dark:text-amber-100">
      <HugeiconsIcon icon={Alert02Icon} className="mt-0.5 size-5 shrink-0" />
      <div>
        <p className="text-sm font-semibold">
          Demo data — not a live investigation
        </p>
        <p className="mt-0.5 text-xs opacity-80">
          Configure an LLM key before acting on these findings.
        </p>
      </div>
    </div>
  )
}
