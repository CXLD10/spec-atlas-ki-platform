import type { Config } from 'tailwindcss'

export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // GitHub Dark theme (default)
        'github-dark': {
          bg: '#0d1117',
          surface: '#161b22',
          border: '#30363d',
          text: '#c9d1d9',
          'text-secondary': '#8b949e',
          accent: '#58a6ff',
          'l1': '#58a6ff',      // Code layer - cyan
          'l3': '#3fb950',      // Specs layer - green
          'l4': '#d291f2',      // Groups layer - purple
          success: '#3fb950',
          warning: '#d29922',
          danger: '#f85149',
        },
        // GitHub Light theme
        'github-light': {
          bg: '#ffffff',
          surface: '#f6f8fa',
          border: '#d0d7de',
          text: '#24292f',
          'text-secondary': '#57606a',
          accent: '#0969da',
          'l1': '#0969da',      // Code layer - blue
          'l3': '#1a7f37',      // Specs layer - green
          'l4': '#8957e5',      // Groups layer - purple
          success: '#1a7f37',
          warning: '#9e6a03',
          danger: '#da3633',
        },
      },
      backgroundColor: {
        primary: 'var(--bg)',
        surface: 'var(--surface)',
      },
      textColor: {
        primary: 'var(--text)',
        secondary: 'var(--text-secondary)',
      },
      spacing: {
        0: '0',
        1: '0.25rem',
        2: '0.5rem',
        3: '0.75rem',
        4: '1rem',
        6: '1.5rem',
        8: '2rem',
        12: '3rem',
        16: '4rem',
        24: '6rem',
        32: '8rem',
        48: '12rem',
        64: '16rem',
      },
      fontFamily: {
        display: ['Space Grotesk', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
        system: ['-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'sans-serif'],
      },
    },
  },
  plugins: [],
  important: true,
} satisfies Config
