import './globals.css';
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { Providers } from './providers';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
    title: 'Vendor Portal - Event Orchestrator',
    description: 'Manage your vendor profile, services, and bookings',
    keywords: ['vendor', 'event', 'management', 'services', 'bookings'],
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en" suppressHydrationWarning>
            <body className={inter.className} suppressHydrationWarning>
                <Providers>{children}</Providers>
            </body>
        </html>
    );
}
