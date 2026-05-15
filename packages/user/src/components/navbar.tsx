"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Calendar, Store, MessageSquare, User, Menu, X, LogOut, ChevronDown, Package, Sparkles } from "lucide-react";
import { cn } from "@repo/ui/lib/utils";
import { NotificationBell } from "./notification-bell";

const navigation = [
    { name: "My Events", href: "/dashboard", icon: Calendar },
    { name: "Marketplace", href: "/marketplace", icon: Store },
    { name: "Bookings", href: "/bookings", icon: Package },
    { name: "AI Assistant", href: "/chat", icon: MessageSquare },
    { name: "Profile", href: "/profile", icon: User },
];

export function Navbar() {
    const pathname = usePathname();
    const router = useRouter();
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const [userMenuOpen, setUserMenuOpen] = useState(false);
    const [userName, setUserName] = useState<string | null>(null);
    const [scrolled, setScrolled] = useState(false);
    const userMenuRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        // Fetch user data from API since we use httpOnly cookies
        fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000/api/v1"}/users/me`, {
            credentials: "include",
        })
            .then(res => res.json())
            .then(data => {
                const user = data.data || data;
                if (user) {
                    setUserName(`${user.first_name || ""} ${user.last_name || ""}`.trim() || user.email || "User");
                }
            })
            .catch(() => setUserName(null));
    }, []);

    useEffect(() => {
        const handleScroll = () => setScrolled(window.scrollY > 8);
        window.addEventListener("scroll", handleScroll, { passive: true });
        return () => window.removeEventListener("scroll", handleScroll);
    }, []);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node))
                setUserMenuOpen(false);
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const handleLogout = async () => {
        try {
            await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000/api/v1"}/auth/logout`, {
                method: "POST",
                credentials: "include",
            });
        } catch {}
        router.push("/login");
    };

    const [isLoggedIn, setIsLoggedIn] = useState(false);

    useEffect(() => {
        // Check auth status via API (httpOnly cookies)
        fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000/api/v1"}/users/me`, {
            credentials: "include",
        })
            .then(res => setIsLoggedIn(res.ok))
            .catch(() => setIsLoggedIn(false));
    }, []);

    if (pathname === "/login" || pathname === "/signup" || pathname === "/register") return null;

    return (
        <nav className="sticky top-0 z-50 transition-all duration-300"
            style={{
                background: scrolled ? "rgba(255,255,255,0.94)" : "rgba(255,255,255,0.88)",
                backdropFilter: "blur(20px)",
                WebkitBackdropFilter: "blur(20px)",
                borderBottom: scrolled ? "1px solid rgba(99,102,241,0.12)" : "1px solid rgba(226,232,240,0.7)",
                boxShadow: scrolled ? "0 4px 24px rgba(0,0,0,0.06)" : "none",
            }}
            role="navigation" aria-label="Main navigation">
            <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
                <div className="flex h-16 items-center justify-between">
                    {/* Logo */}
                    <Link href="/" className="flex items-center gap-2.5 group">
                        <div className="flex h-8 w-8 items-center justify-center rounded-xl transition-transform group-hover:scale-105"
                            style={{ background: "linear-gradient(135deg,#4f46e5,#7c3aed)", boxShadow: "0 4px 12px rgba(99,102,241,0.3)" }}>
                            <Sparkles className="h-4 w-4 text-white" />
                        </div>
                        <span className="text-base font-bold"
                            style={{ background: "linear-gradient(135deg,#1e1b4b,#4f46e5)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
                            Event-AI
                        </span>
                    </Link>

                    {/* Desktop Nav */}
                    <div className="hidden sm:flex sm:items-center sm:gap-0.5">
                        {navigation.map((item) => {
                            const isActive = pathname === item.href;
                            return (
                                <Link key={item.name} href={item.href}
                                    className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-sm font-medium transition-all duration-150"
                                    style={isActive ? { background: "rgba(99,102,241,0.08)", color: "#4f46e5" } : { color: "#64748b" }}
                                    onMouseEnter={(e) => { if (!isActive) { (e.currentTarget as HTMLAnchorElement).style.background = "rgba(99,102,241,0.05)"; (e.currentTarget as HTMLAnchorElement).style.color = "#1e293b"; } }}
                                    onMouseLeave={(e) => { if (!isActive) { (e.currentTarget as HTMLAnchorElement).style.background = "transparent"; (e.currentTarget as HTMLAnchorElement).style.color = "#64748b"; } }}
                                >
                                    <item.icon className="h-4 w-4" />
                                    {item.name}
                                </Link>
                            );
                        })}
                    </div>

                    {/* Right side */}
                    <div className="flex items-center gap-2">
                        {isLoggedIn && <NotificationBell />}
                        {isLoggedIn ? (
                            <div className="relative" ref={userMenuRef}>
                                <button onClick={() => setUserMenuOpen(!userMenuOpen)}
                                    className="flex items-center gap-2 px-2.5 py-1.5 rounded-xl text-sm font-medium transition-all duration-150 hover:bg-indigo-50">
                                    <div className="flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold text-white"
                                        style={{ background: "linear-gradient(135deg,#4f46e5,#7c3aed)" }}>
                                        {userName ? userName.charAt(0).toUpperCase() : "U"}
                                    </div>
                                    <span className="hidden md:inline text-sm font-medium text-slate-700">{userName || "Account"}</span>
                                    <ChevronDown className="h-3 w-3 text-slate-400" />
                                </button>
                                {userMenuOpen && (
                                    <div className="absolute right-0 mt-2 w-52 rounded-2xl overflow-hidden z-50"
                                        style={{ background: "white", border: "1px solid rgba(226,232,240,0.8)", boxShadow: "0 20px 40px rgba(0,0,0,0.12)" }}>
                                        <div className="px-4 py-3 border-b border-gray-100">
                                            <p className="text-xs text-gray-400 uppercase tracking-wider font-semibold">Signed in as</p>
                                            <p className="text-sm font-semibold text-gray-900 truncate mt-0.5">{userName || "User"}</p>
                                        </div>
                                        <button onClick={handleLogout}
                                            className="w-full flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-red-500 hover:bg-red-50 transition-colors">
                                            <LogOut className="h-4 w-4" />
                                            Sign out
                                        </button>
                                    </div>
                                )}
                            </div>
                        ) : (
                            <Link href="/login"
                                className="px-4 py-2 text-sm font-semibold text-white rounded-xl transition-all active:scale-[0.98]"
                                style={{ background: "linear-gradient(135deg,#4f46e5,#7c3aed)", boxShadow: "0 4px 12px rgba(99,102,241,0.3)" }}>
                                Sign in
                            </Link>
                        )}
                        <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                            className="sm:hidden p-2 rounded-xl text-slate-500 hover:bg-indigo-50 transition-colors"
                            aria-label="Toggle menu">
                            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
                        </button>
                    </div>
                </div>
            </div>

            {/* Mobile menu */}
            {mobileMenuOpen && (
                <div className="sm:hidden border-t border-gray-100 bg-white/95 backdrop-blur-xl">
                    <div className="px-4 py-3 space-y-1">
                        {navigation.map((item) => (
                            <Link key={item.name} href={item.href}
                                onClick={() => setMobileMenuOpen(false)}
                                className={cn(
                                    "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors",
                                    pathname === item.href ? "bg-indigo-50 text-indigo-700" : "text-slate-600 hover:bg-gray-50"
                                )}>
                                <item.icon className="h-5 w-5" />
                                {item.name}
                            </Link>
                        ))}
                    </div>
                </div>
            )}
        </nav>
    );
}
