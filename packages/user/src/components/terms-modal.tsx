"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";

interface TermsModalProps {
    onAccept: () => void;
    isAccepting: boolean;
}

export function TermsModal({ onAccept, isAccepting }: TermsModalProps) {
    const [agreed, setAgreed] = useState(false);

    return (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl flex flex-col max-h-[90vh]">
                {/* Header */}
                <div className="px-8 pt-8 pb-4 border-b border-gray-100">
                    <div className="flex items-center gap-3 mb-1">
                        <div className="h-9 w-9 rounded-xl flex items-center justify-center"
                            style={{ background: "linear-gradient(135deg, #1A3D64, #2a5a8f)" }}>
                            <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                    d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                            </svg>
                        </div>
                        <h2 className="text-xl font-semibold text-gray-900">Terms & Conditions</h2>
                    </div>
                    <p className="text-sm text-gray-500">Please read and accept before continuing.</p>
                </div>

                {/* Scrollable terms body */}
                <div className="overflow-y-auto flex-1 px-8 py-5 text-sm text-gray-700 space-y-4 leading-relaxed">
                    <section>
                        <h3 className="font-semibold text-gray-900 mb-1">1. Acceptance of Terms</h3>
                        <p>By accessing or using Event-AI (&quot;the Platform&quot;), you agree to be bound by these Terms and Conditions. If you do not agree, you may not use the Platform.</p>
                    </section>
                    <section>
                        <h3 className="font-semibold text-gray-900 mb-1">2. Platform Description</h3>
                        <p>Event-AI is an AI-powered event planning marketplace connecting users with vendors for events. The Platform facilitates vendor discovery, booking coordination, and AI-assisted planning. Event-AI acts solely as an intermediary; all contracts are between users and vendors directly.</p>
                    </section>
                    <section>
                        <h3 className="font-semibold text-gray-900 mb-1">3. User Responsibilities</h3>
                        <p>You are responsible for (a) maintaining the confidentiality of your account; (b) all activity under your account; (c) ensuring information you provide is accurate and current; (d) complying with all applicable laws and regulations when using the Platform.</p>
                    </section>
                    <section>
                        <h3 className="font-semibold text-gray-900 mb-1">4. Bookings & Payments</h3>
                        <p>Bookings are subject to vendor availability and confirmation. Pricing is set by individual vendors and may vary. Event-AI does not guarantee vendor availability, quality, or timely delivery. All payment disputes must first be resolved directly with the vendor.</p>
                    </section>
                    <section>
                        <h3 className="font-semibold text-gray-900 mb-1">5. AI-Assisted Features</h3>
                        <p>AI recommendations and suggestions are provided for informational purposes only. Event-AI does not guarantee the accuracy, completeness, or suitability of AI-generated content. You should independently verify all vendor information before making booking decisions.</p>
                    </section>
                    <section>
                        <h3 className="font-semibold text-gray-900 mb-1">6. Privacy & Data</h3>
                        <p>Your personal data is collected and processed in accordance with our Privacy Policy. By using the Platform you consent to the collection, use, and sharing of your data as described therein. Event-AI does not sell personal data to third parties.</p>
                    </section>
                    <section>
                        <h3 className="font-semibold text-gray-900 mb-1">7. Prohibited Conduct</h3>
                        <p>You may not: use the Platform for unlawful purposes; attempt to circumvent security measures; post false or misleading information; harass other users or vendors; or engage in fraudulent transactions.</p>
                    </section>
                    <section>
                        <h3 className="font-semibold text-gray-900 mb-1">8. Limitation of Liability</h3>
                        <p>To the maximum extent permitted by applicable law, Event-AI shall not be liable for any indirect, incidental, special, or consequential damages arising from your use of the Platform, including but not limited to disputes between users and vendors.</p>
                    </section>
                    <section>
                        <h3 className="font-semibold text-gray-900 mb-1">9. Modifications</h3>
                        <p>Event-AI reserves the right to update these Terms at any time. Material changes will be communicated through the Platform. Continued use after changes constitutes acceptance of the revised Terms.</p>
                    </section>
                    <section>
                        <h3 className="font-semibold text-gray-900 mb-1">10. Governing Law</h3>
                        <p>These Terms are governed by the applicable laws of the user's jurisdiction. Any disputes shall be subject to the courts of competent jurisdiction in that location.</p>
                    </section>
                </div>

                {/* Footer */}
                <div className="px-8 py-5 border-t border-gray-100 space-y-4">
                    <label className="flex items-start gap-3 cursor-pointer group">
                        <input
                            type="checkbox"
                            checked={agreed}
                            onChange={(e) => setAgreed(e.target.checked)}
                            className="mt-0.5 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                        />
                        <span className="text-sm text-gray-700 leading-snug">
                            I have read and agree to the <strong>Terms & Conditions</strong> and <strong>Privacy Policy</strong>.
                        </span>
                    </label>
                    <button
                        onClick={onAccept}
                        disabled={!agreed || isAccepting}
                        className="w-full py-3 px-6 rounded-xl text-white font-medium text-sm transition-all
                            disabled:opacity-40 disabled:cursor-not-allowed
                            enabled:hover:opacity-90 enabled:active:scale-[0.98]
                            flex items-center justify-center gap-2"
                        style={{ background: "linear-gradient(135deg, #1A3D64, #2a5a8f)" }}
                    >
                        {isAccepting && <Loader2 className="h-4 w-4 animate-spin" />}
                        {isAccepting ? "Saving…" : "Accept & Continue"}
                    </button>
                </div>
            </div>
        </div>
    );
}
