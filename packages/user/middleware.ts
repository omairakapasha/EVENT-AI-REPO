import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
    // COMPLETELY DISABLED - OAuth uses localStorage tokens, not cookies
    // All auth checks happen client-side in API interceptors
    console.log('[Middleware] Path:', request.nextUrl.pathname, '- Allowing through');
    return NextResponse.next();
}

export const config = {
    matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)'],
};
