'use client';

import { useState } from 'react';
import {
    Loader2, MessageSquare, Calendar, Users, Wallet,
    FileText, ChevronDown, ChevronUp, Mail, Phone,
} from 'lucide-react';
import { VendorLayout } from '@/components/vendor-layout';
import { QuoteBuilderDialog } from '@/components/quote-builder-dialog';
import { useInquiries, type Inquiry } from '@/lib/hooks/use-inquiries';
import { cn, formatDate } from '@/lib/utils';

const STATUS_COLORS: Record<string, string> = {
    NEW: 'bg-blue-100 text-blue-700',
    CONTACTED: 'bg-yellow-100 text-yellow-700',
    QUOTED: 'bg-amber-100 text-amber-700',
    CONVERTED: 'bg-emerald-100 text-emerald-700',
    DECLINED: 'bg-gray-100 text-gray-500',
};

const STATUS_LABELS: Record<string, string> = {
    NEW: 'New',
    CONTACTED: 'Contacted',
    QUOTED: 'Quoted',
    CONVERTED: 'Converted',
    DECLINED: 'Declined',
};

const FILTERS = ['All', 'NEW', 'CONTACTED', 'QUOTED', 'CONVERTED', 'DECLINED'] as const;

function InquiryCard({ inquiry, onSendQuote }: { inquiry: Inquiry; onSendQuote: (id: string) => void }) {
    const [expanded, setExpanded] = useState(false);
    const canQuote = inquiry.status === 'NEW' || inquiry.status === 'CONTACTED';

    return (
        <div className="rounded-xl border border-surface-200 bg-white dark:border-surface-800 dark:bg-surface-900">
            <div className="flex items-start justify-between gap-4 p-5">
                <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                        <span className="font-semibold text-surface-900 dark:text-surface-50">
                            {inquiry.customer_name}
                        </span>
                        <span className={cn('rounded-full px-2.5 py-0.5 text-xs font-medium', STATUS_COLORS[inquiry.status])}>
                            {STATUS_LABELS[inquiry.status]}
                        </span>
                        {inquiry.event_type && (
                            <span className="rounded-full bg-surface-100 px-2.5 py-0.5 text-xs text-surface-600 dark:bg-surface-800 dark:text-surface-400">
                                {inquiry.event_type}
                            </span>
                        )}
                    </div>

                    <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-surface-500">
                        <span className="flex items-center gap-1">
                            <Mail className="h-3.5 w-3.5" />
                            {inquiry.customer_email}
                        </span>
                        {inquiry.customer_phone && (
                            <span className="flex items-center gap-1">
                                <Phone className="h-3.5 w-3.5" />
                                {inquiry.customer_phone}
                            </span>
                        )}
                        {inquiry.preferred_date && (
                            <span className="flex items-center gap-1">
                                <Calendar className="h-3.5 w-3.5" />
                                {formatDate(inquiry.preferred_date)}
                            </span>
                        )}
                        {inquiry.expected_guests && (
                            <span className="flex items-center gap-1">
                                <Users className="h-3.5 w-3.5" />
                                {inquiry.expected_guests} guests
                            </span>
                        )}
                        {inquiry.budget_range && (
                            <span className="flex items-center gap-1">
                                <Wallet className="h-3.5 w-3.5" />
                                {inquiry.budget_range}
                            </span>
                        )}
                        <span className="ml-auto text-surface-400">
                            {formatDate(inquiry.created_at)}
                        </span>
                    </div>

                    <p className={cn(
                        'mt-3 text-sm text-surface-700 dark:text-surface-300',
                        !expanded && 'line-clamp-2',
                    )}>
                        {inquiry.message}
                    </p>
                    {inquiry.message.length > 120 && (
                        <button
                            onClick={() => setExpanded((v) => !v)}
                            className="mt-1 flex items-center gap-0.5 text-xs text-primary-600 hover:text-primary-700"
                        >
                            {expanded ? (
                                <><ChevronUp className="h-3.5 w-3.5" /> Show less</>
                            ) : (
                                <><ChevronDown className="h-3.5 w-3.5" /> Show more</>
                            )}
                        </button>
                    )}

                    {inquiry.vendor_response && (
                        <div className="mt-3 rounded-lg border border-surface-200 bg-surface-50 px-3 py-2 text-xs text-surface-600 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-400">
                            <span className="font-medium">Your response: </span>
                            {inquiry.vendor_response}
                        </div>
                    )}

                    {inquiry.quote_id && inquiry.quoted_amount != null && (
                        <p className="mt-2 text-xs text-amber-700 dark:text-amber-400">
                            Quote sent: PKR {inquiry.quoted_amount.toLocaleString()}
                        </p>
                    )}
                </div>

                {canQuote && (
                    <button
                        onClick={() => onSendQuote(inquiry.id)}
                        className="flex flex-shrink-0 items-center gap-1.5 rounded-lg bg-primary-600 px-3 py-2 text-sm font-medium text-white hover:bg-primary-700"
                    >
                        <FileText className="h-4 w-4" />
                        Send Quote
                    </button>
                )}
            </div>
        </div>
    );
}

export default function InquiriesPage() {
    const [filter, setFilter] = useState<string>('All');
    const [quoteInquiryId, setQuoteInquiryId] = useState<string | null>(null);

    const { data: inquiries = [], isLoading } = useInquiries(
        filter === 'All' ? undefined : filter,
    );

    return (
        <VendorLayout>
            <div className="space-y-6">
                <div>
                    <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-50">Inquiries</h1>
                    <p className="mt-1 text-sm text-surface-500">
                        Customer enquiries sent to your vendor profile.
                    </p>
                </div>

                {/* Filters */}
                <div className="flex flex-wrap gap-2">
                    {FILTERS.map((f) => (
                        <button
                            key={f}
                            onClick={() => setFilter(f)}
                            className={cn(
                                'rounded-full px-3.5 py-1.5 text-sm font-medium transition-colors',
                                filter === f
                                    ? 'bg-primary-600 text-white'
                                    : 'border border-surface-200 bg-white text-surface-600 hover:bg-surface-50 dark:border-surface-700 dark:bg-surface-900 dark:text-surface-400 dark:hover:bg-surface-800',
                            )}
                        >
                            {f === 'All' ? 'All' : STATUS_LABELS[f]}
                        </button>
                    ))}
                </div>

                {isLoading ? (
                    <div className="flex justify-center py-20">
                        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
                    </div>
                ) : inquiries.length === 0 ? (
                    <div className="rounded-xl border border-surface-200 bg-white p-16 text-center dark:border-surface-800 dark:bg-surface-900">
                        <MessageSquare className="mx-auto h-10 w-10 text-surface-300" />
                        <p className="mt-3 text-surface-500">No inquiries{filter !== 'All' ? ` with status "${STATUS_LABELS[filter]}"` : ''}</p>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {inquiries.map((inquiry) => (
                            <InquiryCard
                                key={inquiry.id}
                                inquiry={inquiry}
                                onSendQuote={setQuoteInquiryId}
                            />
                        ))}
                    </div>
                )}
            </div>

            {quoteInquiryId && (
                <QuoteBuilderDialog
                    inquiryId={quoteInquiryId}
                    open={!!quoteInquiryId}
                    onClose={() => setQuoteInquiryId(null)}
                />
            )}
        </VendorLayout>
    );
}
