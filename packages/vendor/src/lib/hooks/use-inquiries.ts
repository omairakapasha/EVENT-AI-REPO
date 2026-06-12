import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import api, { getApiError, type Inquiry } from '../api';
import type { CreateQuotePayload } from './use-quotes';

export { type Inquiry };

async function fetchInquiries(status?: string): Promise<Inquiry[]> {
    const res = await api.get('/inquiries/vendor/my-inquiries', {
        params: status ? { status } : undefined,
    });
    return res.data?.data ?? res.data ?? [];
}

export function useInquiries(status?: string) {
    return useQuery({
        queryKey: ['inquiries', status],
        queryFn: () => fetchInquiries(status),
        staleTime: 30_000,
    });
}

export function useSendQuoteFromInquiry(inquiryId: string) {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (payload: CreateQuotePayload) =>
            api.post(`/inquiries/${inquiryId}/quotes`, payload),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['inquiries'] });
            toast.success('Quote sent to customer');
        },
        onError: (err) => {
            toast.error(getApiError(err));
        },
    });
}
