import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import api, { getApiError } from '../api';
import { _mapVendor, type Vendor } from '../auth-store';

async function fetchVendorProfile(): Promise<Vendor> {
    const res = await api.get('/vendors/profile/me');
    const data = res.data.data ?? res.data;
    return _mapVendor(data);
}

export function useVendorProfile() {
    return useQuery({
        queryKey: ['vendor-profile'],
        queryFn: fetchVendorProfile,
        staleTime: 30_000,
    });
}

export function useUpdateProfile() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (data: Partial<Vendor>) => api.put('/vendors/profile/me', data),
        onSuccess: (res) => {
            const updated = _mapVendor(res.data.data ?? res.data);
            queryClient.setQueryData(['vendor-profile'], updated);
            toast.success('Profile updated');
        },
        onError: (err) => {
            toast.error(getApiError(err));
        },
    });
}
