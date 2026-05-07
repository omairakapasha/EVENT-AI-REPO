import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const PROTECTED_PATHS = ['/dashboard', '/bookings', '/services', '/availability', '/profile', '/verify-email'];
const PUBLIC_ONLY_PATHS = ['/login', '/register', '/forgot-password', '/reset-password'];

export function proxy(request: NextRequest) {
    const { pathname } = request.nextUrl;

    // Skip static assets and Next.js internals
    if (
        pathname.startsWith('/_next') ||
        pathname.startsWith('/api') ||
        pathname.startsWith('/favicon') ||
        pathname.includes('.')
    ) {
        return NextResponse.next();
    }

    const isAuthenticated = request.cookies.get('is-authenticated')?.value === 'true';
    const userRole = request.cookies.get('user-role')?.value;

    const isProtected = PROTECTED_PATHS.some((p) => pathname === p || pathname.startsWith(p + '/'));
    const isPublicOnly = PUBLIC_ONLY_PATHS.some((p) => pathname === p || pathname.startsWith(p + '/'));

    // Unauthenticated → redirect to login
    if (isProtected && !isAuthenticated) {
        const loginUrl = new URL('/login', request.url);
        loginUrl.searchParams.set('from', pathname);
        return NextResponse.redirect(loginUrl);
    }

    // Wrong role → redirect to register
    if (isProtected && isAuthenticated && userRole && userRole !== 'vendor' && userRole !== 'admin') {
        return NextResponse.redirect(new URL('/register', request.url));
    }

    // Authenticated vendor visiting public-only pages → redirect to dashboard
    // Exception: /register?incomplete=1 is the onboarding recovery flow.
    // Exception: plain /register — the page itself handles logout + fresh form.
    const isRegisterPage = pathname === '/register';
    const isIncompleteRegistration =
        isRegisterPage &&
        request.nextUrl.searchParams.get('incomplete') === '1';

    if (isPublicOnly && isAuthenticated && !isIncompleteRegistration && !isRegisterPage) {
        return NextResponse.redirect(new URL('/dashboard', request.url));
    }

    return NextResponse.next();
}

export const config = {
    matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
