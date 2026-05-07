import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import api, { setAccessToken, setRefreshToken, clearTokens, getApiError } from './api';

// ── Secure pending credentials (module-scoped, never persisted) ───────────────
let _pendingCredentials: { email: string; password: string } | null = null;
let _pendingTimeout: ReturnType<typeof setTimeout> | null = null;
const PENDING_TIMEOUT_MS = 5 * 60 * 1000;

function setPendingCredentials(email: string, password: string) {
    clearPendingCredentials();
    _pendingCredentials = { email, password };
    _pendingTimeout = setTimeout(clearPendingCredentials, PENDING_TIMEOUT_MS);
}
function clearPendingCredentials() {
    _pendingCredentials = null;
    if (_pendingTimeout) { clearTimeout(_pendingTimeout); _pendingTimeout = null; }
}
function getPendingCredentials() { return _pendingCredentials; }

// ── Mappers ───────────────────────────────────────────────────────────────────
export function _mapUser(u: Record<string, unknown>): User {
    return {
        id: u.id as string,
        email: u.email as string,
        firstName: (u.first_name ?? u.firstName ?? null) as string | null,
        lastName: (u.last_name ?? u.lastName ?? null) as string | null,
        role: (u.role as User['role']) ?? 'user',
        phone: (u.phone ?? null) as string | null,
        avatarUrl: (u.avatar_url ?? u.avatarUrl ?? null) as string | null,
        twoFactorEnabled: (u.two_factor_enabled ?? u.twoFactorEnabled ?? false) as boolean,
        emailVerified: (u.email_verified ?? u.emailVerified ?? false) as boolean,
    };
}

export function _mapVendor(v: Record<string, unknown>): Vendor {
    return {
        id: v.id as string,
        userId: (v.user_id ?? v.userId) as string,
        businessName: (v.business_name ?? v.businessName ?? '') as string,
        description: (v.description ?? null) as string | null,
        contactEmail: (v.contact_email ?? v.contactEmail ?? '') as string,
        contactPhone: (v.contact_phone ?? v.contactPhone ?? null) as string | null,
        website: (v.website ?? null) as string | null,
        logoUrl: (v.logo_url ?? v.logoUrl ?? null) as string | null,
        city: (v.city ?? null) as string | null,
        region: (v.region ?? null) as string | null,
        status: (v.status as Vendor['status']) ?? 'PENDING',
        rating: (v.rating ?? 0) as number,
        totalReviews: (v.total_reviews ?? v.totalReviews ?? 0) as number,
        categories: (v.categories ?? []) as CategoryRead[],
    };
}

// ── Cookie helpers ────────────────────────────────────────────────────────────
// SameSite=Lax; Secure omitted for localhost dev. Add Secure in production.
function setAuthCookie() {
    if (typeof document !== 'undefined') {
        document.cookie = 'is-authenticated=true; path=/; max-age=604800; SameSite=Lax';
    }
}
function setRoleCookie(role: string) {
    if (typeof document !== 'undefined') {
        document.cookie = `user-role=${role}; path=/; max-age=604800; SameSite=Lax`;
    }
}
function clearAuthCookies() {
    if (typeof document !== 'undefined') {
        document.cookie = 'is-authenticated=; path=/; max-age=0; SameSite=Lax';
        document.cookie = 'user-role=; path=/; max-age=0; SameSite=Lax';
    }
}

// ── Types ─────────────────────────────────────────────────────────────────────
export interface CategoryRead { id: string; name: string; slug: string; }

export interface User {
    id: string;
    email: string;
    firstName: string | null;
    lastName: string | null;
    role: 'user' | 'vendor' | 'admin';
    phone: string | null;
    avatarUrl: string | null;
    twoFactorEnabled: boolean;
    emailVerified: boolean;
}

export interface Vendor {
    id: string;
    userId: string;
    businessName: string;
    description: string | null;
    contactEmail: string;
    contactPhone: string | null;
    website: string | null;
    logoUrl: string | null;
    city: string | null;
    region: string | null;
    status: 'PENDING' | 'ACTIVE' | 'SUSPENDED' | 'REJECTED';
    rating: number;
    totalReviews: number;
    categories: CategoryRead[];
}

export interface RegisterData {
    vendorName: string;
    businessType?: string;
    contactEmail: string;
    phone?: string;
    website?: string;
    firstName: string;
    lastName: string;
    email: string;
    password: string;
    confirmPassword: string;
}

/**
 * vendorCheckStatus state machine:
 *   idle     → check has not started (initial / after logout / after login)
 *   checking → fetch in-flight (only ONE fetch allowed at a time — guarded by this flag)
 *   done     → resolved; vendor is either populated or null (no profile exists)
 *
 * NOTE: vendorCheckStatus is intentionally NOT persisted to localStorage.
 * On every page load we re-verify the vendor profile against the backend so
 * stale localStorage data never causes a false "done" state.
 */
interface AuthState {
    user: User | null;
    vendor: Vendor | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    error: string | null;
    requiresTwoFactor: boolean;
    pendingEmail: string | null;
    vendorCheckStatus: 'idle' | 'checking' | 'done';

    login: (email: string, password: string) => Promise<boolean>;
    loginWithTokens: (token: string, refreshToken: string) => Promise<void>;
    verify2FA: (code: string) => Promise<boolean>;
    register: (data: RegisterData) => Promise<boolean>;
    logout: () => Promise<void>;
    fetchVendorProfile: () => Promise<void>;
    ensureVendorProfile: () => Promise<void>;
    updateVendorProfile: (data: Partial<Vendor>) => Promise<void>;
    clearError: () => void;
}

export const useAuthStore = create<AuthState>()(
    persist(
        (set, get) => ({
            user: null,
            vendor: null,
            isAuthenticated: false,
            isLoading: false,
            error: null,
            requiresTwoFactor: false,
            pendingEmail: null,
            // Always start idle — never persisted, re-checked on every mount
            vendorCheckStatus: 'idle' as const,

            // ── Login ─────────────────────────────────────────────────────────
            login: async (email, password) => {
                set({ isLoading: true, error: null });
                try {
                    const response = await api.post('/users/login', { email, password });

                    if (response.data.requiresTwoFactor) {
                        setPendingCredentials(email, password);
                        set({ requiresTwoFactor: true, pendingEmail: email, isLoading: false });
                        return false;
                    }

                    const payload = response.data.data ?? response.data;
                    const { token, refresh_token, user } = payload;
                    setAccessToken(token);
                    setRefreshToken(refresh_token);
                    setAuthCookie();
                    setRoleCookie(user.role ?? 'user');
                    clearPendingCredentials();

                    set({
                        user: _mapUser(user),
                        vendor: null,
                        isAuthenticated: true,
                        isLoading: false,
                        requiresTwoFactor: false,
                        pendingEmail: null,
                        // Reset so ensureVendorProfile re-runs after login
                        vendorCheckStatus: 'idle',
                    });
                    return true;
                } catch (error) {
                    set({ error: getApiError(error), isLoading: false });
                    return false;
                }
            },

            // ── OAuth token login ─────────────────────────────────────────────
            loginWithTokens: async (token, refreshToken) => {
                setAccessToken(token);
                setRefreshToken(refreshToken);
                setAuthCookie();
                try {
                    const userResp = await api.get('/users/me');
                    const userData = userResp.data.data ?? userResp.data;
                    setRoleCookie(userData.role ?? 'user');
                    set({
                        user: _mapUser(userData),
                        isAuthenticated: true,
                        isLoading: false,
                        vendorCheckStatus: 'idle',
                    });
                } catch {
                    set({ isAuthenticated: true, isLoading: false, vendorCheckStatus: 'idle' });
                }
            },

            // ── 2FA ───────────────────────────────────────────────────────────
            verify2FA: async (code) => {
                const creds = getPendingCredentials();
                if (!creds) {
                    set({ error: 'Login session expired. Please try again.' });
                    return false;
                }
                set({ isLoading: true, error: null });
                try {
                    const response = await api.post('/auth/login', {
                        email: creds.email,
                        password: creds.password,
                        twoFactorCode: code,
                    });
                    const payload = response.data.data ?? response.data;
                    const { token, refresh_token, user } = payload;
                    setAccessToken(token);
                    setRefreshToken(refresh_token);
                    setAuthCookie();
                    setRoleCookie(user.role ?? 'user');
                    clearPendingCredentials();
                    set({
                        user: _mapUser(user),
                        vendor: null,
                        isAuthenticated: true,
                        isLoading: false,
                        requiresTwoFactor: false,
                        pendingEmail: null,
                        vendorCheckStatus: 'idle',
                    });
                    return true;
                } catch (error) {
                    set({ error: getApiError(error), isLoading: false });
                    return false;
                }
            },

            // ── Register ──────────────────────────────────────────────────────
            register: async (data) => {
                set({ isLoading: true, error: null });
                try {
                    // Use get() from closure — never reference useAuthStore.getState() inside actions
                    const { isAuthenticated } = get();

                    if (isAuthenticated) {
                        // Recovery path: user exists but vendor profile is missing
                        const vendorResp = await api.post('/vendors/register', {
                            business_name: data.vendorName,
                            contact_email: data.contactEmail || data.email,
                        });
                        const vendorData = vendorResp.data?.data ?? vendorResp.data;
                        if (vendorData) {
                            set({
                                vendor: _mapVendor(vendorData as Record<string, unknown>),
                                // Mark done so VendorLayout stops blocking and renders
                                vendorCheckStatus: 'done',
                                isLoading: false,
                            });
                        } else {
                            set({ isLoading: false });
                        }
                        return true;
                    }

                    // Full registration: create user → get tokens → create vendor profile
                    const regResp = await api.post('/auth/register', {
                        email: data.email,
                        password: data.password,
                        first_name: data.firstName,
                        last_name: data.lastName,
                        role: 'vendor',
                    });
                    const payload = regResp.data.data ?? regResp.data;

                    if (payload?.access_token) {
                        setAccessToken(payload.access_token);
                        if (payload.refresh_token) setRefreshToken(payload.refresh_token);
                        setAuthCookie();
                        setRoleCookie('vendor');

                        const vendorResp = await api.post('/vendors/register', {
                            business_name: data.vendorName,
                            contact_email: data.contactEmail || data.email,
                        });
                        const vendorData = vendorResp.data?.data ?? vendorResp.data;
                        if (vendorData) {
                            set({
                                vendor: _mapVendor(vendorData as Record<string, unknown>),
                                isAuthenticated: true,
                                vendorCheckStatus: 'done',
                            });
                        }
                    }

                    set({ isLoading: false });
                    return true;
                } catch (error) {
                    set({ error: getApiError(error), isLoading: false });
                    return false;
                }
            },

            // ── Logout ────────────────────────────────────────────────────────
            logout: async () => {
                try {
                    await api.post('/auth/logout');
                } catch {
                    // Always clear local state even if server call fails
                } finally {
                    clearTokens();
                    clearAuthCookies();
                    clearPendingCredentials();
                    set({
                        user: null,
                        vendor: null,
                        isAuthenticated: false,
                        requiresTwoFactor: false,
                        pendingEmail: null,
                        vendorCheckStatus: 'idle',
                    });
                }
            },

            // ── Fetch vendor profile (explicit refresh) ───────────────────────
            fetchVendorProfile: async () => {
                set({ isLoading: true });
                try {
                    const response = await api.get('/vendors/profile/me');
                    const vendorData = response.data.data ?? response.data;
                    set({ vendor: _mapVendor(vendorData), isLoading: false });
                } catch (error) {
                    set({ error: getApiError(error), isLoading: false });
                }
            },

            /**
             * ensureVendorProfile — idempotent, concurrency-safe vendor check.
             *
             * Race condition prevention:
             * - Guards on 'checking' status so concurrent calls (React StrictMode
             *   double-invoke, fast navigation) never fire two parallel fetches.
             * - Always re-fetches from backend on 'idle' — never trusts stale
             *   localStorage vendor data as proof of a valid profile.
             * - Sets 'done' in both success and error paths so the layout always
             *   unblocks, even on network failure.
             */
            ensureVendorProfile: async () => {
                const { isAuthenticated, vendorCheckStatus } = get();

                // Guard: only one in-flight check at a time
                if (vendorCheckStatus === 'checking' || vendorCheckStatus === 'done') return;

                if (!isAuthenticated) {
                    set({ vendorCheckStatus: 'done' });
                    return;
                }

                // Atomically transition to 'checking' — prevents concurrent calls
                set({ vendorCheckStatus: 'checking' });

                try {
                    const response = await api.get('/vendors/profile/me');
                    const vendorData = response.data.data ?? response.data;
                    set({ vendor: _mapVendor(vendorData), vendorCheckStatus: 'done' });
                } catch {
                    // 404 = no vendor profile; any other error = treat as missing
                    // Layout will redirect to /register?incomplete=1
                    set({ vendor: null, vendorCheckStatus: 'done' });
                }
            },

            // ── Update vendor profile ─────────────────────────────────────────
            updateVendorProfile: async (data) => {
                set({ isLoading: true, error: null });
                try {
                    const response = await api.put('/vendors/profile/me', data);
                    const vendorData = response.data.data ?? response.data;
                    set({ vendor: _mapVendor(vendorData), isLoading: false });
                } catch (error) {
                    set({ error: getApiError(error), isLoading: false });
                    throw error;
                }
            },

            clearError: () => set({ error: null }),
        }),
        {
            name: 'auth-storage',
            storage: createJSONStorage(() => localStorage),
            // vendorCheckStatus is intentionally excluded — always re-verified on mount
            partialize: (state) => ({
                user: state.user,
                vendor: state.vendor,
                isAuthenticated: state.isAuthenticated,
            }),
        }
    )
);

export default useAuthStore;
