import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        atlas: {
          bg: "#0b0f14",
          panel: "#111820",
          panelSoft: "#151f2a",
          line: "#263241",
          text: "#edf2f7",
          muted: "#97a6ba",
          teal: "#42d3b2",
          amber: "#f0b94d",
          blue: "#7bb7ff",
          rose: "#ef7b93"
        }
      },
      boxShadow: {
        panel: "0 18px 50px rgba(0, 0, 0, 0.28)"
      }
    }
  },
  plugins: []
};

export default config;
