import { useQuery } from '@tanstack/react-query';
import api from '../api';

export interface RecentBookingItem {
    id: string;
    service_name: string | null;
    event_date: string;
    status: string;
    total_price: number;
    currency: string;
    client_name: string | null;
}

export interface DashboardStats {
    total_bookings: number;
    pending_bookings: number;
    confirmed_bookings: number;
    active_services: number;
    total_services: number;
    recent_bookings: RecentBookingItem[];
}

async function fetchDashboard(): Promise<DashboardStats> {
    const res = await api.get('/vendors/me/dashboard');
    return res.data.data;
}

export function useDashboard() {
    return useQuery({
        queryKey: ['dashboard'],
        queryFn: fetchDashboard,
        staleTime: 30_000,
    });
}
