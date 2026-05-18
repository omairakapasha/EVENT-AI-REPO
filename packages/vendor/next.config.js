/** @type {import('next').NextConfig} */
const nextConfig = {
    output: 'standalone',
    reactStrictMode: true,
    // Move dev cache out of the default .next to avoid conflicts with Docker build output.
    // Uses a local .next-dev folder (works on Linux, macOS, and Windows).
    distDir: process.env.NODE_ENV === 'development' ? '.next-dev' : '.next',
    images: {
        remotePatterns: [
            { protocol: 'http', hostname: 'localhost' },
            { protocol: 'https', hostname: '**' },
        ],
    },

    // Security headers — OWASP Secure Headers baseline (constitution §IX)
    async headers() {
        return [
            {
                source: '/(.*)',
                headers: [
                    // Prevent MIME-type sniffing
                    { key: 'X-Content-Type-Options', value: 'nosniff' },
                    // Block clickjacking via iframes
                    { key: 'X-Frame-Options', value: 'DENY' },
                    // Limit referrer leakage
                    { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
                    // Restrict browser feature access
                    { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
                    // Enforce HTTPS (only effective in production behind HTTPS)
                    { key: 'Strict-Transport-Security', value: 'max-age=63072000; includeSubDomains; preload' },
                ],
            },
        ];
    },
};

module.exports = nextConfig;
