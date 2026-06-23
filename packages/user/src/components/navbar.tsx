"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import Image from "next/image";
import { Calendar, Store, MessageSquare, User, Menu, X, LogOut, ChevronDown, Package } from "lucide-react";
import { cn } from "@repo/ui/lib/utils";
import { NotificationBell } from "./notification-bell";
import { logout, getUserProfile } from "@/lib/api";

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
    const [isPro, setIsPro] = useState(false);
    const [isLoggedIn, setIsLoggedIn] = useState(false);
    const [scrolled, setScrolled] = useState(false);
    const userMenuRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        // Skip on auth callback page - let tokens be stored first
        if (pathname === "/auth/callback") {
            return;
        }

        // Only fetch user data if token exists (user is logged in)
        const token = localStorage.getItem('access_token');
        if (!token) {
            setUserName(null);
            setIsLoggedIn(false);
            return;
        }

        // Fetch user data using the API client (handles both cookies and localStorage tokens)
        getUserProfile()
            .then(response => {
                const user = response.data || response;
                if (user) {
                    setUserName(`${user.first_name || ""} ${user.last_name || ""}`.trim() || user.email || "User");
                    setIsPro(user.subscription_status === "pro");
                    setIsLoggedIn(true);
                }
            })
            .catch(() => {
                setUserName(null);
                setIsLoggedIn(false);
            });
    }, [pathname]);

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
        await logout();
        router.push("/login");
    };

    if (pathname === "/login" || pathname === "/signup" || pathname === "/register") return null;

    return (
        <nav className="sticky top-0 z-50 border-b border-surface-200 bg-white/95 backdrop-blur-md transition-all duration-300 dark:border-surface-800 dark:bg-surface-900/95"
            role="navigation" aria-label="Main navigation">
            <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
                <div className="flex h-16 items-center justify-between">
                    {/* Logo */}
                    <Link href="/" className="flex items-center gap-2.5 group">
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg overflow-hidden transition-transform group-hover:scale-105">
                            <Image src="/logo.png" alt="Event-AI" width={32} height={32} className="object-contain" />
                        </div>
                        <span className="text-base font-bold text-primary-600 dark:text-primary-400">Event-AI</span>
                    </Link>

                    {/* Desktop Nav */}
                    <div className="hidden sm:flex sm:items-center sm:gap-1">
                        {navigation.map((item) => {
                            const isActive = pathname === item.href;
                            return (
                                <Link key={item.name} href={item.href}
                                    className={cn(
                                        "flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-colors",
                                        isActive
                                            ? "bg-primary-50 text-primary-700 dark:bg-primary-900/20 dark:text-primary-300"
                                            : "text-surface-600 hover:bg-surface-100 hover:text-primary-600 dark:text-surface-400 dark:hover:bg-surface-800 dark:hover:text-primary-300"
                                    )}
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
                                    className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-sm font-medium transition-colors hover:bg-surface-100 dark:hover:bg-surface-800">
                                    <div className="relative flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold text-white bg-primary-600 dark:bg-primary-500">
                                        {userName ? userName.charAt(0).toUpperCase() : "U"}
                                        {isPro && (
                                            <span className="absolute -top-1 -right-1 flex h-3.5 w-3.5 items-center justify-center rounded-full text-[7px] font-bold text-white leading-none bg-warning-500">
                                                P
                                            </span>
                                        )}
                                    </div>
                                    <span className="hidden md:inline text-sm font-medium text-surface-700 dark:text-surface-300">{userName || "Account"}</span>
                                    {isPro && <span className="hidden md:inline px-1.5 py-0.5 rounded-md text-[9px] font-bold text-white leading-none bg-warning-500">PRO</span>}
                                    <ChevronDown className="h-3 w-3 text-surface-400" />
                                </button>
                                {userMenuOpen && (
                                    <div className="absolute right-0 mt-2 w-52 rounded-lg overflow-hidden z-50 border border-surface-200 bg-white shadow-lg dark:border-surface-700 dark:bg-surface-900">
                                        <div className="px-4 py-3 border-b border-surface-200 dark:border-surface-700">
                                            <p className="text-xs text-surface-400 uppercase tracking-wider font-semibold">Signed in as</p>
                                            <div className="flex items-center gap-2 mt-0.5">
                                                <p className="text-sm font-semibold text-surface-900 truncate dark:text-surface-50">{userName || "User"}</p>
                                                {isPro && (
                                                    <span className="inline-flex items-center px-1.5 py-0.5 rounded-md text-[10px] font-bold text-white leading-none bg-warning-500">
                                                        PRO
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                        <button onClick={handleLogout}
                                            className="w-full flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-error-600 hover:bg-error-50 transition-colors dark:text-error-400 dark:hover:bg-error-900/20">
                                            <LogOut className="h-4 w-4" />
                                            Sign out
                                        </button>
                                    </div>
                                )}
                            </div>
                        ) : (
                            <Link href="/login"
                                className="px-4 py-2 text-sm font-semibold text-white rounded-lg transition-colors bg-primary-600 hover:bg-primary-700 shadow-sm">
                                Sign in
                            </Link>
                        )}
                        <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                            className="sm:hidden p-2 rounded-lg text-surface-500 hover:bg-surface-100 transition-colors dark:hover:bg-surface-800"
                            aria-label="Toggle menu">
                            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
                        </button>
                    </div>
                </div>
            </div>

            {/* Mobile menu */}
            {mobileMenuOpen && (
                <div className="sm:hidden border-t border-surface-200 bg-white dark:border-surface-800 dark:bg-surface-900">
                    <div className="px-4 py-3 space-y-1">
                        {navigation.map((item) => (
                            <Link key={item.name} href={item.href}
                                onClick={() => setMobileMenuOpen(false)}
                                className={cn(
                                    "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                                    pathname === item.href
                                        ? "bg-primary-50 text-primary-700 dark:bg-primary-900/20 dark:text-primary-300"
                                        : "text-surface-600 hover:bg-surface-100 hover:text-primary-600 dark:text-surface-400 dark:hover:bg-surface-800"
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
