import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Backend address for the /api proxy. Override with LYRIS_API_URL if the backend runs elsewhere.
const apiTarget = process.env.LYRIS_API_URL ?? process.env.NORA_API_URL ?? "http://127.0.0.1:8000";

// This folder (frontend/). Vite may only serve files from here (docs/auth.md §3.8).
const frontendDir = fileURLToPath(new URL(".", import.meta.url));

// /api proxy (docs/auth.md §3.3, §3.7):
// - xfwd: Vite appends the caller's real address to X-Forwarded-For / X-Forwarded-Proto; the backend reads the
//   LAST element (uvicorn runs with --no-proxy-headers).
// - no changeOrigin: the backend must see the browser's original Host header for the Origin == Host CSRF check.
const apiProxy = {
  "/api": { target: apiTarget, xfwd: true },
};

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: apiProxy,
    // Never set allowedHosts: true (DNS rebinding). Phase 6 adds only this Mac's *.ts.net name.
    fs: {
      // Pin the workspace root: a package.json with "workspaces" higher up (repo root, home folder) would
      // otherwise let /@fs/... read data/lyris.db from the LAN without logging in.
      strict: true,
      allow: [frontendDir],
      // Vite's defaults (.env, certificates, .git) plus the database and anything under data/.
      deny: [".env", ".env.*", "*.{crt,pem}", "**/.git/**", "**/*.db", "**/*.db-wal", "**/*.db-shm", "**/data/**"],
    },
  },
  preview: {
    port: 5173,
    strictPort: true,
    proxy: apiProxy,
  },
});
