"use client";

import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import {
    Calendar,
    Users,
    DollarSign,
    Package,
    Plus,
    ArrowRight,
    Sparkles,
    Mail,
    Loader2,
    MessageSquare,
} from "lucide-react";
import { getUserEvents, getUserBookings, getSubscriptionStatus, api } from "@/lib/api";
import toast from "react-hot-toast";
import { UpgradeModal } from "@/components/upgrade-modal";

interface DashboardBooking {
    id: string;
    status: string;
    totalAmount?: number;
    amount?: number;
    vendorId?: string;
    vendor?: { id?: string; name?: string };
    service?: { name?: string };
    eventDate: string;
}

interface DashboardEvent {
    id: string;
    eventName?: string;
    eventType?: string;
    eventDate: string;
    location?: string;
    status: string;
}

const quickActions = [
    { label: "Create Event", href: "/create-event", icon: Plus, color: "bg-blue-600" },
    { label: "Find Vendors", href: "/marketplace", icon: Sparkles, color: "bg-purple-600" },
    { label: "View Bookings", href: "/bookings", icon: Package, color: "bg-green-600" },
    { label: "AI Planner", href: "/chat", icon: MessageSquare, color: "bg-indigo-600", alwaysEnabled: true },
];

export default function DashboardPage() {
    const { data: events, isLoading: eventsLoading } = useQuery({
        queryKey: ["events"],
        queryFn: () => getUserEvents(),
    });

    const { data: bookings, isLoading: bookingsLoading } = useQuery({
        queryKey: ["bookings"],
        queryFn: () => getUserBookings(),
    });

    const { data: subscription } = useQuery({
        queryKey: ["subscription"],
        queryFn: getSubscriptionStatus,
    });

    // Compute stats dynamically from API data
    const eventCount = events?.events?.length ?? 0;
    const eventLimitReached = subscription !== undefined && !subscription.is_pro_active && eventCount >= 3;
    const bookingCount = bookings?.bookings?.length ?? 0;
    const totalSpent = bookings?.bookings?.reduce(
        (sum: number, b: DashboardBooking) => sum + (b.totalAmount || b.amount || 0),
        0
    ) ?? 0;
    const vendorsContacted = bookings?.bookings
        ? new Set(bookings.bookings.map((b: DashboardBooking) => b.vendorId || b.vendor?.id).filter(Boolean)).size
        : 0;

    const stats = [
        { label: "My Events", value: String(eventCount), icon: Calendar, color: "bg-blue-100 text-blue-600" },
        { label: "Bookings", value: String(bookingCount), icon: Package, color: "bg-green-100 text-green-600" },
        { label: "Total Spent", value: `PKR ${totalSpent.toLocaleString()}`, icon: DollarSign, color: "bg-yellow-100 text-yellow-600" },
        { label: "Vendors Contacted", value: String(vendorsContacted), icon: Users, color: "bg-purple-100 text-purple-600" },
    ];

    const [showUpgradeModal, setShowUpgradeModal] = useState(false);

    // Email verification state
    const [emailVerified, setEmailVerified] = useState(true);
    const [resending, setResending] = useState(false);

    // Check email verification status from API
    useEffect(() => {
        api.get('/users/me')
            .then((res) => {
                const data = res.data?.data || res.data;
                if (data && data.emailVerified === false) {
                    setEmailVerified(false);
                }
            })
            .catch(() => {});
    }, []);

    const handleResendVerification = async () => {
        setResending(true);
        try {
            await api.post('/users/resend-verification');
            toast.success('Verification email sent! Check your inbox.');
        } catch {
            toast.error('Failed to send verification email. Try again later.');
        } finally {
            setResending(false);
        }
    };

    return (
        <>
        <div className="min-h-screen bg-gray-50">
            <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
                {/* Email Verification Banner */}
                {!emailVerified && (
                    <div className="mb-6 flex items-center justify-between rounded-2xl bg-amber-50 border border-amber-200 px-5 py-4">
                        <div className="flex items-center gap-3">
                            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-amber-100">
                                <Mail className="h-5 w-5 text-amber-600" />
                            </div>
                            <p className="text-sm text-amber-800">
                                <span className="font-semibold">Verify your email</span> to unlock all features and start booking vendors.
                            </p>
                        </div>
                        <button
                            onClick={handleResendVerification}
                            disabled={resending}
                            className="flex items-center gap-1.5 rounded-lg bg-amber-100 px-3 py-1.5 text-sm font-medium text-amber-700 hover:bg-amber-200 disabled:opacity-50 transition-colors"
                        >
                            {resending ? <Loader2 className="h-3 w-3 animate-spin" /> : <Mail className="h-3 w-3" />}
                            {resending ? 'Sending...' : 'Resend email'}
                        </button>
                    </div>
                )}

                {/* Header */}
                <div className="mb-8 flex items-center justify-between">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">My Dashboard</h1>
                        <p className="mt-1 text-gray-500">Manage your events, bookings, and vendor communications.</p>
                    </div>
                    {eventLimitReached ? (
                        <button
                            onClick={() => setShowUpgradeModal(true)}
                            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-[#1A3D64] to-[#2a5a8f] px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:from-[#122d4a] hover:to-[#1A3D64] transition-all duration-150 active:scale-[0.98]"
                        >
                            <Sparkles className="h-4 w-4" />
                            Upgrade to Pro
                        </button>
                    ) : (
                        <Link
                            href="/create-event"
                            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-700 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:from-indigo-700 hover:to-indigo-800 transition-all duration-150 active:scale-[0.98]"
                        >
                            <Plus className="h-4 w-4" />
                            New Event
                        </Link>
                    )}
                </div>

                {/* Quick Actions */}
                <div className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
                    {quickActions.map((action) => {
                        const isCreateEvent = action.label === "Create Event";
                        const locked = isCreateEvent && eventLimitReached;
                        const sharedClass = `group flex items-center gap-3 rounded-2xl px-5 py-5 text-white transition-all hover:opacity-90 hover:-translate-y-0.5 hover:shadow-lg active:scale-[0.98] ${locked ? "bg-[#1A3D64]" : action.color}`;
                        const inner = (
                            <>
                                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white/20">
                                    {locked ? <Sparkles className="h-5 w-5" /> : <action.icon className="h-5 w-5" />}
                                </div>
                                <span className="font-semibold text-sm leading-tight">{locked ? "Upgrade to Pro" : action.label}</span>
                                <ArrowRight className="ml-auto h-4 w-4 shrink-0 group-hover:translate-x-0.5 transition-transform" />
                            </>
                        );
                        return locked ? (
                            <button key={action.label} onClick={() => setShowUpgradeModal(true)} className={sharedClass}>
                                {inner}
                            </button>
                        ) : (
                            <Link key={action.label} href={action.href} className={sharedClass}>
                                {inner}
                            </Link>
                        );
                    })}
                </div>

                {/* Stats */}
                <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    {stats.map((stat) => (
                        <div
                            key={stat.label}
                            className="rounded-2xl bg-white border border-gray-100 p-6 shadow-sm hover:shadow-md transition-shadow duration-200"
                        >
                            <div className="flex items-center gap-4">
                                <div className={`flex h-12 w-12 items-center justify-center rounded-xl ${stat.color}`}>
                                    <stat.icon className="h-6 w-6" />
                                </div>
                                <div>
                                    <p className="text-sm text-gray-500">{stat.label}</p>
                                    <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>

                {/* AI Planner Banner */}
                <div className="mb-6 rounded-2xl bg-gradient-to-r from-indigo-600 to-indigo-700 p-6 flex flex-col sm:flex-row items-start sm:items-center gap-4">
                    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-white/20">
                        <MessageSquare className="h-6 w-6 text-white" />
                    </div>
                    <div className="flex-1">
                        <h3 className="font-semibold text-white">Not sure where to start?</h3>
                        <p className="text-indigo-200 text-sm mt-0.5">Tell our AI planner what you need — it&apos;ll suggest vendors, build timelines, and walk you through the whole process.</p>
                    </div>
                    <Link
                        href="/chat"
                        className="shrink-0 inline-flex items-center gap-2 rounded-xl bg-white px-5 py-2.5 text-sm font-semibold text-indigo-700 hover:bg-indigo-50 active:scale-[0.98] transition-all"
                    >
                        Chat with AI
                        <ArrowRight className="h-4 w-4" />
                    </Link>
                </div>

                {/* Two-column layout */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Recent Events */}
                    <div className="rounded-2xl bg-white border border-gray-100 shadow-sm overflow-hidden">
                        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
                            <h2 className="text-lg font-semibold text-gray-900">My Events</h2>
                            <Link href="/dashboard" className="text-sm font-medium text-indigo-600 hover:text-indigo-700">
                                View all →
                            </Link>
                        </div>
                        <div className="p-6">
                            {eventsLoading ? (
                                <div className="space-y-3">
                                    {[...Array(3)].map((_, i) => (
                                        <div key={i} className="flex items-center justify-between rounded-xl border border-gray-100 p-4">
                                            <div className="space-y-2">
                                                <div className="h-4 w-40 animate-pulse rounded-full bg-gray-200" />
                                                <div className="h-3 w-28 animate-pulse rounded-full bg-gray-200" />
                                            </div>
                                            <div className="h-6 w-16 animate-pulse rounded-full bg-gray-200" />
                                        </div>
                                    ))}
                                </div>
                            ) : events?.events?.length ? (
                                <div className="space-y-3">
                                    {events.events.slice(0, 3).map((event: DashboardEvent) => (
                                        <div key={event.id} className="flex items-center justify-between rounded-xl border border-gray-100 p-4 hover:bg-gray-50 transition-colors">
                                            <div>
                                                <h3 className="font-medium text-gray-900">{event.eventName || event.eventType}</h3>
                                                <p className="text-sm text-gray-500 mt-0.5">
                                                    {new Date(event.eventDate).toLocaleDateString('en-PK', { month: 'short', day: 'numeric', year: 'numeric' })}
                                                    {event.location && ` • ${event.location}`}
                                                </p>
                                            </div>
                                            <span className={`rounded-full px-3 py-1 text-xs font-semibold ${
                                                event.status === "confirmed" ? "bg-green-100 text-green-700"
                                                : event.status === "planning" ? "bg-indigo-100 text-indigo-700"
                                                : "bg-gray-100 text-gray-600"
                                            }`}>
                                                {event.status}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="flex flex-col items-center justify-center py-10 text-center">
                                    <div className="rounded-full bg-gray-100 p-4 mb-4">
                                        <Calendar className="h-7 w-7 text-gray-400" />
                                    </div>
                                    <p className="text-gray-500 mb-4">No events yet</p>
                                    <Link href="/create-event" className="inline-flex items-center gap-2 text-sm font-medium text-indigo-600 hover:text-indigo-700">
                                        <Plus className="h-4 w-4" />
                                        Create your first event
                                    </Link>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Recent Bookings */}
                    <div className="rounded-2xl bg-white border border-gray-100 shadow-sm overflow-hidden">
                        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
                            <h2 className="text-lg font-semibold text-gray-900">Recent Bookings</h2>
                            <Link href="/bookings" className="text-sm font-medium text-indigo-600 hover:text-indigo-700">
                                View all →
                            </Link>
                        </div>
                        <div className="p-6">
                            {bookingsLoading ? (
                                <div className="space-y-3">
                                    {[...Array(3)].map((_, i) => (
                                        <div key={i} className="flex items-center justify-between rounded-xl border border-gray-100 p-4">
                                            <div className="space-y-2">
                                                <div className="h-4 w-36 animate-pulse rounded-full bg-gray-200" />
                                                <div className="h-3 w-24 animate-pulse rounded-full bg-gray-200" />
                                            </div>
                                            <div className="h-6 w-16 animate-pulse rounded-full bg-gray-200" />
                                        </div>
                                    ))}
                                </div>
                            ) : bookings?.bookings?.length ? (
                                <div className="space-y-3">
                                    {bookings.bookings.slice(0, 3).map((booking: DashboardBooking) => (
                                        <div key={booking.id} className="flex items-center justify-between rounded-xl border border-gray-100 p-4 hover:bg-gray-50 transition-colors">
                                            <div>
                                                <h3 className="font-medium text-gray-900">{booking.service?.name || 'Service'}</h3>
                                                <p className="text-sm text-gray-500 mt-0.5">
                                                    {booking.vendor?.name} • {new Date(booking.eventDate).toLocaleDateString('en-PK', { month: 'short', day: 'numeric' })}
                                                </p>
                                            </div>
                                            <span className={`rounded-full px-3 py-1 text-xs font-semibold ${
                                                booking.status === "confirmed" ? "bg-green-100 text-green-700"
                                                : booking.status === "pending" ? "bg-amber-100 text-amber-700"
                                                : booking.status === "cancelled" ? "bg-red-100 text-red-700"
                                                : "bg-gray-100 text-gray-600"
                                            }`}>
                                                {booking.status}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="flex flex-col items-center justify-center py-10 text-center">
                                    <div className="rounded-full bg-gray-100 p-4 mb-4">
                                        <Package className="h-7 w-7 text-gray-400" />
                                    </div>
                                    <p className="text-gray-500 mb-4">No bookings yet</p>
                                    <Link href="/marketplace" className="inline-flex items-center gap-2 text-sm font-medium text-indigo-600 hover:text-indigo-700">
                                        <Sparkles className="h-4 w-4" />
                                        Browse vendors
                                    </Link>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
        {showUpgradeModal && <UpgradeModal onClose={() => setShowUpgradeModal(false)} />}
        </>
    );
}
