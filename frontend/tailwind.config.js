/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#3b82f6', // Azul profesional
        secondary: '#1e40af',
        accent: '#f59e0b', // Naranja escolar
        danger: '#ef4444',
      }
    },
  },
  plugins: [],
}
