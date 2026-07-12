import { proxyBackend } from "@/lib/backend"

export async function POST() {
  return proxyBackend("/investigate/now", { method: "POST" })
}
