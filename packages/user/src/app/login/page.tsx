"use client";

import { useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Eye, EyeOff, Loader2, AlertCircle, CheckCircle, Clock, Sparkles } from "lucide-react";
import Image from "next/image";

// ─── Google SVG ───────────────────────────────────────────────────────────────
function GoogleIcon({ className }: { className?: string }) {
    return (
        <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
            <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
            <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
            <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
            <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
        </svg>
    );
}

// ─── Testimonials for the left panel ─────────────────────────────────────────
const testimonials = [
    { name: "Ayesha Khan", role: "Wedding Planner, Lahore", text: "Found the perfect photographer and caterer in one afternoon. Event-AI is a game changer." },
    { name: "Bilal Ahmed", role: "Corporate Events, Karachi", text: "The AI recommendations saved us weeks of vendor research for our annual conference." },
];

// ─── Login Form ───────────────────────────────────────────────────────────────
function LoginForm() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const registered = searchParams.get("registered");
    const oauthError = searchParams.get("error");

    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const [error, setError] = useState(oauthError || "");
    const [loading, setLoading] = useState(false);
    const [googleLoading, setGoogleLoading] = useState(false);
    const [pendingMessage, setPendingMessage] = useState(false);
    const [rejectedMessage, setRejectedMessage] = useState(false);

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000/api/v1";

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setPendingMessage(false);
        setRejectedMessage(false);
        setLoading(true);

        try {
            const response = await fetch(`${API_URL}/users/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "include",
                body: JSON.stringify({ email, password }),
            });

            const data = await response.json();

            if (!response.ok) {
                if (data.code === "PENDING_APPROVAL") { setPendingMessage(true); setLoading(false); return; }
                if (data.code === "ACCOUNT_REJECTED") { setRejectedMessage(true); setLoading(false); return; }
                throw new Error(data.error?.message || data.error || "Login failed");
            }

            // Store tokens in localStorage (consistent with OAuth flow)
            if (data.data?.token && data.data?.refresh_token) {
                localStorage.setItem("access_token", data.data.token);
                localStorage.setItem("refresh_token", data.data.refresh_token);
            }

            const callbackUrl = searchParams.get("callbackUrl") || "/dashboard";
            router.push(callbackUrl);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Invalid email or password");
            setLoading(false);
        }
    };

    const handleGoogleSignIn = async () => {
        setGoogleLoading(true);
        try {
            // Pass the portal origin so the backend redirects back to the correct portal
            const origin = window.location.origin; // e.g. http://localhost:3003
            window.location.href = `${API_URL}/auth/google?frontend_origin=${encodeURIComponent(origin)}`;
        } catch {
            setGoogleLoading(false);
        }
    };

    return (
        <div className="min-h-screen grid lg:grid-cols-2">
            {/* ── Left: Branding Panel ── */}
            <div className="hidden lg:flex flex-col justify-between relative overflow-hidden p-12 text-white"
                style={{ background: "linear-gradient(135deg, #1A3D64 0%, #2a5a8f 50%, #1A3D64 100%)" }}>
                {/* Decorative blobs */}
                <div className="absolute -top-24 -right-24 h-96 w-96 rounded-full bg-white/5 blur-3xl" />
                <div className="absolute -bottom-24 -left-24 h-96 w-96 rounded-full bg-[#96A78D]/15 blur-3xl" />
                <div className="absolute top-1/2 right-0 h-64 w-64 rounded-full bg-[#EFECE3]/5 blur-2xl" />

                {/* Logo */}
                <div className="relative flex items-center gap-3">
                    <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/20 backdrop-blur-sm shadow-lg overflow-hidden">
                        <Image src="/logo.png" alt="Event-AI" width={44} height={44} className="object-contain" />
                    </div>
                    <div>
                        <span className="text-xl font-bold">Event-AI</span>
                        <div className="flex items-center gap-1 mt-0.5">
                            <Sparkles className="h-3 w-3 text-[#96A78D]" />
                            <span className="text-xs text-[#96A78D]">AI-Powered Planning</span>
                        </div>
                    </div>
                </div>

                {/* Main copy */}
                <div className="relative">
                    <h2 className="text-4xl font-bold leading-tight mb-4">
                        Plan unforgettable events with AI
                    </h2>
                    <p className="text-[#EFECE3]/70 text-lg leading-relaxed">
                        Discover top vendors, get smart recommendations, and manage everything from weddings to corporate events — all in one place.
                    </p>
                </div>

                {/* Testimonial */}
                <div className="relative rounded-2xl bg-white/10 backdrop-blur-sm border border-white/10 p-6">
                    <p className="text-sm text-[#EFECE3]/80 leading-relaxed italic">
                        &ldquo;{testimonials[0].text}&rdquo;
                    </p>
                    <div className="mt-4 flex items-center gap-3">
                        <div className="h-9 w-9 rounded-full bg-white/20 flex items-center justify-center text-sm font-bold">
                            {testimonials[0].name[0]}
                        </div>
                        <div>
                            <p className="text-sm font-semibold text-white">{testimonials[0].name}</p>
                            <p className="text-xs text-[#96A78D]">{testimonials[0].role}</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* ── Right: Login Form ── */}
            <div className="flex items-center justify-center px-4 py-12 sm:px-8 bg-canvas-100 dark:bg-surface-950">
                <div className="w-full max-w-md">
                    {/* Mobile logo */}
                    <div className="flex items-center justify-center gap-2 mb-8 lg:hidden">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg overflow-hidden">
                            <Image src="/logo.png" alt="Event-AI" width={40} height={40} className="object-contain" />
                        </div>
                        <span className="text-xl font-bold text-primary-600 dark:text-primary-400">Event-AI</span>
                    </div>

                    <div className="rounded-xl border border-surface-200 bg-white shadow-lg p-8 dark:border-surface-800 dark:bg-surface-900">
                        <div className="mb-8">
                            <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-50">Welcome back</h1>
                            <p className="mt-1 text-sm text-surface-500 dark:text-surface-400">Sign in to your Event-AI account</p>
                        </div>

                        {/* Status banners */}
                        {registered && (
                            <div className="flex items-start gap-3 rounded-lg bg-success-50 border border-success-100 px-4 py-3 text-sm text-success-700 mb-6 dark:bg-success-900/20 dark:border-success-800 dark:text-success-400">
                                <CheckCircle className="h-4 w-4 mt-0.5 shrink-0" />
                                Account created! Waiting for admin approval.
                            </div>
                        )}
                        {pendingMessage && (
                            <div className="flex items-start gap-3 rounded-lg bg-warning-50 border border-warning-100 px-4 py-3 text-sm text-warning-700 mb-6 dark:bg-warning-900/20 dark:border-warning-800 dark:text-warning-400">
                                <Clock className="h-4 w-4 mt-0.5 shrink-0" />
                                Your account is pending admin approval. Please check back later.
                            </div>
                        )}
                        {rejectedMessage && (
                            <div className="flex items-start gap-3 rounded-lg bg-error-50 border border-error-100 px-4 py-3 text-sm text-error-700 mb-6 dark:bg-error-900/20 dark:border-error-800 dark:text-error-400">
                                <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                                Your account has been rejected. Contact support for assistance.
                            </div>
                        )}
                        {error && (
                            <div className="flex items-start gap-3 rounded-lg bg-error-50 border border-error-100 px-4 py-3 text-sm text-error-700 mb-6 dark:bg-error-900/20 dark:border-error-800 dark:text-error-400">
                                <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                                {error}
                            </div>
                        )}

                        {/* Google Sign-In */}
                        <button
                            type="button"
                            onClick={handleGoogleSignIn}
                            disabled={googleLoading || loading}
                            className="w-full flex items-center justify-center gap-3 rounded-lg border border-surface-300 bg-white px-4 py-3 text-sm font-medium text-surface-700 shadow-sm hover:bg-surface-50 hover:border-surface-400 active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed transition-all dark:border-surface-700 dark:bg-surface-900 dark:text-surface-300 dark:hover:bg-surface-800"
                        >
                            {googleLoading ? (
                                <Loader2 className="h-5 w-5 animate-spin text-surface-400" />
                            ) : (
                                <GoogleIcon className="h-5 w-5" />
                            )}
                            {googleLoading ? "Connecting..." : "Continue with Google"}
                        </button>

                        {/* Divider */}
                        <div className="relative my-6">
                            <div className="absolute inset-0 flex items-center">
                                <div className="w-full border-t border-surface-200 dark:border-surface-700" />
                            </div>
                            <div className="relative flex justify-center text-xs uppercase">
                                <span className="bg-white px-3 text-surface-400 font-medium tracking-wider dark:bg-surface-900">or</span>
                            </div>
                        </div>

                        {/* Email/Password Form */}
                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div className="space-y-1.5">
                                <label htmlFor="email" className="text-sm font-medium text-surface-700 dark:text-surface-300">
                                    Email address
                                </label>
                                <input
                                    id="email"
                                    type="email"
                                    required
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    placeholder="you@example.com"
                                    className="w-full rounded-lg border border-surface-300 bg-white px-4 py-3 text-sm text-surface-900 placeholder:text-surface-400 hover:border-surface-400 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all dark:border-surface-700 dark:bg-surface-900 dark:text-surface-100 dark:placeholder:text-surface-500"
                                />
                            </div>

                            <div className="space-y-1.5">
                                <div className="flex items-center justify-between">
                                    <label htmlFor="password" className="text-sm font-medium text-surface-700 dark:text-surface-300">
                                        Password
                                    </label>
                                    <Link href="/forgot-password" className="text-xs font-medium text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300">
                                        Forgot password?
                                    </Link>
                                </div>
                                <div className="relative">
                                    <input
                                        id="password"
                                        type={showPassword ? "text" : "password"}
                                        required
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        placeholder="Enter your password"
                                        className="w-full rounded-lg border border-surface-300 bg-white px-4 py-3 pr-11 text-sm text-surface-900 placeholder:text-surface-400 hover:border-surface-400 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all dark:border-surface-700 dark:bg-surface-900 dark:text-surface-100 dark:placeholder:text-surface-500"
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowPassword(!showPassword)}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 text-surface-400 hover:text-surface-600 transition-colors dark:hover:text-surface-300"
                                        aria-label={showPassword ? "Hide password" : "Show password"}
                                    >
                                        {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                                    </button>
                                </div>
                            </div>

                            <button
                                type="submit"
                                disabled={loading || googleLoading}
                                className="w-full flex items-center justify-center gap-2 rounded-lg bg-primary-600 px-4 py-3 text-sm font-semibold text-white hover:bg-primary-700 active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed transition-all shadow-sm"
                            >
                                {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                                {loading ? "Signing in..." : "Sign in"}
                            </button>
                        </form>

                        <p className="mt-6 text-center text-sm text-surface-500 dark:text-surface-400">
                            Don&apos;t have an account?{" "}
                            <Link href="/signup" className="font-semibold text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300">
                                Create one free
                            </Link>
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default function LoginPage() {
    return (
        <Suspense fallback={
            <div className="min-h-screen flex items-center justify-center bg-[#EFECE3]">
                <div className="flex flex-col items-center gap-3">
                    <div className="h-10 w-10 rounded-xl overflow-hidden">
                        <Image src="/logo.png" alt="Event-AI" width={40} height={40} className="object-contain" />
                    </div>
                    <Loader2 className="h-5 w-5 animate-spin text-[#1A3D64]" />
                </div>
            </div>
        }>
            <LoginForm />
        </Suspense>
    );
}
