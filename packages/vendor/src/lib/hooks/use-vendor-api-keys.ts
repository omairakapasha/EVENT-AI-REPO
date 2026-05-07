import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import api, { getApiError } from '../api';

export interface ApiKey {
    id: string;
    name: string;
    key_prefix: string;
    is_active: boolean;
    last_used_at: string | null;
    expires_at: string | null;
    created_at: string;
}

export interface ApiKeyCreated extends ApiKey {
    /** Returned only once at creation — store it securely. */
    raw_key: string;
}

export interface ApiKeyCreate {
    name: string;
}

async function fetchApiKeys(): Promise<ApiKey[]> {
    const res = await api.get('/vendors/me/api-keys');
    // Backend returns array directly (response_model=list[VendorApiKeyRead])
    return res.data.data ?? res.data ?? [];
}

export function useApiKeys() {
    return useQuery({
        queryKey: ['api-keys'],
        queryFn: fetchApiKeys,
        staleTime: 60_000,
    });
}

export function useCreateApiKey() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async (data: ApiKeyCreate): Promise<ApiKeyCreated> => {
            const res = await api.post('/vendors/me/api-keys', data);
            return res.data.data ?? res.data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['api-keys'] });
        },
        onError: (err) => {
            toast.error(getApiError(err));
        },
    });
}

export function useRevokeApiKey() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (keyId: string) =>
            api.delete(`/vendors/me/api-keys/${keyId}`),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['api-keys'] });
            toast.success('API key revoked');
        },
        onError: (err) => {
            toast.error(getApiError(err));
        },
    });
}
