'use client';

import { useEffect, useRef, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { useAuthStore } from '@/lib/auth-store';

/**
 * Handles the post-OAuth redirect from the backend.
 *
 * Backend sets httpOnly cookies (access_token, refresh_token) and redirects to:
 *   {FRONTEND_URL}/auth/callback
 *
 * No tokens in the URL — cookies are already set by the backend redirect.
 * This page just fetches /users/me to hydrate the auth store, then goes to /dashboard.
 *
 * Error path: backend redirects to /login?error=<code> directly.
 */
function CallbackHandler() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const { loginWithTokens } = useAuthStore();
    const handled = useRef(false);

    useEffect(() => {
        if (handled.current) return;
        handled.current = true;

        // Backend may still pass an error param if OAuth failed
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

        // Cookies are already set by the backend — just hydrate the store
        // loginWithTokens ignores the token params and calls /users/me directly
        loginWithTokens('', '').then(() => {
            router.replace('/dashboard');
        }).catch(() => {
            router.replace('/login?error=Authentication+failed.+Please+try+again.');
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

