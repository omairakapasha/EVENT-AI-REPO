'use client';

import { useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000/api/v1';

const BACKOFF_STEPS = [1000, 2000, 4000, 8000, 16000, 30000];

export function useSSE(enabled: boolean = true) {
    const queryClient = useQueryClient();
    const esRef = useRef<EventSource | null>(null);
    const retryCountRef = useRef(0);
    const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const [reconnecting, setReconnecting] = useState(false);

    function connect() {
        if (!enabled) return;

        // Token is in httpOnly cookie, sent automatically via withCredentials
        const url = `${API_URL}/sse/stream`;
        const es = new EventSource(url);
        esRef.current = es;

        // Backend pushes a single "notification" SSE event for all domain events
        // (booking.created, booking.confirmed, booking.cancelled, etc.).
        // Payload shape: NotificationRead — { id, user_id, title, body, type, data, ... }
        es.addEventListener('notification', (event) => {
            let payload: { title?: string; body?: string; type?: string } = {};
            try {
                payload = JSON.parse((event as MessageEvent).data);
            } catch {
                // ignore malformed payload — still invalidate queries below
            }

            const type = payload.type ?? '';
            const title = payload.title || 'New notification';
            if (type === 'booking_confirmed') {
                toast.success(title);
            } else if (type === 'booking_cancelled' || type === 'booking_rejected') {
                toast(title, { icon: '⚠️' });
            } else if (type === 'booking_created') {
                toast(title, { icon: '📅' });
            } else {
                toast(title, { icon: '🔔' });
            }

            queryClient.invalidateQueries({ queryKey: ['bookings'] });
            queryClient.invalidateQueries({ queryKey: ['booking'] });
            queryClient.invalidateQueries({ queryKey: ['notifications'] });
            queryClient.invalidateQueries({ queryKey: ['notifications-unread'] });
            queryClient.invalidateQueries({ queryKey: ['dashboard'] });
            queryClient.invalidateQueries({ queryKey: ['availability'] });
        });

        // ping is a no-op — just keeps the connection alive
        es.addEventListener('ping', () => {});

        es.onerror = () => {
            es.close();
            esRef.current = null;
            scheduleReconnect();
        };

        es.onopen = () => {
            retryCountRef.current = 0;
            setReconnecting(false);
        };
    }

    function scheduleReconnect() {
        const delay = BACKOFF_STEPS[Math.min(retryCountRef.current, BACKOFF_STEPS.length - 1)];
        retryCountRef.current += 1;
        setReconnecting(true);
        retryTimerRef.current = setTimeout(() => {
            connect();
        }, delay);
    }

    function cleanup() {
        if (retryTimerRef.current) {
            clearTimeout(retryTimerRef.current);
            retryTimerRef.current = null;
        }
        if (esRef.current) {
            esRef.current.close();
            esRef.current = null;
        }
        setReconnecting(false);
    }

    useEffect(() => {
        if (!enabled) return;
        connect();
        return cleanup;
        // Re-create EventSource when enabled changes (e.g. after login)
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [enabled]);

    return { reconnecting };
}
