import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Routes that don't require authentication
const PUBLIC_ROUTES = ['/', '/login', '/signup', '/register', '/marketplace', '/auth/callback'];

// Route prefixes that are also public
const PUBLIC_PREFIXES = ['/marketplace/'];

// Routes that authenticated users should not revisit
const AUTH_ONLY_ROUTES = ['/login', '/signup', '/register'];

export function proxy(request: NextRequest) {
    const { pathname } = request.nextUrl;

    // Skip Next.js internals and static assets
    if (
        pathname.startsWith('/_next') ||
        pathname.startsWith('/api') ||
        pathname.startsWith('/favicon') ||
        /\.(.*)$/.test(pathname)
    ) {
        return NextResponse.next();
    }

    // Allow public routes and prefixes
    if (
        PUBLIC_ROUTES.includes(pathname) ||
        PUBLIC_PREFIXES.some((prefix) => pathname.startsWith(prefix))
    ) {
        return NextResponse.next();
    }

    // For OAuth flow, tokens are in localStorage (client-side), not cookies
    // Let the client-side handle auth checks via API 401 responses
    // Middleware doesn't have access to localStorage, so skip auth checks here
    return NextResponse.next();
}

export const config = {
    matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)'],
};
