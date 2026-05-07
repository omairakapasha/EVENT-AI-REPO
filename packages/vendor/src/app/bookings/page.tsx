'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Calendar, Loader2 } from 'lucide-react';
import { VendorLayout } from '@/components/vendor-layout';
import { useVendorBookings, useConfirmBooking, useRejectBooking, type Booking } from '@/lib/hooks/use-vendor-bookings';
import { cn, formatCurrency, formatDate } from '@/lib/utils';

const STATUS_TABS = ['all', 'pending', 'confirmed', 'in_progress', 'completed', 'cancelled'];

const STATUS_COLORS: Record<string, string> = {
    pending: 'bg-yellow-100 text-yellow-700',
    confirmed: 'bg-blue-100 text-blue-700',
    in_progress: 'bg-indigo-100 text-indigo-700',
    completed: 'bg-green-100 text-green-700',
    cancelled: 'bg-red-100 text-red-700',
    rejected: 'bg-gray-100 text-gray-700',
    no_show: 'bg-gray-100 text-gray-500',
};

function Skeleton({ className = '' }: { className?: string }) {
    return <div className={`animate-pulse rounded bg-surface-200 dark:bg-surface-700 ${className}`} />;
}

function RejectModal({ booking, onClose }: { booking: Booking; onClose: () => void }) {
    const [reason, setReason] = useState('');
    const reject = useRejectBooking();

    const handleSubmit = async () => {
        await reject.mutateAsync({ bookingId: booking.id, reason: reason || undefined });
        onClose();
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
            <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl dark:bg-surface-900">
                <h3 className="text-lg font-semibold text-surface-900 dark:text-surface-50">Reject Booking</h3>
                <p className="mt-1 text-sm text-surface-500">Optionally provide a reason for the customer.</p>
                <textarea
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    placeholder="Reason (optional)"
                    rows={3}
                    className="mt-4 w-full rounded-lg border border-surface-300 p-3 text-sm focus:border-primary-500 focus:outline-none dark:border-surface-700 dark:bg-surface-800"
                />
                <div className="mt-4 flex justify-end gap-3">
                    <button onClick={onClose} className="rounded-lg border border-surface-300 px-4 py-2 text-sm hover:bg-surface-50">Cancel</button>
                    <button
                        onClick={handleSubmit}
                        disabled={reject.isPending}
                        className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm text-white hover:bg-red-700 disabled:opacity-50"
                    >
                        {reject.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                        Reject
                    </button>
                </div>
            </div>
        </div>
    );
}

export default function BookingsPage() {
    const router = useRouter();
    const [statusFilter, setStatusFilter] = useState('all');
    const [rejectTarget, setRejectTarget] = useState<Booking | null>(null);
    const { data, isLoading, isError } = useVendorBookings({ status: statusFilter });
    const confirm = useConfirmBooking();

    const bookings: Booking[] = data?.data ?? [];

    return (
        <VendorLayout>
            <div className="space-y-6">
                <div>
                    <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-50">Bookings</h1>
                    <p className="mt-1 text-surface-500">Manage your event bookings</p>
                </div>

                {/* Filter tabs */}
                <div className="flex flex-wrap gap-2">
                    {STATUS_TABS.map((s) => (
                        <button
                            key={s}
                            onClick={() => setStatusFilter(s)}
                            className={cn(
                                'rounded-full px-4 py-1.5 text-sm font-medium capitalize transition-colors',
                                statusFilter === s
                                    ? 'bg-primary-600 text-white'
                                    : 'border border-surface-200 bg-white text-surface-600 hover:bg-surface-50 dark:border-surface-700 dark:bg-surface-900 dark:text-surface-400'
                            )}
                        >
                            {s === 'all' ? 'All' : s.replace('_', ' ')}
                        </button>
                    ))}
                </div>

                <div className="rounded-xl border border-surface-200 bg-white dark:border-surface-800 dark:bg-surface-900">
                    {isLoading ? (
                        <div className="divide-y divide-surface-100 dark:divide-surface-800">
                            {[...Array(5)].map((_, i) => (
                                <div key={i} className="flex items-center gap-4 px-6 py-4">
                                    <Skeleton className="h-4 w-32" />
                                    <Skeleton className="h-4 w-24" />
                                    <Skeleton className="h-4 w-24" />
                                    <Skeleton className="h-6 w-20 rounded-full" />
                                    <Skeleton className="ml-auto h-4 w-16" />
                                </div>
                            ))}
                        </div>
                    ) : isError ? (
                        <p className="p-6 text-center text-sm text-red-500">Failed to load bookings.</p>
                    ) : bookings.length === 0 ? (
                        <div className="flex flex-col items-center py-16">
                            <Calendar className="h-12 w-12 text-surface-300" />
                            <p className="mt-4 text-surface-500">No bookings found</p>
                        </div>
                    ) : (
                        <table className="w-full">
                            <thead className="border-b border-surface-200 bg-surface-50 dark:border-surface-800 dark:bg-surface-900/50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase text-surface-500">Client</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase text-surface-500">Event Date</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase text-surface-500">Status</th>
                                    <th className="px-6 py-3 text-right text-xs font-medium uppercase text-surface-500">Amount</th>
                                    <th className="px-6 py-3 text-right text-xs font-medium uppercase text-surface-500">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-surface-100 dark:divide-surface-800">
                                {bookings.map((b) => (
                                    <tr
                                        key={b.id}
                                        className="cursor-pointer hover:bg-surface-50 dark:hover:bg-surface-900/50"
                                        onClick={() => router.push(`/bookings/${b.id}`)}
                                    >
                                        <td className="px-6 py-4 text-sm font-medium text-surface-900 dark:text-surface-50">{b.client_name ?? '—'}</td>
                                        <td className="px-6 py-4 text-sm text-surface-600">{formatDate(b.event_date)}</td>
                                        <td className="px-6 py-4">
                                            <span className={cn('rounded-full px-2.5 py-0.5 text-xs font-medium', STATUS_COLORS[b.status] ?? 'bg-gray-100 text-gray-700')}>
                                                {b.status.replace('_', ' ')}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-right text-sm font-medium text-surface-900 dark:text-surface-50">
                                            {formatCurrency(b.total_price, b.currency)}
                                        </td>
                                        <td className="px-6 py-4 text-right" onClick={(e) => e.stopPropagation()}>
                                            {b.status === 'pending' && (
                                                <div className="flex justify-end gap-2">
                                                    <button
                                                        onClick={() => confirm.mutate(b.id)}
                                                        disabled={confirm.isPending}
                                                        className="rounded-lg bg-green-600 px-3 py-1 text-xs font-medium text-white hover:bg-green-700 disabled:opacity-50"
                                                    >
                                                        Confirm
                                                    </button>
                                                    <button
                                                        onClick={() => setRejectTarget(b)}
                                                        className="rounded-lg bg-red-600 px-3 py-1 text-xs font-medium text-white hover:bg-red-700"
                                                    >
                                                        Reject
                                                    </button>
                                                </div>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            </div>

            {rejectTarget && (
                <RejectModal booking={rejectTarget} onClose={() => setRejectTarget(null)} />
            )}
        </VendorLayout>
    );
}
