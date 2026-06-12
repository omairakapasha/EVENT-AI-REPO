import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import api, { getApiError } from '../api';

export interface QuoteLineItem {
    description: string;
    quantity: number;
    unit_price: number;
    total: number;
}

export interface Quote {
    id: string;
    booking_id: string | null;
    inquiry_id: string | null;
    vendor_id: string;
    line_items: QuoteLineItem[];
    subtotal: number;
    deposit_required: number;
    currency: string;
    valid_until: string | null;
    status: 'draft' | 'sent' | 'accepted' | 'countered' | 'expired' | 'withdrawn';
    notes: string | null;
    round_number: number;
    created_by: string;
    created_at: string;
    updated_at: string;
}

export interface CounterOffer {
    id: string;
    quote_id: string;
    proposed_by_user_id: string;
    proposed_total: number;
    proposed_changes: Record<string, unknown>;
    message: string | null;
    status: 'pending' | 'accepted' | 'rejected' | 'superseded';
    created_at: string;
    updated_at: string;
}

export interface CreateQuotePayload {
    line_items: QuoteLineItem[];
    subtotal: number;
    deposit_required: number;
    currency?: string;
    valid_until?: string | null;
    notes?: string | null;
}

async function fetchBookingQuotes(bookingId: string): Promise<Quote[]> {
    const res = await api.get(`/bookings/${bookingId}/quotes`);
    return res.data.data ?? res.data;
}

async function fetchCounterOffers(quoteId: string): Promise<CounterOffer[]> {
    const res = await api.get(`/quotes/${quoteId}/counter-offers`);
    return res.data.data ?? res.data;
}

export function useBookingQuotes(bookingId: string) {
    return useQuery({
        queryKey: ['booking-quotes', bookingId],
        queryFn: () => fetchBookingQuotes(bookingId),
        staleTime: 15_000,
        enabled: !!bookingId,
    });
}

export function useCounterOffers(quoteId: string | null) {
    return useQuery({
        queryKey: ['counter-offers', quoteId],
        queryFn: () => fetchCounterOffers(quoteId as string),
        staleTime: 15_000,
        enabled: !!quoteId,
    });
}

export function useCreateQuote(bookingId: string) {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (payload: CreateQuotePayload) =>
            api.post(`/bookings/${bookingId}/quotes`, payload),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['booking-quotes', bookingId] });
            queryClient.invalidateQueries({ queryKey: ['booking', bookingId] });
            toast.success('Quote sent to customer');
        },
        onError: (err) => {
            toast.error(getApiError(err));
        },
    });
}

export function useWithdrawQuote(bookingId: string) {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (quoteId: string) =>
            api.patch(`/quotes/${quoteId}/withdraw`),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['booking-quotes', bookingId] });
            toast.success('Quote withdrawn');
        },
        onError: (err) => {
            toast.error(getApiError(err));
        },
    });
}

export function useRespondToCounter(bookingId: string) {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ counterId, action, message }: { counterId: string; action: 'accept' | 'reject'; message?: string }) =>
            api.patch(`/counter-offers/${counterId}/respond`, { action, message }),
        onSuccess: (_data, vars) => {
            queryClient.invalidateQueries({ queryKey: ['booking-quotes', bookingId] });
            queryClient.invalidateQueries({ queryKey: ['booking', bookingId] });
            queryClient.invalidateQueries({ queryKey: ['counter-offers'] });
            toast.success(vars.action === 'accept' ? 'Counter-offer accepted' : 'Counter-offer rejected');
        },
        onError: (err) => {
            toast.error(getApiError(err));
        },
    });
}
