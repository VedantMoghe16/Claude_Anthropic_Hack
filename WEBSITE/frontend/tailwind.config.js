/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      boxShadow: {
        card: "0 10px 28px -14px rgba(15, 23, 42, 0.3)",
      },
    },
  },
  plugins: [],
}

