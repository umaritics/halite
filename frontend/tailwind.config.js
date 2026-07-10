/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        accent: {
          DEFAULT: '#E8650A',
          hover: '#FF7A1A',
        },
        surface: {
          dark: '#0D0D0D',
          'dark-alt': '#111111',
          light: '#F0F0F0',
          'light-alt': '#E8E8E8',
        },
        border: {
          dark: '#1F1F1F',
          light: '#CCCCCC',
          'light-alt': '#DDDDDD',
        },
        text: {
          primary: {
            dark: '#F5F5F5',
            light: '#0A0A0A',
          },
          secondary: {
            dark: '#888888',
            light: '#555555',
          },
          muted: '#555555',
        },
        section: {
          dark: '#0A0A0A',
          light: '#F5F5F5',
        },
      },
      fontFamily: {
        display: ['"Space Grotesk"', 'system-ui', 'sans-serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
        wordmark: ['"Ethnocentric Rg"', '"Ethnocentric"', 'sans-serif'],
      },
      letterSpacing: {
        brand: '-0.03em',
        eyebrow: '0.12em',
      },
    },
  },
  plugins: [],
};
