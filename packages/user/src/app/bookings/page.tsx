'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import {
    Calendar, Package, Clock, CheckCircle, XCircle, AlertCircle,
    ArrowRight, Loader2,
} from 'lucide-react';
import { getUserBookings } from '@/lib/api';

const statusConfig: Record<string, { color: string; icon: any; label: string }> = {
    pending: { color: 'bg-yellow-100 text-yellow-800', icon: Clock, label: 'Pending' },
    confirmed: { color: 'bg-green-100 text-green-800', icon: CheckCircle, label: 'Confirmed' },
    cancelled: { color: 'bg-red-100 text-red-800', icon: XCircle, label: 'Cancelled' },
    completed: { color: 'bg-blue-100 text-blue-800', icon: CheckCircle, label: 'Completed' },
    rejected: { color: 'bg-red-100 text-red-800', icon: XCircle, label: 'Rejected' },
};

export default function BookingsPage() {
    const { data, isLoading } = useQuery({
        queryKey: ['bookings'],
        queryFn: () => getUserBookings(),
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
                    {bookings.map((booking: any) => {
                        const status = statusConfig[booking.status] || statusConfig.pending;
                        const StatusIcon = status.icon;

                        return (
                            <div key={booking.id} className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 hover:shadow-md transition-shadow">
                                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                                    <div>
                                        <h3 className="font-semibold text-gray-900">
                                            {booking.service?.name || booking.serviceName || 'Service'}
                                        </h3>
                                        <p className="text-sm text-gray-500 mt-1">
                                            {booking.vendor?.name || booking.vendorName || 'Vendor'} •{' '}
                                            <Calendar className="inline h-3 w-3 mr-1" />
                                            {new Date(booking.eventDate).toLocaleDateString('en-PK', {
                                                weekday: 'short',
                                                year: 'numeric',
                                                month: 'short',
                                                day: 'numeric',
                                            })}
                                        </p>
                                        {booking.guestCount && (
                                            <p className="text-xs text-gray-400 mt-1">{booking.guestCount} guests</p>
                                        )}
                                    </div>

                                    <div className="flex items-center gap-3">
                                        {booking.totalAmount && (
                                            <span className="text-sm font-medium text-gray-900">
                                                PKR {Number(booking.totalAmount).toLocaleString()}
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
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
