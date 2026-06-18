import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "Vendor Marketplace | Event-AI",
    description: "Browse and discover top-rated event vendors worldwide. Find catering, photography, decoration, venues, and more for your next event.",
};

export default function MarketplaceLayout({ children }: { children: React.ReactNode }) {
    return children;
}
