'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Star, Send, Loader2, User } from 'lucide-react';
import { getVendorReviews, submitReview } from '@/lib/api';
import toast from 'react-hot-toast';
import { isAxiosError } from 'axios';

interface Review {
    id: string;
    rating: number;
    comment: string;
    created_at: string;
    user_name?: string;
}

function StarRating({ rating, onRate, interactive = false }: { rating: number; onRate?: (r: number) => void; interactive?: boolean }) {
    const [hovered, setHovered] = useState(0);
    return (
        <div className="flex gap-0.5">
            {[1, 2, 3, 4, 5].map((i) => (
                <button
                    key={i}
                    type="button"
                    disabled={!interactive}
                    onClick={() => onRate?.(i)}
                    onMouseEnter={() => interactive && setHovered(i)}
                    onMouseLeave={() => interactive && setHovered(0)}
                    className={`${interactive ? 'cursor-pointer hover:scale-110' : 'cursor-default'} transition-transform`}
                >
                    <Star
                        className={`h-5 w-5 ${i <= (hovered || rating)
                                ? 'text-yellow-400 fill-yellow-400'
                                : 'text-gray-300'
                            }`}
                    />
                </button>
            ))}
        </div>
    );
}

export function VendorReviews({ vendorId }: { vendorId: string }) {
    const queryClient = useQueryClient();
    const [rating, setRating] = useState(0);
    const [comment, setComment] = useState('');

    const { data, isLoading } = useQuery({
        queryKey: ['reviews', vendorId],
        queryFn: () => getVendorReviews(vendorId),
    });

    const mutation = useMutation({
        mutationFn: () => submitReview(vendorId, { rating, comment }),
        onSuccess: () => {
            toast.success('Review submitted!');
            setRating(0);
            setComment('');
            queryClient.invalidateQueries({ queryKey: ['reviews', vendorId] });
            queryClient.invalidateQueries({ queryKey: ['vendor', vendorId] });
        },
        onError: (err) => {
            const data = isAxiosError(err) ? err.response?.data : undefined;
            toast.error(data?.detail?.message || data?.message || 'Failed to submit review');
        },
    });

    const reviews = data?.reviews || data?.data || [];

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (rating === 0) {
            toast.error('Please select a rating');
            return;
        }
        if (!comment.trim()) {
            toast.error('Please write a comment');
            return;
        }
        mutation.mutate();
    };

    return (
        <div>
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Reviews {reviews.length > 0 && `(${reviews.length})`}
            </h2>

            {/* Submit Review Form */}
            <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 mb-6">
                <h3 className="text-sm font-medium text-gray-700 mb-3">Leave a Review</h3>
                <div className="mb-3">
                    <StarRating rating={rating} onRate={setRating} interactive />
                </div>
                <textarea
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    placeholder="Share your experience with this vendor..."
                    rows={3}
                    className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 resize-none mb-3"
                />
                <button
                    type="submit"
                    disabled={mutation.isPending}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
                >
                    {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                    Submit Review
                </button>
            </form>

            {/* Review List */}
            {isLoading ? (
                <div className="space-y-3">
                    {[...Array(3)].map((_, i) => (
                        <div key={i} className="bg-white rounded-xl shadow-sm p-5 space-y-2">
                            <div className="h-4 w-24 animate-pulse rounded bg-gray-200" />
                            <div className="h-3 w-full animate-pulse rounded bg-gray-200" />
                            <div className="h-3 w-2/3 animate-pulse rounded bg-gray-200" />
                        </div>
                    ))}
                </div>
            ) : reviews.length === 0 ? (
                <div className="text-center py-8">
                    <Star className="h-8 w-8 text-gray-200 mx-auto mb-2" />
                    <p className="text-sm text-gray-400">No reviews yet. Be the first!</p>
                </div>
            ) : (
                <div className="space-y-3">
                    {reviews.map((review: Review) => (
                        <div key={review.id} className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
                            <div className="flex items-center justify-between mb-2">
                                <div className="flex items-center gap-2">
                                    <div className="h-8 w-8 rounded-full bg-indigo-100 flex items-center justify-center">
                                        <User className="h-4 w-4 text-indigo-600" />
                                    </div>
                                    <span className="text-sm font-medium text-gray-900">
                                        {review.user_name || 'User'}
                                    </span>
                                </div>
                                <span className="text-xs text-gray-400">
                                    {new Date(review.created_at).toLocaleDateString()}
                                </span>
                            </div>
                            <StarRating rating={review.rating} />
                            <p className="mt-2 text-sm text-gray-600">{review.comment}</p>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
