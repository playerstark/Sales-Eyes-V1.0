import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        maroon: {
          50: "#f8f3f4",
          100: "#f0e6e8",
          200: "#e8d4e2",
          300: "#d9b3cc",
          400: "#c27aad",
          500: "#a8548e",
          600: "#8d3b6f",
          700: "#6d2952",
          800: "#532040",
          900: "#3d1730",
          950: "#2a0f21",
        },
        black: "#0a0a0a",
      },
      animation: {
        spin: "spin 1s linear infinite",
        pulse: "pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        bounce: "bounce 1s infinite",
        slideUp: "slideUp 0.5s ease-out",
        fadeIn: "fadeIn 0.4s ease-out",
        scaleIn: "scaleIn 0.3s ease-out",
      },
      keyframes: {
        slideUp: {
          "0%": {
            opacity: "0",
            transform: "translateY(20px)",
          },
          "100%": {
            opacity: "1",
            transform: "translateY(0)",
          },
        },
        fadeIn: {
          "0%": {
            opacity: "0",
          },
          "100%": {
            opacity: "1",
          },
        },
        scaleIn: {
          "0%": {
            opacity: "0",
            transform: "scale(0.95)",
          },
          "100%": {
            opacity: "1",
            transform: "scale(1)",
          },
        },
      },
      backdropBlur: {
        xs: "2px",
      },
      boxShadow: {
        glow: "0 0 20px rgba(128, 0, 32, 0.3)",
      },
    },
  },
  plugins: [],
};

export default config;
