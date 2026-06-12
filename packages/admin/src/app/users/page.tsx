"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getUsers, grantPro, revokePro } from "@/lib/api";
import {
    Loader2, Search, ChevronLeft, ChevronRight, Users as UsersIcon,
    Sparkles, X, ShieldOff,
} from "lucide-react";
import { cn } from "@repo/ui/lib/utils";
import { useState, useEffect } from "react";
import toast from "react-hot-toast";

export default function UsersPage() {
    const queryClient = useQueryClient();
    const [page, setPage] = useState(1);
    const [search, setSearch] = useState("");
    const [debouncedSearch, setDebouncedSearch] = useState("");
    const [role, setRole] = useState<string>("");
    const [actionUserId, setActionUserId] = useState<string | null>(null);
    const PAGE_SIZE = 20;

    useEffect(() => {
        const timer = setTimeout(() => {
            setDebouncedSearch(search);
            setPage(1);
        }, 300);
        return () => clearTimeout(timer);
    }, [search]);

    const { data: response, isLoading } = useQuery({
        queryKey: ["users", { page, limit: PAGE_SIZE, role: role || undefined, q: debouncedSearch || undefined }],
        queryFn: () => getUsers({
            page,
            limit: PAGE_SIZE,
            role: role || undefined,
            q: debouncedSearch || undefined,
        }),
    });

    const grantMutation = useMutation({
        mutationFn: (userId: string) => grantPro(userId),
        onSuccess: (_, userId) => {
            toast.success("Pro granted");
            queryClient.invalidateQueries({ queryKey: ["users"] });
            setActionUserId(null);
        },
        onError: () => {
            toast.error("Failed to grant Pro");
            setActionUserId(null);
        },
    });

    const revokeMutation = useMutation({
        mutationFn: (userId: string) => revokePro(userId),
        onSuccess: () => {
            toast.success("Pro revoked");
            queryClient.invalidateQueries({ queryKey: ["users"] });
            setActionUserId(null);
        },
        onError: () => {
            toast.error("Failed to revoke Pro");
            setActionUserId(null);
        },
    });

    const users = response?.data || response || [];
    const meta = response?.meta || {};
    const totalPages = meta.pages || 1;

    if (isLoading) {
        return (
            <div className="space-y-6">
                <div className="h-8 w-56 animate-pulse rounded-xl bg-gray-200" />
                <div className="rounded-2xl bg-white border border-gray-100 overflow-hidden">
                    {[...Array(6)].map((_, i) => (
                        <div key={i} className="flex items-center gap-4 px-6 py-4 border-b border-gray-50">
                            <div className="flex-1 space-y-2">
                                <div className="h-4 w-40 animate-pulse rounded bg-gray-200" />
                                <div className="h-3 w-24 animate-pulse rounded bg-gray-200" />
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">User Management</h1>
                    <p className="mt-1 text-sm text-gray-500">{meta.total || users.length} users registered</p>
                </div>
                <div className="flex items-center gap-3">
                    <select
                        value={role}
                        onChange={(e) => { setRole(e.target.value); setPage(1); }}
                        className="px-4 py-2 text-sm rounded-xl border border-gray-200 bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-300"
                    >
                        <option value="">All Roles</option>
                        <option value="user">User</option>
                        <option value="vendor">Vendor</option>
                        <option value="admin">Admin</option>
                    </select>
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                        <input
                            type="text"
                            placeholder="Search users..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="pl-9 pr-4 py-2 text-sm rounded-xl border border-gray-200 bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-300 w-56"
                        />
                    </div>
                </div>
            </div>

            {/* Table */}
            <div className="rounded-2xl bg-white border border-gray-100 shadow-sm overflow-hidden">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="bg-gray-50/80 border-b border-gray-100">
                            <th className="px-6 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Name</th>
                            <th className="px-6 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Email</th>
                            <th className="px-6 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Role</th>
                            <th className="px-6 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Plan</th>
                            <th className="px-6 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Vendor</th>
                            <th className="px-6 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Verified</th>
                            <th className="px-6 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Last Login</th>
                            <th className="px-6 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                        {users.map((user: any) => {
                            const isPro = user.subscription_status === "pro";
                            const isActing = actionUserId === user.id && (grantMutation.isPending || revokeMutation.isPending);

                            return (
                                <tr key={user.id} className="hover:bg-gray-50/50 transition-colors">
                                    <td className="px-6 py-4">
                                        <span className="font-medium text-gray-900">
                                            {user.first_name || user.firstName} {user.last_name || user.lastName}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-gray-500">{user.email}</td>
                                    <td className="px-6 py-4">
                                        <span className="capitalize text-gray-700 font-medium">{user.role}</span>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className={cn(
                                            "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold",
                                            isPro
                                                ? "bg-violet-50 text-violet-700"
                                                : "bg-gray-100 text-gray-500"
                                        )}>
                                            {isPro && <Sparkles className="h-3 w-3" />}
                                            {isPro ? "Pro" : "Free"}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-2">
                                            <span className="text-gray-700">{user.vendor?.business_name || user.vendor?.name || "—"}</span>
                                            {user.vendor?.status && (
                                                <span className={cn(
                                                    "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold",
                                                    user.vendor.status === "ACTIVE"
                                                        ? "bg-emerald-50 text-emerald-700"
                                                        : "bg-amber-50 text-amber-700"
                                                )}>
                                                    {user.vendor.status}
                                                </span>
                                            )}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className={cn(
                                            "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold",
                                            user.email_verified || user.emailVerified
                                                ? "bg-emerald-50 text-emerald-700"
                                                : "bg-red-50 text-red-700"
                                        )}>
                                            {user.email_verified || user.emailVerified ? "Verified" : "Unverified"}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-sm text-gray-500">
                                        {user.last_login_at || user.lastLoginAt
                                            ? new Date(user.last_login_at || user.lastLoginAt).toLocaleDateString()
                                            : "Never"}
                                    </td>
                                    <td className="px-6 py-4">
                                        {isPro ? (
                                            <button
                                                onClick={() => {
                                                    setActionUserId(user.id);
                                                    revokeMutation.mutate(user.id);
                                                }}
                                                disabled={isActing}
                                                title="Revoke Pro"
                                                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium text-red-600 hover:bg-red-50 disabled:opacity-40 transition-colors"
                                            >
                                                {isActing
                                                    ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                                    : <ShieldOff className="h-3.5 w-3.5" />
                                                }
                                                Revoke Pro
                                            </button>
                                        ) : (
                                            <button
                                                onClick={() => {
                                                    setActionUserId(user.id);
                                                    grantMutation.mutate(user.id);
                                                }}
                                                disabled={isActing}
                                                title="Grant Pro"
                                                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium text-violet-600 hover:bg-violet-50 disabled:opacity-40 transition-colors"
                                            >
                                                {isActing
                                                    ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                                    : <Sparkles className="h-3.5 w-3.5" />
                                                }
                                                Grant Pro
                                            </button>
                                        )}
                                    </td>
                                </tr>
                            );
                        })}
                        {users.length === 0 && (
                            <tr>
                                <td colSpan={8} className="px-6 py-16 text-center">
                                    <UsersIcon className="h-10 w-10 text-gray-200 mx-auto mb-3" />
                                    <p className="text-sm text-gray-400">No users found</p>
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>

                {totalPages > 1 && (
                    <div className="flex items-center justify-between px-6 py-3.5 border-t border-gray-100 bg-gray-50/50">
                        <span className="text-xs text-gray-500">
                            Page {page} of {totalPages} · {meta.total || users.length} users
                        </span>
                        <div className="flex gap-1.5">
                            <button
                                onClick={() => setPage((p) => Math.max(1, p - 1))}
                                disabled={page === 1}
                                className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-gray-200 text-xs font-medium text-gray-600 hover:bg-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                            >
                                <ChevronLeft className="h-3.5 w-3.5" /> Prev
                            </button>
                            <button
                                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                                disabled={page === totalPages}
                                className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-gray-200 text-xs font-medium text-gray-600 hover:bg-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                            >
                                Next <ChevronRight className="h-3.5 w-3.5" />
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
