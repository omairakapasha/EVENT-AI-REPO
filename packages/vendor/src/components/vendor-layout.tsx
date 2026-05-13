'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useRef } from 'react';
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
    AlertCircle,
    RefreshCw,
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

const VENDOR_CHECK_TIMEOUT = 15000; // 15 seconds timeout

export function VendorLayout({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const router = useRouter();
    const { user, vendor, isAuthenticated, logout, ensureVendorProfile, vendorCheckStatus, error, clearError, sessionStatus, initSession } = useAuthStore();
    const [checkError, setCheckError] = useState<string | null>(null);
    const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
    const [isLoggingOut, setIsLoggingOut] = useState(false);
    const timeoutRef = useRef<NodeJS.Timeout | null>(null);
    const isMountedRef = useRef(true);

    // SSE — called unconditionally (rules of hooks). Only connects when vendor is ACTIVE.
    const { reconnecting } = useSSE(isAuthenticated && vendorCheckStatus === 'done' && !!vendor && vendor.status === 'ACTIVE');

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            isMountedRef.current = false;
            if (timeoutRef.current) {
                clearTimeout(timeoutRef.current);
            }
        };
    }, []);

    // Step 1: Hydrate auth state from cookies on first load
    useEffect(() => {
        initSession();
    }, [initSession]);

    // Step 2: Once session is resolved, enforce auth + role guards and kick off vendor check
    useEffect(() => {
        if (sessionStatus !== 'done') return;

        if (!isAuthenticated) {
            router.replace('/login');
            return;
        }

        // Role guard: only vendor accounts may access this portal (AUTH-05)
        if (user && user.role !== 'vendor') {
            logout().then(() => {
                router.replace('/login?error=Access+denied.+This+portal+is+for+vendors+only.');
            });
            return;
        }

        // Reset error state on re-check
        setCheckError(null);
        clearError();

        // Set a timeout to detect stuck checks
        timeoutRef.current = setTimeout(() => {
            if (isMountedRef.current && vendorCheckStatus === 'checking') {
                setCheckError('Vendor profile check timed out. Please retry.');
            }
        }, VENDOR_CHECK_TIMEOUT);

        ensureVendorProfile();

        return () => {
            if (timeoutRef.current) {
                clearTimeout(timeoutRef.current);
            }
        };
    }, [sessionStatus, isAuthenticated, user, router, clearError, ensureVendorProfile]);

    // Once the check is done and there's no vendor, redirect to onboarding.
    useEffect(() => {
        if (vendorCheckStatus !== 'done') return;
        // Only redirect if we're still mounted and not in an error state
        if (isAuthenticated && !vendor && !checkError) {
            router.replace('/register?incomplete=1');
        }
    }, [vendorCheckStatus, isAuthenticated, vendor, router, checkError]);

    // Block SUSPENDED / REJECTED vendors from accessing the dashboard (AUTH-05)
    // They see a dedicated status screen instead of confusing 403 errors.
    if (vendorCheckStatus === 'done' && vendor && (vendor.status === 'SUSPENDED' || vendor.status === 'REJECTED')) {
        const isSuspended = vendor.status === 'SUSPENDED';
        return (
            <div className="flex min-h-screen items-center justify-center bg-surface-50 dark:bg-surface-950 p-4">
                <div className="max-w-md text-center">
                    <div className={`mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full ${isSuspended ? 'bg-orange-100 dark:bg-orange-900/30' : 'bg-red-100 dark:bg-red-900/30'}`}>
                        <AlertCircle className={`h-7 w-7 ${isSuspended ? 'text-orange-600 dark:text-orange-400' : 'text-red-600 dark:text-red-400'}`} />
                    </div>
                    <h2 className="text-lg font-semibold text-surface-900 dark:text-surface-50 mb-2">
                        {isSuspended ? 'Account Suspended' : 'Account Rejected'}
                    </h2>
                    <p className="text-surface-500 dark:text-surface-400 mb-2">
                        {isSuspended
                            ? 'Your vendor account has been suspended. You cannot access the portal at this time.'
                            : 'Your vendor application was not approved.'}
                    </p>
                    <p className="text-sm text-surface-400 dark:text-surface-500 mb-6">
                        Please contact support at{' '}
                        <a href="mailto:support@event-ai.com" className="text-primary-600 hover:underline dark:text-primary-400">
                            support@event-ai.com
                        </a>{' '}
                        for assistance.
                    </p>
                    <button
                        onClick={() => logout().then(() => router.push('/login'))}
                        className="rounded-lg border border-surface-300 px-4 py-2 text-sm font-medium text-surface-700 hover:bg-surface-100 dark:border-surface-700 dark:text-surface-300 dark:hover:bg-surface-800"
                    >
                        Sign Out
                    </button>
                </div>
            </div>
        );
    }

    // PENDING vendors — awaiting admin approval screen (AUTH-05)
    if (vendorCheckStatus === 'done' && vendor && vendor.status === 'PENDING') {
        return (
            <div className="flex min-h-screen items-center justify-center bg-surface-50 dark:bg-surface-950 p-4">
                <div className="max-w-md text-center">
                    <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-yellow-100 dark:bg-yellow-900/30">
                        <AlertCircle className="h-7 w-7 text-yellow-600 dark:text-yellow-400" />
                    </div>
                    <h2 className="text-lg font-semibold text-surface-900 dark:text-surface-50 mb-2">
                        Awaiting Approval
                    </h2>
                    <p className="text-surface-500 dark:text-surface-400 mb-2">
                        Your vendor application is under review. You&apos;ll receive an email once it&apos;s approved.
                    </p>
                    <p className="text-sm text-surface-400 dark:text-surface-500 mb-6">
                        Questions? Contact{' '}
                        <a href="mailto:support@event-ai.com" className="text-primary-600 hover:underline dark:text-primary-400">
                            support@event-ai.com
                        </a>
                    </p>
                    <button
                        onClick={() => logout().then(() => router.push('/login'))}
                        className="rounded-lg border border-surface-300 px-4 py-2 text-sm font-medium text-surface-700 hover:bg-surface-100 dark:border-surface-700 dark:text-surface-300 dark:hover:bg-surface-800"
                    >
                        Sign Out
                    </button>
                </div>
            </div>
        );
    }


    const handleLogoutClick = () => {
        setShowLogoutConfirm(true);
    };

    const handleConfirmLogout = async () => {
        setIsLoggingOut(true);
        try {
            await logout();
            router.push('/login');
        } finally {
            setIsLoggingOut(false);
            setShowLogoutConfirm(false);
        }
    };

    // Show error state with retry option if check failed or timed out
    if (checkError || (vendorCheckStatus === 'done' && error)) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-surface-50 dark:bg-surface-950 p-4">
                <div className="max-w-md text-center">
                    <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/30">
                        <AlertCircle className="h-7 w-7 text-red-600 dark:text-red-400" />
                    </div>
                    <h2 className="text-lg font-semibold text-surface-900 dark:text-surface-50 mb-2">
                        Failed to load vendor profile
                    </h2>
                    <p className="text-surface-500 dark:text-surface-400 mb-6">
                        {checkError || error || 'An unexpected error occurred while loading your profile.'}
                    </p>
                    <div className="flex gap-3 justify-center">
                        <button
                            onClick={() => {
                                setCheckError(null);
                                clearError();
                                ensureVendorProfile();
                            }}
                            className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
                        >
                            <RefreshCw className="h-4 w-4" />
                            Retry
                        </button>
                        <button
                            onClick={() => {
                                logout().then(() => router.push('/login'));
                            }}
                            className="rounded-lg border border-surface-300 px-4 py-2 text-sm font-medium text-surface-700 hover:bg-surface-100 dark:border-surface-700 dark:text-surface-300 dark:hover:bg-surface-800"
                        >
                            Log Out
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    // Block all rendering until the vendor check resolves.
    if (sessionStatus !== 'done' || vendorCheckStatus !== 'done') {
        return (
            <div className="flex min-h-screen items-center justify-center bg-surface-50 dark:bg-surface-950">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
                <span className="ml-3 text-surface-500">
                    {sessionStatus !== 'done' ? 'Initializing session...' : 'Loading vendor profile...'}
                </span>
            </div>
        );
    }

    // Check done, no vendor — show spinner while redirect fires.
    if (!vendor) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-surface-50 dark:bg-surface-950">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
                <span className="ml-3 text-surface-500">Redirecting to onboarding...</span>
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
                    </div>
                    <button
                        onClick={handleLogoutClick}
                        className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-700 transition-colors hover:bg-red-100 dark:border-red-900/30 dark:bg-red-900/20 dark:text-red-400 dark:hover:bg-red-900/30"
                    >
                        <LogOut className="h-4 w-4" />
                        Sign Out
                    </button>
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

            {/* Logout Confirmation Dialog */}
            {showLogoutConfirm && (
                <>
                    <div className="fixed inset-0 z-50 bg-black/50" onClick={() => !isLoggingOut && setShowLogoutConfirm(false)} />
                    <div className="fixed left-1/2 top-1/2 z-50 w-full max-w-sm -translate-x-1/2 -translate-y-1/2 rounded-xl border border-surface-200 bg-white p-6 shadow-xl dark:border-surface-700 dark:bg-surface-900">
                        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/30">
                            <LogOut className="h-6 w-6 text-red-600 dark:text-red-400" />
                        </div>
                        <h3 className="mb-2 text-lg font-semibold text-surface-900 dark:text-surface-50">
                            Sign Out
                        </h3>
                        <p className="mb-6 text-surface-500 dark:text-surface-400">
                            Are you sure you want to sign out of your vendor account?
                        </p>
                        <div className="flex gap-3">
                            <button
                                onClick={() => setShowLogoutConfirm(false)}
                                disabled={isLoggingOut}
                                className="flex-1 rounded-lg border border-surface-300 px-4 py-2 text-sm font-medium text-surface-700 hover:bg-surface-50 disabled:opacity-50 dark:border-surface-700 dark:text-surface-300 dark:hover:bg-surface-800"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleConfirmLogout}
                                disabled={isLoggingOut}
                                className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
                            >
                                {isLoggingOut ? (
                                    <>
                                        <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                                        Signing out...
                                    </>
                                ) : (
                                    <>
                                        <LogOut className="h-4 w-4" />
                                        Sign Out
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}
