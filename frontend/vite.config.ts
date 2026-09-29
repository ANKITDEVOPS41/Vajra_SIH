import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { env } from "node:process";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": env.VAJRA_API_TARGET || "http://127.0.0.1:8000",
      "/health": env.VAJRA_API_TARGET || "http://127.0.0.1:8000"
    }
  }
});
