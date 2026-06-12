import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000/api/v1';

// Create axios instance — httpOnly cookies are sent automatically via withCredentials
export const api: AxiosInstance = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
    withCredentials: true,
});

// Response interceptor — handle 401 via httpOnly cookie refresh
let isRefreshing = false;
let failedQueue: Array<{
    resolve: (value: unknown) => void;
    reject: (reason?: unknown) => void;
}> = [];

const processQueue = (error: Error | null) => {
    failedQueue.forEach((prom) => {
        if (error) {
            prom.reject(error);
        } else {
            prom.resolve(null);
        }
    });
    failedQueue = [];
};

api.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
        const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

        // Ignore auth routes — let them handle their own errors
        if (originalRequest.url?.includes('/login') || originalRequest.url?.includes('/register')) {
            return Promise.reject(error);
        }

        if (error.response?.status === 401 && !originalRequest._retry) {
            if (isRefreshing) {
                return new Promise((resolve, reject) => {
                    failedQueue.push({ resolve, reject });
                })
                    .then(() => api(originalRequest))
                    .catch((err) => Promise.reject(err));
            }

            originalRequest._retry = true;
            isRefreshing = true;

            try {
                // Refresh token is in httpOnly cookie — sent automatically via withCredentials
                await api.post('/auth/refresh');
                processQueue(null);
                return api(originalRequest);
            } catch (refreshError) {
                processQueue(refreshError as Error);
                if (typeof window !== 'undefined') {
                    window.location.href = '/login';
                }
                return Promise.reject(refreshError);
            } finally {
                isRefreshing = false;
            }
        }

        return Promise.reject(error);
    }
);

// API error handler
export interface ApiError {
    error: string;
    message: string;
    details?: Array<{ field: string; message: string }>;
}

// ── Inquiries ─────────────────────────────────────────────────────────────────

export interface Inquiry {
    id: string;
    vendor_id: string;
    customer_name: string;
    customer_email: string;
    customer_phone: string | null;
    message: string;
    preferred_date: string | null;
    event_type: string | null;
    expected_guests: number | null;
    budget_range: string | null;
    status: 'NEW' | 'CONTACTED' | 'QUOTED' | 'CONVERTED' | 'DECLINED';
    vendor_response: string | null;
    vendor_responded_at: string | null;
    quote_id: string | null;
    quoted_amount: number | null;
    created_at: string;
    updated_at: string;
}

export const getInquiries = async (params?: { status?: string; limit?: number; offset?: number }): Promise<Inquiry[]> => {
    const res = await api.get('/inquiries/vendor/my-inquiries', { params });
    return res.data?.data ?? res.data ?? [];
};

export const getApiError = (error: unknown): string => {
    if (axios.isAxiosError(error)) {
        const data = error.response?.data;
        if (data?.error?.message) return data.error.message;
        if (data?.message) return data.message;
        if (data?.detail) {
            if (typeof data.detail === 'object') return data.detail.message ?? JSON.stringify(data.detail);
            return data.detail;
        }
    }
    if (error instanceof Error) return error.message;
    return 'An unexpected error occurred';
};

// Terms & Conditions
export const acceptTerms = async () => {
    const response = await api.post('/users/accept-terms');
    return response.data;
};

export default api;
