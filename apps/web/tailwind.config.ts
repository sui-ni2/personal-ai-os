import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        surface: "var(--surface)",
        "surface-subtle": "var(--surface-subtle)",
        "surface-elevated": "var(--surface-elevated)",
        sidebar: "var(--sidebar)",
        text: {
          primary: "var(--text-primary)",
          secondary: "var(--text-secondary)",
          tertiary: "var(--text-tertiary)",
        },
        line: "var(--border)",
        "line-strong": "var(--border-strong)",
        accent: {
          DEFAULT: "var(--accent)",
          hover: "var(--accent-hover)",
          soft: "var(--accent-soft)",
        },
        success: "var(--success)",
        warning: "var(--warning)",
        danger: "var(--danger)",
      },
      borderRadius: {
        small: "var(--radius-small)",
        control: "var(--radius-control)",
        card: "var(--radius-card)",
        large: "var(--radius-large)",
      },
      boxShadow: {
        soft: "var(--shadow-soft)",
        composer: "var(--shadow-composer)",
      },
      fontFamily: {
        sans: [
          "MiSans",
          "SF Pro Text",
          "SF Pro Display",
          "PingFang SC",
          "system-ui",
          "Segoe UI",
          "sans-serif",
        ],
        mono: ["JetBrains Mono", "SFMono-Regular", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
