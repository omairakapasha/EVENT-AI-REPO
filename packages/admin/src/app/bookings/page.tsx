'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAdminAuth } from '@/lib/use-admin-auth';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import {
    CalendarCheck, CheckCircle, XCircle, Loader2, AlertCircle,
    Clock, Search, ChevronLeft, ChevronRight
} from 'lucide-react';
import { getBookings, updateBookingStatus } from '@/lib/api';
import toast from 'react-hot-toast';

const STATUS_COLORS: Record<string, string> = {
    pending: 'bg-yellow-100 text-yellow-700',
    confirmed: 'bg-green-100 text-green-700',
    rejected: 'bg-red-100 text-red-700',
    cancelled: 'bg-gray-100 text-gray-600',
};

export default function BookingsPage() {
    const { status } = useAdminAuth();
    const router = useRouter();
    const queryClient = useQueryClient();

    const [page, setPage] = useState(1);
    const [filterStatus, setFilterStatus] = useState('');
    const [rejectModal, setRejectModal] = useState<{ id: string; open: boolean } | null>(null);
    const [rejectReason, setRejectReason] = useState('');
    const [actionId, setActionId] = useState<string | null>(null);

    useEffect(() => {
        if (status === 'unauthenticated') router.push('/login');
    }, [status, router]);

    const { data, isLoading, error } = useQuery({
        queryKey: ['bookings', page, filterStatus],
        queryFn: () => getBookings({ page, status: filterStatus || undefined }),
        placeholderData: (prev) => prev,
    });

    const bookings: any[] = Array.isArray(data) ? data : (data?.items ?? data?.bookings ?? []);
    const total: number = data?.total ?? bookings.length;
    const totalPages = Math.ceil(total / 20);

    const statusMutation = useMutation({
        mutationFn: ({ id, newStatus, reason }: { id: string; newStatus: 'confirmed' | 'rejected'; reason?: string }) =>
            updateBookingStatus(id, newStatus, reason),
        onSuccess: (_, { newStatus }) => {
            toast.success(`Booking ${newStatus === 'confirmed' ? 'approved' : 'rejected'} successfully`);
            queryClient.invalidateQueries({ queryKey: ['bookings'] });
            setActionId(null);
            setRejectModal(null);
            setRejectReason('');
        },
        onError: () => {
            toast.error('Failed to update booking status');
            setActionId(null);
        },
    });

    const handleApprove = (id: string) => {
        setActionId(id);
        statusMutation.mutate({ id, newStatus: 'confirmed' });
    };

    const handleRejectSubmit = () => {
        if (!rejectModal) return;
        setActionId(rejectModal.id);
        statusMutation.mutate({ id: rejectModal.id, newStatus: 'rejected', reason: rejectReason });
    };

    if (status === 'loading' || status === 'unauthenticated') {
        return <div className="flex items-center justify-center h-64"><Loader2 className="h-8 w-8 animate-spin text-indigo-600" /></div>;
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
                        <CalendarCheck className="h-6 w-6 text-indigo-600" />
                        Bookings
                    </h1>
                    <p className="text-sm text-gray-500 mt-1">Manage and approve booking requests from clients.</p>
                </div>
                {/* Filter */}
                <div className="flex items-center gap-2">
                    <Search className="h-4 w-4 text-gray-400" />
                    <select
                        value={filterStatus}
                        onChange={(e) => { setFilterStatus(e.target.value); setPage(1); }}
                        className="text-sm border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    >
                        <option value="">All Statuses</option>
                        <option value="pending">Pending</option>
                        <option value="confirmed">Confirmed</option>
                        <option value="rejected">Rejected</option>
                        <option value="cancelled">Cancelled</option>
                    </select>
                </div>
            </div>

            {/* Error */}
            {error && (
                <div className="flex items-center gap-2 rounded-lg bg-red-50 p-4 text-red-600 text-sm">
                    <AlertCircle className="h-4 w-4 flex-shrink-0" />
                    Failed to load bookings. Is the backend running?
                </div>
            )}

            {/* Table */}
            <div className="rounded-xl border bg-white shadow-sm overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                    <thead className="bg-gray-50">
                        <tr>
                            <th className="px-4 py-3 text-left font-semibold text-gray-600">Client</th>
                            <th className="px-4 py-3 text-left font-semibold text-gray-600">Vendor</th>
                            <th className="px-4 py-3 text-left font-semibold text-gray-600">Service</th>
                            <th className="px-4 py-3 text-left font-semibold text-gray-600">Event Date</th>
                            <th className="px-4 py-3 text-right font-semibold text-gray-600">Total</th>
                            <th className="px-4 py-3 text-center font-semibold text-gray-600">Status</th>
                            <th className="px-4 py-3 text-center font-semibold text-gray-600">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                        {isLoading && [...Array(5)].map((_, i) => (
                            <tr key={i}>
                                {[...Array(7)].map((_, j) => (
                                    <td key={j} className="px-4 py-3">
                                        <div className="h-4 w-full animate-pulse rounded bg-gray-200" />
                                    </td>
                                ))}
                            </tr>
                        ))}

                        {!isLoading && bookings.length === 0 && (
                            <tr>
                                <td colSpan={7} className="px-4 py-12 text-center text-gray-400">
                                    <Clock className="h-8 w-8 mx-auto mb-2 opacity-40" />
                                    No bookings found.
                                </td>
                            </tr>
                        )}

                        {!isLoading && bookings.map((booking: any) => {
                            const isPending = booking.status === 'pending';
                            const isProcessing = actionId === booking.id && statusMutation.isPending;
                            const eventDate = booking.eventDate
                                ? new Date(booking.eventDate).toLocaleDateString('en-PK', { year: 'numeric', month: 'short', day: 'numeric' })
                                : '—';

                            return (
                                <tr key={booking.id} className="hover:bg-gray-50 transition-colors">
                                    <td className="px-4 py-3">
                                        <div className="font-medium text-gray-900">{booking.clientName || '—'}</div>
                                        <div className="text-xs text-gray-400">{booking.clientEmail || ''}</div>
                                    </td>
                                    <td className="px-4 py-3 text-gray-700">{booking.vendor?.name || '—'}</td>
                                    <td className="px-4 py-3 text-gray-700">{booking.service?.name || '—'}</td>
                                    <td className="px-4 py-3 text-gray-600">{eventDate}</td>
                                    <td className="px-4 py-3 text-right font-medium text-gray-900">
                                        {booking.currency || 'PKR'} {Number(booking.totalPrice || 0).toLocaleString()}
                                    </td>
                                    <td className="px-4 py-3 text-center">
                                        <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${STATUS_COLORS[booking.status] || 'bg-gray-100 text-gray-600'}`}>
                                            {booking.status}
                                        </span>
                                    </td>
                                    <td className="px-4 py-3">
                                        {isPending ? (
                                            <div className="flex items-center justify-center gap-2">
                                                <button
                                                    id={`approve-${booking.id}`}
                                                    onClick={() => handleApprove(booking.id)}
                                                    disabled={isProcessing}
                                                    title="Approve booking"
                                                    className="flex items-center gap-1 rounded-lg bg-green-50 px-2.5 py-1.5 text-xs font-medium text-green-700 hover:bg-green-100 disabled:opacity-50"
                                                >
                                                    {isProcessing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle className="h-3.5 w-3.5" />}
                                                    Approve
                                                </button>
                                                <button
                                                    id={`reject-${booking.id}`}
                                                    onClick={() => setRejectModal({ id: booking.id, open: true })}
                                                    disabled={isProcessing}
                                                    title="Reject booking"
                                                    className="flex items-center gap-1 rounded-lg bg-red-50 px-2.5 py-1.5 text-xs font-medium text-red-700 hover:bg-red-100 disabled:opacity-50"
                                                >
                                                    <XCircle className="h-3.5 w-3.5" />
                                                    Reject
                                                </button>
                                            </div>
                                        ) : (
                                            <span className="block text-center text-xs text-gray-400">—</span>
                                        )}
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
                <div className="flex items-center justify-between text-sm text-gray-600">
                    <span>{total} booking{total !== 1 ? 's' : ''} total</span>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => setPage((p) => Math.max(1, p - 1))}
                            disabled={page === 1}
                            className="flex items-center gap-1 rounded-lg border px-3 py-1.5 hover:bg-gray-50 disabled:opacity-40"
                        >
                            <ChevronLeft className="h-4 w-4" /> Prev
                        </button>
                        <span className="px-2">Page {page} of {totalPages}</span>
                        <button
                            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                            disabled={page >= totalPages}
                            className="flex items-center gap-1 rounded-lg border px-3 py-1.5 hover:bg-gray-50 disabled:opacity-40"
                        >
                            Next <ChevronRight className="h-4 w-4" />
                        </button>
                    </div>
                </div>
            )}

            {/* Reject Reason Modal */}
            {rejectModal?.open && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
                    <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
                        <h2 className="text-lg font-semibold text-gray-900 mb-1">Reject Booking</h2>
                        <p className="text-sm text-gray-500 mb-4">Optionally provide a reason — the client will be notified by email.</p>
                        <textarea
                            value={rejectReason}
                            onChange={(e) => setRejectReason(e.target.value)}
                            rows={3}
                            placeholder="e.g. Date is unavailable, venue is fully booked..."
                            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-red-500 focus:border-red-500 resize-none mb-4"
                        />
                        <div className="flex justify-end gap-3">
                            <button
                                onClick={() => { setRejectModal(null); setRejectReason(''); }}
                                className="rounded-lg border px-4 py-2 text-sm font-medium hover:bg-gray-50"
                            >
                                Cancel
                            </button>
                            <button
                                id="confirm-reject-btn"
                                onClick={handleRejectSubmit}
                                disabled={statusMutation.isPending}
                                className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
                            >
                                {statusMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <XCircle className="h-4 w-4" />}
                                Confirm Rejection
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
