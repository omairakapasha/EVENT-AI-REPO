import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000/api/v1";

// httpOnly cookies are sent automatically via withCredentials — no manual token handling
export const api = axios.create({
    baseURL: API_URL,
    headers: {
        "Content-Type": "application/json",
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

        if (originalRequest.url?.includes('/login')) {
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

export const getVendors = async (params?: { page?: number; limit?: number; status?: string; q?: string }) => {
    const response = await api.get("/admin/vendors", { params });
    return response.data?.data || response.data;
};

export const updateVendorStatus = async (id: string, status: string, reason?: string) => {
    const response = await api.patch(`/admin/vendors/${id}/status`, { status, reason });
    return response.data;
};

export const getUsers = async (params?: { page?: number; limit?: number; role?: string; q?: string }) => {
    const response = await api.get("/admin/users", { params });
    return response.data?.data || response.data;
};

export const getStats = async () => {
    const response = await api.get("/admin/stats");
    return response.data?.data || response.data;
};

export const getCategories = async () => {
    const response = await api.get("/admin/categories");
    return response.data?.data || response.data;
};

export const createCategory = async (data: { name: string; slug: string; description?: string }) => {
    const response = await api.post("/admin/categories", data);
    return response.data;
};

export const deleteCategory = async (id: string) => {
    await api.delete(`/admin/categories/${id}`);
};

export const getBookings = async (params?: { page?: number; status?: string }) => {
    const response = await api.get("/bookings", { params: { page: 1, limit: 20, ...params } });
    return response.data?.data || response.data;
};

export const updateBookingStatus = async (id: string, status: "confirmed" | "rejected", reason?: string) => {
    const response = await api.patch(`/bookings/${id}/status`, { status, reason });
    return response.data;
};

export default api;
