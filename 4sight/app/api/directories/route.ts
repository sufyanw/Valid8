import { readdir } from "node:fs/promises"
import { homedir } from "node:os"
import { dirname, resolve } from "node:path"

export async function GET(request: Request) {
  const requestedPath = new URL(request.url).searchParams.get("path")
  const path = resolve(requestedPath?.trim() || homedir())

  try {
    const entries = await readdir(path, { withFileTypes: true })
    const directories = entries
      .filter((entry) => entry.isDirectory() && !entry.name.startsWith("."))
      .map((entry) => entry.name)
      .sort((a, b) => a.localeCompare(b))

    return Response.json({ path, parent: dirname(path), directories })
  } catch {
    return Response.json(
      { error: "This folder cannot be opened." },
      { status: 400 }
    )
  }
}
