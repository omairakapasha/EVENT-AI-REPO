import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "Services | Event-AI Vendor Portal",
    description: "Create, manage, and organize your event services including catering, photography, decoration, and more.",
};

export default function ServicesLayout({ children }: { children: React.ReactNode }) {
    return children;
}
