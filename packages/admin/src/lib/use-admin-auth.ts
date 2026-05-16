"use client";

import { useState, useEffect, useCallback } from "react";
import api from "./api";

interface AdminUser {
    id: string;
    email: string;
    firstName: string | null;
    lastName: string | null;
    role: string;
}

interface UseAdminAuth {
    user: AdminUser | null;
    isAuthenticated: boolean;
    status: "loading" | "authenticated" | "unauthenticated";
}

/**
 * Lightweight auth hook for the admin portal.
 *
 * Replaces next-auth's useSession(). Hydrates auth state from httpOnly
 * cookies via GET /users/me on mount. No client-side token storage.
 */
export function useAdminAuth(): UseAdminAuth {
    const [user, setUser] = useState<AdminUser | null>(null);
    const [status, setStatus] = useState<"loading" | "authenticated" | "unauthenticated">("loading");

    const hydrate = useCallback(async () => {
        try {
            const resp = await api.get("/users/me");
            const data = resp.data?.data ?? resp.data;
            setUser({
                id: data.id,
                email: data.email,
                firstName: data.first_name ?? data.firstName ?? null,
                lastName: data.last_name ?? data.lastName ?? null,
                role: data.role,
            });
            setStatus("authenticated");
        } catch {
            setUser(null);
            setStatus("unauthenticated");
        }
    }, []);

    useEffect(() => {
        hydrate();
    }, [hydrate]);

    return { user, isAuthenticated: status === "authenticated", status };
}
