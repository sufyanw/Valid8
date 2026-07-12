import {
  Alert02Icon,
  ArrowRight02Icon,
  CheckmarkBadge01Icon,
  QuoteDownIcon,
  ShieldEnergyIcon,
} from "@hugeicons/core-free-icons"
import { HugeiconsIcon } from "@hugeicons/react"

import type { EvidenceSource, Investigation } from "@/lib/types"
import { cn } from "@/lib/utils"

const sourceLabels: Record<EvidenceSource, string> = {
  trace_a: "Trace A",
  trace_b: "Trace B",
  deploy_diff: "Git diff",
}

const sourceStyles: Record<EvidenceSource, string> = {
  trace_a: "bg-sky-500/10 text-sky-700 dark:text-sky-300",
  trace_b: "bg-violet-500/10 text-violet-700 dark:text-violet-300",
  deploy_diff: "bg-orange-500/10 text-orange-700 dark:text-orange-300",
}

export function InvestigationReport({ investigation }: { investigation: Investigation }) {
  return (
    <section className="overflow-hidden rounded-2xl border bg-card shadow-[0_24px_80px_-48px_rgba(0,0,0,0.5)]">
      {investigation.mode === "stub" && (
        <div className="flex gap-3 border-b border-amber-500/25 bg-amber-500/10 px-5 py-4 text-amber-950 dark:text-amber-100 sm:px-7">
          <HugeiconsIcon icon={Alert02Icon} className="mt-0.5 size-5 shrink-0" />
          <div>
            <p className="text-sm font-semibold">Placeholder findings — not a live investigation</p>
            <p className="mt-0.5 text-xs leading-relaxed opacity-80">
              The backend is running in stub mode because no LLM key is configured. Do not act on this report.
            </p>
          </div>
        </div>
      )}

      <div className="border-b px-5 py-6 sm:px-7">
        <div className="mb-4 flex items-center gap-2 text-xs font-semibold tracking-[0.16em] text-muted-foreground uppercase">
          <HugeiconsIcon icon={ShieldEnergyIcon} className="size-4 text-emerald-600 dark:text-emerald-400" />
          Investigation report
        </div>
        <h2 className="max-w-4xl text-xl leading-snug font-semibold tracking-tight sm:text-2xl">
          {investigation.incident_summary}
        </h2>
      </div>

      <div className="space-y-4 px-5 py-6 sm:px-7">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="text-sm font-semibold">Ranked root causes</p>
            <p className="mt-1 text-xs text-muted-foreground">Every claim below is tied to verified source material.</p>
          </div>
          <span className="hidden items-center gap-1.5 text-xs text-emerald-700 sm:flex dark:text-emerald-400">
            <HugeiconsIcon icon={CheckmarkBadge01Icon} className="size-4" /> Evidence verified
          </span>
        </div>

        {investigation.hypotheses.map((hypothesis) => {
          const confidence = Math.max(0, Math.min(100, hypothesis.confidence))
          return (
            <article key={`${hypothesis.rank}-${hypothesis.claim}`} className="rounded-xl border bg-background/50 p-4 sm:p-5">
              <div className="flex items-start gap-4">
                <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-foreground font-mono text-xs font-bold text-background">
                  {hypothesis.rank}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <h3 className="max-w-3xl text-sm leading-relaxed font-semibold sm:text-base">{hypothesis.claim}</h3>
                    <div className="flex shrink-0 items-center gap-2">
                      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-muted">
                        <div className="h-full rounded-full bg-emerald-500" style={{ width: `${confidence}%` }} />
                      </div>
                      <span className="font-mono text-xs font-semibold tabular-nums">{confidence}%</span>
                    </div>
                  </div>

                  <div className="mt-4 space-y-3">
                    {hypothesis.evidence.map((evidence, index) => (
                      <div key={`${evidence.source}-${index}`} className="overflow-hidden rounded-lg border bg-muted/30">
                        <div className="flex items-center gap-2 border-b px-3 py-2">
                          <HugeiconsIcon icon={QuoteDownIcon} className="size-3.5 text-muted-foreground" />
                          <span className={cn("rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold tracking-wide uppercase", sourceStyles[evidence.source])}>
                            {sourceLabels[evidence.source]}
                          </span>
                          <span className="text-[10px] text-muted-foreground">verbatim excerpt</span>
                        </div>
                        <pre className="overflow-x-auto px-3 py-3 font-mono text-[12px] leading-relaxed whitespace-pre-wrap text-foreground/80">
                          <code>{evidence.excerpt}</code>
                        </pre>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </article>
          )
        })}

        <div className="flex gap-3 rounded-xl border border-emerald-600/20 bg-emerald-500/8 p-4 sm:p-5">
          <HugeiconsIcon icon={ArrowRight02Icon} className="mt-0.5 size-5 shrink-0 text-emerald-700 dark:text-emerald-400" />
          <div>
            <p className="text-xs font-semibold tracking-wider text-emerald-800 uppercase dark:text-emerald-300">Recommended action</p>
            <p className="mt-1.5 text-sm leading-relaxed">{investigation.recommended_action}</p>
          </div>
        </div>
      </div>

      <footer className="border-t bg-muted/20 px-5 py-3 font-mono text-[10px] text-muted-foreground sm:px-7">
        Mode: {investigation.mode} · {investigation.hypotheses.length} hypotheses shown · {investigation.dropped_hypotheses}{" "}
        {investigation.dropped_hypotheses === 1 ? "hypothesis" : "hypotheses"} failed verification and were hidden
      </footer>
    </section>
  )
}
