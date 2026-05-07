import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "Bookings | Event-AI Vendor Portal",
    description: "View and manage event bookings, track booking status, and respond to client requests.",
};

export default function BookingsLayout({ children }: { children: React.ReactNode }) {
    return children;
}
