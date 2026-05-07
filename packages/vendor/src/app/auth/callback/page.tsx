'use client';

import { useEffect, useRef, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { useAuthStore } from '@/lib/auth-store';

/**
 * Handles the post-OAuth redirect from the backend.
 *
 * Backend redirects to:
 *   {FRONTEND_URL}/auth/callback?token=<access_jwt>&refresh_token=<refresh_token>
 *
 * This page reads those params, stores the tokens, fetches /auth/me,
 * and redirects to /dashboard.
 */
function CallbackHandler() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const { loginWithTokens } = useAuthStore();
    const handled = useRef(false);

    useEffect(() => {
        if (handled.current) return;
        handled.current = true;

        const token = searchParams.get('token');
        const refreshToken = searchParams.get('refresh_token');
        const error = searchParams.get('error');

        if (error) {
            const messages: Record<string, string> = {
                google_auth_denied: 'Google sign-in was cancelled.',
                oauth_email_not_verified: 'Your Google email is not verified.',
                auth_account_inactive: 'Your account has been deactivated.',
                invalid_callback: 'Invalid sign-in callback. Please try again.',
            };
            const msg = encodeURIComponent(messages[error] ?? 'Google sign-in failed. Please try again.');
            router.replace(`/login?error=${msg}`);
            return;
        }

        if (!token || !refreshToken) {
            router.replace('/login?error=Missing+authentication+tokens');
            return;
        }

        loginWithTokens(token, refreshToken).then(() => {
            router.replace('/dashboard');
        });
    }, [searchParams, loginWithTokens, router]);

    return (
        <div className="flex min-h-screen items-center justify-center">
            <div className="flex flex-col items-center gap-4">
                <Loader2 className="h-10 w-10 animate-spin text-primary-600" />
                <p className="text-sm text-surface-500">Completing sign-in...</p>
            </div>
        </div>
    );
}

export default function AuthCallbackPage() {
    return (
        <Suspense
            fallback={
                <div className="flex min-h-screen items-center justify-center">
                    <Loader2 className="h-10 w-10 animate-spin text-primary-600" />
                </div>
            }
        >
            <CallbackHandler />
        </Suspense>
    );
}

