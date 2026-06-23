import axios, { AxiosError } from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000/api/v1";

export const api = axios.create({
    baseURL: API_URL,
    headers: {
        "Content-Type": "application/json",
    },
    withCredentials: true,
});

// Request interceptor — attach access token from localStorage if available
api.interceptors.request.use(
    (config) => {
        if (typeof window !== 'undefined') {
            const accessToken = localStorage.getItem('access_token');
            if (accessToken) {
                console.log('[API Request]', config.method?.toUpperCase(), config.url, '- Token attached');
                config.headers.Authorization = `Bearer ${accessToken}`;
            } else {
                console.log('[API Request]', config.method?.toUpperCase(), config.url, '- No token found');
            }
        }
        return config;
    },
    (error) => Promise.reject(error)
);

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
            console.log('[API 401]', originalRequest.method?.toUpperCase(), originalRequest.url, '- Attempting refresh');
            
            if (isRefreshing) {
                console.log('[API 401] Already refreshing, queuing request');
                return new Promise((resolve, reject) => {
                    failedQueue.push({ resolve, reject });
                })
                    .then(() => api(originalRequest))
                    .catch((err) => Promise.reject(err));
            }

            originalRequest._retry = true;
            isRefreshing = true;

            try {
                // Try refreshing with localStorage refresh token
                const refreshToken = typeof window !== 'undefined' 
                    ? localStorage.getItem('refresh_token') 
                    : null;
                
                console.log('[API Refresh] Using', refreshToken ? 'localStorage token' : 'httpOnly cookie');
                
                if (refreshToken) {
                    const response = await axios.post(
                        `${API_URL}/auth/refresh`,
                        { refresh_token: refreshToken },
                        { withCredentials: true }
                    );
                    
                    const { access_token, refresh_token: newRefreshToken } = response.data;
                    
                    console.log('[API Refresh] Success! Got new tokens');
                    
                    if (typeof window !== 'undefined') {
                        localStorage.setItem('access_token', access_token);
                        if (newRefreshToken) {
                            localStorage.setItem('refresh_token', newRefreshToken);
                        }
                    }
                    
                    processQueue(null);
                    return api(originalRequest);
                } else {
                    // Fallback to httpOnly cookie refresh
                    console.log('[API Refresh] Trying httpOnly cookie refresh');
                    await api.post('/auth/refresh');
                    console.log('[API Refresh] Cookie refresh success');
                    processQueue(null);
                    return api(originalRequest);
                }
            } catch (refreshError) {
                console.log('[API Refresh] Failed:', refreshError);
                processQueue(refreshError as Error);
                // Only clear tokens and redirect if we're not on the callback page
                if (typeof window !== 'undefined' && !window.location.pathname.includes('/auth/callback')) {
                    console.log('[API] Refresh failed, clearing tokens and redirecting to login');
                    console.log('[API] Current pathname:', window.location.pathname);
                    console.log('[API] Refresh error:', refreshError);
                    localStorage.removeItem('access_token');
                    localStorage.removeItem('refresh_token');
                    
                    // Add a small delay to ensure logs are visible
                    setTimeout(() => {
                        console.log('[API] Executing redirect to /login');
                        window.location.href = '/login';
                    }, 100);
                    return Promise.reject(refreshError);
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
export interface EventType {
    id: string;
    name: string;
    description?: string;
    icon?: string;
    display_order: number;
    is_active: boolean;
}

export const getEventTypes = async (): Promise<EventType[]> => {
    const response = await api.get("/events/types");
    return response.data?.data ?? [];
};

export const createEvent = async (data: {
    event_type_id: string;
    name: string;
    description?: string;
    start_date: string;
    city?: string;
    country: string;
    guest_count?: number;
    budget?: number;
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

export const cancelBooking = async (bookingId: string, reason?: string) => {
    const response = await api.patch(`/bookings/${bookingId}/cancel`, { reason: reason ?? null });
    return response.data;
};

// ── Quotes & counter-offers (negotiation loop) ───────────────────────────────

export interface QuoteLineItem {
    description: string;
    quantity: number;
    unit_price: number;
    total: number;
}

export interface UserQuote {
    id: string;
    booking_id: string | null;
    inquiry_id: string | null;
    vendor_id: string;
    line_items: QuoteLineItem[];
    subtotal: number;
    deposit_required: number;
    currency: string;
    valid_until: string | null;
    status: 'draft' | 'sent' | 'accepted' | 'countered' | 'expired' | 'withdrawn';
    notes: string | null;
    round_number: number;
    created_at: string;
    updated_at: string;
}

export const getBookingQuotes = async (bookingId: string): Promise<UserQuote[]> => {
    const res = await api.get(`/bookings/${bookingId}/quotes`);
    return res.data?.data ?? res.data ?? [];
};

export const acceptQuote = async (quoteId: string) => {
    const res = await api.patch(`/quotes/${quoteId}/accept`);
    return res.data;
};

export const submitCounterOffer = async (
    quoteId: string,
    payload: { proposed_total: number; message?: string },
) => {
    const res = await api.post(`/quotes/${quoteId}/counter`, payload);
    return res.data;
};

// Review API
export const getVendorReviews = async (vendorId: string) => {
    const response = await api.get(`/vendors/${vendorId}/reviews`);
    return response.data;
};

export const submitReview = async (vendorId: string, data: { rating: number; comment: string }) => {
    const response = await api.post(`/vendors/${vendorId}/reviews`, data);
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

// Subscription API
export const getSubscriptionStatus = async (): Promise<{
    subscription_status: "free" | "pro";
    is_pro_active: boolean;
    subscription_expires_at: string | null;
}> => {
    const response = await api.get("/subscriptions/me");
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

// Terms & Conditions
export const acceptTerms = async () => {
    const response = await api.post("/users/accept-terms");
    return response.data;
};

// Auth helpers
export const logout = async () => {
    try {
        await api.post("/auth/logout");
    } catch (error) {
        console.error("Logout error:", error);
    } finally {
        // Always clear localStorage tokens
        if (typeof window !== 'undefined') {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
        }
    }
};
