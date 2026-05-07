import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Public routes that don't require authentication
const PUBLIC_ROUTES = [
    '/login',
    '/register',
    '/forgot-password',
    '/reset-password',
    '/verify-email',
    '/auth/callback',
    '/api',  // API routes are handled separately
    '/_next',  // Next.js internal
    '/favicon',
    '/static',
];

// Check if a path is public
function isPublicRoute(path: string): boolean {
    return PUBLIC_ROUTES.some(route =>
        path === route ||
        path.startsWith(`${route}/`) ||
        path.startsWith(route)
    );
}

export function middleware(request: NextRequest) {
    const { pathname } = request.nextUrl;

    // Allow public assets and routes
    if (isPublicRoute(pathname)) {
        return NextResponse.next();
    }

    // Check for auth cookie (httpOnly cookie set by backend)
    const authCookie = request.cookies.get('access_token') || request.cookies.get('refresh_token');

    // If no auth cookie and trying to access protected route, redirect to login
    if (!authCookie) {
        const loginUrl = new URL('/login', request.url);
        // Add the original URL as a redirect parameter
        loginUrl.searchParams.set('redirect', pathname);
        return NextResponse.redirect(loginUrl);
    }

    // Allow the request to proceed
    return NextResponse.next();
}

// Configure which routes the middleware runs on
export const config = {
    matcher: [
        /*
         * Match all request paths except:
         * - _next/static (static files)
         * - _next/image (image optimization files)
         * - favicon.ico (favicon file)
         * - public folder
         */
        '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
    ],
};
