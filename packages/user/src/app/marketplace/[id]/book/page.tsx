'use client';

import { useState, Suspense } from 'react';
import { useParams, useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Calendar, Users, FileText, Loader2, CheckCircle } from 'lucide-react';
import { createBooking } from '@/lib/api';
import toast from 'react-hot-toast';

function BookingContent() {
    const params = useParams();
    const searchParams = useSearchParams();
    const router = useRouter();
    const vendorId = params.id as string;
    const serviceId = searchParams.get('serviceId') || '';
    const serviceName = searchParams.get('serviceName') || 'Service';

    const [form, setForm] = useState({
        eventDate: '',
        guestCount: '',
        notes: '',
    });
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(false);
    const [error, setError] = useState('');

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        setForm({ ...form, [e.target.name]: e.target.value });
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        if (!form.eventDate) {
            setError('Please select an event date');
            return;
        }

        const eventDate = new Date(form.eventDate);
        if (eventDate <= new Date()) {
            setError('Event date must be in the future');
            return;
        }

        setLoading(true);
        try {
            await createBooking({
                vendorId,
                serviceId,
                eventDate: form.eventDate,
                guestCount: form.guestCount ? parseInt(form.guestCount) : undefined,
                notes: form.notes || undefined,
            });
            setSuccess(true);
            toast.success('Booking request sent!');
            setTimeout(() => router.push('/bookings'), 2000);
        } catch (err: any) {
            const msg = err.response?.data?.message || err.response?.data?.error || 'Failed to create booking';
            setError(msg);
            toast.error(msg);
        } finally {
            setLoading(false);
        }
    };

    if (success) {
        return (
            <div className="max-w-lg mx-auto px-4 py-16 text-center">
                <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
                    <CheckCircle className="h-8 w-8 text-green-600" />
                </div>
                <h2 className="text-xl font-bold text-gray-900 mb-2">Booking Request Sent!</h2>
                <p className="text-gray-500 mb-6">
                    The vendor will review your request and get back to you shortly.
                </p>
                <p className="text-sm text-gray-400">Redirecting to your bookings...</p>
            </div>
        );
    }

    // Get tomorrow's date for min date attribute
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const minDate = tomorrow.toISOString().split('T')[0];

    return (
        <div className="max-w-lg mx-auto px-4 py-8">
            <Link href={`/marketplace/${vendorId}`} className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-indigo-600 mb-6">
                <ArrowLeft className="h-4 w-4" />
                Back to Vendor
            </Link>

            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8">
                <h1 className="text-xl font-bold text-gray-900 mb-1">Book a Service</h1>
                <p className="text-sm text-gray-500 mb-6">
                    You're booking: <span className="font-medium text-gray-700">{decodeURIComponent(serviceName)}</span>
                </p>

                {error && (
                    <div className="bg-red-50 text-red-600 px-4 py-3 rounded-lg text-sm mb-4">
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-5">
                    <div>
                        <label htmlFor="eventDate" className="block text-sm font-medium text-gray-700 mb-1">
                            <Calendar className="inline h-4 w-4 mr-1" />
                            Event Date *
                        </label>
                        <input
                            id="eventDate"
                            name="eventDate"
                            type="date"
                            required
                            min={minDate}
                            value={form.eventDate}
                            onChange={handleChange}
                            className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                        />
                    </div>

                    <div>
                        <label htmlFor="guestCount" className="block text-sm font-medium text-gray-700 mb-1">
                            <Users className="inline h-4 w-4 mr-1" />
                            Expected Guests
                        </label>
                        <input
                            id="guestCount"
                            name="guestCount"
                            type="number"
                            min="1"
                            max="10000"
                            value={form.guestCount}
                            onChange={handleChange}
                            placeholder="e.g. 150"
                            className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                        />
                    </div>

                    <div>
                        <label htmlFor="notes" className="block text-sm font-medium text-gray-700 mb-1">
                            <FileText className="inline h-4 w-4 mr-1" />
                            Additional Notes
                        </label>
                        <textarea
                            id="notes"
                            name="notes"
                            rows={4}
                            value={form.notes}
                            onChange={handleChange}
                            placeholder="Any special requirements, theme preferences, or questions for the vendor..."
                            className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 resize-none"
                        />
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full bg-indigo-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-indigo-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                        {loading ? (
                            <>
                                <Loader2 className="h-4 w-4 animate-spin" />
                                Sending Request...
                            </>
                        ) : (
                            <>
                                <Calendar className="h-4 w-4" />
                                Confirm Booking
                            </>
                        )}
                    </button>
                </form>
            </div>
        </div>
    );
}

export default function BookingPage() {
    return (
        <Suspense fallback={
            <div className="flex items-center justify-center min-h-[400px]">
                <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
            </div>
        }>
            <BookingContent />
        </Suspense>
    );
}

