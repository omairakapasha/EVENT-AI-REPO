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
                        <div className="h-9 w-9 rounded-xl flex items-center justify-center bg-gray-900">
                            <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                    d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                            </svg>
                        </div>
                        <h2 className="text-xl font-semibold text-gray-900">Admin Terms & Conditions</h2>
                    </div>
                    <p className="text-sm text-gray-500">Read and accept before accessing the admin dashboard.</p>
                </div>

                <div className="overflow-y-auto flex-1 px-8 py-5 text-sm text-gray-700 space-y-4 leading-relaxed">
                    <section>
                        <h3 className="font-semibold text-gray-900 mb-1">1. Admin Access</h3>
                        <p>Admin access is granted solely for platform management purposes. You acknowledge that misuse of admin privileges may result in immediate account termination and legal liability.</p>
                    </section>
                    <section>
                        <h3 className="font-semibold text-gray-900 mb-1">2. Data Confidentiality</h3>
                        <p>As an admin you have access to sensitive user and vendor data. You are strictly prohibited from disclosing, sharing, or using this data for purposes outside your administrative role.</p>
                    </section>
                    <section>
                        <h3 className="font-semibold text-gray-900 mb-1">3. Audit & Accountability</h3>
                        <p>All admin actions are logged and subject to audit. You are personally accountable for actions taken under your credentials. Do not share your login credentials with anyone.</p>
                    </section>
                    <section>
                        <h3 className="font-semibold text-gray-900 mb-1">4. Vendor & User Moderation</h3>
                        <p>Moderation decisions (approvals, suspensions, rejections) must be exercised fairly, consistently, and in accordance with platform policies. Discriminatory moderation is prohibited.</p>
                    </section>
                    <section>
                        <h3 className="font-semibold text-gray-900 mb-1">5. System Integrity</h3>
                        <p>You must not interfere with platform operations, manipulate data outside authorised workflows, or grant unauthorised access to third parties.</p>
                    </section>
                    <section>
                        <h3 className="font-semibold text-gray-900 mb-1">6. Compliance</h3>
                        <p>All administrative activities must comply with applicable Pakistani data protection and IT laws, including but not limited to the Prevention of Electronic Crimes Act 2016.</p>
                    </section>
                    <section>
                        <h3 className="font-semibold text-gray-900 mb-1">7. Governing Law</h3>
                        <p>These Terms are governed by the laws of the Islamic Republic of Pakistan. Disputes shall be subject to the jurisdiction of the courts of Lahore, Punjab.</p>
                    </section>
                </div>

                <div className="px-8 py-5 border-t border-gray-100 space-y-4">
                    <label className="flex items-start gap-3 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={agreed}
                            onChange={(e) => setAgreed(e.target.checked)}
                            className="mt-0.5 h-4 w-4 rounded border-gray-300 text-gray-900 focus:ring-gray-500 cursor-pointer"
                        />
                        <span className="text-sm text-gray-700 leading-snug">
                            I have read and agree to the <strong>Admin Terms & Conditions</strong>.
                        </span>
                    </label>
                    <button
                        onClick={onAccept}
                        disabled={!agreed || isAccepting}
                        className="w-full py-3 px-6 rounded-xl text-white font-medium text-sm transition-all bg-gray-900
                            disabled:opacity-40 disabled:cursor-not-allowed
                            enabled:hover:bg-gray-800 enabled:active:scale-[0.98]
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
