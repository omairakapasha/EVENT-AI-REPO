'use client';

import { useEffect } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

export default function Error({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    useEffect(() => {
        console.error('Vendor Portal Error:', error);
    }, [error]);

    return (
        <div className="min-h-screen flex items-center justify-center bg-surface-50 px-4">
            <div className="text-center max-w-md">
                <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-red-100">
                    <AlertTriangle className="h-8 w-8 text-red-600" />
                </div>
                <h2 className="text-xl font-bold text-surface-900 mb-2">Something went wrong</h2>
                <p className="text-surface-500 text-sm mb-6">
                    An unexpected error occurred. Our team has been notified.
                </p>
                <button
                    onClick={reset}
                    className="inline-flex items-center gap-2 px-4 py-2.5 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 transition-colors"
                >
                    <RefreshCw className="h-4 w-4" />
                    Try Again
                </button>
                <p className="mt-4 text-xs text-surface-400">
                    Error ID: {error.digest || 'unknown'}
                </p>
            </div>
        </div>
    );
}
