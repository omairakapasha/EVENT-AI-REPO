"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import { getCategories, createCategory, deleteCategory } from "@/lib/api";
import { Save, Trash2, Plus, Loader2, Info, Tag } from "lucide-react";
import toast from "react-hot-toast";

export default function SettingsPage() {
    const { data: session } = useSession();
    const queryClient = useQueryClient();
    const [newCategory, setNewCategory] = useState({
        name: "",
        slug: "",
        description: "",
    });

    const { data: categories, isLoading: categoriesLoading } = useQuery({
        queryKey: ["categories"],
        queryFn: getCategories,
    });

    const createMutation = useMutation({
        mutationFn: createCategory,
        onSuccess: () => {
            toast.success("Category created successfully");
            queryClient.invalidateQueries({ queryKey: ["categories"] });
            setNewCategory({ name: "", slug: "", description: "" });
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.message || "Failed to create category");
        },
    });

    const deleteMutation = useMutation({
        mutationFn: deleteCategory,
        onSuccess: () => {
            toast.success("Category deleted successfully");
            queryClient.invalidateQueries({ queryKey: ["categories"] });
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.message || "Failed to delete category");
        },
    });

    const handleCreateCategory = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!newCategory.name || !newCategory.slug) {
            toast.error("Name and slug are required");
            return;
        }
        createMutation.mutate(newCategory);
    };

    const handleDeleteCategory = (id: string) => {
        if (confirm("Are you sure you want to delete this category?")) {
            deleteMutation.mutate(id);
        }
    };

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000/api/v1";
    const adminEmail = (session as any)?.user?.email || "—";

    return (
        <div className="space-y-6">
            {/* Page Header */}
            <div>
                <h1 className="text-2xl font-bold text-gray-900">Platform Settings</h1>
                <p className="mt-1 text-sm text-gray-500">Manage platform configuration and categories</p>
            </div>

            {/* Platform Info Section */}
            <div className="rounded-2xl bg-white border border-gray-100 shadow-sm overflow-hidden">
                <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-100">
                    <Info className="h-5 w-5 text-gray-400" />
                    <h3 className="font-semibold text-gray-900">Platform Info</h3>
                </div>
                <div className="p-6 space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1">
                                Backend API URL
                            </label>
                            <p className="text-sm text-gray-900 font-mono bg-gray-50 px-3 py-2 rounded-lg border border-gray-200">
                                {apiUrl}
                            </p>
                        </div>
                        <div>
                            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1">
                                Admin Email
                            </label>
                            <p className="text-sm text-gray-900 bg-gray-50 px-3 py-2 rounded-lg border border-gray-200">
                                {adminEmail}
                            </p>
                        </div>
                    </div>
                    <div>
                        <label className="block text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1">
                            Portal Version
                        </label>
                        <p className="text-sm text-gray-900 bg-gray-50 px-3 py-2 rounded-lg border border-gray-200 inline-block">
                            v1.0.0
                        </p>
                    </div>
                </div>
            </div>

            {/* Categories Section */}
            <div className="rounded-2xl bg-white border border-gray-100 shadow-sm overflow-hidden">
                <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-100">
                    <Tag className="h-5 w-5 text-gray-400" />
                    <h3 className="font-semibold text-gray-900">Event Categories</h3>
                </div>
                <div className="p-6">
                    {/* Categories List */}
                    {categoriesLoading ? (
                        <div className="flex items-center justify-center py-8">
                            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
                        </div>
                    ) : (
                        <div className="space-y-2 mb-6">
                            {categories && categories.length > 0 ? (
                                categories.map((category: any) => (
                                    <div
                                        key={category.id}
                                        className="flex items-center justify-between p-4 rounded-xl border border-gray-100 hover:bg-gray-50 transition-colors"
                                    >
                                        <div>
                                            <p className="font-medium text-gray-900">{category.name}</p>
                                            <p className="text-xs text-gray-500 mt-0.5">
                                                Slug: <span className="font-mono">{category.slug}</span>
                                                {category.description && ` · ${category.description}`}
                                            </p>
                                        </div>
                                        <button
                                            onClick={() => handleDeleteCategory(category.id)}
                                            disabled={deleteMutation.isPending}
                                            className="flex h-8 w-8 items-center justify-center rounded-lg text-red-500 hover:bg-red-50 disabled:opacity-40 transition-colors"
                                            title="Delete category"
                                        >
                                            <Trash2 className="h-4 w-4" />
                                        </button>
                                    </div>
                                ))
                            ) : (
                                <div className="text-center py-8 text-sm text-gray-400">
                                    No categories yet. Create one below.
                                </div>
                            )}
                        </div>
                    )}

                    {/* New Category Form */}
                    <div className="border-t border-gray-100 pt-6">
                        <h4 className="text-sm font-semibold text-gray-900 mb-4">Add New Category</h4>
                        <form onSubmit={handleCreateCategory} className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-medium text-gray-700 mb-1">
                                        Name <span className="text-red-500">*</span>
                                    </label>
                                    <input
                                        type="text"
                                        value={newCategory.name}
                                        onChange={(e) => setNewCategory({ ...newCategory, name: e.target.value })}
                                        placeholder="e.g., Wedding"
                                        className="w-full px-3 py-2 text-sm rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-300"
                                        required
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-medium text-gray-700 mb-1">
                                        Slug <span className="text-red-500">*</span>
                                    </label>
                                    <input
                                        type="text"
                                        value={newCategory.slug}
                                        onChange={(e) => setNewCategory({ ...newCategory, slug: e.target.value })}
                                        placeholder="e.g., wedding"
                                        className="w-full px-3 py-2 text-sm rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-300 font-mono"
                                        required
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-gray-700 mb-1">
                                    Description (optional)
                                </label>
                                <textarea
                                    value={newCategory.description}
                                    onChange={(e) => setNewCategory({ ...newCategory, description: e.target.value })}
                                    placeholder="Brief description of this category"
                                    rows={2}
                                    className="w-full px-3 py-2 text-sm rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-300"
                                />
                            </div>
                            <button
                                type="submit"
                                disabled={createMutation.isPending}
                                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-violet-600 text-white text-sm font-medium hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                            >
                                {createMutation.isPending ? (
                                    <>
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                        Creating...
                                    </>
                                ) : (
                                    <>
                                        <Plus className="h-4 w-4" />
                                        Create Category
                                    </>
                                )}
                            </button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    );
}
