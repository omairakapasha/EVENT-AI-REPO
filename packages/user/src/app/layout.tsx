import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Event-AI - Intelligent Event Planning Platform",
  description: "Discover vendors, plan events, and book services with AI-powered recommendations for weddings, birthdays, and corporate events.",
};

import { Providers } from "./providers";
import { LayoutShell } from "@/components/layout-shell";
import { SocketProvider } from "@/components/socket-provider";
import { NotificationProvider } from "@/components/notification-provider";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-gray-50`}
        suppressHydrationWarning
      >
        <Providers>
          <SocketProvider>
            <NotificationProvider>
              <LayoutShell>
                {children}
              </LayoutShell>
            </NotificationProvider>
          </SocketProvider>
        </Providers>
      </body>
    </html>
  );
}
