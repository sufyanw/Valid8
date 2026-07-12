import "server-only"

import type { ApiError } from "@/lib/types"

const API_URL = (process.env.PYTHON_API_URL ?? "http://localhost:8000").replace(/\/$/, "")

export async function proxyBackend(path: string, init?: RequestInit) {
  try {
    const response = await fetch(`${API_URL}${path}`, {
      ...init,
      cache: "no-store",
      headers: {
        Accept: "application/json",
        ...init?.headers,
      },
    })

    if (response.status === 404) {
      return Response.json(
        {
          error: "This backend endpoint is not available yet.",
          code: "BACKEND_NOT_READY",
          backend_status: 404,
        } satisfies ApiError,
        { status: 503 },
      )
    }

    const body = await response.text()
    if (!response.ok) {
      return Response.json(
        {
          error: readBackendMessage(body) ?? `Backend request failed (${response.status}).`,
          code: "BACKEND_ERROR",
          backend_status: response.status,
        } satisfies ApiError,
        { status: response.status },
      )
    }

    return new Response(body, {
      status: response.status,
      headers: { "Content-Type": response.headers.get("content-type") ?? "application/json" },
    })
  } catch {
    return Response.json(
      {
        error: "Cannot reach the local investigation backend.",
        code: "BACKEND_UNAVAILABLE",
      } satisfies ApiError,
      { status: 503 },
    )
  }
}

function readBackendMessage(body: string) {
  try {
    const parsed = JSON.parse(body) as { detail?: unknown; error?: unknown }
    const message = parsed.detail ?? parsed.error
    return typeof message === "string" ? message : null
  } catch {
    return body.trim() || null
  }
}
