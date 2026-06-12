'use client';

import { useQuery } from '@tanstack/react-query';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import {
    ArrowLeft, Star, MapPin, Phone, Mail, Globe, Clock,
    Calendar, Users, Package, AlertCircle,
} from 'lucide-react';
import { getVendorById } from '@/lib/api';
import { VendorReviews } from '@/components/vendor-reviews';
import { VendorGallery } from '@/components/vendor-gallery';

interface VendorPricing {
    basePrice?: number;
    price?: number;
}

interface VendorService {
    id: string;
    name: string;
    description?: string;
    isActive?: boolean;
    capacity?: number;
    duration?: string;
    featuredImage?: string;
    images?: string[];
    pricings?: VendorPricing[];
}

export default function VendorDetailPage() {
    const params = useParams();
    const vendorId = params.id as string;

    const { data, isLoading, error } = useQuery({
        queryKey: ['vendor', vendorId],
        queryFn: () => getVendorById(vendorId),
        enabled: !!vendorId,
    });

    if (isLoading) {
        return (
            <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
                <div className="h-6 w-32 animate-pulse rounded bg-gray-200" />
                <div className="bg-white rounded-xl shadow-sm p-8 space-y-4">
                    <div className="h-8 w-2/3 animate-pulse rounded bg-gray-200" />
                    <div className="h-4 w-1/3 animate-pulse rounded bg-gray-200" />
                    <div className="h-20 w-full animate-pulse rounded bg-gray-200" />
                </div>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    {[...Array(4)].map((_, i) => (
                        <div key={i} className="bg-white rounded-xl shadow-sm p-6 space-y-3">
                            <div className="h-5 w-3/4 animate-pulse rounded bg-gray-200" />
                            <div className="h-4 w-1/2 animate-pulse rounded bg-gray-200" />
                            <div className="h-8 w-24 animate-pulse rounded-lg bg-gray-200" />
                        </div>
                    ))}
                </div>
            </div>
        );
    }

    if (error || !data) {
        return (
            <div className="max-w-4xl mx-auto px-4 py-16 text-center">
                <AlertCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
                <h2 className="text-xl font-bold text-gray-900 mb-2">Vendor not found</h2>
                <p className="text-gray-500 mb-6">This vendor may no longer be available.</p>
                <Link href="/marketplace" className="text-indigo-600 hover:text-indigo-700 font-medium">
                    ← Back to Marketplace
                </Link>
            </div>
        );
    }

    const vendor = data.vendor || data.data || data;
    const services: VendorService[] = vendor.services || [];

    return (
        <div className="max-w-4xl mx-auto px-4 py-8">
            {/* Back Link */}
            <Link href="/marketplace" className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-indigo-600 mb-6">
                <ArrowLeft className="h-4 w-4" />
                Back to Marketplace
            </Link>

            {/* Vendor Header */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8 mb-8">
                <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900">{vendor.name}</h1>
                        <p className="mt-1 text-sm text-gray-500 capitalize">{vendor.category || vendor.businessType}</p>
                        <div className="flex items-center gap-4 mt-3 text-sm text-gray-500">
                            {vendor.rating && (
                                <span className="flex items-center gap-1">
                                    <Star className="h-4 w-4 text-yellow-400 fill-current" />
                                    {Number(vendor.rating).toFixed(1)}
                                    {vendor.totalReviews ? ` (${vendor.totalReviews} reviews)` : ''}
                                </span>
                            )}
                            {vendor.serviceAreas?.length > 0 && (
                                <span className="flex items-center gap-1">
                                    <MapPin className="h-4 w-4" />
                                    {vendor.serviceAreas.join(', ')}
                                </span>
                            )}
                        </div>
                    </div>
                    {vendor.tier && (
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${vendor.tier === 'GOLD' ? 'bg-amber-100 text-amber-800' :
                            vendor.tier === 'SILVER' ? 'bg-slate-100 text-slate-700' :
                                'bg-orange-100 text-orange-800'
                            }`}>
                            {vendor.tier}
                        </span>
                    )}
                </div>

                {vendor.description && (
                    <p className="mt-4 text-gray-600 leading-relaxed">{vendor.description}</p>
                )}

                {/* Gallery */}
                {(() => {
                    const galleryImages: string[] = [
                        ...(vendor.logoUrl ? [vendor.logoUrl] : []),
                        ...services.flatMap((s: VendorService) => [
                            ...(s.featuredImage ? [s.featuredImage] : []),
                            ...(Array.isArray(s.images) ? s.images : []),
                        ]),
                    ].filter(Boolean).slice(0, 10);
                    return galleryImages.length > 0 ? (
                        <div className="mt-6 pt-6 border-t border-gray-100">
                            <VendorGallery images={galleryImages} vendorName={vendor.name} />
                        </div>
                    ) : null;
                })()}

                {/* Contact Info */}
                <div className="mt-6 pt-6 border-t border-gray-100 grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
                    {vendor.contactEmail && (
                        <a href={`mailto:${vendor.contactEmail}`} className="flex items-center gap-2 text-gray-500 hover:text-indigo-600">
                            <Mail className="h-4 w-4" /> {vendor.contactEmail}
                        </a>
                    )}
                    {vendor.phone && (
                        <a href={`tel:${vendor.phone}`} className="flex items-center gap-2 text-gray-500 hover:text-indigo-600">
                            <Phone className="h-4 w-4" /> {vendor.phone}
                        </a>
                    )}
                    {vendor.website && (
                        <a href={vendor.website} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-gray-500 hover:text-indigo-600">
                            <Globe className="h-4 w-4" /> Website
                        </a>
                    )}
                </div>
            </div>

            {/* Services */}
            <div className="mb-8">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">
                    Services ({services.length})
                </h2>

                {services.length === 0 ? (
                    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8 text-center">
                        <Package className="h-10 w-10 text-gray-300 mx-auto mb-3" />
                        <p className="text-gray-500">No services listed yet.</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                        {services.map((service: VendorService) => (
                            <div key={service.id} className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 hover:shadow-md transition-shadow">
                                <div className="flex justify-between items-start mb-2">
                                    <h3 className="font-semibold text-gray-900">{service.name}</h3>
                                    <span className={`text-xs px-2 py-1 rounded-full ${service.isActive ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                                        }`}>
                                        {service.isActive ? 'Available' : 'Unavailable'}
                                    </span>
                                </div>
                                {service.description && (
                                    <p className="text-sm text-gray-500 mb-3 line-clamp-2">{service.description}</p>
                                )}
                                <div className="flex items-center gap-4 text-xs text-gray-400 mb-4">
                                    {service.capacity && (
                                        <span className="flex items-center gap-1">
                                            <Users className="h-3 w-3" /> Up to {service.capacity}
                                        </span>
                                    )}
                                    {service.duration && (
                                        <span className="flex items-center gap-1">
                                            <Clock className="h-3 w-3" /> {service.duration}
                                        </span>
                                    )}
                                </div>

                                {/* Pricing */}
                                {(service.pricings?.length ?? 0) > 0 && (
                                    <p className="text-sm font-medium text-gray-900 mb-3">
                                        From PKR {Math.min(...(service.pricings ?? []).map((p: VendorPricing) => p.basePrice || p.price || 0)).toLocaleString()}
                                    </p>
                                )}

                                {service.isActive && (
                                    <Link
                                        href={`/marketplace/${vendorId}/book?serviceId=${service.id}&serviceName=${encodeURIComponent(service.name)}`}
                                        className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors"
                                    >
                                        <Calendar className="h-4 w-4" />
                                        Book Now
                                    </Link>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Reviews */}
            <VendorReviews vendorId={vendorId} />
        </div>
    );
}
