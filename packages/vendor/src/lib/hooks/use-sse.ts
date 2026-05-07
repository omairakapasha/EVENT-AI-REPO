'use client';

import { useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { getAccessToken } from '../api';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000/api/v1';

const BACKOFF_STEPS = [1000, 2000, 4000, 8000, 16000, 30000];

export function useSSE(enabled: boolean = true) {
    const queryClient = useQueryClient();
    const esRef = useRef<EventSource | null>(null);
    const retryCountRef = useRef(0);
    const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const [reconnecting, setReconnecting] = useState(false);

    function connect() {
        const token = getAccessToken();
        if (!token || !enabled) return;

        const url = `${API_URL}/sse/stream?token=${encodeURIComponent(token)}`;
        const es = new EventSource(url);
        esRef.current = es;

        es.addEventListener('booking.created', () => {
            toast('New booking request received', { icon: '📅' });
            queryClient.invalidateQueries({ queryKey: ['bookings'] });
            queryClient.invalidateQueries({ queryKey: ['notifications-unread'] });
            queryClient.invalidateQueries({ queryKey: ['dashboard'] });
        });

        es.addEventListener('booking.confirmed', () => {
            toast.success('Booking confirmed');
            queryClient.invalidateQueries({ queryKey: ['bookings'] });
            queryClient.invalidateQueries({ queryKey: ['notifications-unread'] });
            queryClient.invalidateQueries({ queryKey: ['dashboard'] });
        });

        es.addEventListener('booking.cancelled', () => {
            toast('Booking cancelled', { icon: '⚠️' });
            queryClient.invalidateQueries({ queryKey: ['bookings'] });
            queryClient.invalidateQueries({ queryKey: ['notifications-unread'] });
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
