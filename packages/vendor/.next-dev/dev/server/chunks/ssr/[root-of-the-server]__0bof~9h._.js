module.exports = [
"[externals]/util [external] (util, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("util", () => require("util"));

module.exports = mod;
}),
"[externals]/stream [external] (stream, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("stream", () => require("stream"));

module.exports = mod;
}),
"[externals]/path [external] (path, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("path", () => require("path"));

module.exports = mod;
}),
"[externals]/http [external] (http, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("http", () => require("http"));

module.exports = mod;
}),
"[externals]/https [external] (https, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("https", () => require("https"));

module.exports = mod;
}),
"[externals]/url [external] (url, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("url", () => require("url"));

module.exports = mod;
}),
"[externals]/fs [external] (fs, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("fs", () => require("fs"));

module.exports = mod;
}),
"[externals]/crypto [external] (crypto, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("crypto", () => require("crypto"));

module.exports = mod;
}),
"[externals]/http2 [external] (http2, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("http2", () => require("http2"));

module.exports = mod;
}),
"[externals]/assert [external] (assert, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("assert", () => require("assert"));

module.exports = mod;
}),
"[externals]/tty [external] (tty, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("tty", () => require("tty"));

module.exports = mod;
}),
"[externals]/os [external] (os, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("os", () => require("os"));

module.exports = mod;
}),
"[externals]/zlib [external] (zlib, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("zlib", () => require("zlib"));

module.exports = mod;
}),
"[externals]/events [external] (events, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("events", () => require("events"));

module.exports = mod;
}),
"[project]/OneDrive/Desktop/Event/packages/vendor/src/lib/api.ts [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "api",
    ()=>api,
    "default",
    ()=>__TURBOPACK__default__export__,
    "getApiError",
    ()=>getApiError
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$node_modules$2f2e$pnpm$2f$axios$40$1$2e$13$2e$4$2f$node_modules$2f$axios$2f$lib$2f$axios$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/OneDrive/Desktop/Event/node_modules/.pnpm/axios@1.13.4/node_modules/axios/lib/axios.js [app-ssr] (ecmascript)");
;
const API_URL = ("TURBOPACK compile-time value", "http://localhost:5000/api/v1") || 'http://localhost:5000/api/v1';
const api = __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$node_modules$2f2e$pnpm$2f$axios$40$1$2e$13$2e$4$2f$node_modules$2f$axios$2f$lib$2f$axios$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"].create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json'
    },
    withCredentials: true
});
// Response interceptor — handle 401 via httpOnly cookie refresh
let isRefreshing = false;
let failedQueue = [];
const processQueue = (error)=>{
    failedQueue.forEach((prom)=>{
        if (error) {
            prom.reject(error);
        } else {
            prom.resolve(null);
        }
    });
    failedQueue = [];
};
api.interceptors.response.use((response)=>response, async (error)=>{
    const originalRequest = error.config;
    // Ignore auth routes — let them handle their own errors
    if (originalRequest.url?.includes('/login') || originalRequest.url?.includes('/register')) {
        return Promise.reject(error);
    }
    if (error.response?.status === 401 && !originalRequest._retry) {
        if (isRefreshing) {
            return new Promise((resolve, reject)=>{
                failedQueue.push({
                    resolve,
                    reject
                });
            }).then(()=>api(originalRequest)).catch((err)=>Promise.reject(err));
        }
        originalRequest._retry = true;
        isRefreshing = true;
        try {
            // Refresh token is in httpOnly cookie — sent automatically via withCredentials
            await api.post('/auth/refresh');
            processQueue(null);
            return api(originalRequest);
        } catch (refreshError) {
            processQueue(refreshError);
            if ("TURBOPACK compile-time falsy", 0) //TURBOPACK unreachable
            ;
            return Promise.reject(refreshError);
        } finally{
            isRefreshing = false;
        }
    }
    return Promise.reject(error);
});
const getApiError = (error)=>{
    if (__TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$node_modules$2f2e$pnpm$2f$axios$40$1$2e$13$2e$4$2f$node_modules$2f$axios$2f$lib$2f$axios$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"].isAxiosError(error)) {
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
const __TURBOPACK__default__export__ = api;
}),
"[project]/OneDrive/Desktop/Event/packages/vendor/src/lib/auth-store.ts [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "_mapUser",
    ()=>_mapUser,
    "_mapVendor",
    ()=>_mapVendor,
    "default",
    ()=>__TURBOPACK__default__export__,
    "useAuthStore",
    ()=>useAuthStore
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$node_modules$2f2e$pnpm$2f$zustand$40$4$2e$5$2e$7_$40$types$2b$react$40$19$2e$2$2e$10_react$40$19$2e$2$2e$3$2f$node_modules$2f$zustand$2f$esm$2f$index$2e$mjs__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__ = __turbopack_context__.i("[project]/OneDrive/Desktop/Event/node_modules/.pnpm/zustand@4.5.7_@types+react@19.2.10_react@19.2.3/node_modules/zustand/esm/index.mjs [app-ssr] (ecmascript) <locals>");
var __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$packages$2f$vendor$2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/OneDrive/Desktop/Event/packages/vendor/src/lib/api.ts [app-ssr] (ecmascript)");
;
;
function _mapUser(u) {
    return {
        id: u.id,
        email: u.email,
        firstName: u.first_name ?? u.firstName ?? null,
        lastName: u.last_name ?? u.lastName ?? null,
        role: u.role ?? 'user',
        phone: u.phone ?? null,
        avatarUrl: u.avatar_url ?? u.avatarUrl ?? null,
        twoFactorEnabled: u.two_factor_enabled ?? u.twoFactorEnabled ?? false,
        emailVerified: u.email_verified ?? u.emailVerified ?? false
    };
}
function _mapVendor(v) {
    return {
        id: v.id,
        userId: v.user_id ?? v.userId,
        businessName: v.business_name ?? v.businessName ?? '',
        description: v.description ?? null,
        contactEmail: v.contact_email ?? v.contactEmail ?? '',
        contactPhone: v.contact_phone ?? v.contactPhone ?? null,
        website: v.website ?? null,
        logoUrl: v.logo_url ?? v.logoUrl ?? null,
        city: v.city ?? null,
        region: v.region ?? null,
        status: v.status ?? 'PENDING',
        rating: v.rating ?? 0,
        totalReviews: v.total_reviews ?? v.totalReviews ?? 0,
        categories: v.categories ?? []
    };
}
const useAuthStore = (0, __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$node_modules$2f2e$pnpm$2f$zustand$40$4$2e$5$2e$7_$40$types$2b$react$40$19$2e$2$2e$10_react$40$19$2e$2$2e$3$2f$node_modules$2f$zustand$2f$esm$2f$index$2e$mjs__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["create"])()((set, get)=>({
        user: null,
        vendor: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
        requiresTwoFactor: false,
        pendingEmail: null,
        vendorCheckStatus: 'idle',
        sessionStatus: 'idle',
        // ── Login ─────────────────────────────────────────────────────────
        login: async (email, password)=>{
            set({
                isLoading: true,
                error: null
            });
            try {
                const response = await __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$packages$2f$vendor$2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"].post('/users/login', {
                    email,
                    password
                });
                if (response.data.requiresTwoFactor) {
                    set({
                        requiresTwoFactor: true,
                        pendingEmail: email,
                        isLoading: false
                    });
                    return false;
                }
                // Backend sets httpOnly cookies; fetch user data
                const userResp = await __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$packages$2f$vendor$2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"].get('/users/me');
                const userData = userResp.data.data ?? userResp.data;
                set({
                    user: _mapUser(userData),
                    vendor: null,
                    isAuthenticated: true,
                    isLoading: false,
                    requiresTwoFactor: false,
                    pendingEmail: null,
                    vendorCheckStatus: 'idle'
                });
                return true;
            } catch (error) {
                set({
                    error: (0, __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$packages$2f$vendor$2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["getApiError"])(error),
                    isLoading: false
                });
                return false;
            }
        },
        // ── 2FA ───────────────────────────────────────────────────────────
        verify2FA: async (code)=>{
            set({
                isLoading: true,
                error: null
            });
            const { pendingEmail } = get();
            if (!pendingEmail) {
                set({
                    error: 'Login session expired. Please try again.',
                    isLoading: false
                });
                return false;
            }
            try {
                await __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$packages$2f$vendor$2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"].post('/auth/login', {
                    email: pendingEmail,
                    password: '',
                    twoFactorCode: code
                });
                // Backend sets httpOnly cookies; fetch user data
                const userResp = await __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$packages$2f$vendor$2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"].get('/users/me');
                const userData = userResp.data.data ?? userResp.data;
                set({
                    user: _mapUser(userData),
                    vendor: null,
                    isAuthenticated: true,
                    isLoading: false,
                    requiresTwoFactor: false,
                    pendingEmail: null,
                    vendorCheckStatus: 'idle'
                });
                return true;
            } catch (error) {
                set({
                    error: (0, __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$packages$2f$vendor$2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["getApiError"])(error),
                    isLoading: false
                });
                return false;
            }
        },
        // ── Register ──────────────────────────────────────────────────────
        register: async (data)=>{
            set({
                isLoading: true,
                error: null
            });
            try {
                const { isAuthenticated } = get();
                if (isAuthenticated) {
                    // Recovery path: user exists but vendor profile is missing
                    const vendorResp = await __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$packages$2f$vendor$2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"].post('/vendors/register', {
                        business_name: data.vendorName,
                        contact_email: data.contactEmail || data.email
                    });
                    const vendorData = vendorResp.data?.data ?? vendorResp.data;
                    if (vendorData) {
                        set({
                            vendor: _mapVendor(vendorData),
                            vendorCheckStatus: 'done',
                            isLoading: false
                        });
                    } else {
                        set({
                            isLoading: false
                        });
                    }
                    return true;
                }
                // Full registration: create user → backend sets httpOnly cookies → create vendor profile
                const regResp = await __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$packages$2f$vendor$2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"].post('/auth/register', {
                    email: data.email,
                    password: data.password,
                    first_name: data.firstName,
                    last_name: data.lastName,
                    role: 'vendor'
                });
                const payload = regResp.data.data ?? regResp.data;
                if (payload?.user) {
                    const vendorResp = await __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$packages$2f$vendor$2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"].post('/vendors/register', {
                        business_name: data.vendorName,
                        contact_email: data.contactEmail || data.email
                    });
                    const vendorData = vendorResp.data?.data ?? vendorResp.data;
                    if (vendorData) {
                        set({
                            vendor: _mapVendor(vendorData),
                            isAuthenticated: true,
                            vendorCheckStatus: 'done'
                        });
                    }
                }
                set({
                    isLoading: false
                });
                return true;
            } catch (error) {
                set({
                    error: (0, __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$packages$2f$vendor$2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["getApiError"])(error),
                    isLoading: false
                });
                return false;
            }
        },
        // ── Logout ────────────────────────────────────────────────────────
        logout: async ()=>{
            try {
                await __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$packages$2f$vendor$2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"].post('/auth/logout');
            } catch  {
            // Always clear local state even if server call fails
            } finally{
                set({
                    user: null,
                    vendor: null,
                    isAuthenticated: false,
                    requiresTwoFactor: false,
                    pendingEmail: null,
                    vendorCheckStatus: 'idle',
                    sessionStatus: 'idle'
                });
            }
        },
        // ── Login with tokens (OAuth callback) ────────────────────────────
        // Token params are ignored — backend already set httpOnly cookies.
        // We just fetch /users/me to hydrate the store.
        loginWithTokens: async (_token, _refreshToken)=>{
            set({
                isLoading: true,
                error: null
            });
            try {
                const userResp = await __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$packages$2f$vendor$2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"].get('/users/me');
                const userData = userResp.data.data ?? userResp.data;
                set({
                    user: _mapUser(userData),
                    vendor: null,
                    isAuthenticated: true,
                    isLoading: false,
                    requiresTwoFactor: false,
                    pendingEmail: null,
                    vendorCheckStatus: 'idle'
                });
            } catch (error) {
                set({
                    error: (0, __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$packages$2f$vendor$2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["getApiError"])(error),
                    isLoading: false,
                    isAuthenticated: false
                });
                throw error;
            }
        },
        // ── Fetch vendor profile (explicit refresh) ───────────────────────
        fetchVendorProfile: async ()=>{
            set({
                isLoading: true
            });
            try {
                const response = await __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$packages$2f$vendor$2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"].get('/vendors/profile/me');
                const vendorData = response.data.data ?? response.data;
                set({
                    vendor: _mapVendor(vendorData),
                    isLoading: false
                });
            } catch (error) {
                set({
                    error: (0, __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$packages$2f$vendor$2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["getApiError"])(error),
                    isLoading: false
                });
            }
        },
        /**
             * ensureVendorProfile — idempotent, concurrency-safe vendor check.
             */ ensureVendorProfile: async ()=>{
            const { isAuthenticated, vendorCheckStatus } = get();
            if (vendorCheckStatus === 'checking' || vendorCheckStatus === 'done') return;
            if (!isAuthenticated) {
                set({
                    vendorCheckStatus: 'done'
                });
                return;
            }
            set({
                vendorCheckStatus: 'checking'
            });
            try {
                const response = await __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$packages$2f$vendor$2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"].get('/vendors/profile/me');
                const vendorData = response.data.data ?? response.data;
                set({
                    vendor: _mapVendor(vendorData),
                    vendorCheckStatus: 'done'
                });
            } catch  {
                set({
                    vendor: null,
                    vendorCheckStatus: 'done'
                });
            }
        },
        // ── Update vendor profile ─────────────────────────────────────────
        updateVendorProfile: async (data)=>{
            set({
                isLoading: true,
                error: null
            });
            try {
                const response = await __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$packages$2f$vendor$2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"].put('/vendors/profile/me', data);
                const vendorData = response.data.data ?? response.data;
                set({
                    vendor: _mapVendor(vendorData),
                    isLoading: false
                });
            } catch (error) {
                set({
                    error: (0, __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$packages$2f$vendor$2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["getApiError"])(error),
                    isLoading: false
                });
                throw error;
            }
        },
        clearError: ()=>set({
                error: null
            }),
        // ── Session hydration (called once on page load) ──────────────────
        // Reads httpOnly cookies via /users/me to restore auth state
        // without requiring the user to log in again.
        initSession: async ()=>{
            const { sessionStatus } = get();
            if (sessionStatus === 'loading' || sessionStatus === 'done') return;
            set({
                sessionStatus: 'loading'
            });
            try {
                const userResp = await __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$packages$2f$vendor$2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"].get('/users/me');
                const userData = userResp.data.data ?? userResp.data;
                set({
                    user: _mapUser(userData),
                    isAuthenticated: true,
                    sessionStatus: 'done',
                    vendorCheckStatus: 'idle'
                });
            } catch  {
                // No valid session — stay unauthenticated
                set({
                    user: null,
                    isAuthenticated: false,
                    sessionStatus: 'done',
                    vendorCheckStatus: 'done'
                });
            }
        }
    }));
const __TURBOPACK__default__export__ = useAuthStore;
}),
"[project]/OneDrive/Desktop/Event/packages/vendor/src/app/auth/callback/page.tsx [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "default",
    ()=>AuthCallbackPage
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$2$2e$4_$40$babel$2b$core$40$7$2e$29$2e$0_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/OneDrive/Desktop/Event/node_modules/.pnpm/next@16.2.4_@babel+core@7.29.0_react-dom@19.2.3_react@19.2.3__react@19.2.3/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react-jsx-dev-runtime.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$2$2e$4_$40$babel$2b$core$40$7$2e$29$2e$0_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/OneDrive/Desktop/Event/node_modules/.pnpm/next@16.2.4_@babel+core@7.29.0_react-dom@19.2.3_react@19.2.3__react@19.2.3/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$2$2e$4_$40$babel$2b$core$40$7$2e$29$2e$0_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$navigation$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/OneDrive/Desktop/Event/node_modules/.pnpm/next@16.2.4_@babel+core@7.29.0_react-dom@19.2.3_react@19.2.3__react@19.2.3/node_modules/next/navigation.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$node_modules$2f2e$pnpm$2f$lucide$2d$react$40$0$2e$309$2e$0_react$40$19$2e$2$2e$3$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$loader$2d$2$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__default__as__Loader2$3e$__ = __turbopack_context__.i("[project]/OneDrive/Desktop/Event/node_modules/.pnpm/lucide-react@0.309.0_react@19.2.3/node_modules/lucide-react/dist/esm/icons/loader-2.js [app-ssr] (ecmascript) <export default as Loader2>");
var __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$packages$2f$vendor$2f$src$2f$lib$2f$auth$2d$store$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/OneDrive/Desktop/Event/packages/vendor/src/lib/auth-store.ts [app-ssr] (ecmascript)");
'use client';
;
;
;
;
;
/**
 * Handles the post-OAuth redirect from the backend.
 *
 * Backend sets httpOnly cookies (access_token, refresh_token) and redirects to:
 *   {FRONTEND_URL}/auth/callback
 *
 * No tokens in the URL — cookies are already set by the backend redirect.
 * This page just fetches /users/me to hydrate the auth store, then goes to /dashboard.
 *
 * Error path: backend redirects to /login?error=<code> directly.
 */ function CallbackHandler() {
    const router = (0, __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$2$2e$4_$40$babel$2b$core$40$7$2e$29$2e$0_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$navigation$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useRouter"])();
    const searchParams = (0, __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$2$2e$4_$40$babel$2b$core$40$7$2e$29$2e$0_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$navigation$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useSearchParams"])();
    const { loginWithTokens } = (0, __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$packages$2f$vendor$2f$src$2f$lib$2f$auth$2d$store$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useAuthStore"])();
    const handled = (0, __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$2$2e$4_$40$babel$2b$core$40$7$2e$29$2e$0_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useRef"])(false);
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$2$2e$4_$40$babel$2b$core$40$7$2e$29$2e$0_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useEffect"])(()=>{
        if (handled.current) return;
        handled.current = true;
        // Backend may still pass an error param if OAuth failed
        const error = searchParams.get('error');
        if (error) {
            const messages = {
                google_auth_denied: 'Google sign-in was cancelled.',
                oauth_email_not_verified: 'Your Google email is not verified.',
                auth_account_inactive: 'Your account has been deactivated.',
                invalid_callback: 'Invalid sign-in callback. Please try again.'
            };
            const msg = encodeURIComponent(messages[error] ?? 'Google sign-in failed. Please try again.');
            router.replace(`/login?error=${msg}`);
            return;
        }
        // Cookies are already set by the backend — just hydrate the store
        // loginWithTokens ignores the token params and calls /users/me directly
        loginWithTokens('', '').then(()=>{
            router.replace('/dashboard');
        }).catch(()=>{
            router.replace('/login?error=Authentication+failed.+Please+try+again.');
        });
    }, [
        searchParams,
        loginWithTokens,
        router
    ]);
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$2$2e$4_$40$babel$2b$core$40$7$2e$29$2e$0_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "flex min-h-screen items-center justify-center",
        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$2$2e$4_$40$babel$2b$core$40$7$2e$29$2e$0_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
            className: "flex flex-col items-center gap-4",
            children: [
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$2$2e$4_$40$babel$2b$core$40$7$2e$29$2e$0_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$node_modules$2f2e$pnpm$2f$lucide$2d$react$40$0$2e$309$2e$0_react$40$19$2e$2$2e$3$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$loader$2d$2$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__default__as__Loader2$3e$__["Loader2"], {
                    className: "h-10 w-10 animate-spin text-primary-600"
                }, void 0, false, {
                    fileName: "[project]/OneDrive/Desktop/Event/packages/vendor/src/app/auth/callback/page.tsx",
                    lineNumber: 55,
                    columnNumber: 17
                }, this),
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$2$2e$4_$40$babel$2b$core$40$7$2e$29$2e$0_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                    className: "text-sm text-surface-500",
                    children: "Completing sign-in..."
                }, void 0, false, {
                    fileName: "[project]/OneDrive/Desktop/Event/packages/vendor/src/app/auth/callback/page.tsx",
                    lineNumber: 56,
                    columnNumber: 17
                }, this)
            ]
        }, void 0, true, {
            fileName: "[project]/OneDrive/Desktop/Event/packages/vendor/src/app/auth/callback/page.tsx",
            lineNumber: 54,
            columnNumber: 13
        }, this)
    }, void 0, false, {
        fileName: "[project]/OneDrive/Desktop/Event/packages/vendor/src/app/auth/callback/page.tsx",
        lineNumber: 53,
        columnNumber: 9
    }, this);
}
function AuthCallbackPage() {
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$2$2e$4_$40$babel$2b$core$40$7$2e$29$2e$0_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$2$2e$4_$40$babel$2b$core$40$7$2e$29$2e$0_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["Suspense"], {
        fallback: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$2$2e$4_$40$babel$2b$core$40$7$2e$29$2e$0_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
            className: "flex min-h-screen items-center justify-center",
            children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$2$2e$4_$40$babel$2b$core$40$7$2e$29$2e$0_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$node_modules$2f2e$pnpm$2f$lucide$2d$react$40$0$2e$309$2e$0_react$40$19$2e$2$2e$3$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$loader$2d$2$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__default__as__Loader2$3e$__["Loader2"], {
                className: "h-10 w-10 animate-spin text-primary-600"
            }, void 0, false, {
                fileName: "[project]/OneDrive/Desktop/Event/packages/vendor/src/app/auth/callback/page.tsx",
                lineNumber: 67,
                columnNumber: 21
            }, this)
        }, void 0, false, {
            fileName: "[project]/OneDrive/Desktop/Event/packages/vendor/src/app/auth/callback/page.tsx",
            lineNumber: 66,
            columnNumber: 17
        }, this),
        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$OneDrive$2f$Desktop$2f$Event$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$2$2e$4_$40$babel$2b$core$40$7$2e$29$2e$0_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(CallbackHandler, {}, void 0, false, {
            fileName: "[project]/OneDrive/Desktop/Event/packages/vendor/src/app/auth/callback/page.tsx",
            lineNumber: 71,
            columnNumber: 13
        }, this)
    }, void 0, false, {
        fileName: "[project]/OneDrive/Desktop/Event/packages/vendor/src/app/auth/callback/page.tsx",
        lineNumber: 64,
        columnNumber: 9
    }, this);
}
}),
];

//# sourceMappingURL=%5Broot-of-the-server%5D__0bof~9h._.js.map