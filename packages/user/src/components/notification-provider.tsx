"use client";

import { createContext, useContext, useEffect, ReactNode } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getUserNotifications, markNotificationAsRead, markAllNotificationsAsRead } from "../lib/api";

interface Notification {
    id: string;
    title: string;
    message: string;
    type: string;
    is_read: boolean;
    created_at: string;
}

interface NotificationsQueryData {
    data?: Notification[];
    [key: string]: unknown;
}

interface NotificationContextType {
    notifications: Notification[];
    unreadCount: number;
    markAsRead: (id: string) => void;
    markAllAsRead: () => void;
    removeNotification: (id: string) => void;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export function NotificationProvider({ children }: { children: ReactNode }) {
    const queryClient = useQueryClient();

    // Fetch notifications using React Query — only if logged in
    const { data } = useQuery({
        queryKey: ["notifications"],
        queryFn: () => getUserNotifications(),
        refetchInterval: 60000, // Refetch every minute
        staleTime: 30000,
        enabled: typeof window !== 'undefined' && !!localStorage.getItem('access_token'), // Only fetch if token exists
    });

    const notifications: Notification[] = data?.data || [];
    const unreadCount = notifications.filter((n) => !n.is_read).length;

    const markAsReadMutation = useMutation({
        mutationFn: markNotificationAsRead,
        onMutate: async (id) => {
            await queryClient.cancelQueries({ queryKey: ["notifications"] });
            const previous = queryClient.getQueryData(["notifications"]);
            queryClient.setQueryData(["notifications"], (old: NotificationsQueryData | undefined) => ({
                ...old,
                data: (old?.data || []).map((n) =>
                    n.id === id ? { ...n, is_read: true } : n
                ),
            }));
            return { previous };
        },
        onError: (_err, _id, context) => {
            queryClient.setQueryData(["notifications"], context?.previous);
        },
        onSettled: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
    });

    const markAllAsReadMutation = useMutation({
        mutationFn: markAllNotificationsAsRead,
        onMutate: async () => {
            await queryClient.cancelQueries({ queryKey: ["notifications"] });
            const previous = queryClient.getQueryData(["notifications"]);
            queryClient.setQueryData(["notifications"], (old: NotificationsQueryData | undefined) => ({
                ...old,
                data: (old?.data || []).map((n) => ({ ...n, is_read: true })),
            }));
            return { previous };
        },
        onError: (_err, _v, context) => {
            queryClient.setQueryData(["notifications"], context?.previous);
        },
        onSettled: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
    });

    const removeNotification = (id: string) => {
        queryClient.setQueryData(["notifications"], (old: NotificationsQueryData | undefined) => ({
            ...old,
            data: (old?.data || []).filter((n) => n.id !== id),
        }));
    };

    // Real-time SSE synchronization — attach token from localStorage
    useEffect(() => {
        let eventSource: EventSource | null = null;
        let reconnectTimeout: NodeJS.Timeout | null = null;

        const connectSSE = () => {
            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000/api/v1";
            const token = localStorage.getItem('access_token');
            
            if (!token) {
                // No token = not logged in, don't try to connect
                return;
            }
            
            // EventSource doesn't support custom headers, so pass token as query param
            eventSource = new EventSource(`${API_URL}/sse/stream?token=${token}`);

            eventSource.addEventListener('notification', () => {
                queryClient.invalidateQueries({ queryKey: ["notifications"] });
            });

            eventSource.onerror = () => {
                eventSource?.close();
                // Only retry if token still exists (user still logged in)
                if (localStorage.getItem('access_token')) {
                    reconnectTimeout = setTimeout(connectSSE, 5000);
                }
            };
        };

        connectSSE();

        return () => {
            if (eventSource) {
                eventSource.close();
            }
            if (reconnectTimeout) {
                clearTimeout(reconnectTimeout);
            }
        };
    }, [queryClient]);

    return (
        <NotificationContext.Provider
            value={{
                notifications,
                unreadCount,
                markAsRead: (id) => markAsReadMutation.mutate(id),
                markAllAsRead: () => markAllAsReadMutation.mutate(),
                removeNotification,
            }}
        >
            {children}
        </NotificationContext.Provider>
    );
}

export function useNotifications() {
    const context = useContext(NotificationContext);
    if (context === undefined) {
        throw new Error("useNotifications must be used within a NotificationProvider");
    }
    return context;
}
