'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { User, Mail, Phone, Lock, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { api } from '@/lib/api';
import toast from 'react-hot-toast';

interface UserData {
    firstName: string;
    lastName: string;
    email: string;
    phone: string;
}

export default function ProfilePage() {
    const router = useRouter();
    const [user, setUser] = useState<UserData>({ firstName: '', lastName: '', email: '', phone: '' });
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [editing, setEditing] = useState(false);
    const [passwordForm, setPasswordForm] = useState({ currentPassword: '', newPassword: '', confirmPassword: '' });
    const [changingPassword, setChangingPassword] = useState(false);
    const [showPasswordSection, setShowPasswordSection] = useState(false);

    useEffect(() => {
        // Fetch user data from API (httpOnly cookies handle auth)
        api.get('/users/me')
            .then((res) => {
                const data = res.data?.data || res.data;
                if (data) {
                    setUser({
                        firstName: data.first_name || data.firstName || '',
                        lastName: data.last_name || data.lastName || '',
                        email: data.email || '',
                        phone: data.phone || '',
                    });
                }
            })
            .catch(() => {
                router.push('/login');
            })
            .finally(() => setLoading(false));
    }, [router]);

    const handleSave = async () => {
        if (!user.firstName.trim()) {
            toast.error('First name is required');
            return;
        }

        setSaving(true);
        try {
            await api.put('/users/me', {
                firstName: user.firstName,
                lastName: user.lastName,
                phone: user.phone,
            });
            toast.success('Profile updated!');
            setEditing(false);
        } catch (err: any) {
            toast.error(err.response?.data?.message || 'Failed to update profile');
        } finally {
            setSaving(false);
        }
    };

    const handlePasswordChange = async () => {
        if (!passwordForm.currentPassword || !passwordForm.newPassword) {
            toast.error('Please fill in all password fields');
            return;
        }
        if (passwordForm.newPassword.length < 8) {
            toast.error('New password must be at least 8 characters');
            return;
        }
        if (passwordForm.newPassword !== passwordForm.confirmPassword) {
            toast.error('New passwords do not match');
            return;
        }

        setChangingPassword(true);
        try {
            await api.patch('/users/me/password', {
                currentPassword: passwordForm.currentPassword,
                newPassword: passwordForm.newPassword,
            });
            toast.success('Password changed successfully!');
            setShowPasswordSection(false);
            setPasswordForm({ currentPassword: '', newPassword: '', confirmPassword: '' });
        } catch (err: any) {
            toast.error(err.response?.data?.message || 'Failed to change password');
        } finally {
            setChangingPassword(false);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 py-8">
            <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="bg-white shadow rounded-lg overflow-hidden">
                    {/* Header */}
                    <div className="bg-blue-600 px-6 py-4">
                        <div className="flex items-center space-x-4">
                            <div className="h-16 w-16 rounded-full bg-white flex items-center justify-center">
                                <User className="h-8 w-8 text-blue-600" />
                            </div>
                            <div>
                                <h1 className="text-2xl font-bold text-white">
                                    {user.firstName} {user.lastName}
                                </h1>
                                <p className="text-blue-100">{user.email}</p>
                            </div>
                        </div>
                    </div>

                    {/* Profile Info */}
                    <div className="p-6 space-y-6">
                        <div className="flex items-center justify-between">
                            <h2 className="text-lg font-semibold text-gray-900">Profile Information</h2>
                            {!editing && (
                                <button
                                    onClick={() => setEditing(true)}
                                    className="text-sm text-blue-600 hover:text-blue-700"
                                >
                                    Edit Profile
                                </button>
                            )}
                        </div>

                        {editing ? (
                            <div className="space-y-4">
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700">First Name</label>
                                        <input
                                            type="text"
                                            value={user.firstName}
                                            onChange={(e) => setUser({ ...user, firstName: e.target.value })}
                                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700">Last Name</label>
                                        <input
                                            type="text"
                                            value={user.lastName}
                                            onChange={(e) => setUser({ ...user, lastName: e.target.value })}
                                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                                        />
                                    </div>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700">Phone</label>
                                    <input
                                        type="tel"
                                        value={user.phone}
                                        onChange={(e) => setUser({ ...user, phone: e.target.value })}
                                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                                    />
                                </div>
                                <div className="flex space-x-3">
                                    <button
                                        onClick={handleSave}
                                        disabled={saving}
                                        className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
                                    >
                                        {saving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                                        Save Changes
                                    </button>
                                    <button
                                        onClick={() => setEditing(false)}
                                        className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                                    >
                                        Cancel
                                    </button>
                                </div>
                            </div>
                        ) : (
                            <div className="space-y-4">
                                <div className="flex items-center space-x-3">
                                    <User className="h-5 w-5 text-gray-400" />
                                    <div>
                                        <p className="text-sm text-gray-500">Full Name</p>
                                        <p className="text-sm font-medium text-gray-900">
                                            {user.firstName} {user.lastName}
                                        </p>
                                    </div>
                                </div>
                                <div className="flex items-center space-x-3">
                                    <Mail className="h-5 w-5 text-gray-400" />
                                    <div>
                                        <p className="text-sm text-gray-500">Email</p>
                                        <p className="text-sm font-medium text-gray-900">{user.email}</p>
                                    </div>
                                </div>
                                <div className="flex items-center space-x-3">
                                    <Phone className="h-5 w-5 text-gray-400" />
                                    <div>
                                        <p className="text-sm text-gray-500">Phone</p>
                                        <p className="text-sm font-medium text-gray-900">{user.phone || 'Not set'}</p>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Password Section */}
                        <div className="border-t pt-6">
                            <div className="flex items-center justify-between">
                                <h2 className="text-lg font-semibold text-gray-900">Password</h2>
                                {!showPasswordSection && (
                                    <button
                                        onClick={() => setShowPasswordSection(true)}
                                        className="text-sm text-blue-600 hover:text-blue-700 flex items-center"
                                    >
                                        <Lock className="h-4 w-4 mr-1" />
                                        Change Password
                                    </button>
                                )}
                            </div>

                            {showPasswordSection && (
                                <div className="mt-4 space-y-4">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700">Current Password</label>
                                        <input
                                            type="password"
                                            value={passwordForm.currentPassword}
                                            onChange={(e) => setPasswordForm({ ...passwordForm, currentPassword: e.target.value })}
                                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700">New Password</label>
                                        <input
                                            type="password"
                                            value={passwordForm.newPassword}
                                            onChange={(e) => setPasswordForm({ ...passwordForm, newPassword: e.target.value })}
                                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700">Confirm New Password</label>
                                        <input
                                            type="password"
                                            value={passwordForm.confirmPassword}
                                            onChange={(e) => setPasswordForm({ ...passwordForm, confirmPassword: e.target.value })}
                                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                                        />
                                    </div>
                                    <div className="flex space-x-3">
                                        <button
                                            onClick={handlePasswordChange}
                                            disabled={changingPassword}
                                            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
                                        >
                                            {changingPassword ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                                            Change Password
                                        </button>
                                        <button
                                            onClick={() => {
                                                setShowPasswordSection(false);
                                                setPasswordForm({ currentPassword: '', newPassword: '', confirmPassword: '' });
                                            }}
                                            className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                                        >
                                            Cancel
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
