const AGENT_API_URL = (
  process.env.MOCK_AGENT_API_URL ?? "http://localhost:8001"
).replace(/\/$/, "")

export async function PUT(request: Request) {
  try {
    const response = await fetch(`${AGENT_API_URL}/api/feature-flags`, {
      method: "PUT",
      cache: "no-store",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: await request.text(),
    })
    const body = await response.text()

    if (!response.ok) {
      return Response.json(
        { error: `The monitored app rejected the fix (${response.status}).` },
        { status: response.status }
      )
    }

    return new Response(body, {
      status: response.status,
      headers: {
        "Content-Type":
          response.headers.get("content-type") ?? "application/json",
      },
    })
  } catch {
    return Response.json(
      {
        error:
          "Could not reach the monitored app. Make sure mockAgent is running on port 8001.",
      },
      { status: 503 }
    )
  }
}
