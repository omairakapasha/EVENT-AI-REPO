'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2, Mail, RefreshCw, CheckCircle } from 'lucide-react';
import { useAuthStore } from '@/lib/auth-store';
import api, { getApiError } from '@/lib/api';
import { cn } from '@/lib/utils';

const OTP_LENGTH = 6;
const RESEND_COOLDOWN = 60; // seconds

export default function VerifyEmailPage() {
    const router = useRouter();
    const { user, isAuthenticated } = useAuthStore();

    const [digits, setDigits] = useState<string[]>(Array(OTP_LENGTH).fill(''));
    const [isVerifying, setIsVerifying] = useState(false);
    const [isResending, setIsResending] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);
    const [cooldown, setCooldown] = useState(0);

    const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

    // Redirect if not authenticated
    useEffect(() => {
        if (!isAuthenticated) {
            router.replace('/login');
        }
    }, [isAuthenticated, router]);

    // Cooldown timer
    useEffect(() => {
        if (cooldown <= 0) return;
        const timer = setTimeout(() => setCooldown((c) => c - 1), 1000);
        return () => clearTimeout(timer);
    }, [cooldown]);

    const focusNext = (index: number) => {
        if (index < OTP_LENGTH - 1) {
            inputRefs.current[index + 1]?.focus();
        }
    };

    const focusPrev = (index: number) => {
        if (index > 0) {
            inputRefs.current[index - 1]?.focus();
        }
    };

    const handleChange = (index: number, value: string) => {
        // Only allow single digit
        const digit = value.replace(/\D/g, '').slice(-1);
        const newDigits = [...digits];
        newDigits[index] = digit;
        setDigits(newDigits);
        setError(null);

        if (digit) focusNext(index);
    };

    const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Backspace') {
            if (digits[index]) {
                const newDigits = [...digits];
                newDigits[index] = '';
                setDigits(newDigits);
            } else {
                focusPrev(index);
            }
        } else if (e.key === 'ArrowLeft') {
            focusPrev(index);
        } else if (e.key === 'ArrowRight') {
            focusNext(index);
        }
    };

    const handlePaste = (e: React.ClipboardEvent) => {
        e.preventDefault();
        const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, OTP_LENGTH);
        if (!pasted) return;
        const newDigits = Array(OTP_LENGTH).fill('');
        pasted.split('').forEach((d, i) => { newDigits[i] = d; });
        setDigits(newDigits);
        // Focus last filled or next empty
        const lastIndex = Math.min(pasted.length, OTP_LENGTH - 1);
        inputRefs.current[lastIndex]?.focus();
    };

    const handleVerify = useCallback(async () => {
        const code = digits.join('');
        if (code.length < OTP_LENGTH) {
            setError('Please enter all 6 digits.');
            return;
        }

        setIsVerifying(true);
        setError(null);
        try {
            await api.post('/auth/verify-email', { code });
            setSuccess(true);
            // Update email_verified in store by refetching user
            setTimeout(() => router.replace('/dashboard'), 2000);
        } catch (err) {
            setError(getApiError(err));
        } finally {
            setIsVerifying(false);
        }
    }, [digits, router]);

    // Auto-submit when all digits filled
    useEffect(() => {
        if (digits.every((d) => d !== '') && !isVerifying && !success) {
            handleVerify();
        }
    }, [digits, handleVerify, isVerifying, success]);

    const handleResend = async () => {
        if (cooldown > 0 || isResending) return;
        setIsResending(true);
        setError(null);
        try {
            await api.post('/auth/resend-otp');
            setCooldown(RESEND_COOLDOWN);
            setDigits(Array(OTP_LENGTH).fill(''));
            inputRefs.current[0]?.focus();
        } catch (err) {
            setError(getApiError(err));
        } finally {
            setIsResending(false);
        }
    };

    if (success) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-primary-600/10 via-surface-50 to-purple-600/10 p-4">
                <div className="w-full max-w-md text-center">
                    <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
                        <CheckCircle className="h-8 w-8 text-green-600" />
                    </div>
                    <h1 className="text-2xl font-bold text-surface-900">Email Verified!</h1>
                    <p className="mt-2 text-surface-500">Redirecting to your dashboard…</p>
                </div>
            </div>
        );
    }

    return (
        <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-primary-600/10 via-surface-50 to-purple-600/10 p-4">
            <div className="w-full max-w-md">
                {/* Header */}
                <div className="mb-8 text-center">
                    <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 shadow-lg shadow-primary-500/25">
                        <Mail className="h-7 w-7 text-white" />
                    </div>
                    <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-50">
                        Verify your email
                    </h1>
                    <p className="mt-2 text-surface-500 dark:text-surface-400">
                        We sent a 6-digit code to
                    </p>
                    <p className="font-medium text-surface-900 dark:text-surface-50">
                        {user?.email ?? ''}
                    </p>
                </div>

                <div className="card space-y-6">
                    {/* OTP inputs */}
                    <div className="flex justify-center gap-3" onPaste={handlePaste}>
                        {digits.map((digit, i) => (
                            <input
                                key={i}
                                ref={(el) => { inputRefs.current[i] = el; }}
                                type="text"
                                inputMode="numeric"
                                maxLength={1}
                                value={digit}
                                onChange={(e) => handleChange(i, e.target.value)}
                                onKeyDown={(e) => handleKeyDown(i, e)}
                                className={cn(
                                    'h-14 w-12 rounded-xl border-2 text-center text-2xl font-bold transition-colors',
                                    'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                                    digit
                                        ? 'border-primary-400 bg-primary-50 text-primary-700 dark:bg-primary-900/20 dark:text-primary-300'
                                        : 'border-surface-300 bg-white dark:border-surface-600 dark:bg-surface-800',
                                    error && 'border-red-400 bg-red-50 dark:bg-red-900/10',
                                )}
                                aria-label={`Digit ${i + 1}`}
                                autoFocus={i === 0}
                            />
                        ))}
                    </div>

                    {/* Error */}
                    {error && (
                        <p className="text-center text-sm text-red-600 dark:text-red-400">{error}</p>
                    )}

                    {/* Verify button */}
                    <button
                        onClick={handleVerify}
                        disabled={isVerifying || digits.some((d) => !d)}
                        className="btn-primary w-full"
                    >
                        {isVerifying ? (
                            <><Loader2 className="h-5 w-5 animate-spin" /> Verifying…</>
                        ) : (
                            'Verify Email'
                        )}
                    </button>

                    {/* Resend */}
                    <div className="text-center">
                        <p className="text-sm text-surface-500">Didn&apos;t receive the code?</p>
                        <button
                            onClick={handleResend}
                            disabled={cooldown > 0 || isResending}
                            className={cn(
                                'mt-1 flex items-center gap-1.5 mx-auto text-sm font-medium transition-colors',
                                cooldown > 0 || isResending
                                    ? 'text-surface-400 cursor-not-allowed'
                                    : 'text-primary-600 hover:text-primary-500'
                            )}
                        >
                            {isResending ? (
                                <><Loader2 className="h-4 w-4 animate-spin" /> Sending…</>
                            ) : cooldown > 0 ? (
                                <><RefreshCw className="h-4 w-4" /> Resend in {cooldown}s</>
                            ) : (
                                <><RefreshCw className="h-4 w-4" /> Resend code</>
                            )}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
