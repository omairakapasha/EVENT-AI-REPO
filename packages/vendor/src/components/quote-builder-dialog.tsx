'use client';

import { useState } from 'react';
import { Loader2, Plus, Trash2, X } from 'lucide-react';
import {
    useCreateQuote,
    type CreateQuotePayload,
    type QuoteLineItem,
} from '@/lib/hooks/use-quotes';
import { useSendQuoteFromInquiry } from '@/lib/hooks/use-inquiries';
import { cn } from '@/lib/utils';

interface QuoteBuilderDialogProps {
    bookingId?: string;
    inquiryId?: string;
    open: boolean;
    onClose: () => void;
}

interface LineRow {
    description: string;
    quantity: string;
    unit_price: string;
}

const _emptyRow: LineRow = { description: '', quantity: '1', unit_price: '0' };

function _rowTotal(row: LineRow): number {
    const qty = parseFloat(row.quantity || '0');
    const price = parseFloat(row.unit_price || '0');
    if (Number.isNaN(qty) || Number.isNaN(price)) return 0;
    return qty * price;
}

export function QuoteBuilderDialog({ bookingId, inquiryId, open, onClose }: QuoteBuilderDialogProps) {
    const [rows, setRows] = useState<LineRow[]>([{ ..._emptyRow }]);
    const [depositRequired, setDepositRequired] = useState('0');
    const [validUntil, setValidUntil] = useState('');
    const [notes, setNotes] = useState('');

    const createFromBooking = useCreateQuote(bookingId ?? '');
    const createFromInquiry = useSendQuoteFromInquiry(inquiryId ?? '');
    const create = inquiryId ? createFromInquiry : createFromBooking;

    if (!open) return null;

    const subtotal = rows.reduce((sum, row) => sum + _rowTotal(row), 0);
    const depositValue = parseFloat(depositRequired || '0') || 0;

    const canSubmit =
        rows.length > 0 &&
        rows.every((r) => r.description.trim() !== '' && _rowTotal(r) >= 0) &&
        subtotal > 0 &&
        !create.isPending;

    const addRow = () => setRows((prev) => [...prev, { ..._emptyRow }]);
    const removeRow = (idx: number) =>
        setRows((prev) => (prev.length === 1 ? prev : prev.filter((_, i) => i !== idx)));

    const updateRow = (idx: number, field: keyof LineRow, value: string) =>
        setRows((prev) => prev.map((r, i) => (i === idx ? { ...r, [field]: value } : r)));

    const handleSubmit = async () => {
        const line_items: QuoteLineItem[] = rows.map((r) => {
            const quantity = parseFloat(r.quantity) || 1;
            const unit_price = parseFloat(r.unit_price) || 0;
            return {
                description: r.description.trim(),
                quantity,
                unit_price,
                total: quantity * unit_price,
            };
        });

        const payload: CreateQuotePayload = {
            line_items,
            subtotal,
            deposit_required: depositValue,
            currency: 'PKR',
            valid_until: validUntil ? new Date(validUntil).toISOString() : null,
            notes: notes.trim() || null,
        };

        await create.mutateAsync(payload);
        // Reset and close on success
        setRows([{ ..._emptyRow }]);
        setDepositRequired('0');
        setValidUntil('');
        setNotes('');
        onClose();
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
            <div className="w-full max-w-2xl rounded-xl bg-white p-6 shadow-xl dark:bg-surface-900">
                <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold text-surface-900 dark:text-surface-50">
                        Send Quote
                    </h3>
                    <button
                        onClick={onClose}
                        className="rounded-md p-1 text-surface-500 hover:bg-surface-100 dark:hover:bg-surface-800"
                    >
                        <X className="h-5 w-5" />
                    </button>
                </div>
                <p className="mt-1 text-sm text-surface-500">
                    Build a quote with line items. Customer will see this on their booking.
                </p>

                <div className="mt-5 space-y-4">
                    <div className="space-y-2">
                        <div className="grid grid-cols-12 gap-2 text-xs font-medium uppercase tracking-wide text-surface-500">
                            <div className="col-span-6">Description</div>
                            <div className="col-span-2 text-right">Qty</div>
                            <div className="col-span-3 text-right">Unit (PKR)</div>
                            <div className="col-span-1" />
                        </div>
                        {rows.map((row, idx) => (
                            <div key={idx} className="grid grid-cols-12 items-center gap-2">
                                <input
                                    value={row.description}
                                    onChange={(e) => updateRow(idx, 'description', e.target.value)}
                                    placeholder="e.g. Photography package — 6 hours"
                                    className="col-span-6 rounded-lg border border-surface-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none dark:border-surface-700 dark:bg-surface-800"
                                />
                                <input
                                    type="number"
                                    min="1"
                                    value={row.quantity}
                                    onChange={(e) => updateRow(idx, 'quantity', e.target.value)}
                                    className="col-span-2 rounded-lg border border-surface-300 px-3 py-2 text-right text-sm focus:border-primary-500 focus:outline-none dark:border-surface-700 dark:bg-surface-800"
                                />
                                <input
                                    type="number"
                                    min="0"
                                    step="100"
                                    value={row.unit_price}
                                    onChange={(e) => updateRow(idx, 'unit_price', e.target.value)}
                                    className="col-span-3 rounded-lg border border-surface-300 px-3 py-2 text-right text-sm focus:border-primary-500 focus:outline-none dark:border-surface-700 dark:bg-surface-800"
                                />
                                <button
                                    onClick={() => removeRow(idx)}
                                    disabled={rows.length === 1}
                                    className="col-span-1 flex justify-center text-surface-400 hover:text-red-600 disabled:opacity-30"
                                >
                                    <Trash2 className="h-4 w-4" />
                                </button>
                            </div>
                        ))}
                        <button
                            onClick={addRow}
                            className="flex items-center gap-1 text-sm text-primary-600 hover:text-primary-700"
                        >
                            <Plus className="h-4 w-4" /> Add line item
                        </button>
                    </div>

                    <div className="grid grid-cols-2 gap-4 border-t border-surface-200 pt-4 dark:border-surface-800">
                        <div>
                            <label className="block text-xs font-medium uppercase tracking-wide text-surface-500">
                                Deposit required (PKR)
                            </label>
                            <input
                                type="number"
                                min="0"
                                step="500"
                                value={depositRequired}
                                onChange={(e) => setDepositRequired(e.target.value)}
                                className="mt-1 w-full rounded-lg border border-surface-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none dark:border-surface-700 dark:bg-surface-800"
                            />
                        </div>
                        <div>
                            <label className="block text-xs font-medium uppercase tracking-wide text-surface-500">
                                Valid until
                            </label>
                            <input
                                type="date"
                                value={validUntil}
                                onChange={(e) => setValidUntil(e.target.value)}
                                className="mt-1 w-full rounded-lg border border-surface-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none dark:border-surface-700 dark:bg-surface-800"
                            />
                        </div>
                    </div>

                    <div>
                        <label className="block text-xs font-medium uppercase tracking-wide text-surface-500">
                            Notes (optional)
                        </label>
                        <textarea
                            value={notes}
                            onChange={(e) => setNotes(e.target.value)}
                            rows={2}
                            placeholder="Inclusions, terms, anything the customer should know."
                            className="mt-1 w-full rounded-lg border border-surface-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none dark:border-surface-700 dark:bg-surface-800"
                        />
                    </div>

                    <div className="flex items-center justify-between border-t border-surface-200 pt-4 text-sm dark:border-surface-800">
                        <div>
                            <p className="text-surface-500">Subtotal</p>
                            <p className="text-xl font-semibold text-surface-900 dark:text-surface-50">
                                PKR {subtotal.toLocaleString()}
                            </p>
                        </div>
                        <div className="flex gap-2">
                            <button
                                onClick={onClose}
                                className="rounded-lg border border-surface-300 px-4 py-2 text-sm hover:bg-surface-50 dark:border-surface-700 dark:hover:bg-surface-800"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleSubmit}
                                disabled={!canSubmit}
                                className={cn(
                                    'flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700',
                                    !canSubmit && 'cursor-not-allowed opacity-50'
                                )}
                            >
                                {create.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                                Send Quote
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
