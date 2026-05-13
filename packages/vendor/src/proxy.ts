import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Routes that require no authentication
const PUBLIC_ROUTES = [
    '/',
    '/login',
    '/register',
    '/forgot-password',
    '/reset-password',
    '/verify-email',
    '/auth/callback',
];

// Routes that authenticated users should not revisit
const AUTH_ONLY_ROUTES = ['/login', '/register', '/forgot-password', '/reset-password'];

// Query params that indicate an error/access-denied redirect — always allow through
const ERROR_PARAMS = ['error', 'incomplete'];

function isPublicRoute(pathname: string): boolean {
    return PUBLIC_ROUTES.some(
        (route) => pathname === route || pathname.startsWith(`${route}/`)
    );
}

function isAuthOnlyRoute(pathname: string): boolean {
    return AUTH_ONLY_ROUTES.some(
        (route) => pathname === route || pathname.startsWith(`${route}/`)
    );
}

/**
 * Next.js 16 proxy (replaces deprecated middleware.ts).
 * Runs on Node.js runtime — edge runtime is NOT supported in proxy.
 *
 * Guards:
 *  1. Unauthenticated users → /login
 *  2. Authenticated users on auth-only routes → /dashboard
 *
 * Role and vendor-status checks (require DB state) are handled
 * client-side in VendorLayout after the auth store hydrates.
 */
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

    // Check for httpOnly auth cookies set by the backend
    const hasAuth =
        request.cookies.has('access_token') || request.cookies.has('refresh_token');

    // Unauthenticated user trying to access a protected route → login
    if (!isPublicRoute(pathname) && !hasAuth) {
        const loginUrl = new URL('/login', request.url);
        loginUrl.searchParams.set('redirect', pathname);
        return NextResponse.redirect(loginUrl);
    }

    // Authenticated user visiting login/register → dashboard
    // Exception: allow through if the URL carries an error/access-denied param
    // (e.g. /login?error=Access+denied) so the user sees the message.
    if (isAuthOnlyRoute(pathname) && hasAuth) {
        const hasErrorParam = ERROR_PARAMS.some((p) => request.nextUrl.searchParams.has(p));
        if (!hasErrorParam) {
            return NextResponse.redirect(new URL('/dashboard', request.url));
        }
    }

    return NextResponse.next();
}

export const config = {
    matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)'],
};
