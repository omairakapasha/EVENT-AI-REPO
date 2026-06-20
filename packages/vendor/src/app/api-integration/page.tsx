'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
    Key, Copy, Plus, Trash2, Loader2, Shield, Clock,
    AlertTriangle, CheckCircle, Eye, EyeOff,
} from 'lucide-react';
import { useAuthStore } from '@/lib/auth-store';
import { useApiKeys, useCreateApiKey, useRevokeApiKey, type ApiKeyCreated } from '@/lib/hooks/use-vendor-api-keys';
import toast from 'react-hot-toast';

export default function ApiIntegrationPage() {
    const router = useRouter();
    const { isAuthenticated } = useAuthStore();
    const [hasMounted, setHasMounted] = useState(false);

    // Form state
    const [showCreateForm, setShowCreateForm] = useState(false);
    const [newKeyName, setNewKeyName] = useState('');

    // One-time raw key display state
    const [newlyCreatedKey, setNewlyCreatedKey] = useState<ApiKeyCreated | null>(null);
    const [rawKeyVisible, setRawKeyVisible] = useState(false);

    // Revoke confirmation
    const [revokingId, setRevokingId] = useState<string | null>(null);

    const { data: apiKeys = [], isLoading, error } = useApiKeys();
    const createKey = useCreateApiKey();
    const revokeKey = useRevokeApiKey();

    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional
    // client-only mount guard to avoid SSR/hydration mismatch.
    useEffect(() => { setHasMounted(true); }, []);

    useEffect(() => {
        if (hasMounted && !isAuthenticated) {
            router.push('/login');
        }
    }, [hasMounted, isAuthenticated, router]);

    if (!hasMounted || !isAuthenticated) {
        return (
            <div className="flex min-h-screen items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
            </div>
        );
    }

    const handleCreateKey = async () => {
        if (!newKeyName.trim()) return;
        const result = await createKey.mutateAsync({ name: newKeyName.trim() });
        setNewlyCreatedKey(result);
        setRawKeyVisible(true);
        setNewKeyName('');
        setShowCreateForm(false);
    };

    const handleCopyKey = (key: string) => {
        navigator.clipboard.writeText(key);
        toast.success('Copied to clipboard');
    };

    const handleRevoke = async (keyId: string) => {
        await revokeKey.mutateAsync(keyId);
        setRevokingId(null);
    };

    const activeKeys = apiKeys.filter((k) => k.is_active);
    const revokedKeys = apiKeys.filter((k) => !k.is_active);

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">API Integration</h1>
                    <p className="text-gray-500 mt-1">Manage API keys for third-party integrations</p>
                </div>
                {!showCreateForm && (
                    <button
                        onClick={() => setShowCreateForm(true)}
                        className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors flex items-center gap-2"
                    >
                        <Plus className="h-4 w-4" />
                        New API Key
                    </button>
                )}
            </div>

            {/* One-time key reveal banner */}
            {newlyCreatedKey && (
                <div className="bg-amber-50 border border-amber-300 rounded-xl p-5">
                    <div className="flex items-start gap-3 mb-3">
                        <AlertTriangle className="h-5 w-5 text-amber-600 mt-0.5 shrink-0" />
                        <div>
                            <p className="font-semibold text-amber-900">Save your API key now</p>
                            <p className="text-sm text-amber-700 mt-0.5">
                                This key will not be shown again. Copy it and store it securely.
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2 bg-white border border-amber-200 rounded-lg px-4 py-3 font-mono text-sm">
                        <span className="flex-1 truncate text-gray-800">
                            {rawKeyVisible ? newlyCreatedKey.raw_key : '•'.repeat(40)}
                        </span>
                        <button
                            onClick={() => setRawKeyVisible((v) => !v)}
                            className="text-gray-400 hover:text-gray-600 transition-colors"
                            title={rawKeyVisible ? 'Hide key' : 'Show key'}
                        >
                            {rawKeyVisible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </button>
                        <button
                            onClick={() => handleCopyKey(newlyCreatedKey.raw_key)}
                            className="text-gray-400 hover:text-gray-600 transition-colors"
                            title="Copy key"
                        >
                            <Copy className="h-4 w-4" />
                        </button>
                    </div>
                    <button
                        onClick={() => setNewlyCreatedKey(null)}
                        className="mt-3 text-sm text-amber-700 hover:text-amber-900 flex items-center gap-1"
                    >
                        <CheckCircle className="h-4 w-4" />
                        I&apos;ve saved my key — dismiss
                    </button>
                </div>
            )}

            {/* Create key form */}
            {showCreateForm && (
                <div className="bg-blue-50 rounded-xl border border-blue-200 p-6">
                    <h3 className="font-semibold text-gray-900 mb-3">Create New API Key</h3>
                    <div className="flex gap-3">
                        <input
                            type="text"
                            value={newKeyName}
                            onChange={(e) => setNewKeyName(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleCreateKey()}
                            placeholder="Key name (e.g. Production, Staging)"
                            className="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                            autoFocus
                        />
                        <button
                            onClick={() => { setShowCreateForm(false); setNewKeyName(''); }}
                            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={handleCreateKey}
                            disabled={!newKeyName.trim() || createKey.isPending}
                            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 flex items-center gap-2"
                        >
                            {createKey.isPending
                                ? <Loader2 className="h-4 w-4 animate-spin" />
                                : <Key className="h-4 w-4" />}
                            Generate
                        </button>
                    </div>
                </div>
            )}

            {/* Error state */}
            {error && (
                <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm">
                    Failed to load API keys. Please refresh the page.
                </div>
            )}

            {/* Active keys */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
                    <h3 className="font-semibold text-gray-900">Active Keys</h3>
                    <span className="text-xs text-gray-500">{activeKeys.length} / 10</span>
                </div>

                {isLoading ? (
                    <div className="flex items-center justify-center py-16">
                        <Loader2 className="h-7 w-7 animate-spin text-primary-600" />
                    </div>
                ) : activeKeys.length === 0 ? (
                    <div className="text-center py-16">
                        <Key className="mx-auto h-10 w-10 text-gray-300 mb-3" />
                        <p className="text-gray-500 text-sm">No active API keys. Create one to get started.</p>
                    </div>
                ) : (
                    <div className="divide-y divide-gray-100">
                        {activeKeys.map((key) => (
                            <div key={key.id} className="px-6 py-4 flex items-center justify-between gap-4">
                                <div className="min-w-0">
                                    <p className="font-medium text-gray-900">{key.name}</p>
                                    <p className="text-sm text-gray-500 font-mono mt-0.5">
                                        {key.key_prefix}••••••••••••••••••••
                                    </p>
                                    <div className="flex items-center gap-3 mt-1 text-xs text-gray-400">
                                        <span className="flex items-center gap-1">
                                            <Clock className="h-3 w-3" />
                                            Created {new Date(key.created_at).toLocaleDateString()}
                                        </span>
                                        {key.last_used_at && (
                                            <span>Last used {new Date(key.last_used_at).toLocaleDateString()}</span>
                                        )}
                                    </div>
                                </div>
                                <div className="flex items-center gap-2 shrink-0">
                                    <span className="px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800">
                                        Active
                                    </span>
                                    {revokingId === key.id ? (
                                        <div className="flex items-center gap-2">
                                            <span className="text-xs text-red-600">Revoke?</span>
                                            <button
                                                onClick={() => handleRevoke(key.id)}
                                                disabled={revokeKey.isPending}
                                                className="px-2 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
                                            >
                                                {revokeKey.isPending ? '...' : 'Yes'}
                                            </button>
                                            <button
                                                onClick={() => setRevokingId(null)}
                                                className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                                            >
                                                No
                                            </button>
                                        </div>
                                    ) : (
                                        <button
                                            onClick={() => setRevokingId(key.id)}
                                            className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                                            title="Revoke key"
                                        >
                                            <Trash2 className="h-4 w-4" />
                                        </button>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Revoked keys (collapsed) */}
            {revokedKeys.length > 0 && (
                <details className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                    <summary className="px-6 py-4 cursor-pointer text-sm font-medium text-gray-500 hover:text-gray-700 select-none">
                        {revokedKeys.length} revoked key{revokedKeys.length !== 1 ? 's' : ''}
                    </summary>
                    <div className="divide-y divide-gray-100 border-t border-gray-100">
                        {revokedKeys.map((key) => (
                            <div key={key.id} className="px-6 py-3 flex items-center justify-between gap-4 opacity-60">
                                <div>
                                    <p className="font-medium text-gray-700 text-sm">{key.name}</p>
                                    <p className="text-xs text-gray-400 font-mono">{key.key_prefix}••••••••••••••••••••</p>
                                </div>
                                <span className="px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-500">
                                    Revoked
                                </span>
                            </div>
                        ))}
                    </div>
                </details>
            )}

            {/* Documentation */}
            <div className="bg-gradient-to-r from-primary-50 to-blue-50 rounded-xl border border-primary-100 p-6">
                <div className="flex items-center gap-2 mb-2">
                    <Shield className="h-4 w-4 text-primary-600" />
                    <h3 className="font-semibold text-gray-900">Using your API key</h3>
                </div>
                <p className="text-gray-600 text-sm mb-3">
                    Include your key in the{' '}
                    <code className="bg-white px-1.5 py-0.5 rounded text-primary-600 text-xs">Authorization</code>{' '}
                    header as a Bearer token with each request.
                </p>
                <pre className="bg-white rounded-lg border border-primary-100 px-4 py-3 text-xs text-gray-700 overflow-x-auto">
{`curl -H "Authorization: Bearer evai_your_key_here" \\
     ${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000/api/v1'}/vendors/profile/me`}
                </pre>
            </div>
        </div>
    );
}
