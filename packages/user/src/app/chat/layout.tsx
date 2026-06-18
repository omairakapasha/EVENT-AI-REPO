import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "AI Event Assistant | Event-AI",
    description: "Chat with our AI assistant to plan events, find vendors, and get personalized recommendations for your celebration.",
};

export default function ChatLayout({ children }: { children: React.ReactNode }) {
    return children;
}
