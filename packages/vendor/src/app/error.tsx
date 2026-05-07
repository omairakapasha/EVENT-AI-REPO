'use client';

import { useEffect, useState } from 'react';
import { AlertCircle, RefreshCcw, Home, LogOut } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/auth-store';

interface ErrorProps {
    error: Error & { digest?: string };
    reset: () => void;
}

export default function Error({ error, reset }: ErrorProps) {
    const router = useRouter();
    const { logout } = useAuthStore();
    const [isResetting, setIsResetting] = useState(false);
    const [isLoggingOut, setIsLoggingOut] = useState(false);
    const [retryCount, setRetryCount] = useState(0);
    const MAX_RETRIES = 3;

    useEffect(() => {
        // Log the error to console for debugging
        console.error('Dashboard Error:', error);
    }, [error]);

    const handleReset = async () => {
        if (retryCount >= MAX_RETRIES) {
            return;
        }
        setIsResetting(true);
        setRetryCount(prev => prev + 1);
        try {
            reset();
        } finally {
            setTimeout(() => setIsResetting(false), 500);
        }
    };

    const handleLogout = async () => {
        setIsLoggingOut(true);
        try {
            await logout();
            router.push('/login');
        } finally {
            setIsLoggingOut(false);
        }
    };

    const hasExceededRetries = retryCount >= MAX_RETRIES;

    return (
        <div className="flex min-h-screen items-center justify-center bg-surface-50 p-4 dark:bg-surface-950">
            <div className="w-full max-w-md rounded-xl border border-surface-200 bg-white p-8 text-center shadow-lg dark:border-surface-800 dark:bg-surface-900">
                <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/30">
                    <AlertCircle className="h-8 w-8 text-red-600 dark:text-red-400" />
                </div>

                <h1 className="mb-2 text-xl font-bold text-surface-900 dark:text-surface-50">
                    {hasExceededRetries ? 'Unable to Recover' : 'Something went wrong'}
                </h1>

                <p className="mb-4 text-surface-500 dark:text-surface-400">
                    {hasExceededRetries
                        ? 'We tried multiple times but couldn\'t recover from this error. Please try signing out and back in.'
                        : 'We encountered an error while loading this page. Please try again.'}
                </p>

                {retryCount > 0 && !hasExceededRetries && (
                    <p className="mb-4 text-xs text-surface-400">
                        Retry attempt {retryCount} of {MAX_RETRIES}
                    </p>
                )}

                {error.digest && (
                    <p className="mb-4 text-xs text-surface-400">
                        Error ID: {error.digest}
                    </p>
                )}

                <div className="flex flex-col gap-3">
                    {!hasExceededRetries ? (
                        <button
                            onClick={handleReset}
                            disabled={isResetting}
                            className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary-700 disabled:opacity-50"
                        >
                            {isResetting ? (
                                <>
                                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                                    Retrying...
                                </>
                            ) : (
                                <>
                                    <RefreshCcw className="h-4 w-4" />
                                    Try Again
                                </>
                            )}
                        </button>
                    ) : (
                        <button
                            onClick={handleLogout}
                            disabled={isLoggingOut}
                            className="flex w-full items-center justify-center gap-2 rounded-lg bg-red-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-red-700 disabled:opacity-50"
                        >
                            {isLoggingOut ? (
                                <>
                                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                                    Signing out...
                                </>
                            ) : (
                                <>
                                    <LogOut className="h-4 w-4" />
                                    Sign Out & Retry
                                </>
                            )}
                        </button>
                    )}

                    <Link
                        href="/dashboard"
                        className="flex w-full items-center justify-center gap-2 rounded-lg border border-surface-300 bg-white px-4 py-2.5 text-sm font-medium text-surface-700 transition-colors hover:bg-surface-50 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-300 dark:hover:bg-surface-700"
                    >
                        <Home className="h-4 w-4" />
                        Go to Dashboard
                    </Link>

                    {retryCount > 0 && (
                        <button
                            onClick={() => setRetryCount(0)}
                            className="text-xs text-surface-400 hover:text-surface-600 underline"
                        >
                            Reset retry counter
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
