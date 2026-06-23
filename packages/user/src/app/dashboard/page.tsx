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
    Mail,
    Loader2,
    MessageSquare,
    Sparkles,
    ChevronRight,
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

const STATUS_COLORS: Record<string, string> = {
    draft: 'bg-surface-100 text-surface-700 dark:bg-surface-800 dark:text-surface-300',
    planned: 'bg-primary-100 text-primary-700 dark:bg-primary-900 dark:text-primary-300',
    active: 'bg-accent-100 text-accent-700 dark:bg-accent-900 dark:text-accent-300',
    completed: 'bg-success-100 text-success-700 dark:bg-success-900 dark:text-success-300',
    canceled: 'bg-error-100 text-error-700 dark:bg-error-900 dark:text-error-300',
    pending: 'bg-warning-100 text-warning-700 dark:bg-warning-900 dark:text-warning-300',
    confirmed: 'bg-primary-100 text-primary-700 dark:bg-primary-900 dark:text-primary-300',
};

function Skeleton({ className = '' }: { className?: string }) {
    return <div className={`animate-pulse rounded-lg bg-surface-200 dark:bg-surface-700 ${className}`} />;
}

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
        { label: "My Events", value: String(eventCount), icon: Calendar },
        { label: "Bookings", value: String(bookingCount), icon: Package },
        { label: "Total Spent", value: `PKR ${totalSpent.toLocaleString()}`, icon: DollarSign },
        { label: "Vendors Contacted", value: String(vendorsContacted), icon: Users },
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
        <div className="space-y-8">
            {/* Email Verification Banner */}
            {!emailVerified && (
                <div className="flex items-center justify-between rounded-xl border border-warning-200 bg-warning-50 px-5 py-4 dark:border-warning-800 dark:bg-warning-900/20">
                    <div className="flex items-center gap-3">
                        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-warning-100 dark:bg-warning-900/50">
                            <Mail className="h-5 w-5 text-warning-600 dark:text-warning-400" />
                        </div>
                        <p className="text-sm text-warning-800 dark:text-warning-200">
                            <span className="font-semibold">Verify your email</span> to unlock all features and start booking vendors.
                        </p>
                    </div>
                    <button
                        onClick={handleResendVerification}
                        disabled={resending}
                        className="flex items-center gap-1.5 rounded-lg bg-warning-100 px-3 py-1.5 text-sm font-medium text-warning-700 hover:bg-warning-200 disabled:opacity-50 transition-colors dark:bg-warning-900/50 dark:text-warning-300 dark:hover:bg-warning-900"
                    >
                        {resending ? <Loader2 className="h-3 w-3 animate-spin" /> : <Mail className="h-3 w-3" />}
                        {resending ? 'Sending...' : 'Resend email'}
                    </button>
                </div>
            )}

            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-50">My Dashboard</h1>
                    <p className="mt-1 text-surface-500">Manage your events, bookings, and vendor communications</p>
                </div>
                {eventLimitReached ? (
                    <button
                        onClick={() => setShowUpgradeModal(true)}
                        className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-primary-700 transition-colors shadow-sm"
                    >
                        <Sparkles className="h-4 w-4" />
                        Upgrade to Pro
                    </button>
                ) : (
                    <Link
                        href="/create-event"
                        className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-primary-700 transition-colors shadow-sm"
                    >
                        <Plus className="h-4 w-4" />
                        New Event
                    </Link>
                )}
            </div>

            {/* Stat cards */}
            <div className="grid grid-cols-2 gap-6 lg:grid-cols-4">
                {stats.map((stat) => (
                    <div key={stat.label} className="rounded-xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-900">
                        <div className="flex items-center gap-3">
                            <div className="rounded-lg bg-primary-50 p-2.5 dark:bg-primary-900/20">
                                <stat.icon className="h-5 w-5 text-primary-600 dark:text-primary-400" />
                            </div>
                        </div>
                        <div className="mt-4">
                            <p className="text-2xl font-bold text-surface-900 dark:text-surface-50">{stat.value}</p>
                            <p className="text-sm text-surface-500">{stat.label}</p>
                        </div>
                    </div>
                ))}
            </div>

            {/* AI Planner Banner */}
            <div className="rounded-xl border border-primary-200 bg-gradient-to-r from-primary-50 to-accent-50 p-6 flex flex-col sm:flex-row items-start sm:items-center gap-4 dark:from-primary-900/20 dark:to-accent-900/20 dark:border-primary-800">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-primary-100 dark:bg-primary-900/50">
                    <MessageSquare className="h-6 w-6 text-primary-600 dark:text-primary-400" />
                </div>
                <div className="flex-1">
                    <h3 className="font-semibold text-surface-900 dark:text-surface-50">Not sure where to start?</h3>
                    <p className="text-surface-600 text-sm mt-0.5 dark:text-surface-400">Tell our AI planner what you need — it'll suggest vendors, build timelines, and walk you through the whole process.</p>
                </div>
                <Link
                    href="/chat"
                    className="shrink-0 inline-flex items-center gap-2 rounded-lg bg-primary-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-primary-700 transition-colors"
                >
                    Chat with AI
                    <ChevronRight className="h-4 w-4" />
                </Link>
            </div>

            {/* Two-column layout */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Recent Events */}
                <div className="rounded-xl border border-surface-200 bg-white dark:border-surface-800 dark:bg-surface-900">
                    <div className="flex items-center justify-between border-b border-surface-200 px-6 py-4 dark:border-surface-800">
                        <h2 className="text-lg font-semibold text-surface-900 dark:text-surface-50">My Events</h2>
                        <Link href="/dashboard" className="flex items-center text-sm text-primary-600 hover:underline dark:text-primary-400">
                            View all <ChevronRight className="ml-1 h-4 w-4" />
                        </Link>
                    </div>
                    <div className="p-6">
                        {eventsLoading ? (
                            <div className="space-y-3">
                                {[...Array(3)].map((_, i) => (
                                    <div key={i} className="flex items-center justify-between rounded-lg border border-surface-100 p-4 dark:border-surface-800">
                                        <div className="space-y-2">
                                            <Skeleton className="h-4 w-40" />
                                            <Skeleton className="h-3 w-28" />
                                        </div>
                                        <Skeleton className="h-6 w-16 rounded-full" />
                                    </div>
                                ))}
                            </div>
                        ) : events?.events?.length ? (
                            <div className="space-y-3">
                                {events.events.slice(0, 3).map((event: DashboardEvent) => (
                                    <div key={event.id} className="flex items-center justify-between rounded-lg border border-surface-100 p-4 hover:bg-surface-50 transition-colors dark:border-surface-800 dark:hover:bg-surface-900/50">
                                        <div>
                                            <h3 className="font-medium text-surface-900 dark:text-surface-50">{event.eventName || event.eventType}</h3>
                                            <p className="text-sm text-surface-500 mt-0.5">
                                                {new Date(event.eventDate).toLocaleDateString('en-PK', { month: 'short', day: 'numeric', year: 'numeric' })}
                                                {event.location && ` • ${event.location}`}
                                            </p>
                                        </div>
                                        <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLORS[event.status] || 'bg-surface-100 text-surface-700'}`}>
                                            {event.status}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="flex flex-col items-center justify-center py-10 text-center">
                                <div className="rounded-full bg-surface-100 p-4 mb-4 dark:bg-surface-800">
                                    <Calendar className="h-7 w-7 text-surface-400 dark:text-surface-600" />
                                </div>
                                <p className="text-surface-500 mb-4">No events yet</p>
                                <Link href="/create-event" className="inline-flex items-center gap-2 text-sm font-medium text-primary-600 hover:underline dark:text-primary-400">
                                    <Plus className="h-4 w-4" />
                                    Create your first event
                                </Link>
                            </div>
                        )}
                    </div>
                </div>

                {/* Recent Bookings */}
                <div className="rounded-xl border border-surface-200 bg-white dark:border-surface-800 dark:bg-surface-900">
                    <div className="flex items-center justify-between border-b border-surface-200 px-6 py-4 dark:border-surface-800">
                        <h2 className="text-lg font-semibold text-surface-900 dark:text-surface-50">Recent Bookings</h2>
                        <Link href="/bookings" className="flex items-center text-sm text-primary-600 hover:underline dark:text-primary-400">
                            View all <ChevronRight className="ml-1 h-4 w-4" />
                        </Link>
                    </div>
                    <div className="p-6">
                        {bookingsLoading ? (
                            <div className="space-y-3">
                                {[...Array(3)].map((_, i) => (
                                    <div key={i} className="flex items-center justify-between rounded-lg border border-surface-100 p-4 dark:border-surface-800">
                                        <div className="space-y-2">
                                            <Skeleton className="h-4 w-36" />
                                            <Skeleton className="h-3 w-24" />
                                        </div>
                                        <Skeleton className="h-6 w-16 rounded-full" />
                                    </div>
                                ))}
                            </div>
                        ) : bookings?.bookings?.length ? (
                            <div className="space-y-3">
                                {bookings.bookings.slice(0, 3).map((booking: DashboardBooking) => (
                                    <div key={booking.id} className="flex items-center justify-between rounded-lg border border-surface-100 p-4 hover:bg-surface-50 transition-colors dark:border-surface-800 dark:hover:bg-surface-900/50">
                                        <div>
                                            <h3 className="font-medium text-surface-900 dark:text-surface-50">{booking.service?.name || 'Service'}</h3>
                                            <p className="text-sm text-surface-500 mt-0.5">
                                                {booking.vendor?.name} • {new Date(booking.eventDate).toLocaleDateString('en-PK', { month: 'short', day: 'numeric' })}
                                            </p>
                                        </div>
                                        <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLORS[booking.status] || 'bg-surface-100 text-surface-700'}`}>
                                            {booking.status}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="flex flex-col items-center justify-center py-10 text-center">
                                <div className="rounded-full bg-surface-100 p-4 mb-4 dark:bg-surface-800">
                                    <Package className="h-7 w-7 text-surface-400 dark:text-surface-600" />
                                </div>
                                <p className="text-surface-500 mb-4">No bookings yet</p>
                                <Link href="/marketplace" className="inline-flex items-center gap-2 text-sm font-medium text-primary-600 hover:underline dark:text-primary-400">
                                    <Sparkles className="h-4 w-4" />
                                    Browse vendors
                                </Link>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
        {showUpgradeModal && <UpgradeModal onClose={() => setShowUpgradeModal(false)} />}
        </>
    );
}
