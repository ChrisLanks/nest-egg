/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { visualizer } from "rollup-plugin-visualizer";

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    // Generate bundle analysis report: npm run build && open stats.html
    visualizer({
      filename: "stats.html",
      open: false,
      gzipSize: true,
      brotliSize: true,
    }),
  ],
  test: {
    environment: "node",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
    exclude: ["src/App.test.tsx"],
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          "vendor-react": ["react", "react-dom", "react-router-dom"],
          "vendor-charts": ["recharts"],
          "vendor-ui": [
            "@chakra-ui/react",
            "@emotion/react",
            "@emotion/styled",
            "framer-motion",
          ],
          "vendor-query": ["@tanstack/react-query"],
        },
      },
    },
  },
  server: {
    // Proxy /api → backend so the httpOnly refresh cookie is treated as same-origin
    // in dev (frontend: 5173, backend: 8000).
    proxy: {
      "/api": {
        // In Docker Compose the backend is reachable via its service name.
        // Direct npm run dev: VITE_PROXY_TARGET is unset → falls back to localhost.
        target: process.env.VITE_PROXY_TARGET || "http://localhost:8000",
        changeOrigin: true,
        // Follow 307 redirects server-side so the browser never sees a cross-origin
        // redirect (which would cause Chrome to strip the Authorization header).
        followRedirects: true,
      },
    },
  },
});
