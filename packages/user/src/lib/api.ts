import axios, { AxiosError } from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000/api/v1";

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
        const originalRequest = error.config as import('axios').InternalAxiosRequestConfig & { _retry?: boolean };

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

// Vendor API - public vendor discovery
export const getVendors = async (params?: { category?: string; search?: string }) => {
    // Backend accepts `q` for text search; category filtering is done client-side
    // since the backend expects category_ids (UUIDs), not category name strings
    const response = await api.get("/public_vendors/", { params: { q: params?.search || undefined } });
    return response.data;
};

export const getVendorById = async (id: string) => {
    const response = await api.get(`/public_vendors/${id}`);
    return response.data;
};

export const getVendorServices = async (vendorId: string) => {
    const response = await api.get(`/public_vendors/${vendorId}`);
    return response.data?.services || [];
};

// Event API
export const createEvent = async (data: {
    eventType: string;
    eventName?: string;
    eventDate: string;
    location?: string;
    attendees?: number;
    budget?: number;
    preferences?: string[];
}) => {
    const response = await api.post("/events", data);
    return response.data;
};

export const getUserEvents = async () => {
    const response = await api.get("/events");
    return response.data;
};

export const getEventById = async (id: string) => {
    const response = await api.get(`/events/${id}`);
    return response.data;
};

// AI Agent API
export const planEventWithAI = async (message: string) => {
    const response = await api.post("/ai/chat", { message });
    return response.data;
};

export const discoverVendorsWithAI = async (query: string, location: string) => {
    const response = await api.post("/ai/chat", {
        message: `Find vendors for: ${query} in ${location}`,
        context: "discovery"
    });
    return response.data;
};

// Booking API
export const createBooking = async (data: {
    vendorId: string;
    serviceId: string;
    eventDate: string;
    guestCount?: number;
    notes?: string;
}) => {
    const response = await api.post("/bookings", data);
    return response.data;
};

export const getUserBookings = async () => {
    const response = await api.get("/bookings");
    return response.data;
};

export const cancelBooking = async (bookingId: string) => {
    const response = await api.patch(`/bookings/${bookingId}/cancel`);
    return response.data;
};

// Review API — note: backend uses /marketplace prefix
export const getVendorReviews = async (vendorId: string) => {
    const response = await api.get(`/marketplace/${vendorId}/reviews`);
    return response.data;
};

export const submitReview = async (vendorId: string, data: { rating: number; comment: string }) => {
    const response = await api.post(`/marketplace/${vendorId}/reviews`, data);
    return response.data;
};

// User Profile API
export const getUserProfile = async () => {
    const response = await api.get("/users/me");
    return response.data;
};

export const updateUserProfile = async (data: {
    firstName?: string;
    lastName?: string;
    phone?: string;
}) => {
    const response = await api.patch("/users/me", data);
    return response.data;
};

export const changePassword = async (data: {
    currentPassword: string;
    newPassword: string;
}) => {
    const response = await api.patch("/users/me/password", data);
    return response.data;
};

export const verifyEmail = async (token: string) => {
    const response = await api.post("/users/verify-email", { token });
    return response.data;
};

export const resendVerificationEmail = async () => {
    const response = await api.post("/users/resend-verification");
    return response.data;
};

// Notifications API
export const getUserNotifications = async () => {
    const response = await api.get("/notifications/");
    return response.data;
};

export const markNotificationAsRead = async (id: string) => {
    const response = await api.patch(`/notifications/${id}/read`);
    return response.data;
};

export const markAllNotificationsAsRead = async () => {
    const response = await api.patch("/notifications/read-all");
    return response.data;
};
