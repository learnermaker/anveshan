/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#08090a',
        surface: '#0b0d0e',
        'surface-dim': '#070809',
        'surface-bright': '#1a1d20',
        'surface-container-lowest': '#050607',
        'surface-container-low': '#0f1214',
        'surface-container': '#14181a',
        'surface-container-high': '#1c2124',
        'surface-container-highest': '#242a2e',
        // used throughout the V0 components but previously undefined
        'surface-elevated': '#14181a',
        'on-surface': '#edece8',
        'on-surface-variant': '#a9afb4',
        outline: '#2e353b',
        'outline-variant': '#1a1e22',
        
        // Semantic Precision Accents
        'cadmium-amber': '#e67e22',
        'primary-container': '#e67e22',
        'transmission-emerald': '#10b981',
        'secondary-container': '#00a572',
        'caliper-cyan': '#00e5ff',
        'divergence-crimson': '#f87171',
      },
      fontFamily: {
        serif: ['Playfair Display', 'serif'],
        sans: ['Plus Jakarta Sans', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      borderRadius: {
        DEFAULT: '0.125rem',
        sm: '0.125rem',
        md: '0.25rem',
        lg: '0.375rem',
        xl: '0.5rem',
      },
      maxWidth: {
        workbench: '1440px',
      },
      keyframes: {
        'fade-in': { from: { opacity: '0', transform: 'translateY(4px)' }, to: { opacity: '1', transform: 'none' } },
      },
      animation: {
        'fade-in': 'fade-in 0.25s ease-out both',
      },
    },
  },
  plugins: [],
}
