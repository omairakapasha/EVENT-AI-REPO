'use client';

import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Loader2, ArrowLeft } from 'lucide-react';
import { VendorLayout } from '@/components/vendor-layout';
import { useCreateService } from '@/lib/hooks/use-vendor-services';

const schema = z.object({
    name: z.string().min(1, 'Name is required').max(150),
    description: z.string().max(1000).optional(),
    capacity: z.string().optional(),
    price_min: z.string().optional(),
    price_max: z.string().optional(),
    requirements: z.string().optional(),
    is_active: z.boolean().default(true),
});

type FormValues = z.infer<typeof schema>;

export default function NewServicePage() {
    const router = useRouter();
    const create = useCreateService();
    const { register, handleSubmit, formState: { errors } } = useForm<FormValues>({
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        resolver: zodResolver(schema) as any,
        defaultValues: { is_active: true },
    });

    const onSubmit = async (values: FormValues) => {
        const payload = {
            name: values.name,
            description: values.description || undefined,
            capacity: values.capacity ? Number(values.capacity) : undefined,
            price_min: values.price_min ? Number(values.price_min) : undefined,
            price_max: values.price_max ? Number(values.price_max) : undefined,
            requirements: values.requirements || undefined,
            is_active: values.is_active,
        };
        await create.mutateAsync(payload);
        router.push('/services');
    };

    return (
        <VendorLayout>
            <div className="mx-auto max-w-2xl space-y-6">
                <button onClick={() => router.back()} className="flex items-center gap-2 text-sm text-surface-500 hover:text-surface-900">
                    <ArrowLeft className="h-4 w-4" /> Back
                </button>
                <div>
                    <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-50">Add Service</h1>
                    <p className="mt-1 text-surface-500">Create a new service offering</p>
                </div>

                <form onSubmit={handleSubmit(onSubmit)} className="rounded-xl border border-surface-200 bg-white p-6 space-y-5 dark:border-surface-800 dark:bg-surface-900">
                    <div>
                        <label className="block text-sm font-medium text-surface-700 dark:text-surface-300">Name *</label>
                        <input {...register('name')} className="mt-1 w-full rounded-lg border border-surface-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none dark:border-surface-700 dark:bg-surface-800" />
                        {errors.name && <p className="mt-1 text-xs text-red-500">{errors.name.message}</p>}
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-surface-700 dark:text-surface-300">Description</label>
                        <textarea {...register('description')} rows={3} className="mt-1 w-full rounded-lg border border-surface-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none dark:border-surface-700 dark:bg-surface-800" />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-surface-700 dark:text-surface-300">Min Price</label>
                            <input type="number" min="0" step="0.01" {...register('price_min')} className="mt-1 w-full rounded-lg border border-surface-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none dark:border-surface-700 dark:bg-surface-800" />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-surface-700 dark:text-surface-300">Max Price</label>
                            <input type="number" min="0" step="0.01" {...register('price_max')} className="mt-1 w-full rounded-lg border border-surface-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none dark:border-surface-700 dark:bg-surface-800" />
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-surface-700 dark:text-surface-300">Capacity (guests)</label>
                        <input type="number" min="1" {...register('capacity')} className="mt-1 w-full rounded-lg border border-surface-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none dark:border-surface-700 dark:bg-surface-800" />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-surface-700 dark:text-surface-300">Requirements</label>
                        <textarea {...register('requirements')} rows={2} className="mt-1 w-full rounded-lg border border-surface-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none dark:border-surface-700 dark:bg-surface-800" />
                    </div>

                    <div className="flex items-center gap-3">
                        <input type="checkbox" id="is_active" {...register('is_active')} className="h-4 w-4 rounded border-surface-300 text-primary-600" />
                        <label htmlFor="is_active" className="text-sm text-surface-700 dark:text-surface-300">Active (visible to customers)</label>
                    </div>

                    <div className="flex justify-end gap-3 pt-2">
                        <button type="button" onClick={() => router.back()} className="rounded-lg border border-surface-300 px-4 py-2 text-sm hover:bg-surface-50">Cancel</button>
                        <button type="submit" disabled={create.isPending} className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm text-white hover:bg-primary-700 disabled:opacity-50">
                            {create.isPending && <Loader2 className="h-4 w-4 animate-spin" />} Create Service
                        </button>
                    </div>
                </form>
            </div>
        </VendorLayout>
    );
}
