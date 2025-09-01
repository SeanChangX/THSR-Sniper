/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // ROG Gaming color scheme
        rog: {
          primary: '#ff0050',
          'primary-dark': '#e60045',
          'primary-light': '#ff3377',
          secondary: '#1a1a1a',
          accent: '#ff6600',
          success: '#00ff88',
          warning: '#ffaa00',
          danger: '#ff3366',
          info: '#2196f3',
        },
        bg: {
          primary: '#0a0a0a',
          secondary: '#1f1f1f',
          tertiary: '#2a2a2a',
          card: '#1f1f1f',
          input: '#2d2d2d',
        },
        text: {
          primary: '#ffffff',
          secondary: '#cccccc',
          muted: '#888888',
        }
      },
      fontFamily: {
        gaming: ['Orbitron', 'monospace'],
        body: ['Rajdhani', 'sans-serif'],
      },
      animation: {
        'pulse-rog': 'pulse-rog 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        'pulse-rog': {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0.5 }
        }
      }
    },
  },
  plugins: [],
}
