'use client';

import { useEffect } from 'react';
import { AlertCircle, RefreshCcw } from 'lucide-react';

/**
 * global-error.tsx — catches errors in the root layout itself.
 * Must include <html> and <body> since it replaces the root layout.
 */
export default function GlobalError({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    useEffect(() => {
        console.error('Global error:', error);
    }, [error]);

    return (
        <html lang="en">
            <body>
                <div
                    style={{
                        display: 'flex',
                        minHeight: '100vh',
                        alignItems: 'center',
                        justifyContent: 'center',
                        backgroundColor: '#f8fafc',
                        padding: '1rem',
                        fontFamily: 'system-ui, sans-serif',
                    }}
                >
                    <div
                        style={{
                            maxWidth: '28rem',
                            width: '100%',
                            textAlign: 'center',
                            padding: '2rem',
                            borderRadius: '0.75rem',
                            border: '1px solid #e2e8f0',
                            backgroundColor: '#ffffff',
                            boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)',
                        }}
                    >
                        <div
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                width: '4rem',
                                height: '4rem',
                                borderRadius: '50%',
                                backgroundColor: '#fee2e2',
                                margin: '0 auto 1.5rem',
                            }}
                        >
                            <AlertCircle style={{ width: '2rem', height: '2rem', color: '#dc2626' }} />
                        </div>
                        <h1 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#0f172a', marginBottom: '0.5rem' }}>
                            Something went wrong
                        </h1>
                        <p style={{ color: '#64748b', marginBottom: '1.5rem', fontSize: '0.875rem' }}>
                            A critical error occurred. Please refresh the page.
                            {error.digest && (
                                <span style={{ display: 'block', marginTop: '0.5rem', fontSize: '0.75rem', color: '#94a3b8' }}>
                                    Error ID: {error.digest}
                                </span>
                            )}
                        </p>
                        <button
                            onClick={reset}
                            style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '0.5rem',
                                padding: '0.625rem 1.25rem',
                                borderRadius: '0.5rem',
                                backgroundColor: '#2563eb',
                                color: '#ffffff',
                                fontSize: '0.875rem',
                                fontWeight: 500,
                                border: 'none',
                                cursor: 'pointer',
                            }}
                        >
                            <RefreshCcw style={{ width: '1rem', height: '1rem' }} />
                            Try Again
                        </button>
                    </div>
                </div>
            </body>
        </html>
    );
}
