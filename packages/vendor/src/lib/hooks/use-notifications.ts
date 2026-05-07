import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import api, { getApiError } from '../api';

export interface Notification {
    id: string;
    user_id: string;
    title: string;
    message: string;
    type: string;
    is_read: boolean;
    data: Record<string, unknown> | null;
    created_at: string;
}

async function fetchNotifications(): Promise<Notification[]> {
    const res = await api.get('/notifications/');
    return res.data.data ?? res.data ?? [];
}

async function fetchUnreadCount(): Promise<number> {
    const res = await api.get('/notifications/unread-count');
    return res.data.data?.count ?? res.data?.count ?? 0;
}

export function useNotifications() {
    return useQuery({
        queryKey: ['notifications'],
        queryFn: fetchNotifications,
        staleTime: 30_000,
        refetchOnWindowFocus: true,
    });
}

export function useUnreadCount() {
    return useQuery({
        queryKey: ['notifications-unread'],
        queryFn: fetchUnreadCount,
        staleTime: 30_000,
        refetchOnWindowFocus: true,
    });
}

export function useMarkNotificationRead() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (id: string) => api.patch(`/notifications/${id}/read`),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['notifications'] });
            queryClient.invalidateQueries({ queryKey: ['notifications-unread'] });
        },
        onError: (err) => {
            toast.error(getApiError(err));
        },
    });
}

export function useMarkAllRead() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: () => api.patch('/notifications/read-all'),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['notifications'] });
            queryClient.invalidateQueries({ queryKey: ['notifications-unread'] });
        },
        onError: (err) => {
            toast.error(getApiError(err));
        },
    });
}
