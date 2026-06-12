'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import {
    Calendar, Package, Clock, CheckCircle, XCircle, Receipt,
    ArrowRight, MessageCircleQuestion, CreditCard, Loader2, Ban,
} from 'lucide-react';
import { getUserBookings, cancelBooking } from '@/lib/api';
import toast from 'react-hot-toast';
import { isAxiosError } from 'axios';

interface BookingItem {
    id: string;
    status: string;
    notes?: string;
    service?: { name?: string };
    serviceName?: string;
    vendor?: { name?: string };
    vendorName?: string;
    event_date?: string;
    eventDate?: string;
    guest_count?: number;
    guestCount?: number;
    total_price?: number;
    totalAmount?: number;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const statusConfig: Record<string, { color: string; icon: any; label: string }> = {
    pending: { color: 'bg-yellow-100 text-yellow-800', icon: Clock, label: 'Pending' },
    quoted: { color: 'bg-amber-100 text-amber-800', icon: Receipt, label: 'Quote Received' },
    negotiating: { color: 'bg-orange-100 text-orange-800', icon: MessageCircleQuestion, label: 'Negotiating' },
    accepted: { color: 'bg-teal-100 text-teal-800', icon: CheckCircle, label: 'Accepted' },
    awaiting_deposit: { color: 'bg-cyan-100 text-cyan-800', icon: CreditCard, label: 'Awaiting Deposit' },
    confirmed: { color: 'bg-green-100 text-green-800', icon: CheckCircle, label: 'Confirmed' },
    in_progress: { color: 'bg-indigo-100 text-indigo-800', icon: Clock, label: 'In Progress' },
    no_show: { color: 'bg-gray-100 text-gray-500', icon: XCircle, label: 'No Show' },
    cancelled: { color: 'bg-red-100 text-red-800', icon: XCircle, label: 'Cancelled' },
    completed: { color: 'bg-blue-100 text-blue-800', icon: CheckCircle, label: 'Completed' },
    rejected: { color: 'bg-red-100 text-red-800', icon: XCircle, label: 'Rejected' },
};

// Statuses the user is allowed to cancel (mirrors backend _CANCELLABLE_STATUSES)
const CANCELLABLE_STATUSES = new Set([
    'pending', 'quoted', 'negotiating', 'accepted', 'awaiting_deposit', 'confirmed',
]);

const QUOTE_STATUSES = new Set(['quoted', 'negotiating']);

// ── Cancel confirmation dialog ────────────────────────────────────────────────

function CancelDialog({
    booking,
    onClose,
    onConfirm,
    isPending,
}: {
    booking: BookingItem;
    onClose: () => void;
    onConfirm: (reason: string) => void;
    isPending: boolean;
}) {
    const [reason, setReason] = useState('');

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
            <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
                <h3 className="text-lg font-semibold text-gray-900">Cancel Booking</h3>
                <p className="mt-1 text-sm text-gray-500">
                    Cancel your booking for{' '}
                    <span className="font-medium text-gray-700">
                        {booking.service?.name || booking.serviceName || 'this service'}
                    </span>
                    {' '}with{' '}
                    <span className="font-medium text-gray-700">
                        {booking.vendor?.name || booking.vendorName || 'the vendor'}
                    </span>
                    ? This cannot be undone.
                </p>
                <div className="mt-4">
                    <label className="block text-xs font-medium uppercase tracking-wide text-gray-500 mb-1">
                        Reason (optional)
                    </label>
                    <textarea
                        value={reason}
                        onChange={(e) => setReason(e.target.value)}
                        rows={3}
                        placeholder="Let the vendor know why you're cancelling…"
                        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-red-400 focus:outline-none focus:ring-1 focus:ring-red-400 resize-none"
                    />
                </div>
                <div className="mt-5 flex justify-end gap-2">
                    <button
                        onClick={onClose}
                        disabled={isPending}
                        className="rounded-lg border border-gray-300 px-4 py-2 text-sm hover:bg-gray-50 disabled:opacity-50"
                    >
                        Keep Booking
                    </button>
                    <button
                        onClick={() => onConfirm(reason.trim())}
                        disabled={isPending}
                        className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
                    >
                        {isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                        Cancel Booking
                    </button>
                </div>
            </div>
        </div>
    );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function BookingsPage() {
    const qc = useQueryClient();
    const [cancelTarget, setCancelTarget] = useState<BookingItem | null>(null);

    const { data, isLoading } = useQuery({
        queryKey: ['bookings'],
        queryFn: () => getUserBookings(),
    });

    const cancel = useMutation({
        mutationFn: ({ id, reason }: { id: string; reason: string }) =>
            cancelBooking(id, reason || undefined),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['bookings'] });
            toast.success('Booking cancelled');
            setCancelTarget(null);
        },
        onError: (err) => {
            const data = isAxiosError(err) ? err.response?.data : undefined;
            const msg =
                data?.error?.message || data?.message || 'Failed to cancel booking';
            toast.error(msg);
        },
    });

    const bookings = data?.bookings || data?.data || [];

    if (isLoading) {
        return (
            <div className="max-w-4xl mx-auto px-4 py-8 space-y-4">
                <div className="h-8 w-48 animate-pulse rounded bg-gray-200" />
                {[...Array(4)].map((_, i) => (
                    <div key={i} className="bg-white rounded-lg shadow-sm p-6 space-y-3">
                        <div className="h-5 w-2/3 animate-pulse rounded bg-gray-200" />
                        <div className="h-4 w-1/3 animate-pulse rounded bg-gray-200" />
                        <div className="flex gap-3">
                            <div className="h-6 w-20 animate-pulse rounded-full bg-gray-200" />
                            <div className="h-6 w-24 animate-pulse rounded bg-gray-200" />
                        </div>
                    </div>
                ))}
            </div>
        );
    }

    return (
        <div className="max-w-4xl mx-auto px-4 py-8">
            <div className="mb-8">
                <h1 className="text-2xl font-bold text-gray-900">My Bookings</h1>
                <p className="mt-1 text-gray-500">Track and manage your event service bookings.</p>
            </div>

            {bookings.length === 0 ? (
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-12 text-center">
                    <Package className="h-12 w-12 text-gray-300 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">No bookings yet</h3>
                    <p className="text-gray-500 mb-6">Browse the marketplace to find vendors and book services.</p>
                    <Link
                        href="/marketplace"
                        className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 transition-colors"
                    >
                        Browse Marketplace
                        <ArrowRight className="h-4 w-4" />
                    </Link>
                </div>
            ) : (
                <div className="space-y-4">
                    {bookings.map((booking: BookingItem) => {
                        const status = statusConfig[booking.status] || statusConfig.pending;
                        const StatusIcon = status.icon;
                        const hasActiveQuote = QUOTE_STATUSES.has(booking.status);
                        const canCancel = CANCELLABLE_STATUSES.has(booking.status);

                        return (
                            <div
                                key={booking.id}
                                className={`bg-white rounded-xl shadow-sm border p-6 hover:shadow-md transition-shadow ${hasActiveQuote ? 'border-amber-200' : 'border-gray-100'}`}
                            >
                                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                                    <div>
                                        <h3 className="font-semibold text-gray-900">
                                            {booking.service?.name || booking.serviceName || 'Service'}
                                        </h3>
                                        <p className="text-sm text-gray-500 mt-1">
                                            {booking.vendor?.name || booking.vendorName || 'Vendor'} •{' '}
                                            <Calendar className="inline h-3 w-3 mr-1" />
                                            {new Date(booking.event_date || booking.eventDate || '').toLocaleDateString('en-PK', {
                                                weekday: 'short',
                                                year: 'numeric',
                                                month: 'short',
                                                day: 'numeric',
                                            })}
                                        </p>
                                        {(booking.guest_count || booking.guestCount) && (
                                            <p className="text-xs text-gray-400 mt-1">
                                                {booking.guest_count || booking.guestCount} guests
                                            </p>
                                        )}
                                    </div>

                                    <div className="flex items-center gap-3">
                                        {(booking.total_price || booking.totalAmount) && (
                                            <span className="text-sm font-medium text-gray-900">
                                                PKR {Number(booking.total_price || booking.totalAmount).toLocaleString()}
                                            </span>
                                        )}
                                        <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium ${status.color}`}>
                                            <StatusIcon className="h-3 w-3" />
                                            {status.label}
                                        </span>
                                    </div>
                                </div>

                                {booking.notes && (
                                    <p className="mt-3 text-sm text-gray-500 bg-gray-50 rounded-lg px-4 py-2">
                                        {booking.notes}
                                    </p>
                                )}

                                <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-gray-50 pt-3">
                                    {hasActiveQuote && (
                                        <Link
                                            href={`/bookings/${booking.id}/quotes`}
                                            className="inline-flex items-center gap-1.5 rounded-lg bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-700 transition-colors"
                                        >
                                            <Receipt className="h-4 w-4" />
                                            {booking.status === 'negotiating' ? 'View Negotiation' : 'View Quote'}
                                            <ArrowRight className="h-3.5 w-3.5" />
                                        </Link>
                                    )}
                                    {!hasActiveQuote && (
                                        <Link
                                            href={`/bookings/${booking.id}/quotes`}
                                            className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 transition-colors"
                                        >
                                            <Receipt className="h-3.5 w-3.5" />
                                            Quotes
                                        </Link>
                                    )}

                                    {canCancel && (
                                        <button
                                            onClick={() => setCancelTarget(booking)}
                                            className="inline-flex items-center gap-1.5 rounded-lg border border-red-200 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 transition-colors ml-auto"
                                        >
                                            <Ban className="h-3.5 w-3.5" />
                                            Cancel
                                        </button>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            {cancelTarget && (
                <CancelDialog
                    booking={cancelTarget}
                    onClose={() => setCancelTarget(null)}
                    onConfirm={(reason) => cancel.mutate({ id: cancelTarget.id, reason })}
                    isPending={cancel.isPending}
                />
            )}
        </div>
    );
}
