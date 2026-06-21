"use client";

import { QueryClient, QueryClientProvider, useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { usePathname } from "next/navigation";
import { Toaster } from "react-hot-toast";
import { TermsModal } from "@/components/terms-modal";
import { api, acceptTerms } from "@/lib/api";

function TermsGate({ children }: { children: React.ReactNode }) {
    const queryClient = useQueryClient();
    const pathname = usePathname();

    // Skip TermsGate on auth callback page - let tokens be stored first
    const isAuthCallback = pathname === "/auth/callback";

    const { data: user } = useQuery({
        queryKey: ["me-terms"],
        queryFn: async () => {
            try {
                const res = await api.get("/users/me");
                return res.data?.data ?? res.data ?? null;
            } catch {
                return null;
            }
        },
        enabled: !isAuthCallback && typeof window !== 'undefined' && !!localStorage.getItem('access_token'),
        retry: false,
        staleTime: Infinity,
    });

    const { mutate, isPending } = useMutation({
        mutationFn: acceptTerms,
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ["me-terms"] }),
    });

    const needsTerms = user && !user.terms_accepted_at;

    return (
        <>
            {children}
            {needsTerms && <TermsModal onAccept={() => mutate()} isAccepting={isPending} />}
        </>
    );
}

export function Providers({ children }: { children: React.ReactNode }) {
    const [queryClient] = useState(
        () =>
            new QueryClient({
                defaultOptions: {
                    queries: {
                        staleTime: 30 * 1000, // 30 seconds
                        refetchOnWindowFocus: false,
                        retry: 1,
                    },
                },
            })
    );

    return (
        <QueryClientProvider client={queryClient}>
            <TermsGate>{children}</TermsGate>
            <Toaster
                position="top-right"
                toastOptions={{
                    duration: 4000,
                    style: {
                        background: '#1f2937',
                        color: '#f9fafb',
                        borderRadius: '0.75rem',
                        fontSize: '0.875rem',
                    },
                    success: {
                        iconTheme: { primary: '#10b981', secondary: '#f9fafb' },
                    },
                    error: {
                        iconTheme: { primary: '#ef4444', secondary: '#f9fafb' },
                    },
                }}
            />
        </QueryClientProvider>
    );
}
