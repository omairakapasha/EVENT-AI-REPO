'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Eye, EyeOff, Mail, Lock, Loader2, Building2 } from 'lucide-react';
import { useAuthStore } from '@/lib/auth-store';
import { cn } from '@/lib/utils';

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

const loginSchema = z.object({
    email: z.string().email('Invalid email address'),
    password: z.string().min(1, 'Password is required'),
});

type LoginForm = z.infer<typeof loginSchema>;

export default function LoginPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [showPassword, setShowPassword] = useState(false);
    const [twoFactorCode, setTwoFactorCode] = useState('');
    const [hasMounted, setHasMounted] = useState(false);
    const [googleLoading, setGoogleLoading] = useState(false);
    const { login, verify2FA, requiresTwoFactor, isLoading, error, clearError } = useAuthStore();

    const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000/api/v1';

    const handleGoogleSignIn = () => {
        setGoogleLoading(true);
        const origin = window.location.origin; // e.g. http://localhost:3000
        window.location.href = `${BACKEND_URL}/auth/google?frontend_origin=${encodeURIComponent(origin)}`;
    };

    useEffect(() => {
        setHasMounted(true);
        // Show OAuth errors passed back from the backend redirect
        const oauthError = searchParams?.get('error');
        if (oauthError) {
            useAuthStore.setState({ error: decodeURIComponent(oauthError) });
        }
    }, [searchParams]);

    const {
        register,
        handleSubmit,
        formState: { errors },
    } = useForm<LoginForm>({
        resolver: zodResolver(loginSchema),
    });

    const onSubmit = async (data: LoginForm) => {
        clearError();
        const success = await login(data.email, data.password);
        if (success) {
            router.push('/dashboard');
        }
    };

    const handle2FASubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        clearError();
        const success = await verify2FA(twoFactorCode);
        if (success) {
            router.push('/dashboard');
        }
    };

    if (!hasMounted) {
        return (
            <div className="flex min-h-screen items-center justify-center">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
            </div>
        );
    }

    if (requiresTwoFactor) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-primary-600/10 via-surface-50 to-purple-600/10 p-4 dark:from-primary-900/20 dark:via-surface-950 dark:to-purple-900/20">
                <div className="w-full max-w-md">
                    <div className="card">
                        <div className="mb-8 text-center">
                            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-primary-100 dark:bg-primary-900/30">
                                <Lock className="h-7 w-7 text-primary-600 dark:text-primary-400" />
                            </div>
                            <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-50">
                                Two-Factor Authentication
                            </h1>
                            <p className="mt-2 text-surface-500 dark:text-surface-400">
                                Enter the 6-digit code from your authenticator app
                            </p>
                        </div>

                        <form onSubmit={handle2FASubmit} className="space-y-4">
                            {error && (
                                <div className="rounded-lg bg-error-50 p-3 text-sm text-error-600 dark:bg-error-900/20 dark:text-error-400">
                                    {error}
                                </div>
                            )}

                            <div>
                                <input
                                    type="text"
                                    maxLength={6}
                                    value={twoFactorCode}
                                    onChange={(e) => setTwoFactorCode(e.target.value.replace(/\D/g, ''))}
                                    placeholder="000000"
                                    className="input text-center text-2xl tracking-[0.5em] font-mono"
                                    autoFocus
                                />
                            </div>

                            <button
                                type="submit"
                                disabled={isLoading || twoFactorCode.length !== 6}
                                className="btn-primary w-full"
                            >
                                {isLoading ? (
                                    <Loader2 className="h-5 w-5 animate-spin" />
                                ) : (
                                    'Verify'
                                )}
                            </button>

                            <button
                                type="button"
                                onClick={() => useAuthStore.setState({ requiresTwoFactor: false })}
                                className="btn-ghost w-full text-surface-500"
                            >
                                Back to Login
                            </button>
                        </form>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-primary-600/10 via-surface-50 to-purple-600/10 p-4 dark:from-primary-900/20 dark:via-surface-950 dark:to-purple-900/20">
            <div className="w-full max-w-md">
                {/* Header */}
                <div className="mb-8 text-center">
                    <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 shadow-lg shadow-primary-500/25">
                        <Building2 className="h-7 w-7 text-white" />
                    </div>
                    <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-50">
                        Welcome Back
                    </h1>
                    <p className="mt-2 text-surface-500 dark:text-surface-400">
                        Sign in to your vendor portal
                    </p>
                </div>

                {/* Login Form */}
                <div className="card">
                    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
                        {error && (
                            <div className="rounded-lg bg-error-50 p-3 text-sm text-error-600 dark:bg-error-900/20 dark:text-error-400">
                                {error}
                            </div>
                        )}

                        {/* Google Sign-In */}
                        <button
                            type="button"
                            onClick={handleGoogleSignIn}
                            disabled={googleLoading || isLoading}
                            className="w-full flex items-center justify-center gap-3 rounded-lg border border-surface-300 bg-white px-4 py-2.5 text-sm font-medium text-surface-700 shadow-sm hover:bg-surface-50 hover:border-surface-400 active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed transition-all duration-150 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-200 dark:hover:bg-surface-700"
                        >
                            {googleLoading ? (
                                <Loader2 className="h-5 w-5 animate-spin text-surface-400" />
                            ) : (
                                <GoogleIcon className="h-5 w-5" />
                            )}
                            {googleLoading ? 'Connecting...' : 'Continue with Google'}
                        </button>

                        {/* Divider */}
                        <div className="relative">
                            <div className="absolute inset-0 flex items-center">
                                <div className="w-full border-t border-surface-200 dark:border-surface-700" />
                            </div>
                            <div className="relative flex justify-center text-xs uppercase">
                                <span className="bg-white px-3 text-surface-400 font-medium tracking-wider dark:bg-surface-900">or</span>
                            </div>
                        </div>

                        {/* Email */}
                        <div>
                            <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
                                Email
                            </label>
                            <div className="relative">
                                <Mail className="absolute left-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-surface-400" />
                                <input
                                    type="email"
                                    {...register('email')}
                                    placeholder="you@company.com"
                                    className={cn('input pl-11', errors.email && 'input-error')}
                                />
                            </div>
                            {errors.email && (
                                <p className="mt-1.5 text-sm text-error-500">{errors.email.message}</p>
                            )}
                        </div>

                        {/* Password */}
                        <div>
                            <div className="mb-1.5 flex items-center justify-between">
                                <label className="block text-sm font-medium text-surface-700 dark:text-surface-300">
                                    Password
                                </label>
                                <Link
                                    href="/forgot-password"
                                    className="text-sm font-medium text-primary-600 hover:text-primary-500 dark:text-primary-400"
                                >
                                    Forgot password?
                                </Link>
                            </div>
                            <div className="relative">
                                <Lock className="absolute left-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-surface-400" />
                                <input
                                    type={showPassword ? 'text' : 'password'}
                                    {...register('password')}
                                    placeholder="••••••••"
                                    className={cn('input pl-11 pr-11', errors.password && 'input-error')}
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-surface-400 hover:text-surface-600"
                                >
                                    {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                                </button>
                            </div>
                            {errors.password && (
                                <p className="mt-1.5 text-sm text-error-500">{errors.password.message}</p>
                            )}
                        </div>

                        {/* Submit */}
                        <button type="submit" disabled={isLoading} className="btn-primary w-full">
                            {isLoading ? (
                                <>
                                    <Loader2 className="h-5 w-5 animate-spin" />
                                    Signing in...
                                </>
                            ) : (
                                'Sign In'
                            )}
                        </button>
                    </form>

                    {/* Divider */}
                    <div className="my-6 flex items-center">
                        <div className="flex-1 border-t border-surface-200 dark:border-surface-700" />
                        <span className="px-4 text-sm text-surface-400">or</span>
                        <div className="flex-1 border-t border-surface-200 dark:border-surface-700" />
                    </div>

                    {/* Register Link */}
                    <p className="text-center text-sm text-surface-500 dark:text-surface-400">
                        Don&apos;t have an account?{' '}
                        <Link
                            href="/register"
                            className="font-medium text-primary-600 hover:text-primary-500 dark:text-primary-400"
                        >
                            Register as a vendor
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    );
}
