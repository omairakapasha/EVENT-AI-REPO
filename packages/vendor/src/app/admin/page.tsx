'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
    LayoutDashboard, Users, Briefcase, Package, Shield, ChevronDown,
    CheckCircle, XCircle, Clock, AlertTriangle, Loader2, Search,
    Building2, Mail, Phone, Globe, MapPin, Calendar, Eye, RefreshCw,
    LogOut,
} from 'lucide-react';
import { useAuthStore } from '@/lib/auth-store';
import { api, getApiError } from '@/lib/api';
import { cn } from '@/lib/utils';

interface Stats {
    totalVendors: number;
    activeVendors: number;
    pendingVendors: number;
    totalUsers: number;
    totalServices: number;
    totalBookings: number;
}

interface VendorItem {
    id: string;
    name: string;
    businessType: string | null;
    contactEmail: string;
    phone: string | null;
    website: string | null;
    description: string | null;
    status: string;
    tier: string;
    verified: boolean;
    createdAt: string;
    _count: { users: number; services: number };
}

const statusColors: Record<string, string> = {
    ACTIVE: 'bg-green-100 text-green-800',
    PENDING: 'bg-yellow-100 text-yellow-800',
    SUSPENDED: 'bg-red-100 text-red-800',
    DEACTIVATED: 'bg-gray-100 text-gray-600',
};

const tierColors: Record<string, string> = {
    GOLD: 'bg-amber-100 text-amber-800',
    SILVER: 'bg-slate-100 text-slate-700',
    BRONZE: 'bg-orange-100 text-orange-800',
};

export default function AdminDashboard() {
    const router = useRouter();
    const { isAuthenticated, user, logout } = useAuthStore();
    const [hasMounted, setHasMounted] = useState(false);
    const [stats, setStats] = useState<Stats | null>(null);
    const [vendors, setVendors] = useState<VendorItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [vendorsLoading, setVendorsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [statusFilter, setStatusFilter] = useState<string>('all');
    const [searchQuery, setSearchQuery] = useState('');
    const [updatingVendor, setUpdatingVendor] = useState<string | null>(null);
    const [selectedVendor, setSelectedVendor] = useState<VendorItem | null>(null);
    const [activeTab, setActiveTab] = useState<'overview' | 'vendors' | 'users'>('overview');

    useEffect(() => { setHasMounted(true); }, []);

    useEffect(() => {
        if (hasMounted && !isAuthenticated) {
            router.push('/login');
            return;
        }
        // Only admin and owner roles can access this page
        if (hasMounted && isAuthenticated && user?.role !== 'admin') {
            router.push('/dashboard');
        }
    }, [hasMounted, isAuthenticated, user?.role, router]);

    const fetchStats = useCallback(async () => {
        try {
            const response = await api.get('/admin/stats');
            setStats(response.data?.data || response.data);
        } catch (err: any) {
            setError(getApiError(err));
        } finally {
            setLoading(false);
        }
    }, []);

    const fetchVendors = useCallback(async () => {
        setVendorsLoading(true);
        try {
            const params: any = {};
            if (statusFilter !== 'all') params.status = statusFilter;
            const response = await api.get('/admin/vendors', { params });
            setVendors(response.data?.data || []);
        } catch (err: any) {
            setError(getApiError(err));
        } finally {
            setVendorsLoading(false);
        }
    }, [statusFilter]);

    useEffect(() => {
        if (hasMounted && isAuthenticated) {
            fetchStats();
            fetchVendors();
        }
    }, [hasMounted, isAuthenticated, fetchStats, fetchVendors]);

    const updateVendorStatus = async (vendorId: string, newStatus: string) => {
        setUpdatingVendor(vendorId);
        try {
            await api.patch(`/admin/vendors/${vendorId}/status`, { status: newStatus });
            await fetchVendors();
            await fetchStats();
        } catch (err: any) {
            setError(getApiError(err));
        } finally {
            setUpdatingVendor(null);
        }
    };

    if (!hasMounted || !isAuthenticated) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-gray-50">
                <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
            </div>
        );
    }

    const filteredVendors = vendors.filter(
        (v) => !searchQuery ||
            v.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            v.contactEmail.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
        <div className="flex min-h-screen bg-gray-50">
            {/* Sidebar */}
            <aside className="w-64 bg-gray-900 text-white flex flex-col">
                <div className="p-5 border-b border-gray-800">
                    <div className="flex items-center gap-3">
                        <div className="h-9 w-9 rounded-lg bg-indigo-600 flex items-center justify-center">
                            <Shield className="h-5 w-5" />
                        </div>
                        <div>
                            <h1 className="font-bold text-sm">Admin Panel</h1>
                            <p className="text-xs text-gray-400">Event Orchestrator</p>
                        </div>
                    </div>
                </div>
                <nav className="flex-1 p-3 space-y-1">
                    {[
                        { id: 'overview', icon: LayoutDashboard, label: 'Overview' },
                        { id: 'vendors', icon: Building2, label: 'Vendors' },
                        { id: 'users', icon: Users, label: 'Users' },
                    ].map((item) => (
                        <button
                            key={item.id}
                            onClick={() => setActiveTab(item.id as any)}
                            className={cn(
                                'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                                activeTab === item.id
                                    ? 'bg-indigo-600 text-white'
                                    : 'text-gray-400 hover:text-white hover:bg-gray-800'
                            )}
                        >
                            <item.icon className="h-4 w-4" />
                            {item.label}
                        </button>
                    ))}
                </nav>
                <div className="p-3 border-t border-gray-800">
                    <Link
                        href="/dashboard"
                        className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
                    >
                        <Briefcase className="h-4 w-4" />
                        Vendor Portal
                    </Link>
                    <button
                        onClick={() => { logout(); router.push('/login'); }}
                        className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
                    >
                        <LogOut className="h-4 w-4" />
                        Sign Out
                    </button>
                    <div className="mt-3 px-3 py-2 rounded-lg bg-gray-800">
                        <p className="text-xs text-gray-400">Signed in as</p>
                        <p className="text-sm font-medium truncate">{user?.email}</p>
                        <p className="text-xs text-indigo-400 capitalize">{user?.role}</p>
                    </div>
                </div>
            </aside>

            {/* Main */}
            <main className="flex-1 overflow-auto">
                <div className="p-8">
                    {error && (
                        <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-xl border border-red-200 flex items-center gap-2">
                            <AlertTriangle className="h-5 w-5" />
                            {error}
                            <button onClick={() => setError(null)} className="ml-auto text-red-500 hover:text-red-700">&times;</button>
                        </div>
                    )}

                    {/* ===== OVERVIEW TAB ===== */}
                    {activeTab === 'overview' && (
                        <div className="space-y-6">
                            <div className="flex items-center justify-between">
                                <div>
                                    <h2 className="text-2xl font-bold text-gray-900">Admin Overview</h2>
                                    <p className="text-gray-500 mt-1">System-wide statistics and platform health</p>
                                </div>
                                <button onClick={() => { fetchStats(); fetchVendors(); }} className="px-4 py-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 flex items-center gap-2 text-sm">
                                    <RefreshCw className="h-4 w-4" /> Refresh
                                </button>
                            </div>

                            {loading ? (
                                <div className="flex items-center justify-center py-20"><Loader2 className="h-8 w-8 animate-spin text-indigo-600" /></div>
                            ) : stats && (
                                <>
                                    <div className="grid grid-cols-3 gap-4">
                                        {[
                                            { label: 'Total Vendors', value: stats.totalVendors, icon: Building2, color: 'text-indigo-600', bg: 'bg-indigo-50' },
                                            { label: 'Active Vendors', value: stats.activeVendors, icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-50' },
                                            { label: 'Pending Approval', value: stats.pendingVendors, icon: Clock, color: 'text-yellow-600', bg: 'bg-yellow-50' },
                                            { label: 'Total Users', value: stats.totalUsers, icon: Users, color: 'text-blue-600', bg: 'bg-blue-50' },
                                            { label: 'Total Services', value: stats.totalServices, icon: Package, color: 'text-purple-600', bg: 'bg-purple-50' },
                                            { label: 'Total Bookings', value: stats.totalBookings, icon: Calendar, color: 'text-pink-600', bg: 'bg-pink-50' },
                                        ].map((stat) => (
                                            <div key={stat.label} className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 flex items-center gap-4">
                                                <div className={cn('h-12 w-12 rounded-xl flex items-center justify-center', stat.bg)}>
                                                    <stat.icon className={cn('h-6 w-6', stat.color)} />
                                                </div>
                                                <div>
                                                    <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
                                                    <p className="text-sm text-gray-500">{stat.label}</p>
                                                </div>
                                            </div>
                                        ))}
                                    </div>

                                    {/* Recent Vendors */}
                                    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                                        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
                                            <h3 className="font-semibold text-gray-900">Recent Vendors</h3>
                                            <button onClick={() => setActiveTab('vendors')} className="text-sm text-indigo-600 hover:text-indigo-800">View all →</button>
                                        </div>
                                        <table className="w-full">
                                            <thead className="bg-gray-50">
                                                <tr>
                                                    <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Vendor</th>
                                                    <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Status</th>
                                                    <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Tier</th>
                                                    <th className="text-center px-6 py-3 text-xs font-medium text-gray-500 uppercase">Services</th>
                                                    <th className="text-center px-6 py-3 text-xs font-medium text-gray-500 uppercase">Users</th>
                                                    <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Joined</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-gray-100">
                                                {vendors.slice(0, 5).map((v) => (
                                                    <tr key={v.id} className="hover:bg-gray-50">
                                                        <td className="px-6 py-4">
                                                            <p className="font-medium text-gray-900">{v.name}</p>
                                                            <p className="text-xs text-gray-500">{v.contactEmail}</p>
                                                        </td>
                                                        <td className="px-6 py-4">
                                                            <span className={cn('px-2.5 py-0.5 rounded-full text-xs font-medium', statusColors[v.status] || 'bg-gray-100')}>
                                                                {v.status}
                                                            </span>
                                                        </td>
                                                        <td className="px-6 py-4">
                                                            <span className={cn('px-2.5 py-0.5 rounded-full text-xs font-medium', tierColors[v.tier] || 'bg-gray-100')}>
                                                                {v.tier}
                                                            </span>
                                                        </td>
                                                        <td className="px-6 py-4 text-center text-sm text-gray-600">{v._count.services}</td>
                                                        <td className="px-6 py-4 text-center text-sm text-gray-600">{v._count.users}</td>
                                                        <td className="px-6 py-4 text-sm text-gray-500">{new Date(v.createdAt).toLocaleDateString()}</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </>
                            )}
                        </div>
                    )}

                    {/* ===== VENDORS TAB ===== */}
                    {activeTab === 'vendors' && (
                        <div className="space-y-6">
                            <div>
                                <h2 className="text-2xl font-bold text-gray-900">All Vendors</h2>
                                <p className="text-gray-500 mt-1">Manage vendor accounts and approvals</p>
                            </div>

                            {/* Filters */}
                            <div className="flex gap-3 flex-wrap items-center">
                                <div className="relative flex-1 max-w-sm">
                                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                                    <input
                                        type="text"
                                        placeholder="Search vendors..."
                                        value={searchQuery}
                                        onChange={(e) => setSearchQuery(e.target.value)}
                                        className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-gray-200 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
                                    />
                                </div>
                                {['all', 'ACTIVE', 'PENDING', 'SUSPENDED', 'DEACTIVATED'].map((s) => (
                                    <button
                                        key={s}
                                        onClick={() => setStatusFilter(s)}
                                        className={cn(
                                            'px-4 py-2 rounded-full text-sm font-medium transition-colors',
                                            statusFilter === s
                                                ? 'bg-indigo-600 text-white'
                                                : 'bg-white text-gray-600 hover:bg-gray-100 border border-gray-200'
                                        )}
                                    >
                                        {s === 'all' ? 'All' : s}
                                    </button>
                                ))}
                            </div>

                            {/* Vendor Table */}
                            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                                {vendorsLoading ? (
                                    <div className="flex items-center justify-center py-20"><Loader2 className="h-8 w-8 animate-spin text-indigo-600" /></div>
                                ) : (
                                    <table className="w-full">
                                        <thead className="bg-gray-50 border-b border-gray-200">
                                            <tr>
                                                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Vendor</th>
                                                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Type</th>
                                                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Contact</th>
                                                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Status</th>
                                                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Tier</th>
                                                <th className="text-center px-6 py-3 text-xs font-medium text-gray-500 uppercase">Services</th>
                                                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-gray-100">
                                            {filteredVendors.map((v) => (
                                                <tr key={v.id} className="hover:bg-gray-50">
                                                    <td className="px-6 py-4">
                                                        <button onClick={() => setSelectedVendor(selectedVendor?.id === v.id ? null : v)} className="text-left">
                                                            <p className="font-medium text-gray-900 hover:text-indigo-600">{v.name}</p>
                                                            <p className="text-xs text-gray-500">{v.contactEmail}</p>
                                                        </button>
                                                    </td>
                                                    <td className="px-6 py-4 text-sm text-gray-600">{v.businessType || '—'}</td>
                                                    <td className="px-6 py-4">
                                                        <div className="text-sm">
                                                            {v.phone && <p className="text-gray-600 flex items-center gap-1"><Phone className="h-3 w-3" />{v.phone}</p>}
                                                            {v.website && <p className="text-gray-500 flex items-center gap-1 text-xs"><Globe className="h-3 w-3" />{v.website.replace('https://', '')}</p>}
                                                        </div>
                                                    </td>
                                                    <td className="px-6 py-4">
                                                        <span className={cn('px-2.5 py-0.5 rounded-full text-xs font-medium', statusColors[v.status])}>
                                                            {v.status}
                                                        </span>
                                                    </td>
                                                    <td className="px-6 py-4">
                                                        <span className={cn('px-2.5 py-0.5 rounded-full text-xs font-medium', tierColors[v.tier])}>
                                                            {v.tier}
                                                        </span>
                                                    </td>
                                                    <td className="px-6 py-4 text-center text-sm text-gray-600">{v._count.services}</td>
                                                    <td className="px-6 py-4">
                                                        <div className="flex gap-1">
                                                            {v.status === 'PENDING' && (
                                                                <button
                                                                    onClick={() => updateVendorStatus(v.id, 'ACTIVE')}
                                                                    disabled={updatingVendor === v.id}
                                                                    className="px-3 py-1.5 bg-green-600 text-white rounded-lg text-xs font-medium hover:bg-green-700 disabled:opacity-50"
                                                                >
                                                                    {updatingVendor === v.id ? <Loader2 className="h-3 w-3 animate-spin" /> : 'Approve'}
                                                                </button>
                                                            )}
                                                            {v.status === 'ACTIVE' && (
                                                                <button
                                                                    onClick={() => updateVendorStatus(v.id, 'SUSPENDED')}
                                                                    disabled={updatingVendor === v.id}
                                                                    className="px-3 py-1.5 bg-red-50 text-red-700 rounded-lg text-xs font-medium hover:bg-red-100 disabled:opacity-50"
                                                                >
                                                                    Suspend
                                                                </button>
                                                            )}
                                                            {v.status === 'SUSPENDED' && (
                                                                <button
                                                                    onClick={() => updateVendorStatus(v.id, 'ACTIVE')}
                                                                    disabled={updatingVendor === v.id}
                                                                    className="px-3 py-1.5 bg-green-50 text-green-700 rounded-lg text-xs font-medium hover:bg-green-100 disabled:opacity-50"
                                                                >
                                                                    Reactivate
                                                                </button>
                                                            )}
                                                        </div>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                )}
                            </div>

                            {/* Vendor Detail Panel */}
                            {selectedVendor && (
                                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                                    <div className="flex items-start justify-between mb-4">
                                        <div>
                                            <h3 className="text-lg font-bold text-gray-900">{selectedVendor.name}</h3>
                                            <p className="text-sm text-gray-500">{selectedVendor.businessType}</p>
                                        </div>
                                        <button onClick={() => setSelectedVendor(null)} className="text-gray-400 hover:text-gray-600">&times;</button>
                                    </div>
                                    <div className="grid grid-cols-2 gap-4 text-sm">
                                        <div>
                                            <p className="text-gray-500 mb-1">Contact Email</p>
                                            <p className="text-gray-900 flex items-center gap-1"><Mail className="h-4 w-4 text-gray-400" />{selectedVendor.contactEmail}</p>
                                        </div>
                                        <div>
                                            <p className="text-gray-500 mb-1">Phone</p>
                                            <p className="text-gray-900 flex items-center gap-1"><Phone className="h-4 w-4 text-gray-400" />{selectedVendor.phone || 'Not set'}</p>
                                        </div>
                                        <div>
                                            <p className="text-gray-500 mb-1">Website</p>
                                            <p className="text-gray-900 flex items-center gap-1"><Globe className="h-4 w-4 text-gray-400" />{selectedVendor.website || 'Not set'}</p>
                                        </div>
                                        <div>
                                            <p className="text-gray-500 mb-1">Verified</p>
                                            <p className="text-gray-900">{selectedVendor.verified ? '✅ Yes' : '❌ No'}</p>
                                        </div>
                                        <div>
                                            <p className="text-gray-500 mb-1">Users</p>
                                            <p className="text-gray-900 font-medium">{selectedVendor._count.users}</p>
                                        </div>
                                        <div>
                                            <p className="text-gray-500 mb-1">Services</p>
                                            <p className="text-gray-900 font-medium">{selectedVendor._count.services}</p>
                                        </div>
                                        <div className="col-span-2">
                                            <p className="text-gray-500 mb-1">Description</p>
                                            <p className="text-gray-900">{selectedVendor.description || 'No description'}</p>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* ===== USERS TAB ===== */}
                    {activeTab === 'users' && <UsersTab />}
                </div>
            </main>
        </div>
    );
}

// ===== Users Tab (separate component to keep main clean) =====
function UsersTab() {
    const [users, setUsers] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchUsers = async () => {
            try {
                const response = await api.get('/admin/users');
                setUsers(response.data?.data || []);
            } catch (err) {
                console.error('Failed to fetch users');
            } finally {
                setLoading(false);
            }
        };
        fetchUsers();
    }, []);

    const roleColors: Record<string, string> = {
        admin: 'bg-red-100 text-red-800',
        owner: 'bg-indigo-100 text-indigo-800',
        staff: 'bg-blue-100 text-blue-800',
        readonly: 'bg-gray-100 text-gray-600',
    };

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-2xl font-bold text-gray-900">All Users</h2>
                <p className="text-gray-500 mt-1">Platform-wide user accounts</p>
            </div>
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                {loading ? (
                    <div className="flex items-center justify-center py-20"><Loader2 className="h-8 w-8 animate-spin text-indigo-600" /></div>
                ) : (
                    <table className="w-full">
                        <thead className="bg-gray-50 border-b border-gray-200">
                            <tr>
                                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">User</th>
                                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Vendor</th>
                                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Role</th>
                                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Email Verified</th>
                                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Last Login</th>
                                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Joined</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {users.map((u: any) => (
                                <tr key={u.id} className="hover:bg-gray-50">
                                    <td className="px-6 py-4">
                                        <p className="font-medium text-gray-900">{u.firstName} {u.lastName}</p>
                                        <p className="text-xs text-gray-500">{u.email}</p>
                                    </td>
                                    <td className="px-6 py-4">
                                        <p className="text-sm text-gray-900">{u.vendor?.name}</p>
                                        <p className="text-xs text-gray-500">{u.vendor?.status}</p>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className={cn('px-2.5 py-0.5 rounded-full text-xs font-medium', roleColors[u.role] || 'bg-gray-100')}>
                                            {u.role}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-sm">
                                        {u.emailVerified ? <CheckCircle className="h-4 w-4 text-green-500" /> : <XCircle className="h-4 w-4 text-red-400" />}
                                    </td>
                                    <td className="px-6 py-4 text-sm text-gray-500">
                                        {u.lastLoginAt ? new Date(u.lastLoginAt).toLocaleDateString() : 'Never'}
                                    </td>
                                    <td className="px-6 py-4 text-sm text-gray-500">
                                        {new Date(u.createdAt).toLocaleDateString()}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
}
