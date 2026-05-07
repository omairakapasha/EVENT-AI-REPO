'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect } from 'react';
import {
    LayoutDashboard,
    Briefcase,
    Calendar,
    Package,
    Settings,
    LogOut,
    Bell,
    Wifi,
    WifiOff,
} from 'lucide-react';
import { cn, getInitials } from '@/lib/utils';
import { useAuthStore } from '@/lib/auth-store';
import { useSSE } from '@/lib/hooks/use-sse';
import { useUnreadCount, useNotifications, useMarkNotificationRead, useMarkAllRead } from '@/lib/hooks/use-notifications';
import { useState } from 'react';
import { formatRelativeTime } from '@/lib/utils';

const navItems = [
    { href: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { href: '/services', icon: Briefcase, label: 'Services' },
    { href: '/bookings', icon: Package, label: 'Bookings' },
    { href: '/availability', icon: Calendar, label: 'Availability' },
    { href: '/profile', icon: Settings, label: 'Profile' },
];

const statusBadgeColors: Record<string, string> = {
    PENDING: 'bg-yellow-100 text-yellow-700',
    ACTIVE: 'bg-green-100 text-green-700',
    SUSPENDED: 'bg-orange-100 text-orange-700',
    REJECTED: 'bg-red-100 text-red-700',
};

function NotificationBell() {
    const [open, setOpen] = useState(false);
    const [hasMounted, setHasMounted] = useState(false);
    const { data: unreadCount = 0 } = useUnreadCount();
    const { data: notifications = [] } = useNotifications();
    const markRead = useMarkNotificationRead();
    const markAllRead = useMarkAllRead();

    useEffect(() => { setHasMounted(true); }, []);

    const count = hasMounted ? unreadCount : 0;

    return (
        <div className="relative">
            <button
                onClick={() => setOpen((v) => !v)}
                className="relative rounded-lg p-2 text-surface-400 hover:bg-surface-100 hover:text-surface-600 dark:hover:bg-surface-800"
                aria-label="Notifications"
            >
                <Bell className="h-5 w-5" />
                {count > 0 && (
                    <span className="absolute right-1 top-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white">
                        {count > 9 ? '9+' : count}
                    </span>
                )}
            </button>

            {open && (
                <>
                    <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
                    <div className="absolute right-0 top-10 z-20 w-80 rounded-xl border border-surface-200 bg-white shadow-lg dark:border-surface-700 dark:bg-surface-900">
                        <div className="flex items-center justify-between border-b border-surface-200 px-4 py-3 dark:border-surface-700">
                            <h3 className="text-sm font-semibold text-surface-900 dark:text-surface-50">
                                Notifications
                            </h3>
                            {unreadCount > 0 && (
                                <button onClick={() => markAllRead.mutate()} className="text-xs text-primary-600 hover:underline">
                                    Mark all as read
                                </button>
                            )}
                        </div>
                        <div className="max-h-80 overflow-y-auto">
                            {notifications.length === 0 ? (
                                <p className="px-4 py-6 text-center text-sm text-surface-500">No notifications</p>
                            ) : (
                                notifications.slice(0, 10).map((n) => (
                                    <button
                                        key={n.id}
                                        onClick={() => { if (!n.is_read) markRead.mutate(n.id); }}
                                        className={cn(
                                            'flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-surface-50 dark:hover:bg-surface-800',
                                            !n.is_read && 'bg-primary-50/50 dark:bg-primary-900/10'
                                        )}
                                    >
                                        {!n.is_read && <span className="mt-1.5 h-2 w-2 flex-shrink-0 rounded-full bg-primary-500" />}
                                        <div className={cn('flex-1', n.is_read && 'pl-5')}>
                                            <p className="text-sm font-medium text-surface-900 dark:text-surface-50">{n.title}</p>
                                            <p className="text-xs text-surface-500">{n.message}</p>
                                            <p className="mt-1 text-xs text-surface-400">{formatRelativeTime(n.created_at)}</p>
                                        </div>
                                    </button>
                                ))
                            )}
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}

export function VendorLayout({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const router = useRouter();
    const { user, vendor, isAuthenticated, logout, ensureVendorProfile, vendorCheckStatus } = useAuthStore();

    // Kick off the vendor profile check once on mount.
    // ensureVendorProfile is idempotent and concurrency-safe — guarded by
    // vendorCheckStatus so concurrent calls never fire two parallel fetches.
    useEffect(() => {
        ensureVendorProfile();
    // Re-run if auth state changes (e.g. token refresh, OAuth callback)
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isAuthenticated]);

    // Once the check is done and there's no vendor, redirect to onboarding.
    useEffect(() => {
        if (vendorCheckStatus !== 'done') return;
        if (isAuthenticated && !vendor) {
            router.replace('/register?incomplete=1');
        }
    }, [vendorCheckStatus, isAuthenticated, vendor, router]);

    // SSE only after vendor is confirmed
    const { reconnecting } = useSSE(isAuthenticated && vendorCheckStatus === 'done' && !!vendor);

    const handleLogout = async () => {
        await logout();
        router.push('/login');
    };

    // Block all rendering until the vendor check resolves.
    // This is the race condition fix — no child page fires API calls until we know
    // the vendor profile exists.
    if (vendorCheckStatus !== 'done') {
        return (
            <div className="flex min-h-screen items-center justify-center bg-surface-50 dark:bg-surface-950">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
            </div>
        );
    }

    // Check done, no vendor — show spinner while redirect fires.
    if (!vendor) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-surface-50 dark:bg-surface-950">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
            </div>
        );
    }

    return (
        <div className="flex min-h-screen bg-surface-50 dark:bg-surface-950">
            <aside className="fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-surface-200 bg-white dark:border-surface-800 dark:bg-surface-900">
                <div className="flex h-16 items-center gap-3 border-b border-surface-200 px-6 dark:border-surface-800">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-primary-500 to-primary-600">
                        <Package className="h-5 w-5 text-white" />
                    </div>
                    <div>
                        <p className="text-sm font-semibold text-surface-900 dark:text-surface-50">Vendor Portal</p>
                        <p className="text-xs text-surface-500">Event-AI</p>
                    </div>
                </div>

                <nav className="flex flex-1 flex-col gap-1 overflow-y-auto p-4">
                    {navItems.map((item) => {
                        const isActive = pathname === item.href || (item.href !== '/dashboard' && pathname?.startsWith(item.href));
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={cn(
                                    'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                                    isActive
                                        ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/20 dark:text-primary-400'
                                        : 'text-surface-600 hover:bg-surface-100 hover:text-surface-900 dark:text-surface-400 dark:hover:bg-surface-800 dark:hover:text-surface-50'
                                )}
                            >
                                <item.icon className="h-5 w-5" />
                                {item.label}
                            </Link>
                        );
                    })}
                </nav>

                <div className="border-t border-surface-200 p-4 dark:border-surface-800">
                    {vendor && (
                        <div className="mb-3">
                            <p className="truncate text-sm font-medium text-surface-900 dark:text-surface-50">{vendor.businessName}</p>
                            <span className={cn('mt-1 inline-block rounded-full px-2 py-0.5 text-xs font-medium', statusBadgeColors[vendor.status] ?? 'bg-surface-100 text-surface-600')}>
                                {vendor.status}
                            </span>
                        </div>
                    )}
                    <div className="flex items-center gap-3">
                        <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-primary-100 text-sm font-medium text-primary-700 dark:bg-primary-900/30 dark:text-primary-400">
                            {getInitials(user?.firstName ? `${user.firstName} ${user.lastName ?? ''}` : vendor?.businessName ?? 'V')}
                        </div>
                        <div className="min-w-0 flex-1">
                            <p className="truncate text-sm font-medium text-surface-900 dark:text-surface-50">
                                {`${user?.firstName ?? ''} ${user?.lastName ?? ''}`.trim()}
                            </p>
                            <p className="truncate text-xs text-surface-500">{user?.email}</p>
                        </div>
                        <button onClick={handleLogout} className="rounded-lg p-1.5 text-surface-400 hover:bg-surface-100 hover:text-surface-600 dark:hover:bg-surface-800" title="Logout">
                            <LogOut className="h-4 w-4" />
                        </button>
                    </div>
                </div>
            </aside>

            <div className="ml-64 flex flex-1 flex-col">
                <header className="sticky top-0 z-40 flex h-16 items-center justify-between border-b border-surface-200 bg-white px-6 dark:border-surface-800 dark:bg-surface-900">
                    <div />
                    <div className="flex items-center gap-2">
                        {reconnecting && (
                            <span className="flex items-center gap-1 text-xs text-surface-400">
                                <WifiOff className="h-3.5 w-3.5" />
                                Reconnecting…
                            </span>
                        )}
                        {!reconnecting && isAuthenticated && (
                            <span className="sr-only">
                                <Wifi className="h-3.5 w-3.5 text-green-500" />
                            </span>
                        )}
                        <NotificationBell />
                    </div>
                </header>

                <main className="flex-1 p-8">{children}</main>
            </div>
        </div>
    );
}
