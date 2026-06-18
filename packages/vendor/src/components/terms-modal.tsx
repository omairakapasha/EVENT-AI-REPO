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
                <div className="px-8 pt-8 pb-4 border-b border-gray-100">
                    <div className="flex items-center gap-3 mb-1">
                        <div className="h-9 w-9 rounded-xl flex items-center justify-center bg-indigo-600">
                            <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                    d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                            </svg>
                        </div>
                        <h2 className="text-xl font-semibold text-gray-900">Vendor Terms & Conditions</h2>
                    </div>
                    <p className="text-sm text-gray-500">Please read and accept before accessing your vendor dashboard.</p>
                </div>

                <div className="overflow-y-auto flex-1 px-8 py-5 text-sm text-gray-700 space-y-4 leading-relaxed">
                    <section>
                        <h3 className="font-semibold text-gray-900 mb-1">1. Vendor Registration</h3>
                        <p>By registering as a vendor on Event-AI, you represent that you are authorised to offer the services listed on your profile and that all information provided is accurate and truthful.</p>
                    </section>
                    <section>
                        <h3 className="font-semibold text-gray-900 mb-1">2. Service Listings</h3>
                        <p>You are solely responsible for the accuracy of your service listings, including pricing, availability, and descriptions. Misleading listings may result in account suspension.</p>
                    </section>
                    <section>
                        <h3 className="font-semibold text-gray-900 mb-1">3. Booking Obligations</h3>
                        <p>Upon confirming a booking, you are contractually obligated to deliver the agreed service. Cancellations without valid reason may affect your vendor rating and account standing.</p>
                    </section>
                    <section>
                        <h3 className="font-semibold text-gray-900 mb-1">4. Platform Commission</h3>
                        <p>Event-AI charges a platform commission on completed bookings as per the current fee schedule. Commission rates are subject to change with 30 days' written notice.</p>
                    </section>
                    <section>
                        <h3 className="font-semibold text-gray-900 mb-1">5. Conduct Standards</h3>
                        <p>Vendors must maintain professional conduct in all interactions with users. Discrimination, harassment, or fraudulent behaviour will result in immediate account termination.</p>
                    </section>
                    <section>
                        <h3 className="font-semibold text-gray-900 mb-1">6. Intellectual Property</h3>
                        <p>By uploading content (photos, descriptions, logos), you grant Event-AI a non-exclusive licence to display such content on the Platform for the purpose of promoting your services.</p>
                    </section>
                    <section>
                        <h3 className="font-semibold text-gray-900 mb-1">7. Privacy & Data</h3>
                        <p>Your business data and user interactions are processed per our Privacy Policy. You must not misuse customer data obtained through the Platform for purposes outside the agreed booking.</p>
                    </section>
                    <section>
                        <h3 className="font-semibold text-gray-900 mb-1">8. Suspension & Termination</h3>
                        <p>Event-AI reserves the right to suspend or terminate vendor accounts that violate these Terms, receive excessive complaints, or fail to maintain minimum service standards.</p>
                    </section>
                    <section>
                        <h3 className="font-semibold text-gray-900 mb-1">9. Governing Law</h3>
                        <p>These Terms are governed by the applicable laws of the user's jurisdiction. Disputes shall be subject to the courts of competent jurisdiction in that location.</p>
                    </section>
                </div>

                <div className="px-8 py-5 border-t border-gray-100 space-y-4">
                    <label className="flex items-start gap-3 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={agreed}
                            onChange={(e) => setAgreed(e.target.checked)}
                            className="mt-0.5 h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 cursor-pointer"
                        />
                        <span className="text-sm text-gray-700 leading-snug">
                            I have read and agree to the <strong>Vendor Terms & Conditions</strong> and <strong>Privacy Policy</strong>.
                        </span>
                    </label>
                    <button
                        onClick={onAccept}
                        disabled={!agreed || isAccepting}
                        className="w-full py-3 px-6 rounded-xl text-white font-medium text-sm transition-all bg-indigo-600
                            disabled:opacity-40 disabled:cursor-not-allowed
                            enabled:hover:bg-indigo-700 enabled:active:scale-[0.98]
                            flex items-center justify-center gap-2"
                    >
                        {isAccepting && <Loader2 className="h-4 w-4 animate-spin" />}
                        {isAccepting ? "Saving…" : "Accept & Continue"}
                    </button>
                </div>
            </div>
        </div>
    );
}
