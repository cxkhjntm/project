/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
          950: '#172554',
        },
        aqua: {
          50: '#f0fdfa',
          100: '#ccfbf1',
          200: '#99f6e4',
          300: '#5eead4',
          400: '#2dd4bf',
          500: '#14b8a6',
          600: '#0d9488',
          700: '#0f766e',
          800: '#115e59',
          900: '#134e4a',
          950: '#042f2e',
        },
        expert: {
          orchestrator: '#8b5cf6',
          pm: '#3b82f6',
          architect: '#10b981',
          doc: '#f59e0b',
        },
      },
      transitionDuration: {
        'snappy': '150ms',
      },
      transitionTimingFunction: {
        'snappy': 'cubic-bezier(0.16, 1, 0.3, 1)',
      },
      boxShadow: {
        'glass': '0 8px 32px 0 rgba(148, 163, 184, 0.08)',
        'glass-hover': '0 12px 40px 0 rgba(14, 165, 233, 0.12)',
        'glow-aqua': '0 0 15px 1px rgba(45, 212, 191, 0.2)',
      },
      animation: {
        'shimmer': 'shimmer 2s infinite',
        'thinking': 'thinking 1.5s ease-in-out infinite',
        'float-slow': 'floatSlow 12s ease-in-out infinite',
        'float-reverse': 'floatReverse 16s ease-in-out infinite',
      },
      keyframes: {
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        thinking: {
          '0%, 100%': { opacity: '0.4' },
          '50%': { opacity: '1' },
        },
        floatSlow: {
          '0%, 100%': { transform: 'translate(0px, 0px) scale(1)' },
          '50%': { transform: 'translate(40px, -60px) scale(1.1)' },
        },
        floatReverse: {
          '0%, 100%': { transform: 'translate(0px, 0px) scale(1)' },
          '50%': { transform: 'translate(-50px, 50px) scale(0.95)' },
        },
      },
    },
  },
  plugins: [],
}
