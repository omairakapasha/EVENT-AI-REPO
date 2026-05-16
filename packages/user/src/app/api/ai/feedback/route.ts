import { NextRequest } from "next/server";

const AI_SERVICE_URL = process.env.AI_SERVICE_URL || process.env.AGENT_SERVICE_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  const token = req.headers.get("authorization") ?? "";
  const body = await req.json();

  try {
    const upstream = await fetch(`${AI_SERVICE_URL}/api/v1/ai/feedback`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": token,
        "X-API-Key": process.env.AI_SERVICE_API_KEY ?? "",
      },
      body: JSON.stringify(body),
    });

    if (!upstream.ok) {
      return new Response(
        JSON.stringify({ error: "Failed to send feedback to AI service" }),
        { status: upstream.status, headers: { "Content-Type": "application/json" } }
      );
    }

    return new Response(JSON.stringify({ success: true }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  } catch {
    return new Response(
      JSON.stringify({ error: "Failed to connect to AI service" }),
      { status: 503, headers: { "Content-Type": "application/json" } }
    );
  }
}
