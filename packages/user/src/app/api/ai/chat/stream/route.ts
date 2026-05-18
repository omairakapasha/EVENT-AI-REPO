import { NextRequest } from "next/server";
import { cookies } from "next/headers";

export const runtime = "edge";

const AI_SERVICE_URL = process.env.AI_SERVICE_URL || process.env.AGENT_SERVICE_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  // Read access_token from httpOnly cookie (set by backend on login)
  const cookieStore = await cookies();
  const accessToken = cookieStore.get("access_token")?.value || "";

  // Prefer cookie-based token; fall back to any Authorization header from client
  const authHeader = accessToken
    ? `Bearer ${accessToken}`
    : req.headers.get("authorization") ?? "";

  const body = await req.text();

  try {
    const upstream = await fetch(`${AI_SERVICE_URL}/api/v1/ai/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": authHeader,
        "X-API-Key": process.env.AI_SERVICE_API_KEY ?? "",
      },
      body,
    });

    if (!upstream.ok) {
      return new Response(
        JSON.stringify({ error: "AI service unavailable" }),
        { status: upstream.status, headers: { "Content-Type": "application/json" } }
      );
    }

    // Pass through the SSE stream directly
    return new Response(upstream.body, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
      },
    });
  } catch {
    return new Response(
      JSON.stringify({ error: "Failed to connect to AI service" }),
      { status: 503, headers: { "Content-Type": "application/json" } }
    );
  }
}

