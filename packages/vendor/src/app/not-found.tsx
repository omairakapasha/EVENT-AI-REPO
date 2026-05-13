import Link from 'next/link';
import { Home } from 'lucide-react';

export default function NotFound() {
    return (
        <div className="flex min-h-screen items-center justify-center bg-surface-50 p-4 dark:bg-surface-950">
            <div className="w-full max-w-md text-center">
                <p className="text-8xl font-bold text-primary-600 dark:text-primary-400">404</p>
                <h1 className="mt-4 text-2xl font-bold text-surface-900 dark:text-surface-50">
                    Page not found
                </h1>
                <p className="mt-2 text-surface-500 dark:text-surface-400">
                    The page you&apos;re looking for doesn&apos;t exist or has been moved.
                </p>
                <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:justify-center">
                    <Link
                        href="/dashboard"
                        className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary-700"
                    >
                        <Home className="h-4 w-4" />
                        Go to Dashboard
                    </Link>
                </div>
            </div>
        </div>
    );
}
