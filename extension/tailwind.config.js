/** @type {import('tailwindcss').Config} */
export default {
  content: ["./src/**/*.{js,ts,jsx,tsx,html}"],
  theme: {
    extend: {
      colors: {
        "risk-low": "#22c55e",
        "risk-moderate": "#eab308",
        "risk-high": "#ef4444",
      },
    },
  },
  plugins: [],
};
