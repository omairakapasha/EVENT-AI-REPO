'use client';

import { useState, useRef, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Send, Loader2, Check, X, FileText, Receipt, Sparkles } from 'lucide-react';
import { VendorLayout } from '@/components/vendor-layout';
import { QuoteBuilderDialog } from '@/components/quote-builder-dialog';
import { useBookingDetail, useBookingMessages, useSendMessage } from '@/lib/hooks/use-booking-detail';
import { useConfirmBooking, useRejectBooking } from '@/lib/hooks/use-vendor-bookings';
import { useBookingQuotes, useWithdrawQuote, useRespondToCounter, useCounterOffers } from '@/lib/hooks/use-quotes';
import { useAuthStore } from '@/lib/auth-store';
import { cn, formatCurrency, formatDate, formatDateTime } from '@/lib/utils';

const STATUS_COLORS: Record<string, string> = {
    pending: 'bg-yellow-100 text-yellow-700',
    quoted: 'bg-amber-100 text-amber-700',
    negotiating: 'bg-orange-100 text-orange-700',
    accepted: 'bg-emerald-100 text-emerald-700',
    awaiting_deposit: 'bg-cyan-100 text-cyan-700',
    confirmed: 'bg-blue-100 text-blue-700',
    in_progress: 'bg-indigo-100 text-indigo-700',
    completed: 'bg-green-100 text-green-700',
    cancelled: 'bg-red-100 text-red-700',
    rejected: 'bg-gray-100 text-gray-700',
    no_show: 'bg-gray-100 text-gray-500',
};

const QUOTE_STATUS_COLORS: Record<string, string> = {
    draft: 'bg-gray-100 text-gray-700',
    sent: 'bg-amber-100 text-amber-700',
    countered: 'bg-orange-100 text-orange-700',
    accepted: 'bg-emerald-100 text-emerald-700',
    withdrawn: 'bg-gray-100 text-gray-500',
    expired: 'bg-gray-100 text-gray-500',
};

export default function BookingDetailPage() {
    const { id } = useParams<{ id: string }>();
    const router = useRouter();
    const { vendor } = useAuthStore();
    const [message, setMessage] = useState('');
    const [rejectOpen, setRejectOpen] = useState(false);
    const [rejectReason, setRejectReason] = useState('');
    const [quoteBuilderOpen, setQuoteBuilderOpen] = useState(false);
    const bottomRef = useRef<HTMLDivElement>(null);

    const { data: booking, isLoading: loadingBooking } = useBookingDetail(id);
    const { data: messages = [], isLoading: loadingMessages } = useBookingMessages(id);
    const { data: quotes = [] } = useBookingQuotes(id);
    const send = useSendMessage(id);
    const confirm = useConfirmBooking();
    const reject = useRejectBooking();
    const withdrawQuote = useWithdrawQuote(id);
    const respondCounter = useRespondToCounter(id);

    const activeQuote = quotes.find((q) => q.status === 'sent' || q.status === 'countered') ?? null;
    const { data: counters = [] } = useCounterOffers(activeQuote?.id ?? null);
    const pendingCounter = counters.find((c) => c.status === 'pending');
    const canSendQuote = booking?.status === 'pending' || booking?.status === 'negotiating';

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSend = async () => {
        if (!message.trim() || send.isPending) return;
        await send.mutateAsync(message.trim());
        setMessage('');
    };

    return (
        <VendorLayout>
            <div className="space-y-6">
                <button onClick={() => router.back()} className="flex items-center gap-2 text-sm text-surface-500 hover:text-surface-900">
                    <ArrowLeft className="h-4 w-4" /> Back to Bookings
                </button>

                {loadingBooking ? (
                    <div className="flex justify-center py-20"><Loader2 className="h-8 w-8 animate-spin text-primary-600" /></div>
                ) : !booking ? (
                    <p className="text-center text-surface-500">Booking not found.</p>
                ) : (
                    <>
                    {booking.status === 'pending' && quotes.length === 0 && (
                        <div className="rounded-xl border border-amber-200 bg-amber-50 p-5 flex flex-col sm:flex-row items-start sm:items-center gap-4 dark:border-amber-900/40 dark:bg-amber-900/10">
                            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-100 dark:bg-amber-900/30">
                                <Sparkles className="h-5 w-5 text-amber-700 dark:text-amber-400" />
                            </div>
                            <div className="flex-1">
                                <p className="font-semibold text-amber-900 dark:text-amber-200">New booking request</p>
                                <p className="text-sm text-amber-700 dark:text-amber-400 mt-0.5">
                                    Send a custom quote to start the negotiation, or confirm/reject the booking directly.
                                </p>
                            </div>
                            <button
                                onClick={() => setQuoteBuilderOpen(true)}
                                className="shrink-0 flex items-center gap-2 rounded-xl bg-amber-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-amber-800 active:scale-[0.98] transition-all"
                            >
                                <FileText className="h-4 w-4" />
                                Send Quote
                            </button>
                        </div>
                    )}

                    <div className="grid gap-6 lg:grid-cols-3">
                        {/* Booking details */}
                        <div className="rounded-xl border border-surface-200 bg-white p-6 dark:border-surface-800 dark:bg-surface-900 lg:col-span-1">
                            <h2 className="mb-4 text-lg font-semibold text-surface-900 dark:text-surface-50">Booking Details</h2>
                            <dl className="space-y-3 text-sm">
                                <div>
                                    <dt className="text-surface-500">Client</dt>
                                    <dd className="font-medium text-surface-900 dark:text-surface-50">{booking.client_name ?? '—'}</dd>
                                </div>
                                <div>
                                    <dt className="text-surface-500">Event Date</dt>
                                    <dd className="font-medium text-surface-900 dark:text-surface-50">{formatDate(booking.event_date)}</dd>
                                </div>
                                <div>
                                    <dt className="text-surface-500">Status</dt>
                                    <dd>
                                        <span className={cn('rounded-full px-2.5 py-0.5 text-xs font-medium', STATUS_COLORS[booking.status] ?? 'bg-gray-100 text-gray-700')}>
                                            {booking.status.replace('_', ' ')}
                                        </span>
                                    </dd>
                                </div>
                                <div>
                                    <dt className="text-surface-500">Total Price</dt>
                                    <dd className="font-medium text-surface-900 dark:text-surface-50">{formatCurrency(booking.total_price)}</dd>
                                </div>
                                {booking.event_location && (
                                    <div>
                                        <dt className="text-surface-500">Location</dt>
                                        <dd className="font-medium text-surface-900 dark:text-surface-50">
                                            {typeof booking.event_location === 'object'
                                                ? Object.values(booking.event_location).filter(Boolean).join(', ')
                                                : String(booking.event_location)}
                                        </dd>
                                    </div>
                                )}
                                {booking.special_requirements && (
                                    <div>
                                        <dt className="text-surface-500">Special Requirements</dt>
                                        <dd className="text-surface-700 dark:text-surface-300">{booking.special_requirements}</dd>
                                    </div>
                                )}
                            </dl>

                            {booking.status === 'pending' && (
                                <div className="mt-6 flex flex-col gap-2 border-t border-surface-200 pt-4 dark:border-surface-800">
                                    <button
                                        onClick={() => confirm.mutate(booking.id)}
                                        disabled={confirm.isPending}
                                        className="flex w-full items-center justify-center gap-2 rounded-lg bg-green-600 px-3 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
                                    >
                                        {confirm.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                                        Confirm Booking
                                    </button>
                                    <button
                                        onClick={() => setRejectOpen(true)}
                                        disabled={reject.isPending}
                                        className="flex w-full items-center justify-center gap-2 rounded-lg bg-red-600 px-3 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
                                    >
                                        <X className="h-4 w-4" />
                                        Reject Booking
                                    </button>
                                </div>
                            )}

                            {canSendQuote && (
                                <div className="mt-6 border-t border-surface-200 pt-4 dark:border-surface-800">
                                    <button
                                        onClick={() => setQuoteBuilderOpen(true)}
                                        className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary-600 px-3 py-2 text-sm font-medium text-white hover:bg-primary-700"
                                    >
                                        <FileText className="h-4 w-4" />
                                        {booking.status === 'negotiating' ? 'Send Revised Quote' : 'Send Quote'}
                                    </button>
                                </div>
                            )}
                        </div>

                        {/* Quotes panel */}
                        {quotes.length > 0 && (
                            <div className="rounded-xl border border-surface-200 bg-white p-6 dark:border-surface-800 dark:bg-surface-900 lg:col-span-3">
                                <div className="mb-4 flex items-center gap-2">
                                    <Receipt className="h-5 w-5 text-primary-600" />
                                    <h2 className="text-lg font-semibold text-surface-900 dark:text-surface-50">Quotes</h2>
                                </div>
                                <div className="space-y-3">
                                    {quotes.map((q) => (
                                        <div key={q.id} className="rounded-lg border border-surface-200 p-4 dark:border-surface-800">
                                            <div className="flex items-start justify-between gap-4">
                                                <div className="flex-1 space-y-1">
                                                    <div className="flex items-center gap-2 text-sm">
                                                        <span className="font-medium text-surface-900 dark:text-surface-50">
                                                            Round {q.round_number}
                                                        </span>
                                                        <span className={cn('rounded-full px-2 py-0.5 text-xs font-medium', QUOTE_STATUS_COLORS[q.status] ?? 'bg-gray-100 text-gray-700')}>
                                                            {q.status}
                                                        </span>
                                                        <span className="text-xs text-surface-500">
                                                            {formatDateTime(q.created_at)}
                                                        </span>
                                                    </div>
                                                    <p className="text-lg font-semibold text-surface-900 dark:text-surface-50">
                                                        PKR {q.subtotal.toLocaleString()}
                                                        {q.deposit_required > 0 && (
                                                            <span className="ml-2 text-sm font-normal text-surface-500">
                                                                · Deposit: PKR {q.deposit_required.toLocaleString()}
                                                            </span>
                                                        )}
                                                    </p>
                                                    {q.valid_until && (
                                                        <p className="text-xs text-surface-500">
                                                            Valid until {formatDate(q.valid_until)}
                                                        </p>
                                                    )}
                                                    {q.notes && (
                                                        <p className="mt-1 text-sm text-surface-700 dark:text-surface-300">
                                                            {q.notes}
                                                        </p>
                                                    )}
                                                </div>
                                                {q.status === 'sent' && (
                                                    <button
                                                        onClick={() => withdrawQuote.mutate(q.id)}
                                                        disabled={withdrawQuote.isPending}
                                                        className="rounded-lg border border-surface-300 px-3 py-1.5 text-xs font-medium text-surface-700 hover:bg-surface-50 disabled:opacity-50 dark:border-surface-700 dark:text-surface-300"
                                                    >
                                                        Withdraw
                                                    </button>
                                                )}
                                            </div>

                                            {q.id === activeQuote?.id && pendingCounter && (
                                                <div className="mt-4 rounded-lg border border-orange-200 bg-orange-50 p-3 dark:border-orange-900/40 dark:bg-orange-900/10">
                                                    <p className="text-xs font-medium uppercase tracking-wide text-orange-700 dark:text-orange-400">
                                                        Customer counter-offer
                                                    </p>
                                                    <p className="mt-1 text-lg font-semibold text-surface-900 dark:text-surface-50">
                                                        PKR {pendingCounter.proposed_total.toLocaleString()}
                                                    </p>
                                                    {pendingCounter.message && (
                                                        <p className="mt-1 text-sm text-surface-700 dark:text-surface-300">
                                                            &ldquo;{pendingCounter.message}&rdquo;
                                                        </p>
                                                    )}
                                                    <div className="mt-3 flex gap-2">
                                                        <button
                                                            onClick={() => respondCounter.mutate({ counterId: pendingCounter.id, action: 'accept' })}
                                                            disabled={respondCounter.isPending}
                                                            className="flex items-center gap-1 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
                                                        >
                                                            <Check className="h-3.5 w-3.5" /> Accept
                                                        </button>
                                                        <button
                                                            onClick={() => respondCounter.mutate({ counterId: pendingCounter.id, action: 'reject' })}
                                                            disabled={respondCounter.isPending}
                                                            className="flex items-center gap-1 rounded-lg border border-red-300 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-50 disabled:opacity-50"
                                                        >
                                                            <X className="h-3.5 w-3.5" /> Reject
                                                        </button>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Messages thread */}
                        <div className="flex flex-col rounded-xl border border-surface-200 bg-white dark:border-surface-800 dark:bg-surface-900 lg:col-span-2">
                            <div className="border-b border-surface-200 px-6 py-4 dark:border-surface-800">
                                <h2 className="text-lg font-semibold text-surface-900 dark:text-surface-50">Messages</h2>
                            </div>

                            <div className="flex-1 overflow-y-auto p-6 space-y-4 min-h-[300px] max-h-[500px]">
                                {loadingMessages ? (
                                    <div className="flex justify-center py-8"><Loader2 className="h-6 w-6 animate-spin text-primary-600" /></div>
                                ) : messages.length === 0 ? (
                                    <p className="text-center text-sm text-surface-500">No messages yet. Start the conversation.</p>
                                ) : (
                                    messages.map((msg) => {
                                        const isVendor = msg.sender_type === 'vendor';
                                        return (
                                            <div key={msg.id} className={cn('flex', isVendor ? 'justify-end' : 'justify-start')}>
                                                <div className={cn(
                                                    'max-w-[70%] rounded-2xl px-4 py-2.5 text-sm',
                                                    isVendor
                                                        ? 'bg-primary-600 text-white'
                                                        : 'bg-surface-100 text-surface-900 dark:bg-surface-800 dark:text-surface-50'
                                                )}>
                                                    <p>{msg.message}</p>
                                                    <p className={cn('mt-1 text-xs', isVendor ? 'text-primary-200' : 'text-surface-400')}>
                                                        {formatDateTime(msg.created_at)}
                                                    </p>
                                                </div>
                                            </div>
                                        );
                                    })
                                )}
                                <div ref={bottomRef} />
                            </div>

                            <div className="border-t border-surface-200 p-4 dark:border-surface-800">
                                <div className="flex gap-3">
                                    <textarea
                                        value={message}
                                        onChange={(e) => setMessage(e.target.value)}
                                        onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
                                        placeholder="Type a message…"
                                        rows={2}
                                        className="flex-1 resize-none rounded-lg border border-surface-300 p-3 text-sm focus:border-primary-500 focus:outline-none dark:border-surface-700 dark:bg-surface-800"
                                    />
                                    <button
                                        onClick={handleSend}
                                        disabled={!message.trim() || send.isPending}
                                        className="flex items-center gap-2 self-end rounded-lg bg-primary-600 px-4 py-2.5 text-sm text-white hover:bg-primary-700 disabled:opacity-50"
                                    >
                                        {send.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                                        Send
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                    </>
                )}
            </div>
            {booking && (
                <QuoteBuilderDialog
                    bookingId={booking.id}
                    open={quoteBuilderOpen}
                    onClose={() => setQuoteBuilderOpen(false)}
                />
            )}
            {rejectOpen && booking && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
                    <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl dark:bg-surface-900">
                        <h3 className="text-lg font-semibold text-surface-900 dark:text-surface-50">Reject Booking</h3>
                        <p className="mt-1 text-sm text-surface-500">Optionally provide a reason for the customer.</p>
                        <textarea
                            value={rejectReason}
                            onChange={(e) => setRejectReason(e.target.value)}
                            placeholder="Reason (optional)"
                            rows={3}
                            className="mt-4 w-full rounded-lg border border-surface-300 p-3 text-sm focus:border-primary-500 focus:outline-none dark:border-surface-700 dark:bg-surface-800"
                        />
                        <div className="mt-4 flex justify-end gap-3">
                            <button onClick={() => setRejectOpen(false)} className="rounded-lg border border-surface-300 px-4 py-2 text-sm hover:bg-surface-50">Cancel</button>
                            <button
                                onClick={async () => {
                                    await reject.mutateAsync({ bookingId: booking.id, reason: rejectReason || undefined });
                                    setRejectOpen(false);
                                    setRejectReason('');
                                }}
                                disabled={reject.isPending}
                                className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm text-white hover:bg-red-700 disabled:opacity-50"
                            >
                                {reject.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                                Reject
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </VendorLayout>
    );
}
