/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Deep, warm knowledge theme
        ink: {
          50: '#f7f6f4',
          100: '#efeee9',
          200: '#dddad2',
          300: '#c6c1b4',
          400: '#aca495',
          500: '#9a8f7e',
          600: '#8d8072',
          700: '#766a5f',
          800: '#625850',
          900: '#514943',
          950: '#2b2622',
        },
        parchment: {
          50: '#fdfcfa',
          100: '#faf8f3',
          200: '#f5f1e8',
          300: '#ede6d7',
          400: '#e2d8c3',
          500: '#d4c7ab',
          600: '#c2b08d',
          700: '#a99371',
          800: '#8b785d',
          900: '#73644e',
        },
        ember: {
          50: '#fef6ee',
          100: '#fdead7',
          200: '#fad1ae',
          300: '#f6b07a',
          400: '#f18544',
          500: '#ed6520',
          600: '#de4c16',
          700: '#b83814',
          800: '#932e18',
          900: '#772917',
        },
        sage: {
          50: '#f4f7f4',
          100: '#e5ebe5',
          200: '#ccd8cc',
          300: '#a6bda6',
          400: '#7a9c7a',
          500: '#5a7f5a',
          600: '#466546',
          700: '#3a513a',
          800: '#314231',
          900: '#29372a',
        }
      },
      fontFamily: {
        'display': ['Playfair Display', 'Georgia', 'serif'],
        'body': ['Source Serif Pro', 'Georgia', 'serif'],
        'mono': ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        'inner-glow': 'inset 0 2px 4px 0 rgb(0 0 0 / 0.05)',
        'paper': '0 1px 3px 0 rgb(0 0 0 / 0.08), 0 1px 2px -1px rgb(0 0 0 / 0.08)',
        'elevated': '0 4px 6px -1px rgb(0 0 0 / 0.08), 0 2px 4px -2px rgb(0 0 0 / 0.06)',
        'floating': '0 10px 15px -3px rgb(0 0 0 / 0.08), 0 4px 6px -4px rgb(0 0 0 / 0.06)',
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'pulse-subtle': 'pulseSubtle 2s ease-in-out infinite',
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
        pulseSubtle: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
      },
    },
  },
  plugins: [],
}
