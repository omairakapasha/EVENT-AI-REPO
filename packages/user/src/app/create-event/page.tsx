"use client";

import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import {
    Loader2,
    ArrowRight,
    ArrowLeft,
    Lock,
    Sparkles,
    CheckCircle,
} from "lucide-react";
import Link from "next/link";
import { isAxiosError } from "axios";
import { createEvent, getEventTypes, getUserEvents, getSubscriptionStatus, type EventType } from "@/lib/api";
import { useRouter } from "next/navigation";
import { UpgradeModal } from "@/components/upgrade-modal";

const eventSchema = z.object({
    eventType: z.string().min(1, "Event type is required"),
    date: z.string().min(1, "Date is required"),
    attendees: z.number().min(1, "At least 1 attendee required"),
    budget: z.number().min(100, "Minimum budget is 100"),
    city: z.string().min(1, "City is required"),
    country: z.string().min(1, "Country is required"),
    description: z.string().optional(),
});

type EventFormValues = z.infer<typeof eventSchema>;

const PRO_FEATURES = [
    "Unlimited events",
    "AI-powered planning assistant",
    "Priority vendor matching",
    "Bookings confirmed instantly (no deposit hold)",
    "Dedicated support",
];

function UpgradeWall() {
    const [showModal, setShowModal] = useState(false);
    return (
        <>
        <div className="max-w-2xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
            <div className="bg-white shadow rounded-lg overflow-hidden">
                {/* Header band */}
                <div className="bg-gradient-to-r from-indigo-600 to-indigo-700 px-8 py-6 text-white text-center">
                    <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-white/20">
                        <Lock className="h-6 w-6" />
                    </div>
                    <h2 className="text-2xl font-bold">Free plan limit reached</h2>
                    <p className="mt-1 text-indigo-200 text-sm">
                        Your free plan includes 3 events. Upgrade to Pro for unlimited events.
                    </p>
                </div>

                {/* Pro feature list */}
                <div className="px-8 py-6">
                    <p className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
                        What you get with Pro
                    </p>
                    <ul className="space-y-3">
                        {PRO_FEATURES.map((f) => (
                            <li key={f} className="flex items-center gap-3 text-sm text-gray-700">
                                <CheckCircle className="h-4 w-4 shrink-0 text-indigo-500" />
                                {f}
                            </li>
                        ))}
                    </ul>
                </div>

                {/* Actions */}
                <div className="border-t border-gray-100 px-8 py-5 flex flex-col sm:flex-row gap-3">
                    <button
                        onClick={() => setShowModal(true)}
                        className="flex-1 inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 transition-colors"
                    >
                        <Sparkles className="h-4 w-4" />
                        Upgrade to Pro
                    </button>
                    <Link
                        href="/dashboard"
                        className="flex-1 inline-flex items-center justify-center gap-2 rounded-xl border border-gray-200 px-4 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
                    >
                        Back to Dashboard
                    </Link>
                </div>
            </div>
        </div>
        {showModal && <UpgradeModal onClose={() => setShowModal(false)} />}
        </>
    );
}

export default function CreateEventPage() {
    const router = useRouter();
    const [step, setStep] = useState(1);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [limitReached, setLimitReached] = useState(false);
    const [checking, setChecking] = useState(true);
    const [eventTypes, setEventTypes] = useState<EventType[]>([]);

    const form = useForm<EventFormValues>({
        resolver: zodResolver(eventSchema),
        defaultValues: {
            eventType: "",
            attendees: 50,
            budget: 5000,
            city: "",
            country: "",
        },
    });

    // Proactive check: if free plan + already has an event, skip straight to upgrade wall
    useEffect(() => {
        async function checkLimit() {
            try {
                const [sub, eventsRes] = await Promise.all([
                    getSubscriptionStatus(),
                    getUserEvents(),
                ]);
                const isFree = !sub.is_pro_active;
                const eventCount: number = eventsRes?.data?.items?.length
                    ?? eventsRes?.data?.length
                    ?? eventsRes?.items?.length
                    ?? eventsRes?.events?.length
                    ?? 0;
                if (isFree && eventCount >= 3) {
                    setLimitReached(true);
                }
            } catch {
                // If check fails, let the form show — submit will catch the limit
            } finally {
                setChecking(false);
            }
        }
        checkLimit();
    }, []);

    useEffect(() => {
        async function loadEventTypes() {
            try {
                const types = await getEventTypes();
                setEventTypes(types);
            } catch {
                // Select will just show no options; submit will surface an error.
            }
        }
        loadEventTypes();
    }, []);

    const onSubmit = async (data: EventFormValues) => {
        setIsSubmitting(true);
        setError(null);

        try {
            const selectedType = eventTypes.find((t) => t.id === data.eventType);

            const eventData = {
                event_type_id: data.eventType,
                name: `${selectedType?.name ?? "New"} Event`,
                description: data.description || undefined,
                start_date: new Date(data.date).toISOString(),
                city: data.city,
                country: data.country,
                guest_count: data.attendees,
                budget: data.budget,
            };

            const result = await createEvent(eventData);

            if (result?.data?.id) {
                router.push(`/dashboard?eventId=${result.data.id}`);
            } else {
                router.push("/dashboard");
            }
        } catch (err) {
            const data = isAxiosError(err) ? err.response?.data : undefined;
            const code = data?.error?.code ?? data?.code;
            if (isAxiosError(err) && err.response?.status === 403 && code === "SUBSCRIPTION_LIMIT_EXCEEDED") {
                setLimitReached(true);
            } else {
                setError(
                    data?.error?.message
                    ?? data?.message
                    ?? "Failed to create event. Please try again."
                );
            }
        } finally {
            setIsSubmitting(false);
        }
    };

    const nextStep = async () => {
        const fields = step === 1
            ? ["eventType", "date", "attendees"] as const
            : ["budget", "city", "country", "description"] as const;

        const isValid = await form.trigger(fields);
        if (isValid) setStep(step + 1);
    };

    if (checking) {
        return (
            <div className="flex min-h-[60vh] items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-indigo-400" />
            </div>
        );
    }

    if (limitReached) {
        return <UpgradeWall />;
    }

    return (
        <div className="max-w-2xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900">Create New Event</h1>
                <p className="mt-2 text-sm text-gray-600">Let&apos;s plan your perfect event together.</p>
            </div>

            <div className="bg-white shadow rounded-lg p-8">
                {/* Progress Bar */}
                <div className="mb-8">
                    <div className="h-2 bg-gray-200 rounded-full">
                        <div
                            className="h-2 bg-indigo-600 rounded-full transition-all duration-300"
                            style={{ width: `${(step / 2) * 100}%` }}
                        />
                    </div>
                    <div className="flex justify-between mt-2 text-xs text-gray-500">
                        <span>Basic Details</span>
                        <span>Preferences</span>
                    </div>
                </div>

                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                    {/* Error Message */}
                    {error && (
                        <div className="rounded-md bg-red-50 p-4">
                            <p className="text-sm text-red-700">{error}</p>
                        </div>
                    )}

                    {step === 1 && (
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700">Event Type</label>
                                <select
                                    {...form.register("eventType")}
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2 border"
                                >
                                    <option value="">Select type...</option>
                                    {eventTypes.map((type) => (
                                        <option key={type.id} value={type.id}>
                                            {type.name}
                                        </option>
                                    ))}
                                </select>
                                {form.formState.errors.eventType && (
                                    <p className="mt-1 text-sm text-red-600">{form.formState.errors.eventType.message}</p>
                                )}
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700">Date</label>
                                <input
                                    type="date"
                                    min={new Date().toISOString().split("T")[0]}
                                    {...form.register("date")}
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2 border"
                                />
                                {form.formState.errors.date && (
                                    <p className="mt-1 text-sm text-red-600">{form.formState.errors.date.message}</p>
                                )}
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700">Estimated Attendees</label>
                                <input
                                    type="number"
                                    {...form.register("attendees", { valueAsNumber: true })}
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2 border"
                                />
                                {form.formState.errors.attendees && (
                                    <p className="mt-1 text-sm text-red-600">{form.formState.errors.attendees.message}</p>
                                )}
                            </div>
                        </div>
                    )}

                    {step === 2 && (
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700">Budget (PKR)</label>
                                <input
                                    type="number"
                                    {...form.register("budget", { valueAsNumber: true })}
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2 border"
                                />
                                {form.formState.errors.budget && (
                                    <p className="mt-1 text-sm text-red-600">{form.formState.errors.budget.message}</p>
                                )}
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700">City</label>
                                <input
                                    type="text"
                                    {...form.register("city")}
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2 border"
                                />
                                {form.formState.errors.city && (
                                    <p className="mt-1 text-sm text-red-600">{form.formState.errors.city.message}</p>
                                )}
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700">Country</label>
                                <input
                                    type="text"
                                    {...form.register("country")}
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2 border"
                                />
                                {form.formState.errors.country && (
                                    <p className="mt-1 text-sm text-red-600">{form.formState.errors.country.message}</p>
                                )}
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700">Additional Description</label>
                                <textarea
                                    {...form.register("description")}
                                    rows={4}
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2 border"
                                    placeholder="Describe your vision..."
                                />
                            </div>
                        </div>
                    )}

                    <div className="flex justify-between pt-4">
                        {step > 1 ? (
                            <button
                                type="button"
                                onClick={() => setStep(step - 1)}
                                className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                            >
                                <ArrowLeft className="mr-2 h-4 w-4" /> Back
                            </button>
                        ) : (
                            <div />
                        )}

                        {step < 2 ? (
                            <button
                                type="button"
                                onClick={nextStep}
                                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                            >
                                Next <ArrowRight className="ml-2 h-4 w-4" />
                            </button>
                        ) : (
                            <button
                                type="submit"
                                disabled={isSubmitting}
                                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
                            >
                                {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                Create Event
                            </button>
                        )}
                    </div>
                </form>
            </div>
        </div>
    );
}
