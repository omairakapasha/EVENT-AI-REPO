"use client";

/**
 * SocketProvider — kept as a no-op stub.
 *
 * The backend uses Server-Sent Events (SSE) at /api/v1/sse/stream,
 * not socket.io. Real-time updates are handled by NotificationProvider
 * via EventSource. This provider exists only to avoid breaking imports.
 */

import { createContext, useContext } from "react";

const SocketContext = createContext<null>(null);

export const useSocket = () => useContext(SocketContext);

export function SocketProvider({ children }: { children: React.ReactNode }) {
    return (
        <SocketContext.Provider value={null}>
            {children}
        </SocketContext.Provider>
    );
}
