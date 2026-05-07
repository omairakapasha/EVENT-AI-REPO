"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import {
    Upload,
    DollarSign,
    Calendar,
    Package,
    CheckCircle,
    AlertCircle,
    Loader2,
    FileSpreadsheet,
    Download
} from "lucide-react";
import { cn } from "@/lib/utils";

interface PricingUpload {
    id: string;
    fileName: string;
    status: "pending" | "processing" | "completed" | "failed" | "partial";
    totalRecords: number;
    processedRecords: number;
    failedRecords: number;
    createdAt: string;
    errorLog?: any[];
}

interface Service {
    id: string;
    name: string;
    category: string;
}

interface PriceRecord {
    serviceId?: string;
    serviceName?: string;
    price: number;
    currency: string;
    unitType: "per_hour" | "per_day" | "per_event" | "per_person" | "per_unit" | "flat_rate";
    effectiveDate: string;
    expiryDate?: string;
}

export default function PricingPage() {
    const router = useRouter();
    const { isAuthenticated } = useAuthStore();
    const queryClient = useQueryClient();
    const [activeTab, setActiveTab] = useState<"upload" | "history">("upload");
    const [uploadData, setUploadData] = useState<PriceRecord[]>([]);
    const [isDragging, setIsDragging] = useState(false);
    const [hasMounted, setHasMounted] = useState(false);

    useEffect(() => {
        setHasMounted(true);
    }, []);

    useEffect(() => {
        if (hasMounted && !isAuthenticated) {
            router.push('/login');
        }
    }, [hasMounted, isAuthenticated, router]);

    // Fetch services for dropdown — must be BEFORE any early return
    const { data: services, isLoading: servicesLoading } = useQuery({
        queryKey: ["services"],
        queryFn: async () => {
            const response = await api.get("/vendors/me/services");
            return response.data?.data || [];
        },
        enabled: hasMounted && isAuthenticated,
    });

    // Fetch upload history
    const { data: uploads, isLoading: uploadsLoading } = useQuery({
        queryKey: ["price-uploads"],
        queryFn: async () => {
            const response = await api.get("/vendors/me/pricing/history");
            return response.data?.data || [];
        },
        enabled: hasMounted && isAuthenticated && activeTab === "history",
    });

    // Bulk upload mutation
    const uploadMutation = useMutation({
        mutationFn: async (records: PriceRecord[]) => {
            const response = await api.post("/vendors/me/pricing/bulk", {
                prices: records,
            });
            return response.data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["price-uploads"] });
            setUploadData([]);
            setActiveTab("history");
        },
    });

    if (!hasMounted || !isAuthenticated) {
        return (
            <div className="flex min-h-screen items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
            </div>
        );
    }

    const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const text = e.target?.result as string;
                const lines = text.split("\n").filter(line => line.trim());

                // Parse CSV format: serviceName,price,unitType,effectiveDate,expiryDate
                const records: PriceRecord[] = lines.slice(1).map((line, index) => {
                    const [serviceName, price, unitType, effectiveDate, expiryDate] = line.split(",").map(s => s.trim());

                    // Try to find matching service
                    const matchingService = services?.find(
                        (s: Service) => s.name.toLowerCase() === serviceName.toLowerCase()
                    );

                    return {
                        serviceId: matchingService?.id,
                        serviceName: serviceName || `Service ${index + 1}`,
                        price: parseFloat(price) || 0,
                        currency: "PKR",
                        unitType: (unitType as PriceRecord["unitType"]) || "per_event",
                        effectiveDate: effectiveDate || new Date().toISOString().split("T")[0],
                        expiryDate: expiryDate || undefined,
                    };
                }).filter(r => r.price > 0);

                setUploadData(records);
            } catch (error) {
                console.error("Error parsing file:", error);
                alert("Error parsing file. Please check the format.");
            }
        };
        reader.readAsText(file);
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);

        const file = e.dataTransfer.files?.[0];
        if (file && file.type === "text/csv") {
            const input = document.getElementById("csv-upload") as HTMLInputElement;
            if (input) {
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                input.files = dataTransfer.files;
                handleFileUpload({ target: input } as any);
            }
        }
    };

    const addManualRow = () => {
        setUploadData([
            ...uploadData,
            {
                serviceName: "",
                price: 0,
                currency: "PKR",
                unitType: "per_event",
                effectiveDate: new Date().toISOString().split("T")[0],
            },
        ]);
    };

    const updateRow = (index: number, field: keyof PriceRecord, value: any) => {
        const updated = [...uploadData];
        updated[index] = { ...updated[index], [field]: value };

        // If serviceId changes, update serviceName
        if (field === "serviceId" && value) {
            const service = services?.find((s: Service) => s.id === value);
            if (service) {
                updated[index].serviceName = service.name;
            }
        }

        setUploadData(updated);
    };

    const removeRow = (index: number) => {
        setUploadData(uploadData.filter((_, i) => i !== index));
    };

    const handleSubmit = () => {
        if (uploadData.length === 0) return;
        uploadMutation.mutate(uploadData);
    };

    const downloadTemplate = () => {
        const template = "Service Name,Price,Unit Type,Effective Date (YYYY-MM-DD),Expiry Date (YYYY-MM-DD)\nWedding Package,50000,per_event,2024-03-01,2024-12-31\nCatering per Person,1500,per_person,2024-03-01,\nPhotography Hourly,5000,per_hour,2024-03-01,";

        const blob = new Blob([template], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "pricing_template.csv";
        a.click();
        URL.revokeObjectURL(url);
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-3xl font-bold tracking-tight">Pricing Management</h1>
                <div className="flex gap-2">
                    <button
                        onClick={() => setActiveTab("upload")}
                        className={cn(
                            "px-4 py-2 rounded-lg font-medium transition-colors",
                            activeTab === "upload"
                                ? "bg-primary-600 text-white"
                                : "bg-surface-100 text-surface-700 hover:bg-surface-200"
                        )}
                    >
                        Upload Prices
                    </button>
                    <button
                        onClick={() => setActiveTab("history")}
                        className={cn(
                            "px-4 py-2 rounded-lg font-medium transition-colors",
                            activeTab === "history"
                                ? "bg-primary-600 text-white"
                                : "bg-surface-100 text-surface-700 hover:bg-surface-200"
                        )}
                    >
                        Upload History
                    </button>
                </div>
            </div>

            {activeTab === "upload" && (
                <div className="space-y-6">
                    {/* Upload Area */}
                    <div
                        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                        onDragLeave={() => setIsDragging(false)}
                        onDrop={handleDrop}
                        className={cn(
                            "border-2 border-dashed rounded-xl p-8 text-center transition-colors",
                            isDragging
                                ? "border-primary-500 bg-primary-50"
                                : "border-surface-300 bg-surface-50"
                        )}
                    >
                        <Upload className="mx-auto h-12 w-12 text-surface-400 mb-4" />
                        <h3 className="text-lg font-semibold text-surface-900 mb-2">
                            Upload Pricing CSV
                        </h3>
                        <p className="text-surface-600 mb-4">
                            Drag and drop your CSV file here, or click to browse
                        </p>
                        <input
                            id="csv-upload"
                            type="file"
                            accept=".csv"
                            onChange={handleFileUpload}
                            className="hidden"
                        />
                        <label
                            htmlFor="csv-upload"
                            className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 cursor-pointer transition-colors"
                        >
                            <FileSpreadsheet className="h-4 w-4" />
                            Choose File
                        </label>
                        <button
                            onClick={downloadTemplate}
                            className="ml-4 inline-flex items-center gap-2 text-primary-600 hover:text-primary-700"
                        >
                            <Download className="h-4 w-4" />
                            Download Template
                        </button>
                    </div>

                    {/* Manual Entry Table */}
                    <div className="bg-white rounded-xl border border-surface-200 shadow-sm">
                        <div className="p-4 border-b border-surface-200 flex items-center justify-between">
                            <h3 className="font-semibold text-surface-900">
                                Price Entries ({uploadData.length})
                            </h3>
                            <button
                                onClick={addManualRow}
                                className="text-sm text-primary-600 hover:text-primary-700 font-medium"
                            >
                                + Add Row
                            </button>
                        </div>

                        {uploadData.length > 0 ? (
                            <div className="overflow-x-auto">
                                <table className="w-full">
                                    <thead className="bg-surface-50">
                                        <tr>
                                            <th className="px-4 py-3 text-left text-xs font-medium text-surface-500 uppercase">
                                                Service
                                            </th>
                                            <th className="px-4 py-3 text-left text-xs font-medium text-surface-500 uppercase">
                                                Price (PKR)
                                            </th>
                                            <th className="px-4 py-3 text-left text-xs font-medium text-surface-500 uppercase">
                                                Unit Type
                                            </th>
                                            <th className="px-4 py-3 text-left text-xs font-medium text-surface-500 uppercase">
                                                Effective Date
                                            </th>
                                            <th className="px-4 py-3 text-left text-xs font-medium text-surface-500 uppercase">
                                                Expiry Date
                                            </th>
                                            <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase">
                                                Actions
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-surface-200">
                                        {uploadData.map((row, index) => (
                                            <tr key={index} className="hover:bg-surface-50">
                                                <td className="px-4 py-3">
                                                    <select
                                                        value={row.serviceId || ""}
                                                        onChange={(e) => updateRow(index, "serviceId", e.target.value)}
                                                        className="w-full text-sm border-surface-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
                                                    >
                                                        <option value="">Select or type name...</option>
                                                        {services?.map((service: Service) => (
                                                            <option key={service.id} value={service.id}>
                                                                {service.name}
                                                            </option>
                                                        ))}
                                                    </select>
                                                    {!row.serviceId && (
                                                        <input
                                                            type="text"
                                                            value={row.serviceName || ""}
                                                            onChange={(e) => updateRow(index, "serviceName", e.target.value)}
                                                            placeholder="New service name"
                                                            className="mt-1 w-full text-sm border-surface-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
                                                        />
                                                    )}
                                                </td>
                                                <td className="px-4 py-3">
                                                    <input
                                                        type="number"
                                                        value={row.price}
                                                        onChange={(e) => updateRow(index, "price", parseFloat(e.target.value))}
                                                        className="w-32 text-sm border-surface-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
                                                    />
                                                </td>
                                                <td className="px-4 py-3">
                                                    <select
                                                        value={row.unitType}
                                                        onChange={(e) => updateRow(index, "unitType", e.target.value)}
                                                        className="text-sm border-surface-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
                                                    >
                                                        <option value="per_hour">Per Hour</option>
                                                        <option value="per_day">Per Day</option>
                                                        <option value="per_event">Per Event</option>
                                                        <option value="per_person">Per Person</option>
                                                        <option value="per_unit">Per Unit</option>
                                                        <option value="flat_rate">Flat Rate</option>
                                                    </select>
                                                </td>
                                                <td className="px-4 py-3">
                                                    <input
                                                        type="date"
                                                        value={row.effectiveDate}
                                                        onChange={(e) => updateRow(index, "effectiveDate", e.target.value)}
                                                        className="text-sm border-surface-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
                                                    />
                                                </td>
                                                <td className="px-4 py-3">
                                                    <input
                                                        type="date"
                                                        value={row.expiryDate || ""}
                                                        onChange={(e) => updateRow(index, "expiryDate", e.target.value || undefined)}
                                                        className="text-sm border-surface-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
                                                    />
                                                </td>
                                                <td className="px-4 py-3 text-right">
                                                    <button
                                                        onClick={() => removeRow(index)}
                                                        className="text-red-600 hover:text-red-700"
                                                    >
                                                        Remove
                                                    </button>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        ) : (
                            <div className="p-8 text-center text-surface-500">
                                <Package className="mx-auto h-12 w-12 mb-4 opacity-50" />
                                <p>No price entries yet. Upload a CSV or add rows manually.</p>
                            </div>
                        )}

                        {uploadData.length > 0 && (
                            <div className="p-4 border-t border-surface-200 flex justify-end">
                                <button
                                    onClick={handleSubmit}
                                    disabled={uploadMutation.isPending}
                                    className="inline-flex items-center gap-2 px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                >
                                    {uploadMutation.isPending ? (
                                        <>
                                            <Loader2 className="h-4 w-4 animate-spin" />
                                            Uploading...
                                        </>
                                    ) : (
                                        <>
                                            <Upload className="h-4 w-4" />
                                            Upload {uploadData.length} Prices
                                        </>
                                    )}
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {activeTab === "history" && (
                <div className="bg-white rounded-xl border border-surface-200 shadow-sm">
                    <div className="p-4 border-b border-surface-200">
                        <h3 className="font-semibold text-surface-900">Upload History</h3>
                    </div>

                    {uploadsLoading ? (
                        <div className="p-8 text-center">
                            <Loader2 className="mx-auto h-8 w-8 animate-spin text-surface-400" />
                        </div>
                    ) : uploads?.length > 0 ? (
                        <div className="divide-y divide-surface-200">
                            {uploads.map((upload: PricingUpload) => (
                                <div key={upload.id} className="p-4 hover:bg-surface-50">
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-3">
                                            {upload.status === "completed" && (
                                                <CheckCircle className="h-5 w-5 text-green-500" />
                                            )}
                                            {upload.status === "failed" && (
                                                <AlertCircle className="h-5 w-5 text-red-500" />
                                            )}
                                            {upload.status === "partial" && (
                                                <AlertCircle className="h-5 w-5 text-yellow-500" />
                                            )}
                                            {(upload.status === "pending" || upload.status === "processing") && (
                                                <Loader2 className="h-5 w-5 animate-spin text-primary-500" />
                                            )}
                                            <div>
                                                <p className="font-medium text-surface-900">
                                                    {upload.fileName}
                                                </p>
                                                <p className="text-sm text-surface-500">
                                                    {new Date(upload.createdAt).toLocaleDateString()}
                                                </p>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <span className={cn(
                                                "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
                                                upload.status === "completed" && "bg-green-100 text-green-800",
                                                upload.status === "failed" && "bg-red-100 text-red-800",
                                                upload.status === "partial" && "bg-yellow-100 text-yellow-800",
                                                upload.status === "processing" && "bg-blue-100 text-blue-800",
                                                upload.status === "pending" && "bg-surface-100 text-surface-800"
                                            )}>
                                                {upload.status}
                                            </span>
                                            <p className="text-sm text-surface-600 mt-1">
                                                {upload.processedRecords} / {upload.totalRecords} processed
                                                {upload.failedRecords > 0 && ` (${upload.failedRecords} failed)`}
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="p-8 text-center text-surface-500">
                            <FileSpreadsheet className="mx-auto h-12 w-12 mb-4 opacity-50" />
                            <p>No upload history yet.</p>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
