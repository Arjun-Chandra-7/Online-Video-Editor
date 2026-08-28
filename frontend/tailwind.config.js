/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        editor: {
          bg: '#121316',
          panel: '#1A1C20',
          card: '#22252B',
          cardHover: '#2A2E35',
          border: '#2E323B',
          borderLight: '#3D424E',
          accent: '#3B82F6',
          accentGlow: 'rgba(59, 130, 246, 0.25)',
          gold: '#EAB308',
          textMuted: '#9CA3AF',
          textBright: '#F3F4F6',
          trackV: '#252932',
          trackA: '#1E232D',
          clipV: '#2B384E',
          clipA: '#23383B',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      }
    },
  },
  plugins: [],
}
