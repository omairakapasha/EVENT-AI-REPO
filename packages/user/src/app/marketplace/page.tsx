"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import Image from "next/image";
import { useState, useMemo } from "react";
import { getVendors } from "@/lib/api";
import { Star, MapPin, Search, SlidersHorizontal, X } from "lucide-react";

interface Vendor {
    id: string;
    name?: string;
    business_name?: string;
    category?: string;
    businessType?: string;
    rating?: number;
    totalReviews?: number;
    total_reviews?: number;
    pricingMin?: number;
    pricingMax?: number;
    logoUrl?: string;
    logo_url?: string;
    verified?: boolean;
    description?: string;
    serviceAreas?: string[];
    city?: string;
    region?: string;
}

const CATEGORIES = [
    "All Categories",
    "Catering",
    "Photography",
    "Videography",
    "Decoration",
    "Venue",
    "Entertainment",
    "Florist",
    "Planner",
    "Sound & Lighting",
    "Transport",
    "Other",
];

const SORT_OPTIONS = [
    { label: "Newest", value: "newest" },
    { label: "Rating: High to Low", value: "rating_desc" },
    { label: "Price: Low to High", value: "price_asc" },
    { label: "Price: High to Low", value: "price_desc" },
];

export default function MarketplacePage() {
    const [searchQuery, setSearchQuery] = useState("");
    const [category, setCategory] = useState("All Categories");
    const [sortBy, setSortBy] = useState("newest");
    const [showFilters, setShowFilters] = useState(false);
    const [page, setPage] = useState(1);
    const PAGE_SIZE = 12;

    const { data: response, isLoading } = useQuery({
        queryKey: ["vendors", searchQuery, category],
        queryFn: () =>
            getVendors({
                search: searchQuery || undefined,
                category: category !== "All Categories" ? category : undefined,
            }),
    });

    // Client-side sort and category filter
    const vendors = useMemo(() => {
        // Extract vendors array from response envelope { success, data, meta }
        const rawVendors: Vendor[] = response?.data || [];
        let list = [...rawVendors];

        // Filter by category name (backend only accepts category_ids/UUIDs)
        if (category !== "All Categories") {
            list = list.filter((v) => {
                const vendorCategory = (v.category || v.businessType || "").toLowerCase();
                return vendorCategory.includes(category.toLowerCase());
            });
        }

        switch (sortBy) {
            case "rating_desc":
                return list.sort((a, b) => (b.rating || 0) - (a.rating || 0));
            case "price_asc":
                return list.sort((a, b) => (a.pricingMin || 0) - (b.pricingMin || 0));
            case "price_desc":
                return list.sort((a, b) => (b.pricingMin || 0) - (a.pricingMin || 0));
            default:
                return list;
        }
    }, [response, sortBy, category]);

    const totalPages = Math.ceil(vendors.length / PAGE_SIZE);
    const paginatedVendors = vendors.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);


    const activeFilterCount = (category !== "All Categories" ? 1 : 0) + (sortBy !== "newest" ? 1 : 0);

    if (isLoading) {
        return (
            <div className="space-y-6">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
                    <div className="h-8 w-48 animate-pulse rounded bg-gray-200" />
                    <div className="mt-4 sm:mt-0 h-10 w-64 animate-pulse rounded-md bg-gray-200" />
                </div>
                <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                    {[...Array(8)].map((_, i) => (
                        <div key={i} className="rounded-lg bg-white shadow-sm overflow-hidden">
                            <div className="h-48 w-full animate-pulse bg-gray-200" />
                            <div className="p-4 space-y-3">
                                <div className="h-5 w-3/4 animate-pulse rounded bg-gray-200" />
                                <div className="h-4 w-1/2 animate-pulse rounded bg-gray-200" />
                                <div className="flex justify-between">
                                    <div className="h-4 w-20 animate-pulse rounded bg-gray-200" />
                                    <div className="h-4 w-16 animate-pulse rounded bg-gray-200" />
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header + Search */}
            <div className="flex flex-col gap-4">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                    <h1 className="text-3xl font-bold tracking-tight text-gray-900">Vendor Marketplace</h1>
                    <div className="flex items-center gap-2">
                        <div className="relative flex-1 sm:w-64">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" aria-hidden="true" />
                            <input
                                type="text"
                                placeholder="Search vendors..."
                                aria-label="Search vendors"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="block w-full rounded-lg border border-gray-300 shadow-sm pl-10 pr-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                            />
                        </div>
                        <button
                            onClick={() => setShowFilters(!showFilters)}
                            className={`flex items-center gap-2 px-3 py-2.5 rounded-lg border text-sm font-medium transition-colors ${showFilters || activeFilterCount > 0
                                ? "bg-indigo-50 border-indigo-200 text-indigo-700"
                                : "border-gray-300 text-gray-700 hover:bg-gray-50"
                                }`}
                        >
                            <SlidersHorizontal className="h-4 w-4" />
                            Filters
                            {activeFilterCount > 0 && (
                                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-indigo-600 text-[10px] text-white font-bold">
                                    {activeFilterCount}
                                </span>
                            )}
                        </button>
                    </div>
                </div>

                {/* Filter Bar */}
                {showFilters && (
                    <div className="flex flex-wrap items-center gap-3 bg-gray-50 rounded-lg px-4 py-3 border border-gray-200">
                        <div>
                            <label className="block text-xs font-medium text-gray-500 mb-1">Category</label>
                            <select
                                value={category}
                                onChange={(e) => setCategory(e.target.value)}
                                className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white"
                            >
                                {CATEGORIES.map((c) => (
                                    <option key={c} value={c}>{c}</option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-gray-500 mb-1">Sort By</label>
                            <select
                                value={sortBy}
                                onChange={(e) => setSortBy(e.target.value)}
                                className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white"
                            >
                                {SORT_OPTIONS.map((opt) => (
                                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                                ))}
                            </select>
                        </div>
                        {activeFilterCount > 0 && (
                            <button
                                onClick={() => { setCategory("All Categories"); setSortBy("newest"); }}
                                className="mt-5 text-xs text-red-500 hover:text-red-700 flex items-center gap-1"
                            >
                                <X className="h-3 w-3" /> Clear filters
                            </button>
                        )}
                    </div>
                )}
            </div>

            {/* Results Count */}
            <p className="text-sm text-gray-500">
                {vendors.length} vendor{vendors.length !== 1 ? "s" : ""} found
                {category !== "All Categories" && ` in ${category}`}
                {searchQuery && ` matching "${searchQuery}"`}
                {totalPages > 1 && ` • Page ${page} of ${totalPages}`}
            </p>

            {/* Vendor Grid */}
            {vendors.length === 0 ? (
                <div className="text-center py-16">
                    <Search className="h-10 w-10 text-gray-200 mx-auto mb-3" />
                    <h3 className="text-lg font-medium text-gray-900 mb-1">No vendors found</h3>
                    <p className="text-sm text-gray-500">Try adjusting your search or filters.</p>
                </div>
            ) : (
                <>
                    <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                        {paginatedVendors.map((vendor: Vendor) => (
                            <div key={vendor.id} className="group relative bg-white border border-gray-100 rounded-2xl shadow-sm overflow-hidden hover:shadow-lg hover:-translate-y-1 transition-all duration-300">
                                <div className="aspect-[4/3] bg-gradient-to-br from-indigo-50 to-purple-50 overflow-hidden relative">
                                    <Image
                                        src={vendor.logoUrl || vendor.logo_url || "/placeholder-vendor.jpg"}
                                        alt={vendor.business_name || vendor.name || "Vendor"}
                                        fill
                                        sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 25vw"
                                        className="object-cover object-center group-hover:scale-105 transition-transform duration-500"
                                        onError={(e) => {
                                            (e.target as HTMLImageElement).style.display = 'none';
                                        }}
                                    />
                                    {vendor.verified && (
                                        <div className="absolute top-3 left-3">
                                            <span className="inline-flex items-center gap-1 rounded-full bg-green-500 px-2.5 py-1 text-xs font-semibold text-white shadow-sm">
                                                ✓ Verified
                                            </span>
                                        </div>
                                    )}
                                    {(vendor.pricingMin || vendor.pricingMax) && (
                                        <div className="absolute top-3 right-3">
                                            <span className="rounded-full bg-white/90 backdrop-blur-sm px-2.5 py-1 text-xs font-semibold text-gray-700 shadow-sm">
                                                {vendor.pricingMin && vendor.pricingMax
                                                    ? `PKR ${vendor.pricingMin}–${vendor.pricingMax}`
                                                    : `From PKR ${vendor.pricingMin}`}
                                            </span>
                                        </div>
                                    )}
                                </div>
                                <div className="p-5 flex flex-col h-full">
                                    <div className="flex items-start justify-between gap-2">
                                        <div className="min-w-0 flex-1">
                                            <h3 className="font-semibold text-gray-900 truncate group-hover:text-indigo-600 transition-colors">
                                                <Link href={`/marketplace/${vendor.id}`}>
                                                    <span aria-hidden="true" className="absolute inset-0" />
                                                    {vendor.business_name || vendor.name}
                                                </Link>
                                            </h3>
                                            <p className="text-sm text-gray-500 mt-0.5">{vendor.category || vendor.businessType}</p>
                                        </div>
                                        <div className="flex items-center gap-1 shrink-0">
                                            <Star className="h-4 w-4 fill-amber-400 text-amber-400" />
                                            <span className="text-sm font-semibold text-gray-900">
                                                {vendor.rating ? Number(vendor.rating).toFixed(1) : "New"}
                                            </span>
                                            {vendor.totalReviews || vendor.total_reviews ? (
                                                <span className="text-xs text-gray-400">({vendor.totalReviews || vendor.total_reviews})</span>
                                            ) : null}
                                        </div>
                                    </div>
                                    {vendor.description && (
                                        <div className="mt-3 text-sm text-gray-600 line-clamp-2">
                                            {vendor.description}
                                        </div>
                                    )}
                                    <div className="mt-auto pt-4 flex items-center gap-1.5 text-xs text-gray-500">
                                        {((vendor.serviceAreas?.length ?? 0) > 0 || vendor.city || vendor.region) && (
                                            <>
                                                <MapPin className="h-3.5 w-3.5 shrink-0" />
                                                <span className="truncate">
                                                    {(vendor.serviceAreas?.length ?? 0) > 0
                                                        ? vendor.serviceAreas!.slice(0, 2).join(", ")
                                                        : [vendor.city, vendor.region].filter(Boolean).join(", ")}
                                                </span>
                                            </>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Pagination Controls */}
                    {totalPages > 1 && (
                        <div className="flex items-center justify-center gap-2 pt-4">
                            <button
                                onClick={() => setPage((p) => Math.max(1, p - 1))}
                                disabled={page === 1}
                                className="px-4 py-2 rounded-lg border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
                            >
                                Previous
                            </button>
                            {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                                <button
                                    key={p}
                                    onClick={() => setPage(p)}
                                    className={`w-9 h-9 rounded-lg text-sm font-medium ${p === page
                                            ? 'bg-indigo-600 text-white'
                                            : 'border border-gray-300 text-gray-700 hover:bg-gray-50'
                                        }`}
                                >
                                    {p}
                                </button>
                            ))}
                            <button
                                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                                disabled={page === totalPages}
                                className="px-4 py-2 rounded-lg border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
                            >
                                Next
                            </button>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}
