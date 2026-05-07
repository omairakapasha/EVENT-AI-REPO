import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import api, { getApiError } from '../api';

export interface AvailabilityRecord {
    id: string;
    vendor_id: string;
    service_id: string | null;
    date: string;
    status: 'available' | 'blocked' | 'tentative' | 'booked' | 'locked';
    notes: string | null;
    booking_id: string | null;
    created_at: string;
    updated_at: string;
}

export interface AvailabilityUpsert {
    date: string;
    status: 'available' | 'blocked' | 'tentative';
    service_id?: string;
    notes?: string;
}

export interface BulkAvailabilityUpsert {
    entries: AvailabilityUpsert[];
}

async function fetchAvailability(
    startDate: string,
    endDate: string,
    serviceId?: string
): Promise<AvailabilityRecord[]> {
    const params: Record<string, string> = { start_date: startDate, end_date: endDate };
    if (serviceId) params.service_id = serviceId;
    const res = await api.get('/vendors/me/availability', { params });
    return res.data.data ?? [];
}

export function useVendorAvailability(
    startDate: string,
    endDate: string,
    serviceId?: string
) {
    return useQuery({
        queryKey: ['availability', startDate, endDate, serviceId],
        queryFn: () => fetchAvailability(startDate, endDate, serviceId),
        staleTime: 30_000,
        enabled: !!startDate && !!endDate,
    });
}

export function useUpsertAvailability() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (data: AvailabilityUpsert) =>
            api.post('/vendors/me/availability', data),
        onMutate: async (newEntry) => {
            await queryClient.cancelQueries({ queryKey: ['availability'] });
            const previousData = queryClient.getQueriesData({ queryKey: ['availability'] });
            // Optimistic update: update matching date in all availability caches
            queryClient.setQueriesData({ queryKey: ['availability'] }, (old: unknown) => {
                if (!Array.isArray(old)) return old;
                const exists = (old as AvailabilityRecord[]).some((r) => r.date === newEntry.date);
                if (exists) {
                    return (old as AvailabilityRecord[]).map((r) =>
                        r.date === newEntry.date ? { ...r, status: newEntry.status } : r
                    );
                }
                return [
                    ...old,
                    {
                        id: `optimistic-${newEntry.date}`,
                        vendor_id: '',
                        service_id: newEntry.service_id ?? null,
                        date: newEntry.date,
                        status: newEntry.status,
                        notes: newEntry.notes ?? null,
                        booking_id: null,
                        created_at: new Date().toISOString(),
                        updated_at: new Date().toISOString(),
                    } satisfies AvailabilityRecord,
                ];
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
            queryClient.invalidateQueries({ queryKey: ['availability'] });
        },
    });
}

export function useBulkUpsertAvailability() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (data: BulkAvailabilityUpsert) =>
            api.post('/vendors/me/availability/bulk', data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['availability'] });
            toast.success('Availability updated');
        },
        onError: (err) => {
            toast.error(getApiError(err));
        },
    });
}
