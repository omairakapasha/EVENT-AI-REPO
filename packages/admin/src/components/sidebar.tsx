"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname, useRouter } from "next/navigation";
import {
    LayoutDashboard, Users, Store, Settings, LogOut,
    CalendarCheck,
} from "lucide-react";
import api from "@/lib/api";

const navigation = [
    { name: "Dashboard", href: "/", icon: LayoutDashboard },
    { name: "Vendors", href: "/vendors", icon: Store },
    { name: "Bookings", href: "/bookings", icon: CalendarCheck },
    { name: "Users", href: "/users", icon: Users },
    { name: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
    const pathname = usePathname();
    const router = useRouter();

    const handleLogout = async () => {
        try {
            await api.post('/auth/logout');
        } catch {
            // Always redirect even if server call fails
        } finally {
            router.push('/login');
        }
    };

    return (
        <aside className="flex h-full w-60 flex-col" style={{
            background: "linear-gradient(180deg, #1A3D64 0%, #122d4a 100%)",
            borderRight: "1px solid rgba(255,255,255,0.06)"
        }}>
            {/* Brand */}
            <div className="flex h-16 items-center gap-3 px-5" style={{
                borderBottom: "1px solid rgba(255,255,255,0.06)"
            }}>
                <div className="flex h-8 w-8 items-center justify-center rounded-lg flex-shrink-0 overflow-hidden bg-white/10">
                    <Image src="/logo.png" alt="Event-AI" width={32} height={32} className="object-contain" />
                </div>
                <div>
                    <p className="text-sm font-bold text-white leading-none">Event-AI</p>
                    <p className="text-[10px] mt-0.5 font-medium uppercase tracking-wider"
                        style={{ color: "rgba(150,167,141,0.6)" }}>Admin</p>
                </div>
            </div>

            {/* Nav */}
            <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
                <p className="px-3 mb-3 text-[10px] font-semibold uppercase tracking-widest"
                    style={{ color: "rgba(239,236,227,0.3)" }}>
                    Navigation
                </p>
                {navigation.map((item) => {
                    const isActive = pathname === item.href;
                    return (
                        <Link
                            key={item.name}
                            href={item.href}
                            className="group flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150"
                            style={isActive ? {
                                background: "rgba(239,236,227,0.15)",
                                color: "#EFECE3",
                                boxShadow: "inset 0 0 0 1px rgba(239,236,227,0.2)"
                            } : {
                                color: "rgba(239,236,227,0.55)"
                            }}
                            onMouseEnter={(e) => {
                                if (!isActive) {
                                    (e.currentTarget as HTMLAnchorElement).style.background = "rgba(239,236,227,0.08)";
                                    (e.currentTarget as HTMLAnchorElement).style.color = "rgba(239,236,227,0.9)";
                                }
                            }}
                            onMouseLeave={(e) => {
                                if (!isActive) {
                                    (e.currentTarget as HTMLAnchorElement).style.background = "transparent";
                                    (e.currentTarget as HTMLAnchorElement).style.color = "rgba(239,236,227,0.55)";
                                }
                            }}
                        >
                            <item.icon className="h-4 w-4 flex-shrink-0" style={{
                                color: isActive ? "#96A78D" : "rgba(150,167,141,0.6)"
                            }} />
                            <span>{item.name}</span>
                            {isActive && (
                                <div className="ml-auto h-1.5 w-1.5 rounded-full"
                                    style={{ background: "#96A78D" }} />
                            )}
                        </Link>
                    );
                })}
            </nav>

            {/* Footer */}
            <div className="p-3" style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}>
                <button
                    onClick={handleLogout}
                    className="flex w-full items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150"
                    style={{ color: "rgba(239,236,227,0.4)" }}
                    onMouseEnter={(e) => {
                        (e.currentTarget as HTMLButtonElement).style.background = "rgba(239,68,68,0.08)";
                        (e.currentTarget as HTMLButtonElement).style.color = "rgba(252,165,165,0.8)";
                    }}
                    onMouseLeave={(e) => {
                        (e.currentTarget as HTMLButtonElement).style.background = "transparent";
                        (e.currentTarget as HTMLButtonElement).style.color = "rgba(239,236,227,0.4)";
                    }}
                >
                    <LogOut className="h-4 w-4 flex-shrink-0" />
                    Sign Out
                </button>
            </div>
        </aside>
    );
}
