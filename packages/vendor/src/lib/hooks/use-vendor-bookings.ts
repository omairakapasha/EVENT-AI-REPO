import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import api, { getApiError } from '../api';

export interface Booking {
    id: string;
    vendor_id: string;
    service_id: string;
    user_id: string | null;
    event_date: string;
    event_name: string | null;
    client_name: string | null;
    client_email: string | null;
    status: 'pending' | 'confirmed' | 'in_progress' | 'completed' | 'cancelled' | 'rejected' | 'no_show';
    total_price: number;
    currency: string;
    event_location: Record<string, unknown> | null;
    special_requirements: string | null;
    created_at: string;
    updated_at: string;
}

export interface BookingFilters {
    status?: string;
    page?: number;
    limit?: number;
}

async function fetchVendorBookings(filters: BookingFilters): Promise<{ data: Booking[]; meta: { total: number; page: number; limit: number; pages: number } }> {
    const params: Record<string, unknown> = {};
    if (filters.status && filters.status !== 'all') params.status = filters.status;
    if (filters.page) params.page = filters.page;
    if (filters.limit) params.limit = filters.limit;
    const res = await api.get('/vendors/me/bookings', { params });
    return res.data;
}

export function useVendorBookings(filters: BookingFilters = {}) {
    return useQuery({
        queryKey: ['bookings', filters],
        queryFn: () => fetchVendorBookings(filters),
        staleTime: 30_000,
        refetchOnWindowFocus: true,
    });
}

export function useConfirmBooking() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (bookingId: string) =>
            api.patch(`/vendors/me/bookings/${bookingId}/status`, { status: 'confirmed' }),
        onMutate: async (bookingId) => {
            await queryClient.cancelQueries({ queryKey: ['bookings'] });
            const previousData = queryClient.getQueriesData({ queryKey: ['bookings'] });
            queryClient.setQueriesData({ queryKey: ['bookings'] }, (old: unknown) => {
                if (!old || typeof old !== 'object') return old;
                const data = old as { data: Booking[] };
                return {
                    ...data,
                    data: data.data?.map((b) =>
                        b.id === bookingId ? { ...b, status: 'confirmed' as const } : b
                    ),
                };
            });
            return { previousData };
        },
        onError: (_err, _bookingId, context) => {
            if (context?.previousData) {
                context.previousData.forEach(([queryKey, data]) => {
                    queryClient.setQueryData(queryKey, data);
                });
            }
            toast.error(getApiError(_err));
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['bookings'] });
            queryClient.invalidateQueries({ queryKey: ['dashboard'] });
        },
    });
}

export function useRejectBooking() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ bookingId, reason }: { bookingId: string; reason?: string }) =>
            api.patch(`/vendors/me/bookings/${bookingId}/status`, { status: 'rejected', reason }),
        onMutate: async ({ bookingId }) => {
            await queryClient.cancelQueries({ queryKey: ['bookings'] });
            const previousData = queryClient.getQueriesData({ queryKey: ['bookings'] });
            queryClient.setQueriesData({ queryKey: ['bookings'] }, (old: unknown) => {
                if (!old || typeof old !== 'object') return old;
                const data = old as { data: Booking[] };
                return {
                    ...data,
                    data: data.data?.map((b) =>
                        b.id === bookingId ? { ...b, status: 'rejected' as const } : b
                    ),
                };
            });
            return { previousData };
        },
        onError: (_err, _vars, context) => {
            if (context?.previousData) {
                context.previousData.forEach(([queryKey, data]) => {
                    queryClient.setQueryData(queryKey, data);
                });
            }
            toast.error(getApiError(_err));
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['bookings'] });
            queryClient.invalidateQueries({ queryKey: ['dashboard'] });
        },
    });
}
