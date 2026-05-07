'use client';

import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Loader2, Edit2, X } from 'lucide-react';
import { VendorLayout } from '@/components/vendor-layout';
import { useVendorProfile, useUpdateProfile } from '@/lib/hooks/use-vendor-profile';
import { cn } from '@/lib/utils';

const STATUS_COLORS: Record<string, string> = {
    PENDING: 'bg-yellow-100 text-yellow-700',
    ACTIVE: 'bg-green-100 text-green-700',
    SUSPENDED: 'bg-orange-100 text-orange-700',
    REJECTED: 'bg-red-100 text-red-700',
};

const schema = z.object({
    business_name: z.string().min(1, 'Business name is required').max(255),
    description: z.string().max(2000).optional(),
    contact_email: z.string().email('Invalid email'),
    contact_phone: z.string().optional(),
    website: z.string()
        .optional()
        .refine(
            (v) => !v || v.startsWith('http://') || v.startsWith('https://'),
            { message: 'Website must start with http:// or https://' }
        ),
    city: z.string().optional(),
    region: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

export default function ProfilePage() {
    const [editing, setEditing] = useState(false);
    const { data: vendor, isLoading } = useVendorProfile();
    const update = useUpdateProfile();

    const { register, handleSubmit, reset, formState: { errors } } = useForm<FormValues>({
        resolver: zodResolver(schema),
    });

    useEffect(() => {
        if (vendor) {
            reset({
                business_name: vendor.businessName,
                description: vendor.description ?? '',
                contact_email: vendor.contactEmail,
                contact_phone: vendor.contactPhone ?? '',
                website: vendor.website ?? '',
                city: vendor.city ?? '',
                region: vendor.region ?? '',
            });
        }
    }, [vendor, reset]);

    const onSubmit = async (values: FormValues) => {
        await update.mutateAsync({
            business_name: values.business_name,
            description: values.description || undefined,
            contact_email: values.contact_email,
            contact_phone: values.contact_phone || undefined,
            website: values.website || undefined,
            city: values.city || undefined,
            region: values.region || undefined,
        } as Parameters<typeof update.mutateAsync>[0]);
        setEditing(false);
    };

    const handleCancel = () => {
        if (vendor) {
            reset({
                business_name: vendor.businessName,
                description: vendor.description ?? '',
                contact_email: vendor.contactEmail,
                contact_phone: vendor.contactPhone ?? '',
                website: vendor.website ?? '',
                city: vendor.city ?? '',
                region: vendor.region ?? '',
            });
        }
        setEditing(false);
    };

    return (
        <VendorLayout>
            <div className="mx-auto max-w-2xl space-y-6">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-50">Profile</h1>
                        <p className="mt-1 text-surface-500">Manage your business information</p>
                    </div>
                    {vendor && !editing && (
                        <button onClick={() => setEditing(true)} className="flex items-center gap-2 rounded-lg border border-surface-300 px-4 py-2 text-sm hover:bg-surface-50 dark:border-surface-700 dark:hover:bg-surface-800">
                            <Edit2 className="h-4 w-4" /> Edit Profile
                        </button>
                    )}
                </div>

                {isLoading ? (
                    <div className="flex justify-center py-20"><Loader2 className="h-8 w-8 animate-spin text-primary-600" /></div>
                ) : (
                    <form onSubmit={handleSubmit(onSubmit)} className="rounded-xl border border-surface-200 bg-white p-6 space-y-5 dark:border-surface-800 dark:bg-surface-900">
                        {/* Status badge (read-only) */}
                        {vendor && (
                            <div className="flex items-center gap-3">
                                <span className="text-sm text-surface-500">Approval Status:</span>
                                <span className={cn('rounded-full px-3 py-0.5 text-xs font-medium', STATUS_COLORS[vendor.status] ?? 'bg-gray-100 text-gray-600')}>
                                    {vendor.status}
                                </span>
                            </div>
                        )}

                        {[
                            { label: 'Business Name *', name: 'business_name' as const },
                            { label: 'Contact Email *', name: 'contact_email' as const },
                            { label: 'Contact Phone', name: 'contact_phone' as const },
                            { label: 'Website', name: 'website' as const },
                            { label: 'City', name: 'city' as const },
                            { label: 'Region', name: 'region' as const },
                        ].map(({ label, name }) => (
                            <div key={name}>
                                <label className="block text-sm font-medium text-surface-700 dark:text-surface-300">{label}</label>
                                <input
                                    {...register(name)}
                                    disabled={!editing}
                                    className={cn(
                                        'mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:border-primary-500 focus:outline-none dark:bg-surface-800',
                                        editing ? 'border-surface-300 dark:border-surface-700' : 'border-transparent bg-surface-50 dark:bg-surface-800/50 text-surface-700 dark:text-surface-300'
                                    )}
                                />
                                {errors[name] && <p className="mt-1 text-xs text-red-500">{errors[name]?.message}</p>}
                            </div>
                        ))}

                        <div>
                            <label className="block text-sm font-medium text-surface-700 dark:text-surface-300">Description</label>
                            <textarea
                                {...register('description')}
                                disabled={!editing}
                                rows={3}
                                className={cn(
                                    'mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:border-primary-500 focus:outline-none dark:bg-surface-800',
                                    editing ? 'border-surface-300 dark:border-surface-700' : 'border-transparent bg-surface-50 dark:bg-surface-800/50 text-surface-700 dark:text-surface-300'
                                )}
                            />
                        </div>

                        {editing && (
                            <div className="flex justify-end gap-3 pt-2">
                                <button type="button" onClick={handleCancel} className="flex items-center gap-2 rounded-lg border border-surface-300 px-4 py-2 text-sm hover:bg-surface-50">
                                    <X className="h-4 w-4" /> Cancel
                                </button>
                                <button type="submit" disabled={update.isPending} className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm text-white hover:bg-primary-700 disabled:opacity-50">
                                    {update.isPending && <Loader2 className="h-4 w-4 animate-spin" />} Save Changes
                                </button>
                            </div>
                        )}
                    </form>
                )}
            </div>
        </VendorLayout>
    );
}
