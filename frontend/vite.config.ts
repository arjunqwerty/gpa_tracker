import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The backend runs on port 8000 on this machine; the dev server forwards /api calls to it.
// host: true also serves the app to other devices on your network (http://<this machine's IP>:5173),
// while the backend itself stays reachable only from this machine.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { host: true, port: 5173, proxy: { "/api": "http://127.0.0.1:8000" } },
  preview: { host: true, port: 4173, proxy: { "/api": "http://127.0.0.1:8000" } },
});
