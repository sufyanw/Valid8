"use client"

import {
  FormEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
  useSyncExternalStore,
} from "react"
import {
  Activity01Icon,
  AiSearchIcon,
  Alert02Icon,
  ArrowRight02Icon,
  CheckmarkCircle02Icon,
  Clock01Icon,
  ComputerTerminal01Icon,
  FolderGitIcon,
  Loading03Icon,
  Moon02Icon,
  PlayIcon,
  RefreshIcon,
  Sun03Icon,
} from "@hugeicons/core-free-icons"
import { HugeiconsIcon } from "@hugeicons/react"
import { useTheme } from "next-themes"

import { InvestigationReport } from "@/components/investigation-report"
import { Button } from "@/components/ui/button"
import type {
  ApiError,
  Investigation,
  LogSpan,
  WatchResponse,
  WatchStatus,
} from "@/lib/types"
import { cn } from "@/lib/utils"

type RequestError = { message: string; code?: ApiError["code"] }
type DirectoryListing = { path: string; parent: string; directories: string[] }

async function apiFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init)
  const data = (await response.json().catch(() => null)) as T | ApiError | null
  if (!response.ok) {
    const error = data as ApiError | null
    throw {
      message: error?.error ?? "The request failed. Please try again.",
      code: error?.code,
    } satisfies RequestError
  }
  return data as T
}

export function Dashboard() {
  const [repoPath, setRepoPath] = useState("")
  const [watchInfo, setWatchInfo] = useState<WatchResponse | null>(null)
  const [status, setStatus] = useState<WatchStatus | null>(null)
  const [report, setReport] = useState<Investigation | null>(null)
  const [watchPending, setWatchPending] = useState(false)
  const [stopPending, setStopPending] = useState(false)
  const [investigating, setInvestigating] = useState(false)
  const [watchError, setWatchError] = useState<RequestError | null>(null)
  const [statusError, setStatusError] = useState<RequestError | null>(null)
  const [investigationError, setInvestigationError] =
    useState<RequestError | null>(null)
  const [manualUnavailable, setManualUnavailable] = useState(false)
  const [announcement, setAnnouncement] = useState<string | null>(null)
  const [folderPickerOpen, setFolderPickerOpen] = useState(false)
  const seenTrigger = useRef<string | null>(null)
  const seenActiveInvestigation = useRef<string | null>(null)
  const reportRef = useRef<HTMLDivElement>(null)

  const pollStatus = useCallback(async () => {
    try {
      const next = await apiFetch<WatchStatus>("/api/status")
      setStatus(next)
      setStatusError(null)
      if (next.active_investigation) {
        const activeKey = `${next.active_investigation.triggered_run_id}:${next.active_investigation.triggered_at}`
        setInvestigating(true)
        if (seenActiveInvestigation.current !== activeKey) {
          seenActiveInvestigation.current = activeKey
          setAnnouncement(
            "An issue was detected. Investigation is now in progress."
          )
          sendInvestigationNotification(
            next.active_investigation.anomaly_reason
          )
        }
      }
      if (next.latest_investigation) {
        const triggerKey = `${next.latest_investigation.triggered_run_id}:${next.latest_investigation.triggered_at}`
        setReport(next.latest_investigation)
        setInvestigating(false)
        if (seenTrigger.current !== triggerKey) {
          seenTrigger.current = triggerKey
          setAnnouncement("An anomaly triggered a new verified investigation.")
          window.setTimeout(
            () =>
              reportRef.current?.scrollIntoView({
                behavior: "smooth",
                block: "start",
              }),
            100
          )
        }
      }
    } catch (error) {
      setStatusError(error as RequestError)
    }
  }, [])

  useEffect(() => {
    const initialPoll = window.setTimeout(() => void pollStatus(), 0)
    const interval = window.setInterval(() => void pollStatus(), 3000)
    return () => {
      window.clearTimeout(initialPoll)
      window.clearInterval(interval)
    }
  }, [pollStatus])

  useEffect(() => {
    if (!announcement) return
    const timeout = window.setTimeout(() => setAnnouncement(null), 7000)
    return () => window.clearTimeout(timeout)
  }, [announcement])

  async function startWatching(event: FormEvent) {
    event.preventDefault()
    if (!repoPath.trim()) return
    setWatchPending(true)
    setWatchError(null)
    requestBrowserNotificationPermission()
    try {
      const response = await apiFetch<WatchResponse>("/api/watch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_path: repoPath.trim() }),
      })
      setWatchInfo(response)
      setStatus({
        watching: true,
        repo_path: response.repo_path,
        log_tail: [],
        known_tools: [],
        baseline_run_id: null,
        latest_investigation: null,
        active_investigation: null,
      })
    } catch (error) {
      setWatchError(error as RequestError)
    } finally {
      setWatchPending(false)
    }
  }

  async function stopWatching() {
    setStopPending(true)
    setWatchError(null)
    try {
      await apiFetch<{ status: "stopped" }>("/api/watch", { method: "DELETE" })
      setWatchInfo(null)
      setStatus((current) => (current ? { ...current, watching: false } : null))
      setAnnouncement("Monitoring stopped.")
    } catch (error) {
      setWatchError(error as RequestError)
    } finally {
      setStopPending(false)
    }
  }

  async function investigate(
    path: "/api/investigate" | "/api/investigate/now"
  ) {
    setInvestigating(true)
    setInvestigationError(null)
    try {
      const response = await apiFetch<Investigation>(path, { method: "POST" })
      setReport(response)
      window.setTimeout(
        () =>
          reportRef.current?.scrollIntoView({
            behavior: "smooth",
            block: "start",
          }),
        100
      )
    } catch (error) {
      const requestError = error as RequestError
      if (path.endsWith("/now") && requestError.code === "BACKEND_NOT_READY")
        setManualUnavailable(true)
      setInvestigationError(requestError)
    } finally {
      setInvestigating(false)
    }
  }

  const isWatching = status?.watching ?? Boolean(watchInfo)

  return (
    <div className="min-h-svh bg-background">
      <Header watching={isWatching} />

      {announcement && (
        <div
          className="fixed top-20 right-4 z-50 flex max-w-sm items-start gap-3 rounded-xl border border-emerald-500/30 bg-card p-4 shadow-xl"
          role="status"
        >
          <HugeiconsIcon
            icon={CheckmarkCircle02Icon}
            className="mt-0.5 size-5 shrink-0 text-emerald-500"
          />
          <div>
            <p className="text-sm font-semibold">Investigation complete</p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {announcement}
            </p>
          </div>
        </div>
      )}

      <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 sm:py-12 lg:px-8">
        <section className="mb-10 grid gap-8 lg:grid-cols-[1fr_0.72fr] lg:items-end">
          <div>
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border bg-card px-3 py-1.5 text-xs text-muted-foreground shadow-sm">
              <span className="size-1.5 rounded-full bg-emerald-500" />{" "}
              Evidence-grounded incident response
            </div>
            <h1 className="max-w-3xl text-4xl leading-[1.05] font-semibold tracking-[-0.04em] sm:text-5xl">
              See why your agent{" "}
              <span className="text-muted-foreground">went off course.</span>
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-relaxed text-muted-foreground sm:text-base">
              Monitor execution traces, detect behavioral drift, and investigate
              every claim against real logs and git history.
            </p>
          </div>
          <form
            onSubmit={startWatching}
            className="rounded-2xl border bg-card p-2 shadow-[0_20px_60px_-36px_rgba(0,0,0,0.5)]"
          >
            <label htmlFor="repo-path" className="sr-only">
              Local repository path
            </label>
            <div className="flex flex-col gap-2 sm:flex-row lg:flex-col xl:flex-row">
              <div className="flex h-11 min-w-0 flex-1 items-center gap-2 px-3">
                <HugeiconsIcon
                  icon={FolderGitIcon}
                  className="size-4 shrink-0 text-muted-foreground"
                />
                <input
                  id="repo-path"
                  value={repoPath}
                  onChange={(event) => setRepoPath(event.target.value)}
                  placeholder="/Users/you/project"
                  className="min-w-0 flex-1 bg-transparent font-mono text-sm outline-none placeholder:text-muted-foreground/60"
                  disabled={watchPending}
                />
                <button
                  type="button"
                  onClick={() => setFolderPickerOpen(true)}
                  className="shrink-0 rounded-md border px-2 py-1 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground"
                  disabled={watchPending}
                >
                  Choose…
                </button>
              </div>
              <Button
                type="submit"
                size="lg"
                disabled={!repoPath.trim() || watchPending}
                className="rounded-xl"
              >
                <HugeiconsIcon
                  icon={watchPending ? Loading03Icon : PlayIcon}
                  className={cn(watchPending && "animate-spin")}
                />
                {watchPending
                  ? "Connecting…"
                  : isWatching
                    ? "Monitor another"
                    : "Start monitoring"}
              </Button>
            </div>
            {watchError && (
              <InlineError
                error={watchError}
                onRetry={() => document.getElementById("repo-path")?.focus()}
              />
            )}
          </form>
        </section>

        {folderPickerOpen && (
          <FolderPicker
            initialPath={repoPath}
            onCancel={() => setFolderPickerOpen(false)}
            onSelect={(path) => {
              setRepoPath(path)
              setFolderPickerOpen(false)
            }}
          />
        )}

        {!watchInfo && !status?.watching ? (
          <EmptyState
            onDemo={() => void investigate("/api/investigate")}
            loading={investigating}
            error={investigationError}
          />
        ) : (
          <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_300px]">
            <LogPanel
              spans={status?.log_tail ?? []}
              statusError={statusError}
              onRetry={() => void pollStatus()}
            />
            <aside className="space-y-4">
              <MonitorCard
                status={status}
                watchInfo={watchInfo}
                stopPending={stopPending}
                onStop={() => void stopWatching()}
              />
              <div className="rounded-xl border bg-card p-4">
                <p className="text-sm font-semibold">Need an answer now?</p>
                <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">
                  Force an investigation of the current trace without waiting
                  for anomaly detection.
                </p>
                <Button
                  className="mt-4 w-full rounded-lg"
                  variant="outline"
                  onClick={() => void investigate("/api/investigate/now")}
                  disabled={investigating || manualUnavailable}
                  title={
                    manualUnavailable
                      ? "Manual override endpoint is not available on the backend yet"
                      : undefined
                  }
                >
                  <HugeiconsIcon
                    icon={investigating ? Loading03Icon : AiSearchIcon}
                    className={cn(investigating && "animate-spin")}
                  />
                  {manualUnavailable
                    ? "Backend not ready"
                    : investigating
                      ? "Investigating…"
                      : "Investigate now"}
                </Button>
                {investigationError && !manualUnavailable && (
                  <InlineError
                    error={investigationError}
                    onRetry={() => void investigate("/api/investigate/now")}
                  />
                )}
                {manualUnavailable && (
                  <p className="mt-3 text-center text-[11px] text-amber-700 dark:text-amber-400">
                    Manual override is coming soon.
                  </p>
                )}
              </div>
            </aside>
          </div>
        )}

        {investigating && <InvestigationLoading />}
        {report && (
          <div ref={reportRef} className="mt-8 scroll-mt-24">
            <InvestigationReport
              key={`${report.incident_summary}:${report.recommended_action}`}
              investigation={report}
            />
          </div>
        )}
      </main>
    </div>
  )
}

function FolderPicker({
  initialPath,
  onCancel,
  onSelect,
}: {
  initialPath: string
  onCancel: () => void
  onSelect: (path: string) => void
}) {
  const [listing, setListing] = useState<DirectoryListing | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const openFolder = useCallback(async (path?: string) => {
    setLoading(true)
    setError(null)
    try {
      const query = path ? `?path=${encodeURIComponent(path)}` : ""
      const response = await fetch(`/api/directories${query}`)
      const data = (await response.json()) as
        DirectoryListing | { error: string }
      if (!response.ok || "error" in data)
        throw new Error(
          "error" in data ? data.error : "Could not open this folder."
        )
      setListing(data)
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Could not open this folder."
      )
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    const query = initialPath ? `?path=${encodeURIComponent(initialPath)}` : ""
    void fetch(`/api/directories${query}`)
      .then(async (response) => {
        const data = (await response.json()) as
          DirectoryListing | { error: string }
        if (!response.ok || "error" in data)
          throw new Error(
            "error" in data ? data.error : "Could not open this folder."
          )
        if (!cancelled) setListing(data)
      })
      .catch((reason: unknown) => {
        if (!cancelled)
          setError(
            reason instanceof Error
              ? reason.message
              : "Could not open this folder."
          )
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [initialPath])

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-black/45 p-4"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onCancel()
      }}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="folder-picker-title"
        className="flex max-h-[70vh] w-full max-w-xl flex-col overflow-hidden rounded-2xl border bg-card shadow-2xl"
      >
        <div className="border-b p-5">
          <h2 id="folder-picker-title" className="font-semibold">
            Choose a repository folder
          </h2>
          <p
            className="mt-1 truncate font-mono text-xs text-muted-foreground"
            title={listing?.path}
          >
            {listing?.path ?? "Loading…"}
          </p>
        </div>
        <div className="min-h-56 flex-1 overflow-y-auto p-2">
          {loading ? (
            <div className="grid h-52 place-items-center">
              <HugeiconsIcon
                icon={Loading03Icon}
                className="animate-spin text-muted-foreground"
              />
            </div>
          ) : error ? (
            <div className="grid h-52 place-items-center px-6 text-center text-sm text-destructive">
              {error}
            </div>
          ) : (
            <div className="space-y-1">
              {listing && listing.parent !== listing.path && (
                <button
                  type="button"
                  onClick={() => void openFolder(listing.parent)}
                  className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm hover:bg-muted"
                >
                  <span className="font-mono text-muted-foreground">../</span>
                  <span>Parent folder</span>
                </button>
              )}
              {listing?.directories.map((name) => (
                <button
                  key={name}
                  type="button"
                  onClick={() => void openFolder(`${listing.path}/${name}`)}
                  className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm hover:bg-muted"
                >
                  <HugeiconsIcon
                    icon={FolderGitIcon}
                    className="size-4 text-muted-foreground"
                  />
                  <span className="truncate">{name}</span>
                </button>
              ))}
              {listing?.directories.length === 0 && (
                <p className="p-8 text-center text-sm text-muted-foreground">
                  No subfolders here.
                </p>
              )}
            </div>
          )}
        </div>
        <div className="flex items-center justify-end gap-2 border-t p-4">
          <Button type="button" variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
          <Button
            type="button"
            onClick={() => listing && onSelect(listing.path)}
            disabled={!listing || loading}
          >
            Choose this folder
          </Button>
        </div>
      </section>
    </div>
  )
}

function Header({ watching }: { watching: boolean }) {
  const { resolvedTheme, setTheme } = useTheme()
  const mounted = useSyncExternalStore(
    subscribeToNothing,
    () => true,
    () => false
  )
  const isDark = mounted && resolvedTheme === "dark"
  return (
    <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-3">
          <div className="grid size-8 place-items-center rounded-lg bg-foreground text-background">
            <HugeiconsIcon icon={Activity01Icon} className="size-4" />
          </div>
          <span className="text-lg font-semibold tracking-[-0.04em]">
            4sight
          </span>
          <span className="hidden rounded border px-1.5 py-0.5 font-mono text-[9px] text-muted-foreground sm:inline">
            LOCAL
          </span>
        </div>
        <div className="flex items-center gap-3">
          {watching && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span className="relative flex size-2">
                <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-400 opacity-60" />
                <span className="relative inline-flex size-2 rounded-full bg-emerald-500" />
              </span>
              Watching
            </div>
          )}
          <button
            type="button"
            onClick={() => setTheme(isDark ? "light" : "dark")}
            className="grid size-9 place-items-center rounded-full border bg-card text-muted-foreground hover:text-foreground"
            aria-label="Toggle color theme"
          >
            <HugeiconsIcon
              icon={isDark ? Sun03Icon : Moon02Icon}
              className="size-4"
            />
          </button>
        </div>
      </div>
    </header>
  )
}

function EmptyState({
  onDemo,
  loading,
  error,
}: {
  onDemo: () => void
  loading: boolean
  error: RequestError | null
}) {
  return (
    <section className="grid min-h-72 place-items-center rounded-2xl border border-dashed bg-muted/20 px-6 py-12 text-center">
      <div className="max-w-sm">
        <div className="mx-auto grid size-12 place-items-center rounded-xl border bg-card shadow-sm">
          <HugeiconsIcon
            icon={ComputerTerminal01Icon}
            className="size-5 text-muted-foreground"
          />
        </div>
        <h2 className="mt-4 font-semibold">Point 4sight at a repository</h2>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          Enter a local path above to begin watching agent execution logs.
          Nothing leaves your machine except configured model requests.
        </p>
        <Button
          variant="ghost"
          size="sm"
          className="mt-4"
          onClick={onDemo}
          disabled={loading}
        >
          {loading ? (
            <HugeiconsIcon icon={Loading03Icon} className="animate-spin" />
          ) : (
            <HugeiconsIcon icon={ArrowRight02Icon} />
          )}
          Run fixed test investigation
        </Button>
        {error && <InlineError error={error} onRetry={onDemo} />}
      </div>
    </section>
  )
}

function MonitorCard({
  status,
  watchInfo,
  stopPending,
  onStop,
}: {
  status: WatchStatus | null
  watchInfo: WatchResponse | null
  stopPending: boolean
  onStop: () => void
}) {
  const active = status?.watching ?? Boolean(watchInfo)
  return (
    <div className="rounded-xl border bg-card p-4">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold">Monitor</p>
        <span
          className={cn(
            "rounded-full px-2 py-1 text-[10px] font-semibold uppercase",
            active
              ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400"
              : "bg-muted text-muted-foreground"
          )}
        >
          {active ? "Watching" : "Stopped"}
        </span>
      </div>
      <div className="mt-4 space-y-3 text-xs">
        <div>
          <p className="text-muted-foreground">Repository</p>
          <p
            className="mt-1 truncate font-mono"
            title={status?.repo_path ?? watchInfo?.repo_path}
          >
            {status?.repo_path ?? watchInfo?.repo_path ?? "—"}
          </p>
        </div>
        {watchInfo?.log_path && (
          <div>
            <p className="text-muted-foreground">Log source</p>
            <p className="mt-1 truncate font-mono" title={watchInfo.log_path}>
              {watchInfo.log_path}
            </p>
          </div>
        )}
        {status?.baseline_run_id && (
          <div>
            <p className="text-muted-foreground">Baseline run</p>
            <p className="mt-1 truncate font-mono">{status.baseline_run_id}</p>
          </div>
        )}
      </div>
      {active && (
        <Button
          type="button"
          variant="outline"
          className="mt-4 w-full rounded-lg"
          onClick={onStop}
          disabled={stopPending}
        >
          <HugeiconsIcon
            icon={stopPending ? Loading03Icon : Alert02Icon}
            className={cn(stopPending && "animate-spin")}
          />
          {stopPending ? "Stopping…" : "End monitoring"}
        </Button>
      )}
    </div>
  )
}

function LogPanel({
  spans,
  statusError,
  onRetry,
}: {
  spans: LogSpan[]
  statusError: RequestError | null
  onRetry: () => void
}) {
  return (
    <section className="overflow-hidden rounded-xl border bg-[#101210] text-zinc-200 shadow-lg">
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
        <div className="flex items-center gap-2">
          <HugeiconsIcon
            icon={ComputerTerminal01Icon}
            className="size-4 text-zinc-400"
          />
          <p className="font-mono text-xs font-semibold">live trace</p>
        </div>
        <div className="flex items-center gap-2 font-mono text-[10px] text-zinc-500">
          <span className="size-1.5 animate-pulse rounded-full bg-emerald-400" />
          polling every 3s
        </div>
      </div>
      {statusError ? (
        <div className="grid h-72 place-items-center p-6 text-center">
          <div>
            <HugeiconsIcon
              icon={Alert02Icon}
              className="mx-auto size-6 text-amber-400"
            />
            <p className="mt-3 text-sm font-medium">
              {statusError.code === "BACKEND_NOT_READY"
                ? "Status backend not ready yet"
                : statusError.message}
            </p>
            <Button
              size="sm"
              variant="outline"
              className="mt-4 border-white/15 bg-transparent text-zinc-200 hover:bg-white/10"
              onClick={onRetry}
            >
              <HugeiconsIcon icon={RefreshIcon} />
              Retry
            </Button>
          </div>
        </div>
      ) : spans.length === 0 ? (
        <div className="grid h-72 place-items-center px-6 text-center">
          <div>
            <span className="mx-auto block size-2 animate-pulse rounded-full bg-emerald-400" />
            <p className="mt-4 text-sm text-zinc-300">
              Waiting for agent activity
            </p>
            <p className="mt-1.5 text-xs text-zinc-500">
              New reasoning, tool calls, and responses will stream in here.
            </p>
          </div>
        </div>
      ) : (
        <div className="max-h-[430px] overflow-y-auto p-2">
          {spans.map((span, index) => (
            <LogRow
              key={
                span.span_id ||
                `${span.run_id}:${span.type}:${span.timestamp}:${index}`
              }
              span={span}
              newRun={index === 0 || spans[index - 1]?.run_id !== span.run_id}
            />
          ))}
        </div>
      )}
    </section>
  )
}

function LogRow({ span, newRun }: { span: LogSpan; newRun: boolean }) {
  const failed = span.status === "error" || (span.status_code ?? 0) >= 500
  const preview =
    span.type === "tool_call"
      ? `${span.tool ?? "tool"}${span.content ? ` · ${span.content}` : ""}`
      : (span.content ?? "No content")
  const styles = {
    reasoning: "text-sky-400",
    tool_call: "text-amber-400",
    final_response: "text-emerald-400",
  }
  return (
    <>
      {newRun && (
        <div className="mt-2 flex items-center gap-2 px-2 py-1.5 first:mt-0">
          <span className="font-mono text-[9px] tracking-wider text-zinc-600 uppercase">
            run {shortId(span.run_id)}
          </span>
          <span className="h-px flex-1 bg-white/5" />
        </div>
      )}
      <div
        className={cn(
          "group grid grid-cols-[92px_minmax(0,1fr)_54px] gap-2 rounded-md px-2 py-2 font-mono text-[11px] hover:bg-white/5",
          failed && "bg-red-500/10 hover:bg-red-500/15"
        )}
      >
        <span
          className={cn(
            "truncate",
            failed ? "font-semibold text-red-400" : styles[span.type]
          )}
        >
          {span.type.replace("_", " ")}
        </span>
        <span
          className={cn("truncate", failed ? "text-red-300" : "text-zinc-300")}
          title={preview}
        >
          {preview}
        </span>
        <span className="text-right text-zinc-600">
          {relativeTime(span.timestamp)}
        </span>
      </div>
    </>
  )
}

function InvestigationLoading() {
  return (
    <div
      className="mt-8 flex items-center gap-4 rounded-xl border bg-card p-5"
      role="status"
    >
      <div className="relative grid size-10 shrink-0 place-items-center rounded-full bg-emerald-500/10">
        <HugeiconsIcon
          icon={AiSearchIcon}
          className="size-5 text-emerald-600 dark:text-emerald-400"
        />
        <span className="absolute inset-0 animate-ping rounded-full border border-emerald-500/30" />
      </div>
      <div>
        <p className="text-sm font-semibold">Investigation in progress</p>
        <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
          4sight is gathering and verifying evidence. Live model requests can
          take several minutes; this activity indicator will keep moving while
          the request is active.
        </p>
      </div>
      <HugeiconsIcon
        icon={Clock01Icon}
        className="ml-auto hidden size-5 text-muted-foreground sm:block"
      />
    </div>
  )
}

function InlineError({
  error,
  onRetry,
}: {
  error: RequestError
  onRetry: () => void
}) {
  return (
    <div className="mt-3 flex items-center gap-2 rounded-lg bg-destructive/8 px-3 py-2 text-xs text-destructive">
      <HugeiconsIcon icon={Alert02Icon} className="size-4 shrink-0" />
      <span className="flex-1">
        {error.code === "BACKEND_NOT_READY"
          ? "Backend endpoint not ready yet."
          : error.message}
      </span>
      <button
        type="button"
        onClick={onRetry}
        className="font-semibold underline underline-offset-2"
      >
        Retry
      </button>
    </div>
  )
}

function shortId(value: string) {
  return value.length > 12 ? `${value.slice(0, 8)}…` : value
}
function relativeTime(value: string) {
  const time = new Date(value).getTime()
  if (!Number.isFinite(time)) return "—"
  const seconds = Math.max(0, Math.floor((Date.now() - time) / 1000))
  if (seconds < 5) return "now"
  if (seconds < 60) return `${seconds}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`
  return `${Math.floor(seconds / 3600)}h`
}
function subscribeToNothing() {
  return () => undefined
}

function requestBrowserNotificationPermission() {
  if ("Notification" in window && Notification.permission === "default") {
    void Notification.requestPermission()
  }
}

function sendInvestigationNotification(reason: string | null) {
  if (!("Notification" in window) || Notification.permission !== "granted")
    return
  const notification = new Notification("4sight detected an issue", {
    body: reason
      ? `Investigation started: ${reason.replaceAll("_", " ")}`
      : "An automated investigation has started.",
    tag: "4sight-investigation-started",
  })
  notification.onclick = () => {
    window.focus()
    notification.close()
  }
}
