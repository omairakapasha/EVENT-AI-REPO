/** @type {import('next').NextConfig} */
const nextConfig = {
    output: 'standalone',
    reactStrictMode: true,
    // Move dev cache to /tmp to avoid slow filesystem penalty on local drives
    distDir: process.env.NODE_ENV === 'development' ? '/tmp/next-vendor' : '.next',
    images: {
        remotePatterns: [
            { protocol: 'http', hostname: 'localhost' },
            { protocol: 'https', hostname: '**' },
        ],
    },
};

module.exports = nextConfig;
