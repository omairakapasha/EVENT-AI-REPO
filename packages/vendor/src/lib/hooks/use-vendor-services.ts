import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import api, { getApiError } from '../api';

export interface Service {
    id: string;
    vendor_id: string;
    name: string;
    description: string | null;
    capacity: number | null;
    price_min: number | null;
    price_max: number | null;
    requirements: string | null;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface ServiceFilters {
    search?: string;
    category?: string;
    page?: number;
    limit?: number;
}

export interface ServiceCreate {
    name: string;
    description?: string;
    capacity?: number;
    price_min?: number;
    price_max?: number;
    requirements?: string;
    is_active?: boolean;
}

export type ServiceUpdate = Partial<ServiceCreate>;

async function fetchVendorServices(filters: ServiceFilters): Promise<{ data: Service[]; meta: { total: number; pages: number } }> {
    const params: Record<string, unknown> = {};
    if (filters.search) params.search = filters.search;
    if (filters.category) params.category = filters.category;
    if (filters.page) params.page = filters.page;
    if (filters.limit) params.limit = filters.limit;
    const res = await api.get('/vendors/me/services', { params });
    return res.data;
}

export function useVendorServices(filters: ServiceFilters = {}) {
    return useQuery({
        queryKey: ['services', filters],
        queryFn: () => fetchVendorServices(filters),
        staleTime: 30_000,
    });
}

export function useCreateService() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (data: ServiceCreate) => api.post('/services/', data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['services'] });
            queryClient.invalidateQueries({ queryKey: ['dashboard'] });
            toast.success('Service created successfully');
        },
        onError: (err) => {
            toast.error(getApiError(err));
        },
    });
}

export function useUpdateService() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ id, data }: { id: string; data: ServiceUpdate }) =>
            api.put(`/services/${id}`, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['services'] });
            toast.success('Service updated successfully');
        },
        onError: (err) => {
            toast.error(getApiError(err));
        },
    });
}

export function useDeleteService() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (id: string) => api.delete(`/services/${id}`),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['services'] });
            queryClient.invalidateQueries({ queryKey: ['dashboard'] });
            toast.success('Service deleted');
        },
        onError: (err) => {
            toast.error(getApiError(err));
        },
    });
}
