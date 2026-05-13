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

    // Check for httpOnly auth cookies set by the backend
    const hasAuth =
        request.cookies.has('access_token') || request.cookies.has('refresh_token');

    // Unauthenticated → redirect to login
    if (!hasAuth) {
        const loginUrl = new URL('/login', request.url);
        loginUrl.searchParams.set('callbackUrl', pathname);
        return NextResponse.redirect(loginUrl);
    }

    // Authenticated user visiting login/register → dashboard
    if (AUTH_ONLY_ROUTES.includes(pathname) && hasAuth) {
        return NextResponse.redirect(new URL('/dashboard', request.url));
    }

    return NextResponse.next();
}

export const config = {
    matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)'],
};
