import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#f5f1e8",
        ink: "#25241f",
        muted: "#777267",
        accent: "#bc6746",
        card: "#fffdf8"
      },
      boxShadow: { soft: "0 18px 55px rgba(65, 56, 43, 0.08)" }
    }
  },
  plugins: []
};

export default config;
