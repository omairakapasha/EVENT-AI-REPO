import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Routes that don't require authentication
const PUBLIC_ROUTES = ['/login'];

export function proxy(request: NextRequest) {
    const { pathname } = request.nextUrl;

    // Allow static assets and Next.js internals
    if (
        pathname.startsWith('/_next') ||
        pathname.startsWith('/api') ||
        pathname.startsWith('/favicon') ||
        /\.(.*)$/.test(pathname)
    ) {
        return NextResponse.next();
    }

    // Allow public routes
    if (PUBLIC_ROUTES.some((r) => pathname === r || pathname.startsWith(`${r}/`))) {
        return NextResponse.next();
    }

    // Check for httpOnly auth cookies set by the backend
    const hasAuth =
        request.cookies.has('access_token') || request.cookies.has('refresh_token');

    if (!hasAuth) {
        return NextResponse.redirect(new URL('/login', request.url));
    }

    // Authenticated user visiting /login → redirect to dashboard
    if (pathname === '/login' && hasAuth) {
        return NextResponse.redirect(new URL('/', request.url));
    }

    return NextResponse.next();
}

export const config = {
    matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)'],
};
