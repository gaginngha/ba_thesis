import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        swiss: {
          red: "#FF0000",
          dark: "#1a1a2e",
          accent: "#0f3460",
          light: "#e8f4f8",
        },
      },
    },
  },
  plugins: [],
};

export default config;
