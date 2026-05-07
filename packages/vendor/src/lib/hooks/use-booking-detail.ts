import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import api, { getApiError } from '../api';
import type { Booking } from './use-vendor-bookings';

export interface BookingMessage {
    id: string;
    booking_id: string;
    sender_id: string | null;
    sender_type: 'vendor' | 'client' | 'system';
    message: string;
    is_read: boolean;
    created_at: string;
}

async function fetchBookingDetail(id: string): Promise<Booking> {
    const res = await api.get(`/bookings/${id}`);
    return res.data.data ?? res.data;
}

async function fetchBookingMessages(id: string): Promise<BookingMessage[]> {
    const res = await api.get(`/bookings/${id}/messages`);
    return res.data.data ?? res.data;
}

export function useBookingDetail(id: string) {
    return useQuery({
        queryKey: ['booking', id],
        queryFn: () => fetchBookingDetail(id),
        staleTime: 30_000,
        enabled: !!id,
    });
}

export function useBookingMessages(id: string) {
    return useQuery({
        queryKey: ['booking-messages', id],
        queryFn: () => fetchBookingMessages(id),
        staleTime: 30_000,
        enabled: !!id,
    });
}

export function useSendMessage(bookingId: string) {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (message: string) =>
            api.post(`/bookings/${bookingId}/messages`, {
                booking_id: bookingId,
                sender_type: 'vendor',
                message,
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['booking-messages', bookingId] });
        },
        onError: (err) => {
            toast.error(getApiError(err));
        },
    });
}
