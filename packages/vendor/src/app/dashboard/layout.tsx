import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "Dashboard | Event-AI Vendor Portal",
    description: "Manage your vendor dashboard, view bookings, services, and performance metrics on Event-AI.",
};

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
    return children;
}
