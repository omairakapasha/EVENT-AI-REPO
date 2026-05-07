'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Eye, EyeOff, Mail, Lock, User, Building2, Phone, Globe, Loader2, CheckCircle, ArrowLeft, ArrowRight } from 'lucide-react';
import { useAuthStore } from '@/lib/auth-store';
import type { RegisterData } from '@/lib/auth-store';
import { cn } from '@/lib/utils';

const registerBaseSchema = z.object({
    // Step 1: Business Info
    vendorName: z.string().min(2, 'Business name is required'),
    businessType: z.string().optional(),
    contactEmail: z.string().email('Invalid business email'),
    phone: z.string().optional(),
    website: z.string().url().optional().or(z.literal('')),
    // Step 2: User Info
    firstName: z.string().min(1, 'First name is required'),
    lastName: z.string().min(1, 'Last name is required'),
    email: z.string().email('Invalid email address'),
    password: z
        .string()
        .min(8, 'Password must be at least 8 characters')
        .regex(/[A-Z]/, 'Password must contain an uppercase letter')
        .regex(/[a-z]/, 'Password must contain a lowercase letter')
        .regex(/[0-9]/, 'Password must contain a number')
        .regex(/[^A-Za-z0-9]/, 'Password must contain a special character'),
    confirmPassword: z.string(),
});

type RegisterForm = z.infer<typeof registerBaseSchema>;

const businessTypes = [
    'Venue',
    'Catering',
    'Photography',
    'Videography',
    'Music & Entertainment',
    'Decoration & Florals',
    'Transportation',
    'Wedding Planning',
    'Event Rentals',
    'Other',
];

export default function RegisterPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const isIncomplete = searchParams?.get('incomplete') === '1';
    const [step, setStep] = useState(1);
    const [showPassword, setShowPassword] = useState(false);
    const [success, setSuccess] = useState(false);
    const { register: registerVendor, isLoading, error, clearError, isAuthenticated, logout } = useAuthStore();

    // If the user is already logged in and visits /register (not the recovery flow),
    // log them out first so they get a clean registration experience.
    useEffect(() => {
        if (isAuthenticated && !isIncomplete) {
            logout();
        }
    // Only run once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // In recovery mode, only business info fields are required
    const schema = isIncomplete
        ? registerBaseSchema.partial({ firstName: true, lastName: true, email: true, password: true, confirmPassword: true })
        : registerBaseSchema;

    const {
        register,
        handleSubmit,
        formState: { errors },
        trigger,
        watch,
        getValues,
        clearErrors,
        setError: setFormError,
    } = useForm<RegisterForm>({
        resolver: zodResolver(schema),
        defaultValues: {
            vendorName: '',
            businessType: '',
            contactEmail: '',
            phone: '',
            website: '',
            firstName: '',
            lastName: '',
            email: '',
            password: '',
            confirmPassword: '',
        },
    });

    const password = watch('password', '');

    const passwordChecks = [
        { label: '8+ characters', valid: password.length >= 8 },
        { label: 'Uppercase letter', valid: /[A-Z]/.test(password) },
        { label: 'Lowercase letter', valid: /[a-z]/.test(password) },
        { label: 'Number', valid: /[0-9]/.test(password) },
        { label: 'Special character', valid: /[^A-Za-z0-9]/.test(password) },
    ];

    const nextStep = () => {
        if (step === 1) {
            const values = getValues();
            let hasError = false;

            if (!values.vendorName || values.vendorName.length < 2) {
                setFormError('vendorName', { message: 'Business name is required' });
                hasError = true;
            }
            if (!values.contactEmail || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.contactEmail)) {
                setFormError('contactEmail', { message: 'Invalid business email' });
                hasError = true;
            }

            if (!hasError) {
                clearErrors(['vendorName', 'contactEmail']);
                // In recovery mode, step 1 is all we need — submit directly
                if (isIncomplete) {
                    handleSubmit(onSubmit)();
                    return;
                }
                setStep(2);
            }
        }
    };

    const onSubmit = async (data: RegisterForm) => {
        // In recovery mode (isIncomplete), only business info is needed —
        // the user account already exists, so skip password validation.
        if (!isIncomplete) {
            if (data.password !== data.confirmPassword) {
                setFormError('confirmPassword', { message: 'Passwords do not match' });
                return;
            }
        }
        clearError();

        const payload: RegisterData = {
            vendorName: data.vendorName,
            contactEmail: data.contactEmail,
            // These are only used in full registration (not recovery)
            firstName: data.firstName || '',
            lastName: data.lastName || '',
            email: data.email || '',
            password: data.password || '',
            confirmPassword: data.confirmPassword || '',
        };
        if (data.businessType) payload.businessType = data.businessType;
        if (data.phone) payload.phone = data.phone;
        if (data.website) payload.website = data.website;

        const success = await registerVendor(payload);
        if (success) {
            if (isIncomplete) {
                router.replace('/dashboard');
            } else {
                // Redirect to OTP verification page
                router.replace('/verify-email');
            }
        }
    };

    if (success) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-primary-600/10 via-surface-50 to-purple-600/10 p-4 dark:from-primary-900/20 dark:via-surface-950 dark:to-purple-900/20">
                <div className="w-full max-w-md">
                    <div className="card text-center">
                        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-success-100 dark:bg-success-900/30">
                            <CheckCircle className="h-8 w-8 text-success-600 dark:text-success-400" />
                        </div>
                        <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-50">
                            Registration Successful!
                        </h1>
                        <p className="mt-3 text-surface-500 dark:text-surface-400">
                            We&apos;ve sent a verification email to your inbox. Please verify your email to complete the registration.
                        </p>
                        <Link href="/login" className="btn-primary mt-6 inline-flex">
                            Go to Login
                        </Link>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-primary-600/10 via-surface-50 to-purple-600/10 p-4 dark:from-primary-900/20 dark:via-surface-950 dark:to-purple-900/20">
            <div className="w-full max-w-xl">
                {/* Header */}
                <div className="mb-8 text-center">
                    <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 shadow-lg shadow-primary-500/25">
                        <Building2 className="h-7 w-7 text-white" />
                    </div>
                    <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-50">
                        Register Your Business
                    </h1>
                    <p className="mt-2 text-surface-500 dark:text-surface-400">
                        Join our vendor marketplace in just a few steps
                    </p>
                </div>

                {/* Progress Steps — hidden in recovery mode (only 1 step needed) */}
                {!isIncomplete && (
                <div className="mb-8 flex items-center justify-center gap-4">
                    {[1, 2].map((s) => (
                        <div key={s} className="flex items-center gap-2">
                            <div
                                className={cn(
                                    'flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium transition-colors',
                                    step >= s
                                        ? 'bg-primary-600 text-white'
                                        : 'bg-surface-200 text-surface-500 dark:bg-surface-700'
                                )}
                            >
                                {step > s ? <CheckCircle className="h-4 w-4" /> : s}
                            </div>
                            <span
                                className={cn(
                                    'text-sm font-medium',
                                    step >= s ? 'text-surface-900 dark:text-surface-50' : 'text-surface-400'
                                )}
                            >
                                {s === 1 ? 'Business Info' : 'Account Setup'}
                            </span>
                            {s < 2 && (
                                <div
                                    className={cn(
                                        'h-0.5 w-12',
                                        step > s ? 'bg-primary-600' : 'bg-surface-200 dark:bg-surface-700'
                                    )}
                                />
                            )}
                        </div>
                    ))}
                </div>
                )}

                {/* Form */}
                <div className="card">
                    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
                        {isIncomplete && (
                            <div className="rounded-lg bg-yellow-50 p-3 text-sm text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-300">
                                Your account was created but the vendor profile setup didn&apos;t complete. Please fill in your business details to finish.
                            </div>
                        )}
                        {error && (
                            <div className="rounded-lg bg-error-50 p-3 text-sm text-error-600 dark:bg-error-900/20 dark:text-error-400">
                                {error}
                            </div>
                        )}

                        {/* Step 1: Business Info */}
                        {step === 1 && (
                            <>
                                <div>
                                    <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
                                        Business Name *
                                    </label>
                                    <div className="relative">
                                        <Building2 className="absolute left-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-surface-400" />
                                        <input
                                            {...register('vendorName')}
                                            placeholder="Your Company Name"
                                            className={cn('input pl-11', errors.vendorName && 'input-error')}
                                        />
                                    </div>
                                    {errors.vendorName && (
                                        <p className="mt-1.5 text-sm text-error-500">{errors.vendorName.message}</p>
                                    )}
                                </div>

                                <div>
                                    <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
                                        Business Type
                                    </label>
                                    <select {...register('businessType')} className="input">
                                        <option value="">Select a category</option>
                                        {businessTypes.map((type) => (
                                            <option key={type} value={type}>{type}</option>
                                        ))}
                                    </select>
                                </div>

                                <div>
                                    <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
                                        Business Email *
                                    </label>
                                    <div className="relative">
                                        <Mail className="absolute left-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-surface-400" />
                                        <input
                                            type="email"
                                            {...register('contactEmail')}
                                            placeholder="contact@company.com"
                                            className={cn('input pl-11', errors.contactEmail && 'input-error')}
                                        />
                                    </div>
                                    {errors.contactEmail && (
                                        <p className="mt-1.5 text-sm text-error-500">{errors.contactEmail.message}</p>
                                    )}
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
                                            Phone
                                        </label>
                                        <div className="relative">
                                            <Phone className="absolute left-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-surface-400" />
                                            <input
                                                {...register('phone')}
                                                placeholder="+1 234 567 8900"
                                                className="input pl-11"
                                            />
                                        </div>
                                    </div>
                                    <div>
                                        <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
                                            Website
                                        </label>
                                        <div className="relative">
                                            <Globe className="absolute left-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-surface-400" />
                                            <input
                                                {...register('website')}
                                                placeholder="https://..."
                                                className="input pl-11"
                                            />
                                        </div>
                                    </div>
                                </div>
                            </>
                        )}

                        {/* Step 2: User Account */}
                        {step === 2 && (
                            <>
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
                                            First Name *
                                        </label>
                                        <div className="relative">
                                            <User className="absolute left-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-surface-400" />
                                            <input
                                                {...register('firstName')}
                                                placeholder="John"
                                                className={cn('input pl-11', errors.firstName && 'input-error')}
                                            />
                                        </div>
                                        {errors.firstName && (
                                            <p className="mt-1.5 text-sm text-error-500">{errors.firstName.message}</p>
                                        )}
                                    </div>
                                    <div>
                                        <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
                                            Last Name *
                                        </label>
                                        <input
                                            {...register('lastName')}
                                            placeholder="Doe"
                                            className={cn('input', errors.lastName && 'input-error')}
                                        />
                                        {errors.lastName && (
                                            <p className="mt-1.5 text-sm text-error-500">{errors.lastName.message}</p>
                                        )}
                                    </div>
                                </div>

                                <div>
                                    <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
                                        Your Email *
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

                                <div>
                                    <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
                                        Password *
                                    </label>
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
                                    <div className="mt-2 flex flex-wrap gap-2">
                                        {passwordChecks.map((check) => (
                                            <span
                                                key={check.label}
                                                className={cn(
                                                    'text-xs px-2 py-1 rounded-full',
                                                    check.valid
                                                        ? 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-400'
                                                        : 'bg-surface-100 text-surface-500 dark:bg-surface-800'
                                                )}
                                            >
                                                {check.label}
                                            </span>
                                        ))}
                                    </div>
                                </div>

                                <div>
                                    <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
                                        Confirm Password *
                                    </label>
                                    <div className="relative">
                                        <Lock className="absolute left-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-surface-400" />
                                        <input
                                            type={showPassword ? 'text' : 'password'}
                                            {...register('confirmPassword')}
                                            placeholder="••••••••"
                                            className={cn('input pl-11', errors.confirmPassword && 'input-error')}
                                        />
                                    </div>
                                    {errors.confirmPassword && (
                                        <p className="mt-1.5 text-sm text-error-500">{errors.confirmPassword.message}</p>
                                    )}
                                </div>
                            </>
                        )}

                        {/* Navigation Buttons */}
                        <div className="flex gap-3 pt-2">
                            {step > 1 && (
                                <button
                                    type="button"
                                    onClick={() => setStep(step - 1)}
                                    className="btn-secondary flex-1"
                                >
                                    <ArrowLeft className="h-4 w-4" />
                                    Back
                                </button>
                            )}

                            {step < 2 ? (
                                <button type="button" onClick={nextStep} className="btn-primary flex-1">
                                    {isIncomplete ? (
                                        isLoading ? (
                                            <><Loader2 className="h-5 w-5 animate-spin" /> Setting up...</>
                                        ) : (
                                            'Complete Setup'
                                        )
                                    ) : (
                                        <><span>Continue</span><ArrowRight className="h-4 w-4" /></>
                                    )}
                                </button>
                            ) : (
                                <button type="submit" disabled={isLoading} className="btn-primary flex-1">
                                    {isLoading ? (
                                        <>
                                            <Loader2 className="h-5 w-5 animate-spin" />
                                            Creating Account...
                                        </>
                                    ) : (
                                        'Create Account'
                                    )}
                                </button>
                            )}
                        </div>
                    </form>

                    {/* Login Link */}
                    <p className="mt-6 text-center text-sm text-surface-500 dark:text-surface-400">
                        Already have an account?{' '}
                        <Link
                            href="/login"
                            className="font-medium text-primary-600 hover:text-primary-500 dark:text-primary-400"
                        >
                            Sign in
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    );
}
