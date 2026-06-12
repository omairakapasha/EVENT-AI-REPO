"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import {
    Eye, EyeOff, Loader2, AlertCircle, CheckCircle,
    Calendar, Sparkles, ArrowRight, Shield, Users,
} from "lucide-react";

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

// ─── Password strength ────────────────────────────────────────────────────────
function getPasswordStrength(password: string): number {
    let score = 0;
    if (password.length >= 8) score++;
    if (/[A-Z]/.test(password)) score++;
    if (/[0-9]/.test(password)) score++;
    if (/[^A-Za-z0-9]/.test(password)) score++;
    return score;
}

const strengthLabels = ["", "Weak", "Fair", "Good", "Strong"];
const strengthColors = ["", "bg-red-500", "bg-yellow-500", "bg-blue-500", "bg-green-500"];
const strengthTextColors = ["", "text-red-600", "text-yellow-600", "text-blue-600", "text-green-600"];

export default function SignupPage() {
    const router = useRouter();
    const [formData, setFormData] = useState({
        firstName: "",
        lastName: "",
        email: "",
        phone: "",
        password: "",
        confirmPassword: "",
    });
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirm, setShowConfirm] = useState(false);
    const [error, setError] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [googleLoading, setGoogleLoading] = useState(false);
    const [success, setSuccess] = useState(false);

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000/api/v1";
    const strength = getPasswordStrength(formData.password);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleGoogleSignUp = async () => {
        setGoogleLoading(true);
        window.location.href = `${API_URL}/auth/google`;
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");

        if (formData.password !== formData.confirmPassword) {
            setError("Passwords do not match");
            return;
        }
        if (formData.password.length < 12) {
            setError("Password must be at least 12 characters");
            return;
        }

        setIsLoading(true);
        try {
            const response = await fetch(`${API_URL}/auth/register`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    first_name: formData.firstName,
                    last_name: formData.lastName,
                    email: formData.email,
                    password: formData.password,
                }),
            });

            const data = await response.json();
            if (!response.ok) throw new Error(data.error?.message || data.error || "Registration failed");

            setSuccess(true);
            setTimeout(() => router.push("/login?registered=true"), 3000);
        } catch (err) {
            setError(err instanceof Error ? err.message : "An error occurred during registration");
        } finally {
            setIsLoading(false);
        }
    };

    // ── Success screen ──────────────────────────────────────────────────────
    if (success) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-50 via-white to-purple-50 px-4">
                <div className="w-full max-w-md text-center">
                    <div className="bg-white rounded-2xl shadow-xl border border-gray-100 p-10">
                        <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
                            <CheckCircle className="h-8 w-8 text-green-600" />
                        </div>
                        <h1 className="text-2xl font-bold text-gray-900">Account Created!</h1>
                        <p className="mt-3 text-gray-500 leading-relaxed">
                            Your account is pending admin approval. You&apos;ll be able to sign in once approved.
                        </p>
                        <p className="mt-2 text-sm text-gray-400">Redirecting to login...</p>
                        <Link
                            href="/login"
                            className="mt-6 inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-6 py-3 text-sm font-semibold text-white hover:bg-indigo-700 transition-colors"
                        >
                            Go to Login <ArrowRight className="h-4 w-4" />
                        </Link>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen grid lg:grid-cols-2">
            {/* ── Left: Branding Panel ── */}
            <div className="hidden lg:flex flex-col justify-between relative overflow-hidden bg-gradient-to-br from-indigo-600 via-indigo-700 to-purple-800 p-12 text-white">
                <div className="absolute -top-24 -right-24 h-96 w-96 rounded-full bg-white/5 blur-3xl" />
                <div className="absolute -bottom-24 -left-24 h-96 w-96 rounded-full bg-purple-500/20 blur-3xl" />

                {/* Logo */}
                <div className="relative flex items-center gap-3">
                    <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/20 backdrop-blur-sm shadow-lg overflow-hidden">
                        <Image src="/logo.png" alt="Event-AI" width={44} height={44} className="object-contain" />
                    </div>
                    <div>
                        <span className="text-xl font-bold">Event-AI</span>
                        <div className="flex items-center gap-1 mt-0.5">
                            <Sparkles className="h-3 w-3 text-indigo-200" />
                            <span className="text-xs text-indigo-200">AI-Powered Planning</span>
                        </div>
                    </div>
                </div>

                {/* Main copy */}
                <div className="relative">
                    <h2 className="text-4xl font-bold leading-tight mb-4">
                        Start planning your perfect event today
                    </h2>
                    <p className="text-indigo-200 text-lg leading-relaxed mb-8">
                        Join thousands of event planners who use Event-AI to discover vendors, get AI recommendations, and create unforgettable experiences.
                    </p>

                    {/* Feature list */}
                    <div className="space-y-4">
                        {[
                            { icon: Sparkles, text: "AI-powered vendor recommendations" },
                            { icon: Shield, text: "All vendors verified and reviewed" },
                            { icon: Calendar, text: "Plan weddings, birthdays, corporate events" },
                            { icon: Users, text: "Direct messaging with vendors" },
                        ].map((item) => (
                            <div key={item.text} className="flex items-center gap-3">
                                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/15">
                                    <item.icon className="h-4 w-4 text-white" />
                                </div>
                                <span className="text-sm text-indigo-100">{item.text}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* ── Right: Signup Form ── */}
            <div className="flex items-center justify-center px-4 py-12 sm:px-8 bg-gray-50">
                <div className="w-full max-w-md">
                    {/* Mobile logo */}
                    <div className="flex items-center justify-center gap-2 mb-8 lg:hidden">
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl overflow-hidden">
                            <Image src="/logo.png" alt="Event-AI" width={40} height={40} className="object-contain" />
                        </div>
                        <span className="text-xl font-bold text-gray-900">Event-AI</span>
                    </div>

                    <div className="bg-white rounded-2xl shadow-xl border border-gray-100 p-8">
                        <div className="mb-8">
                            <h1 className="text-2xl font-bold text-gray-900">Create your account</h1>
                            <p className="mt-1 text-sm text-gray-500">Start planning amazing events in Pakistan</p>
                        </div>

                        {error && (
                            <div className="flex items-start gap-3 rounded-xl bg-red-50 border border-red-100 px-4 py-3 text-sm text-red-700 mb-6">
                                <AlertCircle className="h-4 w-4 mt-0.5 shrink-0 text-red-500" />
                                {error}
                            </div>
                        )}

                        {/* Google Sign-Up */}
                        <button
                            type="button"
                            onClick={handleGoogleSignUp}
                            disabled={googleLoading || isLoading}
                            className="w-full flex items-center justify-center gap-3 rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 hover:border-gray-300 hover:shadow active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed transition-all duration-150"
                        >
                            {googleLoading ? (
                                <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
                            ) : (
                                <GoogleIcon className="h-5 w-5" />
                            )}
                            {googleLoading ? "Connecting..." : "Sign up with Google"}
                        </button>

                        {/* Divider */}
                        <div className="relative my-6">
                            <div className="absolute inset-0 flex items-center">
                                <div className="w-full border-t border-gray-200" />
                            </div>
                            <div className="relative flex justify-center text-xs uppercase">
                                <span className="bg-white px-3 text-gray-400 font-medium tracking-wider">or</span>
                            </div>
                        </div>

                        {/* Form */}
                        <form onSubmit={handleSubmit} className="space-y-4">
                            {/* Name row */}
                            <div className="grid grid-cols-2 gap-3">
                                <div className="space-y-1.5">
                                    <label htmlFor="firstName" className="text-sm font-medium text-gray-700">First Name</label>
                                    <input
                                        id="firstName"
                                        name="firstName"
                                        type="text"
                                        required
                                        value={formData.firstName}
                                        onChange={handleChange}
                                        placeholder="Ahmed"
                                        className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm shadow-sm placeholder:text-gray-400 hover:border-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all duration-150"
                                    />
                                </div>
                                <div className="space-y-1.5">
                                    <label htmlFor="lastName" className="text-sm font-medium text-gray-700">Last Name</label>
                                    <input
                                        id="lastName"
                                        name="lastName"
                                        type="text"
                                        required
                                        value={formData.lastName}
                                        onChange={handleChange}
                                        placeholder="Khan"
                                        className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm shadow-sm placeholder:text-gray-400 hover:border-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all duration-150"
                                    />
                                </div>
                            </div>

                            {/* Email */}
                            <div className="space-y-1.5">
                                <label htmlFor="email" className="text-sm font-medium text-gray-700">Email address</label>
                                <input
                                    id="email"
                                    name="email"
                                    type="email"
                                    required
                                    value={formData.email}
                                    onChange={handleChange}
                                    placeholder="you@example.com"
                                    className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm shadow-sm placeholder:text-gray-400 hover:border-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all duration-150"
                                />
                            </div>

                            {/* Phone */}
                            <div className="space-y-1.5">
                                <label htmlFor="phone" className="text-sm font-medium text-gray-700">
                                    Phone <span className="text-gray-400 font-normal">(optional)</span>
                                </label>
                                <input
                                    id="phone"
                                    name="phone"
                                    type="tel"
                                    value={formData.phone}
                                    onChange={handleChange}
                                    placeholder="+92 300 1234567"
                                    className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm shadow-sm placeholder:text-gray-400 hover:border-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all duration-150"
                                />
                            </div>

                            {/* Password */}
                            <div className="space-y-1.5">
                                <label htmlFor="password" className="text-sm font-medium text-gray-700">Password</label>
                                <div className="relative">
                                    <input
                                        id="password"
                                        name="password"
                                        type={showPassword ? "text" : "password"}
                                        required
                                        value={formData.password}
                                        onChange={handleChange}
                                        placeholder="Min 12 characters"
                                        className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 pr-11 text-sm shadow-sm placeholder:text-gray-400 hover:border-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all duration-150"
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowPassword(!showPassword)}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
                                        aria-label={showPassword ? "Hide password" : "Show password"}
                                    >
                                        {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                                    </button>
                                </div>
                                {/* Strength indicator */}
                                {formData.password && (
                                    <div className="mt-2 space-y-1.5">
                                        <div className="flex gap-1">
                                            {[1, 2, 3, 4].map((level) => (
                                                <div
                                                    key={level}
                                                    className={`h-1 flex-1 rounded-full transition-all duration-300 ${strength >= level ? strengthColors[strength] : "bg-gray-200"}`}
                                                />
                                            ))}
                                        </div>
                                        <p className={`text-xs font-medium ${strengthTextColors[strength]}`}>
                                            {strengthLabels[strength]}
                                        </p>
                                    </div>
                                )}
                            </div>

                            {/* Confirm Password */}
                            <div className="space-y-1.5">
                                <label htmlFor="confirmPassword" className="text-sm font-medium text-gray-700">Confirm Password</label>
                                <div className="relative">
                                    <input
                                        id="confirmPassword"
                                        name="confirmPassword"
                                        type={showConfirm ? "text" : "password"}
                                        required
                                        value={formData.confirmPassword}
                                        onChange={handleChange}
                                        placeholder="Repeat your password"
                                        className={`w-full rounded-xl border px-4 py-3 pr-11 text-sm shadow-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:border-transparent transition-all duration-150 ${formData.confirmPassword && formData.password !== formData.confirmPassword
                                            ? "border-red-300 bg-red-50/50 focus:ring-red-500"
                                            : "border-gray-200 bg-white hover:border-gray-300 focus:ring-indigo-500"
                                            }`}
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowConfirm(!showConfirm)}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
                                        aria-label={showConfirm ? "Hide password" : "Show password"}
                                    >
                                        {showConfirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                                    </button>
                                </div>
                                {formData.confirmPassword && formData.password !== formData.confirmPassword && (
                                    <p className="text-xs text-red-600">Passwords do not match</p>
                                )}
                            </div>

                            <button
                                type="submit"
                                disabled={isLoading || googleLoading}
                                className="w-full flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-700 px-4 py-3 text-sm font-semibold text-white shadow-sm hover:from-indigo-700 hover:to-indigo-800 active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed transition-all duration-150"
                            >
                                {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
                                {isLoading ? "Creating account..." : "Create Account"}
                            </button>
                        </form>

                        <p className="mt-6 text-center text-sm text-gray-500">
                            Already have an account?{" "}
                            <Link href="/login" className="font-semibold text-indigo-600 hover:text-indigo-700">
                                Sign in
                            </Link>
                        </p>

                        <p className="mt-3 text-center text-xs text-gray-400">
                            By creating an account, you agree to wait for admin approval before accessing the platform.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
