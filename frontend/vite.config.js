import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Local development mirrors the production Nginx /api reverse proxy.  It lets
// `npm run dev` use the same relative API paths as the ECS deployment.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
});
