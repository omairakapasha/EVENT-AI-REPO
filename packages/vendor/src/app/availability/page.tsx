'use client';

import { useState } from 'react';
import { ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';
import { VendorLayout } from '@/components/vendor-layout';
import { useVendorAvailability, useUpsertAvailability, type AvailabilityRecord } from '@/lib/hooks/use-vendor-availability';
import { cn } from '@/lib/utils';

const STATUS_COLORS: Record<string, string> = {
    available: 'bg-green-100 text-green-700 border-green-200',
    blocked: 'bg-red-100 text-red-700 border-red-200',
    tentative: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    booked: 'bg-blue-100 text-blue-700 border-blue-200',
    locked: 'bg-purple-100 text-purple-700 border-purple-200',
};

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

function getMonthDates(year: number, month: number) {
    const first = new Date(year, month, 1);
    const last = new Date(year, month + 1, 0);
    const startPad = first.getDay();
    const dates: (Date | null)[] = Array(startPad).fill(null);
    for (let d = 1; d <= last.getDate(); d++) dates.push(new Date(year, month, d));
    return dates;
}

function toISO(d: Date) {
    return d.toISOString().split('T')[0];
}

type AvailStatus = 'available' | 'blocked' | 'tentative';

function DayModal({ date, current, onSelect, onClose }: {
    date: Date;
    current?: AvailabilityRecord;
    onSelect: (status: AvailStatus) => void;
    onClose: () => void;
}) {
    const isBooked = current?.status === 'booked';
    const options: { label: string; value: AvailStatus; color: string }[] = [
        { label: 'Available', value: 'available', color: 'bg-green-100 text-green-700 hover:bg-green-200' },
        { label: 'Blocked', value: 'blocked', color: 'bg-red-100 text-red-700 hover:bg-red-200' },
        { label: 'Tentative', value: 'tentative', color: 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200' },
    ];

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
            <div className="w-full max-w-xs rounded-xl bg-white p-6 shadow-xl dark:bg-surface-900">
                <h3 className="text-lg font-semibold text-surface-900 dark:text-surface-50">
                    {date.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}
                </h3>
                {current && (
                    <p className="mt-1 text-sm text-surface-500">Current: <span className="font-medium capitalize">{current.status}</span></p>
                )}
                <div className="mt-4 space-y-2">
                    {isBooked ? (
                        <p className="rounded-lg bg-blue-50 px-4 py-3 text-sm text-blue-700">This date is booked and cannot be changed.</p>
                    ) : (
                        options.map((opt) => (
                            <button
                                key={opt.value}
                                onClick={() => onSelect(opt.value)}
                                className={cn('w-full rounded-lg px-4 py-2.5 text-sm font-medium transition-colors', opt.color)}
                            >
                                {opt.label}
                            </button>
                        ))
                    )}
                </div>
                <button onClick={onClose} className="mt-4 w-full rounded-lg border border-surface-300 py-2 text-sm hover:bg-surface-50">Close</button>
            </div>
        </div>
    );
}

export default function AvailabilityPage() {
    const today = new Date();
    const [year, setYear] = useState(today.getFullYear());
    const [month, setMonth] = useState(today.getMonth());
    const [selectedDate, setSelectedDate] = useState<Date | null>(null);

    const startDate = toISO(new Date(year, month, 1));
    const endDate = toISO(new Date(year, month + 1, 0));

    const { data: records = [], isLoading } = useVendorAvailability(startDate, endDate);
    const upsert = useUpsertAvailability();

    const recordMap = new Map(records.map((r) => [r.date, r]));
    const dates = getMonthDates(year, month);

    const prevMonth = () => { if (month === 0) { setYear(y => y - 1); setMonth(11); } else setMonth(m => m - 1); };
    const nextMonth = () => { if (month === 11) { setYear(y => y + 1); setMonth(0); } else setMonth(m => m + 1); };

    const handleSelect = async (status: AvailStatus) => {
        if (!selectedDate) return;
        await upsert.mutateAsync({ date: toISO(selectedDate), status });
        setSelectedDate(null);
    };

    const monthLabel = new Date(year, month).toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

    return (
        <VendorLayout>
            <div className="space-y-6">
                <div>
                    <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-50">Availability</h1>
                    <p className="mt-1 text-surface-500">Manage your calendar</p>
                </div>

                {/* Legend */}
                <div className="flex flex-wrap gap-3 text-xs">
                    {Object.entries({ available: 'Available', blocked: 'Blocked', tentative: 'Tentative', booked: 'Booked' }).map(([k, v]) => (
                        <span key={k} className={cn('rounded-full border px-3 py-1 font-medium', STATUS_COLORS[k])}>{v}</span>
                    ))}
                </div>

                <div className="rounded-xl border border-surface-200 bg-white p-6 dark:border-surface-800 dark:bg-surface-900">
                    {/* Month nav */}
                    <div className="mb-6 flex items-center justify-between">
                        <button onClick={prevMonth} className="rounded-lg p-2 hover:bg-surface-100 dark:hover:bg-surface-800"><ChevronLeft className="h-5 w-5" /></button>
                        <h2 className="text-lg font-semibold text-surface-900 dark:text-surface-50">{monthLabel}</h2>
                        <button onClick={nextMonth} className="rounded-lg p-2 hover:bg-surface-100 dark:hover:bg-surface-800"><ChevronRight className="h-5 w-5" /></button>
                    </div>

                    {/* Day headers */}
                    <div className="mb-2 grid grid-cols-7 gap-1">
                        {DAYS.map((d) => (
                            <div key={d} className="text-center text-xs font-medium text-surface-500">{d}</div>
                        ))}
                    </div>

                    {/* Calendar grid */}
                    {isLoading ? (
                        <div className="flex justify-center py-12"><Loader2 className="h-8 w-8 animate-spin text-primary-600" /></div>
                    ) : (
                        <div className="grid grid-cols-7 gap-1">
                            {dates.map((date, i) => {
                                if (!date) return <div key={`pad-${i}`} />;
                                const iso = toISO(date);
                                const rec = recordMap.get(iso);
                                const isPast = date < new Date(today.getFullYear(), today.getMonth(), today.getDate());
                                const isToday = iso === toISO(today);
                                return (
                                    <button
                                        key={iso}
                                        onClick={() => !isPast && setSelectedDate(date)}
                                        disabled={isPast}
                                        className={cn(
                                            'relative flex h-12 flex-col items-center justify-center rounded-lg border text-sm transition-colors',
                                            rec ? STATUS_COLORS[rec.status] : 'border-surface-200 hover:bg-surface-50 dark:border-surface-700 dark:hover:bg-surface-800',
                                            isToday && !rec && 'border-primary-400 font-bold',
                                            isPast && 'cursor-not-allowed opacity-40',
                                        )}
                                    >
                                        <span className={cn('font-medium', isToday && 'text-primary-600')}>{date.getDate()}</span>
                                    </button>
                                );
                            })}
                        </div>
                    )}
                </div>
            </div>

            {selectedDate && (
                <DayModal
                    date={selectedDate}
                    current={recordMap.get(toISO(selectedDate))}
                    onSelect={handleSelect}
                    onClose={() => setSelectedDate(null)}
                />
            )}
        </VendorLayout>
    );
}
