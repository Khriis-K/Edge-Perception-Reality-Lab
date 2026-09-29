import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// The dev server's origin must match VITE_DEV_ORIGINS in backend/app.py (the CORS allow-list).
export default defineConfig({
  plugins: [react()],
  server: { host: "127.0.0.1", port: 5173, strictPort: true },
  // Unit tests only; e2e/ holds the Playwright suite.
  test: { include: ["src/**/*.test.{ts,tsx}"] },
});
