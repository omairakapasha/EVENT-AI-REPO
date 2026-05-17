"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { Toaster } from "react-hot-toast";

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
            {children}
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
