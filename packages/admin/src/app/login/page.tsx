"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Zap, Mail, Lock, Loader2, AlertCircle, Eye, EyeOff, ShieldCheck } from "lucide-react";
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
        <div className="fixed inset-0 overflow-auto" style={{
            background: "linear-gradient(135deg, #0d2240 0%, #1A3D64 40%, #2a5a8f 70%, #1A3D64 100%)"
        }}>
            {/* Mesh noise overlay for depth */}
            <div className="pointer-events-none absolute inset-0" style={{
                backgroundImage: "radial-gradient(ellipse at 20% 50%, rgba(26,61,100,0.3) 0%, transparent 60%), radial-gradient(ellipse at 80% 20%, rgba(150,167,141,0.15) 0%, transparent 50%), radial-gradient(ellipse at 60% 80%, rgba(239,236,227,0.06) 0%, transparent 50%)"
            }} />

            {/* Subtle grid pattern */}
            <div className="pointer-events-none absolute inset-0 opacity-[0.03]" style={{
                backgroundImage: "linear-gradient(rgba(255,255,255,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.5) 1px, transparent 1px)",
                backgroundSize: "40px 40px"
            }} />

            <div className="relative flex min-h-full items-center justify-center p-4">
                <div className="w-full max-w-[420px]">

                    {/* Glow ring behind card */}
                    <div className="absolute inset-0 rounded-3xl blur-3xl opacity-20"
                        style={{ background: "radial-gradient(circle, #1A3D64 0%, transparent 70%)" }} />

                    {/* Main card */}
                    <div className="relative rounded-3xl overflow-hidden"
                        style={{
                            background: "rgba(255,255,255,0.04)",
                            border: "1px solid rgba(255,255,255,0.08)",
                            boxShadow: "0 32px 64px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.08)"
                        }}>

                        {/* Top accent bar */}
                        <div className="h-0.5 w-full" style={{
                            background: "linear-gradient(90deg, transparent, #1A3D64, #96A78D, #1A3D64, transparent)"
                        }} />

                        <div className="p-8">
                            {/* Logo + title */}
                            <div className="flex flex-col items-center mb-8">
                                <div className="relative mb-5">
                                    <div className="absolute inset-0 rounded-2xl blur-xl opacity-60"
                                        style={{ background: "linear-gradient(135deg, #1A3D64, #96A78D)" }} />
                                    <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl"
                                        style={{
                                            background: "linear-gradient(135deg, #1A3D64, #2a5a8f)",
                                            boxShadow: "0 8px 32px rgba(26,61,100,0.5)"
                                        }}>
                                        <Zap className="h-8 w-8 text-white" />
                                    </div>
                                </div>
                                <h1 className="text-2xl font-bold text-white tracking-tight">Event-AI Admin</h1>
                                <div className="mt-2 flex items-center gap-1.5">
                                    <ShieldCheck className="h-3.5 w-3.5 text-[#96A78D]" />
                                    <p className="text-xs font-medium" style={{ color: "#96A78D" }}>Secure Management Portal</p>
                                </div>
                            </div>

                            {/* Error */}
                            {error && (
                                <div className="mb-5 flex items-start gap-3 rounded-xl px-4 py-3 text-sm"
                                    style={{
                                        background: "rgba(239,68,68,0.08)",
                                        border: "1px solid rgba(239,68,68,0.2)"
                                    }}>
                                    <AlertCircle className="h-4 w-4 text-red-400 flex-shrink-0 mt-0.5" />
                                    <span className="text-red-300">{error}</span>
                                </div>
                            )}

                            <form onSubmit={handleSubmit} className="space-y-4">
                                {/* Email */}
                                <div>
                                    <label className="block text-[11px] font-semibold uppercase tracking-widest mb-2"
                                        style={{ color: "rgba(150,167,141,0.8)" }}>
                                        Email Address
                                    </label>
                                    <div className="relative">
                                        <Mail className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4"
                                            style={{ color: "rgba(150,167,141,0.5)" }} />
                                        <input
                                            type="email"
                                            required
                                            value={email}
                                            onChange={(e) => setEmail(e.target.value)}
                                            placeholder="admin@eventai.com"
                                            className="w-full rounded-xl pl-11 pr-4 py-3 text-sm text-white placeholder-white/20 outline-none transition-all"
                                            style={{
                                                background: "rgba(255,255,255,0.05)",
                                                border: "1px solid rgba(255,255,255,0.08)",
                                            }}
                                            onFocus={(e) => {
                                                e.target.style.border = "1px solid rgba(150,167,141,0.6)";
                                                e.target.style.boxShadow = "0 0 0 3px rgba(150,167,141,0.12)";
                                            }}
                                            onBlur={(e) => {
                                                e.target.style.border = "1px solid rgba(255,255,255,0.08)";
                                                e.target.style.boxShadow = "none";
                                            }}
                                        />
                                    </div>
                                </div>

                                {/* Password */}
                                <div>
                                    <label className="block text-[11px] font-semibold uppercase tracking-widest mb-2"
                                        style={{ color: "rgba(150,167,141,0.8)" }}>
                                        Password
                                    </label>
                                    <div className="relative">
                                        <Lock className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4"
                                            style={{ color: "rgba(150,167,141,0.5)" }} />
                                        <input
                                            type={showPassword ? "text" : "password"}
                                            required
                                            value={password}
                                            onChange={(e) => setPassword(e.target.value)}
                                            placeholder="••••••••••"
                                            className="w-full rounded-xl pl-11 pr-12 py-3 text-sm text-white placeholder-white/20 outline-none transition-all"
                                            style={{
                                                background: "rgba(255,255,255,0.05)",
                                                border: "1px solid rgba(255,255,255,0.08)",
                                            }}
                                            onFocus={(e) => {
                                                e.target.style.border = "1px solid rgba(150,167,141,0.6)";
                                                e.target.style.boxShadow = "0 0 0 3px rgba(150,167,141,0.12)";
                                            }}
                                            onBlur={(e) => {
                                                e.target.style.border = "1px solid rgba(255,255,255,0.08)";
                                                e.target.style.boxShadow = "none";
                                            }}
                                        />
                                        <button type="button" onClick={() => setShowPassword(!showPassword)}
                                            className="absolute right-4 top-1/2 -translate-y-1/2 transition-colors"
                                            style={{ color: "rgba(150,167,141,0.5)" }}>
                                            {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                                        </button>
                                    </div>
                                </div>

                                {/* Submit */}
                                <button
                                    type="submit"
                                    disabled={loading}
                                    className="mt-2 w-full flex items-center justify-center gap-2 rounded-xl py-3 text-sm font-semibold text-white transition-all duration-200 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
                                    style={{
                                        background: "linear-gradient(135deg, #1A3D64, #2a5a8f)",
                                        boxShadow: "0 4px 24px rgba(26,61,100,0.4)"
                                    }}
                                    onMouseEnter={(e) => {
                                        (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 4px 32px rgba(26,61,100,0.6)";
                                    }}
                                    onMouseLeave={(e) => {
                                        (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 4px 24px rgba(26,61,100,0.4)";
                                    }}
                                >
                                    {loading ? (
                                        <><Loader2 className="h-4 w-4 animate-spin" /> Authenticating...</>
                                    ) : (
                                        "Sign in to Admin Portal"
                                    )}
                                </button>
                            </form>

                            {/* Stats */}
                            <div className="mt-7 grid grid-cols-3 gap-2.5">
                                {[
                                    { value: "500+", label: "Vendors" },
                                    { value: "10K+", label: "Events" },
                                    { value: "99.9%", label: "Uptime" },
                                ].map((s) => (
                                    <div key={s.label} className="rounded-xl py-3 text-center"
                                        style={{
                                            background: "rgba(150,167,141,0.06)",
                                            border: "1px solid rgba(150,167,141,0.15)"
                                        }}>
                                        <p className="text-sm font-bold text-white">{s.value}</p>
                                        <p className="text-[10px] mt-0.5" style={{ color: "rgba(150,167,141,0.6)" }}>{s.label}</p>
                                    </div>
                                ))}
                            </div>

                            <p className="mt-5 text-center text-[11px]" style={{ color: "rgba(255,255,255,0.15)" }}>
                                Protected · Unauthorized access is prohibited
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
