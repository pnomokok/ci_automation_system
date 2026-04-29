/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      colors: {
        dark: {
          950: '#0d1117',
          900: '#161b22',
          800: '#1c2128',
          700: '#21262d',
          600: '#30363d',
          500: '#484f58',
        },
        status: {
          queued:   { bg: '#78350f', text: '#fcd34d', border: '#92400e' },
          running:  { bg: '#1e3a5f', text: '#93c5fd', border: '#1d4ed8' },
          success:  { bg: '#14532d', text: '#86efac', border: '#166534' },
          failed:   { bg: '#7f1d1d', text: '#fca5a5', border: '#991b1b' },
          stopped:  { bg: '#1f2937', text: '#9ca3af', border: '#374151' },
        },
      },
      animation: {
        'pulse-slow': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
};
