/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
        './src/components/**/*.{js,ts,jsx,tsx,mdx}',
        './src/app/**/*.{js,ts,jsx,tsx,mdx}',
    ],
    darkMode: 'class',
    theme: {
        extend: {
            colors: {
                // ── Brand palette ─────────────────────────────────────────
                // Derived from: #96A78D (sage), #EFECE3 (cream), #1A3D64 (navy)
                //
                // primary  → navy  #1A3D64  (CTAs, links, headings)
                // accent   → sage  #96A78D  (highlights, badges, icons)
                // canvas   → cream #EFECE3  (page backgrounds, cards)

                primary: {
                    50:  '#edf3fa',
                    100: '#d0e2f2',
                    200: '#a3c5e5',
                    300: '#6fa3d4',
                    400: '#4280be',
                    500: '#2260a0',
                    600: '#1a3d64', // ← anchor: #1A3D64
                    700: '#153252',
                    800: '#0f2540',
                    900: '#091829',
                    950: '#040c15',
                },

                // Sage green accent — #96A78D is the 400/mid stop
                accent: {
                    50:  '#f4f6f2',
                    100: '#e6ebe2',
                    200: '#cdd7c6',
                    300: '#b3c3aa',
                    400: '#96a78d', // ← anchor: #96A78D
                    500: '#7a8f71',
                    600: '#617558',
                    700: '#4d5d45',
                    800: '#394534',
                    900: '#252e22',
                    950: '#131811',
                },

                // Warm cream canvas — #EFECE3 is the 100 stop
                canvas: {
                    50:  '#faf9f6',
                    100: '#efece3', // ← anchor: #EFECE3
                    200: '#dedad0',
                    300: '#cac5b8',
                    400: '#b0a99a',
                    500: '#948d7e',
                    600: '#787063',
                    700: '#5e574d',
                    800: '#443f38',
                    900: '#2b2823',
                    950: '#161411',
                },

                // Success colors (kept neutral — green already in accent)
                success: {
                    50: '#ecfdf5',
                    100: '#d1fae5',
                    200: '#a7f3d0',
                    300: '#6ee7b7',
                    400: '#34d399',
                    500: '#10b981',
                    600: '#059669',
                    700: '#047857',
                    800: '#065f46',
                    900: '#064e3b',
                },
                // Warning colors
                warning: {
                    50: '#fffbeb',
                    100: '#fef3c7',
                    200: '#fde68a',
                    300: '#fcd34d',
                    400: '#fbbf24',
                    500: '#f59e0b',
                    600: '#d97706',
                    700: '#b45309',
                    800: '#92400e',
                    900: '#78350f',
                },
                // Error colors
                error: {
                    50: '#fef2f2',
                    100: '#fee2e2',
                    200: '#fecaca',
                    300: '#fca5a5',
                    400: '#f87171',
                    500: '#ef4444',
                    600: '#dc2626',
                    700: '#b91c1c',
                    800: '#991b1b',
                    900: '#7f1d1d',
                },
                // Surface — warm-tinted neutrals (replaces cold zinc)
                surface: {
                    50:  '#faf9f6',
                    100: '#f2f0ea',
                    200: '#e3e0d8',
                    300: '#ccc8be',
                    400: '#aaa59a',
                    500: '#888278',
                    600: '#6a6560',
                    700: '#504d48',
                    800: '#363330',
                    900: '#1e1c1a',
                    950: '#0f0e0d',
                },
            },
            fontFamily: {
                sans: ['Inter', 'system-ui', 'sans-serif'],
                mono: ['JetBrains Mono', 'Menlo', 'monospace'],
            },
            fontSize: {
                '2xs': ['0.625rem', { lineHeight: '0.75rem' }],
            },
            boxShadow: {
                'glow':    '0 0 20px rgba(26, 61, 100, 0.15)',
                'glow-lg': '0 0 40px rgba(26, 61, 100, 0.25)',
                'glow-accent': '0 0 20px rgba(150, 167, 141, 0.20)',
            },
            animation: {
                'fade-in': 'fadeIn 0.3s ease-out',
                'slide-up': 'slideUp 0.3s ease-out',
                'slide-down': 'slideDown 0.3s ease-out',
                'scale-in': 'scaleIn 0.2s ease-out',
                'spin-slow': 'spin 3s linear infinite',
                'pulse-slow': 'pulse 3s ease-in-out infinite',
            },
            keyframes: {
                fadeIn: {
                    '0%': { opacity: '0' },
                    '100%': { opacity: '1' },
                },
                slideUp: {
                    '0%': { opacity: '0', transform: 'translateY(10px)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' },
                },
                slideDown: {
                    '0%': { opacity: '0', transform: 'translateY(-10px)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' },
                },
                scaleIn: {
                    '0%': { opacity: '0', transform: 'scale(0.95)' },
                    '100%': { opacity: '1', transform: 'scale(1)' },
                },
            },
            backdropBlur: {
                xs: '2px',
            },
        },
    },
    plugins: [],
};
