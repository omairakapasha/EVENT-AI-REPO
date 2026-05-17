import Link from "next/link";
import Image from "next/image";
import {
    Calendar, Search, MessageSquare, Shield, Sparkles, ArrowRight,
    Star, MapPin, CheckCircle, Zap, Users, TrendingUp,
} from "lucide-react";

// ─── Data ─────────────────────────────────────────────────────────────────────
const features = [
    {
        icon: Search,
        title: "Smart Vendor Discovery",
        description: "AI-powered matching finds the perfect vendors for your event type, budget, and location in seconds.",
        color: "bg-[#EFECE3] text-[#1A3D64]",
    },
    {
        icon: Calendar,
        title: "AI Event Planning",
        description: "Create detailed event plans with timelines, checklists, and vendor coordination — all guided by AI.",
        color: "bg-[#EFECE3] text-[#96A78D]",
    },
    {
        icon: MessageSquare,
        title: "Direct Messaging",
        description: "Chat with vendors, negotiate prices, and confirm bookings without ever leaving the platform.",
        color: "bg-[#1A3D64]/10 text-[#1A3D64]",
    },
    {
        icon: Shield,
        title: "Verified Vendors",
        description: "Every vendor is verified, reviewed, and rated by real customers for your peace of mind.",
        color: "bg-green-50 text-green-600",
    },
    {
        icon: Zap,
        title: "Instant Booking",
        description: "Book services instantly with real-time availability checks and secure payment processing.",
        color: "bg-amber-50 text-amber-600",
    },
    {
        icon: TrendingUp,
        title: "Budget Tracking",
        description: "Track your event budget in real-time and get AI suggestions to optimize your spending.",
        color: "bg-rose-50 text-rose-600",
    },
];

const eventTypes = [
    { name: "Weddings", emoji: "💍", count: "2,400+" },
    { name: "Mehndi", emoji: "🌿", count: "1,200+" },
    { name: "Baraat", emoji: "🎊", count: "980+" },
    { name: "Walima", emoji: "🌹", count: "870+" },
    { name: "Birthdays", emoji: "🎂", count: "3,100+" },
    { name: "Corporate", emoji: "💼", count: "1,500+" },
    { name: "Conferences", emoji: "🎤", count: "640+" },
    { name: "Parties", emoji: "🎉", count: "2,800+" },
];

const testimonials = [
    {
        name: "Ayesha Khan",
        role: "Bride, Lahore",
        text: "Found our photographer, caterer, and decorator all in one afternoon. The AI recommendations were spot-on!",
        rating: 5,
        avatar: "A",
        color: "from-pink-400 to-rose-500",
    },
    {
        name: "Bilal Ahmed",
        role: "Corporate Events Manager, Karachi",
        text: "Saved us weeks of vendor research for our annual conference. The booking system is seamless.",
        rating: 5,
        avatar: "B",
        color: "from-[#1A3D64] to-[#2a5a8f]",
    },
    {
        name: "Sara Malik",
        role: "Event Planner, Islamabad",
        text: "The AI assistant helped me plan 3 events simultaneously. I can't imagine going back to the old way.",
        rating: 5,
        avatar: "S",
        color: "from-[#96A78D] to-[#7a8f72]",
    },
];

const stats = [
    { value: "10,000+", label: "Events Planned" },
    { value: "500+", label: "Verified Vendors" },
    { value: "4.9/5", label: "Average Rating" },
    { value: "50+", label: "Cities Covered" },
];

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function HomePage() {
    return (
        <div className="min-h-screen bg-white">

            {/* ── Hero ── */}
            <section className="relative overflow-hidden bg-gradient-to-br from-[#EFECE3] via-white to-[#EFECE3]/60 px-4 sm:px-6 lg:px-8 py-20 lg:py-32">
                {/* Background decoration */}
                <div className="absolute inset-0 -z-10 overflow-hidden">
                    <div className="absolute -top-40 -right-32 h-96 w-96 rounded-full bg-[#1A3D64]/8 blur-3xl" />
                    <div className="absolute -bottom-40 -left-32 h-96 w-96 rounded-full bg-[#96A78D]/15 blur-3xl" />
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-64 w-64 rounded-full bg-[#EFECE3]/80 blur-3xl" />
                </div>

                <div className="mx-auto max-w-4xl text-center">
                    {/* Badge */}
                    <div className="inline-flex items-center gap-2 rounded-full bg-[#EFECE3] border border-[#96A78D]/30 px-4 py-1.5 text-sm font-semibold text-[#1A3D64] mb-6">
                        <Sparkles className="h-4 w-4" />
                        AI-Powered Event Planning in Pakistan
                    </div>

                    {/* Headline */}
                    <h1 className="text-5xl sm:text-6xl font-bold tracking-tight text-gray-900 leading-tight">
                        Plan Your Perfect Event
                        <br />
                        <span className="bg-gradient-to-r from-[#1A3D64] to-[#96A78D] bg-clip-text text-transparent">
                            with AI
                        </span>
                    </h1>

                    {/* Subheadline */}
                    <p className="mt-6 text-lg sm:text-xl text-gray-600 max-w-2xl mx-auto leading-relaxed">
                        Discover top vendors, get AI recommendations, and manage weddings,
                        birthdays, corporate events, and more — all in one place.
                    </p>

                    {/* CTAs */}
                    <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
                        <Link
                            href="/create-event"
                            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-[#1A3D64] to-[#2a5a8f] px-8 py-4 text-base font-semibold text-white shadow-lg shadow-[#1A3D64]/20 hover:from-[#122d4a] hover:to-[#1A3D64] hover:shadow-xl hover:shadow-[#1A3D64]/25 active:scale-[0.98] transition-all duration-200"
                        >
                            Start Planning Free
                            <ArrowRight className="h-5 w-5" />
                        </Link>
                        <Link
                            href="/marketplace"
                            className="inline-flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-8 py-4 text-base font-semibold text-gray-700 shadow-sm hover:bg-gray-50 hover:border-gray-300 hover:shadow active:scale-[0.98] transition-all duration-200"
                        >
                            Browse Vendors
                        </Link>
                    </div>

                    {/* Social proof */}
                    <div className="mt-12 flex flex-col sm:flex-row items-center justify-center gap-6 text-sm text-gray-500">
                        <div className="flex items-center gap-2">
                            <div className="flex -space-x-2">
                                {["A", "B", "C", "D", "E"].map((l, i) => (
                                    <div
                                        key={l}
                                        className="h-8 w-8 rounded-full border-2 border-white flex items-center justify-center text-xs font-bold text-white"
                                        style={{
                                            background: `linear-gradient(135deg, ${["#1A3D64", "#96A78D", "#2a5a8f", "#7a8f72", "#122d4a"][i]}, ${["#2a5a8f", "#7a8f72", "#1A3D64", "#96A78D", "#1A3D64"][i]})`,
                                        }}
                                    >
                                        {l}
                                    </div>
                                ))}
                            </div>
                            <span>10,000+ events planned</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                            {[1, 2, 3, 4, 5].map((i) => (
                                <Star key={i} className="h-4 w-4 fill-amber-400 text-amber-400" />
                            ))}
                            <span>4.9/5 from 2,000+ reviews</span>
                        </div>
                    </div>
                </div>
            </section>

            {/* ── Stats Bar ── */}
            <section className="border-y border-gray-100 bg-white py-10 px-4 sm:px-6 lg:px-8">
                <div className="mx-auto max-w-7xl">
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-8">
                        {stats.map((stat) => (
                            <div key={stat.label} className="text-center">
                                <p className="text-3xl font-bold bg-gradient-to-r from-[#1A3D64] to-[#96A78D] bg-clip-text text-transparent">
                                    {stat.value}
                                </p>
                                <p className="mt-1 text-sm text-gray-500">{stat.label}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ── Event Types ── */}
            <section className="py-20 px-4 sm:px-6 lg:px-8 bg-gray-50">
                <div className="mx-auto max-w-7xl">
                    <div className="text-center mb-12">
                        <h2 className="text-3xl sm:text-4xl font-bold text-gray-900">
                            Every Event, Covered
                        </h2>
                        <p className="mt-4 text-lg text-gray-600">
                            From intimate gatherings to grand celebrations
                        </p>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                        {eventTypes.map((type, i) => (
                            <Link
                                key={type.name}
                                href={`/marketplace?category=${type.name}`}
                                className="group rounded-2xl bg-white border border-gray-100 shadow-sm p-6 text-center hover:shadow-md hover:-translate-y-0.5 transition-all duration-200"
                                style={{ animationDelay: `${i * 60}ms` }}
                            >
                                <div className="text-3xl mb-3">{type.emoji}</div>
                                <h3 className="font-semibold text-gray-900 group-hover:text-[#1A3D64] transition-colors">
                                    {type.name}
                                </h3>
                                <p className="text-xs text-gray-400 mt-1">{type.count} events</p>
                            </Link>
                        ))}
                    </div>
                </div>
            </section>

            {/* ── Features ── */}
            <section className="py-20 px-4 sm:px-6 lg:px-8 bg-white">
                <div className="mx-auto max-w-7xl">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl sm:text-4xl font-bold text-gray-900">
                            Everything You Need to Plan Events
                        </h2>
                        <p className="mt-4 text-lg text-gray-600 max-w-2xl mx-auto">
                            From vendor discovery to booking management, we have you covered.
                        </p>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                        {features.map((feature, i) => (
                            <div
                                key={feature.title}
                                className="group rounded-2xl border border-gray-100 bg-white p-6 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-200"
                            >
                                <div className={`inline-flex rounded-xl p-3 mb-4 ${feature.color}`}>
                                    <feature.icon className="h-6 w-6" />
                                </div>
                                <h3 className="text-lg font-semibold text-gray-900 mb-2">{feature.title}</h3>
                                <p className="text-sm text-gray-600 leading-relaxed">{feature.description}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ── How It Works ── */}
            <section className="py-20 px-4 sm:px-6 lg:px-8 bg-gradient-to-br from-[#EFECE3] via-white to-[#EFECE3]/60">
                <div className="mx-auto max-w-7xl">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl sm:text-4xl font-bold text-gray-900">How It Works</h2>
                        <p className="mt-4 text-lg text-gray-600">Plan your event in 3 simple steps</p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8 relative">
                        {/* Connector line */}
                        <div className="hidden md:block absolute top-8 left-1/3 right-1/3 h-0.5 bg-gradient-to-r from-[#1A3D64]/30 to-[#96A78D]/40" />

                        {[
                            { step: "01", title: "Tell AI Your Vision", desc: "Describe your event — type, date, budget, and preferences. Our AI understands exactly what you need.", icon: Sparkles },
                            { step: "02", title: "Discover Vendors", desc: "Get personalized vendor recommendations. Browse profiles, reviews, and pricing to find your perfect match.", icon: Search },
                            { step: "03", title: "Book & Celebrate", desc: "Book services directly, manage everything in one dashboard, and focus on enjoying your event.", icon: CheckCircle },
                        ].map((item, i) => (
                            <div key={item.step} className="relative text-center">
                                <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-[#1A3D64] to-[#2a5a8f] shadow-lg shadow-[#1A3D64]/20 mb-6">
                                    <item.icon className="h-8 w-8 text-white" />
                                </div>
                                <div className="absolute -top-2 -right-2 h-7 w-7 rounded-full bg-white border-2 border-[#96A78D]/50 flex items-center justify-center text-xs font-bold text-[#1A3D64]">
                                    {item.step}
                                </div>
                                <h3 className="text-xl font-bold text-gray-900 mb-3">{item.title}</h3>
                                <p className="text-gray-600 leading-relaxed">{item.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ── Testimonials ── */}
            <section className="py-20 px-4 sm:px-6 lg:px-8 bg-white">
                <div className="mx-auto max-w-7xl">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl sm:text-4xl font-bold text-gray-900">Loved by Event Planners</h2>
                        <p className="mt-4 text-lg text-gray-600">Join thousands of happy customers across Pakistan</p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        {testimonials.map((t, i) => (
                            <div
                                key={t.name}
                                className="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm hover:shadow-md transition-shadow duration-200"
                            >
                                <div className="flex items-center gap-1 mb-4">
                                    {[...Array(t.rating)].map((_, j) => (
                                        <Star key={j} className="h-4 w-4 fill-amber-400 text-amber-400" />
                                    ))}
                                </div>
                                <p className="text-gray-700 leading-relaxed italic mb-6">
                                    &ldquo;{t.text}&rdquo;
                                </p>
                                <div className="flex items-center gap-3">
                                    <div className={`h-10 w-10 rounded-full bg-gradient-to-br ${t.color} flex items-center justify-center text-sm font-bold text-white`}>
                                        {t.avatar}
                                    </div>
                                    <div>
                                        <p className="font-semibold text-gray-900 text-sm">{t.name}</p>
                                        <p className="text-xs text-gray-500">{t.role}</p>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ── CTA ── */}
            <section className="px-4 sm:px-6 lg:px-8 py-20 bg-gray-50">
                <div className="mx-auto max-w-4xl">
                    <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-[#1A3D64] to-[#2a5a8f] px-8 py-16 text-center shadow-2xl">
                        <div className="absolute -top-16 -right-16 h-64 w-64 rounded-full bg-white/10" />
                        <div className="absolute -bottom-16 -left-16 h-64 w-64 rounded-full bg-white/10" />
                        <div className="relative">
                            <h2 className="text-3xl sm:text-4xl font-bold text-white">
                                Ready to Plan Your Event?
                            </h2>
                            <p className="mt-4 text-lg text-[#EFECE3]/80 max-w-xl mx-auto">
                                Join 10,000+ event planners using Event-AI to create memorable experiences across Pakistan.
                            </p>
                            <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
                                <Link
                                    href="/signup"
                                    className="rounded-xl bg-[#EFECE3] px-8 py-3.5 text-base font-semibold text-[#1A3D64] hover:bg-white active:scale-[0.98] transition-all duration-150 shadow-lg"
                                >
                                    Create Free Account
                                </Link>
                                <Link
                                    href="/marketplace"
                                    className="rounded-xl border-2 border-white/40 px-8 py-3.5 text-base font-semibold text-white hover:bg-white/10 active:scale-[0.98] transition-all duration-150"
                                >
                                    Explore Vendors
                                </Link>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* ── Footer ── */}
            <footer className="border-t border-gray-200 bg-white px-4 sm:px-6 lg:px-8 py-12">
                <div className="mx-auto max-w-7xl">
                    <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                        <div className="flex items-center gap-2">
                            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-[#1A3D64] to-[#96A78D]">
                                <Calendar className="h-4 w-4 text-white" />
                            </div>
                            <span className="font-bold text-gray-900">Event-AI</span>
                        </div>
                        <div className="flex items-center gap-6 text-sm text-gray-500">
                            <Link href="/marketplace" className="hover:text-gray-900 transition-colors">Vendors</Link>
                            <Link href="/create-event" className="hover:text-gray-900 transition-colors">Plan Event</Link>
                            <Link href="/chat" className="hover:text-gray-900 transition-colors">AI Assistant</Link>
                        </div>
                        <p className="text-sm text-gray-400">© 2026 Event-AI. All rights reserved.</p>
                    </div>
                </div>
            </footer>
        </div>
    );
}
