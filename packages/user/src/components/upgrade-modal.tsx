"use client";

import { X, Sparkles, CheckCircle, Mail } from "lucide-react";

const PRO_FEATURES = [
    "Unlimited events",
    "AI-powered planning assistant",
    "Priority vendor matching",
    "Instant booking confirmation",
    "Dedicated customer support",
];

interface UpgradeModalProps {
    onClose: () => void;
}

export function UpgradeModal({ onClose }: UpgradeModalProps) {
    return (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden">
                {/* Header */}
                <div className="relative bg-gradient-to-br from-[#1A3D64] to-[#2a5a8f] px-8 py-7 text-center">
                    <button
                        onClick={onClose}
                        className="absolute right-4 top-4 rounded-lg p-1.5 text-white/60 hover:bg-white/10 hover:text-white transition-colors"
                    >
                        <X className="h-4 w-4" />
                    </button>
                    <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-white/15">
                        <Sparkles className="h-6 w-6 text-white" />
                    </div>
                    <h2 className="text-xl font-bold text-white">Upgrade to Pro</h2>
                    <p className="mt-1 text-sm text-blue-200">Unlock unlimited events and AI-powered planning.</p>
                    <div className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-amber-400/20 border border-amber-400/40 px-3 py-1 text-xs font-semibold text-amber-300">
                        <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse" />
                        Payment launching soon
                    </div>
                </div>

                {/* Features */}
                <div className="px-8 py-5">
                    <p className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-3">What you get</p>
                    <ul className="space-y-2.5">
                        {PRO_FEATURES.map((f) => (
                            <li key={f} className="flex items-center gap-3 text-sm text-gray-700">
                                <CheckCircle className="h-4 w-4 shrink-0 text-[#1A3D64]" />
                                {f}
                            </li>
                        ))}
                    </ul>
                </div>

                {/* CTAs */}
                <div className="px-8 pb-7 border-t border-gray-100 pt-5">
                    <p className="text-xs text-gray-500 text-center mb-3">
                        Interested? Reach out and we&apos;ll get you set up.
                    </p>
                    <a
                        href="mailto:support@eventfree.com?subject=Upgrade%20to%20Pro%20Request"
                        className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#1A3D64] px-4 py-3 text-sm font-semibold text-white hover:bg-[#122d4a] active:scale-[0.98] transition-all"
                    >
                        <Mail className="h-4 w-4" />
                        Email us to upgrade
                    </a>
                </div>
            </div>
        </div>
    );
}
