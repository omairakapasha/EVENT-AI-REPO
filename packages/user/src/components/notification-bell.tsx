'use client';

import { useState, useRef, useEffect } from 'react';
import { Bell, X, Check, CheckCheck, Clock, AlertCircle, Info, CheckCircle, type LucideIcon } from 'lucide-react';
import { useNotifications } from './notification-provider';

const typeConfig: Record<string, { icon: LucideIcon; color: string; bg: string }> = {
    info: { icon: Info, color: 'text-blue-500', bg: 'bg-blue-50' },
    success: { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-50' },
    warning: { icon: AlertCircle, color: 'text-amber-500', bg: 'bg-amber-50' },
    error: { icon: AlertCircle, color: 'text-red-500', bg: 'bg-red-50' },
};

export function NotificationBell() {
    const { notifications, unreadCount, markAsRead, markAllAsRead, removeNotification } = useNotifications();
    const [open, setOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    // Close dropdown on outside click
    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
                setOpen(false);
            }
        };
        if (open) document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [open]);

    const formatTime = (date: Date) => {
        const now = new Date();
        const diff = Math.floor((now.getTime() - new Date(date).getTime()) / 1000);
        if (diff < 60) return 'Just now';
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
        return new Date(date).toLocaleDateString();
    };

    return (
        <div className="relative" ref={dropdownRef}>
            <button
                onClick={() => setOpen(!open)}
                aria-label={`Notifications${unreadCount > 0 ? `, ${unreadCount} unread` : ''}`}
                className="relative p-2 text-gray-500 hover:text-gray-700 transition-colors rounded-lg hover:bg-gray-100"
            >
                <Bell className="h-5 w-5" />
                {unreadCount > 0 && (
                    <span className="absolute -top-0.5 -right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white">
                        {unreadCount > 9 ? '9+' : unreadCount}
                    </span>
                )}
            </button>

            {open && (
                <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white rounded-xl shadow-xl border border-gray-100 z-50 overflow-hidden">
                    {/* Header */}
                    <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
                        <h3 className="text-sm font-semibold text-gray-900">
                            Notifications {unreadCount > 0 && `(${unreadCount})`}
                        </h3>
                        {unreadCount > 0 && (
                            <button
                                onClick={markAllAsRead}
                                className="text-xs text-indigo-600 hover:text-indigo-700 font-medium flex items-center gap-1"
                            >
                                <CheckCheck className="h-3 w-3" />
                                Mark all read
                            </button>
                        )}
                    </div>

                    {/* Notification List */}
                    <div className="max-h-80 overflow-y-auto">
                        {notifications.length === 0 ? (
                            <div className="py-12 text-center">
                                <Bell className="h-8 w-8 text-gray-200 mx-auto mb-2" />
                                <p className="text-sm text-gray-400">No notifications yet</p>
                            </div>
                        ) : (
                            notifications.slice(0, 20).map((n) => {
                                const config = typeConfig[n.type] || typeConfig.info;
                                const Icon = config.icon;
                                return (
                                    <div
                                        key={n.id}
                                        className={`flex items-start gap-3 px-4 py-3 border-b border-gray-50 hover:bg-gray-50 transition-colors ${!n.is_read ? 'bg-indigo-50/30' : ''
                                            }`}
                                    >
                                        <div className={`mt-0.5 p-1.5 rounded-lg ${config.bg}`}>
                                            <Icon className={`h-3.5 w-3.5 ${config.color}`} />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className={`text-sm ${!n.is_read ? 'font-medium text-gray-900' : 'text-gray-700'}`}>
                                                {n.title}
                                            </p>
                                            <p className="text-xs text-gray-500 mt-0.5 truncate">{n.message}</p>
                                            <p className="text-[10px] text-gray-400 mt-1 flex items-center gap-1">
                                                <Clock className="h-2.5 w-2.5" />
                                                {formatTime(new Date(n.created_at))}
                                            </p>
                                        </div>
                                        <div className="flex items-center gap-1">
                                            {!n.is_read && (
                                                <button
                                                    onClick={() => markAsRead(n.id)}
                                                    className="p-1 text-gray-300 hover:text-indigo-500"
                                                    aria-label="Mark as read"
                                                >
                                                    <Check className="h-3.5 w-3.5" />
                                                </button>
                                            )}
                                            <button
                                                onClick={() => removeNotification(n.id)}
                                                className="p-1 text-gray-300 hover:text-red-500"
                                                aria-label="Dismiss notification"
                                            >
                                                <X className="h-3.5 w-3.5" />
                                            </button>
                                        </div>
                                    </div>
                                );
                            })
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
