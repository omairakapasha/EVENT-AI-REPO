"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Mail, Lock, Loader2, AlertCircle, Eye, EyeOff, ShieldCheck } from "lucide-react";
import Image from "next/image";
import api, { getApiError } from "@/lib/api";

export default function LoginPage() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);
    const router = useRouter();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setLoading(true);
        try {
            const response = await api.post('/users/login', { email, password });
            const user = response.data?.data?.user ?? response.data?.user;
            if (user?.role !== 'admin') {
                setError("Access denied. Only admin accounts can access this portal.");
                // Log out immediately — backend set cookies but user isn't admin
                await api.post('/auth/logout').catch(() => {});
                setLoading(false);
                return;
            }
            router.push("/");
            router.refresh();
        } catch (err) {
            setError(getApiError(err) || "Invalid credentials. Only admin accounts can access this portal.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen grid lg:grid-cols-2">
            {/* ── Left: Admin Branding Panel ── */}
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
                        <span className="text-xl font-bold">Event-AI Admin</span>
                        <div className="flex items-center gap-1 mt-0.5">
                            <ShieldCheck className="h-3 w-3 text-[#96A78D]" />
                            <span className="text-xs text-[#96A78D]">Secure Management Portal</span>
                        </div>
                    </div>
                </div>

                {/* Main copy */}
                <div className="relative">
                    <h2 className="text-4xl font-bold leading-tight mb-4">
                        Platform Administration
                    </h2>
                    <p className="text-[#EFECE3]/70 text-lg leading-relaxed">
                        Manage users, vendors, bookings, and platform analytics with powerful admin tools and AI insights.
                    </p>
                </div>

                {/* Security notice */}
                <div className="relative rounded-2xl bg-white/10 backdrop-blur-sm border border-white/10 p-6">
                    <div className="flex items-start gap-3">
                        <ShieldCheck className="h-5 w-5 text-[#96A78D] flex-shrink-0 mt-0.5" />
                        <div>
                            <p className="text-sm font-semibold text-white mb-1">Protected Access</p>
                            <p className="text-xs text-[#EFECE3]/70 leading-relaxed">
                                This portal is restricted to authorized administrators only. All actions are logged and monitored.
                            </p>
                        </div>
                    </div>
                </div>
            </div>

            {/* ── Right: Login Form ── */}
            <div className="flex items-center justify-center px-4 py-12 sm:px-8 bg-canvas-100">
                <div className="w-full max-w-md">
                    {/* Mobile logo */}
                    <div className="flex items-center justify-center gap-2 mb-8 lg:hidden">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg overflow-hidden">
                            <Image src="/logo.png" alt="Event-AI" width={40} height={40} className="object-contain" />
                        </div>
                        <span className="text-xl font-bold text-primary-600">Event-AI Admin</span>
                    </div>

                    <div className="rounded-xl border border-surface-200 bg-white shadow-lg p-8"
                        style={{ borderColor: "#dedad0" }}>

                        <div className="mb-8">
                            <h1 className="text-2xl font-bold text-surface-900">Welcome back</h1>
                            <p className="mt-1 text-sm text-surface-500">Sign in to the admin portal</p>
                        </div>

                        {/* Error */}
                        {error && (
                            <div className="mb-6 flex items-start gap-3 rounded-lg bg-error-50 border border-error-100 px-4 py-3 text-sm text-error-700">
                                <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                                <span>{error}</span>
                            </div>
                        )}

                        <form onSubmit={handleSubmit} className="space-y-4">
                            {/* Email */}
                            <div className="space-y-1.5">
                                <label htmlFor="email" className="text-sm font-medium text-surface-700">
                                    Email address
                                </label>
                                <div className="relative">
                                    <Mail className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-surface-400" />
                                    <input
                                        id="email"
                                        type="email"
                                        required
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        placeholder="admin@eventai.com"
                                        className="w-full rounded-lg border border-surface-300 bg-white pl-11 pr-4 py-3 text-sm text-surface-900 placeholder:text-surface-400 hover:border-surface-400 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all"
                                        style={{ borderColor: "#ccc8be" }}
                                    />
                                </div>
                            </div>

                            {/* Password */}
                            <div className="space-y-1.5">
                                <label htmlFor="password" className="text-sm font-medium text-surface-700">
                                    Password
                                </label>
                                <div className="relative">
                                    <Lock className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-surface-400" />
                                    <input
                                        id="password"
                                        type={showPassword ? "text" : "password"}
                                        required
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        placeholder="Enter your password"
                                        className="w-full rounded-lg border border-surface-300 bg-white pl-11 pr-12 py-3 text-sm text-surface-900 placeholder:text-surface-400 hover:border-surface-400 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all"
                                        style={{ borderColor: "#ccc8be" }}
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowPassword(!showPassword)}
                                        className="absolute right-4 top-1/2 -translate-y-1/2 text-surface-400 hover:text-surface-600 transition-colors"
                                        aria-label={showPassword ? "Hide password" : "Show password"}
                                    >
                                        {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                                    </button>
                                </div>
                            </div>

                            {/* Submit */}
                            <button
                                type="submit"
                                disabled={loading}
                                className="w-full flex items-center justify-center gap-2 rounded-lg bg-primary-600 px-4 py-3 text-sm font-semibold text-white hover:bg-primary-700 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
                            >
                                {loading ? (
                                    <><Loader2 className="h-4 w-4 animate-spin" /> Authenticating...</>
                                ) : (
                                    "Sign in to Admin Portal"
                                )}
                            </button>
                        </form>

                        <p className="mt-6 text-center text-xs text-surface-400">
                            Protected · Unauthorized access is prohibited
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
