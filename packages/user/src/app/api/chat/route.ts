import { NextRequest, NextResponse } from "next/server";

// Agent service URL (Python FastAPI)
const AGENT_SERVICE_URL = process.env.AGENT_SERVICE_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
    try {
        const body = await request.json();
        const { message, sessionId } = body;

        if (!message) {
            return NextResponse.json(
                { error: "Message is required" },
                { status: 400 }
            );
        }

        // Try the Python agent service first
        try {
            const agentResponse = await fetch(`${AGENT_SERVICE_URL}/api/chat`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-API-Key": process.env.AI_SERVICE_API_KEY || ""
                },
                body: JSON.stringify({
                    message,
                    session_id: sessionId || undefined,
                }),
                signal: AbortSignal.timeout(30000), // 30s timeout
            });

            if (agentResponse.ok) {
                const data = await agentResponse.json();
                return NextResponse.json({
                    response: data.response || data.result,
                    agent: data.agent || "AI Assistant",
                    sessionId: data.session_id,
                });
            }
        } catch {
            console.log("Agent service not available, using Gemini fallback");
        }

        // Fallback: Use Google Gemini API directly
        const geminiApiKey = process.env.GEMINI_API_KEY;
        if (!geminiApiKey) {
            return NextResponse.json({
                response:
                    `Welcome to **Event-AI**! 🎉\n\n` +
                    `I received your message: "${message}"\n\n` +
                    `I'm currently running in **demo mode**. To get full AI capabilities:\n` +
                    `- Start the agent service: \`cd packages/agentic_event_orchestrator && python server.py\`\n` +
                    `- Or set \`GEMINI_API_KEY\` in your environment\n\n` +
                    `Here's what I can help with when fully connected:\n` +
                    `• 📋 Plan Events — Create weddings, birthdays, corporate events\n` +
                    `• 🔍 Find Vendors — Search top-rated vendors in Pakistan\n` +
                    `• 📅 Book Services — Reserve vendors for your event\n` +
                    `• 📊 Track Bookings — View and manage bookings`,
                agent: "Demo Mode",
                sessionId: sessionId || crypto.randomUUID(),
            });
        }

        // Call Gemini API as fallback
        const geminiResponse = await fetch(
            `https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key=${geminiApiKey}`,
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    contents: [
                        {
                            role: "user",
                            parts: [
                                {
                                    text: `You are Event-AI, an intelligent event planning assistant for Pakistan. Help users plan events, find vendors, and book services. Be friendly and use markdown formatting with emojis.

User message: ${message}`,
                                },
                            ],
                        },
                    ],
                }),
            }
        );

        if (!geminiResponse.ok) {
            throw new Error("Gemini API error");
        }

        const geminiData = await geminiResponse.json();
        const responseText =
            geminiData.candidates?.[0]?.content?.parts?.[0]?.text ||
            "I apologize, I couldn't generate a response. Please try again.";

        return NextResponse.json({
            response: responseText,
            agent: "Gemini AI",
            sessionId: sessionId || crypto.randomUUID(),
        });
    } catch (error) {
        console.error("Chat API error:", error);
        return NextResponse.json(
            { error: "Internal server error" },
            { status: 500 }
        );
    }
}
