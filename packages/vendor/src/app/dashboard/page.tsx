'use client';

import { Suspense, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Calendar, TrendingUp, Package, Users, ChevronRight, AlertCircle, RefreshCw } from 'lucide-react';
import { useAuthStore } from '@/lib/auth-store';
import { useDashboard } from '@/lib/hooks/use-dashboard';
import { VendorLayout } from '@/components/vendor-layout';
import { cn, formatCurrency, formatDate } from '@/lib/utils';

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
    return <div className={`animate-pulse rounded-lg bg-surface-200 dark:bg-surface-700 ${className}`} />;
}

function DashboardContent() {
    const searchParams = useSearchParams();
    const { isAuthenticated, loginWithTokens } = useAuthStore();
    const { data, isLoading, isError, refetch } = useDashboard();

    // Handle OAuth callback tokens
    useEffect(() => {
        const token = searchParams?.get('token');
        const refreshToken = searchParams?.get('refresh_token');
        if (token && refreshToken) {
            loginWithTokens(token, refreshToken).then(() => {
                const url = new URL(window.location.href);
                url.searchParams.delete('token');
                url.searchParams.delete('refresh_token');
                window.history.replaceState({}, '', url.toString());
            });
        }
    }, [searchParams, loginWithTokens]);

    const stats = [
        { label: 'Total Bookings', value: data?.total_bookings ?? 0, icon: Calendar },
        { label: 'Pending', value: data?.pending_bookings ?? 0, icon: TrendingUp },
        { label: 'Confirmed', value: data?.confirmed_bookings ?? 0, icon: Users },
        { label: 'Active Services', value: data?.active_services ?? 0, icon: Package },
    ];

    return (
        <div className="space-y-8">
            <div>
                <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-50">Dashboard</h1>
                <p className="mt-1 text-surface-500">Your business at a glance</p>
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
                            {isLoading ? (
                                <Skeleton className="h-8 w-16" />
                            ) : (
                                <p className="text-2xl font-bold text-surface-900 dark:text-surface-50">{stat.value}</p>
                            )}
                            <p className="text-sm text-surface-500">{stat.label}</p>
                        </div>
                    </div>
                ))}
            </div>

            {/* Recent bookings */}
            <div className="rounded-xl border border-surface-200 bg-white dark:border-surface-800 dark:bg-surface-900">
                <div className="flex items-center justify-between border-b border-surface-200 px-6 py-4 dark:border-surface-800">
                    <h2 className="text-lg font-semibold text-surface-900 dark:text-surface-50">Recent Bookings</h2>
                    <Link href="/bookings" className="flex items-center text-sm text-primary-600 hover:underline">
                        View all <ChevronRight className="ml-1 h-4 w-4" />
                    </Link>
                </div>

                {isError && (
                    <div className="flex items-center gap-3 p-6">
                        <AlertCircle className="h-5 w-5 text-red-500" />
                        <p className="text-sm text-red-600">Failed to load dashboard data.</p>
                        <button onClick={() => refetch()} className="ml-auto flex items-center gap-1 text-sm text-primary-600 hover:underline">
                            <RefreshCw className="h-4 w-4" /> Retry
                        </button>
                    </div>
                )}

                {isLoading && (
                    <div className="divide-y divide-surface-100 dark:divide-surface-800">
                        {[...Array(5)].map((_, i) => (
                            <div key={i} className="flex items-center gap-4 px-6 py-4">
                                <Skeleton className="h-4 w-32" />
                                <Skeleton className="h-4 w-24" />
                                <Skeleton className="h-6 w-20 rounded-full" />
                                <Skeleton className="ml-auto h-4 w-16" />
                            </div>
                        ))}
                    </div>
                )}

                {!isLoading && !isError && (
                    <table className="w-full">
                        <thead className="bg-surface-50 dark:bg-surface-900/50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase text-surface-500">Service</th>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase text-surface-500">Event Date</th>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase text-surface-500">Status</th>
                                <th className="px-6 py-3 text-right text-xs font-medium uppercase text-surface-500">Amount</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-surface-100 dark:divide-surface-800">
                            {(data?.recent_bookings ?? []).map((b) => (
                                <tr key={b.id} className="hover:bg-surface-50 dark:hover:bg-surface-900/50">
                                    <td className="px-6 py-4 text-sm font-medium text-surface-900 dark:text-surface-50">{b.service_name ?? '—'}</td>
                                    <td className="px-6 py-4 text-sm text-surface-600">{formatDate(b.event_date)}</td>
                                    <td className="px-6 py-4">
                                        <span className={cn('rounded-full px-2.5 py-0.5 text-xs font-medium', STATUS_COLORS[b.status] ?? 'bg-gray-100 text-gray-700')}>
                                            {b.status.replace('_', ' ')}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-right text-sm font-medium text-surface-900 dark:text-surface-50">
                                        {formatCurrency(b.total_price, b.currency)}
                                    </td>
                                </tr>
                            ))}
                            {(data?.recent_bookings ?? []).length === 0 && (
                                <tr>
                                    <td colSpan={4} className="px-6 py-10 text-center text-sm text-surface-500">
                                        No bookings yet
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
}

export default function DashboardPage() {
    return (
        <VendorLayout>
            <Suspense fallback={<div className="flex min-h-[60vh] items-center justify-center"><div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" /></div>}>
                <DashboardContent />
            </Suspense>
        </VendorLayout>
    );
}
