'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Plus, Edit, Trash2, Search, Package, Loader2, AlertCircle } from 'lucide-react';
import { VendorLayout } from '@/components/vendor-layout';
import { useVendorServices, useDeleteService } from '@/lib/hooks/use-vendor-services';
import { cn, formatCurrency } from '@/lib/utils';

function Skeleton({ className = '' }: { className?: string }) {
    return <div className={`animate-pulse rounded bg-surface-200 dark:bg-surface-700 ${className}`} />;
}

function DeleteConfirmDialog({ name, onConfirm, onCancel, loading }: { name: string; onConfirm: () => void; onCancel: () => void; loading: boolean }) {
    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
            <div className="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl dark:bg-surface-900">
                <h3 className="text-lg font-semibold text-surface-900 dark:text-surface-50">Delete Service</h3>
                <p className="mt-2 text-sm text-surface-500">Are you sure you want to delete <strong>{name}</strong>? This cannot be undone.</p>
                <div className="mt-5 flex justify-end gap-3">
                    <button onClick={onCancel} className="rounded-lg border border-surface-300 px-4 py-2 text-sm hover:bg-surface-50">Cancel</button>
                    <button onClick={onConfirm} disabled={loading} className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm text-white hover:bg-red-700 disabled:opacity-50">
                        {loading && <Loader2 className="h-4 w-4 animate-spin" />} Delete
                    </button>
                </div>
            </div>
        </div>
    );
}

export default function ServicesPage() {
    const [search, setSearch] = useState('');
    const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);
    const { data, isLoading, isError } = useVendorServices({ search: search || undefined });
    const deleteService = useDeleteService();

    const services = data?.data ?? [];

    const handleDelete = async () => {
        if (!deleteTarget) return;
        await deleteService.mutateAsync(deleteTarget.id);
        setDeleteTarget(null);
    };

    return (
        <VendorLayout>
            <div className="space-y-6">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-50">Services</h1>
                        <p className="mt-1 text-surface-500">Manage your service offerings</p>
                    </div>
                    <Link href="/services/new" className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm text-white hover:bg-primary-700">
                        <Plus className="h-4 w-4" /> Add Service
                    </Link>
                </div>

                {/* Search */}
                <div className="relative max-w-sm">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-surface-400" />
                    <input
                        type="text"
                        placeholder="Search services…"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="w-full rounded-lg border border-surface-300 pl-10 pr-4 py-2 text-sm focus:border-primary-500 focus:outline-none dark:border-surface-700 dark:bg-surface-800"
                    />
                </div>

                {isError && (
                    <div className="flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 p-4">
                        <AlertCircle className="h-5 w-5 text-red-500" />
                        <p className="text-sm text-red-700">Failed to load services.</p>
                    </div>
                )}

                <div className="rounded-xl border border-surface-200 bg-white dark:border-surface-800 dark:bg-surface-900">
                    {isLoading ? (
                        <div className="divide-y divide-surface-100 dark:divide-surface-800">
                            {[...Array(5)].map((_, i) => (
                                <div key={i} className="flex items-center gap-4 px-6 py-4">
                                    <Skeleton className="h-4 w-40" />
                                    <Skeleton className="h-4 w-20" />
                                    <Skeleton className="h-6 w-16 rounded-full" />
                                    <Skeleton className="ml-auto h-4 w-24" />
                                </div>
                            ))}
                        </div>
                    ) : services.length === 0 ? (
                        <div className="flex flex-col items-center py-16">
                            <Package className="h-12 w-12 text-surface-300" />
                            <p className="mt-4 text-surface-500">No services yet</p>
                            <Link href="/services/new" className="mt-3 flex items-center gap-1 text-sm text-primary-600 hover:underline">
                                <Plus className="h-4 w-4" /> Add your first service
                            </Link>
                        </div>
                    ) : (
                        <table className="w-full">
                            <thead className="border-b border-surface-200 bg-surface-50 dark:border-surface-800 dark:bg-surface-900/50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase text-surface-500">Name</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase text-surface-500">Status</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase text-surface-500">Capacity</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase text-surface-500">Price Range</th>
                                    <th className="px-6 py-3 text-right text-xs font-medium uppercase text-surface-500">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-surface-100 dark:divide-surface-800">
                                {services.map((s) => (
                                    <tr key={s.id} className="hover:bg-surface-50 dark:hover:bg-surface-900/50">
                                        <td className="px-6 py-4">
                                            <p className="font-medium text-surface-900 dark:text-surface-50">{s.name}</p>
                                            {s.description && <p className="text-xs text-surface-500 line-clamp-1">{s.description}</p>}
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className={cn('rounded-full px-2.5 py-0.5 text-xs font-medium', s.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600')}>
                                                {s.is_active ? 'Active' : 'Inactive'}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-sm text-surface-600">{s.capacity ? `${s.capacity} guests` : '—'}</td>
                                        <td className="px-6 py-4 text-sm text-surface-600">
                                            {s.price_min != null && s.price_max != null
                                                ? `${formatCurrency(s.price_min)} – ${formatCurrency(s.price_max)}`
                                                : s.price_min != null ? `From ${formatCurrency(s.price_min)}` : '—'}
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex items-center justify-end gap-2">
                                                <Link href={`/services/${s.id}/edit`} className="rounded-lg p-1.5 text-surface-500 hover:bg-surface-100 hover:text-surface-700 dark:hover:bg-surface-800">
                                                    <Edit className="h-4 w-4" />
                                                </Link>
                                                <button
                                                    onClick={() => setDeleteTarget({ id: s.id, name: s.name })}
                                                    className="rounded-lg p-1.5 text-surface-500 hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900/30"
                                                >
                                                    <Trash2 className="h-4 w-4" />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            </div>

            {deleteTarget && (
                <DeleteConfirmDialog
                    name={deleteTarget.name}
                    onConfirm={handleDelete}
                    onCancel={() => setDeleteTarget(null)}
                    loading={deleteService.isPending}
                />
            )}
        </VendorLayout>
    );
}
