import { proxyBackend } from "@/lib/backend"
import type { ApiError } from "@/lib/types"

export async function POST(request: Request) {
  let repoPath: unknown
  try {
    repoPath = ((await request.json()) as { repo_path?: unknown }).repo_path
  } catch {
    repoPath = null
  }

  if (typeof repoPath !== "string" || !repoPath.trim()) {
    return Response.json(
      {
        error: "Enter a repository path.",
        code: "INVALID_REQUEST",
      } satisfies ApiError,
      { status: 400 }
    )
  }

  return proxyBackend("/watch", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo_path: repoPath.trim() }),
  })
}

export async function DELETE() {
  return proxyBackend("/watch", { method: "DELETE" })
}
