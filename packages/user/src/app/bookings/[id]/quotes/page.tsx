'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
    ArrowLeft, CheckCircle2, Loader2, MessageCircleQuestion, Receipt, XCircle,
} from 'lucide-react';
import toast from 'react-hot-toast';
import {
    acceptQuote, getBookingQuotes, submitCounterOffer, type UserQuote,
} from '@/lib/api';

const STATUS_COLORS: Record<string, string> = {
    draft: 'bg-gray-100 text-gray-700',
    sent: 'bg-amber-100 text-amber-800',
    countered: 'bg-orange-100 text-orange-800',
    accepted: 'bg-emerald-100 text-emerald-800',
    withdrawn: 'bg-gray-100 text-gray-500',
    expired: 'bg-gray-100 text-gray-500',
};


function CounterOfferDialog({
    quote, open, onClose,
}: { quote: UserQuote; open: boolean; onClose: () => void }) {
    const [proposedTotal, setProposedTotal] = useState(String(quote.subtotal));
    const [message, setMessage] = useState('');
    const qc = useQueryClient();

    const counter = useMutation({
        mutationFn: () =>
            submitCounterOffer(quote.id, {
                proposed_total: parseFloat(proposedTotal),
                message: message.trim() || undefined,
            }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['booking-quotes', quote.booking_id] });
            toast.success('Counter-offer sent to vendor');
            onClose();
        },
        onError: (err: unknown) => {
            const e = err as { response?: { data?: { error?: { message?: string } } }; message?: string };
            toast.error(e.response?.data?.error?.message ?? e.message ?? 'Failed to send counter-offer');
        },
    });

    if (!open) return null;
    const proposedValue = parseFloat(proposedTotal);
    const canSubmit = !Number.isNaN(proposedValue) && proposedValue > 0 && !counter.isPending;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
            <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
                <h3 className="text-lg font-semibold text-gray-900">Send counter-offer</h3>
                <p className="mt-1 text-sm text-gray-500">
                    Current quote: <span className="font-medium">PKR {quote.subtotal.toLocaleString()}</span>
                </p>
                <div className="mt-4 space-y-4">
                    <div>
                        <label className="block text-xs font-medium uppercase tracking-wide text-gray-500">
                            Your proposed total (PKR)
                        </label>
                        <input
                            type="number"
                            min="1"
                            step="100"
                            value={proposedTotal}
                            onChange={(e) => setProposedTotal(e.target.value)}
                            className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-medium uppercase tracking-wide text-gray-500">
                            Message (optional)
                        </label>
                        <textarea
                            value={message}
                            onChange={(e) => setMessage(e.target.value)}
                            rows={3}
                            placeholder="Reason for the counter-offer."
                            className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                        />
                    </div>
                </div>
                <div className="mt-5 flex justify-end gap-2">
                    <button
                        onClick={onClose}
                        className="rounded-lg border border-gray-300 px-4 py-2 text-sm hover:bg-gray-50"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={() => counter.mutate()}
                        disabled={!canSubmit}
                        className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
                    >
                        {counter.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                        Send counter-offer
                    </button>
                </div>
            </div>
        </div>
    );
}


export default function BookingQuotesPage() {
    const { id } = useParams<{ id: string }>();
    const router = useRouter();
    const qc = useQueryClient();
    const [counterFor, setCounterFor] = useState<UserQuote | null>(null);

    const { data: quotes = [], isLoading } = useQuery({
        queryKey: ['booking-quotes', id],
        queryFn: () => getBookingQuotes(id),
        enabled: !!id,
    });

    const accept = useMutation({
        mutationFn: (quoteId: string) => acceptQuote(quoteId),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['booking-quotes', id] });
            qc.invalidateQueries({ queryKey: ['bookings'] });
            toast.success('Quote accepted');
        },
        onError: (err: unknown) => {
            const e = err as { response?: { data?: { error?: { message?: string } } }; message?: string };
            toast.error(e.response?.data?.error?.message ?? e.message ?? 'Failed to accept quote');
        },
    });

    return (
        <div className="max-w-4xl mx-auto px-4 py-8">
            <button
                onClick={() => router.back()}
                className="mb-6 inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
            >
                <ArrowLeft className="h-4 w-4" /> Back
            </button>

            <div className="mb-6">
                <h1 className="text-2xl font-bold text-gray-900">Quotes for this booking</h1>
                <p className="mt-1 text-gray-500">
                    Review, accept, or counter the vendor&apos;s proposals.
                </p>
            </div>

            {isLoading ? (
                <div className="flex justify-center py-20">
                    <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
                </div>
            ) : quotes.length === 0 ? (
                <div className="bg-white rounded-xl border border-gray-100 p-12 text-center shadow-sm">
                    <Receipt className="h-10 w-10 text-gray-300 mx-auto mb-3" />
                    <p className="text-gray-500">No quotes have been sent yet.</p>
                </div>
            ) : (
                <div className="space-y-4">
                    {quotes.map((q) => {
                        const statusClass = STATUS_COLORS[q.status] ?? 'bg-gray-100 text-gray-700';
                        const canAct = q.status === 'sent';
                        return (
                            <div key={q.id} className="bg-white rounded-xl border border-gray-100 p-6 shadow-sm">
                                <div className="flex items-start justify-between gap-4">
                                    <div className="flex-1 space-y-1">
                                        <div className="flex items-center gap-2 text-sm">
                                            <span className="font-medium text-gray-900">Round {q.round_number}</span>
                                            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusClass}`}>
                                                {q.status}
                                            </span>
                                            <span className="text-xs text-gray-500">
                                                {new Date(q.created_at).toLocaleString('en-PK')}
                                            </span>
                                        </div>
                                        <p className="text-2xl font-semibold text-gray-900">
                                            PKR {q.subtotal.toLocaleString()}
                                        </p>
                                        {q.deposit_required > 0 && (
                                            <p className="text-sm text-gray-500">
                                                Deposit required: PKR {q.deposit_required.toLocaleString()}
                                            </p>
                                        )}
                                        {q.valid_until && (
                                            <p className="text-xs text-gray-500">
                                                Valid until {new Date(q.valid_until).toLocaleDateString('en-PK')}
                                            </p>
                                        )}
                                        {q.notes && (
                                            <p className="mt-2 text-sm text-gray-700 bg-gray-50 rounded px-3 py-2">
                                                {q.notes}
                                            </p>
                                        )}
                                    </div>
                                </div>

                                {q.line_items.length > 0 && (
                                    <div className="mt-4 border-t border-gray-100 pt-3">
                                        <table className="w-full text-sm">
                                            <thead>
                                                <tr className="text-xs uppercase tracking-wide text-gray-500">
                                                    <th className="text-left font-medium pb-1">Item</th>
                                                    <th className="text-right font-medium pb-1">Qty</th>
                                                    <th className="text-right font-medium pb-1">Unit</th>
                                                    <th className="text-right font-medium pb-1">Total</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {q.line_items.map((li, idx) => (
                                                    <tr key={idx} className="border-t border-gray-50">
                                                        <td className="py-1.5 text-gray-700">{li.description}</td>
                                                        <td className="py-1.5 text-right text-gray-700">{li.quantity}</td>
                                                        <td className="py-1.5 text-right text-gray-700">PKR {li.unit_price.toLocaleString()}</td>
                                                        <td className="py-1.5 text-right font-medium text-gray-900">PKR {li.total.toLocaleString()}</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}

                                {canAct && (
                                    <div className="mt-4 flex flex-wrap gap-2 border-t border-gray-100 pt-3">
                                        <button
                                            onClick={() => accept.mutate(q.id)}
                                            disabled={accept.isPending}
                                            className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
                                        >
                                            <CheckCircle2 className="h-4 w-4" /> Accept quote
                                        </button>
                                        <button
                                            onClick={() => setCounterFor(q)}
                                            className="inline-flex items-center gap-1.5 rounded-lg border border-indigo-300 px-4 py-2 text-sm font-medium text-indigo-700 hover:bg-indigo-50"
                                        >
                                            <MessageCircleQuestion className="h-4 w-4" /> Counter-offer
                                        </button>
                                    </div>
                                )}

                                {q.status === 'countered' && (
                                    <p className="mt-4 flex items-center gap-1.5 border-t border-gray-100 pt-3 text-sm text-orange-700">
                                        <MessageCircleQuestion className="h-4 w-4" />
                                        Waiting for vendor to respond to your counter-offer.
                                    </p>
                                )}
                                {q.status === 'withdrawn' && (
                                    <p className="mt-4 flex items-center gap-1.5 border-t border-gray-100 pt-3 text-sm text-gray-500">
                                        <XCircle className="h-4 w-4" />
                                        Vendor withdrew this quote.
                                    </p>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}

            {counterFor && (
                <CounterOfferDialog
                    quote={counterFor}
                    open={!!counterFor}
                    onClose={() => setCounterFor(null)}
                />
            )}
        </div>
    );
}
