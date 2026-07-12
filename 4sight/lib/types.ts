export type InvestigationMode = "live" | "stub"
export type EvidenceSource = "trace_a" | "trace_b" | "deploy_diff"

export interface Evidence {
  source: EvidenceSource
  excerpt: string
}

export interface Hypothesis {
  rank: number
  claim: string
  confidence: number
  evidence: Evidence[]
}

export interface Investigation {
  mode: InvestigationMode
  incident_summary: string
  recommended_action: string
  dropped_hypotheses: number
  hypotheses: Hypothesis[]
}

export interface TriggeredInvestigation extends Investigation {
  triggered_run_id: string
  triggered_at: string
}

export interface WatchResponse {
  status: "watching"
  repo_path: string
  log_path: string
}

export type SpanType = "reasoning" | "tool_call" | "final_response"

export interface LogSpan {
  run_id: string
  span_id: string
  type: SpanType
  content: string | null
  tool: string | null
  timestamp: string
  status?: string | null
  status_code?: number | null
  error_type?: string | null
}

export interface WatchStatus {
  watching: boolean
  repo_path: string | null
  log_tail: LogSpan[]
  known_tools: string[]
  baseline_run_id: string | null
  latest_investigation: TriggeredInvestigation | null
  active_investigation: {
    triggered_run_id: string
    triggered_at: string
    anomaly_reason: string | null
  } | null
}

export interface ApiError {
  error: string
  code:
    | "BACKEND_NOT_READY"
    | "BACKEND_UNAVAILABLE"
    | "BACKEND_ERROR"
    | "INVALID_REQUEST"
  backend_status?: number
}
