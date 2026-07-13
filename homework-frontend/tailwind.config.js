/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          teal:       '#2ab5a5',
          'teal-light': '#e6faf8',
          'teal-border': '#99e6dc',
          'teal-dark':  '#1a9e8f',
        },
      },
      backgroundImage: {
        'gradient-cta': 'linear-gradient(to right, #7c3aed, #a855f7, #ec4899)',
        'gradient-progress': 'linear-gradient(to right, #7c3aed, #ec4899)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
