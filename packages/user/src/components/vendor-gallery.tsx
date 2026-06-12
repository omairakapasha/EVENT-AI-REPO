'use client';

import { useState } from 'react';
import Image from 'next/image';
import { ChevronLeft, ChevronRight, X, ZoomIn } from 'lucide-react';

interface VendorGalleryProps {
    images: string[];
    vendorName: string;
}

export function VendorGallery({ images, vendorName }: VendorGalleryProps) {
    const [activeIndex, setActiveIndex] = useState(0);
    const [lightboxOpen, setLightboxOpen] = useState(false);

    if (!images || images.length === 0) {
        return (
            <div className="flex h-48 items-center justify-center rounded-xl bg-gray-100">
                <p className="text-sm text-gray-400">No images available</p>
            </div>
        );
    }

    const prev = () => setActiveIndex((i) => (i === 0 ? images.length - 1 : i - 1));
    const next = () => setActiveIndex((i) => (i === images.length - 1 ? 0 : i + 1));

    return (
        <>
            {/* Main Gallery */}
            <div className="space-y-3">
                {/* Featured Image */}
                <div className="group relative h-72 overflow-hidden rounded-xl bg-gray-100">
                    <Image
                        src={images[activeIndex]}
                        alt={`${vendorName} — image ${activeIndex + 1}`}
                        fill
                        sizes="(max-width: 768px) 100vw, 768px"
                        className="object-cover transition-transform duration-300 group-hover:scale-105"
                        onError={(e) => { (e.target as HTMLImageElement).src = '/placeholder-image.jpg'; }}
                    />
                    {/* Nav arrows */}
                    {images.length > 1 && (
                        <>
                            <button
                                onClick={prev}
                                className="absolute left-3 top-1/2 -translate-y-1/2 rounded-full bg-white/80 p-2 shadow hover:bg-white"
                                aria-label="Previous image"
                            >
                                <ChevronLeft className="h-5 w-5 text-gray-700" />
                            </button>
                            <button
                                onClick={next}
                                className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full bg-white/80 p-2 shadow hover:bg-white"
                                aria-label="Next image"
                            >
                                <ChevronRight className="h-5 w-5 text-gray-700" />
                            </button>
                        </>
                    )}
                    {/* Zoom icon */}
                    <button
                        onClick={() => setLightboxOpen(true)}
                        className="absolute bottom-3 right-3 rounded-full bg-white/80 p-2 shadow hover:bg-white"
                        aria-label="View fullscreen"
                    >
                        <ZoomIn className="h-4 w-4 text-gray-700" />
                    </button>
                    {/* Counter */}
                    <span className="absolute bottom-3 left-3 rounded-full bg-black/50 px-3 py-1 text-xs text-white">
                        {activeIndex + 1} / {images.length}
                    </span>
                </div>

                {/* Thumbnail strip */}
                {images.length > 1 && (
                    <div className="flex gap-2 overflow-x-auto pb-1">
                        {images.map((img, i) => (
                            <button
                                key={i}
                                onClick={() => setActiveIndex(i)}
                                className={`relative h-16 w-20 flex-shrink-0 overflow-hidden rounded-lg border-2 transition-all ${i === activeIndex ? 'border-blue-500 ring-2 ring-blue-200' : 'border-transparent'}`}
                            >
                                <Image
                                    src={img}
                                    alt={`Thumbnail ${i + 1}`}
                                    fill
                                    sizes="80px"
                                    className="object-cover"
                                    onError={(e) => { (e.target as HTMLImageElement).src = '/placeholder-image.jpg'; }}
                                />
                            </button>
                        ))}
                    </div>
                )}
            </div>

            {/* Lightbox */}
            {lightboxOpen && (
                <div
                    className="fixed inset-0 z-50 flex items-center justify-center bg-black/90"
                    onClick={() => setLightboxOpen(false)}
                >
                    <button
                        className="absolute right-4 top-4 rounded-full bg-white/10 p-2 text-white hover:bg-white/20"
                        onClick={() => setLightboxOpen(false)}
                        aria-label="Close"
                    >
                        <X className="h-6 w-6" />
                    </button>
                    <button
                        className="absolute left-4 top-1/2 -translate-y-1/2 rounded-full bg-white/10 p-3 text-white hover:bg-white/20"
                        onClick={(e) => { e.stopPropagation(); prev(); }}
                    >
                        <ChevronLeft className="h-7 w-7" />
                    </button>
                    <div
                        className="relative h-[90vh] w-[90vw]"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <Image
                            src={images[activeIndex]}
                            alt={`${vendorName} — image ${activeIndex + 1}`}
                            fill
                            sizes="90vw"
                            className="rounded-xl object-contain shadow-2xl"
                        />
                    </div>
                    <button
                        className="absolute right-4 top-1/2 -translate-y-1/2 rounded-full bg-white/10 p-3 text-white hover:bg-white/20"
                        onClick={(e) => { e.stopPropagation(); next(); }}
                    >
                        <ChevronRight className="h-7 w-7" />
                    </button>
                </div>
            )}
        </>
    );
}
