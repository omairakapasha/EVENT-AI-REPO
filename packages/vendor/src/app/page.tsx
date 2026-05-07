import Link from 'next/link';
import { Building2, ArrowRight, CheckCircle, Zap, Shield, BarChart3 } from 'lucide-react';

const features = [
    {
        icon: Zap,
        title: 'Fast Onboarding',
        description: 'Get started in minutes with our streamlined registration process.',
    },
    {
        icon: Shield,
        title: 'Secure & Compliant',
        description: 'Enterprise-grade security with 2FA and full GDPR compliance.',
    },
    {
        icon: BarChart3,
        title: 'Real-time Analytics',
        description: 'Track bookings, revenue, and performance in one dashboard.',
    },
];

const benefits = [
    'Manage services and pricing',
    'Accept bookings from event planners',
    'API integration support',
    'Automated notifications',
    'Revenue tracking',
    'Multi-user access',
];

export default function HomePage() {
    return (
        <div className="min-h-screen bg-surface-50 dark:bg-surface-950">
            {/* Navbar */}
            <nav className="border-b border-surface-200 bg-white/80 backdrop-blur-lg dark:border-surface-800 dark:bg-surface-900/80">
                <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
                    <div className="flex items-center gap-3">
                        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-primary-500 to-primary-600">
                            <Building2 className="h-5 w-5 text-white" />
                        </div>
                        <span className="text-lg font-semibold text-surface-900 dark:text-surface-50">
                            Vendor Portal
                        </span>
                    </div>
                    <div className="flex items-center gap-4">
                        <Link href="/login" className="btn-ghost">
                            Sign In
                        </Link>
                        <Link href="/register" className="btn-primary">
                            Get Started
                            <ArrowRight className="h-4 w-4" />
                        </Link>
                    </div>
                </div>
            </nav>

            {/* Hero Section */}
            <section className="relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-br from-primary-600/5 via-transparent to-purple-600/5" />
                <div className="relative mx-auto max-w-7xl px-6 py-24 sm:py-32">
                    <div className="mx-auto max-w-3xl text-center">
                        <div className="mb-6 inline-flex items-center gap-2 rounded-full bg-primary-100 px-4 py-1.5 text-sm font-medium text-primary-700 dark:bg-primary-900/30 dark:text-primary-400">
                            <Zap className="h-4 w-4" />
                            Now with API Integration Support
                        </div>
                        <h1 className="text-4xl font-bold tracking-tight text-surface-900 dark:text-surface-50 sm:text-6xl">
                            Grow Your Event Business with Our
                            <span className="bg-gradient-to-r from-primary-600 to-purple-600 bg-clip-text text-transparent">
                                {' '}Vendor Portal
                            </span>
                        </h1>
                        <p className="mt-6 text-lg leading-8 text-surface-600 dark:text-surface-400">
                            Join hundreds of vendors managing their services, pricing, and bookings
                            on the Event Orchestrator platform. Streamline operations and reach more clients.
                        </p>
                        <div className="mt-10 flex items-center justify-center gap-4">
                            <Link href="/register" className="btn-primary btn-lg">
                                Register Your Business
                                <ArrowRight className="h-5 w-5" />
                            </Link>
                            <Link href="/login" className="btn-outline btn-lg">
                                Sign In
                            </Link>
                        </div>
                    </div>
                </div>
            </section>

            {/* Features Section */}
            <section className="border-y border-surface-200 bg-white py-16 dark:border-surface-800 dark:bg-surface-900">
                <div className="mx-auto max-w-7xl px-6">
                    <div className="grid grid-cols-3 gap-8">
                        {features.map((feature) => (
                            <div key={feature.title} className="text-center">
                                <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-primary-100 dark:bg-primary-900/30">
                                    <feature.icon className="h-7 w-7 text-primary-600 dark:text-primary-400" />
                                </div>
                                <h3 className="text-lg font-semibold text-surface-900 dark:text-surface-50">
                                    {feature.title}
                                </h3>
                                <p className="mt-2 text-surface-500 dark:text-surface-400">
                                    {feature.description}
                                </p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Benefits Section */}
            <section className="py-24">
                <div className="mx-auto max-w-7xl px-6">
                    <div className="grid grid-cols-2 gap-16 items-center">
                        <div>
                            <h2 className="text-3xl font-bold text-surface-900 dark:text-surface-50">
                                Everything you need to manage your vendor business
                            </h2>
                            <p className="mt-4 text-lg text-surface-500 dark:text-surface-400">
                                Our platform provides all the tools you need to showcase your services,
                                manage pricing, and grow your bookings.
                            </p>
                            <ul className="mt-8 space-y-4">
                                {benefits.map((benefit) => (
                                    <li key={benefit} className="flex items-center gap-3">
                                        <CheckCircle className="h-5 w-5 text-success-500" />
                                        <span className="text-surface-700 dark:text-surface-300">{benefit}</span>
                                    </li>
                                ))}
                            </ul>
                            <Link href="/register" className="btn-primary mt-8 inline-flex">
                                Start Free Trial
                                <ArrowRight className="h-4 w-4" />
                            </Link>
                        </div>
                        <div className="relative">
                            <div className="aspect-square rounded-2xl bg-gradient-to-br from-primary-100 to-purple-100 p-8 dark:from-primary-900/20 dark:to-purple-900/20">
                                <div className="h-full rounded-xl bg-white shadow-xl dark:bg-surface-800">
                                    <div className="p-6">
                                        <div className="h-4 w-24 rounded bg-surface-200 dark:bg-surface-700" />
                                        <div className="mt-4 space-y-3">
                                            <div className="h-3 w-full rounded bg-surface-100 dark:bg-surface-700" />
                                            <div className="h-3 w-4/5 rounded bg-surface-100 dark:bg-surface-700" />
                                            <div className="h-3 w-3/5 rounded bg-surface-100 dark:bg-surface-700" />
                                        </div>
                                        <div className="mt-6 grid grid-cols-2 gap-4">
                                            <div className="h-20 rounded-lg bg-primary-50 dark:bg-primary-900/20" />
                                            <div className="h-20 rounded-lg bg-success-50 dark:bg-success-900/20" />
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* CTA Section */}
            <section className="bg-gradient-to-r from-primary-600 to-primary-700 py-16">
                <div className="mx-auto max-w-4xl px-6 text-center">
                    <h2 className="text-3xl font-bold text-white">
                        Ready to grow your business?
                    </h2>
                    <p className="mt-4 text-lg text-primary-100">
                        Join our vendor network today and start receiving bookings from event planners.
                    </p>
                    <Link
                        href="/register"
                        className="mt-8 inline-flex items-center gap-2 rounded-lg bg-white px-6 py-3 font-medium text-primary-600 shadow-lg transition-all hover:bg-primary-50"
                    >
                        Get Started for Free
                        <ArrowRight className="h-5 w-5" />
                    </Link>
                </div>
            </section>

            {/* Footer */}
            <footer className="border-t border-surface-200 bg-white py-12 dark:border-surface-800 dark:bg-surface-900">
                <div className="mx-auto max-w-7xl px-6">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary-500 to-primary-600">
                                <Building2 className="h-4 w-4 text-white" />
                            </div>
                            <span className="font-semibold text-surface-900 dark:text-surface-50">
                                Vendor Portal
                            </span>
                        </div>
                        <p className="text-sm text-surface-500">
                            © 2026 Event Orchestrator. All rights reserved.
                        </p>
                    </div>
                </div>
            </footer>
        </div>
    );
}
