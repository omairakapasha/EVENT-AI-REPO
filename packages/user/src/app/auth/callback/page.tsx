"use client";

import { useEffect, useRef, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import Image from "next/image";

/**
 * OAuth callback handler for the user portal.
 *
 * After a successful Google OAuth flow the backend:
 *   1. Sets httpOnly cookies (access_token, refresh_token)
 *   2. Redirects to this page (a public route)
 *
 * This page:
 *   1. Checks auth by calling /users/me
 *   2. Redirects to /dashboard on success
 *   3. Redirects to /login on error
 */
const ERROR_MESSAGES: Record<string, string> = {
    google_auth_denied: "Google sign-in was cancelled.",
    oauth_email_not_verified: "Your Google email is not verified.",
    auth_account_inactive: "Your account has been deactivated. Contact support.",
    invalid_callback: "Invalid sign-in callback. Please try again.",
    oauth_invalid_state: "Sign-in session expired. Please try again.",
    oauth_token_exchange_failed: "Google sign-in failed. Please try again.",
    oauth_not_configured: "Google sign-in is not available right now.",
};

function CallbackHandler() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const handled = useRef(false);
    const tokensStored = useRef(false);

    useEffect(() => {
        // Guard against React strict-mode double-invocation
        if (handled.current) {
            console.log("[OAuth Callback] Already handled, skipping");
            return;
        }
        handled.current = true;

        const error = searchParams.get("error");
        const accessToken = searchParams.get("access_token");
        const refreshToken = searchParams.get("refresh_token");

        console.log("[OAuth Callback] error:", error);
        console.log("[OAuth Callback] accessToken:", accessToken ? "present" : "missing");
        console.log("[OAuth Callback] refreshToken:", refreshToken ? "present" : "missing");

        // ── Error redirect from backend ──────────────────────────────
        if (error) {
            const msg = encodeURIComponent(
                ERROR_MESSAGES[error] ?? "Google sign-in failed. Please try again."
            );
            console.log("[OAuth Callback] Redirecting to login with error:", error);
            router.replace(`/login?error=${msg}`);
            return;
        }

        // ── Tokens passed via URL (cross-domain OAuth) ──────────────
        if (accessToken && refreshToken && !tokensStored.current) {
            console.log("[OAuth Callback] Storing tokens in localStorage");
            tokensStored.current = true;
            
            // Store tokens synchronously
            localStorage.setItem("access_token", accessToken);
            localStorage.setItem("refresh_token", refreshToken);
            
            // Verify tokens were stored
            const storedAccess = localStorage.getItem("access_token");
            const storedRefresh = localStorage.getItem("refresh_token");
            console.log("[OAuth Callback] Tokens stored successfully:", {
                access: !!storedAccess,
                refresh: !!storedRefresh
            });
            
            // Use window.location for hard redirect (more reliable than router.replace)
            console.log("[OAuth Callback] Redirecting to dashboard with window.location");
            setTimeout(() => {
                window.location.href = "/dashboard";
            }, 100);
            return;
        }

        // ── Fallback: Verify auth via API (httpOnly cookies for localhost dev) ──
        console.log("[OAuth Callback] No tokens in URL, trying cookie auth");
        fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000/api/v1"}/users/me`, {
            credentials: "include",
        })
            .then((res) => {
                console.log("[OAuth Callback] /users/me response status:", res.status);
                if (res.ok) {
                    router.replace("/dashboard");
                } else {
                    router.replace(
                        "/login?" +
                            encodeURIComponent("Authentication failed. Please try again.")
                    );
                }
            })
            .catch((err) => {
                console.error("[OAuth Callback] /users/me error:", err);
                router.replace(
                    "/login?" +
                        encodeURIComponent("Authentication failed. Please try again.")
                );
            });
    }, [searchParams, router]);

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
            <div className="flex flex-col items-center gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl shadow-lg overflow-hidden">
                    <Image src="/logo.png" alt="Event-AI" width={48} height={48} className="object-contain" />
                </div>
                <Loader2 className="h-6 w-6 animate-spin text-indigo-600" />
                <p className="text-sm text-gray-500">Completing sign-in...</p>
            </div>
        </div>
    );
}

export default function AuthCallbackPage() {
    return (
        <Suspense
            fallback={
                <div className="min-h-screen flex items-center justify-center bg-gray-50">
                    <div className="flex flex-col items-center gap-3">
                        <div className="h-10 w-10 rounded-xl flex items-center justify-center overflow-hidden">
                            <Image src="/logo.png" alt="Event-AI" width={40} height={40} className="object-contain" />
                        </div>
                        <Loader2 className="h-5 w-5 animate-spin text-indigo-600" />
                    </div>
                </div>
            }
        >
            <CallbackHandler />
        </Suspense>
    );
}
