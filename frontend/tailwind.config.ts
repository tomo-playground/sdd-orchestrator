import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontSize: {
        xs: ["0.8125rem", { lineHeight: "1.25rem" }], // 13px (was 12px)
        sm: ["0.9375rem", { lineHeight: "1.375rem" }], // 15px (was 14px)
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};

export default config;
