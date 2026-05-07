'use client';

import { useState, useRef, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Send, Loader2 } from 'lucide-react';
import { VendorLayout } from '@/components/vendor-layout';
import { useBookingDetail, useBookingMessages, useSendMessage } from '@/lib/hooks/use-booking-detail';
import { useAuthStore } from '@/lib/auth-store';
import { cn, formatCurrency, formatDate, formatDateTime } from '@/lib/utils';

const STATUS_COLORS: Record<string, string> = {
    pending: 'bg-yellow-100 text-yellow-700',
    confirmed: 'bg-blue-100 text-blue-700',
    in_progress: 'bg-indigo-100 text-indigo-700',
    completed: 'bg-green-100 text-green-700',
    cancelled: 'bg-red-100 text-red-700',
    rejected: 'bg-gray-100 text-gray-700',
    no_show: 'bg-gray-100 text-gray-500',
};

export default function BookingDetailPage() {
    const { id } = useParams<{ id: string }>();
    const router = useRouter();
    const { vendor } = useAuthStore();
    const [message, setMessage] = useState('');
    const bottomRef = useRef<HTMLDivElement>(null);

    const { data: booking, isLoading: loadingBooking } = useBookingDetail(id);
    const { data: messages = [], isLoading: loadingMessages } = useBookingMessages(id);
    const send = useSendMessage(id);

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
                                    <dd className="font-medium text-surface-900 dark:text-surface-50">{formatCurrency(booking.total_price, booking.currency)}</dd>
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
                        </div>

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
                )}
            </div>
        </VendorLayout>
    );
}
