/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'Fira Sans', 'ui-sans-serif', 'system-ui'],
        mono: ['Fira Code', 'ui-monospace', 'SFMono-Regular']
      },
      colors: {
        ink: '#0F172A',
        panel: '#111827',
        panel2: '#172033',
        line: '#26364F',
        run: '#22C55E',
        warn: '#F59E0B',
        bad: '#EF4444'
      }
    }
  },
  plugins: []
};
